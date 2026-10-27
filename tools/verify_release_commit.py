#!/usr/bin/env python3
"""Verify contained source provenance; this does not authorize a release tag."""

from __future__ import annotations

import argparse
import http.client
import base64
import binascii
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FULL_COMMIT = re.compile(r"^[0-9a-f]{40}$")
REPOSITORY = "relux-works/curator-spec"
DEFAULT_BRANCH = "main"
API_URL = "https://api.github.com"
SOURCE_ENTRY = re.compile(r'source-commit namespaces="git" ssh-ed25519 ([A-Za-z0-9+/]+={0,2})')


class VerificationFailure(RuntimeError):
    pass


def git(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env={
            **{key: value for key, value in os.environ.items()
               if not key.startswith(("GIT_", "XDG_"))
               and key not in {"SSH_AUTH_SOCK", "SSH_ASKPASS"}},
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_NO_REPLACE_OBJECTS": "1",
        },
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise VerificationFailure(f"git {' '.join(arguments)} failed: {detail}")
    return result


def resolve_commit(value: str) -> str:
    commit = git("rev-parse", "--verify", "--end-of-options", f"{value}^{{commit}}").stdout.strip()
    if FULL_COMMIT.fullmatch(commit) is None:
        raise VerificationFailure("release target did not resolve to a full commit")
    return commit


def require_repository_context() -> None:
    # These are policy roots, not caller-selected verification overrides.
    for name, expected in (("GITHUB_REPOSITORY", REPOSITORY),
                           ("GITHUB_DEFAULT_BRANCH", DEFAULT_BRANCH),
                           ("GITHUB_API_URL", API_URL)):
        if name in os.environ and os.environ[name] != expected:
            raise VerificationFailure(f"{name} does not match repository policy")


def commit_signature_kind(commit: str) -> str:
    headers = git("cat-file", "commit", commit).stdout.split("\n\n", 1)[0]
    signatures = re.findall(r"^gpgsig (.+)$", headers, re.MULTILINE)
    if signatures == ["-----BEGIN SSH SIGNATURE-----"]:
        return "ssh"
    if signatures == ["-----BEGIN PGP SIGNATURE-----"]:
        return "github"
    raise VerificationFailure("source target lacks supported signed material")


def trusted_signature_valid(commit: str) -> bool:
    # Both inputs are fixed repository policy. Only the release input is used
    # by verify-tag; adding a source signer does not add tag authority.
    paths = [ROOT / "maintainers.allowed_signers", ROOT / "source.allowed_signers"]
    try:
        for path in paths:
            if path.is_symlink() or not path.is_file() or not path.read_bytes().strip():
                raise VerificationFailure(f"invalid trust input: {path.name}")
        entries = [line for line in paths[1].read_text(encoding="utf-8").splitlines()
                   if line and not line.startswith("#")]
        match = SOURCE_ENTRY.fullmatch(entries[0]) if len(entries) == 1 else None
        if match is None:
            raise VerificationFailure("source trust must contain one commit-only SSH entry")
        blob = base64.b64decode(match.group(1), validate=True)
        prefix = b"\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20"
        if len(blob) != len(prefix) + 32 or not blob.startswith(prefix):
            raise VerificationFailure("source trust has an invalid Ed25519 key")
    except (OSError, UnicodeError, binascii.Error) as exc:
        raise VerificationFailure("could not read source trust inputs") from exc
    return any(git("-c", "gpg.format=ssh", "-c", "gpg.ssh.program=ssh-keygen",
                   "-c", f"gpg.ssh.allowedSignersFile={path}",
                   "verify-commit", commit, check=False).returncode == 0 for path in paths)


def require_default_branch_ancestor(commit: str) -> None:
    remote_ref = f"refs/remotes/origin/{DEFAULT_BRANCH}"
    git("show-ref", "--verify", remote_ref)
    result = git("merge-base", "--is-ancestor", commit, remote_ref, check=False)
    if result.returncode != 0:
        raise VerificationFailure(f"release target is not contained in origin/{DEFAULT_BRANCH}")


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
    if any(not isinstance(verification.get(key), str) or not verification[key].strip()
           for key in ("signature", "payload")):
        raise VerificationFailure("GitHub commit verification lacks signed material")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request: Any, fp: Any, code: int, message: str,
                         headers: Any, new_url: str) -> None:
        # Never send the bearer token to a redirect-selected authority.
        return None


def fetch_github_payload(commit: str, token: str) -> Any:
    if not token:
        raise VerificationFailure("GITHUB_TOKEN is required for GitHub commit verification")
    request = urllib.request.Request(
        f"{API_URL}/repos/{REPOSITORY}/commits/{commit}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "curator-spec-release-verifier",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=30) as response:
            return json.load(response)
    except (OSError, urllib.error.URLError, http.client.HTTPException, ValueError):
        # HTTP errors may contain Authorization values. Discard the raw error
        # and raise outside its handler so even chained tracebacks stay safe.
        pass
    raise VerificationFailure("could not read GitHub commit verification")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", default="HEAD")
    arguments = parser.parse_args()
    try:
        require_repository_context()
        commit = resolve_commit(arguments.commit)
        require_default_branch_ancestor(commit)
        if commit_signature_kind(commit) == "ssh":
            if not trusted_signature_valid(commit):
                raise VerificationFailure("source target has no authorized SSH signature")
            print(f"source target {commit} has an authorized signature on origin/{DEFAULT_BRANCH}")
            return 0
        payload = fetch_github_payload(commit, os.environ.get("GITHUB_TOKEN", ""))
        validate_github_payload(payload, commit)
    except VerificationFailure as exc:
        print(f"release commit verification failed: {exc}", file=sys.stderr)
        return 1
    print(f"release target {commit} is a GitHub-verified commit on origin/{DEFAULT_BRANCH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
