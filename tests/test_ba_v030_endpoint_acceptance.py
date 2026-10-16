"""Execute real receiver endpoint under isolated WordPress stubs. No network or production writes."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PLUGIN=ROOT/"wordpress/business-analysis-snapshot-receiver/business-analysis-snapshot-receiver.php"

PHP=r"""
error_reporting(E_ALL);
define('ABSPATH', '/');
define('HOUR_IN_SECONDS', 3600);
class WP_Error {
    private $code;
    public function __construct($code, $msg, $meta=[]) {$this->code=$code;}
    public function get_error_code() {return $this->code;}
}
class WP_REST_Request {
    private $value;
    public function __construct($body) {$this->value=$body;}
    public function get_json_params() {return $this->value;}
    public function get_body() {return json_encode($this->value);}
}
function is_wp_error($x) {return $x instanceof WP_Error;}
function wp_http_validate_url($url) {return is_string($url) && str_starts_with($url,'https://');}
function wp_get_upload_dir() {return ['basedir'=>$GLOBALS['sandbox'], 'error'=>false];}
function trailingslashit($path) {return rtrim($path,'/').'/';}
function wp_mkdir_p($dir) {return is_dir($dir)||mkdir($dir,0770,true);}
function add_action($a,$b) {}
function add_filter($a,$b,$p) {}
function is_page($id) {return $id===49;}
function get_the_ID() {return 49;}
function wp_json_encode($value, $flags=0) {return json_encode($value, $flags);}
function wp_parse_url($url) {return parse_url($url);}
function wp_date($format,$time) {return gmdate($format,$time);}
function esc_html($text) {return htmlspecialchars((string)$text, ENT_QUOTES, 'UTF-8');}
function esc_url($url) {return htmlspecialchars((string)$url,ENT_QUOTES,'UTF-8');}
require $argv[1];
$GLOBALS['sandbox']=sys_get_temp_dir().'/ba-receiver-acceptance-'.bin2hex(random_bytes(5));
mkdir($GLOBALS['sandbox'],0770,true);
function document($src,$family,$id,$label,$timestamp) {
  $names=['CV-Library','Totaljobs','Reed UK','Indeed UK','JobServe'];
  $sources=[];
  foreach ($names as $name) $sources[]=[
    'source'=>$name, 'run_id'=>$label.'-'.str_replace(' ','',$name),
    'dataset_id'=>$label.'-dataset-'.str_replace(' ','',$name),
    'status'=>'SUCCEEDED','attempted'=>true
  ];
  $match=array_values(array_filter($sources,static fn($x)=>$x['source']===$src))[0];
  $record=[
    'id'=>$id, 'title'=>$family.' vacancy', 'role_family'=>$family,
    'job_source'=>$src, 'source_run_id'=>$match['run_id'],
    'dataset_id'=>$match['dataset_id'],
    'observed_at'=>$timestamp,
    'original_advert_url'=>'https://example.org/jobs/'.rawurlencode($id),
    'description_summary'=>'Example source excerpt',
    'posted_date'=>substr($timestamp,0,10),
    'advertiser'=>'Example Ltd','location'=>'London','source_observed_only'=>true
  ];
  return ['schema'=>'ba-live-snapshot/v1','quality'=>['passed'=>true],
    'refresh'=>['status'=>'success','finished_at'=>$timestamp],
    'sources'=>$sources,'records'=>[$record]];
}
function request_snapshot($d,$badChecksum=false) {
  $raw=json_encode($d);
  return new WP_REST_Request([
    'snapshot'=>$raw,
    'sha256'=>$badChecksum?str_repeat('0',64):hash('sha256',$raw)
  ]);
}
function outcome($x) {return is_wp_error($x)?$x->get_error_code():'accepted';}

