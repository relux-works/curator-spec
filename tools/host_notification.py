"""Draft notification carrier conformance; no editor or runtime execution."""
from __future__ import annotations

import argparse
import json
import ntpath
import posixpath
import re
import sys
import unicodedata
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = "host-notification-v1"
VALID = ("ok", "$")


def strict(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate")
            result[key] = value
        return result
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="strict")
    value = json.loads(raw, object_pairs_hook=pairs,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError("constant")))
    # Also reject lone escaped surrogates, without printing input.
    json.dumps(value, ensure_ascii=False).encode("utf-8", errors="strict")
    return value


def validators(root):
    registry = Registry()
    for path in (root / "schemas").rglob("*.schema.json"):
        schema = strict(path.read_bytes())
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    result = {}
    for name in ("manager-config-v7", "manager-config-v8", "launcher-config-v1", "launcher-config-v2"):
        schema = strict((root / "schemas" / NAMESPACE / (name + ".schema.json")).read_bytes())
        Draft202012Validator.check_schema(schema)
        result[name] = Draft202012Validator(schema, registry=registry)
    return result


def reference(value):
    return (isinstance(value, str) and 0 < len(value.encode("utf-8")) <= 4096
            and value.strip() == value
            and not any(unicodedata.category(c) == "Cc" for c in value))


def absolute(value):
    if not reference(value):
        return False
    platform = ntpath if re.match(r"^(?:[A-Za-z]:[\\/]|\\\\)", value) else posixpath
    # Match target-platform Clean rather than converting separator spelling.
    cleaned = platform.normpath(value)
    if platform is ntpath:
        cleaned = cleaned.replace("/", "\\")
    return platform.isabs(value) and cleaned == value and not (platform is posixpath and value.startswith("//"))


def extension_semantics(ext):
    if "proxy" in ext and not reference(ext["proxy"]["profile"]):
        return False
    if "claude_auth" in ext:
        store = ext["claude_auth"]["store"]
        if store["type"] == "file":
            if not absolute(store["path"]):
                return False
        elif not reference(store["service"]) or not reference(store["account"]):
            return False
    return True


def verdict(case, compiled):
    try:
        value = strict(case["input_json"])
    except (ValueError, UnicodeError):
        return ("config_json_invalid", "$")
    if not isinstance(value, dict):
        return ("config_shape_invalid", "$")
    if case["entry"] == "system":
        locks = value.get("locked", [])
        if "extensions" in value or any(isinstance(k, str) and
                (k == "extensions" or k.startswith("extensions.")) for k in locks):
            return ("launcher_selection_machine_only", "extensions")
        return VALID
    if case["entry"] == "projection":
        version = value.get("config_schema")
        name = "launcher-config-v2" if version == 8 else "launcher-config-v1"
        if not compiled[name].is_valid(value):
            return ("launcher_projection_invalid", "schema")
        if not absolute(value["config_path"]) or not extension_semantics(value["extensions"]):
            return ("launcher_selection_invalid", "extensions")
        return VALID
    version = value.get("schema_version")
    if type(version) is not int or version not in (1, 2, 3, 5, 7, 8):
        return ("config_schema_unsupported", "schema_version")
    ext = value.get("extensions", {})
    if "extensions" in value and version not in (7, 8):
        return ("launcher_extensions_schema", "extensions")
    # Validate the extension in a known-good containing object before applying
    # unrelated carrier checks. This is a conformance model, not a Core parser.
    if version in (7, 8):
        control = {"schema_version": version, "skills_root": "x", "projects": {}, "extensions": ext}
        if not compiled[f"manager-config-v{version}"].is_valid(control) or not extension_semantics(ext):
            return ("launcher_selection_invalid", "extensions")
        if not compiled[f"manager-config-v{version}"].is_valid(value):
            return ("config_shape_invalid", "$")
    else:
        # Legacy configuration vectors here establish extension refusal only;
        # full legacy admission remains in the repository's frozen suites.
        return ("config_shape_invalid", "$")
    return VALID


def load_cases(root):
    cases = strict((root / "conformance" / NAMESPACE / "cases.json").read_bytes())
    if not isinstance(cases, list) or not cases:
        raise ValueError("corpus")
    ids = set()
    for case in cases:
        if (not isinstance(case, dict) or set(case) != {"id", "entry", "input_json", "expected"}
                or not isinstance(case["id"], str) or not re.fullmatch(r"[a-z0-9-]+", case["id"])
                or case["id"] in ids or case["entry"] not in ("configuration", "projection", "system")
                or not isinstance(case["input_json"], str) or not isinstance(case["expected"], list)
                or len(case["expected"]) != 2
                or not all(isinstance(x, str) for x in case["expected"])):
            raise ValueError("case")
        ids.add(case["id"])
    return cases


def check_cases(cases, compiled, output):
    failures = 0
    for case in cases:
        ok = verdict(case, compiled) == tuple(case["expected"])
        failures += not ok
        print(("PASS " if ok else "FAIL ") + case["id"], file=output)
    return failures


def predecessor_controls(root, compiled):
    # Published predecessor corpus is the independent positive control, not
    # output from the inspected implementation. Version migration alone must
    # retain every existing valid configuration fixture in this corpus.
    count = 0
    for path in (root / "conformance/rc7-carriers-v1/cases").glob("config-*.json"):
        original = strict(path.read_bytes())
        # Deliberately invalid predecessor files must not become positive controls.
        registry_schema = compiled["manager-config-v8"]._registry
        old = strict((root / "schemas/rc7-carriers-v1/manager-config-v5.schema.json").read_bytes())
        if not Draft202012Validator(old, registry=registry_schema).is_valid(original):
            continue
        for version in (7, 8):
            candidate = dict(original, schema_version=version)
            if not compiled[f"manager-config-v{version}"].is_valid(candidate):
                raise ValueError("predecessor-preservation")
        count += 1
    if not count:
        raise ValueError("missing-predecessor")
    return count


def run(root=ROOT, output=sys.stdout):
    try:
        compiled = validators(root)
        controls = predecessor_controls(root, compiled)
        cases = load_cases(root)
        failures = check_cases(cases, compiled, output)
    except Exception:
        print("FAIL notification-corpus-setup", file=output)
        return 2
    print(f"notification-cases={len(cases)} predecessor-controls={controls} failures={failures} runtime-cases=0", file=output)
    return int(failures != 0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    raise SystemExit(run(parser.parse_args().root))
