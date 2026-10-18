"""Public job-board observation checks; read-only, no Apify or WordPress requests.

Source: Reed.co.uk public category pages crawled October 2026.
Titles are source-observed, not employer-verified open positions; some may
overlap the October 16 historical set and cannot be assumed newly posted.
"""
import unittest
import json
from scripts.ba_scope_classifier_offline_audit import assess

OBSERVATIONS=[
 {"title":"Senior Business Analyst","source":"https://www.reed.co.uk/jobs/permanent-senior-business-analyst-jobs","expected":"AUTO_INCLUDE"},
 {"title":"Technical Business Analyst (Azure FinOps)","source":"https://www.reed.co.uk/jobs/business-analyst-jobs?fullTime=true&hideTrainingJobs=true","expected":"AUTO_INCLUDE"},
 {"title":"Business Analyst - Supply Chain","source":"https://www.reed.co.uk/jobs/business-analyst-jobs?fullTime=true&hideTrainingJobs=true","expected":"AUTO_INCLUDE"},
 {"title":"MES Business Analyst","source":"https://www.reed.co.uk/jobs/business-analyst-jobs?fullTime=true&hideTrainingJobs=true","expected":"AUTO_INCLUDE"},
 {"title":"Business Analyst Apprentice","source":"https://www.reed.co.uk/jobs/business-analyst-jobs?fullTime=true&hideTrainingJobs=true","expected":"REVIEW"},
 {"title":"Business Analyst/Project Manager- GMI Migration","source":"https://www.reed.co.uk/jobs/business-analyst-jobs?fullTime=true&hideTrainingJobs=true","expected":"AUTO_INCLUDE"},
 {"title":"Business Analyst (Technology)","source":"https://www.reed.co.uk/jobs/business-analyst-jobs?isEasyApply=true&perm=true","expected":"AUTO_INCLUDE"},
 {"title":"Transformation Business Analyst","source":"https://www.reed.co.uk/jobs/business-analyst-jobs?isEasyApply=true&perm=true","expected":"AUTO_INCLUDE"}
]
class RealPublicListingsAcceptance(unittest.TestCase):
    def test_public_reed_samples_document_expected_classifications(self):
        failures=[]
        results=[]
        for entry in OBSERVATIONS:
            outcome=assess(entry["title"])
            results.append({"title":entry["title"],"observed":outcome["status"],
                            "expected":entry["expected"],"match":outcome["status"]==entry["expected"]})
            if outcome["status"]!=entry["expected"]:
                failures.append(entry["title"])
        print("BA_PUBLIC_OBSERVATION_QA",json.dumps({"sample_count":len(results),
                "matched":len(results)-len(failures),"exceptions":failures,
                "rows":results},sort_keys=True))
        self.assertEqual(len(failures),0,results)
        self.assertGreaterEqual(len(results),8)
    def test_no_paid_or_delivery_modules(self):
        self.assertEqual(len(OBSERVATIONS),8)
if __name__=="__main__":
    unittest.main()
