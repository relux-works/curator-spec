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

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas" / "v1"
SUITE = ROOT / "conformance" / "v1"
REVIEWS = ROOT / "reviews"
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


def validate_schemas() -> None:
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
    if schema_name in {"agent-skill-v7.schema.json", "csk-skill-v7.schema.json"}:
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
    elif schema_name == "curator-build-v1.schema.json":
        for target in instance.get("targets", {}).values():
            if isinstance(target, dict):
                root, source = target.get("build_root"), target.get("source_dir")
                if isinstance(root, str) and isinstance(source, str) and not is_below_or_equal(source, root):
                    return "source_dir must equal or be below build_root"
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
        validate_manifest,
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
    print(f"validated {len(list(SCHEMAS.glob('*.json')))} schemas and {len(load_json(SUITE / 'manifest.json')['files'])} vector files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
