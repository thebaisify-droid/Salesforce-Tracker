"""No-spend validated raw dataset fan-out to two independent tracker inputs.

Passing source data to both consumers does not imply the adverts are suitable
for either tracker. Each must independently run its current scope, dedupe,
assurance and WordPress publication gates before any live updates.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

from scripts.shared_acquisition_ledger import SharedLedger, replay_verified


def dual_readonly_handoff(request, *, ledger: SharedLedger, getter, now=None):
    now = now or datetime.now(timezone.utc)
    replay = replay_verified(request, ledger, getter, now=now)
    rows = replay["rows"]
    # Distinct deep copies ensure that the Salesforce classifier cannot
    # mutate an in-memory reference used by the BA classifier, or vice versa.
    sf = deepcopy(rows)
    ba = deepcopy(rows)
    return {
        "status": "TWO_INDEPENDENT_UNCLASSIFIED_INPUTS_NOT_PUBLISHED",
        "salesforce_raw_records": sf,
        "ba_raw_records": ba,
        "source_run_id": replay["run_id"],
        "dataset_id": replay["dataset_id"],
        "source_rows": len(rows),
        "actors_started": 0,
        "wordpress_requests": 0,
        "consumer_quality_passed": False,
    }


def summarise(handoff):
    """Metadata-only report; never upload raw candidate records to public CI."""
    return {k: handoff[k] for k in (
        "status", "source_run_id", "dataset_id", "source_rows",
        "actors_started", "wordpress_requests", "consumer_quality_passed")}
