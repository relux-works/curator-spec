#!/usr/bin/env python3
"""Validate the hardened execution profile suite.

The portable candidate suite under ``conformance/v1`` is accepted and pinned,
so this validator has two jobs. It checks that the hardened schemas, vectors,
manifest, and release metadata are internally consistent and honest, and it
checks that the hardened material does not touch, widen, alias, or contradict
the portable profile.
"""

from __future__ import annotations

import hashlib
import json
import re
import struct
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[1]
PORTABLE_SCHEMAS = ROOT / "schemas" / "v1"
HARDENED_SCHEMAS = ROOT / "schemas" / "hardened" / "v1"
PORTABLE_SUITE = ROOT / "conformance" / "v1"
HARDENED_SUITE = ROOT / "conformance" / "hardened" / "v1"
PROTOCOL_DOCUMENT = ROOT / "protocol" / "hardened-execution.md"
MANAGER_DOCUMENT = ROOT / "profiles" / "manager-hardened.md"

HARDENED_PROFILE_VERSION = "hardened-1.0.0-rc.1"
PORTABLE_PROTOCOL_VERSION = "1.0.0-rc.5"
HARDENED_PROFILE_IDENTITY = "hardened-profile-v1"
HARDENED_EXECUTION_POLICY = "hardened-worker-v1"
PORTABLE_EXECUTION_POLICY = "manager-worker-v1"
CAPABILITY_INVENTORY_VERSION = "hardened-capability-inventory-v1"
HARDENED_EVIDENCE_RECORD_VERSION = "hardened-capability-evidence-v1"
PORTABLE_EVIDENCE_RECORD_VERSION = "capability-evidence-v1"
TCB_RECORD_VERSION = "hardened-tcb-v1"
IDENTITY_BINDING_VERSION = "hardened-identity-binding-v1"
TCB_DIGEST_ALGORITHM = "curator-hardened-tcb-v1"
OWNER_STORY = "STORY-260728-327soo"

# The two boundaries the whole profile is written around, and the only actor
# that lives inside the build domain.
DOMAIN_ENTRY_PHASE = "domain-entry"
FIRST_PACKAGE_PHASE = "go-list"
IN_DOMAIN_ACTOR = "domain-root-worker"

# goos values map onto hardened platform names. A native hardened build cannot
# report a trusted computing base from another host.
GOOS_TO_PLATFORM = {"darwin": "macos", "linux": "linux", "windows": "windows"}

# One platform declares exactly one enforcement backend. The relation is closed
# in both directions, so a record cannot pair a platform with another platform's
# mechanism and still hash to a valid trusted computing base.
PLATFORM_BACKENDS = {
    "linux": "linux-namespace-seccomp-v1",
    "macos": "macos-sandbox-v1",
    "windows": "windows-appcontainer-job-v1",
}

# The closed hardened-tcb-v1 record. Every member identifies something whose
# replacement changes what the kernel actually enforces, so omitting one would
# let two materially different trusted bases share a digest, a cache key, a
# receipt binding, a marker, and a claim.
TCB_FIELDS = [
    "backend",
    "enforcement_backend",
    "execution_policy",
    "hardened_profile",
    "host",
    "parent_sha256",
    "platform",
    "record_version",
    "supervisor_sha256",
    "toolchain",
    "trusted_components",
    "worker_sha256",
]

# The three members this profile revision fixes by constant. They cannot be
# rotated without leaving the profile entirely, so they carry no rotation case.
TCB_CONSTANT_FIELDS = {"record_version", "hardened_profile", "execution_policy"}

TCB_HOST_FIELDS = ["build", "identity", "kind", "version"]

# review-cycle-3 finding R3-2: a host record detached from the platform it is
# supposed to identify is not an identity. Every enforcement backend this
# revision declares is an operating-system-kernel mechanism, so the host kind is
# constant and the host identity is the canonical kernel identity of the
# platform. protocol/hardened-execution.md sections 2.3.3 and 6.3.
TCB_HOST_KIND = "operating-system"
CANONICAL_HOST_IDENTITY = {"linux": "linux", "macos": "darwin", "windows": "windows-nt"}

# review-cycle-4 finding R4-1: a nullable descriptive build string let two
# materially different kernels reporting one platform and one release produce one
# hardened-tcb-v1 record, one cache key, one receipt, one marker, and one claim.
# The kernel build identity is now a required closed record whose digest covers
# the platform's declared build-identity sources.
# protocol/hardened-execution.md sections 2.3.3 and 6.3.
HOST_BUILD_ALGORITHM = "curator-hardened-host-build-v1"
HOST_BUILD_FIXTURE_VERSION = "hardened-host-build-fixtures-v1"
HOST_BUILD_FIELDS = ["algorithm", "content_sha256", "identifier"]
HOST_VERSION_PATTERN = re.compile(
    r"^(?:0|[1-9][0-9]{0,8})(?:\.(?:0|[1-9][0-9]{0,8})){0,3}(?:-[0-9A-Za-z][0-9A-Za-z._+-]{0,63})?$"
)
HOST_BUILD_IDENTIFIER_PATTERN = {
    "linux": re.compile(r"^[0-9a-f]{32,128}$"),
    "macos": re.compile(r"^[0-9]{1,3}[A-Z][0-9]{1,6}[a-z]?$"),
    "windows": re.compile(r"^[0-9]{1,7}\.[0-9]{1,7}$"),
}
HOST_BUILD_IDENTIFIER_SOURCE = {
    "linux": "kernel.build-id",
    "macos": "kern.osversion",
    "windows": "kernel.current-build-and-ubr",
}
HOST_BUILD_SOURCES = {
    "linux": ["kernel.build-id", "kernel.osrelease", "kernel.version-string"],
    "macos": ["kern.osversion", "kern.osproductversion", "kern.version"],
    "windows": [
        "kernel.current-build-and-ubr",
        "kernel.build-lab-ex",
        "kernel.image-file-version",
    ],
}

# Every mutable facet of the observed kernel build identity. Rotating the host
# record as a whole is not coverage for any of them.
HOST_BUILD_ASPECTS = {"identifier", "release-binding", "source-value"}

TCB_BACKEND_FIELDS = ["configuration", "version"]

# The comparable enforcement-backend version identity of section 2.3.4, and the
# series token each backend's version line carries. Two series are not ordered
# against each other.
BACKEND_VERSION_GRAMMAR = "hardened-backend-version-v1"
BACKEND_VERSION_PATTERN = re.compile(
    r"^([a-z][a-z0-9]*)-((?:0|[1-9][0-9]{0,8})(?:\.(?:0|[1-9][0-9]{0,8})){0,3})$"
)
BACKEND_VERSION_SERIES = {
    "linux-namespace-seccomp-v1": "cgroup2",
    "macos-sandbox-v1": "sandbox",
    "windows-appcontainer-job-v1": "appcontainer",
}

TCB_COMPONENT_FIELDS = ["algorithm", "content_sha256", "kind", "name"]
COMPONENT_FILE_ALGORITHM = "curator-hardened-component-file-v1"
COMPONENT_TREE_ALGORITHM = "curator-hardened-component-tree-v1"
TCB_COMPONENT_ALGORITHMS = {COMPONENT_FILE_ALGORITHM, COMPONENT_TREE_ALGORITHM}
COMPONENT_FIXTURE_VERSION = "hardened-component-digest-fixtures-v1"
COMPONENT_TREE_ENTRY_KINDS = {"D", "F", "L"}

# review-cycle-3 finding R3-1: which algorithm a kind admits is part of the
# construction. A kind that can only ever name one file must not carry a tree
# digest. protocol/hardened-execution.md section 2.3.2.
COMPONENT_ALGORITHM_BY_KIND = {
    "capability-probe": {COMPONENT_FILE_ALGORITHM, COMPONENT_TREE_ALGORITHM},
    "enforcement-adapter": {COMPONENT_FILE_ALGORITHM, COMPONENT_TREE_ALGORITHM},
    "helper-executable": {COMPONENT_FILE_ALGORITHM},
    "identity-verifier": {COMPONENT_FILE_ALGORITHM, COMPONENT_TREE_ALGORITHM},
    "installed-package-tree": {COMPONENT_TREE_ALGORITHM},
    "interpreter": {COMPONENT_FILE_ALGORITHM},
    "sandbox-policy-file": {COMPONENT_FILE_ALGORITHM},
    "script": {COMPONENT_FILE_ALGORITHM},
    "shared-library": {COMPONENT_FILE_ALGORITHM},
}
TCB_COMPONENT_KINDS = set(COMPONENT_ALGORITHM_BY_KIND)

# Every mutable facet of a trusted component. Rotating the array as a whole is
# not coverage for any of them: review cycle 3 rejected exactly that.
COMPONENT_ASPECTS = {
    "algorithm",
    "component-set",
    "content",
    "entry-type",
    "kind",
    "link-substitution",
    "name",
    "tree-membership",
}

# The relations that keep two different trusted bases from sharing one digest.
# Each one names where it is enforced, and validate_tcb_schema_relations proves
# every schema-enforced entry against the real schemas.
TCB_RELATIONS = {
    "backend-version-series-to-backend",
    "claim-backend-version-at-least-minimum",
    "claim-operating-system-covers-tcb-platform",
    "claim-required-configuration-observed-in-tcb",
    "component-algorithm-to-kind",
    "host-build-digest-reproduces-observed-host",
    "host-build-identifier-to-platform",
    "host-identity-to-platform",
    "input-digest-reproduces-tcb-record",
    "marker-key-reproducible-from-published-identities",
    "operating-system-to-backend",
    "platform-to-backend",
    "target-to-platform",
    "tcb-toolchain-equals-build-input-toolchain",
}

TCB_CASE_KINDS = {
    "digest-mismatch",
    "narrower-than-trusted",
    "omission",
    "relation-mismatch",
    "uncryptographic-component",
}

TCB_ENFORCEMENT_SITES = {"conformance-validator", "implementation", "schema"}

# A defs-only document has no wire instance of its own, exactly like the
# portable common schema.
DEFS_ONLY_SCHEMAS = {"hardened-common.schema.json"}

# The six guarantees protocol/core.md section 4.2.1 defers. The set is not
# hard-coded as authority here: it is cross-checked against the portable vector
# so the two documents cannot drift.
GUARANTEES = {
    "exact-executable-allowlisting",
    "fail-closed-capability-preflight",
    "hard-aggregate-descendant-resource-bounds",
    "private-build-root-only-writes",
    "read-only-source-and-toolchain",
    "total-network-denial",
}

CAPABILITY_CLASSES = {
    "active-capability-probe",
    "aggregate-resource-bounds",
    "domain-atomic-termination",
    "domain-membership-enforcement",
    "exec-path-allowlist",
    "filesystem-view-restriction",
    "network-syscall-denial",
    "preexisting-endpoint-revocation",
    "read-only-source-view",
    "read-only-toolchain-view",
    "write-path-confinement",
}

HARDENED_DIAGNOSTICS = {
    "hardened_capability_unavailable",
    "hardened_domain_breach_detected",
    "hardened_domain_establishment_failed",
    "hardened_domain_protocol_invalid",
    "hardened_evidence_invalid",
    "hardened_package_influence_forbidden",
    "hardened_profile_claim_forbidden",
    "hardened_profile_unsupported",
    "hardened_tcb_identity_invalid",
}

# The six portable execution diagnostics of profiles/manager.md section 2.2.1.
# A hardened code may never collide with one of them.
PORTABLE_DIAGNOSTICS = {
    "build_execution_capability_evidence_invalid",
    "build_execution_control_unavailable",
    "build_execution_hardened_claim_forbidden",
    "build_execution_package_influence_forbidden",
    "build_execution_worker_identity_invalid",
    "build_execution_worker_protocol_invalid",
}

# The one normative ordered phase list. protocol/hardened-execution.md section
# 7.2 is its normative statement; profiles/manager-hardened.md and the profile
# vector mirror it, and validate_phase_list_documents proves all three agree.
ORDERED_PHASES = [
    "profile-selection",
    "platform-qualification",
    "capability-probe",
    "toolchain-probe-and-snapshot-freeze",
    "tcb-identity-verification",
    "build-input-and-cache-lookup",
    "domain-establishment",
    "domain-entry",
    "in-domain-guarantee-self-test",
    "go-list",
    "parent-graph-validation",
    "build-permit",
    "go-build",
    "artifact-verification",
    # review-cycle-4 finding R4-2: the domain is destroyed and joined before the
    # trusted computing base is re-verified, so re-verification observes a state
    # no domain member can still change.
    "domain-teardown",
    "identity-reverification",
    "publication",
]

REVERIFICATION_PHASE = "identity-reverification"
TEARDOWN_PHASE = "domain-teardown"
PUBLICATION_PHASE = "publication"
REVERIFICATION_CASE_KINDS = {
    "changed-member",
    "omitted-member",
    "phase-order",
    "restated-record",
}

GRAPH_NODES = [
    "manager-parent",
    "hardened-supervisor",
    "domain-root-worker",
    "go-launcher",
    "goroot-tools",
]

SAFE_INTEGER = 9_007_199_254_740_991


class ValidationFailure(RuntimeError):
    pass


def load_json(path: Path) -> Any:
    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValidationFailure(f"{path}: duplicate JSON key {key!r}")
            result[key] = value
        return result

    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=object_pairs)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValidationFailure(f"{path}: invalid JSON: {exc}") from exc


def ccj1_bytes(value: Any) -> bytes:
    def check(item: Any) -> None:
        if item is None or isinstance(item, (str, bool)):
            return
        if isinstance(item, int):
            if abs(item) > SAFE_INTEGER:
                raise ValidationFailure("integer outside CCJ-1 safe range")
            return
        if isinstance(item, list):
            for child in item:
                check(child)
            return
        if isinstance(item, dict):
            for key, child in item.items():
                if not isinstance(key, str):
                    raise ValidationFailure("CCJ-1 object key is not text")
                check(child)
            return
        raise ValidationFailure(f"unsupported CCJ-1 value {type(item).__name__}")

    check(value)
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def ccj1_sha256(value: Any) -> str:
    return "sha256:" + hashlib.sha256(ccj1_bytes(value)).hexdigest()


def tcb_digest(record: Any) -> str:
    """curator-hardened-tcb-v1 over a closed hardened-tcb-v1 record.

    Domain-separated and length-framed exactly like the portable snapshot and
    toolchain algorithms, so it can never collide with a cache key computed
    over the same canonical bytes.
    """
    payload = ccj1_bytes(record)
    digest = hashlib.sha256()
    digest.update(TCB_DIGEST_ALGORITHM.encode("ascii") + b"\x00")
    digest.update(struct.pack(">Q", len(payload)))
    digest.update(payload)
    return "sha256:" + digest.hexdigest()


def component_file_digest(content: bytes) -> str:
    """curator-hardened-component-file-v1 over one regular file's bytes.

    Independent of the generator: this is the construction
    protocol/hardened-execution.md section 2.3.1 defines, written from the
    document rather than from the Go code, so the published fixture digests are
    reproduced by a second implementation. review-cycle-3 finding R3-1.
    """
    digest = hashlib.sha256()
    digest.update(COMPONENT_FILE_ALGORITHM.encode("ascii") + b"\x00")
    digest.update(b"F")
    digest.update(struct.pack(">Q", len(content)))
    digest.update(content)
    return "sha256:" + digest.hexdigest()


def component_tree_digest(entries: list[tuple[str, bytes, bytes]]) -> str:
    """curator-hardened-component-tree-v1 over a directory-tree walk.

    Entries are ``(kind, path_utf8, payload)``. The kind byte is hashed, which
    is what makes a link substitution a different tree even when the substituted
    regular file holds the referent's exact bytes.
    """
    ordered = sorted(entries, key=lambda entry: entry[1])
    seen: set[bytes] = set()
    digest = hashlib.sha256()
    digest.update(COMPONENT_TREE_ALGORITHM.encode("ascii") + b"\x00")
    for kind, path, payload in ordered:
        if kind not in COMPONENT_TREE_ENTRY_KINDS:
            raise ValidationFailure(f"component tree entry kind {kind!r} is not D, F, or L")
        if path in seen:
            raise ValidationFailure("component tree repeats an encoded relative path")
        seen.add(path)
        digest.update(kind.encode("ascii"))
        digest.update(struct.pack(">Q", len(path)))
        digest.update(path)
        digest.update(struct.pack(">Q", len(payload)))
        digest.update(payload)
    return "sha256:" + digest.hexdigest()


def host_build_digest(
    identity: str, version: str, identifier: str, sources: list[tuple[bytes, bytes]]
) -> str:
    """curator-hardened-host-build-v1 over one observed kernel build identity.

    Independent of the generator: this is the construction
    protocol/hardened-execution.md section 2.3.3 defines, written from the
    document, so a published fixture digest is reproduced by a second
    implementation rather than trusted. review-cycle-4 finding R4-1.
    """
    digest = hashlib.sha256()
    digest.update(HOST_BUILD_ALGORITHM.encode("ascii") + b"\x00")
    for value in (identity, version, identifier):
        encoded = value.encode("utf-8")
        digest.update(struct.pack(">Q", len(encoded)))
        digest.update(encoded)
    digest.update(struct.pack(">Q", len(sources)))
    for name, observed in sources:
        digest.update(struct.pack(">Q", len(name)))
        digest.update(name)
        digest.update(struct.pack(">Q", len(observed)))
        digest.update(observed)
    return "sha256:" + digest.hexdigest()


def parse_backend_version(value: Any) -> tuple[str, tuple[int, int, int, int]] | None:
    """Parse a hardened-backend-version-v1 value into its series and components.

    Returns None for anything outside the grammar. A missing numeric component
    is zero, so ``sandbox-2`` and ``sandbox-2.0.0`` parse to the same tuple.
    """
    if not isinstance(value, str):
        return None
    match = BACKEND_VERSION_PATTERN.fullmatch(value)
    if match is None:
        return None
    numbers = [int(part) for part in match.group(2).split(".")]
    numbers.extend([0] * (4 - len(numbers)))
    return match.group(1), (numbers[0], numbers[1], numbers[2], numbers[3])


def backend_version_at_least(observed: Any, minimum: Any) -> tuple[bool, bool]:
    """Return (satisfied, comparable) for an observed version and a minimum.

    Comparing two series is not a lower or higher result: a backend's version
    line has no ordering against another backend's, so it is invalid.
    """
    left = parse_backend_version(observed)
    right = parse_backend_version(minimum)
    if left is None or right is None or left[0] != right[0]:
        return False, False
    return left[1] >= right[1], True


