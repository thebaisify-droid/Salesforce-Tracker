"""Offline second-stage candidate evidence gate. Does not scrape or publish."""
import argparse,json,re
from collections import Counter,defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit,parse_qs,unquote

def norm(s):
 return re.sub(r"[^a-z0-9]+"," ",str(s or "").lower()).strip()
def identity_url(url):
 try:
  p=urlsplit(url)
  if p.scheme not in ("http","https") or not p.netloc:return None
  host=p.netloc.lower().removeprefix("www.")
  q=parse_qs(p.query)
  job_id=next((q[k][0] for k in ("jk","jobId","job_id","vacancyId") if q.get(k)),None)
  return (host+"/id/"+norm(job_id)) if job_id else host+unquote(p.path).rstrip("/").lower()
 except (TypeError,ValueError):return None
def assess(rows,required_families=22):
 if not isinstance(rows,list):raise ValueError("Rows must be a list")
 seen_urls=set();keys=defaultdict(list);out=[];covered=set();source_counts=Counter()
 for i,r in enumerate(rows):
  if not isinstance(r,dict):raise ValueError("Invalid record")
  title=r.get("title");url=r.get("url");source=r.get("source")
  u=identity_url(url)
  flags=[]
  if not title or not str(title).strip():flags.append("MISSING_TITLE")
  if not u:flags.append("INVALID_JOB_URL")
  elif u in seen_urls:flags.append("DUPLICATE_URL")
  if u:seen_urls.add(u)
  company=r.get("employer") or r.get("company")
  location=r.get("location")
  if not company:flags.append("EMPLOYER_UNVERIFIED")
  if not location or not ("uk" in norm(location).split() or re.search(r"\b(united kingdom|england|scotland|wales|northern ireland)\b",str(location),re.I)):flags.append("UK_LOCATION_UNVERIFIED")
  if not r.get("description"):flags.append("DESCRIPTION_UNAVAILABLE")
  if not r.get("posted_date"):flags.append("POSTING_DATE_UNVERIFIED")
  if r.get("active_verified") is not True:flags.append("VACANCY_STATUS_UNVERIFIED")
  if r.get("manual_relevance_verified") is not True:flags.append("RELEVANCE_UNVERIFIED")
  family=r.get("verified_role_family")
  if family and r.get("manual_relevance_verified") is True:covered.add(family)
  if source:source_counts[source]+=1
  key=(norm(title),norm(company),norm(location))
  if all(key):keys[key].append(i)
  out.append({"index":i,"title":title,"source":source,"flags":flags,"publication_ready":not flags})
 for group in keys.values():
  if len(group)>1:
   for i in group:
    if "POTENTIAL_CROSS_SOURCE_DUPLICATE" not in out[i]["flags"]:
     out[i]["flags"].append("POTENTIAL_CROSS_SOURCE_DUPLICATE")
     out[i]["publication_ready"]=False
 return {"schema":"candidate-evidence-gate/v1","record_count":len(rows),"source_counts":dict(source_counts),
 "publication_ready_count":sum(r["publication_ready"] for r in out),
 "verified_families":sorted(covered),"verified_family_count":len(covered),
 "family_coverage_required":required_families,"security_coverage_verified":any("security" in f.lower() or "soc" in f.lower() for f in covered),
 "flag_counts":dict(Counter(f for r in out for f in r["flags"])),"records":out,
 "external_vacancy_checks_performed":False,"publication_approved":False,"passed":False,
 "notes":"Requires human-labelled real vacancy evidence; title/URL checks alone cannot establish validity."}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--input",required=True);p.add_argument("--output",required=True)
 a=p.parse_args()
 rows=json.loads(Path(a.input).read_text())
 result=assess(rows.get("records",rows.get("vacancies",rows)) if isinstance(rows,dict) else rows)
 target=Path(a.output)
 if target.resolve() in {Path("dashboard/data.json").resolve(),Path("dashboard/live-data.json").resolve()}:raise ValueError("Production output forbidden")
 target.parent.mkdir(parents=True,exist_ok=True)
 target.write_text(json.dumps(result,indent=2)+"\n")
 print(json.dumps({"record_count":result["record_count"],"publication_approved":False,"passed":False}))
if __name__=="__main__":main()
