from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen

from scripts.state_snapshot import MANIFEST_RELATIVE, safe_extract, verify_manifest


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "salesforce-tracker-state-restore",
    }


def fetch_json(url: str, token: str) -> Any:
    request = Request(url, headers=_headers(token))
    with urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def select_latest_artifact(payload: dict[str, Any], artifact_name: str, branch: str) -> dict[str, Any] | None:
    candidates = [
        item
        for item in payload.get("artifacts", [])
        if item.get("name") == artifact_name
        and not item.get("expired")
        and (item.get("workflow_run") or {}).get("head_branch") == branch
    ]
    candidates.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return candidates[0] if candidates else None


def download_artifact(api_url: str, repository: str, artifact_id: int, token: str, output: Path) -> None:
    url = f"{api_url}/repos/{repository}/actions/artifacts/{artifact_id}/zip"
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "curl",
        "--fail",
        "--silent",
        "--show-error",
        "--location",
        "-H", f"Authorization: Bearer {token}",
        "-H", "Accept: application/vnd.github+json",
        "-H", "X-GitHub-Api-Version: 2022-11-28",
        url,
        "-o", str(output),
    ]
    subprocess.run(command, check=True)


def restore_latest(
    *,
    root: Path,
    api_url: str,
    repository: str,
    token: str,
    artifact_name: str,
    branch: str,
) -> dict[str, Any]:
    endpoint = (
        f"{api_url}/repos/{repository}/actions/artifacts"
        f"?name={quote(artifact_name)}&per_page=100"
    )
    payload = fetch_json(endpoint, token)
    artifact = select_latest_artifact(payload, artifact_name, branch)
    if artifact is None:
        return {
            "restored": False,
            "artifact_name": artifact_name,
            "branch": branch,
            "reason": "no non-expired matching state artifact exists",
        }

    with tempfile.TemporaryDirectory(prefix="tracker-state-") as temp_dir:
        archive = Path(temp_dir) / "tracker-state.zip"
        download_artifact(api_url, repository, int(artifact["id"]), token, archive)
        extracted = safe_extract(archive, root)

    verification = verify_manifest(root, root / MANIFEST_RELATIVE)
    return {
        "restored": True,
        "artifact_id": artifact["id"],
        "artifact_name": artifact_name,
        "artifact_created_at": artifact.get("created_at"),
        "branch": branch,
        "restored_files": extracted,
        "verification": verification,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore the latest verified tracker-state GitHub artifact")
    parser.add_argument("--root", default=".")
    parser.add_argument("--artifact-name", default="tracker-state")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--api-url", default=os.environ.get("GITHUB_API_URL", "https://api.github.com"))
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY"))
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN is required", file=sys.stderr)
        return 2
    if not args.repository:
        print("GITHUB_REPOSITORY is required", file=sys.stderr)
        return 2

    try:
        result = restore_latest(
            root=Path(args.root).resolve(),
            api_url=args.api_url.rstrip("/"),
            repository=args.repository,
            token=token,
            artifact_name=args.artifact_name,
            branch=args.branch,
        )
    except Exception as exc:
        print(json.dumps({"restored": False, "error": str(exc)}, indent=2), file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
