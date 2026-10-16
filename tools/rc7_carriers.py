"""Whole-carrier publication checks. These never execute a vendor or qualify storage."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource


NAMESPACE = "rc7-carriers-v1"
SCHEMAS = {
    "manager-config-v5", "env-status-v1", "agent-context-v2",
    "context-lock-v4", "agent-environment-marker-v5", "launch-env-fragment-v5",
}
PREDECESSORS = {
    "agent-context-v2": "agent-context-v1",
    "context-lock-v4": "context-lock-v2",
    "agent-environment-marker-v5": "agent-environment-marker-v3",
    "launch-env-fragment-v5": "launch-env-fragment-v4",
}
HOME_CREDENTIAL_SOURCES = {"per-home", "native"}

# These bounded clauses pin the status execution rule on each amended normative
# surface. A link to the central publication alone does not establish agreement.
STATUS_BOUNDARIES = {
    "protocol/rc7-carriers.md":
        "Adopting readiness status executes no agent binary, including --version or auth status.",
    "protocol/login-readiness.md":
        "Status MUST NOT invoke an agent executable, open a credential file for its content, "
        "request Keychain secret data, invoke a secret-producing helper, attempt network access, "
        "acquire a broker lease, prompt or unlock a store.",
    "protocol/environments.md":
        "Adopting readiness status MUST execute no agent binary, including `--version` and `auth status`; "
        "detected release is unknown unless established without agent execution.",
    "cli/curator.md":
        "Adopting status invokes no agent binary, including version probes and auth status; "
        "detected version can be unknown.",
    "profiles/manager.md":
        "execute no agent binary, including version probes and auth status. Detected release "
        "remains unknown unless established without agent execution; any later vendor diagnostic "
        "is explicit, with no implicit status call site.",
}


class ContractError(ValueError):
    """A published carrier or a claimed corpus verdict is inconsistent."""


def registry(root, load):
    resources = []
    schemas = {}
    for namespace in ("v1", "login-readiness-v1", "profile-codex-settings-v1", NAMESPACE):
        for path in sorted((root / "schemas" / namespace).glob("*.schema.json")):
            document = load(path)
            Draft202012Validator.check_schema(document)
            resources.append((document["$id"], Resource.from_contents(document)))
            if namespace == NAMESPACE:
                name = path.name.removesuffix(".schema.json")
                if document["$id"] != f"https://relux-works.github.io/curator-spec/schemas/{NAMESPACE}/{path.name}":
                    raise ContractError("carrier schema identity differs")
                schemas[name] = document
    if set(schemas) != SCHEMAS:
        raise ContractError("carrier schema inventory differs")
    return Registry().with_resources(resources), schemas


def carrier_error(name, instance, schemas, resources, wire_semantics):
    """Return a stable publication refusal; leave the supplied document unchanged."""
    schema = schemas[name]
    if not Draft202012Validator(schema, registry=resources).is_valid(instance):
        return "carrier_schema_invalid"
    if name in PREDECESSORS:
        predecessor = PREDECESSORS[name]
        # Reuse retained non-schema constraints; schema validation above has
        # already checked the new token and the single payload authority.
        legacy = copy.deepcopy(instance)
        if name == "launch-env-fragment-v5":
            legacy["fragment"] = predecessor
            payload = legacy.pop("codex_settings", None)
            if payload:
                legacy["credential_store"]["config_overrides"] = payload
        if wire_semantics(predecessor + ".schema.json", legacy):
            return "carrier_semantics_invalid"
    if name == "env-status-v1":
        identities = []
        for row in instance["rows"]:
            readiness = row["readiness"]
            identities.append((readiness["profile"], readiness["environment"]))
            if row["effective_store"] != readiness["login_detail"]["store"]:
                return "carrier_semantics_invalid"
            if readiness["environment"] == "muse" and (
                row["effective_store"] != "file" or row["configured_store"] == "keychain"
            ):
                return "carrier_semantics_invalid"
            detail = readiness["login_detail"]
            if (readiness["environment"] == "muse" and readiness["login"] in {"present", "absent"}
                    and detail["source"] in HOME_CREDENTIAL_SOURCES and detail["backend"] != "file"):
                return "carrier_semantics_invalid"
            if readiness["environment"] == "opencode" and (
                readiness["login"] != "unknown" or readiness["login_detail"]["source"] != "ambient"
                or readiness["login_detail"]["backend"] != "unknown"
                or readiness["login_detail"]["reason"] != "ambient"
            ):
                return "carrier_semantics_invalid"
        if identities != sorted(set(identities)):
            return "carrier_semantics_invalid"
        profiles = [row["profile"] for row in instance["codex_settings"]]
        if profiles != sorted(set(profiles)) or set(profiles) != {p for p, _ in identities}:
            return "carrier_semantics_invalid"
    return None


def check_corpus(root: Path, load, canonical, wire_semantics):
    directory = root / "conformance" / NAMESPACE
    resources, schemas = registry(root, load)
    cases = load(directory / "index.json")
    names, paths, coverage = set(), set(), {name: set() for name in schemas}
    negatives = 0
    for case in cases:
        if set(case) != {"name", "schema", "instance", "error"} or case["name"] in names:
            raise ContractError("invalid or duplicate carrier case")
        names.add(case["name"])
        path = directory / case["instance"]
        if not path.resolve().is_relative_to((directory / "cases").resolve()):
            raise ContractError("carrier case escapes inventory")
        paths.add(case["instance"])
        instance = load(path)
        actual = carrier_error(case["schema"], instance, schemas, resources, wire_semantics)
        if actual != case["error"]:
            raise ContractError(f"{case['name']}: expected {case['error']}, got {actual}")
        coverage[case["schema"]].add(actual is None)
        negatives += actual is not None
    inventory = {p.relative_to(directory).as_posix() for p in (directory / "cases").glob("*.json")}
    if paths != inventory or len(paths) != len(cases) or any(v != {True, False} for v in coverage.values()):
        raise ContractError("carrier inventory or paired coverage differs")
    canonical_cases = load(directory / "canonical.json")
    if {case["instance"] for case in canonical_cases} != {
        next(c["instance"] for c in cases if c["schema"] == name and c["error"] is None)
        for name in schemas
    } or len(canonical_cases) != len(schemas):
        raise ContractError("canonical carrier inventory differs")
    for case in canonical_cases:
        instance = load(directory / case["instance"])
        payload = canonical(instance)
        if (directory / case["bytes"]).read_bytes() != payload:
            raise ContractError("canonical carrier bytes differ: " + case["instance"])
        if hashlib.sha256(payload).hexdigest() != case["sha256"]:
            raise ContractError("canonical carrier digest differs: " + case["instance"])
    check_compatibility(root, load, schemas, resources, wire_semantics)
    check_decisions(root, load)
    check_delivery_vectors(root, load)
    return len(cases), negatives


def check_compatibility(root, load, schemas, resources, wire_semantics):
    directory = root / "conformance" / NAMESPACE
    pairs = load(directory / "compatibility.json")
    if {pair["new_schema"] for pair in pairs} != set(PREDECESSORS) or len(pairs) != len(PREDECESSORS):
        raise ContractError("carrier compatibility inventory differs")
    for pair in pairs:
        new_name = pair["new_schema"]
        if pair["old_schema"] != PREDECESSORS[new_name]:
            raise ContractError("carrier predecessor differs")
        old_reader = Draft202012Validator(load(root / "schemas/v1" / (pair["old_schema"] + ".schema.json")),
                                           registry=resources)
        old = load(root / pair["old_control"])
        new = load(directory / pair["new_control"])
        if not old_reader.is_valid(old) or old_reader.is_valid(new):
            raise ContractError("old reader compatibility differs: " + new_name)
        if carrier_error(new_name, new, schemas, resources, wire_semantics) is not None:
            raise ContractError("successor control invalid: " + new_name)
        if carrier_error(new_name, old, schemas, resources, wire_semantics) != "carrier_schema_invalid":
            raise ContractError("new reader admitted old token: " + new_name)
        if new[pair["discriminator"]] != pair["new_value"]:
            raise ContractError("successor discriminator differs: " + new_name)


def check_decisions(root, load):
    """Check published cross-document requirements, not runtime outcomes."""
    decisions = load(root / "conformance" / NAMESPACE / "decisions.json")
    publication = (root / "protocol/rc7-carriers.md").read_text()
    for decision in decisions:
        if set(decision) != {"id", "clause", "outcome", "forbidden_effects"}:
            raise ContractError("invalid publication decision")
        if decision["clause"] not in publication or decision["outcome"] not in publication:
            raise ContractError("missing published decision: " + decision["id"])
        if not decision["forbidden_effects"]:
            raise ContractError("missing forbidden-effects requirement: " + decision["id"])
    for path in ("protocol/login-readiness.md", "protocol/profile-codex-settings.md", "protocol/environments.md"):
        if "rc7-carriers.md" not in (root / path).read_text():
            raise ContractError("missing coordinated publication reference: " + path)
    for path, clause in STATUS_BOUNDARIES.items():
        if clause not in " ".join((root / path).read_text().split()):
            raise ContractError("incoherent status execution boundary: " + path)


def check_delivery_vectors(root, load):
    """Validate expected transport outcomes against the published decision table.

    This checks requirements as data. It does not execute an env/shell renderer
    or establish that a consumer enforces the required refusal/effect boundary.
    """
    vectors = load(root / "conformance" / NAMESPACE / "delivery-vectors.json")
    coverage = set()
    for case in vectors:
        if set(case) != {"name", "format", "settings", "supported_consumer", "expected"}:
            raise ContractError("invalid delivery vector shape")
        mode, settings, supported = case["format"], case["settings"], case["supported_consumer"]
        if mode not in {"json", "env", "shell", "direct-login"} or type(supported) is not bool:
            raise ContractError("invalid delivery vector input")
        if settings not in ({}, {"cli_auth_credentials_store": "file"},
                            {"cli_auth_credentials_store": "keyring"}):
            raise ContractError("invalid delivery vector settings")
        refused = (bool(settings) and mode in {"env", "shell"}) or not supported
        expected = {"diagnostic": "codex_settings_unsupported" if refused else None,
                    "usable_output": not refused, "partial_output": False,
                    "config_write": False, "vendor_execution": False}
        if case["expected"] != expected:
            raise ContractError("delivery expectation differs: " + case["name"])
        coverage.add((mode, bool(settings), supported))
    required = {(mode, nonempty, supported) for mode in ("json", "env", "shell", "direct-login")
                for nonempty in (False, True) for supported in (False, True)}
    if coverage != required:
        raise ContractError("delivery vector coverage differs")


if __name__ == "__main__":
    import validate

    total, negatives = check_corpus(validate.ROOT, validate.load_json, validate.ccj1_bytes,
                                    validate.validate_wire_semantics)
    print(f"carrier cases: {total}/{total}; negatives: {negatives}/{negatives}; runtime: unrun")
