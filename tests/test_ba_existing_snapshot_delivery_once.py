import json,unittest
from datetime import datetime,timezone,timedelta
from copy import deepcopy
from scripts.ba_existing_snapshot_delivery_once import CANDIDATE,build_snapshot,LAST_SOURCE_FINISHED_AT
from scripts.ba_atomic_snapshot_sender import envelope
class BASnapshotControlledDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads(CANDIDATE.read_text(encoding="utf8"))
        cls.test_time=datetime(2026,10,15,20,45,tzinfo=timezone.utc)
    def test_receives_only_existing_observations(self):
        d=build_snapshot(self.data,now=self.test_time)
        self.assertEqual(len(d["records"]),57)
        self.assertEqual(len(d["sources"]),5)
        self.assertEqual(d["refresh"]["finished_at"],LAST_SOURCE_FINISHED_AT)
        self.assertEqual(d["refresh"]["type"],"HISTORICAL_COMPLETED_FIVE_SOURCE_PILOT")
        self.assertFalse(d["quality"]["independently_confirmed_open"])
        self.assertEqual(len(envelope(d)["sha256"]),64)
        self.assertTrue(all(r["source_observed_only"] for r in d["records"]))
    def test_mismatched_run_cannot_be_sent(self):
        b=deepcopy(self.data)
        b["records"][0]["source_run_id"]="forged-source-run"
        with self.assertRaisesRegex(ValueError,"provenance"):
            build_snapshot(b,now=self.test_time)
    def test_stale_data_fail_closed(self):
        late=datetime(2026,10,18,tzinfo=timezone.utc)
        with self.assertRaisesRegex(ValueError,"too old"):
            build_snapshot(self.data,now=late)
    def test_count_or_duplicate_review_changes_are_blocked(self):
        changed=deepcopy(self.data)
        changed["probable_cross_post_pairs"]=0
        with self.assertRaises(ValueError):
            build_snapshot(changed,now=self.test_time)
        changed=deepcopy(self.data)
        changed["records"].pop()
        with self.assertRaises(ValueError):
            build_snapshot(changed,now=self.test_time)
if __name__=="__main__":
    unittest.main()
