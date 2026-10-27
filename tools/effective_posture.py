"""Offline effective-posture specification oracle; not the launcher admission gate.

Context is synthetic independently admitted evidence, not a public request or
an authority source. This checks bytes and named relations, never provider
qualification, real inspection, lane grants, filesystem ownership or start.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from ccj1_grammar import integer

LIMIT = 64 * 1024
REQUIRED_PAIRS = {
    "EP01-missing", "EP02-unknown", "EP03-unqualified", "EP04-suffix-policy",
    "EP05-strict-unsupported", "EP06-no-tools-unsupported", "EP07-stale-lock",
    "EP08-stale-plan", "EP09-strict-downgrade", "EP10-permission-downgrade",
    "EP11-tool-downgrade", "EP12-incomplete-policy", "EP13-relaxed-policy",
    "EP14-lane-approval", "EP15-state-substitution", "EP16-terminal-lease",
    "EP17-hosted-missing-lease", "EP18-qualification-provider", "EP19-suffix-digest",
    "EP20-policy-digest", "EP21-source-spoof", "EP22-unknown-qualification",
    "EP23-default-not-native", "EP24-isolation-bypass",
    "EP25-yolo-incomplete-honesty", "EP26-generation-moved",
}


def ccj(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False,
                      sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(ccj(value)).hexdigest()


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("duplicate member")
        result[name] = value
    return result


def _reject_number(token: str) -> Any:
    raise ValueError("non-CCJ-1 number")


def _walk(value: Any, depth: int = 0) -> None:
    if depth > 12:
        raise ValueError("record depth")
    if isinstance(value, str):
        value.encode("utf-8", errors="strict")
    elif type(value) is int and abs(value) > 9007199254740991:
        raise ValueError("unsafe integer")
    elif isinstance(value, dict):
        for key, child in value.items():
            _walk(key, depth + 1)
            _walk(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            _walk(child, depth + 1)


def decode_record(raw: bytes, schema: Draft202012Validator) -> dict[str, Any]:
    if len(raw) > LIMIT:
        raise ValueError("record size")
    value = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=_pairs,
                       parse_int=integer, parse_float=_reject_number,
                       parse_constant=_reject_number)
    _walk(value)
    if ccj(value) != raw:
        raise ValueError("noncanonical record")
    schema.validate(value)
    return value


def validator(root: Path) -> Draft202012Validator:
    doc = json.loads((root / "schemas/effective-posture-v1/record.schema.json").read_text())
    Draft202012Validator.check_schema(doc)
    return Draft202012Validator(doc, format_checker=FormatChecker())


def relation_verdict(case: dict[str, Any], schema: Draft202012Validator) -> str:
    """Named relation oracle over fixture authority; no runtime/route graph model."""
    if "posture" not in case:
        return "posture_missing"
    try:
        p = decode_record(ccj(case["posture"]), schema)
    except (ValueError, UnicodeError, RecursionError, ValidationError):
        return "posture_invalid"
    c = case["context"]
    project = p["project"]
    requested = project["requested"]
    mode = "strict" if requested["strict"] else "native-project" if requested["native_project"] else "none"
    if (project["mode"] != mode or project["no_tools"] != requested["no_tools"]
            or project != c["resolved_project"] or p["permission"] != c["resolved_permission"]):
        return "posture_downgrade"
    if p["permission"]["source"] == "default" and p["permission"]["mode"] != "yolo":
        return "posture_default_conflict"
    if mode != "none" and p["permission"]["mode"] == "yolo":
        return "posture_isolation_bypass"
    if p["binding"] != c["current_binding"]:
        return "posture_binding_stale"
    if p["native_suffix"]["sha256"] != digest(p["native_suffix"]["argv"]):
        return "posture_suffix_changed"
    if p["native_policy"] != c["native_policy"]:
        return "posture_policy_changed"
    q = c["qualification"]
    if p["qualification"]["state"] != "qualified" or q["state"] != "qualified":
        return "posture_unqualified"
    if (p["qualification"]["id"] != q["id"] or p["qualification"]["sha256"] != digest(q)
            or p["provider"] != c["provider"] or p["provider"] != q["provider"]):
        return "posture_qualification_mismatch"
    if mode not in q["project_modes"]:
        return "posture_strict_unsupported" if mode == "strict" else "posture_mode_unsupported"
    if project["no_tools"] and not q["no_tools"]:
        return "posture_no_tools_unsupported"
    policy = p["native_policy"]
    if (policy["inspection"] == "unsupported"
            or policy["inspection"] == "complete" and policy["uninspected_sources"]
            or p["permission"]["mode"] == "native" and (
                policy["inspection"] != "complete" or policy["uninspected_sources"])):
        return "posture_policy_uninspected"
    if p["permission"]["mode"] == "native" and policy["relaxations"]:
        return "posture_policy_relaxed"
    if not c["lane"]["approved"] or c["lane"]["permissions"] != p["permission"]["mode"]:
        return "posture_lane_unapproved"
    if p["native_suffix"]["argv"] not in q["policy_free_suffixes"]:
        return "posture_suffix_conflict"
    provenance = p["provenance"]
    state = c["launcher_state"]
    if (state["record"] != "launcher-path-state/1" or state["launch_id"] != provenance["launch_id"]
            or state["binding"] != p["binding"]
            or digest(state) != provenance["launcher_state"]["sha256"]):
        return "posture_provenance_mismatch"
    lease = c["home_lease"]
    ref = provenance["home_lease"]
    if provenance["route"] == "native":
        return "admit" if lease is None else "posture_provenance_mismatch"
    if lease is None or lease["phase"] != "prepared" or lease["holder"]["kind"] != "prepared":
        return "posture_lease_unavailable"
    if (lease["kind"] != ref["record"] or digest(lease) != ref["record_sha256"]
            or any(lease[k] != ref[k] for k in ("lease_id", "revision", "manager_root_id", "home_id"))
            or any(lease["holder"][k] != ref[k] for k in ("request_id", "manager_id", "manager_registered_at"))
            or lease["profile"] != p["binding"]["profile"]
            or "sha256:" + lease["lock_sha256"] != p["binding"]["lock_sha256"]
            or lease["environment"] != p["provider"]["environment"]):
        return "posture_provenance_mismatch"
    return "admit"


def materialize(fixtures: dict[str, Any], branch: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(fixtures[branch["fixture"]])
    for change in branch["changes"]:
        target = value
        for key in change["path"][:-1]:
            target = target[key]
        key = change["path"][-1]
        if change["op"] == "remove":
            del target[key]
        elif change["op"] == "replace":
            if key not in target:
                raise ValueError("replacement target absent")
            target[key] = copy.deepcopy(change["value"])
        else:
            raise ValueError("unknown fixture mutation")
    return value


def check_pairs(fixtures: dict[str, Any], pairs: list[dict[str, Any]], schema: Draft202012Validator) -> None:
    identifiers = [pair["id"] for pair in pairs]
    if set(identifiers) != REQUIRED_PAIRS or len(identifiers) != len(REQUIRED_PAIRS):
        raise ValueError("pair coverage mismatch")
    if {p["requirement"] for p in pairs} != {"EPA01", "EPA02", "EPA03", "EPA04", "EPA05", "EPA06", "EPA-C1"}:
        raise ValueError("obligation coverage mismatch")
    for pair in pairs:
        for side in ("admit", "refuse"):
            if side not in pair:
                raise ValueError("missing paired control: " + pair["id"])
            branch = pair[side]
            if side == "admit" and branch["expected"] != "admit":
                raise ValueError("positive must admit")
            if side == "refuse" and not branch["expected"].startswith("posture_"):
                raise ValueError("negative must name refusal")
            observed = relation_verdict(materialize(fixtures, branch), schema)
            if observed != branch["expected"]:
                raise ValueError(f"{side} mismatch {pair['id']}: {observed}, expected {branch['expected']}")


def check_corpus(root: Path) -> int:
    suite = root / "conformance/effective-posture-v1"
    fixtures = json.loads((suite / "fixtures.json").read_text())["fixtures"]
    cases = json.loads((suite / "cases.json").read_text())
    if cases["kind"] != "effective-posture-pairs/1":
        raise ValueError("corpus kind")
    check_pairs(fixtures, cases["pairs"], validator(root))
    golden = (suite / "default-yolo.ccj").read_bytes()
    identity = json.loads((suite / "golden.json").read_text())
    p = decode_record(golden, validator(root))
    if p != fixtures[identity["fixture"]]["posture"] or digest(p) != identity["posture_sha256"] or len(golden) != identity["size_bytes"]:
        raise ValueError("golden identity mismatch")
    return len(cases["pairs"])


if __name__ == "__main__":
    count = check_corpus(Path(__file__).resolve().parents[1])
    print(f"effective posture: {count} paired specification relations; runtime and qualification unverified")