def markdown_section(path: Path, heading: str) -> str:
    """Return one Markdown section body, so document checks stay anchored."""
    text = path.read_text(encoding="utf-8")
    start = text.find(heading)
    if start < 0:
        raise ValidationFailure(f"{path.name}: section {heading!r} is missing")
    level = heading.split(" ", 1)[0]
    remainder = text[start + len(heading) :]
    for line in remainder.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith("#") and len(stripped.split(" ", 1)[0]) <= len(level):
            return remainder[: remainder.find(line)]
    return remainder


def registry_and_paths() -> tuple[Registry, dict[str, Path]]:
    """Both schema families in one registry so cross-family refs resolve."""
    documents: dict[str, Any] = {}
    paths: dict[str, Path] = {}
    for directory in (PORTABLE_SCHEMAS, HARDENED_SCHEMAS):
        for path in sorted(directory.glob("*.json")):
            document = load_json(path)
            try:
                Draft202012Validator.check_schema(document)
            except SchemaError as exc:
                raise ValidationFailure(
                    f"{path}: invalid Draft 2020-12 schema: {exc.message}"
                ) from exc
            schema_id = document.get("$id")
            if not isinstance(schema_id, str) or not schema_id:
                raise ValidationFailure(f"{path}: schema has no $id")
            if schema_id in documents:
                raise ValidationFailure(f"{path}: duplicate $id {schema_id}")
            documents[schema_id] = document
            paths[path.name] = path
    registry = Registry().with_resources(
        (schema_id, Resource.from_contents(document))
        for schema_id, document in documents.items()
    )
    return registry, paths


def validator_for(name: str) -> Draft202012Validator:
    registry, paths = registry_and_paths()
    if name not in paths:
        raise ValidationFailure(f"unknown schema {name}")
    return Draft202012Validator(load_json(paths[name]), registry=registry)


def validate_hardened_schemas() -> None:
    registry, paths = registry_and_paths()
    hardened_names = {path.name for path in HARDENED_SCHEMAS.glob("*.json")}
    for name in sorted(hardened_names):
        document = load_json(paths[name])
        schema_id = document["$id"]
        if not schema_id.endswith(f"/schemas/hardened/v1/{name}"):
            raise ValidationFailure(f"{name}: $id does not identify the hardened schema family")

    index = load_json(HARDENED_SUITE / "schema-cases" / "index.json")
    if not isinstance(index, list) or not index:
        raise ValidationFailure("hardened schema-case index is empty")
    seen: set[str] = set()
    covered_valid: set[str] = set()
    covered_invalid: set[str] = set()
    for case in index:
        schema_name = case["schema"]
        if schema_name not in hardened_names:
            raise ValidationFailure(f"hardened schema case names unknown schema {schema_name}")
        instance_path = HARDENED_SUITE / "schema-cases" / case["instance"]
        if case["instance"] in seen:
            raise ValidationFailure(f"duplicate hardened schema case {case['instance']}")
        seen.add(case["instance"])
        instance = load_json(instance_path)
        errors = list(
            Draft202012Validator(load_json(paths[schema_name]), registry=registry).iter_errors(
                instance
            )
        )
        actual = not errors
        if actual != case["valid"]:
            detail = "valid" if actual else errors[0].message
            raise ValidationFailure(
                f"hardened schema case {case['instance']} against {schema_name}: "
                f"expected valid={case['valid']}, got {detail}"
            )
        (covered_valid if case["valid"] else covered_invalid).add(schema_name)

    wire_schemas = hardened_names - DEFS_ONLY_SCHEMAS
    for label, covered in (("positive", covered_valid), ("negative", covered_invalid)):
        missing = sorted(wire_schemas - covered)
        if missing:
            raise ValidationFailure(
                f"hardened schemas without {label} cases: {', '.join(missing)}"
            )


def validate_portable_profile_unchanged() -> None:
    """The portable profile must stay closed, pinned, and unwidened."""
    common = load_json(PORTABLE_SCHEMAS / "common.schema.json")
    policy = common["$defs"]["goExecutionPolicyV1"]
    if policy != {"const": PORTABLE_EXECUTION_POLICY}:
        raise ValidationFailure(
            f"portable goExecutionPolicyV1 was widened away from {PORTABLE_EXECUTION_POLICY}: {policy}"
        )
    for name, version in (
        ("build-receipt-v1.schema.json", 1),
        ("build-receipt-v2.schema.json", 2),
    ):
        document = load_json(PORTABLE_SCHEMAS / name)
        if document["properties"]["schema_version"] != {"const": version}:
            raise ValidationFailure(f"{name}: portable receipt schema version changed")
    claim = load_json(PORTABLE_SCHEMAS / "conformance-claim-v3.schema.json")
    if claim["properties"]["schema_version"] != {"const": 3}:
        raise ValidationFailure("conformance-claim-v3: portable claim schema version changed")

    manifest_path = PORTABLE_SUITE / "manifest.json"
    digest = "sha256:" + hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    release = load_json(ROOT / "release" / f"{PORTABLE_PROTOCOL_VERSION}.json")
    if release["candidate_protocol_pin"]["manifest_sha256"] != digest:
        raise ValidationFailure(
            "the portable rc.5 suite no longer matches its own release pin; "
            "hardened work must not change conformance/v1"
        )
    listed = {entry["path"] for entry in load_json(manifest_path)["files"]}
    if any(path.startswith("hardened") for path in listed):
        raise ValidationFailure("hardened files leaked into the portable rc.5 suite manifest")
    if release["execution_policy"]["hardened_profile_claimed"] is not False:
        raise ValidationFailure("the rc.5 release metadata now claims the hardened profile")
    if release["execution_policy"]["hardened_profile_owner"] != OWNER_STORY:
        raise ValidationFailure("the rc.5 release metadata no longer attributes the hardened owner")


def validate_hardened_manifest() -> None:
    manifest_path = HARDENED_SUITE / "manifest.json"
    manifest = load_json(manifest_path)
    if manifest.get("profile_version") != HARDENED_PROFILE_VERSION:
        raise ValidationFailure("hardened manifest profile_version is wrong")
    entries = manifest.get("files")
    if not isinstance(entries, list) or not entries:
        raise ValidationFailure("hardened manifest files must be a non-empty list")
    listed = [entry["path"] for entry in entries]
    if listed != sorted(listed) or len(listed) != len(set(listed)):
        raise ValidationFailure("hardened manifest paths must be sorted and unique")
    actual = sorted(
        path.relative_to(HARDENED_SUITE).as_posix()
        for path in HARDENED_SUITE.rglob("*")
        if path.is_file() and path != manifest_path
    )
    if listed != actual:
        missing = sorted(set(actual) - set(listed))
        extra = sorted(set(listed) - set(actual))
        raise ValidationFailure(
            f"hardened manifest inventory mismatch; missing={missing}, extra={extra}"
        )
    for entry in entries:
        payload = (HARDENED_SUITE / entry["path"]).read_bytes()
        digest = "sha256:" + hashlib.sha256(payload).hexdigest()
        if digest != entry["sha256"]:
            raise ValidationFailure(f"hardened vector digest mismatch for {entry['path']}")


def validate_hardened_release() -> None:
    release = load_json(ROOT / "release" / f"{HARDENED_PROFILE_VERSION}.json")
    manifest_digest = (
        "sha256:" + hashlib.sha256((HARDENED_SUITE / "manifest.json").read_bytes()).hexdigest()
    )
    portable_digest = (
        "sha256:" + hashlib.sha256((PORTABLE_SUITE / "manifest.json").read_bytes()).hexdigest()
    )
    if release.get("protocol_version") != HARDENED_PROFILE_VERSION:
        raise ValidationFailure("hardened release metadata names the wrong candidate version")
    pin = release.get("candidate_protocol_pin", {})
    if pin.get("manifest_sha256") != manifest_digest or pin.get("suite_root") != "conformance/hardened/v1":
        raise ValidationFailure("hardened candidate pin does not match the hardened suite manifest")
    downstream = release.get("downstream_consumption", {})
    if (
        downstream.get("required_manifest_sha256") != manifest_digest
        or downstream.get("committed_release_pin_advanced") is not False
    ):
        raise ValidationFailure("hardened downstream consumption metadata is incomplete")
    baseline = release.get("portable_baseline", {})
    if (
        baseline.get("protocol_version") != PORTABLE_PROTOCOL_VERSION
        or baseline.get("manifest_sha256") != portable_digest
        or baseline.get("suite_root") != "conformance/v1"
        or baseline.get("modified") is not False
    ):
        raise ValidationFailure("hardened release metadata misreports the portable baseline")
    execution = release.get("execution_policy", {})
    if (
        execution.get("hardened") != HARDENED_EXECUTION_POLICY
        or execution.get("hardened_profile") != HARDENED_PROFILE_IDENTITY
        or execution.get("portable") != PORTABLE_EXECUTION_POLICY
        or execution.get("portable_profile_widened") is not False
        or execution.get("capability_inventory_version") != CAPABILITY_INVENTORY_VERSION
        or execution.get("capability_evidence_record_version") != HARDENED_EVIDENCE_RECORD_VERSION
        or execution.get("tcb_record_version") != TCB_RECORD_VERSION
        or execution.get("identity_binding_version") != IDENTITY_BINDING_VERSION
        or execution.get("tcb_digest_algorithm") != TCB_DIGEST_ALGORITHM
        or execution.get("rc5_reserved_policy_slot_is_hardened_input") is not False
    ):
        raise ValidationFailure("hardened release metadata does not honestly record the profile")
    claim = release.get("claim_v4", {})
    if claim.get("claims_emitted") != []:
        raise ValidationFailure("hardened candidate fabricates conformance claims")
    if release.get("qualified_platforms") != []:
        raise ValidationFailure("hardened candidate fabricates a qualified platform")
    if release.get("owner_story") != OWNER_STORY:
        raise ValidationFailure("hardened release metadata does not name the owning story")


def require_named_key(values: Any, key: str, label: str) -> dict[str, dict[str, Any]]:
    if not isinstance(values, list) or not values:
        raise ValidationFailure(f"{label} must be a non-empty array")
    names = [item.get(key) for item in values if isinstance(item, dict)]
    if len(names) != len(values) or any(not isinstance(name, str) or not name for name in names):
        raise ValidationFailure(f"{label} entries require non-empty {key} values")
    if len(names) != len(set(names)):
        raise ValidationFailure(f"{label} {key} values must be unique")
    return {item[key]: item for item in values}


def require_named(values: Any, label: str) -> dict[str, dict[str, Any]]:
    return require_named_key(values, "name", label)


def validate_guarantee_agreement(profile: dict[str, Any]) -> None:
    """The hardened guarantee set must equal what rc.5 deferred, exactly."""
    portable = load_json(PORTABLE_SUITE / "vectors" / "go-host-execution-policy.json")
    deferred = {item["name"] for item in portable["deferred_hardened_guarantees"]}
    if deferred != GUARANTEES:
        raise ValidationFailure(
            "the portable suite no longer defers exactly the six known guarantees"
        )
    if portable["reserved_hardened_execution_policy"] != HARDENED_EXECUTION_POLICY:
        raise ValidationFailure(
            "the hardened execution policy does not match the identity rc.5 reserved"
        )
    if portable["hardened_profile_owner"] != OWNER_STORY:
        raise ValidationFailure("the portable suite no longer names the hardened owner")
    for item in portable["deferred_hardened_guarantees"]:
        if item["portable_profile_claims"] is not False or item["rejects_portable_build"] is not False:
            raise ValidationFailure(
                "the portable suite now claims or rejects on a hardened guarantee"
            )

    named = require_named(profile["guarantees"], "hardened guarantees")
    if set(named) != GUARANTEES:
        raise ValidationFailure("hardened guarantees do not match the six deferred guarantees")
    for name, item in named.items():
        if item["kernel_or_hypervisor"] is not True:
            raise ValidationFailure(f"{name} is not stated as a kernel or hypervisor property")
        if item["claimable_under_portable"] is not False:
            raise ValidationFailure(f"{name} is marked claimable under the portable profile")
        if item["established_in_this_revision"] is not False:
            raise ValidationFailure(f"{name} claims establishment without native evidence")
        if not item["not_sufficient"]:
            raise ValidationFailure(f"{name} does not state what is not sufficient")
        classes = item["required_capability_classes"]
        if not classes or sorted(classes) != classes or len(set(classes)) != len(classes):
            raise ValidationFailure(f"{name} capability classes must be a sorted unique array")
        unknown = sorted(set(classes) - CAPABILITY_CLASSES)
        if unknown:
            raise ValidationFailure(f"{name} names capability classes outside the inventory: {unknown}")


def validate_capability_inventory(profile: dict[str, Any]) -> dict[str, dict[str, Any]]:
    inventory = profile["capability_inventory"]
    if inventory["version"] != CAPABILITY_INVENTORY_VERSION:
        raise ValidationFailure("hardened capability inventory version is wrong")
    if inventory["exhaustive"] is not True:
        raise ValidationFailure("hardened capability inventory must be exhaustive")
    if inventory["probe_scope"] != "per-operation" or inventory["probe_timing"] != "pre-domain-entry":
        raise ValidationFailure("hardened capability probing is not per-operation before domain entry")
    if inventory["availability_states"] != ["available", "unavailable", "unprobed"]:
        raise ValidationFailure("hardened availability states are wrong")
    if inventory["status_states"] != ["applied", "not-applied"]:
        raise ValidationFailure("hardened status states are wrong")
    classes = require_named(inventory["classes"], "hardened capability classes")
    if set(classes) != CAPABILITY_CLASSES:
        raise ValidationFailure("hardened capability classes do not match the inventory")
    if CAPABILITY_CLASSES & GUARANTEES:
        raise ValidationFailure("a guarantee name is also used as a capability class name")

    # Every class must serve at least one guarantee, and the reverse mapping in
    # the guarantee list must agree with the class list.
    reverse: dict[str, set[str]] = {name: set() for name in CAPABILITY_CLASSES}
    for guarantee in profile["guarantees"]:
        for class_name in guarantee["required_capability_classes"]:
            reverse[class_name].add(guarantee["name"])
    for name, item in classes.items():
        if item["optional"] is not False:
            raise ValidationFailure(f"capability class {name} is marked optional")
        if not item["serves"]:
            raise ValidationFailure(f"capability class {name} serves no guarantee")
        if set(item["serves"]) != reverse[name]:
            raise ValidationFailure(
                f"capability class {name} disagrees with the guarantee-to-class mapping"
            )
    unused = sorted(name for name, serves in reverse.items() if not serves)
    if unused:
        raise ValidationFailure(f"capability classes serve no guarantee: {unused}")

    # A portable native control must not be reused as a hardened class.
    portable = load_json(PORTABLE_SUITE / "vectors" / "go-host-execution-policy.json")
    portable_controls = {item["name"] for item in portable["native_control_inventory"]["controls"]}
    if portable_controls & CAPABILITY_CLASSES:
        raise ValidationFailure(
            "a portable native control name is reused as a hardened capability class"
        )
    return classes


def validate_platform_declarations(profile: dict[str, Any]) -> None:
    declarations = profile["platform_declarations"]
    platforms = [item["platform"] for item in declarations]
    if platforms != ["linux", "macos", "windows"]:
        raise ValidationFailure("hardened platform declarations must cover exactly linux, macos, windows")
    backends = [item["enforcement_backend"] for item in declarations]
    if len(set(backends)) != len(backends):
        raise ValidationFailure("hardened enforcement backends must be distinct per platform")
    for item in declarations:
        platform = item["platform"]
        if item["qualification_status"] != "unqualified":
            raise ValidationFailure(
                f"{platform} is declared qualified without native adversarial evidence"
            )
        if item["native_evidence"] != "absent":
            raise ValidationFailure(f"{platform} claims native evidence this revision does not have")
        if not item["qualification_tasks"]:
            raise ValidationFailure(f"{platform} does not name a qualification task")
        if not item["candidate_primitives"]:
            raise ValidationFailure(f"{platform} does not name candidate primitives")
        blocking = item["blocking_capability_classes"]
        unknown = sorted(set(blocking) - CAPABILITY_CLASSES)
        if unknown:
            raise ValidationFailure(f"{platform} blocks on unknown capability classes: {unknown}")
        if blocking and not item["blocking_reason"]:
            raise ValidationFailure(f"{platform} lists blocking classes without a reason")
        if not blocking and item["blocking_reason"] is not None:
            raise ValidationFailure(f"{platform} states a blocking reason without a blocking class")


def validate_ordered_phases(profile: dict[str, Any]) -> None:
    """The phase list must be executable, not merely enumerated.

    Every phase names the actor that performs it, and an actor that lives
    inside the build domain cannot appear before the phase that creates the
    first process in it. That single rule is what makes the in-domain
    guarantee self-test a step an implementation can actually perform.
    """
    phases = profile["ordered_phases"]
    if [item["name"] for item in phases] != ORDERED_PHASES:
        raise ValidationFailure("hardened ordered phases are wrong or out of order")
    if [item["index"] for item in phases] != list(range(1, len(ORDERED_PHASES) + 1)):
        raise ValidationFailure("hardened phase indices are not 1..n in order")

    entry_index = ORDERED_PHASES.index(DOMAIN_ENTRY_PHASE)
    exposure_index = ORDERED_PHASES.index(FIRST_PACKAGE_PHASE)
    if exposure_index <= entry_index:
        raise ValidationFailure("package exposure is not ordered after domain entry")

    for position, item in enumerate(phases):
        name = item["name"]
        actor = item["actor"]
        if actor not in GRAPH_NODES:
            raise ValidationFailure(f"phase {name} names an actor outside the process graph")
        if item["actor_in_build_domain"] is not (actor == IN_DOMAIN_ACTOR):
            raise ValidationFailure(f"phase {name} misreports whether its actor is contained")
        if item["actor_in_build_domain"] and position <= entry_index:
            raise ValidationFailure(
                f"phase {name} is performed inside the build domain before {DOMAIN_ENTRY_PHASE}"
            )
        if item["before_domain_entry"] != (position < entry_index):
            raise ValidationFailure(
                f"phase {name} misreports whether it precedes domain entry"
            )
        if item["before_package_exposure"] != (position < exposure_index):
            raise ValidationFailure(
                f"phase {name} misreports whether it precedes package exposure"
            )
        if item["package_bytes_reach_go_process"] is item["before_package_exposure"]:
            raise ValidationFailure(
                f"phase {name} contradicts itself about package bytes reaching Go"
            )
        diagnostic = item["rejection_diagnostic"]
        if diagnostic is not None and diagnostic not in HARDENED_DIAGNOSTICS:
            raise ValidationFailure(f"phase {name} names an unknown diagnostic")

    first_package_phase = next(
        item["name"] for item in phases if item["package_bytes_reach_go_process"]
    )
    if first_package_phase != FIRST_PACKAGE_PHASE:
        raise ValidationFailure("a Go process sees package bytes before go list")

    validate_ordering_invariants(profile)
    validate_self_test(profile)
    validate_identity_reverification(profile)


