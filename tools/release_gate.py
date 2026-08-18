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

import assurance
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


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
PROTOCOL_VERSION = "1.0.0-rc.7"
RC6_PROTOCOL_VERSION = "1.0.0-rc.6"
RC5_PROTOCOL_VERSION = "1.0.0-rc.5"
RC5_RELEASE_METADATA_SHA256 = (
    "sha256:75ae17fc029b4f51ca40ce768d04fd72991ec3db2602b8fe59213bee6ac34583"
)
RC5_PUBLISHED_COMMIT = "f5d7673039226ab81de2f4f87e2155ae995c4df3"
RC6_RELEASE_METADATA_SHA256 = (
    "sha256:c4ad58e76687bd563679773a60c6ce35c238d4117b7cbceb05d4f88b5300ed3f"
)
RC6_SOURCE_COMMIT = "dce6643c55434464c56f0fe20064db754cd58c61"
CLAIM_PROTOCOL_VERSIONS = {
    1: "1.0.0-rc.3",
    2: "1.0.0-rc.4",
    3: RC5_PROTOCOL_VERSION,
    4: PROTOCOL_VERSION,
}
CLAIM_HISTORY_FROZEN_SHA256 = {
    "schemas/v1/conformance-claim-v1.schema.json": "c9f49460618ccc8b1d7d2dfaf760fc6ad3a53a870a6685a685ddc148d3c87b3f",
    "conformance/v1/schema-cases/conformance-claim-v1/valid.json": "799682489be118331135d91798db90b8d020cbb703207331824ab113f037693c",
    "conformance/v1/schema-cases/conformance-claim-v1/invalid.json": "de9568757a2bb89c87702e47f6d9c162df24f5ee964f1ef49b9e191ed94b7017",
    "schemas/v1/conformance-claim-v2.schema.json": "4c05a97a1aa9f7dafe629a406a853239928413e79e95488ac2b20ebd0c52a38c",
    "conformance/v1/schema-cases/conformance-claim-v2/invalid-duplicate-classes.json": "2d74783021873fb41b0176205835624e56db4fa7fb3c0435c8dbcd0e05b58fc0",
    "conformance/v1/schema-cases/conformance-claim-v2/invalid-protocol-version-rc3.json": "5558db5556576993d4abe93c0f4849380591f71c25173a77f2493448fbe11eef",
    "conformance/v1/schema-cases/conformance-claim-v2/invalid-result-fail.json": "eeeecc9577f418b78a9a5edbaea9d6294d30f1d06886d6af9f56e64e271d8268",
    "conformance/v1/schema-cases/conformance-claim-v2/invalid-schema-version-1.json": "aa5588297fb49d39eb39ca3052f6f97bb67236608b72cc9d0478b043cce6562f",
    "conformance/v1/schema-cases/conformance-claim-v2/invalid-unknown-field.json": "d10459fefb4b07aa1ade03a0627fbcfe9cd790c99d5d6374c9de15c5f22dc9a3",
    "conformance/v1/schema-cases/conformance-claim-v2/invalid.json": "79d244335cb2ddfb9c831aa38c31c6ca37c89f0704ad61a19032882b1bec8604",
    "conformance/v1/schema-cases/conformance-claim-v2/valid.json": "f7e7cc86f33ea03ee9bb4d149e1dba29cf34f5ceaf5504df8a9e91c659a1835f",
}
RC7_REQUIRED_FILES = {
    "decisions/0004-compile-only-build-drivers.md",
    "schemas/v1/agent-skill-v6.schema.json",
    "schemas/v1/csk-skill-v6.schema.json",
    "schemas/v1/build-receipt-v1.schema.json",
    "schemas/v1/install-marker-v2.schema.json",
    "schemas/v1/conformance-claim-v1.schema.json",
    "schemas/v1/conformance-claim-v2.schema.json",
    "schemas/v1/conformance-claim-v3.schema.json",
    "conformance/v1/schema-cases/index.json",
    "conformance/v1/expected/marker.json",
    "conformance/v1/expected/marker-v2.json",
    "conformance/v1/vectors/build-drivers.json",
    "conformance/v1/vectors/manager-lifecycle.json",
    "release/1.0.0-rc.5.json",
    "release/1.0.0-rc.6.json",
    "release/1.0.0-rc.7.json",
    "decisions/0007-portable-and-verified-assurance.md",
    "protocol/assurance.md",
    "docs/assurance-modes.md",
    "schemas/v1/assurance-policy-v1.schema.json",
    "schemas/v1/verified-provider-v1.schema.json",
    "schemas/v1/provider-capability-receipt-v1.schema.json",
    "schemas/v1/execution-permit-v1.schema.json",
    "schemas/v1/execution-receipt-v1.schema.json",
    "schemas/v1/execution-checkpoint-v1.schema.json",
    "schemas/v1/conformance-claim-v4.schema.json",
    "conformance/v1/vectors/assurance-modes.json",
}
RC7_REQUIRED_MANIFEST_FILES = {
    "schema-cases/index.json",
    "expected/marker.json",
    "expected/marker-v2.json",
    "vectors/build-drivers.json",
    "vectors/manager-lifecycle.json",
    "vectors/assurance-modes.json",
}
# The published marker-v1 legacy-read evidence. Its bytes are release history,
# so the writer golden a candidate publishes for the same golden skill is a
# separate file rather than an edit to this one.
FROZEN_MARKER_V1_SHA256 = (
    "sha256:80989f850887814ec09c724a7dd891ac7e2422d5fef7e31f330be3554aa9b28a"
)
# Managers write marker schema 2 for schema 1 through 6 mutations, and the
# schema-5 golden skill activates no compiled command, so the writer golden
# restates the legacy marker with exactly these members changed.
SHARED_FIXTURE_MARKER_V2_DELTA = frozenset({"schema_version", "build_roots", "builds"})
RC7_REQUIRED_INDEXED_SCHEMAS = {
    "agent-skill-v6.schema.json",
    "csk-skill-v6.schema.json",
    "build-receipt-v1.schema.json",
    "install-marker-v2.schema.json",
    "conformance-claim-v2.schema.json",
    "conformance-claim-v3.schema.json",
    "assurance-policy-v1.schema.json",
    "verified-provider-v1.schema.json",
    "provider-capability-receipt-v1.schema.json",
    "execution-permit-v1.schema.json",
    "execution-receipt-v1.schema.json",
    "execution-checkpoint-v1.schema.json",
    "conformance-claim-v4.schema.json",
}
RC6_MANAGER_DRY_RUN_CASES = {"compiled-cache-miss-is-read-only"}
RC6_MANAGER_LIFECYCLE_CASES = {
    "planning_cases": {"all-source-and-trust-gates-before-build"},
    "build_order_cases": {"provider-first-and-lexical-command-order"},
    "private_build_cases": {
        "all-misses-stage-and-verify-before-home-lock",
        "second-build-failure-preserves-persistent-state",
    },
    "cache_publication_cases": {
        "publish-complete-immutable-entry-under-home-lock",
        "concurrent-identical-winner",
        "concurrent-determinism-mismatch",
        "corrupt-live-entry",
        "untrusted-cache-boundary",
    },
    "cross_project_cases": {
        "two-project-success-preserves-both-consumers",
        "successful-project-survives-other-project-rollback",
    },
    "transaction_cases": {
        "deterministic-lock-order",
        "deterministic-target-order-and-consumer-last",
        "reverse-rollback-under-home-lock",
    },
    "recovery_cases": {
        "interrupted-global-journal-recovered-by-transaction-id",
        "install-recovery-runs-after-private-builds",
    },
    "status_cases": {
        "compiled-installation-current",
        "compiled-currentness-failure-matrix",
    },
    "repair_cases": {"repair-rebuilds-invalid-compiled-entry"},
    "gc_cases": {
        "locked-mark-and-sweep-compiled-cache",
        "post-commit-gc-failure-is-maintenance-warning",
    },
}


