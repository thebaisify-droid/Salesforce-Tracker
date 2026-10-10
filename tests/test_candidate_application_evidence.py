import copy
import json
import unittest
from pathlib import Path

from scripts.assess_candidate_application_evidence import assess

SOURCE = json.loads(Path("docs/evidence/candidate_employer_backed_security_gaps_2026-10-09.json").read_text())
CHECKS = json.loads(Path("docs/evidence/candidate_cyber_application_checks_2026-10-10.json").read_text())


class CandidateApplicationEvidenceTests(unittest.TestCase):
    def test_valid_review_does_not_elevate_unconfirmed_leads(self):
        result = assess(SOURCE,CHECKS)
        self.assertEqual(result["leads_checked"],2)
        self.assertEqual(result["readable_source_pages"],2)
        self.assertEqual(result["application_flows_independently_verified"],0)
        self.assertEqual(result["human_role_reviews_completed"],0)
        self.assertEqual(result["live_vacancies_confirmed"],0)
        self.assertFalse(result["publication_approved"])
        self.assertEqual(result["paid_apify_runs_started"],0)
        self.assertEqual(len(result["review_queue"]),2)
        self.assertTrue(all(row["publication_ready"] is False for row in result["review_queue"]))

    def test_mismatched_or_overstated_check_fails_closed(self):
        for key,value in [
            ("application_status","VERIFIED"),
            ("vacancy_live_independently_verified",True),
            ("role_family_human_approved",True),
            ("human_publication_signoff",True),
            ("publication_ready",True),
            ("employer_reference","MADEUP"),
            ("source_page_url","https://not-example.invalid"),
            ("proposed_primary_family","Information Security Analysis"),
            ("observed_apply_destination","https://fake.example.org/apply"),
            ("official_portal_job_code","555"),
        ]:
            with self.subTest(field=key):
                mutated = copy.deepcopy(CHECKS)
                mutated["records"][1][key]=value
                with self.assertRaises(ValueError):
                    assess(SOURCE,mutated)

    def test_sony_apply_link_and_family_must_match_employer_source(self):
        for key,value in [
            ("application_destination_outcome","FLOW_VERIFIED"),
            ("observed_apply_destination","https://sony-fake.example/submit"),
            ("proposed_primary_family","Security Operations / SOC"),
        ]:
            with self.subTest(field=key):
                modified = copy.deepcopy(CHECKS)
                modified["records"][0][key]=value
                with self.assertRaises(ValueError):
                    assess(SOURCE,modified)

    def test_duplicate_or_missing_leads_rejected(self):
        for mutator in [
            lambda obj: obj["records"].append(copy.deepcopy(obj["records"][0])),
            lambda obj: obj["records"].pop(),
            lambda obj: obj.__setitem__("new_apify_paid_runs",1),
            lambda obj: obj.__setitem__("publication_approved",True),
        ]:
            modified=copy.deepcopy(CHECKS)
            mutator(modified)
            with self.assertRaises(ValueError):
                assess(SOURCE,modified)

    def test_read_only_original_data_unchanged(self):
        original_source=copy.deepcopy(SOURCE)
        original_checks=copy.deepcopy(CHECKS)
        assess(SOURCE,CHECKS)
        self.assertEqual(SOURCE,original_source)
        self.assertEqual(CHECKS,original_checks)


if __name__=="__main__":
    unittest.main()
