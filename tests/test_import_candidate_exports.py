import json
import tempfile
import unittest
from pathlib import Path

from scripts.import_candidate_exports import load_export

class ExistingExportImportTests(unittest.TestCase):
    def test_json_wrapped_and_explicit_source(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"existing.json"
            path.write_text(json.dumps({"items": [
                {"jobTitle":"SOC Analyst","jobUrl":"https://example.org/soc",
                 "companyName":"Employer","descriptionText":"SIEM"},
                {"jobTitle":"No URL"}
            ]}),encoding="utf-8")
            result=load_export(path,"Reed")
            self.assertEqual(len(result),1)
            self.assertEqual(result[0]["source"],"Reed")
            self.assertEqual(result[0]["title"],"SOC Analyst")
    def test_csv_import(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"existing.csv"
            path.write_text("title,url,description\\nData Analyst,https://example.org/data,SQL\\n",encoding="utf-8")
            # A real newline separated CSV, not escaped string.
            path.write_text(path.read_text(encoding="utf-8").replace("\\\\n","\n").replace("\\n","\n"),encoding="utf-8")
            result=load_export(path,"Totaljobs")
            self.assertEqual(result[0]["title"],"Data Analyst")
            self.assertEqual(result[0]["source"],"Totaljobs")
    def test_invalid_json_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"bad.json"
            path.write_text('{"status":"ok"}',encoding="utf-8")
            with self.assertRaises(ValueError):
                load_export(path,"Reed")

if __name__=="__main__":
    unittest.main()