class ReleaseFailure(RuntimeError):
    pass


def validate_assurance_release_surface() -> None:
    vector = load_json(ROOT / "conformance" / "v1" / "vectors" / "assurance-modes.json")
    flow = vector.get("valid_flow")
    baseline_error = assurance.validate_flow(flow)
    if baseline_error is not None:
        raise ReleaseFailure(f"valid assurance flow rejected as {baseline_error}")
    cases = vector.get("relational_rejection_cases")
    if not isinstance(cases, list) or len(cases) != 14:
        raise ReleaseFailure("assurance relational release coverage is incomplete")
    names: set[str] = set()
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("name"), str):
            raise ReleaseFailure("assurance relational rejection has no stable name")
        name = case["name"]
        if name in names:
            raise ReleaseFailure(f"duplicate assurance relational rejection {name}")
        names.add(name)
        expected = case.get("expected")
        if not isinstance(expected, dict) or (
            expected.get("failure_stage") != "pre-execution"
            or expected.get("execution_started") is not False
            or expected.get("fallback_mode") is not None
            or not isinstance(expected.get("error"), str)
        ):
            raise ReleaseFailure(f"assurance relational rejection is not fail-closed: {name}")
        try:
            candidate = assurance.apply_mutation(flow, case.get("mutation"))
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ReleaseFailure(f"invalid assurance mutation {name}: {exc}") from exc
        actual = assurance.validate_flow(candidate)
        if actual != expected["error"]:
            raise ReleaseFailure(
                f"assurance relational rejection {name}: got {actual!r}, want {expected['error']!r}"
            )


