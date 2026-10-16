#!/usr/bin/env python3
"""Bounded publication checker controls, with named narrowing-mutant killers."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import rc7_carriers as carriers
from test_rc7_carriers import CarrierTests, CORPUS, ROOT, validate


# Each mutation admits one previously forbidden class while retaining the gate.
MUTANTS = [
    ("config-wrapper", "make only skills_root optional", "test_config_enclosing_fields_and_old_readers"),
    ("status-wrapper", "make only observations optional", "test_status_enclosing_fields_and_secret_closure"),
    ("v4-settings", "admit empty settings under the old v4 token", "test_compatibility_dispatch_and_v4_ownership"),
    ("losing-contribution", "admit exactly one forbidden losing store contribution", "test_package_authority_and_empty_provenance"),
    ("competing-owner", "admit legacy file payload beside the sole typed payload", "test_single_typed_payload_required_and_agrees"),
    ("missing-transport", "allow file agreement without its required typed payload", "test_single_typed_payload_required_and_agrees"),
    ("muse-parent", "skip only the Muse XDG parent relation", "test_muse_and_other_adapter_boundaries"),
    ("muse-taxonomy", "permit the former native-selector error for explicit keychain", "test_published_muse_decision_table"),
    ("status-version-exception", "permit --version while still forbidding auth status", "test_status_no_agent_execution_published"),
    ("env-shell-file-exception", "allow only file settings through env/shell", "test_renderer_transition_and_cli_published"),
    ("muse-status-native-source", "enforce file candidates only for per-home, admitting shared-native Keychain metadata",
     "test_muse_status_source_backend_regression"),
    ("muse-status-per-home-source", "enforce file candidates only for shared-native, admitting per-home Keychain metadata",
     "test_muse_status_source_backend_regression"),
    ("status-consuming-auth-exception", "permit auth status only in environments.md, retaining the central prohibition and links",
     "test_cross_document_status_boundary_regression"),
    ("status-login-auth-exception", "permit auth status only in login-readiness.md, retaining the central prohibition and links",
     "test_cross_document_status_boundary_regression"),
    ("status-cli-auth-exception", "permit auth status only in cli/curator.md, retaining the central prohibition and links",
     "test_cross_document_status_boundary_regression"),
    ("status-manager-auth-exception", "permit auth status only in profiles/manager.md, retaining the central prohibition and links",
     "test_cross_document_status_boundary_regression"),
]

STATUS_DOCUMENT_MUTANTS = {
    "status-consuming-auth-exception": (
        "protocol/environments.md",
        "Adopting readiness status MUST execute\nno agent binary, including `--version` and `auth status`;",
        "Adopting readiness status MAY execute\nan agent binary for `auth status`;"),
    "status-login-auth-exception": (
        "protocol/login-readiness.md", "Status MUST NOT invoke an agent executable,",
        "Status MAY invoke an agent executable for auth status; it MUST NOT"),
    "status-cli-auth-exception": (
        "cli/curator.md", "Adopting status invokes no agent binary, including\nversion probes and auth status;",
        "Adopting status permits auth status; it invokes no agent binary for\nversion probes;"),
    "status-manager-auth-exception": (
        "profiles/manager.md", "execute no agent binary, including version probes and auth status.",
        "may execute auth status, but execute no agent binary for version probes."),
}


def schema_mutation(mutant, path, value):
    name = path.name
    # Deep copies prevent changes to the on-disk candidate and other controls.
    value = copy.deepcopy(value)
    if mutant == "config-wrapper" and name == "manager-config-v5.schema.json":
        value["required"].remove("skills_root")
    elif mutant == "status-wrapper" and name == "env-status-v1.schema.json":
        value["required"].remove("observations")
    elif mutant == "v4-settings" and name == "launch-env-fragment-v4.schema.json":
        value["properties"]["codex_settings"] = {"type": "object", "maxProperties": 0}
    elif mutant == "losing-contribution" and name == "context-lock-v4.schema.json":
        value["properties"]["codex_settings_contributions"] = {"anyOf": [
            {"type": "array", "maxItems": 0},
            {"const": [{"package": "loser", "settings": {"cli_auth_credentials_store": "file"}}]},
        ]}
    elif mutant == "competing-owner" and name == "launch-env-fragment-v5.schema.json":
        value["properties"]["credential_store"]["properties"]["config_overrides"] = {
            "const": {"cli_auth_credentials_store": "file"}}
    elif mutant == "missing-transport" and name == "launch-env-fragment-v5.schema.json":
        value["allOf"][1]["then"]["allOf"][1]["then"].pop("required")
    return value


def run_mutants():
    original_load, original_text = validate.load_json, Path.read_text
    original_semantics = validate.validate_wire_semantics
    survivors = []
    print("| Mutant | Narrowing | Named failing test | Survivor bound |")
    print("|---|---|---|---|")
    for mutant, narrowing, test_name in MUTANTS:
        document_mutated = False
        def altered_load(path):
            return schema_mutation(mutant, path, original_load(path))

        def altered_text(path, *args, **kwargs):
            nonlocal document_mutated
            text = original_text(path, *args, **kwargs)
            if mutant in STATUS_DOCUMENT_MUTANTS:
                document, old, new = STATUS_DOCUMENT_MUTANTS[mutant]
                if path == ROOT / document:
                    document_mutated = old in text
                    text = text.replace(old, new)
            if path == ROOT / "protocol/rc7-carriers.md":
                if mutant == "muse-taxonomy":
                    text = text.replace("Muse explicit keychain | `environment_credential_store_unsupported`",
                                        "Muse explicit keychain | `environment_credential_unsupported`")
                elif mutant == "status-version-exception":
                    text = text.replace("Adopting readiness status executes no agent binary, including --version or auth status.",
                                        "Adopting readiness status permits --version only; auth status remains forbidden.")
                elif mutant == "env-shell-file-exception":
                    text = text.replace("Nonempty Codex settings refuse with `codex_settings_unsupported`, zero output",
                                        "Only keyring Codex settings refuse with `codex_settings_unsupported`, zero output")
            return text

        def altered_semantics(name, value):
            if mutant == "muse-parent" and name == "launch-env-fragment-v4.schema.json" and value.get("environment") == "muse":
                return None
            return original_semantics(name, value)

        excluded_source = {
            "muse-status-native-source": "native", "muse-status-per-home-source": "per-home",
        }.get(mutant, "")
        sources = carriers.HOME_CREDENTIAL_SOURCES - {excluded_source}
        with patch.object(validate, "load_json", side_effect=altered_load), \
                patch.object(Path, "read_text", new=altered_text), \
                patch.object(validate, "validate_wire_semantics", side_effect=altered_semantics), \
                patch.object(carriers, "HOME_CREDENTIAL_SOURCES", sources):
            result = unittest.TestResult()
            CarrierTests(test_name).run(result)
        # An unrelated exception/setup error is not a killed narrowing mutant.
        killed = len(result.failures) > 0 and not result.errors and not result.skipped
        if mutant in STATUS_DOCUMENT_MUTANTS:
            killed = killed and document_mutated
        if not killed:
            survivors.append(mutant)
        print(f"| {mutant} | {narrowing} | {test_name if killed else 'none'} | "
              f"{'none; killed' if killed else 'UNPROVEN: intended assertion did not fail'} |")
    print(f"Narrowing mutants killed: {len(MUTANTS) - len(survivors)}/{len(MUTANTS)}")
    return int(bool(survivors))


def run_plant():
    # Positive control is required before the production gate consumes the plant.
    validate.validate_rc7_carriers()
    original_load = validate.load_json

    def planted(path):
        value = original_load(path)
        if path == CORPUS / "cases/config-valid.json":
            value["schema_version"] = 3
        return value

    with patch.object(validate, "load_json", side_effect=planted):
        try:
            validate.validate_rc7_carriers()
        except validate.ValidationFailure as exc:
            intended = "config-valid: expected None, got carrier_schema_invalid"
            if intended not in str(exc):
                raise
            print("EXPECTED RED: " + str(exc))
            return 1
    print("SURVIVING PLANT: wrong enclosing config discriminator was admitted")
    return 0


if __name__ == "__main__":
    if sys.argv[1:] not in ([], ["--plant"]):
        raise SystemExit("usage: check_rc7_carrier_controls.py [--plant]")
    raise SystemExit(run_plant() if sys.argv[1:] else run_mutants())
