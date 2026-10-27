"""Check home-lease specification data; no process, lock or runtime model."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


def _pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in values:
        if key in result:
            raise ValueError(f"duplicate member: {key}")
        result[key] = value
    return result


def _no_constant(value: str) -> Any:
    raise ValueError(f"non-integer or non-JSON number: {value}")


def decode(raw: bytes) -> Any:
    value = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=_pairs,
                       parse_constant=_no_constant, parse_float=_no_constant)
    # Reject unpaired surrogate escapes even when the byte stream is valid UTF-8.
    json.dumps(value, ensure_ascii=False).encode("utf-8", errors="strict")
    return value


def validators(root: Path) -> dict[str, Draft202012Validator]:
    documents = {}
    for path in sorted((root / "schemas/home-leases-v1").glob("*.schema.json")):
        document = decode(path.read_bytes())
        Draft202012Validator.check_schema(document)
        documents[path.stem.removesuffix(".schema")] = document
    if set(documents) != {"holder", "record", "event", "result"}:
        raise ValueError("home-lease schema set changed")
    registry = Registry().with_resources(
        (document["$id"], Resource.from_contents(document)) for document in documents.values()
    )
    return {name: Draft202012Validator(document, registry=registry, format_checker=FormatChecker())
            for name, document in documents.items()}


def accepts(validator: Draft202012Validator, raw: bytes) -> bool:
    try:
        document = decode(raw)
    except (ValueError, UnicodeError):
        return False
    return validator.is_valid(document)


def check_schema_pairs(pairs: list[dict[str, Any]], checks: dict[str, Draft202012Validator]) -> None:
    names = set()
    for pair in pairs:
        name = pair["name"]
        if name in names:
            raise ValueError(f"duplicate schema pair: {name}")
        names.add(name)
        validator = checks[pair["schema"]]
        if not accepts(validator, pair["positive"].encode("utf-8")):
            raise ValueError(f"positive rejected: {name}")
        raw = bytes.fromhex(pair["negative_hex"]) if "negative_hex" in pair else pair["negative"].encode("utf-8")
        if accepts(validator, raw):
            raise ValueError(f"negative accepted: {name}")


def check_semantic_pairs(cases: list[dict[str, Any]], required: set[str]) -> None:
    found = set()
    for case in cases:
        if set(case) != {"requirement", "negative", "positive"}:
            raise ValueError("semantic pair requires negative and positive controls")
        found.add(case["requirement"])
        for key in ("negative", "positive"):
            branch = case[key]
            if not branch.get("setup") or not branch.get("steps") or not branch.get("expected"):
                raise ValueError(f"incomplete semantic {key}: {case['requirement']}")
        if not case["negative"].get("preserve") or not case["negative"].get("forbidden"):
            raise ValueError(f"missing negative invariant: {case['requirement']}")
    if found != required:
        raise ValueError(f"requirement coverage mismatch: missing={sorted(required-found)}, extra={sorted(found-required)}")


def check_corpus(root: Path) -> tuple[int, int]:
    checks = validators(root)
    suite = root / "conformance/home-leases-v1"
    schema_pairs = decode((suite / "schema-cases.json").read_bytes())
    semantic = decode((suite / "cases.json").read_bytes())
    if schema_pairs["kind"] != "home-lease-schema-pairs-v1" or semantic["kind"] != "home-lease-semantic-v1":
        raise ValueError("home-lease corpus version changed")
    text = (root / "protocol/home-leases.md").read_text()
    required = set(re.findall(r"\*\*(HL\d{2})(?: \(L\d\))?\.\*\*", text))
    required.update(re.findall(r"^\| (W\d{2}) \|", text, flags=re.MULTILINE))
    if not required:
        raise ValueError("home-lease requirements absent")
    check_schema_pairs(schema_pairs["pairs"], checks)
    check_semantic_pairs(semantic["cases"], required)
    return len(schema_pairs["pairs"]), len(semantic["cases"])


if __name__ == "__main__":
    count, semantic = check_corpus(Path(__file__).resolve().parents[1])
    print(f"home leases: {count} schema/decoder pairs; {semantic} semantic pairs; runtime unverified")
