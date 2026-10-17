"""Offline quality audit of 16 Oct 2026 completed, already-paid Apify outputs.

No network, GitHub Actions dispatch, Actor POST, WordPress or production writes.
Only use the immutable, trimmed evidence on the feature branch; never treat
dataset output as evidence that an employer currently accepts applications.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from scripts.ba_stage_five_source_data import (
    MAPPING, cleaned_excerpt, company, link, location, posted, stage, working, employment,
)
from tracker.business_product_delivery_security import classify_market_role, taxonomy

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "business-analysis-tracker/evidence/ba-five-completed-20261016-audit-redacted.json"
DEFAULT_REPORT = ROOT / "business-analysis-tracker/data/ba-20261016-offline-quality-report.json"
TARGETS = {
    "CV-Library": "Security Management",
    "Totaljobs": "IT Security",
    "Reed UK": "Business Analysis",
    "Indeed UK": "Data Analysis",
    "JobServe": "Business Intelligence",
}
APPROVED_COUNTS = {"CV-Library": 30, "Totaljobs": 25, "Reed UK": 30, "Indeed UK": 30, "JobServe": 46}
AUTHORISED_ITEMS = {name: 30 for name in TARGETS}
EXCLUDED_AD_STYLES = re.compile(
    r"\b(?:no experience needed|no experience required|"
    r"guaranteed job|career change programme|training course|"
    r"training provider|bootcamp|placement guarantee)\b",
    re.IGNORECASE,
)

def _normalise(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower()).strip()

def inspect() -> dict:
    doc = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    config = json.loads(MAPPING.read_text(encoding="utf-8"))
    sources = doc.get("sources", [])
    if (doc.get("schema") != "ba-offline-actor-observations/v1"
            or len(sources) != 5 or {s.get("name") for s in sources} != set(TARGETS)
            or doc.get("publication_approved") is not False
            or doc.get("paid_actor_runs_started_by_audit") != 0):
        raise ValueError("Not the provenance-locked, unpaid five-source audit file")

    families = {family["name"] for family in taxonomy()["role_families"]}
    if len(families) != 22:
        raise ValueError("Expected 22 distinct registered role families")
    observed_counts = {}
    source_results = []
    encountered_urls = set()
    all_titles = Counter()
    overall_quality = Counter()
    audit_candidates = []
    all_rejected = Counter()
    for receipt in sources:
        name = receipt["name"]
        records = receipt["records"]
        n = len(records)
        if (receipt.get("status") != "SUCCEEDED" or not receipt.get("attempted")
                or not receipt.get("run_id") or not receipt.get("dataset_id")
                or not isinstance(receipt.get("observed_at"), str)):
            raise ValueError("Invalid completed source provenance: " + name)
        if n != APPROVED_COUNTS[name]:
            raise ValueError("Dataset snapshot count changed; do not silently adopt new rows: " + name)
        observed_counts[name] = n
        source_q = Counter()
        matched_families = Counter()
        accepted_title_examples = []
        flagged_title_examples = []
        for raw in records:
            title = raw.get("title") or raw.get("jobTitle") or ""
            snippet = cleaned_excerpt(raw)
            url = link(raw, name)
            decision = classify_market_role(title, snippet)
            all_titles[_normalise(title)] += 1
            if not title: source_q["missing_title"] += 1
            if not url: source_q["missing_safe_https_url"] += 1
            if not posted(raw): source_q["no_usable_posted_date"] += 1
            if not snippet: source_q["no_description_snippet"] += 1
            if employment(raw) == "Not specified": source_q["employment_unspecified"] += 1
            if working(raw) == "Not specified": source_q["working_unspecified"] += 1
            if EXCLUDED_AD_STYLES.search(title + " " + (snippet or "")):
                source_q["training_or_nonvacancy_pattern"] += 1
                if len(flagged_title_examples) < 5: flagged_title_examples.append(title)
            if decision.get("included"):
                source_q["taxonomy_title_matches"] += 1
                matched_families[decision["role_family"]] += 1
                if decision["role_family"] == TARGETS[name]:
                    source_q["matches_intended_search_family"] += 1
                if decision.get("review_required"):
                    source_q["title_context_review_required"] += 1
                if len(accepted_title_examples) < 5: accepted_title_examples.append(title)
            else:
                source_q["taxonomy_title_excluded"] += 1
                all_rejected[decision.get("reason", "unknown")] += 1
            if url:
                if url in encountered_urls:
                    source_q["exact_url_repeated_across_dataset"] += 1
                encountered_urls.add(url)
            if not isinstance(raw, dict):
                source_q["malformed"] += 1
        overall_quality.update(source_q)
        source_results.append({
            "source": name, "intended_family": TARGETS[name],
            "requested_max_results": AUTHORISED_ITEMS[name],
            "records_saved_after_completion": n,
            "count_recorded_inside_original_workflow": doc["source_run_counts_recorded_in_workflow"][name],
            "observed_count_growth": n - doc["source_run_counts_recorded_in_workflow"][name],
            "output_exceeds_requested_results": n > AUTHORISED_ITEMS[name],
            "quality": dict(source_q),
            "classified_families": dict(matched_families.most_common()),
            "example_matching_titles": accepted_title_examples,
            "example_training_or_nonvacancy_titles": flagged_title_examples,
            "actor_run_id": receipt["run_id"],
            "dataset_id": receipt["dataset_id"],
        })
    staging = stage(
        {"schema": "ba-five-source-completed-batch/v1", "sources": sources},
        config,
    )
    if staging["status"] != "FIVE_SOURCES_RECEIVED_STAGED_ONLY":
        raise ValueError("Historical review staging did not pass receipt contract")
    rows = staging["records"]
    clusters = defaultdict(list)
    for record in rows:
        key = (_normalise(record["title"]), _normalise(record["advertiser"]),
               _normalise(record["location"]))
        clusters[key].append(record)
    possible_duplicate_clusters = [
        [row["id"] for row in cluster] for cluster in clusters.values()
        if len(cluster) > 1
    ]
    counts = Counter(row["role_family"] for row in rows)
    source_retained = Counter(row["job_source"] for row in rows)
    sector_known = sum(r["sector"] != "Not specified" for r in rows)
    date_known = sum(bool(r.get("posted_date")) for r in rows)
    working_known = sum(r["working_arrangement"] != "Not specified" for r in rows)
    example_flagged = [
        {"source": r["job_source"], "title": r["title"],
         "reason": "POTENTIAL_TRAINING_LEAD_INSTEAD_OF_EMPLOYER_OPENING"}
        for r in rows
        if EXCLUDED_AD_STYLES.search(r["title"] + " " + (r.get("description_summary") or ""))
    ][:20]
    return {
        "schema": "ba-20261016-offline-quality-assessment/v1",
        "status": "OFFLINE_AUDIT_ONLY_NOT_APPROVED_FOR_PUBLICATION",
        "observation_date": "2026-10-16",
        "metadata_basis": "Completed Apify source datasets, not employer-verified job openings",
        "sources_succeeded": 5,
        "total_source_rows_observed": sum(observed_counts.values()),
        "authorized_per_source_request": AUTHORISED_ITEMS,
        "dataset_counts": observed_counts,
        "source_count_drift_warning": any(x["observed_count_growth"] != 0 for x in source_results),
        "jobserve_output_limit_breach": observed_counts["JobServe"] > AUTHORISED_ITEMS["JobServe"],
        "sources": source_results,
        "pipeline_qa_preview": {
            "taxonomy_matched_after_url_and_duplicate_filters": len(rows),
            "title_family_counts": dict(counts.most_common()),
            "distinct_families": len(counts),
            "missing_families": sorted(families - set(counts)),
            "source_accepted_counts": dict(source_retained),
            "excluded_counts": staging.get("rejected", {}),
            "possible_duplicate_rows": staging.get("potential_duplicate_rows",0),
            "possible_cross_board_duplicate_clusters": len(possible_duplicate_clusters),
            "posted_dates_available": date_known,
            "advertiser_sector_evidenced": sector_known,
            "working_arrangement_available": working_known,
            "training_or_nonvacancy_patterns_in_candidate": len([
                r for r in rows if EXCLUDED_AD_STYLES.search(
                    r["title"] + " " + (r.get("description_summary") or ""))]),
            "training_or_nonvacancy_examples": example_flagged,
        },
        "quality_metrics_raw": dict(overall_quality),
        "paid_actor_runs_started_by_audit": 0,
        "wordpress_requests": 0,
        "publication_approved": False,
        "billing_cost_verified": False,
        "requires": [
            "Do not accept JobServe 46/30 as input-limit compliant",
            "Investigate Reed and Indeed post-run row-count growth",
            "Review training/course marketing and occupational false positives",
            "Reconcile actual invoice/usage before further paid acquisition",
            "Preserve prior WordPress snapshot and $8 Salesforce reserve",
        ],
    }

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    options = p.parse_args()
    output = inspect()
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
    summary = {
        "status": output["status"],"source_rows":output["total_source_rows_observed"],
        "matched":output["pipeline_qa_preview"]["taxonomy_matched_after_url_and_duplicate_filters"],
        "families":output["pipeline_qa_preview"]["distinct_families"],
        "per_family":output["pipeline_qa_preview"]["title_family_counts"],
        "by_source":output["pipeline_qa_preview"]["source_accepted_counts"],
        "rejected":output["pipeline_qa_preview"]["excluded_counts"],
        "missing_sector":output["pipeline_qa_preview"]["taxonomy_matched_after_url_and_duplicate_filters"]-output["pipeline_qa_preview"]["advertiser_sector_evidenced"],
        "training_patterns":output["pipeline_qa_preview"]["training_or_nonvacancy_patterns_in_candidate"],
        "actor_runs_started":0,"wordpress_requests":0,
    }
    print("OFFLINE_AUDIT_RESULT",json.dumps(summary,sort_keys=True))

if __name__ == "__main__":
    main()
