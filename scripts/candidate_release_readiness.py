"""Fail-closed go-live gate for the separate candidate market tracker.

Evaluate evidence files; does not trigger collection or publish anything.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

EXPECTED_SOURCES = {"CV-Library", "Totaljobs", "Indeed UK", "JobServe"}
EXPECTED_FAMILIES = 22

def assess(*, assurance: dict, evidence: dict, source_names=EXPECTED_SOURCES):
    reasons=[]
    if assurance.get("evidence_level") != "human_labelled_source_records":
        reasons.append("no_human_labelled_source_evidence")
    if not assurance.get("passed"):
        reasons.append("reviewed_classification_thresholds_not_met")
    if assurance.get("sample_size", 0) < 100:
        reasons.append("fewer_than_100_reviewed_vacancies")
    if not set(source_names).issubset(set(assurance.get("sources") or {})):
        reasons.append("missing_core_source_review_coverage")
    if not evidence.get("source_authenticity_confirmed"):
        reasons.append("source_authenticity_not_confirmed")
    if not evidence.get("independent_review_confirmed"):
        reasons.append("independent_review_not_confirmed")
    if not evidence.get("unbiased_sampling_confirmed"):
        reasons.append("representative_random_sample_not_confirmed")
    if not evidence.get("cross_source_deduplication_checked"):
        reasons.append("cross_source_deduplication_not_checked")
    if not evidence.get("account_spend_limit_confirmed_at_or_below_19_usd"):
        reasons.append("apify_account_spending_limit_unconfirmed")
    if not evidence.get("independent_database_restore_tested"):
        reasons.append("database_restore_not_tested")
    if evidence.get("configured_role_families") != EXPECTED_FAMILIES:
        reasons.append("role_family_configuration_unverified")
    if not evidence.get("website_filter_navigation_tested"):
        reasons.append("website_filters_not_tested")
    return {
        "schema": "candidate-release-readiness/v1",
        "ready_for_review": not reasons,
        "publication_approved": False,
        "paid_acquisition_enabled": False,
        "reasons": reasons,
        "note": "This report never changes production settings or grants go-live approval."
    }

def main():
    p=argparse.ArgumentParser(description="Offline release readiness evidence check")
    p.add_argument("--assurance",required=True)
    p.add_argument("--evidence",required=True)
    p.add_argument("--report",required=True)
    a=p.parse_args()
    output=Path(a.report).resolve()
    forbidden={Path("dashboard/live-data.json").resolve(),Path("dashboard/data.json").resolve()}
    if output in forbidden:
        p.error("live Salesforce outputs are protected")
    assurance=json.loads(Path(a.assurance).read_text(encoding="utf-8"))
    evidence=json.loads(Path(a.evidence).read_text(encoding="utf-8"))
    report=assess(assurance=assurance,evidence=evidence)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(report,sort_keys=True))
    return 0 if report["ready_for_review"] else 2

if __name__=="__main__":
    raise SystemExit(main())
