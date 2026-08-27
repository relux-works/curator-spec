"""Reproduce review-cycle-2 finding R2-1 against the real hardened schemas."""
import json, sys
sys.path.insert(0, "tools")
from validate_hardened import HARDENED_SUITE, load_json, validator_for

receipt = load_json(HARDENED_SUITE / "schema-cases" / "hardened-build-receipt-v3" / "valid.json")
claim = load_json(HARDENED_SUITE / "schema-cases" / "hardened-conformance-claim-v4" / "valid.json")
rv = validator_for("hardened-build-receipt-v3.schema.json")
cv = validator_for("hardened-conformance-claim-v4.schema.json")


def errs(v, doc):
    return len(list(v.iter_errors(doc)))


mismatched = json.loads(json.dumps(receipt))
mismatched["tcb"]["enforcement_backend"] = "linux-namespace-seccomp-v1"
print("platform/backend mismatch receipt errors =", errs(rv, mismatched))

target = json.loads(json.dumps(receipt))
target["tcb"]["platform"] = "linux"
target["tcb"]["enforcement_backend"] = "linux-namespace-seccomp-v1"
print("darwin target with linux TCB receipt errors =", errs(rv, target))

interpreter = json.loads(json.dumps(receipt))
interpreter["tcb"]["additional_trusted_components"] = ["mutable-interpreter-with-no-cryptographic-identity"]
print("uncryptographic trusted component receipt errors =", errs(rv, interpreter))

noparent = json.loads(json.dumps(receipt))
print("manager parent identity present in TCB =", "parent_sha256" in noparent["tcb"])
print("host OS/hypervisor identity present in TCB =", any(k in noparent["tcb"] for k in ("host", "operating_system", "hypervisor")))
print("backend version present in TCB =", any(k in noparent["tcb"] for k in ("backend", "enforcement_backend_version")))

winclaim = json.loads(json.dumps(claim))
winclaim["tcb"]["platform"] = "macos"
winclaim["tcb"]["enforcement_backend"] = "windows-appcontainer-job-v1"
print("macos TCB with windows backend claim errors =", errs(cv, winclaim))
