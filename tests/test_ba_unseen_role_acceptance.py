"""Independent synthetic unseen role samples: no live sources, no spend."""
import unittest
from scripts.ba_scope_classifier_offline_audit import assess
CASES=[
 ("Senior Business Analyst – Payments Modernisation","", "AUTO_INCLUDE"),
 ("Lead Data Analyst, Retail Pricing","", "AUTO_INCLUDE"),
 ("Cyber Security Analyst, Threat Detection","", "AUTO_INCLUDE"),
 ("Trainee Cyber Security Analyst – No Experience Needed","", "REVIEW"),
 ("Trainee Cyber Security Analyst – No Experience Needed – Online Course","", "REVIEW"),
 ("Head of Technology, Enterprise Platforms","", "REVIEW"),
 ("Enterprise Architect, Cloud Transformation","", "REVIEW"),
 ("Digital Analyst - Tech, Risk & Governance","", "REVIEW"),
 ("Implementation Manager","", "REVIEW"),
 ("Security Consultant","", "REVIEW"),
 ("Lead Engineer","", "REVIEW"),
 ("Pensions Technical Manager","", "REVIEW"),
 ("Retail Security Guard","", "REVIEW"),
 ("Security Consultant – physical building access","", "REVIEW"),
 ("Salesforce Business Analyst – Service Cloud","", "AUTO_INCLUDE"),
 ("Salesforce Developer – Apex and LWC","", "REVIEW"),
 ("Data Analyst – Reporting","", "AUTO_INCLUDE"),
 ("Project Manager – Digital Transformation","", "AUTO_INCLUDE"),
]
class UnseenAcceptance(unittest.TestCase):
 def test_all_sample_expectations(self):
  outcomes=[]
  for title,desc,expected in CASES:
   observed=assess(title,desc)
   outcomes.append((title,observed["status"],expected))
   self.assertEqual(observed["status"],expected,title)
  print("BA_UNSEEN_ACCEPTANCE",{"samples":len(outcomes),"passed":len(outcomes)})
 def test_no_automatic_acceptance_for_adversarial_cases(self):
  for title in ("Trainee Cyber Security Analyst – No Experience Needed",
                "Retail Security Guard","Implementation Manager","Pensions Technical Manager"):
   self.assertNotEqual(assess(title)["status"],"AUTO_INCLUDE",title)
if __name__=="__main__":unittest.main()