def validate_ordering_invariants(profile: dict[str, Any]) -> None:
    invariants = require_named(profile["ordering_invariants"], "hardened ordering invariants")
    required = {
        "capability-probe-before-domain-establishment",
        "cache-lookup-before-domain-establishment",
        "domain-entry-before-in-domain-self-test",
        "graph-validation-before-build-permit",
        "build-permit-before-go-build",
        "self-test-before-package-exposure",
        "tcb-verification-before-cache-lookup",
        # review-cycle-4 finding R4-2.
        "teardown-before-identity-reverification",
        "identity-reverification-before-publication",
        "teardown-before-publication",
    }
    missing = sorted(required - set(invariants))
    if missing:
        raise ValidationFailure(f"hardened ordering invariants are missing: {missing}")
    for name, item in invariants.items():
        for field in ("earlier", "later"):
            if item[field] not in ORDERED_PHASES:
                raise ValidationFailure(f"ordering invariant {name} names an unknown phase")
        if ORDERED_PHASES.index(item["earlier"]) >= ORDERED_PHASES.index(item["later"]):
            raise ValidationFailure(
                f"ordering invariant {name} does not hold in the ordered phase list"
            )
        if not item["because"]:
            raise ValidationFailure(f"ordering invariant {name} states no reason")


def validate_self_test(profile: dict[str, Any]) -> None:
    """The self-test must have an actor that exists when it runs."""
    test = profile["in_domain_self_test"]
    if test["phase"] not in ORDERED_PHASES:
        raise ValidationFailure("the in-domain self-test names an unknown phase")
    if test["actor"] != IN_DOMAIN_ACTOR or test["actor_in_build_domain"] is not True:
        raise ValidationFailure(
            "the in-domain self-test is not performed by a process inside the build domain"
        )
    position = ORDERED_PHASES.index(test["phase"])
    if position <= ORDERED_PHASES.index(DOMAIN_ENTRY_PHASE):
        raise ValidationFailure(
            "the in-domain self-test is ordered before the domain-root worker exists"
        )
    if position >= ORDERED_PHASES.index(FIRST_PACKAGE_PHASE):
        raise ValidationFailure(
            "the in-domain self-test is ordered after a Go process sees package bytes"
        )
    if test["runs_after_phase"] != DOMAIN_ENTRY_PHASE:
        raise ValidationFailure("the in-domain self-test does not follow domain entry")
    if test["runs_before_phase"] != FIRST_PACKAGE_PHASE:
        raise ValidationFailure("the in-domain self-test does not precede package exposure")
    if sorted(test["guarantees_probed"]) != sorted(GUARANTEES):
        raise ValidationFailure("the in-domain self-test does not probe every guarantee")
    for field in (
        "package_bytes_read_by_domain",
        "go_process_started",
        "source_view_opened_by_worker",
        "on_failure_partial_mode_permitted",
        "on_failure_published",
    ):
        if test[field] is not False:
            raise ValidationFailure(f"the in-domain self-test violates {field}")
    for field in ("on_failure_tears_domain_down", "unperformable_test_is_a_failure"):
        if test[field] is not True:
            raise ValidationFailure(f"the in-domain self-test violates {field}")
    if test["on_failure_diagnostic"] not in HARDENED_DIAGNOSTICS:
        raise ValidationFailure("the in-domain self-test names an unknown failure diagnostic")


def reverified_members() -> list[str]:
    """Every mutable trusted-computing-base member, plus the frozen snapshot.

    review-cycle-4 finding R4-2: the manager obligation re-verified four
    identities while ``tcb-identity-verification`` had hashed twelve, so an
    omitted member could change during the operation with no end-of-operation
    check at all. The expected set is derived from the closed record here rather
    than restated, so a future member is covered the moment it is added.
    """
    return sorted((set(TCB_FIELDS) - TCB_CONSTANT_FIELDS) | {"source-snapshot"})


def validate_identity_reverification(profile: dict[str, Any]) -> None:
    """The end-of-operation check must be complete, and ordered after teardown."""
    check = profile["identity_reverification"]
    if check["phase"] != REVERIFICATION_PHASE:
        raise ValidationFailure("the end-of-operation check names another phase")
    if check["actor"] != "manager-parent":
        raise ValidationFailure("the end-of-operation check is not performed by the manager parent")
    actors = {item["name"]: item["actor"] for item in profile["ordered_phases"]}
    if actors.get(REVERIFICATION_PHASE) != check["actor"]:
        raise ValidationFailure("the end-of-operation check disagrees with the phase list actor")

    position = ORDERED_PHASES.index(REVERIFICATION_PHASE)
    if position <= ORDERED_PHASES.index(TEARDOWN_PHASE):
        raise ValidationFailure(
            "the trusted computing base is re-verified before the build domain has been destroyed "
            "and joined, so a surviving member can still change a trusted component afterwards"
        )
    if position >= ORDERED_PHASES.index(PUBLICATION_PHASE):
        raise ValidationFailure("the trusted computing base is re-verified after publication")
    if check["runs_after_phase"] != TEARDOWN_PHASE:
        raise ValidationFailure("the end-of-operation check does not follow domain teardown")
    if check["runs_before_phase"] != PUBLICATION_PHASE:
        raise ValidationFailure("the end-of-operation check does not precede publication")

    if check["reverified_members"] != reverified_members():
        missing = sorted(set(reverified_members()) - set(check["reverified_members"]))
        extra = sorted(set(check["reverified_members"]) - set(reverified_members()))
        raise ValidationFailure(
            "the end-of-operation check does not re-verify exactly the mutable trusted computing "
            f"base and the frozen snapshot; missing={missing}, extra={extra}"
        )
    if check["comparison"] != "byte-identical-record-and-digest":
        raise ValidationFailure(
            "the end-of-operation check accepts something weaker than a byte-identical record"
        )
    for field in (
        "domain_joined_before_reverification",
        "recomputes_complete_tcb_record",
        "observes_canonical_pinned_identities",
        "skipped_on_exact_cache_hit",
    ):
        if check[field] is not True:
            raise ValidationFailure(f"the end-of-operation check violates {field}")
    for field in (
        "partial_reverification_permitted",
        "restating_earlier_record_permitted",
        "published_on_change",
    ):
        if check[field] is not False:
            raise ValidationFailure(f"the end-of-operation check violates {field}")
    if check["on_change_diagnostic"] not in HARDENED_DIAGNOSTICS:
        raise ValidationFailure("the end-of-operation check names an unknown diagnostic")

    # A cache hit compiles nothing and creates no domain, so the phase list must
    # agree that the skipped span reaches this phase rather than stopping short.
    for item in profile["ordered_phases"]:
        if item["name"] == REVERIFICATION_PHASE and item["skipped_on_exact_cache_hit"] is not True:
            raise ValidationFailure(
                "an exact cache hit runs the end-of-operation check for an operation that "
                "established no domain"
            )
        if item["name"] == PUBLICATION_PHASE and item["skipped_on_exact_cache_hit"] is not False:
            raise ValidationFailure("an exact cache hit skips publication")


def validate_phase_list_documents() -> None:
    """One normative ordered list; every document mirrors it exactly.

    protocol/hardened-execution.md section 7.2 states the list. The manager
    profile attaches obligations to those phase names and MUST NOT publish an
    ordering of its own. Both are parsed here so neither can drift.
    """
    protocol = markdown_section(PROTOCOL_DOCUMENT, "### 7.2 ")
    numbered = re.findall(r"^\|\s*(\d+)\s*\|\s*`([a-z0-9-]+)`\s*\|", protocol, re.MULTILINE)
    if [name for _, name in numbered] != ORDERED_PHASES:
        raise ValidationFailure(
            "protocol/hardened-execution.md section 7.2 does not state the ordered phase list"
        )
    if [int(index) for index, _ in numbered] != list(range(1, len(ORDERED_PHASES) + 1)):
        raise ValidationFailure(
            "protocol/hardened-execution.md section 7.2 phase indices are not 1..n in order"
        )

    manager = markdown_section(MANAGER_DOCUMENT, "## 2. ")
    mirrored = re.findall(r"^\|\s*`([a-z0-9-]+)`\s*\|", manager, re.MULTILINE)
    if mirrored != ORDERED_PHASES:
        raise ValidationFailure(
            "profiles/manager-hardened.md does not mirror the ordered phase list exactly"
        )
    if re.search(r"^\s*\d+\.\s", manager, re.MULTILINE):
        raise ValidationFailure(
            "profiles/manager-hardened.md publishes an ordering of its own"
        )

    authority = load_json(HARDENED_SUITE / "vectors" / "hardened-execution-profile.json")[
        "phase_list_authority"
    ]
    if authority["normative_document"] != "protocol/hardened-execution.md":
        raise ValidationFailure("the hardened phase list names the wrong normative document")
    if authority["independent_orderings_permitted"] is not False:
        raise ValidationFailure("the hardened phase list permits an independent ordering")
    if (
        authority["domain_entry_phase"] != DOMAIN_ENTRY_PHASE
        or authority["first_package_exposure_phase"] != FIRST_PACKAGE_PHASE
        or authority["in_domain_actor"] != IN_DOMAIN_ACTOR
    ):
        raise ValidationFailure("the hardened phase list misnames its own boundaries")
    expected_mirrors = sorted(
        {
            "conformance/hardened/v1/vectors/hardened-execution-profile.json",
            "profiles/manager-hardened.md",
            "protocol/hardened-execution.md",
        }
    )
    if sorted(authority["mirrors"]) != expected_mirrors:
        raise ValidationFailure("the hardened phase list does not name every mirroring document")


def validate_host_build_declaration_document() -> None:
    """Section 6.3 must declare exactly the sources the tools hash.

    A construction whose declared inputs live only in a generator is a
    construction a second implementation cannot reproduce. The normative table
    is parsed here so the document, the schemas, the vector, and this validator
    cannot drift apart.
    """
    section = markdown_section(PROTOCOL_DOCUMENT, "### 6.3 ")
    rows = re.findall(
        r"^\|\s*`([a-z]+)`\s*\|([^|]+)\|\s*`([^`]+)`\s*\|([^|]+)\|\s*$",
        section,
        re.MULTILINE,
    )
    declared = {}
    for platform, _grammar, identifier_source, sources in rows:
        if platform not in HOST_BUILD_SOURCES:
            continue
        declared[platform] = (
            identifier_source.strip(),
            [item.strip() for item in re.findall(r"`([^`]+)`", sources)],
        )
    if set(declared) != set(HOST_BUILD_SOURCES):
        raise ValidationFailure(
            "protocol/hardened-execution.md section 6.3 does not declare the kernel build "
            f"identity sources for every platform; found {sorted(declared)}"
        )
    for platform, (identifier_source, sources) in declared.items():
        if sources != HOST_BUILD_SOURCES[platform]:
            raise ValidationFailure(
                f"section 6.3 declares {sources} for {platform}, but the profile hashes "
                f"{HOST_BUILD_SOURCES[platform]}"
            )
        if identifier_source != HOST_BUILD_IDENTIFIER_SOURCE[platform]:
            raise ValidationFailure(
                f"section 6.3 reads the {platform} build identifier from {identifier_source}, "
                f"but the profile reads it from {HOST_BUILD_IDENTIFIER_SOURCE[platform]}"
            )


def validate_reverification_documents() -> None:
    """The normative documents must state the complete end-of-operation check.

    review-cycle-4 finding R4-2: the executable phase model and the manager
    obligation disagreed with the protocol's own MUST, and nothing parsed either.
    """
    section = markdown_section(PROTOCOL_DOCUMENT, "#### End-of-operation re-verification")
    named = set(re.findall(r"`([a-z0-9_]+)`", section))
    missing = sorted(
        member
        for member in reverified_members()
        if member != "source-snapshot" and member not in named
    )
    if missing:
        raise ValidationFailure(
            "the end-of-operation re-verification section does not name every mutable "
            f"trusted-computing-base member: {missing}"
        )
    if "source snapshot" not in section:
        raise ValidationFailure(
            "the end-of-operation re-verification section does not name the frozen source snapshot"
        )
    for phrase in ("byte-identical", "subset"):
        if phrase not in section:
            raise ValidationFailure(
                f"the end-of-operation re-verification section does not state {phrase!r}"
            )

    manager = markdown_section(MANAGER_DOCUMENT, "## 2. ")
    row = next(
        (line for line in manager.splitlines() if line.startswith(f"| `{REVERIFICATION_PHASE}` |")),
        None,
    )
    if row is None:
        raise ValidationFailure(
            "profiles/manager-hardened.md states no obligation for identity-reverification"
        )
    for phrase in (
        "complete `hardened-tcb-v1` record",
        "byte-identical",
        "subset",
        "destroyed and joined",
    ):
        if phrase not in row:
            raise ValidationFailure(
                f"the manager re-verification obligation does not state {phrase!r}"
            )


def validate_failure_boundary(profile: dict[str, Any]) -> None:
    """Two boundaries, stated separately and honestly.

    Capability, qualification, and identity rejections happen before the build
    domain exists. The in-domain self-test necessarily runs after entry, so it
    is checked against the package-exposure boundary instead of being
    misreported as pre-entry.
    """
    boundary = profile["failure_boundary"]
    pre_entry = {
        "unqualified_platform": "hardened_profile_unsupported",
        "unavailable_capability_class": "hardened_capability_unavailable",
        "unprobed_capability_class": "hardened_capability_unavailable",
        "tcb_identity_failure": "hardened_tcb_identity_invalid",
        "domain_establishment_failure": "hardened_domain_establishment_failed",
        "portable_fallback_after_rejection": "hardened_profile_claim_forbidden",
    }
    pre_exposure = {
        "domain_entry_failure": "hardened_domain_establishment_failed",
        "self_test_not_denied": "hardened_domain_establishment_failed",
    }
    for name, expected in {**pre_entry, **pre_exposure}.items():
        case = boundary[name]
        if case["expected_error"] != expected:
            raise ValidationFailure(f"failure boundary {name} uses the wrong diagnostic")
        if case["fails_before"] not in ORDERED_PHASES:
            raise ValidationFailure(f"failure boundary {name} names an unknown phase")
        position = ORDERED_PHASES.index(case["fails_before"])
        if case["before_domain_entry"] is not (position < ORDERED_PHASES.index(DOMAIN_ENTRY_PHASE)):
            raise ValidationFailure(
                f"failure boundary {name} misreports its position against domain entry"
            )
        if case["before_package_exposure"] is not True:
            raise ValidationFailure(
                f"failure boundary {name} does not reject before any package byte reaches a Go process"
            )
        if case["rejects_build"] is not True:
            raise ValidationFailure(f"failure boundary {name} does not reject the build")
        for field in ("compiler_started", "published"):
            if case[field] is not False:
                raise ValidationFailure(f"failure boundary {name} starts a compiler or publishes")
    for name in pre_entry:
        if boundary[name]["before_domain_entry"] is not True:
            raise ValidationFailure(
                f"failure boundary {name} does not reject before domain entry"
            )
    breach = boundary["guarantee_violated_after_entry"]
    if (
        breach["expected_error"] != "hardened_domain_breach_detected"
        or breach["rejects_build"] is not True
        or breach["published"] is not False
    ):
        raise ValidationFailure("a post-entry guarantee violation does not reject and withhold publication")


def validate_evidence_shape(profile: dict[str, Any]) -> None:
    record = profile["capability_evidence_record"]
    if record["record_version"] != HARDENED_EVIDENCE_RECORD_VERSION:
        raise ValidationFailure("hardened evidence record version is wrong")
    if record["distinct_from_portable_record"] != PORTABLE_EVIDENCE_RECORD_VERSION:
        raise ValidationFailure("hardened evidence record does not name the portable record it differs from")
    if record["result_only"] is not True:
        raise ValidationFailure("hardened evidence record is not result-only")
    if sorted(record["excluded_from"]) != ["cache-key", "conformance-claim", "install-marker", "receipt"]:
        raise ValidationFailure("hardened evidence record is not excluded from every reusable output")
    if record["probe_timings"] != ["pre-domain-entry"]:
        raise ValidationFailure("hardened evidence probe timing is wrong")

    schema = validator_for("hardened-capability-evidence-v1.schema.json")
    for name, example in record["examples"].items():
        errors = list(schema.iter_errors(example))
        if errors:
            raise ValidationFailure(f"hardened evidence example {name}: {errors[0].message}")
        check_evidence_consistency(name, example, profile)


def check_evidence_consistency(label: str, record: dict[str, Any], profile: dict[str, Any]) -> None:
    applied = {
        item["name"] for item in record["capabilities"] if item["status"] == "applied"
    }
    names = [item["name"] for item in record["capabilities"]]
    if sorted(names) != sorted(CAPABILITY_CLASSES):
        raise ValidationFailure(f"evidence {label} does not carry exactly one entry per class")
    guarantee_names = [item["name"] for item in record["guarantees"]]
    if sorted(guarantee_names) != sorted(GUARANTEES):
        raise ValidationFailure(f"evidence {label} does not carry exactly one entry per guarantee")
    required = {
        item["name"]: set(item["required_capability_classes"]) for item in profile["guarantees"]
    }
    for item in record["guarantees"]:
        if item["established"] and not required[item["name"]] <= applied:
            raise ValidationFailure(
                f"evidence {label} reports {item['name']} established without every mapped class applied"
            )
    established = all(item["established"] for item in record["guarantees"])
    if (record["outcome"] == "established") != established:
        raise ValidationFailure(f"evidence {label} outcome contradicts its guarantee entries")
    if record["outcome"] == "rejected" and (
        record["rejected_before"] is None or record["diagnostic"] is None
    ):
        raise ValidationFailure(f"evidence {label} rejects without a phase and a diagnostic")


