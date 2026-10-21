"""Two independent classifiers over identical raw source records, read-only.

The result is evidence of classification feasibility, NEVER approval to
publish or assertion of complete coverage of BA's 22 rotating role families.
"""
from __future__ import annotations
from collections import Counter
from tracker.relevance import salesforce_relevance
from tracker.normalize import normalize
from tracker.business_product_delivery_security import classify_raw, taxonomy


def audit_dual(rows, *, source_name="shared-readonly"):
    if not isinstance(rows, list):
        raise ValueError("Raw rows must be a list")
    sf_count, ba_count, both, sf_normalize_failed = 0, 0, 0, 0
    families = Counter()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Raw row must be an object")
        sf, _ = salesforce_relevance(row)
        ba = classify_raw(row)
        if sf:
            sf_count += 1
            try:
                if not normalize(row, source_name).get("display_title"):
                    sf_normalize_failed += 1
            except (ValueError, KeyError, TypeError):
                sf_normalize_failed += 1
        if ba["included"]:
            ba_count += 1
            families[ba["role_family"]] += 1
        if sf and ba["included"]:
            both += 1
    configured = {family["name"] for family in taxonomy()["role_families"]}
    return {
        "status": "INDEPENDENT_CLASSIFICATION_SHADOW_ONLY",
        "raw_source_rows": len(rows),
        "salesforce_relevant": sf_count,
        "salesforce_normalize_errors": sf_normalize_failed,
        "ba_relevant": ba_count,
        "cross_scope": both,
        "ba_role_family_count_configured": len(configured),
        "ba_families_observed": dict(sorted(families.items())),
        "ba_families_unobserved": sorted(configured - set(families)),
        "coverage_approved": False, "publication_approved": False,
        "actors_started": 0, "wordpress_requests": 0,
    }
