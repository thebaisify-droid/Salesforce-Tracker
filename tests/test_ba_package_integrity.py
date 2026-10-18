"""Protect the published, manual-install ZIP from corruption or source drift."""
from pathlib import Path
from zipfile import ZipFile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "dist/business-analysis-snapshot-receiver-v0.3.6.zip"
PLUGIN = ROOT / "wordpress/business-analysis-snapshot-receiver"
PREFIX = "business-analysis-snapshot-receiver/"
FILES = ("business-analysis-snapshot-receiver.php", "rolling-retention.php", "evidenced-terms-20261018.json")

class BAPackageIntegrityTests(unittest.TestCase):
    def test_zip_is_valid_and_byte_identical_to_reviewed_plugin(self):
        self.assertTrue(PACKAGE.is_file())
        with ZipFile(PACKAGE) as z:
            self.assertEqual(set(z.namelist()), {PREFIX+name for name in FILES})
            self.assertIsNone(z.testzip(), "ZIP entry CRC mismatch")
            for name in FILES:
                self.assertEqual(z.read(PREFIX+name),(PLUGIN/name).read_bytes())
            self.assertIn(b"Version: 0.3.6",z.read(PREFIX+FILES[0]))

if __name__ == "__main__":
    unittest.main()