def validate_diagnostics(profile: dict[str, Any]) -> None:
    rows = profile["diagnostics"]
    codes = [item["code"] for item in rows]
    if sorted(codes) != codes or len(set(codes)) != len(codes):
        raise ValidationFailure("hardened diagnostics must be sorted and unique")
    if set(codes) != HARDENED_DIAGNOSTICS:
        raise ValidationFailure("hardened diagnostics do not match the specified set")
    if set(codes) & PORTABLE_DIAGNOSTICS:
        raise ValidationFailure("a hardened diagnostic collides with a portable execution code")
    for item in rows:
        if item["phase"] != "execution":
            raise ValidationFailure(f"{item['code']} is not an execution-phase diagnostic")
        if item["state"] not in {"blocked", "corrupt", "unsupported"}:
            raise ValidationFailure(f"{item['code']} has an unknown result state")
        if item["severity"] != "error":
            raise ValidationFailure(f"{item['code']} is not an error")
        if item["portable_code"] is not False:
            raise ValidationFailure(f"{item['code']} is marked as a portable code")


def validate_profile_vector() -> dict[str, Any]:
    profile = load_json(HARDENED_SUITE / "vectors" / "hardened-execution-profile.json")
    validate_profile_vector_document(profile)
    return profile


def validate_profile_vector_document(profile: dict[str, Any]) -> None:
    if profile["profile_version"] != HARDENED_PROFILE_VERSION:
        raise ValidationFailure("hardened profile vector names the wrong candidate version")
    if profile["hardened_profile"] != HARDENED_PROFILE_IDENTITY:
        raise ValidationFailure("hardened profile identity is wrong")
    if profile["execution_policy"] != HARDENED_EXECUTION_POLICY:
        raise ValidationFailure("hardened execution policy is wrong")
    if profile["portable_execution_policy"] != PORTABLE_EXECUTION_POLICY:
        raise ValidationFailure("hardened vector misnames the portable execution policy")
    if profile["portable_suite_modified"] is not False:
        raise ValidationFailure("hardened vector admits modifying the portable suite")
    if profile["partial_profile_permitted"] is not False:
        raise ValidationFailure("hardened vector permits a partial profile")
    if profile["portable_fallback_permitted"] is not False:
        raise ValidationFailure("hardened vector permits a silent portable fallback")
    if sorted(profile["drivers"]) != ["go-repository-v1", "go-v1"]:
        raise ValidationFailure("hardened vector does not cover both compiled drivers")

    if profile["identity_binding_version"] != IDENTITY_BINDING_VERSION:
        raise ValidationFailure("hardened profile vector names the wrong identity binding model")

    graph = profile["process_graph"]
    nodes = [item["node"] for item in graph]
    if nodes != GRAPH_NODES:
        raise ValidationFailure("hardened process graph is wrong")
    if [item["in_build_domain"] for item in graph] != [False, False, True, True, True]:
        raise ValidationFailure("hardened domain membership does not start at the worker")
    actors = {item["name"]: item["actor"] for item in profile["ordered_phases"]}
    performed: set[str] = set()
    for item in graph:
        if item["package_selectable"] is not False or item["selected_by"] != "manager":
            raise ValidationFailure(f"graph node {item['node']} is package selectable")
        for phase in item["performs_phases"]:
            if phase not in ORDERED_PHASES:
                raise ValidationFailure(f"graph node {item['node']} performs an unknown phase")
            if actors.get(phase) != item["node"]:
                raise ValidationFailure(
                    f"graph node {item['node']} claims {phase}, which names another actor"
                )
            if phase in performed:
                raise ValidationFailure(f"phase {phase} is performed by more than one graph node")
            performed.add(phase)
            if item["in_build_domain"] and ORDERED_PHASES.index(phase) <= ORDERED_PHASES.index(
                DOMAIN_ENTRY_PHASE
            ):
                raise ValidationFailure(
                    f"graph node {item['node']} performs {phase} before it exists"
                )
    unassigned = sorted(set(ORDERED_PHASES) - performed)
    if unassigned:
        raise ValidationFailure(f"phases with no actor in the process graph: {unassigned}")

    if not profile["package_influence_exclusions"]:
        raise ValidationFailure("hardened vector lists no package-influence exclusions")

    validate_guarantee_agreement(profile)
    validate_capability_inventory(profile)
    validate_platform_declarations(profile)
    validate_ordered_phases(profile)
    validate_failure_boundary(profile)
    validate_evidence_shape(profile)
    validate_diagnostics(profile)


def validate_adversarial_vector(profile: dict[str, Any]) -> None:
    vector = load_json(HARDENED_SUITE / "vectors" / "hardened-adversarial-vectors.json")
    if vector["evidence_status"] != "pending-native-validation":
        raise ValidationFailure("adversarial vectors claim evidence this revision does not have")
    if vector["qualified_platforms"] != []:
        raise ValidationFailure("adversarial vectors fabricate a qualified platform")

    # Five guarantees are containment properties an in-domain attacker can try
    # to break. The sixth, fail-closed-capability-preflight, is proved by the
    # forced-unavailable preflight cases below instead.
    containment = GUARANTEES - {"fail-closed-capability-preflight"}
    escapes = require_named(vector["escape_cases"], "hardened escape cases")
    covered: dict[str, int] = {name: 0 for name in containment}
    for name, case in escapes.items():
        guarantee = case["guarantee"]
        if guarantee not in containment:
            raise ValidationFailure(f"escape case {name} names an unknown containment guarantee")
        covered[guarantee] += 1
        if case["expected_outcome"] != "denied-by-kernel":
            raise ValidationFailure(f"escape case {name} does not require a kernel denial")
        if case["expected_error_if_observed_succeeding"] != "hardened_domain_breach_detected":
            raise ValidationFailure(f"escape case {name} does not map a success to a breach")
        if case["published"] is not False:
            raise ValidationFailure(f"escape case {name} publishes after an escape attempt")
        if case["native_evidence_required"] is not True:
            raise ValidationFailure(f"escape case {name} does not require native evidence")
        if case["evidence_status"] != "pending-native-validation":
            raise ValidationFailure(f"escape case {name} claims evidence that does not exist")
    thin = sorted(name for name, count in covered.items() if count < 1)
    if thin:
        raise ValidationFailure(f"guarantees without an adversarial escape case: {thin}")

    preflight = require_named(vector["capability_preflight_cases"], "hardened preflight cases")
    forced = {
        case["forced_unavailable"] for case in preflight.values() if case["forced_unavailable"]
    }
    missing = sorted(CAPABILITY_CLASSES - forced)
    if missing:
        raise ValidationFailure(f"capability classes without a forced-unavailable case: {missing}")
    for name, case in preflight.items():
        if case["before_domain_entry"] is not True:
            raise ValidationFailure(f"preflight case {name} does not reject before domain entry")
        for field in ("domain_created", "compiler_started", "published", "falls_back_to_portable"):
            if case[field] is not False:
                raise ValidationFailure(f"preflight case {name} violates the fail-closed boundary")
        if case["expected_error"] not in HARDENED_DIAGNOSTICS:
            raise ValidationFailure(f"preflight case {name} names an unknown diagnostic")

    influence = require_named(vector["package_influence_cases"], "hardened package-influence cases")
    if len(influence) < 10:
        raise ValidationFailure("hardened package-influence coverage is too thin")
    for name, case in influence.items():
        if case["expected_error"] != "hardened_package_influence_forbidden":
            raise ValidationFailure(f"package-influence case {name} uses the wrong diagnostic")
        if case["manifest_field"] is not None or case["descriptor_field"] is not None:
            raise ValidationFailure(
                f"package-influence case {name} implies a package-visible field exists"
            )
        for field in ("domain_created", "compiler_started", "published"):
            if case[field] is not False:
                raise ValidationFailure(f"package-influence case {name} reaches the compiler")
        if case["before_domain_entry"] is not True:
            raise ValidationFailure(f"package-influence case {name} is detected too late")

    identity = require_named(vector["identity_and_protocol_cases"], "hardened identity cases")
    for name, case in identity.items():
        if case["expected_error"] not in HARDENED_DIAGNOSTICS:
            raise ValidationFailure(f"identity case {name} names an unknown diagnostic")
        if case["published"] is not False:
            raise ValidationFailure(f"identity case {name} publishes after a failure")

    # review-cycle-4 finding R4-2: every member the end-of-operation check must
    # re-verify has an omission case of its own, and the ordering that made the
    # check meaningless has one too.
    reverification = require_named(vector["reverification_cases"], "hardened reverification cases")
    omitted = {
        case["omitted_member"]
        for case in reverification.values()
        if case["kind"] == "omitted-member"
    }
    missing = sorted(set(reverified_members()) - omitted)
    if missing:
        raise ValidationFailure(f"re-verified members without an omission case: {missing}")
    kinds = {case["kind"] for case in reverification.values()}
    if kinds != REVERIFICATION_CASE_KINDS:
        raise ValidationFailure("hardened reverification cases do not cover every failure kind")
    for name, case in reverification.items():
        if case["kind"] == "omitted-member":
            if case["omitted_member"] not in reverified_members():
                raise ValidationFailure(
                    f"reverification case {name} omits something the check does not re-verify"
                )
        elif case["omitted_member"] is not None:
            raise ValidationFailure(f"reverification case {name} names an omission it is not")
        if case["expected_error"] not in HARDENED_DIAGNOSTICS:
            raise ValidationFailure(f"reverification case {name} names an unknown diagnostic")
        if case["detected"] is not True:
            raise ValidationFailure(f"reverification case {name} is not detected")
        if not case["statement"]:
            raise ValidationFailure(f"reverification case {name} states nothing")
        for field in ("published", "cache_entry_written", "marker_updated"):
            if case[field] is not False:
                raise ValidationFailure(f"reverification case {name} still changes {field}")

    completeness = require_named(vector["tcb_completeness_cases"], "hardened TCB completeness cases")
    omitted = {case["field"] for case in completeness.values() if case["kind"] == "omission"}
    missing = sorted(set(TCB_FIELDS) - omitted)
    if missing:
        raise ValidationFailure(
            f"trusted-computing-base members without an omission case: {missing}"
        )
    kinds = {case["kind"] for case in completeness.values()}
    if kinds != TCB_CASE_KINDS:
        raise ValidationFailure("hardened TCB completeness cases do not cover every failure kind")
    for name, case in completeness.items():
        if case["field"] not in TCB_FIELDS:
            raise ValidationFailure(f"TCB completeness case {name} names a field outside the record")
        if case["expected_error"] not in HARDENED_DIAGNOSTICS:
            raise ValidationFailure(f"TCB completeness case {name} names an unknown diagnostic")
        if case["rejected_by"] not in TCB_ENFORCEMENT_SITES:
            raise ValidationFailure(f"TCB completeness case {name} names an unknown enforcement site")
        if not case["statement"]:
            raise ValidationFailure(f"TCB completeness case {name} states nothing")
        for field in ("receipt_rejected", "marker_rejected", "claim_rejected"):
            if case[field] is not True:
                raise ValidationFailure(f"TCB completeness case {name} is accepted by {field}")
        for field in ("cache_entry_reused", "published"):
            if case[field] is not False:
                raise ValidationFailure(f"TCB completeness case {name} reuses or publishes state")

    evidence = require_named(vector["evidence_cases"], "hardened evidence cases")
    for name, case in evidence.items():
        if case["record_valid"] is not False:
            raise ValidationFailure(f"evidence case {name} is not a negative case")
        if case["expected_error"] not in HARDENED_DIAGNOSTICS:
            raise ValidationFailure(f"evidence case {name} names an unknown diagnostic")
        for field in ("in_cache_key", "in_receipt", "in_marker", "in_claim", "build_permitted"):
            if case[field] is not False:
                raise ValidationFailure(f"evidence case {name} leaks evidence into reusable output")

    fallback = require_named(vector["no_fallback_cases"], "hardened no-fallback cases")
    for name in ("unqualified-platform-does-not-fall-back", "unavailable-capability-does-not-fall-back"):
        case = fallback[name]
        if case["resulting_execution_policy"] is not None:
            raise ValidationFailure(f"{name} still produces an execution policy")
        if case["portable_build_performed"] is not False or case["published"] is not False:
            raise ValidationFailure(f"{name} silently performs a portable build")
    hardened_hit = fallback["hardened-operation-does-not-adopt-portable-entry"]
    if hardened_hit["portable_entry_consulted"] is not False:
        raise ValidationFailure("a hardened operation consults a portable cache entry")


def check_tcb_record(label: str, record: Any) -> None:
    """The concrete trusted computing base must be complete and closed.

    review-cycle-2 finding R2-1: a record that names only the supervisor, the
    worker, and the toolchain lets two materially different trusted bases hash
    to one digest. Every member below identifies something whose replacement
    changes what the kernel enforces, and every one of them is checked here on
    every record the suite publishes, not only on the schema examples.
    """
    if not isinstance(record, dict):
        raise ValidationFailure(f"{label}: trusted computing base is not a record")
    if sorted(record) != TCB_FIELDS:
        missing = sorted(set(TCB_FIELDS) - set(record))
        extra = sorted(set(record) - set(TCB_FIELDS))
        raise ValidationFailure(
            f"{label}: trusted computing base is not the closed hardened-tcb-v1 record; "
            f"missing={missing}, extra={extra}"
        )
    if record["record_version"] != TCB_RECORD_VERSION:
        raise ValidationFailure(f"{label}: unknown trusted-computing-base record version")
    if record["hardened_profile"] != HARDENED_PROFILE_IDENTITY:
        raise ValidationFailure(f"{label}: trusted computing base names another profile")
    if record["execution_policy"] != HARDENED_EXECUTION_POLICY:
        raise ValidationFailure(f"{label}: trusted computing base names another execution policy")
    platform = record["platform"]
    if platform not in PLATFORM_BACKENDS:
        raise ValidationFailure(f"{label}: unknown hardened platform {platform}")
    if record["enforcement_backend"] != PLATFORM_BACKENDS[platform]:
        raise ValidationFailure(
            f"{label}: platform {platform} is paired with a backend another platform declares"
        )

    host = record["host"]
    if not isinstance(host, dict) or sorted(host) != TCB_HOST_FIELDS:
        raise ValidationFailure(f"{label}: host identity is not the closed observed-host record")
    if host["kind"] != TCB_HOST_KIND:
        raise ValidationFailure(
            f"{label}: host kind is {host['kind']!r}, but every backend this revision declares "
            f"is an operating-system-kernel mechanism"
        )
    for field in ("identity", "version"):
        if not isinstance(host[field], str) or not host[field]:
            raise ValidationFailure(f"{label}: host {field} is not an observed value")
    if host["identity"] != CANONICAL_HOST_IDENTITY[platform]:
        raise ValidationFailure(
            f"{label}: platform {platform} observed the kernel identity "
            f"{host['identity']!r}, which another platform declares"
        )
    if not HOST_VERSION_PATTERN.fullmatch(host["version"]):
        raise ValidationFailure(
            f"{label}: observed kernel release {host['version']!r} is outside the bounded "
            f"release grammar, so one kernel would have more than one spelling"
        )

    # review-cycle-4 finding R4-1: a null or descriptive build value cannot
    # separate two materially different kernels that report the same platform and
    # the same release, so a claimed-complete record without a digested kernel
    # build identity is invalid here rather than merely under-specified.
    build = host["build"]
    if build is None:
        raise ValidationFailure(
            f"{label}: the observed host reports no kernel build identity, so two materially "
            f"different kernels could produce this trusted-computing-base record"
        )
    if not isinstance(build, dict) or sorted(build) != HOST_BUILD_FIELDS:
        raise ValidationFailure(
            f"{label}: kernel build identity is not the closed {HOST_BUILD_ALGORITHM} record"
        )
    if build["algorithm"] != HOST_BUILD_ALGORITHM:
        raise ValidationFailure(f"{label}: kernel build identity uses an unknown algorithm")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(build["content_sha256"])):
        raise ValidationFailure(f"{label}: kernel build identity carries no content digest")
    if not HOST_BUILD_IDENTIFIER_PATTERN[platform].fullmatch(str(build["identifier"])):
        raise ValidationFailure(
            f"{label}: kernel build identifier {build['identifier']!r} is not in the grammar "
            f"platform {platform} declares"
        )

    backend = record["backend"]
    if not isinstance(backend, dict) or sorted(backend) != TCB_BACKEND_FIELDS:
        raise ValidationFailure(f"{label}: enforcement-backend identity is not the closed record")
    parsed = parse_backend_version(backend["version"])
    if parsed is None:
        raise ValidationFailure(
            f"{label}: observed backend version {backend['version']!r} is outside the "
            f"{BACKEND_VERSION_GRAMMAR} grammar, so it cannot be compared with a minimum"
        )
    if parsed[0] != BACKEND_VERSION_SERIES[record["enforcement_backend"]]:
        raise ValidationFailure(
            f"{label}: backend {record['enforcement_backend']} reports a version in the "
            f"{parsed[0]!r} series, which another backend declares"
        )
    settings = []
    for entry in backend["configuration"]:
        if not isinstance(entry, dict) or sorted(entry) != ["observed_value", "setting"]:
            raise ValidationFailure(
                f"{label}: backend configuration entry is not a closed observation record"
            )
        settings.append(entry["setting"])
    if settings != sorted(settings) or len(settings) != len(set(settings)):
        raise ValidationFailure(f"{label}: backend configuration is not a sorted unique set")

    components = record["trusted_components"]
    if not isinstance(components, list):
        raise ValidationFailure(f"{label}: trusted components are not a list")
    ordered = []
    for entry in components:
        if not isinstance(entry, dict):
            raise ValidationFailure(
                f"{label}: a trusted component is named without a cryptographic identity"
            )
        if sorted(entry) != TCB_COMPONENT_FIELDS:
            raise ValidationFailure(f"{label}: trusted component is not the closed component record")
        if entry["kind"] not in TCB_COMPONENT_KINDS:
            raise ValidationFailure(f"{label}: trusted component names an unknown component kind")
        if entry["algorithm"] not in TCB_COMPONENT_ALGORITHMS:
            raise ValidationFailure(f"{label}: trusted component uses an unknown digest algorithm")
        if entry["algorithm"] not in COMPONENT_ALGORITHM_BY_KIND[entry["kind"]]:
            raise ValidationFailure(
                f"{label}: trusted component of kind {entry['kind']} carries a "
                f"{entry['algorithm']} digest, which that kind does not admit"
            )
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(entry["content_sha256"])):
            raise ValidationFailure(f"{label}: trusted component carries no content digest")
        ordered.append((entry["kind"], entry["name"]))
    if ordered != sorted(ordered) or len(ordered) != len(set(ordered)):
        raise ValidationFailure(f"{label}: trusted components are not a sorted unique set")


