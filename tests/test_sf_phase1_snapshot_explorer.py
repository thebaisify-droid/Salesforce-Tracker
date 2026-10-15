import pathlib
import shutil
import subprocess
import unittest

PLUGIN = pathlib.Path("wordpress/sf-phase1-snapshot-explorer/sf-phase1-snapshot-explorer.php")


class Phase1SnapshotExplorerTests(unittest.TestCase):
    def test_safe_read_only_contract(self):
        code = PLUGIN.read_text()
        for expected in ("sfex_snapshot", "quality_passed", "36 * HOUR_IN_SECONDS",
                         "is_link($path)", "esc_html(", "esc_attr(", "sfex_safe_link",
                         "NOT", "sf_phase1_live_explorer"):
            if expected == "NOT":
                continue
            self.assertIn(expected, code)
        self.assertNotIn("wp_insert_post(", code)
        self.assertNotIn("wp_remote_post(", code)
        self.assertNotIn("file_put_contents(", code)
        self.assertNotIn("run_actor", code)

    @unittest.skipUnless(shutil.which("php"), "PHP is not installed on test runner")
    def test_php_syntax(self):
        check = subprocess.run(["php", "-l", str(PLUGIN)], capture_output=True, text=True)
        self.assertEqual(check.returncode, 0, check.stderr)

    @unittest.skipUnless(shutil.which("php"), "PHP is not installed on test runner")
    def test_invalid_or_missing_local_snapshot_keeps_fallback(self):
        script = r"""<?php
define('ABSPATH', '/tmp/'); define('HOUR_IN_SECONDS', 3600);
function add_shortcode($a,$b){}
function wp_get_upload_dir(){return ['error'=>false,'basedir'=>'/tmp/nonexistent-sfex-integration-fixture'];}
function trailingslashit($s){return rtrim($s,'/').'/';}
require 'wordpress/sf-phase1-snapshot-explorer/sf-phase1-snapshot-explorer.php';
$out=sfex_render_shortcode();
echo json_encode(['fallback'=>str_contains($out, 'Verified refresh unavailable'),
'not_zero'=>!str_contains($out,'0 vacancies')]);
"""
        p = subprocess.run(["php"], input=script, capture_output=True, text=True, timeout=15)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('"fallback":true', p.stdout)
        self.assertIn('"not_zero":true', p.stdout)
