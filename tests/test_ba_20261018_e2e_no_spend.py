"""One controlled read-only E2E replay. No paid calls, no HTTP POST, no live changes.

Tests the production code on the archived five-source observations dated 2026-10-16.
The archived batch is historical: it must not be pushed as a fresh WordPress snapshot.
"""
import json
import unittest
from pathlib import Path

from scripts.ba_controlled_refresh import CONFIG, validate
from scripts.ba_e2e_offline import run_offline
from scripts.ba_reviewed_124_offline_replay import replay
from scripts.ba_stage_five_source_data import MAPPING, link, user_excluded_adverts, FINAL_SCOPE_DECISIONS

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/"business-analysis-tracker/evidence/ba-five-completed-20261016-audit-redacted.json"

class OfflineBusinessTrackerE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=json.loads(CONFIG.read_text(encoding="utf8"))
        cls.source=json.loads(ARCHIVE.read_text(encoding="utf8"))
        cls.mapping=json.loads(MAPPING.read_text(encoding="utf8"))
        cls.decisions=json.loads(FINAL_SCOPE_DECISIONS.read_text(encoding="utf8"))
        cls.receipts=cls.source["sources"]
        cls.batch={"schema":"ba-five-source-completed-batch/v1","sources":cls.receipts}
        cls.result=run_offline(cls.batch,cls.mapping)

    def test_guardrails_remain_paused(self):
        validated=validate(self.config)
        self.assertTrue(validated["valid"])
        self.assertFalse(validated["enabled"])
        self.assertFalse(self.config["paid_acquisition_enabled"])
        self.assertFalse(self.config["scheduling_enabled"])
        self.assertFalse(self.config["wordpress_delivery_enabled"])
        self.assertEqual((self.config["monthly_limit_usd"],
                          self.config["monthly_ba_allowance_usd"],
                          self.config["max_total_charge_usd"],
                          self.config["salesforce_reserve_usd"]),(19,11,1.2,8))

    def test_all_five_historical_sources_staged_and_packaged(self):
        r=self.result
        self.assertEqual(r["status"],"DRY_RUN_PASS_NOT_PUBLISHED")
        self.assertEqual((r["sources"],r["raw_source_rows"]),(5,161))
        self.assertEqual((r["actors_started"],r["wordpress_requests"]),(0,0))
        self.assertFalse(r["package"]["delivery_approved"])
        self.assertEqual(len(r["candidate"]["records"]),r["matched"])
        self.assertEqual(len({x["url"] for x in r["candidate"]["records"]}),r["matched"])
        self.assertTrue(r["preview_sha256"])
        self.assertEqual(r["matched"],81)
        print("BA_END_TO_END_REHEARSAL", json.dumps({
            "source_records":161,"source_boards":5,
            "automatic_scope_matches":r["matched"],
            "approved_scope_total":124,
            "manual_scope_gap_for_future_refresh":124-r["matched"],
            "excluded_by_user":37,"actors_started":0,
            "wordpress_requests":0,
            "status":r["status"],
            "preview_sha256":r["preview_sha256"]
        },sort_keys=True))

    def test_explicit_exclusions_absent_from_generated_candidate(self):
        self.assertEqual(len(user_excluded_adverts()),37)
        candidates={(r["source"],r["url"]) for r in self.result["candidate"]["records"]}
        self.assertTrue(candidates.isdisjoint(user_excluded_adverts()))
        observed={(s["name"],link(raw,s["name"]))
                  for s in self.receipts for raw in s["records"]}
        ledger={(x["source"],x["original_advert_url"]) for x in self.decisions["decisions"]}
        self.assertEqual(observed,ledger)
        self.assertEqual(len(observed),161)
        self.assertEqual(len([x for x in self.decisions["decisions"] if x["decision"]=="KEEP"]),124)

    def test_exact_user_reviewed_124_e2e_replay_without_paid_or_delivery(self):
        r=replay()
        self.assertEqual(r["status"],"REVIEWED_124_OFFLINE_READY_NOT_FRESH_NOT_PUBLISHED")
        self.assertEqual((r["source_records"],r["approved_records"],r["excluded_records"]),(161,124,37))
        self.assertEqual((r["baseline_automatic_records"],r["reviewed_exact_override_records"]),(81,43))
        self.assertEqual((r["actor_runs_started"],r["wordpress_requests"]),(0,0))
        self.assertFalse(r["package"]["delivery_approved"])
        keep={(x["source"],x["original_advert_url"])
              for x in self.decisions["decisions"] if x["decision"]=="KEEP"}
        actual={(x["source"],x["url"]) for x in r["candidate"]["records"]}
        self.assertEqual(keep,actual)
        self.assertTrue(actual.isdisjoint(user_excluded_adverts()))
        self.assertEqual(len({x["id"] for x in r["candidate"]["records"]}),124)
        self.assertTrue(all(x["scope_review_provenance"]=="EXACT_20261016_APPROVED_ADVERT"
                            for x in r["candidate"]["records"]))
        print("BA_REVIEWED_124_E2E",json.dumps({k:v for k,v in r.items()
             if k not in ("candidate","package")},sort_keys=True))

    def test_older_source_batch_must_not_be_republished_as_fresh(self):
        self.assertEqual(self.source["date"],"2026-10-16")
        self.assertIs(self.source["publication_approved"],False)
        self.assertFalse(self.result["candidate"]["publication_approved"])
        self.assertFalse(self.result["package"]["delivery_approved"])

if __name__=="__main__":unittest.main()
