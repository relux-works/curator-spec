#!/usr/bin/env python3
"""Verify that repository merge settings preserve release-target provenance."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


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


def fetch_repository_payload(repository: str, token: str, api_url: str) -> Any:
    if REPOSITORY.fullmatch(repository) is None:
        raise PolicyFailure("GITHUB_REPOSITORY is invalid")
    if not token:
        raise PolicyFailure("GITHUB_TOKEN is required for repository policy verification")
    owner, name = repository.split("/", 1)
    path = "/repos/{}/{}".format(
        urllib.parse.quote(owner, safe=""),
        urllib.parse.quote(name, safe=""),
    )
    request = urllib.request.Request(
        api_url.rstrip("/") + path,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "curator-spec-release-policy-verifier",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise PolicyFailure(f"could not read GitHub repository settings: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--api-url", default=os.environ.get("GITHUB_API_URL", "https://api.github.com"))
    arguments = parser.parse_args()
    try:
        payload = fetch_repository_payload(
            arguments.repository,
            os.environ.get("GITHUB_TOKEN", ""),
            arguments.api_url,
        )
        validate_repository_payload(payload, arguments.repository)
    except PolicyFailure as exc:
        print(f"release merge policy verification failed: {exc}", file=sys.stderr)
        return 1
    print(f"repository {arguments.repository} permits only GitHub-verified squash release targets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
