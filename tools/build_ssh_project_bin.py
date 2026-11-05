"""Validate the draft SSH and project ownership witnesses against their rules."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1] / "conformance/draft-build-ssh-project-bin"

def require(condition, reason):
    if not condition:
        raise ValueError(reason)

def validate_ssh(v):
    require(v["selection_order"] == ["operator-absolute", "fixed-system-list"] and v["inherited_path"] is False, "SSH selection must ignore inherited PATH")
    require(set(v["forbidden_roots"]) == {"project-bin", "manager-bin", "managed-command-root"}, "managed roots must refuse")
    require(v["fingerprint"] == "sha256", "executable fingerprint required")
    require(v["tuple"] == ["argc", "argv[0]", "host", "remote-command"], "complete four-value tuple required")
    require(v["mandatory_option"] == "EscapeChar=none" and v["unsupported_option"] == "EnableEscapeCommandline=no", "OpenSSH 8.9 escape isolation required")
    require(v["unix_policy"] == "read-only-descriptor" and v["windows_policy"] == "current-user-only-protected-record", "protected policy transport required")
    require({c["condition"] for c in v["cases"]} == {"valid", "no-credentials", "no-host-keys", "auth", "host-key"}, "SSH positive and refusal controls required")
    for c in v["cases"]:
        expected = None if c["condition"] == "valid" else ("build_repository_ssh_credential_missing" if c["condition"] == "no-credentials" else "build_repository_credential_policy_invalid")
        require(c["code"] == expected and c["snapshot"] == (expected is None), "credential refusal and snapshot mapping")
        reason = {"auth": "authentication_failed", "host-key": "host_key_verification_failed"}.get(c["condition"])
        require(c.get("reason") == reason, "static authentication and host-key reasons differ")

def validate_ownership(v):
    require(v["ledger"] == ".agents/.curator-bin-ownership.json", "project ledger location required")
    require(v["preflight_before_build"] is True, "ownership refusal must precede build")
    require(v["unrelated_foreign_opened"] is False, "unrelated foreign file must not be opened")
    require({c["name"] for c in v["cases"]} == {"legacy-adopt", "legacy-remove", "sidecar-mismatch", "marker-absent"}, "legacy positive and refusal controls required")
    for c in v["cases"]:
        adopt = c["marker"] and c["enforced"] and c["sidecar_matches"]
        require(c["code"] == (None if adopt else "project_bin_legacy_enforced"), "legacy enforcement evidence refusal required")
        require(c["mutated"] == adopt and c["pair_removed"] == (adopt and not c["desired"]), "legacy refusal preserves state and removal deletes pair")

def validate():
    validate_ssh(json.loads((ROOT / "ssh-policy.json").read_text()))
    validate_ownership(json.loads((ROOT / "project-bin.json").read_text()))

if __name__ == "__main__":
    validate()
    print("validated draft SSH and project ownership vectors")
