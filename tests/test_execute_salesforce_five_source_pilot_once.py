import unittest
from scripts.execute_salesforce_five_source_pilot_once import (
    APPROVAL, MAX_RESULTS, account_headroom, task_input, actor_input,
    start_url, run,
)


class FiveSourcePilotRunnerTests(unittest.TestCase):
    def test_auth_required_before_api(self):
        with self.assertRaises(RuntimeError):
            run("placeholder", "WRONG")

    def test_caps_and_counts(self):
        self.assertIn("maxTotalChargeUsd=0.15", start_url("apify_task", "owner/task", .15))
        self.assertIn("maxItems=20", start_url("apify_actor", "owner/actor", .2))
        self.assertEqual(actor_input("Indeed UK")["maxResults"], MAX_RESULTS)
        self.assertEqual(actor_input("JobServe")["maxResults"], MAX_RESULTS)

    def test_task_overrides_keep_search_salesforce(self):
        cases = [("CV-Library", {"query":"other","maxResults":100}, "query"),
                 ("Totaljobs", {"keywords":["other"],"maxListings":100}, "keywords"),
                 ("Reed UK", {"keywords":["other"],"maxResults":100}, "keywords")]
        for source, payload, key in cases:
            out = task_input(source, payload)
            self.assertIn("Salesforce", str(out[key]))
            self.assertNotIn("other", str(out[key]))

    def test_account_budget_fails_closed(self):
        def fake(url, token):
            return {"limits": {"maxMonthlyUsageUsd": 19}, "current": {"monthlyUsageUsd": 11.0}}
        self.assertEqual(account_headroom("dummy", fake), 8)
        def bad(url, token):
            return {"limits": {"maxMonthlyUsageUsd": 30}, "current": {"monthlyUsageUsd": 4}}
        with self.assertRaises(RuntimeError):
            account_headroom("dummy", bad)

    def test_no_start_without_sufficient_headroom(self):
        calls=[]
        def get(url, token):
            return {"limits":{"maxMonthlyUsageUsd":19},"current":{"monthlyUsageUsd":10.2}}
        def launch(*args):
            calls.append(args)
            return {"id":"ID1"}
        with self.assertRaisesRegex(RuntimeError, "reserve"):
            run("dummy", APPROVAL, get=get, load=lambda r,t: {}, launch=launch)
        self.assertEqual(calls, [])

    def test_one_per_source_and_stop_on_failed_actor(self):
        calls=[]
        def get(url, token):
            return {"limits":{"maxMonthlyUsageUsd":19},"current":{"monthlyUsageUsd":7.65}}
        def load(ref, token):
            if "cv-library" in ref: return {"query":"old","maxResults":100}
            if "totaljobs" in ref: return {"keywords":"old","maxListings":100}
            return {"keywords":["old"],"maxResults":100}
        def launch(url, token, payload):
            calls.append((url,payload))
            return {"id":"Run"+str(len(calls))}
        def wait(run_id, token):
            return "FAILED" if run_id=="Run2" else "SUCCEEDED"
        with self.assertRaisesRegex(RuntimeError, "remaining sources cancelled"):
            run("dummy", APPROVAL, get=get, load=load, launch=launch, wait=wait)
        self.assertEqual(len(calls),2)
        self.assertTrue(all("maxTotalChargeUsd=" in url for url,_ in calls))

    def test_dry_review_success_never_publishes(self):
        calls=[]
        def get(url,token):
            return {"limits":{"maxMonthlyUsageUsd":19},"current":{"monthlyUsageUsd":7.65}}
        def load(ref,token):
            if "cv-library" in ref: return {"query":"old","maxResults":100}
            if "totaljobs" in ref: return {"keywords":"old","maxListings":100}
            return {"keywords":"old","maxResults":100}
        def launch(url,token,payload):
            calls.append(url)
            return {"id":"Run"+str(len(calls))}
        result=run("dummy",APPROVAL,get=get,load=load,launch=launch,
                   wait=lambda *args:"SUCCEEDED")
        self.assertEqual(len(calls),5)
        self.assertFalse(result["wordpress_published"])
        self.assertEqual(result["automatic_retries"],0)
        self.assertTrue(result["source_data_not_yet_qa_approved"])
