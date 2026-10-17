"""Fail-closed source-count checks. No Apify charges, network, or publishing."""
import json
import os
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from scripts.ba_controlled_refresh import CONFIG, run, verified_dataset_count
from scripts.ba_completed_dataset_handoff import build_batch, EXPECTED

class TestPerSourceItemCap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=json.loads(CONFIG.read_text(encoding="utf8"))

    def test_jobserve_historical_24_rows_from_20_requested_allowed(self):
        self.assertEqual(verified_dataset_count({"itemCount":24},20,"JobServe"),24)
        self.assertEqual(verified_dataset_count({"itemCount":20},20,"JobServe"),20)
        self.assertEqual(verified_dataset_count({"itemCount":1},30,"JobServe"),1)
        self.assertEqual(verified_dataset_count({"itemCount":0},30,"Reed UK"),0)
        for x in (None, True, -1, "24", 30.5):
            with self.assertRaises(ValueError):
                verified_dataset_count({"itemCount":x},30,"Reed UK")

    def test_stop_before_second_paid_actor_after_first_dataset_overrun(self):
        cfg=deepcopy(self.config)
        cfg["rolling_coverage_enabled"]=True
        cfg["rotation_slot"]=1
        family_names=[
            "Business Analysis","Data Analysis","Business Intelligence",
            "Delivery Management","Product Ownership"
        ]
        for source,family in zip(cfg["sources"],family_names):
            source["query_family"]=family
        cfg["sources"][0]["max_items"]=20
        cfg["sources"][0]["input"]["maxResults"]=20
        urls=[]
        def getter(url,token,body=None):
            urls.append(url)
            if url.endswith("/users/me/limits"):
                return {"limits":{"maxMonthlyUsageUsd":25}, "current":{"monthlyUsageUsd":0}}
            if "/runs?" in url:
                return {"id":"SOURCE001"}
            if "/actor-runs/" in url:
                return {"status":"SUCCEEDED","defaultDatasetId":"DATASET001"}
            if "/datasets/" in url:
                return {"itemCount":24}
            raise AssertionError("Unexpected URL: "+url)
        with tempfile.TemporaryDirectory() as t:
            with patch("scripts.ba_controlled_refresh.OUT",Path(t)/"audit.json"), \
                 patch.dict(os.environ,{"BA_PAID_REFRESH_APPROVAL":"EXPLICIT_BA_REFRESH_APPROVED"}):
                with self.assertRaisesRegex(RuntimeError,"dataset count fails closed"):
                    run(cfg,"fake-token",getter=getter,sleep=lambda _:None)
                audit=json.loads((Path(t)/"audit.json").read_text())
                self.assertEqual(audit["receipts"][0]["status"],"OUTPUT_COUNT_REJECTED")
                self.assertEqual(audit["receipts"][0]["dataset_items"] if "dataset_items" in audit["receipts"][0] else None,None)
        self.assertEqual(sum("/runs?" in u for u in urls),1)
        self.assertEqual(sum("/datasets/" in u for u in urls),1)

    def test_completed_handoff_accepts_bounded_jobserve_page_overrun(self):
        receipts=[{"source":name,"run_id":"run_000"+str(i)} for i,name in enumerate(EXPECTED)]
        def get(url,token):
            if "/actor-runs/" in url:
                i=int(url.rsplit("_",1)[-1]);source=list(EXPECTED)[i]
                return {"status":"SUCCEEDED","actId":EXPECTED[source],
                        "defaultDatasetId":"dataset_"+str(i),"finishedAt":"2026-10-15T15:00:00Z"}
            if "/items?" in url:
                count=24 if "dataset_4" in url else 2
                return [{"title":"Example","url":"https://example.com/"+str(j)} for j in range(count)]
            if "/datasets/" in url:
                return {"itemCount":24 if "dataset_4" in url else 2}
            raise AssertionError(url)
        caps={name:30 for name in EXPECTED}
        caps["JobServe"]=20
        batch=build_batch(receipts,"fake",get=get,max_per_source=50,max_items_by_source=caps)
        self.assertEqual(len(next(s for s in batch["sources"] if s["name"]=="JobServe")["records"]),24)

if __name__=="__main__":unittest.main()
