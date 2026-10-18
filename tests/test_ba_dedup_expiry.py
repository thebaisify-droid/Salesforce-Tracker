"""Read-only regression for rolling advert identity and 30-day render-time expiry."""
import json
import shutil
import subprocess
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "wordpress/business-analysis-snapshot-receiver/rolling-retention.php"
RECEIVER = ROOT / "wordpress/business-analysis-snapshot-receiver/business-analysis-snapshot-receiver.php"
SOURCES = ("CV-Library", "Totaljobs", "Reed UK", "Indeed UK", "JobServe")
MERGE_SCRIPT = r"""
define('ABSPATH', '/');
require $argv[1];
$d=json_decode(stream_get_contents(STDIN),true);
$m=zarafy_ba_merge_rolling_snapshot($d['current'],$d['prior']??null);
echo json_encode($m);
"""
DISPLAY_SCRIPT = r"""
define('ABSPATH','/');
define('DAY_IN_SECONDS',86400);
function add_action(){ }
function add_filter(){ }
function is_page($id){return $id===49;}
function get_the_ID(){return 49;}
function wp_get_upload_dir(){return ['basedir'=>$GLOBALS['dir'], 'error'=>''];}
function wp_parse_url($s){return parse_url($s);}
function wp_json_encode($v,$flags=0){return json_encode($v,$flags);}
function wp_date($f,$t){return gmdate($f,$t);}
function esc_html($s){return htmlspecialchars((string)$s,ENT_QUOTES);}
function esc_attr($s){return htmlspecialchars((string)$s,ENT_QUOTES);}
function esc_url($s){return htmlspecialchars((string)$s,ENT_QUOTES);}
require $argv[1];
$GLOBALS['dir']=sys_get_temp_dir().'/ba-expiry-test-'.getmypid();
mkdir($GLOBALS['dir'].'/business-analysis-tracker',0700,true);
$path=$GLOBALS['dir'].'/business-analysis-tracker/live-data.json';
$d=json_decode(stream_get_contents(STDIN),true);
file_put_contents($path, $d['mode']==='invalid' ? 'INVALID' : json_encode($d['snapshot']));
$template='<div class="ba-wrap"><b id="ba-v2-total">181</b><b id="ba-v2-family-total">22 / 28</b><strong id="ba-v2-status" aria-live="polite">181 of 181 advertisements shown</strong><tbody id="ba-v2-body"><tr>STALE_ARCHIVE_MARKER</tr></tbody><script type="application/json" id="ba-v2-json">[{"title":"STALE_ARCHIVE_MARKER"}]</script><select id="ba-v2-family"></select></div>';
$out=zarafy_ba_live_content_bridge($template);
preg_match('/<script type="application\/json" id="ba-v2-json">(.+?)<\/script>/s',$out,$match);
echo json_encode([
  'notice'=>strpos($out,'No retained source-observed adverts available')!==false,
  'stale_archive_exposed'=>strpos($out,'STALE_ARCHIVE_MARKER')!==false,
  'count_one'=>strpos($out,'<b id="ba-v2-total">1</b>')!==false,
  'family_one'=>strpos($out,'<b id="ba-v2-family-total">1 / 28</b>')!==false,
  'status_one'=>strpos($out,'1 of 1 advertisements shown')!==false,
  'records'=>isset($match[1])?json_decode($match[1],true):null,
]);
@unlink($path);
@rmdir($GLOBALS['dir'].'/business-analysis-tracker');
@rmdir($GLOBALS['dir']);
"""

def run_php(script, path, data):
    completed = subprocess.run(
        ["php", "-r", script, str(path)], input=json.dumps(data),
        text=True, capture_output=True, timeout=20,
    )
    if completed.returncode:
        raise AssertionError(completed.stderr + completed.stdout)
    return json.loads(completed.stdout)

def receipts(run):
    return [{"source": source, "status": "SUCCEEDED", "attempted": True,
             "run_id": f"{run}-{i}", "dataset_id": f"{run}-dataset-{i}"}
            for i, source in enumerate(SOURCES)]

def row(source, run, identity, advert, when, family="Business Analysis"):
    i=SOURCES.index(source)
    return {
        "id": identity, "title": identity, "role_family": family,
        "job_source": source, "source_run_id": f"{run}-{i}",
        "dataset_id": f"{run}-dataset-{i}",
        "original_advert_url": advert, "observed_at": when,
        "last_observed_at": when, "advertiser": "Fixture company",
        "posted_date": when[:10],
    }

