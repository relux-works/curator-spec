"""Bounded executable model for the environments §9.1 host-classification vectors.

Only HTTP(S) URL fixtures are extracted here. This is a specification checker,
not a production source-code detector or an implementation conformance claim.
"""

from __future__ import annotations

import fnmatch
import json
from pathlib import Path
import re
from urllib.parse import urlsplit


VECTOR = Path(__file__).resolve().parents[1] / "conformance/context-detectors/network-contacts.json"
RESERVED_LABELS = frozenset({"test", "example", "invalid", "localhost"})
REQUIRED_CASES = frozenset({
    "loopback-localhost", "loopback-ipv4", "loopback-ipv6", "loopback-case-dot",
    "reserved-test", "reserved-example", "reserved-invalid", "reserved-localhost",
    "reserved-nested", "reserved-case-dot", "reserved-idn", "reserved-punycode",
    "lookalike-nested-test", "lookalike-nested-example", "lookalike-hyphen",
    "bare-test", "bare-example", "bare-invalid", "bare-test-dot",
    "lookalike-idn-label", "lookalike-punycode-label", "lookalike-idn-real-tld",
    "lookalike-case-dot", "documentation-com", "documentation-net", "documentation-org",
    "documentation-subdomain-com", "documentation-subdomain-net", "documentation-subdomain-org",
    "documentation-case-dot", "canary-undeclared", "canary-declared",
    "mixed-reserved-first", "mixed-real-first", "mixed-cross-file",
    "declared-exact", "declared-glob", "declared-other-host", "missing-manifest",
    "missing-network-declaration",
})


def normalize_host(host: str) -> str:
    """Normalize an already detected host; URL brackets/ports are not host bytes."""
    ascii_host = host.encode("idna").decode("ascii").lower()
    return ascii_host.removesuffix(".")


def is_network_contact(host: str) -> bool:
    host = normalize_host(host)
    if host in {"localhost", "127.0.0.1", "::1"}:
        return False
    labels = host.split(".")
    return not (len(labels) > 1 and labels[-1] in RESERVED_LABELS)


def evaluate(case: dict) -> dict:
    findings = []
    canary = False
    network = case.get("manifest", {}).get("capabilities", {}).get("network", "none")
    globs = network if isinstance(network, list) else []
    for file, text in sorted(case["files"].items()):
        for match in re.finditer(r"https?://[^\s]+", text):
            host = urlsplit(match.group()).hostname
            if host is None:
                raise ValueError(f"{case['name']}: URL fixture lacks a host")
            normalized = normalize_host(host)
            # This fixed canary fixture remains independent of capability declarations.
            canary |= normalized == "exfiltrate.example.com"
            if is_network_contact(host) and not any(
                fnmatch.fnmatchcase(normalized, glob) for glob in globs
            ):
                findings.append({
                    "class": "audit.capability.network-undeclared",
                    "host": normalized, "file": file,
                })
    return {
        "findings": findings,
        "capability_check_passes": not findings,
        "static_canary_blocks": canary,
    }


def load_vectors() -> dict:
    return json.loads(VECTOR.read_text(encoding="utf-8"))


def validate(vector: dict | None = None) -> int:
    vector = load_vectors() if vector is None else vector
    if (vector.get("schema_version") != 1
            or vector.get("capability") != "agent-environments"
            or vector.get("capability_revision") != 1):
        raise ValueError("network contact corpus identity mismatch")
    cases = vector["cases"]
    if len(cases) != len(REQUIRED_CASES) or {c["name"] for c in cases} != REQUIRED_CASES:
        raise ValueError("network contact case inventory mismatch")
    for case in cases:
        actual = evaluate(case)
        if actual != case["expected"]:
            raise ValueError(f"{case['name']}: expected {case['expected']!r}; actual {actual!r}")
    return len(cases)


if __name__ == "__main__":
    print(f"network contact vectors: {validate()} passed; manager runtime: unverified")
