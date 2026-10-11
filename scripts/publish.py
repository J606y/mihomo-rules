#!/usr/bin/env python3
"""Build Mihomo providers and publish changed files to the public GitHub repository."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OWNER, REPO, BRANCH = "J606y", "mihomo-rules", "main"
API = f"https://api.github.com/repos/{OWNER}/{REPO}"


def token_value() -> str:
    token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
    if token:
        return token
    env_file = Path("/root/.hermes/.env")
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("GITHUB_PERSONAL_ACCESS_TOKEN="):
                return line.split("=", 1)[1].strip().strip("\"'")
    raise RuntimeError("GITHUB_PERSONAL_ACCESS_TOKEN is unavailable")


def request(url: str, token: str, method: str = "GET", data: dict | None = None) -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "hermes-mihomo-rules-sync",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read(2048).decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API HTTP {exc.code}: {detail}") from None


def publish() -> str:
    token = token_value()
    ref_url = f"{API}/git/refs/heads/{BRANCH}"
    parent_sha = request(ref_url, token)["object"]["sha"]
    commit = request(f"{API}/git/commits/{parent_sha}", token)
    files = [ROOT / "README.md", ROOT / "scripts/build_rules.py", ROOT / "scripts/publish.py", ROOT / "tests/test_build_rules.py"]
    files.extend(sorted((ROOT / "rules").glob("*.yaml")))
    if len(list((ROOT / "rules").glob("*.yaml"))) != 25:
        raise RuntimeError("expected exactly 25 generated providers")
    tree = [{
        "path": path.relative_to(ROOT).as_posix(),
        "mode": "100644",
        "type": "blob",
        "content": path.read_text(encoding="utf-8"),
    } for path in files]
    new_tree = request(f"{API}/git/trees", token, "POST", {
        "base_tree": commit["tree"]["sha"], "tree": tree,
    })
    new_commit = request(f"{API}/git/commits", token, "POST", {
        "message": "feat: publish Mihomo classical rule providers",
        "tree": new_tree["sha"], "parents": [parent_sha],
    })
    request(ref_url, token, "PATCH", {"sha": new_commit["sha"]})
    return new_commit["sha"]


if __name__ == "__main__":
    try:
        print(publish())
    except Exception as exc:
        print(f"publish failed: {exc}", file=sys.stderr)
        sys.exit(1)
