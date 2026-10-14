"""Conservative offline Salesforce relevance shortlist from EXISTING pilot review rows.

Input is the prior audit's review-only JSON artifact. Does not make HTTP calls,
does not assert a job is open, and cannot update WordPress or production DB.
"""
from __future__ import annotations
import json
import re
from collections import Counter
from pathlib import Path

STRONG = re.compile(r"\b(?:salesforce|sfdc|agentforce)\b", re.I)
CORE_ROLES = re.compile(
    r"\b(?:developer|engineer|architect|administrator|admin|consultant|"
    r"business analyst|functional|technical lead|product (?:manager|owner)|"
    r"solution|qa|tester|test analyst|platform|implementation|configuration|"
    r"release manager|delivery manager|systems trainer)\b", re.I)
ADJACENT = re.compile(r"\b(?:crm|marketing cloud|account executive|sales|"
                      r"support|operations|account manager|engagement|customer success)\b", re.I)


def category(row):
    title = str(row.get("title", ""))
    if STRONG.search(title) and CORE_ROLES.search(title):
        return "CORE_CANDIDATE"
    if STRONG.search(title):
        return "ADJACENT_REVIEW"
    if row.get("text_salesforce_signal") and (CORE_ROLES.search(title) or ADJACENT.search(title)):
        return "ADJACENT_REVIEW"
    return "IRRELEVANT_OR_INSUFFICIENT_EVIDENCE"


def shortlist(rows):
    if not isinstance(rows, list):
        raise ValueError("Expected review rows")
    out = []
    by_identity = {}
    for item in rows:
        if not isinstance(item, dict):
            raise ValueError("Invalid review row")
        row = {key: item.get(key) for key in (
            "source", "title", "employer", "posted_at", "url")}
        row["relevance"] = category(item)
        row["availability"] = "NOT_VERIFIED_OPEN"
        row["publication_allowed"] = False
        row["link_verified"] = False
        row["evidence_type"] = "PILOT_SOURCE_OBSERVATION"
        key = (re.sub(r"[^a-z0-9]+", " ", str(row["title"]).lower()).strip(),
               re.sub(r"[^a-z0-9]+", " ", str(row["employer"]).lower()
                      .replace(" limited", "").replace(" ltd", "")).strip())
        if key not in by_identity:
            by_identity[key] = []
        by_identity[key].append(row)
        out.append(row)
    for group in by_identity.values():
        if len(group) > 1:
            for row in group:
                row["duplicate_review_required"] = True
    counts = Counter(x["relevance"] for x in out)
    eligible = [x for x in out if x["relevance"] == "CORE_CANDIDATE"
                and x.get("url") and not x.get("duplicate_review_required")]
    return {"schema": "salesforce-pilot-shortlist-review/v1",
            "raw_observations": len(out),
            "relevance_counts": dict(counts),
            "core_nonduplicate_linked_candidates": len(eligible),
            "publication_allowed": False, "verified_open_count": 0,
            "classification_is_provisional": True,
            "caveat": "A title and source observation do not independently verify a vacancy is live."}, out


def main():
    src = Path("review/salesforce-pilot-20261014/review-only-candidates.json")
    rows = json.loads(src.read_text())
    report, tagged = shortlist(rows)
    dest = src.parent
    (dest / "relevance-summary.json").write_text(json.dumps(report, indent=2) + "\n")
    (dest / "classified-review-only.json").write_text(json.dumps(tagged, indent=2) + "\n")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
