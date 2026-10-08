from __future__ import annotations

import re
from typing import Any

from tracker.normalize import first_value, text_value

TITLE_DIRECT = (
    "salesforce",
    "sfdc",
    "mulesoft",
    "sales cloud",
    "service cloud",
    "experience cloud",
    "marketing cloud",
    "commerce cloud",
    "data cloud",
    "revenue cloud",
    "agentforce",
)

STRONG_PLATFORM_PHRASES = (
    "salesforce sales cloud",
    "salesforce service cloud",
    "salesforce experience cloud",
    "salesforce marketing cloud",
    "salesforce commerce cloud",
    "salesforce data cloud",
    "salesforce financial services cloud",
    "salesforce revenue cloud",
    "salesforce cpq",
    "salesforce implementation",
    "salesforce configuration",
    "salesforce development",
    "salesforce integration",
    "salesforce administrator",
    "salesforce developer",
    "salesforce architect",
    "salesforce consultant",
    "salesforce business analyst",
    "salesforce product owner",
    "salesforce trainer",
    "salesforce org",
    "salesforce flows",
    "lightning web component",
    "visualforce",
    "omnistudio",
    "apex",
    "mulesoft",
)

CONTEXTUAL_PHRASES = (
    "salesforce crm",
    "salesforce platform",
    "salesforce ecosystem",
)

CONTEXT_TITLE_HINTS = (
    "business analyst",
    "product owner",
    "product manager",
    "developer",
    "architect",
    "consultant",
    "crm",
    "platform",
    "integration",
    "systems",
    "devops",
    "release",
    "test",
    "qa",
    "customer success",
    "delivery",
)

COMPANY_KEYS = ("advertiser", "company", "company_name", "companyName", "employer", "recruiter")


def salesforce_relevance(raw: dict[str, Any]) -> tuple[bool, str]:
    title = (text_value(first_value(raw, "title", "title_raw", "job_title", "jobTitle", "position", "name")) or "").lower()
    company = (text_value(first_value(raw, *COMPANY_KEYS)) or "").lower().strip()
    description = (text_value(first_value(
        raw, "description", "descriptionText", "description_full", "descriptionFull",
        "job_description", "jobDescription", "body", "summary", "snippet",
        "descriptionSnippet", "description_snippet", "textSnippet", "skills_text"
    )) or "").lower()
    combined = f"{title}\n{description}"

    if any(term in title for term in TITLE_DIRECT):
        return True, "title_salesforce_signal"

    if company == "salesforce" or company.startswith("salesforce "):
        return True, "salesforce_direct_employer"

    strong_hits = [phrase for phrase in STRONG_PLATFORM_PHRASES if phrase in combined]
    if strong_hits:
        return True, "platform_signal:" + strong_hits[0]

    salesforce_mentions = len(re.findall(r"\bsalesforce\b", combined))
    contextual_hits = [phrase for phrase in CONTEXTUAL_PHRASES if phrase in combined]
    if (
        salesforce_mentions >= 2
        and contextual_hits
        and any(hint in title for hint in CONTEXT_TITLE_HINTS)
    ):
        return True, "role_plus_salesforce_context"

    return False, "generic_or_incidental_salesforce_mention"
