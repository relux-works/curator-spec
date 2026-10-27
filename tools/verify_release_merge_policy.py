#!/usr/bin/env python3
"""Verify that repository merge settings preserve release-target provenance."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

from verify_release_commit import (
    API_URL, REPOSITORY, NoRedirect, VerificationFailure, require_repository_context,
)


class PolicyFailure(RuntimeError):
    pass


def validate_repository_payload(payload: Any, expected_repository: str) -> None:
    if not isinstance(payload, dict) or payload.get("full_name") != expected_repository:
        raise PolicyFailure("GitHub returned different repository settings")
    if payload.get("allow_squash_merge") is not True:
        raise PolicyFailure("squash merging must be enabled for GitHub-verified release targets")
    if payload.get("allow_rebase_merge") is not False:
        raise PolicyFailure("rebase merging must be disabled because GitHub rewrites commits unsigned")
    if payload.get("allow_merge_commit") is not False:
        raise PolicyFailure("merge commits must remain disabled by repository policy")


def fetch_repository_payload(token: str) -> Any:
    if not token:
        raise PolicyFailure("GITHUB_TOKEN is required for repository policy verification")
    request = urllib.request.Request(
        f"{API_URL}/repos/{REPOSITORY}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "curator-spec-release-policy-verifier",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=30) as response:
            return json.load(response)
    except (OSError, urllib.error.URLError, ValueError) as exc:
        raise PolicyFailure(f"could not read GitHub repository settings: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    try:
        require_repository_context()
        payload = fetch_repository_payload(os.environ.get("GITHUB_TOKEN", ""))
        validate_repository_payload(payload, REPOSITORY)
    except (PolicyFailure, VerificationFailure) as exc:
        print(f"release merge policy verification failed: {exc}", file=sys.stderr)
        return 1
    print(f"repository {REPOSITORY} preserves the GitHub-verified squash fallback")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
