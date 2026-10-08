import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.stage_candidate_market import main

class StageCandidateMarketTests(unittest.TestCase):
    def test_offline_staging(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            src = folder / "input.json"
            db = folder / "market.db"
            out = folder / "preview.json"
            src.write_text(json.dumps([
                {"title": "Senior Product Manager", "url": "https://jobs.test/p", "source": "Reed"},
                {"title": "Information Security Analyst", "url": "https://jobs.test/s", "source": "Totaljobs"},
            ]), encoding="utf-8")
            with patch("sys.argv", ["stage_candidate_market", "--input", str(src),
                                    "--database", str(db), "--batch-id", "fixture-1",
                                    "--output", str(out)]):
                self.assertEqual(main(), 0)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["total_vacancies"], 2)
            self.assertEqual([x["value"] for x in payload["by_track"]], [1, 1])
            self.assertFalse(payload["publication_approved"])

if __name__ == "__main__":
    unittest.main()
