#!/usr/bin/env python3
"""Verify version, independent review, and stable promotion invariants."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
FULL_COMMIT = re.compile(r"^[0-9a-f]{40}$")
SEMVER = re.compile(
    r"^(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
# The only execution policy protocol 1.0 defines. A candidate that names any
# other portable policy, or that claims the deferred hardened profile, is not
# releasable.
PORTABLE_EXECUTION_POLICY = "manager-worker-v1"
# The exhaustive native-control inventory and closed capability-evidence record
# a portable candidate reports. They are versioned separately from the policy
# because neither enters a build input or a hashed identity.
NATIVE_CONTROL_INVENTORY_VERSION = "rc5-native-control-inventory-v1"
CAPABILITY_EVIDENCE_RECORD_VERSION = "capability-evidence-v1"
# The one manager-neutral repository-root build descriptor. Its retired
# implementation-branded name is not an alias, so no release surface may carry
# it. The stem is assembled from parts so this gate can scan its own source.
REPOSITORY_DESCRIPTOR_SCHEMA = "skill-build-v1.schema.json"
RETIRED_DESCRIPTOR_STEM = "curator" + "-build"
# The schema-6 build-source digest algorithm namespace shares the retired stem
# but is a different, byte-frozen identifier.
BUILD_SOURCE_ALGORITHM_NAMESPACE = RETIRED_DESCRIPTOR_STEM + "-source"


class ReleaseFailure(RuntimeError):
    pass


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReleaseFailure(f"could not read {path.relative_to(ROOT)}: {exc}") from exc


def git(*arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise ReleaseFailure(f"git {' '.join(arguments)} failed: {detail}")
    return result.stdout.strip()


def validate_version(version: str) -> None:
    if SEMVER.fullmatch(version) is None:
        raise ReleaseFailure(f"{version!r} is not a supported semantic version")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    if f"**Version:** {version}" not in readme:
        raise ReleaseFailure(f"README version is not {version}")
    manifest = load_json(ROOT / "conformance" / "v1" / "manifest.json")
    if manifest.get("protocol_version") != version:
        raise ReleaseFailure(f"conformance manifest version is not {version}")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if not re.search(rf"^## {re.escape(version)}(?: - [0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}})?$", changelog, re.MULTILINE):
        raise ReleaseFailure(f"CHANGELOG has no {version} release heading")
    if "-" in version:
        metadata_path = ROOT / "release" / f"{version}.json"
        metadata = load_json(metadata_path)
        if metadata.get("protocol_version") != version:
            raise ReleaseFailure(f"{metadata_path.relative_to(ROOT)} identifies the wrong protocol version")
        expected = "sha256:" + hashlib.sha256(
            (ROOT / "conformance" / "v1" / "manifest.json").read_bytes()
        ).hexdigest()
        pin = metadata.get("candidate_protocol_pin", {})
        downstream = metadata.get("downstream_consumption", {})
        if (
            not isinstance(pin, dict)
            or pin.get("manifest_sha256") != expected
            or not isinstance(downstream, dict)
            or downstream.get("required_manifest_sha256") != expected
        ):
            raise ReleaseFailure(f"{metadata_path.relative_to(ROOT)} does not pin the exact suite manifest")
        execution = metadata.get("execution_policy", {})
        if (
            not isinstance(execution, dict)
            or execution.get("portable") != PORTABLE_EXECUTION_POLICY
            or execution.get("hardened_profile_claimed") is not False
            or not execution.get("hardened_profile_owner")
            or execution.get("native_control_inventory_version")
            != NATIVE_CONTROL_INVENTORY_VERSION
            or execution.get("capability_evidence_record_version")
            != CAPABILITY_EVIDENCE_RECORD_VERSION
        ):
            raise ReleaseFailure(
                f"{metadata_path.relative_to(ROOT)} does not honestly record its execution policy"
            )


def names_retired_descriptor(text: str) -> bool:
    offset = 0
    while True:
        hit = text.find(RETIRED_DESCRIPTOR_STEM, offset)
        if hit < 0:
            return False
        if not text.startswith(BUILD_SOURCE_ALGORITHM_NAMESPACE, hit):
            return True
        offset = hit + 1


def validate_repository_descriptor(version: str) -> None:
    """The released schema set and release surfaces name one descriptor only."""
    schemas = ROOT / "schemas" / "v1"
    if not (schemas / REPOSITORY_DESCRIPTOR_SCHEMA).is_file():
        raise ReleaseFailure(f"release is missing {REPOSITORY_DESCRIPTOR_SCHEMA}")
    surfaces = [
        *sorted(schemas.glob("*.json")),
        ROOT / "conformance" / "v1" / "manifest.json",
        ROOT / "CHANGELOG.md",
        ROOT / "COMPATIBILITY.md",
    ]
    if "-" in version:
        surfaces.append(ROOT / "release" / f"{version}.json")
    for path in surfaces:
        if not path.is_file():
            continue
        if names_retired_descriptor(path.read_text(encoding="utf-8")):
            raise ReleaseFailure(
                f"{path.relative_to(ROOT)} names the retired repository descriptor, which is not an alias"
            )


def validate_reviews(version: str, release_commit: str) -> None:
    schema = load_json(ROOT / "reviews" / "review-report-v2.schema.json")
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    review_root = ROOT / "reviews" / version
    reviewed_types: set[str] = set()
    reviewer_contacts: dict[str, str] = {}
    for expected_type in ("security", "interoperability"):
        path = review_root / f"{expected_type}.json"
        if not path.is_file():
            raise ReleaseFailure(f"stable release requires {path.relative_to(ROOT)}")
        report = load_json(path)
        errors = sorted(validator.iter_errors(report), key=lambda item: list(item.absolute_path))
        if errors:
            raise ReleaseFailure(f"{path.relative_to(ROOT)}: {errors[0].message}")
        if report["protocol_version"] != version or report["review_type"] != expected_type:
            raise ReleaseFailure(f"{path.relative_to(ROOT)} identifies the wrong release or review type")
        if report["conclusion"] != "pass":
            raise ReleaseFailure(f"{path.relative_to(ROOT)} conclusion is not pass")
        reviewer_contact = report["reviewer"]["contact"].strip().casefold()
        previous_type = reviewer_contacts.get(reviewer_contact)
        if previous_type is not None:
            raise ReleaseFailure(
                f"{path.relative_to(ROOT)} repeats the {previous_type} reviewer; "
                "stable security and interoperability reviews require different reviewer contacts"
            )
        reviewer_contacts[reviewer_contact] = expected_type
        blocking = [
            finding["id"]
            for finding in report["findings"]
            if finding["severity"] in {"critical", "high"} and finding["status"] == "open"
        ]
        if blocking:
            raise ReleaseFailure(f"{path.relative_to(ROOT)} has open blocking findings: {blocking}")
        reviewed_commit = report["reviewed_commit"]
        if not FULL_COMMIT.fullmatch(reviewed_commit):
            raise ReleaseFailure(f"{path.relative_to(ROOT)} has an invalid reviewed commit")
        git("merge-base", "--is-ancestor", reviewed_commit, release_commit)
        changed = git("diff", "--name-only", f"{reviewed_commit}..{release_commit}").splitlines()
        outside_reviews = [name for name in changed if name and not name.startswith("reviews/")]
        if outside_reviews:
            raise ReleaseFailure(
                f"normative files changed after {expected_type} review: {outside_reviews}"
            )
        reviewed_types.add(report["review_type"])
    if reviewed_types != {"security", "interoperability"}:
        raise ReleaseFailure("stable release lacks both independent review types")


def validate_checkout(release_commit: str) -> None:
    if release_commit != git("rev-parse", "HEAD"):
        raise ReleaseFailure("release gate must run from the candidate commit checkout")
    if git("status", "--porcelain"):
        raise ReleaseFailure("release gate requires a clean candidate checkout")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--commit", default="HEAD")
    arguments = parser.parse_args()
    try:
        release_commit = git("rev-parse", f"{arguments.commit}^{{commit}}")
        validate_checkout(release_commit)
        validate_version(arguments.version)
        validate_repository_descriptor(arguments.version)
        if "-" not in arguments.version:
            validate_reviews(arguments.version, release_commit)
    except ReleaseFailure as exc:
        print(f"release gate failed: {exc}")
        return 1
    print(f"release gate passed for {arguments.version} at {release_commit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
