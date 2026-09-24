#!/usr/bin/env python3
"""Validate schemas, examples, vector manifest, and local Markdown links."""

from __future__ import annotations

import base64
import hashlib
import json
import re
import sys
import tomllib
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
_VALID_SCHEMA_DOCUMENTS: set[bytes] = set()
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
        schema_content = ccj1_bytes(document)
        if schema_content not in _VALID_SCHEMA_DOCUMENTS:
            try:
                Draft202012Validator.check_schema(document)
            except SchemaError as exc:
                raise ValidationFailure(f"{path}: invalid Draft 2020-12 schema: {exc.message}") from exc
            _VALID_SCHEMA_DOCUMENTS.add(schema_content)
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
    elif schema_name in (
        "agent-environment-marker-v1.schema.json",
        "agent-environment-marker-v2.schema.json",
    ):
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
    elif schema_name in ("launch-env-fragment-v1.schema.json", "launch-env-fragment-v2.schema.json"):
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

    if vector.get("hard_link_substitution_definition") != (
        "a hard link that makes resolution select an identity other than the "
        "platform-owned executable the manager intended"
    ):
        raise ValidationFailure("script hard-link substitution definition drifted")
    expected_identity_cases = {
        "windows-system32-exec-platform-owned-component-store-hardlinks": {
            "name": "windows-system32-exec-platform-owned-component-store-hardlinks",
            "platform": "windows", "use": "declared-exec-name",
            "resolution": "manager-default-windows-search-list",
            "system_root": "manager-captured",
            "target": "physically-below-canonical-systemroot-system32",
            "platform_owned": True,
            "additional_links": "systemroot-winsxs-component-store-only",
            "accepted": True,
            "reason": "bounded-windows-system32-winsxs-exception",
        },
        "windows-exec-outside-system32-hardlinks": {
            "name": "windows-exec-outside-system32-hardlinks",
            "platform": "windows", "use": "declared-exec-name",
            "resolution": "manager-default-windows-search-list",
            "system_root": "manager-captured",
            "target": "outside-canonical-systemroot-system32",
            "platform_owned": True,
            "additional_links": "systemroot-winsxs-component-store-only",
            "accepted": False, "reason": "target-not-below-system32",
        },
        "windows-exec-noncomponent-store-hardlinks": {
            "name": "windows-exec-noncomponent-store-hardlinks",
            "platform": "windows", "use": "declared-exec-name",
            "resolution": "manager-default-windows-search-list",
            "system_root": "manager-captured",
            "target": "physically-below-canonical-systemroot-system32",
            "platform_owned": True,
            "additional_links": "not-platform-component-store-or-unknown",
            "accepted": False, "reason": "extra-links-not-only-component-store",
        },
        "windows-exec-nondefault-search-hardlinks": {
            "name": "windows-exec-nondefault-search-hardlinks",
            "platform": "windows", "use": "declared-exec-name",
            "resolution": "caller-path-or-package-controlled",
            "system_root": "manager-captured",
            "target": "physically-below-canonical-systemroot-system32",
            "platform_owned": True,
            "additional_links": "systemroot-winsxs-component-store-only",
            "accepted": False, "reason": "not-manager-default-search",
        },
        "windows-exec-uncaptured-systemroot-hardlinks": {
            "name": "windows-exec-uncaptured-systemroot-hardlinks",
            "platform": "windows", "use": "declared-exec-name",
            "resolution": "manager-default-windows-search-list",
            "system_root": "caller-or-package-value",
            "target": "physically-below-system32-from-uncaptured-value",
            "platform_owned": True,
            "additional_links": "systemroot-winsxs-component-store-only",
            "accepted": False, "reason": "systemroot-not-manager-captured",
        },
        "windows-exec-unowned-file-hardlinks": {
            "name": "windows-exec-unowned-file-hardlinks",
            "platform": "windows", "use": "declared-exec-name",
            "resolution": "manager-default-windows-search-list",
            "system_root": "manager-captured",
            "target": "physically-below-canonical-systemroot-system32",
            "platform_owned": False,
            "additional_links": "systemroot-winsxs-component-store-only",
            "accepted": False, "reason": "target-not-platform-owned",
        },
        "windows-python3-interpreter-hardlinks": {
            "name": "windows-python3-interpreter-hardlinks",
            "platform": "windows", "use": "interpreter",
            "interpreter": "python3-v1",
            "resolution": "closed-interpreter-resolution", "system_root": None,
            "target": "resolved-interpreter-target", "platform_owned": True,
            "additional_links": "one-or-more-extra-hard-links",
            "accepted": False,
            "reason": "interpreter-hard-link-rejection-unchanged",
        },
        "windows-node-interpreter-hardlinks": {
            "name": "windows-node-interpreter-hardlinks",
            "platform": "windows", "use": "interpreter",
            "interpreter": "node-v1",
            "resolution": "closed-interpreter-resolution", "system_root": None,
            "target": "resolved-interpreter-target", "platform_owned": True,
            "additional_links": "one-or-more-extra-hard-links",
            "accepted": False,
            "reason": "interpreter-hard-link-rejection-unchanged",
        },
    }
    identity_cases = named_cases(vector.get("executable_identity_cases"), "script executable identity")
    if identity_cases != expected_identity_cases:
        raise ValidationFailure("script executable identity cases widen or drift from the hard-link bounds")

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


PAGE_BOUNDARY_DIAGNOSTICS = frozenset(
    {
        "registry_page_boundary_stale",
        "registry_page_boundary_mismatch",
        "registry_page_boundary_missing",
    }
)

PAGE_BOUNDARY_CASES = frozenset(
    {
        "fresh-boundary-advances-high-water",
        "equal-version-same-body-accepted",
        "equal-version-different-body-rejected",
        "below-high-water-rejected",
        "chain-boundary-mismatch-rejected",
        "missing-boundary-excluded",
        "bad-signature-rejected",
        "stale-and-mismatch-reports-mismatch",
        "higher-and-mismatch-never-advances",
    }
)

CHECKPOINT_DIAGNOSTICS = frozenset(
    {
        "restore_below_checkpoint",
        "restore_inconsistent_with_checkpoint",
        "checkpoint_signature_invalid",
    }
)

CHECKPOINT_NOT_CONFIGURED = "checkpoint_not_configured"

CHECKPOINT_CASES = frozenset(
    {
        "checkpoint-below-live-consistent",
        "checkpoint-equal-consistent",
        "checkpoint-equal-inconsistent",
        "live-below-checkpoint",
        "live-above-prefix-mismatch",
        "checkpoint-signature-invalid",
        "checkpoint-not-configured",
    }
)


def expected_page_boundary_verdict(case: dict[str, Any]) -> tuple[bool, str | None, bool]:
    """Recompute the R1 client verdict from the case inputs.

    Returns (accepted, diagnostic, high_water_advanced) following registry
    protocol section 9.3: presence and section 2 signature verification
    first (absent or failing reports `registry_page_boundary_missing` with
    no state change); then, for every page after the first, the chain
    comparison against the chain boundary (the first page's boundary) — a
    difference reports `registry_page_boundary_mismatch` with no state
    change, and a later page never advances or re-checks the high-water on
    its own; then, for the first page, the section 5 high-water comparison
    (below, or equal with a different body, reports
    `registry_page_boundary_stale` with no state change; equal with the
    same body is accepted with nothing persisted; higher is accepted with
    the high-water advanced). Only a first page that passes presence and
    signature verification and the high-water check changes rollback state;
    a rejected page leaves it untouched. Diagnostic precedence for a later
    page is `missing` over `mismatch`, and `stale` is reported only for a
    first page. In the vector shape, `chain_boundary_equal: false` on a
    present, signature-valid boundary denotes a later page differing from
    the chain boundary.
    """
    if not case.get("boundary_present") or not case.get("signature_valid"):
        return False, "registry_page_boundary_missing", False
    if not case.get("chain_boundary_equal"):
        return False, "registry_page_boundary_mismatch", False
    stored = case.get("stored_version")
    boundary = case.get("boundary_version")
    if (
        not isinstance(stored, int)
        or not isinstance(boundary, int)
        or isinstance(stored, bool)
        or isinstance(boundary, bool)
        or stored < 0
        or boundary < 0
    ):
        raise ValidationFailure(
            f"registry-client page boundary case {case.get('name')!r} needs "
            "non-negative integer stored and boundary versions"
        )
    if boundary < stored or (boundary == stored and not case.get("same_body")):
        return False, "registry_page_boundary_stale", False
    return True, None, boundary > stored


def validate_registry_page_boundary_vectors(client: Any = None, service: Any = None) -> None:
    """The R1/P1 records page-boundary vector gate.

    Each client case's accepted, diagnostic, high-water, and exclusion values
    are recomputed from its inputs, so a vector that admits a stale,
    mismatched, or missing boundary fails. The service half pins the
    boundary-on-every-page emission and the P1 cursor-boundary refusal.
    """
    if client is None:
        client = load_json(SUITE / "vectors" / "registry-client.json")
    if service is None:
        service = load_json(SUITE / "vectors" / "registry-service.json")
    require_named_cases(
        client.get("page_boundary_cases"),
        "registry-client page boundary",
        set(PAGE_BOUNDARY_CASES),
    )
    for case in client["page_boundary_cases"]:
        name = case.get("name")
        accepted, diagnostic, advanced = expected_page_boundary_verdict(case)
        if case.get("accepted") is not accepted:
            raise ValidationFailure(
                f"registry-client page boundary case {name!r} admits what "
                "section 9.3 must reject" if accepted is False else
                f"registry-client page boundary case {name!r} rejects what "
                "section 9.3 must accept"
            )
        if case.get("diagnostic") is not None and case.get("diagnostic") not in PAGE_BOUNDARY_DIAGNOSTICS:
            raise ValidationFailure(
                f"registry-client page boundary case {name!r} uses "
                f"non-closed diagnostic {case.get('diagnostic')!r}"
            )
        if case.get("diagnostic") != diagnostic:
            raise ValidationFailure(
                f"registry-client page boundary case {name!r} carries "
                f"{case.get('diagnostic')!r}, expected {diagnostic!r}"
            )
        if case.get("high_water_advanced") is not advanced:
            raise ValidationFailure(
                f"registry-client page boundary case {name!r} has the wrong "
                "high-water advance"
            )
        if case.get("registry_excluded") is not (not accepted):
            raise ValidationFailure(
                f"registry-client page boundary case {name!r} has the wrong "
                "registry exclusion"
            )
    pagination = service.get("pagination")
    if not isinstance(pagination, dict):
        raise ValidationFailure("registry-service pagination boundary is incomplete")
    if pagination.get("boundary_emitted_on_every_page") is not True:
        raise ValidationFailure("registry-service must emit the boundary on every page")
    if pagination.get("chain_boundary_byte_identical") is not True:
        raise ValidationFailure("registry-service cursor-chain boundaries must be byte-identical")
    require_named_cases(
        pagination.get("cursor_boundary_cases"),
        "registry-service cursor boundary",
        {"cursor-boundary-disagreement"},
    )
    for case in pagination["cursor_boundary_cases"]:
        if (
            case.get("status") != 404
            or case.get("error") != "invalid_cursor"
            or case.get("reevaluate_at_newer_boundary") is not False
        ):
            raise ValidationFailure(
                f"registry-service cursor boundary case {case.get('name')!r} must "
                "refuse with 404 invalid_cursor without re-evaluating"
            )


def expected_checkpoint_verdict(case: dict[str, Any]) -> tuple[bool, str | None, str | None]:
    """Recompute the R3/P2 startup checkpoint verdict from the case inputs.

    Returns (ready, diagnostic, posture) following registry-service profile
    section 6: without a configured checkpoint the service starts and records
    the `checkpoint_not_configured` posture; otherwise the checkpoint
    signature is verified first (a failure refuses with
    `checkpoint_signature_invalid` without comparison); then a live
    version below the checkpoint refuses with `restore_below_checkpoint`,
    an equal version with a different boundary body refuses with
    `restore_inconsistent_with_checkpoint`, and a live state above the
    checkpoint serves only when the live log reproduces the checkpoint
    boundary at its log size (head and Merkle root at that prefix),
    otherwise `restore_inconsistent_with_checkpoint`.
    """
    if case.get("checkpoint_configured") is not True:
        return True, None, CHECKPOINT_NOT_CONFIGURED
    if case.get("signature_valid") is not True:
        return False, "checkpoint_signature_invalid", None
    live = case.get("live_version")
    checkpoint = case.get("checkpoint_version")
    if (
        not isinstance(live, int)
        or not isinstance(checkpoint, int)
        or isinstance(live, bool)
        or isinstance(checkpoint, bool)
        or live < 0
        or checkpoint < 0
    ):
        raise ValidationFailure(
            f"registry-service checkpoint case {case.get('name')!r} needs "
            "non-negative integer live and checkpoint versions"
        )
    if live < checkpoint:
        return False, "restore_below_checkpoint", None
    if live == checkpoint:
        if case.get("same_boundary_body") is True:
            return True, None, None
        return False, "restore_inconsistent_with_checkpoint", None
    if case.get("prefix_reproduced") is True:
        return True, None, None
    return False, "restore_inconsistent_with_checkpoint", None


def require_checkpoint_scenario(case: dict[str, Any]) -> None:
    """Pin each required checkpoint case name to its mandatory scenario inputs.

    The verdict oracle recomputes ready, diagnostic, and posture from
    whatever inputs a case carries, so without this pin a negative case
    replaced by an internally consistent passing case of the same name
    would survive the gate. Each required name therefore asserts its
    discriminating input predicates (configured versus absent checkpoint,
    signature validity, the live-versus-checkpoint version relationship,
    equal-body versus different-body, prefix reproduced versus not)
    following profile section 6. Extra (non-required) names carry no
    scenario pin; the caller still verdict-checks them.
    """
    name = case.get("name")
    if name == "checkpoint-not-configured":
        if case.get("checkpoint_configured") is True:
            raise ValidationFailure(
                f"registry-service checkpoint case {name!r} must leave "
                "the checkpoint unconfigured"
            )
        return
    if name == "checkpoint-signature-invalid":
        if case.get("checkpoint_configured") is not True:
            raise ValidationFailure(
                f"registry-service checkpoint case {name!r} must configure "
                "a checkpoint"
            )
        if case.get("signature_valid") is True:
            raise ValidationFailure(
                f"registry-service checkpoint case {name!r} must carry "
                "an invalid checkpoint signature"
            )
        return
    if name not in (
        "checkpoint-below-live-consistent",
        "checkpoint-equal-consistent",
        "checkpoint-equal-inconsistent",
        "live-below-checkpoint",
        "live-above-prefix-mismatch",
    ):
        return
    if case.get("checkpoint_configured") is not True:
        raise ValidationFailure(
            f"registry-service checkpoint case {name!r} must configure "
            "a checkpoint"
        )
    if case.get("signature_valid") is not True:
        raise ValidationFailure(
            f"registry-service checkpoint case {name!r} must carry "
            "a valid checkpoint signature"
        )
    live = case.get("live_version")
    checkpoint = case.get("checkpoint_version")
    if (
        not isinstance(live, int)
        or not isinstance(checkpoint, int)
        or isinstance(live, bool)
        or isinstance(checkpoint, bool)
        or live < 0
        or checkpoint < 0
    ):
        raise ValidationFailure(
            f"registry-service checkpoint case {case.get('name')!r} needs "
            "non-negative integer live and checkpoint versions"
        )
    if name == "live-below-checkpoint":
        if not live < checkpoint:
            raise ValidationFailure(
                f"registry-service checkpoint case {name!r} must place "
                "the live version below the checkpoint version"
            )
    elif name in ("checkpoint-equal-consistent", "checkpoint-equal-inconsistent"):
        if live != checkpoint:
            raise ValidationFailure(
                f"registry-service checkpoint case {name!r} must hold "
                "the live version equal to the checkpoint version"
            )
        if (case.get("same_boundary_body") is True) == (
            name == "checkpoint-equal-inconsistent"
        ):
            raise ValidationFailure(
                f"registry-service checkpoint case {name!r} must carry "
                + (
                    "a different boundary body"
                    if name == "checkpoint-equal-inconsistent"
                    else "the same boundary body"
                )
            )
    elif not live > checkpoint:
        raise ValidationFailure(
            f"registry-service checkpoint case {name!r} must place "
            "the live version above the checkpoint version"
        )
    elif (case.get("prefix_reproduced") is True) == (
        name == "live-above-prefix-mismatch"
    ):
        raise ValidationFailure(
            f"registry-service checkpoint case {name!r} must "
            + (
                "fail to reproduce the checkpoint boundary at its log size"
                if name == "live-above-prefix-mismatch"
                else "reproduce the checkpoint boundary at its log size"
            )
        )


def validate_registry_checkpoint_vectors(service: Any = None) -> None:
    """The R3/P2 startup checkpoint comparison vector gate.

    Each checkpoint case's ready, diagnostic, and posture values are
    recomputed from its inputs, so a vector that admits a below-checkpoint
    restore, an inconsistent equal version, an unreproduced prefix, or a
    bad checkpoint signature fails. The not-configured case must record
    the `checkpoint_not_configured` posture instead of a diagnostic.
    Each required case name is additionally pinned to its mandatory
    scenario inputs, so a self-consistent replacement scenario under a
    required name fails as well.
    """
    if service is None:
        service = load_json(SUITE / "vectors" / "registry-service.json")
    require_named_cases(
        service.get("checkpoint_cases"),
        "registry-service checkpoint",
        set(CHECKPOINT_CASES),
    )
    for case in service["checkpoint_cases"]:
        name = case.get("name")
        require_checkpoint_scenario(case)
        ready, diagnostic, posture = expected_checkpoint_verdict(case)
        if case.get("ready") is not ready:
            raise ValidationFailure(
                f"registry-service checkpoint case {name!r} admits what "
                "section 6 must refuse" if ready is False else
                f"registry-service checkpoint case {name!r} refuses what "
                "section 6 must serve"
            )
        if case.get("diagnostic") is not None and case.get("diagnostic") not in CHECKPOINT_DIAGNOSTICS:
            raise ValidationFailure(
                f"registry-service checkpoint case {name!r} uses "
                f"non-closed diagnostic {case.get('diagnostic')!r}"
            )
        if case.get("diagnostic") != diagnostic:
            raise ValidationFailure(
                f"registry-service checkpoint case {name!r} carries "
                f"{case.get('diagnostic')!r}, expected {diagnostic!r}"
            )
        if case.get("posture") != posture:
            raise ValidationFailure(
                f"registry-service checkpoint case {name!r} carries "
                f"posture {case.get('posture')!r}, expected {posture!r}"
            )


BOOTSTRAP_DIAGNOSTICS = frozenset(
    {
        "registry_checkpoint_regression",
        "registry_view_divergence",
    }
)

BOOTSTRAP_POSTURE = "registry_bootstrap_tofu"

BOOTSTRAP_PHASES = frozenset({"bootstrap", "rebootstrap", "compare"})

BOOTSTRAP_POLICIES = frozenset({"advisory", "strict"})

BOOTSTRAP_SEVERITIES = frozenset({"warning", "error"})

BOOTSTRAP_CASES = frozenset(
    {
        "checkpoint-first-use-accepted",
        "checkpoint-first-network-below-tampered",
        "checkpoint-first-network-equal-different-tampered",
        "no-checkpoint-first-use-tofu",
        "checkpoint-signature-invalid-first-use",
        "rebootstrap-advance-accepted",
        "rebootstrap-equal-consistent-noop",
        "rebootstrap-regression-refused",
        "rebootstrap-equal-inconsistent-refused",
        "rebootstrap-signature-invalid-ignored",
        "divergence-detected-advisory",
        "divergence-detected-strict",
        "divergence-views-agree",
        "divergence-different-sizes-skipped",
        "divergence-single-registry-skipped",
    }
)


def bootstrap_version(case: dict[str, Any], field: str) -> int:
    value = case.get(field)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValidationFailure(
            f"registry-client bootstrap case {case.get('name')!r} needs "
            f"a non-negative integer {field}"
        )
    return value


def bootstrap_bool(case: dict[str, Any], field: str) -> bool:
    value = case.get(field)
    if not isinstance(value, bool):
        raise ValidationFailure(
            f"registry-client bootstrap case {case.get('name')!r} needs "
            f"a boolean {field}"
        )
    return value


def expected_bootstrap_verdict(
    case: dict[str, Any],
) -> tuple[bool, bool, str | None, str | None, str | None, bool, bool, bool, bool]:
    """Recompute the S2 bootstrap verdict from the case inputs.

    Returns (accepted, state_changed, diagnostic, posture, severity,
    compared, registry_excluded, resolution_changed, check_current)
    following registry protocol section 5 and section 5.1 and the
    manager profile section 10 status mapping. Every discriminating
    boolean input must be present with an exact boolean type — a
    missing, null, or mistyped input is refused, never read as false.
    The `bootstrap` arm (first use) verifies a configured checkpoint
    signature first — a failure refuses with no diagnostic and no
    state change, leaving the registry unavailable (and `--check`
    non-current) — and persists a verified checkpoint before any
    network response is accepted, so a tampered first network still
    reports a state change while the checkpoint-persisted row stays
    current; without a checkpoint the first network view fixes the
    high-water with the `registry_bootstrap_tofu` posture (a warning
    row that stays current). The `rebootstrap` arm (prior state
    present) verifies first as well — a bad signature is ignored with
    the state unchanged and the registry usable on the persisted row,
    which stays current — then refuses a checkpoint below the
    high-water, or equal with a different body, with
    `registry_checkpoint_regression` (an error row, `--check`
    non-current). The `compare` arm states the behavior of a client
    implementing section 5.1 detection: two or more enabled
    registries of one mirror group exposing the same log size are
    compared by Merkle root, a difference reports
    `registry_view_divergence` (warning under advisory, staying
    current; error under strict, `--check` non-current), and the
    verdict never changes resolution, never excludes a registry, and
    never blocks acceptance.
    """
    phase = case.get("phase")
    if phase == "compare":
        group = bootstrap_version(case, "group_size")
        policy = case.get("policy")
        if policy not in BOOTSTRAP_POLICIES:
            raise ValidationFailure(
                f"registry-client bootstrap case {case.get('name')!r} needs "
                "a closed registry policy"
            )
        same_size = bootstrap_bool(case, "same_log_size")
        roots_equal = bootstrap_bool(case, "roots_equal")
        compared = group >= 2 and same_size
        if compared and not roots_equal:
            severity = "error" if policy == "strict" else "warning"
            check_current = policy != "strict"
            return True, False, "registry_view_divergence", None, severity, True, False, False, check_current
        return True, False, None, None, None, compared, False, False, True
    if phase == "bootstrap":
        if case.get("prior_state") != "missing":
            raise ValidationFailure(
                f"registry-client bootstrap case {case.get('name')!r} must "
                "start from missing prior state"
            )
        configured = bootstrap_bool(case, "checkpoint_configured")
        if not configured:
            return True, True, None, BOOTSTRAP_POSTURE, "warning", False, False, False, True
        signature_valid = bootstrap_bool(case, "signature_valid")
        if not signature_valid:
            return False, False, None, None, None, False, True, False, False
        checkpoint = bootstrap_version(case, "checkpoint_version")
        first = bootstrap_version(case, "first_network_version")
        same_body = bootstrap_bool(case, "candidate_same_body")
        if first < checkpoint or (first == checkpoint and not same_body):
            return False, True, None, None, None, False, True, False, True
        return True, True, None, None, None, False, False, False, True
    if phase == "rebootstrap":
        if case.get("prior_state") != "present":
            raise ValidationFailure(
                f"registry-client bootstrap case {case.get('name')!r} must "
                "start from present prior state"
            )
        configured = bootstrap_bool(case, "checkpoint_configured")
        if not configured:
            raise ValidationFailure(
                f"registry-client bootstrap case {case.get('name')!r} must "
                "configure a checkpoint"
            )
        signature_valid = bootstrap_bool(case, "signature_valid")
        if not signature_valid:
            return False, False, None, None, None, False, False, False, True
        checkpoint = bootstrap_version(case, "checkpoint_version")
        stored = bootstrap_version(case, "stored_version")
        same_body = bootstrap_bool(case, "candidate_same_body")
        if checkpoint < stored or (checkpoint == stored and not same_body):
            return False, False, "registry_checkpoint_regression", None, "error", False, False, False, False
        if checkpoint == stored:
            return True, False, None, None, None, False, False, False, True
        return True, True, None, None, None, False, False, False, True
    raise ValidationFailure(
        f"registry-client bootstrap case {case.get('name')!r} needs "
        f"a closed phase, got {phase!r}"
    )


def require_bootstrap_scenario(case: dict[str, Any]) -> None:
    """Pin each required bootstrap case name to its mandatory scenario inputs.

    The verdict oracle recomputes every output from whatever inputs a case
    carries, so without this pin a negative case replaced by an internally
    consistent passing case of the same name would survive the gate. Each
    required name therefore asserts its discriminating input predicates
    (phase, configured versus absent checkpoint, signature validity,
    missing versus present prior state, the version relationship, equal
    body versus different body, group size, shared log size, root
    equality, and registry policy) following registry protocol section 5
    and section 5.1. Every discriminating boolean must be present with
    an exact boolean type and, where false is the discriminator, must be
    explicitly false — a missing, null, or mistyped input is refused,
    never accepted as the negative branch. Extra (non-required) names
    carry no scenario pin; the caller still verdict-checks them.
    """
    name = case.get("name")
    if name in (
        "checkpoint-first-use-accepted",
        "checkpoint-first-network-below-tampered",
        "checkpoint-first-network-equal-different-tampered",
        "no-checkpoint-first-use-tofu",
        "checkpoint-signature-invalid-first-use",
    ):
        if case.get("phase") != "bootstrap":
            raise ValidationFailure(
                f"registry-client bootstrap case {name!r} must run the bootstrap phase"
            )
        if case.get("prior_state") != "missing":
            raise ValidationFailure(
                f"registry-client bootstrap case {name!r} must start from missing prior state"
            )
        configured = bootstrap_bool(case, "checkpoint_configured")
        if name == "no-checkpoint-first-use-tofu":
            if configured:
                raise ValidationFailure(
                    f"registry-client bootstrap case {name!r} must leave "
                    "the checkpoint unconfigured"
                )
            return
        if not configured:
            raise ValidationFailure(
                f"registry-client bootstrap case {name!r} must configure a checkpoint"
            )
        signature_valid = bootstrap_bool(case, "signature_valid")
        if name == "checkpoint-signature-invalid-first-use":
            if signature_valid:
                raise ValidationFailure(
                    f"registry-client bootstrap case {name!r} must carry "
                    "an invalid checkpoint signature"
                )
            return
        if not signature_valid:
            raise ValidationFailure(
                f"registry-client bootstrap case {name!r} must carry a valid checkpoint signature"
            )
        checkpoint = bootstrap_version(case, "checkpoint_version")
        first = bootstrap_version(case, "first_network_version")
        same_body = bootstrap_bool(case, "candidate_same_body")
        if name == "checkpoint-first-use-accepted":
            if not first > checkpoint:
                raise ValidationFailure(
                    f"registry-client bootstrap case {name!r} must place "
                    "the first network version above the checkpoint version"
                )
        elif name == "checkpoint-first-network-below-tampered":
            if not first < checkpoint:
                raise ValidationFailure(
                    f"registry-client bootstrap case {name!r} must place "
                    "the first network version below the checkpoint version"
                )
        else:
            if first != checkpoint:
                raise ValidationFailure(
                    f"registry-client bootstrap case {name!r} must hold "
                    "the first network version equal to the checkpoint version"
                )
            if same_body:
                raise ValidationFailure(
                    f"registry-client bootstrap case {name!r} must carry a different body"
                )
        return
    if name in (
        "rebootstrap-advance-accepted",
        "rebootstrap-equal-consistent-noop",
        "rebootstrap-regression-refused",
        "rebootstrap-equal-inconsistent-refused",
        "rebootstrap-signature-invalid-ignored",
    ):
        if case.get("phase") != "rebootstrap":
            raise ValidationFailure(
                f"registry-client bootstrap case {name!r} must run the rebootstrap phase"
            )
        if case.get("prior_state") != "present":
            raise ValidationFailure(
                f"registry-client bootstrap case {name!r} must start from present prior state"
            )
        configured = bootstrap_bool(case, "checkpoint_configured")
        if not configured:
            raise ValidationFailure(
                f"registry-client bootstrap case {name!r} must configure a checkpoint"
            )
        signature_valid = bootstrap_bool(case, "signature_valid")
        if name == "rebootstrap-signature-invalid-ignored":
            if signature_valid:
                raise ValidationFailure(
                    f"registry-client bootstrap case {name!r} must carry "
                    "an invalid checkpoint signature"
                )
            return
        if not signature_valid:
            raise ValidationFailure(
                f"registry-client bootstrap case {name!r} must carry a valid checkpoint signature"
            )
        checkpoint = bootstrap_version(case, "checkpoint_version")
        stored = bootstrap_version(case, "stored_version")
        same_body = bootstrap_bool(case, "candidate_same_body")
        if name == "rebootstrap-regression-refused":
            if not checkpoint < stored:
                raise ValidationFailure(
                    f"registry-client bootstrap case {name!r} must place "
                    "the checkpoint version below the stored version"
                )
        elif name == "rebootstrap-advance-accepted":
            if not checkpoint > stored:
                raise ValidationFailure(
                    f"registry-client bootstrap case {name!r} must place "
                    "the checkpoint version above the stored version"
                )
        else:
            if checkpoint != stored:
                raise ValidationFailure(
                    f"registry-client bootstrap case {name!r} must hold "
                    "the checkpoint version equal to the stored version"
                )
            if same_body == (name == "rebootstrap-equal-inconsistent-refused"):
                raise ValidationFailure(
                    f"registry-client bootstrap case {name!r} must carry "
                    + (
                        "a different body"
                        if name == "rebootstrap-equal-inconsistent-refused"
                        else "the same body"
                    )
                )
        return
    if name in (
        "divergence-detected-advisory",
        "divergence-detected-strict",
        "divergence-views-agree",
        "divergence-different-sizes-skipped",
        "divergence-single-registry-skipped",
    ):
        if case.get("phase") != "compare":
            raise ValidationFailure(
                f"registry-client bootstrap case {name!r} must run the compare phase"
            )
        group = bootstrap_version(case, "group_size")
        same_size = bootstrap_bool(case, "same_log_size")
        roots_equal = bootstrap_bool(case, "roots_equal")
        if name == "divergence-single-registry-skipped":
            if group >= 2:
                raise ValidationFailure(
                    f"registry-client bootstrap case {name!r} must compare "
                    "fewer than two registries"
                )
            return
        if group < 2:
            raise ValidationFailure(
                f"registry-client bootstrap case {name!r} must compare "
                "two or more registries"
            )
        if name == "divergence-different-sizes-skipped":
            if same_size:
                raise ValidationFailure(
                    f"registry-client bootstrap case {name!r} must expose "
                    "different log sizes"
                )
            return
        if not same_size:
            raise ValidationFailure(
                f"registry-client bootstrap case {name!r} must expose the same log size"
            )
        if name == "divergence-views-agree":
            if not roots_equal:
                raise ValidationFailure(
                    f"registry-client bootstrap case {name!r} must carry equal roots"
                )
            return
        if roots_equal:
            raise ValidationFailure(
                f"registry-client bootstrap case {name!r} must carry different roots"
            )
        want_policy = "strict" if name == "divergence-detected-strict" else "advisory"
        if case.get("policy") != want_policy:
            raise ValidationFailure(
                f"registry-client bootstrap case {name!r} must run under {want_policy} policy"
            )


BOOTSTRAP_BEHAVIOR = {
    "checkpoint_object": "registry-snapshot-v1",
    "checkpoint_form": "path",
    "verified_before_network": True,
    "tofu_posture": "registry_bootstrap_tofu",
    "regression_diagnostic": "registry_checkpoint_regression",
    "first_fixation_source": "checkpoint-or-network-only",
}

BOOTSTRAP_DIVERGENCE_BEHAVIOR = {
    "compared_at": "same_log_size",
    "diagnostic": "registry_view_divergence",
    "resolution_changed": False,
    "quorum": False,
}


