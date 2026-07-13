#!/usr/bin/env python3
"""Verify that a release target has trusted commit provenance."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FULL_COMMIT = re.compile(r"^[0-9a-f]{40}$")
REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
BRANCH = re.compile(r"^[A-Za-z0-9._/-]+$")


class VerificationFailure(RuntimeError):
    pass


def git(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise VerificationFailure(f"git {' '.join(arguments)} failed: {detail}")
    return result


def resolve_commit(value: str) -> str:
    commit = git("rev-parse", f"{value}^{{commit}}").stdout.strip()
    if FULL_COMMIT.fullmatch(commit) is None:
        raise VerificationFailure("release target did not resolve to a full commit")
    return commit


def maintainer_signature_valid(commit: str) -> bool:
    return git("verify-commit", commit, check=False).returncode == 0


def require_default_branch_ancestor(commit: str, default_branch: str) -> None:
    if BRANCH.fullmatch(default_branch) is None or default_branch.startswith(("/", "-")) or ".." in default_branch:
        raise VerificationFailure("default branch name is not portable")
    remote_ref = f"refs/remotes/origin/{default_branch}"
    git("show-ref", "--verify", remote_ref)
    result = git("merge-base", "--is-ancestor", commit, remote_ref, check=False)
    if result.returncode != 0:
        raise VerificationFailure(f"release target is not contained in origin/{default_branch}")


def validate_github_payload(payload: Any, expected_commit: str) -> None:
    if not isinstance(payload, dict) or payload.get("sha") != expected_commit:
        raise VerificationFailure("GitHub returned a different release target")
    commit = payload.get("commit")
    if not isinstance(commit, dict):
        raise VerificationFailure("GitHub commit metadata is missing")
    committer = commit.get("committer")
    if not isinstance(committer, dict) or committer.get("name") != "GitHub" or committer.get("email") != "noreply@github.com":
        raise VerificationFailure("release target is not a GitHub-created merge commit")
    verification = commit.get("verification")
    if not isinstance(verification, dict):
        raise VerificationFailure("GitHub commit verification is missing")
    if verification.get("verified") is not True or verification.get("reason") != "valid":
        raise VerificationFailure("GitHub did not validate the release target signature")
    if not verification.get("signature") or not verification.get("payload"):
        raise VerificationFailure("GitHub commit verification lacks signed material")


def fetch_github_payload(repository: str, commit: str, token: str, api_url: str) -> Any:
    if REPOSITORY.fullmatch(repository) is None:
        raise VerificationFailure("GITHUB_REPOSITORY is invalid")
    if not token:
        raise VerificationFailure("GITHUB_TOKEN is required for GitHub commit verification")
    owner, name = repository.split("/", 1)
    path = "/repos/{}/{}/commits/{}".format(
        urllib.parse.quote(owner, safe=""),
        urllib.parse.quote(name, safe=""),
        commit,
    )
    request = urllib.request.Request(
        api_url.rstrip("/") + path,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "curator-spec-release-verifier",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise VerificationFailure(f"could not read GitHub commit verification: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", default="HEAD")
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--default-branch", default=os.environ.get("GITHUB_DEFAULT_BRANCH", "main"))
    parser.add_argument("--api-url", default=os.environ.get("GITHUB_API_URL", "https://api.github.com"))
    arguments = parser.parse_args()
    try:
        commit = resolve_commit(arguments.commit)
        if maintainer_signature_valid(commit):
            print(f"release target {commit} has a trusted maintainer signature")
            return 0
        require_default_branch_ancestor(commit, arguments.default_branch)
        payload = fetch_github_payload(
            arguments.repository,
            commit,
            os.environ.get("GITHUB_TOKEN", ""),
            arguments.api_url,
        )
        validate_github_payload(payload, commit)
    except VerificationFailure as exc:
        print(f"release commit verification failed: {exc}", file=sys.stderr)
        return 1
    print(f"release target {commit} is a GitHub-verified commit on origin/{arguments.default_branch}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
