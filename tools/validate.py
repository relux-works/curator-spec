#!/usr/bin/env python3
"""Validate schemas, examples, vector manifest, and local Markdown links."""

from __future__ import annotations

import base64
import hashlib
import json
import re
import sys
import urllib.parse

# Importing a sibling module writes bytecode next to it by default, which would
# leave an untracked ``tools/__pycache__`` behind and fail the release gate's
# clean-checkout requirement. These tools are run once per invocation, so the
# cache buys nothing.
sys.dont_write_bytecode = True

import toolchain_gate
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas" / "v1"
SUITE = ROOT / "conformance" / "v1"
# The unreleased candidate suite root. conformance/v1 is pinned byte-for-byte by
# release/1.0.0-rc.5.json, so a case generated for a surface that is minted but
# not yet released lives here: it is validated exactly as strictly, and it moves
# no released identity. TASK-260728-251p01 owns promoting it.
CANDIDATE_SUITE = ROOT / "conformance" / "next"
CANDIDATE_RELEASE_PIN_OWNER = "TASK-260728-251p01"
# Every schema whose generated cases belong to the candidate suite root. The
# split is by schema, not by directory scan, so a case silently written to the
# wrong root is a manifest inventory failure on both sides.
CANDIDATE_CASE_SCHEMAS = frozenset(
    {
        "agent-skill-v8.schema.json",
        "csk-skill-v8.schema.json",
        "skill-build-v2.schema.json",
        "toolchain-registry-v1.schema.json",
        "toolchain-guidance-catalog-v1.schema.json",
        "toolchain-diagnostic-v1.schema.json",
    }
)
REVIEWS = ROOT / "reviews"
SAFE_INTEGER = 9_007_199_254_740_991

# The single execution-policy identity that protocol 1.0 defines for the
# compiled-build drivers, the identity reserved for the separately tracked
# fail-closed profile, and the board story that owns it.
PORTABLE_EXECUTION_POLICY = "manager-worker-v1"
RESERVED_HARDENED_EXECUTION_POLICY = "hardened-worker-v1"
HARDENED_EXECUTION_OWNER = "STORY-260728-327soo"
# The exhaustive rc.5 per-platform native-control inventory and the closed
# per-operation capability-evidence record that reports it.
NATIVE_CONTROL_INVENTORY_VERSION = "rc5-native-control-inventory-v1"
CAPABILITY_EVIDENCE_RECORD_VERSION = "capability-evidence-v1"
UNAVAILABLE_NATIVE_CONTROL_REASON = "no-private-aggregate-domain"
# Exact rc.4 candidate go-v1 cache key computed before the execution-policy
# revision existed. A pre-revision input must miss, never alias.
LEGACY_RC4_GO_V1_CACHE_KEY = (
    "sha256:3fcd714a40e8918eb67dbd35d435875dcce6c9047da811a1fa26626e5e57be48"
)
# The repository-root build descriptor is manager-neutral: one fixed filename
# and one strict schema. Schema 7 is unreleased, so the implementation-branded
# predecessor name has no alias and no compatibility behavior; it must be
# absent from every normative, schema, generated and release surface. The
# retired stem is assembled from parts so the absence guard can scan its own
# source without matching itself.
REPOSITORY_DESCRIPTOR_NAME = "skill-build.json"
REPOSITORY_DESCRIPTOR_SCHEMA = "skill-build-v1.schema.json"
RETIRED_DESCRIPTOR_STEM = "curator" + "-build"
# The schema-6 build-source digest algorithm namespace shares that stem but is
# a different identifier bound into byte-frozen rc.4 artifacts, so it stays.
# Negative fixtures mutate its version suffix, so the whole namespace is kept.
BUILD_SOURCE_ALGORITHM_NAMESPACE = RETIRED_DESCRIPTOR_STEM + "-source"
FROZEN_BUILD_SOURCE_ALGORITHM = BUILD_SOURCE_ALGORITHM_NAMESPACE + "-v1"
# Directory names that hold scratch or version-control state rather than a
# protocol surface.
NON_SURFACE_DIRECTORIES = (".git", ".temp", ".venv", "__pycache__")

# Decision 0008 fixes the version, source-ownership, artifact and execution
# boundary for the additional-language drivers. Protocol 1.0 admits exactly the
# two Go identifiers below; the six family/mode combinations are reserved for
# that boundary and are not admitted anywhere on the wire yet. Reserved names
# are assembled from a family and a source-mode suffix so this guard can scan
# its own source without matching itself.
ADDITIONAL_DRIVER_BOUNDARY_DECISION = (
    "decisions/0008-additional-language-driver-boundary.md"
)
# Decision records are where a closed identifier is proposed, reserved, and
# retired, so they may name a reserved driver. Every other surface may not,
# because naming one there is admission.
DRIVER_RESERVATION_EXEMPT_DIRECTORY = "decisions"
ADMITTED_BUILD_DRIVERS = ("go-repository-v1", "go-v1")
RESERVED_DRIVER_FAMILIES = ("kotlin-native", "rust", "swift")
LOCAL_DRIVER_SUFFIX = "-v1"
REPOSITORY_DRIVER_SUFFIX = "-repository-v1"
RESERVED_BUILD_DRIVERS = tuple(
    sorted(
        family + suffix
        for family in RESERVED_DRIVER_FAMILIES
        for suffix in (LOCAL_DRIVER_SUFFIX, REPOSITORY_DRIVER_SUFFIX)
    )
)
# The additional drivers run under a second portable execution-policy identity
# and report host capability evidence under a re-versioned record. Both are
# reserved by the boundary and minted by the integration task, so both are
# assembled from parts for the same self-scan reason as the driver names.
EXECUTION_POLICY_FAMILY = "manager-worker"
RESERVED_DRIVER_EXECUTION_POLICY = EXECUTION_POLICY_FAMILY + "-v2"
CAPABILITY_EVIDENCE_RECORD_FAMILY = "capability-evidence"
RESERVED_CAPABILITY_EVIDENCE_RECORD = CAPABILITY_EVIDENCE_RECORD_FAMILY + "-v2"
# The closed toolchain requirement object owned by decision 0007. The boundary
# owns only where it lands, so the boundary decision must name it. Placement is
# by a single shared definition reference and never by an inline object, so the
# boundary also fixes the definition name the three reserved slots point at and
# the two members both decisions already close it to. The grammar inside
# ``version`` stays decision 0007's and is deliberately not restated here.
TOOLCHAIN_REQUIREMENT_OBJECT = "toolchain-requirement-v1"
TOOLCHAIN_REQUIREMENT_DEFINITION = "toolchainRequirementV1"
TOOLCHAIN_REQUIREMENT_REF: dict[str, str] = {
    "$ref": "#/$defs/" + TOOLCHAIN_REQUIREMENT_DEFINITION
}
TOOLCHAIN_REQUIREMENT_MEMBERS: tuple[tuple[str, ...], tuple[str, ...]] = (
    ("id", "version"),
    (),
)
# The boundary must keep admission and reservation as two separately named
# closed sets, so a reader has one normative answer for each.
ADMITTED_DRIVER_SET_LABEL = "Admitted wire driver set"
RESERVED_DRIVER_SET_LABEL = "Reserved driver namespace"
# The one artifact class this version admits and the class it rejects.
ADMITTED_ARTIFACT_CLASS = "native-executable-v1"
REJECTED_ARTIFACT_CLASS = "runtime-bundle"
# ``native-executable-v1`` is exactly one bounded regular file, so the shared
# definition carrying it is closed the same way every driver-bearing shape is:
# by exact member set over an object, never by a property-name comparison. A
# property-name check alone leaves the definition free to declare itself a
# scalar, to union the object with one, or to drop every member from
# ``required`` — each of which readmits the rejected class while the shipped
# positive cases still validate.
ARTIFACT_DEFINITION = "buildArtifactV1"
ARTIFACT_MEMBERS: tuple[tuple[str, ...], tuple[str, ...]] = (
    ("path", "sha256", "size"),
    (),
)
# Path, digest and size carry the artifact's identity, so each is pinned to its
# canonical shared definition. A member set alone would accept a free-text
# digest, an absolute or traversing path, or a negative size under the same
# three names.
ARTIFACT_PROPERTY_SCHEMAS: dict[str, dict[str, str]] = {
    "path": {"$ref": "#/$defs/portablePath"},
    "sha256": {"$ref": "#/$defs/sha256"},
    "size": {"$ref": "#/$defs/nonNegativeSafeInteger"},
}
LOCAL_DEFS_PREFIX = "#/$defs/"
# Pinning the three references above is satisfied by a reference to a definition
# that has since been widened, and a finite set of rejected sample values cannot
# close that: raising ``maxLength`` by one, adding uppercase to the digest
# alphabet, or lifting the safe-integer ceiling by one leaves every sampled
# negative still rejected while the compiled receipt validator starts accepting a
# longer path, an uppercase digest, and an out-of-range size. The path grammar,
# the digest alphabet, and the size ceiling are part of the artifact's identity
# rather than illustrative examples, so each referenced definition is held to its
# exact canonical schema. Only the artifact's own reference targets are pinned
# here: ``toolchainRequirementV1`` is unminted and its internals belong to
# decision 0007, so this boundary closes its member set and stops there.
ARTIFACT_REFERENCE_TARGETS: dict[str, dict[str, Any]] = {
    # Each literal below is the schema text verbatim: Python and JSON agree on
    # every escape used here, so a reviewer can diff these against
    # ``schemas/v1/common.schema.json`` character for character.
    "portablePath": {
        "type": "string",
        "minLength": 1,
        "maxLength": 4096,
        "pattern": (
            "^[^/\\\\:\\u0000-\\u001f\\u007f-\\u009f]"
            "(?:[^\\\\:\\u0000-\\u001f\\u007f-\\u009f]*"
            "[^/ .\\\\:\\u0000-\\u001f\\u007f-\\u009f])?$"
        ),
        "not": {
            "pattern": (
                "(?:^|/)(?:\\.{1,2}|[Cc][Oo][Nn]|[Pp][Rr][Nn]|[Aa][Uu][Xx]"
                "|[Nn][Uu][Ll]|[Cc][Oo][Mm][1-9]|[Ll][Pp][Tt][1-9])(?:\\.|/|$)|//"
            )
        },
    },
    "sha256": {
        "type": "string",
        "pattern": "^sha256:[0-9a-f]{64}$",
    },
    "nonNegativeSafeInteger": {
        "type": "integer",
        "minimum": 0,
        "maximum": SAFE_INTEGER,
    },
}
# Property names that can never carry protocol meaning in common.schema.json:
# generic language and build-system selectors, package-controlled installation
# and trust fields, and the members that would turn one published artifact into
# a runtime bundle. This is defense in depth behind the exact member-set tables
# below, so a definition added later cannot introduce one unnoticed.
FORBIDDEN_BUILD_MEMBERS = (
    "artifacts",
    "backend",
    "build_system",
    "bundle",
    "channel",
    "classpath",
    "download_url",
    "install_command",
    "interpreter",
    "language",
    "launcher",
    "mirror",
    "package_manager",
    "runtime",
    "runtime_files",
    "sidecar",
    "signing_identity",
    "toolchain_family",
    "toolchain_path",
    "toolchain_root",
    "trust_root",
    "version_manager",
)
# Every driver-bearing definition is closed by exact member set, never by a
# deny-list, so an optional selector, command, install or bundle member cannot
# be added anywhere. Each entry is (required members, optional members); the
# property set must equal their union and additionalProperties must be false.
#
# The package-controlled wire shapes deployed today. Frozen at these members.
DEPLOYED_WIRE_SHAPES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "buildCommandV6": (("driver", "source_dir", "type"), ()),
    "repositoryBuildCommandV1": (("driver", "repository", "target", "type"), ()),
    "skillBuildTargetV1": (("build_root", "driver", "source_dir"), ()),
}
# The schema-8 and descriptor schema-2 shapes decision 0008 reserved and the
# toolchain contract minted. They carry the REQUIRED and OPTIONAL toolchain
# requirement placement of decision 0007 and nothing else. The table predates the
# schemas on purpose: it held them to this member set while they were reservations
# and holds them to it now that they exist, so admission of a version was never
# an opportunity to widen the package surface.
TOOLCHAIN_WIRE_SHAPES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "buildCommandV8": (("driver", "source_dir", "toolchain", "type"), ()),
    "repositoryBuildCommandV2": (
        ("driver", "repository", "target", "toolchain", "type"),
        (),
    ),
    "skillBuildTargetV2": (("build_root", "driver", "source_dir"), ("toolchain",)),
}
# A member set closes which names may appear; it says nothing about what a name
# means. These properties must additionally match one exact schema, because a
# ``toolchain`` declared as a bare string, an open object, an object naming a
# path, or a reference to the resolved toolchain identity would satisfy the
# member set while leaving the trusted-preflight boundary unenforced.
EXACT_PROPERTY_SCHEMAS: dict[str, dict[str, dict[str, str]]] = {
    **{name: {"toolchain": TOOLCHAIN_REQUIREMENT_REF} for name in TOOLCHAIN_WIRE_SHAPES},
    ARTIFACT_DEFINITION: ARTIFACT_PROPERTY_SCHEMAS,
}
# Manager-authored driver-bearing shapes: build inputs and marker build records.
MANAGER_DRIVER_SHAPES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "goBuildInputV1": (
        (
            "build_root",
            "build_source",
            "command",
            "driver",
            "policy",
            "schema_version",
            "source_dir",
            "target",
            "toolchain",
        ),
        (),
    ),
    "goRepositoryBuildInputV1": (
        (
            "build_root",
            "command",
            "driver",
            "policy",
            "schema_version",
            "source",
            "source_dir",
            "target",
            "toolchain",
        ),
        (),
    ),
    "buildRecordV1": (
        ("artifact_path", "artifact_sha256", "cache_key", "driver", "receipt_sha256"),
        (),
    ),
    "buildRecordV1WithReceiptVersion": (
        (
            "artifact_path",
            "artifact_sha256",
            "cache_key",
            "driver",
            "execution_policy",
            "receipt_schema_version",
            "receipt_sha256",
        ),
        (),
    ),
    "buildRecordV2": (
        (
            "artifact_path",
            "artifact_sha256",
            "build_source",
            "cache_key",
            "commit",
            "declared_identity",
            "declared_locked_commit",
            "descriptor_target",
            "driver",
            "effective_identity",
            "execution_policy",
            "object_format",
            "receipt_schema_version",
            "receipt_sha256",
            "repository",
            "substituted",
        ),
        ("declared_tag", "substitution"),
    ),
}
CLOSED_DRIVER_SHAPES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    **DEPLOYED_WIRE_SHAPES,
    **MANAGER_DRIVER_SHAPES,
}
# Schema files still reserved by the boundary and deliberately not created here.
# The three slots decision 0007 names as the landing site of the toolchain
# requirement — manifest schema 8 and descriptor schema 2 — left this list when
# they were minted, because reservation is a statement about an unallocated
# number rather than a permanent prohibition. The receipt, marker and claim
# slots stay reserved: nothing in the toolchain contract re-versions them, and
# decision 0007 records that every frozen receipt, marker and cache key keeps
# its exact bytes under it.
RESERVED_SCHEMA_SLOTS = (
    "build-receipt-v3.schema.json",
    "build-receipt-v4.schema.json",
    "conformance-claim-v4.schema.json",
    "install-marker-v4.schema.json",
)
# The reserved slots the toolchain contract allocated. Each must exist, and each
# must reject the reserved driver identifiers exactly as every frozen surface
# does, so admission of a version is never admission of an identifier.
ADMITTED_TOOLCHAIN_SCHEMA_SLOTS = (
    "agent-skill-v8.schema.json",
    "csk-skill-v8.schema.json",
    "skill-build-v2.schema.json",
)
# The closed driver-to-execution-policy binding of the boundary. It covers both
# closed sets, because a claim minted after an identifier is admitted must pair
# it with the same policy the reservation allocated. A conformance claim may
# assert only the admitted wire driver set, so an identifier whose contract was
# rejected and retired stays structurally unassertable.
DRIVER_EXECUTION_POLICIES: dict[str, str] = {
    **{driver: PORTABLE_EXECUTION_POLICY for driver in ADMITTED_BUILD_DRIVERS},
    **{driver: RESERVED_DRIVER_EXECUTION_POLICY for driver in RESERVED_BUILD_DRIVERS},
}
CLAIM_SCHEMA_PATTERN = re.compile(r"conformance-claim-v(\d+)\.schema\.json\Z", re.ASCII)
CLAIM_DRIVER_MEMBER = "build_drivers"
CLAIM_ASSERTION_MEMBERS = ("driver", "execution_policy", "language", "operating_systems")
# ``items.oneOf`` is the single admission path for a driver assertion, so the
# container carrying it is closed to keywords that cannot open a second one.
# Draft 2020-12 ``items`` applies only to elements ``prefixItems`` did not cover,
# so a ``prefixItems`` entry is not a stylistic variation of the same list: it is
# an element position the closed ``oneOf`` never sees. The same is true of any
# array applicator added later, so this is an allow-list of keywords that cannot
# reach an element at all, not a deny-list of the ones known to.
CLAIM_DRIVER_CONTAINER_KEYWORDS = (
    "description",
    "items",
    "maxItems",
    "minItems",
    "title",
    "type",
    "uniqueItems",
)
# One driver assertion is exactly a closed object schema. Any other keyword is an
# applicator with its own reachability, and ``type`` is required for the same
# reason the requirement definition needs it: object keywords do not constrain a
# non-object, so an assertion without it would let a bare string sit in the list.
CLAIM_ASSERTION_KEYWORDS = ("additionalProperties", "properties", "required", "type")
COMMON_REF_PREFIX = "common.schema.json#/$defs/"
# Semantic failure classes the boundary itself owns.
BOUNDARY_FAILURE_CLASSES = (
    "build_artifact_class_unsupported",
    "build_descriptor_driver_unsupported",
    "build_descriptor_schema_unsupported",
    "build_package_code_execution_forbidden",
)
# Frozen surfaces that must reject every reserved identifier, with the JSON
# path at which each generated positive case names its driver.
FROZEN_DRIVER_CASES = (
    ("agent-skill-v6.schema.json", "agent-skill-v6", ("commands", "build-tool")),
    ("agent-skill-v7.schema.json", "agent-skill-v7", ("commands", "build-tool")),
    ("agent-skill-v7.schema.json", "agent-skill-v7", ("commands", "golden-tool")),
    ("csk-skill-v6.schema.json", "csk-skill-v6", ("commands", "build-tool")),
    ("csk-skill-v7.schema.json", "csk-skill-v7", ("commands", "build-tool")),
    ("skill-build-v1.schema.json", "skill-build-v1", ("targets", "golden-tool")),
    ("build-receipt-v1.schema.json", "build-receipt-v1", ("input",)),
    ("build-receipt-v2.schema.json", "build-receipt-v2", ("input",)),
    ("install-marker-v2.schema.json", "install-marker-v2", ("builds", "golden-tool")),
    ("install-marker-v3.schema.json", "install-marker-v3", ("builds", "golden-tool")),
    ("conformance-claim-v3.schema.json", "conformance-claim-v3", ("build_drivers", 0)),
    ("agent-skill-v8.schema.json", "agent-skill-v8", ("commands", "build-tool")),
    ("agent-skill-v8.schema.json", "agent-skill-v8", ("commands", "golden-tool")),
    ("csk-skill-v8.schema.json", "csk-skill-v8", ("commands", "build-tool")),
    ("skill-build-v2.schema.json", "skill-build-v2", ("targets", "golden-tool")),
)
# Frozen surfaces that carry the published artifact, with the JSON path at which
# each generated positive case names it. The structural closure above says what
# the definition and its three reference targets must be; these prove what the
# compiled validators actually do with the result, so a shape that reads as
# closed but is not enforced by the shipped receipts is still caught.
FROZEN_ARTIFACT_CASES = (
    ("build-receipt-v1.schema.json", "build-receipt-v1", ("artifact",)),
    ("build-receipt-v2.schema.json", "build-receipt-v2", ("artifact",)),
)


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

    def parse_int(text: str) -> int:
        value = int(text)
        if abs(value) > SAFE_INTEGER:
            raise ValidationFailure(f"{path}: integer outside CCJ-1 safe range: {text}")
        return value

    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=object_pairs,
            parse_int=parse_int,
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValidationFailure(f"{path}: invalid JSON: {exc}") from exc


