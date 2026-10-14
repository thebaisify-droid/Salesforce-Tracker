import unittest
import io
from unittest.mock import patch
from scripts.salesforce_five_source_readonly_preflight import fetch
from scripts.salesforce_five_source_readonly_preflight import inspect, BASE, TASKS, OTHER_ACTORS


class FiveSourceReadOnlyTests(unittest.TestCase):
    def test_requests_get_only_and_redacts_inputs(self):
        calls = []
        names = list(TASKS)
        ids = ["act_cv", "act_total", "act_reed"]
        mapping = {}
        for label, aid in zip(names, ids):
            name = TASKS[label].replace("/", "~")
            mapping[BASE + "actor-tasks/" + name] = {"actId": aid}
            mapping[BASE + "actor-tasks/" + name + "/input"] = {
                "query": "Salesforce", "maxResults": 10, "apiToken": "DO-NOT-LEAK"}
            mapping[BASE + "acts/" + aid] = {"id": aid, "name": aid}
        for _, aid in OTHER_ACTORS.items():
            mapping[BASE + "acts/" + aid] = {"id": aid, "name": aid}
        def get(url, token):
            calls.append(url)
            return mapping[url]
        result = inspect("placeholder-token", get)
        self.assertEqual(len(result["saved_tasks"]), 3)
        self.assertEqual(len(calls), 11)
        self.assertFalse(result["paid_acquisition_approved"])
        self.assertEqual(result["actor_runs_started"], 0)
        self.assertEqual(result["tasks_mutated"], 0)
        self.assertNotIn("DO-NOT-LEAK", str(result))
        self.assertNotIn("apiToken", str(result))
    def test_missing_token_rejected(self):
        with self.assertRaises(ValueError):
            inspect("")

    def test_raw_task_input_json_response(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, *args): return b'{"query":"Salesforce","maxResults":12}'
        with patch("scripts.salesforce_five_source_readonly_preflight.urlopen",return_value=Response()):
            response=fetch(BASE+"actor-tasks/develop_ify~uk-jobs-reed-task/input","dummy")
        self.assertEqual(response,{"query":"Salesforce","maxResults":12})

    def test_metadata_without_data_is_rejected(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, *args): return b'{"error":"unexpected"}'
        with patch("scripts.salesforce_five_source_readonly_preflight.urlopen",return_value=Response()):
            with self.assertRaisesRegex(ValueError,"metadata response missing"):
                fetch(BASE+"actor-tasks/develop_ify~uk-jobs-reed-task","dummy")
