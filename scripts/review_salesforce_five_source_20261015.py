"""Read-only deterministic QA of the immutable 15 October five-source pilot.

No Actor starts, billable acquisition, WordPress calls, production DB writes or
publication. Existing taxonomy v2.2 and master data v1.4 are used unchanged.
"""
from __future__ import annotations
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from tracker.classify import classify, versions

SOURCES = (
    ("CV-Library", "RTMRMZthaZ8BeVbli", 15),
    ("Totaljobs", "mkF6Ck2YNOA6pDK1r", 20),
    ("Reed UK", "eAzDgMOr4l1O16uv4", 20),
    ("Indeed UK", "3TrVqYn3rDsP8eyf6", 20),
    ("JobServe", "1VUnFLW3aSR5YefTY", 22),
)
OUT = Path("review/salesforce-pilot-20261015")
API = "https://api.apify.com/v2/datasets/"
CORE_TITLE = re.compile(r"\b(salesforce|sfdc|agentforce|mulesoft)\b", re.I)
PLATFORM_TEXT = re.compile(r"\b(salesforce|sfdc|agentforce|mulesoft)\b", re.I)
KNOWN_DOMAINS = ("cv-library.co.uk", "totaljobs.com", "reed.co.uk", "indeed.com", "jobserve.com")


def get_dataset(dataset_id, token):
    url = API + dataset_id + "/items?clean=false&limit=100"
    request = Request(url, method="GET", headers={"Authorization":"Bearer " + token,
                                                   "Accept":"application/json"})
    with urlopen(request, timeout=45) as response:
        rows = json.load(response)
    if not isinstance(rows, list): raise ValueError("Malformed dataset")
    return rows


def name(value):
    if isinstance(value, dict):
        return str(value.get("name") or value.get("companyName") or "").strip()
    return str(value or "").strip()


def first(row, *keys):
    for key in keys:
        obj = row.get(key)
        if obj is not None and obj != "" and obj != []:
            return obj
    return None


def parse_date(value):
    if not isinstance(value, str): return None
    try:
        d = datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError:
        try: d = datetime.strptime(value, "%A, %d %B %Y").replace(tzinfo=timezone.utc)
        except ValueError: return None
    if d.tzinfo is None: d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc).isoformat()


def valid_url(value):
    if not isinstance(value, str): return None
    value = value.strip()
    if value.startswith("https://www.totaljobs.com/https://"):
        value = value[len("https://www.totaljobs.com/"):]
    p=urlsplit(value)
    if p.scheme != "https" or not p.hostname or p.username or p.password or "://" in p.path:
        return None
    host=p.hostname.lower()
    return value if any(host==d or host.endswith("."+d) for d in KNOWN_DOMAINS) else None


def normal(value):
    return re.sub(r"[^a-z0-9]+"," ",re.sub(r"\b(ltd|limited|plc)\b","",str(value or "").lower())).strip()


def map_row(row, source):
    title = str(first(row,"title","jobTitle") or "").strip()
    advertiser = name(first(row,"company","employer","recruiter","employer.name"))
    if not advertiser and isinstance(row.get("employer"),dict):
        advertiser = name(row["employer"])
    description = str(first(row,"descriptionText","descriptionSnippet","textSnippet","snippet","description") or "")[:12000]
    posted = parse_date(first(row,"postedAt","datePosted","postedDateTime","postedDate"))
    url=valid_url(first(row,"canonicalUrl","jobUrl","externalUrl","url","applyUrl"))
    classified=classify(title,advertiser,description)
    title_signal=bool(CORE_TITLE.search(title))
    description_signal=bool(PLATFORM_TEXT.search(description))
    # Employer named Salesforce does not itself establish a platform role.
    if title_signal:
        relevance="CORE_CANDIDATE"
    elif description_signal and normal(advertiser)!="salesforce":
        relevance="ADJACENT_REVIEW"
    else:
        relevance="NOT_CORE_SIGNAL"
    return {
        "source":source,"source_record_id":str(first(row,"jobId","externalId","reference","jobKey") or ""),
        "title":title,"advertiser":advertiser,"posted_at":posted,"source_url":url,
        "relevance":relevance,"role_family":classified["role_family"],
        "role_confidence":classified["role_confidence"],
        "role_review_required":bool(classified["role_review_required"]),
        "sector":classified.get("end_client_sector") or "Unresolved",
        "sector_review_required":bool(classified.get("sector_review_required")),
        "skills":classified["role_specialism"],
        "employment":str(first(row,"employmentType","contractType","jobType") or ""),
        "location":str(first(row,"location","location.text") or "")[:180],
        "availability":"SOURCE_OBSERVED_NOT_VERIFIED_OPEN",
        "publication_allowed":False,
    }