def ccj1_bytes(value: Any) -> bytes:
    if isinstance(value, dict):
        value = dict(value)
        value.pop("sig", None)

    def validate(item: Any) -> None:
        if item is None or isinstance(item, (str, bool)):
            return
        if isinstance(item, int):
            if abs(item) > SAFE_INTEGER:
                raise ValidationFailure("integer outside CCJ-1 safe range")
            return
        if isinstance(item, list):
            for child in item:
                validate(child)
            return
        if isinstance(item, dict):
            for key, child in item.items():
                if not isinstance(key, str):
                    raise ValidationFailure("CCJ-1 object key is not text")
                validate(child)
            return
        raise ValidationFailure(f"unsupported CCJ-1 value {type(item).__name__}")

    validate(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def ccj1_sha256(value: Any) -> str:
    return "sha256:" + hashlib.sha256(ccj1_bytes(value)).hexdigest()


def schema_registry() -> tuple[Registry, dict[str, Path]]:
    documents: dict[str, Any] = {}
    paths: dict[str, Path] = {}
    for path in sorted(SCHEMAS.glob("*.json")):
        document = load_json(path)
        try:
            Draft202012Validator.check_schema(document)
        except SchemaError as exc:
            raise ValidationFailure(f"{path}: invalid Draft 2020-12 schema: {exc.message}") from exc
        schema_id = document.get("$id")
        if not isinstance(schema_id, str) or not schema_id:
            raise ValidationFailure(f"{path}: schema has no $id")
        if schema_id in documents:
            raise ValidationFailure(f"{path}: duplicate $id {schema_id}")
        documents[schema_id] = document
        paths[path.name] = path

    registry = Registry().with_resources(
        (schema_id, Resource.from_contents(document)) for schema_id, document in documents.items()
    )
    return registry, paths


def case_root(schema_name: str) -> Path:
    """The suite root that owns one schema's generated cases."""
    suite = CANDIDATE_SUITE if schema_name in CANDIDATE_CASE_SCHEMAS else SUITE
    return suite / "schema-cases"


def validate_schemas() -> None:
    registry, paths = schema_registry()
    covered: set[str] = set()
    for suite in (SUITE, CANDIDATE_SUITE):
        root = suite / "schema-cases"
        indexed: set[str] = set()
        for case in load_json(root / "index.json"):
            indexed.add(case["instance"])
            schema_name = case["schema"]
            if schema_name not in paths:
                raise ValidationFailure(f"schema case names unknown schema {schema_name}")
            # A case indexed under the wrong root would validate identically and
            # move a released digest, so the root is part of what is checked.
            if case_root(schema_name) != root:
                raise ValidationFailure(
                    f"{root.relative_to(ROOT).as_posix()}/index.json indexes {schema_name}, "
                    f"whose cases belong to {case_root(schema_name).relative_to(ROOT).as_posix()}"
                )
            schema = load_json(paths[schema_name])
            instance = load_json(root / case["instance"])
            errors = list(Draft202012Validator(schema, registry=registry).iter_errors(instance))
            semantic_error = validate_wire_semantics(schema_name, instance) if not errors else None
            actual = not errors and semantic_error is None
            expected = case["valid"]
            if actual != expected:
                detail = "valid" if actual else (errors[0].message if errors else semantic_error)
                raise ValidationFailure(
                    f"schema case {case['instance']} against {schema_name}: expected valid={expected}, got {detail}"
                )
            covered.add(schema_name)

        # The generator writes cases and never prunes them, so a renamed or
        # withdrawn case leaves its old file behind. Nothing validates an
        # unindexed file, but the suite manifest walks the directory and hashes
        # it, so an orphan silently enters a pinned digest. Two such files were
        # already shipping before this check existed.
        present = {
            path.relative_to(root).as_posix()
            for path in root.rglob("*.json")
            if path.name != "index.json"
        }
        orphans = sorted(present - indexed)
        if orphans:
            raise ValidationFailure(
                f"{root.relative_to(ROOT).as_posix()} carries case files that no index entry "
                f"names, so nothing validates them: {orphans}"
            )
        dangling = sorted(indexed - present)
        if dangling:
            raise ValidationFailure(
                f"{root.relative_to(ROOT).as_posix()}/index.json names missing cases: {dangling}"
            )

    wire_schemas = set(paths) - {"common.schema.json"}
    missing = sorted(wire_schemas - covered)
    if missing:
        raise ValidationFailure(f"schemas without positive/negative cases: {', '.join(missing)}")

    for prefix in ("agent-skill", "csk-skill"):
        for version in range(1, 7):
            schema_name = f"{prefix}-v{version}.schema.json"
            schema = load_json(paths[schema_name])
            legacy_with_v7_repository = {
                "schema_version": version,
                "build_repositories": {
                    "repo": {
                        "git": "https://example.com/repo.git",
                        "locked_commit": {
                            "object_format": "sha1",
                            "hex": "0" * 40,
                        },
                    }
                },
            }
            if version >= 2:
                legacy_with_v7_repository["runtime_roots"] = []
                legacy_with_v7_repository["dependencies"] = {"commands": {}}
            if version >= 3:
                legacy_with_v7_repository["capabilities"] = {}
            if version >= 4:
                legacy_with_v7_repository["dependencies"]["skills"] = {}
            if version >= 5:
                legacy_with_v7_repository["dependencies"]["mcp_servers"] = {}
            if version >= 6:
                legacy_with_v7_repository["build_roots"] = []
            schema_errors = list(
                Draft202012Validator(schema, registry=registry).iter_errors(
                    legacy_with_v7_repository
                )
            )
            semantic_error = (
                validate_wire_semantics(schema_name, legacy_with_v7_repository)
                if not schema_errors
                else None
            )
            if not schema_errors and semantic_error is None:
                raise ValidationFailure(
                    f"{schema_name}: accepts schema-7-only build_repositories"
                )


def retired_descriptor_offsets(text: str) -> list[int]:
    """Offsets of the retired descriptor stem, ignoring the frozen algorithm."""
    offsets: list[int] = []
    start = 0
    while True:
        index = text.find(RETIRED_DESCRIPTOR_STEM, start)
        if index < 0:
            return offsets
        if not text.startswith(BUILD_SOURCE_ALGORITHM_NAMESPACE, index):
            offsets.append(index)
        start = index + 1


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def surface_files() -> list[Path]:
    files: list[Path] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        if any(part in NON_SURFACE_DIRECTORIES for part in path.relative_to(ROOT).parts):
            continue
        files.append(path)
    return files


def validate_repository_descriptor_identity() -> None:
    descriptor_schema = SCHEMAS / REPOSITORY_DESCRIPTOR_SCHEMA
    if not descriptor_schema.is_file():
        raise ValidationFailure(f"missing repository descriptor schema {REPOSITORY_DESCRIPTOR_SCHEMA}")
    document = load_json(descriptor_schema)
    if not document["$id"].endswith(f"/{REPOSITORY_DESCRIPTOR_SCHEMA}"):
        raise ValidationFailure(f"{descriptor_schema}: $id does not name the neutral descriptor schema")
    if document["title"] != f"{REPOSITORY_DESCRIPTOR_NAME} schema 1":
        raise ValidationFailure(f"{descriptor_schema}: title does not name {REPOSITORY_DESCRIPTOR_NAME}")

    common = load_json(SCHEMAS / "common.schema.json")
    selection = common["$defs"]["repositoryDescriptorSelectionV1"]["properties"]["path"]
    if selection != {"const": REPOSITORY_DESCRIPTOR_NAME}:
        raise ValidationFailure(
            f"repositoryDescriptorSelectionV1.path is not fixed to {REPOSITORY_DESCRIPTOR_NAME}: {selection}"
        )

    # A receipt that names any other descriptor path is a schema rejection,
    # not an alias. Proved end to end against the real compiled validator and
    # the generated positive example.
    registry, paths = schema_registry()
    receipt_schema = load_json(paths["build-receipt-v2.schema.json"])
    validator = Draft202012Validator(receipt_schema, registry=registry)
    receipt = load_json(SUITE / "schema-cases" / "build-receipt-v2" / "valid.json")
    descriptor = receipt["input"]["source"]["descriptor"]
    if descriptor["path"] != REPOSITORY_DESCRIPTOR_NAME:
        raise ValidationFailure(
            f"generated receipt v2 example selects {descriptor['path']!r}, want {REPOSITORY_DESCRIPTOR_NAME!r}"
        )
    if list(validator.iter_errors(receipt)):
        raise ValidationFailure("generated receipt v2 example does not validate")
    descriptor["path"] = f"{RETIRED_DESCRIPTOR_STEM}.json"
    if not list(validator.iter_errors(receipt)):
        raise ValidationFailure("receipt v2 accepts the retired repository descriptor name")

    # Marker v3 carries no descriptor path of its own: it binds the selected
    # target by name and the descriptor bytes transitively through the receipt
    # hash, so the retired name is not expressible there at all.
    build_record = load_json(SCHEMAS / "common.schema.json")["$defs"]["buildRecordV2"]
    if "descriptor_target" not in build_record["properties"] or "descriptor" in build_record["properties"]:
        raise ValidationFailure(
            "buildRecordV2 must bind descriptor_target only, never a descriptor path"
        )

    # The retired name must be absent from every protocol surface, including
    # this validator, the generator, documentation and release metadata.
    for path in surface_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, ValueError):
            continue
        offsets = retired_descriptor_offsets(text)
        if offsets:
            line = text.count("\n", 0, offsets[0]) + 1
            raise ValidationFailure(
                f"{display_path(path)}:{line}: retired repository descriptor name is not an alias and must be absent"
            )

    # The rename must not have reached the byte-frozen schema-6 build-source
    # digest algorithm, which shares the retired stem.
    frozen_marker = SUITE / "schema-cases" / "install-marker-v2" / "valid.json"
    if FROZEN_BUILD_SOURCE_ALGORITHM not in frozen_marker.read_text(encoding="utf-8"):
        raise ValidationFailure(
            f"{display_path(frozen_marker)}: frozen build-source algorithm {FROZEN_BUILD_SOURCE_ALGORITHM} was renamed"
        )


def driver_bearing_definitions(common: Any) -> dict[str, Any]:
    """Every common definition whose object shape names a build driver."""
    return {
        name: definition
        for name, definition in common["$defs"].items()
        if isinstance(definition, dict)
        and isinstance(definition.get("properties"), dict)
        and "driver" in definition["properties"]
    }


def is_decision_record(path: Path) -> bool:
    try:
        parts = path.relative_to(ROOT).parts
    except ValueError:
        return False
    return bool(parts) and parts[0] == DRIVER_RESERVATION_EXEMPT_DIRECTORY


def reserved_schema_slot_paths() -> list[Path]:
    """Schema files the boundary reserves but deliberately does not create."""
    return [SCHEMAS / slot for slot in RESERVED_SCHEMA_SLOTS]


def set_at(document: Any, path: tuple[Any, ...], value: Any) -> None:
    node = document
    for key in path:
        node = node[key]
    node["driver"] = value


def replace_at(document: Any, path: tuple[Any, ...], value: Any) -> None:
    """Replace the node a JSON path names, rather than a member inside it."""
    node = document
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value


def reserved_boundary_identifiers() -> tuple[str, ...]:
    """Reserved names that must not appear on any surface outside a decision.

    The reserved capability-evidence record version is deliberately not here.
    Unlike a driver identifier or a policy identity, a record version already
    appears in the frozen rc.5 corpus and release gate as the example of a
    version that MUST be rejected, so absence would be the wrong test. Its
    non-admission is proved positively by
    ``check_reserved_evidence_record_is_rejected`` instead.
    """
    return (*RESERVED_BUILD_DRIVERS, RESERVED_DRIVER_EXECUTION_POLICY)


def check_reserved_evidence_record_is_rejected() -> None:
    """Prove the reserved evidence record version is still un-admitted.

    The rc.5 corpus must keep asserting that a record carrying the reserved
    version is invalid. This is stronger than an absence scan: it shows the
    frozen suite actively rejects the reservation rather than merely never
    mentioning it.
    """
    vector = SUITE / "vectors" / "go-host-execution-policy.json"
    cases = load_json(vector).get("capability_evidence_cases", [])
    matching = [
        case
        for case in cases
        if case.get("record_version") == RESERVED_CAPABILITY_EVIDENCE_RECORD
    ]
    if not matching:
        raise ValidationFailure(
            f"{display_path(vector)}: no case proves the reserved capability-evidence "
            "record version is rejected"
        )
    for case in matching:
        if case.get("record_valid") is not False or case.get("build_permitted") is not False:
            raise ValidationFailure(
                f"{display_path(vector)}: case {case.get('name')!r} admits the reserved "
                "capability-evidence record version"
            )
        if case.get("expected_error") != "build_execution_capability_evidence_invalid":
            raise ValidationFailure(
                f"{display_path(vector)}: case {case.get('name')!r} does not reject the "
                "reserved capability-evidence record version as an invalid record"
            )


def check_closed_member_set(
    name: str,
    definition: Any,
    required: tuple[str, ...],
    optional: tuple[str, ...],
) -> None:
    """Hold one definition to its exact member set, not to a deny-list.

    An allow-list is what makes the boundary checkable: a deny-list accepts any
    member nobody thought to forbid, so an optional language selector, an
    arbitrary command, or a runtime-bundle member would pass unnoticed.

    The closure is only meaningful over objects. ``properties``, ``required`` and
    ``additionalProperties`` do not constrain a string, a number or an array, so
    a definition that declares any other type — or declares none, or unions the
    object with a scalar — carries the closed member set as decoration while
    admitting a package-controlled value of any shape.
    """
    if not isinstance(definition, dict):
        raise ValidationFailure(
            f"common.schema.json $defs.{name} is not a schema object, so it carries no "
            f"closed member set at all: found {definition!r}"
        )
    if definition.get("type") != "object":
        raise ValidationFailure(
            f"common.schema.json $defs.{name} is not an object schema, so its closed "
            f"member set constrains nothing: found type {definition.get('type')!r}"
        )
    if definition.get("additionalProperties") is not False:
        raise ValidationFailure(
            f"common.schema.json $defs.{name} does not close additionalProperties"
        )
    expected_members = set(required) | set(optional)
    members = set(definition.get("properties", {}))
    if members != expected_members:
        added = sorted(members - expected_members)
        removed = sorted(expected_members - members)
        raise ValidationFailure(
            f"common.schema.json $defs.{name} is not its closed member set: "
            f"added {added}, removed {removed}"
        )
    declared_required = set(definition.get("required", []))
    if declared_required != set(required):
        raise ValidationFailure(
            f"common.schema.json $defs.{name} required set is not closed: "
            f"expected {sorted(required)}, found {sorted(declared_required)}"
        )


def check_exact_property_schemas(name: str, definition: Any) -> None:
    """Hold named properties to an exact schema, not merely to a member name.

    The member-set table answers *which* names a definition may carry. Without
    this check it accepts any meaning for them, so a reserved slot could declare
    ``toolchain`` as a string, an open object, an object naming a toolchain path,
    or a reference to the resolved toolchain identity, and the gate would call
    the closed requirement object enforced when it is not.
    """
    for member, expected in sorted(EXACT_PROPERTY_SCHEMAS.get(name, {}).items()):
        found = definition.get("properties", {}).get(member)
        if found != expected:
            raise ValidationFailure(
                f"common.schema.json $defs.{name}.{member} is not exactly {expected}: "
                f"found {found}"
            )


def check_toolchain_requirement_definition(common: Any) -> None:
    """Keep the referenced requirement object resolvable and closed.

    Where the requirement lands is this boundary's to fix; the version grammar,
    comparison, and diagnostics inside it belong to decision 0007 and are not
    restated. What is enforced here is that the three reserved slots cannot point
    at a definition that does not exist, and that the definition, once minted, is
    an object schema carrying exactly the two members both decisions already close
    it to. The object requirement is load-bearing rather than stylistic: a slot
    whose ``$ref`` resolves to ``type: string`` — or to a definition declaring no
    type at all, or to an ``object``/``string`` union — would let the package hand
    the manager a free-text toolchain value while every member-set check still
    passed, which is the trusted-preflight boundary read back as prose.
    """
    definitions = common["$defs"]
    # Only the shapes whose exact-schema entry actually names the requirement
    # reference make the definition mandatory. The table also pins property
    # schemas that have nothing to do with the toolchain, and a shape listed for
    # one of those must not make an unminted reservation look overdue.
    referencing = [
        name
        for name in sorted(EXACT_PROPERTY_SCHEMAS)
        if name in definitions
        and TOOLCHAIN_REQUIREMENT_REF in EXACT_PROPERTY_SCHEMAS[name].values()
    ]
    definition = definitions.get(TOOLCHAIN_REQUIREMENT_DEFINITION)
    if definition is None:
        if referencing:
            raise ValidationFailure(
                f"common.schema.json {referencing} reference $defs."
                f"{TOOLCHAIN_REQUIREMENT_DEFINITION}, which does not exist"
            )
        return
    required, optional = TOOLCHAIN_REQUIREMENT_MEMBERS
    check_closed_member_set(TOOLCHAIN_REQUIREMENT_DEFINITION, definition, required, optional)


