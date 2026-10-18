"""Provenance-bound static terms ledger for WordPress no-JS and JS display.

The ledger supplements the historical *display* only: never modifies the
original source snapshot or its genuine observation/refresh timestamps.
"""
from __future__ import annotations
import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "wordpress/business-analysis-snapshot-receiver"
LEDGER = PLUGIN / "evidenced-terms-20261018.json"


class TestBAPersistedTerms(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = json.loads(LEDGER.read_text(encoding="utf8"))

    def test_complete_unique_source_bound_evidence(self):
        doc = self.ledger
        self.assertEqual(doc["schema"], "ba-evidenced-terms/v1")
        self.assertEqual(doc["record_count"], 218)
        self.assertEqual(len(doc["records"]), 218)
        self.assertEqual(doc["as_of_source_observation"], "2026-10-18T08:16:56.668Z")
        keys = set()
        for rec_id, rec in doc["records"].items():
            self.assertTrue(rec_id)
            self.assertIn(rec["source"], {"CV-Library", "Totaljobs", "Reed UK", "Indeed UK", "JobServe"})
            self.assertTrue(rec["url"].startswith("https://"))
            self.assertRegex(rec["last_observed_at"], r"^2026-10-1[568]T")
            self.assertIn(rec["ir35_status"], {"Inside IR35", "Outside IR35", "Not stated", "Not applicable", "Check advert"})
            self.assertIn(rec["work_mode_display"], {"Hybrid", "Remote", "Remote (site visits)", "On-site", "Not stated"})
            key = (rec["source"], rec["url"])
            self.assertNotIn(key, keys)
            keys.add(key)
        records = list(doc["records"].values())
        self.assertEqual(sum(r["pay_display"] != "Not stated" for r in records), 72)
        self.assertEqual(sum(r["ir35_status"] in ("Inside IR35", "Outside IR35") for r in records), 35)
        self.assertEqual(sum(r["office_requirement"] != "Not stated" for r in records), 32)

    def test_jobserve_ir35_without_imaginary_day_rate(self):
        matches = [v for v in self.ledger["records"].values() if v["url"].endswith("/hGfqg")]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["ir35_status"], "Outside IR35")
        self.assertEqual(matches[0]["pay_display"], "Not stated")

    def test_php_overlay_accepts_exact_provenance_rejects_later_observations(self):
        if not shutil.which("php"):
            self.skipTest("PHP not available")
        php = (
            'define("ABSPATH","/");'
            'function add_action(){} function add_filter(){}'
            'require ' + json.dumps(str(PLUGIN / "business-analysis-snapshot-receiver.php")) + ';'
            '$data=json_decode(file_get_contents(' + json.dumps(str(LEDGER)) + '),true);'
            '$id=array_key_first($data["records"]);'
            '$e=$data["records"][$id];'
            '$r=["id"=>$id,"job_source"=>$e["source"],"original_advert_url"=>$e["url"],'
            '"last_observed_at"=>$e["last_observed_at"]];'
            'if(zarafy_ba_evidenced_terms($r)===null)exit(5);'
            '$r["last_observed_at"]="2026-10-19T00:00:00Z";'
            'if(zarafy_ba_evidenced_terms($r)!==null)exit(6);'
            '$r["last_observed_at"]=$e["last_observed_at"];'
            '$r["original_advert_url"]="https://example.com/wrong";'
            'if(zarafy_ba_evidenced_terms($r)!==null)exit(7);'
            'echo "MATCH_ONLY";'
        )
        proc = subprocess.run(["php", "-r", php], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertEqual(proc.stdout, "MATCH_ONLY")

if __name__ == "__main__":
    unittest.main()