def analyse(payloads, *, observed_at=None):
    source_stats=[]
    ads=[]
    lifecycle=[]
    for source,dataset,expected in SOURCES:
        rows=payloads.get(dataset)
        if not isinstance(rows,list) or len(rows)!=expected:
            raise ValueError("Source missing or count mismatch: "+source)
        counts=Counter()
        for item in rows:
            if not isinstance(item,dict): raise ValueError("Non-object row in "+source)
            if item.get("changeType") == "EXPIRED":
                lifecycle.append({"source":source,"job_id":item.get("jobId"),
                                  "state_key":item.get("stateKey"),
                                  "event":"SOURCE_EXPIRED_NOT_INDEPENDENTLY_VERIFIED"})
                counts["expiry_events"]+=1
                continue
            out=map_row(item,source)
            ads.append(out)
            counts["adverts"]+=1
            counts[out["relevance"]]+=1
            if not out["source_url"]: counts["invalid_urls"]+=1
            if not out["title"] or not out["advertiser"]: counts["missing_required"]+=1
            if not out["posted_at"]: counts["unparseable_dates"]+=1
        source_stats.append({"source":source,"dataset_id":dataset,"raw":len(rows),**dict(counts)})
    groups={}
    for row in ads:
        key=(normal(row["title"]),normal(row["advertiser"]))
        groups.setdefault(key,[]).append(row)
    unique=[]
    duplicate_groups=[]
    for key,records in groups.items():
        records.sort(key=lambda x:(not bool(x["source_url"]),x["source"]))
        main=dict(records[0])
        main["source_evidence"]=sorted(set(x["source"] for x in records))
        main["supporting_urls"]=sorted(set(x["source_url"] for x in records if x["source_url"]))
        main["possible_duplicate"]=len(records)>1
        unique.append(main)
        if len(records)>1:
            duplicate_groups.append({"title":main["title"],"advertiser":main["advertiser"],
                                     "sources":main["source_evidence"],"count":len(records)})
    counters=Counter(row["relevance"] for row in unique)
    quality={
        "schema":"sf-five-source-quality-review/v1","observed_at":observed_at,
        "master_data_version":versions()[0],"taxonomy_version":versions()[1],
        "raw_rows":sum(x["raw"] for x in source_stats),
        "advert_rows":len(ads),"expiry_events":len(lifecycle),
        "provisional_unique_records":len(unique),
        "duplicate_excess":len(ads)-len(unique),
        "duplicate_groups":duplicate_groups,
        "classifications":dict(counters),
        "source_stats":source_stats,
        "publication_allowed":False,
        "wordPress_changed":False,"actors_started":0,
        "reason":"REVIEW_ONLY: source-observed signals and provisional cross-board deduplication are not a publication-ready quality-approved snapshot",
    }
    return quality, unique, lifecycle


def main():
    token=os.getenv("APIFY_TOKEN","")
    if not token: raise SystemExit("APIFY_TOKEN required for GET-only existing dataset reading")
    payloads={id:get_dataset(id,token) for _,id,_ in SOURCES}
    report, candidates, lifecycle=analyse(payloads,observed_at=datetime.now(timezone.utc).isoformat())
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"quality-report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    (OUT/"candidate-register.json").write_text(json.dumps(candidates,indent=2,ensure_ascii=False)+"\n")
    (OUT/"lifecycle-events.json").write_text(json.dumps(lifecycle,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k not in ("duplicate_groups","source_stats")},sort_keys=True))

if __name__ == "__main__":
    main()
