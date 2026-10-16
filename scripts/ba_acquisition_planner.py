"""Plan budget-aware, source-specific UK jobs collection across all 22 role families.

Pure planning only: no paid Actors, credentials, or network requests.
Each scheduled slot searches five *different* families. All 22 receive an
acquisition opportunity within five successful scheduled slots. Retaining
records across slots is a separate publication requirement.
"""
from __future__ import annotations
from copy import deepcopy
import json
import math
from pathlib import Path

from tracker.business_product_delivery_security import taxonomy

ROOT = Path(__file__).resolve().parents[1]
ROTATION = ROOT / "business-analysis-tracker/config/role_search_rotation.json"
SEARCH_FIELD = {
    "CV-Library": "query",
    "Totaljobs": "keywords",
    "Reed UK": "keywords",
    "Indeed UK": "query",
    "JobServe": "keywords",
}
RESULT_FIELD = {
    "CV-Library": "maxResults",
    "Totaljobs": "maxListings",
    "Reed UK": "maxResults",
    "Indeed UK": "maxResults",
    "JobServe": "maxResults",
}

def role_queries(path=ROTATION):
    spec = json.loads(Path(path).read_text(encoding="utf8"))
    entries = spec.get("role_queries")
    registered = [item["name"] for item in taxonomy()["role_families"]]
    if spec.get("schema") != "business-tech-role-rotation/v1" or not isinstance(entries, list):
        raise ValueError("Missing audited 22-family search plan")
    if len(entries) != 22 or [item.get("family") for item in entries] != registered:
        raise ValueError("Search plan must match the existing 22-family taxonomy exactly")
    if any(not isinstance(item.get("query"), str) or not item["query"].strip() for item in entries):
        raise ValueError("Each family requires a real search term")
    return entries

def select_slot(config:dict, slot_number:int, report:dict, *, entries=None) -> dict:
    """Return source inputs with per-item price-aware reductions, never increases."""
    if type(slot_number) is not int or not 1 <= slot_number <= 9:
        raise ValueError("Scheduled slot must be between 1 and 9")
    entries = role_queries() if entries is None else entries
    if len(entries) != 22 or len({x["family"] for x in entries}) != 22:
        raise ValueError("22 unique role-family searches required")
    planned = deepcopy(config)
    rates = {item["source"]: item for item in report.get("actor_pricing", [])}
    if len(planned["sources"]) != 5 or set(rates) != set(SEARCH_FIELD):
        raise ValueError("Five source pricing observations required")
    for i, source in enumerate(planned["sources"]):
        family = entries[((slot_number - 1) * 5 + i) % 22]
        name = source["name"]
        field = SEARCH_FIELD[name]
        cap = source["max_charge_usd"]
        price = rates[name]
        maximum = source["max_items"]
        if price.get("pricing_model") in ("PRICE_PER_DATASET_ITEM", "PAY_PER_RESULT"):
            unit = price.get("price_per_unit_usd")
            if type(unit) not in (float, int) or unit < 0:
                raise ValueError(name + ": unit price missing")
            if unit > 0:
                maximum = min(maximum, math.floor((cap + 1e-9) / unit))
        if maximum < 1:
            raise ValueError(name + ": no result fits the approved Actor charge cap")
        source["max_items"] = maximum
        source["input"][RESULT_FIELD[name]] = maximum
        source["input"][field] = [family["query"]] if name == "JobServe" else family["query"]
        source["query_family"] = family["family"]
    planned["rotation_slot"] = slot_number
    return planned

def coverage_for_slots(slots:int=5) -> set[str]:
    entries = role_queries()
    return {entries[((slot - 1) * 5 + i) % 22]["family"]
            for slot in range(1, slots + 1) for i in range(5)}
