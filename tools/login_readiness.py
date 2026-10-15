"""Structural conformance for the separately published login-readiness grammar."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource


class ContractError(ValueError):
    """The corpus or a structural verdict violates the published contract."""


def validate(root: Path, *, schemas=None, cases=None) -> tuple[int, int]:
    directory = root / "conformance/login-readiness-v1"
    schema_dir = root / "schemas/login-readiness-v1"
    if schemas is None:
        schemas = {p.name: json.loads(p.read_text()) for p in schema_dir.glob("*.json")}
    if cases is None:
        cases = json.loads((directory / "index.json").read_text())
    expected = {"login-row-v1.schema.json", "credential-store-config-v1.schema.json",
                "store-projection-v1.schema.json"}
    if set(schemas) != expected:
        raise ContractError("login-readiness schema inventory differs")
    resources = []
    for path in sorted((root / "schemas/v1").glob("*.json")):
        document = json.loads(path.read_text())
        resources.append((document["$id"], Resource.from_contents(document)))
    for name, document in schemas.items():
        Draft202012Validator.check_schema(document)
        if document["$id"] != "https://relux-works.github.io/curator-spec/schemas/login-readiness-v1/" + name:
            raise ContractError("login-readiness schema identity differs")
        resources.append((document["$id"], Resource.from_contents(document)))
    registry = Registry().with_resources(resources)
    coverage = {name: set() for name in schemas}
    instances = set()
    names = set()
    for case in cases:
        if (set(case) != {"name", "schema", "instance", "valid"}
                or type(case["valid"]) is not bool or case["schema"] not in schemas
                or case["name"] in names or case["instance"] in instances):
            raise ContractError("invalid or duplicated login-readiness case")
        path = directory / case["instance"]
        if not path.resolve().is_relative_to((directory / "schema-cases").resolve()):
            raise ContractError("login-readiness instance escapes schema cases")
        instance = json.loads(path.read_text())
        actual = Draft202012Validator(schemas[case["schema"]], registry=registry).is_valid(instance)
        if actual != case["valid"]:
            raise ContractError(f"{case['name']}: expected valid={case['valid']}, got {actual}")
        names.add(case["name"])
        instances.add(case["instance"])
        coverage[case["schema"]].add(actual)
    inventory = {p.relative_to(directory).as_posix() for p in (directory / "schema-cases").glob("*.json")}
    if instances != inventory or any(values != {True, False} for values in coverage.values()):
        raise ContractError("login-readiness cases missing from inventory or positive/negative coverage")
    return len(cases), sum(not case["valid"] for case in cases)
