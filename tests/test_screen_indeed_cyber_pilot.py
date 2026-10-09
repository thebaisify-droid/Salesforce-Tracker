import unittest
from datetime import date
from tracker.business_product_delivery_security import classify_market_role
from scripts.screen_indeed_cyber_pilot import screen

class CyberPilotScreeningTests(unittest.TestCase):
    def row(self,jobid,title,company="Employer",location="London",posted="2026-10-09T05:00:00Z",relative="Just posted"):
        return {"jobId":jobid,"title":title,"company":company,"location":location,
                "postedAt":posted,"postedRelative":relative,
                "url":"https://uk.indeed.com/viewjob?jk="+jobid}
    def test_strict_positive_security_titles(self):
        samples=[
            ("Cyber Threat Detection & Response Apprentice","Security Operations / SOC"),
            ("Senior Manager, Cyber Architect, Cyber Security, Financial Services","Security Architecture"),
            ("Cyber Security Engineer Apprentice","IT Security"),
            ("Cyber Security Engineer","IT Security"),
            ("IT Security & Compliance Manager","IT Security"),
            ("Technical Cyber Security Manager","Security Management"),
        ]
        for title,family in samples:
            with self.subTest(title=title):
                r=classify_market_role(title)
                self.assertTrue(r["included"])
                self.assertEqual(r["role_family"],family)
    def test_negative_and_ambiguous_remain_excluded(self):
        for title in ("Police Officer","Security Specialist","Security Guard",
                      "Network and Security Enterprise Architect","Cloud Finance Analyst"):
            with self.subTest(title=title):
                self.assertFalse(classify_market_role(title)["included"])
    def test_no_publication_and_duplicate_flags(self):
        data=[
          self.row("A","Security Specialist","AWE","Aldermaston","2026-09-17T05:00:00Z","22 days ago"),
          self.row("B","Security Specialist","AWE","Aldermaston","2026-10-06T05:00:00Z","3 days ago"),
          self.row("C","Police Officer"),
          self.row("D","Cyber Threat Detection & Response Apprentice","QA","Oswestry","2026-08-21T05:00:00Z","23 days ago"),
          self.row("E","Cyber Security Engineer")]
        output=screen(data,as_of=date(2026,10,9))
        self.assertEqual(output["record_count"],5)
        self.assertEqual(output["triage_counts"]["EXCLUDE_OFF_SCOPE"],1)
        self.assertEqual(output["triage_counts"]["PROVISIONAL_REVIEW_REQUIRED"],2)
        self.assertEqual(output["date_conflicts"],1)
        self.assertEqual(output["potential_exact_duplicate_record_count"],2)
        self.assertEqual(output["older_than_30_days"],1)
        self.assertFalse(output["publication_approved"])
        self.assertTrue(all(x["publication_ready"] is False for x in output["records"]))
    def test_duplicate_ids_fail(self):
        data=[self.row("X","Cyber Security Engineer"),self.row("X","Cyber Security Engineer")]
        with self.assertRaises(ValueError):
            screen(data,as_of=date(2026,10,9))

if __name__=="__main__":unittest.main()