$a=document('Totaljobs','Business Analysis','ba','runA',gmdate('Y-m-d\\TH:i:s\\Z',time()-3000));
$b=document('Indeed UK','Information Security Analysis','infosec','runB',gmdate('Y-m-d\\TH:i:s\\Z',time()-120));
$a_success=zarafy_ba_receive(request_snapshot($a));
$b_success=zarafy_ba_receive(request_snapshot($b));
$stored=json_decode(file_get_contents($GLOBALS['sandbox'].'/business-analysis-tracker/live-data.json'),true);
$map=[];
foreach ($stored['records'] as $r) $map[$r['id']]=$r;
$replay=outcome(zarafy_ba_receive(request_snapshot($b)));
$c=document('JobServe','Project Management','pm','runC',gmdate('Y-m-d\\TH:i:s\\Z',time()-5));
$checksum=outcome(zarafy_ba_receive(request_snapshot($c,true)));
$forged=$c;
$forged['records'][0]['dataset_id']='wrong-dataset';
$forgery=outcome(zarafy_ba_receive(request_snapshot($forged)));
$unchanged=json_decode(file_get_contents($GLOBALS['sandbox'].'/business-analysis-tracker/live-data.json'),true);

$example='<div class="ba-wrap"></div><tbody id="ba-v2-body"></tbody><script type="application/json" id="ba-v2-json">[]</script><strong id="ba-v2-status" aria-live="polite">0</strong>';
$rendered=zarafy_ba_live_content_bridge($example);
echo json_encode([
 'accepted1'=>outcome($a_success),
 'accepted2'=>outcome($b_success),
 'currentCount2'=>$b_success['record_count']??null,
 'retainedCount2'=>$b_success['retained_display_count']??null,
 'storedSchema'=>$stored['schema'],
 'storedCount'=>count($stored['records']),
 'historicalCount'=>count($stored['historical_sources']),
 'oldRun'=>$map['ba']['source_run_id']??'',
 'oldDate'=>$map['ba']['last_observed_at']??'',
 'newRun'=>$map['infosec']['source_run_id']??'',
 'oldSource'=>$map['ba']['job_source']??'',
 'replayRejected'=>$replay,
 'checksumRejected'=>$checksum,
 'forgeryRejected'=>$forgery,
 'unchangedAfterRejections'=>count($unchanged['records'])===2,
 'pageHasBA'=>str_contains($rendered,'Business Analysis vacancy'),
 'pageHasInfosec'=>str_contains($rendered,'Information Security Analysis vacancy'),
 'pageShowsObserved'=>str_contains($rendered,'Last source observation'),
 'pageShowsCaveat'=>str_contains($rendered,'Not employer-confirmed open')
]);
$dir=$GLOBALS['sandbox'].'/business-analysis-tracker';
foreach (glob($dir.'/*') as $file) if(is_file($file))unlink($file);
@unlink($dir.'/.snapshot.lock');@rmdir($dir);@rmdir($GLOBALS['sandbox']);
"""

class BAV03EndpointAcceptance(unittest.TestCase):
    def test_atomic_receiver_two_consecutive_real_calls(self):
        if not shutil.which('php'):
            self.skipTest('PHP unavailable')
        cmd=['php','-r',PHP,str(PLUGIN)]
        result=subprocess.run(cmd, capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr+result.stdout)
        d=json.loads(result.stdout)
        self.assertEqual(d['accepted1'],'accepted')
        self.assertEqual(d['accepted2'],'accepted')
        self.assertEqual(d['currentCount2'],1)
        self.assertEqual(d['retainedCount2'],2)
        self.assertEqual(d['storedSchema'],'ba-live-snapshot/v2')
        self.assertEqual(d['storedCount'],2)
        self.assertEqual(d['historicalCount'],1)
        self.assertTrue(d['oldRun'].startswith('runA-'))
        self.assertTrue(d['newRun'].startswith('runB-'))
        self.assertTrue(d['oldDate'])
        self.assertEqual(d['oldSource'],'Totaljobs')
        self.assertEqual(d['replayRejected'],'ba_rollback')
        self.assertEqual(d['checksumRejected'],'ba_checksum')
        self.assertEqual(d['forgeryRejected'],'ba_bad_row')
        for key in ('unchangedAfterRejections','pageHasBA','pageHasInfosec','pageShowsObserved','pageShowsCaveat'):
            self.assertTrue(d[key],key)

if __name__=='__main__':
    unittest.main()