def snapshot(run, finished, records):
    return {"schema":"ba-live-snapshot/v1", "quality":{"passed":True},
            "refresh":{"status":"success","finished_at":finished},
            "sources":receipts(run), "records":records}

def dt(delta):
    return (datetime.now(timezone.utc)-delta).isoformat(timespec="seconds").replace("+00:00","Z")

@unittest.skipUnless(shutil.which("php"), "PHP unavailable")
class BADedupExpiryTests(unittest.TestCase):
    def test_cross_run_duplicate_uses_newest_source_receipt(self):
        before="2026-10-15T10:00:00Z"
        after="2026-10-16T10:00:00Z"
        url="https://www.jobserve.com/gb/en/hGeRi"
        old=snapshot("old",before,[row("JobServe","old","pilot-1",url,before)])
        new=snapshot("new",after,[row("JobServe","new","new-identity",url,after)])
        d=run_php(MERGE_SCRIPT,HELPER,{"current":new,"prior":old})
        self.assertEqual(len(d["records"]),1)
        kept=d["records"][0]
        self.assertEqual(kept["id"],"new-identity")
        self.assertEqual(kept["source_run_id"],"new-4")
        self.assertEqual(kept["last_observed_at"],after)
        self.assertEqual(len(d["historical_sources"]),0)

    def test_distinct_sources_urls_and_six_approved_families_survive(self):
        when="2026-10-16T10:00:00Z"
        shared="https://jobs.example.com/job/1"
        extra=["Technology Leadership & Management",
               "Enterprise & Solution Architecture",
               "IT Infrastructure & Support Engineering",
               "Engineering & Technical Delivery",
               "Security Engineering",
               "Technology Governance, Risk & Compliance"]
        records=[row("Reed UK","new","r1",shared,when),
                 row("JobServe","new","j1",shared,when)]
        records.extend(row("Totaljobs","new",f"tech-{i}",f"https://jobs.example.com/job/{i+2}",
                           when,family) for i,family in enumerate(extra))
        d=run_php(MERGE_SCRIPT,HELPER,{"current":snapshot("new",when,records)})
        self.assertEqual(len(d["records"]),8)
        self.assertEqual(set(extra).difference(r["role_family"] for r in d["records"]),set())

    def test_display_collapses_stored_duplicates_expires_old_and_updates_counts(self):
        finished=dt(timedelta(days=2))
        recent=dt(timedelta(days=2,hours=1))
        older=dt(timedelta(days=3))
        expired=dt(timedelta(days=30,hours=6))
        url="https://www.jobserve.com/gb/en/test-42"
        rnew=row("JobServe","now","new",url,recent)
        rold=row("JobServe","then","old",url,older)
        r_exp=row("Reed UK","then","expired","https://www.reed.co.uk/jobs/expired",expired)
        d=snapshot("now",finished,[rnew,rold,r_exp])
        d["schema"]="ba-live-snapshot/v2"
        d["historical_sources"]=receipts("then")
        result=run_php(DISPLAY_SCRIPT,RECEIVER,{"mode":"valid","snapshot":d})
        self.assertFalse(result["notice"])
        self.assertFalse(result["stale_archive_exposed"])
        self.assertTrue(result["count_one"])
        self.assertTrue(result["family_one"])
        self.assertTrue(result["status_one"])
        self.assertEqual(len(result["records"]),1)
        self.assertEqual(result["records"][0]["id"],"new")

    def test_display_fails_closed_when_all_records_expire(self):
        finished=dt(timedelta(days=2))
        expired=dt(timedelta(days=30,hours=6))
        d=snapshot("now",finished,[])
        d["schema"]="ba-live-snapshot/v2"
        d["historical_sources"]=receipts("then")
        d["records"]=[row("JobServe","then","old","https://www.jobserve.com/gb/en/old",expired)]
        result=run_php(DISPLAY_SCRIPT,RECEIVER,{"mode":"valid","snapshot":d})
        self.assertTrue(result["notice"])
        self.assertFalse(result["stale_archive_exposed"])
        self.assertIsNone(result["records"])

    def test_display_fails_closed_when_snapshot_unreadable(self):
        result=run_php(DISPLAY_SCRIPT,RECEIVER,{"mode":"invalid","snapshot":{}})
        self.assertTrue(result["notice"])
        self.assertFalse(result["stale_archive_exposed"])
        self.assertIsNone(result["records"])

if __name__=="__main__":unittest.main()