def check_build_artifact_closure(common: Any) -> None:
    """Hold the published artifact to one exact object schema.

    One build publishes exactly one artifact, and every downstream identity —
    the receipt, the marker, the shim relationship, currentness, and garbage
    collection — is built on that one path and that one digest. Comparing only
    the property names and ``additionalProperties`` leaves the same object-
    keyword escape that the requirement definition and the claim assertions
    already close: ``properties``, ``required`` and ``additionalProperties``
    constrain objects only, so a definition typed ``string``, typed
    ``["object","string"]``, carrying no type, or expressed as a boolean schema
    keeps the three names while accepting a launcher plus a runtime. Dropping
    members from ``required`` is the same failure from the other side: it keeps
    the names available and admits an artifact that asserts nothing.

    Pinning each property to a shared definition is a closure only while that
    definition still means what the boundary fixed, so the three reference
    targets are held to their exact canonical schemas here as well.
    """
    definition = common["$defs"].get(ARTIFACT_DEFINITION)
    if definition is None:
        raise ValidationFailure(
            "common.schema.json no longer declares the closed single-file artifact "
            f"$defs.{ARTIFACT_DEFINITION}"
        )
    required, optional = ARTIFACT_MEMBERS
    try:
        check_closed_member_set(ARTIFACT_DEFINITION, definition, required, optional)
        check_exact_property_schemas(ARTIFACT_DEFINITION, definition)
    except ValidationFailure as failure:
        raise ValidationFailure(
            f"{ADMITTED_ARTIFACT_CLASS} is not the closed single-file artifact: {failure}"
        ) from failure
    check_artifact_reference_targets(common)


def schema_difference(expected: Any, found: Any) -> str:
    """Account keyword by keyword for how a pinned schema was changed.

    A pinned schema is only auditable if its failure says which keyword moved
    and in which direction. Printing both schemas whole would bury a one-digit
    bound change in the path grammar it sits next to.
    """
    if not isinstance(found, dict):
        return f"expected a schema object, found {found!r}"
    absent = object()
    changes: list[str] = []
    for keyword in sorted(set(expected) | set(found)):
        want = expected.get(keyword, absent)
        have = found.get(keyword, absent)
        if want == have:
            continue
        if want is absent:
            changes.append(f"{keyword} added as {have!r}")
        elif have is absent:
            changes.append(f"{keyword} removed, was {want!r}")
        else:
            changes.append(f"{keyword} changed from {want!r} to {have!r}")
    return "; ".join(changes)


def check_artifact_reference_targets(common: Any) -> None:
    """Hold the artifact's reference targets to their exact canonical schemas.

    ``check_exact_property_schemas`` pins ``path``, ``sha256`` and ``size`` to
    three shared definitions, which is satisfied by a reference to a definition
    somebody has since widened. ``check_build_artifact_rejections`` then samples
    invalid values, which catches a target opened wholesale but not one widened
    by a single keyword: ``maxLength`` raised by one, uppercase added to the
    digest alphabet, or the safe-integer ceiling lifted by one all leave every
    sampled negative still rejected while the compiled receipt validator starts
    accepting a longer path, an uppercase digest and an out-of-range size.

    Those bounds are ``native-executable-v1``'s identity — the path names where
    the published file lives, the digest is the only description of what it
    contains, and the size is what the manager recorded — so each target is held
    structurally to the exact schema this boundary fixed rather than to a sample
    of the values it happens to reject today.
    """
    definitions = common.get("$defs", {})
    referenced: set[str] = set()
    for member, schema in sorted(ARTIFACT_PROPERTY_SCHEMAS.items()):
        reference = schema.get("$ref", "")
        if not reference.startswith(LOCAL_DEFS_PREFIX):
            raise ValidationFailure(
                f"{ADMITTED_ARTIFACT_CLASS} member {member!r} is pinned to {reference!r}, "
                "which is not a shared definition this boundary can hold to a schema"
            )
        referenced.add(reference[len(LOCAL_DEFS_PREFIX) :])
    if referenced != set(ARTIFACT_REFERENCE_TARGETS):
        unpinned = sorted(referenced - set(ARTIFACT_REFERENCE_TARGETS))
        unused = sorted(set(ARTIFACT_REFERENCE_TARGETS) - referenced)
        raise ValidationFailure(
            f"{ADMITTED_ARTIFACT_CLASS} identity targets and their canonical schemas "
            f"have diverged: unpinned {unpinned}, pinned but unreferenced {unused}"
        )
    for name in sorted(ARTIFACT_REFERENCE_TARGETS):
        expected = ARTIFACT_REFERENCE_TARGETS[name]
        found = definitions.get(name)
        if found != expected:
            raise ValidationFailure(
                f"{ADMITTED_ARTIFACT_CLASS} identity target common.schema.json "
                f"$defs.{name} is not its canonical schema, so the pinned reference "
                f"no longer bounds what it names: {schema_difference(expected, found)}"
            )


def rejected_artifact_instances(artifact: Any) -> list[tuple[str, Any]]:
    """Artifact values the admitted class must reject, derived from a real one.

    Each is built from the generated positive case so the corpus, not this
    file, decides what a valid artifact looks like. The scalar and array cases
    are the rejected ``runtime-bundle`` read literally: a launcher name, and a
    list of published files.
    """
    if not isinstance(artifact, dict):
        raise ValidationFailure(
            f"generated artifact case is not an object: found {artifact!r}"
        )
    digest = artifact["sha256"]
    rejected: list[tuple[str, Any]] = [
        ("a launcher name instead of a published file", artifact["path"]),
        ("a list of bundle members", [dict(artifact)]),
        ("a boolean standing in for the artifact", True),
        ("an object that asserts nothing", {}),
        ("a runtime beside the published file", {**artifact, "runtime": "runtime-image"}),
        ("a path that escapes the published tree", {**artifact, "path": "../" + artifact["path"]}),
        ("an absolute path", {**artifact, "path": "/" + artifact["path"]}),
        ("an unprefixed digest", {**artifact, "sha256": digest.split(":", 1)[-1]}),
        ("a negative size", {**artifact, "size": -1}),
        ("a size that is not an integer", {**artifact, "size": str(artifact["size"])}),
    ]
    rejected.extend(
        (
            f"an artifact without {member}",
            {name: value for name, value in artifact.items() if name != member},
        )
        for member in sorted(artifact)
    )
    return rejected


def check_build_artifact_rejections(registry: Registry, paths: dict[str, Path]) -> None:
    """Prove the artifact closure against the compiled validators.

    Reading the definition proves what it says; this proves what the frozen
    receipt surfaces do with it. It is deliberately behavioural and therefore
    finite: it catches a reference target opened wholesale, while
    ``check_artifact_reference_targets`` is what holds ``portablePath``,
    ``sha256`` and ``nonNegativeSafeInteger`` to their exact schemas, including
    the narrow widenings no sample of rejected values can see.
    """
    for schema_name, case, path in FROZEN_ARTIFACT_CASES:
        schema = load_json(paths[schema_name])
        validator = Draft202012Validator(schema, registry=registry)
        valid = load_json(SUITE / "schema-cases" / case / "valid.json")
        if list(validator.iter_errors(valid)):
            raise ValidationFailure(f"generated {case} positive case does not validate")
        node = valid
        for key in path:
            node = node[key]
        for label, value in rejected_artifact_instances(node):
            instance = load_json(SUITE / "schema-cases" / case / "valid.json")
            replace_at(instance, path, value)
            if not list(validator.iter_errors(instance)):
                raise ValidationFailure(
                    f"{schema_name} accepts {label} as {ADMITTED_ARTIFACT_CLASS} "
                    f"at {'/'.join(str(key) for key in path)}"
                )


def conformance_claim_schemas() -> list[tuple[int, Path]]:
    """Every conformance claim schema that exists, oldest version first."""
    found: list[tuple[int, Path]] = []
    for path in sorted(SCHEMAS.glob("conformance-claim-v*.schema.json")):
        match = CLAIM_SCHEMA_PATTERN.search(path.name)
        if match:
            found.append((int(match.group(1)), path))
    return sorted(found)


def closed_const(common: Any, node: Any, label: str) -> Any:
    """Resolve a schema node that must be a const, directly or by reference."""
    if not isinstance(node, dict):
        raise ValidationFailure(f"{label} is not a schema object")
    if set(node) == {"const"}:
        return node["const"]
    if set(node) == {"$ref"}:
        ref = node["$ref"]
        if not isinstance(ref, str) or not ref.startswith(COMMON_REF_PREFIX):
            raise ValidationFailure(f"{label} references {ref!r} outside the shared definitions")
        target = common["$defs"].get(ref[len(COMMON_REF_PREFIX) :])
        if not isinstance(target, dict) or set(target) != {"const"}:
            raise ValidationFailure(f"{label} references {ref!r}, which is not a closed const")
        return target["const"]
    raise ValidationFailure(f"{label} is neither a const nor a shared const reference")


def check_claim_driver_container(label: str, member: Any) -> list:
    """Close the assertion list so ``items.oneOf`` is its only element path.

    Reading ``items.oneOf`` and stopping there answers what the listed branches
    say, not what the list admits. Under Draft 2020-12 ``items`` applies only to
    the elements ``prefixItems`` did not already cover, so a single ``prefixItems``
    entry silently exempts element zero from the closed ``oneOf`` — the shipped
    claim mutated that way is accepted by the real validator. Rather than name
    that keyword and the next one nobody has thought of, the container is closed
    to keywords that cannot reach an element at all.
    """
    if not isinstance(member, dict):
        raise ValidationFailure(f"{label} is not a schema object")
    unlisted = sorted(set(member) - set(CLAIM_DRIVER_CONTAINER_KEYWORDS))
    if unlisted:
        raise ValidationFailure(
            f"{label} declares array keywords outside the closed container set: "
            f"{unlisted}; every element must be reached by items.oneOf alone"
        )
    if member.get("type") != "array":
        raise ValidationFailure(
            f"{label} is not an array schema: found type {member.get('type')!r}"
        )
    items = member.get("items")
    if not isinstance(items, dict) or set(items) != {"oneOf"}:
        raise ValidationFailure(
            f"{label} does not constrain every element with exactly items.oneOf"
        )
    assertions = items["oneOf"]
    if not isinstance(assertions, list) or not assertions:
        raise ValidationFailure(
            f"{label} is not a closed oneOf over driver assertions"
        )
    return assertions


def check_claim_driver_admission(common: Any) -> None:
    """A conformance claim may assert exactly the admitted wire driver set.

    Reservation is not admission, and a reserved contract may be rejected and its
    identifier retired unused. So claim membership cannot be a fixed count: the
    current claim schema asserts exactly the drivers admitted when it is minted,
    an older frozen claim asserts a subset of them, and a reserved or retired
    identifier can never be asserted at all. Each assertion also pairs its driver
    with the policy the closed table binds to it, so the section 2 binding is
    structural rather than a prose rule a claim author could violate.

    Which schema is current is decided before anything is inspected. Choosing it
    from the schemas that happen to declare the driver member would let a newer
    claim drop the member and hand the title back to a frozen predecessor, which
    is admission by omission: the newest claim would assert nothing while the gate
    reported the older one as covering the admitted set.
    """
    schemas = conformance_claim_schemas()
    if not schemas:
        raise ValidationFailure("no conformance claim schema exists")
    _, current = schemas[-1]
    current_claimed: set[str] | None = None
    for _, path in schemas:
        claim = load_json(path)
        member = claim.get("properties", {}).get(CLAIM_DRIVER_MEMBER)
        if member is None:
            if path == current:
                raise ValidationFailure(
                    f"{display_path(path)}: the current claim schema does not declare "
                    f"{CLAIM_DRIVER_MEMBER}, so it asserts no admitted wire driver"
                )
            continue
        assertions = check_claim_driver_container(
            f"{display_path(path)}: {CLAIM_DRIVER_MEMBER}", member
        )
        claimed: set[str] = set()
        for assertion in assertions:
            label = f"{display_path(path)}: {CLAIM_DRIVER_MEMBER} assertion"
            if not isinstance(assertion, dict):
                raise ValidationFailure(f"{label} is not a schema object")
            unlisted = sorted(set(assertion) - set(CLAIM_ASSERTION_KEYWORDS))
            if unlisted:
                raise ValidationFailure(
                    f"{label} declares keywords outside the closed assertion set: {unlisted}"
                )
            if assertion.get("type") != "object":
                raise ValidationFailure(
                    f"{label} is not an object schema: found type {assertion.get('type')!r}"
                )
            properties = assertion.get("properties")
            if not isinstance(properties, dict):
                raise ValidationFailure(f"{label} declares no properties")
            if assertion.get("additionalProperties") is not False:
                raise ValidationFailure(f"{label} does not close additionalProperties")
            if tuple(sorted(properties)) != CLAIM_ASSERTION_MEMBERS or set(
                assertion.get("required", [])
            ) != set(CLAIM_ASSERTION_MEMBERS):
                raise ValidationFailure(
                    f"{label} is not the closed assertion member set "
                    f"{list(CLAIM_ASSERTION_MEMBERS)}"
                )
            driver = properties["driver"]
            if not isinstance(driver, dict) or set(driver) != {"const"}:
                raise ValidationFailure(f"{label} does not close driver with a const")
            name = driver["const"]
            if name not in ADMITTED_BUILD_DRIVERS:
                raise ValidationFailure(
                    f"{label} asserts {name!r}, which is not in the admitted wire driver set"
                )
            if name in claimed:
                raise ValidationFailure(f"{label} asserts {name!r} more than once")
            claimed.add(name)
            policy = closed_const(
                common, properties["execution_policy"], f"{label} {name!r} execution_policy"
            )
            if policy != DRIVER_EXECUTION_POLICIES[name]:
                raise ValidationFailure(
                    f"{label} pairs {name!r} with execution policy {policy!r} instead of "
                    f"{DRIVER_EXECUTION_POLICIES[name]!r}"
                )
        if path == current:
            current_claimed = claimed
    if current_claimed is None:
        raise ValidationFailure("no conformance claim schema asserts a build driver")
    missing = sorted(set(ADMITTED_BUILD_DRIVERS) - current_claimed)
    if missing:
        raise ValidationFailure(
            f"{display_path(current)}: the current claim schema does not assert every "
            f"admitted wire driver: missing {missing}"
        )


def validate_additional_driver_boundary() -> None:
    """Guard the decision 0008 driver, version and artifact boundary.

    The six additional-language identifiers are reserved, not admitted. Nothing
    outside the boundary decision may name one, every frozen schema must reject
    one, the reserved schema slots must stay unallocated, and the wire must keep
    expressing exactly one artifact per build.
    """
    decision = ROOT / ADDITIONAL_DRIVER_BOUNDARY_DECISION
    if not decision.is_file():
        raise ValidationFailure(f"missing boundary decision {ADDITIONAL_DRIVER_BOUNDARY_DECISION}")
    decision_text = decision.read_text(encoding="utf-8")

    # The decision is the sole normative source of the closed identifier set,
    # the admitted and rejected artifact classes, the boundary failure classes,
    # and the deferral owner.
    required_terms = (
        *ADMITTED_BUILD_DRIVERS,
        *RESERVED_BUILD_DRIVERS,
        ADMITTED_DRIVER_SET_LABEL,
        RESERVED_DRIVER_SET_LABEL,
        ADMITTED_ARTIFACT_CLASS,
        REJECTED_ARTIFACT_CLASS,
        *BOUNDARY_FAILURE_CLASSES,
        HARDENED_EXECUTION_OWNER,
        PORTABLE_EXECUTION_POLICY,
        RESERVED_DRIVER_EXECUTION_POLICY,
        RESERVED_CAPABILITY_EVIDENCE_RECORD,
        TOOLCHAIN_REQUIREMENT_OBJECT,
        TOOLCHAIN_REQUIREMENT_DEFINITION,
        *TOOLCHAIN_WIRE_SHAPES,
    )
    for term in required_terms:
        if term not in decision_text:
            raise ValidationFailure(
                f"{ADDITIONAL_DRIVER_BOUNDARY_DECISION}: boundary does not fix {term!r}"
            )

    # A boundary that adds no containment may not name a deferred hardened
    # guarantee, because naming one in an admitting decision reads as a claim.
    for guarantee in sorted(DEFERRED_HARDENED_GUARANTEES):
        if guarantee in decision_text:
            raise ValidationFailure(
                f"{ADDITIONAL_DRIVER_BOUNDARY_DECISION}: names deferred hardened guarantee {guarantee!r}"
            )

    # Reservation is not admission: no surface file outside the decision record
    # directory may name a reserved driver, the reserved execution-policy
    # identity, or the reserved capability-evidence record version until the
    # contract lands and the admitted sets above grow with it.
    reserved = reserved_boundary_identifiers()
    for path in surface_files():
        if is_decision_record(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, ValueError):
            continue
        for identifier in reserved:
            index = text.find(identifier)
            if index >= 0:
                line = text.count("\n", 0, index) + 1
                raise ValidationFailure(
                    f"{display_path(path)}:{line}: reserved identifier {identifier!r} is not admitted by any schema version"
                )

    check_reserved_evidence_record_is_rejected()

    # The reserved wire versions are allocated by the boundary and minted by the
    # integration task, so their schema files must not exist yet.
    for slot in reserved_schema_slot_paths():
        if slot.exists():
            raise ValidationFailure(
                f"reserved schema slot {slot.name} was created outside the integration task"
            )
    # The three slots the toolchain contract allocated are the converse test: a
    # slot that leaves the reserved list must actually have been minted, so the
    # list cannot be shortened to silence the guard above.
    for slot in ADMITTED_TOOLCHAIN_SCHEMA_SLOTS:
        if not (SCHEMAS / slot).is_file():
            raise ValidationFailure(
                f"schema slot {slot} left the reserved set without being minted"
            )

    # Every driver-bearing definition closes its driver with a const, so a
    # generic language, enum widening or pattern cannot smuggle a driver in.
    common = load_json(SCHEMAS / "common.schema.json")
    definitions = driver_bearing_definitions(common)
    if not definitions:
        raise ValidationFailure("common.schema.json declares no driver-bearing definition")
    for name, definition in sorted(definitions.items()):
        driver = definition["properties"]["driver"]
        if set(driver) != {"const"} or driver["const"] not in ADMITTED_BUILD_DRIVERS:
            raise ValidationFailure(
                f"common.schema.json $defs.{name}.driver is not a const over the admitted drivers: {driver}"
            )
        if "driver" not in definition.get("required", []):
            raise ValidationFailure(f"common.schema.json $defs.{name} does not require driver")

    # Every driver-bearing definition matches its exact closed member set. The
    # table also carries the reserved schema-8 and descriptor schema-2 shapes,
    # so the toolchain requirement placement of decision 0007 is enforced from
    # the moment those definitions are minted. A driver-bearing definition that
    # is not in the table at all is a failure, because an unlisted shape is an
    # unreviewed package surface.
    closed_shapes = {**CLOSED_DRIVER_SHAPES, **TOOLCHAIN_WIRE_SHAPES}
    for name, definition in sorted(definitions.items()):
        if name not in closed_shapes:
            raise ValidationFailure(
                f"common.schema.json $defs.{name} is a driver-bearing definition "
                "outside the closed boundary member-set table"
            )
        required, optional = closed_shapes[name]
        check_closed_member_set(name, definition, required, optional)
        check_exact_property_schemas(name, definition)
    for name in sorted(CLOSED_DRIVER_SHAPES):
        if name not in definitions:
            raise ValidationFailure(
                f"common.schema.json no longer declares the closed driver-bearing definition {name}"
            )
    # A reserved shape minted without a driver would never be driver-bearing, so
    # neither the member-set table nor the exact property schemas above would see
    # it. That is the one way the reserved slots could be smuggled past the gate.
    for name in sorted(TOOLCHAIN_WIRE_SHAPES):
        if name in common["$defs"] and name not in definitions:
            raise ValidationFailure(
                f"common.schema.json $defs.{name} was minted without a driver"
            )
    check_toolchain_requirement_definition(common)
    check_claim_driver_admission(common)

    # Defense in depth behind the tables: a name that can never carry protocol
    # meaning must not appear as a property anywhere in the shared definitions,
    # including in a definition that names no driver.
    for name, definition in sorted(common["$defs"].items()):
        if not isinstance(definition, dict):
            continue
        properties = definition.get("properties")
        if not isinstance(properties, dict):
            continue
        forbidden = sorted(set(properties).intersection(FORBIDDEN_BUILD_MEMBERS))
        if forbidden:
            raise ValidationFailure(
                f"common.schema.json $defs.{name} admits forbidden build members {forbidden}"
            )

    # One build publishes exactly one artifact. A bundle member would redefine
    # the receipt, marker, shim and currentness identities at once, and so would
    # an artifact that is not an object or that requires nothing.
    check_build_artifact_closure(common)

    # Prove the rejection end to end against the real compiled validators and
    # the generated positive cases rather than by reading the schema text.
    registry, paths = schema_registry()
    check_build_artifact_rejections(registry, paths)
    for schema_name, case, path in FROZEN_DRIVER_CASES:
        schema = load_json(paths[schema_name])
        validator = Draft202012Validator(schema, registry=registry)
        for driver in RESERVED_BUILD_DRIVERS:
            instance = load_json(case_root(schema_name) / case / "valid.json")
            if list(validator.iter_errors(instance)):
                raise ValidationFailure(f"generated {case} positive case does not validate")
            set_at(instance, path, driver)
            if not list(validator.iter_errors(instance)):
                raise ValidationFailure(
                    f"{schema_name} accepts reserved driver {driver!r} at {'/'.join(str(key) for key in path)}"
                )


