"""Specification checks for the separate snapshot corpus; no manager execution."""

from __future__ import annotations

import hashlib
import unicodedata
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource


NAMESPACE = "managed-home-snapshot-v1"
MANIFEST_SCHEMA = "managed-home-snapshot-v1.schema.json"
LAUNCH_SCHEMA = "snapshot-launch-v1.schema.json"


def sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def validators(root, load_json):
    resources, schemas = [], {}
    for directory in (root / "schemas/v1", root / "schemas" / NAMESPACE):
        for path in sorted(directory.glob("*.schema.json")):
            schema = load_json(path)
            Draft202012Validator.check_schema(schema)
            resources.append((schema["$id"], Resource.from_contents(schema)))
            if directory.name == NAMESPACE:
                schemas[path.name] = schema
    if set(schemas) != {MANIFEST_SCHEMA, LAUNCH_SCHEMA}:
        raise ValueError("snapshot schema inventory")
    registry = Registry().with_resources(resources)
    return {name: Draft202012Validator(schema, registry=registry)
            for name, schema in schemas.items()}


def portable_projection(manifest):
    """Only source-fragment provenance is excluded, not producer/profile identity."""
    return {key: value for key, value in manifest.items() if key != "fragment_sha256"}


def check_bundle(manifest, launch, content, checks, canonicalize, wire_semantics,
                 manifest_bytes=None, launch_bytes=None):
    """Validate synthetic bundle metadata and file identities, not filesystem safety."""
    if not checks[MANIFEST_SCHEMA].is_valid(manifest):
        raise ValueError("manifest-schema")
    if not checks[LAUNCH_SCHEMA].is_valid(launch):
        raise ValueError("launch-schema")
    expected_manifest = canonicalize(manifest) + b"\n"
    expected_launch = canonicalize(launch) + b"\n"
    if ((manifest_bytes is not None and manifest_bytes != expected_manifest)
            or (launch_bytes is not None and launch_bytes != expected_launch)):
        raise ValueError("metadata-canonical")
    if manifest["adapter"] != launch["environment"] or manifest["profile"] != launch["profile"]:
        raise ValueError("adapter-profile")
    if manifest["launch_sha256"] != sha256(expected_launch):
        raise ValueError("launch-digest")
    paths = [entry["path"] for entry in manifest["files"]]
    if paths != sorted(paths, key=lambda path: path.encode("utf-8")):
        raise ValueError("path-order")
    normalized, components = set(), {}
    for path in paths:
        parts = path.split("/")
        for index in range(1, len(parts) + 1):
            prefix = "/".join(parts[:index])
            key = unicodedata.normalize("NFC", prefix).casefold()
            if key in components and components[key] != prefix:
                raise ValueError("path-collision")
            components[key] = prefix
        key = unicodedata.normalize("NFC", path).casefold()
        if key in normalized:
            raise ValueError("path-collision")
        normalized.add(key)
    for path in paths:
        parts = path.split("/")
        if any(unicodedata.normalize("NFC", "/".join(parts[:index])).casefold()
               in normalized for index in range(1, len(parts))):
            raise ValueError("file-ancestor")
    if set(paths) != set(content):
        raise ValueError("entry-set")
    for entry in manifest["files"]:
        payload, mode = content[entry["path"]]
        if (entry["size"] != len(payload) or entry["sha256"] != sha256(payload)
                or entry["mode"] != mode):
            raise ValueError("file-identity")
    for channel in ("system_prompt", "mcp"):
        if channel in launch and launch[channel]["path"] not in paths:
            raise ValueError("channel-reference")
    # Reuse the environments validator for unchanged channel semantics. It
    # does not inspect the fragment discriminator or alter snapshot env maps.
    if wire_semantics("launch-env-fragment-v3.schema.json", launch) is not None:
        raise ValueError("channel-semantics")
    if launch["environment"] == "muse":
        has_root = "home/config/muse/AGENTS.md" in paths
        if ("root_context" in launch) != has_root:
            raise ValueError("root-context")


