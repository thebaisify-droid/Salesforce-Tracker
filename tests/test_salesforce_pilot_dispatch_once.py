import os
import pathlib
import unittest
from unittest.mock import patch
from scripts.verify_salesforce_pilot_dispatch_once import verify_once

class PilotOnceTests(unittest.TestCase):
    def test_only_this_one_dispatch_can_run(self):
        env={"GITHUB_RUN_ATTEMPT":"1","GITHUB_REPOSITORY":"thebaisify-droid/Salesforce-Tracker","GITHUB_RUN_ID":"123","GITHUB_TOKEN":"test"}
        with patch.dict(os.environ,env,clear=True):
            verify_once(get=lambda path: {"workflow_runs":[{"id":123}]})
            with self.assertRaises(RuntimeError):
                verify_once(get=lambda path: {"workflow_runs":[{"id":122},{"id":123}]})
            with self.assertRaises(RuntimeError):
                verify_once(get=lambda path: {"workflow_runs":[]})

    def test_rerun_blocked(self):
        env={"GITHUB_RUN_ATTEMPT":"2","GITHUB_REPOSITORY":"thebaisify-droid/Salesforce-Tracker","GITHUB_RUN_ID":"123","GITHUB_TOKEN":"test"}
        with patch.dict(os.environ,env,clear=True):
            with self.assertRaises(RuntimeError):
                verify_once(get=lambda path: {"workflow_runs":[{"id":123}]})

    def test_workflow_manual_no_publication(self):
        w=pathlib.Path(".github/workflows/salesforce-five-source-once.yml").read_text()
        self.assertIn("workflow_dispatch:",w)
        self.assertNotIn("schedule:",w)
        self.assertIn("verify_salesforce_pilot_dispatch_once",w)
        self.assertIn("salesforce_controlled_refresh_budget",w)
        self.assertIn("execute_salesforce_five_source_pilot_once",w)
        self.assertNotIn("send_salesforce_wordpress_snapshot_once",w)
        self.assertNotIn("git push",w)