def validate_tcb_completeness(vector: dict[str, Any]) -> None:
    """The completeness statement must cover the whole closed record."""
    completeness = vector["tcb_completeness"]
    if completeness["record_version"] != TCB_RECORD_VERSION:
        raise ValidationFailure("hardened TCB completeness names the wrong record version")
    if completeness["closed"] is not True:
        raise ValidationFailure("hardened TCB completeness does not state a closed record")
    if completeness["unconstrained_string_components_permitted"] is not False:
        raise ValidationFailure(
            "hardened TCB completeness still permits an unconstrained string trusted component"
        )
    if sorted(completeness["component_digest_algorithms"]) != sorted(TCB_COMPONENT_ALGORITHMS):
        raise ValidationFailure("hardened trusted-component digest algorithms are wrong")

    admitted = completeness["component_algorithm_by_kind"]
    if set(admitted) != TCB_COMPONENT_KINDS:
        raise ValidationFailure(
            "the component algorithm-by-kind table does not cover every component kind"
        )
    for kind, algorithms in admitted.items():
        if set(algorithms) != COMPONENT_ALGORITHM_BY_KIND[kind]:
            raise ValidationFailure(
                f"component kind {kind} publishes algorithms it does not admit"
            )

    if completeness["backend_version_grammar"] != BACKEND_VERSION_GRAMMAR:
        raise ValidationFailure("hardened TCB completeness names the wrong backend version grammar")
    if completeness["backend_version_series"] != BACKEND_VERSION_SERIES:
        raise ValidationFailure("the backend version series table does not match the declarations")
    if completeness["canonical_host_identity"] != CANONICAL_HOST_IDENTITY:
        raise ValidationFailure("the canonical host identity table does not match the declarations")
    if completeness["host_kind"] != TCB_HOST_KIND:
        raise ValidationFailure("hardened TCB completeness admits a host kind this revision cannot")

    # review-cycle-4 finding R4-1: completeness of the observed host is exactly
    # the claim that failed, so the statement carries the declaration it rests on.
    build = completeness["host_build_identity"]
    if build["algorithm"] != HOST_BUILD_ALGORITHM:
        raise ValidationFailure("the kernel build identity names the wrong algorithm")
    if build["required"] is not True or build["nullable"] is not False:
        raise ValidationFailure("hardened TCB completeness admits a host with no kernel build identity")
    if build["identifier_equals_source"] is not True:
        raise ValidationFailure("the kernel build identifier is detached from its declared source")
    if build["absent_source_fails_closed"] is not True:
        raise ValidationFailure("an unreadable build-identity source does not fail closed")
    if build["fixture_version"] != HOST_BUILD_FIXTURE_VERSION:
        raise ValidationFailure("the kernel build identity names the wrong fixture set")
    if build["expected_error"] not in HARDENED_DIAGNOSTICS:
        raise ValidationFailure("the kernel build identity names an unknown diagnostic")
    if build["rejected_before_phase"] not in ORDERED_PHASES:
        raise ValidationFailure("the kernel build identity rejects before an unknown phase")
    if ORDERED_PHASES.index(build["rejected_before_phase"]) > ORDERED_PHASES.index(
        DOMAIN_ENTRY_PHASE
    ):
        raise ValidationFailure(
            "a kernel build identity failure is detected after the build domain already exists"
        )
    if set(build["declarations"]) != set(HOST_BUILD_SOURCES):
        raise ValidationFailure(
            "the kernel build identity declarations do not cover every hardened platform"
        )
    for platform, declaration in build["declarations"].items():
        if declaration["sources"] != HOST_BUILD_SOURCES[platform]:
            raise ValidationFailure(
                f"platform {platform} declares build-identity sources the profile does not"
            )
        if declaration["identifier_source"] != HOST_BUILD_IDENTIFIER_SOURCE[platform]:
            raise ValidationFailure(f"platform {platform} declares the wrong identifier source")

    fields = require_named_key(completeness["bound_fields"], "field", "hardened TCB bound fields")
    if sorted(fields) != TCB_FIELDS:
        raise ValidationFailure(
            "hardened TCB completeness does not cover exactly the closed record members"
        )
    for name, item in fields.items():
        if not item["identifies"]:
            raise ValidationFailure(f"hardened TCB field {name} states what it identifies nowhere")
        if not item["enforced_by"]:
            raise ValidationFailure(f"hardened TCB field {name} names no enforcement")

    relations = require_named(completeness["relations"], "hardened TCB relations")
    if set(relations) != TCB_RELATIONS:
        raise ValidationFailure("hardened TCB relations do not match the specified set")
    for name, item in relations.items():
        if item["enforced_by"] not in TCB_ENFORCEMENT_SITES:
            raise ValidationFailure(f"hardened TCB relation {name} names an unknown enforcement site")
        if item["expected_error"] not in HARDENED_DIAGNOSTICS:
            raise ValidationFailure(f"hardened TCB relation {name} names an unknown diagnostic")
        if not item["statement"]:
            raise ValidationFailure(f"hardened TCB relation {name} states nothing")

    narrower = completeness["narrower_record_than_actually_trusted"]
    if narrower["permitted"] is not False:
        raise ValidationFailure(
            "hardened TCB completeness permits a record narrower than what is actually trusted"
        )
    if narrower["expected_error"] not in HARDENED_DIAGNOSTICS:
        raise ValidationFailure("a narrower-than-trusted record names an unknown diagnostic")
    if not narrower["statement"]:
        raise ValidationFailure("a narrower-than-trusted record states nothing")


def validate_tcb_rotation(vector: dict[str, Any]) -> None:
    """Rotate every bound identity and require the cache key to move.

    A rotation the key does not notice is an identity that does not bind. The
    package-invisible rotations carry the argument: nothing a package can see
    differs, so only the trusted computing base can have moved the key.
    """
    base = vector["cache_identity"]["hardened"]
    base_key = base["cache_key"]
    base_visible = {key: value for key, value in base["input"].items() if key != "hardened"}
    cases = require_named(vector["tcb_rotation_cases"], "hardened TCB rotation cases")
    keys: dict[str, str] = {base_key: "hardened"}
    invisible = 0
    for name, case in cases.items():
        check_tcb_record(f"rotation {name}", case["tcb"])
        if case["tcb"] == base["tcb"]:
            raise ValidationFailure(f"rotation {name} rotates nothing")
        if case["tcb_digest"] != tcb_digest(case["tcb"]):
            raise ValidationFailure(f"rotation {name} publishes a digest its own record disproves")
        member = case["input"]["hardened"]
        if member["profile"] != HARDENED_PROFILE_IDENTITY:
            raise ValidationFailure(f"rotation {name} drops the hardened profile identity")
        if member["tcb"]["content_sha256"] != case["tcb_digest"]:
            raise ValidationFailure(f"rotation {name} input does not carry its own TCB digest")
        recomputed = ccj1_sha256(case["input"])
        if recomputed != case["cache_key"]:
            raise ValidationFailure(f"rotation {name} cache key is not reproducible from its input")
        if case["base_cache_key"] != base_key:
            raise ValidationFailure(f"rotation {name} compares against the wrong base key")
        if recomputed == base_key or case["cache_key_differs_from_base"] is not True:
            raise ValidationFailure(
                f"rotation {name} does not move the cache key, so that identity does not bind"
            )
        if recomputed in keys:
            raise ValidationFailure(f"rotation {name} aliases {keys[recomputed]}")
        keys[recomputed] = name

        visible = {key: value for key, value in case["input"].items() if key != "hardened"}
        changed = visible != base_visible
        if case["package_visible_input_changed"] is not changed:
            raise ValidationFailure(
                f"rotation {name} misreports whether a package-visible value changed"
            )
        if changed and not case["package_visible_change_reason"]:
            raise ValidationFailure(f"rotation {name} changes a visible value without a reason")
        if not changed:
            invisible += 1
            if case["package_visible_change_reason"] is not None:
                raise ValidationFailure(f"rotation {name} states a reason it does not need")
        for field in (
            "receipt_rejected_against_base",
            "marker_rejected_against_base",
            "claim_rejected_against_base",
        ):
            if case[field] is not True:
                raise ValidationFailure(f"rotation {name} lets another identity satisfy {field}")
        if case["published_from_another_identity"] is not False:
            raise ValidationFailure(f"rotation {name} publishes under another trusted computing base")
        if case["expected_error_if_reused"] not in HARDENED_DIAGNOSTICS:
            raise ValidationFailure(f"rotation {name} names an unknown diagnostic")

    if invisible < 1:
        raise ValidationFailure(
            "no rotation isolates the trusted computing base from every package-visible value"
        )
    fields = require_named_key(
        vector["tcb_completeness"]["bound_fields"], "field", "hardened TCB bound fields"
    )
    for name, item in fields.items():
        rotations = item["rotated_by"]
        if name in TCB_CONSTANT_FIELDS:
            if rotations:
                raise ValidationFailure(
                    f"hardened TCB field {name} is fixed by this revision but claims a rotation"
                )
            continue
        if not rotations:
            raise ValidationFailure(f"hardened TCB field {name} is never rotated, so it is unproven")
        unknown = sorted(set(rotations) - set(cases))
        if unknown:
            raise ValidationFailure(f"hardened TCB field {name} names unknown rotations: {unknown}")

    # review-cycle-3 finding R3-1: rotating the trusted_components array is not
    # coverage for the kind, the name, the algorithm, the tree membership, an
    # entry type, or a link substitution. Each facet is tracked on its own, and
    # each named rotation must actually declare that facet.
    coverage = require_named_key(
        vector["tcb_completeness"]["component_rotation_coverage"],
        "aspect",
        "hardened trusted-component rotation coverage",
    )
    if set(coverage) != COMPONENT_ASPECTS:
        raise ValidationFailure(
            "trusted-component rotation coverage does not cover exactly the mutable facets"
        )
    for aspect, item in coverage.items():
        rotations = item["rotated_by"]
        if not rotations:
            raise ValidationFailure(
                f"trusted-component facet {aspect} is never rotated, so it is unproven"
            )
        if not item["statement"]:
            raise ValidationFailure(f"trusted-component facet {aspect} states nothing")
        for name in rotations:
            if name not in cases:
                raise ValidationFailure(f"facet {aspect} names an unknown rotation {name}")
            if aspect not in cases[name]["rotated_component_aspects"]:
                raise ValidationFailure(
                    f"rotation {name} is credited with facet {aspect} it does not declare"
                )
    for name, case in cases.items():
        declared = case["rotated_component_aspects"]
        unknown = sorted(set(declared) - COMPONENT_ASPECTS)
        if unknown:
            raise ValidationFailure(f"rotation {name} declares unknown component facets: {unknown}")
        if declared and "trusted_components" not in case["rotated_fields"]:
            raise ValidationFailure(
                f"rotation {name} claims a component facet without rotating trusted_components"
            )

    # review-cycle-4 finding R4-1: the same per-facet rule the components got.
    # Rotating the host record is not coverage for the declared build-identity
    # sources two materially different kernels differ in.
    host_coverage = require_named_key(
        vector["tcb_completeness"]["host_build_identity"]["host_build_rotation_coverage"],
        "aspect",
        "hardened kernel build identity rotation coverage",
    )
    if set(host_coverage) != HOST_BUILD_ASPECTS:
        raise ValidationFailure(
            "kernel build identity rotation coverage does not cover exactly the mutable facets"
        )
    for aspect, item in host_coverage.items():
        rotations = item["rotated_by"]
        if not rotations:
            raise ValidationFailure(
                f"kernel build identity facet {aspect} is never rotated, so it is unproven"
            )
        if not item["statement"]:
            raise ValidationFailure(f"kernel build identity facet {aspect} states nothing")
        for name in rotations:
            if name not in cases:
                raise ValidationFailure(f"facet {aspect} names an unknown rotation {name}")
            if aspect not in cases[name]["rotated_host_build_aspects"]:
                raise ValidationFailure(
                    f"rotation {name} is credited with facet {aspect} it does not declare"
                )
    for name, case in cases.items():
        declared = case["rotated_host_build_aspects"]
        unknown = sorted(set(declared) - HOST_BUILD_ASPECTS)
        if unknown:
            raise ValidationFailure(
                f"rotation {name} declares unknown kernel build facets: {unknown}"
            )
        if declared and "host" not in case["rotated_fields"]:
            raise ValidationFailure(
                f"rotation {name} claims a kernel build facet without rotating host"
            )

    # The rotation that answers the finding directly: a kernel that agrees with
    # the base on everything a record published before this revision, and differs
    # only in a declared build-identity source, must still move the cache key.
    rebuilt = cases["rotate-host-build-source"]
    base_host = base["tcb"]["host"]
    rebuilt_host = rebuilt["tcb"]["host"]
    for field in ("kind", "identity", "version"):
        if base_host[field] != rebuilt_host[field]:
            raise ValidationFailure(
                f"rotate-host-build-source differs from the base in host {field}, so it does not "
                f"isolate the kernel build identity"
            )
    if base_host["build"]["identifier"] != rebuilt_host["build"]["identifier"]:
        raise ValidationFailure(
            "rotate-host-build-source differs from the base in the build identifier, so it does "
            "not isolate the declared build-identity sources"
        )
    if base_host["build"]["content_sha256"] == rebuilt_host["build"]["content_sha256"]:
        raise ValidationFailure(
            "rotate-host-build-source reproduces the base kernel build digest, so two materially "
            "different kernels still share one trusted computing base"
        )


def recompute_component_fixture(name: str, fixture: dict[str, Any]) -> str:
    """Recompute one published fixture from its own bytes."""
    algorithm = fixture["algorithm"]
    if algorithm == COMPONENT_FILE_ALGORITHM:
        if fixture["entries"] is not None:
            raise ValidationFailure(f"file fixture {name} carries tree entries")
        content = fixture["file"]["content"].encode("utf-8")
        if len(content) != fixture["file"]["content_byte_length"]:
            raise ValidationFailure(f"file fixture {name} misreports its own byte length")
        return component_file_digest(content)
    if fixture["file"] is not None:
        raise ValidationFailure(f"tree fixture {name} carries file content")
    entries: list[tuple[str, bytes, bytes]] = []
    paths = {entry["path"]: entry["kind"] for entry in fixture["entries"]}
    for entry in fixture["entries"]:
        path = entry["path"].encode("utf-8")
        payload = entry["payload"].encode("utf-8")
        if len(path) != entry["path_byte_length"] or len(payload) != entry["payload_byte_length"]:
            raise ValidationFailure(f"tree fixture {name} misreports an entry byte length")
        if entry["kind"] == "D" and payload:
            raise ValidationFailure(f"tree fixture {name} gives a directory a payload")

        # A walk that skipped a parent, or invented an absolute or escaping
        # path, is not a walk of one tree. The construction only means something
        # if the fixture is a tree the construction could have produced.
        if entry["path"].startswith("/") or ".." in entry["path"].split("/"):
            raise ValidationFailure(f"tree fixture {name} names a path outside its own root")
        if "" in entry["path"].split("/"):
            raise ValidationFailure(f"tree fixture {name} names an empty path component")
        if "/" in entry["path"]:
            parent = entry["path"].rsplit("/", 1)[0]
            if paths.get(parent) != "D":
                raise ValidationFailure(
                    f"tree fixture {name} walks {entry['path']} without its parent directory"
                )

        # A symbolic link must be relative, non-dangling, and resolve within the
        # root, so its referent has its own record in the same tree.
        if entry["kind"] == "L":
            if entry["payload"].startswith("/"):
                raise ValidationFailure(f"tree fixture {name} carries an absolute symbolic link")
            base = entry["path"].rsplit("/", 1)[0] if "/" in entry["path"] else ""
            parts = [] if not base else base.split("/")
            for part in entry["payload"].split("/"):
                if part == "..":
                    if not parts:
                        raise ValidationFailure(
                            f"tree fixture {name} carries a symbolic link escaping its root"
                        )
                    parts.pop()
                elif part not in ("", "."):
                    parts.append(part)
            if "/".join(parts) not in paths:
                raise ValidationFailure(
                    f"tree fixture {name} carries a dangling symbolic link to {entry['payload']}"
                )

        entries.append((entry["kind"], path, payload))
    return component_tree_digest(entries)


