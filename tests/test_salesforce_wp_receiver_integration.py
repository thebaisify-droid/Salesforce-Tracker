"""Disposable local WordPress-stub integration; never touches the live site."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which("php"), "PHP executable required")
class ReceiverStagingIntegration(unittest.TestCase):
    def test_authorisation_checksums_replay_rollback_and_atomic_storage(self):
        script = r"""<?php
define('ABSPATH', '/tmp/'); define('HOUR_IN_SECONDS', 3600);
class WP_Error {
 public $code;
 public function __construct($code, $message, $data) {$this->code=$code;}
}
class WP_REST_Request {
 private $data;
 public function __construct($data) {$this->data=$data;}
 public function get_json_params() {return $this->data;}
 public function get_body() {return json_encode($this->data);}
}
function add_action($event,$callback) {if ($event==='rest_api_init') {$callback();}}
function register_rest_route($space,$route,$config) {$GLOBALS['permission']=$config['permission_callback'];}
function is_user_logged_in() {return (bool) $GLOBALS['logged_in'];}
function current_user_can($permission) {return $permission==='sf_deliver_snapshot' && (bool) $GLOBALS['has_cap'];}
function is_wp_error($result) {return $result instanceof WP_Error;}
function wp_get_upload_dir() {return ['error'=>false,'basedir'=>$GLOBALS['basedir']];}
function trailingslashit($s) {return rtrim($s, '/').'/';}
function wp_mkdir_p($s) {return is_dir($s) || mkdir($s,0700,true);}
function delete_transient($key) {$GLOBALS['cleared'][]=$key;}
require 'wordpress/salesforce-snapshot-receiver/salesforce-snapshot-receiver.php';
$GLOBALS['basedir'] = sys_get_temp_dir().'/sf-receiver-'.bin2hex(random_bytes(8));
mkdir($GLOBALS['basedir'],0700,true);
$GLOBALS['logged_in']=false; $GLOBALS['has_cap']=false;
($GLOBALS['permission'])();
$deny=($GLOBALS['permission'])()===false;
$GLOBALS['logged_in']=true; $GLOBALS['has_cap']=true;
$allow=($GLOBALS['permission'])()===true;
$now=gmdate('Y-m-d\TH:i:s\Z');
$good=['schema'=>'salesforce-hiring-dashboard/v1',
 'vacancies'=>[['title'=>'Salesforce Developer']], 'active_vacancies'=>1,
 'pipeline'=>['quality_passed'=>true],
 'refresh'=>['status'=>'success','finished_at'=>$now]];
$raw=json_encode($good);
$envelope=['snapshot'=>$raw,'sha256'=>hash('sha256',$raw)];
$invalid=$envelope; $invalid['sha256']=str_repeat('a',64);
$bad=sf_snapshot_receive(new WP_REST_Request($invalid));
$first=sf_snapshot_receive(new WP_REST_Request($envelope));
$target=$GLOBALS['basedir'].'/salesforce-tracker/live-data.json';
$bytes=is_file($target)?file_get_contents($target):'';
$replay=sf_snapshot_receive(new WP_REST_Request($envelope));
$prior=$good;$prior['refresh']['finished_at']=gmdate('Y-m-d\TH:i:s\Z',time()-3500);
$earlier=json_encode($prior);
$older=sf_snapshot_receive(new WP_REST_Request(['snapshot'=>$earlier,'sha256'=>hash('sha256',$earlier)]));
$lock=fopen($GLOBALS['basedir'].'/salesforce-tracker/.salesforce-snapshot.lock','c');
flock($lock,LOCK_EX|LOCK_NB);
$busy=sf_snapshot_receive(new WP_REST_Request($envelope));
flock($lock,LOCK_UN);fclose($lock);
$files=glob($GLOBALS['basedir'].'/salesforce-tracker/sf-stage-*');
echo json_encode([
 'unauthorised_denied'=>$deny,'capability_allowed'=>$allow,
 'bad_checksum_rejected'=>$bad instanceof WP_Error && $bad->code==='sf_checksum_failed',
 'accepted'=>is_array($first)&&($first['accepted']??false)===true,
 'bytes_match'=>$bytes===$raw,
 'replay_idempotent'=>is_array($replay)&&($replay['accepted']??false)===true,
 'rollback_rejected'=>$older instanceof WP_Error && $older->code==='sf_rollback_refused',
 'lock_rejected'=>$busy instanceof WP_Error && $busy->code==='sf_busy',
 'no_temp_remaining'=>count($files)===0,
 'cache_cleared'=>in_array('zarafytek_sf_dashboard_v2',$GLOBALS['cleared']??[],true)
]);
unlink($target);unlink($GLOBALS['basedir'].'/salesforce-tracker/.salesforce-snapshot.lock');
rmdir($GLOBALS['basedir'].'/salesforce-tracker');rmdir($GLOBALS['basedir']);
"""
        p = subprocess.run(["php"], input=script, capture_output=True, text=True,
                           timeout=15)
        self.assertEqual(p.returncode, 0, p.stderr)
        values = json.loads(p.stdout)
        self.assertTrue(all(values.values()), values)
