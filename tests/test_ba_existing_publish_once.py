"""No-spend Oct 18 publication gates; never send a live request in CI."""
import unittest
from datetime import datetime, timezone
from scripts.ba_publish_oct18_existing_once import (
    APPROVAL, TRIGGER, AUDITED_BY_SOURCE, AUDITED_REJECTIONS, AUDITED_SHA256,
    check_approval, verify_qa,
)

def environment():
    return {
        "BA_EXISTING_DATASET_PUBLISH_APPROVAL": APPROVAL,
        "BA_WP_DELIVERY_APPROVAL": "EXPLICIT_APPROVAL",
        "GITHUB_EVENT_NAME": "push",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_COMMIT_MESSAGE": TRIGGER,
        "APIFY_TOKEN": "test-only",
        "BA_WP_USERNAME": "test-only",
        "BA_WP_APPLICATION_PASSWORD": "test-only",
    }

class ExistingDatasetPublishSafetyTests(unittest.TestCase):
    def test_exact_single_run_gate(self):
        check_approval(environment(), datetime(2026,10,18,10,0,tzinfo=timezone.utc))
        for key, replacement in [
            ("GITHUB_EVENT_NAME", "workflow_dispatch"),
            ("GITHUB_RUN_ATTEMPT", "2"),
            ("GITHUB_REF", "refs/heads/other"),
            ("BA_EXISTING_DATASET_PUBLISH_APPROVAL", "NO"),
            ("BA_WP_DELIVERY_APPROVAL", ""),
            ("GITHUB_COMMIT_MESSAGE", "unrelated"),
            ("APIFY_TOKEN", ""),
        ]:
            with self.subTest(key=key):
                e=environment()
                e[key]=replacement
                with self.assertRaises(ValueError):
                    check_approval(e, datetime(2026,10,18,10,0,tzinfo=timezone.utc))

    def test_old_or_future_day_rejected(self):
        for dt in [
            datetime(2026,10,17,22,0,tzinfo=timezone.utc),
            datetime(2026,10,18,23,0,tzinfo=timezone.utc),
        ]:
            with self.assertRaises(ValueError):
                check_approval(environment(),dt)

    def test_audited_fingerprint_required_before_write(self):
        batch={"sources":[{"name":name,"records":[{} for _ in range(n)]}
                          for name,n in AUDITED_BY_SOURCE.items()]}
        expected={"status":"DRY_RUN_PASS_NOT_PUBLISHED", "raw_source_rows":159,
                  "matched":120, "rejected":dict(AUDITED_REJECTIONS),
                  "preview_sha256":AUDITED_SHA256}
        verify_qa(batch,expected)
        for field, value in [
            ("status","FAILED"),
            ("raw_source_rows",160),
            ("matched",121),
            ("rejected",{}),
            ("preview_sha256","bad"),
        ]:
            x=dict(expected)
            x[field]=value
            with self.subTest(field=field), self.assertRaises(ValueError):
                verify_qa(batch,x)
        batch["sources"][0]["records"].pop()
        with self.assertRaises(ValueError):
            verify_qa(batch, expected)

if __name__=="__main__":
    unittest.main()
