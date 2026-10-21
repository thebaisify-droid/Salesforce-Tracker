"""Identify a previous verified GitHub Actions ledger artifact using GET only.

A previous successful run of the SAME workflow and branch is required.
Never fall back to a failed, expired or unverified checkpoint.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
from urllib.request import Request, urlopen

NAME = "joint-acquisition-verified-ledger"
WORKFLOW_PATH = ".github/workflows/shared-acquisition-audit.yml"
REPO_PATTERN = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")


def choose(listing, *, get_run, branch, current_run_id, now=None):
    if (not isinstance(listing, dict)
            or not isinstance(listing.get("artifacts"), list)
            or type(listing.get("total_count")) is not int):
        raise ValueError("Untrustworthy GitHub artifact listing")
    if listing["total_count"] > len(listing["artifacts"]):
        raise ValueError("Artifact listing truncated; cannot select prior checkpoint")
    now = now or datetime.now(timezone.utc)
    candidates = []
    for artifact in listing["artifacts"]:
        if not isinstance(artifact, dict) or artifact.get("name") != NAME:
            continue
        run = artifact.get("workflow_run") or {}
        if (type(artifact.get("id")) is not int or type(run.get("id")) is not int
                or run["id"] == current_run_id or run.get("head_branch") != branch):
            continue
        try:
            created = datetime.fromisoformat(artifact["created_at"].replace("Z", "+00:00"))
        except (ValueError, KeyError, TypeError, AttributeError):
            raise ValueError("Malformed checkpoint timestamp") from None
        if created.tzinfo is None or created > now:
            raise ValueError("Future or timezone-free checkpoint")
        candidates.append((created, artifact))
    if not candidates:
        return {"found": False, "reason": "NO_VERIFIED_PREVIOUS_CHECKPOINT"}
    created, selected = max(candidates, key=lambda x: (x[0], x[1]["id"]))
    if selected.get("expired") is not False or now - created > timedelta(days=30):
        raise ValueError("Latest checkpoint expired; abort reuse")
    parent = get_run(selected["workflow_run"]["id"])
    if (not isinstance(parent, dict)
            or parent.get("id") != selected["workflow_run"]["id"]
            or parent.get("status") != "completed"
            or parent.get("conclusion") != "success"
            or parent.get("head_branch") != branch
            or (parent.get("path") or "").split("@", 1)[0] != WORKFLOW_PATH):
        raise ValueError("Latest checkpoint not from successful same-workflow run")
    return {"found": True, "run_id": parent["id"],
            "artifact_id": selected["id"], "created_at": selected["created_at"]}


def github_get(repo, token, suffix):
    if (not REPO_PATTERN.fullmatch(repo) or not token or
            not (suffix.startswith("/actions/artifacts?name=") or
                 re.fullmatch(r"/actions/runs/[0-9]{1,18}", suffix))):
        raise ValueError("Only authenticated read-only GitHub Actions metadata is supported")
    req = Request("https://api.github.com/repos/" + repo + suffix, method="GET",
                  headers={"Authorization": "Bearer " + token,
                           "Accept": "application/vnd.github+json",
                           "X-GitHub-Api-Version": "2022-11-28"})
    with urlopen(req, timeout=30) as response:
        data = json.load(response)
    if not isinstance(data, dict):
        raise ValueError("Malformed GitHub metadata")
    return data


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--allow-empty-shadow-bootstrap", action="store_true")
    args = p.parse_args()
    repo, token = os.getenv("GITHUB_REPOSITORY", ""), os.getenv("GITHUB_TOKEN", "")
    run_id = int(os.getenv("GITHUB_RUN_ID", "0"))
    branch = os.getenv("GITHUB_REF_NAME", "")
    if run_id <= 0 or not branch:
        raise SystemExit("GitHub run identity missing")
    listing = github_get(repo, token, "/actions/artifacts?name=" + NAME + "&per_page=100")
    selection = choose(listing, get_run=lambda rid: github_get(
        repo, token, "/actions/runs/" + str(rid)), branch=branch,
        current_run_id=run_id)
    if not selection["found"] and not (
        args.allow_empty_shadow_bootstrap
        and os.getenv("GITHUB_EVENT_NAME") == "workflow_dispatch"
        and os.getenv("SHARED_PAID_ACQUISITION_ENABLED") == "false"
    ):
        raise SystemExit("No trustworthy prior checkpoint; block paid execution")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(selection, indent=2) + "\n")
    if os.getenv("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
            out.write("found=" + str(selection["found"]).lower() + "\n")
            out.write("run_id=" + str(selection.get("run_id", "")) + "\n")
    print(json.dumps(selection))


if __name__ == "__main__":
    main()
