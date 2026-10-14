"""Offline WordPress receiver checks. Never sends HTTP requests or writes WordPress."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

PLUGIN = Path("wordpress/salesforce-snapshot-receiver/salesforce-snapshot-receiver.php")


class SnapshotReceiverTests(unittest.TestCase):
    def test_contract_requires_admin_and_checksum(self):
        source = PLUGIN.read_text(encoding="utf-8")
        for required in (
            "current_user_can('manage_options')",
            "is_user_logged_in()",
            "hash_equals(",
            "sf_snapshot_validate($data)",
            "wp_get_upload_dir()",
            "wp_mkdir_p($dir)",
            "tempnam($dir, 'sf-stage-')",
            "rename($temporary, $target)",
            "delete_transient('zarafytek_sf_dashboard_v2')",
            "sf_rollback_refused",
            "36 * HOUR_IN_SECONDS",
        ):
            self.assertIn(required, source)
        self.assertNotIn("add_action('init'", source)

    @unittest.skipUnless(shutil.which("php"), "PHP executable unavailable")
    def test_php_syntax(self):
        p = subprocess.run(["php", "-l", str(PLUGIN)], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)

    @unittest.skipUnless(shutil.which("php"), "PHP executable unavailable")
    def test_validator_fail_closed(self):
        # WordPress functions are stubbed only in this isolated subprocess.
        script = r"""<?php
define('ABSPATH','/tmp/'); define('HOUR_IN_SECONDS',3600);
function add_action($name,$handler) {}
class WP_Error { public $code; function __construct($code,$msg,$details){$this->code=$code;} }
require 'wordpress/salesforce-snapshot-receiver/salesforce-snapshot-receiver.php';
$now=strtotime('2026-10-14T12:00:00Z');
$good=[
 'schema'=>'salesforce-hiring-dashboard/v1',
 'vacancies'=>[['title'=>'Salesforce Developer']],
 'active_vacancies'=>1,
 'pipeline'=>['quality_passed'=>true],
 'refresh'=>['status'=>'success','finished_at'=>'2026-10-14T11:00:00Z']
];
$ok=sf_snapshot_validate($good,$now);
$bad=$good; $bad['pipeline']['quality_passed']=false;
$failed=sf_snapshot_validate($bad,$now);
$stale=$good; $stale['refresh']['finished_at']='2026-10-10T06:41:39Z';
$old=sf_snapshot_validate($stale,$now);
$future=$good; $future['refresh']['finished_at']='2026-10-15T11:00:00Z';
$soon=sf_snapshot_validate($future,$now);
echo json_encode(['ok'=>is_int($ok),'qa'=>$failed instanceof WP_Error,
 'stale'=>$old instanceof WP_Error,'future'=>$soon instanceof WP_Error]);
"""
        p = subprocess.run(["php"], input=script, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout), {"ok": True, "qa": True,
                                               "stale": True, "future": True})
