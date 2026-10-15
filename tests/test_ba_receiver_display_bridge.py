"""Ensure independent BA receiver provides a read-only, fail-closed page bridge."""
import shutil
import subprocess
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1] / "wordpress/business-analysis-snapshot-receiver/business-analysis-snapshot-receiver.php"

class BAReceiverDisplayBridgeTests(unittest.TestCase):
    def test_php_syntax(self):
        if not shutil.which("php"):
            self.skipTest("PHP CLI unavailable in runner")
        result = subprocess.run(["php", "-l", str(PLUGIN)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_isolation_and_fallback_code(self):
        source = PLUGIN.read_text(encoding="utf-8")
        self.assertIn("function zarafy_ba_live_content_bridge(", source)
        self.assertIn("is_page(49)", source)
        self.assertIn("get_the_ID() !== 49", source)
        self.assertIn("return $content;", source)
        self.assertIn("'business-analysis-tracker'", source)
        self.assertIn("'<tbody id=\"ba-v2-body\">''".strip("'"), source)
        self.assertIn("'ba-live-snapshot/v1'", source)
        self.assertIn("array('CV-Library','Totaljobs','Reed UK','Indeed UK','JobServe')", source)
        self.assertIn("JSON_HEX_TAG", source)
        self.assertNotIn("salesforce_tracker.db", source)

if __name__ == "__main__":
    unittest.main()