def validate_registry_bootstrap_vectors(client: Any = None, behavior: Any = None) -> None:
    """The S2 bootstrap checkpoint and view-divergence vector gate.

    Each bootstrap case's accepted, state-changed, diagnostic, posture,
    severity, compared, exclusion, resolution, and `--check` currency
    values are recomputed from its inputs, so a vector that admits a
    tampered first network, a regressing checkpoint, a bad checkpoint
    signature, a dropped TOFU posture, a downgraded divergence severity,
    a resolution-changing detection, or a mislabelled status row fails.
    Each required case name is additionally pinned to its mandatory
    scenario inputs, so a self-consistent replacement scenario under a
    required name fails as well. The registry-behavior bootstrap and
    divergence summaries are pinned to their exact S2 values, including
    the checkpoint-or-network-only first-fixation source: the cache
    never fixes first-use high-water.
    """
    if client is None:
        client = load_json(SUITE / "vectors" / "registry-client.json")
    require_named_cases(
        client.get("bootstrap_cases"),
        "registry-client bootstrap",
        set(BOOTSTRAP_CASES),
    )
    for case in client["bootstrap_cases"]:
        name = case.get("name")
        require_bootstrap_scenario(case)
        expected = expected_bootstrap_verdict(case)
        actual = (
            case.get("accepted"),
            case.get("state_changed"),
            case.get("diagnostic"),
            case.get("posture"),
            case.get("severity"),
            case.get("compared"),
            case.get("registry_excluded"),
            case.get("resolution_changed"),
            case.get("check_current"),
        )
        if actual != expected:
            fields = (
                "accepted",
                "state_changed",
                "diagnostic",
                "posture",
                "severity",
                "compared",
                "registry_excluded",
                "resolution_changed",
                "check_current",
            )
            mismatched = next(
                field
                for field, want, got in zip(fields, expected, actual)
                if want != got
            )
            raise ValidationFailure(
                f"registry-client bootstrap case {name!r} carries {mismatched} "
                f"{case.get(mismatched)!r}, expected {expected[fields.index(mismatched)]!r}"
            )
        if case.get("diagnostic") is not None and case.get("diagnostic") not in BOOTSTRAP_DIAGNOSTICS:
            raise ValidationFailure(
                f"registry-client bootstrap case {name!r} uses "
                f"non-closed diagnostic {case.get('diagnostic')!r}"
            )
        if case.get("posture") is not None and case.get("posture") != BOOTSTRAP_POSTURE:
            raise ValidationFailure(
                f"registry-client bootstrap case {name!r} uses "
                f"non-closed posture {case.get('posture')!r}"
            )
        if case.get("severity") is not None and case.get("severity") not in BOOTSTRAP_SEVERITIES:
            raise ValidationFailure(
                f"registry-client bootstrap case {name!r} uses "
                f"non-closed severity {case.get('severity')!r}"
            )
        if not isinstance(case.get("check_current"), bool):
            raise ValidationFailure(
                f"registry-client bootstrap case {name!r} needs "
                "a boolean check_current"
            )
    if behavior is None:
        behavior = load_json(SUITE / "vectors" / "registry-behavior.json")
    bootstrap_summary = behavior.get("bootstrap")
    if not isinstance(bootstrap_summary, dict):
        raise ValidationFailure("registry-behavior bootstrap summary is incomplete")
    for key, want in BOOTSTRAP_BEHAVIOR.items():
        if bootstrap_summary.get(key) != want:
            raise ValidationFailure(
                f"registry-behavior bootstrap summary carries {key} "
                f"{bootstrap_summary.get(key)!r}, expected {want!r}"
            )
    divergence_summary = behavior.get("divergence")
    if not isinstance(divergence_summary, dict):
        raise ValidationFailure("registry-behavior divergence summary is incomplete")
    for key, want in BOOTSTRAP_DIVERGENCE_BEHAVIOR.items():
        if divergence_summary.get(key) != want:
            raise ValidationFailure(
                f"registry-behavior divergence summary carries {key} "
                f"{divergence_summary.get(key)!r}, expected {want!r}"
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
    "transitive_system_modules": ("$defs", "environments", "properties", "transitive_system_modules", "default"),
    "backup_retention": ("$defs", "environments", "properties", "backup_retention", "default"),
    "require_current_profile": ("$defs", "environments", "properties", "require_current_profile", "default"),
    "provider_directories": ("$defs", "environments", "properties", "provider_directories", "default"),
    "source_signers.<source>": ("$defs", "environments", "properties", "source_signers", "default"),
    "require_source_signers": ("$defs", "environments", "properties", "require_source_signers", "default"),
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
    "permissions.<profile>": (
        "$defs", "environments", "properties", "permissions", "additionalProperties", "enum"
    ),
    "transitive_system_modules": ("$defs", "environments", "properties", "transitive_system_modules", "enum"),
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


SYSTEM_CONFIG_SCHEMAS = {1: "system-config-v1.schema.json", 2: "system-config-v2.schema.json"}

# The section 12.2 knobs whose system-file grammar is narrower than their
# section 12.1 grammar: `isolation` is lockable only in the direction of
# `shared`, `transitive_system_modules` only in the direction of `error`,
# `require_source_signers` only in the direction of `true`, and
# `permissions` only in the direction of `native`, so the system schema
# admits that literal alone in each case.
SYSTEM_CONFIG_ISOLATION_ENUM_PATH = (
    "$defs", "environments", "properties", "isolation", "additionalProperties", "additionalProperties", "enum"
)
SYSTEM_CONFIG_TRANSITIVE_ENUM_PATH = (
    "$defs", "environments", "properties", "transitive_system_modules", "enum"
)
SYSTEM_CONFIG_REQUIRE_SIGNERS_ENUM_PATH = (
    "$defs", "environments", "properties", "require_source_signers", "enum"
)
SYSTEM_CONFIG_PERMISSIONS_ENUM_PATH = (
    "$defs", "environments", "properties", "permissions", "additionalProperties", "enum"
)
SYSTEM_CONFIG_POSTURE_ENUM_PATH = ("properties", "security_posture", "enum")


def environments_lockable_keys(text: str) -> list[str]:
    """Parse the environments.md section 12.2 sentence that extends the
    manager section 1 `locked` set into its ordered key list."""
    section = text.split("### 12.2 Lockable knobs", 1)
    if len(section) != 2:
        raise ValidationFailure("environments.md has no section 12.2 lockable-knob text")
    marker = "by exactly these keys under `environments`:"
    sentence = section[1].split("## 13", 1)[0]
    if marker not in sentence:
        raise ValidationFailure("section 12.2 no longer enumerates the lockable keys")
    sentence = sentence.split(marker, 1)[1].split(".", 1)[0]
    keys = BACKTICKED.findall(sentence)
    if not keys or len(keys) != len(set(keys)):
        raise ValidationFailure(f"section 12.2 lockable-key list is empty or repeats a key: {keys}")
    return keys


def validate_system_config_v2_schema(
    schema: Any = None, schema_v1: Any = None, manager_schema: Any = None, environments_text: str | None = None
) -> None:
    """`system-config-v2.schema.json` against schema 1, `manager-config-v2`, and
    environments.md section 12.2.

    Schema 2 is schema 1 plus one closed `environments` object whose members
    are exactly the section 12.2 lockable keys, the top-level
    `security_posture` member (manager section 1: lockable only in the
    direction of `hardened`), and a `locked` enum that is exactly the
    schema-1 enum plus `security_posture` plus `environments.<key>` for
    each lockable key. Every schema-1 member other than `schema_version`
    and `locked` keeps its schema-1 node byte for byte. Every environments
    knob other than `isolation`, `transitive_system_modules`,
    `require_source_signers`, and `permissions` takes its grammar from the
    `manager-config-v2` environments object by reference, so the two
    schemas cannot drift; `isolation` admits `shared` and `isolated`,
    `transitive_system_modules` admits `error` alone,
    `require_source_signers` admits `true` alone, and `permissions`
    admits `native` alone (section 12.2: each lockable only in that
    direction).
    """
    _registry, paths = schema_registry()
    if schema is None:
        schema = load_json(paths[SYSTEM_CONFIG_SCHEMAS[2]])
    if schema_v1 is None:
        schema_v1 = load_json(paths[SYSTEM_CONFIG_SCHEMAS[1]])
    if manager_schema is None:
        manager_schema = load_json(paths[MANAGER_CONFIG_SCHEMAS[2]])
    if environments_text is None:
        environments_text = (ROOT / "protocol" / "environments.md").read_text(encoding="utf-8")

    if schema.get("additionalProperties") is not False:
        raise ValidationFailure("system-config-v2 is not a closed object")
    if schema["properties"].get("schema_version") != {"const": 2}:
        raise ValidationFailure("system-config-v2 schema_version is not const 2")
    inherited = set(schema_v1["properties"]) - {"schema_version", "locked"}
    if set(schema["properties"]) != inherited | {"schema_version", "locked", "environments", "security_posture"}:
        raise ValidationFailure(
            "system-config-v2 properties are not schema 1 plus environments plus security_posture: "
            f"{sorted(set(schema['properties']) ^ (inherited | {'schema_version', 'locked', 'environments', 'security_posture'}))}"
        )
    for name in sorted(inherited):
        if schema["properties"][name] != schema_v1["properties"][name]:
            raise ValidationFailure(f"system-config-v2 changes the schema-1 shape of {name}")

    keys = environments_lockable_keys(environments_text)
    manager_knobs = manager_schema["$defs"]["environments"]["properties"]
    unknown = [key for key in keys if key not in manager_knobs]
    if unknown:
        raise ValidationFailure(f"section 12.2 locks knobs section 12.1 does not carry: {unknown}")

    environments = schema["$defs"]["environments"]
    if environments.get("additionalProperties") is not False:
        raise ValidationFailure("system-config-v2 environments object is not closed")
    if schema["properties"].get("environments") != {"$ref": "#/$defs/environments"}:
        raise ValidationFailure("system-config-v2 environments property does not reference $defs/environments")
    if set(environments["properties"]) != set(keys):
        raise ValidationFailure(
            "system-config-v2 environments properties differ from section 12.2: "
            f"schema-only {sorted(set(environments['properties']) - set(keys))}, "
            f"table-only {sorted(set(keys) - set(environments['properties']))}"
        )
    for key in keys:
        if key in ("isolation", "transitive_system_modules", "require_source_signers", "permissions"):
            continue
        want = {"$ref": f"{MANAGER_CONFIG_SCHEMAS[2]}#/$defs/environments/properties/{key}"}
        if environments["properties"][key] != want:
            raise ValidationFailure(f"system-config-v2 {key} does not take its grammar from manager-config-v2")
    node: Any = schema
    for segment in SYSTEM_CONFIG_ISOLATION_ENUM_PATH:
        if not isinstance(node, dict) or segment not in node:
            raise ValidationFailure("system-config-v2 states no closed isolation value set")
        node = node[segment]
    if node != ["shared", "isolated"]:
        raise ValidationFailure(
            f"system-config-v2 isolation admits {node!r}; section 12.2 permits exactly shared and isolated"
        )
    node = schema
    for segment in SYSTEM_CONFIG_TRANSITIVE_ENUM_PATH:
        if not isinstance(node, dict) or segment not in node:
            raise ValidationFailure("system-config-v2 states no closed transitive_system_modules value set")
        node = node[segment]
    if node != ["error"]:
        raise ValidationFailure(f"system-config-v2 transitive_system_modules admits {node!r}; section 12.2 permits error alone")
    node = schema
    for segment in SYSTEM_CONFIG_REQUIRE_SIGNERS_ENUM_PATH:
        if not isinstance(node, dict) or segment not in node:
            raise ValidationFailure("system-config-v2 states no closed require_source_signers value set")
        node = node[segment]
    if node != [True]:
        raise ValidationFailure(f"system-config-v2 require_source_signers admits {node!r}; section 12.2 permits true alone")
    node = schema
    for segment in SYSTEM_CONFIG_PERMISSIONS_ENUM_PATH:
        if not isinstance(node, dict) or segment not in node:
            raise ValidationFailure("system-config-v2 states no closed permissions value set")
        node = node[segment]
    if node != ["native"]:
        raise ValidationFailure(f"system-config-v2 permissions admits {node!r}; section 12.2 permits native alone")
    node = schema
    for segment in SYSTEM_CONFIG_POSTURE_ENUM_PATH:
        if not isinstance(node, dict) or segment not in node:
            raise ValidationFailure("system-config-v2 states no closed security_posture value set")
        node = node[segment]
    if node != ["hardened"]:
        raise ValidationFailure(f"system-config-v2 security_posture admits {node!r}; manager section 1 permits hardened alone")

    locked_v1 = schema_v1["properties"]["locked"]["items"]["enum"]
    want_locked = [*locked_v1, "security_posture", *(f"environments.{key}" for key in keys)]
    locked = schema["properties"].get("locked", {})
    if locked.get("type") != "array" or locked.get("uniqueItems") is not True:
        raise ValidationFailure("system-config-v2 locked is not a unique-item array")
    if locked.get("items", {}).get("enum") != want_locked:
        raise ValidationFailure(
            f"system-config-v2 locked enum is {locked.get('items', {}).get('enum')!r}; want {want_locked!r}"
        )


TAKEOVER_CARRYING_OPERATIONS = (
    "profile install",
    "profile use",
    "profile sync",
    "profile update",
    "env resolve --repair",
)

CLI_TAKEOVER_ROW_COUNTS = {
    "profile install": 1,
    "profile use <name>": 1,
    "profile use --clear": 1,
    "profile update": 1,
    "profile sync": 1,
    "env resolve --repair": 1,
}
CLI_TAKEOVER_ROW_CARRIERS = {
    "profile install": "profile install",
    "profile use <name>": "profile use",
    "profile use --clear": "profile use",
    "profile update": "profile update",
    "profile sync": "profile sync",
    "env resolve --repair": "env resolve --repair",
}
CLI_TAKEOVER_ROW_POINTER = "see the takeover note below."
CLI_TAKEOVER_NOTE_LABEL = "**Takeover note:**"
CLI_TAKEOVER_ENV_RESOLVE_SCOPE = "For `env resolve`, `--takeover` applies only with `--repair`."

# These full sentences are pinned in their owning sections. Whitespace
# normalization permits Markdown wrapping without making the predicates,
# subjects, recovery meaning, or section placement token-presence checks.
TAKEOVER_EXCLUSION_95 = (
    "By design, `profile import` activation and section 9.4 `global add` and `global install` are "
    "outside this closed set and fail closed on `environment_surface_unmanaged_conflict` exactly as "
    "section 8.3 states; recover activation by running `profile use --takeover` or `profile sync "
    "--takeover`, then retry activation rather than `profile import`, and recover a blocked global "
    "operation by running `profile sync --takeover` or `profile use --takeover`, then retry that operation."
)

TAKEOVER_EXCLUSION_94 = (
    "The `global add` and `global install` operations carry no takeover flag: they are outside the "
    "section 9.5 closed set and fail closed on `environment_surface_unmanaged_conflict` exactly as "
    "section 8.3 states; recover by running `profile sync --takeover` or `profile use --takeover`, "
    "then retry the blocked global operation."
)

TAKEOVER_EXCLUSION_96 = (
    "That activation carries no takeover flag: it is outside the section 9.5 closed set and fails "
    "closed on `environment_surface_unmanaged_conflict` exactly as section 8.3 states; recover by "
    "running `profile use --takeover` or `profile sync --takeover`, then retry activation rather "
    "than `profile import`."
)

TAKEOVER_EXCLUSION_MANAGER = (
    "`Profile import` activation and the environments §9.4 `global add` and `global install` "
    "operations carry no takeover flag: they are outside the environments §9.5 closed set and fail "
    "closed on `environment_surface_unmanaged_conflict` exactly as environments §8.3 states; recover "
    "activation by running `profile use --takeover` or `profile sync --takeover`, then retry activation "
    "rather than `profile import`, and recover a blocked global operation by running `profile sync "
    "--takeover` or `profile use --takeover`, then retry that operation."
)


def squash_prose(text: str) -> str:
    """Collapse every whitespace run to one space so wrapped prose matches."""
    return re.sub(r"\s+", " ", text).strip()


def markdown_h3_section(text: str, heading: str, *, label: str) -> str:
    """Return an exact H3 section, ending at its next same-or-higher heading."""
    lines = text.splitlines(keepends=True)
    matches = [index for index, line in enumerate(lines) if line.rstrip("\r\n").strip() == heading]
    if len(matches) != 1:
        raise ValidationFailure(f"{label} has no {heading} section")
    start = matches[0]
    depth = len(heading) - len(heading.lstrip("#"))
    if depth != 3:
        raise ValidationFailure(f"{label} section pin is not an H3 heading: {heading}")
    for end in range(start + 1, len(lines)):
        candidate = lines[end].rstrip("\r\n")
        match = re.match(r"^(#{1,6})(?:[ \t]+|$)", candidate)
        if match is not None and len(match.group(1)) <= depth:
            return "".join(lines[start + 1 : end])
    return "".join(lines[start + 1 :])


def takeover_carrying_operations(section95: str) -> list[str]:
    """The backticked operations of the §9.5 closed-carrier sentence, in order."""
    match = re.search(
        r"The flag is accepted on exactly (.*?) and on no other operation",
        squash_prose(section95),
    )
    if match is None:
        raise ValidationFailure("environments.md section 9.5 states no closed takeover-carrier enumeration")
    return BACKTICKED.findall(match.group(1))


def takeover_trigger_operations(section95: str) -> list[str]:
    """The backticked operations of the §9.5 onboarding-trigger sentence, in order."""
    match = re.search(
        r"triggered only by .*?— (.*?)\. Read-only commands",
        squash_prose(section95),
    )
    if match is None:
        raise ValidationFailure("environments.md section 9.5 states no onboarding-trigger enumeration")
    return BACKTICKED.findall(match.group(1))


def takeover_cli_clause(section95: str) -> str:
    """Copy the §9.5 takeover clause with its source-relative pointer made explicit."""
    normalized = squash_prose(section95)
    match = re.search(
        r"Takeover is not an operation of its own:.*?and on no other operation\. "
        r"A carrying operation that meets unmanaged files outside onboarding performs the same notice "
        r"and backup as onboarding when the flag is given; without the flag, section 8\.3 applies and "
        r"the operation fails with `environment_surface_unmanaged_conflict` rather than overwrite\.",
        normalized,
    )
    if match is None:
        raise ValidationFailure("environments.md section 9.5 states no complete CLI takeover and write-coverage clause")
    clause = match.group(0)
    source_pointer = "named above as onboarding triggers"
    if clause.count(source_pointer) != 1:
        raise ValidationFailure("environments.md section 9.5 has no unique source-relative onboarding-trigger pointer")
    return clause.replace(source_pointer, "named in environments section 9.5 as onboarding triggers")


def require_exact_takeover_sentence(section: str, expected: str, *, label: str) -> None:
    """Require one whitespace-normalized exact sentence in its owning section."""
    normalized = squash_prose(section)
    pinned = squash_prose(expected)
    if normalized.count(pinned) != 1:
        raise ValidationFailure(f"{label} does not contain exactly one pinned takeover sentence")


def validate_cli_takeover_rows(cli_text: str, carrying: list[str], clause: str) -> None:
    """Pin the CLI carrier rows and note while excluding import/global rows."""
    import_rows = [line for line in cli_text.splitlines() if "curator profile import" in line]
    if not import_rows:
        raise ValidationFailure("cli/curator.md names no profile import command")
    global_rows = [line for line in cli_text.splitlines() if "curator global" in line]
    if not global_rows:
        raise ValidationFailure("cli/curator.md names no global command")
    for line in [*import_rows, *global_rows]:
        if "--takeover" in line:
            raise ValidationFailure(f"cli/curator.md row carries a takeover flag it must not: {line.strip()[:80]}")

    lines = cli_text.splitlines()
    try:
        commands_heading = lines.index("## Commands")
    except ValueError as error:
        raise ValidationFailure("cli/curator.md has no Commands table for the takeover note") from error
    table_lines: list[int] = []
    command_rows: list[tuple[str, str]] = []
    for index in range(commands_heading + 1, len(lines)):
        line = lines[index]
        if not line.startswith("|"):
            if table_lines:
                break
            if line.strip():
                break
            continue
        table_lines.append(index)
        row = re.match(r"^\|\s*`([^`]*)`\s*\|\s*(.*?)\s*\|\s*$", line)
        if row is not None:
            command_rows.append((row.group(1), row.group(2).strip()))
    if not table_lines or not command_rows:
        raise ValidationFailure("cli/curator.md has no parseable Commands table for takeover carriers")

    # The complete clause must appear once, immediately under the table, and
    # match the carrier, notice, backup, and refusal rules in environments §9.5.
    cursor = table_lines[-1] + 1
    while cursor < len(lines) and not lines[cursor].strip():
        cursor += 1
    note_lines: list[str] = []
    while cursor < len(lines) and lines[cursor].strip():
        note_lines.append(lines[cursor].strip())
        cursor += 1
    note_paragraph = " ".join(note_lines)
    if not note_paragraph.startswith(CLI_TAKEOVER_NOTE_LABEL):
        raise ValidationFailure("cli/curator.md does not place the takeover note immediately below the Commands table")
    note_clause = note_paragraph[len(CLI_TAKEOVER_NOTE_LABEL) :].strip()
    expected_note = f"{clause} {CLI_TAKEOVER_ENV_RESOLVE_SCOPE}"
    if squash_prose(note_clause) != squash_prose(expected_note):
        raise ValidationFailure("cli/curator.md takeover note does not match the complete environments §9.5 clause and env resolve repair scope")
    if squash_prose(cli_text).count(clause) != 1:
        raise ValidationFailure("cli/curator.md must state the §9.5 takeover clause exactly once")

    if set(CLI_TAKEOVER_ROW_CARRIERS.values()) != set(carrying):
        raise ValidationFailure("CLI takeover rows do not map to the §9.5 carrier set")
    actual_counts: dict[str, int] = {}
    for command, behavior in command_rows:
        if "--takeover" not in command:
            continue
        if "[--takeover]" not in command:
            raise ValidationFailure(f"CLI takeover carrier is not shown as an optional flag: {command}")
        if command.startswith("curator profile install "):
            row_key = "profile install"
        elif command.startswith("curator profile use <name>"):
            row_key = "profile use <name>"
        elif command.startswith("curator profile use --clear"):
            row_key = "profile use --clear"
        elif command.startswith("curator profile update "):
            row_key = "profile update"
        elif command.startswith("curator profile sync "):
            row_key = "profile sync"
        elif command.startswith("curator env resolve "):
            if "[--repair]" not in command:
                raise ValidationFailure("CLI env resolve takeover carrier is not scoped to --repair")
            row_key = "env resolve --repair"
        else:
            raise ValidationFailure(f"CLI command row adds --takeover outside the §9.5 carrier set: {command}")
        actual_counts[row_key] = actual_counts.get(row_key, 0) + 1
        if not behavior.lower().endswith(CLI_TAKEOVER_ROW_POINTER):
            raise ValidationFailure(f"CLI takeover row does not point to the note: {command}")
        before_pointer = behavior[: -len(CLI_TAKEOVER_ROW_POINTER)].lower()
        if re.search(r"\btakeover\b|\btakes over\b", before_pointer):
            raise ValidationFailure(f"CLI takeover row repeats the clause instead of using only a pointer: {command}")
    if actual_counts != CLI_TAKEOVER_ROW_COUNTS:
        raise ValidationFailure(
            f"CLI takeover row carriers/counts are {actual_counts!r}; want {CLI_TAKEOVER_ROW_COUNTS!r}"
        )


def validate_takeover_closed_set_text(
    environments_text: str | None = None,
    manager_text: str | None = None,
    cli_text: str | None = None,
) -> None:
    """Pin the five §9.5 carriers and exact exclusion clauses in their sections."""
    if environments_text is None:
        environments_text = (ROOT / "protocol" / "environments.md").read_text(encoding="utf-8")
    if manager_text is None:
        manager_text = (ROOT / "profiles" / "manager.md").read_text(encoding="utf-8")
    if cli_text is None:
        cli_text = (ROOT / "cli" / "curator.md").read_text(encoding="utf-8")
    section94 = markdown_h3_section(environments_text, "### 9.4 Profile-scoped skills and migration", label="environments.md")
    section95 = markdown_h3_section(environments_text, "### 9.5 Onboarding", label="environments.md")
    section96 = markdown_h3_section(environments_text, "### 9.6 Onboarding import", label="environments.md")
    carrying = takeover_carrying_operations(section95)
    if carrying != list(TAKEOVER_CARRYING_OPERATIONS):
        raise ValidationFailure(
            f"section 9.5 takeover carriers are {carrying!r}; want {list(TAKEOVER_CARRYING_OPERATIONS)!r}"
        )
    triggers = takeover_trigger_operations(section95)
    if triggers != carrying:
        raise ValidationFailure(
            f"section 9.5 onboarding triggers name {triggers!r} but the takeover carriers name {carrying!r}"
        )
    require_exact_takeover_sentence(section95, TAKEOVER_EXCLUSION_95, label="environments.md section 9.5")
    require_exact_takeover_sentence(section94, TAKEOVER_EXCLUSION_94, label="environments.md section 9.4")
    require_exact_takeover_sentence(section96, TAKEOVER_EXCLUSION_96, label="environments.md section 9.6")
    section123 = markdown_h3_section(manager_text, "### 12.3 Profile lifecycle", label="profiles/manager.md")
    require_exact_takeover_sentence(section123, TAKEOVER_EXCLUSION_MANAGER, label="profiles/manager.md section 12.3")
    validate_cli_takeover_rows(cli_text, carrying, takeover_cli_clause(section95))


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
    "system-module-direct",
    "system-module-transitive-drop",
    "system-module-transitive-error",
    "system-module-transitive-waived",
    "system-module-overlay-direct",
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


def environment_machine_policy(case: dict[str, Any]) -> tuple[str, set[str]]:
    """The section 12.1 admission policy of a materialization case: the
    `transitive_system_modules` mode (`drop` when the case states none) and
    the waived package names."""
    policy = case.get("machine_policy", {})
    mode = policy.get("transitive_system_modules", "drop")
    if mode not in ("drop", "error"):
        raise ValidationFailure(f"environment case {case.get('name', '<unnamed>')}: unknown admission mode {mode!r}")
    waivers = policy.get("system_module_waivers", [])
    if not isinstance(waivers, list) or any(
        not isinstance(entry, dict) or not entry.get("package") or not entry.get("reason")
        for entry in waivers
    ):
        raise ValidationFailure(f"environment case {case.get('name', '<unnamed>')}: malformed system_module_waivers")
    return mode, {entry["package"] for entry in waivers}


def environment_direct_packages(lock: dict[str, Any]) -> set[str]:
    """The section 3 direct set: the root, every active overlay, and every
    package the root or an active overlay names in requires."""
    members = {member["name"]: member for member in lock["members"] if member["kind"] == "context"}
    overlays = {name for name, member in members.items() if member.get("overlay")}
    root = lock["root"]
    direct = {root} | set(overlays)
    for name, member in members.items():
        for requirer in member.get("required_by", []):
            if requirer == root or requirer in overlays:
                direct.add(name)
    return direct


def environment_system_prompt_admission(case: dict[str, Any]) -> tuple[str, list[dict[str, str]], list[dict[str, str]]]:
    """Split a system-prompt case's applicable system modules into admitted
    and dropped `{"package", "path"}` records under its machine policy, in
    emitted order with manifest order within a package."""
    mode, waived = environment_machine_policy(case)
    lock = case["lock"]
    packages = case.get("packages", {})
    environment = case["environment"]
    order = environment_emitted_order(lock, case.get("precedence"))
    direct = environment_direct_packages(lock)
    admitted: list[dict[str, str]] = []
    dropped: list[dict[str, str]] = []
    for member in order:
        for module in environment_applicable(packages[member["name"]], environment, "system"):
            entry = {"package": member["name"], "path": module["path"]}
            if member["name"] in direct or member["name"] in waived:
                admitted.append(entry)
            else:
                dropped.append(entry)
    return mode, admitted, dropped


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
        mode, admitted, dropped = environment_system_prompt_admission(case)
        if mode == "error" and dropped:
            return {}
        admitted_keys = {(entry["package"], entry["path"]) for entry in admitted}
        admitted_contents = [
            module["content"]
            for member in order
            for module in environment_applicable(packages[member["name"]], environment, "system")
            if (member["name"], module["path"]) in admitted_keys
        ]
        if not admitted_contents:
            return {}
        return {ENVIRONMENT_SYSTEM_PROMPT_PATH: "\n".join(admitted_contents).encode("utf-8")}
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
        if case["surface"] == "system-prompt":
            mode, admitted, dropped = environment_system_prompt_admission(case)
            if case.get("admitted") != admitted:
                raise ValidationFailure(f"environment case {name}: admitted record is stale")
            if case.get("dropped") != dropped:
                raise ValidationFailure(f"environment case {name}: dropped record is stale")
            if mode == "error" and dropped:
                if case.get("error") != "context_system_module_transitive":
                    raise ValidationFailure(f"environment case {name}: refusal is not context_system_module_transitive")
                if case.get("error_package") != dropped[0]["package"] or case.get("error_module") != dropped[0]["path"]:
                    raise ValidationFailure(f"environment case {name}: refusal names the wrong module")
                if case.get("warnings") != []:
                    raise ValidationFailure(f"environment case {name}: a refusal carries no materialization warnings")
            else:
                if "error" in case or "error_package" in case or "error_module" in case:
                    raise ValidationFailure(f"environment case {name}: no refusal without the error policy and a dropped module")
                want_warnings = [
                    {"diagnostic": "context_system_module_dropped", "package": entry["package"], "path": entry["path"]}
                    for entry in dropped
                ]
                if case.get("warnings") != want_warnings:
                    raise ValidationFailure(f"environment case {name}: drop warnings are stale")
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
# S4: MCP env passthrough bounds and declaration surfacing
# (environments.md sections 2.2, 2.3, 9.1, 9.2, 10.3, 12, 12.1)


S4_WARN_PROFILE = "s4-warn"
S4_ENFORCE_PROFILE = "s4-enforce"
S4_PROFILES = ("s4-enforce", "s4-warn")

S4_DIAG_ALLOWLIST_EMPTY = "mcp_package_allowlist_empty"
S4_DIAG_UNLISTED = "mcp_env_passthrough_unlisted"
S4_DIAG_DROPPED = "mcp_env_passthrough_dropped"
S4_DIAG_NOT_ALLOWED = "mcp_package_not_allowed"

S4_ALLOWLIST_EMPTY_ADMITTED = "every declaration package in the closure"
S4_ALLOWLIST_NONEMPTY_ADMITTED = "only listed declaration packages"

S4_SURFACING_ORDER = ["audit-gate", "surfacing", "lock-published", "materialization"]
S4_SURFACING_TRANSPORTS = ("stdio", "http")

S4_DEFAULT_RESOLUTION_CASES = {
    "s4-warn-absent-warns-every-passed",
    "s4-enforce-absent-drops-all",
    "explicit-null-unbounded",
    "s4-warn-explicit-list-bounds-silently",
    "s4-enforce-explicit-list-drops-with-diagnostic",
    "s4-enforce-absent-passes-unlisted",
    "explicit-null-treated-as-empty",
}
S4_DEFAULT_NEGATIVE_CASES = {
    "s4-enforce-absent-passes-unlisted",
    "explicit-null-treated-as-empty",
}
S4_ALLOWLIST_CASES = {
    "empty-allowlist-install-warns",
    "empty-allowlist-update-warns",
    "empty-allowlist-status-posture",
    "non-empty-allowlist-silent",
    "non-empty-allowlist-warns",
    "outside-non-empty-allowlist-refused",
}
S4_ALLOWLIST_NEGATIVE_CASES = {"non-empty-allowlist-warns"}
S4_SURFACING_CASES = {
    "single-stdio-declaration",
    "stdio-and-http-ordering",
    "args-with-space",
    "args-with-escaped-quote",
    "row-missing-env-names",
    "row-wrong-column-order",
}
S4_SURFACING_NEGATIVE_CASES = {"row-missing-env-names", "row-wrong-column-order"}
S4_SURFACING_ORDER_CASES = {
    "install-surfacing-before-publish": "profile-install",
    "update-surfacing-before-publish": "profile-update",
}
S4_SCHEMA_CASES = {
    "knob-absent-defaults-empty",
    "knob-explicit-null-unbounded",
    "knob-explicit-list",
    "knob-invalid-name",
}


def s4_effective_passable(knob: Any, profile: str) -> Any:
    """Recompute the effective passable_env_names for one knob state (§10.3).

    The knob is `"absent"`, `None` (explicit null), or a list. An absent
    knob is unbounded under `s4-warn` and empty under `s4-enforce`; an
    explicit null is unbounded under both; a list bounds under both.
    """
    if knob == "absent":
        return "unbounded" if profile == S4_WARN_PROFILE else []
    if knob is None:
        return "unbounded"
    return list(knob)


def s4_compact_json(value: Any) -> str:
    """Compact JSON with no spaces, matching the §2.3 row grammar.

    Raw UTF-8 (ensure_ascii=False), the same choice the Go vector generator
    makes: Go's encoder never escapes non-ASCII runes.
    """
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def s4_surfacing_row(declaration: Any) -> str:
    """Render one §2.3 surfacing row from a declaration, without the LF."""
    if not isinstance(declaration, dict):
        raise ValidationFailure("surfacing declaration must be an object")
    package = declaration.get("package")
    version = declaration.get("version")
    transport = declaration.get("transport")
    if not isinstance(package, str) or not package:
        raise ValidationFailure("surfacing declaration needs a package name")
    if not isinstance(version, str) or not version:
        raise ValidationFailure(f"surfacing declaration {package}: needs a version")
    if transport not in S4_SURFACING_TRANSPORTS:
        raise ValidationFailure(f"surfacing declaration {package}: transport must be stdio or http")
    env_names = declaration.get("env_names")
    if not isinstance(env_names, list) or any(not isinstance(item, str) for item in env_names):
        raise ValidationFailure(f"surfacing declaration {package}: env_names must be a string array")
    if transport == "http":
        if "command" in declaration and declaration["command"] != "-":
            raise ValidationFailure(f"surfacing declaration {package}: http rows carry command=-")
        if "args" in declaration and declaration["args"] != []:
            raise ValidationFailure(f"surfacing declaration {package}: http rows carry args=[]")
        command, args = "-", []
    else:
        command = declaration.get("command")
        args = declaration.get("args")
        if not isinstance(command, str) or not command:
            raise ValidationFailure(f"surfacing declaration {package}: stdio needs a command")
        if not isinstance(args, list) or any(not isinstance(item, str) for item in args):
            raise ValidationFailure(f"surfacing declaration {package}: stdio args must be a string array")
    return (
        f"mcp-declaration {package} {version} {transport} "
        f"command={command} args={s4_compact_json(args)} env_names={s4_compact_json(env_names)}"
    )


def s4_parse_surfacing_row(row: Any) -> dict[str, Any] | None:
    """Parse one §2.3 surfacing row, or return None when it is non-conforming.

    The columns are closed and ordered: command=, args=, env_names=. The
    `args` and `env_names` JSON arrays are decoded structurally, so spaces
    and escapes inside string values are preserved; the arrays must still
    be compact (no separator whitespace), so a re-serialization check
    rejects padded but otherwise valid rows. Missing, reordered, or extra
    columns are rejected.
    """
    if not isinstance(row, str):
        return None
    if "\n" in row or "\r" in row:
        return None
    head = row.split(" ", 4)
    if len(head) != 5:
        return None
    marker, package, version, transport, rest = head
    if marker != "mcp-declaration" or not package or not version:
        return None
    if transport not in S4_SURFACING_TRANSPORTS:
        return None
    if not rest.startswith("command="):
        return None
    space = rest.find(" ")
    if space < 0:
        return None
    command = rest[len("command="):space]
    if not command:
        return None
    if transport == "http" and command != "-":
        return None
    after_command = rest[space + 1:]
    if not after_command.startswith("args="):
        return None
    try:
        args_value, args_end = json.JSONDecoder().raw_decode(after_command, len("args="))
    except json.JSONDecodeError:
        return None
    if not isinstance(args_value, list) or any(not isinstance(item, str) for item in args_value):
        return None
    if s4_compact_json(args_value) != after_command[len("args="):args_end]:
        return None
    after_args = after_command[args_end:]
    if not after_args.startswith(" env_names="):
        return None
    try:
        env_value, env_end = json.JSONDecoder().raw_decode(after_args, len(" env_names="))
    except json.JSONDecodeError:
        return None
    if not isinstance(env_value, list) or any(not isinstance(item, str) for item in env_value):
        return None
    if s4_compact_json(env_value) != after_args[len(" env_names="):env_end]:
        return None
    if env_end != len(after_args):
        return None
    if transport == "http" and args_value != []:
        return None
    return {
        "package": package,
        "version": version,
        "transport": transport,
        "command": command,
        "args": args_value,
        "env_names": env_value,
    }


def s4_expected_passthrough(knob: Any, profile: str, requested: list[str]) -> tuple[list[str], list[str], str | None]:
    """Recompute (passed, dropped, diagnostic) for one launch composition."""
    effective = s4_effective_passable(knob, profile)
    if effective == "unbounded":
        passed, dropped = list(requested), []
    else:
        passed = [name for name in requested if name in effective]
        dropped = [name for name in requested if name not in effective]
    if profile == S4_WARN_PROFILE:
        if knob == "absent":
            diagnostic = S4_DIAG_UNLISTED if passed else None
        else:
            # An explicit list still bounds under s4-warn, silently: the
            # pre-S4 behavior is kept and nothing outside a list passes, so
            # the unlisted warning has nothing to name.
            diagnostic = None
    else:
        diagnostic = S4_DIAG_DROPPED if dropped else None
    return passed, dropped, diagnostic


def validate_environments_env_passthrough_vectors(
    vector: Any = None, suite_root: Path | None = None, schema: Any = None
) -> None:
    """Recompute the S4 passthrough, allowlist, and surfacing expectations.

    Every positive case is derived from its declared inputs — the effective
    passable_env_names per profile/knob state, the passed/dropped name sets
    and diagnostics, the allowlist warning verdict, and the surfacing output
    bytes — and compared against the declared fields. Every negative case
    must carry an observation that genuinely contradicts the recomputed rule,
    so a repaired observation or a flipped flag fails here.
    """
    root = SUITE if suite_root is None else Path(suite_root)
    if vector is None:
        vector = load_json(root / "vectors" / "environments-env-passthrough.json")
    if (
        vector.get("schema_version") != 1
        or vector.get("protocol_version") != PROTOCOL_VERSION
        or vector.get("capability") != "agent-environments"
        or vector.get("capability_revision") != 1
    ):
        raise ValidationFailure("env-passthrough vector has the wrong capability identity")
    if vector.get("s4_profiles") != list(S4_PROFILES):
        raise ValidationFailure("env-passthrough s4_profiles must pin exactly s4-enforce and s4-warn")

    defaults = named_cases(vector.get("default_resolution_cases"), "env-passthrough default resolution")
    if set(defaults) != S4_DEFAULT_RESOLUTION_CASES:
        raise ValidationFailure("env-passthrough default resolution case inventory is not exact")
    for name, case in defaults.items():
        profiles = case.get("profiles", [case.get("profile")])
        if (
            not isinstance(profiles, list)
            or not profiles
            or any(profile not in S4_PROFILES for profile in profiles)
        ):
            raise ValidationFailure(f"env-passthrough case {name}: profile must be s4-warn or s4-enforce")
        knob = case.get("knob", "absent")
        if not (knob == "absent" or knob is None or isinstance(knob, list)):
            raise ValidationFailure(f"env-passthrough case {name}: knob must be absent, null, or a list")
        requested = case.get("requested")
        if not isinstance(requested, list) or any(not isinstance(item, str) for item in requested):
            raise ValidationFailure(f"env-passthrough case {name}: requested must be a string array")
        if name in S4_DEFAULT_NEGATIVE_CASES:
            if case.get("conforming") is not False or not case.get("reason"):
                raise ValidationFailure(f"env-passthrough case {name}: a negative needs conforming=false and a reason")
            observed = case.get("passed")
            if not isinstance(observed, list):
                raise ValidationFailure(f"env-passthrough case {name}: a negative needs its observed passed set")
            for profile in profiles:
                expected_passed, _, _ = s4_expected_passthrough(knob, profile, requested)
                if observed == expected_passed:
                    raise ValidationFailure(
                        f"env-passthrough case {name}: the observation no longer violates the {profile} rule"
                    )
            continue
        if case.get("conforming") is False:
            raise ValidationFailure(f"env-passthrough case {name}: a positive case must not carry conforming=false")
        for profile in profiles:
            expected_passed, expected_dropped, expected_diag = s4_expected_passthrough(knob, profile, requested)
            if case.get("passed") != expected_passed or case.get("dropped") != expected_dropped:
                raise ValidationFailure(
                    f"env-passthrough case {name}: passed/dropped are not the {profile} rule "
                    f"({expected_passed}/{expected_dropped})"
                )
            if case.get("diagnostic") != expected_diag:
                raise ValidationFailure(
                    f"env-passthrough case {name}: diagnostic is not the {profile} rule ({expected_diag!r})"
                )
            if case.get("effective") != s4_effective_passable(knob, profile):
                raise ValidationFailure(f"env-passthrough case {name}: effective is not the {profile} rule")
        if case.get("diagnostic") == S4_DIAG_UNLISTED:
            if case.get("migration_hint_names_variables") is not True or case.get("migration_hint_names_knob") is not True:
                raise ValidationFailure(f"env-passthrough case {name}: the unlisted warning must name the variables and the knob")
        elif case.get("migration_hint_names_variables") is True or case.get("migration_hint_names_knob") is True:
            raise ValidationFailure(f"env-passthrough case {name}: a migration hint without the unlisted warning is stale")

    allowlist = named_cases(vector.get("allowlist_empty_cases"), "env-passthrough allowlist")
    if set(allowlist) != S4_ALLOWLIST_CASES:
        raise ValidationFailure("env-passthrough allowlist case inventory is not exact")
    for name, case in allowlist.items():
        operation = case.get("operation")
        if operation not in {"profile-install", "profile-update", "env-status"}:
            raise ValidationFailure(f"env-passthrough case {name}: operation must be install, update, or status")
        entries = case.get("mcp_package_allowlist")
        if not isinstance(entries, list) or any(not isinstance(item, str) for item in entries):
            raise ValidationFailure(f"env-passthrough case {name}: mcp_package_allowlist must be a string array")
        expected_diag = S4_DIAG_ALLOWLIST_EMPTY if not entries else None
        if name in S4_ALLOWLIST_NEGATIVE_CASES:
            if case.get("conforming") is not False or not case.get("reason"):
                raise ValidationFailure(f"env-passthrough case {name}: a negative needs conforming=false and a reason")
            if case.get("diagnostic") == expected_diag:
                raise ValidationFailure(f"env-passthrough case {name}: the observation no longer violates the allowlist rule")
            continue
        if case.get("conforming") is False:
            raise ValidationFailure(f"env-passthrough case {name}: a positive case must not carry conforming=false")
        if case.get("diagnostic") != expected_diag and "package" not in case:
            raise ValidationFailure(f"env-passthrough case {name}: diagnostic is not the allowlist rule ({expected_diag!r})")
        if "package" in case:
            if not entries or case.get("package") in entries:
                raise ValidationFailure(f"env-passthrough case {name}: the refused package must sit outside a non-empty allowlist")
            if case.get("diagnostic") != S4_DIAG_NOT_ALLOWED or case.get("fails_operation") is not True:
                raise ValidationFailure(f"env-passthrough case {name}: an outside package is refused with mcp_package_not_allowed")
        elif not entries:
            if case.get("admitted") != S4_ALLOWLIST_EMPTY_ADMITTED:
                raise ValidationFailure(f"env-passthrough case {name}: an empty allowlist admits every declaration package in the closure")
            if operation == "env-status":
                if case.get("row_current") is not True:
                    raise ValidationFailure(f"env-passthrough case {name}: the warning row stays current")
            elif case.get("fails_operation") is not False:
                raise ValidationFailure(f"env-passthrough case {name}: the warning never fails the operation")
        else:
            if case.get("admitted") != S4_ALLOWLIST_NONEMPTY_ADMITTED:
                raise ValidationFailure(f"env-passthrough case {name}: a non-empty allowlist admits only listed declaration packages")
            if case.get("fails_operation") is not False:
                raise ValidationFailure(f"env-passthrough case {name}: silence never fails the operation")

    surfacing = named_cases(vector.get("surfacing_cases"), "env-passthrough surfacing")
    if set(surfacing) != S4_SURFACING_CASES:
        raise ValidationFailure("env-passthrough surfacing case inventory is not exact")
    for name, case in surfacing.items():
        if name in S4_SURFACING_NEGATIVE_CASES:
            if case.get("conforming") is not False or not case.get("reason"):
                raise ValidationFailure(f"env-passthrough case {name}: a negative needs conforming=false and a reason")
            if s4_parse_surfacing_row(case.get("row")) is not None:
                raise ValidationFailure(f"env-passthrough case {name}: the row no longer violates the closed columns")
            continue
        if case.get("conforming") is False:
            raise ValidationFailure(f"env-passthrough case {name}: a positive case must not carry conforming=false")
        declarations = case.get("declarations")
        if not isinstance(declarations, list) or not declarations:
            raise ValidationFailure(f"env-passthrough case {name}: declarations must be a non-empty array")
        rows = [s4_surfacing_row(item) for item in declarations]
        rows.sort(key=lambda row: row.split(" ", 2)[1].encode("utf-8"))
        for row in rows:
            if s4_parse_surfacing_row(row) is None:
                raise ValidationFailure(f"env-passthrough case {name}: recomputed row {row!r} violates the closed columns")
        expected = "".join(row + "\n" for row in rows).encode("utf-8")
        if not isinstance(case.get("expected_bytes"), str) or case["expected_bytes"].encode("utf-8") != expected:
            raise ValidationFailure(f"env-passthrough case {name}: expected_bytes are stale")
        if case.get("expected_byte_length") != len(expected):
            raise ValidationFailure(f"env-passthrough case {name}: expected_byte_length is false")
        if case.get("expected_sha256") != "sha256:" + hashlib.sha256(expected).hexdigest():
            raise ValidationFailure(f"env-passthrough case {name}: expected_sha256 is stale")

    order = named_cases(vector.get("surfacing_order_cases"), "env-passthrough surfacing order")
    if set(order) != set(S4_SURFACING_ORDER_CASES):
        raise ValidationFailure("env-passthrough surfacing order case inventory is not exact")
    for name, case in order.items():
        if case.get("operation") != S4_SURFACING_ORDER_CASES[name]:
            raise ValidationFailure(f"env-passthrough case {name}: operation does not match the pinned one")
        if case.get("order") != S4_SURFACING_ORDER:
            raise ValidationFailure(
                f"env-passthrough case {name}: surfacing must print after the audit gate "
                "and before the lock is published or any surface is (re-)materialized"
            )

    registry, paths = schema_registry()
    if schema is None:
        schema = load_json(paths[MANAGER_CONFIG_SCHEMAS[2]])
    knob_schema_default = schema["$defs"]["environments"]["properties"]["passable_env_names"]["default"]
    if knob_schema_default != []:
        raise ValidationFailure("env-passthrough schema cases need the passable_env_names schema default to be []")
    knob_validator = Draft202012Validator(schema, registry=registry)
    schema_cases = named_cases(vector.get("schema_cases"), "env-passthrough schema")
    if set(schema_cases) != S4_SCHEMA_CASES:
        raise ValidationFailure("env-passthrough schema case inventory is not exact")
    for name, case in schema_cases.items():
        knob = case.get("knob", "absent")
        instance: dict[str, Any] = {"schema_version": 2, "skills_root": "./skills", "projects": {}, "environments": {}}
        if knob != "absent":
            instance["environments"]["passable_env_names"] = knob
        errors = list(knob_validator.iter_errors(instance))
        semantic = manager_config_semantic_error(instance) if not errors else None
        if (not errors and semantic is None) != bool(case.get("valid")):
            raise ValidationFailure(f"env-passthrough case {name}: valid flag contradicts the manager-config-v2 grammar")
        if case.get("valid"):
            expected_effective = [] if knob == "absent" else ("unbounded" if knob is None else knob)
            if case.get("effective") != expected_effective:
                raise ValidationFailure(f"env-passthrough case {name}: effective is not the knob default rule")
        elif "effective" in case:
            raise ValidationFailure(f"env-passthrough case {name}: an invalid knob binds no effective value")


# ---------------------------------------------------------------------------
# Sections 1.4, 9.2, 12: source signer allowlist and update-delta confirmation


E1_DIAG_UNSIGNED = "context_source_unsigned"
E1_DIAG_REJECTED = "context_source_signer_rejected"
E1_DIAG_MISSING = "context_source_signers_missing"
E1_DIAG_DELTA = "profile_update_system_delta"
E1_DIAG_CONFIRM = "profile_update_confirmation_required"

E1_HINT_DELTA = "revision B refuses with profile_update_confirmation_required unless --confirm-system-delta is given"

E1_REVISION_A = "warning release: a triggered update delta warns profile_update_system_delta and proceeds"
E1_REVISION_B = "flip release: a triggered update delta refuses profile_update_confirmation_required unless --confirm-system-delta is given"

E1_CONFIRMATION_BEHAVIOR = {
    "A-warning": "a triggered update delta warns profile_update_system_delta and proceeds",
    "B-flip": "a triggered update delta refuses profile_update_confirmation_required unless --confirm-system-delta is given",
}

E1_MEMBER_KINDS = ("context", "mcp", "skill")

E1_VERIFICATION_CASES = {
    "ssh-tag-signature-accepted",
    "gpg-commit-signature-accepted",
    "either-signature-suffices",
    "unsigned-refused",
    "wrong-signer-refused",
    "invalid-signature-refused",
    "no-allowlist-accepted",
    "require-without-allowlist-refused",
    "require-with-allowlist-accepted",
    "path-source-never-verified",
    "no-silent-fallback-to-lower-candidate",
    "empty-allowlist-signed-refused",
    "empty-allowlist-unsigned-refused",
    "exact-tag-selection-verified",
    "revision-selection-verifies-commit",
    "ssh-same-key-different-comment-accepted",
    "ssh-different-material-rejected",
    "unsigned-accepted",
    "fallback-selection",
}
E1_VERIFICATION_NEGATIVE_CASES = {"unsigned-accepted", "fallback-selection"}
E1_MERGE_CASES = {
    "locked-overlap-system-wins-with-warning",
    "locked-disjoint-machine-addition",
    "locked-machine-absent",
    "locked-empty-system-machine-adds",
    "unlocked-machine-replaces-whole",
    "unlocked-absent-machine-falls-back",
}
E1_POSTURE_CASES = {
    "enforced-names-verified-signer",
    "enforced-unknown-without-local-material",
    "enforced-pin-fails-non-current",
    "unconfigured",
    "required-missing",
}
E1_DELTA_CASES = {
    "plain-version-bump-no-confirmation",
    "empty-delta-identical-lock",
    "new-system-module",
    "changed-system-bytes",
    "changed-system-module-set",
    "changed-system-selector",
    "new-mcp-member",
    "changed-mcp-command",
    "changed-mcp-args",
    "changed-mcp-env-names",
    "changed-mcp-url",
    "changed-mcp-url-confirmed",
    "changed-mcp-selector",
    "changed-mcp-selector-confirmed",
    "mcp-env-names-reorder-triggers",
    "absent-selector-to-present",
    "absent-selector-to-present-confirmed",
    "present-selector-to-absent",
    "present-selector-to-absent-confirmed",
    "absent-env-names-to-empty",
    "absent-env-names-to-empty-confirmed",
    "empty-env-names-to-absent",
    "empty-env-names-to-absent-confirmed",
    "removed-system-member-silent",
    "confirmed-flag-proceeds",
    "added-skill-silent",
    "moved-skill-without-version",
    "config-preconfirm-claim",
    "silent-system-introduction",
}
E1_DELTA_NEGATIVE_CASES = {"config-preconfirm-claim", "silent-system-introduction"}
E1_ALL_CASES = {
    "all-with-flag-confirms-every-profile",
    "all-without-flag-stops-at-first-refusal",
}
E1_REINSTALL_CASES = {
    "reinstall-with-flag-proceeds",
    "reinstall-without-flag-refuses-under-b",
}
E1_CONFIRMATION_POSTURE_CASES = {
    "update-confirmation-revision-a-warning",
    "update-confirmation-revision-b-flip",
}


def e1_check_signer_shape(signer: Any, label: str) -> tuple[str, str]:
    """A claimed signer is a closed `{ type, key }` or `{ type, fingerprint }`
    shape; return its `(type, identity)` key."""
    if not isinstance(signer, dict):
        raise ValidationFailure(f"{label}: a signer must be an object")
    kind = signer.get("type")
    if kind == "ssh":
        if not isinstance(signer.get("key"), str) or set(signer) != {"type", "key"}:
            raise ValidationFailure(f"{label}: an ssh signer is exactly {{ type, key }}")
        return ("ssh", signer["key"])
    if kind == "gpg":
        if not isinstance(signer.get("fingerprint"), str) or set(signer) != {"type", "fingerprint"}:
            raise ValidationFailure(f"{label}: a gpg signer is exactly {{ type, fingerprint }}")
        return ("gpg", signer["fingerprint"])
    raise ValidationFailure(f"{label}: a signer type must be ssh or gpg")


def e1_signer_identity(signer: dict[str, Any]) -> tuple[str, str]:
    """The section 12.1 matching identity of a shape-checked signer: key type
    plus base64 key material for `ssh` — the trailing OpenSSH comment is not
    part of the identity — and the fingerprint for `gpg`."""
    if signer["type"] == "ssh":
        fields = signer["key"].split()
        if len(fields) >= 2:
            return ("ssh", f"{fields[0]} {fields[1]}")
        return ("ssh", signer["key"])
    return ("gpg", signer["fingerprint"])


def e1_check_signer_map(value: Any, knob_validator: Any, label: str) -> None:
    """Every allowlist map in the vectors MUST satisfy the `source_signers`
    grammar of manager-config-v2, so the vectors cannot drift from the
    schema's closed entry shapes."""
    if not isinstance(value, dict):
        raise ValidationFailure(f"{label}: a signer map must be an object")
    instance: dict[str, Any] = {
        "schema_version": 2, "skills_root": "./skills", "projects": {},
        "environments": {"source_signers": value},
    }
    errors = list(knob_validator.iter_errors(instance))
    semantic = manager_config_semantic_error(instance) if not errors else None
    if errors or semantic is not None:
        detail = errors[0].message if errors else semantic
        raise ValidationFailure(f"{label}: source_signers map violates the manager-config-v2 grammar ({detail})")


def e1_check_signature(value: Any, label: str) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValidationFailure(f"{label}: a signature must be an object or null")
    if set(value) != {"signer", "valid"}:
        raise ValidationFailure(f"{label}: a signature is exactly {{ signer, valid }}")
    e1_check_signer_shape(value.get("signer"), label)
    if value.get("valid") is not True and value.get("valid") is not False:
        raise ValidationFailure(f"{label}: a signature valid flag must be a boolean")
    return value


def e1_expected_verification(case: dict[str, Any]) -> tuple[str, str | None, str | None, bool, list[dict[str, str]]]:
    """Recompute the section 1.4 verdict from the declared inputs: the
    allowlist presence, the require flag, and the top candidate's two
    signatures. Only the top candidate is ever consulted: a verification
    failure refuses, it never falls through to a lower candidate."""
    label = f"source-signers case {case.get('name')}"
    kind = case.get("source_kind")
    if kind not in ("git", "path"):
        raise ValidationFailure(f"{label}: source_kind must be git or path")
    allowlist = case.get("allowlist")
    if allowlist is not None and not isinstance(allowlist, list):
        raise ValidationFailure(f"{label}: allowlist must be an array or null")
    require = case.get("require_source_signers")
    if require is not True and require is not False:
        raise ValidationFailure(f"{label}: require_source_signers must be a boolean")
    candidates = case.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValidationFailure(f"{label}: candidates must be a non-empty array")
    for candidate in candidates:
        if not isinstance(candidate, dict) or not isinstance(candidate.get("version"), str):
            raise ValidationFailure(f"{label}: a candidate carries a version string")
        form = candidate.get("form")
        if form not in ("range", "tag", "revision", "path"):
            raise ValidationFailure(f"{label}: a candidate form must be range, tag, revision, or path")
        tag, commit = candidate.get("tag"), candidate.get("commit")
        if form == "path":
            if tag is not None or commit is not None:
                raise ValidationFailure(f"{label}: a path candidate carries no tag or commit")
        elif form == "revision":
            if tag is not None or not isinstance(commit, str):
                raise ValidationFailure(f"{label}: a revision candidate carries a commit and no tag")
            if candidate.get("tag_signature") is not None:
                raise ValidationFailure(f"{label}: a revision selection carries no tag, so tag-only signature evidence cannot satisfy the check")
        elif not isinstance(tag, str) or not isinstance(commit, str):
            raise ValidationFailure(f"{label}: a range or tag candidate carries a tag and a commit")
        e1_check_signature(candidate.get("tag_signature"), label)
        e1_check_signature(candidate.get("commit_signature"), label)
    if kind == "path":
        if case.get("source") is not None or allowlist is not None:
            raise ValidationFailure(f"{label}: a path source carries no source identity and no allowlist")
        return ("accepted", None, candidates[0]["version"], True, [])
    top = candidates[0]
    signatures = [
        signature
        for signature in (top.get("tag_signature"), top.get("commit_signature"))
        if signature is not None
    ]
    for item in signatures:
        e1_check_signer_shape(item["signer"], label)
    seen = sorted({e1_signer_identity(item["signer"]) for item in signatures})
    signers_seen = [
        {"type": kind, "key": identity} if kind == "ssh" else {"type": kind, "fingerprint": identity}
        for kind, identity in seen
    ]
    if allowlist is None:
        if require:
            return ("refused", E1_DIAG_MISSING, None, False, signers_seen)
        return ("accepted", None, top["version"], True, signers_seen)
    for entry in allowlist:
        e1_check_signer_shape(entry, label)
    allowed = {e1_signer_identity(entry) for entry in allowlist}
    if not signatures:
        return ("refused", E1_DIAG_UNSIGNED, None, False, signers_seen)
    if any(item["valid"] and e1_signer_identity(item["signer"]) in allowed for item in signatures):
        return ("accepted", None, top["version"], True, signers_seen)
    return ("refused", E1_DIAG_REJECTED, None, False, signers_seen)


def e1_expected_merge(case: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Recompute the section 12.2 effective allowlist: a locked map wins per
    source with a warning on overlap, an unlocked map is a default the
    machine knob replaces whole."""
    label = f"source-signers case {case.get('name')}"
    locked = case.get("locked")
    if locked is not True and locked is not False:
        raise ValidationFailure(f"{label}: locked must be a boolean")
    system = case.get("system")
    machine = case.get("machine")
    if not isinstance(system, dict) or (machine is not None and not isinstance(machine, dict)):
        raise ValidationFailure(f"{label}: system must be an object and machine an object or null")
    if locked:
        effective = dict(system)
        warnings = sorted(machine) if machine else []
        warnings = [source for source in warnings if source in system]
        if machine:
            for source, entries in machine.items():
                if source not in effective:
                    effective[source] = entries
        return effective, warnings
    return (machine if machine is not None else system), []


def e1_expected_posture(case: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    """Recompute the section 12 signer rows: one per lock member source with
    the enforced/unconfigured/required-missing state, the verified signer or
    `unknown`, and the currency the re-verification decides."""
    label = f"source-signers case {case.get('name')}"
    members = case.get("members")
    if not isinstance(members, list) or not members:
        raise ValidationFailure(f"{label}: members must be a non-empty array")
    sources: set[str] = set()
    for member in members:
        if not isinstance(member, dict) or member.get("kind") not in E1_MEMBER_KINDS:
            raise ValidationFailure(f"{label}: a member carries a kind of context, mcp, or skill")
        if not isinstance(member.get("name"), str):
            raise ValidationFailure(f"{label}: a member carries a name")
        source = member.get("source")
        if source is not None:
            if not isinstance(source, str):
                raise ValidationFailure(f"{label}: a member source must be a string or null")
            sources.add(source)
    allowlists = case.get("allowlists")
    if not isinstance(allowlists, dict):
        raise ValidationFailure(f"{label}: allowlists must be an object")
    require = case.get("require_source_signers")
    if require is not True and require is not False:
        raise ValidationFailure(f"{label}: require_source_signers must be a boolean")
    local = case.get("local")
    if not isinstance(local, dict):
        raise ValidationFailure(f"{label}: local must be an object")
    rows: list[dict[str, Any]] = []
    for source in sorted(sources):
        if source in allowlists:
            if source not in local:
                raise ValidationFailure(f"{label}: an enforced source needs its local re-verification")
            verdict = local[source].get("verdict") if isinstance(local[source], dict) else None
            if verdict == "verified":
                signer = local[source].get("signer")
                e1_check_signer_shape(signer, label)
                for entry in allowlists[source]:
                    e1_check_signer_shape(entry, label)
                if e1_signer_identity(signer) not in {
                    e1_signer_identity(entry) for entry in allowlists[source]
                }:
                    raise ValidationFailure(f"{label}: the verified signer must sit in the source allowlist")
                rows.append({"source": source, "state": "enforced", "signer": signer, "current": True})
            elif verdict == "unknown":
                rows.append({"source": source, "state": "enforced", "signer": "unknown", "current": True})
            elif verdict == "fails":
                rows.append({"source": source, "state": "enforced", "signer": "unknown", "current": False})
            else:
                raise ValidationFailure(f"{label}: a local verdict must be verified, unknown, or fails")
        elif require:
            rows.append({"source": source, "state": "required-missing", "signer": None, "current": True})
        else:
            rows.append({"source": source, "state": "unconfigured", "signer": None, "current": True})
    if set(local) != {source for source in sources if source in allowlists}:
        raise ValidationFailure(f"{label}: local covers exactly the enforced sources")
    return rows, require


def e1_member_pin(member: dict[str, Any], label: str) -> tuple[str, str]:
    """A lock member pin is exactly one of `commit` or `state_sha256`; return
    its hex and its delta-line spelling."""
    has_commit = isinstance(member.get("commit"), str)
    has_state = isinstance(member.get("state_sha256"), str)
    if has_commit == has_state:
        raise ValidationFailure(f"{label}: a member carries exactly one of commit or state_sha256")
    if has_commit:
        if re.fullmatch(r"[0-9a-f]{40}", member["commit"]) is None:
            raise ValidationFailure(f"{label}: a commit pin is 40 lowercase hex")
        return member["commit"], f"commit:{member['commit']}"
    if re.fullmatch(r"[0-9a-f]{64}", member["state_sha256"]) is None:
        raise ValidationFailure(f"{label}: a state pin is 64 lowercase hex")
    return member["state_sha256"], f"state:{member['state_sha256']}"


def e1_check_lock_members(value: Any, label: str) -> dict[tuple[str, str], dict[str, Any]]:
    if not isinstance(value, list):
        raise ValidationFailure(f"{label}: lock members must be an array")
    members: dict[tuple[str, str], dict[str, Any]] = {}
    for member in value:
        if not isinstance(member, dict) or member.get("kind") not in E1_MEMBER_KINDS:
            raise ValidationFailure(f"{label}: a member carries a kind of context, mcp, or skill")
        if not isinstance(member.get("name"), str):
            raise ValidationFailure(f"{label}: a member carries a name")
        version = member.get("version")
        if version is not None and not isinstance(version, str):
            raise ValidationFailure(f"{label}: a member version must be a string or null")
        e1_member_pin(member, label)
        key = (member["kind"], member["name"])
        if key in members:
            raise ValidationFailure(f"{label}: a lock names one member per kind and name")
        members[key] = member
    return members


def e1_check_snapshots(
    value: Any,
    old: dict[tuple[str, str], dict[str, Any]],
    new: dict[tuple[str, str], dict[str, Any]],
    label: str,
    mcp_validator: Any,
) -> dict[str, Any]:
    """Snapshots cover exactly the old and new member pins; an mcp snapshot
    is a presence-preserving declaration object — a real `server` object as
    the lock and the materialization read it, with optional fields absent
    rather than padded — validated through the agent-mcp-v1 Draft 2020-12
    entry, so absent and present stay distinct inputs to the section 9.2
    canonical-byte comparison."""
    if not isinstance(value, dict):
        raise ValidationFailure(f"{label}: snapshots must be an object")
    for pin, snapshot in value.items():
        if not isinstance(snapshot, dict):
            raise ValidationFailure(f"{label}: a snapshot must be an object")
        modules = snapshot.get("system_modules")
        if not isinstance(modules, list):
            raise ValidationFailure(f"{label}: snapshot system_modules must be an array")
        for module in modules:
            if (
                not isinstance(module, dict)
                or not isinstance(module.get("path"), str)
                or not isinstance(module.get("environments"), list)
                or any(not isinstance(item, str) for item in module["environments"])
                or not isinstance(module.get("bytes"), str)
            ):
                raise ValidationFailure(f"{label}: a system module is {{ path, environments, bytes }}")
        mcp = snapshot.get("mcp")
        if mcp is not None:
            if not isinstance(mcp, dict):
                raise ValidationFailure(f"{label}: an mcp snapshot is a declaration object")
            if mcp.get("transport") == "stdio":
                if "url" in mcp:
                    raise ValidationFailure(f"{label}: a stdio declaration carries no url")
                if not isinstance(mcp.get("command"), str):
                    raise ValidationFailure(f"{label}: a stdio declaration carries its command")
                if not isinstance(mcp.get("args"), list) or any(
                    not isinstance(item, str) for item in mcp["args"]
                ):
                    raise ValidationFailure(f"{label}: a stdio declaration carries its args array")
            elif mcp.get("transport") == "http":
                if "command" in mcp or "args" in mcp:
                    raise ValidationFailure(f"{label}: an http declaration carries no command or args")
                if not isinstance(mcp.get("url"), str):
                    raise ValidationFailure(f"{label}: an http declaration carries its url")
            else:
                raise ValidationFailure(f"{label}: a declaration transport is stdio or http")
            if "env_names" in mcp and (
                not isinstance(mcp.get("env_names"), list)
                or any(not isinstance(item, str) for item in mcp["env_names"])
            ):
                raise ValidationFailure(f"{label}: a declaration env_names, when present, is an array of names")
            if "environments" in mcp and (
                not isinstance(mcp.get("environments"), list)
                or any(not isinstance(item, str) for item in mcp["environments"])
            ):
                raise ValidationFailure(f"{label}: a declaration environments, when present, is a selector array")
            manifest = {
                "schema_version": 1,
                "name": "e1-fixture",
                "version": "1.0.0",
                "server": mcp,
            }
            errors = list(mcp_validator.iter_errors(manifest))
            if errors:
                raise ValidationFailure(
                    f"{label}: an mcp snapshot is a declaration valid under agent-mcp-v1 ({errors[0].message})"
                )
    pins = {e1_member_pin(member, label)[0] for member in [*old.values(), *new.values()]}
    if set(value) != pins:
        raise ValidationFailure(f"{label}: snapshots cover exactly the old and new member pins")
    kinds = {e1_member_pin(member, label)[0]: member["kind"] for member in [*old.values(), *new.values()]}
    for pin, snapshot in value.items():
        if kinds[pin] == "mcp":
            if snapshot["mcp"] is None or snapshot["system_modules"]:
                raise ValidationFailure(f"{label}: an mcp member snapshot carries its declaration and no system module")
        elif snapshot["mcp"] is not None:
            raise ValidationFailure(f"{label}: only an mcp member snapshot carries a declaration")
    return value


def e1_system_inventory(snapshot: dict[str, Any]) -> list[tuple[str, tuple[str, ...], str]]:
    return sorted(
        (module["path"], tuple(sorted(module["environments"])), module["bytes"])
        for module in snapshot["system_modules"]
    )


def e1_mcp_changed(old: dict[str, Any], new: dict[str, Any]) -> bool:
    """The section 9.2 MCP trigger: the CCJ-1 bytes of the moved member's
    declaration object differ — the complete declaration as the
    lock/materialization reads it, array order included, with no
    field narrowed out and no set-comparison exception."""
    return ccj1_bytes(old) != ccj1_bytes(new)


def e1_expected_delta(
    old: dict[tuple[str, str], dict[str, Any]], new: dict[tuple[str, str], dict[str, Any]], snapshots: dict[str, Any], label: str
) -> tuple[list[str], list[str]]:
    """Recompute the section 9.2 delta lines and the confirmation trigger:
    added, removed, and moved members in lock order, and the members whose
    system-module inventory or MCP declaration canonical bytes the delta
    introduces or changes."""
    lines: list[str] = []
    for kind, name in sorted(set(old) | set(new)):
        if (kind, name) not in old:
            member = new[(kind, name)]
            version = member["version"] if isinstance(member.get("version"), str) else "-"
            lines.append(f"lock-delta added {kind} {name} {version} {e1_member_pin(member, label)[1]}")
        elif (kind, name) not in new:
            member = old[(kind, name)]
            version = member["version"] if isinstance(member.get("version"), str) else "-"
            lines.append(f"lock-delta removed {kind} {name} {version} {e1_member_pin(member, label)[1]}")
        else:
            before, after = old[(kind, name)], new[(kind, name)]
            if before.get("version") == after.get("version") and e1_member_pin(before, label) == e1_member_pin(after, label):
                continue
            from_version = before["version"] if isinstance(before.get("version"), str) else "-"
            to_version = after["version"] if isinstance(after.get("version"), str) else "-"
            from_pin = e1_member_pin(before, label)[1]
            to_pin = e1_member_pin(after, label)[1]
            lines.append(f"lock-delta moved {kind} {name} {from_version} → {to_version} {from_pin} → {to_pin}")
    trigger: dict[tuple[str, str], str] = {}
    for key, member in new.items():
        if key in old:
            continue
        snapshot = snapshots[e1_member_pin(member, label)[0]]
        if member["kind"] == "context" and snapshot["system_modules"]:
            trigger[key] = member["name"]
        elif member["kind"] == "mcp":
            trigger[key] = member["name"]
    for key in new.keys() & old.keys():
        before, after = old[key], new[key]
        if before.get("version") == after.get("version") and e1_member_pin(before, label) == e1_member_pin(after, label):
            continue
        kind = key[0]
        before_snapshot = snapshots[e1_member_pin(before, label)[0]]
        after_snapshot = snapshots[e1_member_pin(after, label)[0]]
        if kind == "context" and e1_system_inventory(before_snapshot) != e1_system_inventory(after_snapshot):
            trigger[key] = after["name"]
        elif kind == "mcp" and e1_mcp_changed(before_snapshot["mcp"], after_snapshot["mcp"]):
            trigger[key] = after["name"]
    return lines, [trigger[key] for key in sorted(trigger)]


def e1_revision_outcomes(trigger: list[str], flag: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    revision_a: dict[str, Any] = {
        "diagnostic": E1_DIAG_DELTA if trigger else None,
        "hint": E1_HINT_DELTA if trigger else None,
        "proceeds": True,
        "lock_published": True,
    }
    if trigger and not flag:
        revision_b: dict[str, Any] = {"diagnostic": E1_DIAG_CONFIRM, "proceeds": False, "lock_published": False}
    else:
        revision_b = {"diagnostic": None, "proceeds": True, "lock_published": True}
    return revision_a, revision_b


def e1_expected_confirmation_posture(revision: Any, label: str) -> dict[str, str]:
    """The section 12 update-confirmation row: the active revision spelled as
    section 9.2 spells the rollout, with the behaviour that revision gives a
    triggered delta."""
    if revision not in E1_CONFIRMATION_BEHAVIOR:
        raise ValidationFailure(f"{label}: update_confirmation_revision must be A-warning or B-flip")
    return {"revision": revision, "behavior": E1_CONFIRMATION_BEHAVIOR[revision]}


def validate_environments_source_signers_vectors(
    vector: Any = None, suite_root: Path | None = None, schema: Any = None
) -> None:
    """Recompute the E1 signer-verification, merge, posture, update-delta,
    reinstall, and update-confirmation-posture expectations.

    Every positive case is derived from its declared inputs — the
    verification verdict from the allowlist, the require flag, and the top
    candidate's signatures; the effective allowlist from the locked and
    machine maps; the status rows from the lock sources and the local
    re-verification; the delta lines, the trigger, and both rollout
    revisions' outcomes from the old and new locks, identically for the
    reinstall path; the update-confirmation row from the active revision.
    Every negative case must carry an observation that genuinely contradicts
    the recomputed rule, so a repaired observation or a flipped flag fails
    here.
    """
    root = SUITE if suite_root is None else Path(suite_root)
    if vector is None:
        vector = load_json(root / "vectors" / "environments-source-signers.json")
    if (
        vector.get("schema_version") != 1
        or vector.get("protocol_version") != PROTOCOL_VERSION
        or vector.get("capability") != "agent-environments"
        or vector.get("capability_revision") != 1
    ):
        raise ValidationFailure("source-signers vector has the wrong capability identity")
    if vector.get("revision_a") != E1_REVISION_A or vector.get("revision_b") != E1_REVISION_B:
        raise ValidationFailure("source-signers revisions must pin exactly the warning and flip releases")

    registry, paths = schema_registry()
    if schema is None:
        schema = load_json(paths[MANAGER_CONFIG_SCHEMAS[2]])
    knob_validator = Draft202012Validator(schema, registry=registry)
    mcp_validator = Draft202012Validator(load_json(SCHEMAS / "agent-mcp-v1.schema.json"), registry=registry)

    verification = named_cases(vector.get("verification_cases"), "source-signers verification")
    if set(verification) != E1_VERIFICATION_CASES:
        raise ValidationFailure("source-signers verification case inventory is not exact")
    for name, case in verification.items():
        label = f"source-signers case {name}"
        allowlist = case.get("allowlist")
        if allowlist is not None:
            e1_check_signer_map({"vector": allowlist}, knob_validator, label)
        verdict, diagnostic, selected, lock_written, signers_seen = e1_expected_verification(case)
        if name in E1_VERIFICATION_NEGATIVE_CASES:
            if case.get("conforming") is not False or not case.get("reason"):
                raise ValidationFailure(f"{label}: a negative needs conforming=false and a reason")
            observed = case.get("observed")
            if not isinstance(observed, dict):
                raise ValidationFailure(f"{label}: a negative needs its observed outcome")
            if (
                observed.get("verdict") == verdict
                and observed.get("diagnostic") == diagnostic
                and observed.get("selected") == selected
                and observed.get("lock_written") == lock_written
            ):
                raise ValidationFailure(f"{label}: the observation no longer violates the verification rule")
            continue
        if case.get("conforming") is False:
            raise ValidationFailure(f"{label}: a positive case must not carry conforming=false")
        expected = case.get("expected")
        if not isinstance(expected, dict):
            raise ValidationFailure(f"{label}: a positive case needs its expected outcome")
        if (
            expected.get("verdict") != verdict
            or expected.get("diagnostic") != diagnostic
            or expected.get("selected") != selected
            or expected.get("lock_written") != lock_written
            or expected.get("signers_seen") != signers_seen
        ):
            raise ValidationFailure(
                f"{label}: expected is not the verification rule ({verdict}/{diagnostic}/{selected})"
            )

    merge = named_cases(vector.get("merge_cases"), "source-signers merge")
    if set(merge) != E1_MERGE_CASES:
        raise ValidationFailure("source-signers merge case inventory is not exact")
    for name, case in merge.items():
        label = f"source-signers case {name}"
        e1_check_signer_map(case.get("system"), knob_validator, label)
        if case.get("machine") is not None:
            e1_check_signer_map(case.get("machine"), knob_validator, label)
        effective, warnings = e1_expected_merge(case)
        expected = case.get("expected")
        if not isinstance(expected, dict):
            raise ValidationFailure(f"{label}: a merge case needs its expected outcome")
        if expected.get("effective") != effective or expected.get("warnings") != warnings:
            raise ValidationFailure(f"{label}: expected is not the section 12.2 merge rule")

    posture = named_cases(vector.get("posture_cases"), "source-signers posture")
    if set(posture) != E1_POSTURE_CASES:
        raise ValidationFailure("source-signers posture case inventory is not exact")
    for name, case in posture.items():
        label = f"source-signers case {name}"
        e1_check_signer_map(case.get("allowlists"), knob_validator, label)
        rows, require = e1_expected_posture(case)
        expected = case.get("expected")
        if not isinstance(expected, dict):
            raise ValidationFailure(f"{label}: a posture case needs its expected outcome")
        if expected.get("rows") != rows or expected.get("require_source_signers") != require:
            raise ValidationFailure(f"{label}: expected is not the section 12 posture rule")

    delta = named_cases(vector.get("delta_cases"), "source-signers delta")
    if set(delta) != E1_DELTA_CASES:
        raise ValidationFailure("source-signers delta case inventory is not exact")
    for name, case in delta.items():
        label = f"source-signers case {name}"
        flag = case.get("flag")
        if flag is not True and flag is not False:
            raise ValidationFailure(f"{label}: flag must be a boolean")
        old = e1_check_lock_members(case.get("old_members"), label)
        new = e1_check_lock_members(case.get("new_members"), label)
        snapshots = e1_check_snapshots(case.get("snapshots"), old, new, label, mcp_validator)
        lines, trigger = e1_expected_delta(old, new, snapshots, label)
        revision_a, revision_b = e1_revision_outcomes(trigger, flag)
        if name in E1_DELTA_NEGATIVE_CASES:
            if case.get("conforming") is not False or not case.get("reason"):
                raise ValidationFailure(f"{label}: a negative needs conforming=false and a reason")
            claimed = case.get("claimed")
            if not isinstance(claimed, dict) or claimed.get("revision") not in ("revision-a", "revision-b"):
                raise ValidationFailure(f"{label}: a negative claims one revision outcome")
            ruled = revision_a if claimed["revision"] == "revision-a" else revision_b
            matches = (
                claimed.get("diagnostic") == ruled["diagnostic"]
                and claimed.get("proceeds") == ruled["proceeds"]
                and claimed.get("lock_published") == ruled["lock_published"]
            )
            if claimed["revision"] == "revision-a":
                matches = matches and claimed.get("hint") == ruled["hint"]
            if matches:
                raise ValidationFailure(f"{label}: the claimed outcome no longer violates the confirmation rule")
            continue
        if case.get("conforming") is False:
            raise ValidationFailure(f"{label}: a positive case must not carry conforming=false")
        expected = case.get("expected")
        if not isinstance(expected, dict):
            raise ValidationFailure(f"{label}: a positive case needs its expected outcome")
        if (
            expected.get("lines") != lines
            or expected.get("trigger") != trigger
            or expected.get("revision_a") != revision_a
            or expected.get("revision_b") != revision_b
        ):
            raise ValidationFailure(f"{label}: expected is not the section 9.2 delta rule")

    runs = named_cases(vector.get("all_cases"), "source-signers all")
    if set(runs) != E1_ALL_CASES:
        raise ValidationFailure("source-signers --all case inventory is not exact")
    for name, case in runs.items():
        label = f"source-signers case {name}"
        flag = case.get("flag")
        if flag is not True and flag is not False:
            raise ValidationFailure(f"{label}: flag must be a boolean")
        profiles = case.get("profiles")
        if not isinstance(profiles, list) or len(profiles) < 2:
            raise ValidationFailure(f"{label}: an --all case runs at least two profiles")
        if len({item.get("profile") for item in profiles if isinstance(item, dict)}) != len(profiles):
            raise ValidationFailure(f"{label}: an --all case names every profile once")
        expected = case.get("expected")
        if not isinstance(expected, dict):
            raise ValidationFailure(f"{label}: an --all case needs its expected outcome")
        expected_profiles = expected.get("profiles")
        if not isinstance(expected_profiles, list) or len(expected_profiles) != len(profiles):
            raise ValidationFailure(f"{label}: an --all case expects one outcome per profile")
        stopped_a: str | None = None
        stopped_b: str | None = None
        for item, want in zip(profiles, expected_profiles):
            profile_label = f"{label} profile {item.get('profile')}"
            old = e1_check_lock_members(item.get("old_members"), profile_label)
            new = e1_check_lock_members(item.get("new_members"), profile_label)
            snapshots = e1_check_snapshots(item.get("snapshots"), old, new, profile_label, mcp_validator)
            lines, trigger = e1_expected_delta(old, new, snapshots, profile_label)
            revision_a, revision_b = e1_revision_outcomes(trigger, flag)
            if not isinstance(want, dict) or want.get("profile") != item.get("profile"):
                raise ValidationFailure(f"{profile_label}: the expected outcome names its profile")
            if want.get("lines") != lines or want.get("trigger") != trigger:
                raise ValidationFailure(f"{profile_label}: expected is not the section 9.2 delta rule")
            if want.get("revision_a") != revision_a:
                raise ValidationFailure(f"{profile_label}: revision A always proceeds")
            if stopped_b is not None:
                if want.get("revision_b") != "untouched":
                    raise ValidationFailure(f"{profile_label}: a profile past the refusal stays untouched")
            else:
                if want.get("revision_b") != revision_b:
                    raise ValidationFailure(f"{profile_label}: expected is not the revision B rule")
                if not revision_b["proceeds"]:
                    stopped_b = item.get("profile")
        stopped = expected.get("stopped")
        if not isinstance(stopped, dict) or stopped.get("revision_a") != stopped_a or stopped.get("revision_b") != stopped_b:
            raise ValidationFailure(f"{label}: stopped names the first refusing profile per revision")

    reinstalls = named_cases(vector.get("reinstall_cases"), "source-signers reinstall")
    if set(reinstalls) != E1_REINSTALL_CASES:
        raise ValidationFailure("source-signers reinstall case inventory is not exact")
    for name, case in reinstalls.items():
        label = f"source-signers case {name}"
        if case.get("operation") != "profile install":
            raise ValidationFailure(f"{label}: a reinstall case runs the profile install path")
        flag = case.get("flag")
        if flag is not True and flag is not False:
            raise ValidationFailure(f"{label}: flag must be a boolean")
        old = e1_check_lock_members(case.get("old_members"), label)
        new = e1_check_lock_members(case.get("new_members"), label)
        snapshots = e1_check_snapshots(case.get("snapshots"), old, new, label, mcp_validator)
        lines, trigger = e1_expected_delta(old, new, snapshots, label)
        revision_a, revision_b = e1_revision_outcomes(trigger, flag)
        expected = case.get("expected")
        if not isinstance(expected, dict):
            raise ValidationFailure(f"{label}: a reinstall case needs its expected outcome")
        if (
            expected.get("lines") != lines
            or expected.get("trigger") != trigger
            or expected.get("revision_a") != revision_a
            or expected.get("revision_b") != revision_b
        ):
            raise ValidationFailure(f"{label}: expected is not the section 9.2 reinstall rule")

    confirmations = named_cases(vector.get("confirmation_posture_cases"), "source-signers confirmation posture")
    if set(confirmations) != E1_CONFIRMATION_POSTURE_CASES:
        raise ValidationFailure("source-signers confirmation-posture case inventory is not exact")
    for name, case in confirmations.items():
        label = f"source-signers case {name}"
        row = e1_expected_confirmation_posture(case.get("update_confirmation_revision"), label)
        expected = case.get("expected")
        if not isinstance(expected, dict):
            raise ValidationFailure(f"{label}: a confirmation-posture case needs its expected outcome")
        if expected.get("row") != row:
            raise ValidationFailure(f"{label}: expected is not the section 12 update-confirmation row")


# ---------------------------------------------------------------------------
# Sections 4, 8.4, 10.1, 10.4, 12: protected-boundary contract (S5)


S5_DIAG_UNTRUSTED = "environment_store_untrusted"
S5_OUTCOME_WOULD_REBUILD = "would-rebuild-untrusted-store"
S5_DIAG_REPAIR_FAILED = "environment_repair_failed"
S5_DIAG_HOME_STALE = "environment_home_stale"
S5_DIAG_MARKER_UNREADABLE = "environment_marker_unreadable"

S5_BOUNDARY_CHECKS = ("ownership", "permissions", "containment", "regular_types", "link_safety")
S5_OBJECTS = ("environments-root", "store-root", "lock-file", "marker-file", "store-entry")
S5_ENCLOSING_OBJECTS = ("environments-root", "store-root")
S5_SURFACES = ("system-prompt", "root-context")
S5_ENTRY_KINDS = ("git", "path", "local")
S5_HOME_STATES = ("current", "stale-old-marker", "unprovisioned", "unreadable-marker")

S5_RESOLVE_CASES = {
    "intact-resolve-emits-fragment",
    "swapped-system-prompt-bytes-untrusted",
    "swapped-root-context-bytes-untrusted",
    "symlinked-entry-root-untrusted",
    "wrong-ownership-untrusted",
    "wrong-permissions-untrusted",
    "containment-escape-untrusted",
    "non-regular-component-untrusted",
    "lock-file-wrong-owner-untrusted",
    "marker-symlink-untrusted",
    "environments-root-wrong-owner-untrusted",
    "store-root-symlinked-untrusted",
    "intact-updated-store-old-marker-stale",
    "swapped-updated-store-old-marker-untrusted",
    "unprovisioned-intact-stale",
    "unprovisioned-swapped-untrusted",
    "unreadable-marker-non-current",
    "swapped-bytes-emits-fragment",
    "untrusted-reported-current",
    "untrusted-without-diagnostic",
}
S5_RESOLVE_NEGATIVE_CASES = {
    "swapped-bytes-emits-fragment",
    "untrusted-reported-current",
    "untrusted-without-diagnostic",
}
S5_DRY_RUN_CASES = {
    "dry-run-untrusted-reports-would-rebuild",
    "dry-run-intact-plans-nothing",
    "dry-run-enclosing-no-rebuild",
    "dry-run-mutates",
}
S5_DRY_RUN_NEGATIVE_CASES = {"dry-run-mutates"}
S5_REPAIR_CASES = {
    "repair-rebuilds-git-entry-from-snapshot",
    "repair-path-entry-cannot-rebuild",
    "repair-local-entry-cannot-rebuild",
    "repair-rebuilds-entry-boundary-failure",
    "repair-enclosing-refuses-no-rebuild",
    "repair-stale-old-marker-succeeds",
    "repair-swapped-old-marker-never-adopted",
    "repair-unprovisioned-intact-provisions",
    "repair-unprovisioned-swapped-rebuilds",
    "repair-reapplies-untrusted",
}
S5_REPAIR_NEGATIVE_CASES = {"repair-reapplies-untrusted"}
S5_STATUS_CASES = {
    "status-intact-current",
    "status-names-failing-check",
    "status-enclosing-names-boundary",
    "status-hides-failing-check",
}
S5_STATUS_NEGATIVE_CASES = {"status-hides-failing-check"}

# Each named case is pinned to its discriminating inputs: the object that
# fails, the check that fails, the home state, and — for a pin-hash failure
# on a store entry — the swapped surface. A corpus where a named branch no
# longer exercises its check (for example the five boundary branches
# collapsed to ownership-only) is refused.
S5_RESOLVE_PIN: dict[str, dict[str, Any]] = {
    "intact-resolve-emits-fragment": {"object": "store-entry", "check": None, "home": "current", "surface": None},
    "swapped-system-prompt-bytes-untrusted": {"object": "store-entry", "check": "pin_hash", "home": "current", "surface": "system-prompt"},
    "swapped-root-context-bytes-untrusted": {"object": "store-entry", "check": "pin_hash", "home": "current", "surface": "root-context"},
    "symlinked-entry-root-untrusted": {"object": "store-entry", "check": "link_safety", "home": "current", "surface": None},
    "wrong-ownership-untrusted": {"object": "store-entry", "check": "ownership", "home": "current", "surface": None},
    "wrong-permissions-untrusted": {"object": "store-entry", "check": "permissions", "home": "current", "surface": None},
    "containment-escape-untrusted": {"object": "store-entry", "check": "containment", "home": "current", "surface": None},
    "non-regular-component-untrusted": {"object": "store-entry", "check": "regular_types", "home": "current", "surface": None},
    "lock-file-wrong-owner-untrusted": {"object": "lock-file", "check": "ownership", "home": "current", "surface": None},
    "marker-symlink-untrusted": {"object": "marker-file", "check": "link_safety", "home": "current", "surface": None},
    "environments-root-wrong-owner-untrusted": {"object": "environments-root", "check": "ownership", "home": "current", "surface": None},
    "store-root-symlinked-untrusted": {"object": "store-root", "check": "link_safety", "home": "current", "surface": None},
    "intact-updated-store-old-marker-stale": {"object": "store-entry", "check": "home_currency", "home": "stale-old-marker", "surface": None},
    "swapped-updated-store-old-marker-untrusted": {"object": "store-entry", "check": "pin_hash", "home": "stale-old-marker", "surface": "system-prompt"},
    "unprovisioned-intact-stale": {"object": "store-entry", "check": None, "home": "unprovisioned", "surface": None},
    "unprovisioned-swapped-untrusted": {"object": "store-entry", "check": "pin_hash", "home": "unprovisioned", "surface": "root-context"},
    "unreadable-marker-non-current": {"object": "marker-file", "check": None, "home": "unreadable-marker", "surface": None},
    "swapped-bytes-emits-fragment": {"object": "store-entry", "check": "pin_hash", "home": "current", "surface": "system-prompt"},
    "untrusted-reported-current": {"object": "store-entry", "check": "ownership", "home": "current", "surface": None},
    "untrusted-without-diagnostic": {"object": "store-entry", "check": "link_safety", "home": "current", "surface": None},
}
S5_DRY_RUN_PIN: dict[str, dict[str, Any]] = {
    "dry-run-untrusted-reports-would-rebuild": {"object": "store-entry", "check": "ownership", "home": "current", "surface": None},
    "dry-run-intact-plans-nothing": {"object": "store-entry", "check": None, "home": "current", "surface": None},
    "dry-run-enclosing-no-rebuild": {"object": "store-root", "check": "ownership", "home": "current", "surface": None},
    "dry-run-mutates": {"object": "store-entry", "check": "ownership", "home": "current", "surface": None},
}
S5_REPAIR_PIN: dict[str, dict[str, Any]] = {
    "repair-rebuilds-git-entry-from-snapshot": {"object": "store-entry", "check": "pin_hash", "kind": "git", "home": "current", "surface": "system-prompt"},
    "repair-path-entry-cannot-rebuild": {"object": "store-entry", "check": "ownership", "kind": "path", "home": "current", "surface": None},
    "repair-local-entry-cannot-rebuild": {"object": "store-entry", "check": "permissions", "kind": "local", "home": "current", "surface": None},
    "repair-rebuilds-entry-boundary-failure": {"object": "store-entry", "check": "ownership", "kind": "git", "home": "current", "surface": None},
    "repair-enclosing-refuses-no-rebuild": {"object": "store-root", "check": "ownership", "kind": "git", "home": "current", "surface": None},
    "repair-stale-old-marker-succeeds": {"object": "store-entry", "check": None, "kind": "git", "home": "stale-old-marker", "surface": None},
    "repair-swapped-old-marker-never-adopted": {"object": "store-entry", "check": "pin_hash", "kind": "git", "home": "stale-old-marker", "surface": "system-prompt"},
    "repair-unprovisioned-intact-provisions": {"object": "store-entry", "check": None, "kind": "git", "home": "unprovisioned", "surface": None},
    "repair-unprovisioned-swapped-rebuilds": {"object": "store-entry", "check": "pin_hash", "kind": "git", "home": "unprovisioned", "surface": "root-context"},
    "repair-reapplies-untrusted": {"object": "store-entry", "check": "ownership", "kind": "git", "home": "current", "surface": None},
}
S5_STATUS_PIN: dict[str, dict[str, Any]] = {
    "status-intact-current": {"object": "store-entry", "check": None, "home": "current", "surface": None},
    "status-names-failing-check": {"object": "store-entry", "check": "ownership", "home": "current", "surface": None},
    "status-enclosing-names-boundary": {"object": "store-root", "check": "ownership", "home": "current", "surface": None},
    "status-hides-failing-check": {"object": "store-entry", "check": "ownership", "home": "current", "surface": None},
}


def s5_check_inputs(case: dict[str, Any], name: str) -> dict[str, bool]:
    """Read the six §4/§10.1 store-trust inputs of one case.

    The five boundary checks plus the pin-hash comparison; each is a
    boolean, true when the check passes. Anything else is a malformed
    vector, not a verdict.
    """
    inputs: dict[str, bool] = {}
    for check in (*S5_BOUNDARY_CHECKS, "pin_hash_match"):
        value = case.get(check)
        if not isinstance(value, bool):
            raise ValidationFailure(f"store-boundary case {name}: {check} must be a boolean")
        inputs[check] = value
    return inputs


def s5_check_home(case: dict[str, Any], name: str) -> str:
    """Read the modeled home state: current, stale-old-marker, unprovisioned, or unreadable-marker."""
    home = case.get("home")
    if home not in S5_HOME_STATES:
        raise ValidationFailure(f"store-boundary case {name}: home must be one of {', '.join(S5_HOME_STATES)}")
    return str(home)


def s5_store_trusted(inputs: dict[str, bool]) -> tuple[bool, list[str]]:
    """Recompute the §4 store-trust verdict: every boundary check and the pin hash pass, else untrusted.

    Returns the verdict with the failing checks in §4 order, the pin-hash
    comparison last.
    """
    failing = [check for check in S5_BOUNDARY_CHECKS if not inputs[check]]
    if not inputs["pin_hash_match"]:
        failing.append("pin_hash")
    return (not failing, failing)


def s5_check_swap_shape(case: dict[str, Any], inputs: dict[str, bool], name: str) -> None:
    """A modeled byte swap breaks the pin hash, and only a swap does.

    `surface` names the entry file the swap touched (`system-prompt` or
    `root-context`) or is null when the case models no swap; a swap lives
    on a store entry, and only a store entry carries a pin hash.
    """
    surface = case.get("surface")
    if surface is None:
        if inputs["pin_hash_match"] is not True:
            raise ValidationFailure(f"store-boundary case {name}: a pin mismatch without a swap needs its surface")
    else:
        if surface not in S5_SURFACES:
            raise ValidationFailure(f"store-boundary case {name}: surface must be system-prompt, root-context, or null")
        if inputs["pin_hash_match"] is not False:
            raise ValidationFailure(f"store-boundary case {name}: a modeled swap breaks the pin hash")
        if case.get("object") != "store-entry":
            raise ValidationFailure(f"store-boundary case {name}: a modeled swap lives on a store entry")
    if case.get("object") != "store-entry" and inputs["pin_hash_match"] is not True:
        raise ValidationFailure(f"store-boundary case {name}: only a store entry carries a pin hash")


def s5_check_pin(pin: dict[str, Any], case: dict[str, Any], failing: list[str], home: str, name: str) -> None:
    """Bind a named case to its discriminating inputs: object, check, home, and surface.

    A named branch that no longer exercises its check — for example five
    boundary branches collapsed to ownership-only — is refused.
    """
    if case.get("object") != pin["object"]:
        raise ValidationFailure(f"store-boundary case {name}: object must be {pin['object']} for this branch")
    if home != pin["home"]:
        raise ValidationFailure(f"store-boundary case {name}: home must be {pin['home']} for this branch")
    if case.get("surface") != pin["surface"]:
        raise ValidationFailure(f"store-boundary case {name}: surface must be {pin['surface']!r} for this branch")
    expected = pin["check"]
    if expected is None:
        if failing:
            raise ValidationFailure(f"store-boundary case {name}: this branch models no failing store check")
    elif expected == "home_currency":
        if failing:
            raise ValidationFailure(f"store-boundary case {name}: this branch models intact store with a stale marker")
        if home != "stale-old-marker":
            raise ValidationFailure(f"store-boundary case {name}: home currency fails only for a stale old marker")
    elif expected not in failing:
        raise ValidationFailure(f"store-boundary case {name}: this branch must fail {expected}")
    elif len(failing) != 1:
        raise ValidationFailure(f"store-boundary case {name}: this branch isolates exactly its failing check")


def validate_environments_store_boundary_vectors(vector: Any = None) -> None:
    """Recompute every §4 protected-boundary verdict (§8.4, §10.1, §10.4, §12).

    Verification order is enclosing boundary → entries → pin hashes → home
    currency (§4, §10.1). Each named case is pinned to its discriminating
    inputs — the object, the failing check, the home state, and the swapped
    surface — so a corpus where a named branch no longer exercises its
    check is refused. Negatives carry a non-conforming observation that
    must still violate the recomputed rule.
    """
    if vector is None:
        vector = load_json(SUITE / "vectors" / "environments-store-boundary.json")
    if vector.get("capability") != "agent-environments" or vector.get("capability_revision") != 1:
        raise ValidationFailure("store-boundary vector has the wrong capability identity")
    pinned = vector.get("diagnostics")
    if (
        not isinstance(pinned, dict)
        or pinned.get("store_untrusted") != S5_DIAG_UNTRUSTED
        or pinned.get("dry_run_outcome") != S5_OUTCOME_WOULD_REBUILD
        or pinned.get("repair_failed") != S5_DIAG_REPAIR_FAILED
        or pinned.get("home_stale") != S5_DIAG_HOME_STALE
        or pinned.get("marker_unreadable") != S5_DIAG_MARKER_UNREADABLE
    ):
        raise ValidationFailure(
            "store-boundary diagnostics must pin environment_store_untrusted, "
            "would-rebuild-untrusted-store, environment_repair_failed, "
            "environment_home_stale, and environment_marker_unreadable"
        )

    resolve = named_cases(vector.get("resolve_cases"), "store-boundary resolve")
    if set(resolve) != S5_RESOLVE_CASES:
        raise ValidationFailure("store-boundary resolve case inventory is not exact")
    for name, case in resolve.items():
        if case.get("object") not in S5_OBJECTS:
            raise ValidationFailure(f"store-boundary case {name}: object must be one of {', '.join(S5_OBJECTS)}")
        inputs = s5_check_inputs(case, name)
        home = s5_check_home(case, name)
        s5_check_swap_shape(case, inputs, name)
        store_trusted, failing = s5_store_trusted(inputs)
        s5_check_pin(S5_RESOLVE_PIN[name], case, failing, home, name)
        if failing:
            expected_diag: str | None = S5_DIAG_UNTRUSTED
            expected_fragment = False
            expected_current = False
            expected_check: str | None = failing[0] if len(failing) == 1 else None
        elif home == "stale-old-marker":
            expected_diag = S5_DIAG_HOME_STALE
            expected_fragment = False
            expected_current = False
            expected_check = "home_currency"
        elif home == "unprovisioned":
            expected_diag = S5_DIAG_HOME_STALE
            expected_fragment = False
            expected_current = False
            expected_check = None
        elif home == "unreadable-marker":
            expected_diag = S5_DIAG_MARKER_UNREADABLE
            expected_fragment = False
            expected_current = False
            expected_check = None
        else:
            expected_diag = None
            expected_fragment = True
            expected_current = True
            expected_check = None
        if name in S5_RESOLVE_NEGATIVE_CASES:
            if case.get("conforming") is not False or not case.get("reason"):
                raise ValidationFailure(f"store-boundary case {name}: a negative needs conforming=false and a reason")
            if (
                case.get("diagnostic") == expected_diag
                and case.get("fragment_emitted") is expected_fragment
                and case.get("row_current") is expected_current
            ):
                raise ValidationFailure(f"store-boundary case {name}: the observation no longer violates the §10.1 rule")
            continue
        if case.get("conforming") is False:
            raise ValidationFailure(f"store-boundary case {name}: a positive case must not carry conforming=false")
        if case.get("diagnostic") != expected_diag:
            raise ValidationFailure(f"store-boundary case {name}: diagnostic is not the §10.1 rule ({expected_diag!r})")
        if case.get("fragment_emitted") is not expected_fragment:
            raise ValidationFailure(f"store-boundary case {name}: fragment verdict is not the §10.1 rule")
        if case.get("row_current") is not expected_current:
            raise ValidationFailure(f"store-boundary case {name}: currency is not the §10.1 rule")
        if case.get("failing_check") != expected_check:
            raise ValidationFailure(f"store-boundary case {name}: failing_check is not the §10.1 rule ({expected_check!r})")

    dry_run = named_cases(vector.get("dry_run_cases"), "store-boundary dry-run")
    if set(dry_run) != S5_DRY_RUN_CASES:
        raise ValidationFailure("store-boundary dry-run case inventory is not exact")
    for name, case in dry_run.items():
        if case.get("object") not in S5_OBJECTS:
            raise ValidationFailure(f"store-boundary case {name}: object must be one of {', '.join(S5_OBJECTS)}")
        inputs = s5_check_inputs(case, name)
        home = s5_check_home(case, name)
        s5_check_swap_shape(case, inputs, name)
        store_trusted, failing = s5_store_trusted(inputs)
        s5_check_pin(S5_DRY_RUN_PIN[name], case, failing, home, name)
        if store_trusted:
            expected_outcome = None
        elif case.get("object") in S5_ENCLOSING_OBJECTS:
            expected_outcome = None
        else:
            expected_outcome = S5_OUTCOME_WOULD_REBUILD
        if name in S5_DRY_RUN_NEGATIVE_CASES:
            if case.get("conforming") is not False or not case.get("reason"):
                raise ValidationFailure(f"store-boundary case {name}: a negative needs conforming=false and a reason")
            if case.get("mutated") is not True and case.get("outcome") == expected_outcome:
                raise ValidationFailure(f"store-boundary case {name}: the observation no longer violates the dry-run rule")
            continue
        if case.get("conforming") is False:
            raise ValidationFailure(f"store-boundary case {name}: a positive case must not carry conforming=false")
        if case.get("outcome") != expected_outcome:
            raise ValidationFailure(f"store-boundary case {name}: outcome is not the §4 dry-run rule ({expected_outcome!r})")
        if case.get("mutated") is not False:
            raise ValidationFailure(f"store-boundary case {name}: dry-run evaluation mutates nothing")

    repair = named_cases(vector.get("repair_cases"), "store-boundary repair")
    if set(repair) != S5_REPAIR_CASES:
        raise ValidationFailure("store-boundary repair case inventory is not exact")
    for name, case in repair.items():
        kind = case.get("entry_kind")
        if kind not in S5_ENTRY_KINDS:
            raise ValidationFailure(f"store-boundary case {name}: entry_kind must be git, path, or local")
        if case.get("object") not in S5_OBJECTS:
            raise ValidationFailure(f"store-boundary case {name}: object must be one of {', '.join(S5_OBJECTS)}")
        inputs = s5_check_inputs(case, name)
        home = s5_check_home(case, name)
        s5_check_swap_shape(case, inputs, name)
        store_trusted, failing = s5_store_trusted(inputs)
        pin = S5_REPAIR_PIN[name]
        if kind != pin["kind"]:
            raise ValidationFailure(f"store-boundary case {name}: entry_kind must be {pin['kind']} for this branch")
        s5_check_pin(pin, case, failing, home, name)
        if name in S5_REPAIR_NEGATIVE_CASES:
            if case.get("conforming") is not False or not case.get("reason"):
                raise ValidationFailure(f"store-boundary case {name}: a negative needs conforming=false and a reason")
            if store_trusted or case.get("reapplied_before_trust") is not True:
                raise ValidationFailure(f"store-boundary case {name}: the observation no longer violates the repair rule")
            continue
        if case.get("conforming") is False:
            raise ValidationFailure(f"store-boundary case {name}: a positive case must not carry conforming=false")
        if case.get("reapplied_before_trust") is not False:
            raise ValidationFailure(f"store-boundary case {name}: a non-trusted entry is never re-applied")
        obj = case.get("object")
        if obj in S5_ENCLOSING_OBJECTS:
            if store_trusted:
                raise ValidationFailure(f"store-boundary case {name}: an enclosing repair case starts from an unproven boundary")
            if case.get("rebuilt_from_snapshot") is not False:
                raise ValidationFailure(f"store-boundary case {name}: an enclosing failure is never rebuilt")
            if case.get("diagnostic") != S5_DIAG_UNTRUSTED or case.get("fragment_emitted") is not False:
                raise ValidationFailure(f"store-boundary case {name}: an enclosing failure refuses with no fragment")
        elif not store_trusted:
            if (case.get("rebuilt_from_snapshot") is True) != (kind == "git"):
                raise ValidationFailure(f"store-boundary case {name}: only a git entry rebuilds from the revalidated snapshot")
            if kind == "git":
                if case.get("diagnostic") is not None or case.get("fragment_emitted") is not True:
                    raise ValidationFailure(f"store-boundary case {name}: a rebuilt git entry resolves")
            elif case.get("diagnostic") != S5_DIAG_REPAIR_FAILED or case.get("fragment_emitted") is not False:
                raise ValidationFailure(f"store-boundary case {name}: an unrebuildable entry fails repair without a fragment")
        else:
            if home not in ("stale-old-marker", "unprovisioned"):
                raise ValidationFailure(f"store-boundary case {name}: a trusted-store repair starts from a stale or unprovisioned home")
            if case.get("rebuilt_from_snapshot") is not False:
                raise ValidationFailure(f"store-boundary case {name}: a verified store needs no rebuild")
            if case.get("diagnostic") is not None or case.get("fragment_emitted") is not True:
                raise ValidationFailure(f"store-boundary case {name}: repair from a verified store resolves")

    status = named_cases(vector.get("status_cases"), "store-boundary status")
    if set(status) != S5_STATUS_CASES:
        raise ValidationFailure("store-boundary status case inventory is not exact")
    for name, case in status.items():
        if case.get("object") not in S5_OBJECTS:
            raise ValidationFailure(f"store-boundary case {name}: object must be one of {', '.join(S5_OBJECTS)}")
        inputs = s5_check_inputs(case, name)
        home = s5_check_home(case, name)
        s5_check_swap_shape(case, inputs, name)
        store_trusted, failing = s5_store_trusted(inputs)
        s5_check_pin(S5_STATUS_PIN[name], case, failing, home, name)
        expected_diag = None if store_trusted else S5_DIAG_UNTRUSTED
        if name in S5_STATUS_NEGATIVE_CASES:
            if case.get("conforming") is not False or not case.get("reason"):
                raise ValidationFailure(f"store-boundary case {name}: a negative needs conforming=false and a reason")
            if case.get("diagnostic") == expected_diag and case.get("row_current") is store_trusted and (case.get("names_failing_check") in failing or store_trusted):
                raise ValidationFailure(f"store-boundary case {name}: the observation no longer violates the §12 rule")
            continue
        if case.get("conforming") is False:
            raise ValidationFailure(f"store-boundary case {name}: a positive case must not carry conforming=false")
        if case.get("diagnostic") != expected_diag:
            raise ValidationFailure(f"store-boundary case {name}: diagnostic is not the §12 rule ({expected_diag!r})")
        if case.get("row_current") is not store_trusted:
            raise ValidationFailure(f"store-boundary case {name}: an untrusted profile is non-current")
        if store_trusted:
            if case.get("names_failing_check") is not None:
                raise ValidationFailure(f"store-boundary case {name}: a trusted row names no failing check")
        elif case.get("names_failing_check") not in failing:
            raise ValidationFailure(f"store-boundary case {name}: the status row names the failing check")
# Sections 7.4, 7.7, 7.8, 8.2, 12: codex seed mcp_servers handling (E3)


E3_DIAG_UNGOVERNED = "mcp_native_servers_ungoverned"
E3_DIAG_NOT_INHERITED = "mcp_native_servers_not_inherited"
E3_DIAG_UNSTRIPPED = "mcp_seed_unstripped"

E3_REVISION_A = "warning release: the codex_cli seed is still copied whole, but provisioning warns mcp_native_servers_ungoverned naming every inherited native mcp_servers entry with the migration hint"
E3_REVISION_B = "flip release: the codex_cli seed strips the mcp_servers table and every mcp_servers.* sub-table; provisioning reports the stripped names once with mcp_native_servers_not_inherited"

# Each provisioning case is pinned to the branch it exercises: the seed
# rule revision, the native mcp_servers state (present/absent/empty), the
# TOML form that carries it, and the exact native top-level member set. A
# named case whose body no longer matches its pin — e.g. the B-strip case
# replaced by the no-server case — fails here even when the replacement is
# internally consistent.
E3_PROVISIONING_BRANCH = {
    "a-copies-whole-with-servers": {
        "revision": "A", "servers": "present", "form": "subtable",
        "members": frozenset({"mcp_servers", "model", "projects", "tui"}),
    },
    "b-strips-servers-keeps-rest": {
        "revision": "B", "servers": "present", "form": "subtable",
        "members": frozenset({"mcp_servers", "model", "projects", "tui"}),
    },
    "a-without-servers-no-warning": {
        "revision": "A", "servers": "absent", "form": "absent",
        "members": frozenset({"model", "projects", "tui"}),
    },
    "b-without-servers-no-warning": {
        "revision": "B", "servers": "absent", "form": "absent",
        "members": frozenset({"model", "projects", "tui"}),
    },
    "b-subtable-only-form-stripped": {
        "revision": "B", "servers": "present", "form": "subtable-only",
        "members": frozenset({"mcp_servers", "model"}),
    },
    "a-inline-table-form-inherited": {
        "revision": "A", "servers": "present", "form": "inline",
        "members": frozenset({"mcp_servers", "model"}),
    },
    "b-empty-mcp-servers-table-no-warning": {
        "revision": "B", "servers": "empty", "form": "empty-table",
        "members": frozenset({"mcp_servers", "model"}),
    },
}

# Each posture case is pinned to its inputs: the manager-shipped revision,
# the adapter, the home's recorded seed revision (None means the record is
# absent), and the snapshot state. The manager revision and the recorded
# revision are distinct inputs: an A-record home under a B manager is its
# own pinned case, not the A/A one.
E3_POSTURE_BRANCH = {
    "a-home-lists-ungoverned": {
        "shipped": "A", "environment": "codex_cli", "record": "A", "snapshot": "non-empty",
    },
    "a-home-unstripped-under-b": {
        "shipped": "B", "environment": "codex_cli", "record": "A", "snapshot": "non-empty",
    },
    "b-home-lists-not-inherited": {
        "shipped": "B", "environment": "codex_cli", "record": "B", "snapshot": "non-empty",
    },
    "pre-rule-home-unstripped-under-b": {
        "shipped": "B", "environment": "codex_cli", "record": None, "snapshot": "absent",
    },
    "pre-rule-home-unstripped-under-a": {
        "shipped": "A", "environment": "codex_cli", "record": None, "snapshot": "absent",
    },
    "b-home-empty-snapshot-no-rows": {
        "shipped": "B", "environment": "codex_cli", "record": "B", "snapshot": "empty",
    },
    "a-home-empty-snapshot-no-rows": {
        "shipped": "A", "environment": "codex_cli", "record": "A", "snapshot": "empty",
    },
    "non-codex-home-without-record-no-rows": {
        "shipped": "B", "environment": "claude_code", "record": None, "snapshot": "absent",
    },
}

E3_PROVISIONING_CASE_KEYS = frozenset({"name", "revision", "native_config_toml", "expected"})
E3_PROVISIONING_EXPECTED_KEYS = frozenset({
    "seeded_has_mcp_servers", "seeded_top_level_members", "seeded_members",
    "names", "diagnostic", "migration_hint", "codex_seed_record",
})
E3_POSTURE_CASE_KEYS = frozenset({"name", "revision_shipped", "environment", "codex_seed_record", "expected"})
E3_POSTURE_EXPECTED_KEYS = frozenset({
    "codex_seed_row", "status_diagnostics", "names_listed", "listed_as", "repair_hint", "row_current",
})


def e3_check_seed_record(value: Any, label: str) -> tuple[str, list[str]]:
    """A section 8.2 seed record is the closed `{ revision,
    native_mcp_servers }` object with an A/B revision and an
    ascending-byte-order snapshot of non-empty names; return both."""
    if not isinstance(value, dict) or set(value) != {"revision", "native_mcp_servers"}:
        raise ValidationFailure(f"{label}: a codex seed record is exactly {{ revision, native_mcp_servers }}")
    revision = value.get("revision")
    if revision not in ("A", "B"):
        raise ValidationFailure(f"{label}: a seed record revision must be A or B")
    names = value.get("native_mcp_servers")
    if not isinstance(names, list) or any(not isinstance(item, str) or not item for item in names):
        raise ValidationFailure(f"{label}: native_mcp_servers must be an array of non-empty names")
    if len(set(names)) != len(names):
        raise ValidationFailure(f"{label}: native_mcp_servers names must be unique")
    if names != sorted(names, key=lambda item: item.encode("utf-8")):
        raise ValidationFailure(f"{label}: native_mcp_servers must be in ascending byte order")
    return revision, names


def e3_parse_native_config(text: Any, label: str) -> tuple[dict[str, Any], list[str]]:
    """Parse a provisioning fixture: the native `config.toml` bytes and the
    sorted native `mcp_servers` entry names. A fixture that is not TOML, or
    whose `mcp_servers` member is not a table, asserts nothing and fails."""
    if not isinstance(text, str):
        raise ValidationFailure(f"{label}: native_config_toml must be text")
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ValidationFailure(f"{label}: native_config_toml is not valid TOML ({exc})") from exc
    if "mcp_servers" not in doc:
        return doc, []
    servers = doc["mcp_servers"]
    if not isinstance(servers, dict):
        raise ValidationFailure(f"{label}: a native mcp_servers member is a table")
    names = sorted(servers, key=lambda item: item.encode("utf-8"))
    if any(not name for name in names):
        raise ValidationFailure(f"{label}: a native mcp_servers entry name is empty")
    return doc, names


def e3_expected_provisioning(revision: str, doc: dict[str, Any], names: list[str]) -> dict[str, Any]:
    """Recompute the section 7.4 provisioning outcome: revision A seeds the
    native document whole, revision B seeds every top-level member except
    `mcp_servers`, and the warning fires exactly when the snapshot is
    non-empty, with the migration hint only on the revision-A warning."""
    seeded = dict(doc) if revision == "A" else {key: value for key, value in doc.items() if key != "mcp_servers"}
    diagnostic = (E3_DIAG_UNGOVERNED if revision == "A" else E3_DIAG_NOT_INHERITED) if names else None
    return {
        "seeded_has_mcp_servers": "mcp_servers" in seeded,
        "seeded_top_level_members": sorted(seeded),
        "seeded_members": seeded,
        "names": names,
        "diagnostic": diagnostic,
        "migration_hint": diagnostic == E3_DIAG_UNGOVERNED,
    }


def e3_expected_posture(
    shipped: str, environment: str, record_revision: str | None, record_names: list[str]
) -> dict[str, Any]:
    """Recompute the section 12 posture rows from the manager-shipped
    revision and the home's recorded seed revision. An A-record home keeps
    its inherited names listed as ungoverned under either manager and adds
    `mcp_seed_unstripped` under a B manager when its snapshot is
    non-empty; a B record lists stripped names as not inherited; an absent
    record is pre-rule; any other adapter rows nothing. Every warning row
    stays current."""
    if environment != "codex_cli":
        diagnostics, names, listed, repair = [], [], "none", False
    elif record_revision is None:
        diagnostics, names, listed, repair = [E3_DIAG_UNSTRIPPED], [], "unknown", True
    elif record_revision == "A":
        names = record_names
        diagnostics = [E3_DIAG_UNGOVERNED] if record_names else []
        if shipped == "B" and record_names:
            diagnostics.append(E3_DIAG_UNSTRIPPED)
        listed = "ungoverned" if record_names else "none"
        repair = E3_DIAG_UNSTRIPPED in diagnostics
    else:
        names = record_names
        diagnostics = [E3_DIAG_NOT_INHERITED] if record_names else []
        listed = "not-inherited" if record_names else "none"
        repair = False
    return {
        "codex_seed_row": shipped,
        "status_diagnostics": diagnostics,
        "names_listed": names,
        "listed_as": listed,
        "repair_hint": repair,
        "row_current": True,
    }


def e3_check_native_form(raw: str, form: str, label: str) -> None:
    """The TOML spelling the named case promises: dotted sub-tables, an
    inline table, an empty table, or no `mcp_servers` mention at all. The
    parsed document cannot tell an inline table from dotted sub-tables, so
    the pin reads the raw fixture text."""
    if form == "subtable" and "[mcp_servers." not in raw:
        raise ValidationFailure(f"{label}: the pinned subtable form is gone")
    elif form == "subtable-only" and ("[mcp_servers." not in raw or "mcp_servers =" in raw):
        raise ValidationFailure(f"{label}: the pinned subtable-only form is gone")
    elif form == "inline" and "mcp_servers = {" not in raw:
        raise ValidationFailure(f"{label}: the pinned inline-table form is gone")
    elif form == "absent" and "mcp_servers" in raw:
        raise ValidationFailure(f"{label}: the pinned server-free form gained mcp_servers")
    elif form == "empty-table" and ("[mcp_servers]" not in raw or "[mcp_servers." in raw):
        raise ValidationFailure(f"{label}: the pinned empty-table form is gone")


def validate_environments_codex_seed_vectors(
    vector: Any = None, suite_root: Path | None = None
) -> None:
    """Recompute the E3 codex-seed provisioning and posture expectations.

    Every provisioning case is derived from its declared inputs — the
    parsed native `config.toml` members and values, the seed rule
    revision, the snapshot names, the diagnostic and hint, and the marker
    seed record — and every posture case from the manager-shipped
    revision, the adapter, and the home's recorded seed revision. Every
    named case is additionally pinned to the branch it exercises, so a
    corpus where a named case no longer represents its branch — an
    internally consistent replacement under the same name — fails here.
    """
    root = SUITE if suite_root is None else Path(suite_root)
    if vector is None:
        vector = load_json(root / "vectors" / "environments-codex-seed.json")
    if (
        vector.get("schema_version") != 1
        or vector.get("protocol_version") != PROTOCOL_VERSION
        or vector.get("capability") != "agent-environments"
        or vector.get("capability_revision") != 1
    ):
        raise ValidationFailure("codex-seed vector has the wrong capability identity")
    if vector.get("revision_a") != E3_REVISION_A or vector.get("revision_b") != E3_REVISION_B:
        raise ValidationFailure("codex-seed revisions must pin exactly the warning and flip releases")

    provisioning = named_cases(vector.get("provisioning_cases"), "codex-seed provisioning")
    if set(provisioning) != set(E3_PROVISIONING_BRANCH):
        raise ValidationFailure("codex-seed provisioning case inventory is not exact")
    for name, case in provisioning.items():
        label = f"codex-seed case {name}"
        pin = E3_PROVISIONING_BRANCH[name]
        if set(case) != E3_PROVISIONING_CASE_KEYS:
            raise ValidationFailure(f"{label}: a provisioning case is exactly {{ name, revision, native_config_toml, expected }}")
        revision = case.get("revision")
        if revision not in ("A", "B"):
            raise ValidationFailure(f"{label}: revision must be A or B")
        if revision != pin["revision"]:
            raise ValidationFailure(f"{label}: revision does not match the pinned one ({pin['revision']})")
        raw = case.get("native_config_toml")
        doc, names = e3_parse_native_config(raw, label)
        if set(doc) != pin["members"]:
            raise ValidationFailure(f"{label}: native top-level members are not the pinned set ({sorted(pin['members'])})")
        servers_state = "absent" if "mcp_servers" not in doc else ("empty" if not names else "present")
        if servers_state != pin["servers"]:
            raise ValidationFailure(f"{label}: native mcp_servers are {servers_state}, the case pins {pin['servers']}")
        e3_check_native_form(raw, pin["form"], label)
        expected = case.get("expected")
        if not isinstance(expected, dict) or set(expected) != E3_PROVISIONING_EXPECTED_KEYS:
            raise ValidationFailure(f"{label}: expected is not the closed provisioning set")
        want = e3_expected_provisioning(revision, doc, names)
        if expected.get("seeded_has_mcp_servers") != want["seeded_has_mcp_servers"]:
            raise ValidationFailure(f"{label}: seeded_has_mcp_servers is not the revision {revision} rule")
        if expected.get("seeded_top_level_members") != want["seeded_top_level_members"]:
            raise ValidationFailure(
                f"{label}: seeded_top_level_members are not the revision {revision} rule ({want['seeded_top_level_members']})"
            )
        if expected.get("seeded_members") != want["seeded_members"]:
            raise ValidationFailure(f"{label}: seeded_members are not the retained revision {revision} values")
        if expected.get("names") != want["names"]:
            raise ValidationFailure(f"{label}: names are not the native mcp_servers entries ({want['names']})")
        if expected.get("diagnostic") != want["diagnostic"]:
            raise ValidationFailure(f"{label}: diagnostic is not the revision {revision} rule ({want['diagnostic']!r})")
        if expected.get("migration_hint") != want["migration_hint"]:
            raise ValidationFailure(f"{label}: migration_hint rides only the revision-A warning")
        record_revision, record_names = e3_check_seed_record(expected.get("codex_seed_record"), label)
        if record_revision != revision or record_names != names:
            raise ValidationFailure(f"{label}: codex_seed_record is not the revision {revision} record with the native names")

    posture = named_cases(vector.get("posture_cases"), "codex-seed posture")
    if set(posture) != set(E3_POSTURE_BRANCH):
        raise ValidationFailure("codex-seed posture case inventory is not exact")
    for name, case in posture.items():
        label = f"codex-seed case {name}"
        pin = E3_POSTURE_BRANCH[name]
        if set(case) != E3_POSTURE_CASE_KEYS:
            raise ValidationFailure(f"{label}: a posture case is exactly {{ name, revision_shipped, environment, codex_seed_record, expected }}")
        shipped = case.get("revision_shipped")
        if shipped not in ("A", "B"):
            raise ValidationFailure(f"{label}: revision_shipped must be A or B")
        if shipped != pin["shipped"]:
            raise ValidationFailure(f"{label}: revision_shipped does not match the pinned one ({pin['shipped']})")
        environment = case.get("environment")
        if environment not in ENVIRONMENT_HOME_VARIABLES:
            raise ValidationFailure(f"{label}: environment {environment!r} is outside the closed adapter set")
        if environment != pin["environment"]:
            raise ValidationFailure(f"{label}: environment does not match the pinned one ({pin['environment']})")
        record = case.get("codex_seed_record")
        if record is None:
            if pin["record"] is not None or pin["snapshot"] != "absent":
                raise ValidationFailure(f"{label}: the seed record is absent, the case pins a {pin['record']} record")
            record_revision, record_names = None, []
        else:
            record_revision, record_names = e3_check_seed_record(record, label)
            if record_revision != pin["record"]:
                raise ValidationFailure(f"{label}: recorded revision does not match the pinned one ({pin['record']})")
            snapshot = "empty" if not record_names else "non-empty"
            if snapshot != pin["snapshot"]:
                raise ValidationFailure(f"{label}: snapshot is {snapshot}, the case pins {pin['snapshot']}")
        # The non-codex pin (record None) is what enforces the section 8.2
        # absence rule: any other adapter carrying a seed record fails its
        # recorded-revision pin above.
        expected = case.get("expected")
        if not isinstance(expected, dict) or set(expected) != E3_POSTURE_EXPECTED_KEYS:
            raise ValidationFailure(f"{label}: expected is not the closed posture set")
        want = e3_expected_posture(shipped, environment, record_revision, record_names)
        if expected.get("codex_seed_row") != want["codex_seed_row"]:
            raise ValidationFailure(f"{label}: codex_seed_row is not the shipped revision ({want['codex_seed_row']})")
        if expected.get("status_diagnostics") != want["status_diagnostics"]:
            raise ValidationFailure(f"{label}: status_diagnostics are not the posture rule ({want['status_diagnostics']})")
        if expected.get("names_listed") != want["names_listed"]:
            raise ValidationFailure(f"{label}: names_listed are not the recorded names ({want['names_listed']})")
        if expected.get("listed_as") != want["listed_as"]:
            raise ValidationFailure(f"{label}: listed_as is not the posture rule ({want['listed_as']!r})")
        if expected.get("repair_hint") != want["repair_hint"]:
            raise ValidationFailure(f"{label}: repair_hint rides only mcp_seed_unstripped")
        if expected.get("row_current") != want["row_current"]:
            raise ValidationFailure(f"{label}: a codex-seed warning row stays current")


# ---------------------------------------------------------------------------
# E6: path-kind admission and the store-boundary extension to path source
# directories (sections 1, 2.1, 2.2, 3, 4, 6, 8.5, 9.6, 10.1, 10.4, 12, 13)


E6_DIAG_MCP_REFUSED = "mcp_declaration_path_source_refused"
E6_DIAG_UNTRUSTED = "environment_store_untrusted"
E6_DIAG_TRANSITIVE = "context_system_module_transitive"

E6_BOUNDARY_CHECKS = ("ownership", "permissions", "containment", "regular_types", "link_safety")
E6_SOURCE_KINDS = ("git", "path")
E6_PIN_KINDS = ("commit", "state_sha256")
E6_MCP_ORIGINS = ("requires-edge", "root", "overlay", "onboarding-import")
E6_ROLES = ("root", "overlay", "member")
E6_ORIGINS = ("operator", "onboarding-import")
E6_POLICIES = ("drop", "error")

E6_MCP_CASES = {
    "git-mcp-declaration-admitted",
    "path-overlay-mcp-declaration-refused",
    "path-root-mcp-declaration-refused",
    "path-import-mcp-declaration-refused",
    "path-mcp-declaration-admitted",
}
E6_MCP_NEGATIVE_CASES = {"path-mcp-declaration-admitted"}
E6_BOUNDARY_CASES = {
    "path-overlay-system-module-admitted",
    "path-root-no-system-modules-admitted",
    "path-import-no-system-modules-admitted",
    "path-overlay-no-system-modules-admitted",
    "path-overlay-world-writable-untrusted",
    "path-overlay-symlinked-component-untrusted",
    "path-overlay-wrong-ownership-untrusted",
    "path-overlay-containment-escape-untrusted",
    "path-overlay-non-regular-component-untrusted",
    "path-overlay-no-system-world-writable-untrusted",
    "path-import-no-system-wrong-ownership-untrusted",
    "path-transitive-system-module-refused",
    "path-overlay-untrusted-reported-current",
    "path-overlay-untrusted-rebuilds",
}
E6_BOUNDARY_NEGATIVE_CASES = {
    "path-overlay-untrusted-reported-current",
    "path-overlay-untrusted-rebuilds",
}
E6_DRY_RUN_CASES = {
    "path-overlay-dry-run-untrusted-no-rebuild",
    "path-overlay-dry-run-intact-plans-nothing",
    "path-overlay-dry-run-reports-would-rebuild",
}
E6_DRY_RUN_NEGATIVE_CASES = {"path-overlay-dry-run-reports-would-rebuild"}

# Each named case is pinned to its discriminating inputs: an MCP case to
# the declaration's source kind, pin kind, and origin; a boundary or
# dry-run case to its failing check (or none), directness, system-module
# content, machine policy, role, and origin. A corpus where a named branch
# no longer exercises its inputs (for example a path refusal rewritten as
# a git admission under the same name, the five boundary branches
# collapsed to ownership-only, or a no-system refusal rewritten as a
# system-module case) is refused.
E6_MCP_PIN: dict[str, dict[str, Any]] = {
    "git-mcp-declaration-admitted": {"source_kind": "git", "pin_kind": "commit", "origin": "requires-edge"},
    "path-overlay-mcp-declaration-refused": {"source_kind": "path", "pin_kind": "state_sha256", "origin": "overlay"},
    "path-root-mcp-declaration-refused": {"source_kind": "path", "pin_kind": "state_sha256", "origin": "root"},
    "path-import-mcp-declaration-refused": {"source_kind": "path", "pin_kind": "state_sha256", "origin": "onboarding-import"},
    "path-mcp-declaration-admitted": {"source_kind": "path", "pin_kind": "state_sha256", "origin": "overlay"},
}
E6_BOUNDARY_PIN: dict[str, dict[str, Any]] = {
    "path-overlay-system-module-admitted": {"check": None, "direct": True, "carries": True, "policy": "drop", "role": "overlay", "origin": "operator"},
    "path-root-no-system-modules-admitted": {"check": None, "direct": True, "carries": False, "policy": "drop", "role": "root", "origin": "operator"},
    "path-import-no-system-modules-admitted": {"check": None, "direct": True, "carries": False, "policy": "drop", "role": "root", "origin": "onboarding-import"},
    "path-overlay-no-system-modules-admitted": {"check": None, "direct": True, "carries": False, "policy": "drop", "role": "overlay", "origin": "operator"},
    "path-overlay-world-writable-untrusted": {"check": "permissions", "direct": True, "carries": True, "policy": "drop", "role": "overlay", "origin": "operator"},
    "path-overlay-symlinked-component-untrusted": {"check": "link_safety", "direct": True, "carries": True, "policy": "drop", "role": "overlay", "origin": "operator"},
    "path-overlay-wrong-ownership-untrusted": {"check": "ownership", "direct": True, "carries": True, "policy": "drop", "role": "overlay", "origin": "operator"},
    "path-overlay-containment-escape-untrusted": {"check": "containment", "direct": True, "carries": True, "policy": "drop", "role": "overlay", "origin": "operator"},
    "path-overlay-non-regular-component-untrusted": {"check": "regular_types", "direct": True, "carries": True, "policy": "drop", "role": "overlay", "origin": "operator"},
    "path-overlay-no-system-world-writable-untrusted": {"check": "permissions", "direct": True, "carries": False, "policy": "drop", "role": "overlay", "origin": "operator"},
    "path-import-no-system-wrong-ownership-untrusted": {"check": "ownership", "direct": True, "carries": False, "policy": "drop", "role": "root", "origin": "onboarding-import"},
    "path-transitive-system-module-refused": {"check": None, "direct": False, "carries": True, "policy": "error", "role": "member", "origin": "operator"},
    "path-overlay-untrusted-reported-current": {"check": "permissions", "direct": True, "carries": True, "policy": "drop", "role": "overlay", "origin": "operator"},
    "path-overlay-untrusted-rebuilds": {"check": "ownership", "direct": True, "carries": True, "policy": "drop", "role": "overlay", "origin": "operator"},
}
E6_DRY_RUN_PIN: dict[str, dict[str, Any]] = {
    "path-overlay-dry-run-untrusted-no-rebuild": {"check": "permissions", "direct": True, "carries": True, "policy": "drop", "role": "overlay", "origin": "operator"},
    "path-overlay-dry-run-intact-plans-nothing": {"check": None, "direct": True, "carries": True, "policy": "drop", "role": "overlay", "origin": "operator"},
    "path-overlay-dry-run-reports-would-rebuild": {"check": "permissions", "direct": True, "carries": True, "policy": "drop", "role": "overlay", "origin": "operator"},
}


def e6_check_boundary_inputs(case: dict[str, Any], name: str) -> dict[str, bool]:
    """Read the five §4 boundary inputs of one path-directory case.

    No pin is recomputed against the live directory (§4): a case carrying
    a pin-hash comparison models the wrong rule.
    """
    if "pin_hash_match" in case:
        raise ValidationFailure(f"path-kind case {name}: no pin is recomputed against the live directory")
    inputs: dict[str, bool] = {}
    for check in E6_BOUNDARY_CHECKS:
        value = case.get(check)
        if not isinstance(value, bool):
            raise ValidationFailure(f"path-kind case {name}: {check} must be a boolean")
        inputs[check] = value
    return inputs


def e6_boundary_trusted(inputs: dict[str, bool]) -> tuple[bool, list[str]]:
    """Recompute the §4 directory verdict: every boundary check passes, else untrusted."""
    failing = [check for check in E6_BOUNDARY_CHECKS if not inputs[check]]
    return (not failing, failing)


def e6_check_mcp_pin(pin: dict[str, Any], case: dict[str, Any], name: str) -> None:
    """Bind a named MCP case to its source kind, pin kind, and origin."""
    for field in ("source_kind", "pin_kind", "origin"):
        if case.get(field) != pin[field]:
            raise ValidationFailure(f"path-kind case {name}: {field} must be {pin[field]} for this branch")


def e6_check_boundary_pin(pin: dict[str, Any], case: dict[str, Any], failing: list[str], name: str) -> None:
    """Bind a named boundary case to its failing check, directness, content, policy, role, and origin."""
    if case.get("direct") is not pin["direct"]:
        raise ValidationFailure(f"path-kind case {name}: direct must be {pin['direct']} for this branch")
    if case.get("carries_system_modules") is not pin["carries"]:
        raise ValidationFailure(f"path-kind case {name}: carries_system_modules must be {pin['carries']} for this branch")
    if case.get("machine_policy", {}).get("transitive_system_modules") != pin["policy"]:
        raise ValidationFailure(f"path-kind case {name}: policy must be {pin['policy']} for this branch")
    if case.get("role") != pin["role"]:
        raise ValidationFailure(f"path-kind case {name}: role must be {pin['role']} for this branch")
    if case.get("origin") != pin["origin"]:
        raise ValidationFailure(f"path-kind case {name}: origin must be {pin['origin']} for this branch")
    expected = pin["check"]
    if expected is None:
        if failing:
            raise ValidationFailure(f"path-kind case {name}: this branch models no failing boundary check")
    elif expected not in failing:
        raise ValidationFailure(f"path-kind case {name}: this branch must fail {expected}")
    elif len(failing) != 1:
        raise ValidationFailure(f"path-kind case {name}: this branch isolates exactly its failing check")


def e6_expected_names(case: dict[str, Any], expected_diag: str | None, failing: list[str]) -> dict[str, Any]:
    """Recompute the §2.1/§3.1/§12 naming rule for one boundary observation."""
    if expected_diag == E6_DIAG_UNTRUSTED:
        return {"names_path": case.get("path"), "names_check": failing[0], "names_package": None, "names_module": None}
    if expected_diag == E6_DIAG_TRANSITIVE:
        return {"names_path": None, "names_check": None, "names_package": case.get("package"), "names_module": case.get("module")}
    return {"names_path": None, "names_check": None, "names_package": None, "names_module": None}


def validate_environments_path_kind_admission_vectors(vector: Any = None) -> None:
    """Recompute every E6 path-kind admission verdict (§1, §2.1, §2.2, §3, §4, §10.1, §10.4, §12).

    An MCP declaration resolves only from a `git` source: a declaration
    carried by a `path` root, overlay, or onboarding import is refused
    with `mcp_declaration_path_source_refused` naming the package and the
    declaration. A `path` source directory passes the five §4 boundary
    checks at every resolve; a failure is entry-class
    `environment_store_untrusted` — no fragment, non-current, posture row
    naming the path and the failing check — with no rebuild, while a
    directory that passes admits system modules only under the §3
    direct-naming rule. Dry-run evaluation of a `path` directory failure
    reports `environment_store_untrusted` with no rebuild planned and
    mutates nothing — never `would-rebuild-untrusted-store`, which names
    only a store entry, lock, or marker file failure. Each named case is
    pinned to its discriminating inputs, so a corpus where a named branch
    no longer exercises its branch is refused. Negatives carry a
    non-conforming observation that must still violate the recomputed rule.
    """
    if vector is None:
        vector = load_json(SUITE / "vectors" / "environments-path-kind-admission.json")
    if vector.get("capability") != "agent-environments" or vector.get("capability_revision") != 1:
        raise ValidationFailure("path-kind vector has the wrong capability identity")
    pinned = vector.get("diagnostics")
    if (
        not isinstance(pinned, dict)
        or pinned.get("mcp_path_source_refused") != E6_DIAG_MCP_REFUSED
        or pinned.get("store_untrusted") != E6_DIAG_UNTRUSTED
        or pinned.get("system_module_transitive") != E6_DIAG_TRANSITIVE
    ):
        raise ValidationFailure(
            "path-kind diagnostics must pin mcp_declaration_path_source_refused, "
            "environment_store_untrusted, and context_system_module_transitive"
        )

    mcp = named_cases(vector.get("mcp_kind_cases"), "path-kind mcp")
    if set(mcp) != E6_MCP_CASES:
        raise ValidationFailure("path-kind mcp case inventory is not exact")
    for name, case in mcp.items():
        if case.get("source_kind") not in E6_SOURCE_KINDS:
            raise ValidationFailure(f"path-kind case {name}: source_kind must be git or path")
        if case.get("pin_kind") not in E6_PIN_KINDS:
            raise ValidationFailure(f"path-kind case {name}: pin_kind must be commit or state_sha256")
        if case.get("origin") not in E6_MCP_ORIGINS:
            raise ValidationFailure(f"path-kind case {name}: origin must be one of {', '.join(E6_MCP_ORIGINS)}")
        if not case.get("package") or not case.get("declaration"):
            raise ValidationFailure(f"path-kind case {name}: package and declaration must be named")
        if case["source_kind"] == "git":
            if not case.get("source") or case.get("pin_kind") != "commit":
                raise ValidationFailure(f"path-kind case {name}: a git declaration carries a canonical source and a commit pin")
        else:
            if case.get("source") is not None or case.get("pin_kind") != "state_sha256":
                raise ValidationFailure(f"path-kind case {name}: a path declaration carries no source and a state pin")
        e6_check_mcp_pin(E6_MCP_PIN[name], case, name)
        expected_admitted = case["source_kind"] == "git"
        expected_diag = None if expected_admitted else E6_DIAG_MCP_REFUSED
        if name in E6_MCP_NEGATIVE_CASES:
            if case.get("conforming") is not False or not case.get("reason"):
                raise ValidationFailure(f"path-kind case {name}: a negative needs conforming=false and a reason")
            if case.get("admitted") is expected_admitted and case.get("diagnostic") == expected_diag:
                raise ValidationFailure(f"path-kind case {name}: the observation no longer violates the §2.2 rule")
            continue
        if case.get("conforming") is False:
            raise ValidationFailure(f"path-kind case {name}: a positive case must not carry conforming=false")
        if case.get("admitted") is not expected_admitted:
            raise ValidationFailure(f"path-kind case {name}: admission is not the §2.2 rule")
        if case.get("diagnostic") != expected_diag:
            raise ValidationFailure(f"path-kind case {name}: diagnostic is not the §2.1 rule ({expected_diag!r})")
        if expected_admitted:
            if case.get("names_package") is not None or case.get("names_declaration") is not None:
                raise ValidationFailure(f"path-kind case {name}: an admitted declaration names nothing")
        elif case.get("names_package") != case.get("package") or case.get("names_declaration") != case.get("declaration"):
            raise ValidationFailure(f"path-kind case {name}: the refusal names the package and the declaration")

    boundary = named_cases(vector.get("path_boundary_cases"), "path-kind boundary")
    if set(boundary) != E6_BOUNDARY_CASES:
        raise ValidationFailure("path-kind boundary case inventory is not exact")
    for name, case in boundary.items():
        if case.get("role") not in E6_ROLES:
            raise ValidationFailure(f"path-kind case {name}: role must be one of {', '.join(E6_ROLES)}")
        if case.get("origin") not in E6_ORIGINS:
            raise ValidationFailure(f"path-kind case {name}: origin must be operator or onboarding-import")
        if not isinstance(case.get("direct"), bool) or not isinstance(case.get("carries_system_modules"), bool):
            raise ValidationFailure(f"path-kind case {name}: direct and carries_system_modules must be booleans")
        policy = case.get("machine_policy", {}).get("transitive_system_modules")
        if policy not in E6_POLICIES:
            raise ValidationFailure(f"path-kind case {name}: policy must be drop or error")
        path = case.get("path")
        if not isinstance(path, str) or not path.startswith("/"):
            raise ValidationFailure(f"path-kind case {name}: path must be an absolute directory")
        if not case.get("package"):
            raise ValidationFailure(f"path-kind case {name}: package must be named")
        if case["carries_system_modules"]:
            if not case.get("module"):
                raise ValidationFailure(f"path-kind case {name}: a system-module carrier names its module")
        elif case.get("module") is not None:
            raise ValidationFailure(f"path-kind case {name}: no module without system modules")
        inputs = e6_check_boundary_inputs(case, name)
        trusted, failing = e6_boundary_trusted(inputs)
        e6_check_boundary_pin(E6_BOUNDARY_PIN[name], case, failing, name)
        if not trusted:
            expected_diag = E6_DIAG_UNTRUSTED
        elif case["carries_system_modules"] and not case["direct"] and policy == "error":
            expected_diag = E6_DIAG_TRANSITIVE
        else:
            expected_diag = None
        expected_fragment = expected_diag is None
        expected_current = expected_diag is None
        expected_names = e6_expected_names(case, expected_diag, failing)
        if name in E6_BOUNDARY_NEGATIVE_CASES:
            if case.get("conforming") is not False or not case.get("reason"):
                raise ValidationFailure(f"path-kind case {name}: a negative needs conforming=false and a reason")
            if (
                case.get("diagnostic") == expected_diag
                and case.get("fragment_emitted") is expected_fragment
                and case.get("row_current") is expected_current
                and case.get("rebuild_planned") is False
                and all(case.get(field) == value for field, value in expected_names.items())
            ):
                raise ValidationFailure(f"path-kind case {name}: the observation no longer violates the §4 rule")
            continue
        if case.get("conforming") is False:
            raise ValidationFailure(f"path-kind case {name}: a positive case must not carry conforming=false")
        if case.get("diagnostic") != expected_diag:
            raise ValidationFailure(f"path-kind case {name}: diagnostic is not the §4/§3 rule ({expected_diag!r})")
        if case.get("fragment_emitted") is not expected_fragment:
            raise ValidationFailure(f"path-kind case {name}: fragment verdict is not the §4 rule")
        if case.get("row_current") is not expected_current:
            raise ValidationFailure(f"path-kind case {name}: currency is not the §12 rule")
        if case.get("rebuild_planned") is not False:
            raise ValidationFailure(f"path-kind case {name}: a path source is never rebuilt")
        expected_check: str | None = failing[0] if failing else None
        if case.get("failing_check") != expected_check:
            raise ValidationFailure(f"path-kind case {name}: failing_check is not the §4 rule ({expected_check!r})")
        for field, value in expected_names.items():
            if case.get(field) != value:
                raise ValidationFailure(f"path-kind case {name}: {field} is not the §12 rule ({value!r})")

    dry_run = named_cases(vector.get("dry_run_cases"), "path-kind dry-run")
    if set(dry_run) != E6_DRY_RUN_CASES:
        raise ValidationFailure("path-kind dry-run case inventory is not exact")
    for name, case in dry_run.items():
        if case.get("role") not in E6_ROLES:
            raise ValidationFailure(f"path-kind case {name}: role must be one of {', '.join(E6_ROLES)}")
        if case.get("origin") not in E6_ORIGINS:
            raise ValidationFailure(f"path-kind case {name}: origin must be operator or onboarding-import")
        if not isinstance(case.get("direct"), bool) or not isinstance(case.get("carries_system_modules"), bool):
            raise ValidationFailure(f"path-kind case {name}: direct and carries_system_modules must be booleans")
        policy = case.get("machine_policy", {}).get("transitive_system_modules")
        if policy not in E6_POLICIES:
            raise ValidationFailure(f"path-kind case {name}: policy must be drop or error")
        path = case.get("path")
        if not isinstance(path, str) or not path.startswith("/"):
            raise ValidationFailure(f"path-kind case {name}: path must be an absolute directory")
        if not case.get("package"):
            raise ValidationFailure(f"path-kind case {name}: package must be named")
        if case["carries_system_modules"]:
            if not case.get("module"):
                raise ValidationFailure(f"path-kind case {name}: a system-module carrier names its module")
        elif case.get("module") is not None:
            raise ValidationFailure(f"path-kind case {name}: no module without system modules")
        inputs = e6_check_boundary_inputs(case, name)
        trusted, failing = e6_boundary_trusted(inputs)
        e6_check_boundary_pin(E6_DRY_RUN_PIN[name], case, failing, name)
        expected_diag = E6_DIAG_UNTRUSTED if not trusted else None
        expected_check: str | None = failing[0] if failing else None
        expected_names_path = path if not trusted else None
        if name in E6_DRY_RUN_NEGATIVE_CASES:
            if case.get("conforming") is not False or not case.get("reason"):
                raise ValidationFailure(f"path-kind case {name}: a negative needs conforming=false and a reason")
            if case.get("outcome") != S5_OUTCOME_WOULD_REBUILD:
                raise ValidationFailure(f"path-kind case {name}: this branch must report would-rebuild-untrusted-store")
            if (
                case.get("diagnostic") != expected_diag
                or case.get("mutated") is not False
                or case.get("rebuild_planned") is not False
                or case.get("failing_check") != expected_check
                or case.get("names_path") != expected_names_path
                or case.get("names_check") != expected_check
            ):
                raise ValidationFailure(f"path-kind case {name}: only the reported outcome violates the §10.1 rule")
            continue
        if case.get("conforming") is False:
            raise ValidationFailure(f"path-kind case {name}: a positive case must not carry conforming=false")
        if case.get("diagnostic") != expected_diag:
            raise ValidationFailure(f"path-kind case {name}: diagnostic is not the §10.4 rule ({expected_diag!r})")
        if case.get("outcome") is not None:
            raise ValidationFailure(f"path-kind case {name}: a path directory dry-run never plans a rebuild")
        if case.get("mutated") is not False:
            raise ValidationFailure(f"path-kind case {name}: dry-run evaluation mutates nothing")
        if case.get("rebuild_planned") is not False:
            raise ValidationFailure(f"path-kind case {name}: a path source is never rebuilt")
        if case.get("failing_check") != expected_check:
            raise ValidationFailure(f"path-kind case {name}: failing_check is not the §4 rule ({expected_check!r})")
        if case.get("names_path") != expected_names_path or case.get("names_check") != expected_check:
            raise ValidationFailure(f"path-kind case {name}: posture naming is not the §12 rule")


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


SHELL_HOOK_TRUST_FILES = (".agents/env.sh", ".agents/env.ps1")
SHELL_HOOK_TRUST_DIAGNOSTICS = ("shell_hook_env_unapproved", "shell_hook_env_changed")
SHELL_HOOK_TRUST_PROFILES = ("A-warning", "B-enforcing")
SHELL_HOOK_TRUST_APPROVERS = ("manager", "operator")
SHELL_HOOK_TRUST_FIXTURES = (
    "env-sh-v1",
    "env-sh-v2-changed",
    "env-ps1-v1",
    "env-ps1-v2-changed",
)
SHELL_HOOK_TRUST_CASES = frozenset(
    {
        "approved-env-sh-A-warning-sourced",
        "approved-env-sh-B-enforcing-sourced",
        "unapproved-env-sh-A-warning-sourced-with-warning",
        "unapproved-env-sh-B-enforcing-not-sourced",
        "changed-env-sh-A-warning-sourced-with-warning",
        "changed-env-sh-B-enforcing-not-sourced",
        "approved-env-ps1-A-warning-sourced",
        "approved-env-ps1-B-enforcing-sourced",
        "unapproved-env-ps1-A-warning-sourced-with-warning",
        "unapproved-env-ps1-B-enforcing-not-sourced",
        "changed-env-ps1-A-warning-sourced-with-warning",
        "changed-env-ps1-B-enforcing-not-sourced",
        "forged-project-record-env-sh-A-warning-sourced-with-warning",
        "forged-project-record-env-sh-B-enforcing-not-sourced",
    }
)
SHELL_HOOK_TRUST_DOWNSTREAM_OWNERS = ("TASK-260910-1952mz", "TASK-260910-3ungjy")
SHELL_HOOK_SHA256 = re.compile(r"[0-9a-f]{64}", re.ASCII)
SHELL_HOOK_RFC3339 = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", re.ASCII)


def check_shell_hook_approval_record(record: Any, label: str) -> None:
    if not isinstance(record, dict) or set(record) != {
        "path",
        "sha256",
        "approved_by",
        "approved_at",
    }:
        raise ValidationFailure(f"{label} is not the closed four-member approval record")
    if not isinstance(record["path"], str) or not record["path"].startswith("/"):
        raise ValidationFailure(f"{label} path is not absolute")
    if not isinstance(record["sha256"], str) or SHELL_HOOK_SHA256.fullmatch(record["sha256"]) is None:
        raise ValidationFailure(f"{label} sha256 is not lowercase hex without prefix")
    if record["approved_by"] not in SHELL_HOOK_TRUST_APPROVERS:
        raise ValidationFailure(f"{label} approved_by is not manager or operator")
    if not isinstance(record["approved_at"], str) or SHELL_HOOK_RFC3339.fullmatch(record["approved_at"]) is None:
        raise ValidationFailure(f"{label} approved_at is not an RFC 3339 timestamp")


def validate_shell_hook_trust_vectors(vector: Any = None) -> None:
    """The manager-profile section 8 trust-gate vector.

    Structural validation only: fixture digests are recomputed from the
    fixture bytes, and each case's sourced, diagnostic, and warning values
    are derived from its trust state and rollout profile. This gate never
    executes the emitted hook; downstream execution is owned by
    TASK-260910-1952mz and TASK-260910-3ungjy (profile section 8.7).
    """
    if vector is None:
        vector = load_json(SUITE / "vectors" / "shell-hook-trust.json")
    if (
        vector.get("schema_version") != 1
        or vector.get("protocol_version") != PROTOCOL_VERSION
        or vector.get("capability") != "shell-hook-trust"
        or vector.get("finding") != "S6"
    ):
        raise ValidationFailure("shell-hook-trust vector has the wrong capability identity")
    if vector.get("files") != list(SHELL_HOOK_TRUST_FILES):
        raise ValidationFailure("shell-hook-trust files are not the closed two-file set")
    if vector.get("diagnostics") != list(SHELL_HOOK_TRUST_DIAGNOSTICS):
        raise ValidationFailure("shell-hook-trust diagnostics are not the closed two-code set")
    profiles = {entry.get("name"): entry for entry in vector.get("rollout_profiles", [])}
    if set(profiles) != set(SHELL_HOOK_TRUST_PROFILES):
        raise ValidationFailure("shell-hook-trust rollout profiles are not exactly A-warning and B-enforcing")
    if profiles["A-warning"].get("sources_unapproved") is not True or profiles["A-warning"].get("sources_changed") is not True:
        raise ValidationFailure("shell-hook-trust Revision A must keep sourcing unapproved and changed files")
    if profiles["B-enforcing"].get("sources_unapproved") is not False or profiles["B-enforcing"].get("sources_changed") is not False:
        raise ValidationFailure("shell-hook-trust Revision B must not source unapproved or changed files")
    shape = vector.get("approval_record_shape", {})
    if shape.get("members") != ["path", "sha256", "approved_by", "approved_at"] or shape.get("approved_by") != list(SHELL_HOOK_TRUST_APPROVERS):
        raise ValidationFailure("shell-hook-trust approval record shape is not the closed four-member shape")
    check_shell_hook_approval_record(vector.get("example_record"), "shell-hook-trust example_record")

    fixtures = vector.get("fixtures", {})
    if set(fixtures) != set(SHELL_HOOK_TRUST_FIXTURES):
        raise ValidationFailure("shell-hook-trust fixture inventory is not exact")
    for fixture_id, fixture in fixtures.items():
        if fixture.get("file") not in SHELL_HOOK_TRUST_FILES:
            raise ValidationFailure(f"shell-hook-trust fixture {fixture_id} names a file outside the closed set")
        try:
            raw = base64.b64decode(fixture.get("bytes_base64", ""), validate=True)
        except ValueError as exc:
            raise ValidationFailure(f"shell-hook-trust fixture {fixture_id} bytes are not valid base64") from exc
        if hashlib.sha256(raw).hexdigest() != fixture.get("sha256"):
            raise ValidationFailure(f"shell-hook-trust fixture {fixture_id} sha256 does not match its bytes")

    binding = vector.get("execution_binding", {})
    if binding.get("downstream_owner_tasks") != list(SHELL_HOOK_TRUST_DOWNSTREAM_OWNERS):
        raise ValidationFailure("shell-hook-trust execution binding does not name the downstream owner tasks")
    recipe = vector.get("execution_recipe")
    if not isinstance(recipe, list) or not recipe or any(not isinstance(step, str) or not step for step in recipe):
        raise ValidationFailure("shell-hook-trust execution recipe is not a non-empty step list")
    sequence = vector.get("activation_sequence", {})
    if sequence.get("activations") != [
        "first activation in a fresh shell session",
        "second activation in the same shell session",
    ]:
        raise ValidationFailure("shell-hook-trust activation sequence is not the two-activation session pair")

    cases = named_cases(vector.get("cases"), "shell-hook trust")
    if set(cases) != SHELL_HOOK_TRUST_CASES:
        raise ValidationFailure("shell-hook-trust case inventory is not exact")
    for name, case in cases.items():
        fixture_id = case.get("candidate_fixture")
        if fixture_id not in fixtures:
            raise ValidationFailure(f"shell-hook-trust case {name} names an unknown fixture")
        fixture = fixtures[fixture_id]
        if case.get("file") != fixture["file"]:
            raise ValidationFailure(f"shell-hook-trust case {name} file does not match its fixture")
        if not isinstance(case.get("candidate_path"), str) or not case["candidate_path"].endswith("/" + case["file"]):
            raise ValidationFailure(f"shell-hook-trust case {name} candidate path does not name the fixture file")
        observed = case.get("observed_sha256")
        if observed != fixture["sha256"]:
            raise ValidationFailure(f"shell-hook-trust case {name} observed digest is not its fixture digest")
        if case.get("rollout_profile") not in SHELL_HOOK_TRUST_PROFILES:
            raise ValidationFailure(f"shell-hook-trust case {name} names an unknown rollout profile")

        approval = case.get("approval")
        record = case.get("manager_approval_record")
        if approval == "absent":
            if record is not None or case.get("recorded_sha256") is not None:
                raise ValidationFailure(f"shell-hook-trust case {name} is absent yet carries a record")
            if "approved_by" in case:
                raise ValidationFailure(f"shell-hook-trust case {name} is absent yet names an approver")
        elif approval in ("present-match", "present-mismatch"):
            check_shell_hook_approval_record(record, f"shell-hook-trust case {name} manager record")
            if record["path"] != case["candidate_path"]:
                raise ValidationFailure(f"shell-hook-trust case {name} record path is not the candidate path")
            if case.get("recorded_sha256") != record["sha256"]:
                raise ValidationFailure(f"shell-hook-trust case {name} recorded digest is not its record digest")
            if case.get("approved_by") != record["approved_by"]:
                raise ValidationFailure(f"shell-hook-trust case {name} approver is not its record approver")
            match = record["sha256"] == observed
            if (approval == "present-match") != match:
                raise ValidationFailure(f"shell-hook-trust case {name} approval state contradicts its digests")
        else:
            raise ValidationFailure(f"shell-hook-trust case {name} has an unknown approval state")

        forged = case.get("project_supplied_record")
        if name.startswith("forged-project-record-"):
            if not isinstance(forged, dict) or not str(forged.get("source", "")).startswith("project:"):
                raise ValidationFailure(f"shell-hook-trust case {name} must carry a project-sourced forged record")
            check_shell_hook_approval_record(forged.get("record"), f"shell-hook-trust case {name} forged record")
            if forged["record"]["sha256"] != observed:
                raise ValidationFailure(f"shell-hook-trust case {name} forged record must match the observed bytes")
        elif forged is not None:
            raise ValidationFailure(f"shell-hook-trust case {name} carries a forged record outside the forged family")

        trusted = record is not None and record["sha256"] == observed
        if trusted:
            expected_diagnostic = None
        elif record is None:
            expected_diagnostic = "shell_hook_env_unapproved"
        else:
            expected_diagnostic = "shell_hook_env_changed"
        if case.get("diagnostic") != expected_diagnostic:
            raise ValidationFailure(f"shell-hook-trust case {name} diagnostic does not follow its trust state")
        expected_sourced = trusted or case["rollout_profile"] == "A-warning"
        if case.get("sourced") is not expected_sourced:
            raise ValidationFailure(f"shell-hook-trust case {name} sourcing does not follow its trust state and profile")
        warned = not trusted
        warning_checks = {
            "warns_once_per_shell_session": warned,
            "warning_first_activation": warned,
            "warning_second_activation_same_session": False,
            "warnings_total_across_two_activations": 1 if warned else 0,
            "warning_names_path": warned,
            "warning_names_approval_command": warned,
            "migration_hint_names_approval_command": warned,
        }
        for field, expected in warning_checks.items():
            if case.get(field) is not expected:
                raise ValidationFailure(f"shell-hook-trust case {name} field {field} does not follow its trust state")


WRITE_NOFOLLOW_WRITE_CLASSES = ("materialize", "takeover", "repair", "backup")
WRITE_NOFOLLOW_MODES = ("linked", "copied", "managed-home")
WRITE_NOFOLLOW_OUTCOMES = ("written", "replaced", "refused")
WRITE_NOFOLLOW_DIAGNOSTICS = (
    "environment_write_would_follow_link",
    "environment_foreign_manager_detected",
    "environment_surface_unmanaged_conflict",
)
WRITE_NOFOLLOW_TARGET_KINDS = ("absent", "file", "symlink")
WRITE_NOFOLLOW_LINK_POINTS = ("outside", "store")
WRITE_NOFOLLOW_ENTRY_STATES = ("managed-file", "managed-link", "unchanged")
WRITE_NOFOLLOW_FIXTURES = ("foreign-notes", "managed-root-context")
# Each required scenario pinned to its discriminating inputs (producer
# rule 7): a named case rewritten as an internally consistent passing case
# under the same name must be refused, not merely inventoried.
WRITE_NOFOLLOW_SCENARIOS = {
    "takeover-symlinked-target-authorized-replaced": {
        "operation": "takeover",
        "mode": "linked",
        "takeover_authorized": True,
        "marker_records_target": False,
        "target_kind": "symlink",
        "link_owner": "foreign",
        "link_points": "outside",
        "parent_link_points": None,
        "foreign_target_fixture": "foreign-notes",
    },
    "takeover-symlinked-target-unauthorized-stopped": {
        "operation": "takeover",
        "mode": "linked",
        "takeover_authorized": False,
        "marker_records_target": False,
        "target_kind": "symlink",
        "link_owner": "foreign",
        "link_points": "outside",
        "parent_link_points": None,
        "foreign_target_fixture": "foreign-notes",
    },
    "materialize-symlinked-parent-refused": {
        "operation": "materialize",
        "mode": "managed-home",
        "takeover_authorized": False,
        "marker_records_target": False,
        "target_kind": "absent",
        "link_owner": None,
        "link_points": None,
        "parent_link_points": "outside",
        "foreign_target_fixture": "foreign-notes",
    },
    "takeover-symlinked-parent-authorized-still-refused": {
        "operation": "takeover",
        "mode": "linked",
        "takeover_authorized": True,
        "marker_records_target": False,
        "target_kind": "symlink",
        "link_owner": "foreign",
        "link_points": "outside",
        "parent_link_points": "outside",
        "foreign_target_fixture": "foreign-notes",
    },
    "repair-planted-link-replaced": {
        "operation": "repair",
        "mode": "copied",
        "takeover_authorized": False,
        "marker_records_target": True,
        "target_kind": "symlink",
        "link_owner": "foreign",
        "link_points": "outside",
        "parent_link_points": None,
        "foreign_target_fixture": "foreign-notes",
    },
    "repair-manager-owned-link-replaced": {
        "operation": "repair",
        "mode": "linked",
        "takeover_authorized": False,
        "marker_records_target": True,
        "target_kind": "symlink",
        "link_owner": "manager",
        "link_points": "store",
        "parent_link_points": None,
        "foreign_target_fixture": None,
    },
    "backup-symlinked-destination-refused": {
        "operation": "backup",
        "mode": "copied",
        "takeover_authorized": False,
        "marker_records_target": False,
        "target_kind": "absent",
        "link_owner": None,
        "link_points": None,
        "parent_link_points": "outside",
        "foreign_target_fixture": "foreign-notes",
    },
    "backup-symlinked-target-refused": {
        "operation": "backup",
        "mode": "copied",
        "takeover_authorized": False,
        "marker_records_target": False,
        "target_kind": "symlink",
        "link_owner": "foreign",
        "link_points": "outside",
        "parent_link_points": None,
        "foreign_target_fixture": "foreign-notes",
    },
    "materialize-clean-path-written": {
        "operation": "materialize",
        "mode": "managed-home",
        "takeover_authorized": False,
        "marker_records_target": False,
        "target_kind": "absent",
        "link_owner": None,
        "link_points": None,
        "parent_link_points": None,
        "foreign_target_fixture": None,
    },
    "takeover-inside-link-unauthorized-unmanaged-conflict": {
        "operation": "takeover",
        "mode": "linked",
        "takeover_authorized": False,
        "marker_records_target": False,
        "target_kind": "symlink",
        "link_owner": "foreign",
        "link_points": "store",
        "parent_link_points": None,
        "foreign_target_fixture": "foreign-notes",
    },
    "materialize-recorded-file-replaced": {
        "operation": "materialize",
        "mode": "copied",
        "takeover_authorized": False,
        "marker_records_target": True,
        "target_kind": "file",
        "link_owner": None,
        "link_points": None,
        "parent_link_points": None,
        "foreign_target_fixture": None,
    },
}
WRITE_NOFOLLOW_CASES = frozenset(WRITE_NOFOLLOW_SCENARIOS)


def _validate_write_nofollow_case(name: str, case: dict[str, Any], fixtures: dict[str, Any]) -> None:
    label = f"environments-write-nofollow case {name}"
    operation = case.get("operation")
    if operation not in WRITE_NOFOLLOW_WRITE_CLASSES:
        raise ValidationFailure(f"{label} names an unknown write class")
    if case.get("mode") not in WRITE_NOFOLLOW_MODES:
        raise ValidationFailure(f"{label} names an unknown mode")
    authorized = case.get("takeover_authorized")
    recorded = case.get("marker_records_target")
    if authorized not in (True, False) or recorded not in (True, False):
        raise ValidationFailure(f"{label} authorization and marker flags must be booleans")
    target = case.get("target", {})
    if not isinstance(target, dict):
        raise ValidationFailure(f"{label} target is not an object")
    kind = target.get("kind")
    if kind not in WRITE_NOFOLLOW_TARGET_KINDS:
        raise ValidationFailure(f"{label} names an unknown target kind")
    points = target.get("link_points")
    owner = target.get("link_owner")
    if kind == "symlink":
        if points not in WRITE_NOFOLLOW_LINK_POINTS:
            raise ValidationFailure(f"{label} symlink target must point outside or to the store")
        if owner not in ("manager", "foreign"):
            raise ValidationFailure(f"{label} symlink target must be manager- or foreign-owned")
        if owner == "manager" and not recorded:
            raise ValidationFailure(f"{label} manager-owned link must be a recorded entry")
    elif points is not None or owner is not None:
        raise ValidationFailure(f"{label} non-link target must not carry link fields")
    parent = case.get("parent_link")
    if parent is not None and (
        not isinstance(parent, dict) or parent.get("link_points") not in WRITE_NOFOLLOW_LINK_POINTS
    ):
        raise ValidationFailure(f"{label} parent link must point outside or to the store")
    if case.get("managed_fixture") != "managed-root-context":
        raise ValidationFailure(f"{label} managed fixture is not managed-root-context")

    pinned = WRITE_NOFOLLOW_SCENARIOS.get(name)
    actual = {
        "operation": operation,
        "mode": case.get("mode"),
        "takeover_authorized": authorized,
        "marker_records_target": recorded,
        "target_kind": kind,
        "link_owner": owner,
        "link_points": points,
        "parent_link_points": parent.get("link_points") if parent is not None else None,
        "foreign_target_fixture": case.get("foreign_target_fixture"),
    }
    if pinned is None or actual != pinned:
        raise ValidationFailure(f"{label} inputs do not match its pinned scenario")

    # Derive the section 8.3.1 disposition: a non-manager parent link
    # refuses first, then a manager-private destination naming a link,
    # then the managed-surface target-link rule, then the clean path.
    expected_diagnostic: Any = None
    if parent is not None:
        expected_outcome = "refused"
        expected_diagnostic = "environment_write_would_follow_link"
    elif operation == "backup" and kind == "symlink":
        # Manager-private destination (§8.3.1): a backup path has no ledger
        # or takeover machinery of its own, so any pre-existing link at
        # the destination refuses with the nofollow code — never the
        # section 9.5 foreign-manager stop.
        expected_outcome = "refused"
        expected_diagnostic = "environment_write_would_follow_link"
    elif kind == "symlink":
        if recorded or owner == "manager":
            expected_outcome = "replaced"
        elif points == "outside":
            if operation == "takeover" and authorized:
                expected_outcome = "replaced"
            else:
                expected_outcome = "refused"
                expected_diagnostic = "environment_foreign_manager_detected"
        elif operation == "takeover" and authorized:
            expected_outcome = "replaced"
        else:
            expected_outcome = "refused"
            expected_diagnostic = "environment_surface_unmanaged_conflict"
    elif kind == "absent":
        expected_outcome = "written"
    elif recorded:
        expected_outcome = "replaced"
    else:
        raise ValidationFailure(f"{label} unrecorded regular file is outside this vector's scope")

    expected = case.get("expected", {})
    if expected.get("outcome") != expected_outcome:
        raise ValidationFailure(f"{label} outcome does not follow the section 8.3.1 disposition")
    if expected.get("diagnostic") != expected_diagnostic:
        raise ValidationFailure(f"{label} diagnostic does not follow the section 8.3.1 disposition")

    backup = kind == "symlink" and expected_outcome == "replaced" and not (recorded or owner == "manager")
    if expected.get("backup_holds_link") is not backup:
        raise ValidationFailure(f"{label} backup expectation does not follow its disposition")

    if expected_outcome == "refused":
        expected_entry = "unchanged"
    elif kind == "symlink" and recorded and case.get("mode") == "linked":
        expected_entry = "managed-link"
    else:
        expected_entry = "managed-file"
    if expected.get("entry_after") != expected_entry:
        raise ValidationFailure(f"{label} entry state does not follow its disposition")

    foreign_id = case.get("foreign_target_fixture")
    foreign_after = expected.get("foreign_target_sha256_after")
    has_foreign_link = (kind == "symlink" and owner == "foreign") or parent is not None
    if has_foreign_link:
        if foreign_id not in fixtures:
            raise ValidationFailure(f"{label} names an unknown foreign-target fixture")
        if foreign_after != fixtures[foreign_id]["sha256"]:
            raise ValidationFailure(f"{label} foreign target is not byte-identical afterwards")
    elif foreign_id is not None or foreign_after is not None:
        raise ValidationFailure(f"{label} carries a foreign target without a foreign link")


def validate_environments_write_nofollow_vectors(vector: Any = None) -> None:
    """The environments section 8.3.1 nofollow write-discipline vector.

    Structural validation only: fixture digests are recomputed from the
    fixture bytes, each named case is pinned to its discriminating inputs,
    and each case's outcome, diagnostic, backup, entry, and untouched-target
    values are derived from the section 8.3.1 disposition model. This gate
    never touches the filesystem; behavioral conformance is owned by the
    manager implementation task TASK-260916-19shmj.
    """
    if vector is None:
        vector = load_json(SUITE / "vectors" / "environments-write-nofollow.json")
    if (
        vector.get("schema_version") != 1
        or vector.get("protocol_version") != PROTOCOL_VERSION
        or vector.get("capability") != "agent-environments"
        or vector.get("capability_revision") != 1
        or vector.get("finding") != "E5"
    ):
        raise ValidationFailure("environments-write-nofollow vector has the wrong capability identity")
    if vector.get("write_classes") != list(WRITE_NOFOLLOW_WRITE_CLASSES):
        raise ValidationFailure("environments-write-nofollow write classes are not the closed four-class set")
    if vector.get("modes") != list(WRITE_NOFOLLOW_MODES):
        raise ValidationFailure("environments-write-nofollow modes are not the closed three-mode set")
    if vector.get("outcomes") != list(WRITE_NOFOLLOW_OUTCOMES):
        raise ValidationFailure("environments-write-nofollow outcomes are not the closed three-outcome set")
    if vector.get("diagnostics") != list(WRITE_NOFOLLOW_DIAGNOSTICS):
        raise ValidationFailure("environments-write-nofollow diagnostics are not the closed three-code set")
    if vector.get("target_kinds") != list(WRITE_NOFOLLOW_TARGET_KINDS):
        raise ValidationFailure("environments-write-nofollow target kinds are not the closed three-kind set")
    if vector.get("link_points_values") != list(WRITE_NOFOLLOW_LINK_POINTS):
        raise ValidationFailure("environments-write-nofollow link-points values are not the closed two-value set")
    if vector.get("entry_states") != list(WRITE_NOFOLLOW_ENTRY_STATES):
        raise ValidationFailure("environments-write-nofollow entry states are not the closed three-state set")

    fixtures = vector.get("fixtures", {})
    if set(fixtures) != set(WRITE_NOFOLLOW_FIXTURES):
        raise ValidationFailure("environments-write-nofollow fixture inventory is not exact")
    for fixture_id, fixture in fixtures.items():
        raw = decode_base64(
            fixture.get("bytes_base64"),
            f"environments-write-nofollow fixture {fixture_id} bytes",
        )
        if hashlib.sha256(raw).hexdigest() != fixture.get("sha256"):
            raise ValidationFailure(f"environments-write-nofollow fixture {fixture_id} sha256 does not match its bytes")

    cases = named_cases(vector.get("cases"), "environments write-nofollow")
    if set(cases) != WRITE_NOFOLLOW_CASES:
        raise ValidationFailure("environments-write-nofollow case inventory is not exact")
    for name, case in cases.items():
        _validate_write_nofollow_case(name, case, fixtures)


DOTFILE_MANAGERS = ("chezmoi", "home-manager", "yadm", "stow", "dotbot")
DOTFILE_PLATFORMS = ("macos", "linux", "windows")
DOTFILE_LOCATION_STATES = ("directory", "absent", "symlink", "file", "unreadable")
DOTFILE_DIAGNOSTIC = "environment_foreign_manager_suspected"
DOTFILE_RULE = "environments section 9.5 dotfile-manager state table"
DOTFILE_ENV_KEYS = ("XDG_DATA_HOME", "XDG_CONFIG_HOME")
# The section 9.5 closed table, pinned cell by cell: each located cell is
# (xdg base variable, leaf name); None is an explicit none — there is no
# path to check on that platform. Row order is the heuristic scan order:
# the notice names the first row in this order whose location is present.
DOTFILE_TABLE = {
    "chezmoi": {
        "macos": ("XDG_DATA_HOME", "chezmoi"),
        "linux": ("XDG_DATA_HOME", "chezmoi"),
        "windows": ("XDG_DATA_HOME", "chezmoi"),
    },
    "home-manager": {
        "macos": ("XDG_CONFIG_HOME", "home-manager"),
        "linux": ("XDG_CONFIG_HOME", "home-manager"),
        "windows": None,
    },
    "yadm": {
        "macos": ("XDG_DATA_HOME", "yadm"),
        "linux": ("XDG_DATA_HOME", "yadm"),
        "windows": None,
    },
    "stow": {"macos": None, "linux": None, "windows": None},
    "dotbot": {"macos": None, "linux": None, "windows": None},
}
DOTFILE_CASE_KEYS = frozenset({"name", "platform", "home", "env", "states", "expected"})
DOTFILE_EXPECTED_KEYS = frozenset({"notice", "names_manager", "resolved_path", "blocks"})
# Each required scenario pinned to its discriminating inputs (producer
# rule 7): a named case rewritten as an internally consistent passing
# case under the same name must be refused, not merely inventoried.
DOTFILE_SCENARIOS = {
    "chezmoi-linux-present-suspected": {
        "platform": "linux",
        "home": "/home/operator",
        "env": {},
        "states": {
            "chezmoi": "directory",
            "dotbot": None,
            "home-manager": "absent",
            "stow": None,
            "yadm": "absent",
        },
    },
    "chezmoi-macos-present-suspected": {
        "platform": "macos",
        "home": "/Users/operator",
        "env": {},
        "states": {
            "chezmoi": "directory",
            "dotbot": None,
            "home-manager": "absent",
            "stow": None,
            "yadm": "absent",
        },
    },
    "chezmoi-windows-present-suspected": {
        "platform": "windows",
        "home": "C:\\Users\\operator",
        "env": {},
        "states": {
            "chezmoi": "directory",
            "dotbot": None,
            "home-manager": None,
            "stow": None,
            "yadm": None,
        },
    },
    "home-manager-linux-present-suspected": {
        "platform": "linux",
        "home": "/home/operator",
        "env": {},
        "states": {
            "chezmoi": "absent",
            "dotbot": None,
            "home-manager": "directory",
            "stow": None,
            "yadm": "absent",
        },
    },
    "home-manager-macos-present-suspected": {
        "platform": "macos",
        "home": "/Users/operator",
        "env": {},
        "states": {
            "chezmoi": "absent",
            "dotbot": None,
            "home-manager": "directory",
            "stow": None,
            "yadm": "absent",
        },
    },
    "yadm-linux-present-suspected": {
        "platform": "linux",
        "home": "/home/operator",
        "env": {},
        "states": {
            "chezmoi": "absent",
            "dotbot": None,
            "home-manager": "absent",
            "stow": None,
            "yadm": "directory",
        },
    },
    "yadm-macos-present-suspected": {
        "platform": "macos",
        "home": "/Users/operator",
        "env": {},
        "states": {
            "chezmoi": "absent",
            "dotbot": None,
            "home-manager": "absent",
            "stow": None,
            "yadm": "directory",
        },
    },
    "linux-all-absent-quiet": {
        "platform": "linux",
        "home": "/home/operator",
        "env": {},
        "states": {
            "chezmoi": "absent",
            "dotbot": None,
            "home-manager": "absent",
            "stow": None,
            "yadm": "absent",
        },
    },
    "macos-all-absent-quiet": {
        "platform": "macos",
        "home": "/Users/operator",
        "env": {},
        "states": {
            "chezmoi": "absent",
            "dotbot": None,
            "home-manager": "absent",
            "stow": None,
            "yadm": "absent",
        },
    },
    "windows-all-absent-quiet": {
        "platform": "windows",
        "home": "C:\\Users\\operator",
        "env": {},
        "states": {
            "chezmoi": "absent",
            "dotbot": None,
            "home-manager": None,
            "stow": None,
            "yadm": None,
        },
    },
    "chezmoi-linux-xdg-data-home-relocated": {
        "platform": "linux",
        "home": "/home/operator",
        "env": {"XDG_DATA_HOME": "/data"},
        "states": {
            "chezmoi": "directory",
            "dotbot": None,
            "home-manager": "absent",
            "stow": None,
            "yadm": "absent",
        },
    },
    "chezmoi-linux-xdg-data-home-empty-uses-default": {
        "platform": "linux",
        "home": "/home/operator",
        "env": {"XDG_DATA_HOME": ""},
        "states": {
            "chezmoi": "directory",
            "dotbot": None,
            "home-manager": "absent",
            "stow": None,
            "yadm": "absent",
        },
    },
    "chezmoi-linux-xdg-data-home-relative-uses-default": {
        "platform": "linux",
        "home": "/home/operator",
        "env": {"XDG_DATA_HOME": "rel/path"},
        "states": {
            "chezmoi": "directory",
            "dotbot": None,
            "home-manager": "absent",
            "stow": None,
            "yadm": "absent",
        },
    },
    "home-manager-linux-xdg-config-home-relocated": {
        "platform": "linux",
        "home": "/home/operator",
        "env": {"XDG_CONFIG_HOME": "/cfg"},
        "states": {
            "chezmoi": "absent",
            "dotbot": None,
            "home-manager": "directory",
            "stow": None,
            "yadm": "absent",
        },
    },
    "home-manager-linux-xdg-config-home-relative-uses-default": {
        "platform": "linux",
        "home": "/home/operator",
        "env": {"XDG_CONFIG_HOME": "rel/cfg"},
        "states": {
            "chezmoi": "absent",
            "dotbot": None,
            "home-manager": "directory",
            "stow": None,
            "yadm": "absent",
        },
    },
    "yadm-macos-xdg-data-home-relocated": {
        "platform": "macos",
        "home": "/Users/operator",
        "env": {"XDG_DATA_HOME": "/Volumes/data"},
        "states": {
            "chezmoi": "absent",
            "dotbot": None,
            "home-manager": "absent",
            "stow": None,
            "yadm": "directory",
        },
    },
    "chezmoi-windows-xdg-data-home-relocated": {
        "platform": "windows",
        "home": "C:\\Users\\operator",
        "env": {"XDG_DATA_HOME": "D:\\data"},
        "states": {
            "chezmoi": "directory",
            "dotbot": None,
            "home-manager": None,
            "stow": None,
            "yadm": None,
        },
    },
    "chezmoi-linux-symlink-quiet": {
        "platform": "linux",
        "home": "/home/operator",
        "env": {},
        "states": {
            "chezmoi": "symlink",
            "dotbot": None,
            "home-manager": "absent",
            "stow": None,
            "yadm": "absent",
        },
    },
    "yadm-linux-regular-file-quiet": {
        "platform": "linux",
        "home": "/home/operator",
        "env": {},
        "states": {
            "chezmoi": "absent",
            "dotbot": None,
            "home-manager": "absent",
            "stow": None,
            "yadm": "file",
        },
    },
    "home-manager-linux-unreadable-quiet": {
        "platform": "linux",
        "home": "/home/operator",
        "env": {},
        "states": {
            "chezmoi": "absent",
            "dotbot": None,
            "home-manager": "unreadable",
            "stow": None,
            "yadm": "absent",
        },
    },
    "linux-chezmoi-and-yadm-names-chezmoi": {
        "platform": "linux",
        "home": "/home/operator",
        "env": {},
        "states": {
            "chezmoi": "directory",
            "dotbot": None,
            "home-manager": "absent",
            "stow": None,
            "yadm": "directory",
        },
    },
    "macos-home-manager-and-yadm-names-home-manager": {
        "platform": "macos",
        "home": "/Users/operator",
        "env": {},
        "states": {
            "chezmoi": "absent",
            "dotbot": None,
            "home-manager": "directory",
            "stow": None,
            "yadm": "directory",
        },
    },
}
DOTFILE_CASES = frozenset(DOTFILE_SCENARIOS)


def _dotfile_is_absolute(platform: str, value: str) -> bool:
    if platform == "windows":
        return value.startswith("\\\\") or re.match(r"^[A-Za-z]:[\\/]", value) is not None
    return value.startswith("/")


def _dotfile_join(platform: str, base: str, *rest: str) -> str:
    sep = "\\" if platform == "windows" else "/"
    out = base
    for part in rest:
        out += sep + part
    return out


def _dotfile_resolve(
    platform: str, home: str, env: dict[str, Any], cell: tuple[str, str] | None
) -> str | None:
    if cell is None:
        return None
    base, leaf = cell
    override = env.get(base, "")
    if isinstance(override, str) and override and _dotfile_is_absolute(platform, override):
        root = override
    elif base == "XDG_DATA_HOME":
        root = _dotfile_join(platform, home, ".local", "share")
    else:
        root = _dotfile_join(platform, home, ".config")
    return _dotfile_join(platform, root, leaf)


def _validate_dotfile_case(name: str, case: dict[str, Any]) -> None:
    label = f"environments-dotfile-managers case {name}"
    if set(case) != DOTFILE_CASE_KEYS:
        raise ValidationFailure(f"{label} is not exactly {{ name, platform, home, env, states, expected }}")
    platform = case.get("platform")
    if platform not in DOTFILE_PLATFORMS:
        raise ValidationFailure(f"{label} names an unknown platform")
    home = case.get("home")
    if not isinstance(home, str) or not home or not _dotfile_is_absolute(platform, home):
        raise ValidationFailure(f"{label} home is not a non-empty absolute path")
    env = case.get("env")
    if not isinstance(env, dict) or any(key not in DOTFILE_ENV_KEYS for key in env):
        raise ValidationFailure(f"{label} env carries a variable outside the closed XDG pair")
    for key, value in env.items():
        if not isinstance(value, str) or value.endswith(("/", "\\")):
            raise ValidationFailure(f"{label} env {key} is not a string without a trailing separator")
    states = case.get("states")
    if not isinstance(states, dict) or set(states) != set(DOTFILE_MANAGERS):
        raise ValidationFailure(f"{label} states do not cover exactly the five managers")
    for manager in DOTFILE_MANAGERS:
        cell = DOTFILE_TABLE[manager][platform]
        state = states[manager]
        if cell is None:
            if state is not None:
                raise ValidationFailure(
                    f"{label} inspects a none cell ({manager} has no path on {platform})"
                )
        elif state not in DOTFILE_LOCATION_STATES:
            raise ValidationFailure(f"{label} {manager} state is outside the closed five-state set")
    pinned = DOTFILE_SCENARIOS.get(name)
    actual = {"platform": platform, "home": home, "env": env, "states": states}
    if pinned is None or actual != pinned:
        raise ValidationFailure(f"{label} inputs do not match its pinned scenario")
    resolved = {
        manager: _dotfile_resolve(platform, home, env, DOTFILE_TABLE[manager][platform])
        for manager in DOTFILE_MANAGERS
    }
    winner = next((manager for manager in DOTFILE_MANAGERS if states[manager] == "directory"), None)
    expected = case.get("expected")
    if not isinstance(expected, dict) or set(expected) != DOTFILE_EXPECTED_KEYS:
        raise ValidationFailure(f"{label} expected is not the closed four-field set")
    if expected.get("blocks") is not False:
        raise ValidationFailure(f"{label} heuristic blocks; the section 9.5 heuristic never blocks")
    if (
        expected.get("notice") != (DOTFILE_DIAGNOSTIC if winner else None)
        or expected.get("names_manager") != winner
        or expected.get("resolved_path") != (resolved[winner] if winner else None)
    ):
        raise ValidationFailure(f"{label} notice does not follow the table-order first-present rule")


def validate_environments_dotfile_managers_vectors(vector: Any = None) -> None:
    """The environments section 9.5 dotfile-manager state-table vector.

    Structural validation only: the closed manager order, platform set,
    location-state vocabulary, and the table itself are pinned cell by
    cell; each named case is pinned to its discriminating inputs; and
    every resolved path, notice, and named manager is recomputed from
    the section 9.5 resolution rules. This gate never touches the
    filesystem; behavioral conformance is owned by the manager
    implementation task created after this spec lands (STORY-260916-12lbww).
    """
    if vector is None:
        vector = load_json(SUITE / "vectors" / "environments-dotfile-managers.json")
    if (
        vector.get("schema_version") != 1
        or vector.get("protocol_version") != PROTOCOL_VERSION
        or vector.get("capability") != "agent-environments"
        or vector.get("capability_revision") != 1
        or vector.get("rule") != DOTFILE_RULE
    ):
        raise ValidationFailure("environments-dotfile-managers vector has the wrong capability identity")
    if vector.get("managers") != list(DOTFILE_MANAGERS):
        raise ValidationFailure("environments-dotfile-managers managers are not the closed ordered five-manager set")
    if vector.get("platforms") != list(DOTFILE_PLATFORMS):
        raise ValidationFailure("environments-dotfile-managers platforms are not the closed three-platform set")
    if vector.get("location_states") != list(DOTFILE_LOCATION_STATES):
        raise ValidationFailure("environments-dotfile-managers location states are not the closed five-state set")
    if vector.get("diagnostic") != DOTFILE_DIAGNOSTIC:
        raise ValidationFailure(
            "environments-dotfile-managers diagnostic is not environment_foreign_manager_suspected"
        )
    rows = vector.get("table")
    if (
        not isinstance(rows, list)
        or [row.get("manager") for row in rows if isinstance(row, dict)] != list(DOTFILE_MANAGERS)
    ):
        raise ValidationFailure("environments-dotfile-managers table rows are not the closed ordered five-manager set")
    for row in rows:
        manager = row["manager"]
        if set(row) != {"manager", "macos", "linux", "windows"}:
            raise ValidationFailure(
                f"environments-dotfile-managers table row {manager} is not exactly one cell per platform"
            )
        for platform in DOTFILE_PLATFORMS:
            want = DOTFILE_TABLE[manager][platform]
            cell = row[platform]
            if want is None:
                if cell is not None:
                    raise ValidationFailure(
                        f"environments-dotfile-managers table cell {manager}/{platform} is not the pinned none"
                    )
            elif (
                not isinstance(cell, dict)
                or set(cell) != {"base", "leaf"}
                or (cell.get("base"), cell.get("leaf")) != want
            ):
                raise ValidationFailure(
                    f"environments-dotfile-managers table cell {manager}/{platform} is not the pinned location"
                )
    cases = named_cases(vector.get("cases"), "environments dotfile managers")
    if set(cases) != DOTFILE_CASES:
        raise ValidationFailure("environments-dotfile-managers case inventory is not exact")
    for name, case in cases.items():
        _validate_dotfile_case(name, case)


READ_FAILURE_DIAGNOSTICS = (
    "environment_backup_record_unreadable",
    "environment_home_stale",
    "environment_marker_unreadable",
    "environment_passthrough_detached",
    "environment_passthrough_unreadable",
    "environment_seed_unreadable",
    "environment_store_untrusted",
    "profile_unknown",
)
READ_FAILURE_FILE_CLASSES = ("backup-record", "lock", "marker", "passthrough", "seed")
READ_FAILURE_OPERATIONS = ("env-resolve", "env-status", "provision", "repair", "restore", "update")
READ_FAILURE_PRESENCE_VALUES = ("absent", "present")
READ_FAILURE_ENTRY_KINDS = ("directory", "file", "missing", "symlink")
READ_FAILURE_FAILURE_CLASSES = (
    "directory-where-file-expected",
    "io-error",
    "parent-not-directory",
    "permission-denied",
    "schema-invalid-content",
    "symlink-where-regular-required",
    "unparseable-content",
)
READ_FAILURE_CURRENCIES = ("known", "unknown")
# Failure classes applicable per file class (section 8.4.1): a marker failure
# that violates the section 4 contract, or that prevents proving the boundary,
# is environment_store_untrusted and is outside this family, so markers cover
# the open/read/parse stages only; seeds are unparsed byte copies except the
# codex_cli revision-B strip, so schema-invalid-content does not apply to them;
# passthrough entries carry no content and require a link, so only the
# lstat/readlink failure classes apply to them; backup-record inventories are
# listed, never parsed, and their inventory root is a directory, so only the
# list/stat failure classes apply to them.
READ_FAILURE_APPLICABLE = {
    "backup-record": frozenset(
        {"permission-denied", "io-error", "parent-not-directory"}
    ),
    "marker": frozenset(
        {
            "permission-denied",
            "io-error",
            "unparseable-content",
            "schema-invalid-content",
        }
    ),
    "lock": frozenset(READ_FAILURE_FAILURE_CLASSES),
    "seed": frozenset(
        {
            "permission-denied",
            "io-error",
            "unparseable-content",
            "symlink-where-regular-required",
            "directory-where-file-expected",
            "parent-not-directory",
        }
    ),
    "passthrough": frozenset(
        {"permission-denied", "io-error", "parent-not-directory"}
    ),
}
# Each required scenario pinned to its typed discriminating inputs (producer
# rule 7): a named case rewritten as another branch's passing case under the
# same name — or with its failure class collapsed to another — must be
# refused, not merely inventoried.
READ_FAILURE_SCENARIOS = {
    "marker-open-permission-denied-unreadable": {
        "file_class": "marker",
        "operation": "env-resolve",
        "presence": "present",
        "entry_kind": "file",
        "failure_class": "permission-denied",
    },
    "marker-read-io-error-unreadable": {
        "file_class": "marker",
        "operation": "env-resolve",
        "presence": "present",
        "entry_kind": "file",
        "failure_class": "io-error",
    },
    "marker-unparseable-content-unreadable": {
        "file_class": "marker",
        "operation": "env-resolve",
        "presence": "present",
        "entry_kind": "file",
        "failure_class": "unparseable-content",
    },
    "marker-schema-invalid-content-unreadable": {
        "file_class": "marker",
        "operation": "env-resolve",
        "presence": "present",
        "entry_kind": "file",
        "failure_class": "schema-invalid-content",
    },
    "marker-absent-unprovisioned-stale": {
        "file_class": "marker",
        "operation": "env-resolve",
        "presence": "absent",
        "entry_kind": "missing",
        "failure_class": None,
    },
    "marker-unreadable-reported-stale": {
        "file_class": "marker",
        "operation": "env-resolve",
        "presence": "present",
        "entry_kind": "file",
        "failure_class": "permission-denied",
    },
    "lock-open-permission-denied-untrusted": {
        "file_class": "lock",
        "operation": "env-resolve",
        "presence": "present",
        "entry_kind": "file",
        "failure_class": "permission-denied",
    },
    "lock-read-io-error-untrusted": {
        "file_class": "lock",
        "operation": "env-resolve",
        "presence": "present",
        "entry_kind": "file",
        "failure_class": "io-error",
    },
    "lock-unparseable-content-untrusted": {
        "file_class": "lock",
        "operation": "env-resolve",
        "presence": "present",
        "entry_kind": "file",
        "failure_class": "unparseable-content",
    },
    "lock-schema-invalid-content-untrusted": {
        "file_class": "lock",
        "operation": "env-resolve",
        "presence": "present",
        "entry_kind": "file",
        "failure_class": "schema-invalid-content",
    },
    "lock-symlink-where-regular-required-untrusted": {
        "file_class": "lock",
        "operation": "env-resolve",
        "presence": "present",
        "entry_kind": "symlink",
        "failure_class": "symlink-where-regular-required",
    },
    "lock-directory-where-file-expected-untrusted": {
        "file_class": "lock",
        "operation": "env-resolve",
        "presence": "present",
        "entry_kind": "directory",
        "failure_class": "directory-where-file-expected",
    },
    "lock-parent-not-directory-untrusted": {
        "file_class": "lock",
        "operation": "env-resolve",
        "presence": "present",
        "entry_kind": "file",
        "failure_class": "parent-not-directory",
    },
    "lock-absent-profile-unknown": {
        "file_class": "lock",
        "operation": "env-resolve",
        "presence": "absent",
        "entry_kind": "missing",
        "failure_class": None,
    },
    "lock-unreadable-reported-unknown": {
        "file_class": "lock",
        "operation": "env-resolve",
        "presence": "present",
        "entry_kind": "file",
        "failure_class": "permission-denied",
    },
    "lock-unreadable-repair-refused-no-rebuild": {
        "file_class": "lock",
        "operation": "repair",
        "presence": "present",
        "entry_kind": "file",
        "failure_class": "permission-denied",
    },
    "lock-unreadable-update-refused-no-rebuild": {
        "file_class": "lock",
        "operation": "update",
        "presence": "present",
        "entry_kind": "file",
        "failure_class": "unparseable-content",
    },
    "lock-unreadable-repair-rebuilt": {
        "file_class": "lock",
        "operation": "repair",
        "presence": "present",
        "entry_kind": "file",
        "failure_class": "permission-denied",
    },
    "seed-open-permission-denied-unreadable": {
        "file_class": "seed",
        "operation": "provision",
        "presence": "present",
        "entry_kind": "file",
        "failure_class": "permission-denied",
    },
    "seed-read-io-error-unreadable": {
        "file_class": "seed",
        "operation": "provision",
        "presence": "present",
        "entry_kind": "file",
        "failure_class": "io-error",
    },
    "seed-unparseable-content-unreadable": {
        "file_class": "seed",
        "operation": "provision",
        "presence": "present",
        "entry_kind": "file",
        "failure_class": "unparseable-content",
    },
    "seed-symlink-where-regular-required-unreadable": {
        "file_class": "seed",
        "operation": "provision",
        "presence": "present",
        "entry_kind": "symlink",
        "failure_class": "symlink-where-regular-required",
    },
    "seed-directory-where-file-expected-unreadable": {
        "file_class": "seed",
        "operation": "provision",
        "presence": "present",
        "entry_kind": "directory",
        "failure_class": "directory-where-file-expected",
    },
    "seed-parent-not-directory-unreadable": {
        "file_class": "seed",
        "operation": "provision",
        "presence": "present",
        "entry_kind": "file",
        "failure_class": "parent-not-directory",
    },
    "seed-absent-not-seeded-provisioned": {
        "file_class": "seed",
        "operation": "provision",
        "presence": "absent",
        "entry_kind": "missing",
        "failure_class": None,
    },
    "seed-unreadable-skipped-as-absent": {
        "file_class": "seed",
        "operation": "provision",
        "presence": "present",
        "entry_kind": "file",
        "failure_class": "permission-denied",
    },
    "passthrough-lstat-permission-denied-unreadable": {
        "file_class": "passthrough",
        "operation": "env-status",
        "presence": "present",
        "entry_kind": "symlink",
        "failure_class": "permission-denied",
    },
    "passthrough-readlink-io-error-unreadable": {
        "file_class": "passthrough",
        "operation": "env-status",
        "presence": "present",
        "entry_kind": "symlink",
        "failure_class": "io-error",
    },
    "passthrough-parent-not-directory-unreadable": {
        "file_class": "passthrough",
        "operation": "env-status",
        "presence": "present",
        "entry_kind": "symlink",
        "failure_class": "parent-not-directory",
    },
    "passthrough-unreadable-resolve-no-fragment": {
        "file_class": "passthrough",
        "operation": "env-resolve",
        "presence": "present",
        "entry_kind": "symlink",
        "failure_class": "permission-denied",
    },
    "passthrough-link-missing-detached": {
        "file_class": "passthrough",
        "operation": "env-status",
        "presence": "absent",
        "entry_kind": "missing",
        "failure_class": None,
    },
    "passthrough-directory-at-entry-detached": {
        "file_class": "passthrough",
        "operation": "env-status",
        "presence": "present",
        "entry_kind": "directory",
        "failure_class": None,
    },
    "passthrough-detached-resolve-stale": {
        "file_class": "passthrough",
        "operation": "env-resolve",
        "presence": "absent",
        "entry_kind": "missing",
        "failure_class": None,
    },
    "passthrough-unreadable-reported-detached": {
        "file_class": "passthrough",
        "operation": "env-status",
        "presence": "present",
        "entry_kind": "symlink",
        "failure_class": "permission-denied",
    },
    "backup-record-unreadable-status-unknown": {
        "file_class": "backup-record",
        "operation": "env-status",
        "presence": "present",
        "entry_kind": "directory",
        "failure_class": "permission-denied",
    },
    "backup-record-unreadable-restore-stops": {
        "file_class": "backup-record",
        "operation": "restore",
        "presence": "present",
        "entry_kind": "directory",
        "failure_class": "io-error",
    },
    "backup-record-absent-status-zero": {
        "file_class": "backup-record",
        "operation": "env-status",
        "presence": "absent",
        "entry_kind": "missing",
        "failure_class": None,
    },
    "backup-record-absent-restore-nothing": {
        "file_class": "backup-record",
        "operation": "restore",
        "presence": "absent",
        "entry_kind": "missing",
        "failure_class": None,
    },
    "backup-record-unreadable-reported-empty": {
        "file_class": "backup-record",
        "operation": "env-status",
        "presence": "present",
        "entry_kind": "directory",
        "failure_class": "permission-denied",
    },
}
READ_FAILURE_CASES = frozenset(READ_FAILURE_SCENARIOS)
# Each negative pinned to the exact non-conforming observation it refuses —
# absence-shaped for the per-class negatives, rebuild-shaped for the lock
# no-rebuild negative: a negative rewritten as an internally consistent
# passing case — or as a different violation — under the same name must be
# refused.
READ_FAILURE_NEGATIVES = {
    "marker-unreadable-reported-stale": {
        "diagnostic": "environment_home_stale",
        "fragment_emitted": False,
        "row_current": False,
        "currency": "known",
    },
    "lock-unreadable-reported-unknown": {
        "diagnostic": "profile_unknown",
        "fragment_emitted": False,
        "row_current": False,
        "currency": "known",
    },
    "seed-unreadable-skipped-as-absent": {
        "diagnostic": None,
        "provisioning_continues": True,
        "currency": "known",
    },
    "passthrough-unreadable-reported-detached": {
        "diagnostic": "environment_passthrough_detached",
        "row_current": False,
        "currency": "known",
        "repair_relinks": True,
    },
    "lock-unreadable-repair-rebuilt": {
        "diagnostic": "environment_store_untrusted",
        "fragment_emitted": False,
        "row_current": False,
        "currency": "unknown",
        "rebuilt": True,
        "written": True,
    },
    "backup-record-unreadable-reported-empty": {
        "diagnostic": None,
        "row_current": True,
        "currency": "known",
    },
}


def _read_failure_expected(
    file_class: str, operation: str, presence: str, entry_kind: str, failure_class: Any
) -> dict[str, Any]:
    """Derive the section 8.4.1 disposition for one scenario's inputs."""
    if failure_class is None:
        if file_class == "marker":
            return {
                "diagnostic": "environment_home_stale",
                "fragment_emitted": False,
                "row_current": False,
                "currency": "known",
            }
        if file_class == "lock":
            return {
                "diagnostic": "profile_unknown",
                "fragment_emitted": False,
                "row_current": False,
                "currency": "known",
            }
        if file_class == "seed":
            return {
                "diagnostic": None,
                "provisioning_continues": True,
                "currency": "known",
            }
        if file_class == "backup-record":
            if operation == "restore":
                return {
                    "diagnostic": None,
                    "currency": "known",
                    "written": False,
                }
            return {
                "diagnostic": None,
                "row_current": True,
                "currency": "known",
            }
        if operation == "env-resolve":
            return {
                "diagnostic": "environment_home_stale",
                "fragment_emitted": False,
                "row_current": False,
                "currency": "known",
            }
        return {
            "diagnostic": "environment_passthrough_detached",
            "row_current": False,
            "currency": "known",
            "repair_relinks": True,
        }
    if file_class == "marker":
        return {
            "diagnostic": "environment_marker_unreadable",
            "fragment_emitted": False,
            "row_current": False,
            "currency": "unknown",
        }
    if file_class == "lock":
        if operation == "repair":
            return {
                "diagnostic": "environment_store_untrusted",
                "fragment_emitted": False,
                "row_current": False,
                "currency": "unknown",
                "rebuilt": False,
                "written": False,
            }
        if operation == "update":
            return {
                "diagnostic": "environment_store_untrusted",
                "row_current": False,
                "currency": "unknown",
                "rebuilt": False,
                "written": False,
            }
        return {
            "diagnostic": "environment_store_untrusted",
            "fragment_emitted": False,
            "row_current": False,
            "currency": "unknown",
        }
    if file_class == "seed":
        return {
            "diagnostic": "environment_seed_unreadable",
            "provisioning_continues": False,
            "currency": "unknown",
        }
    if file_class == "backup-record":
        if operation == "restore":
            return {
                "diagnostic": "environment_backup_record_unreadable",
                "currency": "unknown",
                "written": False,
            }
        return {
            "diagnostic": "environment_backup_record_unreadable",
            "row_current": False,
            "currency": "unknown",
        }
    if operation == "env-resolve":
        return {
            "diagnostic": "environment_passthrough_unreadable",
            "fragment_emitted": False,
            "row_current": False,
            "currency": "unknown",
        }
    return {
        "diagnostic": "environment_passthrough_unreadable",
        "row_current": False,
        "currency": "unknown",
        "repair_relinks": False,
    }


def _validate_read_failure_case(name: str, case: dict[str, Any]) -> None:
    label = f"environments-read-failure case {name}"
    file_class = case.get("file_class")
    if file_class not in READ_FAILURE_FILE_CLASSES:
        raise ValidationFailure(f"{label} names an unknown file class")
    operation = case.get("operation")
    if operation not in READ_FAILURE_OPERATIONS:
        raise ValidationFailure(f"{label} names an unknown operation")
    if file_class == "marker" and operation != "env-resolve":
        raise ValidationFailure(f"{label} marker scenarios resolve")
    if file_class == "lock" and operation not in ("env-resolve", "repair", "update"):
        raise ValidationFailure(f"{label} lock scenarios resolve, repair, or update")
    if file_class == "seed" and operation != "provision":
        raise ValidationFailure(f"{label} seed scenarios provision")
    if file_class == "passthrough" and operation not in ("env-resolve", "env-status"):
        raise ValidationFailure(f"{label} passthrough scenarios resolve or report status")
    if file_class == "backup-record" and operation not in ("env-status", "restore"):
        raise ValidationFailure(f"{label} backup-record scenarios report status or restore")
    presence = case.get("presence")
    if presence not in READ_FAILURE_PRESENCE_VALUES:
        raise ValidationFailure(f"{label} presence is not absent or present")
    entry_kind = case.get("entry_kind")
    if entry_kind not in READ_FAILURE_ENTRY_KINDS:
        raise ValidationFailure(f"{label} names an unknown entry kind")
    failure_class = case.get("failure_class")
    if failure_class is not None and failure_class not in READ_FAILURE_FAILURE_CLASSES:
        raise ValidationFailure(f"{label} names an unknown failure class")
    if presence == "absent":
        if entry_kind != "missing" or failure_class is not None:
            raise ValidationFailure(f"{label} an absent entry carries no kind or failure")
    elif failure_class is None:
        # The one present-but-absence-side scenario: a directory at a
        # passthrough entry path is "no longer a symlink" (section 7.4).
        if not (
            file_class == "passthrough"
            and entry_kind == "directory"
            and operation == "env-status"
        ):
            raise ValidationFailure(f"{label} a present entry with no failure is outside this family")
    else:
        if failure_class not in READ_FAILURE_APPLICABLE[file_class]:
            raise ValidationFailure(f"{label} failure class does not apply to its file class")
        if failure_class == "symlink-where-regular-required" and entry_kind != "symlink":
            raise ValidationFailure(f"{label} symlink failure needs a symlink entry")
        elif failure_class == "directory-where-file-expected" and entry_kind != "directory":
            raise ValidationFailure(f"{label} directory failure needs a directory entry")
        elif failure_class == "parent-not-directory" and entry_kind not in ("file", "symlink"):
            raise ValidationFailure(f"{label} parent failure needs an entry beyond the bad component")
        elif (
            failure_class
            in (
                "permission-denied",
                "io-error",
                "unparseable-content",
                "schema-invalid-content",
            )
            and entry_kind
            != {"passthrough": "symlink", "backup-record": "directory"}.get(
                file_class, "file"
            )
        ):
            raise ValidationFailure(f"{label} content failure needs its file-class entry shape")

    pinned = READ_FAILURE_SCENARIOS.get(name)
    actual = {
        "file_class": file_class,
        "operation": operation,
        "presence": presence,
        "entry_kind": entry_kind,
        "failure_class": failure_class,
    }
    if pinned is None or actual != pinned:
        raise ValidationFailure(f"{label} inputs do not match its pinned scenario")

    expected = case.get("expected")
    if not isinstance(expected, dict):
        raise ValidationFailure(f"{label} expected is not an object")
    if name in READ_FAILURE_NEGATIVES:
        if case.get("conforming") is not False or not case.get("reason"):
            raise ValidationFailure(f"{label} a negative needs conforming=false and a reason")
        refused = READ_FAILURE_NEGATIVES[name]
        if expected != refused:
            raise ValidationFailure(f"{label} observation is not its pinned absence-shaped refusal")
        return
    if case.get("conforming") is False or "reason" in case:
        raise ValidationFailure(f"{label} a positive case must not carry a negative verdict")
    derived = _read_failure_expected(file_class, operation, presence, entry_kind, failure_class)
    if expected != derived:
        raise ValidationFailure(f"{label} observation does not follow the section 8.4.1 disposition")


def validate_environments_read_failure_vectors(vector: Any = None) -> None:
    """The environments section 8.4.1 absence-versus-read-failure vectors.

    Structural validation only: closed sets are exact, each named case is
    pinned to its typed discriminating inputs, each positive observation is
    derived from the section 8.4.1 disposition, and each negative pins the
    exact absence-shaped observation it refuses. This gate never touches the
    filesystem; behavioral conformance is owned by the manager
    implementation task created after this spec lands.
    """
    if vector is None:
        vector = load_json(SUITE / "vectors" / "environments-read-failure.json")
    if (
        vector.get("schema_version") != 1
        or vector.get("protocol_version") != PROTOCOL_VERSION
        or vector.get("capability") != "agent-environments"
        or vector.get("capability_revision") != 1
        or vector.get("story") != "STORY-260916-1ll22r"
    ):
        raise ValidationFailure("environments-read-failure vector has the wrong capability identity")
    if vector.get("file_classes") != list(READ_FAILURE_FILE_CLASSES):
        raise ValidationFailure("environments-read-failure file classes are not the closed five-class set")
    if vector.get("operations") != list(READ_FAILURE_OPERATIONS):
        raise ValidationFailure("environments-read-failure operations are not the closed six-operation set")
    if vector.get("presence_values") != list(READ_FAILURE_PRESENCE_VALUES):
        raise ValidationFailure("environments-read-failure presence values are not the closed two-value set")
    if vector.get("entry_kinds") != list(READ_FAILURE_ENTRY_KINDS):
        raise ValidationFailure("environments-read-failure entry kinds are not the closed four-kind set")
    if vector.get("failure_classes") != list(READ_FAILURE_FAILURE_CLASSES):
        raise ValidationFailure("environments-read-failure failure classes are not the closed seven-class set")
    if vector.get("diagnostics") != list(READ_FAILURE_DIAGNOSTICS):
        raise ValidationFailure("environments-read-failure diagnostics are not the closed eight-code set")
    if vector.get("currencies") != list(READ_FAILURE_CURRENCIES):
        raise ValidationFailure("environments-read-failure currencies are not the closed two-value set")
    if not isinstance(vector.get("rule"), str) or not vector.get("rule"):
        raise ValidationFailure("environments-read-failure rule text is missing")

    cases = named_cases(vector.get("cases"), "environments read-failure")
    if set(cases) != READ_FAILURE_CASES:
        raise ValidationFailure("environments-read-failure case inventory is not exact")
    for name, case in cases.items():
        _validate_read_failure_case(name, case)


UMBRELLA_PROVIDER_DIAGNOSTICS = {
    "subcommand_provider_missing",
    "subcommand_provider_untrusted",
    "subcommand_provider_outside_trust_roots",
    "subcommand_provider_root_unreadable",
}

UMBRELLA_PROVIDER_CASES = {
    "install-dir-provider-missing-then-resolved",
    "install-dir-beats-listed-directory",
    "listed-directory-provider-resolved",
    "listed-order-first-match-wins",
    "s6-planted-path-provider-warns-then-refuses",
    "non-executable-in-trust-root-skipped",
    "manager-published-directory-refused",
    "listed-but-published-directory-still-refused",
    "managed-directory-refused",
    "unreadable-listed-directory-fails",
    "unreadable-install-directory-fails",
    "path-selects-different-provider-while-trusted-exists",
    "trusted-provider-on-path-resolves-silently",
    "provider-missing",
}


def _umbrella_dirname(path: str) -> str:
    """POSIX dirname for a vector absolute path (vectors use POSIX spellings)."""
    if "/" not in path:
        return "."
    head = path.rsplit("/", 1)[0]
    return head if head else "/"


def _umbrella_inside_forbidden(path: str, forbidden: list[str]) -> bool:
    """True when path resides directly inside or below a forbidden directory."""
    for entry in forbidden:
        prefix = entry.rstrip("/") + "/"
        if path.startswith(prefix):
            return True
    return False


def _umbrella_executables(case: dict[str, Any]) -> set[str]:
    """Paths present as executable regular files of the provider name."""
    executable_name = case.get("executable_name")
    found: set[str] = set()
    present = case.get("present")
    if not isinstance(present, list):
        return found
    for item in present:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        if (
            isinstance(path, str)
            and item.get("executable") is True
            and path.rsplit("/", 1)[-1] == executable_name
        ):
            found.add(path)
    return found


def _umbrella_path_search(case: dict[str, Any], executables: set[str]) -> str | None:
    """First executable directly inside the PATH entries, in order, or None."""
    executable_name = case.get("executable_name")
    entries = case.get("path_entries")
    if not isinstance(entries, list):
        return None
    for entry in entries:
        if not isinstance(entry, str):
            continue
        candidate = entry.rstrip("/") + "/" + str(executable_name)
        if candidate in executables:
            return candidate
    return None


def _umbrella_trust_roots(case: dict[str, Any]) -> list[str]:
    """Install directory first, then provider_directories in listed order."""
    roots = [case.get("install_dir")]
    listed = case.get("provider_directories")
    if isinstance(listed, list):
        roots.extend(entry for entry in listed if isinstance(entry, str))
    return [entry for entry in roots if isinstance(entry, str)]


def _umbrella_expected(case: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Derive the required revision_a/revision_b outcomes from the case inputs.

    Implements environments §11: revision A keeps ambient-PATH selection and
    only warns outside the trust roots; revision B searches the trust roots
    only, with a diagnostic-only PATH probe; published/managed refusal
    outranks dispatch; an unreadable root fails instead of resolving or
    reporting absence.
    """
    name = case.get("name", "<unnamed>")
    roots = _umbrella_trust_roots(case)
    unreadable = case.get("unreadable_dirs")
    unreadable_set = set(unreadable) if isinstance(unreadable, list) else set()
    for entry in unreadable_set:
        if entry not in roots:
            raise ValidationFailure(
                f"umbrella provider case {name} marks non-root {entry!r} unreadable"
            )
    first_unreadable = next((entry for entry in roots if entry in unreadable_set), None)
    executables = _umbrella_executables(case)
    forbidden = list(case.get("published_dirs", [])) + list(case.get("managed_dirs", []))
    path_match = _umbrella_path_search(case, executables)

    # Revision A: PATH selects; forbidden refuses; unreadable fails; inside
    # roots resolves silently; outside resolves with the warning; no PATH
    # match is missing even when a trust root holds the provider.
    if path_match is not None and _umbrella_inside_forbidden(path_match, forbidden):
        revision_a: dict[str, Any] = {
            "resolved": None,
            "diagnostic": "subcommand_provider_untrusted",
            "untrusted_path": path_match,
            "trust_roots_consulted": roots,
        }
    elif first_unreadable is not None:
        revision_a = {
            "resolved": None,
            "diagnostic": "subcommand_provider_root_unreadable",
            "unreadable_directory": first_unreadable,
            "trust_roots_consulted": roots,
        }
    elif path_match is None:
        revision_a = {
            "resolved": None,
            "diagnostic": "subcommand_provider_missing",
            "trust_roots_consulted": roots,
        }
    elif _umbrella_dirname(path_match) in roots:
        revision_a = {"resolved": path_match, "diagnostic": None}
    else:
        revision_a = {
            "resolved": path_match,
            "diagnostic": "subcommand_provider_outside_trust_roots",
            "migration_hint_directory": _umbrella_dirname(path_match),
            "trust_roots_consulted": roots,
        }

    # Revision B: trust roots in order, stopping at the first unreadable
    # before any match; a later unreadable past a match is not consulted.
    trusted: str | None = None
    failed: str | None = None
    executable_name = case.get("executable_name")
    for root in roots:
        if root in unreadable_set:
            failed = root
            break
        candidate = root.rstrip("/") + "/" + str(executable_name)
        if candidate in executables:
            trusted = candidate
            break
    if failed is not None:
        revision_b: dict[str, Any] = {
            "resolved": None,
            "diagnostic": "subcommand_provider_root_unreadable",
            "unreadable_directory": failed,
            "trust_roots_consulted": roots,
        }
    elif trusted is not None and _umbrella_inside_forbidden(trusted, forbidden):
        revision_b = {
            "resolved": None,
            "diagnostic": "subcommand_provider_untrusted",
            "untrusted_path": trusted,
            "trust_roots_consulted": roots,
        }
    elif trusted is not None:
        revision_b = {"resolved": trusted, "diagnostic": None}
    elif path_match is not None:
        revision_b = {
            "resolved": None,
            "diagnostic": "subcommand_provider_untrusted",
            "untrusted_path": path_match,
            "trust_roots_consulted": roots,
        }
    else:
        revision_b = {
            "resolved": None,
            "diagnostic": "subcommand_provider_missing",
            "trust_roots_consulted": roots,
        }
    return {"revision_a": revision_a, "revision_b": revision_b}


def validate_umbrella_provider_vectors(root: Path | None = None) -> None:
    """`vectors/umbrella-provider-resolution.json` (environments §11, finding E4).

    The case inventory is exact, every case states both rollout profiles,
    every diagnostic is one of the closed §11.1 set, the revision-A warning
    never appears under revision B, every outcome carries exactly the
    details its diagnostic requires (migration hint, refused path, consulted
    roots, unreadable directory), and every declared outcome equals the
    resolver model derived from the case inputs (precedence, executable
    filtering, published/managed refusal, missing/untrusted/unreadable
    distinction).
    """
    if root is None:
        root = SUITE
    vector = load_json(root / "vectors" / "umbrella-provider-resolution.json")
    if (
        vector.get("schema_version") != 1
        or vector.get("protocol_version") != PROTOCOL_VERSION
        or vector.get("capability") != "agent-environments"
        or vector.get("capability_revision") != 1
    ):
        raise ValidationFailure("umbrella-provider-resolution vector has the wrong capability identity")
    cases = named_cases(vector.get("cases"), "umbrella provider resolution")
    if set(cases) != UMBRELLA_PROVIDER_CASES:
        raise ValidationFailure(
            "umbrella provider case inventory is not exact: "
            f"missing={sorted(UMBRELLA_PROVIDER_CASES - set(cases))}, "
            f"extra={sorted(set(cases) - UMBRELLA_PROVIDER_CASES)}"
        )
    warned = refused = failed_unreadable = 0
    for name, case in cases.items():
        for member in (
            "subcommand", "executable_name", "install_dir", "provider_directories",
            "path_entries", "published_dirs", "managed_dirs", "present",
            "unreadable_dirs", "revision_a", "revision_b",
        ):
            if member not in case:
                raise ValidationFailure(f"umbrella provider case {name} lacks {member}")
        if case.get("executable_name") != f"curator-{case.get('subcommand')}":
            raise ValidationFailure(f"umbrella provider case {name} misnames its executable")
        for member in (
            "provider_directories", "path_entries", "published_dirs",
            "managed_dirs", "present", "unreadable_dirs",
        ):
            if not isinstance(case.get(member), list):
                raise ValidationFailure(f"umbrella provider case {name} has non-list {member}")
        for profile in ("revision_a", "revision_b"):
            outcome = case.get(profile)
            if not isinstance(outcome, dict):
                raise ValidationFailure(f"umbrella provider case {name} lacks {profile}")
            diagnostic = outcome.get("diagnostic")
            resolved = outcome.get("resolved")
            if diagnostic is not None and diagnostic not in UMBRELLA_PROVIDER_DIAGNOSTICS:
                raise ValidationFailure(
                    f"umbrella provider case {name} {profile} uses unknown diagnostic {diagnostic!r}"
                )
            if diagnostic is None and resolved is None:
                raise ValidationFailure(
                    f"umbrella provider case {name} {profile} neither resolves nor diagnoses"
                )
            if diagnostic is not None and diagnostic != "subcommand_provider_outside_trust_roots" and resolved is not None:
                raise ValidationFailure(
                    f"umbrella provider case {name} {profile} both resolves and refuses"
                )
            hint = outcome.get("migration_hint_directory")
            untrusted_path = outcome.get("untrusted_path")
            unreadable_directory = outcome.get("unreadable_directory")
            roots_consulted = outcome.get("trust_roots_consulted")
            if diagnostic == "subcommand_provider_outside_trust_roots":
                if profile != "revision_a":
                    raise ValidationFailure(
                        f"umbrella provider case {name} warns outside revision A"
                    )
                if not isinstance(hint, str) or not hint:
                    raise ValidationFailure(
                        f"umbrella provider case {name} warning names no migration-hint directory"
                    )
                if not isinstance(roots_consulted, list) or not roots_consulted:
                    raise ValidationFailure(
                        f"umbrella provider case {name} warning names no trust-roots-consulted list"
                    )
                if untrusted_path is not None or unreadable_directory is not None:
                    raise ValidationFailure(
                        f"umbrella provider case {name} warning carries a refusal detail"
                    )
                warned += 1
            elif diagnostic == "subcommand_provider_untrusted":
                if not isinstance(untrusted_path, str) or not untrusted_path:
                    raise ValidationFailure(
                        f"umbrella provider case {name} {profile} names no untrusted_path"
                    )
                if not isinstance(roots_consulted, list) or not roots_consulted:
                    raise ValidationFailure(
                        f"umbrella provider case {name} {profile} names no trust-roots-consulted list"
                    )
                if hint is not None or unreadable_directory is not None:
                    raise ValidationFailure(
                        f"umbrella provider case {name} {profile} refusal carries a foreign detail"
                    )
                refused += 1
            elif diagnostic == "subcommand_provider_missing":
                if not isinstance(roots_consulted, list) or not roots_consulted:
                    raise ValidationFailure(
                        f"umbrella provider case {name} {profile} names no trust-roots-consulted list"
                    )
                if hint is not None or untrusted_path is not None or unreadable_directory is not None:
                    raise ValidationFailure(
                        f"umbrella provider case {name} {profile} missing outcome carries a refusal detail"
                    )
                refused += 1
            elif diagnostic == "subcommand_provider_root_unreadable":
                if not isinstance(unreadable_directory, str) or not unreadable_directory:
                    raise ValidationFailure(
                        f"umbrella provider case {name} {profile} names no unreadable_directory"
                    )
                if not isinstance(roots_consulted, list) or not roots_consulted:
                    raise ValidationFailure(
                        f"umbrella provider case {name} {profile} names no trust-roots-consulted list"
                    )
                if hint is not None or untrusted_path is not None:
                    raise ValidationFailure(
                        f"umbrella provider case {name} {profile} unreadable failure carries a foreign detail"
                    )
                failed_unreadable += 1
            else:
                if hint is not None or untrusted_path is not None or unreadable_directory is not None or roots_consulted is not None:
                    raise ValidationFailure(
                        f"umbrella provider case {name} {profile} success carries a diagnostic detail"
                    )
            if hint is not None and diagnostic != "subcommand_provider_outside_trust_roots":
                raise ValidationFailure(
                    f"umbrella provider case {name} {profile} carries a hint without the warning"
                )
        expected = _umbrella_expected(case)
        for profile in ("revision_a", "revision_b"):
            outcome = case.get(profile)
            want = expected[profile]
            if outcome.get("resolved") != want.get("resolved"):
                raise ValidationFailure(
                    f"umbrella provider case {name} {profile} resolves "
                    f"{outcome.get('resolved')!r} but the §11 model expects {want.get('resolved')!r}"
                )
            if outcome.get("diagnostic") != want.get("diagnostic"):
                raise ValidationFailure(
                    f"umbrella provider case {name} {profile} diagnoses "
                    f"{outcome.get('diagnostic')!r} but the §11 model expects {want.get('diagnostic')!r}"
                )
            for detail in (
                "migration_hint_directory", "untrusted_path",
                "unreadable_directory", "trust_roots_consulted",
            ):
                if want.get(detail) is not None and outcome.get(detail) != want.get(detail):
                    raise ValidationFailure(
                        f"umbrella provider case {name} {profile} {detail} "
                        f"{outcome.get(detail)!r} mismatches the §11 model {want.get(detail)!r}"
                    )
    if not warned:
        raise ValidationFailure("umbrella provider vectors warn under no revision-A case")
    if not refused:
        raise ValidationFailure("umbrella provider vectors refuse under no case")
    if not failed_unreadable:
        raise ValidationFailure("umbrella provider vectors fail unreadable under no case")


# The manager-profile section 7.1 hardened-defaults vocabulary (findings
# S1+S3): rollout revisions with their posture defaults, the four new
# diagnostic codes plus the one pre-existing code the profile escalates,
# the three refusals that are the profile's meaning, the closed provenance
# set, and the posture-row gate orders of manager section 10 and
# environments section 12.
SECURITY_POSTURE_REVISION_DEFAULTS = {"A": "permissive", "B": "hardened"}
SECURITY_POSTURE_DIAGNOSTICS = (
    "source_allowlist_empty",
    "passable_env_names_unbounded_refused",
    "security_posture_permissive",
    "registry_unreachable_during_install",
)
SECURITY_POSTURE_REFERENCED_DIAGNOSTICS = ("mcp_package_allowlist_empty",)
SECURITY_POSTURE_REFUSALS = (
    "source_allowlist_empty",
    "mcp_package_allowlist_empty",
    "passable_env_names_unbounded_refused",
)
SECURITY_POSTURE_PROVENANCE = ("profile", "explicit", "lock", "shipped")
# One shared closed gate vocabulary (manager section 10, environments
# section 12): when the environments capability exists both `curator
# status` and `env status` carry the header row plus these thirteen rows in
# this order. A schema-1 manager has no environments capability and its
# `curator status` carries only the header row plus the four-gate manager
# subset; `env status` then has no posture section.
SECURITY_POSTURE_STATUS_GATES = (
    "hook-trust",
    "registry-policy",
    "audit-mode",
    "source-allowlist",
    "env-passthrough",
    "transitive-system-modules",
    "provider-trust-roots",
    "source-signers",
    "update-confirmation",
    "codex-seed",
    "store-boundary",
    "write-discipline",
    "mcp-package-allowlist",
)
SECURITY_POSTURE_SCHEMA1_GATES = (
    "hook-trust",
    "registry-policy",
    "audit-mode",
    "source-allowlist",
)
SECURITY_POSTURE_DEFAULTS = {
    "permissive": {
        "audit_mode": "advisory",
        "audit_registry_policy": "advisory",
        "transitive_system_modules": "drop",
        "require_source_signers": False,
    },
    "hardened": {
        "audit_mode": "strict",
        "audit_registry_policy": "strict",
        "transitive_system_modules": "error",
        "require_source_signers": True,
    },
}
SECURITY_POSTURE_DIAGNOSTIC_ORDER = (
    "security_posture_permissive",
    "source_allowlist_empty",
    "mcp_package_allowlist_empty",
    "passable_env_names_unbounded_refused",
    "registry_unreachable_during_install",
)
SECURITY_POSTURE_CASES = {
    "revision-A-default-permissive-status",
    "revision-B-default-hardened-flip-install",
    "explicit-hardened-effective-defaults",
    "explicit-knob-beats-profile-default",
    "locked-value-beats-explicit",
    "locked-posture-beats-explicit-permissive",
    "refusal-source-allowlist-empty-explicit",
    "refusal-mcp-allowlist-empty-with-declarations",
    "hardened-empty-mcp-allowlist-without-declarations-warns",
    "refusal-passable-env-null",
    "revision-A-permissive-warning-once-install",
    "unreachable-registry-permissive-warns",
    "unreachable-registry-hardened-refuses",
    "schema1-machine-is-permissive",
    "hardened-contradiction-status-check-non-current",
    "hardened-absent-passthrough-follows-s4-warn",
    "posture-rows-flipped-revisions",
}
# Each required scenario pinned to its schema version, its effective
# posture, its precedence conditions, and the inputs distinguishing its
# branch (producer rule 7): a named case rewritten as an internally
# consistent passing case under the same name — a changed posture, a
# changed precedence source, or another case's whole body — must be
# refused, not merely inventoried. Pins are dotted input paths to exact
# values; "<absent>" requires the path to be missing, {"contains": x}
# requires list membership, {"nonempty": True} requires a non-empty list,
# and {"present": None} requires a present null (distinct from absent).
# The "effective.profile" and "effective.profile_source" pins name the
# posture the inputs must resolve to under the section 7.1 merge rules,
# so a rewrite that keeps the inputs plausible but flips the effective
# posture (or its precedence source) still fails under its old name.
SECURITY_POSTURE_SCENARIOS = {
    "revision-A-default-permissive-status": {
        "rollout_revision": "A",
        "machine.schema_version": 2,
        "machine.security_posture": "<absent>",
        "machine.audit": "<absent>",
        "machine.allowed_sources": "<absent>",
        "machine.environments": "<absent>",
        "system.locked": "<absent>",
        "system.audit": "<absent>",
        "system.allowed_sources": "<absent>",
        "system.security_posture": "<absent>",
        "system.environments": "<absent>",
        "shipped_revisions.hook_trust": "A-warning",
        "shipped_revisions.env_passthrough": "s4-enforce",
        "shipped_revisions.provider_trust_roots": "revision-A",
        "shipped_revisions.update_confirmation": "A-warning",
        "shipped_revisions.codex_seed": "A",
        "operation.kind": "status",
        "operation.mcp_declarations_present": False,
        "operation.unreachable_trusted_registries": [],
        "operation.artifacts_without_evidence": [],
        "effective.profile": "permissive",
        "effective.profile_source": "profile",
    },
    "revision-B-default-hardened-flip-install": {
        "rollout_revision": "B",
        "machine.schema_version": 2,
        "machine.security_posture": "<absent>",
        "machine.audit": "<absent>",
        "machine.allowed_sources": {"nonempty": True},
        "machine.environments.mcp_package_allowlist": {"nonempty": True},
        "machine.environments.passable_env_names": "<absent>",
        "machine.environments.transitive_system_modules": "<absent>",
        "machine.environments.require_source_signers": "<absent>",
        "system.locked": "<absent>",
        "system.audit": "<absent>",
        "system.allowed_sources": "<absent>",
        "system.security_posture": "<absent>",
        "system.environments": "<absent>",
        "shipped_revisions.hook_trust": "A-warning",
        "shipped_revisions.env_passthrough": "s4-enforce",
        "shipped_revisions.provider_trust_roots": "revision-A",
        "shipped_revisions.update_confirmation": "A-warning",
        "shipped_revisions.codex_seed": "A",
        "operation.kind": "install",
        "operation.mcp_declarations_present": False,
        "operation.unreachable_trusted_registries": [],
        "operation.artifacts_without_evidence": [],
        "effective.profile": "hardened",
        "effective.profile_source": "profile",
    },
    "explicit-hardened-effective-defaults": {
        "rollout_revision": "A",
        "machine.schema_version": 2,
        "machine.security_posture": "hardened",
        "machine.audit": "<absent>",
        "machine.allowed_sources": "<absent>",
        "machine.environments": "<absent>",
        "system.locked": "<absent>",
        "system.audit": "<absent>",
        "system.allowed_sources": "<absent>",
        "system.security_posture": "<absent>",
        "system.environments": "<absent>",
        "shipped_revisions.hook_trust": "A-warning",
        "shipped_revisions.env_passthrough": "s4-enforce",
        "shipped_revisions.provider_trust_roots": "revision-A",
        "shipped_revisions.update_confirmation": "A-warning",
        "shipped_revisions.codex_seed": "A",
        "operation.kind": "status",
        "operation.mcp_declarations_present": False,
        "operation.unreachable_trusted_registries": [],
        "operation.artifacts_without_evidence": [],
        "effective.profile": "hardened",
        "effective.profile_source": "explicit",
    },
    "explicit-knob-beats-profile-default": {
        "rollout_revision": "A",
        "machine.schema_version": 2,
        "machine.security_posture": "hardened",
        "machine.audit.mode": "advisory",
        "machine.audit.registry_policy": "<absent>",
        "machine.allowed_sources": {"nonempty": True},
        "machine.environments.mcp_package_allowlist": {"nonempty": True},
        "machine.environments.passable_env_names": "<absent>",
        "machine.environments.transitive_system_modules": "<absent>",
        "machine.environments.require_source_signers": "<absent>",
        "system.locked": "<absent>",
        "system.audit": "<absent>",
        "system.allowed_sources": "<absent>",
        "system.security_posture": "<absent>",
        "system.environments": "<absent>",
        "shipped_revisions.hook_trust": "A-warning",
        "shipped_revisions.env_passthrough": "s4-enforce",
        "shipped_revisions.provider_trust_roots": "revision-A",
        "shipped_revisions.update_confirmation": "A-warning",
        "shipped_revisions.codex_seed": "A",
        "operation.kind": "install",
        "operation.mcp_declarations_present": False,
        "operation.unreachable_trusted_registries": [],
        "operation.artifacts_without_evidence": [],
        "effective.profile": "hardened",
        "effective.profile_source": "explicit",
    },
    "locked-value-beats-explicit": {
        "rollout_revision": "A",
        "machine.schema_version": 2,
        "machine.security_posture": "<absent>",
        "machine.audit.mode": "advisory",
        "machine.audit.registry_policy": "advisory",
        "machine.allowed_sources": "<absent>",
        "machine.environments": "<absent>",
        "system.locked": ["audit"],
        "system.audit.mode": "strict",
        "system.audit.registry_policy": "strict",
        "system.allowed_sources": "<absent>",
        "system.security_posture": "<absent>",
        "system.environments": "<absent>",
        "shipped_revisions.hook_trust": "A-warning",
        "shipped_revisions.env_passthrough": "s4-enforce",
        "shipped_revisions.provider_trust_roots": "revision-A",
        "shipped_revisions.update_confirmation": "A-warning",
        "shipped_revisions.codex_seed": "A",
        "operation.kind": "status",
        "operation.mcp_declarations_present": False,
        "operation.unreachable_trusted_registries": [],
        "operation.artifacts_without_evidence": [],
        "effective.profile": "permissive",
        "effective.profile_source": "profile",
    },
    "locked-posture-beats-explicit-permissive": {
        "rollout_revision": "A",
        "machine.schema_version": 2,
        "machine.security_posture": "permissive",
        "machine.audit": "<absent>",
        "machine.allowed_sources": "<absent>",
        "machine.environments": "<absent>",
        "system.locked": ["security_posture"],
        "system.security_posture": "hardened",
        "system.audit": "<absent>",
        "system.allowed_sources": "<absent>",
        "system.environments": "<absent>",
        "shipped_revisions.hook_trust": "A-warning",
        "shipped_revisions.env_passthrough": "s4-enforce",
        "shipped_revisions.provider_trust_roots": "revision-A",
        "shipped_revisions.update_confirmation": "A-warning",
        "shipped_revisions.codex_seed": "A",
        "operation.kind": "status",
        "operation.mcp_declarations_present": False,
        "operation.unreachable_trusted_registries": [],
        "operation.artifacts_without_evidence": [],
        "effective.profile": "hardened",
        "effective.profile_source": "lock",
    },
    "refusal-source-allowlist-empty-explicit": {
        "rollout_revision": "A",
        "machine.schema_version": 2,
        "machine.security_posture": "hardened",
        "machine.audit": "<absent>",
        "machine.allowed_sources": [],
        "machine.environments": "<absent>",
        "system.locked": "<absent>",
        "system.audit": "<absent>",
        "system.allowed_sources": "<absent>",
        "system.security_posture": "<absent>",
        "system.environments": "<absent>",
        "shipped_revisions.hook_trust": "A-warning",
        "shipped_revisions.env_passthrough": "s4-enforce",
        "shipped_revisions.provider_trust_roots": "revision-A",
        "shipped_revisions.update_confirmation": "A-warning",
        "shipped_revisions.codex_seed": "A",
        "operation.kind": "install",
        "operation.mcp_declarations_present": False,
        "operation.unreachable_trusted_registries": [],
        "operation.artifacts_without_evidence": [],
        "effective.profile": "hardened",
        "effective.profile_source": "explicit",
    },
    "refusal-mcp-allowlist-empty-with-declarations": {
        "rollout_revision": "B",
        "machine.schema_version": 2,
        "machine.security_posture": "<absent>",
        "machine.audit": "<absent>",
        "machine.allowed_sources": {"nonempty": True},
        "machine.environments": "<absent>",
        "system.locked": "<absent>",
        "system.audit": "<absent>",
        "system.allowed_sources": "<absent>",
        "system.security_posture": "<absent>",
        "system.environments": "<absent>",
        "shipped_revisions.hook_trust": "A-warning",
        "shipped_revisions.env_passthrough": "s4-enforce",
        "shipped_revisions.provider_trust_roots": "revision-A",
        "shipped_revisions.update_confirmation": "A-warning",
        "shipped_revisions.codex_seed": "A",
        "operation.kind": "profile-install",
        "operation.mcp_declarations_present": True,
        "operation.unreachable_trusted_registries": [],
        "operation.artifacts_without_evidence": [],
        "effective.profile": "hardened",
        "effective.profile_source": "profile",
    },
    "hardened-empty-mcp-allowlist-without-declarations-warns": {
        "rollout_revision": "B",
        "machine.schema_version": 2,
        "machine.security_posture": "hardened",
        "machine.audit": "<absent>",
        "machine.allowed_sources": {"nonempty": True},
        "machine.environments": "<absent>",
        "system.locked": "<absent>",
        "system.audit": "<absent>",
        "system.allowed_sources": "<absent>",
        "system.security_posture": "<absent>",
        "system.environments": "<absent>",
        "shipped_revisions.hook_trust": "A-warning",
        "shipped_revisions.env_passthrough": "s4-enforce",
        "shipped_revisions.provider_trust_roots": "revision-A",
        "shipped_revisions.update_confirmation": "A-warning",
        "shipped_revisions.codex_seed": "A",
        "operation.kind": "profile-install",
        "operation.mcp_declarations_present": False,
        "operation.unreachable_trusted_registries": [],
        "operation.artifacts_without_evidence": [],
        "effective.profile": "hardened",
        "effective.profile_source": "explicit",
    },
    "refusal-passable-env-null": {
        "rollout_revision": "A",
        "machine.schema_version": 2,
        "machine.security_posture": "hardened",
        "machine.audit": "<absent>",
        "machine.allowed_sources": {"nonempty": True},
        "machine.environments.mcp_package_allowlist": {"nonempty": True},
        "machine.environments.passable_env_names": {"present": None},
        "machine.environments.transitive_system_modules": "<absent>",
        "machine.environments.require_source_signers": "<absent>",
        "system.locked": "<absent>",
        "system.audit": "<absent>",
        "system.allowed_sources": "<absent>",
        "system.security_posture": "<absent>",
        "system.environments": "<absent>",
        "shipped_revisions.hook_trust": "A-warning",
        "shipped_revisions.env_passthrough": "s4-enforce",
        "shipped_revisions.provider_trust_roots": "revision-A",
        "shipped_revisions.update_confirmation": "A-warning",
        "shipped_revisions.codex_seed": "A",
        "operation.kind": "profile-install",
        "operation.mcp_declarations_present": True,
        "operation.unreachable_trusted_registries": [],
        "operation.artifacts_without_evidence": [],
        "effective.profile": "hardened",
        "effective.profile_source": "explicit",
    },
    "revision-A-permissive-warning-once-install": {
        "rollout_revision": "A",
        "machine.schema_version": 2,
        "machine.security_posture": "<absent>",
        "machine.audit": "<absent>",
        "machine.allowed_sources": "<absent>",
        "machine.environments": "<absent>",
        "system.locked": "<absent>",
        "system.audit": "<absent>",
        "system.allowed_sources": "<absent>",
        "system.security_posture": "<absent>",
        "system.environments": "<absent>",
        "shipped_revisions.hook_trust": "A-warning",
        "shipped_revisions.env_passthrough": "s4-enforce",
        "shipped_revisions.provider_trust_roots": "revision-A",
        "shipped_revisions.update_confirmation": "A-warning",
        "shipped_revisions.codex_seed": "A",
        "operation.kind": "install",
        "operation.mcp_declarations_present": False,
        "operation.unreachable_trusted_registries": [],
        "operation.artifacts_without_evidence": [],
        "effective.profile": "permissive",
        "effective.profile_source": "profile",
    },
    "unreachable-registry-permissive-warns": {
        "rollout_revision": "A",
        "machine.schema_version": 2,
        "machine.security_posture": "<absent>",
        "machine.audit": "<absent>",
        "machine.allowed_sources": {"nonempty": True},
        "machine.environments": "<absent>",
        "system.locked": "<absent>",
        "system.audit": "<absent>",
        "system.allowed_sources": "<absent>",
        "system.security_posture": "<absent>",
        "system.environments": "<absent>",
        "shipped_revisions.hook_trust": "A-warning",
        "shipped_revisions.env_passthrough": "s4-enforce",
        "shipped_revisions.provider_trust_roots": "revision-A",
        "shipped_revisions.update_confirmation": "A-warning",
        "shipped_revisions.codex_seed": "A",
        "operation.kind": "install",
        "operation.mcp_declarations_present": False,
        "operation.unreachable_trusted_registries": {"nonempty": True},
        "operation.artifacts_without_evidence": {"nonempty": True},
        "effective.profile": "permissive",
        "effective.profile_source": "profile",
    },
    "unreachable-registry-hardened-refuses": {
        "rollout_revision": "A",
        "machine.schema_version": 2,
        "machine.security_posture": "hardened",
        "machine.audit": "<absent>",
        "machine.allowed_sources": {"nonempty": True},
        "machine.environments": "<absent>",
        "system.locked": "<absent>",
        "system.audit": "<absent>",
        "system.allowed_sources": "<absent>",
        "system.security_posture": "<absent>",
        "system.environments": "<absent>",
        "shipped_revisions.hook_trust": "A-warning",
        "shipped_revisions.env_passthrough": "s4-enforce",
        "shipped_revisions.provider_trust_roots": "revision-A",
        "shipped_revisions.update_confirmation": "A-warning",
        "shipped_revisions.codex_seed": "A",
        "operation.kind": "install",
        "operation.mcp_declarations_present": False,
        "operation.unreachable_trusted_registries": {"nonempty": True},
        "operation.artifacts_without_evidence": {"nonempty": True},
        "effective.profile": "hardened",
        "effective.profile_source": "explicit",
    },
    "schema1-machine-is-permissive": {
        "rollout_revision": "B",
        "machine.schema_version": 1,
        "machine.security_posture": "<absent>",
        "machine.audit.mode": "advisory",
        "machine.audit.registry_policy": "<absent>",
        "machine.allowed_sources": "<absent>",
        "machine.environments": "<absent>",
        "system.locked": "<absent>",
        "system.audit": "<absent>",
        "system.allowed_sources": "<absent>",
        "system.security_posture": "<absent>",
        "system.environments": "<absent>",
        "shipped_revisions.hook_trust": "A-warning",
        "shipped_revisions.env_passthrough": "s4-enforce",
        "shipped_revisions.provider_trust_roots": "revision-A",
        "shipped_revisions.update_confirmation": "A-warning",
        "shipped_revisions.codex_seed": "A",
        "operation.kind": "install",
        "operation.mcp_declarations_present": False,
        "operation.unreachable_trusted_registries": [],
        "operation.artifacts_without_evidence": [],
        "effective.profile": "permissive",
        "effective.profile_source": "profile",
    },
    "hardened-contradiction-status-check-non-current": {
        "rollout_revision": "B",
        "machine.schema_version": 2,
        "machine.security_posture": "<absent>",
        "machine.audit": "<absent>",
        "machine.allowed_sources": "<absent>",
        "machine.environments": "<absent>",
        "system.locked": "<absent>",
        "system.audit": "<absent>",
        "system.allowed_sources": "<absent>",
        "system.security_posture": "<absent>",
        "system.environments": "<absent>",
        "shipped_revisions.hook_trust": "A-warning",
        "shipped_revisions.env_passthrough": "s4-enforce",
        "shipped_revisions.provider_trust_roots": "revision-A",
        "shipped_revisions.update_confirmation": "A-warning",
        "shipped_revisions.codex_seed": "A",
        "operation.kind": "status-check",
        "operation.mcp_declarations_present": True,
        "operation.unreachable_trusted_registries": [],
        "operation.artifacts_without_evidence": [],
        "effective.profile": "hardened",
        "effective.profile_source": "profile",
    },
    "hardened-absent-passthrough-follows-s4-warn": {
        "rollout_revision": "A",
        "machine.schema_version": 2,
        "machine.security_posture": "hardened",
        "machine.audit": "<absent>",
        "machine.allowed_sources": {"nonempty": True},
        "machine.environments.mcp_package_allowlist": {"nonempty": True},
        "machine.environments.passable_env_names": "<absent>",
        "machine.environments.transitive_system_modules": "<absent>",
        "machine.environments.require_source_signers": "<absent>",
        "system.locked": "<absent>",
        "system.audit": "<absent>",
        "system.allowed_sources": "<absent>",
        "system.security_posture": "<absent>",
        "system.environments": "<absent>",
        "shipped_revisions.hook_trust": "A-warning",
        "shipped_revisions.env_passthrough": "s4-warn",
        "shipped_revisions.provider_trust_roots": "revision-A",
        "shipped_revisions.update_confirmation": "A-warning",
        "shipped_revisions.codex_seed": "A",
        "operation.kind": "profile-install",
        "operation.mcp_declarations_present": True,
        "operation.unreachable_trusted_registries": [],
        "operation.artifacts_without_evidence": [],
        "effective.profile": "hardened",
        "effective.profile_source": "explicit",
    },
    "posture-rows-flipped-revisions": {
        "rollout_revision": "B",
        "machine.schema_version": 2,
        "machine.security_posture": "hardened",
        "machine.audit.mode": "strict",
        "machine.audit.registry_policy": "<absent>",
        "machine.allowed_sources": {"nonempty": True},
        "machine.environments.mcp_package_allowlist": {"nonempty": True},
        "machine.environments.passable_env_names": "<absent>",
        "machine.environments.transitive_system_modules": "error",
        "machine.environments.require_source_signers": True,
        "system.locked": "<absent>",
        "system.audit": "<absent>",
        "system.allowed_sources": "<absent>",
        "system.security_posture": "<absent>",
        "system.environments": "<absent>",
        "shipped_revisions.hook_trust": "B-enforcing",
        "shipped_revisions.env_passthrough": "s4-enforce",
        "shipped_revisions.provider_trust_roots": "revision-B",
        "shipped_revisions.update_confirmation": "B-flip",
        "shipped_revisions.codex_seed": "B",
        "operation.kind": "status",
        "operation.mcp_declarations_present": True,
        "operation.unreachable_trusted_registries": [],
        "operation.artifacts_without_evidence": [],
        "effective.profile": "hardened",
        "effective.profile_source": "explicit",
    },
}


def _posture_lookup(case: Any, path: str) -> tuple[bool, Any]:
    node = case
    for segment in path.split("."):
        if not isinstance(node, dict) or segment not in node:
            return False, None
        node = node[segment]
    return True, node


def _posture_check_scenario(name: str, case: Any, profile: str = "", profile_source: str = "") -> None:
    pins = SECURITY_POSTURE_SCENARIOS.get(name)
    if pins is None:
        raise ValidationFailure(f"security-posture case {name} has no scenario pin")
    derived = {"effective.profile": profile, "effective.profile_source": profile_source}
    for path, want in pins.items():
        if path in derived:
            if derived[path] != want:
                raise ValidationFailure(
                    f"security-posture case {name} must resolve {path} == {want!r}"
                )
            continue
        present, value = _posture_lookup(case, path)
        if want == "<absent>":
            if present:
                raise ValidationFailure(f"security-posture case {name} must leave {path} absent")
            continue
        if isinstance(want, dict) and "contains" in want:
            if not present or not isinstance(value, list) or want["contains"] not in value:
                raise ValidationFailure(f"security-posture case {name} must carry {path} containing {want['contains']!r}")
            continue
        if isinstance(want, dict) and want.get("nonempty") is True:
            if not present or not isinstance(value, list) or not value:
                raise ValidationFailure(f"security-posture case {name} must carry a non-empty {path}")
            continue
        if isinstance(want, dict) and "present" in want:
            if not present or value != want["present"]:
                raise ValidationFailure(f"security-posture case {name} must carry {path} present as {want['present']!r}")
            continue
        if not present or value != want:
            raise ValidationFailure(f"security-posture case {name} must carry {path} == {want!r}")


def _posture_resolve(name: str, case: Any) -> tuple[str, str, dict[str, Any], dict[str, str], bool]:
    """Resolve the effective profile, values, and provenance from the inputs.

    Returns (profile, profile_source, effective, sources,
    passable_env_null_explicit) under the manager section 1 and 7.1 merge
    rules: lock, then explicit machine value, then the profile default. A
    schema-1 machine has no posture knob and runs permissive.
    """
    label = f"security-posture case {name}"
    revision = case.get("rollout_revision")
    if revision not in SECURITY_POSTURE_REVISION_DEFAULTS:
        raise ValidationFailure(f"{label} names an unknown rollout revision")
    machine = case.get("machine")
    if not isinstance(machine, dict) or machine.get("schema_version") not in (1, 2):
        raise ValidationFailure(f"{label} machine names no known schema_version")
    schema2 = machine.get("schema_version") == 2
    if not schema2 and "security_posture" in machine:
        raise ValidationFailure(f"{label} schema-1 machine carries a posture knob")
    if "security_posture" in machine and machine["security_posture"] not in ("permissive", "hardened"):
        raise ValidationFailure(f"{label} machine posture is not a closed value")
    system = case.get("system")
    if not isinstance(system, dict):
        raise ValidationFailure(f"{label} system is not an object")
    locked = system.get("locked", [])
    if not isinstance(locked, list) or any(not isinstance(key, str) for key in locked):
        raise ValidationFailure(f"{label} system locked is not a string list")
    known_locks = {
        "audit", "allowed_sources", "security_posture",
        "environments.mcp_package_allowlist", "environments.passable_env_names",
        "environments.transitive_system_modules", "environments.require_source_signers",
    }
    for key in locked:
        if key not in known_locks:
            raise ValidationFailure(f"{label} system locks an unknown key {key}")
    if "security_posture" in system and system["security_posture"] != "hardened":
        raise ValidationFailure(f"{label} system posture is not the hardened direction")
    shipped = case.get("shipped_revisions")
    if not isinstance(shipped, dict) or set(shipped) != {
        "hook_trust", "env_passthrough", "provider_trust_roots", "update_confirmation",
        "codex_seed",
    }:
        raise ValidationFailure(f"{label} shipped revisions are not the closed five-gate set")
    if shipped["hook_trust"] not in ("A-warning", "B-enforcing"):
        raise ValidationFailure(f"{label} hook-trust revision is not closed")
    if shipped["env_passthrough"] not in ("s4-warn", "s4-enforce"):
        raise ValidationFailure(f"{label} passthrough profile is not closed")
    if shipped["provider_trust_roots"] not in ("revision-A", "revision-B"):
        raise ValidationFailure(f"{label} provider-trust-roots revision is not closed")
    if shipped["update_confirmation"] not in ("A-warning", "B-flip"):
        raise ValidationFailure(f"{label} update-confirmation revision is not closed")
    if shipped["codex_seed"] not in ("A", "B"):
        raise ValidationFailure(f"{label} codex-seed revision is not closed")

    if not schema2:
        profile, profile_source = "permissive", "profile"
    elif "security_posture" in locked:
        if "security_posture" not in system:
            raise ValidationFailure(f"{label} locks security_posture without a system value")
        profile, profile_source = system["security_posture"], "lock"
    elif "security_posture" in machine:
        profile, profile_source = machine["security_posture"], "explicit"
    else:
        profile = SECURITY_POSTURE_REVISION_DEFAULTS[revision]
        profile_source = "profile"

    def resolve(lock_key: str, machine_value: Any, machine_present: bool,
                system_value: Any, system_present: bool, default: Any) -> tuple[Any, str]:
        if lock_key in locked:
            if not system_present:
                raise ValidationFailure(f"{label} locks {lock_key} without a system value")
            return system_value, "lock"
        if machine_present:
            return machine_value, "explicit"
        return default, "profile"

    machine_audit = machine.get("audit", {})
    system_audit = system.get("audit", {})
    if not isinstance(machine_audit, dict) or not isinstance(system_audit, dict):
        raise ValidationFailure(f"{label} audit member is not an object")
    defaults = SECURITY_POSTURE_DEFAULTS[profile]
    effective: dict[str, Any] = {}
    sources: dict[str, str] = {}
    effective["audit_mode"], sources["audit_mode"] = resolve(
        "audit", machine_audit.get("mode"), "mode" in machine_audit,
        system_audit.get("mode"), "mode" in system_audit, defaults["audit_mode"])
    effective["audit_registry_policy"], sources["audit_registry_policy"] = resolve(
        "audit", machine_audit.get("registry_policy"), "registry_policy" in machine_audit,
        system_audit.get("registry_policy"), "registry_policy" in system_audit,
        defaults["audit_registry_policy"])
    effective["allowed_sources"], sources["allowed_sources"] = resolve(
        "allowed_sources", machine.get("allowed_sources"), "allowed_sources" in machine,
        system.get("allowed_sources"), "allowed_sources" in system, [])
    if not isinstance(effective["allowed_sources"], list):
        raise ValidationFailure(f"{label} effective allowed_sources is not a list")
    null_explicit = False
    if schema2:
        machine_env = machine.get("environments", {})
        system_env = system.get("environments", {})
        if not isinstance(machine_env, dict) or not isinstance(system_env, dict):
            raise ValidationFailure(f"{label} environments member is not an object")
        effective["mcp_package_allowlist"], sources["mcp_package_allowlist"] = resolve(
            "environments.mcp_package_allowlist",
            machine_env.get("mcp_package_allowlist"), "mcp_package_allowlist" in machine_env,
            system_env.get("mcp_package_allowlist"), "mcp_package_allowlist" in system_env, [])
        if not isinstance(effective["mcp_package_allowlist"], list):
            raise ValidationFailure(f"{label} effective mcp_package_allowlist is not a list")
        pass_default = [] if shipped["env_passthrough"] == "s4-enforce" else None
        effective["passable_env_names"], sources["passable_env_names"] = resolve(
            "environments.passable_env_names",
            machine_env.get("passable_env_names"), "passable_env_names" in machine_env,
            system_env.get("passable_env_names"), "passable_env_names" in system_env,
            pass_default)
        if effective["passable_env_names"] is not None and not isinstance(effective["passable_env_names"], list):
            raise ValidationFailure(f"{label} effective passable_env_names is not a list or null")
        null_explicit = (
            effective["passable_env_names"] is None
            and sources["passable_env_names"] in ("explicit", "lock")
        )
        effective["transitive_system_modules"], sources["transitive_system_modules"] = resolve(
            "environments.transitive_system_modules",
            machine_env.get("transitive_system_modules"), "transitive_system_modules" in machine_env,
            system_env.get("transitive_system_modules"), "transitive_system_modules" in system_env,
            defaults["transitive_system_modules"])
        effective["require_source_signers"], sources["require_source_signers"] = resolve(
            "environments.require_source_signers",
            machine_env.get("require_source_signers"), "require_source_signers" in machine_env,
            system_env.get("require_source_signers"), "require_source_signers" in system_env,
            defaults["require_source_signers"])
    return profile, profile_source, effective, sources, null_explicit


def _posture_diagnostics(name: str, case: Any, profile: str, effective: dict[str, Any],
                          null_explicit: bool) -> list[dict[str, Any]]:
    """Derive the operation diagnostics in canonical order from the inputs."""
    label = f"security-posture case {name}"
    operation = case.get("operation")
    if not isinstance(operation, dict) or set(operation) != {
        "kind", "mcp_declarations_present", "unreachable_trusted_registries", "artifacts_without_evidence"
    }:
        raise ValidationFailure(f"{label} operation is not the closed four-member shape")
    kind = operation["kind"]
    if kind not in ("install", "profile-install", "status", "status-check"):
        raise ValidationFailure(f"{label} operation kind is not closed")
    unreachable = operation["unreachable_trusted_registries"]
    artifacts = operation["artifacts_without_evidence"]
    if not isinstance(unreachable, list) or not isinstance(artifacts, list):
        raise ValidationFailure(f"{label} unreachable registries and artifacts must be lists")
    if bool(unreachable) != bool(artifacts):
        raise ValidationFailure(f"{label} names unreachable registries without artifacts, or artifacts without a registry")
    schema2 = case["machine"].get("schema_version") == 2
    if not schema2 and operation["mcp_declarations_present"]:
        raise ValidationFailure(f"{label} schema-1 machine carries MCP declarations")
    found: dict[str, dict[str, Any]] = {}
    if profile == "permissive":
        found["security_posture_permissive"] = {
            "code": "security_posture_permissive", "severity": "warning",
            "count": 1, "names_knob": True, "migration_hint": True,
        }
    if profile == "hardened" and not effective["allowed_sources"] and kind in ("install", "profile-install"):
        found["source_allowlist_empty"] = {"code": "source_allowlist_empty", "severity": "error"}
    if schema2 and kind == "profile-install" and not effective["mcp_package_allowlist"]:
        severity = "error" if profile == "hardened" and operation["mcp_declarations_present"] else "warning"
        found["mcp_package_allowlist_empty"] = {"code": "mcp_package_allowlist_empty", "severity": severity}
    if profile == "hardened" and null_explicit and kind == "profile-install":
        found["passable_env_names_unbounded_refused"] = {
            "code": "passable_env_names_unbounded_refused", "severity": "error", "names_knob": True,
        }
    if unreachable and kind in ("install", "profile-install"):
        found["registry_unreachable_during_install"] = {
            "code": "registry_unreachable_during_install",
            "severity": "warning" if profile == "permissive" else "error",
            "registries": unreachable, "artifacts": artifacts,
        }
    return [found[code] for code in SECURITY_POSTURE_DIAGNOSTIC_ORDER if code in found]


def _posture_status_rows(case: Any, profile: str, profile_source: str,
                         effective: dict[str, Any], sources: dict[str, str]) -> tuple[list[dict[str, Any]], Any]:
    """Derive both status-command posture outputs from the resolved inputs.

    When the environments capability exists (schema 2) `curator status`
    and `env status` carry the same closed inventory — the header row
    plus the thirteen shared gates of manager section 10 — so both
    outputs are the one derived list. A schema-1 manager carries only
    the header row plus the four-gate manager subset on `curator
    status`, and `env status` has no posture section (None).
    """
    # The header row spells the knob (`security_posture`, manager §10);
    # the per-gate rows use the hyphenated gate vocabulary.
    header = {"gate": "security_posture", "value": profile, "source": profile_source}
    shipped = case["shipped_revisions"]
    manager_rows = [
        {"gate": "hook-trust", "value": shipped["hook_trust"], "source": "shipped"},
        {"gate": "registry-policy", "value": effective["audit_registry_policy"],
         "source": sources["audit_registry_policy"]},
        {"gate": "audit-mode", "value": effective["audit_mode"], "source": sources["audit_mode"]},
        {"gate": "source-allowlist", "value": len(effective["allowed_sources"]),
         "source": sources["allowed_sources"]},
    ]
    if case["machine"].get("schema_version") == 1:
        return [header, *manager_rows], None
    environments_rows = [
        {"gate": "env-passthrough", "value": shipped["env_passthrough"], "source": "shipped"},
        {"gate": "transitive-system-modules", "value": effective["transitive_system_modules"],
         "source": sources["transitive_system_modules"]},
        {"gate": "provider-trust-roots", "value": shipped["provider_trust_roots"],
         "source": "shipped"},
        {"gate": "source-signers", "value": "true" if effective["require_source_signers"] else "false",
         "source": sources["require_source_signers"]},
        {"gate": "update-confirmation", "value": shipped["update_confirmation"],
         "source": "shipped"},
        {"gate": "codex-seed", "value": shipped["codex_seed"],
         "source": "shipped"},
        {"gate": "store-boundary", "value": "enforced", "source": "shipped"},
        {"gate": "write-discipline", "value": "enforced", "source": "shipped"},
        {"gate": "mcp-package-allowlist", "value": len(effective["mcp_package_allowlist"]),
         "source": sources["mcp_package_allowlist"]},
    ]
    full = [header, *manager_rows, *environments_rows]
    return full, [dict(row) for row in full]


def validate_security_posture_vectors(vector: Any = None) -> None:
    """`vectors/security-posture.json` (manager §1/§7.1/§10, findings S1+S3).

    Structural validation only: the closed posture, diagnostic, provenance,
    and gate vocabularies are pinned, every case is pinned to its
    discriminating inputs, and the effective profile, values, diagnostics,
    outcome, and posture rows are recomputed from the case inputs under the
    section 7.1 merge rules. This gate never runs a manager; downstream
    execution is owned by TASK-260910-1sapuy and the manager posture work.
    """
    if vector is None:
        vector = load_json(SUITE / "vectors" / "security-posture.json")
    if (
        vector.get("schema_version") != 1
        or vector.get("protocol_version") != PROTOCOL_VERSION
        or vector.get("capability") != "security-posture"
        or vector.get("findings") != ["S1", "S3"]
    ):
        raise ValidationFailure("security-posture vector has the wrong capability identity")
    revisions = {entry.get("name"): entry for entry in vector.get("rollout_revisions", [])}
    if set(revisions) != set(SECURITY_POSTURE_REVISION_DEFAULTS):
        raise ValidationFailure("security-posture rollout revisions are not exactly A and B")
    for name, default in SECURITY_POSTURE_REVISION_DEFAULTS.items():
        if revisions[name].get("posture_default") != default:
            raise ValidationFailure(f"security-posture revision {name} defaults to the wrong posture")
    if revisions["A"].get("posture_default") != "permissive" or revisions["B"].get("posture_default") != "hardened":
        raise ValidationFailure("security-posture revisions do not warn first and flip second")
    if vector.get("postures") != ["permissive", "hardened"]:
        raise ValidationFailure("security-posture postures are not the closed two-value set")
    if vector.get("profile_defaults") != SECURITY_POSTURE_DEFAULTS:
        raise ValidationFailure("security-posture profile defaults are not the section 7.1 table")
    if vector.get("profile_refusals") != list(SECURITY_POSTURE_REFUSALS):
        raise ValidationFailure("security-posture refusals are not the closed three-code set")
    if vector.get("diagnostics") != list(SECURITY_POSTURE_DIAGNOSTICS):
        raise ValidationFailure("security-posture diagnostics are not the closed four-code set")
    if vector.get("referenced_diagnostics") != list(SECURITY_POSTURE_REFERENCED_DIAGNOSTICS):
        raise ValidationFailure("security-posture referenced diagnostics are not exact")
    if vector.get("provenance") != list(SECURITY_POSTURE_PROVENANCE):
        raise ValidationFailure("security-posture provenance is not the closed four-value set")
    if vector.get("status_gates") != list(SECURITY_POSTURE_STATUS_GATES):
        raise ValidationFailure("security-posture status gates are not the closed ordered thirteen-gate set")
    if vector.get("schema1_gates") != list(SECURITY_POSTURE_SCHEMA1_GATES):
        raise ValidationFailure("security-posture schema-1 gates are not the closed ordered manager subset")
    binding = vector.get("execution_binding", {})
    if binding.get("downstream_owner_tasks") != ["TASK-260910-1sapuy"]:
        raise ValidationFailure("security-posture execution binding does not name the downstream owner task")
    notes = vector.get("scope_notes")
    if not isinstance(notes, list) or not notes or any(not isinstance(note, str) or not note for note in notes):
        raise ValidationFailure("security-posture scope notes are not a non-empty note list")

    cases = named_cases(vector.get("cases"), "security posture")
    if set(cases) != SECURITY_POSTURE_CASES:
        raise ValidationFailure("security-posture case inventory is not exact")
    seen_codes: set[str] = set()
    for name, case in cases.items():
        profile, profile_source, effective, sources, null_explicit = _posture_resolve(name, case)
        _posture_check_scenario(name, case, profile, profile_source)
        expected = case.get("expected")
        if not isinstance(expected, dict):
            raise ValidationFailure(f"security-posture case {name} carries no expected block")
        if expected.get("profile") != profile or expected.get("profile_source") != profile_source:
            raise ValidationFailure(f"security-posture case {name} profile does not follow its inputs")
        if expected.get("effective") != effective or expected.get("sources") != sources:
            raise ValidationFailure(f"security-posture case {name} effective values do not follow their inputs")
        if expected.get("passable_env_null_explicit") is not null_explicit:
            raise ValidationFailure(f"security-posture case {name} null-explicit flag does not follow its inputs")
        diagnostics = _posture_diagnostics(name, case, profile, effective, null_explicit)
        if expected.get("diagnostics") != diagnostics:
            raise ValidationFailure(f"security-posture case {name} diagnostics do not follow their inputs")
        for entry in diagnostics:
            seen_codes.add(entry["code"])
        kind = case["operation"]["kind"]
        if kind in ("install", "profile-install"):
            want_outcome = "refused" if any(entry["severity"] == "error" for entry in diagnostics) else "proceeds"
        elif kind == "status":
            want_outcome = "current"
        else:
            schema2 = case["machine"].get("schema_version") == 2
            contradicts = profile == "hardened" and (
                not effective["allowed_sources"]
                or (schema2 and null_explicit)
                or (schema2 and not effective["mcp_package_allowlist"]
                    and case["operation"]["mcp_declarations_present"])
            )
            want_outcome = "non-current" if contradicts else "current"
        if expected.get("outcome") != want_outcome:
            raise ValidationFailure(f"security-posture case {name} outcome does not follow its inputs")

        # Both status commands are pinned: `curator status` and `env
        # status` carry the same closed inventory (manager section 10),
        # so both outputs must equal the one derived list.
        want_curator, want_env = _posture_status_rows(case, profile, profile_source, effective, sources)
        curator_rows = expected.get("curator_status_rows")
        if not isinstance(curator_rows, list) or [row.get("gate") for row in curator_rows] != [
            row["gate"] for row in want_curator
        ]:
            raise ValidationFailure(f"security-posture case {name} curator status rows are not the closed ordered set")
        if curator_rows != want_curator:
            raise ValidationFailure(f"security-posture case {name} curator status rows do not follow their inputs")
        env_rows = expected.get("env_status_rows")
        if want_env is None:
            if env_rows is not None:
                raise ValidationFailure(f"security-posture case {name} schema-1 machine carries env status rows")
            continue
        if not isinstance(env_rows, list) or [row.get("gate") for row in env_rows] != [
            row["gate"] for row in want_env
        ]:
            raise ValidationFailure(f"security-posture case {name} env status rows are not the closed ordered set")
        if env_rows != want_env:
            raise ValidationFailure(f"security-posture case {name} env status rows do not follow their inputs")
    want_codes = set(SECURITY_POSTURE_DIAGNOSTICS) | set(SECURITY_POSTURE_REFERENCED_DIAGNOSTICS)
    if seen_codes != want_codes:
        raise ValidationFailure(
            f"security-posture cases cover {sorted(seen_codes)}; want {sorted(want_codes)}"
        )


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
        validate_environments_env_passthrough_vectors,
        validate_environments_source_signers_vectors,
        validate_environments_store_boundary_vectors,
        validate_environments_codex_seed_vectors,
        validate_environments_path_kind_admission_vectors,
        validate_context_version_vectors,
        validate_context_detector_vectors,
        validate_snapshot_acquisition_vectors,
        validate_shell_hook_trust_vectors,
        validate_environments_write_nofollow_vectors,
        validate_environments_dotfile_managers_vectors,
        validate_environments_read_failure_vectors,
        validate_registry_page_boundary_vectors,
        validate_registry_checkpoint_vectors,
        validate_registry_bootstrap_vectors,
        validate_manager_config_vectors,
        validate_system_config_v2_schema,
        validate_umbrella_provider_vectors,
        validate_security_posture_vectors,
        validate_takeover_closed_set_text,
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
