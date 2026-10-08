import json
import unittest
from pathlib import Path

class ActorSchemaEvidenceTests(unittest.TestCase):
    def test_candidate_actor_matches_not_falsely_verified(self):
        evidence=json.loads(Path("config/candidate_actor_schema_evidence.example.json").read_text())
        self.assertTrue(evidence["offline_only"])
        self.assertFalse(evidence["paid_runs_authorised"])
        self.assertFalse(evidence["task_mutations_authorised"])
        self.assertEqual({x["source"] for x in evidence["actors"]},{"CV-Library","Totaljobs"})
        for actor in evidence["actors"]:
            self.assertFalse(actor["actor_id_match_verified"])
            self.assertFalse(actor["field_support_for_actual_saved_task_verified"])
            self.assertTrue(actor["documentation_url"].startswith("https://apify.com/"))
if __name__=="__main__":unittest.main()
