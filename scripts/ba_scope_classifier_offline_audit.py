"""Conservative candidate role taxonomy validation; never publish or acquire."""
import json
from pathlib import Path
from collections import Counter
from tracker.business_product_delivery_security import classify_market_role
ROOT=Path(__file__).resolve().parents[1]
LEDGER=ROOT/"business-analysis-tracker/evidence/ba-20261016-final-161-scope-decisions.json"
PATTERNS=[
 ("Technology Leadership & Management",("head of technology","it manager")),
 ("Enterprise & Solution Architecture",("enterprise architect","solutions architect","solution architect")),
 ("Security Management",("cyber security manager","information security manager")),
 ("Information Security Analysis",("cyber security analyst","cybersecurity specialist")),
 ("Technology Governance, Risk & Compliance",("technology grc analyst","digital analyst - tech")),
]
def assess(title,description=""):
    lower=(title or "").casefold()
    if "apprentice" in lower or "apprenticeship" in lower:
        return {"status":"REVIEW","family":None,"basis":"APPRENTICESHIP_REQUIRES_REVIEW"}
    if "no experience needed" in lower and "trainee" in lower:
        return {"status":"REVIEW","family":None,"basis":"PROMOTIONAL_TRAINEE_REVIEW"}
    result=classify_market_role(title,description)
    if result["included"]:
        return {"status":"AUTO_INCLUDE","family":result["role_family"],"basis":"EXISTING"}
    lower=(title or "").casefold()
    for family,terms in PATTERNS:
        if any(term in lower for term in terms):
            return {"status":"REVIEW","family":family,"basis":"PROPOSED_REVIEW_ONLY"}
    return {"status":"REVIEW","family":None,"basis":"NO_CONFIDENT_TITLE_RULE"}
def audit():
    data=json.loads(LEDGER.read_text(encoding="utf8"))
    counts=Counter()
    samples=[]
    for row in data["decisions"]:
        res=assess(row["title"])
        counts[(row["decision"],res["status"])]+=1
        if row["decision"]=="EXCLUDE" and res["status"]=="AUTO_INCLUDE":
            samples.append({"title":row["title"],"source":row["source"]})
    return {"total":len(data["decisions"]),"metrics":{a+"__"+b:v for (a,b),v in sorted(counts.items())},
            "false_auto_inclusions":len(samples),"false_auto_inclusion_examples":samples[:12],
            "paid_actors":0,"wordpress_requests":0}
if __name__=="__main__":
    print(json.dumps(audit(),sort_keys=True))
