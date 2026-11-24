"""Validate Antigravity managed-home schemas (CIP-0033) and conformance vectors."""
from __future__ import annotations

import json
import posixpath
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = "antigravity-managed-home-v1"


def strict_json(raw: bytes) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for k, v in items:
            if k in out:
                raise ValueError(f"duplicate key: {k}")
            out[k] = v
        return out

    text = raw.decode("utf-8", errors="strict")
    val = json.loads(
        text,
        object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("non-finite JSON constant")),
    )
    json.dumps(val, ensure_ascii=False).encode("utf-8", errors="strict")
    return val


def build_validators(root: Path) -> dict[str, Draft202012Validator]:
    registry = Registry()
    for path in (root / "schemas").rglob("*.schema.json"):
        schema = strict_json(path.read_bytes())
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))

    targets = {
        "launch-env-fragment-v7": root / "schemas" / NAMESPACE / "launch-env-fragment-v7.schema.json",
        "snapshot-launch-v2": root / "schemas" / NAMESPACE / "snapshot-launch-v2.schema.json",
        "node-source-v2": root / "schemas" / NAMESPACE / "node-source-v2.schema.json",
        "launch-env-fragment-v6": root / "schemas" / "local-setup-token-v1" / "launch-env-fragment-v6.schema.json",
        "snapshot-launch-v1": root / "schemas" / "managed-home-snapshot-v1" / "snapshot-launch-v1.schema.json",
    }
    validators: dict[str, Draft202012Validator] = {}
    for name, path in targets.items():
        schema = strict_json(path.read_bytes())
        Draft202012Validator.check_schema(schema)
        validators[name] = Draft202012Validator(schema, registry=registry)
    return validators


def check_semantics(schema_name: str, doc: dict[str, Any]) -> str | None:
    if schema_name == "launch-env-fragment-v7" and doc.get("environment") == "antigravity":
        home = doc.get("home") or {}
        home_path = home.get("path", "")
        cleaned = posixpath.normpath(home_path)
        if not home_path or cleaned != home_path or posixpath.basename(cleaned) == ".gemini":
            return "antigravity home.path must be normalized and basename must not be .gemini"
        mcp = doc.get("mcp")
        if mcp is not None:
            expected = posixpath.join(cleaned, "config/mcp_config.json")
            if mcp.get("path") != expected:
                return f"antigravity mcp.path must equal {expected}"
    return None


def run(root: Path = ROOT, out=None) -> int:
    stream = out or sys.stdout
    validators = build_validators(root)
    cases_path = root / "conformance" / NAMESPACE / "cases.json"
    data = strict_json(cases_path.read_bytes())
    passed = 0
    for case in data["cases"]:
        cid = case["id"]
        sname = case["schema"]
        expect = case["expect"]
        doc = case["document"]
        schema_errs = list(validators[sname].iter_errors(doc))
        sem_err = None if schema_errs else check_semantics(sname, doc)
        is_valid = (not schema_errs) and (sem_err is None)
        if expect == "valid" and not is_valid:
            msg = schema_errs[0].message if schema_errs else sem_err
            print(f"FAIL {cid}: expected valid, got: {msg}", file=stream)
            return 1
        if expect == "invalid" and is_valid:
            print(f"FAIL {cid}: expected invalid, got valid", file=stream)
            return 1
        passed += 1
    print(f"antigravity-managed-home-v1: {passed}/{len(data['cases'])} schema/semantic cases passed", file=stream)
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
