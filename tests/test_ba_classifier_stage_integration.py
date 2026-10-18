"""Fail-closed QA: proposal gate is used by real five-source staging."""
import json
import unittest
from scripts.ba_scope_classifier_offline_audit import audit
from scripts.ba_stage_five_source_data import stage, MAPPING
class BAIntegration(unittest.TestCase):
 def test_source_stage_routes_ambiguous_adverts_to_review(self):
  receipts=[]
  for name in ("CV-Library","Totaljobs","Reed UK","Indeed UK","JobServe"):
   receipts.append({"name":name,"status":"SUCCEEDED","attempted":True,
                    "run_id":"dummy_"+name,"dataset_id":"dataset_"+name,
                    "observed_at":"2026-10-18T07:00:00Z","records":[]})
  receipts[0]["records"]=[
   {"title":"Business Analyst Apprentice","url":"https://example.org/vacancy/new-apprentice"},
   {"title":"Trainee Cyber Security Analyst - No Experience Needed","url":"https://example.org/vacancy/new-course"},
   {"title":"Senior Business Analyst","url":"https://example.org/vacancy/real-ba"}]
  batch={"schema":"ba-five-source-completed-batch/v1","sources":receipts}
  result=stage(batch,json.loads(MAPPING.read_text()))
  self.assertEqual(len(result["records"]),1,result)
  self.assertEqual(result["records"][0]["title"],"Senior Business Analyst")
  self.assertEqual(result["rejected"]["scope_review_required_not_auto_published"],2)
 def test_historical_audit_still_has_zero_known_false_auto_inclusions(self):
  self.assertEqual(audit()["false_auto_inclusions"],0)
if __name__=="__main__":unittest.main()
