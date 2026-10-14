"""Read-only post-pilot billing + review candidate builder.

Five immutable existing Apify dataset IDs only. GET requests only. No Actor
execution, no WordPress writes, no database mutations, no raw descriptions.
Candidate records are REVIEW_ONLY, never publishable evidence.
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

DATASETS = (
    ("CV-Library", "DdaNpBgWqKtIGQPoP", 20),
    ("Totaljobs", "Frb9dCblni8WJL2mm", 20),
    ("Reed UK", "6u5oU6lzTwCVHaQdh", 20),
    ("Indeed UK", "mc7XljwsWVCnN0hvz", 20),
    ("JobServe", "JMfCWdTNBAl02U5r5", 22),
)
API = "https://api.apify.com/v2/"
OUT = Path("review/salesforce-pilot-20261014")
BASELINE_USAGE_ROUNDED = 7.65


def get(path, token):
    if not path.startswith(API):
        raise ValueError("Non-Apify URL denied")
    request = Request(path, method="GET", headers={
        "Authorization": "Bearer " + token, "Accept": "application/json"})
    with urlopen(request, timeout=45) as response:
        return json.load(response)


def normalize_url(value):
    if not isinstance(value, str):
        return None
    url = value.strip()
    # Exact, source-confirmed duplication pattern only; never manufacture links.
    prefix = "https://www.totaljobs.com/"
    if url.startswith(prefix + "https://www.totaljobs.com/"):
        url = url[len(prefix):]
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or "://" in parsed.path:
        return None
    allowed = ("cv-library.co.uk", "totaljobs.com", "reed.co.uk",
               "indeed.com", "jobserve.com")
    host = parsed.hostname.lower()
    if not any(host == a or host.endswith("." + a) for a in allowed):
        return None
    return url


def employer_name(row):
    obj = row.get("company") or row.get("employer")
    if isinstance(obj, dict):
        obj = obj.get("name") or obj.get("companyName") or obj.get("displayName")
    return str(obj or "").strip()[:160]


def normal(value):
    return re.sub(r"[^a-z0-9]+", " ", re.sub(r"\b(limited|ltd|plc)\b", "", str(value).lower())).strip()


def inspect_sources(payloads):
    all_rows = []
    source_summaries = []
    for name, dataset, expected in DATASETS:
        rows = payloads.get(dataset)
        if not isinstance(rows, list) or len(rows) != expected:
            raise ValueError("Dataset unavailable or count changed for " + name)
        summary = dict(source=name, raw=len(rows), title_signal=0,
                       description_signal=0, posted_oct_12_onward=0,
                       malformed_url=0, before_sep_30=0)
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("Unexpected source row")
            title = str(row.get("title") or "").strip()[:240]
            employer = employer_name(row)
            posted = str(row.get("postedAt") or row.get("datePosted")
                         or row.get("postedDateTime") or "")[:60]
            link_raw = row.get("canonicalUrl") or row.get("jobUrl") or row.get("externalUrl") or row.get("url")
            link = normalize_url(link_raw)
            if not link:
                summary["malformed_url"] += 1
            signal = bool(re.search(r"salesforce|sfdc|agentforce", title, re.I))
            description = str(row.get("descriptionText") or row.get("descriptionSnippet")
                              or row.get("snippet") or row.get("description") or "")[:9000]
            desc_signal = bool(re.search(r"salesforce|sfdc|agentforce", title + " " + description, re.I))
            summary["title_signal"] += signal
            summary["description_signal"] += desc_signal
            try:
                date = datetime.fromisoformat(posted.replace("Z", "+00:00"))
                if date.tzinfo is None:
                    date = date.replace(tzinfo=timezone.utc)
                summary["posted_oct_12_onward"] += date >= datetime(2026, 10, 12, tzinfo=timezone.utc)
                summary["before_sep_30"] += date < datetime(2026, 9, 30, tzinfo=timezone.utc)
            except ValueError:
                pass
            all_rows.append({"source": name, "title": title, "employer": employer,
                             "posted_at": posted, "url": link,
                             "title_salesforce_signal": signal,
                             "text_salesforce_signal": desc_signal,
                             "status": "REVIEW_ONLY_NOT_VERIFIED_OPEN"})
        source_summaries.append(summary)
    grouped = {}
    for row in all_rows:
        key = (normal(row["title"]), normal(row["employer"]))
        grouped.setdefault(key, []).append(row)
    duplicates = [g for g in grouped.values() if len(g) > 1]
    for group in duplicates:
        for row in group:
            row["status"] = "DUPLICATE_REVIEW"
    report = {"schema": "salesforce-pilot-readonly-qa/v1",
              "source_summaries": source_summaries,
              "raw_rows": len(all_rows),
              "same_title_employer_duplicate_groups": len(duplicates),
              "duplicate_excess_rows": sum(len(x)-1 for x in duplicates),
              "candidate_unique_title_employer": len(grouped),
              "publication_allowed": False, "verified_open": 0,
              "actors_started": 0, "wordPress_changed": False,
              "caveat": "Title/text matches and posting dates do not establish Salesforce-platform relevance or vacancy availability"}
    return report, all_rows


def billing(data):
    info = data.get("data", {})
    lim = info.get("limits", {}).get("maxMonthlyUsageUsd")
    used = info.get("current", {}).get("monthlyUsageUsd")
    if type(lim) not in (int, float) or type(used) not in (int, float):
        raise ValueError("Billing limit or usage unavailable")
    if abs(lim - 19) > .0001 or used < 0 or used > lim:
        raise ValueError("Billing exceeds account guard")
    return {"account_limit_usd": lim, "current_monthly_usage_usd": used,
            "internal_salesforce_reserve_usd": 8,
            "headroom_after_reserve_usd": round(max(0, lim-used-8), 4),
            "baseline_usage_usd_rounded": BASELINE_USAGE_ROUNDED,
            "change_since_baseline_usd_approx": round(used-BASELINE_USAGE_ROUNDED, 4),
            "per_run_invoiced_charges_verified": False,
            "note": "Account usage delta is not per-run billing evidence and can include unrelated runs"}


def main():
    token = os.getenv("APIFY_TOKEN", "")
    if not token:
        raise SystemExit("APIFY_TOKEN is required")
    account = billing(get(API + "users/me/limits", token))
    datasets = {}
    for _, dataset, _ in DATASETS:
        result = get(API + "datasets/" + dataset + "/items?clean=true&limit=100", token)
        if not isinstance(result, list):
            raise ValueError("Unexpected dataset payload")
        datasets[dataset] = result
    report, rows = inspect_sources(datasets)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "quality-summary.json").write_text(json.dumps(report, indent=2) + "\n")
    (OUT / "billing-summary.json").write_text(json.dumps(account, indent=2) + "\n")
    (OUT / "review-only-candidates.json").write_text(json.dumps(rows, indent=2) + "\n")
    print(json.dumps({"billing": account, "quality": report}, sort_keys=True))


if __name__ == "__main__":
    main()