def load_json(path: Path) -> Any:
    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ReleaseFailure(f"{path}: duplicate JSON key {key!r}")
            value[key] = item
        return value

    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=object_pairs,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        try:
            label = path.relative_to(ROOT)
        except ValueError:
            label = path
        raise ReleaseFailure(f"could not read {label}: {exc}") from exc


def sha256_identity(path: Path) -> str:
    try:
        return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise ReleaseFailure(f"could not hash {path}: {exc}") from exc


def current_suite_sha256() -> str:
    return sha256_identity(ROOT / "conformance" / "v1" / "manifest.json")


def named_cases(values: Any, label: str, required: set[str]) -> dict[str, dict[str, Any]]:
    if not isinstance(values, list):
        raise ReleaseFailure(f"{label} must be an array")
    names = [
        item.get("name") if isinstance(item, dict) else None
        for item in values
    ]
    if any(not isinstance(name, str) or not name for name in names):
        raise ReleaseFailure(f"{label} cases require non-empty names")
    if len(names) != len(set(names)):
        raise ReleaseFailure(f"{label} case names must be unique")
    missing = sorted(required - set(names))
    if missing:
        raise ReleaseFailure(f"{label} is missing lifecycle cases: {missing}")
    return {item["name"]: item for item in values}


def validate_manifest_inventory() -> None:
    suite = ROOT / "conformance" / "v1"
    manifest = load_json(suite / "manifest.json")
    if manifest.get("protocol_version") != PROTOCOL_VERSION:
        raise ReleaseFailure(f"conformance manifest is not {PROTOCOL_VERSION}")
    entries = manifest.get("files")
    if not isinstance(entries, list):
        raise ReleaseFailure("conformance manifest files must be an array")
    paths: list[str] = []
    hashes: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256"}:
            raise ReleaseFailure("conformance manifest entry shape is invalid")
        relative = entry.get("path")
        digest = entry.get("sha256")
        if not isinstance(relative, str) or not relative or not isinstance(digest, str):
            raise ReleaseFailure("conformance manifest entry identity is invalid")
        paths.append(relative)
        hashes[relative] = digest
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise ReleaseFailure("conformance manifest paths must be sorted and unique")

    actual = sorted(
        path.relative_to(suite).as_posix()
        for path in suite.rglob("*")
        if path.is_file()
        and path.name != "manifest.json"
        and "__pycache__" not in path.parts
    )
    if paths != actual:
        raise ReleaseFailure("conformance manifest inventory is incomplete or stale")
    missing_required = sorted(RC7_REQUIRED_MANIFEST_FILES - set(paths))
    if missing_required:
        raise ReleaseFailure(
            f"{PROTOCOL_VERSION} manifest omits required files: {missing_required}"
        )
    for relative in paths:
        if hashes[relative] != sha256_identity(suite / relative):
            raise ReleaseFailure(f"conformance manifest hash is stale: {relative}")


