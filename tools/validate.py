#!/usr/bin/env python3
"""Validate schemas, examples, vector manifest, and local Markdown links."""

from __future__ import annotations

import base64
import hashlib
import json
import re
import sys
import urllib.parse
from pathlib import Path
from typing import Any

import assurance
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas" / "v1"
SUITE = ROOT / "conformance" / "v1"
REVIEWS = ROOT / "reviews"
SAFE_INTEGER = 9_007_199_254_740_991
PROTOCOL_VERSION = "1.0.0-rc.9"
RC8_PROTOCOL_VERSION = "1.0.0-rc.8"
RC7_PROTOCOL_VERSION = "1.0.0-rc.7"
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
RC7_RELEASE_METADATA_SHA256 = (
    "sha256:e5872ee4dd207bf6b190d8c8be15a9366d9c1e3638047ea983620b97c9f84d5d"
)
RC7_SOURCE_COMMIT = "99f70947d6f2447366d6c996127b73eca37a9159"
RC8_RELEASE_METADATA_SHA256 = (
    "sha256:293f101d10665061aa049efa72141f9e3c5d608bbde300e882f6e3e095e31ede"
)
RC8_SOURCE_COMMIT = "f8c405aa3ad0a39d260c2ed93684e55c5a346359"

# The single execution-policy identity that protocol 1.0 defines for the
# compiled-build drivers, the identity reserved for the separately tracked
# fail-closed profile, and the board story that owns it.
PORTABLE_EXECUTION_POLICY = "manager-worker-v1"
RESERVED_HARDENED_EXECUTION_POLICY = "hardened-worker-v1"
SCRIPT_EXECUTION_POLICY = "script-worker-v1"
SCRIPT_EXECUTION_FIELDS = ("execution_policy", "interpreter")
MODULE_ROOT_FIELDS = ("modules",)
HARDENED_EXECUTION_OWNER = "STORY-260728-327soo"
# The exhaustive rc.5 per-platform native-control inventory and the closed
# per-operation capability-evidence record that reports it.
NATIVE_CONTROL_INVENTORY_VERSION = "rc5-native-control-inventory-v1"
CAPABILITY_EVIDENCE_RECORD_VERSION = "capability-evidence-v1"
SCRIPT_NATIVE_CONTROL_INVENTORY_VERSION = "script-worker-v1-native-control-inventory-v1"
SCRIPT_CAPABILITY_EVIDENCE_RECORD_VERSION = "script-capability-evidence-v1"
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
# expected/marker.json is the published marker-v1 legacy-read evidence a
# manager MAY still regard as current for a schema 1 through 5 package. Its
# bytes are frozen, so it is never the golden a writer compares against.
# expected/marker-v2.json carries that writer golden for the same golden skill:
# managers write marker schema 2 for schema 1 through 6 mutations, and the
# schema-5 golden skill declares no build roots, so the two markers differ in
# exactly these members.
FROZEN_MARKER_V1_SHA256 = "80989f850887814ec09c724a7dd891ac7e2422d5fef7e31f330be3554aa9b28a"
SHARED_FIXTURE_MARKER_V2_DELTA = frozenset({"schema_version", "build_roots", "builds"})
# Directory names that hold scratch or version-control state rather than a
# protocol surface.
NON_SURFACE_DIRECTORIES = (".git", ".temp", ".venv", "__pycache__")


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


