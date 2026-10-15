"""BA scheduled publication and spend safety (no external calls)."""
import json
import os
import unittest
from copy import deepcopy
from datetime import datetime, timezone, date
from zoneinfo import ZoneInfo
from unittest.mock import patch

from scripts.ba_controlled_refresh import CONFIG, validate as validate_config
from scripts.ba_recurring_cycle import scheduled_slot, build_live_document, main

class TestBARecurringCycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=json.loads(CONFIG.read_text(encoding="utf8"))

    def test_default_state_never_runs_paid_actors(self):
        meta=validate_config(self.cfg)
        self.assertTrue(meta["valid"])
        self.assertFalse(meta["enabled"])
        self.assertFalse(self.cfg["recurring_budget_approved"])
        self.assertFalse(self.cfg["pricing_guard_verified"])
        self.assertFalse(self.cfg["wordpress_delivery_enabled"])
        with patch.dict(os.environ,{"BA_PAID_REFRESH_APPROVAL":"EXPLICIT_BA_REFRESH_APPROVED"},clear=True), \
             patch("sys.argv",["ba_recurring_cycle","--execute","--scheduled"]):
            with self.assertRaises(SystemExit):
                main()

    def test_summer_and_winter_local_time(self):
        summer=datetime(2026,10,16,6,35,tzinfo=timezone.utc)  # Fri 07:35 BST
        winter=datetime(2026,11,6,7,35,tzinfo=timezone.utc)   # Fri 07:35 GMT
        self.assertTrue(scheduled_slot(summer)["due"])
        self.assertTrue(scheduled_slot(winter)["due"])
        self.assertFalse(scheduled_slot(datetime(2026,10,16,7,35,tzinfo=timezone.utc))["due"])
        self.assertFalse(scheduled_slot(datetime(2026,10,17,6,35,tzinfo=timezone.utc))["due"])

    def test_monthly_slot_count_never_exceeds_nine(self):
        # At most nine Tue/Fri pairs can occur in a calendar month.
        from calendar import monthrange
        for year in (2026,2027):
            for month in range(1,13):
                slots=[day for day in range(1,monthrange(year,month)[1]+1)
                       if date(year,month,day).weekday() in (1,4)]
                self.assertLessEqual(len(slots),9)
                y,m,d=year,month,slots[-1]
                dt=datetime(y,m,d,7,35,tzinfo=ZoneInfo("Europe/London"))
                self.assertTrue(scheduled_slot(dt)["due"])
                self.assertLessEqual(scheduled_slot(dt)["month_slots"],9)

    def test_snapshot_adapts_current_run_provenance_not_historic(self):
        sources=["CV-Library","Totaljobs","Reed UK","Indeed UK","JobServe"]
        time="2026-10-15T15:52:00Z"
        rows=[{"id":"id"+str(i),"title":"Business Analyst",
               "role_family":"Business Analysis",
               "source":src,"source_run_id":"run"+str(i),
               "dataset_id":"dataset"+str(i),
               "url":"https://www.jobserve.com/gb/en/example"+str(i)}
              for i,src in enumerate(sources)]
        batch={"sources":[{"name":src,"status":"SUCCEEDED","attempted":True,
                          "run_id":"run"+str(i),"dataset_id":"dataset"+str(i),
                          "observed_at":time} for i,src in enumerate(sources)]}
        qa={"status":"DRY_RUN_PASS_NOT_PUBLISHED",
            "candidate":{"records":rows,"publication_approved":False},
            "rejected":{}}
        # WordPress preflight only relies on all five sources, provenance, and HTTPS URLs.
        now=datetime(2026,10,15,16,0,tzinfo=timezone.utc)
        result=build_live_document(batch,qa,now)
        self.assertEqual(result["schema"],"ba-live-snapshot/v1")
        self.assertEqual(len(result["records"]),5)
        self.assertEqual(len(result["sources"]),5)
        self.assertEqual(result["refresh"]["type"],"CONTROLLED_FIVE_SOURCE_REFRESH")
        self.assertFalse(result["quality"]["independently_confirmed_open"])
        self.assertEqual(result["records"][0]["job_source"],"CV-Library")
        wrong=deepcopy(qa)
        wrong["candidate"]["records"][0]["source_run_id"]="other-run"
        with self.assertRaisesRegex(ValueError,"provenance"):
            build_live_document(batch,wrong,now)

    def test_incomplete_source_blocks_publication(self):
        sources=["CV-Library","Totaljobs","Reed UK","Indeed UK"]
        bad={"sources":[{"name":x,"status":"SUCCEEDED","attempted":True,
                         "run_id":"r","dataset_id":"d","observed_at":"2026-10-15T15:00:00Z"}
                        for x in sources]}
        with self.assertRaises(ValueError):
            build_live_document(bad,{"status":"DRY_RUN_PASS_NOT_PUBLISHED","candidate":{"records":[]}},datetime(2026,10,15,16,tzinfo=timezone.utc))

if __name__=="__main__":
    unittest.main()
