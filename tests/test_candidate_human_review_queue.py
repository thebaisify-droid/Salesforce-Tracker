import unittest
from scripts.candidate_human_review_queue import build_queue,summarise_review

class ReviewQueueTests(unittest.TestCase):
 def test_missing_evidence_cannot_pass(self):
  pilot={'results':[{'source':'Totaljobs','vacancies':[{'title':'Business Analyst','url':'https://example.org/job/1'}]},{'source':'Indeed UK','vacancies':[]},{'source':'JobServe','vacancies':[]}]}
  report=build_queue(pilot)
  self.assertEqual(report['pilot_records'],1)
  self.assertEqual(summarise_review(report)['verified_count'],0)
  self.assertFalse(summarise_review(report)['publication_approved'])
 def test_duplicate_ids_rejected(self):
  with self.assertRaises(ValueError):summarise_review({'queue':[{'record_id':'x'},{'record_id':'x'}]})