def validate_manager_lifecycle_release_surface() -> None:
    suite = ROOT / "conformance" / "v1"
    manager = load_json(suite / "vectors" / "manager-lifecycle.json")
    build_drivers = load_json(suite / "vectors" / "build-drivers.json")
    if not isinstance(manager, dict) or manager.get("schema_version") != 1:
        raise ReleaseFailure("manager lifecycle vector is not schema 1")
    named_cases(
        manager.get("dry_run_cases"),
        "manager compiled dry run",
        RC6_MANAGER_DRY_RUN_CASES,
    )
    for field, required in RC6_MANAGER_LIFECYCLE_CASES.items():
        named_cases(
            manager.get(field),
            f"manager lifecycle {field}",
            required,
        )

    fixture = manager.get("compiled_build_fixture")
    identity = (
        build_drivers.get("portable_identity")
        if isinstance(build_drivers, dict)
        else None
    )
    if not isinstance(fixture, dict) or not isinstance(identity, dict):
        raise ReleaseFailure("compiled lifecycle/build-driver identity is missing")
    if fixture.get("source_vector") != "build-drivers.json#/portable_identity":
        raise ReleaseFailure("compiled lifecycle fixture has a stale source vector")
    if (
        fixture.get("execution_policy") != PORTABLE_EXECUTION_POLICY
        or identity.get("execution_policy") != PORTABLE_EXECUTION_POLICY
    ):
        raise ReleaseFailure("compiled lifecycle has a stale execution policy")
    for lifecycle_field, identity_field in {
        "execution_policy": "execution_policy",
        "build_input": "build_input",
        "cache_key": "cache_key",
        "stored_receipt": "stored_receipt",
        "receipt_sha256": "receipt_sha256",
        "artifact": "artifact",
    }.items():
        if fixture.get(lifecycle_field) != identity.get(identity_field):
            raise ReleaseFailure(
                f"compiled lifecycle {lifecycle_field} differs from build-driver {identity_field}"
            )
    build_input = identity.get("build_input")
    if (
        not isinstance(build_input, dict)
        or not isinstance(build_input.get("policy"), dict)
        or build_input["policy"].get("execution_policy")
        != PORTABLE_EXECUTION_POLICY
        or fixture.get("logical_command") != build_input.get("command")
    ):
        raise ReleaseFailure("compiled lifecycle fixture is not bound to its portable input")


def validate_shared_fixture_marker_release_surface() -> None:
    """Publish both marker roles for the shared golden skill.

    The frozen marker-v1 file remains the legacy-read evidence a manager MAY
    still regard as current, so it can never double as the writer golden: a
    candidate that ships only that file lets a downstream consumer compare
    schema-2 writer output against schema-1 bytes and go red for the whole
    release. The writer golden is therefore a required, separately named
    release artifact.
    """
    expected = ROOT / "conformance" / "v1" / "expected"
    legacy_path = expected / "marker.json"
    writer_path = expected / "marker-v2.json"
    if not writer_path.is_file():
        raise ReleaseFailure(
            "the candidate publishes no marker-v2 writer golden for the shared fixture"
        )
    if sha256_identity(legacy_path) != FROZEN_MARKER_V1_SHA256:
        raise ReleaseFailure("published marker-v1 legacy-read evidence changed")
    legacy = load_json(legacy_path)
    writer = load_json(writer_path)
    if not isinstance(legacy, dict) or not isinstance(writer, dict):
        raise ReleaseFailure("shared fixture markers must be objects")
    if legacy.get("schema_version") != 1 or writer.get("schema_version") != 2:
        raise ReleaseFailure("shared fixture markers do not carry their own schema identity")
    skill_schema_version = writer.get("skill_schema_version")
    if (
        not isinstance(skill_schema_version, int)
        or isinstance(skill_schema_version, bool)
        or not 1 <= skill_schema_version <= 6
    ):
        raise ReleaseFailure("the marker-v2 writer golden leaves the schema 1 through 6 range")
    if writer.get("build_roots") != [] or writer.get("builds") != {}:
        raise ReleaseFailure("the marker-v2 writer golden records build state the fixture has none of")
    if "build_source" in writer:
        raise ReleaseFailure("build_source is releasable only alongside a non-empty builds object")
    differing = {key for key in set(legacy) | set(writer) if legacy.get(key) != writer.get(key)}
    if differing != SHARED_FIXTURE_MARKER_V2_DELTA:
        raise ReleaseFailure(
            "the marker-v2 writer golden describes a different installation than the "
            f"legacy marker; it differs in {sorted(differing)}"
        )