def validate_component_digest_fixtures(vector: dict[str, Any]) -> None:
    """Reproduce every published component digest from its published bytes.

    review-cycle-3 finding R3-1: the two algorithms were names with no
    construction, so content_sha256 was not independently reproducible. Every
    fixture is recomputed here from the document's rules rather than trusted,
    and every trusted-component digest anywhere in the suite must come from one.
    """
    fixtures_block = vector["component_digest_fixtures"]
    if fixtures_block["version"] != COMPONENT_FIXTURE_VERSION:
        raise ValidationFailure("component digest fixtures name the wrong fixture-set version")
    if fixtures_block["file_algorithm"] != COMPONENT_FILE_ALGORITHM:
        raise ValidationFailure("component digest fixtures name the wrong file algorithm")
    if fixtures_block["tree_algorithm"] != COMPONENT_TREE_ALGORITHM:
        raise ValidationFailure("component digest fixtures name the wrong tree algorithm")
    if set(fixtures_block["tree_entry_kinds"]) != COMPONENT_TREE_ENTRY_KINDS:
        raise ValidationFailure("component tree entry kinds are not exactly D, F, and L")

    fixtures = require_named(fixtures_block["fixtures"], "component digest fixtures")
    digests: dict[str, str] = {}
    for name, fixture in fixtures.items():
        recomputed = recompute_component_fixture(name, fixture)
        if recomputed != fixture["expected_sha256"]:
            raise ValidationFailure(
                f"component fixture {name} publishes {fixture['expected_sha256']} but its own "
                f"bytes produce {recomputed}"
            )
        if recomputed in digests:
            raise ValidationFailure(f"component fixture {name} aliases {digests[recomputed]}")
        digests[recomputed] = name
    if fixtures_block["all_digests_distinct"] is not True:
        raise ValidationFailure("component digest fixtures do not claim distinct digests")

    # The two structural claims the tree construction rests on, checked rather
    # than asserted: an empty tree and an empty file are different values, and a
    # regular file holding a link's referent bytes is a different tree.
    empty_file = fixtures["empty-file-component"]["expected_sha256"]
    empty_tree = fixtures["empty-tree-component"]["expected_sha256"]
    if empty_file == empty_tree:
        raise ValidationFailure("the empty file and the empty tree share one digest")
    base_tree = fixtures["capability-probe-suite"]
    substituted = fixtures["capability-probe-suite-link-substituted"]
    if base_tree["expected_sha256"] == substituted["expected_sha256"]:
        raise ValidationFailure(
            "a symbolic link replaced by a regular file reproduces the tree it replaced"
        )
    base_links = [entry for entry in base_tree["entries"] if entry["kind"] == "L"]
    if not base_links:
        raise ValidationFailure("the base tree fixture contains no symbolic link to substitute")
    referent = base_links[0]["payload"]
    referent_paths = [
        entry
        for entry in base_tree["entries"]
        if entry["path"].rsplit("/", 1)[-1] == referent and entry["kind"] == "F"
    ]
    if not referent_paths:
        raise ValidationFailure("the base tree fixture's link does not resolve within the tree")
    replaced = [
        entry for entry in substituted["entries"] if entry["path"] == base_links[0]["path"]
    ]
    if len(replaced) != 1 or replaced[0]["kind"] != "F":
        raise ValidationFailure("the link-substitution fixture does not replace the link")
    if replaced[0]["payload"] != referent_paths[0]["payload"]:
        raise ValidationFailure(
            "the link-substitution fixture does not hold the referent's exact bytes, so it does "
            "not test the substitution the tree algorithm must notice"
        )

    published = set(digests)
    checked = 0
    for label, record in conforming_tcb_records():
        for entry in record["trusted_components"]:
            checked += 1
            if entry["content_sha256"] not in published:
                raise ValidationFailure(
                    f"{label}: trusted component {entry['name']} carries a digest no published "
                    f"fixture reproduces, so it is an invented identity"
                )
    if checked < 1:
        raise ValidationFailure("no conforming trusted computing base names a trusted component")


def recompute_host_build_fixture(name: str, fixture: dict[str, Any]) -> str:
    """Recompute one published kernel build identity from its own bytes."""
    platform = fixture["platform"]
    if platform not in HOST_BUILD_SOURCES:
        raise ValidationFailure(f"host build fixture {name} names an unknown platform")
    if fixture["host_identity"] != CANONICAL_HOST_IDENTITY[platform]:
        raise ValidationFailure(
            f"host build fixture {name} observes a kernel identity its own platform does not declare"
        )
    if not HOST_VERSION_PATTERN.fullmatch(fixture["host_version"]):
        raise ValidationFailure(f"host build fixture {name} observes a release outside the grammar")

    declared = HOST_BUILD_SOURCES[platform]
    observed = [entry["name"] for entry in fixture["sources"]]
    if observed != declared:
        raise ValidationFailure(
            f"host build fixture {name} observes {observed}, but platform {platform} declares "
            f"{declared} in that order"
        )
    if fixture["source_count"] != len(declared):
        raise ValidationFailure(f"host build fixture {name} misreports its own source count")

    sources: list[tuple[bytes, bytes]] = []
    for entry in fixture["sources"]:
        source_name = entry["name"].encode("utf-8")
        value = entry["value"].encode("utf-8")
        if not value:
            raise ValidationFailure(
                f"host build fixture {name} observes an empty {entry['name']}, which fails closed"
            )
        if len(source_name) != entry["name_byte_length"] or len(value) != entry["value_byte_length"]:
            raise ValidationFailure(f"host build fixture {name} misreports a source byte length")
        sources.append((source_name, value))

    # The identifier is the exact value of the platform's declared identifier
    # source. A fixture free to state any identifier would prove nothing about
    # the identifier a real host must publish.
    identifier_source = HOST_BUILD_IDENTIFIER_SOURCE[platform]
    declared_identifier = next(
        entry["value"] for entry in fixture["sources"] if entry["name"] == identifier_source
    )
    if fixture["identifier"] != declared_identifier:
        raise ValidationFailure(
            f"host build fixture {name} publishes an identifier that is not the value of its own "
            f"{identifier_source} source"
        )
    if not HOST_BUILD_IDENTIFIER_PATTERN[platform].fullmatch(fixture["identifier"]):
        raise ValidationFailure(
            f"host build fixture {name} carries an identifier platform {platform} cannot report"
        )
    if len(fixture["identifier"].encode("utf-8")) != fixture["identifier_byte_length"]:
        raise ValidationFailure(f"host build fixture {name} misreports its identifier byte length")

    return host_build_digest(
        fixture["host_identity"], fixture["host_version"], fixture["identifier"], sources
    )


def validate_host_build_fixtures(vector: dict[str, Any]) -> None:
    """Reproduce every published kernel build identity from its published bytes.

    review-cycle-4 finding R4-1: ``host.build`` was an optional descriptive
    string, so two materially different kernels reporting one platform and one
    release produced one trusted-computing-base record, one cache key, one
    receipt, one marker, and one claim. Every fixture is recomputed here from the
    document's construction rather than trusted, every observed host in the suite
    must trace to one, and the non-aliasing claim is checked rather than asserted.
    """
    block = vector["host_build_fixtures"]
    if block["version"] != HOST_BUILD_FIXTURE_VERSION:
        raise ValidationFailure("host build fixtures name the wrong fixture-set version")
    if block["algorithm"] != HOST_BUILD_ALGORITHM:
        raise ValidationFailure("host build fixtures name the wrong algorithm")
    if block["nullable_build_permitted"] is not False:
        raise ValidationFailure("host build fixtures still permit a null kernel build identity")
    if block["unreadable_source_permitted"] is not False:
        raise ValidationFailure("host build fixtures permit an unreadable build-identity source")

    declarations = block["declarations"]
    if set(declarations) != set(HOST_BUILD_SOURCES):
        raise ValidationFailure("the build-identity declarations do not cover every platform")
    for platform, declaration in declarations.items():
        if declaration["sources"] != HOST_BUILD_SOURCES[platform]:
            raise ValidationFailure(
                f"platform {platform} declares build-identity sources the profile does not"
            )
        if declaration["identifier_source"] != HOST_BUILD_IDENTIFIER_SOURCE[platform]:
            raise ValidationFailure(f"platform {platform} declares the wrong identifier source")
        if declaration["identifier_source"] not in declaration["sources"]:
            raise ValidationFailure(
                f"platform {platform} reads its identifier from a source the digest does not cover"
            )

    fixtures = require_named(block["fixtures"], "host build fixtures")
    digests: dict[str, str] = {}
    for name, fixture in fixtures.items():
        recomputed = recompute_host_build_fixture(name, fixture)
        if recomputed != fixture["expected_sha256"]:
            raise ValidationFailure(
                f"host build fixture {name} publishes {fixture['expected_sha256']} but its own "
                f"bytes produce {recomputed}"
            )
        if recomputed in digests:
            raise ValidationFailure(f"host build fixture {name} aliases {digests[recomputed]}")
        digests[recomputed] = name
    if block["all_digests_distinct"] is not True:
        raise ValidationFailure("host build fixtures do not claim distinct digests")

    # The finding itself, as a checked property: two kernels that agree on
    # platform, release, and build identifier, and differ only in a declared
    # build-identity source, must not share a digest.
    base = fixtures["macos-host-build"]
    rebuilt = fixtures["macos-host-build-recompiled-kernel"]
    for field in ("platform", "host_identity", "host_version", "identifier"):
        if base[field] != rebuilt[field]:
            raise ValidationFailure(
                "the recompiled-kernel fixture differs from the base in "
                f"{field}, so it does not test the aliasing review cycle 4 found"
            )
    differing = [
        left["name"]
        for left, right in zip(base["sources"], rebuilt["sources"])
        if left["value"] != right["value"]
    ]
    if not differing:
        raise ValidationFailure("the recompiled-kernel fixture observes the same kernel as the base")
    if base["expected_sha256"] == rebuilt["expected_sha256"]:
        raise ValidationFailure(
            "two kernels differing only in a declared build-identity source share one build digest"
        )

    # Field separation, checked rather than asserted: an implementation that
    # hashed the declared source values as one concatenated blob would give this
    # probe and the base one digest. The unit tests cover the complementary
    # property — that the per-field length framing separates two field lists
    # whose whole hashed byte stream would otherwise concatenate identically.
    shifted = fixtures["macos-host-build-source-boundary-shift"]
    if "".join(entry["value"] for entry in shifted["sources"]) != "".join(
        entry["value"] for entry in base["sources"]
    ):
        raise ValidationFailure(
            "the boundary-shift fixture does not carry the base's concatenated source bytes, so it "
            "does not test the framing"
        )
    if [entry["value"] for entry in shifted["sources"]] == [
        entry["value"] for entry in base["sources"]
    ]:
        raise ValidationFailure("the boundary-shift fixture shifts nothing")
    if shifted["expected_sha256"] == base["expected_sha256"]:
        raise ValidationFailure("source bytes moved across a field boundary reproduce the digest")
    if shifted["conforming_observed_host"] is not False:
        raise ValidationFailure(
            "the boundary-shift probe is published as an observed host rather than a probe"
        )

    # No observed host anywhere in the suite may carry a digest a published
    # fixture does not reproduce, and the fixture must be the one computed over
    # that record's own kernel identity, release, and identifier.
    by_digest = {fixture["expected_sha256"]: (name, fixture) for name, fixture in fixtures.items()}
    checked = 0
    for label, record in conforming_tcb_records():
        host = record["host"]
        build = host["build"]
        if build["content_sha256"] not in by_digest:
            raise ValidationFailure(
                f"{label}: the observed host carries a kernel build digest no published fixture "
                f"reproduces, so it is an invented identity"
            )
        name, fixture = by_digest[build["content_sha256"]]
        # A fixture published as a construction probe rather than an observed
        # host must not turn up as the identity of a conforming record.
        if fixture["conforming_observed_host"] is not True:
            raise ValidationFailure(
                f"{label}: the observed host carries {name}, which the fixture set publishes as a "
                f"construction probe rather than an observed host"
            )
        if fixture["platform"] != record["platform"]:
            raise ValidationFailure(
                f"{label}: the observed host carries the {fixture['platform']} build identity "
                f"{name} on a {record['platform']} trusted computing base"
            )
        for record_value, fixture_field, what in (
            (host["identity"], "host_identity", "kernel identity"),
            (host["version"], "host_version", "kernel release"),
            (build["identifier"], "identifier", "build identifier"),
        ):
            if record_value != fixture[fixture_field]:
                raise ValidationFailure(
                    f"{label}: the observed host publishes {what} {record_value!r} beside a build "
                    f"digest computed over {fixture[fixture_field]!r}"
                )
        checked += 1
    if checked < 1:
        raise ValidationFailure("no conforming trusted computing base observes a host")


def conforming_tcb_records() -> list[tuple[str, dict[str, Any]]]:
    """Every hardened-tcb-v1 record a conforming document publishes.

    Deliberately invalid schema cases are excluded: an omission or mutation case
    is supposed to carry a record the rules reject.
    """
    records: list[tuple[str, dict[str, Any]]] = []

    def collect(label: str, value: Any) -> None:
        if isinstance(value, dict):
            if value.get("record_version") == TCB_RECORD_VERSION and "trusted_components" in value:
                records.append((label, value))
            for item in value.values():
                collect(label, item)
        elif isinstance(value, list):
            for item in value:
                collect(label, item)

    for path in sorted((HARDENED_SUITE / "vectors").glob("*.json")):
        collect(path.name, load_json(path))
    for case in load_json(HARDENED_SUITE / "schema-cases" / "index.json"):
        if not case["valid"]:
            continue
        collect(case["instance"], load_json(HARDENED_SUITE / "schema-cases" / case["instance"]))
    return records


def validate_backend_version_comparison(vector: dict[str, Any]) -> None:
    """Re-evaluate every published version comparison independently.

    review-cycle-3 finding R3-2: "at or above" was prose. Each case is decided
    here by the section 2.3.4 rule, and a case whose published verdict differs
    fails, so the comparison cannot drift back into a string match.
    """
    block = vector["backend_version_comparison"]
    if block["grammar"] != BACKEND_VERSION_GRAMMAR:
        raise ValidationFailure("the backend version comparison names the wrong grammar")
    if block["missing_component_value"] != 0:
        raise ValidationFailure("a missing numeric component must be zero")
    if block["cross_series_comparison"] != "invalid":
        raise ValidationFailure("comparing two backend version series must be invalid")

    cases = require_named(block["cases"], "hardened backend version comparison cases")
    outcomes: set[tuple[bool, bool, bool]] = set()
    for name, case in cases.items():
        satisfied, comparable = backend_version_at_least(case["observed"], case["minimum"])
        if comparable is not case["comparable"]:
            raise ValidationFailure(
                f"version case {name} publishes comparable={case['comparable']} for "
                f"{case['observed']!r} against {case['minimum']!r}"
            )
        if satisfied is not case["satisfied"] or satisfied is not case["claim_qualifies"]:
            raise ValidationFailure(
                f"version case {name} publishes a verdict the {BACKEND_VERSION_GRAMMAR} "
                f"comparison disproves"
            )
        if (parse_backend_version(case["observed"]) is not None) is not case["observed_valid"]:
            raise ValidationFailure(f"version case {name} misreports observed-version validity")
        if (parse_backend_version(case["minimum"]) is not None) is not case["minimum_valid"]:
            raise ValidationFailure(f"version case {name} misreports minimum-version validity")
        if case["expected_error"] not in HARDENED_DIAGNOSTICS:
            raise ValidationFailure(f"version case {name} names an unknown diagnostic")
        if case["published"] is not False:
            raise ValidationFailure(f"version case {name} publishes state")
        outcomes.add((case["observed_valid"] and case["minimum_valid"], comparable, satisfied))

    # Below, equal, above, incomparable, and malformed must all be present: a
    # suite that only shows the passing direction proves nothing.
    if (True, True, True) not in outcomes:
        raise ValidationFailure("no version case satisfies the minimum")
    if (True, True, False) not in outcomes:
        raise ValidationFailure("no version case observes a version below the minimum")
    if (True, False, False) not in outcomes:
        raise ValidationFailure("no version case compares two different backend series")
    if (False, False, False) not in outcomes:
        raise ValidationFailure("no version case carries a malformed version")


def validate_schema_closed_value_sets() -> None:
    """Pin the closed value sets the shipped schemas declare.

    A relation branch protects a value set only for the platforms it enumerates.
    If a later revision adds a platform and forgets a branch, the value sets
    below are the backstop, so they are checked directly rather than left as
    redundancy no test would notice being widened.
    """
    common = load_json(HARDENED_SCHEMAS / "hardened-common.schema.json")["$defs"]
    if common["hardenedHostKindV1"] != {"const": TCB_HOST_KIND}:
        raise ValidationFailure(
            "the hardened host kind is not the single operating-system value this revision admits"
        )
    if sorted(common["hardenedHostIdentityValueV1"].get("enum", [])) != sorted(
        set(CANONICAL_HOST_IDENTITY.values())
    ):
        raise ValidationFailure(
            "the hardened host identity value set is not exactly the declared canonical kernels"
        )
    if sorted(common["hardenedPlatformV1"]["enum"]) != sorted(CANONICAL_HOST_IDENTITY):
        raise ValidationFailure("the hardened platform set does not match the host identity table")
    if sorted(common["hardenedEnforcementBackendV1"]["enum"]) != sorted(BACKEND_VERSION_SERIES):
        raise ValidationFailure(
            "the hardened enforcement backend set does not match the version series table"
        )
    if sorted(common["hardenedComponentDigestAlgorithmV1"]["enum"]) != sorted(
        TCB_COMPONENT_ALGORITHMS
    ):
        raise ValidationFailure("the component digest algorithm set is not exactly the two defined")
    if sorted(common["hardenedTrustedComponentKindV1"]["enum"]) != sorted(TCB_COMPONENT_KINDS):
        raise ValidationFailure(
            "the trusted component kind set does not match the algorithm-by-kind table"
        )
    # review-cycle-4 finding R4-2: the phase enum is the fourth place the order
    # appears, so it is pinned to the one normative list rather than left to
    # drift into a set that admits an ordering the profile rejects.
    if common["hardenedPhaseV1"]["enum"] != ORDERED_PHASES:
        raise ValidationFailure(
            "the hardened phase value set is not the normative ordered phase list"
        )
    if common["hardenedHostBuildAlgorithmV1"] != {"const": HOST_BUILD_ALGORITHM}:
        raise ValidationFailure(
            "the kernel build identity algorithm is not the single value this revision defines"
        )
    if sorted(common["hardenedHostBuildV1"]["required"]) != HOST_BUILD_FIELDS:
        raise ValidationFailure("the kernel build identity record is not closed over its own members")
    if common["hardenedHostBuildV1"].get("additionalProperties") is not False:
        raise ValidationFailure("the kernel build identity record admits additional properties")
    if sorted(common["hardenedHostIdentityV1"]["required"]) != sorted(TCB_HOST_FIELDS):
        raise ValidationFailure("the observed host record is not closed over its own members")
    if common["hardenedHostIdentityV1"]["properties"]["build"] != {
        "$ref": "#/$defs/hardenedHostBuildV1"
    }:
        raise ValidationFailure(
            "the observed host still admits a kernel build value other than the closed record"
        )

    # The per-platform identifier grammars the schema enforces must be exactly
    # the ones this validator, the profile vector, and section 6.3 declare.
    for branch in common["hardenedHostBuildIdentifierPlatformRelationV1"]["allOf"]:
        platform = branch["if"]["properties"]["platform"]["const"]
        pattern = branch["then"]["properties"]["host"]["properties"]["build"]["properties"][
            "identifier"
        ]["pattern"]
        expected = HOST_BUILD_IDENTIFIER_PATTERN[platform].pattern[:-1] + r"(?![\s\S])"
        if pattern != expected:
            raise ValidationFailure(
                f"the schema admits kernel build identifiers on {platform} the profile does not: "
                f"{pattern!r} is not {expected!r}"
            )

    # Every relation branch must exist for every member of the set it keys on,
    # so adding a platform or a backend without its branch fails here.
    for name, keyed, expected in (
        ("hardenedHostPlatformRelationV1", "platform", set(CANONICAL_HOST_IDENTITY)),
        ("hardenedHostBuildIdentifierPlatformRelationV1", "platform", set(CANONICAL_HOST_IDENTITY)),
        ("hardenedPlatformBackendRelationV1", "platform", set(CANONICAL_HOST_IDENTITY)),
        ("hardenedBackendVersionSeriesRelationV1", "enforcement_backend", set(BACKEND_VERSION_SERIES)),
        ("hardenedMinimumVersionSeriesRelationV1", "enforcement_backend", set(BACKEND_VERSION_SERIES)),
        ("hardenedOperatingSystemBackendRelationV1", "operating_system", set(CANONICAL_HOST_IDENTITY)),
    ):
        branches = set()
        for branch in common[name]["allOf"]:
            branches.add(branch["if"]["properties"][keyed]["const"])
        if branches != expected:
            raise ValidationFailure(
                f"{name} branches on {sorted(branches)}, but the declarations name {sorted(expected)}"
            )

    # The algorithm-by-kind relation must reach every kind that is not free to
    # choose, in the direction its table states.
    constrained = {
        kind: next(iter(algorithms))
        for kind, algorithms in COMPONENT_ALGORITHM_BY_KIND.items()
        if len(algorithms) == 1
    }
    bound: dict[str, str] = {}
    for branch in common["hardenedComponentAlgorithmKindRelationV1"]["allOf"]:
        condition = branch["if"]["properties"]["kind"]
        kinds = condition.get("enum", [condition.get("const")])
        for kind in kinds:
            bound[kind] = branch["then"]["properties"]["algorithm"]["const"]
    if bound != constrained:
        raise ValidationFailure(
            "the component algorithm-by-kind relation does not bind exactly the constrained kinds"
        )


