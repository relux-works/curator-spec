"""Validate containing-schema drafts only; final #216 parity is unverified."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from host_notification import IntegerTokenValidator


ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = "machine-claude-env-v1"
RESOURCES = (
    "host-notification-v1/manager-config-v8.schema.json",
    "host-notification-v1/extensions.schema.json",
    "host-notification-v1/launcher-config-v2.schema.json",
    "machine-claude-env-v1/claude-env.schema.json",
    "machine-claude-env-v1/extensions.schema.json",
    "machine-claude-env-v1/manager-config-v9.schema.json",
    "machine-claude-env-v1/launcher-config-v3.schema.json",
    "rc7-carriers-v1/manager-config-v5.schema.json",
    "v1/common.schema.json",
    "v1/manager-config-v1.schema.json",
    "login-readiness-v1/credential-store-config-v1.schema.json",
)


class SetupError(ValueError):
    """Fixed setup classification; never expose supplied input in diagnostics."""


def strict(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise SetupError("invalid-json")
            result[key] = value
        return result

    def constant(_):
        raise SetupError("invalid-json")

    try:
        return json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw,
                          object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeError):
        raise SetupError("invalid-json") from None


def validators(root):
    documents = {}
    resources = []
    for name in RESOURCES:
        document = strict((root / "schemas" / name).read_bytes())
        Draft202012Validator.check_schema(document)
        identity = "https://relux-works.github.io/curator-spec/schemas/" + name
        if document.get("$id") != identity:
            raise SetupError("schema-setup")
        documents[name] = document
        resources.append((identity, Resource.from_contents(document)))
    # No retrieval callback: an undeclared schema reference fails closed offline.
    registry = Registry().with_resources(resources)
    return {
        entry: IntegerTokenValidator(documents[name], registry=registry)
        for entry, name in (
            ("configuration", f"{NAMESPACE}/manager-config-v9.schema.json"),
            ("launcher", f"{NAMESPACE}/launcher-config-v3.schema.json"),
            ("configuration-v8", "host-notification-v1/manager-config-v8.schema.json"),
            ("launcher-v2", "host-notification-v1/launcher-config-v2.schema.json"),
        )
    }


def load_cases(root):
    cases = strict((root / "conformance" / NAMESPACE / "containing-cases.json").read_bytes())
    fields = {"id", "claim", "entry", "input_json", "schema_valid"}
    if not isinstance(cases, list) or not cases:
        raise SetupError("corpus-setup")
    seen = set()
    for case in cases:
        if (not isinstance(case, dict) or set(case) != fields
                or any(not isinstance(case[key], str) for key in fields - {"schema_valid"})
                or type(case["schema_valid"]) is not bool
                or not case["claim"] or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", case["id"])
                or case["id"] in seen or case["entry"] not in {
                    "configuration", "launcher", "configuration-v8", "launcher-v2"}):
            raise SetupError("corpus-setup")
        seen.add(case["id"])
    return cases


def check_cases(cases, compiled, output):
    failures = 0
    for case in cases:
        try:
            valid = compiled[case["entry"]].is_valid(strict(case["input_json"]))
        except SetupError:
            valid = False
        passed = valid == case["schema_valid"]
        failures += not passed
        print(f"{'PASS' if passed else 'FAIL'} {case['id']} schema-valid={str(valid).lower()}", file=output)
    return failures


def declaration_controls(root, validator, baseline=None):
    # Prove the exact same carrier accepts a valid member before interpreting
    # any embedded member vector. This is structural setup, not a Core driver.
    prefix = baseline if baseline is not None else '{"schema_version":9,"skills_root":"/example/skills","projects":{},"extensions":{"claude_env":'
    suffix = '}}'
    if not validator.is_valid(strict(prefix + '{"BASH_MAX_OUTPUT_LENGTH":"8000"}' + suffix)):
        raise SetupError("carrier-setup")
    count = 0
    cases = strict((root / "conformance" / NAMESPACE / "cases.json").read_bytes())
    for case in cases:
        if case["entry"] != "declaration":
            continue
        embedded = prefix + case["input_json"] + suffix
        try:
            strict(case["input_json"])
        except SetupError:
            try:
                strict(embedded)
            except SetupError:
                count += 1
                continue
            raise SetupError("file-control")
        if validator.is_valid(strict(embedded)) != case["schema_valid"]:
            raise SetupError("member-control")
        count += 1
    return count


def run(root, output):
    try:
        compiled = validators(root)
        cases = load_cases(root)
        controls = declaration_controls(root, compiled["configuration"])
        failures = check_cases(cases, compiled, output)
    except Exception:
        # Includes resolution/schema errors: never print parser details or input.
        print("FAIL containing-setup", file=output)
        return 2
    print(f"containing-cases={len(cases)} declaration-controls={controls} failures={failures} "
          "final-predecessor-parity=unverified runtime-cases=0", file=output)
    return int(failures != 0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    sys.exit(run(args.root, sys.stdout))