def is_below_or_equal(path: str, root: str) -> bool:
    return root == "." or path == root or path.startswith(root + "/")


HOST_PATTERN = r"[A-Za-z0-9][A-Za-z0-9.-]*"
SSH_USER_PATTERN = r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}"
HTTPS_REPOSITORY = re.compile(
    rf"https://(?P<host>{HOST_PATTERN})/(?P<path>.+)", re.ASCII
)
SSH_URI_REPOSITORY = re.compile(
    rf"ssh://(?:(?P<user>{SSH_USER_PATTERN})@)?"
    rf"(?P<host>{HOST_PATTERN})/(?P<path>.+)",
    re.ASCII,
)
SSH_SCP_REPOSITORY = re.compile(
    rf"(?:(?P<user>{SSH_USER_PATTERN})@)?"
    rf"(?P<host>{HOST_PATTERN}):(?P<path>.+)",
    re.ASCII,
)
SSH_REPOSITORY_PATH = re.compile(r"[A-Za-z0-9._/-]+", re.ASCII)
LOWERCASE_HOST = re.compile(r"[a-z0-9][a-z0-9.-]*", re.ASCII)


def validate_repository_path(path: str, *, ssh: bool) -> str | None:
    try:
        path.encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        return "repository path must contain only valid Unicode scalar text"
    if ssh and SSH_REPOSITORY_PATH.fullmatch(path) is None:
        return "SSH repository path must contain only ASCII letters, digits, dot, underscore, hyphen, and slash"
    if (
        not path
        or path.startswith("/")
        or path.endswith("/")
        or any(component in {"", ".", ".."} for component in path.split("/"))
    ):
        return "repository path must have non-empty components other than dot or dot-dot"
    if any(
        character.isspace()
        or character in "%?#\\:"
        or ord(character) < 32
        or 127 <= ord(character) <= 159
        for character in path
    ):
        return "repository path contains a forbidden character"
    return None


