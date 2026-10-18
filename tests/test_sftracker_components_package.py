"""Verify manually installable Salesforce-only migration ZIP matches reviewed source."""
from pathlib import Path
from zipfile import ZipFile
import unittest
ROOT=Path(__file__).resolve().parents[1]
FILES=(
 "salesforce-tracker-components.php",
 "includes/salesforce-snapshot-receiver.php",
 "includes/sf-phase1-snapshot-explorer.php",
)
class SalesforceComponentsMigrationTests(unittest.TestCase):
 def test_package_is_source_identical(self):
  pkg=ROOT/"dist/salesforce-tracker-components-v1.0.0.zip"
  src=ROOT/"wordpress/salesforce-tracker-components"
  with ZipFile(pkg) as z:
   self.assertIsNone(z.testzip())
   self.assertEqual(set(z.namelist()),{"salesforce-tracker-components/"+p for p in FILES})
   for p in FILES:
    self.assertEqual(z.read("salesforce-tracker-components/"+p),(src/p).read_bytes())
   self.assertIn(b"Version: 1.0.0",z.read("salesforce-tracker-components/salesforce-tracker-components.php"))