def validate_protocol_artifacts(version: str) -> None:
    if version != PROTOCOL_VERSION:
        return

    missing = sorted(path for path in RC7_REQUIRED_FILES if not (ROOT / path).is_file())
    if missing:
        raise ReleaseFailure(
            f"{PROTOCOL_VERSION} required artifacts are missing: {missing}"
        )

    schema_expectations = {
        "agent-skill-v6.schema.json": (6, None),
        "csk-skill-v6.schema.json": (6, None),
        "build-receipt-v1.schema.json": (1, None),
        "install-marker-v2.schema.json": (2, None),
        "conformance-claim-v1.schema.json": (1, CLAIM_PROTOCOL_VERSIONS[1]),
        "conformance-claim-v2.schema.json": (2, CLAIM_PROTOCOL_VERSIONS[2]),
        "conformance-claim-v3.schema.json": (3, CLAIM_PROTOCOL_VERSIONS[3]),
        "conformance-claim-v4.schema.json": (4, CLAIM_PROTOCOL_VERSIONS[4]),
        "verified-provider-v1.schema.json": (1, None),
        "provider-capability-receipt-v1.schema.json": (1, None),
        "execution-permit-v1.schema.json": (1, None),
        "execution-receipt-v1.schema.json": (1, None),
        "execution-checkpoint-v1.schema.json": (1, None),
    }
    schemas = ROOT / "schemas" / "v1"
    for name, (schema_version, protocol_version) in schema_expectations.items():
        schema = load_json(schemas / name)
        properties = schema.get("properties")
        if not isinstance(properties, dict):
            raise ReleaseFailure(f"{name} has no properties")
        if properties.get("schema_version") != {"const": schema_version}:
            raise ReleaseFailure(f"{name} has the wrong schema_version identity")
        if (
            protocol_version is not None
            and properties.get("protocol_version") != {"const": protocol_version}
        ):
            raise ReleaseFailure(f"{name} has the wrong protocol_version identity")
    marker = load_json(schemas / "install-marker-v2.schema.json")
    if marker.get("properties", {}).get("skill_schema_version", {}).get("maximum") != 6:
        raise ReleaseFailure("install-marker-v2 does not admit manifest schema 6")

    for relative, expected in CLAIM_HISTORY_FROZEN_SHA256.items():
        actual = sha256_identity(ROOT / relative).removeprefix("sha256:")
        if actual != expected:
            raise ReleaseFailure(f"historical claim artifact changed: {relative}")

    rc5_metadata = ROOT / "release" / "1.0.0-rc.5.json"
    if sha256_identity(rc5_metadata) != RC5_RELEASE_METADATA_SHA256:
        raise ReleaseFailure("published rc.5 release metadata changed")

    validate_manifest_inventory()
    index = load_json(ROOT / "conformance" / "v1" / "schema-cases" / "index.json")
    if not isinstance(index, list):
        raise ReleaseFailure("schema-case index must be an array")
    indexed = {
        item.get("schema")
        for item in index
        if isinstance(item, dict) and isinstance(item.get("schema"), str)
    }
    missing_schemas = sorted(RC7_REQUIRED_INDEXED_SCHEMAS - indexed)
    if missing_schemas:
        raise ReleaseFailure(
            f"{PROTOCOL_VERSION} schema-case index is incomplete: {missing_schemas}"
        )

    if sha256_identity(ROOT / "release" / "1.0.0-rc.6.json") != RC6_RELEASE_METADATA_SHA256:
        raise ReleaseFailure("historical rc.6 release metadata changed")

    validate_assurance_release_surface()

    release = load_json(ROOT / "release" / "1.0.0-rc.7.json")
    history = release.get("historical_release", {})
    claim = release.get("claim_v4", {})
    assurance = release.get("assurance", {})
    if (
        release.get("protocol_version") != PROTOCOL_VERSION
        or release.get("source_baseline_commit") != RC6_SOURCE_COMMIT
        or release.get("legacy_release") != RC6_PROTOCOL_VERSION
        or not isinstance(history, dict)
        or history.get("protocol_version") != RC6_PROTOCOL_VERSION
        or history.get("metadata_path") != "release/1.0.0-rc.6.json"
        or history.get("metadata_sha256") != RC6_RELEASE_METADATA_SHA256
        or history.get("source_commit") != RC6_SOURCE_COMMIT
        or history.get("immutable") is not True
        or not isinstance(claim, dict)
        or claim.get("claim_protocol_version") != PROTOCOL_VERSION
        or claim.get("schema") != "schemas/v1/conformance-claim-v4.schema.json"
        or claim.get("claims_emitted") != []
        or not isinstance(assurance, dict)
        or assurance.get("default_mode") != "portable"
        or assurance.get("verified_implementations") != []
        or assurance.get("verified_platform_claims") != []
        or assurance.get("silent_downgrade_permitted") is not False
        or assurance.get("skill_vendored_provider_allowed") is not False
    ):
        raise ReleaseFailure(
            "rc.7 metadata rewrites rc.6 evidence or fabricates a verified claim"
        )

    validate_manager_lifecycle_release_surface()
    validate_shared_fixture_marker_release_surface()
    decision = (
        ROOT / "decisions" / "0004-compile-only-build-drivers.md"
    ).read_text(encoding="utf-8")
    for required_text in (
        "# Decision 0004:",
        "Manifest schema 6",
        "go-v1",
        "## Rejected alternatives",
    ):
        if required_text not in decision:
            raise ReleaseFailure(
                f"decision 0004 is stale: missing {required_text!r}"
            )
    assurance_decision = (
        ROOT / "decisions" / "0007-portable-and-verified-assurance.md"
    ).read_text(encoding="utf-8")
    for required_text in (
        "portable-cli-policy-v1",
        "verified-provider-policy-v1",
        "host-execution-provider-v1",
        "no fallback or downgrade",
        "macOS, Linux, and Windows",
    ):
        if required_text not in assurance_decision:
            raise ReleaseFailure(
                f"decision 0007 is stale: missing {required_text!r}"
            )