def check_corpus(root, load_json, canonicalize, wire_semantics, vector=None):
    suite = root / "conformance" / NAMESPACE
    checks = validators(root, load_json)
    index = load_json(suite / "index.json")
    coverage = {}
    instances = set()
    for case in index:
        if set(case) != {"schema", "instance", "valid"} or case["schema"] not in checks:
            raise ValueError("snapshot schema case shape")
        instance = case["instance"]
        if instance in instances or not instance.startswith("cases/") or ".." in instance.split("/"):
            raise ValueError("snapshot schema case inventory")
        instances.add(instance)
        actual = checks[case["schema"]].is_valid(load_json(suite / instance))
        if actual != case["valid"]:
            raise ValueError(f"snapshot schema case {instance}: expected {case['valid']}, got {actual}")
        coverage.setdefault(case["schema"], set()).add(case["valid"])
    if set(coverage) != set(checks) or any(values != {True, False} for values in coverage.values()):
        raise ValueError("snapshot schema positive/negative coverage")
    actual_cases = {path.relative_to(suite).as_posix() for path in (suite / "cases").glob("*.json")}
    if instances != actual_cases:
        raise ValueError("snapshot unindexed schema case")

    if vector is None:
        vector = load_json(suite / "vectors.json")
    if set(vector) != {"contract", "cases"} or vector["contract"] != NAMESPACE:
        raise ValueError("snapshot vector identity")
    names = set()
    for case in vector["cases"]:
        if set(case) != {"name", "manifest", "launch", "content", "expected"} or case["name"] in names:
            raise ValueError("snapshot semantic case shape")
        names.add(case["name"])
        manifest_path, launch_path = suite / case["manifest"], suite / case["launch"]
        content = {}
        for entry in case["content"]:
            if set(entry) != {"path", "source", "mode"} or entry["path"] in content:
                raise ValueError("snapshot content fixture shape")
            content[entry["path"]] = ((suite / entry["source"]).read_bytes(), entry["mode"])
        try:
            check_bundle(load_json(manifest_path), load_json(launch_path), content,
                         checks, canonicalize, wire_semantics,
                         manifest_path.read_bytes(), launch_path.read_bytes())
            actual = "accept"
        except ValueError as exc:
            actual = str(exc)
        if actual != case["expected"]:
            raise ValueError(f"snapshot semantic case {case['name']}: expected {case['expected']}, got {actual}")
    required = {"exact-content", "extra-entry", "missing-entry", "changed-bytes", "execute-mode",
                "wrong-size", "launch-digest", "adapter-binding", "profile-binding", "path-order",
                "duplicate-path", "case-collision", "directory-case-collision", "unicode-collision",
                "file-ancestor", "channel-reference", "channel-semantics", "metadata-lf"}
    if not required <= names:
        raise ValueError("snapshot semantic case coverage")

    golden = suite / "golden"
    digests = load_json(golden / "digests.json")
    for name in ("manifest.json", "launch.json"):
        if digests.get(name) != sha256((golden / name).read_bytes()):
            raise ValueError("snapshot golden digest")
    manifest = load_json(golden / "manifest.json")
    provenance = load_json(golden / "other-source-manifest.json")
    if (manifest["fragment_sha256"] == provenance["fragment_sha256"]
            or portable_projection(manifest) != portable_projection(provenance)
            or canonicalize(manifest) == canonicalize(provenance)):
        raise ValueError("snapshot source-bound versus portable identity")

    pins = load_json(suite / "manifest.json")
    expected_paths = {"protocol/managed-home-snapshots.md"}
    for directory in (suite, root / "schemas" / NAMESPACE):
        expected_paths.update(path.relative_to(root).as_posix() for path in directory.rglob("*")
                              if path.is_file() and path != suite / "manifest.json")
    if set(pins) != {"contract", "files"} or pins["contract"] != NAMESPACE:
        raise ValueError("snapshot corpus manifest shape")
    entries = pins["files"]
    if [entry["path"] for entry in entries] != sorted(expected_paths):
        raise ValueError("snapshot corpus manifest inventory")
    for entry in entries:
        if set(entry) != {"path", "sha256"} or entry["sha256"] != "sha256:" + sha256((root / entry["path"]).read_bytes()):
            raise ValueError("snapshot corpus pin mismatch")
    print(f"snapshot schemas: {len(checks)}/{len(checks)}; schema cases: {len(index)}/{len(index)}; "
          f"semantic metadata cases: {len(names)}/{len(names)}; materialize execution: 0")
