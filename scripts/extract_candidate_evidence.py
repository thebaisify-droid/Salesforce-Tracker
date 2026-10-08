"""Minimal public vacancy evidence extraction; never infer missing attributes."""
import re
from urllib.parse import urlsplit
FIELDS={
"title":("title","jobTitle","job_title"),
"url":("url","jobUrl","job_url","link"),
"employer":("company","companyName","employer","employerName"),
"location":("location","jobLocation","city"),
"posted_date":("postedDate","datePosted","posted_at","publicationDate"),
"description":("description","jobDescription","job_description"),
"source_job_id":("jobId","job_id","id","vacancyId")
}
def first_text(record,names):
 for name in names:
  value=record.get(name)
  if isinstance(value,str) and value.strip():return value.strip()
 return None
def clean_description(value):
 if not value:return None
 value=re.sub(r"<[^>]+>"," ",value)
 value=re.sub(r"\b[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}\b","[redacted-email]",value)
 value=re.sub(r"(?:\+\d{1,3}[ -]?)?(?:\(?0\d{2,4}\)?[ -]?)?\d{3,5}[ -]?\d{3,5}","[redacted-phone]",value)
 return re.sub(r"\s+"," ",value).strip()[:4000] or None
def extract(record,source):
 if not isinstance(record,dict):return None
 values={k:first_text(record,aliases) for k,aliases in FIELDS.items()}
 title,url=values["title"],values["url"]
 try:
  parsed=urlsplit(url or "")
  if parsed.scheme not in ("https","http") or not parsed.hostname or parsed.username or parsed.password:return None
 except ValueError:return None
 if not title:return None
 result={"source":source,"title":title[:200],"url":url[:1000],
    "employer":(values["employer"] or "")[:200] or None,
    "location":(values["location"] or "")[:240] or None,
    "posted_date":values["posted_date"],
    "description":clean_description(values["description"]),
    "source_job_id":(values["source_job_id"] or "")[:120] or None,
    "active_verified":False,"manual_relevance_verified":False,
    "evidence_status":"SOURCE_CLAIM_UNVERIFIED"}
 return result