def validate_conformance_claim(path: Path, version: str) -> None:
    schema_version = {
        protocol_version: version_number
        for version_number, protocol_version in CLAIM_PROTOCOL_VERSIONS.items()
    }.get(version)
    if schema_version is None:
        raise ReleaseFailure(f"claim verification is not defined for {version}")
    schemas: dict[str, Any] = {}
    for schema_path in sorted((ROOT / "schemas" / "v1").glob("*.json")):
        document = load_json(schema_path)
        schema_id = document.get("$id")
        if isinstance(schema_id, str):
            schemas[schema_id] = document
    registry = Registry().with_resources(
        (
            schema_id,
            Resource.from_contents(document),
        )
        for schema_id, document in schemas.items()
    )
    claim_schema = load_json(
        ROOT
        / "schemas"
        / "v1"
        / f"conformance-claim-v{schema_version}.schema.json"
    )
    claim = load_json(path)
    errors = sorted(
        Draft202012Validator(
            claim_schema,
            registry=registry,
            format_checker=FormatChecker(),
        ).iter_errors(claim),
        key=lambda item: list(item.absolute_path),
    )
    if errors:
        raise ReleaseFailure(
            f"{path}: invalid {version} conformance claim: {errors[0].message}"
        )
    expected_suite = current_suite_sha256()
    if claim.get("suite_sha256") != expected_suite:
        raise ReleaseFailure(
            f"{path}: suite_sha256 does not identify the current {version} suite"
        )


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
        if version == PROTOCOL_VERSION:
            assurance = metadata.get("assurance", {})
            if (
                not isinstance(assurance, dict)
                or assurance.get("default_mode") != "portable"
                or assurance.get("portable_execution_policy") != PORTABLE_EXECUTION_POLICY
                or assurance.get("verified_provider_contract")
                != "host-execution-provider-v1"
                or assurance.get("verified_implementations") != []
                or assurance.get("verified_platform_claims") != []
                or assurance.get("silent_downgrade_permitted") is not False
                or assurance.get("skill_vendored_provider_allowed") is not False
            ):
                raise ReleaseFailure(
                    f"{metadata_path.relative_to(ROOT)} does not honestly record its assurance policy"
                )
        else:
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
    parser.add_argument("--claim", action="append", type=Path, default=[])
    arguments = parser.parse_args()
    try:
        release_commit = git("rev-parse", f"{arguments.commit}^{{commit}}")
        validate_checkout(release_commit)
        validate_version(arguments.version)
        validate_repository_descriptor(arguments.version)
        validate_protocol_artifacts(arguments.version)
        for claim in arguments.claim:
            validate_conformance_claim(claim, arguments.version)
        if "-" not in arguments.version:
            validate_reviews(arguments.version, release_commit)
    except ReleaseFailure as exc:
        print(f"release gate failed: {exc}")
        return 1
    print(f"release gate passed for {arguments.version} at {release_commit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
