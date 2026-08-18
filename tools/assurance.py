"""Executable relational validation for the rc.8 assurance evidence chain."""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime
from typing import Any


VERIFIED_CAPABILITIES = [
    "total-network-denial-v1",
    "read-only-source-and-toolchain-v1",
    "exact-executable-allowlisting-v1",
    "private-build-root-only-writes-v1",
    "hard-aggregate-descendant-resource-bounds-v1",
    "fail-closed-capability-preflight-v1",
]


def ccj1_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _provider_error(expected: Any, actual: Any) -> str | None:
    if not isinstance(expected, dict) or not isinstance(actual, dict):
        return "verified_provider_identity_invalid"
    if actual.get("provider_contract") != expected.get("provider_contract"):
        return "verified_provider_unavailable"
    if (
        actual.get("provider_id") != expected.get("provider_id")
        or actual.get("provider_binary_sha256")
        != expected.get("provider_binary_sha256")
        or actual.get("provider_version") != expected.get("provider_version")
        or actual.get("operating_system") != expected.get("operating_system")
    ):
        return "verified_provider_identity_invalid"
    return None


def validate_flow(flow: Any) -> str | None:
    """Return the stable rejection code for a relational mismatch, or None."""
    if not isinstance(flow, dict):
        return "assurance_evidence_mismatch"
    if flow.get("fallback_mode") is not None:
        return "assurance_evidence_mismatch"
    if (
        flow.get("selected_mode") != "verified"
        or flow.get("policy_id") != "verified-provider-policy-v1"
        or flow.get("execution_policy") != "verified-provider-execution-v1"
    ):
        return "assurance_evidence_mismatch"

    provider = flow.get("provider")
    if not isinstance(provider, dict):
        return "verified_provider_identity_invalid"
    if provider.get("provider_contract") != "host-execution-provider-v1":
        return "verified_provider_unavailable"

    capability_receipt = flow.get("capability_receipt")
    if not isinstance(capability_receipt, dict):
        return "verified_capabilities_unsatisfied"
    provider_error = _provider_error(provider, capability_receipt.get("provider"))
    if provider_error is not None:
        return provider_error
    capabilities = capability_receipt.get("capabilities")
    expected_capabilities = [
        {"capability_id": capability_id, "status": "established"}
        for capability_id in VERIFIED_CAPABILITIES
    ]
    if capabilities != expected_capabilities or capability_receipt.get("health") != "healthy":
        return "verified_capabilities_unsatisfied"

    observed_at = parse_timestamp(capability_receipt.get("observed_at"))
    expires_at = parse_timestamp(capability_receipt.get("expires_at"))
    validation_time = parse_timestamp(flow.get("validation_time"))
    if (
        observed_at is None
        or expires_at is None
        or validation_time is None
        or observed_at >= expires_at
        or validation_time < observed_at
        or validation_time >= expires_at
    ):
        return "verified_capabilities_unsatisfied"

    capability_receipt_sha256 = ccj1_sha256(capability_receipt)
    permit = flow.get("permit")
    cache = flow.get("cache")
    if not isinstance(permit, dict) or not isinstance(cache, dict):
        return "verified_permit_invalid"
    if (
        permit.get("capability_receipt_sha256") != capability_receipt_sha256
        or cache.get("input", {}).get("capability_receipt_sha256")
        != capability_receipt_sha256
    ):
        return "verified_capabilities_unsatisfied"
    if capability_receipt.get("nonce") != permit.get("nonce"):
        return "verified_permit_invalid"
    provider_error = _provider_error(provider, permit.get("provider"))
    if provider_error is not None:
        return provider_error
    permit_expires_at = parse_timestamp(permit.get("expires_at"))
    if permit_expires_at is None or validation_time >= permit_expires_at:
        return "verified_permit_invalid"
    if (
        permit.get("policy_id") != flow.get("policy_id")
        or permit.get("execution_policy") != flow.get("execution_policy")
        or permit.get("operation_id") != flow.get("operation_id")
        or permit.get("build_input_sha256") != flow.get("build_input_sha256")
    ):
        return "verified_permit_invalid"

    cache_input = cache.get("input", {})
    if not isinstance(cache_input, dict):
        return "assurance_evidence_mismatch"
    if (
        cache.get("expected_key") != ccj1_sha256(cache_input)
        or cache_input.get("cache_identity") != "verified-cache-identity-v1"
        or cache_input.get("policy_id") != flow.get("policy_id")
        or cache_input.get("execution_policy") != flow.get("execution_policy")
        or cache_input.get("provider_contract") != provider.get("provider_contract")
        or cache_input.get("provider_id") != provider.get("provider_id")
        or cache_input.get("provider_binary_sha256")
        != provider.get("provider_binary_sha256")
        or cache_input.get("build_input_sha256") != flow.get("build_input_sha256")
    ):
        return "assurance_evidence_mismatch"

    receipt = flow.get("execution_receipt")
    if not isinstance(receipt, dict):
        return "verified_execution_receipt_invalid"
    provider_error = _provider_error(provider, receipt.get("provider"))
    if provider_error is not None:
        return provider_error
    if (
        receipt.get("policy_id") != flow.get("policy_id")
        or receipt.get("execution_policy") != flow.get("execution_policy")
        or receipt.get("operation_id") != flow.get("operation_id")
        or receipt.get("capability_receipt_sha256") != capability_receipt_sha256
        or receipt.get("permit_sha256") != ccj1_sha256(permit)
        or receipt.get("build_input_sha256") != flow.get("build_input_sha256")
        or receipt.get("artifact_sha256") != flow.get("artifact_sha256")
    ):
        return "verified_execution_receipt_invalid"
    started_at = parse_timestamp(receipt.get("started_at"))
    completed_at = parse_timestamp(receipt.get("completed_at"))
    if started_at is None or completed_at is None or started_at > completed_at:
        return "verified_execution_receipt_invalid"

    checkpoints = flow.get("checkpoints")
    if not isinstance(checkpoints, list) or len(checkpoints) != 3:
        return "verified_checkpoint_invalid"
    phases = ["permit-issued", "execution-started", "execution-succeeded"]
    previous_digest: str | None = None
    permit_sha256 = ccj1_sha256(permit)
    for index, checkpoint in enumerate(checkpoints):
        if not isinstance(checkpoint, dict):
            return "verified_checkpoint_invalid"
        provider_error = _provider_error(provider, checkpoint.get("provider"))
        if provider_error is not None:
            return "verified_checkpoint_invalid"
        if (
            checkpoint.get("checkpoint_type") != "verified-execution-checkpoint-v1"
            or checkpoint.get("phase") != phases[index]
            or checkpoint.get("previous_checkpoint_sha256") != previous_digest
            or checkpoint.get("operation_id") != flow.get("operation_id")
            or checkpoint.get("capability_receipt_sha256")
            != capability_receipt_sha256
            or checkpoint.get("permit_sha256") != permit_sha256
        ):
            return "verified_checkpoint_invalid"
        previous_digest = ccj1_sha256(checkpoint)
    return None


def apply_mutation(flow: Any, mutation: Any) -> Any:
    """Apply one generated path mutation to a copy of the valid flow."""
    candidate = copy.deepcopy(flow)
    if not isinstance(mutation, dict) or not isinstance(mutation.get("path"), list):
        raise ValueError("invalid assurance mutation")
    path = mutation["path"]
    if not path:
        raise ValueError("empty assurance mutation path")
    parent: Any = candidate
    for component in path[:-1]:
        parent = parent[component]
    parent[path[-1]] = copy.deepcopy(mutation.get("value"))
    return candidate
