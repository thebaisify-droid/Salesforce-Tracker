"""Atomically claim a scheduled BA slot with a durable GitHub ref.

First successful claim wins. A failed/partial acquisition remains claimed:
no automated retry or second paid attempt is allowed.
"""
from __future__ import annotations
import json
import os
import re
from datetime import date
from urllib.request import Request, urlopen
from urllib.error import HTTPError

def claim_slot(slot_uk: str, *, token: str, repository: str, sha: str, post=None) -> dict:
    scheduled = date.fromisoformat(slot_uk[:10])
    if not slot_uk.startswith(scheduled.isoformat() + "T07:35:00"):
        raise ValueError("Only the approved 07:35 UK scheduled slot can be claimed")
    if scheduled.weekday() not in (1, 4):
        raise ValueError("Slot is not Tuesday or Friday")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository or ""):
        raise ValueError("Invalid GitHub repository")
    if not re.fullmatch(r"[0-9a-fA-F]{40}", sha or "") or not token:
        raise ValueError("GitHub claim credentials missing")
    ref = "refs/heads/ba-acquisition-slot-" + scheduled.strftime("%Y%m%d")
    url = "https://api.github.com/repos/" + repository + "/git/refs"
    payload = {"ref": ref, "sha": sha}

    def github_post():
        request = Request(url, data=json.dumps(payload).encode("utf8"), method="POST",
            headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
                     "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=25) as response:
                return response.status
        except HTTPError as e:
            if e.code in (409, 422):
                return e.code
            raise RuntimeError("Could not verify unique GitHub slot claim") from None

    status = github_post() if post is None else post(url, payload)
    if status == 201:
        return {"claimed": True, "ref": ref, "status": "SLOT_CLAIMED"}
    if status in (409, 422):
        # A conflict could also arise from a malformed request, so never spend.
        return {"claimed": False, "ref": ref, "status": "SLOT_ALREADY_CLAIMED_OR_CONFLICT"}
    raise RuntimeError("GitHub slot claim was not independently confirmed")

def claim_from_environment(slot: dict) -> dict:
    if not slot.get("due") or not isinstance(slot.get("scheduled_uk"), str):
        raise ValueError("A verified UK schedule is required")
    if os.getenv("GITHUB_EVENT_NAME") != "schedule" or os.getenv("GITHUB_RUN_ATTEMPT") != "1":
        raise ValueError("Only first scheduled GitHub attempt may claim slot")
    return claim_slot(slot["scheduled_uk"], token=os.getenv("GITHUB_TOKEN", ""),
                      repository=os.getenv("GITHUB_REPOSITORY", ""), sha=os.getenv("GITHUB_SHA", ""))
