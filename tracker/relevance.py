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
)

PLATFORM_PHRASES = (
    "salesforce platform",
    "salesforce crm",
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
    "salesforce ecosystem",
    "salesforce org",
    "salesforce flows",
    "lightning web component",
    "visualforce",
    "mulesoft",
)

TITLE_ROLE_HINTS = (
    "business analyst",
    "product owner",
    "product manager",
    "administrator",
    "developer",
    "architect",
    "technical consultant",
    "functional consultant",
    "crm",
    "platform",
    "integration",
    "systems trainer",
    "salesforce trainer",
    "devops",
    "release manager",
    "test analyst",
)


def salesforce_relevance(raw: dict[str, Any]) -> tuple[bool, str]:
    title = (text_value(first_value(raw, "title", "title_raw", "job_title", "jobTitle", "position", "name")) or "").lower()
    description = (text_value(first_value(
        raw, "description", "descriptionText", "job_description", "jobDescription",
        "body", "summary", "descriptionSnippet", "textSnippet"
    )) or "").lower()
    combined = f"{title}\n{description}"

    if any(term in title for term in TITLE_DIRECT):
        return True, "title_salesforce_signal"

    phrase_hits = [phrase for phrase in PLATFORM_PHRASES if phrase in combined]
    if phrase_hits:
        return True, "platform_signal:" + phrase_hits[0]

    salesforce_mentions = len(re.findall(r"\bsalesforce\b", combined))
    if salesforce_mentions >= 2 and any(hint in title for hint in TITLE_ROLE_HINTS):
        return True, "role_plus_salesforce_context"

    return False, "generic_or_incidental_salesforce_mention"
