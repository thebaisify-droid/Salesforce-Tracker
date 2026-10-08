import unittest
from unittest.mock import patch
from scripts.inspect_candidate_apify_tasks import _task_url, inspect, summarise

class SavedTaskInspectionTests(unittest.TestCase):
    def test_url_points_only_to_task_metadata(self):
        url = _task_url("develop_ify/cv-library-scraper-task")
        self.assertIn("/actor-tasks/develop_ify~cv-library-scraper-task", url)
        self.assertNotIn("/run", url)
    def test_redacts_sensitive_field_names_and_values(self):
        result = summarise("owner/task", {"data":{"actId":"actor123"}},
                           {"data":{"query":"Salesforce","password":"secret",
                                    "apiToken":"secret","maxResults":15}})
        self.assertEqual(result["candidate_search_fields"], ["maxResults","query"])
        self.assertFalse(result["raw_input_included"])
        self.assertNotIn("secret",str(result))
        self.assertFalse(result["input_schema_verified"])
    def test_get_only_and_zero_actor_runs(self):
        with patch("scripts.inspect_candidate_apify_tasks._get") as get:
            get.side_effect = lambda url, token: (
                {"data":{"query":"Salesforce"}} if url.endswith("/input")
                else {"data":{"actId":"example"}})
            out = inspect("dummy-token")
        self.assertEqual(get.call_count,4)
        self.assertTrue(all("/run" not in c.args[0] for c in get.call_args_list))
        self.assertEqual(out["actor_runs_started"],0)
        self.assertFalse(out["paid_acquisition_approved"])
    def test_token_required(self):
        with self.assertRaises(ValueError):
            inspect("")

if __name__=="__main__":
    unittest.main()