def validate_tcb_schema_relations() -> None:
    """Run the mutants review cycle 2 ran, against the real schemas.

    Every relation the completeness statement marks ``schema`` is exercised
    here on a real instance, so a schema that silently stops enforcing one
    fails this validator rather than passing on prose.
    """
    receipt_v3 = validator_for("hardened-build-receipt-v3.schema.json")
    receipt_v4 = validator_for("hardened-build-receipt-v4.schema.json")
    claim = validator_for("hardened-conformance-claim-v4.schema.json")
    marker = validator_for("hardened-install-marker-v4.schema.json")
    evidence = validator_for("hardened-capability-evidence-v1.schema.json")
    index = load_json(HARDENED_SUITE / "schema-cases" / "index.json")

    def valid_case(schema: str) -> Any:
        case = next(item for item in index if item["schema"] == schema and item["valid"])
        return load_json(HARDENED_SUITE / "schema-cases" / case["instance"])

    def clone(document: Any) -> Any:
        return json.loads(json.dumps(document))

    def must_reject(validator: Draft202012Validator, document: Any, why: str) -> None:
        if not list(validator.iter_errors(document)):
            raise ValidationFailure(f"the hardened schemas accept {why}")

    base_v3 = valid_case("hardened-build-receipt-v3.schema.json")
    base_v4 = valid_case("hardened-build-receipt-v4.schema.json")
    base_marker = valid_case("hardened-install-marker-v4.schema.json")
    base_claim = valid_case("hardened-conformance-claim-v4.schema.json")

    for field in TCB_FIELDS:
        mutant = clone(base_v3)
        del mutant["tcb"][field]
        must_reject(receipt_v3, mutant, f"a receipt whose trusted computing base omits {field}")
        marker_mutant = clone(base_marker)
        for record in marker_mutant["builds"].values():
            del record["tcb"][field]
        must_reject(marker, marker_mutant, f"a marker whose trusted computing base omits {field}")
        claim_mutant = clone(base_claim)
        del claim_mutant["tcb"][field]
        must_reject(claim, claim_mutant, f"a claim whose trusted computing base omits {field}")

    platform_goos = {platform: goos for goos, platform in GOOS_TO_PLATFORM.items()}
    for platform, backend in PLATFORM_BACKENDS.items():
        for other, other_backend in PLATFORM_BACKENDS.items():
            if other == platform:
                continue
            mutant = clone(base_v3)
            # The native target follows the platform, so the only rule this
            # instance breaks is the platform-to-backend relation itself.
            mutant["input"]["target"]["goos"] = platform_goos[platform]
            mutant["tcb"]["platform"] = platform
            mutant["tcb"]["enforcement_backend"] = other_backend
            must_reject(
                receipt_v3, mutant, f"a {platform} trusted computing base with the {other} backend"
            )
            record = clone(base_claim)
            record["tcb"]["platform"] = platform
            record["tcb"]["enforcement_backend"] = other_backend
            must_reject(claim, record, f"a claim pairing {platform} with the {other} backend")
            report = clone(valid_case("hardened-capability-evidence-v1.schema.json"))
            report["platform"] = platform
            report["enforcement_backend"] = other_backend
            must_reject(
                evidence, report, f"an evidence record pairing {platform} with the {other} backend"
            )
            entry = clone(base_claim)
            entry["enforcement_backends"][0]["operating_system"] = platform
            entry["enforcement_backends"][0]["enforcement_backend"] = other_backend
            must_reject(
                claim, entry, f"a claim backend entry pairing {platform} with the {other} backend"
            )
        _ = backend

    for goos, platform in GOOS_TO_PLATFORM.items():
        for other in PLATFORM_BACKENDS:
            if other == platform:
                continue
            mutant = clone(base_v3)
            mutant["input"]["target"]["goos"] = goos
            mutant["tcb"]["platform"] = other
            mutant["tcb"]["enforcement_backend"] = PLATFORM_BACKENDS[other]
            must_reject(receipt_v3, mutant, f"a {goos} receipt whose trusted base reports {other}")
            repository = clone(base_v4)
            repository["input"]["target"]["goos"] = goos
            repository["tcb"]["platform"] = other
            repository["tcb"]["enforcement_backend"] = PLATFORM_BACKENDS[other]
            must_reject(
                receipt_v4, repository, f"a {goos} repository receipt whose trusted base reports {other}"
            )

    outside = clone(base_v3)
    outside["input"]["target"]["goos"] = "freebsd"
    must_reject(receipt_v3, outside, "a hardened build input targeting a platform with no declaration")

    for document, validator, label in (
        (base_v3, receipt_v3, "receipt"),
        (base_claim, claim, "claim"),
    ):
        strings_only = clone(document)
        strings_only["tcb"]["trusted_components"] = ["mutable-interpreter"]
        must_reject(validator, strings_only, f"a {label} naming a trusted component as a bare string")
        undigested = clone(document)
        undigested["tcb"]["trusted_components"] = [
            {"kind": "interpreter", "name": "python", "algorithm": "curator-hardened-component-file-v1"}
        ]
        must_reject(validator, undigested, f"a {label} trusted component with no content digest")
        revived = clone(document)
        revived["tcb"]["additional_trusted_components"] = ["mutable-interpreter"]
        must_reject(validator, revived, f"a {label} that revives the unconstrained component field")

    untyped = clone(base_claim)
    untyped["enforcement_backends"][0]["required_configuration"] = ["cgroup v2 unified hierarchy"]
    must_reject(claim, untyped, "a claim whose required configuration is prose rather than settings")

    # review-cycle-3 finding R3-2: the observed host must be the platform's own
    # kernel, and the hypervisor kind no backend of this revision can supply is
    # gone rather than left unenforced.
    for document, validator, label in (
        (base_v3, receipt_v3, "receipt"),
        (base_v4, receipt_v4, "repository receipt"),
        (base_claim, claim, "claim"),
    ):
        for platform, identity in CANONICAL_HOST_IDENTITY.items():
            if identity == document["tcb"]["host"]["identity"]:
                continue
            mutant = clone(document)
            mutant["tcb"]["host"]["identity"] = identity
            must_reject(
                validator,
                mutant,
                f"a {label} whose {document['tcb']['platform']} trusted base observed the "
                f"{platform} kernel identity",
            )
            _ = platform
        hypervisor = clone(document)
        hypervisor["tcb"]["host"]["kind"] = "hypervisor"
        must_reject(validator, hypervisor, f"a {label} reporting a hypervisor host")

        # review-cycle-4 finding R4-1: the kernel build identity is required,
        # closed, digested, and written in its own platform's grammar.
        for build, why in (
            (None, "a null kernel build identity"),
            ("25A123", "a kernel build identity as a bare descriptive string"),
            (
                {"algorithm": HOST_BUILD_ALGORITHM, "identifier": "25A123"},
                "a kernel build identity with no content digest",
            ),
            (
                {"algorithm": HOST_BUILD_ALGORITHM, "content_sha256": "sha256:" + "a" * 64},
                "a kernel build identity with no identifier",
            ),
            (
                {
                    "algorithm": TCB_DIGEST_ALGORITHM,
                    "identifier": "25A123",
                    "content_sha256": "sha256:" + "a" * 64,
                },
                "a kernel build identity under another algorithm",
            ),
            (
                {
                    "algorithm": HOST_BUILD_ALGORITHM,
                    "identifier": "25A123",
                    "content_sha256": "sha256:" + "a" * 64,
                    "sources": ["kern.version"],
                },
                "a kernel build identity carrying its own extra member",
            ),
        ):
            mutant = clone(document)
            mutant["tcb"]["host"]["build"] = build
            must_reject(validator, mutant, f"a {label} with {why}")
        missing_build = clone(document)
        del missing_build["tcb"]["host"]["build"]
        must_reject(validator, missing_build, f"a {label} whose observed host omits its build")

        for platform, pattern in HOST_BUILD_IDENTIFIER_PATTERN.items():
            if platform == document["tcb"]["platform"]:
                continue
            foreign = {
                "linux": "4f2a1c8e6b90d3574a1e2f8c0b7d69315ae4c2f8",
                "macos": "25A123",
                "windows": "26100.1",
            }[platform]
            if pattern.fullmatch(foreign) is None:
                raise ValidationFailure(f"the {platform} probe identifier is not a {platform} value")
            mutant = clone(document)
            mutant["tcb"]["host"]["build"]["identifier"] = foreign
            must_reject(
                validator,
                mutant,
                f"a {document['tcb']['platform']} {label} carrying a {platform} kernel build "
                f"identifier",
            )
        for malformed in ("", " ", "25A123 ", "25A123\n", "a" * 65, "25/A123"):
            mutant = clone(document)
            mutant["tcb"]["host"]["build"]["identifier"] = malformed
            must_reject(
                validator, mutant, f"a {label} whose kernel build identifier is {malformed!r}"
            )
        for malformed in (
            "twenty-five",
            "25.0.0 ",
            # $ alone would admit this one in an engine where it also matches
            # before a final newline.
            "25.0.0\n",
            "25.00.0",
            "25.0.0.0.0",
            "",
        ):
            mutant = clone(document)
            mutant["tcb"]["host"]["version"] = malformed
            must_reject(validator, mutant, f"a {label} whose observed release is {malformed!r}")

        # The backend version series is bound to the backend, in both directions.
        for backend, series in BACKEND_VERSION_SERIES.items():
            if backend == document["tcb"]["enforcement_backend"]:
                continue
            mutant = clone(document)
            mutant["tcb"]["backend"]["version"] = f"{series}-1.0"
            must_reject(
                validator,
                mutant,
                f"a {label} whose {document['tcb']['enforcement_backend']} reports a {series} "
                f"version",
            )
        for malformed in (
            "2.0",
            "sandbox-02.0",
            "sandbox-",
            "sandbox-1.2.3.4.5",
            "latest",
            # A tail of $ would let this one through in an engine where $ also
            # matches before a final newline.
            "sandbox-2.0\n",
        ):
            mutant = clone(document)
            mutant["tcb"]["backend"]["version"] = malformed
            must_reject(validator, mutant, f"a {label} whose backend version is {malformed!r}")

        # review-cycle-3 finding R3-1: a kind that names one file cannot carry a
        # tree digest, and the tree kind cannot carry a file digest.
        file_only = clone(document)
        file_only["tcb"]["trusted_components"] = [
            {
                "kind": "interpreter",
                "name": "supervisor-launcher-interpreter",
                "algorithm": COMPONENT_TREE_ALGORITHM,
                "content_sha256": "sha256:" + "a" * 64,
            }
        ]
        must_reject(validator, file_only, f"a {label} digesting an interpreter as a tree")
        tree_only = clone(document)
        tree_only["tcb"]["trusted_components"] = [
            {
                "kind": "installed-package-tree",
                "name": "vendored-runtime",
                "algorithm": COMPONENT_FILE_ALGORITHM,
                "content_sha256": "sha256:" + "a" * 64,
            }
        ]
        must_reject(validator, tree_only, f"a {label} digesting an installed package tree as a file")

    for series in BACKEND_VERSION_SERIES.values():
        if series == BACKEND_VERSION_SERIES[base_claim["enforcement_backends"][0]["enforcement_backend"]]:
            continue
        mutant = clone(base_claim)
        mutant["enforcement_backends"][0]["minimum_version"] = f"{series}-1.0"
        must_reject(claim, mutant, f"a claim whose minimum version is in the {series} series")
    for malformed in (
        "6.1",
        "cgroup2-06.1",
        "cgroup2-",
        "cgroup2-1.2.3.4.5",
        "newest",
        "cgroup2-6.1\n",
    ):
        mutant = clone(base_claim)
        mutant["enforcement_backends"][0]["minimum_version"] = malformed
        must_reject(claim, mutant, f"a claim whose minimum version is {malformed!r}")


def validate_claim_qualification_binding() -> None:
    """A claim's trusted computing base must be one the claim itself declares."""
    index = load_json(HARDENED_SUITE / "schema-cases" / "index.json")
    checked = 0
    for case in index:
        if case["schema"] != "hardened-conformance-claim-v4.schema.json" or not case["valid"]:
            continue
        claim = load_json(HARDENED_SUITE / "schema-cases" / case["instance"])
        check_claim_qualification(case["instance"], claim)
        checked += 1
    if checked < 1:
        raise ValidationFailure("no valid hardened claim exercises the qualification binding")


def check_claim_qualification(label: str, claim: dict[str, Any]) -> None:
    check_tcb_record(label, claim["tcb"])
    declared = claim["operating_systems"]
    entries = require_named_key(
        claim["enforcement_backends"], "operating_system", f"{label} enforcement backends"
    )
    if sorted(entries) != sorted(declared):
        raise ValidationFailure(
            f"{label} does not declare exactly one enforcement backend per claimed operating system"
        )
    platform = claim["tcb"]["platform"]
    if platform not in declared:
        raise ValidationFailure(
            f"{label} names a trusted computing base for an operating system it does not claim"
        )
    entry = entries[platform]
    if entry["enforcement_backend"] != claim["tcb"]["enforcement_backend"]:
        raise ValidationFailure(
            f"{label} declares one enforcement backend for {platform} and runs another"
        )
    observed = {
        item["setting"]: item["observed_value"]
        for item in claim["tcb"]["backend"]["configuration"]
    }
    for requirement in entry["required_configuration"]:
        setting = requirement["setting"]
        if observed.get(setting) != requirement["required_value"]:
            raise ValidationFailure(
                f"{label} requires {setting} that its own trusted computing base did not observe"
            )

    # review-cycle-3 finding R3-2: the normative "at or above" of section 8.5 was
    # stated and never compared, so a claim declaring minimum_version 999999 was
    # accepted against an observed version of 0.
    observed_version = claim["tcb"]["backend"]["version"]
    minimum_version = entry["minimum_version"]
    satisfied, comparable = backend_version_at_least(observed_version, minimum_version)
    if not comparable:
        raise ValidationFailure(
            f"{label} declares minimum version {minimum_version!r} that cannot be compared with "
            f"the observed {observed_version!r}: one is malformed or they are different series"
        )
    if not satisfied:
        raise ValidationFailure(
            f"{label} declares minimum version {minimum_version!r} that its own trusted "
            f"computing base does not satisfy: it observed {observed_version!r}"
        )
    for driver in claim["build_drivers"]:
        unknown = sorted(set(driver["operating_systems"]) - set(declared))
        if unknown:
            raise ValidationFailure(f"{label} drives an operating system it does not claim: {unknown}")


def validate_identity_binding(vector: dict[str, Any]) -> None:
    """Both hardened identities must reach every reusable output.

    The task contract requires the hardened profile identity and the concrete
    trusted computing base to bind cache reuse, receipts, markers, and claims.
    That is expressed structurally: both live inside the hashed build input, so
    they are inside the cache key, inside the exact receipt bytes, and inside
    receipt_sha256, and a lookup that recomputes the key cannot cross either.
    """
    binding = vector["identity_binding"]
    if binding["version"] != IDENTITY_BINDING_VERSION:
        raise ValidationFailure("hardened identity binding names the wrong model version")
    if binding["tcb_digest_algorithm"] != TCB_DIGEST_ALGORITHM:
        raise ValidationFailure("hardened identity binding names the wrong TCB digest algorithm")
    identities = require_named_key(binding["identities"], "identity", "hardened identities")
    expected = {"capability-evidence", "execution-policy", "hardened-profile", "trusted-computing-base"}
    if set(identities) != expected:
        raise ValidationFailure("hardened identity binding does not cover exactly the four identities")
    for name in ("execution-policy", "hardened-profile", "trusted-computing-base"):
        item = identities[name]
        for field in (
            "in_hashed_build_input",
            "in_receipt_bytes",
            "in_install_marker",
            "in_conformance_claim",
            "binds_cache_reuse",
        ):
            if item[field] is not True:
                raise ValidationFailure(
                    f"hardened identity {name} does not bind {field.replace('_', ' ')}"
                )
    evidence = identities["capability-evidence"]
    for field in (
        "in_hashed_build_input",
        "in_receipt_bytes",
        "in_install_marker",
        "in_conformance_claim",
        "binds_cache_reuse",
    ):
        if evidence[field] is not False:
            raise ValidationFailure(
                "the per-operation capability-evidence record leaks into a reusable output"
            )
    for field in ("cross_tcb_reuse", "cross_profile_reuse", "in_place_upgrade"):
        if binding[field] is not False:
            raise ValidationFailure(f"hardened identity binding permits {field}")
    if binding["per_host_key_divergence_is_intended"] is not True:
        raise ValidationFailure(
            "hardened identity binding does not own the per-host key divergence it creates"
        )


