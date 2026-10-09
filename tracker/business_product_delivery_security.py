"""Independent, non-acquiring classifier for business/product/delivery/security jobs.

This module does not import or change the Salesforce relevance gate.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TAXONOMY_PATH = ROOT / "config" / "business_product_delivery_security_taxonomy_v1.0.json"

@lru_cache(maxsize=1)
def taxonomy() -> dict[str, Any]:
    return json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))

def _has_phrase(text: str, phrase: str) -> bool:
    return re.search(r"(?<!\w)" + re.escape(phrase.lower()) + r"(?!\w)", text.lower()) is not None

def classify_market_role(title: str | None, description: str | None = None) -> dict[str, Any]:
    """Return inclusion decision, family, track, evidence and review status.

    A title match is mandatory. Generic security titles require verifiable cyber/
    IT/information-security context; marketing or incidental description mentions
    alone never qualify an unrelated job.
    """
    title = re.sub(r"\s+", " ", title or "").strip().lower()
    description = re.sub(r"\s+", " ", description or "").strip().lower()
    cfg = taxonomy()
    if not title:
        return {"included": False, "reason": "missing_title", "role_family": None, "track": None, "review_required": True}
    if title.startswith(("assistant to ", "pa to ", "secretary to ")) or any(_has_phrase(title, phrase) for phrase in cfg["excluded_title_phrases"]):
        return {"included": False, "reason": "excluded_title", "role_family": None, "track": None, "review_required": False}
    matched = []
    for index, family in enumerate(cfg["role_families"]):
        for phrase in family["titles"]:
            if _has_phrase(title, phrase):
                matched.append((len(phrase), -index, phrase, family))
    if not matched:
        return {"included": False, "reason": "no_target_title", "role_family": None, "track": None, "review_required": False}
    _, _, phrase, family = max(matched, key=lambda item: (item[0], item[1]))
    is_security = family["track"] == "SECURITY"
    cyber_context = any(_has_phrase(title + " " + description, term) for term in cfg["security_context_terms"])
    ambiguous_security = is_security and phrase in {
        "security architect", "security advisor", "security adviser",
        "security risk manager", "security assurance consultant",
        "technology risk manager", "third party risk analyst",
        "third-party risk analyst", "third party risk manager",
        "third-party risk manager", "risk analyst (third party risk)",
        "risk analyst (third-party risk)",
    }
    # A generic third-party/vendor-risk title does not by itself establish
    # cyber/information-security specialism. Requiring independent cyber context
    # avoids treating procurement, finance or operational TPRM as cyber roles.
    if is_security and phrase in {
        "third party risk analyst", "third-party risk analyst",
        "third party risk manager", "third-party risk manager",
        "risk analyst (third party risk)", "risk analyst (third-party risk)",
    }:
        cyber_context = any(
            _has_phrase(title + " " + description, term)
            for term in cfg["security_context_terms"]
            if term not in {"third party risk", "third-party risk", "tprm"}
        )
    if ambiguous_security and not cyber_context:
        return {"included": False, "reason": "ambiguous_security_context", "role_family": family["name"],
                "track": family["track"], "matched_title": phrase, "review_required": True}
    # Operational roles can also be ambiguous; flag for QA rather than discarding
    # every valid job with a minimal snippet.
    review = (
        (not is_security and phrase in {
            "delivery manager", "service owner", "service designer",
            "service delivery manager", "product analyst", "product lead",
            "change analyst", "transformation lead", "reporting analyst",
            "insights analyst", "performance analyst", "analytics manager"
        })
        or (is_security and phrase in {
            "analyst, information security",
            "risk analyst (third party risk)", "risk analyst (third-party risk)",
            "third party risk analyst", "third-party risk analyst",
            "third party risk manager", "third-party risk manager",
        })
    )
    return {"included": True, "reason": "matched_title", "role_family": family["name"],
            "track": family["track"], "matched_title": phrase, "review_required": review}

def classify_raw(raw: dict[str, Any]) -> dict[str, Any]:
    title = next((str(raw[key]) for key in ("title", "title_raw", "job_title", "jobTitle", "position", "name")
                  if raw.get(key)), None)
    description = next((str(raw[key]) for key in ("description", "descriptionText", "job_description",
                     "jobDescription", "summary", "snippet", "body") if raw.get(key)), None)
    return classify_market_role(title, description)
