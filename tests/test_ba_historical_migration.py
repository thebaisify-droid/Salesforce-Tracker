"""Read-only 57-record migration assurance against actual historical pilot evidence."""
import json
import shutil
import subprocess
import unittest
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CANDIDATE=ROOT/"business-analysis-tracker/evidence/ba-five-source-publication-candidate-20261015.json"
HELPER=ROOT/"wordpress/business-analysis-snapshot-receiver/rolling-retention.php"
IDENTITIES={
    "CV-Library":("qo9YEfFlbYaV31MkK","OD5lSdCGHaw4q1D4j","2026-10-15T13:38:38.889Z"),
    "Totaljobs":("2TlvO2bI41Bl50TeR","Yt7qb5XvPgdWn3TSW","2026-10-15T13:39:04.363Z"),
    "Reed UK":("xLIKQOkwaZE5jFJn7","lecElui54GPzA0Qux","2026-10-15T13:39:24.929Z"),
    "Indeed UK":("i6unDcLG8Qh1XSftt","ssJHtekdlbvmP2UCZ","2026-10-15T13:39:51.979Z"),
    "JobServe":("c2PSagDDBiesSovtt","nkk1RZK5gznvfZogL","2026-10-15T15:51:48.728Z"),
}
CODE=r"""
define('ABSPATH','/');
require $argv[1];
$input=json_decode(stream_get_contents(STDIN),true);
$merged=zarafy_ba_merge_rolling_snapshot($input['current'],$input['previous']);
$source_counts=array();
$originals=array();
foreach ($merged['records'] as $row) {
    $name=$row['job_source'];
    $source_counts[$name]=($source_counts[$name]??0)+1;
    if ($row['id']!=='fresh-info-security') {
        $originals[$row['id']]=array(
          $row['last_observed_at']??null, $row['observation_timestamp_basis']??null);
    }
}
echo json_encode(array('count'=>count($merged['records']),
    'historic_receipts'=>count($merged['historical_sources']),
    'schema'=>$merged['schema'],'source_counts'=>$source_counts,
    'historical_observations'=>$originals,
    'last_observation_status'=>$merged['records'][0]['availability_status']??''));
"""

def fixtures():
    d=json.loads(CANDIDATE.read_text(encoding="utf8"))
    assert len(d["records"])==57
    rows=[]
    for row in d["records"]:
        r=dict(row)
        r["job_source"]=r["source"]
        r.pop("observed_at",None)
        rows.append(r)
    sources=[{"source":src,"status":"SUCCEEDED","attempted":True,
              "run_id":values[0],"dataset_id":values[1]}
             for src,values in IDENTITIES.items()]
    previous={"schema":"ba-live-snapshot/v1","quality":{"passed":True},
              "refresh":{"status":"success",
                 "finished_at":"2026-10-15T15:51:48.728Z",
                 "type":"HISTORICAL_COMPLETED_FIVE_SOURCE_PILOT"},
              "sources":sources,"records":rows}
    current_sources=[{"source":src,"status":"SUCCEEDED","attempted":True,
                "run_id":"newsource"+str(i),"dataset_id":"newdataset"+str(i)}
                 for i,src in enumerate(IDENTITIES)]
    source=next(x for x in current_sources if x["source"]=="Indeed UK")
    current={"schema":"ba-live-snapshot/v1",
             "refresh":{"status":"success","finished_at":"2026-10-16T04:45:00Z"},
             "quality":{"passed":True},
             "sources":current_sources,
             "records":[{"id":"fresh-info-security",
                 "title":"Information Security Analyst",
                 "job_source":"Indeed UK","role_family":"Information Security Analysis",
                 "source_run_id":source["run_id"],
                 "dataset_id":source["dataset_id"],
                 "original_advert_url":"https://uk.indeed.com/viewjob?jk=pilot-fresh",
                 "observed_at":"2026-10-16T04:45:00Z"}]}
    return {"current":current,"previous":previous}

class HistoricalPilotMigrationTest(unittest.TestCase):
    def test_57_historical_ads_remain_after_first_new_family_snapshot(self):
        if not shutil.which("php"):self.skipTest("PHP unavailable")
        data=fixtures()
        p=subprocess.run(["php","-r",CODE,str(HELPER)],
              input=json.dumps(data),capture_output=True,text=True,timeout=20)
        self.assertEqual(p.returncode,0,p.stderr+p.stdout)
        d=json.loads(p.stdout)
        self.assertEqual(d["count"],58)
        self.assertEqual(d["schema"],"ba-live-snapshot/v2")
        self.assertEqual(d["historic_receipts"],5)
        self.assertEqual(d["source_counts"]["Indeed UK"],7)
        self.assertEqual(d["source_counts"]["JobServe"],24)
        self.assertEqual(len(d["historical_observations"]),57)
        for row in data["previous"]["records"]:
            finish=IDENTITIES[row["source"]][2]
            self.assertEqual(d["historical_observations"][row["id"]],
                [finish,"ORIGINAL_ACTOR_RUN_FINISHED_AT"])
        self.assertEqual(d["last_observation_status"],
                         "SOURCE_OBSERVED_NOT_EMPLOYER_CONFIRMED")

    def test_unknown_legacy_actor_identity_is_not_given_fabricated_timestamp(self):
        if not shutil.which("php"):self.skipTest("PHP unavailable")
        data=fixtures()
        corrupted=data["previous"]["records"][0]
        corrupted["source_run_id"]="not-the-historical-run"
        p=subprocess.run(["php","-r",CODE,str(HELPER)],
             input=json.dumps(data),capture_output=True,text=True,timeout=20)
        self.assertEqual(p.returncode,0,p.stderr)
        d=json.loads(p.stdout)
        self.assertEqual(d["count"],57)
        self.assertNotIn(corrupted["id"],d["historical_observations"])

if __name__=="__main__":unittest.main()