def validate_identity_separation() -> None:
    vector = load_json(HARDENED_SUITE / "vectors" / "hardened-identity-separation.json")
    portable_vector = load_json(PORTABLE_SUITE / "vectors" / "go-host-execution-policy.json")
    reserved = portable_vector["cache_identity"]

    if vector["identity_binding_version"] != IDENTITY_BINDING_VERSION:
        raise ValidationFailure("hardened identity vector names the wrong binding model")
    validate_identity_binding(vector)
    validate_component_digest_fixtures(vector)
    validate_host_build_fixtures(vector)
    validate_backend_version_comparison(vector)
    validate_tcb_completeness(vector)

    identity = vector["cache_identity"]
    if identity["aliases"] is not False:
        raise ValidationFailure("hardened cache identity admits aliasing")

    cases = [
        "hardened",
        "hardened_rotated_tcb",
        "rc5_reserved_policy_slot_only",
        "portable",
        "legacy_rc4_without_execution_policy",
    ]
    keys: dict[str, str] = {}
    for name in cases:
        case = identity[name]
        recomputed = ccj1_sha256(case["input"])
        if recomputed != case["cache_key"]:
            raise ValidationFailure(f"{name} cache key is not reproducible from its input")
        if recomputed in keys.values():
            raise ValidationFailure(f"{name} aliases another execution contract")
        keys[name] = recomputed

    # The two hardened inputs bind the profile identity and a concrete trusted
    # computing base, and their digests must be recomputable from the records
    # the vector publishes.
    for name in ("hardened", "hardened_rotated_tcb"):
        case = identity[name]
        check_tcb_record(name, case["tcb"])
        member = case["input"].get("hardened")
        if not isinstance(member, dict):
            raise ValidationFailure(f"{name} build input carries no hardened identity member")
        if member.get("profile") != HARDENED_PROFILE_IDENTITY:
            raise ValidationFailure(f"{name} build input does not bind the hardened profile identity")
        digest = member.get("tcb", {})
        if digest.get("algorithm") != TCB_DIGEST_ALGORITHM:
            raise ValidationFailure(f"{name} build input uses the wrong TCB digest algorithm")
        if digest.get("content_sha256") != tcb_digest(case["tcb"]):
            raise ValidationFailure(
                f"{name} build input digest does not reproduce its own trusted-computing-base record"
            )
        if case["tcb"]["hardened_profile"] != HARDENED_PROFILE_IDENTITY:
            raise ValidationFailure(f"{name} trusted computing base names another profile")
        goos = case["input"]["target"]["goos"]
        if case["tcb"]["platform"] != GOOS_TO_PLATFORM[goos]:
            raise ValidationFailure(
                f"{name} trusted computing base reports a platform its native target contradicts"
            )
        if case["tcb"]["toolchain"]["content_sha256"] != case["input"]["toolchain"]["content_sha256"]:
            raise ValidationFailure(
                f"{name} trusted computing base names a toolchain its build input does not use"
            )

    # Rotating only the trusted computing base must move the key: that is what
    # "the trusted computing base binds cache reuse" means mechanically.
    if keys["hardened"] == keys["hardened_rotated_tcb"]:
        raise ValidationFailure("rotating the trusted computing base does not change cache identity")
    base_input = dict(identity["hardened"]["input"])
    rotated_input = dict(identity["hardened_rotated_tcb"]["input"])
    base_input.pop("hardened", None)
    rotated_input.pop("hardened", None)
    if base_input != rotated_input:
        raise ValidationFailure(
            "the rotated-trusted-computing-base case differs in something a package can see"
        )

    # rc.5 recorded a policy-slot-only input and marked it schema_valid: false.
    # It is a comparison point, not a hardened build input.
    slot = identity["rc5_reserved_policy_slot_only"]
    if slot["is_hardened_input"] is not False:
        raise ValidationFailure(
            "the rc.5 policy-slot reservation is presented as a valid hardened build input"
        )
    if slot["cache_key"] != slot["reserved_cache_key"]:
        raise ValidationFailure("the rc.5 policy-slot key drifted from its reserved value")
    if slot["input"] != reserved["reserved_hardened"]["input"]:
        raise ValidationFailure("the rc.5 policy-slot input differs from the portable reservation")
    if reserved["reserved_hardened"].get("schema_valid") is not False:
        raise ValidationFailure("rc.5 no longer marks the reserved hardened input schema invalid")
    for name, portable_name in (
        ("portable", "portable"),
        ("legacy_rc4_without_execution_policy", "legacy_rc4_without_execution_policy"),
    ):
        case = identity[name]
        if case["cache_key"] != case["reserved_cache_key"]:
            raise ValidationFailure(f"{name} cache key drifted from its reserved value")
        if case["cache_key"] != reserved[portable_name]["cache_key"]:
            raise ValidationFailure(
                f"{name} cache key disagrees with the portable suite reservation"
            )
        if case["input"] != reserved[portable_name]["input"]:
            raise ValidationFailure(
                f"{name} build input differs from the portable suite reservation"
            )

    hashed = sorted(identity["hashed_identity_inputs"])
    if hashed != [
        "the curator-hardened-tcb-v1 digest of the concrete trusted computing base",
        "the execution-policy identity inside the canonical build policy object",
        "the hardened profile identity inside the closed hardened input member",
    ]:
        raise ValidationFailure(
            "the hardened hashed identity does not carry the profile and trusted-computing-base identities"
        )
    if sorted(identity["excluded_from_hashed_identity"]) != [
        "the per-operation hardened capability-evidence record"
    ]:
        raise ValidationFailure(
            "the hardened hashed identity excludes something other than the per-operation record"
        )

    for row in vector["receipt_separation"]:
        if row["portable_schema_widened"] is not False:
            raise ValidationFailure("a portable receipt schema is reported as widened")
        if row["hardened_schema_version"] == row["portable_schema_version"]:
            raise ValidationFailure("hardened and portable receipts share a schema version")
        if sorted(row["hardened_receipt_binds"]) != [
            "execution_policy",
            "hardened_profile",
            "tcb",
        ]:
            raise ValidationFailure("a hardened receipt does not bind all three identities")
    marker = vector["marker_separation"]
    if marker["hardened_schema_version"] in marker["portable_schema_versions"]:
        raise ValidationFailure("the hardened marker version collides with a portable one")
    for field in (
        "portable_schema_widened",
        "hardened_record_in_portable_marker",
        "portable_record_in_hardened_marker",
    ):
        if marker[field] is not False:
            raise ValidationFailure(f"marker separation violates {field}")
    if sorted(marker["hardened_record_requires"]) != ["execution_policy", "hardened_profile", "tcb"]:
        raise ValidationFailure("a hardened marker record does not require all three identities")
    claim = vector["claim_separation"]
    if claim["portable_admits"] != [PORTABLE_EXECUTION_POLICY] or claim["hardened_admits"] != [
        HARDENED_EXECUTION_POLICY
    ]:
        raise ValidationFailure("claim schemas are not structurally disjoint")
    if sorted(claim["hardened_claim_requires"]) != ["execution_policy", "hardened_profile", "tcb"]:
        raise ValidationFailure("a hardened claim does not require all three identities")
    if claim["hardened_claims_emitted"] != [] or claim["hardened_qualified_operating_systems"] != []:
        raise ValidationFailure("claim separation fabricates a hardened claim")

    reuse = require_named(vector["cross_profile_reuse_cases"], "cross-profile reuse cases")
    if "hardened-reader-sees-entry-from-another-tcb" not in reuse:
        raise ValidationFailure(
            "no reuse case covers an entry produced under another trusted computing base"
        )
    for name, case in reuse.items():
        if case["upgrades"] is not False:
            raise ValidationFailure(f"reuse case {name} upgrades an entry in place")
        same_contract = case["reader"] == case["entry"] and case["reader_tcb"] == case["entry_tcb"]
        if not same_contract and case["result"] != "miss":
            raise ValidationFailure(f"reuse case {name} accepts an entry from another contract")
        if case["adopts_bytes"] is not (case["result"] == "hit"):
            raise ValidationFailure(f"reuse case {name} contradicts itself about adopting bytes")

    validate_tcb_rotation(vector)


def validate_identity_binding_chain() -> None:
    """Follow the binding through the real generated artifacts.

    Receipt bytes carry the concrete record, the hashed input carries its
    domain-separated digest, the cache key is the digest of that input, and the
    marker repeats the same record and key. Nothing here is asserted in prose.
    """
    index = load_json(HARDENED_SUITE / "schema-cases" / "index.json")
    checked = 0
    for schema in ("hardened-build-receipt-v3.schema.json", "hardened-build-receipt-v4.schema.json"):
        for case in index:
            if case["schema"] != schema or not case["valid"]:
                continue
            receipt = load_json(HARDENED_SUITE / "schema-cases" / case["instance"])
            check_tcb_record(case["instance"], receipt["tcb"])
            if receipt["tcb"]["platform"] != GOOS_TO_PLATFORM[receipt["input"]["target"]["goos"]]:
                raise ValidationFailure(
                    f"{case['instance']} trusted computing base contradicts its own native target"
                )
            if receipt["tcb"]["toolchain"] != receipt["input"]["toolchain"]:
                raise ValidationFailure(
                    f"{case['instance']} trusted computing base names a toolchain its input does not use"
                )
            member = receipt["input"]["hardened"]
            if member["profile"] != HARDENED_PROFILE_IDENTITY:
                raise ValidationFailure(f"{case['instance']} does not bind the profile identity")
            if member["tcb"]["content_sha256"] != tcb_digest(receipt["tcb"]):
                raise ValidationFailure(
                    f"{case['instance']} input digest does not reproduce its own TCB record"
                )
            if receipt["cache_key"] != ccj1_sha256(receipt["input"]):
                raise ValidationFailure(
                    f"{case['instance']} cache key is not the digest of its own input"
                )
            if receipt["input"]["policy"]["execution_policy"] != HARDENED_EXECUTION_POLICY:
                raise ValidationFailure(f"{case['instance']} is not a hardened receipt")
            checked += 1
    if checked < 2:
        raise ValidationFailure("no valid hardened receipt case exercises the identity binding")

    for case in index:
        if case["schema"] != "hardened-install-marker-v4.schema.json" or not case["valid"]:
            continue
        marker = load_json(HARDENED_SUITE / "schema-cases" / case["instance"])
        for command, record in marker["builds"].items():
            if record["hardened_profile"] != HARDENED_PROFILE_IDENTITY:
                raise ValidationFailure(
                    f"{case['instance']} build record {command} does not bind the profile identity"
                )
            if record["execution_policy"] != HARDENED_EXECUTION_POLICY:
                raise ValidationFailure(
                    f"{case['instance']} build record {command} is not a hardened record"
                )
            if record["tcb"]["record_version"] != TCB_RECORD_VERSION:
                raise ValidationFailure(
                    f"{case['instance']} build record {command} carries no trusted-computing-base record"
                )
            check_tcb_record(f"{case['instance']} build record {command}", record["tcb"])
            rebuilt = rebuild_hardened_input(record)
            if record["cache_key"] != ccj1_sha256(rebuilt):
                raise ValidationFailure(
                    f"{case['instance']} build record {command} key does not follow from its own identities"
                )

    for case in index:
        if case["schema"] != "hardened-conformance-claim-v4.schema.json" or not case["valid"]:
            continue
        claim = load_json(HARDENED_SUITE / "schema-cases" / case["instance"])
        if claim["hardened_profile"] != HARDENED_PROFILE_IDENTITY:
            raise ValidationFailure(f"{case['instance']} does not bind the profile identity")
        if claim["tcb"]["record_version"] != TCB_RECORD_VERSION:
            raise ValidationFailure(f"{case['instance']} carries no trusted-computing-base record")
        check_claim_qualification(case["instance"], claim)


def rebuild_hardened_input(record: dict[str, Any]) -> dict[str, Any]:
    """Recover the hashed input a marker build record implies.

    The receipt for the record is the suite's own valid receipt case, so this
    only substitutes the identities the marker itself publishes. A marker that
    reports a trusted computing base other than the one the build used
    therefore fails to reproduce its own cache key.
    """
    index = load_json(HARDENED_SUITE / "schema-cases" / "index.json")
    schema = f"hardened-build-receipt-v{record['receipt_schema_version']}.schema.json"
    case = next(item for item in index if item["schema"] == schema and item["valid"])
    receipt = load_json(HARDENED_SUITE / "schema-cases" / case["instance"])
    rebuilt = json.loads(json.dumps(receipt["input"]))
    rebuilt["hardened"] = {
        "profile": record["hardened_profile"],
        "tcb": {"algorithm": TCB_DIGEST_ALGORITHM, "content_sha256": tcb_digest(record["tcb"])},
    }
    rebuilt["policy"]["execution_policy"] = record["execution_policy"]
    return rebuilt


def validate_schema_level_separation() -> None:
    """Run the real validators across families to prove no aliasing."""
    vector = load_json(HARDENED_SUITE / "vectors" / "hardened-identity-separation.json")
    identity = vector["cache_identity"]
    hardened_input = identity["hardened"]["input"]
    portable_input = identity["portable"]["input"]
    legacy_input = identity["legacy_rc4_without_execution_policy"]["input"]
    slot_input = identity["rc5_reserved_policy_slot_only"]["input"]

    portable_receipt = validator_for("build-receipt-v1.schema.json")
    hardened_receipt = validator_for("hardened-build-receipt-v3.schema.json")
    artifact = {"path": "bin/golden-tool", "sha256": "sha256:" + "d" * 64, "size": 1024}
    hardened_receipt_document = {
        "schema_version": 3,
        "cache_key": ccj1_sha256(hardened_input),
        "input": hardened_input,
        "tcb": identity["hardened"]["tcb"],
        "artifact": artifact,
    }
    portable_receipt_document = {
        "schema_version": 1,
        "cache_key": ccj1_sha256(portable_input),
        "input": portable_input,
        "artifact": artifact,
    }
    if list(hardened_receipt.iter_errors(hardened_receipt_document)):
        raise ValidationFailure("the hardened receipt schema rejects a hardened receipt")
    if list(portable_receipt.iter_errors(portable_receipt_document)):
        raise ValidationFailure("the portable receipt schema rejects a portable receipt")
    if not list(portable_receipt.iter_errors(hardened_receipt_document)):
        raise ValidationFailure("receipt v1 accepts hardened output")
    if not list(hardened_receipt.iter_errors(portable_receipt_document)):
        raise ValidationFailure("hardened receipt v3 accepts portable output")
    legacy_receipt_document = dict(portable_receipt_document, input=legacy_input)
    if not list(portable_receipt.iter_errors(legacy_receipt_document)):
        raise ValidationFailure("receipt v1 accepts a pre-revision input with no execution policy")
    if not list(hardened_receipt.iter_errors(legacy_receipt_document)):
        raise ValidationFailure("hardened receipt v3 accepts a pre-revision input")

    # An input that only fills the reserved policy slot binds neither the
    # profile identity nor a trusted computing base, so no schema accepts it.
    slot_document = dict(hardened_receipt_document, input=slot_input, cache_key=ccj1_sha256(slot_input))
    if not list(hardened_receipt.iter_errors(slot_document)):
        raise ValidationFailure(
            "hardened receipt v3 accepts an input that binds no profile or trusted computing base"
        )
    if not list(portable_receipt.iter_errors(dict(slot_document, schema_version=1))):
        raise ValidationFailure("receipt v1 accepts the reserved hardened policy slot")
    stripped = {key: value for key, value in hardened_receipt_document.items() if key != "tcb"}
    if not list(hardened_receipt.iter_errors(stripped)):
        raise ValidationFailure("hardened receipt v3 accepts a receipt with no trusted computing base")

    portable_claim = validator_for("conformance-claim-v3.schema.json")
    hardened_claim = validator_for("hardened-conformance-claim-v4.schema.json")
    index = load_json(HARDENED_SUITE / "schema-cases" / "index.json")
    hardened_claim_valid = next(
        case
        for case in index
        if case["schema"] == "hardened-conformance-claim-v4.schema.json" and case["valid"]
    )
    claim_document = load_json(HARDENED_SUITE / "schema-cases" / hardened_claim_valid["instance"])
    if list(hardened_claim.iter_errors(claim_document)):
        raise ValidationFailure("the hardened claim schema rejects a hardened claim")
    if not list(portable_claim.iter_errors(claim_document)):
        raise ValidationFailure("claim v3 accepts a hardened claim")

    portable_marker = validator_for("install-marker-v3.schema.json")
    hardened_marker = validator_for("hardened-install-marker-v4.schema.json")
    marker_case = next(
        case
        for case in index
        if case["schema"] == "hardened-install-marker-v4.schema.json" and case["valid"]
    )
    marker_document = load_json(HARDENED_SUITE / "schema-cases" / marker_case["instance"])
    if list(hardened_marker.iter_errors(marker_document)):
        raise ValidationFailure("the hardened marker schema rejects a hardened marker")
    if not list(portable_marker.iter_errors(marker_document)):
        raise ValidationFailure("marker v3 accepts a hardened marker")
    downgraded = dict(marker_document, schema_version=3)
    if not list(portable_marker.iter_errors(downgraded)):
        raise ValidationFailure("marker v3 accepts a hardened build record")

    evidence = validator_for("hardened-capability-evidence-v1.schema.json")
    portable_evidence = load_json(PORTABLE_SUITE / "vectors" / "go-host-execution-policy.json")[
        "capability_evidence_record"
    ]["examples"]["macos"]
    if not list(evidence.iter_errors(portable_evidence)):
        raise ValidationFailure("the hardened evidence schema accepts a portable evidence record")


def main() -> int:
    checks = [
        validate_hardened_schemas,
        validate_portable_profile_unchanged,
        validate_hardened_manifest,
        validate_hardened_release,
        validate_identity_separation,
        validate_identity_binding_chain,
        validate_schema_closed_value_sets,
        validate_tcb_schema_relations,
        validate_claim_qualification_binding,
        validate_schema_level_separation,
        validate_phase_list_documents,
        validate_host_build_declaration_document,
        validate_reverification_documents,
    ]
    try:
        for check in checks:
            check()
        profile = validate_profile_vector()
        validate_adversarial_vector(profile)
    except ValidationFailure as exc:
        print(f"hardened validation failed: {exc}", file=sys.stderr)
        return 1
    manifest = load_json(HARDENED_SUITE / "manifest.json")
    schemas = len(list(HARDENED_SCHEMAS.glob("*.json")))
    print(
        f"validated {schemas} hardened schemas and {len(manifest['files'])} hardened suite files"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
