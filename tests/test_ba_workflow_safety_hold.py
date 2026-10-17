"""Offline regression checks for the temporary BA cost safety hold."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/ba-controlled-refresh.yml"


class TestBaWorkflowSafetyHold(unittest.TestCase):
    def test_paid_acquisition_stays_disabled_while_oversize_unresolved(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("if: ${{ false }}", workflow)
        self.assertIn("BLOCKED_COST_SAFETY_HOLD", workflow)
        self.assertIn("exit 1", workflow)
        self.assertIn("No paid Actors were launched", workflow)
        self.assertIn("if: always()", workflow)

    def test_two_dst_crons_still_defined(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('35 6 * * 2,5', workflow)
        self.assertIn('35 7 * * 2,5', workflow)
        self.assertIn('BA_SCHEDULE_CRON: ${{ github.event.schedule }}', workflow)


if __name__ == "__main__":
    unittest.main()