def validate_schemas() -> None:
    registry, paths = schema_registry()
    index = load_json(SUITE / "schema-cases" / "index.json")
    covered: set[str] = set()
    for case in index:
        schema_name = case["schema"]
        if schema_name not in paths:
            raise ValidationFailure(f"schema case names unknown schema {schema_name}")
        schema = load_json(paths[schema_name])
        instance = load_json(SUITE / "schema-cases" / case["instance"])
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

    for prefix in ("agent-skill", "csk-skill"):
        for version in range(1, 8):
            schema_name = f"{prefix}-v{version}.schema.json"
            schema = load_json(paths[schema_name])
            for field in SCRIPT_EXECUTION_FIELDS:
                legacy_with_v8_enforcement = {
                    "schema_version": version,
                    "commands": {
                        "enforced-tool": {
                            "type": "script",
                            "unix_path": "scripts/enforced",
                            field: SCRIPT_EXECUTION_POLICY
                            if field == "execution_policy"
                            else "python3-v1",
                        }
                    },
                }
                if version >= 3:
                    legacy_with_v8_enforcement["capabilities"] = {}
                schema_errors = list(
                    Draft202012Validator(schema, registry=registry).iter_errors(
                        legacy_with_v8_enforcement
                    )
                )
                semantic_error = (
                    validate_wire_semantics(schema_name, legacy_with_v8_enforcement)
                    if not schema_errors
                    else None
                )
                if not schema_errors and semantic_error is None:
                    raise ValidationFailure(
                        f"{schema_name}: accepts schema-8-only command {field}"
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


def validate_wire_semantics(schema_name: str, instance: Any) -> str | None:
    if not isinstance(instance, dict):
        return None
    pre_schema8_manifest = re.fullmatch(
        r"(?:agent-skill|csk-skill)-v([1-7])\.schema\.json", schema_name
    )
    if pre_schema8_manifest is not None:
        for field in SCRIPT_EXECUTION_FIELDS + MODULE_ROOT_FIELDS:
            if field in instance:
                return f"{field} is legal only in manifest schema 8"
        commands = instance.get("commands", {})
        if isinstance(commands, dict):
            for command in commands.values():
                if not isinstance(command, dict):
                    continue
                for field in SCRIPT_EXECUTION_FIELDS + MODULE_ROOT_FIELDS:
                    if field in command:
                        return f"command {field} is legal only in manifest schema 8"
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
    elif schema_name == "skill-build-v1.schema.json":
        for target in instance.get("targets", {}).values():
            if isinstance(target, dict):
                root, source = target.get("build_root"), target.get("source_dir")
                if isinstance(root, str) and isinstance(source, str) and not is_below_or_equal(source, root):
                    return "source_dir must equal or be below build_root"
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
    elif schema_name in {"install-marker-v3.schema.json", "install-marker-v4.schema.json"}:
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
    elif schema_name == "provider-capability-receipt-v1.schema.json":
        observed_at = assurance.parse_timestamp(instance.get("observed_at"))
        expires_at = assurance.parse_timestamp(instance.get("expires_at"))
        if observed_at is None or expires_at is None or observed_at >= expires_at:
            return "capability receipt observed_at must precede expires_at"
    elif schema_name == "execution-receipt-v1.schema.json":
        started_at = assurance.parse_timestamp(instance.get("started_at"))
        completed_at = assurance.parse_timestamp(instance.get("completed_at"))
        if started_at is None or completed_at is None or started_at > completed_at:
            return "execution receipt started_at must be at or before completed_at"
    elif schema_name == "execution-checkpoint-v1.schema.json":
        phase = instance.get("phase")
        previous = instance.get("previous_checkpoint_sha256")
        if phase == "permit-issued" and previous is not None:
            return "permit-issued checkpoint must have a null predecessor"
        if phase in {"execution-started", "execution-succeeded"} and previous is None:
            return f"{phase} checkpoint must have a digest predecessor"
    elif schema_name == "agent-context-v1.schema.json":
        modules = instance.get("context", {}).get("modules") if isinstance(instance.get("context"), dict) else None
        if isinstance(modules, list):
            paths = [
                module.get("path")
                for module in modules
                if isinstance(module, dict) and isinstance(module.get("path"), str)
            ]
            if len(paths) != len(set(paths)):
                return "module paths must be unique across the manifest"
    elif schema_name == "context-lock-v1.schema.json":
        members = instance.get("members")
        if isinstance(members, list) and all(isinstance(member, dict) for member in members):
            keys = [(member.get("kind"), member.get("name")) for member in members]
            if keys != sorted(keys) or len(keys) != len(set(keys)):
                return "lock members must be sorted by (kind, name) without duplicates"
            names = {member.get("name") for member in members}
            root = next((member for member in members if member.get("kind") == "context" and member.get("name") == instance.get("root")), None)
            if root is None:
                return "the lock root must be a context member"
            if root.get("required_by") != [] or root.get("overlay") is not False:
                return "the lock root has no requirers and is not an overlay"
            for member in members:
                required_by = member.get("required_by")
                if isinstance(required_by, list):
                    if required_by != sorted(required_by) or len(required_by) != len(set(required_by)):
                        return "required_by must be sorted and unique"
                    if not set(required_by) <= names:
                        return "required_by names a package outside the lock"
                    if member.get("name") in required_by:
                        return "required_by names the member itself"
    elif schema_name == "agent-environment-marker-v1.schema.json":
        surfaces = instance.get("surfaces")
        if isinstance(surfaces, dict):
            keys = list(surfaces)
            if keys != sorted(keys):
                return "environment marker surface keys must be sorted"
            for key, entry in surfaces.items():
                if not isinstance(entry, dict):
                    continue
                paths = entry.get("paths")
                copies = entry.get("copies")
                if isinstance(paths, list) and isinstance(copies, list):
                    for copy in copies:
                        if isinstance(copy, dict) and copy.get("path") not in paths:
                            return f"surface {key} records a copy outside its paths: {copy.get('path')!r}"
        members = instance.get("members")
        profile = instance.get("profile")
        if isinstance(members, list) and all(isinstance(member, dict) for member in members):
            names = [member.get("name") for member in members]
            if len(names) != len(set(names)):
                return "environment marker members must be unique"
            if isinstance(profile, dict):
                root = next((member for member in members if member.get("name") == profile.get("root")), None)
                if root is None:
                    return "environment marker members must include the root"
                if root.get("overlay") is not False:
                    return "the root member is not an overlay"
        seeded = instance.get("seeded_projects")
        if isinstance(seeded, list) and seeded != sorted(seeded):
            return "seeded_projects must be sorted"
    elif schema_name == "launch-env-fragment-v1.schema.json":
        environment = instance.get("environment")
        system_prompt = instance.get("system_prompt")
        if isinstance(system_prompt, dict) and environment in ENVIRONMENT_SYSTEM_PROMPT_CHANNELS:
            if system_prompt.get("channels") != ENVIRONMENT_SYSTEM_PROMPT_CHANNELS[environment]:
                return "system_prompt.channels must reproduce the adapter's section 7.3 descriptors"
        mcp = instance.get("mcp")
        if isinstance(mcp, dict) and environment in ENVIRONMENT_MCP_CHANNELS:
            if mcp.get("channels") != ENVIRONMENT_MCP_CHANNELS[environment]:
                return "mcp.channels must reproduce the adapter's section 7.8 descriptor"
            names = mcp.get("env_names")
            if isinstance(names, list) and (names != sorted(names) or len(names) != len(set(names))):
                return "mcp.env_names must be the sorted union"
        prepend = instance.get("path_prepend")
        if isinstance(prepend, str) and not prepend.startswith("/manager/environments/"):
            return "path_prepend must stay below the manager-owned environments root"
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
    if manifest.get("protocol_version") != PROTOCOL_VERSION:
        raise ValidationFailure(
            f"vector manifest protocol_version is not {PROTOCOL_VERSION}"
        )
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

    historical_path = ROOT / "release" / "1.0.0-rc.5.json"
    historical_digest = "sha256:" + hashlib.sha256(historical_path.read_bytes()).hexdigest()
    if historical_digest != RC5_RELEASE_METADATA_SHA256:
        raise ValidationFailure("published rc.5 release metadata changed")

    rc6_path = ROOT / "release" / "1.0.0-rc.6.json"
    rc6_digest = "sha256:" + hashlib.sha256(rc6_path.read_bytes()).hexdigest()
    if rc6_digest != RC6_RELEASE_METADATA_SHA256:
        raise ValidationFailure("historical rc.6 release metadata changed")

    rc7_path = ROOT / "release" / "1.0.0-rc.7.json"
    rc7_digest = "sha256:" + hashlib.sha256(rc7_path.read_bytes()).hexdigest()
    if rc7_digest != RC7_RELEASE_METADATA_SHA256:
        raise ValidationFailure("historical rc.7 release metadata changed")

    rc8_path = ROOT / "release" / "1.0.0-rc.8.json"
    rc8_digest = "sha256:" + hashlib.sha256(rc8_path.read_bytes()).hexdigest()
    if rc8_digest != RC8_RELEASE_METADATA_SHA256:
        raise ValidationFailure("historical rc.8 release metadata changed")

    release = load_json(ROOT / "release" / "1.0.0-rc.9.json")
    manifest_digest = "sha256:" + hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    if release.get("protocol_version") != PROTOCOL_VERSION:
        raise ValidationFailure("rc.9 release metadata identifies the wrong protocol version")
    pin = release.get("candidate_protocol_pin", {})
    if not isinstance(pin, dict) or pin.get("manifest_sha256") != manifest_digest:
        raise ValidationFailure("rc.9 downstream candidate pin does not match the suite manifest")
    downstream = release.get("downstream_consumption", {})
    if (
        not isinstance(downstream, dict)
        or downstream.get("required_manifest_sha256") != manifest_digest
        or downstream.get("committed_release_pin_advanced") is not False
    ):
        raise ValidationFailure("rc.9 downstream consumption metadata is incomplete")
    history = release.get("historical_release", {})
    if (
        not isinstance(history, dict)
        or history.get("protocol_version") != RC8_PROTOCOL_VERSION
        or history.get("metadata_path") != "release/1.0.0-rc.8.json"
        or history.get("metadata_sha256") != RC8_RELEASE_METADATA_SHA256
        or history.get("source_commit") != RC8_SOURCE_COMMIT
        or history.get("immutable") is not True
        or release.get("source_baseline_commit") != RC8_SOURCE_COMMIT
        or release.get("legacy_release") != RC8_PROTOCOL_VERSION
    ):
        raise ValidationFailure("rc.9 metadata does not preserve historical rc.8 evidence")
    claim = release.get("claim_v5", {})
    if (
        not isinstance(claim, dict)
        or claim.get("claim_protocol_version") != PROTOCOL_VERSION
        or claim.get("schema") != "schemas/v1/conformance-claim-v5.schema.json"
        or claim.get("claims_emitted") != []
    ):
        raise ValidationFailure("rc.9 release metadata fabricates a platform claim")
    execution = release.get("assurance", {})
    if (
        not isinstance(execution, dict)
        or execution.get("default_mode") != "portable"
        or execution.get("portable_policy") != "portable-cli-policy-v1"
        or execution.get("portable_execution_policy") != PORTABLE_EXECUTION_POLICY
        or execution.get("verified_policy") != "verified-provider-policy-v1"
        or execution.get("verified_execution_policy") != "verified-provider-execution-v1"
        or execution.get("verified_provider_contract") != "host-execution-provider-v1"
        or execution.get("verified_implementations") != []
        or execution.get("verified_platform_claims") != []
        or execution.get("silent_downgrade_permitted") is not False
        or execution.get("skill_vendored_provider_allowed") is not False
    ):
        raise ValidationFailure(
            "rc.9 release metadata does not honestly record assurance availability"
        )


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


def validate_script_host_execution_policy(vector: Any = None) -> None:
    """Check script-worker-v1 opt-in, derivation, preflight, and evidence closure."""
    if vector is None:
        vector = load_json(SUITE / "vectors" / "script-host-execution-policy.json")
    if vector.get("execution_policy") != SCRIPT_EXECUTION_POLICY:
        raise ValidationFailure("script vector has the wrong execution-policy identity")

    opt_in = named_cases(vector.get("opt_in_cases"), "script opt-in")
    required_opt_in = {
        "schema8-explicit-opt-in", "schema8-absent-policy", "legacy-schema7-script",
        "interpreter-without-policy", "policy-without-interpreter", "unknown-policy",
    }
    if set(opt_in) != required_opt_in:
        raise ValidationFailure("script opt-in case inventory is not exact")
    if opt_in["schema8-explicit-opt-in"].get("mode") != "enforced":
        raise ValidationFailure("explicit schema-8 opt-in is not enforced")
    for name in ("schema8-absent-policy", "legacy-schema7-script"):
        if opt_in[name].get("mode") != "declared-only" or opt_in[name].get("accepted") is not True:
            raise ValidationFailure(f"{name} does not preserve declared-only behavior")
    for name in ("interpreter-without-policy", "policy-without-interpreter", "unknown-policy"):
        if opt_in[name].get("accepted") is not False:
            raise ValidationFailure(f"invalid script opt-in {name} is accepted")

    derivation = named_cases(vector.get("capability_derivation_cases"), "script derivation")
    absent = derivation.get("all-fields-absent-deny-by-default", {}).get("derived", {})
    if (
        absent.get("network") != "offline-environment"
        or absent.get("exec") != ["resolved-interpreter"]
        or absent.get("secrets") != []
        or absent.get("env_read") != []
        or absent.get("filesystem") != [
            "private-cache-root", "private-config-root", "private-temp-root",
            "manager-selected-working-directory",
        ]
    ):
        raise ValidationFailure("absent script capabilities do not derive deny-by-default")
    hosts = derivation.get("declared-network-hosts-are-reporting-only", {})
    if (
        hosts.get("accepted") is not True
        or hosts.get("warning") != "script-command-unfiltered-declared-network"
        or hosts.get("derived", {}).get("network_filter") is not None
    ):
        raise ValidationFailure("declared script network hosts are represented as filtering")

    mandatory = vector.get("mandatory_controls")
    if set(mandatory or []) != {
        "fixed-process-graph", "worker-identity-verification",
        "interpreter-resolution-and-identity-verification", "manager-built-environment",
        "manager-built-path", "offline-network-configuration", "operation-private-runtime-area",
        "explicit-standard-stream-binding", "inventory-controls-applied",
        "closed-script-capability-evidence-record", "worker-domain-teardown",
    } or len(mandatory or []) != 11:
        raise ValidationFailure("mandatory script control inventory is not exact")

    inventory = vector.get("native_control_inventory")
    if not isinstance(inventory, dict) or (
        inventory.get("version") != SCRIPT_NATIVE_CONTROL_INVENTORY_VERSION
        or inventory.get("exhaustive") is not True
        or inventory.get("platforms") != ["linux", "macos", "windows"]
        or inventory.get("availability_states") != ["available", "host-conditional", "unavailable"]
        or inventory.get("probe_timing") != "pre-worker-launch"
        or inventory.get("probe_scope") != "per-invocation"
    ):
        raise ValidationFailure("script native-control inventory header is not exact")
    native = named_cases(inventory.get("controls"), "script native controls")
    required_native = {
        "descendant-domain-termination", "active-process-count-limit", "aggregate-memory-limit",
        "per-file-size-limit", "inherited-handle-restriction", "descendant-exec-denial",
        "filesystem-write-confinement", "network-isolation-domain",
    }
    if set(native) != required_native:
        raise ValidationFailure("script native-control inventory is not exact")
    for name, control in native.items():
        platforms = control.get("platforms")
        if not isinstance(platforms, dict) or set(platforms) != {"linux", "macos", "windows"}:
            raise ValidationFailure(f"script native control {name} lacks exact platform cells")
    linux_pids = native["active-process-count-limit"]["platforms"]["linux"]
    if linux_pids != {
        "availability": "host-conditional",
        "mechanism": "delegated-cgroup-v2-pids.max",
        "unavailable_reason": None,
    }:
        raise ValidationFailure("Linux active-process limit is not delegated cgroup v2 pids.max")

    preflight = named_cases(vector.get("preflight_cases"), "script preflight")
    for name in ("mandatory-control-unavailable-at-install", "mandatory-control-unavailable-at-invocation"):
        case = preflight.get(name, {})
        if (
            case.get("expected_error") != "script_execution_control_unavailable"
            or case.get("worker_started") is not False
            or case.get("invocation_succeeds") is not False
        ):
            raise ValidationFailure(f"mandatory script preflight {name} does not reject before launch")
    linux_unavailable = preflight.get(
        "linux-pids-max-probe-unavailable-evidence-unavailable-invocation-succeeds", {}
    )
    if (
        linux_unavailable.get("control") != "active-process-count-limit"
        or linux_unavailable.get("inventory_availability") != "host-conditional"
        or linux_unavailable.get("probe_result") != "unavailable"
        or linux_unavailable.get("evidence_status") != "unavailable"
        or linux_unavailable.get("invocation_succeeds") is not True
        or linux_unavailable.get("expected_error") is not None
    ):
        raise ValidationFailure("unavailable Linux pids.max probe does not permit invocation")
    linux_available = preflight.get(
        "linux-pids-max-probe-available-evidence-applied-invocation-succeeds", {}
    )
    if (
        linux_available.get("probe_result") != "available"
        or linux_available.get("evidence_status") != "applied"
        or linux_available.get("invocation_succeeds") is not True
        or linux_available.get("expected_error") is not None
    ):
        raise ValidationFailure("available Linux pids.max probe is not applied")

    record = vector.get("capability_evidence_record")
    if not isinstance(record, dict) or (
        record.get("record_version") != SCRIPT_CAPABILITY_EVIDENCE_RECORD_VERSION
        or record.get("inventory_version") != SCRIPT_NATIVE_CONTROL_INVENTORY_VERSION
        or set(record.get("record_fields") or []) != {"controls", "execution_policy", "platform", "record_version"}
        or set(record.get("control_entry_fields") or []) != {"availability", "name", "probed_at", "status"}
        or record.get("entry_cardinality") != "exactly-one-per-inventory-control"
        or record.get("record_cardinality") != "exactly-one-per-invocation"
        or record.get("probe_timings") != ["pre-worker-launch"]
        or record.get("result_only") is not True
        or record.get("excluded_from") != [
            "cache-key", "command-stderr", "command-stdout", "conformance-claim",
            "install-marker", "receipt",
        ]
    ):
        raise ValidationFailure("script capability-evidence record is not closed")
    examples = record.get("examples")
    if not isinstance(examples, dict) or set(examples) != {"linux", "macos", "windows"}:
        raise ValidationFailure("script evidence lacks exact platform examples")
    for platform, example in examples.items():
        if (
            example.get("record_version") != SCRIPT_CAPABILITY_EVIDENCE_RECORD_VERSION
            or example.get("execution_policy") != SCRIPT_EXECUTION_POLICY
            or example.get("platform") != platform
        ):
            raise ValidationFailure(f"{platform} script evidence header is invalid")
        entries = named_cases(example.get("controls"), f"{platform} script evidence")
        if set(entries) != required_native:
            raise ValidationFailure(f"{platform} script evidence does not close the inventory")
        for name, entry in entries.items():
            if set(entry) != {"availability", "name", "probed_at", "status"}:
                raise ValidationFailure(f"{platform} script evidence entry {name} is open")
            if entry.get("probed_at") != "pre-worker-launch":
                raise ValidationFailure(f"{platform} script evidence entry {name} was probed late")
            availability = native[name]["platforms"][platform]["availability"]
            expected_status = "applied" if availability == "available" else "unavailable"
            if entry.get("availability") != availability or entry.get("status") != expected_status:
                raise ValidationFailure(f"{platform} script evidence contradicts {name}")
    linux_evidence = named_cases(examples["linux"]["controls"], "Linux script evidence")
    if linux_evidence["active-process-count-limit"].get("status") != "unavailable":
        raise ValidationFailure("Linux conditional pids.max example is not honestly unavailable")

    evidence = named_cases(vector.get("capability_evidence_cases"), "script evidence cases")
    invalid_evidence = {
        "available-control-reported-unavailable", "unavailable-control-reported-applied",
        "missing-control-entry", "duplicate-control-entry", "extra-control-entry",
        "unknown-record-version", "host-conditional-status-contradicts-probe",
        "cached-probe-result", "second-record-for-invocation", "foreign-build-record-version",
    }
    for name in invalid_evidence:
        case = evidence.get(name, {})
        if (
            case.get("record_valid") is not False
            or case.get("invocation_succeeds") is not False
            or case.get("expected_error") != "script_execution_capability_evidence_invalid"
        ):
            raise ValidationFailure(f"script evidence closure negative {name} is not rejected")
    for name in (
        "foreign-build-execution-policy", "deferred-script-guarantee-entry",
        "deferred-build-guarantee-entry",
    ):
        if evidence.get(name, {}).get("expected_error") != "script_execution_hardened_claim_forbidden":
            raise ValidationFailure(f"script evidence foreign/hardened negative {name} has wrong error")

    audit = named_cases(vector.get("audit_label_cases"), "script audit labels")
    for name in ("schema7-script", "schema8-declared-only-script"):
        if audit.get(name, {}).get("labels") != ["script-command-declared-only"]:
            raise ValidationFailure(f"legacy declared-only audit label is missing for {name}")
    if audit.get("schema8-enforced-script", {}).get("labels") != []:
        raise ValidationFailure("enforced script is labeled declared-only")


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


BUILD_DRIVER_EXPECTED = SUITE / "expected" / "build-driver"
BUILD_DRIVER_FIXTURE = SUITE / "fixtures" / "go-build-skill"
BUILD_SOURCE_DOMAIN_PREFIX = FROZEN_BUILD_SOURCE_ALGORITHM.encode("utf-8") + b"\x00"
TOOLCHAIN_DOMAIN_PREFIX = b"curator-go-toolchain-v1\x00"
BUILD_DRIVER_POSITIVE_CASES = {
    "schema-6-mixed-script-and-build-commands",
    "build-root-excluded-from-agent-context",
    "valid-standard-library-only-main",
    "valid-vendor-only-main-with-transitive-embed",
    "fixed-environment-and-five-direct-argv-forms",
    "portable-execution-policy-is-required-input",
    "protected-cache-hit",
    "compiler-free-dry-run-miss",
}
BUILD_DRIVER_BOUNDARIES = {
    "manifest",
    "filesystem",
    "module",
    "dependency-graph",
    "compiler-directive",
    "process",
    "toolchain",
    "cache",
    "context",
    "execution-policy",
}
BUILD_DRIVER_EXECUTION_POLICY_REJECTIONS = {
    "legacy-rc4-input-without-execution-policy",
    "reserved-hardened-execution-policy",
}
BUILD_SOURCE_CASES = {
    "fixture-exact-build-source",
    "domain-prefix-ordering-framing-empty-binary-and-root-marker",
    "mode-and-timestamp-are-non-inputs",
    "invalid-unicode-build-source-path",
    "duplicate-build-source-path",
    "build-source-symbolic-link",
    "build-source-special-file",
    "build-source-mutation-during-use",
    "legacy-nul-stream-structural-collision",
    "root-marker-bytes-are-build-input",
}
TOOLCHAIN_CASES = {
    "unsorted-directories-files-and-internal-link",
    "crlf-version-normalizes-to-lf-identity",
    "toolchain-mode-and-timestamp-are-non-inputs",
    "toolchain-version-missing-terminal-lf",
    "toolchain-version-multiple-terminal-newlines",
    "invalid-unicode-toolchain-path",
    "duplicate-toolchain-path",
    "escaping-toolchain-link",
    "absolute-toolchain-link",
    "dangling-toolchain-link",
    "selected-go-outside-goroot",
    "toolchain-tree-mutation-during-use",
}
MANAGER_COMPILED_DRY_RUN_CASES = {"compiled-cache-miss-is-read-only"}
MANAGER_COMPILED_LIFECYCLE_CASES = {
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


def frame_build_source(records: list[tuple[str, bytes]]) -> bytes:
    """Reproduce the curator-build-source-v1 length-framed preimage."""
    payload = bytearray(BUILD_SOURCE_DOMAIN_PREFIX)
    for path, content in sorted(records, key=lambda item: item[0]):
        name = path.encode("utf-8")
        payload += b"F" + len(name).to_bytes(8, "big") + name
        payload += len(content).to_bytes(8, "big") + content
    return bytes(payload)


def read_expected_identity(name: str) -> str:
    return (BUILD_DRIVER_EXPECTED / name).read_text(encoding="utf-8").strip()


def validate_build_driver_vectors() -> None:
    """Check the go-v1 build-driver golden suite against its own bytes.

    Every published identity is recomputed here from the fixture on disk and
    from the vector's own stored inputs, so a golden artifact cannot drift
    away from the candidate it claims to describe.
    """
    vector = load_json(SUITE / "vectors" / "build-drivers.json")
    if vector.get("driver") != "go-v1" or vector.get("schema_version") != 1:
        raise ValidationFailure("build-driver vector does not identify go-v1 schema 1")

    validate_fixed_environment_cases(vector)

    # The physical fixture is the build-source oracle.
    fixture = vector["fixture"]
    if fixture.get("root") != "fixtures/go-build-skill":
        raise ValidationFailure("build-driver fixture root is not the published path")
    on_disk = sorted(
        path.relative_to(BUILD_DRIVER_FIXTURE).as_posix()
        for path in BUILD_DRIVER_FIXTURE.rglob("*")
        if path.is_file()
    )
    if fixture.get("snapshot_files") != on_disk:
        raise ValidationFailure("build-driver fixture snapshot inventory does not match the fixture")
    preimage = frame_build_source(
        [(name, (BUILD_DRIVER_FIXTURE / name).read_bytes()) for name in on_disk]
    )
    digest = "sha256:" + hashlib.sha256(preimage).hexdigest()
    if fixture["build_source"].get("algorithm") != FROZEN_BUILD_SOURCE_ALGORITHM:
        raise ValidationFailure("build-driver fixture does not name the frozen build-source algorithm")
    if decode_base64(fixture["build_source"]["preimage_base64"], "fixture preimage") != preimage:
        raise ValidationFailure("build-driver fixture preimage does not frame the fixture bytes")
    if (BUILD_DRIVER_EXPECTED / "build-source.preimage.bin").read_bytes() != preimage:
        raise ValidationFailure("expected build-source preimage does not frame the fixture bytes")
    if fixture["build_source"]["content_sha256"] != digest or read_expected_identity("build-source-sha256.txt") != digest:
        raise ValidationFailure("build-driver build-source identity does not match its own preimage")
    context = fixture["expected_context_files"]
    require_sorted_unique(context, "build-driver expected context files")
    if load_json(BUILD_DRIVER_EXPECTED / "context_files.json") != context:
        raise ValidationFailure("expected build-driver context files disagree with the vector")
    if any(name in context for name in fixture["excluded_context_files"]):
        raise ValidationFailure("a declared build root is still visible in the agent context")

    # The portable identity is byte-exact and derives from its own input.
    identity = vector["portable_identity"]
    if identity.get("execution_policy") != PORTABLE_EXECUTION_POLICY:
        raise ValidationFailure("build-driver portable identity names the wrong execution policy")
    build_input = identity["build_input"]
    if build_input["policy"].get("execution_policy") != PORTABLE_EXECUTION_POLICY:
        raise ValidationFailure("build-driver portable input does not require the execution policy")
    input_bytes = ccj1_bytes(build_input)
    cache_key = "sha256:" + hashlib.sha256(input_bytes).hexdigest()
    if identity["cache_key"] != cache_key or identity["build_input_ccj_utf8"] != input_bytes.decode("utf-8"):
        raise ValidationFailure("build-driver cache key is not SHA-256(CCJ-1(input))")
    if (BUILD_DRIVER_EXPECTED / "build-input.ccj.json").read_bytes() != input_bytes:
        raise ValidationFailure("expected build input does not carry exact CCJ-1 bytes")
    if read_expected_identity("cache-key.txt") != cache_key:
        raise ValidationFailure("expected cache key disagrees with the vector")

    receipt = identity["stored_receipt"]
    if receipt.get("cache_key") != cache_key or receipt.get("input") != build_input:
        raise ValidationFailure("stored receipt does not bind the portable input and key")
    receipt_bytes = ccj1_bytes(receipt)
    receipt_hash = "sha256:" + hashlib.sha256(receipt_bytes).hexdigest()
    if identity["receipt_sha256"] != receipt_hash or identity["stored_receipt_ccj_utf8"] != receipt_bytes.decode("utf-8"):
        raise ValidationFailure("stored receipt hash is not SHA-256 of its exact canonical bytes")
    stored = (BUILD_DRIVER_EXPECTED / "receipt.ccj.json").read_bytes()
    if stored != receipt_bytes or stored.endswith(b"\n"):
        raise ValidationFailure("expected receipt is not exact canonical JSON without a terminal newline")
    if read_expected_identity("receipt-sha256.txt") != receipt_hash:
        raise ValidationFailure("expected receipt hash disagrees with the vector")
    marker = load_json(BUILD_DRIVER_EXPECTED / "marker.json")
    record = marker["builds"]["golden-tool"]
    if (
        marker != identity["marker"]
        or record["cache_key"] != cache_key
        or record["receipt_sha256"] != receipt_hash
        or record["artifact_sha256"] != receipt["artifact"]["sha256"]
    ):
        raise ValidationFailure("expected build marker does not bind the published build identity")

    validate_build_driver_cache_identity(vector, build_input, cache_key)
    validate_build_driver_cases(vector, cache_key, receipt_hash)


def validate_fixed_environment_cases(vector: Any) -> None:
    """Require one exact closed-environment realization per candidate host."""
    if not isinstance(vector, dict):
        raise ValidationFailure("build-driver vector is not an object")
    cases = named_cases(vector.get("fixed_environment_cases"), "fixed environment")
    expected_targets = {
        "darwin-arm64": ("darwin", "arm64", "GOARM64", "v8.0"),
        "linux-amd64": ("linux", "amd64", "GOAMD64", "v1"),
        "windows-amd64": ("windows", "amd64", "GOAMD64", "v1"),
    }
    if set(cases) != set(expected_targets):
        raise ValidationFailure("fixed environment host coverage changed")
    for name, (goos, goarch, tuning, tuning_value) in expected_targets.items():
        case = cases[name]
        environment = case.get("environment")
        if (
            case.get("goos") != goos
            or case.get("goarch") != goarch
            or not isinstance(environment, dict)
            or environment.get("GOOS") != goos
            or environment.get("GOARCH") != goarch
            or environment.get(tuning) != tuning_value
        ):
            raise ValidationFailure(f"fixed environment case {name} has the wrong native target")
    if vector.get("fixed_environment") != cases["darwin-arm64"].get("environment"):
        raise ValidationFailure("legacy fixed environment is not the Darwin/arm64 realization")
    windows = cases["windows-amd64"]
    environment = windows["environment"]
    if any(
        key not in environment
        for key in ("APPDATA", "LOCALAPPDATA", "USERPROFILE", "TEMP", "TMP")
    ):
        raise ValidationFailure("Windows fixed environment omits private process variables")
    if windows.get("optional_variables") != ["SYSTEMROOT", "WINDIR"]:
        raise ValidationFailure("Windows fixed environment does not name its optional indispensable variables")


def validate_manager_lifecycle_vectors(manager: Any, build_drivers: Any) -> None:
    """Require the complete schema-6 compiled lifecycle surface.

    The lifecycle vector deliberately reuses the current portable go-v1
    identity. Keeping this check separate from manifest hashing prevents a
    self-consistent regeneration from silently certifying a dropped lifecycle
    group or a stale pre-execution-policy identity.
    """
    if not isinstance(manager, dict) or manager.get("schema_version") != 1:
        raise ValidationFailure("manager lifecycle vector is not schema 1")
    require_named_cases(
        manager.get("dry_run_cases"),
        "manager compiled dry run",
        MANAGER_COMPILED_DRY_RUN_CASES,
    )
    for field, required in MANAGER_COMPILED_LIFECYCLE_CASES.items():
        require_named_cases(manager.get(field), f"manager lifecycle {field}", required)

    if not isinstance(build_drivers, dict):
        raise ValidationFailure("compiled lifecycle build-driver vector is missing")
    fixture = manager.get("compiled_build_fixture")
    identity = build_drivers.get("portable_identity")
    if not isinstance(fixture, dict) or not isinstance(identity, dict):
        raise ValidationFailure("compiled lifecycle/build-driver identity is missing")
    if fixture.get("source_vector") != "build-drivers.json#/portable_identity":
        raise ValidationFailure("compiled lifecycle fixture has a stale source vector")
    if (
        fixture.get("execution_policy") != PORTABLE_EXECUTION_POLICY
        or identity.get("execution_policy") != PORTABLE_EXECUTION_POLICY
    ):
        raise ValidationFailure("compiled lifecycle does not name the portable execution policy")
    build_input = identity.get("build_input")
    if (
        not isinstance(build_input, dict)
        or not isinstance(build_input.get("policy"), dict)
        or build_input["policy"].get("execution_policy") != PORTABLE_EXECUTION_POLICY
    ):
        raise ValidationFailure("compiled lifecycle portable input omits its execution policy")
    for lifecycle_field, identity_field in {
        "execution_policy": "execution_policy",
        "build_input": "build_input",
        "cache_key": "cache_key",
        "stored_receipt": "stored_receipt",
        "receipt_sha256": "receipt_sha256",
        "artifact": "artifact",
    }.items():
        if fixture.get(lifecycle_field) != identity.get(identity_field):
            raise ValidationFailure(
                f"compiled lifecycle {lifecycle_field} differs from build-driver {identity_field}"
            )
    if fixture.get("logical_command") != build_input.get("command"):
        raise ValidationFailure("compiled lifecycle logical command differs from its build input")


def validate_build_driver_cache_identity(vector: Any, portable_input: Any, portable_key: str) -> None:
    """Prove the portable identity misses the two non-portable inputs.

    The reserved hardened profile and the pre-revision rc.4 shape each derive
    their own distinct key and are rejected by the real compiled receipt
    schema, so neither can be reached through the portable cache entry.
    """
    identity = vector["cache_identity"]
    if identity.get("aliases") is not False:
        raise ValidationFailure("build-driver cache identity claims an alias")
    expected_policies = {
        "portable": (PORTABLE_EXECUTION_POLICY, True),
        "reserved_hardened": (RESERVED_HARDENED_EXECUTION_POLICY, False),
        "legacy_rc4_without_execution_policy": (None, False),
    }
    registry, paths = schema_registry()
    validator = Draft202012Validator(load_json(paths["build-receipt-v1.schema.json"]), registry=registry)
    template = load_json(SUITE / "schema-cases" / "build-receipt-v1" / "valid.json")
    keys: dict[str, str] = {}
    for name, (policy, schema_valid) in expected_policies.items():
        entry = identity.get(name)
        if not isinstance(entry, dict):
            raise ValidationFailure(f"build-driver cache identity has no {name} entry")
        if entry.get("execution_policy") != policy or entry.get("schema_valid") is not schema_valid:
            raise ValidationFailure(f"build-driver cache identity misreports {name}")
        derived = ccj1_sha256(entry["input"])
        if entry.get("cache_key") != derived:
            raise ValidationFailure(f"{name} cache key is not SHA-256(CCJ-1(its own input))")
        if derived in keys:
            raise ValidationFailure(f"{name} aliases {keys[derived]}")
        keys[derived] = name
        candidate = dict(template)
        candidate["input"] = entry["input"]
        candidate["cache_key"] = derived
        rejected = bool(list(validator.iter_errors(candidate)))
        if rejected is schema_valid:
            raise ValidationFailure(f"{name} receipt schema verdict contradicts schema_valid={schema_valid}")
    if identity["portable"]["input"] != portable_input or identity["portable"]["cache_key"] != portable_key:
        raise ValidationFailure("build-driver cache identity does not publish the portable input")
    if identity["legacy_rc4_without_execution_policy"]["cache_key"] != LEGACY_RC4_GO_V1_CACHE_KEY:
        raise ValidationFailure("build-driver legacy entry is not the exact rc.4 candidate key")
    if identity["reserved_hardened"].get("hardened_profile_owner") != HARDENED_EXECUTION_OWNER:
        raise ValidationFailure("build-driver reserved hardened entry omits its deferred owner")


def validate_build_driver_cases(vector: Any, cache_key: str, receipt_hash: str) -> None:
    positive = named_cases(vector["positive_cases"], "build-driver positive")
    if set(positive) != BUILD_DRIVER_POSITIVE_CASES:
        raise ValidationFailure("build-driver positive coverage changed")
    if positive["portable-execution-policy-is-required-input"].get("execution_policy") != PORTABLE_EXECUTION_POLICY:
        raise ValidationFailure("the portable execution-policy positive does not name the policy")
    for name in ("protected-cache-hit", "compiler-free-dry-run-miss"):
        case = positive[name]
        if case.get("cache_key") != cache_key or case.get("source_aware_go_commands") != []:
            raise ValidationFailure(f"{name} does not reuse the portable identity without source-aware commands")
    if positive["protected-cache-hit"].get("receipt_sha256") != receipt_hash:
        raise ValidationFailure("the protected cache hit does not bind the published receipt hash")

    rejections = named_cases(vector["rejection_cases"], "build-driver rejection")
    if not BUILD_DRIVER_EXECUTION_POLICY_REJECTIONS <= set(rejections):
        raise ValidationFailure("the non-portable execution-policy negatives are not published")
    errors: set[str] = set()
    for name, case in rejections.items():
        boundary = case.get("boundary")
        if boundary not in BUILD_DRIVER_BOUNDARIES:
            raise ValidationFailure(f"rejection {name} names an unknown boundary {boundary!r}")
        expected = case.get("expected")
        if not isinstance(expected, dict) or expected.get("result") != "reject":
            raise ValidationFailure(f"rejection {name} has no reject outcome")
        if not expected.get("error") or expected.get("artifact_executed") is not False:
            raise ValidationFailure(f"rejection {name} lacks a named non-executing outcome")
        errors.add(expected["error"])
    if len(errors) < 40:
        raise ValidationFailure("build-driver rejection outcomes lost their named error classes")
    for name in BUILD_DRIVER_EXECUTION_POLICY_REJECTIONS:
        case = rejections[name]
        derived = ccj1_sha256(case["input"]["build_input"])
        if case["input"].get("derived_cache_key") != derived or derived == cache_key:
            raise ValidationFailure(f"{name} does not derive a distinct non-portable key")
        expected = case["expected"]
        if (
            expected.get("schema_valid") is not False
            or expected.get("aliases_portable_cache_key") is not False
            or expected.get("cache_lookup_performed") is not False
        ):
            raise ValidationFailure(f"{name} is not an explicit schema-invalid non-alias negative")

    forged = rejections["self-consistent-forged-receipt-outside-protected-state"]["candidate"]
    if forged["receipt_sha256"] != ccj1_sha256(forged["receipt"]):
        raise ValidationFailure("the forged-receipt regression is no longer internally self-consistent")
    if forged["receipt"]["cache_key"] != ccj1_sha256(forged["receipt"]["input"]):
        raise ValidationFailure("the forged receipt no longer binds its own input")

    build_source = named_cases(vector["build_source_cases"], "build-driver build-source")
    if set(build_source) != BUILD_SOURCE_CASES:
        raise ValidationFailure("build-source byte-edge coverage changed")
    edge = build_source["domain-prefix-ordering-framing-empty-binary-and-root-marker"]
    if decode_base64(edge["domain_prefix_base64"], "build-source domain prefix") != BUILD_SOURCE_DOMAIN_PREFIX:
        raise ValidationFailure("build-source edge case lost its domain prefix")
    edge_preimage = decode_base64(edge["preimage_base64"], "build-source edge preimage")
    if edge["content_sha256"] != "sha256:" + hashlib.sha256(edge_preimage).hexdigest():
        raise ValidationFailure("build-source edge digest does not match its own preimage")
    collision = build_source["legacy-nul-stream-structural-collision"]
    framed = collision["framed_content_sha256"]
    if collision.get("legacy_streams_equal") is not True or collision.get("framed_hashes_equal") is not False:
        raise ValidationFailure("the legacy NUL-stream regression no longer proves the collision")
    if len(framed) != 2 or framed[0] == framed[1]:
        raise ValidationFailure("length framing no longer separates the colliding legacy streams")

    toolchain = named_cases(vector["toolchain_cases"], "build-driver toolchain")
    if set(toolchain) != TOOLCHAIN_CASES:
        raise ValidationFailure("toolchain byte-edge coverage changed")
    exact = toolchain["unsorted-directories-files-and-internal-link"]
    preimage = decode_base64(exact["preimage_base64"], "toolchain preimage")
    if not preimage.startswith(TOOLCHAIN_DOMAIN_PREFIX):
        raise ValidationFailure("toolchain preimage lost its domain prefix")
    digest = "sha256:" + hashlib.sha256(preimage).hexdigest()
    if exact["content_sha256"] != digest or read_expected_identity("toolchain-sha256.txt") != digest:
        raise ValidationFailure("toolchain identity does not match its own preimage")
    if (BUILD_DRIVER_EXPECTED / "toolchain.preimage.bin").read_bytes() != preimage:
        raise ValidationFailure("expected toolchain preimage disagrees with the vector")
    crlf = toolchain["crlf-version-normalizes-to-lf-identity"]
    if crlf["content_sha256"] != digest or crlf["normalized_go_version"] != exact["normalized_go_version"]:
        raise ValidationFailure("a CRLF go version no longer normalizes to the LF toolchain identity")
    if decode_base64(crlf["go_version_stdout_base64"], "crlf go version") != exact["normalized_go_version"].encode("utf-8") + b"\r\n":
        raise ValidationFailure("the CRLF toolchain case does not carry CRLF stdout")


def validate_shared_fixture_markers(expected_root: Path | None = None) -> None:
    """Check the frozen legacy-read marker and the marker-v2 writer golden.

    A conforming manager reads marker schema 1 but writes marker schema 2 for
    every schema 1 through 6 installation mutation, so the shared fixture
    publishes both: `expected/marker.json` stays byte-frozen as the legacy-read
    evidence, and `expected/marker-v2.json` is the writer golden downstream
    implementations compare their own marker output against. The writer golden
    is required, so a suite that lost it fails here instead of silently
    dropping the writer assertion.
    """
    if expected_root is None:
        expected_root = SUITE / "expected"
    registry, paths = schema_registry()
    legacy_path = expected_root / "marker.json"
    writer_path = expected_root / "marker-v2.json"
    if not writer_path.is_file():
        raise ValidationFailure(
            f"{display_path(writer_path)} is missing; managers write marker schema 2 "
            "for every schema 1 through 6 installation mutation"
        )
    legacy_digest = hashlib.sha256(legacy_path.read_bytes()).hexdigest()
    if legacy_digest != FROZEN_MARKER_V1_SHA256:
        raise ValidationFailure(
            f"{display_path(legacy_path)} is frozen marker-v1 legacy-read evidence and changed bytes"
        )

    legacy = load_json(legacy_path)
    writer = load_json(writer_path)
    for path, marker, version in ((legacy_path, legacy, 1), (writer_path, writer, 2)):
        label = display_path(path)
        if marker.get("schema_version") != version:
            raise ValidationFailure(f"{label} does not carry marker schema {version}")
        schema_name = f"install-marker-v{version}.schema.json"
        errors = list(
            Draft202012Validator(load_json(paths[schema_name]), registry=registry).iter_errors(marker)
        )
        if errors:
            raise ValidationFailure(f"{label} violates {schema_name}: {errors[0].message}")
        for field in ("agents", "commands", "dependencies", "files", "runtime_roots", "requirers"):
            require_sorted_unique(marker[field], f"{label} {field}")
        require_sorted_unique(marker["activation"]["commands"], f"{label} activation.commands")
        if "locale" not in marker or marker["locale"] is not None:
            raise ValidationFailure(f"{label} must carry explicit locale: null")

    if writer.get("build_roots") != [] or writer.get("builds") != {}:
        raise ValidationFailure(
            "the golden skill activates no compiled command, so its writer marker "
            "must record empty build_roots and builds"
        )
    if "build_source" in writer:
        raise ValidationFailure("build_source is REQUIRED exactly when builds is non-empty")
    differing = {key for key in set(legacy) | set(writer) if legacy.get(key) != writer.get(key)}
    if differing != SHARED_FIXTURE_MARKER_V2_DELTA:
        raise ValidationFailure(
            f"{display_path(writer_path)} must restate the same golden installation as "
            f"{display_path(legacy_path)}, differing only in "
            f"{sorted(SHARED_FIXTURE_MARKER_V2_DELTA)}, not {sorted(differing)}"
        )


def validate_vector_semantics() -> None:
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
        {"project-upgrade", "global-upgrade", *MANAGER_COMPILED_DRY_RUN_CASES},
    )
    validate_manager_lifecycle_vectors(
        manager,
        load_json(SUITE / "vectors" / "build-drivers.json"),
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
            "schema8-script-worker",
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

    schema8 = named_cases(lifecycle["mixed_build_cases"], "external repository mixed builds")[
        "schema8-script-worker"
    ]
    marker_v4 = load_json(SUITE / "expected" / "install-marker-v4.json")
    if (
        schema8.get("manifest_schema") != 8
        or schema8.get("marker_version") != 4
        or schema8.get("expected_marker") != "expected/install-marker-v4.json"
        or marker_v4.get("schema_version") != 4
        or marker_v4.get("skill_schema_version") != 8
    ):
        raise ValidationFailure("schema-8 lifecycle does not bind to the marker-v4 golden")

    validate_go_host_execution_policy()
    validate_script_host_execution_policy()
    validate_local_go_receipt_oracles()
    validate_build_driver_vectors()

    qualification = load_json(SUITE / "vectors" / "conformance-claim-v3-qualification.json")
    if qualification.get("candidate_claims_emitted") != []:
        raise ValidationFailure("rc.5 candidate fabricates native platform claims")
    platforms = named_cases(qualification.get("platforms"), "claim-v3 platforms")
    if (
        platforms.get("linux", {}).get("status") != "excluded"
        or platforms["linux"].get("until_task") != "TASK-260728-1skseh"
    ):
        raise ValidationFailure("claim-v3 Linux exclusion is not bound to its later native task")


MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


MANAGER_CONFIG_SCHEMAS = {1: "manager-config-v1.schema.json", 2: "manager-config-v2.schema.json"}

# environments.md section 12.1 spells a nested knob as `a.<x>.b`; the schema
# carries the first segment as a property and the rest as its value shape.
# The entries below name the schema location of every default the table
# states as a literal, so that a default drifting on either side fails here.
MANAGER_CONFIG_KNOB_DEFAULT_PATHS = {
    "current_profile": ("$defs", "environments", "properties", "current_profile", "default"),
    "overlay_default_weight": ("$defs", "environments", "properties", "overlay_default_weight", "default"),
    "overlays_allowed": ("$defs", "environments", "properties", "overlays_allowed", "default"),
    "precedence.winner": ("$defs", "precedence", "properties", "winner", "default"),
    "precedence.placement": ("$defs", "precedence", "properties", "placement", "default"),
    "system_prompt_files.<profile>.pi": ("$defs", "systemPromptFiles", "properties", "pi", "default"),
    "targets.<target-id>.participation": ("$defs", "target", "properties", "participation", "default"),
    "targets.<target-id>.consented": ("$defs", "target", "properties", "consented", "default"),
    "xdg_seed_allowlist": ("$defs", "environments", "properties", "xdg_seed_allowlist", "default"),
    "passable_env_names": ("$defs", "environments", "properties", "passable_env_names", "default"),
    "backup_retention": ("$defs", "environments", "properties", "backup_retention", "default"),
    "require_current_profile": ("$defs", "environments", "properties", "require_current_profile", "default"),
}


# The knobs whose section 12.1 `Values` cell is a closed set of backticked
# literals, with the schema location of the enum that admits them. The two
# sets MUST be equal: a value the schema admits that the table does not
# state (a widened enum) fails here, as does a value the table states that
# the schema rejects.
MANAGER_CONFIG_KNOB_ENUM_PATHS = {
    "precedence.winner": ("$defs", "precedence", "properties", "winner", "enum"),
    "precedence.placement": ("$defs", "precedence", "properties", "placement", "enum"),
    "forms.<env-id>": ("$defs", "environments", "properties", "forms", "additionalProperties", "enum"),
    "system_prompt_files.<profile>.pi": ("$defs", "systemPromptFiles", "properties", "pi", "enum"),
    "targets.<target-id>.participation": ("$defs", "target", "properties", "participation", "enum"),
    "isolation.<profile>.<env-id>": (
        "$defs", "environments", "properties", "isolation", "additionalProperties", "additionalProperties", "enum"
    ),
    "in_place_mode.<env-id>": ("$defs", "environments", "properties", "in_place_mode", "additionalProperties", "enum"),
}

BACKTICKED = re.compile(r"`([^`]+)`")


def environments_knob_rows(text: str) -> dict[str, tuple[str, str]]:
    """Parse the environments.md section 12.1 knob table into knob -> (values, default)."""
    section = text.split("### 12.1 Machine configuration knobs", 1)
    if len(section) != 2:
        raise ValidationFailure("environments.md has no section 12.1 knob table")
    knobs: dict[str, tuple[str, str]] = {}
    for line in section[1].split("### 12.2", 1)[0].splitlines():
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            raise ValidationFailure(f"section 12.1 knob row has too few cells: {line}")
        knobs[cells[0].strip("`")] = (cells[1], cells[2])
    if not knobs:
        raise ValidationFailure("section 12.1 knob table is empty")
    return knobs


def environments_knob_table(text: str) -> dict[str, str]:
    """Parse the environments.md section 12.1 knob table into knob -> default."""
    return {knob: default for knob, (_values, default) in environments_knob_rows(text).items()}


def environments_knob_values(text: str) -> dict[str, list[str]]:
    """Parse the environments.md section 12.1 knob table into knob -> backticked values."""
    return {knob: BACKTICKED.findall(values) for knob, (values, _default) in environments_knob_rows(text).items()}


def manager_config_semantic_error(instance: Any) -> str | None:
    """The manager §1 registry rules a schema cannot state: an audit registry
    URL is https, and two registries never share one canonical identity."""
    registries = instance.get("audit_registries", []) if isinstance(instance, dict) else []
    canonical: set[str] = set()
    for registry in registries:
        if not isinstance(registry, dict) or not isinstance(registry.get("url"), str):
            continue
        parts = urllib.parse.urlsplit(registry["url"])
        if parts.scheme.lower() != "https":
            return f"audit registry {registry.get('name')} is not https"
        host = (parts.hostname or "").lower()
        if parts.port not in (None, 443):
            host = f"{host}:{parts.port}"
        identity = f"https://{host}{parts.path.rstrip('/')}"
        if identity in canonical:
            return f"audit registries share the canonical identity {identity}"
        canonical.add(identity)
    return None


def validate_manager_config_vectors(
    vector: Any = None, vector_v2: Any = None, schema: Any = None, environments_text: str | None = None
) -> None:
    """`vectors/manager-config.json` (schema 1) and `vectors/manager-config-v2.json`.

    The schema-1 family is byte-frozen because the pinned Go manager reads
    it and implements schema 1 only, so every case in it MUST carry
    `schema_version` 1. The v2 family carries the schema-2 cases (and the
    schema-1 rejection of the `environments` knob). Every vector is
    validated against the schema its `schema_version` selects and MUST agree
    with its `valid` flag; a valid vector that carries
    `expected.environments` MUST equal the schema-2 knob defaults with the
    input's knobs replacing them, so the defaults a reader fills are pinned
    by the vector and the schema together. The schema-2 `environments`
    property set and every literal default MUST match the environments.md
    section 12.1 table byte for byte.
    """
    registry, paths = schema_registry()
    if vector is None:
        vector = load_json(SUITE / "vectors" / "manager-config.json")
    if vector_v2 is None:
        vector_v2 = load_json(SUITE / "vectors" / "manager-config-v2.json")
    if schema is None:
        schema = load_json(paths[MANAGER_CONFIG_SCHEMAS[2]])
    if environments_text is None:
        environments_text = (ROOT / "protocol" / "environments.md").read_text(encoding="utf-8")

    environments = schema["$defs"]["environments"]
    if environments.get("additionalProperties") is not False:
        raise ValidationFailure("manager-config-v2 environments object is not closed")
    knobs = environments_knob_table(environments_text)
    table_names = {knob.split(".", 1)[0] for knob in knobs}
    schema_names = set(environments["properties"])
    if table_names != schema_names:
        raise ValidationFailure(
            "manager-config-v2 environments properties differ from section 12.1: "
            f"schema-only {sorted(schema_names - table_names)}, table-only {sorted(table_names - schema_names)}"
        )
    for knob, path in MANAGER_CONFIG_KNOB_DEFAULT_PATHS.items():
        if knob not in knobs:
            raise ValidationFailure(f"section 12.1 no longer states knob {knob}")
        stated = knobs[knob].strip("`")
        try:
            stated_value = json.loads(stated)
        except json.JSONDecodeError:
            stated_value = stated
        node: Any = schema
        for segment in path:
            if not isinstance(node, dict) or segment not in node:
                raise ValidationFailure(f"manager-config-v2 states no default for {knob}")
            node = node[segment]
        if node != stated_value:
            raise ValidationFailure(
                f"manager-config-v2 default for {knob} is {node!r}; section 12.1 states {stated_value!r}"
            )
    defaults = {name: prop["default"] for name, prop in environments["properties"].items() if "default" in prop}
    if set(defaults) != schema_names:
        raise ValidationFailure(
            f"manager-config-v2 knobs without a default: {sorted(schema_names - set(defaults))}"
        )
    values = environments_knob_values(environments_text)
    for knob, path in MANAGER_CONFIG_KNOB_ENUM_PATHS.items():
        if knob not in values:
            raise ValidationFailure(f"section 12.1 no longer states knob {knob}")
        stated_values = values[knob]
        if not stated_values or len(stated_values) != len(set(stated_values)):
            raise ValidationFailure(f"section 12.1 states no closed value set for {knob}")
        node = schema
        for segment in path:
            if not isinstance(node, dict) or segment not in node:
                raise ValidationFailure(f"manager-config-v2 states no enum for {knob}")
            node = node[segment]
        if not isinstance(node, list) or len(node) != len(set(map(str, node))):
            raise ValidationFailure(f"manager-config-v2 enum for {knob} is not a set of literals: {node!r}")
        if set(node) != set(stated_values):
            raise ValidationFailure(
                f"manager-config-v2 enum for {knob} is {sorted(node)}; section 12.1 states {sorted(stated_values)}"
            )

    families = {"manager-config.json": vector, "manager-config-v2.json": vector_v2}
    seen: set[str] = set()
    versions_seen: dict[str, set[int]] = {family: set() for family in families}
    for family, cases in families.items():
        if not isinstance(cases, list) or not cases:
            raise ValidationFailure(f"{family} is not a non-empty case list")
        for case in cases:
            name = case.get("name")
            if not isinstance(name, str) or name in seen:
                raise ValidationFailure(f"manager-config vector name missing or repeated: {name!r}")
            seen.add(name)
            instance = case.get("input")
            version = instance.get("schema_version") if isinstance(instance, dict) else None
            if version not in MANAGER_CONFIG_SCHEMAS:
                raise ValidationFailure(f"manager-config vector {name} names no known schema_version")
            versions_seen[family].add(version)
            case_schema = schema if version == 2 else load_json(paths[MANAGER_CONFIG_SCHEMAS[version]])
            errors = list(Draft202012Validator(case_schema, registry=registry).iter_errors(instance))
            semantic_error = manager_config_semantic_error(instance) if not errors else None
            actual = not errors and semantic_error is None
            if actual != bool(case.get("valid")):
                detail = "valid" if actual else (errors[0].message if errors else semantic_error)
                raise ValidationFailure(
                    f"manager-config vector {name}: expected valid={case.get('valid')}, got {detail}"
                )
            expected = case.get("expected", {})
            if not case.get("valid") or "environments" not in expected:
                continue
            effective = dict(defaults)
            for knob, value in instance.get("environments", {}).items():
                if knob == "precedence":
                    value = {**defaults["precedence"], **value}
                effective[knob] = value
            if expected["environments"] != effective:
                raise ValidationFailure(
                    f"manager-config vector {name}: expected.environments is not defaults plus input"
                )
    if versions_seen["manager-config.json"] != {1}:
        raise ValidationFailure(
            "manager-config.json is the byte-frozen schema-1 family; it carries schema versions "
            f"{sorted(versions_seen['manager-config.json'])}"
        )
    if 2 not in versions_seen["manager-config-v2.json"]:
        raise ValidationFailure("manager-config-v2.json carries no schema-2 case")


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


ASSURANCE_RELATIONAL_REJECTIONS = {
    "provider-id-mismatch",
    "provider-contract-mismatch",
    "provider-binary-mismatch",
    "capability-set-mismatch",
    "capability-receipt-mismatch",
    "nonce-mismatch",
    "operation-mismatch",
    "permit-mismatch",
    "build-input-mismatch",
    "artifact-mismatch",
    "capability-receipt-stale",
    "permit-expired",
    "checkpoint-chain-mismatch",
    "portable-fallback-attempt",
}


def validate_assurance_vectors(vector: Any = None) -> None:
    if vector is None:
        vector = load_json(SUITE / "vectors" / "assurance-modes.json")
    if vector.get("contract_version") != "assurance-modes-v1":
        raise ValidationFailure("assurance vector has the wrong contract identity")
    if vector.get("platforms") != ["linux", "macos", "windows"]:
        raise ValidationFailure("provider contract is not platform-neutral")
    policies = vector.get("policies")
    if not isinstance(policies, list) or len(policies) != 2:
        raise ValidationFailure("assurance policy set is not closed")
    by_mode = {item.get("mode"): item for item in policies if isinstance(item, dict)}
    if (
        by_mode.get("portable", {}).get("default") is not True
        or by_mode.get("portable", {}).get("provider_contract") is not None
        or by_mode.get("verified", {}).get("default") is not False
        or by_mode.get("verified", {}).get("provider_contract")
        != "host-execution-provider-v1"
    ):
        raise ValidationFailure("assurance defaults or provider binding are invalid")
    identities = vector.get("cache_identities")
    if not isinstance(identities, list) or len(identities) != 2:
        raise ValidationFailure("assurance cache identities are incomplete")
    keys: set[str] = set()
    for item in identities:
        expected = "sha256:" + hashlib.sha256(ccj1_bytes(item.get("input"))).hexdigest()
        if item.get("expected_key") != expected:
            raise ValidationFailure("assurance cache identity digest is stale")
        keys.add(expected)
    if len(keys) != 2:
        raise ValidationFailure("portable and verified cache identities alias")
    failures = vector.get("fail_closed_cases")
    if not isinstance(failures, list) or len(failures) < 8:
        raise ValidationFailure("assurance negative coverage is incomplete")
    for case in failures:
        if case.get("execution_started") is not False or case.get("fallback_mode") is not None:
            raise ValidationFailure(f"assurance case is not fail-closed: {case.get('name')}")
    record_ids = vector.get("record_identities")
    if not isinstance(record_ids, list) or len(record_ids) != len(set(record_ids)):
        raise ValidationFailure("assurance record identities alias")
    if vector.get("release_claims") != []:
        raise ValidationFailure("rc.9 fabricates a verified provider claim")
    flow = vector.get("valid_flow")
    baseline_error = assurance.validate_flow(flow)
    if baseline_error is not None:
        raise ValidationFailure(f"valid assurance flow rejected as {baseline_error}")
    relational_cases = named_cases(
        vector.get("relational_rejection_cases"), "assurance relational rejection"
    )
    if set(relational_cases) != ASSURANCE_RELATIONAL_REJECTIONS:
        raise ValidationFailure("assurance relational rejection coverage is not exact")
    for name, case in relational_cases.items():
        expected = case.get("expected")
        if not isinstance(expected, dict) or (
            expected.get("failure_stage") != "pre-execution"
            or expected.get("execution_started") is not False
            or expected.get("fallback_mode") is not None
            or not isinstance(expected.get("error"), str)
        ):
            raise ValidationFailure(f"assurance relational rejection is not fail-closed: {name}")
        try:
            candidate = assurance.apply_mutation(flow, case.get("mutation"))
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ValidationFailure(f"invalid assurance mutation {name}: {exc}") from exc
        actual = assurance.validate_flow(candidate)
        if actual != expected["error"]:
            raise ValidationFailure(
                f"assurance relational rejection {name}: got {actual!r}, want {expected['error']!r}"
            )


# The agent-environments revision-1 surfaces of protocol/environments.md
# under the Decision 0012 model. This is an independent implementation of the
# section 1.4 version and range grammar and the resolution algorithm, the
# section 1.3 lock hash, the section 5 emitted order, the
# curator-root-context-v2 generation header, part joining, chapter parts, the
# referenced layout, the managed opencode.json CCJ-1 bytes, the system-prompt
# output, the section 5.8 MCP bytes per adapter, the section 5.6 surface hash,
# and the section 9.1 detector classes, cross-checked byte-for-byte against
# the Go generator's expected files and vectors.
import functools

ENVIRONMENT_HEADER_MARKER = "curator-root-context-v2"
ENVIRONMENT_GENERATED_LINE = (
    "generated: Curator Protocol environments revision 1 "
    "(https://github.com/relux-works/curator-spec)"
)
ENVIRONMENT_NOTICE_LINE = (
    "notice: generated file; direct edits are unsupported and are detected as "
    "drift; update the source profile repository or its composed profiles instead"
)
ENVIRONMENT_ROOT_TARGETS = {
    "claude_code": "CLAUDE.md",
    "codex_cli": "AGENTS.md",
    "opencode": "AGENTS.md",
    "pi": "AGENTS.md",
}
ENVIRONMENT_MCP_TARGETS = {
    "claude_code": ".agent-context/mcp/claude_code.json",
    "codex_cli": "curator-mcp.config.toml",
    "opencode": ".agent-context/mcp/opencode.json",
}
ENVIRONMENT_HOME_VARIABLES = {
    "claude_code": "CLAUDE_CONFIG_DIR",
    "codex_cli": "CODEX_HOME",
    "opencode": "XDG_CONFIG_HOME",
    "pi": "PI_CODING_AGENT_DIR",
}
ENVIRONMENT_SYSTEM_PROMPT_CHANNELS = {
    "claude_code": [
        {"kind": "flag", "semantics": "append", "flag": "--append-system-prompt-file", "argument": "path"},
        {"kind": "flag", "semantics": "replace", "flag": "--system-prompt-file", "argument": "path"},
    ],
    "codex_cli": [{"kind": "config-key", "semantics": "replace", "key": "model_instructions_file"}],
    "opencode": [],
    "pi": [
        {"kind": "flag", "semantics": "append", "flag": "--append-system-prompt", "argument": "path"},
        {"kind": "file", "semantics": "append", "filename": "APPEND_SYSTEM.md"},
        {"kind": "file", "semantics": "replace", "filename": "SYSTEM.md"},
    ],
}
ENVIRONMENT_MCP_CHANNELS = {
    "claude_code": [{"kind": "flag", "flag": "--mcp-config", "argument": "path", "with": ["--strict-mcp-config"]}],
    "codex_cli": [{"kind": "flag", "flag": "-p", "argument": "name", "name": "curator-mcp"}],
    "opencode": [{"kind": "variable", "variable": "OPENCODE_CONFIG"}],
}
ENVIRONMENT_SYSTEM_PROMPT_PATH = ".agent-context/system-prompt.md"
ENVIRONMENT_WINNERS = {"higher-weight", "lower-weight"}
ENVIRONMENT_PLACEMENTS = {"winner-last", "winner-first"}
ENVIRONMENT_HEADER_CASES = {
    "single-root",
    "composed-overlays-default",
    "composed-winner-lower-placement-first",
    "local-state-pin",
}
ENVIRONMENT_MATERIALIZATION_CASES = {
    "monolithic-claude-code",
    "monolithic-codex-selector-excluded",
    "monolithic-composed-no-chapter",
    "monolithic-zero-modules",
    "monolithic-zero-modules-composed",
    "referenced-claude-code-composed",
    "referenced-opencode",
    "referenced-opencode-zero-modules",
    "no-context-directory",
    "system-prompt-composed",
    "system-prompt-none-applicable",
    "weights-winner-higher-placement-last",
    "weights-winner-lower-placement-last",
    "weights-winner-higher-placement-first",
    "weights-winner-lower-placement-first",
    "mcp-claude-code",
    "mcp-codex-cli",
    "mcp-opencode",
    "mcp-pi-none",
}


# ---------------------------------------------------------------------------
# Section 1.4: versions and ranges


_NUMERIC = re.compile(r"^(?:0|[1-9][0-9]*)$")
_PRERELEASE_PART = re.compile(r"^[0-9A-Za-z-]+$")


class RangeInvalid(Exception):
    pass


def semver_parse(text: str) -> tuple | None:
    """Parse a strict SemVer 2.0 version without build metadata."""
    if not isinstance(text, str):
        return None
    core, _, pre = text.partition("-")
    parts = core.split(".")
    if len(parts) != 3 or not all(_NUMERIC.match(part) for part in parts):
        return None
    prerelease: tuple[str, ...] = ()
    if "-" in text:
        if not pre:
            return None
        ids = pre.split(".")
        for part in ids:
            if not _PRERELEASE_PART.match(part):
                return None
            if part.isdigit() and len(part) > 1 and part[0] == "0":
                return None
        prerelease = tuple(ids)
    return (int(parts[0]), int(parts[1]), int(parts[2]), prerelease)


def semver_parse_tag(tag: str) -> tuple | None:
    if not isinstance(tag, str) or not tag.startswith("v"):
        return None
    return semver_parse(tag[1:])


def semver_text(version: tuple) -> str:
    text = f"{version[0]}.{version[1]}.{version[2]}"
    if version[3]:
        text += "-" + ".".join(version[3])
    return text


def _compare_prerelease(a: tuple[str, ...], b: tuple[str, ...]) -> int:
    if not a and not b:
        return 0
    if not a:
        return 1
    if not b:
        return -1
    for left, right in zip(a, b):
        ln, rn = left.isdigit(), right.isdigit()
        if ln and rn:
            if int(left) != int(right):
                return -1 if int(left) < int(right) else 1
        elif ln:
            return -1
        elif rn:
            return 1
        elif left != right:
            return -1 if left < right else 1
    if len(a) != len(b):
        return -1 if len(a) < len(b) else 1
    return 0


def semver_compare(a: tuple, b: tuple) -> int:
    for x, y in zip(a[:3], b[:3]):
        if x != y:
            return -1 if x < y else 1
    return _compare_prerelease(a[3], b[3])


_semver_key = functools.cmp_to_key(semver_compare)


def _parse_partial(text: str) -> tuple[list[int], list[bool], tuple[str, ...]]:
    if not text:
        raise RangeInvalid(text)
    core, _, pre = text.partition("-")
    parts = core.split(".")
    if len(parts) > 3:
        raise RangeInvalid(text)
    values, present = [0, 0, 0], [False, False, False]
    for index, part in enumerate(parts):
        if part in {"x", "X", "*"}:
            break
        if not _NUMERIC.match(part):
            raise RangeInvalid(text)
        values[index] = int(part)
        present[index] = True
    prerelease: tuple[str, ...] = ()
    if "-" in text:
        if not present[2] or not pre:
            raise RangeInvalid(text)
        parsed = semver_parse(f"{values[0]}.{values[1]}.{values[2]}-{pre}")
        if parsed is None:
            raise RangeInvalid(text)
        prerelease = parsed[3]
    return values, present, prerelease


def _lowest(major: int, minor: int, patch: int) -> tuple:
    return (major, minor, patch, ("0",))


def _desugar(primitive: str) -> list[tuple]:
    """Return comparators as (op, version) tuples; ("*", None) is the any comparator."""
    op = ""
    for candidate in (">=", "<=", ">", "<", "=", "^", "~"):
        if primitive.startswith(candidate):
            op = candidate
            primitive = primitive[len(candidate):]
            break
    values, present, prerelease = _parse_partial(primitive)
    M, m, p = values
    full = (M, m, p, prerelease)
    any_ = [("*", None)]
    if op in {"", "="}:
        if not present[0]:
            return any_
        if not present[1]:
            return [(">=", (M, 0, 0, ())), ("<", _lowest(M + 1, 0, 0))]
        if not present[2]:
            return [(">=", (M, m, 0, ())), ("<", _lowest(M, m + 1, 0))]
        return [("=", full)]
    if op == ">=":
        return any_ if not present[0] else [(">=", full)]
    if op == ">":
        if not present[0]:
            return [("<", _lowest(0, 0, 0))]
        if not present[1]:
            return [(">=", (M + 1, 0, 0, ()))]
        if not present[2]:
            return [(">=", (M, m + 1, 0, ()))]
        return [(">", full)]
    if op == "<":
        if not present[0]:
            return [("<", _lowest(0, 0, 0))]
        if not present[1]:
            return [("<", _lowest(M, 0, 0))]
        if not present[2]:
            return [("<", _lowest(M, m, 0))]
        return [("<", full)]
    if op == "<=":
        if not present[0]:
            return any_
        if not present[1]:
            return [("<", _lowest(M + 1, 0, 0))]
        if not present[2]:
            return [("<", _lowest(M, m + 1, 0))]
        return [("<=", full)]
    if op == "^":
        if not present[0]:
            return any_
        if not present[1]:
            return [(">=", (M, 0, 0, ())), ("<", _lowest(M + 1, 0, 0))]
        if not present[2]:
            if M == 0:
                return [(">=", (0, m, 0, ())), ("<", _lowest(0, m + 1, 0))]
            return [(">=", (M, m, 0, ())), ("<", _lowest(M + 1, 0, 0))]
        if M > 0:
            return [(">=", full), ("<", _lowest(M + 1, 0, 0))]
        if m > 0:
            return [(">=", full), ("<", _lowest(0, m + 1, 0))]
        return [(">=", full), ("<", _lowest(0, 0, p + 1))]
    if op == "~":
        if not present[0]:
            return any_
        if not present[1]:
            return [(">=", (M, 0, 0, ())), ("<", _lowest(M + 1, 0, 0))]
        if not present[2]:
            return [(">=", (M, m, 0, ())), ("<", _lowest(M, m + 1, 0))]
        return [(">=", full), ("<", _lowest(M, m + 1, 0))]
    raise RangeInvalid(primitive)


def range_parse(text: str) -> list[list[tuple]]:
    if not isinstance(text, str):
        raise RangeInvalid(text)
    if text == "latest":
        text = "*"
    sets = []
    for set_text in text.split("||"):
        set_text = set_text.strip()
        if not set_text:
            raise RangeInvalid(text)
        comparators: list[tuple] = []
        for primitive in set_text.split():
            comparators.extend(_desugar(primitive))
        sets.append(comparators)
    return sets


def comparator_text(comparator: tuple) -> str:
    op, version = comparator
    return "*" if op == "*" else op + semver_text(version)


def _comparator_matches(comparator: tuple, version: tuple) -> bool:
    op, bound = comparator
    if op == "*":
        return True
    cmp = semver_compare(version, bound)
    return {"=": cmp == 0, ">": cmp > 0, ">=": cmp >= 0, "<": cmp < 0, "<=": cmp <= 0}[op]


def range_satisfies(sets: list[list[tuple]], version: tuple) -> bool:
    for comparators in sets:
        if not all(_comparator_matches(c, version) for c in comparators):
            continue
        if not version[3]:
            return True
        if any(
            op != "*" and bound[3] and bound[:3] == version[:3]
            for op, bound in comparators
        ):
            return True
    return False


# ---------------------------------------------------------------------------
# Section 1.4: resolution


class ResolutionError(Exception):
    def __init__(self, diagnostic: str, detail: dict[str, Any]) -> None:
        super().__init__(diagnostic)
        self.diagnostic = diagnostic
        self.detail = detail


def _requirement_form(entry: dict[str, Any]) -> tuple[str, Any]:
    for form in ("range", "tag", "revision", "path"):
        if form in entry:
            return form, entry[form]
    raise ValidationFailure(f"requirement has no form: {entry}")


def resolve_closure(case_input: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Run the environments.md section 1.4 algorithm and section 6 weights."""
    install = case_input["install"]
    packages = case_input["packages"]
    overlays = case_input.get("overlays", [])
    default_overlay_weight = case_input.get("overlay_default_weight", 1000)
    root = install["name"]

    constraints: list[dict[str, Any]] = []
    selected: dict[str, dict[str, Any]] = {}
    ceiling: dict[str, tuple] = {}
    pending: set[str] = set()
    warnings: list[dict[str, Any]] = []

    def add(name: str, kind: str, requirer: str, requirer_of: str, form: str, value: Any, weight: Any = None, directory: Any = None, overlay: Any = None) -> None:
        constraints.append({
            "name": name, "kind": kind, "requirer": requirer, "requirer_of": requirer_of,
            "form": form, "value": value, "weight": weight, "directory": directory, "overlay": overlay,
        })
        pending.add(name)

    form, value = _requirement_form(install)
    add(root, "context", "machine", "", form, value, directory=install.get("directory"))
    seen = {root}
    for overlay in overlays:
        if overlay["name"] in seen:
            raise ResolutionError("environment_composition_invalid", {"name": overlay["name"]})
        seen.add(overlay["name"])
        form, value = _requirement_form(overlay)
        add(overlay["name"], "context", "machine", "", form, value, directory=overlay.get("directory"), overlay=overlay)

    def spelling(c: dict[str, Any]) -> str:
        return "path" if c["form"] == "path" else f"{c['form']} {c['value']}"

    def constraints_on(name: str) -> list[dict[str, Any]]:
        return [c for c in constraints if c["name"] == name]

    def drop_attributed(requirer: str) -> None:
        kept = []
        for c in constraints:
            if c["requirer"] == requirer:
                pending.add(c["name"])
            else:
                kept.append(c)
        constraints[:] = kept

    def conflict(name: str, cs: list[dict[str, Any]], candidates: list[str]) -> ResolutionError:
        return ResolutionError("context_range_conflict", {
            "name": name,
            "requirers": [{"requirer": c["requirer"], "constraint": spelling(c)} for c in cs],
            "candidates": candidates,
        })

    def label(name: str, version: tuple | None) -> str:
        return name if version is None else f"{name}@{semver_text(version)}"

    while pending:
        name = min(pending)
        pending.discard(name)
        cs = constraints_on(name)
        if not cs:
            current = selected.pop(name, None)
            if current is not None:
                drop_attributed(label(name, current["version"]))
            continue
        kind = cs[0]["kind"]
        path_decl = None
        exact: list[str] = []
        ranges = []
        for c in cs:
            if c["form"] == "path":
                path_decl = c["overlay"]
            elif c["form"] == "range":
                try:
                    ranges.append(range_parse(c["value"]))
                except RangeInvalid:
                    raise ResolutionError("profile_source_invalid", {"name": name, "range": c["value"]})
            elif c["form"] == "tag":
                tags = packages[name]["tags"]
                if c["value"] not in tags:
                    raise ResolutionError("profile_source_invalid", {"name": name, "tag": c["value"]})
                exact.append(tags[c["value"]])
            else:
                exact.append(c["value"])
        if path_decl is not None:
            manifest = path_decl["path"]["manifest"]
            nxt = {"kind": kind, "version": semver_parse(manifest["version"]), "commit": None, "state": path_decl["path"]["state_sha256"], "source": None, "directory": None, "manifest": manifest, "overlay": path_decl}
        elif exact:
            if any(commit != exact[0] for commit in exact[1:]):
                raise conflict(name, cs, [])
            package = packages[name]
            commit = exact[0]
            manifest = package["commits"].get(commit)
            version = None
            if kind == "skill":
                for tag, tag_commit in package["tags"].items():
                    if tag_commit != commit:
                        continue
                    parsed = semver_parse_tag(tag)
                    if parsed is not None and (version is None or semver_compare(parsed, version) > 0):
                        version = parsed
            else:
                version = semver_parse(manifest["version"]) if manifest else None
                if version is None:
                    raise ResolutionError("context_manifest_invalid", {"name": name})
            for parsed_range in ranges:
                if version is None or not range_satisfies(parsed_range, version):
                    raise conflict(name, cs, [] if version is None else [semver_text(version)])
            nxt = {"kind": kind, "version": version, "commit": commit, "state": None, "source": package["source"], "directory": cs[0]["directory"], "manifest": manifest, "overlay": None}
        else:
            package = packages[name]
            candidates = []
            for tag, commit in package["tags"].items():
                parsed = semver_parse_tag(tag)
                if parsed is not None:
                    candidates.append((parsed, commit, tag))
            candidates.sort(key=lambda item: _semver_key(item[0]))
            considered = [semver_text(item[0]) for item in candidates]
            chosen = None
            for parsed, commit, tag in reversed(candidates):
                if name in ceiling and semver_compare(parsed, ceiling[name]) > 0:
                    continue
                if all(range_satisfies(r, parsed) for r in ranges):
                    chosen = (parsed, commit, tag)
                    break
            if chosen is None:
                raise conflict(name, cs, considered)
            parsed, commit, tag = chosen
            manifest = package["commits"].get(commit)
            if kind != "skill" and (manifest is None or manifest.get("version") != semver_text(parsed)):
                raise ResolutionError("context_version_mismatch", {"name": name, "tag": tag, "manifest_version": "" if manifest is None else manifest.get("version", "")})
            nxt = {"kind": kind, "version": parsed, "commit": commit, "state": None, "source": package["source"], "directory": cs[0]["directory"], "manifest": manifest, "overlay": None}
        for c in cs:
            if c["overlay"] is not None:
                nxt["overlay"] = c["overlay"]
        current = selected.get(name)
        if current is not None:
            if current["commit"] == nxt["commit"] and current["state"] == nxt["state"]:
                continue
            drop_attributed(label(name, current["version"]))
        selected[name] = nxt
        if nxt["version"] is not None:
            ceiling[name] = nxt["version"]
        if nxt["manifest"] is not None:
            requirer = label(name, nxt["version"])
            for requirement in nxt["manifest"].get("requires", []):
                form, value = _requirement_form(requirement)
                add(requirement["name"], requirement["kind"], requirer, name, form, value, weight=requirement.get("weight"), directory=requirement.get("directory"))

    for c in constraints:
        sel = selected.get(c["name"])
        if sel is None:
            raise conflict(c["name"], constraints_on(c["name"]), [])
        if c["form"] == "range" and (sel["version"] is None or not range_satisfies(range_parse(c["value"]), sel["version"])):
            raise conflict(c["name"], constraints_on(c["name"]), [])

    root_sel = selected[root]
    root_weights = dict(root_sel["manifest"].get("weights", {}))
    root_map = dict(root_weights)
    names = sorted(selected)
    for name in names:
        sel = selected[name]
        if name != root and sel["kind"] == "context" and sel["manifest"] is not None and sel["manifest"].get("weights"):
            raise ResolutionError("context_weights_not_root", {"name": name})
    for c in constraints:
        if c["requirer_of"] == root and c["weight"] is not None:
            if c["name"] in root_weights:
                raise ResolutionError("context_weights_duplicate", {"name": c["name"]})
            root_map[c["name"]] = c["weight"]
    for key in sorted(root_weights):
        sel = selected.get(key)
        if sel is None or sel["kind"] != "context":
            raise ResolutionError("context_weight_unknown", {"name": key})
    weights: dict[str, int] = {}
    for name in names:
        sel = selected[name]
        if sel["kind"] != "context":
            weights[name] = 0
            continue
        weight = sel["manifest"].get("weight", 0) if sel["manifest"] is not None else 0
        edges = [c for c in constraints if c["name"] == name and c["weight"] is not None and c["requirer_of"] not in {"", root}]
        if edges:
            if any(edge["weight"] != edges[0]["weight"] for edge in edges[1:]):
                detail = {"name": name, "requirers": [{"requirer": edge["requirer"], "weight": edge["weight"]} for edge in edges]}
                if name not in root_map:
                    raise ResolutionError("context_weight_conflict", detail)
                detail["diagnostic"] = "context_weight_conflict"
                warnings.append(detail)
            else:
                weight = edges[0]["weight"]
        if name in root_map:
            weight = root_map[name]
        if sel["overlay"] is not None:
            weight = sel["overlay"].get("weight", default_overlay_weight)
        weights[name] = weight

    members = []
    for name in names:
        sel = selected[name]
        required_by = sorted({c["requirer_of"] for c in constraints if c["name"] == name and c["requirer_of"]})
        member: dict[str, Any] = {
            "kind": sel["kind"], "name": name, "weight": weights[name],
            "required_by": required_by, "overlay": sel["overlay"] is not None,
        }
        if sel["state"] is not None:
            member["state_sha256"] = sel["state"]
        else:
            member["source"] = sel["source"]
            member["commit"] = sel["commit"]
            if sel["directory"]:
                member["directory"] = sel["directory"]
        if sel["version"] is not None:
            member["version"] = semver_text(sel["version"])
        members.append(member)
    members.sort(key=lambda member: (member["kind"], member["name"]))
    return {"schema_version": 1, "root": root, "members": members}, warnings


def validate_context_version_vectors(vector: Any = None, suite_root: Path | None = None) -> None:
    """Recompute every section 1.3/1.4 expectation of context-versions.json."""
    root = SUITE if suite_root is None else Path(suite_root)
    if vector is None:
        vector = load_json(root / "vectors" / "context-versions.json")
    if (
        vector.get("schema_version") != 1
        or vector.get("protocol_version") != PROTOCOL_VERSION
        or vector.get("capability") != "agent-environments"
        or vector.get("capability_revision") != 1
    ):
        raise ValidationFailure("context-versions vector has the wrong capability identity")

    version_cases = vector.get("version_cases")
    if not isinstance(version_cases, list) or len(version_cases) < 10:
        raise ValidationFailure("context-versions version_cases must list the tag grammar cases")
    for case in version_cases:
        parsed = semver_parse_tag(case.get("tag"))
        if case.get("candidate") != (parsed is not None):
            raise ValidationFailure(f"version case {case.get('tag')!r} candidate flag is false")
        if parsed is not None and (
            case.get("version") != semver_text(parsed)
            or (case.get("major"), case.get("minor"), case.get("patch")) != parsed[:3]
            or case.get("prerelease") != list(parsed[3])
        ):
            raise ValidationFailure(f"version case {case.get('tag')!r} parse is stale")
    required_tags = {"v1.2.3+build.5", "1.2.3", "v01.2.3", "v2.0.0-rc.1"}
    if required_tags - {case.get("tag") for case in version_cases}:
        raise ValidationFailure("context-versions version_cases lost a required tag case")

    for case in named_cases(vector.get("ordering_cases"), "version ordering").values():
        parsed = [semver_parse(text) for text in case["input"]]
        if any(item is None for item in parsed):
            raise ValidationFailure(f"ordering case {case['name']} has an unparsable version")
        expected = [semver_text(item) for item in sorted(parsed, key=_semver_key)]
        if case.get("expected_ascending") != expected:
            raise ValidationFailure(f"ordering case {case['name']} is stale")

    range_cases = vector.get("range_cases")
    if not isinstance(range_cases, list):
        raise ValidationFailure("context-versions range_cases must be an array")
    seen_ranges = set()
    for case in range_cases:
        text = case.get("range")
        seen_ranges.add(text)
        try:
            sets = range_parse(text)
        except RangeInvalid:
            if case.get("valid") is not False or case.get("error") != "profile_source_invalid":
                raise ValidationFailure(f"range case {text!r} must be rejected as profile_source_invalid")
            continue
        if case.get("valid") is not True:
            raise ValidationFailure(f"range case {text!r} parses but is declared invalid")
        expected = [[comparator_text(c) for c in comparators] for comparators in sets]
        if case.get("comparator_sets") != expected:
            raise ValidationFailure(f"range case {text!r} comparator sets are stale: {case.get('comparator_sets')} != {expected}")
    coercion_table = {"1.2", "=1.2", ">=2.1", ">1.2", "<3", "<=1.2", "^1.2.3", "^0.2.3", "^0.0.3", "^1.4", "^0.1", "^0", "~1.2.3", "~1.2", "~1", "latest", "1.2.3 - 2.3.4", "v1.2.3"}
    if coercion_table - seen_ranges:
        raise ValidationFailure("context-versions range_cases lost a coercion-table or excluded-form row")

    satisfies_cases = vector.get("satisfies_cases")
    if not isinstance(satisfies_cases, list) or len(satisfies_cases) < 40:
        raise ValidationFailure("context-versions satisfies_cases must list the admission cases")
    for case in satisfies_cases:
        version = semver_parse(case.get("version"))
        if version is None:
            raise ValidationFailure(f"satisfies case version {case.get('version')!r} does not parse")
        if case.get("satisfies") != range_satisfies(range_parse(case.get("range")), version):
            raise ValidationFailure(f"satisfies case ({case.get('range')!r}, {case.get('version')!r}) is stale")
    required_pairs = {("^2.0.0-rc.0", "2.0.0-rc.1"), ("^2.0.0-rc.0", "2.1.0-rc.1"), ("*", "2.0.0-rc.1"), ("<3", "3.0.0-rc.1")}
    if required_pairs - {(case.get("range"), case.get("version")) for case in satisfies_cases}:
        raise ValidationFailure("context-versions satisfies_cases lost a prerelease rule case")

    lock_schema = load_json(SCHEMAS / "context-lock-v1.schema.json")
    registry, _ = schema_registry()
    lock_validator = Draft202012Validator(lock_schema, registry=registry)

    def check_lock(lock: Any, label: str) -> None:
        errors = list(lock_validator.iter_errors(lock))
        if errors:
            raise ValidationFailure(f"{label}: lock is not a valid context-lock-v1: {errors[0].message}")
        semantic = validate_wire_semantics("context-lock-v1.schema.json", lock)
        if semantic is not None:
            raise ValidationFailure(f"{label}: {semantic}")

    for case in named_cases(vector.get("lock_cases"), "lock canonicalization").values():
        lock = case.get("lock")
        check_lock(lock, f"lock case {case['name']}")
        payload = ccj1_bytes(lock)
        if case.get("ccj1_bytes") != payload.decode("utf-8") or case.get("byte_length") != len(payload):
            raise ValidationFailure(f"lock case {case['name']} CCJ-1 bytes are stale")
        if case.get("lock_sha256") != ccj1_sha256(lock):
            raise ValidationFailure(f"lock case {case['name']} lock_sha256 is stale")

    resolution_cases = named_cases(vector.get("resolution_cases"), "resolution")
    required_resolution = {
        "worked-example-default-policy", "range-conflict-empty-intersection", "downward-reselection",
        "prerelease-admission", "exact-constraint-unification", "or-highest-member", "latest-is-star",
        "version-mismatch", "weight-conflict", "weights-not-root", "overlay-joint-resolution-conflict",
    }
    if required_resolution - set(resolution_cases):
        raise ValidationFailure("context-versions resolution_cases lost a required case")
    for name, case in resolution_cases.items():
        expected = case.get("expected")
        if not isinstance(expected, dict):
            raise ValidationFailure(f"resolution case {name} has no expected outcome")
        try:
            lock, warnings = resolve_closure(case["input"])
        except ResolutionError as error:
            if expected.get("error") != error.diagnostic or expected.get("detail") != error.detail:
                raise ValidationFailure(
                    f"resolution case {name}: recomputed {error.diagnostic} {error.detail} does not match the expected outcome"
                )
            continue
        if "error" in expected:
            raise ValidationFailure(f"resolution case {name}: resolves but expects {expected['error']}")
        if expected.get("lock") != lock:
            raise ValidationFailure(f"resolution case {name}: expected lock is stale")
        if expected.get("warnings") != warnings:
            raise ValidationFailure(f"resolution case {name}: expected warnings are stale")
        check_lock(lock, f"resolution case {name}")
        if expected.get("lock_sha256") != ccj1_sha256(lock):
            raise ValidationFailure(f"resolution case {name}: lock_sha256 is stale")


# ---------------------------------------------------------------------------
# Section 5: materialization


def environment_module_error(content: Any) -> str | None:
    if not isinstance(content, str):
        return "module content must be UTF-8 text"
    if "\r" in content:
        return "module carries a non-LF line ending"
    if not content.endswith("\n") or content.endswith("\n\n"):
        return "module must end with exactly one trailing LF"
    return None


def environment_member_pin(member: dict[str, Any]) -> str:
    if "state_sha256" in member:
        return f"state sha256:{member['state_sha256']}"
    return f"commit {member['commit']}"


def environment_precedence(precedence: Any) -> tuple[str, str]:
    if (
        not isinstance(precedence, dict)
        or set(precedence) != {"winner", "placement"}
        or precedence["winner"] not in ENVIRONMENT_WINNERS
        or precedence["placement"] not in ENVIRONMENT_PLACEMENTS
    ):
        raise ValidationFailure(f"environment case declares an invalid precedence policy: {precedence!r}")
    return precedence["winner"], precedence["placement"]


def environment_emitted_order(lock: dict[str, Any], precedence: Any) -> list[dict[str, Any]]:
    """Section 5 emitted order: Kahn order over context members, stably sorted by weight."""
    winner, placement = environment_precedence(precedence)
    contexts = {member["name"]: member for member in lock["members"] if member["kind"] == "context"}
    requires: dict[str, set[str]] = {name: set() for name in contexts}
    for name, member in contexts.items():
        for requirer in member["required_by"]:
            if requirer in contexts:
                requires[requirer].add(name)
    emitted: list[str] = []
    while len(emitted) < len(contexts):
        ready = sorted(name for name in contexts if name not in emitted and requires[name] <= set(emitted))
        if not ready:
            raise ValidationFailure("environment lock has a context cycle")
        emitted.append(ready[0])
    ascending = (winner == "higher-weight") == (placement == "winner-last")
    ordered = [contexts[name] for name in emitted]
    return sorted(ordered, key=lambda member: member["weight"] if ascending else -member["weight"])


def environment_header_bytes(lock: dict[str, Any], precedence: Any) -> bytes:
    root = next(member for member in lock["members"] if member["name"] == lock["root"])
    lines = ["<!--", ENVIRONMENT_HEADER_MARKER, f"root: {root['name']} {root['version']} {environment_member_pin(root)}"]
    for member in environment_emitted_order(lock, precedence):
        line = f"member: {member['name']} {member['version']} {environment_member_pin(member)} weight {member['weight']}"
        if member["overlay"]:
            line += " overlay"
        lines.append(line)
    lines.append(f"precedence: winner={precedence['winner']} placement={precedence['placement']}")
    lines.append(f"lock: {ccj1_sha256(lock)}")
    lines.extend([ENVIRONMENT_GENERATED_LINE, ENVIRONMENT_NOTICE_LINE, "-->"])
    return ("\n".join(lines) + "\n").encode("utf-8")


def environment_applicable(package: dict[str, Any], environment: str, module_class: str) -> list[dict[str, Any]]:
    applicable = []
    for module in package.get("modules", []):
        if module.get("class", "root") != module_class:
            continue
        selector = module.get("environments")
        if selector is not None and environment not in selector:
            continue
        applicable.append(module)
    return applicable


def environment_mcp_set(case: dict[str, Any]) -> list[str]:
    environment = case["environment"]
    servers = case.get("mcp_servers", {})
    names = []
    for member in case["lock"]["members"]:
        if member["kind"] != "mcp":
            continue
        server = servers[member["name"]]
        selector = server.get("environments")
        if selector is not None and environment not in selector:
            continue
        names.append(member["name"])
    return sorted(names)


def toml_basic_string(value: str) -> str:
    out = ['"']
    for char in value:
        if char == '"':
            out.append('\\"')
        elif char == "\\":
            out.append("\\\\")
        elif char == "\n":
            out.append("\\n")
        elif char == "\r":
            out.append("\\r")
        elif char == "\t":
            out.append("\\t")
        elif ord(char) < 0x20 or ord(char) == 0x7F:
            out.append("\\u%04X" % ord(char))
        else:
            out.append(char)
    out.append('"')
    return "".join(out)


def environment_mcp_files(case: dict[str, Any]) -> dict[str, bytes]:
    environment = case["environment"]
    target = ENVIRONMENT_MCP_TARGETS.get(environment)
    names = environment_mcp_set(case)
    if target is None or not names:
        return {}
    servers = case["mcp_servers"]
    if environment == "claude_code":
        body = {}
        for name in names:
            server = servers[name]
            if server["transport"] == "stdio":
                body[name] = {"args": list(server["args"]), "command": server["command"], "type": "stdio"}
            else:
                body[name] = {"type": "http", "url": server["url"]}
        return {target: ccj1_bytes({"mcpServers": body}) + b"\n"}
    if environment == "opencode":
        body = {}
        for name in names:
            server = servers[name]
            if server["transport"] == "stdio":
                body[name] = {"command": [server["command"], *server["args"]], "type": "local"}
            else:
                body[name] = {"type": "remote", "url": server["url"]}
        return {target: ccj1_bytes({"mcp": body}) + b"\n"}
    lines = []
    for name in names:
        server = servers[name]
        lines.append(f"[mcp_servers.{name}]")
        if server["transport"] == "stdio":
            lines.append(f"command = {toml_basic_string(server['command'])}")
            lines.append("args = [" + ", ".join(toml_basic_string(arg) for arg in server["args"]) + "]")
        else:
            lines.append(f"url = {toml_basic_string(server['url'])}")
    return {target: ("\n".join(lines) + "\n").encode("utf-8")}


def environment_case_files(case: dict[str, Any]) -> dict[str, bytes]:
    name = case.get("name", "<unnamed>")
    lock = case["lock"]
    packages = case.get("packages", {})
    environment = case["environment"]
    precedence = case.get("precedence")
    if case["surface"] == "mcp":
        return environment_mcp_files(case)
    for package in packages.values():
        if not package.get("has_context"):
            continue
        for module in package.get("modules", []):
            error = environment_module_error(module.get("content"))
            if error is not None:
                raise ValidationFailure(f"environment case {name}: module {module.get('path')}: {error}")
    order = environment_emitted_order(lock, precedence)
    if case["surface"] == "system-prompt":
        parts = [
            module["content"]
            for member in order
            for module in environment_applicable(packages[member["name"]], environment, "system")
        ]
        if not parts:
            return {}
        return {ENVIRONMENT_SYSTEM_PROMPT_PATH: "\n".join(parts).encode("utf-8")}
    if not packages[lock["root"]].get("has_context"):
        return {}
    form = case["form"]
    header = environment_header_bytes(lock, precedence).decode("utf-8")
    files: dict[str, bytes] = {}
    instructions: list[str] = []
    parts = [header]
    for member in order:
        modules = environment_applicable(packages[member["name"]], environment, "root")
        if not modules:
            continue
        if not (environment == "opencode" and form == "referenced"):
            parts.append(f"---\n\n## Context: {member['name']} {member['version']}\n")
        for module in modules:
            if form == "monolithic":
                parts.append(module["content"])
            elif form == "referenced":
                reference = f".agent-context/modules/{member['name']}/{module['path']}"
                files[reference] = module["content"].encode("utf-8")
                instructions.append(reference)
                if environment != "opencode":
                    parts.append("@" + reference + "\n")
            else:
                raise ValidationFailure(f"environment case {name}: unsupported form {form!r}")
    target = ENVIRONMENT_ROOT_TARGETS[environment]
    if environment == "opencode" and form == "referenced":
        files[target] = header.encode("utf-8")
        files["opencode.json"] = ccj1_bytes({"instructions": instructions}) + b"\n"
    else:
        files[target] = "\n".join(parts).encode("utf-8")
    return files


def environment_content_hash(files: dict[str, bytes]) -> str:
    records = [path.encode("utf-8") + b"\x00" + files[path] for path in sorted(files)]
    return "sha256:" + hashlib.sha256(b"\x00".join(records)).hexdigest()


def validate_environment_vectors(vector: Any = None, suite_root: Path | None = None) -> None:
    root = SUITE if suite_root is None else Path(suite_root)
    if vector is None:
        vector = load_json(root / "vectors" / "environments.json")
    if (
        vector.get("schema_version") != 1
        or vector.get("protocol_version") != PROTOCOL_VERSION
        or vector.get("capability") != "agent-environments"
        or vector.get("capability_revision") != 1
        or vector.get("header_type_line") != ENVIRONMENT_HEADER_MARKER
    ):
        raise ValidationFailure("environments vector has the wrong capability identity")

    registry, _ = schema_registry()
    lock_validator = Draft202012Validator(load_json(SCHEMAS / "context-lock-v1.schema.json"), registry=registry)

    def check_lock(case: dict[str, Any], label: str) -> dict[str, Any]:
        lock = case.get("lock")
        errors = list(lock_validator.iter_errors(lock))
        if errors:
            raise ValidationFailure(f"{label}: lock is not a valid context-lock-v1: {errors[0].message}")
        semantic = validate_wire_semantics("context-lock-v1.schema.json", lock)
        if semantic is not None:
            raise ValidationFailure(f"{label}: {semantic}")
        if case.get("lock_sha256") != ccj1_sha256(lock):
            raise ValidationFailure(f"{label}: lock_sha256 is stale")
        expected_order = [member["name"] for member in environment_emitted_order(lock, case.get("precedence"))]
        if case.get("emitted_order") != expected_order:
            raise ValidationFailure(f"{label}: emitted_order is not the section 5 order {expected_order}")
        return lock

    header_cases = named_cases(vector.get("header_cases"), "environment header")
    if set(header_cases) != ENVIRONMENT_HEADER_CASES:
        raise ValidationFailure("environment header case inventory is not exact")
    for name, case in header_cases.items():
        lock = check_lock(case, f"environment header case {name}")
        expected = environment_header_bytes(lock, case.get("precedence"))
        declared = case.get("expected_bytes")
        if not isinstance(declared, str) or declared.encode("utf-8") != expected:
            raise ValidationFailure(f"environment header case {name} bytes are stale")
        if case.get("sha256") != "sha256:" + hashlib.sha256(expected).hexdigest():
            raise ValidationFailure(f"environment header case {name} digest is stale")
        if case.get("line_count") != expected.count(b"\n"):
            raise ValidationFailure(f"environment header case {name} line count is false")

    cases = named_cases(vector.get("materialization_cases"), "environment materialization")
    if set(cases) != ENVIRONMENT_MATERIALIZATION_CASES:
        raise ValidationFailure("environment materialization case inventory is not exact")
    referenced_expected: set[str] = set()
    for name, case in cases.items():
        check_lock(case, f"environment case {name}")
        if case["surface"] == "mcp":
            if case.get("mcp_set") != environment_mcp_set(case):
                raise ValidationFailure(f"environment case {name}: mcp_set is not the sorted applicable set")
            union = sorted({env for server_name in environment_mcp_set(case) for env in case["mcp_servers"][server_name].get("env_names", [])})
            if case.get("env_names") != union:
                raise ValidationFailure(f"environment case {name}: env_names is not the sorted union")
        files = environment_case_files(case)
        if case.get("file_written") is not bool(files):
            raise ValidationFailure(f"environment case {name}: file_written contradicts the section 5 rules")
        entries = case.get("files")
        if not isinstance(entries, list):
            raise ValidationFailure(f"environment case {name}: files must be an array")
        declared_paths = [entry.get("path") for entry in entries if isinstance(entry, dict)]
        if declared_paths != sorted(files):
            raise ValidationFailure(f"environment case {name}: file inventory mismatch")
        if not files:
            if "surface_sha256" in case:
                raise ValidationFailure(f"environment case {name}: an absent surface must not bind a hash")
            continue
        for entry in entries:
            path = entry["path"]
            payload = files[path]
            if entry.get("sha256") != "sha256:" + hashlib.sha256(payload).hexdigest():
                raise ValidationFailure(f"environment case {name}: digest for {path} is stale")
            if entry.get("bytes") != len(payload):
                raise ValidationFailure(f"environment case {name}: byte length for {path} is stale")
            expected_name = entry.get("expected")
            if not isinstance(expected_name, str) or not expected_name.startswith("expected/environments/"):
                raise ValidationFailure(f"environment case {name}: {path} has no expected byte file")
            referenced_expected.add(expected_name)
            expected_path = root / expected_name
            if not expected_path.is_file() or expected_path.read_bytes() != payload:
                raise ValidationFailure(f"environment case {name}: expected bytes for {path} differ")
            if payload.endswith(b"\n\n") or not payload.endswith(b"\n") or b"\r" in payload:
                raise ValidationFailure(f"environment case {name}: {path} violates the LF discipline")
        if case.get("surface_sha256") != environment_content_hash(files):
            raise ValidationFailure(f"environment case {name}: surface hash is not the core section 8 content hash")

    expected_root = root / "expected" / "environments"
    on_disk = {
        "expected/environments/" + path.relative_to(expected_root).as_posix()
        for path in expected_root.rglob("*")
        if path.is_file()
    } if expected_root.is_dir() else set()
    if on_disk != referenced_expected:
        raise ValidationFailure("expected/environments inventory does not match the vector's referenced files")


# ---------------------------------------------------------------------------
# Section 9.1: detector classes


DETECTOR_SCOPE_PREFIX = "context/"
DETECTOR_SCOPE_FILES = {"agent-context.json", "agent-mcp.json", "CONTEXT.md"}
DETECTOR_REQUIRED_CASES = {
    "secret-aws-access-key", "secret-private-key-block", "secret-bearer-token",
    "secret-in-mcp-args", "secret-in-mcp-url", "placeholder-example-key",
    "content-hash-not-secret", "waived-span-clears-only-itself",
    "pin-does-not-clear-finding", "system-module-present",
}


def detector_in_scope(path: str) -> bool:
    return path.startswith(DETECTOR_SCOPE_PREFIX) or path in DETECTOR_SCOPE_FILES


def detector_is_placeholder(body: str) -> bool:
    return body.endswith("EXAMPLE") or len(set(body)) <= 1


def detector_findings(pattern_classes: list[dict[str, Any]], pin: str, files: dict[str, str], waivers: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    compiled = [(item["pattern"], re.compile(item["regexp"]), item["group"], item.get("placeholder_prefix", "")) for item in pattern_classes]
    findings: list[dict[str, Any]] = []
    matched: set[int] = set()
    for path in sorted(files):
        if not detector_in_scope(path):
            continue
        content = files[path]
        file_findings = []
        for pattern_name, expression, group, prefix in compiled:
            for match in expression.finditer(content):
                start, end = match.span(group)
                body = content[start:end]
                if body.startswith(prefix):
                    body = body[len(prefix):]
                if detector_is_placeholder(body):
                    continue
                file_findings.append({"class": "context-secret-material", "pattern": pattern_name, "file": path, "span": [start, end], "severity": "blocking", "waived": False})
        file_findings.sort(key=lambda item: (item["span"][0], item["pattern"]))
        for finding in file_findings:
            for index, waiver in enumerate(waivers):
                if waiver["pin"] == pin and waiver["file"] == finding["file"] and list(waiver["span"]) == finding["span"]:
                    finding["waived"] = True
                    finding["waiver_reason"] = waiver["reason"]
                    matched.add(index)
            findings.append(finding)
    unmatched = [waiver for index, waiver in enumerate(waivers) if index not in matched]
    return findings, unmatched


def detector_system_module_warnings(files: dict[str, str]) -> list[dict[str, Any]]:
    if "agent-context.json" not in files:
        return []
    manifest = json.loads(files["agent-context.json"])
    warnings = []
    for module in manifest.get("context", {}).get("modules", []):
        if module.get("class") != "system":
            continue
        warnings.append({"class": "context-system-module-present", "package": manifest["name"], "path": module["path"], "selector": module.get("environments")})
    return warnings


def validate_context_detector_vectors(vector: Any = None, suite_root: Path | None = None) -> None:
    """Recompute every finding of context-detectors.json from the case bytes."""
    root = SUITE if suite_root is None else Path(suite_root)
    if vector is None:
        vector = load_json(root / "vectors" / "context-detectors.json")
    if (
        vector.get("schema_version") != 1
        or vector.get("protocol_version") != PROTOCOL_VERSION
        or vector.get("capability") != "agent-environments"
        or vector.get("capability_revision") != 1
    ):
        raise ValidationFailure("context-detectors vector has the wrong capability identity")
    pattern_classes = vector.get("pattern_classes")
    if not isinstance(pattern_classes, list) or {item.get("pattern") for item in pattern_classes} != {"aws-access-key-id", "private-key-block", "bearer-token"}:
        raise ValidationFailure("context-detectors pattern classes are not the closed set")
    cases = named_cases(vector.get("cases"), "context detector")
    if DETECTOR_REQUIRED_CASES - set(cases):
        raise ValidationFailure("context-detectors lost a required case")
    registry, _ = schema_registry()
    validators = {
        "context": Draft202012Validator(load_json(SCHEMAS / "agent-context-v1.schema.json"), registry=registry),
        "mcp": Draft202012Validator(load_json(SCHEMAS / "agent-mcp-v1.schema.json"), registry=registry),
    }
    for name, case in cases.items():
        files = case.get("files")
        if not isinstance(files, dict) or not all(isinstance(content, str) for content in files.values()):
            raise ValidationFailure(f"detector case {name}: files must map paths to text")
        kind = case.get("package_kind")
        manifest_name = "agent-context.json" if kind == "context" else "agent-mcp.json"
        if kind not in validators or manifest_name not in files:
            raise ValidationFailure(f"detector case {name}: package kind {kind!r} needs its manifest")
        manifest = json.loads(files[manifest_name])
        # A manifest that fails its schema would never reach the audit, so a
        # detector case over an invalid manifest asserts nothing.
        if list(validators[kind].iter_errors(manifest)):
            raise ValidationFailure(f"detector case {name}: {manifest_name} is not schema-valid")
        findings, unmatched = detector_findings(pattern_classes, case.get("pin"), files, case.get("waivers", []))
        expected = case.get("expected", {})
        if expected.get("findings") != findings:
            raise ValidationFailure(f"detector case {name}: expected findings are stale: {expected.get('findings')} != {findings}")
        warnings = []
        for finding in findings:
            if finding["waived"]:
                warnings.append({"diagnostic": "context_secret_waiver_applied", "file": finding["file"], "span": finding["span"], "reason": finding["waiver_reason"]})
        for waiver in unmatched:
            warnings.append({"diagnostic": "context_secret_waiver_unmatched", "pin": waiver["pin"], "file": waiver["file"], "span": list(waiver["span"])})
        warnings.extend(detector_system_module_warnings(files))
        if expected.get("warnings") != warnings:
            raise ValidationFailure(f"detector case {name}: expected warnings are stale")
        blocking = any(not finding["waived"] for finding in findings)
        if expected.get("installs") is not (not blocking):
            raise ValidationFailure(f"detector case {name}: installs contradicts the blocking findings")
        if case.get("content_hash_pin") and blocking is False and name == "pin-does-not-clear-finding":
            raise ValidationFailure("pin-does-not-clear-finding must keep its finding blocking")


SNAPSHOT_ACQUISITION_FILES = {
    ".gitattributes",
    "crlf.txt",
    "lf.txt",
    "mixed.txt",
    "subst.txt",
}


def validate_snapshot_acquisition_vectors(
    vector: Any = None, suite_root: Path | None = None
) -> None:
    """The environments.md section 1.2 byte-exactness vector.

    The expected hash is recomputed from the fixture bytes as checked out, so
    a checkout that normalized a line ending, a fixture edit without
    regeneration, or a hand-edited expected file all fail here.
    """
    root = SUITE if suite_root is None else Path(suite_root)
    if vector is None:
        vector = load_json(root / "vectors" / "snapshot-acquisition.json")
    if (
        vector.get("schema_version") != 1
        or vector.get("protocol_version") != PROTOCOL_VERSION
        or vector.get("capability") != "agent-environments"
        or vector.get("capability_revision") != 1
    ):
        raise ValidationFailure("snapshot-acquisition vector has the wrong capability identity")
    cases = named_cases(vector.get("cases"), "snapshot acquisition")
    if set(cases) != {"byte-exact-snapshot"}:
        raise ValidationFailure("snapshot acquisition case inventory is not exact")
    case = cases["byte-exact-snapshot"]
    if case.get("fixture") != "fixtures/byte-exact":
        raise ValidationFailure("byte-exact-snapshot names the wrong fixture")
    fixture = root / "fixtures" / "byte-exact"
    files = {
        path.relative_to(fixture).as_posix(): path.read_bytes()
        for path in fixture.rglob("*")
        if path.is_file()
    }
    if set(files) != SNAPSHOT_ACQUISITION_FILES:
        raise ValidationFailure(
            f"byte-exact fixture inventory is not exact: {sorted(files)}"
        )
    if files[".gitattributes"] != b"* text=auto\nsubst.txt export-subst\n":
        raise ValidationFailure("byte-exact .gitattributes bytes drifted")
    if b"\r" in files["lf.txt"]:
        raise ValidationFailure("byte-exact lf.txt carries a CR")
    if b"\r\n" not in files["crlf.txt"] or b"\n" in files["crlf.txt"].replace(b"\r\n", b""):
        raise ValidationFailure("byte-exact crlf.txt is not CRLF-only (normalized checkout?)")
    if b"\r\n" not in files["mixed.txt"] or b"\n" not in files["mixed.txt"].replace(b"\r\n", b""):
        raise ValidationFailure("byte-exact mixed.txt does not mix LF and CRLF (normalized checkout?)")
    if b"$Format:%H$" not in files["subst.txt"] or b"$Format:%h$" not in files["subst.txt"]:
        raise ValidationFailure("byte-exact subst.txt lost a literal $Format: placeholder")
    records = case.get("files")
    if not isinstance(records, list) or [r.get("path") for r in records] != sorted(files):
        raise ValidationFailure("byte-exact file records are not the sorted fixture inventory")
    for record in records:
        payload = files[record["path"]]
        if record.get("bytes") != len(payload) or record.get("sha256") != (
            "sha256:" + hashlib.sha256(payload).hexdigest()
        ):
            raise ValidationFailure(f"byte-exact file record {record['path']} is stale")
    expected = environment_content_hash(files)
    if case.get("expected_sha256") != expected:
        raise ValidationFailure("byte-exact-snapshot expected_sha256 is not the raw fixture content hash")
    if case.get("expected") != "expected/byte-exact-snapshot_sha256.txt":
        raise ValidationFailure("byte-exact-snapshot names the wrong expected file")
    if (root / case["expected"]).read_bytes() != expected.encode("ascii") + b"\n":
        raise ValidationFailure("expected/byte-exact-snapshot_sha256.txt is stale")
    contract = case.get("acquisition_contract")
    if not isinstance(contract, list) or not any("core.autocrlf=true" in step for step in contract) or not any("$Format:%H$" in step for step in contract):
        raise ValidationFailure("byte-exact-snapshot acquisition contract does not state the autocrlf and export-subst checks")


def main() -> int:
    checks = [
        validate_schemas,
        validate_repository_descriptor_identity,
        validate_manifest,
        validate_review_evidence,
        validate_shared_fixture_markers,
        validate_vector_semantics,
        validate_assurance_vectors,
        validate_environment_vectors,
        validate_context_version_vectors,
        validate_context_detector_vectors,
        validate_snapshot_acquisition_vectors,
        validate_manager_config_vectors,
        validate_local_links,
    ]
    try:
        for check in checks:
            check()
    except ValidationFailure as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        return 1
    print(f"validated {len(list(SCHEMAS.glob('*.json')))} schemas and {len(load_json(SUITE / 'manifest.json')['files'])} vector files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
