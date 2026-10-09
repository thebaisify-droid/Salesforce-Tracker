"""Screen existing Apify cybersecurity job exports OFFLINE, with conservative scope and evidence flags.

No paid calls, network access, production database updates or publication.
"""
import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from tracker.business_product_delivery_security import classify_raw

EXCLUDE_EXPLICIT = ("police officer", "security guard", "security officer",
                    "door supervisor", "loss prevention")
PROTECTED = {Path("dashboard/live-data.json").resolve(),
             Path("dashboard/data.json").resolve(),
             Path("candidate-beta/data/pilot-snapshot.json").resolve()}

def _normal(text):
    return re.sub(r"\s+", " ", str(text or "").casefold()).strip()

def _age(posted, as_of):
    try:
        return (as_of - date.fromisoformat(str(posted)[:10])).days
    except (TypeError, ValueError):
        return None

def _date_conflict(relative, age):
    if age is None or age < 0:
        return True
    r = _normal(relative)
    if r.startswith("just posted"):
        return age > 2
    if r.startswith("30+"):
        return age < 30
    m = re.fullmatch(r"(\d+) days? ago", r)
    return abs(age - int(m.group(1))) > 3 if m else False

def screen(items, *, as_of, historical_urls=()):
    if not isinstance(items, list) or len(items) > 30:
        raise ValueError("Require list with at most 30 pre-acquired records")
    seen_ids = set()
    known_urls = set(historical_urls)
    indexed = defaultdict(list)
    output = []
    for src in items:
        if not isinstance(src, dict):
            raise ValueError("Non-object source record")
        identifier = str(src.get("jobId") or "").strip()
        url = str(src.get("url") or "").strip()
        if not identifier or identifier in seen_ids or not url.startswith("https://"):
            raise ValueError("Missing/duplicate ID or invalid source URL")
        seen_ids.add(identifier)
        title = str(src.get("title") or "").strip()
        company = str(src.get("company") or "").strip()
        location = str(src.get("location") or "").strip()
        matched = classify_raw(src)
        explicit_exclude = any(phrase in _normal(title) for phrase in EXCLUDE_EXPLICIT)
        if explicit_exclude:
            triage = "EXCLUDE_OFF_SCOPE"
        elif matched.get("included") and matched.get("track") == "SECURITY":
            triage = "PROVISIONAL_REVIEW_REQUIRED"
        else:
            triage = "HOLD_AMBIGUOUS"
        age = _age(src.get("postedAt"), as_of)
        k = (_normal(title), _normal(company), _normal(location))
        indexed[k].append(identifier)
        output.append({
            "job_id": identifier, "source": "Indeed UK", "original_title": title,
            "source_employer": company, "source_location": location, "source_url": url,
            "source_posted_at": src.get("postedAt"), "source_posted_relative": src.get("postedRelative"),
            "source_age_days": age,
            "date_claim_conflict": _date_conflict(src.get("postedRelative"), age),
            "source_claim_older_than_30_days": (age is not None and age > 30),
            "provisional_family": matched.get("role_family") if triage == "PROVISIONAL_REVIEW_REQUIRED" else None,
            "triage": triage, "same_title_employer_location_ids": [],
            "overlaps_historical_beta_url": url in known_urls,
            "independently_verified": False, "publication_ready": False
        })
    for row in output:
        group=indexed[(_normal(row["original_title"]),_normal(row["source_employer"]),_normal(row["source_location"]))]
        row["same_title_employer_location_ids"] = sorted(set(group)-{row["job_id"]})
    counts=Counter(row["triage"] for row in output)
    return {
        "schema": "candidate-cyber-pilot-triage/v1", "checked_as_of": as_of.isoformat(),
        "source_run_id": "7SvLoLd7RZpCjO0Hq",
        "source_dataset_id": "2uG7TW13hpphfQ0P8",
        "record_count": len(output), "triage_counts": dict(counts),
        "older_than_30_days": sum(x["source_claim_older_than_30_days"] for x in output),
        "date_conflicts": sum(x["date_claim_conflict"] for x in output),
        "potential_exact_duplicate_record_count": sum(bool(x["same_title_employer_location_ids"]) for x in output),
        "independently_verified_count": 0, "publication_approved": False,
        "note": "This report uses source claims and provisional classification only; never a live-market proof.",
        "records": output
    }

def main():
    p=argparse.ArgumentParser(description="Screen previously acquired Indeed cyber dataset locally")
    p.add_argument("--input",required=True,help="Private JSON export of Apify dataset")
    p.add_argument("--output",required=True,help="Private QA JSON path, not public dashboard")
    p.add_argument("--as-of",default="2026-10-09")
    p.add_argument("--existing-beta",default="candidate-beta/data/pilot-snapshot.json")
    args=p.parse_args()
    dest=Path(args.output).resolve()
    if dest in PROTECTED or dest==Path(args.input).resolve():
        p.error("No production or input overwrite allowed")
    raw=json.loads(Path(args.input).read_text(encoding="utf-8"))
    existing=json.loads(Path(args.existing_beta).read_text(encoding="utf-8"))
    report=screen(raw,as_of=date.fromisoformat(args.as_of),
                  historical_urls=(r["url"] for r in existing.get("records",[])))
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="records"},sort_keys=True))

if __name__=="__main__":
    main()
