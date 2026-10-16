"""Offline PHP integration checks for immutable, bounded rolling source observations."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HELPER=ROOT/"wordpress/business-analysis-snapshot-receiver/rolling-retention.php"
RECEIVER=ROOT/"wordpress/business-analysis-snapshot-receiver/business-analysis-snapshot-receiver.php"
FAMILIES=("Business Analysis", "Project Management", "Information Security Analysis")

class BARollingRetentionTests(unittest.TestCase):
    def test_php_plugin_and_helper_syntax(self):
        if not shutil.which("php"):self.skipTest("PHP unavailable")
        for file in (HELPER,RECEIVER):
            p=subprocess.run(["php","-l",str(file)],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)

    def test_retains_original_run_and_observation_date(self):
        if not shutil.which("php"):self.skipTest("PHP unavailable")
        script=r"""
define('ABSPATH','/');
require $argv[1];
function doc($date, $family, $id, $run) {
  $names=array('CV-Library','Totaljobs','Reed UK','Indeed UK','JobServe');
  $sources=array(); foreach($names as $name)
    $sources[]=array('source'=>$name,'status'=>'SUCCEEDED',
      'attempted'=>true,'run_id'=>$run.'-'.$name,'dataset_id'=>$run.'-ds-'.$name);
  $row=array('id'=>$id,'title'=>$family,'role_family'=>$family,
      'job_source'=>'Indeed UK','source_run_id'=>$run.'-Indeed UK',
      'dataset_id'=>$run.'-ds-Indeed UK','original_advert_url'=>'https://example.com/'. $id,
      'observed_at'=>$date, 'advertiser'=>'Example');
  return array('schema'=>'ba-live-snapshot/v1','quality'=>array('passed'=>true),
    'refresh'=>array('status'=>'success','finished_at'=>$date),
    'sources'=>$sources,'records'=>array($row));
}
$first=doc('2026-10-01T10:00:00Z','Business Analysis','ba','runA');
$second=doc('2026-10-08T10:00:00Z','Project Management','pm','runB');
$third=doc('2026-10-10T10:00:00Z','Information Security Analysis','cyber','runC');
$combined=zarafy_ba_merge_rolling_snapshot($second,$first);
$combined=zarafy_ba_merge_rolling_snapshot($third,$combined);
$items=array(); foreach($combined['records'] as $r) $items[$r['id']]=$r;
$expired=zarafy_ba_merge_rolling_snapshot(
 doc('2026-11-03T10:00:00Z','Information Security Analysis','cyber2','runD'),$combined);
$ids=array_map(static function($r){return $r['id'];},$expired['records']);
echo json_encode(array(
 'schema'=>$combined['schema'], 'families'=>array_keys($items),
 'old_run'=>$items['ba']['source_run_id'],
 'old_date'=>$items['ba']['last_observed_at'],
 'old_age'=>$items['ba']['observed_age_days'],
 'historical_receipts'=>count($combined['historical_sources']),
 'old_expired'=>!in_array('ba',$ids,true),
 'current_receipts'=>count($combined['sources']),
 'status'=>$items['ba']['availability_status']
));
"""
        p=subprocess.run(["php","-r",script,str(HELPER)],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        d=json.loads(p.stdout)
        self.assertEqual(d["schema"],"ba-live-snapshot/v2")
        self.assertEqual(set(d["families"]),{"ba","pm","cyber"})
        self.assertEqual(d["old_run"],"runA-Indeed UK")
        self.assertEqual(d["old_date"],"2026-10-01T10:00:00Z")
        self.assertEqual(d["old_age"],9)
        self.assertEqual(d["historical_receipts"],2)
        self.assertEqual(d["current_receipts"],5)
        self.assertTrue(d["old_expired"])
        self.assertEqual(d["status"],"SOURCE_OBSERVED_NOT_EMPLOYER_CONFIRMED")

if __name__=="__main__":unittest.main()