def validate_repository_git(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    if len(value) > 4096:
        return "repository Git source exceeds 4096 Unicode scalar values"
    match = HTTPS_REPOSITORY.fullmatch(value)
    ssh = False
    if match is None:
        match = SSH_URI_REPOSITORY.fullmatch(value)
        ssh = match is not None
    if match is None:
        match = SSH_SCP_REPOSITORY.fullmatch(value)
        ssh = match is not None
    if match is None:
        return "repository Git source must be exact HTTPS, SSH URI, or SSH SCP form"
    return validate_repository_path(match.group("path"), ssh=ssh)


def validate_network_identity(identity: Any, transport: Any = None) -> str | None:
    if not isinstance(identity, dict) or identity.get("kind") != "network-git":
        return None
    value = identity.get("value")
    if not isinstance(value, str):
        return None
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        return "network source identity must contain only valid Unicode scalar text"
    if len(value) > 4096 or "/" not in value:
        return "network source identity must be canonical host/path of at most 4096 Unicode scalar values"
    host, path = value.split("/", 1)
    if LOWERCASE_HOST.fullmatch(host) is None:
        return "network source identity host must use canonical lowercase ASCII spelling"
    path_error = validate_repository_path(path, ssh=transport == "ssh")
    if path_error is not None:
        return f"network source identity is not canonical: {path_error}"
    if path.endswith(".git"):
        return "network source identity must remove one trailing lowercase .git"
    return None


def validate_git_ref_name(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        encoded = value.encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        return "Git ref name must contain only valid Unicode scalar text"
    if not 1 <= len(encoded) <= 255:
        return "Git ref name must encode to 1 through 255 UTF-8 bytes"
    components = value.split("/")
    if (
        value.startswith("/")
        or value.endswith("/")
        or value.endswith(".")
        or any(component == "" or component.startswith(".") or component.endswith(".lock") for component in components)
        or ".." in value
        or "@{" in value
        or value == "@"
        or any(ord(character) <= 32 or ord(character) == 127 or character in "~^:?*[\\"
               for character in value)
    ):
        return "Git ref name is not a safe exact tag or branch name"
    return None


def validate_structured_ref(ref: Any, object_format: Any = None) -> str | None:
    if not isinstance(ref, dict):
        return None
    kind, value = ref.get("kind"), ref.get("value")
    if kind in {"tag", "branch"}:
        return validate_git_ref_name(value)
    if kind == "revision" and isinstance(value, str) and object_format in {"sha1", "sha256"}:
        expected = 40 if object_format == "sha1" else 64
        if len(value) != expected:
            return f"structured revision width must match effective {object_format} object format"
    return None


def validate_effective_source(
    declared: dict[str, Any], effective: dict[str, Any]
) -> str | None:
    substitution = effective.get("substitution", {})
    identity = effective.get("identity", {})
    declared_identity_error = validate_network_identity(
        declared.get("identity"), declared.get("transport")
    )
    if declared_identity_error is not None:
        return declared_identity_error
    effective_identity_error = validate_network_identity(
        identity, effective.get("transport")
    )
    if effective_identity_error is not None:
        return effective_identity_error
    tag_error = validate_git_ref_name(declared.get("tag"))
    if tag_error is not None:
        return tag_error
    object_format = effective.get("object_format")
    commit = effective.get("commit")
    if object_format in {"sha1", "sha256"} and isinstance(commit, str):
        expected = 40 if object_format == "sha1" else 64
        if len(commit) != expected:
            return f"effective commit width must match {object_format} object format"
    ref_error = validate_structured_ref(
        substitution.get("ref") if isinstance(substitution, dict) else None,
        object_format,
    )
    if ref_error is not None:
        return ref_error
    if effective.get("substituted") is False:
        locked = declared.get("locked_commit", {})
        if (
            effective.get("identity") != declared.get("identity")
            or effective.get("transport") != declared.get("transport")
            or not isinstance(locked, dict)
            or effective.get("object_format") != locked.get("object_format")
            or effective.get("commit") != locked.get("hex")
        ):
            return "unsubstituted effective source must equal declared source and lock"
    elif isinstance(substitution, dict) and isinstance(identity, dict):
        substitution_type = substitution.get("type")
        identity_kind = identity.get("kind")
        if substitution_type == "local-path" and identity_kind != "operator-local-git":
            return "local substitution requires operator-local-git effective identity"
        if substitution_type == "network-git" and identity_kind != "network-git":
            return "network substitution requires network-git effective identity"
    return None


def validate_toolchain_requirement(requirement: Any, driver: Any) -> str | None:
    return toolchain_gate.check_requirement(requirement, driver)


def validate_toolchain_document(schema_name: str, instance: Any) -> str | None:
    """Semantic rules of a manager-owned toolchain document.

    Coverage against the registry is a property of the pair, so it belongs to
    ``validate_toolchain_contract``; what a single document can be held to on
    its own is checked here, which is what makes a schema case meaningful.
    """
    try:
        if schema_name == "toolchain-registry-v1.schema.json":
            toolchain_gate.check_registry(instance, ValidationFailure)
        else:
            toolchain_gate.check_guidance_lifecycle(instance, ValidationFailure)
    except ValidationFailure as exc:
        return str(exc)
    return None


def validate_wire_semantics(schema_name: str, instance: Any) -> str | None:
    if not isinstance(instance, dict):
        return None
    pre_v8_manifest = re.fullmatch(r"(?:agent-skill|csk-skill)-v([1-7])\.schema\.json", schema_name)
    if pre_v8_manifest is not None:
        # The toolchain requirement lands in manifest schema 8. Schemas 6 and 7
        # keep their exact package surface and take the driver's registry
        # baseline, which is the rule they already state in prose.
        if "toolchain" in instance:
            return "toolchain is legal only in manifest schema 8"
        commands = instance.get("commands", {})
        if isinstance(commands, dict):
            for command in commands.values():
                if isinstance(command, dict) and "toolchain" in command:
                    return "command toolchain is legal only in manifest schema 8"
    legacy_manifest = re.fullmatch(r"(?:agent-skill|csk-skill)-v([1-6])\.schema\.json", schema_name)
    if legacy_manifest is not None:
        for field in ("build_repositories", "repository", "target"):
            if field in instance:
                return f"{field} is legal only in manifest schema 7"
        if instance.get("driver") == "go-repository-v1":
            return "go-repository-v1 is legal only in manifest schema 7"
        commands = instance.get("commands", {})
        if isinstance(commands, dict):
            for command in commands.values():
                if not isinstance(command, dict):
                    continue
                for field in ("repository", "target"):
                    if field in command:
                        return f"command {field} is legal only in manifest schema 7"
                if command.get("driver") == "go-repository-v1":
                    return "go-repository-v1 is legal only in manifest schema 7"
    if schema_name in {
        "agent-skill-v7.schema.json",
        "csk-skill-v7.schema.json",
        "agent-skill-v8.schema.json",
        "csk-skill-v8.schema.json",
    }:
        repositories = instance.get("build_repositories", {})
        commands = instance.get("commands", {})
        if not isinstance(repositories, dict) or not isinstance(commands, dict):
            return None
        for repository in repositories.values():
            if not isinstance(repository, dict):
                continue
            git_error = validate_repository_git(repository.get("git"))
            if git_error is not None:
                return git_error
            tag_error = validate_git_ref_name(repository.get("tag"))
            if tag_error is not None:
                return tag_error
        selected = {
            command.get("repository")
            for command in commands.values()
            if isinstance(command, dict) and command.get("driver") == "go-repository-v1"
        }
        if selected - set(repositories):
            return "repository command selects an undeclared build repository"
        if set(repositories) - selected:
            return "every build repository declaration must be selected by a command"
        if schema_name in {"agent-skill-v8.schema.json", "csk-skill-v8.schema.json"}:
            for command in commands.values():
                if not isinstance(command, dict) or command.get("type") != "build":
                    continue
                error = validate_toolchain_requirement(command.get("toolchain"), command.get("driver"))
                if error is not None:
                    return error
    elif schema_name == "skillfile-dev-v2.schema.json":
        substitutions = instance.get("build_repository_substitutions", {})
        if isinstance(substitutions, dict):
            for repositories in substitutions.values():
                if not isinstance(repositories, dict):
                    continue
                for substitution in repositories.values():
                    if not isinstance(substitution, dict) or "git" not in substitution:
                        continue
                    git_error = validate_repository_git(substitution.get("git"))
                    if git_error is not None:
                        return git_error
                    ref_error = validate_structured_ref(substitution.get("ref"))
                    if ref_error is not None:
                        return ref_error
    elif schema_name in {"skill-build-v1.schema.json", "skill-build-v2.schema.json"}:
        for target in instance.get("targets", {}).values():
            if isinstance(target, dict):
                root, source = target.get("build_root"), target.get("source_dir")
                if isinstance(root, str) and isinstance(source, str) and not is_below_or_equal(source, root):
                    return "source_dir must equal or be below build_root"
                error = validate_toolchain_requirement(target.get("toolchain"), target.get("driver"))
                if error is not None:
                    return error
    elif schema_name in {"toolchain-registry-v1.schema.json", "toolchain-guidance-catalog-v1.schema.json"}:
        return validate_toolchain_document(schema_name, instance)
    elif schema_name == "build-receipt-v1.schema.json":
        build_input = instance.get("input", {})
        if isinstance(build_input, dict):
            if "cache_key" in instance and instance.get("cache_key") != ccj1_sha256(build_input):
                return "receipt cache_key must equal SHA-256(CCJ-1(input))"
            policy = build_input.get("policy", {})
            if (
                isinstance(policy, dict)
                and policy.get("execution_policy") != PORTABLE_EXECUTION_POLICY
            ):
                return (
                    "go-v1 policy must declare the portable "
                    f"{PORTABLE_EXECUTION_POLICY} execution policy"
                )
    elif schema_name == "build-receipt-v2.schema.json":
        build_input = instance.get("input", {})
        if isinstance(build_input, dict):
            if "cache_key" in instance and instance.get("cache_key") != ccj1_sha256(build_input):
                return "receipt cache_key must equal SHA-256(CCJ-1(input))"
            root, source_dir = build_input.get("build_root"), build_input.get("source_dir")
            if isinstance(root, str) and isinstance(source_dir, str) and not is_below_or_equal(source_dir, root):
                return "receipt source_dir must equal or be below build_root"
            source = build_input.get("source", {})
            if isinstance(source, dict):
                declared, effective = source.get("declared", {}), source.get("effective", {})
                if isinstance(declared, dict) and isinstance(effective, dict):
                    error = validate_effective_source(declared, effective)
                    if error is not None:
                        return error
    elif schema_name == "install-marker-v3.schema.json":
        builds = instance.get("builds", {})
        if not isinstance(builds, dict):
            return None
        has_local = any(isinstance(record, dict) and record.get("driver") == "go-v1" for record in builds.values())
        if has_local != ("build_source" in instance):
            return "marker build_source is present exactly when a local go-v1 build is active"
        for record in builds.values():
            if not isinstance(record, dict) or record.get("driver") != "go-repository-v1":
                continue
            declared = {
                "identity": record.get("declared_identity"),
                "locked_commit": record.get("declared_locked_commit"),
            }
            if "declared_tag" in record:
                declared["tag"] = record["declared_tag"]
            effective = {
                "identity": record.get("effective_identity"),
                "object_format": record.get("object_format"),
                "commit": record.get("commit"),
                "substituted": record.get("substituted"),
            }
            if "substitution" in record:
                effective["substitution"] = record["substitution"]
            error = validate_effective_source(declared, effective)
            if error is not None:
                return error
    elif schema_name == "conformance-claim-v3.schema.json":
        systems = set(instance.get("operating_systems", []))
        if "linux" in systems:
            return "Linux claim-v3 qualification is excluded until TASK-260728-1skseh passes"
        claims = instance.get("build_drivers", [])
        if isinstance(claims, list):
            drivers = [claim.get("driver") for claim in claims if isinstance(claim, dict)]
            if len(drivers) != len(set(drivers)):
                return "build driver assertions must be unique"
            for claim in claims:
                if isinstance(claim, dict) and not set(claim.get("operating_systems", [])).issubset(systems):
                    return "build driver platforms must be a subset of the top-level evidenced platforms"
    return None


def validate_manifest() -> None:
    manifest_path = SUITE / "manifest.json"
    manifest = load_json(manifest_path)
    if manifest.get("protocol_version") != "1.0.0-rc.5":
        raise ValidationFailure("vector manifest protocol_version is not 1.0.0-rc.5")
    entries = manifest.get("files")
    if not isinstance(entries, list):
        raise ValidationFailure("vector manifest files must be a list")
    listed = [entry["path"] for entry in entries]
    if listed != sorted(listed) or len(listed) != len(set(listed)):
        raise ValidationFailure("vector manifest paths must be sorted and unique")

    actual = sorted(
        path.relative_to(SUITE).as_posix()
        for path in SUITE.rglob("*")
        if path.is_file() and path != manifest_path
    )
    if listed != actual:
        missing = sorted(set(actual) - set(listed))
        extra = sorted(set(listed) - set(actual))
        raise ValidationFailure(f"vector manifest inventory mismatch; missing={missing}, extra={extra}")
    for entry in entries:
        vector_path = SUITE / entry["path"]
        payload = vector_path.read_bytes()
        digest = "sha256:" + hashlib.sha256(payload).hexdigest()
        if digest != entry["sha256"]:
            raise ValidationFailure(f"vector digest mismatch for {entry['path']}")
        if vector_path.suffix == ".json":
            load_json(vector_path)

    release = load_json(ROOT / "release" / "1.0.0-rc.5.json")
    manifest_digest = "sha256:" + hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    if release.get("protocol_version") != "1.0.0-rc.5":
        raise ValidationFailure("rc.5 release metadata identifies the wrong protocol version")
    pin = release.get("candidate_protocol_pin", {})
    if not isinstance(pin, dict) or pin.get("manifest_sha256") != manifest_digest:
        raise ValidationFailure("rc.5 downstream candidate pin does not match the suite manifest")
    downstream = release.get("downstream_consumption", {})
    if (
        not isinstance(downstream, dict)
        or downstream.get("required_manifest_sha256") != manifest_digest
        or downstream.get("committed_release_pin_advanced") is not False
    ):
        raise ValidationFailure("rc.5 downstream consumption metadata is incomplete")
    claim = release.get("claim_v3", {})
    if (
        not isinstance(claim, dict)
        or claim.get("claims_emitted") != []
        or claim.get("linux_excluded_until_task") != "TASK-260728-1skseh"
    ):
        raise ValidationFailure("rc.5 release metadata fabricates or weakens platform qualification")
    execution = release.get("execution_policy", {})
    if (
        not isinstance(execution, dict)
        or execution.get("portable") != PORTABLE_EXECUTION_POLICY
        or execution.get("hardened_profile_claimed") is not False
        or execution.get("hardened_profile_owner") != HARDENED_EXECUTION_OWNER
        or execution.get("legacy_rc4_go_v1_cache_key") != LEGACY_RC4_GO_V1_CACHE_KEY
        or execution.get("native_control_inventory_version")
        != NATIVE_CONTROL_INVENTORY_VERSION
        or execution.get("capability_evidence_record_version")
        != CAPABILITY_EVIDENCE_RECORD_VERSION
    ):
        raise ValidationFailure(
            "rc.5 release metadata does not honestly record the portable execution policy"
        )


def validate_candidate_manifest() -> None:
    """The unreleased candidate suite root indexes itself and claims nothing.

    It is held to the same inventory and digest discipline as the released
    suite, because a candidate corpus nobody verifies is not evidence. What it
    must not do is carry a protocol version: naming one is minting one, and the
    surface it belongs to is reserved to ``CANDIDATE_RELEASE_PIN_OWNER``.
    """
    manifest_path = CANDIDATE_SUITE / "manifest.json"
    manifest = load_json(manifest_path)
    if "protocol_version" in manifest:
        raise ValidationFailure(
            "the candidate suite manifest names a protocol version; the surface it "
            f"belongs to is unminted and reserved to {CANDIDATE_RELEASE_PIN_OWNER}"
        )
    if manifest.get("released") is not False:
        raise ValidationFailure("the candidate suite manifest does not record itself as unreleased")
    if manifest.get("candidate_against") != "1.0.0-rc.5":
        raise ValidationFailure("the candidate suite manifest names the wrong released predecessor")
    if manifest.get("release_pin_owner") != CANDIDATE_RELEASE_PIN_OWNER:
        raise ValidationFailure(
            f"the candidate suite manifest does not name {CANDIDATE_RELEASE_PIN_OWNER} as the pin owner"
        )
    entries = manifest.get("files")
    if not isinstance(entries, list) or not entries:
        raise ValidationFailure("the candidate suite manifest lists no file")
    listed = [entry["path"] for entry in entries]
    if listed != sorted(listed) or len(listed) != len(set(listed)):
        raise ValidationFailure("candidate manifest paths must be sorted and unique")
    actual = sorted(
        path.relative_to(CANDIDATE_SUITE).as_posix()
        for path in CANDIDATE_SUITE.rglob("*")
        if path.is_file() and path != manifest_path
    )
    if listed != actual:
        missing = sorted(set(actual) - set(listed))
        extra = sorted(set(listed) - set(actual))
        raise ValidationFailure(
            f"candidate manifest inventory mismatch; missing={missing}, extra={extra}"
        )
    for entry in entries:
        vector_path = CANDIDATE_SUITE / entry["path"]
        digest = "sha256:" + hashlib.sha256(vector_path.read_bytes()).hexdigest()
        if digest != entry["sha256"]:
            raise ValidationFailure(f"candidate vector digest mismatch for {entry['path']}")
        if vector_path.suffix == ".json":
            load_json(vector_path)

    # No candidate file may sit inside the pinned suite. Stated over the pinned
    # manifest rather than over the filesystem, so it is checked against the
    # same inventory the release document pins.
    candidate_prefixes = {
        f"schema-cases/{name[: -len('.schema.json')]}/" for name in CANDIDATE_CASE_SCHEMAS
    }
    intruders = sorted(
        entry["path"]
        for entry in load_json(SUITE / "manifest.json")["files"]
        if entry["path"].startswith(tuple(candidate_prefixes))
        or entry["path"].rpartition("/")[2] in toolchain_gate.TOOLCHAIN_VECTOR_FILES
    )
    if intruders:
        raise ValidationFailure(
            f"candidate corpus files are inside the pinned rc.5 suite: {intruders}"
        )


FROZEN_RELEASE_SUBJECTS = (
    ("release_document", "release_document_sha256"),
    ("suite_manifest", "suite_manifest_sha256"),
    ("schema_cases_index", "schema_cases_index_sha256"),
)


def check_frozen_release_identity(root: Path, fail: type[Exception]) -> list[str]:
    """Hold every released artifact to its authored, accepted byte identity.

    ``release/frozen.json`` is authored and never generated, which is the whole
    point: a regeneration that rewrites a released suite manifest also rewrites
    the release document that pins it, so the result is internally consistent
    and says nothing. Comparing against a record that regeneration cannot move
    is what makes a silent rewrite of a frozen release fail. Returns the
    protocol versions it verified.
    """
    frozen = load_json(root / "release" / "frozen.json")
    records = frozen.get("releases")
    if not isinstance(records, list) or not records:
        raise fail("release/frozen.json records no frozen release")
    verified: list[str] = []
    for record in records:
        version = record["protocol_version"]
        for subject, expected_key in FROZEN_RELEASE_SUBJECTS:
            relative = record[subject]
            path = root / relative
            if not path.is_file():
                raise fail(f"frozen release {version} names a missing artifact {relative}")
            actual = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != record[expected_key]:
                raise fail(
                    f"frozen release {version} was rewritten: {relative} is {actual}, "
                    f"release/frozen.json requires {record[expected_key]}"
                )
        # The release document's own pins must agree with the frozen manifest
        # digest. Without this a future document could keep its accepted bytes
        # while pointing at a different suite.
        document = load_json(root / record["release_document"])
        if document.get("protocol_version") != version:
            raise fail(f"{record['release_document']} identifies the wrong protocol version")
        pin = document.get("candidate_protocol_pin", {})
        downstream = document.get("downstream_consumption", {})
        if (
            not isinstance(pin, dict)
            or pin.get("suite_root") != record["suite_root"]
            or pin.get("manifest_sha256") != record["suite_manifest_sha256"]
            or not isinstance(downstream, dict)
            or downstream.get("required_manifest_sha256") != record["suite_manifest_sha256"]
        ):
            raise fail(
                f"{record['release_document']} does not pin the frozen {record['suite_manifest']}"
            )
        verified.append(version)
    return verified


def validate_frozen_releases() -> None:
    verified = check_frozen_release_identity(ROOT, ValidationFailure)
    if "1.0.0-rc.5" not in verified:
        raise ValidationFailure("release/frozen.json does not record the 1.0.0-rc.5 release")


def validate_review_evidence() -> None:
    cases = {
        "review-report.schema.json": (("v1-valid.json", True), ("v1-invalid.json", False)),
        "review-report-v2.schema.json": (("valid.json", True), ("invalid.json", False)),
    }
    for schema_name, schema_cases in cases.items():
        schema_path = REVIEWS / schema_name
        schema = load_json(schema_path)
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as exc:
            raise ValidationFailure(
                f"{schema_path}: invalid Draft 2020-12 schema: {exc.message}"
            ) from exc
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        for name, expected in schema_cases:
            path = REVIEWS / "examples" / name
            errors = list(validator.iter_errors(load_json(path)))
            if (not errors) != expected:
                detail = "valid" if not errors else errors[0].message
                raise ValidationFailure(
                    f"review example {name}: expected valid={expected}, got {detail}"
                )
    validator = Draft202012Validator(
        load_json(REVIEWS / "review-report-v2.schema.json"),
        format_checker=FormatChecker(),
    )
    for directory in sorted(REVIEWS.iterdir()):
        if not directory.is_dir() or directory.name == "examples":
            continue
        if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", directory.name) is None:
            raise ValidationFailure(f"unexpected review evidence directory {directory.name}")
        for path in sorted(directory.glob("*.json")):
            errors = list(validator.iter_errors(load_json(path)))
            if errors:
                raise ValidationFailure(f"{path}: {errors[0].message}")


def require_sorted_unique(values: Any, label: str) -> None:
    if not isinstance(values, list) or values != sorted(values) or len(values) != len(set(values)):
        raise ValidationFailure(f"{label} must be a sorted unique array")


def require_named_cases(values: Any, label: str, required: set[str]) -> None:
    if not isinstance(values, list):
        raise ValidationFailure(f"{label} must be an array")
    names = [item.get("name") for item in values if isinstance(item, dict)]
    if len(names) != len(values) or any(not isinstance(name, str) or not name for name in names):
        raise ValidationFailure(f"{label} cases require non-empty names")
    if len(names) != len(set(names)):
        raise ValidationFailure(f"{label} case names must be unique")
    missing = sorted(required - set(names))
    if missing:
        raise ValidationFailure(f"{label} is missing cases: {', '.join(missing)}")


def named_cases(values: Any, label: str) -> dict[str, dict[str, Any]]:
    require_named_cases(values, label, set())
    return {item["name"]: item for item in values}


def decode_base64(value: Any, label: str) -> bytes:
    if not isinstance(value, str):
        raise ValidationFailure(f"{label} must be base64 text")
    try:
        return base64.b64decode(value, validate=True)
    except ValueError as exc:
        raise ValidationFailure(f"{label} is not canonical base64") from exc


def git_object_id(object_format: str, object_type: str, content: bytes) -> str:
    payload = f"{object_type} {len(content)}\0".encode("ascii") + content
    return hashlib.new(object_format, payload).hexdigest()


def decode_hex(value: Any, label: str) -> bytes:
    if not isinstance(value, str):
        raise ValidationFailure(f"{label} must be hexadecimal text")
    try:
        return bytes.fromhex(value)
    except ValueError as exc:
        raise ValidationFailure(f"{label} has malformed hexadecimal bytes") from exc


def object_digest(object_format: str, payload: bytes) -> bytes:
    if object_format not in {"sha1", "sha256"}:
        raise ValidationFailure(f"unsupported Git object format {object_format!r}")
    return hashlib.new(object_format, payload).digest()


def validate_empty_pack_index(
    case: dict[str, Any],
    object_format: str,
    *,
    expect_index_checksum: bool,
) -> tuple[bytes, bytes]:
    label = f"pack/index fixture {case.get('name', '<unnamed>')}"
    width = {"sha1": 20, "sha256": 32}.get(object_format)
    if width is None:
        raise ValidationFailure(f"{label} has unsupported object format")
    pack = decode_hex(case.get("pack_hex"), f"{label} pack")
    index = decode_hex(case.get("index_hex"), f"{label} index")
    if len(pack) != 12 + width:
        raise ValidationFailure(f"{label} pack length does not match {object_format}")
    if pack[:4] != b"PACK":
        raise ValidationFailure(f"{label} has the wrong pack magic")
    pack_version = int.from_bytes(pack[4:8], "big")
    if pack_version != case.get("pack_version"):
        raise ValidationFailure(f"{label} pack version metadata is false")
    if int.from_bytes(pack[8:12], "big") != 0:
        raise ValidationFailure(f"{label} is not an empty pack")
    pack_checksum = pack[-width:]
    if pack_checksum != object_digest(object_format, pack[:-width]):
        raise ValidationFailure(f"{label} pack checksum is invalid")
    if case.get("pack_name") != f"pack-{pack_checksum.hex()}.pack":
        raise ValidationFailure(f"{label} pack filename does not match its checksum")

    expected_index_size = 8 + 256 * 4 + width * 2
    if len(index) != expected_index_size:
        raise ValidationFailure(f"{label} index length does not match {object_format}")
    if index[:4] != b"\xfftOc":
        raise ValidationFailure(f"{label} has the wrong index magic")
    index_version = int.from_bytes(index[4:8], "big")
    if index_version != case.get("index_version"):
        raise ValidationFailure(f"{label} index version metadata is false")
    fanout = [
        int.from_bytes(index[offset : offset + 4], "big")
        for offset in range(8, 8 + 256 * 4, 4)
    ]
    if fanout != sorted(fanout) or fanout[-1] != 0:
        raise ValidationFailure(f"{label} index fanout is invalid for an empty pack")
    embedded_pack_checksum = index[8 + 256 * 4 : 8 + 256 * 4 + width]
    if embedded_pack_checksum != pack_checksum:
        raise ValidationFailure(f"{label} index embeds the wrong pack checksum")
    actual_index_checksum = index[-width:]
    expected_index_checksum = object_digest(object_format, index[:-width])
    if (actual_index_checksum == expected_index_checksum) != expect_index_checksum:
        state = "valid" if expect_index_checksum else "invalid"
        raise ValidationFailure(f"{label} index checksum is not {state} as declared")
    return pack, index


def materialize_pack_mutation(
    base: dict[str, Any],
    mutation: dict[str, Any],
) -> tuple[bytes, bytes]:
    pack = bytearray(decode_hex(base.get("pack_hex"), "base pack"))
    index = bytearray(decode_hex(base.get("index_hex"), "base index"))
    target = mutation.get("target")
    operation = mutation.get("operation")
    if target == "index" and operation == "xor-byte":
        offset = mutation.get("offset_from_end")
        xor = mutation.get("xor")
        if not isinstance(offset, int) or offset < 1 or offset > len(index):
            raise ValidationFailure("pack mutation has invalid offset_from_end")
        if not isinstance(xor, int) or xor < 1 or xor > 255:
            raise ValidationFailure("pack mutation has invalid xor byte")
        index[-offset] ^= xor
    elif target == "repository_object_format" and operation == "replace":
        if mutation.get("from") != "sha1" or mutation.get("to") != "sha256":
            raise ValidationFailure("hash-family mutation is not the exact sha1-to-sha256 replacement")
    else:
        raise ValidationFailure("pack mutation is not executable by the shared harness")
    return bytes(pack), bytes(index)


def validate_external_receipt_oracles(
    receipt: dict[str, Any],
    marker: dict[str, Any],
    plan: dict[str, Any],
) -> None:
    expected_cache_key = ccj1_sha256(receipt.get("input"))
    expected_receipt_hash = ccj1_sha256(receipt)
    external_record = marker.get("builds", {}).get("golden-tool", {})
    plan_commands = {
        command.get("name"): command
        for command in plan.get("commands", [])
        if isinstance(command, dict)
    }
    plan_external = plan_commands.get("golden-tool", {})
    if receipt.get("cache_key") != expected_cache_key:
        raise ValidationFailure("exact build receipt cache_key is not SHA-256(CCJ-1(input))")
    if (
        external_record.get("cache_key") != expected_cache_key
        or external_record.get("receipt_sha256") != expected_receipt_hash
        or plan_external.get("cache_key") != expected_cache_key
        or plan_external.get("receipt_sha256") != expected_receipt_hash
    ):
        raise ValidationFailure("mixed marker/plan does not carry the exact generated receipt hashes")


MANDATORY_PORTABLE_CONTROLS = {
    "fixed-offline-vendored-go",
    "fixed-argument-vectors",
    "fixed-empty-environment",
    "fixed-manager-selected-process-graph",
    "identity-verified-manager-owned-worker",
    "pre-launch-worker-identity-verification",
    "post-exec-identity-reverification",
    "frozen-source-snapshot-integrity",
    "manager-private-staging-roots",
    "manager-derived-output-path",
    "bounded-wall-clock-deadline",
    "bounded-combined-output",
    "bounded-artifact-size",
    "closed-standard-input-and-descriptors",
    "worker-domain-teardown",
    "no-artifact-execution",
    "inventory-native-controls-applied",
    "closed-capability-evidence-record",
}

# The exhaustive rc.5 native-control inventory. Every conforming manager reports
# exactly these controls, and the availability recorded here is normative per
# platform.
NATIVE_CONTROL_INVENTORY = {
    "descendant-domain-termination": {
        "macos": "process-group-and-session-teardown",
        "windows": "job-object-kill-on-close",
    },
    "active-process-count-limit": {
        "macos": None,
        "windows": "job-object-active-process-limit",
    },
    "aggregate-memory-limit": {
        "macos": None,
        "windows": "job-object-process-and-job-memory-limit",
    },
    "per-file-size-limit": {
        "macos": "rlimit-fsize",
        "windows": None,
    },
    "inherited-handle-restriction": {
        "macos": "close-on-exec-and-explicit-descriptor-release",
        "windows": "explicit-handle-inheritance-list",
    },
}

CAPABILITY_EVIDENCE_RECORD_FIELDS = {
    "controls",
    "execution_policy",
    "platform",
    "record_version",
}

CAPABILITY_EVIDENCE_ENTRY_FIELDS = {"availability", "name", "probed_at", "status"}

CAPABILITY_EVIDENCE_CASES = {
    "available-native-control-is-applied",
    "unavailable-native-control-does-not-reject",
    "capability-evidence-is-not-cache-input",
    "unavailable-control-cannot-be-reported-as-applied",
    "available-control-cannot-be-reported-as-unavailable",
    "unknown-native-control-is-rejected",
    "missing-native-control-entry-is-rejected",
    "duplicate-native-control-entry-is-rejected",
    "unknown-evidence-record-version-is-rejected",
    "hardened-guarantee-claimed-under-portable-policy",
    "hardened-execution-policy-in-evidence-record",
}

DEFERRED_HARDENED_GUARANTEES = {
    "total-network-denial",
    "read-only-source-and-toolchain",
    "private-build-root-only-writes",
    "hard-aggregate-descendant-resource-bounds",
    "exact-executable-allowlisting",
    "fail-closed-capability-preflight",
}

PACKAGE_INFLUENCE_SURFACES = {
    "package-selected-executable",
    "package-selected-argv",
    "package-selected-environment",
    "package-selected-output-path",
    "package-selected-flags",
    "package-selected-hooks",
    "package-selected-plugins",
    "package-selected-generators",
}

WORKER_SESSION_ORDER = (
    (
        "parent-native-control-availability-probe",
        "parent-worker-identity-verification",
    ),
    ("parent-worker-identity-verification", "worker-launch"),
    (
        "worker-identity-proof-and-nonce-acknowledgement",
        "worker-control-application-and-evidence",
    ),
    ("worker-control-application-and-evidence", "worker-fixed-go-list"),
    ("worker-fixed-go-list", "parent-complete-package-graph-validation"),
    ("parent-complete-package-graph-validation", "parent-authenticated-build-permit"),
    ("parent-authenticated-build-permit", "worker-fixed-go-build"),
    ("worker-fixed-go-build", "parent-artifact-verification"),
    ("parent-artifact-verification", "parent-post-exec-identity-reverification"),
    ("parent-post-exec-identity-reverification", "worker-domain-teardown"),
)

IDENTITY_CASES_BEFORE_WORKER = {
    "pre-launch-identity-mismatch",
    "worker-executable-symlink-substitution",
    "mandatory-control-cannot-be-applied",
}

# Portable mechanisms and the hardened guarantee each one deliberately stops
# short of. Every deferred guarantee must be answered by exactly one mechanism.
POLICY_SEMANTIC_KEYS = {
    "network",
    "source_integrity",
    "executable_graph",
    "private_write_confinement",
    "resource_bounds",
    "capability_preflight",
}

IDENTITY_CASES_BEFORE_COMPILER = {
    "build-permit-before-complete-list-validation",
    "replayed-session-nonce",
    "out-of-order-protocol-message",
    "oversize-protocol-message",
    "unknown-protocol-message-kind",
}


def validate_go_host_execution_policy(vector: Any = None) -> None:
    """Check the executable portable `manager-worker-v1` execution contract."""
    if vector is None:
        vector = load_json(SUITE / "vectors" / "go-host-execution-policy.json")
    if (
        vector.get("execution_policy") != PORTABLE_EXECUTION_POLICY
        or vector.get("reserved_hardened_execution_policy")
        != RESERVED_HARDENED_EXECUTION_POLICY
        or vector.get("hardened_profile_owner") != HARDENED_EXECUTION_OWNER
    ):
        raise ValidationFailure(
            "execution-policy vector does not separate portable from hardened execution"
        )
    if vector.get("drivers") != ["go-repository-v1", "go-v1"]:
        raise ValidationFailure("execution policy does not cover both closed build drivers")
    if vector.get("process_graph") != [
        "manager-parent",
        "identity-verified-manager-owned-worker",
        "fingerprinted-goroot-bin-go",
        "fingerprinted-goroot-pkg-tool-child",
    ]:
        raise ValidationFailure("execution policy does not fix the four-node process graph")

    states = vector.get("session_states")
    if not isinstance(states, list) or len(states) != len(set(states)):
        raise ValidationFailure("worker session states must be a unique ordered list")
    positions = {name: index for index, name in enumerate(states)}
    for earlier, later in WORKER_SESSION_ORDER:
        if positions.get(earlier, len(states)) >= positions.get(later, -1):
            raise ValidationFailure(f"worker session does not order {earlier} before {later}")

    controls = named_cases(vector.get("mandatory_controls"), "mandatory portable controls")
    if set(controls) != MANDATORY_PORTABLE_CONTROLS:
        raise ValidationFailure("mandatory portable control inventory is not exact")
    for name, control in controls.items():
        if (
            control.get("portable") is not True
            or control.get("enforced") != "always"
            or control.get("hardened_guarantee") is not False
        ):
            raise ValidationFailure(f"{name} is not an always-enforced portable control")

    inventory = vector.get("native_control_inventory")
    if not isinstance(inventory, dict):
        raise ValidationFailure("execution policy has no native-control inventory")
    if (
        inventory.get("version") != NATIVE_CONTROL_INVENTORY_VERSION
        or inventory.get("exhaustive") is not True
        or inventory.get("platforms") != ["macos", "windows"]
        or inventory.get("availability_states") != ["available", "unavailable"]
        or inventory.get("unavailable_reasons") != [UNAVAILABLE_NATIVE_CONTROL_REASON]
        or inventory.get("probe_timing") != "pre-worker-launch"
        or inventory.get("probe_scope") != "per-operation"
    ):
        raise ValidationFailure(
            "native-control inventory is not the exhaustive versioned per-platform authority"
        )
    native = named_cases(inventory.get("controls"), "native control inventory")
    if set(native) != set(NATIVE_CONTROL_INVENTORY):
        raise ValidationFailure("native-control inventory is not exact")
    for name, control in native.items():
        if (
            control.get("applied_when_available") is not True
            or control.get("hardened_guarantee") is not False
        ):
            raise ValidationFailure(f"{name} is not an available-only portable control")
        platforms = control.get("platforms")
        if not isinstance(platforms, dict) or set(platforms) != {"macos", "windows"}:
            raise ValidationFailure(f"{name} lacks exact macOS and Windows availability")
        for system, mechanism in NATIVE_CONTROL_INVENTORY[name].items():
            state = platforms[system]
            if not isinstance(state, dict) or set(state) != {
                "availability",
                "mechanism",
                "unavailable_reason",
            }:
                raise ValidationFailure(f"{name} has no closed {system} availability record")
            if mechanism is None:
                expected = {
                    "availability": "unavailable",
                    "mechanism": None,
                    "unavailable_reason": UNAVAILABLE_NATIVE_CONTROL_REASON,
                }
            else:
                expected = {
                    "availability": "available",
                    "mechanism": mechanism,
                    "unavailable_reason": None,
                }
            if state != expected:
                raise ValidationFailure(
                    f"{name} does not record the normative {system} availability"
                )

    deferred = named_cases(
        vector.get("deferred_hardened_guarantees"), "deferred hardened guarantees"
    )
    if set(deferred) != DEFERRED_HARDENED_GUARANTEES:
        raise ValidationFailure("deferred hardened guarantee inventory is not exact")
    for name, guarantee in deferred.items():
        if (
            guarantee.get("deferred_to") != HARDENED_EXECUTION_OWNER
            or guarantee.get("portable_profile_claims") is not False
            or guarantee.get("rejects_portable_build") is not False
        ):
            raise ValidationFailure(f"{name} is not honestly deferred to the hardened story")

    influence = named_cases(vector.get("package_influence_cases"), "package influence")
    if set(influence) != PACKAGE_INFLUENCE_SURFACES:
        raise ValidationFailure("package-influence surface inventory is not exact")
    for name, case in influence.items():
        if case.get("manifest_field") is not None or case.get("descriptor_field") is not None:
            raise ValidationFailure(f"{name} is expressible in a closed package surface")
        if (
            case.get("expected_error") != "build_execution_package_influence_forbidden"
            or case.get("worker_started") is not False
            or case.get("compiler_started") is not False
            or case.get("published") is not False
        ):
            raise ValidationFailure(f"{name} does not fail before the worker and the compiler")

    identity = named_cases(
        vector.get("identity_and_protocol_cases"), "worker identity and protocol"
    )
    required_identity = IDENTITY_CASES_BEFORE_WORKER | IDENTITY_CASES_BEFORE_COMPILER | {
        "worker-executable-replaced-between-checks",
        "worker-identity-proof-mismatch",
        "post-build-toolchain-identity-mismatch",
        "post-build-source-snapshot-mutated",
        "unexpected-program-started-below-the-worker",
        "second-build-request-in-one-session",
    }
    missing = sorted(required_identity - set(identity))
    if missing:
        raise ValidationFailure(
            f"worker identity/protocol cases are missing: {', '.join(missing)}"
        )
    for name, case in identity.items():
        code = case.get("expected_error")
        if not isinstance(code, str) or not code.startswith("build_execution_"):
            raise ValidationFailure(f"{name} does not use a stable execution diagnostic")
        if case.get("published") is not False:
            raise ValidationFailure(f"{name} publishes despite a rejected execution boundary")
    for name in IDENTITY_CASES_BEFORE_WORKER:
        if identity[name].get("worker_started") is not False:
            raise ValidationFailure(f"{name} must fail before the worker starts")
    for name in IDENTITY_CASES_BEFORE_COMPILER:
        if identity[name].get("compiler_started") is not False:
            raise ValidationFailure(f"{name} must fail before the compiler starts")

    validate_capability_evidence_record(vector, native, deferred)
    validate_capability_evidence_cases(vector, native, deferred)
    validate_execution_failure_boundary(vector, native, deferred)

    identities = vector.get("cache_identity")
    if not isinstance(identities, dict) or identities.get("aliases") is not False:
        raise ValidationFailure("cache-identity vector does not assert non-aliasing")
    keys: dict[str, str] = {}
    for name in ("portable", "reserved_hardened", "legacy_rc4_without_execution_policy"):
        entry = identities.get(name)
        if not isinstance(entry, dict) or not isinstance(entry.get("input"), dict):
            raise ValidationFailure(f"cache identity {name} is missing its exact input")
        expected = ccj1_sha256(entry["input"])
        if entry.get("cache_key") != expected:
            raise ValidationFailure(f"cache identity {name} key is not SHA-256(CCJ-1(input))")
        if expected in keys.values():
            raise ValidationFailure(f"cache identity {name} aliases another execution policy")
        keys[name] = expected
    if keys["legacy_rc4_without_execution_policy"] != LEGACY_RC4_GO_V1_CACHE_KEY:
        raise ValidationFailure(
            "the pre-revision go-v1 input no longer reproduces the recorded rc.4 cache key"
        )
    if (
        identities["portable"].get("schema_valid") is not True
        or identities["reserved_hardened"].get("schema_valid") is not False
        or identities["legacy_rc4_without_execution_policy"].get("schema_valid") is not False
    ):
        raise ValidationFailure("only the portable execution policy may be schema valid")


def validate_capability_evidence_record(
    vector: Any, native: dict[str, Any], deferred: dict[str, Any]
) -> None:
    """Check the closed per-operation capability-evidence record."""
    record = vector.get("capability_evidence_record")
    if not isinstance(record, dict):
        raise ValidationFailure("execution policy has no closed capability-evidence record")
    if (
        record.get("record_version") != CAPABILITY_EVIDENCE_RECORD_VERSION
        or record.get("inventory_version") != NATIVE_CONTROL_INVENTORY_VERSION
        or set(record.get("record_fields") or []) != CAPABILITY_EVIDENCE_RECORD_FIELDS
        or set(record.get("control_entry_fields") or []) != CAPABILITY_EVIDENCE_ENTRY_FIELDS
        or record.get("availability_states") != ["available", "unavailable"]
        or record.get("status_states") != ["applied", "unavailable"]
        or record.get("probe_timings") != ["pre-worker-launch"]
        or record.get("entry_cardinality") != "exactly-one-per-inventory-control"
    ):
        raise ValidationFailure("capability-evidence record vocabulary is not closed")
    if record.get("result_only") is not True or record.get("exposed_in") != [
        "dry-run-plan-result",
        "install-result",
        "status-result",
    ]:
        raise ValidationFailure("capability evidence is not exposed as result-only reporting")
    if record.get("excluded_from") != [
        "cache-key",
        "conformance-claim",
        "install-marker",
        "receipt",
    ]:
        raise ValidationFailure(
            "capability evidence is not excluded from every hashed or published identity"
        )

    rules = {item.get("rule"): item for item in record.get("consistency_rules") or []}
    required_rules = {
        "available-control-must-report-status-applied": (
            "build_execution_capability_evidence_invalid"
        ),
        "unavailable-control-must-report-status-unavailable": (
            "build_execution_capability_evidence_invalid"
        ),
        "exactly-one-entry-per-inventory-control": (
            "build_execution_capability_evidence_invalid"
        ),
        "no-entry-outside-the-inventory": "build_execution_capability_evidence_invalid",
        "unknown-record-version-is-rejected": (
            "build_execution_capability_evidence_invalid"
        ),
        "availability-probed-per-operation-before-worker-launch": (
            "build_execution_capability_evidence_invalid"
        ),
        "no-deferred-hardened-guarantee-entry": (
            "build_execution_hardened_claim_forbidden"
        ),
        "record-execution-policy-must-be-the-portable-identity": (
            "build_execution_hardened_claim_forbidden"
        ),
    }
    if set(rules) != set(required_rules):
        raise ValidationFailure("capability-evidence consistency rules are not exact")
    for rule, expected_error in required_rules.items():
        if rules[rule].get("expected_error") != expected_error:
            raise ValidationFailure(f"capability-evidence rule {rule} has no stable diagnostic")

    examples = record.get("examples")
    if not isinstance(examples, dict) or set(examples) != {"macos", "windows"}:
        raise ValidationFailure("capability-evidence record lacks per-platform examples")
    for platform, example in examples.items():
        if set(example) != CAPABILITY_EVIDENCE_RECORD_FIELDS:
            raise ValidationFailure(f"{platform} evidence example is not the closed record")
        if (
            example.get("record_version") != CAPABILITY_EVIDENCE_RECORD_VERSION
            or example.get("execution_policy") != PORTABLE_EXECUTION_POLICY
            or example.get("platform") != platform
        ):
            raise ValidationFailure(f"{platform} evidence example is not portable-policy state")
        entries = example.get("controls")
        if not isinstance(entries, list) or len(entries) != len(native):
            raise ValidationFailure(
                f"{platform} evidence example does not report every inventory control once"
            )
        seen: set[str] = set()
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) != CAPABILITY_EVIDENCE_ENTRY_FIELDS:
                raise ValidationFailure(f"{platform} evidence entry is not the closed shape")
            name = entry.get("name")
            if name not in native or name in seen:
                raise ValidationFailure(
                    f"{platform} evidence entry {name} is unknown or duplicated"
                )
            if name in deferred:
                raise ValidationFailure(
                    f"{platform} evidence example reports the deferred guarantee {name}"
                )
            seen.add(name)
            if entry.get("probed_at") != "pre-worker-launch":
                raise ValidationFailure(f"{platform} evidence entry {name} is probed too late")
            availability = native[name]["platforms"][platform]["availability"]
            expected_status = "applied" if availability == "available" else "unavailable"
            if (
                entry.get("availability") != availability
                or entry.get("status") != expected_status
            ):
                raise ValidationFailure(
                    f"{platform} evidence entry {name} contradicts the inventory"
                )


def validate_capability_evidence_cases(
    vector: Any, native: dict[str, Any], deferred: dict[str, Any]
) -> None:
    """Check the executable capability-evidence oracles and negative guards."""
    evidence = named_cases(vector.get("capability_evidence_cases"), "capability evidence")
    if set(evidence) != CAPABILITY_EVIDENCE_CASES:
        raise ValidationFailure("capability-evidence case inventory is not exact")
    for name, case in evidence.items():
        if case.get("changes_cache_key") is not False:
            raise ValidationFailure(f"{name} leaks host capability evidence into cache identity")
        valid = case.get("record_valid")
        if valid not in (True, False):
            raise ValidationFailure(f"{name} does not state whether the record is valid")
        if case.get("build_permitted") is not valid:
            raise ValidationFailure(f"{name} does not bind the verdict to record validity")
        if (case.get("expected_error") is None) is not valid:
            raise ValidationFailure(f"{name} does not bind a diagnostic to an invalid record")

        control = case.get("control")
        in_inventory = case.get("in_inventory")
        if in_inventory is not (control in native):
            raise ValidationFailure(f"{name} misstates inventory membership of {control}")
        expected_error: Any = None
        if control in deferred or case.get("record_execution_policy") != (
            PORTABLE_EXECUTION_POLICY
        ):
            expected_error = "build_execution_hardened_claim_forbidden"
        elif (
            not in_inventory
            or case.get("entry_count") != 1
            or case.get("record_version") != CAPABILITY_EVIDENCE_RECORD_VERSION
            or (case.get("availability") == "available" and case.get("status") != "applied")
            or (
                case.get("availability") == "unavailable"
                and case.get("status") != "unavailable"
            )
        ):
            expected_error = "build_execution_capability_evidence_invalid"
        if case.get("expected_error") != expected_error:
            raise ValidationFailure(
                f"{name} expects {case.get('expected_error')}, not {expected_error}"
            )
        if case.get("hardened_guarantee_claimed") is True and valid is not False:
            raise ValidationFailure(f"{name} emits a hardened claim under the portable policy")
        if case.get("expected_error") == "build_execution_control_unavailable":
            raise ValidationFailure(
                f"{name} turns a reporting fault into a mandatory-control rejection"
            )

    unavailable = evidence["unavailable-native-control-does-not-reject"]
    if (
        unavailable.get("availability") != "unavailable"
        or unavailable.get("status") != "unavailable"
        or unavailable.get("build_permitted") is not True
        or unavailable.get("expected_error") is not None
    ):
        raise ValidationFailure(
            "an unavailable inventory control must not reject a portable build"
        )


def validate_execution_failure_boundary(
    vector: Any, native: dict[str, Any], deferred: dict[str, Any]
) -> None:
    """Check the single portable failure boundary and its deferral guards."""
    boundary = vector.get("failure_boundary")
    if not isinstance(boundary, dict) or set(boundary) != {
        "missing_mandatory_portable_control",
        "unavailable_inventory_native_control",
        "missing_deferred_hardened_capability",
    }:
        raise ValidationFailure("the portable failure boundary is not stated exactly once")
    mandatory = boundary["missing_mandatory_portable_control"]
    if (
        mandatory.get("rejects_build") is not True
        or mandatory.get("expected_error") != "build_execution_control_unavailable"
        or mandatory.get("fails_before") != "worker-launch"
        or mandatory.get("published") is not False
    ):
        raise ValidationFailure(
            "a missing mandatory portable control does not reject before the worker"
        )
    for key in ("unavailable_inventory_native_control", "missing_deferred_hardened_capability"):
        entry = boundary[key]
        if (
            entry.get("rejects_build") is not False
            or entry.get("expected_error") is not None
            or entry.get("fails_before") is not None
            or entry.get("published") is not True
        ):
            raise ValidationFailure(f"{key} is treated as a portable rejection")

    guards = named_cases(
        vector.get("deferred_capability_rejection_guards"), "deferred rejection guards"
    )
    if set(guards) != set(deferred):
        raise ValidationFailure("deferred hardened guarantees lack exact rejection guards")
    mandatory_controls = named_cases(vector.get("mandatory_controls"), "mandatory controls")
    record = vector.get("capability_evidence_record") or {}
    example_controls = {
        entry.get("name")
        for example in (record.get("examples") or {}).values()
        for entry in example.get("controls") or []
    }
    for name, guard in guards.items():
        if (
            guard.get("in_mandatory_controls") is not False
            or guard.get("in_native_control_inventory") is not False
            or guard.get("in_capability_evidence_record") is not False
            or guard.get("portable_rejection_code") is not None
            or guard.get("build_permitted_when_absent") is not True
        ):
            raise ValidationFailure(f"{name} can reject a portable build")
        if name in mandatory_controls or name in native or name in example_controls:
            raise ValidationFailure(
                f"{name} is a deferred guarantee but appears as a portable control"
            )

    semantics = vector.get("policy_semantics")
    if not isinstance(semantics, dict) or set(semantics) != POLICY_SEMANTIC_KEYS:
        raise ValidationFailure("portable policy semantics are not stated exactly")
    answered: set[str] = set()
    for key, entry in semantics.items():
        if set(entry) != {
            "policy_field",
            "value",
            "means",
            "does_not_mean",
            "deferred_hardened_guarantee",
        }:
            raise ValidationFailure(f"policy semantics {key} is not the closed shape")
        guarantee = entry.get("deferred_hardened_guarantee")
        if guarantee not in deferred or guarantee in answered:
            raise ValidationFailure(
                f"policy semantics {key} does not answer one deferred guarantee"
            )
        answered.add(guarantee)
        for field in ("value", "means", "does_not_mean"):
            if not isinstance(entry.get(field), str) or not entry[field]:
                raise ValidationFailure(f"policy semantics {key} has no exact {field}")
    if answered != set(deferred):
        raise ValidationFailure(
            "every deferred hardened guarantee needs a stated portable mechanism"
        )
    if semantics["network"].get("policy_field") != "network" or semantics["network"].get(
        "value"
    ) != "none":
        raise ValidationFailure("policy network=none has no stated portable meaning")


def validate_local_go_receipt_oracles() -> None:
    """Check that the generated go-v1 receipt binds its own execution policy."""
    receipt = load_json(SUITE / "schema-cases" / "build-receipt-v1" / "valid.json")
    build_input = receipt.get("input", {})
    if not isinstance(build_input, dict):
        raise ValidationFailure("go-v1 receipt example has no input")
    if receipt.get("cache_key") != ccj1_sha256(build_input):
        raise ValidationFailure("go-v1 receipt cache_key is not SHA-256(CCJ-1(input))")
    policy = build_input.get("policy", {})
    if not isinstance(policy, dict) or policy.get("execution_policy") != PORTABLE_EXECUTION_POLICY:
        raise ValidationFailure("go-v1 receipt does not bind the portable execution policy")
    if receipt["cache_key"] == LEGACY_RC4_GO_V1_CACHE_KEY:
        raise ValidationFailure("go-v1 receipt aliases the rc.4 candidate cache key")

    marker = load_json(
        SUITE / "expected" / "external-repository" / "install-marker-v3-mixed.json"
    )
    builds = marker.get("builds", {})
    if not isinstance(builds, dict) or not builds:
        raise ValidationFailure("mixed marker records no builds")
    for command, record in builds.items():
        if (
            not isinstance(record, dict)
            or record.get("execution_policy") != PORTABLE_EXECUTION_POLICY
        ):
            raise ValidationFailure(f"marker record {command} omits its execution policy")

    claim = load_json(SUITE / "schema-cases" / "conformance-claim-v3" / "valid.json")
    drivers = claim.get("build_drivers", [])
    if not isinstance(drivers, list) or not drivers:
        raise ValidationFailure("claim v3 example declares no build drivers")
    for driver in drivers:
        if (
            not isinstance(driver, dict)
            or driver.get("execution_policy") != PORTABLE_EXECUTION_POLICY
        ):
            raise ValidationFailure("claim v3 driver assertion omits its execution policy")


def validate_vector_semantics() -> None:
    marker = load_json(SUITE / "expected" / "marker.json")
    for field in ("agents", "commands", "dependencies", "files", "runtime_roots", "requirers"):
        require_sorted_unique(marker[field], f"marker.{field}")
    require_sorted_unique(marker["activation"]["commands"], "marker.activation.commands")
    if "locale" not in marker or marker["locale"] is not None:
        raise ValidationFailure("golden marker must carry explicit locale: null")

    ledger = load_json(SUITE / "expected" / "adapter-ledger.json")
    require_sorted_unique(ledger["entries"], "adapter ledger entries")

    manifest_resolution = load_json(SUITE / "vectors" / "skill-manifest-resolution.json")
    require_named_cases(
        manifest_resolution,
        "skill-manifest resolution",
        {
            "canonical-only",
            "legacy-only",
            "equal-dual-manifests",
            "conflicting-dual-manifests",
            "invalid-canonical-does-not-fallback",
            "invalid-legacy-does-not-hide-behind-canonical",
            "runtime-fallback-without-modern-manifest",
            "pure-context-without-manifest",
        },
    )
    errors = {item.get("error") for item in manifest_resolution if "error" in item}
    if errors != {"conflicting_skill_manifests", "manifest_invalid"}:
        raise ValidationFailure("skill-manifest resolution error classes are incomplete")
    for item in manifest_resolution:
        files = item.get("files")
        if not isinstance(files, dict) or any(
            not isinstance(name, str) or not isinstance(payload, str)
            for name, payload in files.items()
        ):
            raise ValidationFailure("skill-manifest resolution files must map paths to text")

    valid_ccj = load_json(SUITE / "vectors" / "canonical-valid.json")
    if not valid_ccj or any(not item.get("canonical_utf8") for item in valid_ccj):
        raise ValidationFailure("canonical-valid vectors are empty")
    invalid_ccj = load_json(SUITE / "vectors" / "canonical-invalid.json")
    expected_errors = {
        "duplicate_key",
        "invalid_unicode",
        "non_integer_number",
        "non_shortest_integer",
        "unsafe_integer",
    }
    if {item["error"] for item in invalid_ccj} != expected_errors:
        raise ValidationFailure("canonical-invalid vectors do not cover all CCJ-1 rejection classes")

    service = load_json(SUITE / "vectors" / "registry-service.json")
    expected_key = ["name", "source_identity", "commit", "content_sha256"]
    if service.get("artifact_key") != expected_key or service.get("sort_key") != expected_key:
        raise ValidationFailure("registry-service artifact and sort keys are incomplete")
    records = service.get("records")
    if not isinstance(records, list) or len(records) < 4:
        raise ValidationFailure("registry-service records are incomplete")
    record_ids = [item.get("id") for item in records if isinstance(item, dict)]
    if len(record_ids) != len(records) or len(record_ids) != len(set(record_ids)):
        raise ValidationFailure("registry-service record ids must be present and unique")
    require_named_cases(
        service.get("query_cases"),
        "registry-service query",
        {
            "identity-pair-keeps-content-equivocation",
            "content-hash-matches-mirrors",
            "all-filters-are-conjunctive",
            "conjunctive-mismatch-is-empty",
            "source-without-commit",
            "commit-without-source",
        },
    )
    pagination = service.get("pagination")
    if (
        not isinstance(pagination, dict)
        or pagination.get("boundary_log_size") != len(records)
        or pagination.get("invalid_cursor_status") != 404
        or not pagination.get("expected_pages")
    ):
        raise ValidationFailure("registry-service pagination boundary is incomplete")
    if set(pagination.get("cursor_rejections", [])) != {
        "changed_query",
        "changed_limit",
        "wrong_endpoint",
        "expired",
        "unavailable_snapshot",
    }:
        raise ValidationFailure("registry-service cursor rejection classes are incomplete")
    require_named_cases(
        service.get("idempotency_cases"),
        "registry-service idempotency",
        {"same-auditor-replay", "same-auditor-conflict", "different-auditors-do-not-conflict"},
    )
    require_named_cases(
        service.get("transaction_cases"),
        "registry-service transaction",
        {"concurrent-writers", "failure-before-commit", "bundle-import-failure"},
    )
    require_named_cases(
        service.get("recovery_cases"),
        "registry-service recovery",
        {
            "valid-restart",
            "broken-previous-hash",
            "broken-entry-hash",
            "missing-sequence",
            "idempotency-orphan",
            "import-ledger-orphan",
            "missing-service-metadata",
            "missing-schema-table",
        },
    )
    require_named_cases(
        service.get("restore_cases"),
        "registry-service restore",
        {"checkpoint-equal", "checkpoint-rollback", "checkpoint-equivocation"},
    )
    require_named_cases(
        service.get("transport_cases"),
        "registry-service transport",
        {
            "maximum-page-size",
            "oversize-page",
            "oversize-cursor",
            "oversize-request-body",
            "compressed-request-body",
            "maximum-idempotency-key",
            "oversize-idempotency-key",
            "non-visible-idempotency-key",
            "network-rate-limit",
            "auditor-rate-limit",
        },
    )
    require_named_cases(
        service.get("cache_cases"),
        "registry-service cache",
        {"public-read", "authenticated-write", "error-response"},
    )

    client = load_json(SUITE / "vectors" / "registry-client.json")
    require_named_cases(
        client.get("snapshot_transitions"),
        "registry-client snapshot transition",
        {"advance-after-key-rotation", "restore-rollback", "equal-version-repeat", "equal-version-equivocation"},
    )
    require_named_cases(
        client.get("retry_cases"),
        "registry-client retry",
        {
            "get-network",
            "get-rate-limit",
            "get-unavailable",
            "get-conflict",
            "post-idempotent-unavailable",
            "post-unsafe-unavailable",
            "post-idempotent-bad-request",
        },
    )
    retry_values = {item["retry_permitted"] for item in client["retry_cases"]}
    if retry_values != {True, False}:
        raise ValidationFailure("registry-client retry vectors need permitted and forbidden cases")
    if client.get("retry_policy") != {
        "max_attempts": 3,
        "get_total_deadline_seconds": 30,
        "post_total_deadline_seconds": 45,
        "follow_redirects": False,
    }:
        raise ValidationFailure("registry-client retry policy is incomplete")
    require_named_cases(
        client.get("pagination_rejections"),
        "registry-client pagination rejection",
        {"repeated-cursor", "oversize-cursor", "record-limit", "oversize-response"},
    )
    require_named_cases(
        client.get("rollback_state_cases"),
        "registry-client rollback state",
        {
            "missing-on-first-use",
            "deleted-after-prior-use",
            "corrupted-existing-state",
            "unavailable-state-directory",
        },
    )

    manager = load_json(SUITE / "vectors" / "manager-lifecycle.json")
    require_named_cases(
        manager.get("launcher_cases"),
        "manager launcher",
        {"skill-command-without-shell-activation", "declared-system-command-without-profile"},
    )
    require_named_cases(
        manager.get("bootstrap_cases"),
        "manager bootstrap",
        {"missing-config-if-missing", "existing-config-if-missing", "if-missing-with-force"},
    )
    require_named_cases(
        manager.get("upgrade_cases"),
        "manager upgrade",
        {"selected-project-closure", "all-projects-deduplicate", "global-closure"},
    )
    require_named_cases(
        manager.get("dry_run_cases"),
        "manager dry run",
        {"project-upgrade", "global-upgrade"},
    )

    acquisition = load_json(SUITE / "vectors" / "external-repository-acquisition.json")
    require_named_cases(
        acquisition.get("cases"),
        "external repository acquisition",
        {
            "sha1-untagged-https",
            "sha256-untagged-https",
            "sha1-tagged-https",
            "sha256-tagged-ssh",
            "tag-moved",
            "tag-missing",
            "tag-malformed-object",
            "untagged-missing-object",
            "network-substitution-revision",
            "network-substitution-tag",
            "network-substitution-branch",
            "malformed-ref-rejected-before-git",
        },
    )
    acquisition_cases = named_cases(acquisition["cases"], "external repository acquisition")
    for name in ("tag-moved", "tag-missing", "tag-malformed-object"):
        case = acquisition_cases[name]
        if any(
            case.get(field) is not False
            for field in (
                "direct_oid_fetch_attempted",
                "audit_started",
                "artifact_cache_lookup",
                "compiler_started",
            )
        ):
            raise ValidationFailure(
                f"external repository acquisition {name} must fail before direct-OID fallback, audit, cache, and compiler"
            )
    forbidden_fetch = set(acquisition.get("forbidden_fetch_features", []))
    if forbidden_fetch != {
        "configured-refspec",
        "depth",
        "filter",
        "helper-selected-transport",
        "mirror",
        "prune",
        "remote-name",
        "server-option",
        "source-upload-pack",
        "stdin-refspec",
        "tag-auto-follow",
    }:
        raise ValidationFailure("external repository fetch-negative boundary is incomplete")

    fixtures = SUITE / "fixtures" / "external-repository"
    for fixture_path in sorted(fixtures.glob("*.json")):
        if fixture_path.stat().st_size > 65_536:
            raise ValidationFailure(
                f"{fixture_path.relative_to(ROOT)} exceeds the 65536-byte shared-fixture limit"
            )
    raw = load_json(fixtures / "raw-objects.json")
    require_named_cases(
        raw.get("cases"),
        "external repository raw objects",
        {
            "valid-commit-with-signed-and-extra-headers",
            "valid-sha256-commit",
            "reject-duplicate-tree-header",
            "reject-misordered-tree-after-parent",
            "reject-missing-header-message-separator",
            "valid-signed-annotated-tag",
            "reject-duplicate-object-and-type-headers",
            "reject-tag-declared-target-type-mismatch",
            "valid-regular-and-executable-files",
            "reject-symbolic-link",
            "reject-submodule-gitlink",
            "reject-special-file-mode",
        },
    )
    for case in raw["cases"]:
        content = decode_base64(case.get("content_base64"), f"raw object {case['name']}")
        try:
            digest = git_object_id(case.get("object_format"), case.get("object_type"), content)
        except (TypeError, ValueError) as exc:
            raise ValidationFailure(f"raw object {case['name']} has invalid hash metadata") from exc
        if case.get("object_id") != digest:
            raise ValidationFailure(f"raw object {case['name']} has the wrong exact object ID")

    lfs = load_json(fixtures / "lfs-pointers.json")
    require_named_cases(
        lfs.get("cases"),
        "external repository LFS",
        {
            "canonical-current-pointer",
            "accepted-crlf-blank-unsorted-and-no-terminal-lf",
            "accepted-exact-duplicate-key-last-value-wins",
            "distinct-duplicate-priority-is-ordinary",
            "nonempty-size-zero-is-noncanonical",
            "cutoff-1023-after-trim",
            "cutoff-1024-is-ordinary",
            "near-miss-extension-starts-with-punctuation",
            "near-miss-uppercase-oid",
            "zero-byte-blob",
        },
    )
    lfs_cases = named_cases(lfs["cases"], "external repository LFS")
    if len(decode_base64(lfs_cases["cutoff-1023-after-trim"]["bytes_base64"], "LFS 1023 cutoff")) != 1023:
        raise ValidationFailure("LFS lower cutoff fixture is not exactly 1023 bytes")
    if len(decode_base64(lfs_cases["cutoff-1024-is-ordinary"]["bytes_base64"], "LFS 1024 cutoff")) != 1024:
        raise ValidationFailure("LFS upper cutoff fixture is not exactly 1024 bytes")

    local = load_json(fixtures / "local-config-and-refs.json")
    require_named_cases(
        local.get("cases"),
        "external repository local admission",
        {
            "valid-sha1-files-ref",
            "valid-sha256-detached-head",
            "reject-gitfile",
            "reject-bare-layout",
            "reject-linked-worktree",
            "reject-config-include",
            "reject-alternate-object-store",
            "reject-replace-ref",
            "reject-grafts",
            "reject-promisor-sidecar",
            "reject-partial-clone-config",
            "source-filter-config-is-inert",
            "source-credential-helper-is-inert",
            "reject-reftable",
            "reject-link-or-special-administration-file",
        },
    )
    for case in local["cases"]:
        for path, payload in case.get("files_base64", {}).items():
            decode_base64(payload, f"local admission {case['name']} {path}")

    packs = load_json(fixtures / "pack-index.json")
    require_named_cases(
        packs.get("cases"),
        "external repository pack/index",
        {
            "valid-empty-pack-v2-sha1",
            "valid-empty-pack-v3-sha1",
            "valid-empty-pack-v2-sha256",
            "reject-pack-v4",
            "reject-index-v1",
            "reject-pack-without-index",
            "reject-index-checksum-mismatch",
            "reject-pack-hash-family-mismatch",
        },
    )
    pack_cases = named_cases(packs["cases"], "external repository pack/index")
    for name in ("valid-empty-pack-v2-sha1", "valid-empty-pack-v3-sha1", "valid-empty-pack-v2-sha256"):
        case = pack_cases[name]
        validate_empty_pack_index(
            case,
            case.get("object_format"),
            expect_index_checksum=True,
        )

    checksum_case = pack_cases["reject-index-checksum-mismatch"]
    checksum_base = pack_cases.get(checksum_case.get("base_case"))
    if checksum_base is None:
        raise ValidationFailure("index-checksum mutation references an unknown base case")
    checksum_mutation = checksum_case.get("mutation")
    if not isinstance(checksum_mutation, dict):
        raise ValidationFailure("index-checksum mutation is not structured")
    mutated_pack, mutated_index = materialize_pack_mutation(checksum_base, checksum_mutation)
    case_pack = decode_hex(checksum_case.get("pack_hex"), "index-checksum case pack")
    case_index = decode_hex(checksum_case.get("index_hex"), "index-checksum case index")
    base_index = decode_hex(checksum_base.get("index_hex"), "index-checksum base index")
    differences = [
        index for index, (before, after) in enumerate(zip(base_index, case_index)) if before != after
    ]
    if (
        case_pack != mutated_pack
        or case_index != mutated_index
        or differences != [len(base_index) - 1]
        or checksum_case.get("expected_error")
        != "build_repository_local_object_format_unsupported"
    ):
        raise ValidationFailure("index-checksum negative does not prove its exact single-byte fault")
    validate_empty_pack_index(
        checksum_case,
        "sha1",
        expect_index_checksum=False,
    )

    family_case = pack_cases["reject-pack-hash-family-mismatch"]
    family_base = pack_cases.get(family_case.get("base_case"))
    if family_base is None:
        raise ValidationFailure("hash-family mutation references an unknown base case")
    family_mutation = family_case.get("mutation")
    if not isinstance(family_mutation, dict):
        raise ValidationFailure("hash-family mutation is not structured")
    family_pack, family_index = materialize_pack_mutation(family_base, family_mutation)
    if (
        family_pack != decode_hex(family_case.get("pack_hex"), "hash-family case pack")
        or family_index != decode_hex(family_case.get("index_hex"), "hash-family case index")
        or family_case.get("fixture_object_format") != "sha1"
        or family_case.get("object_format") != "sha256"
        or family_case.get("expected_error")
        != "build_repository_local_object_format_unsupported"
    ):
        raise ValidationFailure("hash-family negative is not the exact sha1-bytes/sha256-declaration fault")
    validate_empty_pack_index(family_case, "sha1", expect_index_checksum=True)
    try:
        validate_empty_pack_index(family_case, "sha256", expect_index_checksum=True)
    except ValidationFailure:
        pass
    else:
        raise ValidationFailure("hash-family negative is valid under its declared sha256 format")

    expected_root = SUITE / "expected" / "external-repository"
    receipt = load_json(expected_root / "build-receipt-v2.json")
    marker = load_json(expected_root / "install-marker-v3-mixed.json")
    plan = load_json(expected_root / "mixed-build-plan.json")
    validate_external_receipt_oracles(receipt, marker, plan)

    lifecycle = load_json(SUITE / "vectors" / "external-repository-lifecycle.json")
    order = lifecycle.get("whole_snapshot_order")
    require_sorted_unique(
        sorted(order) if isinstance(order, list) else order,
        "external repository whole-snapshot phase inventory",
    )
    if not isinstance(order, list):
        raise ValidationFailure("external repository whole-snapshot order must be an array")
    positions = {name: index for index, name in enumerate(order)}
    for later in ("artifact-cache-lookup", "compiler"):
        if positions.get("independent-external-audit", len(order)) >= positions.get(later, -1):
            raise ValidationFailure(f"external repository audit must precede {later}")
    lifecycle_requirements = {
        "cache_cases": {
            "verified-cache-hit",
            "cache-miss",
            "corrupt-receipt",
            "corrupt-artifact",
            "untrusted-protected-boundary",
            "offline-syntax-only",
            "offline-install",
        },
        "source_covering_cases": {
            "external-source-dry-run",
            "external-audit-only",
        },
        "mixed_build_cases": {
            "schema6-local-only",
            "schema7-local-only",
            "schema7-external-only",
            "schema7-mixed",
            "schema7-substituted-external",
        },
        "transaction_cases": {
            "failure-before-publication",
            "failure-after-private-stage",
            "marker-consumer-last",
            "recovery-uncertain-journal",
        },
        "status_repair_gc_cases": {
            "status-current",
            "status-missing-snapshot",
            "status-unreadable-protected-state",
            "repair-reacquires-exact-source",
            "gc-retains-roots",
        },
        "path_shim_cases": {
            "external-command-shim",
            "package-path-entry-rejected",
            "shim-collision-rolls-back",
        },
        "signing_cases": {
            "unsigned-local-build",
            "package-signing-request",
            "platform-requires-local-signing",
            "release-pipeline-signing",
        },
    }
    for field, required in lifecycle_requirements.items():
        require_named_cases(lifecycle.get(field), f"external repository {field}", required)

    cache_cases = named_cases(lifecycle["cache_cases"], "external repository cache")
    source_covering = named_cases(
        lifecycle["source_covering_cases"],
        "external repository source-covering operations",
    )
    status_cases = named_cases(
        lifecycle["status_repair_gc_cases"],
        "external repository status/repair/GC",
    )

    def require_audit_order(
        label: str,
        case: dict[str, Any],
        *,
        cache_lookup: bool,
        compiler: bool,
    ) -> None:
        phases = case.get("ordered_phases")
        if not isinstance(phases, list) or not phases:
            raise ValidationFailure(f"{label} has no executable ordered phases")
        if len(phases) != len(set(phases)) or any(phase not in positions for phase in phases):
            raise ValidationFailure(f"{label} has unknown or duplicate ordered phases")
        path_positions = [positions[phase] for phase in phases]
        if path_positions != sorted(path_positions):
            raise ValidationFailure(f"{label} does not follow whole-snapshot order")
        for required_phase in (
            "exact-source-acquisition",
            "whole-snapshot-validation",
            "independent-external-audit",
        ):
            if required_phase not in phases:
                raise ValidationFailure(f"{label} does not prove {required_phase}")
        if ("artifact-cache-lookup" in phases) != cache_lookup:
            raise ValidationFailure(f"{label} has the wrong cache-lookup phase")
        if ("compiler" in phases) != compiler:
            raise ValidationFailure(f"{label} has the wrong compiler phase")
        audit_position = phases.index("independent-external-audit")
        for later in ("artifact-cache-lookup", "compiler"):
            if later in phases and audit_position >= phases.index(later):
                raise ValidationFailure(f"{label} audits after {later}")

    require_audit_order(
        "verified cache hit",
        cache_cases["verified-cache-hit"],
        cache_lookup=True,
        compiler=False,
    )
    require_audit_order(
        "cache miss",
        cache_cases["cache-miss"],
        cache_lookup=True,
        compiler=True,
    )
    require_audit_order(
        "source-covering dry run",
        source_covering["external-source-dry-run"],
        cache_lookup=True,
        compiler=False,
    )
    require_audit_order(
        "audit-only operation",
        source_covering["external-audit-only"],
        cache_lookup=False,
        compiler=False,
    )
    require_audit_order(
        "repair operation",
        status_cases["repair-reacquires-exact-source"],
        cache_lookup=True,
        compiler=True,
    )
    for name in ("external-source-dry-run", "external-audit-only"):
        case = source_covering[name]
        if (
            case.get("source_claimed") is not True
            or case.get("audit_claimed") is not True
            or case.get("mutation") is not False
        ):
            raise ValidationFailure(f"{name} is not a non-mutating source-covering proof")
    syntax_only = cache_cases["offline-syntax-only"]
    if any(
        syntax_only.get(field) is not False
        for field in ("source_claimed", "audit_claimed", "cache_claimed", "mutation")
    ):
        raise ValidationFailure("syntax-only check is not disjoint from source-covering claims")

    validate_go_host_execution_policy()
    validate_local_go_receipt_oracles()

    qualification = load_json(SUITE / "vectors" / "conformance-claim-v3-qualification.json")
    if qualification.get("candidate_claims_emitted") != []:
        raise ValidationFailure("rc.5 candidate fabricates native platform claims")
    platforms = named_cases(qualification.get("platforms"), "claim-v3 platforms")
    if (
        platforms.get("linux", {}).get("status") != "excluded"
        or platforms["linux"].get("until_task") != "TASK-260728-1skseh"
    ):
        raise ValidationFailure("claim-v3 Linux exclusion is not bound to its later native task")


def validate_toolchain_contract() -> None:
    """Guard the decision 0007 toolchain requirement, preflight and guidance.

    Four properties are of the whole surface rather than of one document, so
    none of them is expressible as a schema keyword or as a runtime code:

    1. the wire surface of every published schema version carries no field that
       names an executable path, toolchain root, URL, mirror, channel or track,
       version manager, install command, environment override, credential,
       keyring, checksum, or trust root. A field that does not exist produces no
       value to diagnose, so this is an authoring obligation on the schemas;
    2. every complete registry entry resolves exactly one relpath and one probe
       for every operating system in its platforms set, and declares neither
       outside it. That is what makes the Stage A step 2 host-pair check total;
    3. the guidance catalog is total over supported toolchains, all twelve
       reasons and supported platforms, every active entry is reachable, and the
       revision lifecycle is one-way monotone;
    4. the generated corpus carries the section 8 vector inventory.
    """
    common = load_json(SCHEMAS / "common.schema.json")
    enumerated = toolchain_gate.check_wire_surface(common, ValidationFailure)

    # The enumeration is only a gate if it actually reaches the surfaces that
    # exist. Every wire definition that a published manifest or descriptor
    # schema references must be enumerated, so a schema version added later
    # cannot introduce an unlisted package surface.
    referenced = set()
    for schema_path in sorted(SCHEMAS.glob("*.json")):
        if schema_path.name == "common.schema.json":
            continue
        text = schema_path.read_text(encoding="utf-8")
        for name in toolchain_gate.WIRE_SURFACE_DEFINITIONS:
            if COMMON_REF_PREFIX + name in text:
                referenced.add(name)
    for name in ("skillBuildTargetV1", "skillBuildTargetV2"):
        if name not in referenced:
            raise ValidationFailure(
                f"{name} is enumerated by the wire-surface gate but referenced by no descriptor schema"
            )
    unenumerated = sorted(referenced - set(enumerated))
    if unenumerated:
        raise ValidationFailure(
            f"published wire definitions outside the wire-surface enumeration: {unenumerated}"
        )

    registry = load_json(CANDIDATE_SUITE / "vectors" / "toolchain-registry.json")["registry"]
    catalog = load_json(CANDIDATE_SUITE / "vectors" / "toolchain-guidance-catalog.json")["catalog"]
    toolchain_gate.check_registry(registry, ValidationFailure)
    toolchain_gate.check_guidance_catalog(catalog, registry, ValidationFailure)

    diagnostics = load_json(CANDIDATE_SUITE / "vectors" / "toolchain-diagnostics.json")
    payloads = list(diagnostics["union"])
    named = [payload for case in diagnostics["payloads"] for payload in case["payloads"]]
    for payload in named:
        if payload not in payloads:
            raise ValidationFailure(
                f"inventory payload {payload['code']} at stage {payload['stage']} is outside the declared union"
            )
    toolchain_gate.check_diagnostic_payloads(payloads, catalog, ValidationFailure)

    # The section 5.1 site table is the union's discriminant set, so every
    # payload the corpus carries must land on a declared site, and every
    # declared site must carry a payload. A site with no instance is a shape
    # nobody exercised; an instance with no site is a shape nobody reviewed.
    def firing_site(value: Any, discriminant: Any = None) -> tuple[str, str, str | None]:
        """A site is (code, stage, discriminant).

        The discriminant is load-bearing rather than decorative:
        ``platform_unsupported`` fires twice inside stage A with different
        established member sets, so a key that dropped it would let either half
        satisfy the other's obligation.
        """
        source = discriminant if discriminant is not None else value
        token = next(
            (source[member] for member in ("check", "substep") if member in source),
            None,
        )
        return value["code"], value["stage"], token

    sites = {
        firing_site(site, site.get("discriminant")) for site in diagnostics["sites"]
    }
    for payload in payloads:
        if firing_site(payload) not in sites:
            raise ValidationFailure(
                f"diagnostic payload {payload['code']} at stage {payload['stage']} is not a declared firing site"
            )
    instantiated = {firing_site(payload) for payload in payloads}
    uninstantiated = sorted(sites - instantiated)
    if uninstantiated:
        raise ValidationFailure(
            f"firing sites with no payload instance: {uninstantiated}"
        )

    toolchain_gate.check_inventory(CANDIDATE_SUITE, ValidationFailure)

    # The preflight corpus must keep declaring the compatibility set as fixture
    # input, which is what makes a vector outcome deterministic across managers.
    preflight = load_json(CANDIDATE_SUITE / "vectors" / "toolchain-preflight.json")
    defaults = preflight.get("defaults", {})
    if defaults.get("compatibility") != {
        "family_granularity": "major_minor",
        "families": [[1, 23]],
    }:
        raise ValidationFailure(
            "the preflight corpus does not declare the manager compatibility set as fixture input"
        )
    if defaults.get("registry_baseline") != {"kind": "at_least", "min": "1.23.0"}:
        raise ValidationFailure("the preflight corpus does not declare the registry baseline")

    # Every rejecting preflight case asserts the failure preceded persistent
    # mutation and a compiler child. That is the no-mutation boundary the two
    # stages exist to hold, and it is asserted per case rather than in prose.
    for case in preflight["cases"]:
        expected = case.get("expected", {})
        if expected.get("outcome") != "rejected":
            continue
        for assertion in ("compiler_started", "persistent_mutation"):
            if expected.get(assertion) is not False:
                raise ValidationFailure(
                    f"preflight case {case['case']} does not assert {assertion} is false"
                )
        if not str(expected.get("code", "")).startswith(("build_toolchain_", "build_descriptor_", "manifest_")):
            raise ValidationFailure(
                f"preflight case {case['case']} reports the untyped code {expected.get('code')!r}"
            )

    # Every Go metadata case is produced before cache lookup and before a
    # compiler child, at a named Stage B step.
    metadata = load_json(CANDIDATE_SUITE / "vectors" / "toolchain-go-metadata.json")
    for case in metadata["cases"]:
        site = case.get("expected", {}).get("site")
        if site is None:
            continue
        if site.get("stage") != "B" or site.get("step") not in {"3", "5"}:
            raise ValidationFailure(
                f"go metadata case {case['case']} names the site {site}, which is not a Stage B classifier step"
            )
        for assertion in ("before_cache_lookup", "before_compiler_child"):
            if site.get(assertion) is not True:
                raise ValidationFailure(
                    f"go metadata case {case['case']} does not assert {assertion}"
                )
    check_go_alignment_properties(metadata)
    toolchain_gate.check_probe_agreement(metadata["alignment"]["rows"], ROOT, ValidationFailure)


def check_go_alignment_properties(metadata: Any) -> None:
    """Properties P1 and P2 over the section 4.2.1.1 fixture table.

    P1 keeps Stage B meaningful: a value outside what the Go command admits must
    not pass as a permitted comparison and reach cache lookup and a compiler
    child. P2 keeps a Go-valid, non-forbidden file from being failed for a
    grammar reason. They are two properties rather than one equality, because
    the security partition deliberately subtracts from what upstream admits.
    """
    rows = metadata["alignment"]["rows"]
    for row in rows:
        position, value = row["position"], row["value"]
        upstream = row["upstream_admitted"]
        if upstream != (row["shape_layer"] and row["semantic_layer"]):
            raise ValidationFailure(
                f"{position} {value!r}: upstream admission is not the conjunction of both layers"
            )
        compared = row["outcome"] == "compare_base_triple" or row["outcome"] == "permitted_not_honored"
        forbidden = row["disposition"] == "forbidden"
        if compared and not upstream:
            raise ValidationFailure(
                f"P1 violated: {position} {value!r} is compared but the Go command does not admit it"
            )
        if upstream and not forbidden and not compared:
            raise ValidationFailure(
                f"P2 violated: {position} {value!r} is admitted upstream, is not forbidden, and is not compared"
            )
    forbidden_go = [row["value"] for row in rows if row["position"] == "go" and row["disposition"] == "forbidden"]
    if forbidden_go:
        raise ValidationFailure(
            f"the go directive has no forbidden class, but the table disposes {forbidden_go} forbidden"
        )
    subtracting = [
        row["value"]
        for row in rows
        if row["disposition"] == "forbidden" and row["upstream_admitted"]
    ]
    if not subtracting:
        raise ValidationFailure(
            "the security partition does not subtract: no forbidden value is admitted upstream, "
            "so P1 and P2 collapse into one equality the contract states is unsatisfiable"
        )
    outside = [
        row["value"]
        for row in rows
        if row["disposition"] == "forbidden" and not row["upstream_admitted"]
    ]
    if not outside:
        raise ValidationFailure(
            "the forbidden partition is bounded by upstream, so only one of the two directions is pinned"
        )


REFERENCE_DOCUMENT = Path("docs") / "compiled-build-toolchain-requirements.md"
# The reference document says of itself that a disagreement with protocol/core.md
# is a defect in the reference. That is only true if something checks; a prose
# rule nobody executes drifts silently, and this one already did. These two
# patterns pull the token set out of each document's own sentence.
REFERENCE_SURFACE_TOKENS = re.compile(
    r"`surface` is ((?:`[a-z_]+`(?:, or |, | or ))*`[a-z_]+`)"
)
CORE_SURFACE_TOKENS = re.compile(
    r"`surface` one of ((?:`[a-z_]+`(?:, or |, | or ))*`[a-z_]+`)"
)
BACKTICKED = re.compile(r"`([a-z_]+)`")
# The `matches` legend of section 3.1.1 and the two classifier tables. Both are
# ordinary Markdown tables, and the classifier tables are matched by their exact
# header so a renamed or reordered column is a failure rather than a silent skip.
MATCHES_LEGEND_HEADER = "| `matches` | Meaning |"
CLASSIFIER_TABLE_HEADER = "| # | Class | `matches` | Match | Disposition | Outcome |"
# In document order: section 4.2.2's `go` directive, then the `toolchain`
# directive. Both are fields of the `go` entry's `go.mod` metadata source.
CLASSIFIER_TABLE_FIELDS = ("go", "toolchain")


def markdown_tables(text: str, header: str) -> list[list[list[str]]]:
    """Every Markdown table opening with ``header``, in document order."""
    tables: list[list[list[str]]] = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() != header:
            continue
        rows: list[list[str]] = []
        for body in lines[index + 2 :]:
            if not body.startswith("|"):
                break
            rows.append([cell.strip() for cell in body.strip().strip("|").split("|")])
        tables.append(rows)
    return tables


def go_metadata_classifiers() -> dict[str, list[dict[str, Any]]]:
    """The shipped `go` entry's `go.mod` value classifiers, by field path."""
    registry = load_json(CANDIDATE_SUITE / "vectors" / "toolchain-registry.json")["registry"]
    entry = next(item for item in registry["entries"] if item["toolchain_id"] == "go")
    source = next(item for item in entry["metadata_sources"] if item["path"] == "go.mod")
    return {
        field["field_path"]: field["classes"]
        for field in source["fields"]
        if field["disposition"] == "classified"
    }


def validate_reference_document() -> None:
    """Hold the extended reference to the normative contract it explains.

    The reference is not normative, but it is the document a reader reaches for,
    and it declares its own disagreement with ``protocol/core.md`` to be a
    defect. This check makes that declaration executable over the two rules that
    are easiest to state once and then leave behind: the closed `source_ref`
    surface token set, and the value-classifier tables.
    """
    reference = (ROOT / REFERENCE_DOCUMENT).read_text(encoding="utf-8")
    core = (ROOT / "protocol" / "core.md").read_text(encoding="utf-8")
    flat = " ".join(reference.split())
    core_flat = " ".join(core.split())

    schema_tokens = load_json(SCHEMAS / "common.schema.json")["$defs"][
        "toolchainSourceRefV1"
    ]["properties"]["surface"]["enum"]
    for label, text, pattern in (
        (REFERENCE_DOCUMENT.as_posix(), flat, REFERENCE_SURFACE_TOKENS),
        ("protocol/core.md", core_flat, CORE_SURFACE_TOKENS),
    ):
        match = pattern.search(text)
        if match is None:
            raise ValidationFailure(f"{label} does not state the source_ref surface token set")
        tokens = BACKTICKED.findall(match.group(1))
        if sorted(tokens) != sorted(schema_tokens):
            raise ValidationFailure(
                f"{label} states source_ref surfaces {tokens}, but "
                f"common.schema.json closes them at {sorted(schema_tokens)}"
            )

    class_schema = load_json(SCHEMAS / "toolchain-registry-v1.schema.json")["$defs"][
        "valueClass"
    ]
    matches_enum = class_schema["properties"]["matches"]["enum"]
    legend = markdown_tables(reference, MATCHES_LEGEND_HEADER)
    if len(legend) != 1:
        raise ValidationFailure(
            f"{REFERENCE_DOCUMENT.as_posix()} does not carry exactly one value-class matches legend"
        )
    legend_tokens = [row[0].strip("`") for row in legend[0]]
    if sorted(legend_tokens) != sorted(matches_enum):
        raise ValidationFailure(
            f"{REFERENCE_DOCUMENT.as_posix()} legends the matches tokens {legend_tokens}, but "
            f"toolchain-registry-v1.schema.json closes them at {sorted(matches_enum)}"
        )
    if "matches" not in class_schema["required"]:
        raise ValidationFailure(
            "toolchain-registry-v1.schema.json does not require a value class to declare what it matches"
        )

    classifiers = go_metadata_classifiers()
    tables = markdown_tables(reference, CLASSIFIER_TABLE_HEADER)
    if len(tables) != len(CLASSIFIER_TABLE_FIELDS):
        raise ValidationFailure(
            f"{REFERENCE_DOCUMENT.as_posix()} carries {len(tables)} classifier tables, "
            f"expected {len(CLASSIFIER_TABLE_FIELDS)}"
        )
    for field_path, rows in zip(CLASSIFIER_TABLE_FIELDS, tables):
        classes = classifiers.get(field_path)
        if classes is None:
            raise ValidationFailure(f"the shipped go entry declares no classifier for {field_path!r}")
        documented = [
            (row[1].strip("`"), row[2].strip("`"), row[4].strip("`")) for row in rows
        ]
        shipped = [
            (item["name"], item["matches"], item["disposition"]) for item in classes
        ]
        if documented != shipped:
            raise ValidationFailure(
                f"{REFERENCE_DOCUMENT.as_posix()} documents the {field_path!r} classifier as "
                f"{documented}, but the shipped registry declares {shipped}"
            )
        if [row[0] for row in rows] != [str(number) for number in range(1, len(rows) + 1)]:
            raise ValidationFailure(
                f"{REFERENCE_DOCUMENT.as_posix()} numbers the {field_path!r} classifier out of order, "
                "so its prose class references do not resolve"
            )


MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def validate_local_links() -> None:
    for path in sorted(ROOT.rglob("*.md")):
        if ".git" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for raw_target in MARKDOWN_LINK.findall(text):
            target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
            if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            decoded = urllib.parse.unquote(target.split("#", 1)[0])
            destination = (path.parent / decoded).resolve()
            try:
                destination.relative_to(ROOT.resolve())
            except ValueError as exc:
                raise ValidationFailure(f"{path}: link escapes repository: {target}") from exc
            if not destination.exists():
                raise ValidationFailure(f"{path}: broken local link: {target}")


def main() -> int:
    checks = [
        validate_schemas,
        validate_repository_descriptor_identity,
        validate_additional_driver_boundary,
        validate_toolchain_contract,
        validate_manifest,
        validate_candidate_manifest,
        validate_frozen_releases,
        validate_reference_document,
        validate_review_evidence,
        validate_vector_semantics,
        validate_local_links,
    ]
    try:
        for check in checks:
            check()
    except ValidationFailure as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        return 1
    released = len(load_json(SUITE / "manifest.json")["files"])
    candidate = len(load_json(CANDIDATE_SUITE / "manifest.json")["files"])
    print(
        f"validated {len(list(SCHEMAS.glob('*.json')))} schemas and "
        f"{released + candidate} vector files ({released} released, {candidate} candidate)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
