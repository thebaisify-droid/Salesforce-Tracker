import copy
import json
import unittest
from datetime import date
from pathlib import Path

from scripts.reconcile_candidate_employer_evidence import reconcile, evidence_index
from scripts.screen_indeed_cyber_pilot import screen

EVIDENCE = json.loads(Path("docs/evidence/candidate_cyber_gov_apprenticeships_2026-10-09.json").read_text())

def source(job_id, title, company="QA Ltd", location="Oswestry SY10 8NR"):
    return {
        "jobId": job_id, "title": title, "company": company,
        "location": location, "postedAt": "2026-08-21T05:00:00Z",
        "postedRelative": "23 days ago",
        "url": "https://uk.indeed.com/viewjob?jk=" + job_id,
    }

class EmployerEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.source_records = [
            source("efbcdd8118a397fa","Cyber Threat Detection & Response Apprentice"),
            source("20fdf094041231b1","Cyber Security Engineer Apprentice"),
            source("x3","Security Specialist","AWE","Aldermaston"),
        ]
        self.screened = screen(self.source_records, as_of=date(2026,10,9))

    def test_two_government_records_correct_employer_not_advertiser(self):
        result = reconcile(self.screened,EVIDENCE)
        a,b,c = result["records"]
        self.assertEqual(result["official_registry_matches"],2)
        self.assertEqual(result["distinct_official_vacancy_references"],2)
        self.assertEqual(result["advertisers_correlated_to_training_providers"],2)
        self.assertEqual(a["source_advertiser"],"QA Ltd")
        self.assertEqual(a["source_advertiser_role"],"TRAINING_PROVIDER_IN_OFFICIAL_LISTING")
        self.assertEqual(a["official_registry_hiring_employer"],"Specialist Network Operations")
        self.assertEqual(b["official_registry_hiring_employer"],"Specialist Network Operations")
        self.assertNotEqual(a["official_government_reference"],b["official_government_reference"])
        self.assertEqual(a["same_official_employer_site_review_ids"],[b["job_id"]])
        self.assertTrue(a["government_posting_conflicts_with_board"])
        self.assertIsNone(c["official_registry_hiring_employer"])
        self.assertEqual(c["source_advertiser_role"],"UNCONFIRMED")
        self.assertIsNone(c["human_confirmed_role_family"])
        self.assertFalse(result["publication_approved"])
        self.assertEqual(result["auto_merged_count"],0)
        self.assertEqual(result["independently_verified_count"],0)
        self.assertFalse(any(x["publication_ready"] for x in result["records"]))

    def test_reference_same_title_location_still_distinct(self):
        records = copy.deepcopy(self.source_records)
        records[1]["title"] = records[0]["title"]
        s = screen(records, as_of=date(2026,10,9))
        ev = copy.deepcopy(EVIDENCE)
        ev["records"][1]["official_title"] = records[0]["title"]
        r = reconcile(s,ev)["records"]
        self.assertEqual(r[0]["same_title_employer_location_ids"],[r[1]["job_id"]])
        self.assertEqual(r[0]["separate_official_requisition_from"],[r[1]["job_id"]])
        self.assertEqual(r[0]["same_official_reference_review_ids"],[])
        self.assertFalse(r[0]["automatic_dedupe_performed"])

    def test_wrong_source_or_gov_reference_rejected(self):
        for change in ("wrong_source","wrong_url","wrong_title","wrong_gov_ref","fake_employer_review"):
            with self.subTest(change=change):
                ev = copy.deepcopy(EVIDENCE)
                item = ev["records"][0]
                if change=="wrong_source":
                    item["source_job_id"]="unknown"
                elif change=="wrong_url":
                    item["source_job_url"]="https://uk.indeed.com/viewjob?jk=wrong"
                elif change=="wrong_title":
                    item["official_title"]="Unrelated position"
                elif change=="wrong_gov_ref":
                    item["official_evidence_url"]="https://malicious.example/apprenticeship/VAC2000049619"
                else:
                    item["human_approved"]=True
                with self.assertRaises(ValueError):
                    reconcile(self.screened,ev)

    def test_evidence_does_not_mutate_original_screening(self):
        snapshot=copy.deepcopy(self.screened)
        reconcile(self.screened,EVIDENCE)
        self.assertEqual(self.screened,snapshot)
        self.assertNotIn("source_advertiser",self.screened["records"][0])

if __name__=="__main__": unittest.main()
