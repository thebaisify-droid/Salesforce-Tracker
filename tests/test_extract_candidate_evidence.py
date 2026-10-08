import unittest
from scripts.extract_candidate_evidence import extract,clean_description
class EvidenceExtractionTests(unittest.TestCase):
 def test_preserves_supported_fields_without_assuming_verification(self):
  x=extract({"jobTitle":"BA","jobUrl":"https://example.com/job/1","companyName":"A Ltd","jobLocation":"Bristol","datePosted":"2026-10-08","jobDescription":"Analyze requirements","jobId":"123"},"Totaljobs")
  self.assertEqual(x["employer"],"A Ltd")
  self.assertEqual(x["source_job_id"],"123")
  self.assertFalse(x["active_verified"])
  self.assertEqual(x["evidence_status"],"SOURCE_CLAIM_UNVERIFIED")
 def test_no_invented_metadata(self):
  x=extract({"title":"BA","url":"https://example.com/1"},"JobServe")
  self.assertIsNone(x["employer"])
  self.assertIsNone(x["description"])
 def test_reject_bad_url(self):
  self.assertIsNone(extract({"title":"BA","url":"https://u:p@example.com/job"},"Indeed UK"))
  self.assertIsNone(extract({"title":"BA","url":"javascript:alert(1)"},"Indeed UK"))
 def test_contact_redaction(self):
  self.assertNotIn("a@example.com",clean_description("write a@example.com"))
