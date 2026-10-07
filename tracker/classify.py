from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MASTER_PATH = ROOT / "config" / "master_data_v1.4.json"
TAXONOMY_PATH = ROOT / "config" / "role_taxonomy_v2.2.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def master_data() -> dict[str, Any]:
    return _load(MASTER_PATH)


@lru_cache(maxsize=1)
def role_taxonomy() -> dict[str, Any]:
    return _load(TAXONOMY_PATH)


def versions() -> tuple[str, str]:
    return str(master_data()["version"]), str(role_taxonomy()["version"])


def _contains_any(text: str, values: list[str]) -> list[str]:
    low = text.lower()
    return [v for v in values if v.lower() in low]


def _phrase_present(text: str, phrase: str) -> bool:
    pattern = r"(?<!\w)" + re.escape(phrase.lower()) + r"(?!\w)"
    return re.search(pattern, text.lower()) is not None


def classify_advertiser(advertiser: str | None, description: str | None) -> dict[str, Any]:
    advertiser = (advertiser or "").strip()
    description = description or ""
    cfg = master_data()["advertiser"]

    known_hits = _contains_any(advertiser, cfg.get("known_agencies", []))
    name_hits = _contains_any(advertiser, cfg["agency_name_markers"])
    desc_hits = _contains_any(description, cfg["agency_description_markers"])

    if known_hits:
        return {
            "advertiser_type": "RECRUITMENT_AGENCY",
            "advertiser_type_confidence": 0.99,
            "advertiser_method": "KNOWN_AGENCY",
        }
    if name_hits:
        return {
            "advertiser_type": "RECRUITMENT_AGENCY",
            "advertiser_type_confidence": 0.98,
            "advertiser_method": "AGENCY_NAME_MARKER",
        }
    if desc_hits:
        return {
            "advertiser_type": "RECRUITMENT_AGENCY",
            "advertiser_type_confidence": 0.95,
            "advertiser_method": "AGENCY_DESCRIPTION_MARKER",
        }
    if advertiser:
        return {
            "advertiser_type": "DIRECT_EMPLOYER",
            "advertiser_type_confidence": 0.78,
            "advertiser_method": "NO_AGENCY_SIGNAL",
        }
    return {
        "advertiser_type": "MIXED_OR_UNKNOWN",
        "advertiser_type_confidence": 0.45,
        "advertiser_method": "INSUFFICIENT_EVIDENCE",
    }


def _extract_end_client(description: str) -> tuple[str | None, str | None]:
    patterns = [
        r"(?:our client|the client)\s+(?:is|are)\s+(?:an?\s+)?([A-Z][A-Za-z0-9&.'()\- ]{2,70}?)(?:[,.]|\s+who\b|\s+seeking\b|\s+looking\b)",
        r"(?:on behalf of)\s+([A-Z][A-Za-z0-9&.'()\- ]{2,70}?)(?:[,.]|\s+we\b)",
    ]
    for pattern in patterns:
        match = re.search(pattern, description or "")
        if match:
            name = re.sub(r"\s+", " ", match.group(1)).strip(" -")
            if 2 < len(name) <= 80:
                return name, "DESCRIPTION_CLIENT_NAME"
    return None, None


def classify_sector(description: str | None, advertiser_type: str, end_client_name: str | None) -> dict[str, Any]:
    text = description or ""
    sectors = master_data()["sectors"]
    scored: list[tuple[int, str, list[str]]] = []
    for sector, keywords in sectors.items():
        hits = [kw for kw in keywords if _phrase_present(text, kw)]
        if hits:
            scored.append((len(hits), sector, hits))
    scored.sort(key=lambda item: (-item[0], item[1]))

    if not scored:
        return {
            "end_client_sector": None,
            "end_client_sector_confidence": 0.0,
            "sector_basis": "UNRESOLVED",
            "sector_method": None,
            "sector_review_required": 1,
        }

    hit_count, sector, hits = scored[0]
    confidence = min(0.95, 0.72 + 0.08 * hit_count)
    basis = "END_CLIENT_DESCRIPTION_SECTOR" if advertiser_type == "RECRUITMENT_AGENCY" else "ADVERTISER_DESCRIPTION_SECTOR"
    review = int(confidence < 0.85 or (advertiser_type == "RECRUITMENT_AGENCY" and not end_client_name))
    return {
        "end_client_sector": sector,
        "end_client_sector_confidence": round(confidence, 4),
        "sector_basis": basis,
        "sector_method": "DESCRIPTION_KEYWORDS:" + ",".join(hits[:4]),
        "sector_review_required": review,
    }


def classify_role(title: str | None, description: str | None) -> dict[str, Any]:
    title = title or ""
    description = description or ""
    title_low = title.lower()
    desc_low = description.lower()
    taxonomy = role_taxonomy()

    best_name = "Other / Unresolved"
    best_score = 0
    best_hits: list[str] = []
    for family in taxonomy["role_families"]:
        score = 0
        hits: list[str] = []
        for keyword in family["keywords"]:
            k = keyword.lower()
            if k in title_low:
                score += 4
                hits.append(keyword)
            elif k in desc_low:
                score += 1
                hits.append(keyword)
        if score > best_score:
            best_score = score
            best_name = family["name"]
            best_hits = hits

    if best_score >= 4:
        confidence = min(0.99, 0.86 + 0.025 * min(best_score - 4, 5))
    elif best_score > 0:
        confidence = 0.68
    else:
        confidence = 0.35

    seniority = "Standard"
    for label, markers in taxonomy["seniority"].items():
        if any(marker in title_low for marker in markers):
            seniority = label
            break

    combined = f"{title_low}\n{desc_low}"
    specialisms = [name for name, markers in taxonomy["specialisms"].items() if any(m.lower() in combined for m in markers)]

    return {
        "role_family": best_name,
        "role_seniority": seniority,
        "role_specialism": specialisms,
        "role_confidence": round(confidence, 4),
        "role_method": "TITLE_DESCRIPTION_KEYWORDS" if best_hits else "UNRESOLVED",
        "role_review_required": int(confidence < 0.75 or best_name == "Other / Unresolved"),
    }


def classify(title: str | None, advertiser: str | None, description: str | None) -> dict[str, Any]:
    advert = classify_advertiser(advertiser, description)
    end_client_name = None
    end_client_method = None
    if advert["advertiser_type"] == "RECRUITMENT_AGENCY":
        end_client_name, end_client_method = _extract_end_client(description or "")

    role = classify_role(title, description)
    sector = classify_sector(description, advert["advertiser_type"], end_client_name)
    return {
        **advert,
        **role,
        **sector,
        "end_client_name": end_client_name,
        "end_client_method": end_client_method or sector.get("sector_method"),
    }
