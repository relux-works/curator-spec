from __future__ import annotations

import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import shlex
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).with_name("validate.py")
SPEC = importlib.util.spec_from_file_location("curator_spec_validate", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
validate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validate)


def swapped(values: list, first: int, second: int) -> list:
    result = list(values)
    result[first], result[second] = result[second], result[first]
    return result


class SchemaRegistryCacheTests(unittest.TestCase):
    def test_schema_documents_are_cached_by_content_and_changes_are_rechecked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            schema_dir = Path(directory)
            schema_path = schema_dir / "cache-test.schema.json"
            schema = {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$id": f"urn:cache-test:{schema_dir.name}",
                "type": "object",
            }
            schema_path.write_text(json.dumps(schema), encoding="utf-8")
            check_schema = validate.Draft202012Validator.check_schema

            with patch.object(validate, "SCHEMAS", schema_dir), patch.object(
                validate.Draft202012Validator,
                "check_schema",
                wraps=check_schema,
            ) as checked:
                validate.schema_registry()
                validate.schema_registry()
                self.assertEqual(checked.call_count, 1)

                schema["type"] = "unknown-json-schema-type"
                schema_path.write_text(json.dumps(schema), encoding="utf-8")
                with self.assertRaises(validate.ValidationFailure):
                    validate.schema_registry()
                self.assertEqual(checked.call_count, 2)


class WireSemanticValidationTests(unittest.TestCase):
    def test_manifest_requires_exact_declared_repository_selection(self) -> None:
        valid = {
            "schema_version": 7,
            "build_repositories": {"repo": {}},
            "commands": {
                "tool": {
                    "type": "build",
                    "driver": "go-repository-v1",
                    "repository": "repo",
                    "target": "tool",
                }
            },
        }
        self.assertIsNone(
            validate.validate_wire_semantics("agent-skill-v7.schema.json", valid)
        )
        missing = copy.deepcopy(valid)
        missing["commands"]["tool"]["repository"] = "missing"
        self.assertIn(
            "undeclared",
            validate.validate_wire_semantics(
                "agent-skill-v7.schema.json", missing
            ),
        )
        unused = copy.deepcopy(valid)
        unused["build_repositories"]["unused"] = {}
        self.assertIn(
            "must be selected",
            validate.validate_wire_semantics(
                "agent-skill-v7.schema.json", unused
            ),
        )

    def test_legacy_manifest_version_selection_rejects_v7_surface(self) -> None:
        reserved_instances = [
            {"build_repositories": {}},
            {"repository": "repo"},
            {"target": "tool"},
            {"driver": "go-repository-v1"},
            {"commands": {"tool": {"repository": "repo"}}},
            {"commands": {"tool": {"target": "tool"}}},
            {"commands": {"tool": {"driver": "go-repository-v1"}}},
        ]
        for prefix in ("agent-skill", "csk-skill"):
            for version in range(1, 7):
                for reserved in reserved_instances:
                    instance = {"schema_version": version, **copy.deepcopy(reserved)}
                    error = validate.validate_wire_semantics(
                        f"{prefix}-v{version}.schema.json", instance
                    )
                    self.assertIn("only in manifest schema 7", error)

    def test_pre_schema8_manifests_reject_script_execution_surface(self) -> None:
        reserved_instances = [
            {"execution_policy": "script-worker-v1"},
            {"interpreter": "python3-v1"},
            {"commands": {"tool": {"execution_policy": "script-worker-v1"}}},
            {"commands": {"tool": {"interpreter": "python3-v1"}}},
        ]
        for prefix in ("agent-skill", "csk-skill"):
            for version in range(1, 8):
                for reserved in reserved_instances:
                    instance = {"schema_version": version, **copy.deepcopy(reserved)}
                    error = validate.validate_wire_semantics(
                        f"{prefix}-v{version}.schema.json", instance
                    )
                    self.assertIn("only in manifest schema 8", error)

    def test_pre_schema8_manifests_reject_module_roots_surface(self) -> None:
        reserved_instances = [
            {"modules": ["pkg/lib"]},
            {"commands": {"tool": {"modules": ["pkg/lib"]}}},
        ]
        for prefix in ("agent-skill", "csk-skill"):
            for version in range(1, 8):
                for reserved in reserved_instances:
                    instance = {"schema_version": version, **copy.deepcopy(reserved)}
                    error = validate.validate_wire_semantics(
                        f"{prefix}-v{version}.schema.json", instance
                    )
                    self.assertIn("only in manifest schema 8", error)

    def test_schema8_admits_enforced_scripts_and_keeps_schema7_rules(self) -> None:
        enforced = {
            "schema_version": 8,
            "capabilities": {},
            "commands": {
                "enforced-tool": {
                    "type": "script",
                    "unix_path": "scripts/enforced",
                    "execution_policy": "script-worker-v1",
                    "interpreter": "python3-v1",
                },
                "declared-tool": {"type": "script", "unix_path": "scripts/declared"},
                "build-tool": {
                    "type": "build",
                    "driver": "go-v1",
                    "source_dir": "build/cmd/tool",
                    "modules": ["pkg/board", "pkg/remoteconfig"],
                },
            },
            "build_roots": ["build"],
        }
        for prefix in ("agent-skill", "csk-skill"):
            self.assertIsNone(
                validate.validate_wire_semantics(
                    f"{prefix}-v8.schema.json", enforced
                )
            )
        with_repository = copy.deepcopy(enforced)
        with_repository["build_repositories"] = {"repo": {}}
        with_repository["commands"]["golden-tool"] = {
            "type": "build",
            "driver": "go-repository-v1",
            "repository": "repo",
            "target": "golden-tool",
        }
        self.assertIsNone(
            validate.validate_wire_semantics(
                "agent-skill-v8.schema.json", with_repository
            )
        )
        unused = copy.deepcopy(with_repository)
        unused["build_repositories"]["unused"] = {}
        self.assertIn(
            "must be selected",
            validate.validate_wire_semantics("agent-skill-v8.schema.json", unused),
        )
        missing = copy.deepcopy(with_repository)
        missing["commands"]["golden-tool"]["repository"] = "missing"
        self.assertIn(
            "undeclared",
            validate.validate_wire_semantics("agent-skill-v8.schema.json", missing),
        )

    def test_external_repository_transport_and_ref_grammar(self) -> None:
        valid_sources = [
            "https://example.com/组织/工具.git",
            "ssh://git@example.com/org/repo.git",
            "git@example.com:org/repo.git",
        ]
        for source in valid_sources:
            self.assertIsNone(validate.validate_repository_git(source), source)

        invalid_sources = [
            "https://example.com/org/../repo.git",
            "ssh://git@example.com/./repo.git",
            "git@example.com:org/../repo.git",
            "git@example.com:repo;touch",
            "ssh://git@example.com/répo.git",
        ]
        for source in invalid_sources:
            self.assertIsNotNone(validate.validate_repository_git(source), source)

        self.assertIsNone(validate.validate_git_ref_name("界" * 85))
        self.assertIn("255 UTF-8 bytes", validate.validate_git_ref_name("a" * 256))
        self.assertIn("255 UTF-8 bytes", validate.validate_git_ref_name("界" * 100))

    def test_canonical_identity_and_structured_revision_width(self) -> None:
        self.assertIsNone(
            validate.validate_network_identity(
                {"kind": "network-git", "value": "example.com/Org/repo.GIT"},
                "https",
            )
        )
        for value in (
            "Example.com/org/repo",
            "example.com/org/../repo",
            "example.com/org/repo.git",
        ):
            self.assertIsNotNone(
                validate.validate_network_identity(
                    {"kind": "network-git", "value": value}, "https"
                ),
                value,
            )
        self.assertIsNone(
            validate.validate_structured_ref(
                {"kind": "revision", "value": "a" * 40}, "sha1"
            )
        )
        self.assertIn(
            "effective sha1",
            validate.validate_structured_ref(
                {"kind": "revision", "value": "a" * 64}, "sha1"
            ),
        )
        self.assertIn(
            "effective sha256",
            validate.validate_structured_ref(
                {"kind": "revision", "value": "a" * 40}, "sha256"
            ),
        )

    def test_descriptor_and_receipt_containment(self) -> None:
        descriptor = {
            "targets": {
                "tool": {
                    "build_root": "tools/admin",
                    "source_dir": "tools/admin/cmd/tool",
                }
            }
        }
        self.assertIsNone(
            validate.validate_wire_semantics(
                "skill-build-v1.schema.json", descriptor
            )
        )
        descriptor["targets"]["tool"]["source_dir"] = "cmd/tool"
        self.assertIn(
            "below build_root",
            validate.validate_wire_semantics(
                "skill-build-v1.schema.json", descriptor
            ),
        )

    def test_unsubstituted_receipt_keeps_declared_and_effective_equal(self) -> None:
        receipt = {
            "input": {
                "build_root": ".",
                "source_dir": "cmd/tool",
                "source": {
                    "declared": {
                        "identity": {"kind": "network-git", "value": "example/repo"},
                        "transport": "https",
                        "locked_commit": {
                            "object_format": "sha1",
                            "hex": "0" * 40,
                        },
                    },
                    "effective": {
                        "identity": {"kind": "network-git", "value": "example/repo"},
                        "transport": "https",
                        "object_format": "sha1",
                        "commit": "0" * 40,
                        "substituted": False,
                    },
                },
            }
        }
        self.assertIsNone(
            validate.validate_wire_semantics(
                "build-receipt-v2.schema.json", receipt
            )
        )
        receipt["input"]["source"]["effective"]["commit"] = "1" * 40
        self.assertIn(
            "must equal declared",
            validate.validate_wire_semantics(
                "build-receipt-v2.schema.json", receipt
            ),
        )

    def test_marker_v4_records_schema8_installations_under_v3_rules(self) -> None:
        marker = {
            "builds": {
                "local": {"driver": "go-v1"},
                "external": {"driver": "go-repository-v1"},
            },
            "build_source": {},
        }
        self.assertIsNone(
            validate.validate_wire_semantics(
                "install-marker-v4.schema.json", marker
            )
        )
        del marker["build_source"]
        self.assertIn(
            "exactly when",
            validate.validate_wire_semantics(
                "install-marker-v4.schema.json", marker
            ),
        )
        v3 = validate.load_json(
            validate.ROOT / "schemas" / "v1" / "install-marker-v3.schema.json"
        )
        v4 = validate.load_json(
            validate.ROOT / "schemas" / "v1" / "install-marker-v4.schema.json"
        )
        self.assertEqual(v3["properties"]["skill_schema_version"], {"const": 7})
        self.assertEqual(v4["properties"]["skill_schema_version"], {"const": 8})
        self.assertEqual(v4["properties"]["schema_version"], {"const": 4})
        for schema in (v3, v4):
            schema.pop("$id")
            schema.pop("title")
            schema["properties"].pop("schema_version")
            schema["properties"].pop("skill_schema_version")
        self.assertEqual(v3, v4)

    def test_marker_and_claim_conditionals(self) -> None:
        marker = {
            "builds": {
                "local": {"driver": "go-v1"},
                "external": {"driver": "go-repository-v1"},
            },
            "build_source": {},
        }
        self.assertIsNone(
            validate.validate_wire_semantics(
                "install-marker-v3.schema.json", marker
            )
        )
        del marker["build_source"]
        self.assertIn(
            "exactly when",
            validate.validate_wire_semantics(
                "install-marker-v3.schema.json", marker
            ),
        )

        claim = {
            "operating_systems": ["macos"],
            "build_drivers": [
                {
                    "driver": "go-repository-v1",
                    "language": "go",
                    "operating_systems": ["windows"],
                }
            ],
        }
        self.assertIn(
            "subset",
            validate.validate_wire_semantics(
                "conformance-claim-v3.schema.json", claim
            ),
        )

        linux = copy.deepcopy(claim)
        linux["operating_systems"] = ["linux"]
        linux["build_drivers"][0]["operating_systems"] = ["linux"]
        self.assertIn(
            "TASK-260728-1skseh",
            validate.validate_wire_semantics(
                "conformance-claim-v3.schema.json", linux
            ),
        )

    def test_external_receipt_and_marker_hashes_are_ccj1_derived(self) -> None:
        expected = (
            validate.SUITE / "expected" / "external-repository"
        )
        receipt = validate.load_json(expected / "build-receipt-v2.json")
        marker = validate.load_json(expected / "install-marker-v3-mixed.json")
        plan = validate.load_json(expected / "mixed-build-plan.json")
        cache_key = validate.ccj1_sha256(receipt["input"])
        receipt_hash = validate.ccj1_sha256(receipt)
        external = marker["builds"]["golden-tool"]
        plan_external = next(
            command for command in plan["commands"] if command["name"] == "golden-tool"
        )
        self.assertEqual(receipt["cache_key"], cache_key)
        self.assertEqual(external["cache_key"], cache_key)
        self.assertEqual(external["receipt_sha256"], receipt_hash)
        self.assertEqual(plan_external["cache_key"], cache_key)
        self.assertEqual(plan_external["receipt_sha256"], receipt_hash)

        bad_receipt = copy.deepcopy(receipt)
        bad_receipt["cache_key"] = "sha256:" + "0" * 64
        self.assertIn(
            "SHA-256(CCJ-1(input))",
            validate.validate_wire_semantics(
                "build-receipt-v2.schema.json", bad_receipt
            ),
        )
        bad_marker = copy.deepcopy(marker)
        bad_marker["builds"]["golden-tool"]["receipt_sha256"] = (
            "sha256:" + "0" * 64
        )
        with self.assertRaisesRegex(
            validate.ValidationFailure,
            "exact generated receipt hashes",
        ):
            validate.validate_external_receipt_oracles(
                receipt, bad_marker, plan
            )

    def test_local_go_receipt_binds_the_portable_execution_policy(self) -> None:
        receipt = validate.load_json(
            validate.SUITE / "schema-cases" / "build-receipt-v1" / "valid.json"
        )
        self.assertEqual(
            receipt["input"]["policy"]["execution_policy"],
            validate.PORTABLE_EXECUTION_POLICY,
        )
        self.assertEqual(receipt["cache_key"], validate.ccj1_sha256(receipt["input"]))
        self.assertNotEqual(receipt["cache_key"], validate.LEGACY_RC4_GO_V1_CACHE_KEY)

        false_key = copy.deepcopy(receipt)
        false_key["cache_key"] = "sha256:" + "0" * 64
        self.assertIn(
            "SHA-256(CCJ-1(input))",
            validate.validate_wire_semantics(
                "build-receipt-v1.schema.json", false_key
            ),
        )
        hardened = copy.deepcopy(receipt)
        hardened["input"]["policy"]["execution_policy"] = (
            validate.RESERVED_HARDENED_EXECUTION_POLICY
        )
        hardened["cache_key"] = validate.ccj1_sha256(hardened["input"])
        self.assertIn(
            validate.PORTABLE_EXECUTION_POLICY,
            validate.validate_wire_semantics(
                "build-receipt-v1.schema.json", hardened
            ),
        )

    def test_execution_policy_revision_cannot_alias_earlier_candidates(self) -> None:
        vector = validate.load_json(
            validate.SUITE / "vectors" / "go-host-execution-policy.json"
        )
        identities = vector["cache_identity"]
        keys = {
            name: validate.ccj1_sha256(identities[name]["input"])
            for name in (
                "portable",
                "reserved_hardened",
                "legacy_rc4_without_execution_policy",
            )
        }
        self.assertEqual(len(set(keys.values())), 3)
        for name, key in keys.items():
            self.assertEqual(identities[name]["cache_key"], key)
        self.assertEqual(
            keys["legacy_rc4_without_execution_policy"],
            validate.LEGACY_RC4_GO_V1_CACHE_KEY,
        )

    def test_script_execution_vector_rejects_contract_drift(self) -> None:
        vector = validate.load_json(
            validate.SUITE / "vectors" / "script-host-execution-policy.json"
        )
        validate.validate_script_host_execution_policy(vector)

        def case(items: list, name: str) -> dict:
            return next(item for item in items if item["name"] == name)

        mutations = {
            "Linux pids limit becomes per-user RLIMIT": lambda item: case(
                item["native_control_inventory"]["controls"],
                "active-process-count-limit",
            )["platforms"]["linux"].update(
                {"availability": "available", "mechanism": "RLIMIT_NPROC"}
            ),
            "unavailable Linux probe rejects": lambda item: case(
                item["preflight_cases"],
                "linux-pids-max-probe-unavailable-evidence-unavailable-invocation-succeeds",
            ).__setitem__("invocation_succeeds", False),
            "absent exec inherits PATH": lambda item: case(
                item["capability_derivation_cases"],
                "all-fields-absent-deny-by-default",
            )["derived"].__setitem__("exec", ["inherited-path"]),
            "legacy script loses declared-only label": lambda item: case(
                item["audit_label_cases"], "schema7-script"
            ).__setitem__("labels", []),
            "missing evidence entry becomes valid": lambda item: case(
                item["capability_evidence_cases"], "missing-control-entry"
            ).update(
                {"record_valid": True, "invocation_succeeds": True, "expected_error": None}
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                changed = copy.deepcopy(vector)
                mutate(changed)
                with self.assertRaises(validate.ValidationFailure):
                    validate.validate_script_host_execution_policy(changed)

    def test_portable_execution_vector_rejects_dishonest_evidence(self) -> None:
        vector = validate.load_json(
            validate.SUITE / "vectors" / "go-host-execution-policy.json"
        )
        validate.validate_go_host_execution_policy(vector)

        def case(items: list, name: str) -> dict:
            return next(item for item in items if item["name"] == name)

        mutations = {
            "hardened claim is permitted": lambda item: case(
                item["capability_evidence_cases"],
                "hardened-guarantee-claimed-under-portable-policy",
            ).__setitem__("build_permitted", True),
            "unavailable control reported as applied": lambda item: case(
                item["capability_evidence_cases"],
                "unavailable-control-cannot-be-reported-as-applied",
            ).__setitem__("build_permitted", True),
            "capability evidence enters cache identity": lambda item: case(
                item["capability_evidence_cases"],
                "capability-evidence-is-not-cache-input",
            ).__setitem__("changes_cache_key", True),
            "unavailable control rejects a portable build": lambda item: case(
                item["capability_evidence_cases"],
                "unavailable-native-control-does-not-reject",
            ).__setitem__("build_permitted", False),
            "deferred guarantee is claimed": lambda item: case(
                item["deferred_hardened_guarantees"], "total-network-denial"
            ).__setitem__("portable_profile_claims", True),
            "deferred guarantee rejects portable builds": lambda item: case(
                item["deferred_hardened_guarantees"], "exact-executable-allowlisting"
            ).__setitem__("rejects_portable_build", True),
            "package influence reaches the worker": lambda item: case(
                item["package_influence_cases"], "package-selected-argv"
            ).__setitem__("worker_started", True),
            "package influence becomes expressible": lambda item: case(
                item["package_influence_cases"], "package-selected-generators"
            ).__setitem__("manifest_field", "commands.tool.generate"),
            "identity failure still publishes": lambda item: case(
                item["identity_and_protocol_cases"], "pre-launch-identity-mismatch"
            ).__setitem__("published", True),
            "build permit precedes graph validation": lambda item: item.__setitem__(
                "session_states", swapped(item["session_states"], 7, 8)
            ),
            "native controls are probed after the worker starts": (
                lambda item: item.__setitem__(
                    "session_states", swapped(item["session_states"], 1, 3)
                )
            ),
            "mandatory control becomes optional": lambda item: case(
                item["mandatory_controls"], "no-artifact-execution"
            ).__setitem__("enforced", "when-available"),
            "hardened cache identity aliases the portable one": lambda item: item[
                "cache_identity"
            ]["reserved_hardened"].__setitem__(
                "cache_key", item["cache_identity"]["portable"]["cache_key"]
            ),
            "reserved hardened policy becomes schema valid": lambda item: item[
                "cache_identity"
            ]["reserved_hardened"].__setitem__("schema_valid", True),
            "native-control inventory loses a control": lambda item: item[
                "native_control_inventory"
            ]["controls"].pop(),
            "native-control inventory stops being exhaustive": lambda item: item[
                "native_control_inventory"
            ].__setitem__("exhaustive", False),
            "native-control inventory version drifts": lambda item: item[
                "native_control_inventory"
            ].__setitem__("version", "rc5-native-control-inventory-v2"),
            "inventory availability contradicts the platform record": lambda item: case(
                item["native_control_inventory"]["controls"], "aggregate-memory-limit"
            )["platforms"]["macos"].__setitem__("availability", "available"),
            "inventory control gains an unknown platform state": lambda item: case(
                item["native_control_inventory"]["controls"], "per-file-size-limit"
            )["platforms"]["windows"].__setitem__("mechanism", "sandbox-quota"),
            "native controls are probed per host instead of per operation": (
                lambda item: item["native_control_inventory"].__setitem__(
                    "probe_scope", "per-host"
                )
            ),
            "a deferred guarantee enters the native inventory": lambda item: item[
                "native_control_inventory"
            ]["controls"].append(
                {
                    "name": "total-network-denial",
                    "applied_when_available": True,
                    "hardened_guarantee": False,
                    "platforms": {
                        "macos": {
                            "availability": "available",
                            "mechanism": "socket-denial",
                            "unavailable_reason": None,
                        },
                        "windows": {
                            "availability": "available",
                            "mechanism": "socket-denial",
                            "unavailable_reason": None,
                        },
                    },
                }
            ),
            "evidence record gains an extra field": lambda item: item[
                "capability_evidence_record"
            ]["record_fields"].append("host_label"),
            "evidence record admits an open probe time": lambda item: item[
                "capability_evidence_record"
            ]["probe_timings"].append("post-build"),
            "evidence record enters the receipt": lambda item: item[
                "capability_evidence_record"
            ].__setitem__("excluded_from", ["cache-key", "conformance-claim", "install-marker"]),
            "evidence record stops being result-only": lambda item: item[
                "capability_evidence_record"
            ].__setitem__("result_only", False),
            "evidence record drops a consistency rule": lambda item: item[
                "capability_evidence_record"
            ]["consistency_rules"].pop(),
            "evidence example omits an inventory control": lambda item: item[
                "capability_evidence_record"
            ]["examples"]["windows"]["controls"].pop(),
            "evidence example contradicts the inventory": lambda item: item[
                "capability_evidence_record"
            ]["examples"]["macos"]["controls"][0].__setitem__("status", "unavailable"),
            "evidence example claims a hardened policy": lambda item: item[
                "capability_evidence_record"
            ]["examples"]["macos"].__setitem__("execution_policy", "hardened-worker-v1"),
            "an unknown control becomes acceptable": lambda item: case(
                item["capability_evidence_cases"], "unknown-native-control-is-rejected"
            ).update({"record_valid": True, "build_permitted": True, "expected_error": None}),
            "a missing control entry becomes acceptable": lambda item: case(
                item["capability_evidence_cases"], "missing-native-control-entry-is-rejected"
            ).update({"record_valid": True, "build_permitted": True, "expected_error": None}),
            "a contradictory availability pair becomes acceptable": lambda item: case(
                item["capability_evidence_cases"],
                "available-control-cannot-be-reported-as-unavailable",
            ).update({"record_valid": True, "build_permitted": True, "expected_error": None}),
            "an unknown record version becomes acceptable": lambda item: case(
                item["capability_evidence_cases"],
                "unknown-evidence-record-version-is-rejected",
            ).update({"record_valid": True, "build_permitted": True, "expected_error": None}),
            "a reporting fault becomes a mandatory-control rejection": lambda item: case(
                item["capability_evidence_cases"],
                "unavailable-control-cannot-be-reported-as-applied",
            ).__setitem__("expected_error", "build_execution_control_unavailable"),
            "a capability evidence case disappears": lambda item: item[
                "capability_evidence_cases"
            ].pop(),
            "a mandatory control failure stops rejecting": lambda item: item[
                "failure_boundary"
            ]["missing_mandatory_portable_control"].__setitem__("rejects_build", False),
            "a mandatory control failure rejects after the worker": lambda item: item[
                "failure_boundary"
            ]["missing_mandatory_portable_control"].__setitem__(
                "fails_before", "compiler-start"
            ),
            "an unavailable native control rejects at the boundary": lambda item: item[
                "failure_boundary"
            ]["unavailable_inventory_native_control"].__setitem__("rejects_build", True),
            "a deferred capability rejects at the boundary": lambda item: item[
                "failure_boundary"
            ]["missing_deferred_hardened_capability"].__setitem__(
                "expected_error", "build_execution_control_unavailable"
            ),
            "a deferred guarantee gains a portable rejection code": lambda item: case(
                item["deferred_capability_rejection_guards"], "read-only-source-and-toolchain"
            ).__setitem__("portable_rejection_code", "build_execution_control_unavailable"),
            "a deferred guarantee blocks a portable build": lambda item: case(
                item["deferred_capability_rejection_guards"],
                "private-build-root-only-writes",
            ).__setitem__("build_permitted_when_absent", False),
            "a deferred guarantee loses its rejection guard": lambda item: item[
                "deferred_capability_rejection_guards"
            ].pop(),
            "network=none is left undefined": lambda item: item[
                "policy_semantics"
            ]["network"].__setitem__("does_not_mean", ""),
            "network=none stops naming its policy field": lambda item: item[
                "policy_semantics"
            ]["network"].__setitem__("policy_field", None),
            "a deferred guarantee loses its portable mechanism": lambda item: item[
                "policy_semantics"
            ].pop("executable_graph"),
            "two mechanisms answer the same deferred guarantee": lambda item: item[
                "policy_semantics"
            ]["source_integrity"].__setitem__(
                "deferred_hardened_guarantee", "exact-executable-allowlisting"
            ),
        }
        for label, mutate in mutations.items():
            mutated = copy.deepcopy(vector)
            mutate(mutated)
            with self.assertRaises(
                validate.ValidationFailure, msg=f"{label} was accepted"
            ):
                validate.validate_go_host_execution_policy(mutated)

    def test_rc6_release_metadata_pins_exact_suite_without_claims(self) -> None:
        validate.validate_manifest()
        release = validate.load_json(
            validate.ROOT / "release" / "1.0.0-rc.6.json"
        )
        self.assertEqual(
            release["candidate_protocol_pin"]["manifest_sha256"],
            release["downstream_consumption"]["required_manifest_sha256"],
        )
        self.assertFalse(
            release["downstream_consumption"]["committed_release_pin_advanced"]
        )
        self.assertEqual(release["claim_v3"]["claims_emitted"], [])
        self.assertEqual(
            release["claim_v3"]["claim_protocol_version"],
            validate.RC5_PROTOCOL_VERSION,
        )
        self.assertIsNone(release["claim_v3"]["rc6_claim_schema"])

    def test_published_rc5_release_metadata_is_byte_frozen(self) -> None:
        path = validate.ROOT / "release" / "1.0.0-rc.5.json"
        digest = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(digest, validate.RC5_RELEASE_METADATA_SHA256)


class AssuranceRelationalValidationTests(unittest.TestCase):
    def vector(self) -> dict:
        return validate.load_json(
            validate.SUITE / "vectors" / "assurance-modes.json"
        )

    def test_timestamp_and_checkpoint_wire_semantics(self) -> None:
        capability = self.vector()["valid_flow"]["capability_receipt"]
        invalid_capability = copy.deepcopy(capability)
        invalid_capability["observed_at"] = invalid_capability["expires_at"]
        self.assertIn(
            "must precede",
            validate.validate_wire_semantics(
                "provider-capability-receipt-v1.schema.json", invalid_capability
            ),
        )

        receipt = self.vector()["valid_flow"]["execution_receipt"]
        invalid_receipt = copy.deepcopy(receipt)
        invalid_receipt["started_at"] = "2026-07-13T00:04:00Z"
        self.assertIn(
            "at or before",
            validate.validate_wire_semantics(
                "execution-receipt-v1.schema.json", invalid_receipt
            ),
        )

        checkpoints = self.vector()["valid_flow"]["checkpoints"]
        first = copy.deepcopy(checkpoints[0])
        first["previous_checkpoint_sha256"] = "sha256:" + "9" * 64
        self.assertIn(
            "null predecessor",
            validate.validate_wire_semantics(
                "execution-checkpoint-v1.schema.json", first
            ),
        )
        for checkpoint in checkpoints[1:]:
            invalid = copy.deepcopy(checkpoint)
            invalid["previous_checkpoint_sha256"] = None
            self.assertIn(
                "digest predecessor",
                validate.validate_wire_semantics(
                    "execution-checkpoint-v1.schema.json", invalid
                ),
            )

    def test_validate_gate_rejects_every_generated_relational_mutation(self) -> None:
        vector = self.vector()
        validate.validate_assurance_vectors(vector)
        for case in vector["relational_rejection_cases"]:
            with self.subTest(case=case["name"]):
                mutated = copy.deepcopy(vector)
                mutated["valid_flow"] = validate.assurance.apply_mutation(
                    vector["valid_flow"], case["mutation"]
                )
                with self.assertRaisesRegex(
                    validate.ValidationFailure, case["expected"]["error"]
                ):
                    validate.validate_assurance_vectors(mutated)

    def test_generated_relational_cases_have_stable_unique_rejections(self) -> None:
        cases = self.vector()["relational_rejection_cases"]
        self.assertEqual(
            {case["name"] for case in cases},
            validate.ASSURANCE_RELATIONAL_REJECTIONS,
        )
        self.assertEqual(len(cases), len({case["name"] for case in cases}))
        for case in cases:
            self.assertEqual(case["expected"]["failure_stage"], "pre-execution")
            self.assertFalse(case["expected"]["execution_started"])
            self.assertIsNone(case["expected"]["fallback_mode"])


class RepositoryDescriptorIdentityTests(unittest.TestCase):
    def test_candidate_names_only_the_neutral_descriptor(self) -> None:
        validate.validate_repository_descriptor_identity()

    def test_scanner_keeps_the_frozen_build_source_algorithm(self) -> None:
        retired = validate.RETIRED_DESCRIPTOR_STEM
        namespace = validate.BUILD_SOURCE_ALGORITHM_NAMESPACE
        self.assertEqual(validate.retired_descriptor_offsets(f"{namespace}-v1"), [])
        self.assertEqual(validate.retired_descriptor_offsets(f"{namespace}-v2"), [])
        self.assertEqual(validate.retired_descriptor_offsets(f"{retired}.json"), [0])
        self.assertEqual(
            validate.retired_descriptor_offsets(f"{retired}-v1.schema.json"), [0]
        )
        self.assertEqual(
            len(validate.retired_descriptor_offsets(f"{namespace}-v1 {retired}.json")),
            1,
        )

    def test_receipt_v2_rejects_the_retired_descriptor_name(self) -> None:
        registry, paths = validate.schema_registry()
        schema = validate.load_json(paths["build-receipt-v2.schema.json"])
        validator = validate.Draft202012Validator(schema, registry=registry)
        receipt = validate.load_json(
            validate.SUITE / "schema-cases" / "build-receipt-v2" / "valid.json"
        )
        self.assertEqual(
            receipt["input"]["source"]["descriptor"]["path"],
            validate.REPOSITORY_DESCRIPTOR_NAME,
        )
        self.assertEqual(list(validator.iter_errors(receipt)), [])
        retired = copy.deepcopy(receipt)
        retired["input"]["source"]["descriptor"]["path"] = (
            f"{validate.RETIRED_DESCRIPTOR_STEM}.json"
        )
        self.assertNotEqual(list(validator.iter_errors(retired)), [])

    def test_absence_guard_fires_when_the_retired_name_returns(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            planted = Path(directory) / "protocol-surface.md"
            planted.write_text(
                f"The descriptor is `{validate.RETIRED_DESCRIPTOR_STEM}.json`.\n",
                encoding="utf-8",
            )
            original = validate.surface_files
            validate.surface_files = lambda: [planted]
            try:
                with self.assertRaises(validate.ValidationFailure) as raised:
                    validate.validate_repository_descriptor_identity()
            finally:
                validate.surface_files = original
        self.assertIn("must be absent", str(raised.exception))

    def test_descriptor_rename_misses_the_pre_rename_external_identity(self) -> None:
        # The descriptor path is part of the external build input, so the
        # neutral name is a cache-identity revision, never an alias.
        pre_rename_cache_key = (
            "sha256:07dd911a7edc29b906a021aa6e1449632ce91c2e5a3eb0ea4f851cb84fe5c492"
        )
        pre_rename_receipt = (
            "sha256:11d2bf4df52638ef353b3286c426261eac2a73b0b64a32f85d78c04490072cea"
        )
        receipt = validate.load_json(
            validate.SUITE / "schema-cases" / "build-receipt-v2" / "valid.json"
        )
        key = validate.ccj1_sha256(receipt["input"])
        self.assertEqual(receipt["cache_key"], key)
        self.assertNotEqual(key, pre_rename_cache_key)

        marker = validate.load_json(
            validate.SUITE
            / "expected"
            / "external-repository"
            / "install-marker-v3-mixed.json"
        )
        external = marker["builds"]["golden-tool"]
        self.assertEqual(external["cache_key"], key)
        self.assertNotEqual(external["receipt_sha256"], pre_rename_receipt)

        # A local go-v1 build carries no descriptor, so its identity is
        # untouched by the rename.
        local = validate.load_json(
            validate.SUITE / "schema-cases" / "build-receipt-v1" / "valid.json"
        )
        self.assertEqual(local["cache_key"], validate.ccj1_sha256(local["input"]))
        self.assertEqual(
            marker["builds"]["local-helper"]["receipt_sha256"],
            "sha256:" + "e" * 64,
        )

    def test_marker_v3_cannot_express_any_descriptor_path(self) -> None:
        common = validate.load_json(validate.SCHEMAS / "common.schema.json")
        record = common["$defs"]["buildRecordV2"]
        self.assertIn("descriptor_target", record["properties"])
        self.assertNotIn("descriptor", record["properties"])
        self.assertFalse(record["additionalProperties"])


class ManagerLifecycleValidationTests(unittest.TestCase):
    def vectors(self) -> tuple[dict, dict]:
        lifecycle = validate.load_json(
            validate.SUITE / "vectors" / "manager-lifecycle.json"
        )
        build_drivers = validate.load_json(
            validate.SUITE / "vectors" / "build-drivers.json"
        )
        return lifecycle, build_drivers

    def test_candidate_requires_all_22_compiled_lifecycle_cases(self) -> None:
        lifecycle, build_drivers = self.vectors()
        self.assertEqual(
            sum(
                len(names)
                for names in validate.MANAGER_COMPILED_LIFECYCLE_CASES.values()
            ),
            21,
        )
        self.assertIn(
            "compiled-cache-miss-is-read-only",
            validate.MANAGER_COMPILED_DRY_RUN_CASES,
        )
        validate.validate_manager_lifecycle_vectors(lifecycle, build_drivers)

    def test_each_compiled_lifecycle_group_fails_closed(self) -> None:
        for field, required in validate.MANAGER_COMPILED_LIFECYCLE_CASES.items():
            for name in sorted(required):
                with self.subTest(field=field, name=name):
                    lifecycle, build_drivers = self.vectors()
                    lifecycle[field] = [
                        case for case in lifecycle[field] if case["name"] != name
                    ]
                    with self.assertRaises(validate.ValidationFailure):
                        validate.validate_manager_lifecycle_vectors(
                            lifecycle, build_drivers
                        )

    def test_compiled_dry_run_fails_closed(self) -> None:
        lifecycle, build_drivers = self.vectors()
        lifecycle["dry_run_cases"] = [
            case
            for case in lifecycle["dry_run_cases"]
            if case["name"] != "compiled-cache-miss-is-read-only"
        ]
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_manager_lifecycle_vectors(lifecycle, build_drivers)

    def test_lifecycle_schema_and_portable_identity_fail_closed(self) -> None:
        mutations = {
            "schema version": lambda lifecycle: lifecycle.__setitem__(
                "schema_version", 2
            ),
            "source vector": lambda lifecycle: lifecycle[
                "compiled_build_fixture"
            ].__setitem__("source_vector", "build-drivers.json#/cache_identity"),
            "execution policy": lambda lifecycle: lifecycle[
                "compiled_build_fixture"
            ].__setitem__("execution_policy", "hardened-worker-v1"),
            "cache key": lambda lifecycle: lifecycle[
                "compiled_build_fixture"
            ].__setitem__("cache_key", "sha256:" + "0" * 64),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                lifecycle, build_drivers = self.vectors()
                mutate(lifecycle)
                with self.assertRaises(validate.ValidationFailure):
                    validate.validate_manager_lifecycle_vectors(
                        lifecycle, build_drivers
                    )


class BuildDriverGoldenSuiteTests(unittest.TestCase):
    PORTABLE_CACHE_KEY = (
        "sha256:529370122ae11e2e961d5265b1a020e046bcd43165b2eb96b05e73a51187ac9b"
    )
    PORTABLE_RECEIPT_SHA256 = (
        "sha256:919fbbad8e6ce95532219fd952c2309d0d7026f85209650508fd6834af4020cd"
    )
    RESERVED_HARDENED_CACHE_KEY = (
        "sha256:13736230d33ce59de7f7323dcd4cffd510655ad8dabd5ee9e8b6cb182ec70037"
    )

    def vector(self) -> dict:
        return validate.load_json(validate.SUITE / "vectors" / "build-drivers.json")

    def test_rc6_carries_forward_the_portable_rc5_build_driver_identity(self) -> None:
        validate.validate_build_driver_vectors()
        identity = self.vector()["portable_identity"]
        self.assertEqual(identity["execution_policy"], validate.PORTABLE_EXECUTION_POLICY)
        self.assertEqual(
            identity["build_input"]["policy"]["execution_policy"],
            validate.PORTABLE_EXECUTION_POLICY,
        )
        self.assertEqual(identity["cache_key"], self.PORTABLE_CACHE_KEY)
        self.assertEqual(identity["receipt_sha256"], self.PORTABLE_RECEIPT_SHA256)
        self.assertEqual(identity["cache_key"], validate.ccj1_sha256(identity["build_input"]))
        expected = validate.SUITE / "expected" / "build-driver"
        self.assertEqual(
            (expected / "build-input.ccj.json").read_bytes(),
            validate.ccj1_bytes(identity["build_input"]),
        )
        self.assertEqual(
            (expected / "receipt.ccj.json").read_bytes(),
            validate.ccj1_bytes(identity["stored_receipt"]),
        )
        self.assertEqual(
            (expected / "cache-key.txt").read_text(encoding="utf-8"),
            self.PORTABLE_CACHE_KEY + "\n",
        )
        self.assertEqual(
            (expected / "receipt-sha256.txt").read_text(encoding="utf-8"),
            self.PORTABLE_RECEIPT_SHA256 + "\n",
        )

    def test_fixed_environment_guard_rejects_incomplete_windows_private_state(self) -> None:
        vector = self.vector()
        windows = next(
            item
            for item in vector["fixed_environment_cases"]
            if item["name"] == "windows-amd64"
        )
        del windows["environment"]["APPDATA"]
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_fixed_environment_cases(vector)

    def test_execution_policy_negatives_are_schema_invalid_and_not_aliases(self) -> None:
        identity = self.vector()["cache_identity"]
        self.assertFalse(identity["aliases"])
        keys = {
            name: validate.ccj1_sha256(identity[name]["input"])
            for name in (
                "portable",
                "reserved_hardened",
                "legacy_rc4_without_execution_policy",
            )
        }
        self.assertEqual(len(set(keys.values())), 3)
        self.assertEqual(keys["portable"], self.PORTABLE_CACHE_KEY)
        self.assertEqual(keys["reserved_hardened"], self.RESERVED_HARDENED_CACHE_KEY)
        self.assertEqual(
            keys["legacy_rc4_without_execution_policy"],
            validate.LEGACY_RC4_GO_V1_CACHE_KEY,
        )

        # The two non-portable inputs are rejected by the real compiled
        # receipt schema, so they are negatives rather than alternative
        # spellings of the portable entry.
        registry, paths = validate.schema_registry()
        validator = validate.Draft202012Validator(
            validate.load_json(paths["build-receipt-v1.schema.json"]), registry=registry
        )
        template = validate.load_json(
            validate.SUITE / "schema-cases" / "build-receipt-v1" / "valid.json"
        )
        for name, schema_valid in (
            ("portable", True),
            ("reserved_hardened", False),
            ("legacy_rc4_without_execution_policy", False),
        ):
            candidate = copy.deepcopy(template)
            candidate["input"] = identity[name]["input"]
            candidate["cache_key"] = keys[name]
            self.assertEqual(not list(validator.iter_errors(candidate)), schema_valid, name)
            self.assertEqual(identity[name]["schema_valid"], schema_valid, name)

    def test_cache_identity_guard_fires_when_a_negative_claims_validity(self) -> None:
        vector = self.vector()
        vector["cache_identity"]["reserved_hardened"]["schema_valid"] = True
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_build_driver_cache_identity(
                vector,
                vector["portable_identity"]["build_input"],
                self.PORTABLE_CACHE_KEY,
            )

    def test_cache_identity_guard_fires_when_a_negative_aliases_the_portable_key(self) -> None:
        vector = self.vector()
        portable = vector["portable_identity"]["build_input"]
        legacy = vector["cache_identity"]["legacy_rc4_without_execution_policy"]
        legacy["input"] = copy.deepcopy(portable)
        legacy["cache_key"] = validate.ccj1_sha256(portable)
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_build_driver_cache_identity(
                vector, portable, self.PORTABLE_CACHE_KEY
            )

    def test_cache_identity_guard_fires_when_aliasing_is_declared(self) -> None:
        vector = self.vector()
        vector["cache_identity"]["aliases"] = True
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_build_driver_cache_identity(
                vector,
                vector["portable_identity"]["build_input"],
                self.PORTABLE_CACHE_KEY,
            )

    def test_case_guard_fires_when_a_negative_stops_being_explicit(self) -> None:
        for field in ("schema_valid", "aliases_portable_cache_key", "cache_lookup_performed"):
            with self.subTest(field=field):
                vector = self.vector()
                case = next(
                    item
                    for item in vector["rejection_cases"]
                    if item["name"] == "reserved-hardened-execution-policy"
                )
                case["expected"][field] = True
                with self.assertRaises(validate.ValidationFailure):
                    validate.validate_build_driver_cases(
                        vector, self.PORTABLE_CACHE_KEY, self.PORTABLE_RECEIPT_SHA256
                    )

    def test_case_guard_fires_when_a_rejection_executes_the_artifact(self) -> None:
        vector = self.vector()
        vector["rejection_cases"][0]["expected"]["artifact_executed"] = True
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_build_driver_cases(
                vector, self.PORTABLE_CACHE_KEY, self.PORTABLE_RECEIPT_SHA256
            )

    def test_case_guard_fires_when_a_prior_cluster_is_dropped(self) -> None:
        for section in ("positive_cases", "build_source_cases", "toolchain_cases"):
            with self.subTest(section=section):
                vector = self.vector()
                vector[section] = vector[section][1:]
                with self.assertRaises(validate.ValidationFailure):
                    validate.validate_build_driver_cases(
                        vector, self.PORTABLE_CACHE_KEY, self.PORTABLE_RECEIPT_SHA256
                    )

    def test_case_guard_fires_when_the_forged_receipt_stops_being_self_consistent(self) -> None:
        vector = self.vector()
        forged = next(
            item
            for item in vector["rejection_cases"]
            if item["name"] == "self-consistent-forged-receipt-outside-protected-state"
        )
        forged["candidate"]["receipt_sha256"] = "sha256:" + "0" * 64
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_build_driver_cases(
                vector, self.PORTABLE_CACHE_KEY, self.PORTABLE_RECEIPT_SHA256
            )

    def test_case_guard_fires_when_a_byte_edge_digest_drifts(self) -> None:
        for section, name in (
            ("build_source_cases", "domain-prefix-ordering-framing-empty-binary-and-root-marker"),
            ("toolchain_cases", "unsorted-directories-files-and-internal-link"),
        ):
            with self.subTest(section=section):
                vector = self.vector()
                case = next(item for item in vector[section] if item["name"] == name)
                case["content_sha256"] = "sha256:" + "0" * 64
                with self.assertRaises(validate.ValidationFailure):
                    validate.validate_build_driver_cases(
                        vector, self.PORTABLE_CACHE_KEY, self.PORTABLE_RECEIPT_SHA256
                    )

    def test_build_source_preimage_frames_the_fixture_on_disk(self) -> None:
        fixture = validate.BUILD_DRIVER_FIXTURE
        files = sorted(
            path.relative_to(fixture).as_posix()
            for path in fixture.rglob("*")
            if path.is_file()
        )
        preimage = validate.frame_build_source(
            [(name, (fixture / name).read_bytes()) for name in files]
        )
        self.assertTrue(preimage.startswith(validate.BUILD_SOURCE_DOMAIN_PREFIX))
        self.assertEqual(
            (validate.BUILD_DRIVER_EXPECTED / "build-source.preimage.bin").read_bytes(),
            preimage,
        )
        digest = "sha256:" + hashlib.sha256(preimage).hexdigest()
        self.assertEqual(
            (validate.BUILD_DRIVER_EXPECTED / "build-source-sha256.txt").read_text(
                encoding="utf-8"
            ),
            digest + "\n",
        )
        self.assertEqual(self.vector()["fixture"]["build_source"]["content_sha256"], digest)

    def test_declared_build_root_never_reaches_the_agent_context(self) -> None:
        fixture = self.vector()["fixture"]
        self.assertEqual(fixture["expected_context_files"], ["SKILL.md", "assets/prompt.md"])
        for name in fixture["excluded_context_files"]:
            self.assertNotIn(name, fixture["expected_context_files"])
        self.assertIn("assets/build-tool/go.mod", fixture["excluded_context_files"])


class SharedFixtureMarkerTests(unittest.TestCase):
    """Both marker roles the shared golden skill has to publish.

    `expected/marker.json` is frozen marker-v1 legacy-read evidence, and
    `expected/marker-v2.json` is the writer golden a manager's own marker
    output is compared against, because managers write marker schema 2 for
    every schema 1 through 6 installation mutation.
    """

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.expected = Path(self.temporary.name)
        for name in ("marker.json", "marker-v2.json"):
            (self.expected / name).write_bytes(
                (validate.SUITE / "expected" / name).read_bytes()
            )
        self.addCleanup(self.temporary.cleanup)

    def _rewrite(self, name: str, mutate) -> None:
        path = self.expected / name
        marker = json.loads(path.read_text(encoding="utf-8"))
        mutate(marker)
        path.write_text(json.dumps(marker, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def test_published_markers_are_accepted(self) -> None:
        validate.validate_shared_fixture_markers()
        validate.validate_shared_fixture_markers(self.expected)

    def test_writer_golden_is_byte_derived_from_the_legacy_marker(self) -> None:
        legacy = validate.load_json(validate.SUITE / "expected" / "marker.json")
        writer = validate.load_json(validate.SUITE / "expected" / "marker-v2.json")
        derived = dict(legacy)
        derived.update({"schema_version": 2, "build_roots": [], "builds": {}})
        self.assertEqual(writer, derived)
        self.assertEqual(writer["skill_schema_version"], 5)
        self.assertNotIn("build_source", writer)

    def test_missing_writer_golden_fails_closed(self) -> None:
        (self.expected / "marker-v2.json").unlink()
        with self.assertRaisesRegex(validate.ValidationFailure, "is missing"):
            validate.validate_shared_fixture_markers(self.expected)

    def test_legacy_marker_may_not_be_upgraded_in_place(self) -> None:
        self._rewrite(
            "marker.json",
            lambda marker: marker.update(
                {"schema_version": 2, "build_roots": [], "builds": {}}
            ),
        )
        with self.assertRaisesRegex(validate.ValidationFailure, "frozen marker-v1"):
            validate.validate_shared_fixture_markers(self.expected)

    def test_writer_golden_must_carry_marker_schema_2(self) -> None:
        self._rewrite("marker-v2.json", lambda marker: marker.__setitem__("schema_version", 1))
        with self.assertRaisesRegex(validate.ValidationFailure, "marker schema 2"):
            validate.validate_shared_fixture_markers(self.expected)

    def test_writer_golden_must_satisfy_its_own_schema(self) -> None:
        self._rewrite(
            "marker-v2.json", lambda marker: marker.__setitem__("skill_schema_version", 7)
        )
        with self.assertRaisesRegex(
            validate.ValidationFailure, "install-marker-v2.schema.json"
        ):
            validate.validate_shared_fixture_markers(self.expected)

    def test_writer_golden_may_not_invent_build_state(self) -> None:
        for mutate in (
            lambda marker: marker.__setitem__("build_roots", ["build"]),
            lambda marker: marker.__setitem__(
                "builds",
                {
                    "golden-tool": {
                        "driver": "go-v1",
                        "cache_key": "sha256:" + "3" * 64,
                        "receipt_sha256": "sha256:" + "e" * 64,
                        "artifact_sha256": "sha256:" + "d" * 64,
                        "artifact_path": "bin/golden-tool",
                    }
                },
            ),
        ):
            with self.subTest(mutation=mutate):
                self.setUp()
                self._rewrite("marker-v2.json", mutate)
                with self.assertRaises(validate.ValidationFailure):
                    validate.validate_shared_fixture_markers(self.expected)

    def test_writer_golden_may_not_carry_build_source_without_builds(self) -> None:
        self._rewrite(
            "marker-v2.json",
            lambda marker: marker.__setitem__(
                "build_source",
                {
                    "algorithm": validate.FROZEN_BUILD_SOURCE_ALGORITHM,
                    "content_sha256": "sha256:" + "a" * 64,
                },
            ),
        )
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_shared_fixture_markers(self.expected)

    def test_writer_golden_may_not_describe_another_installation(self) -> None:
        for field, value in (
            ("content_sha256", "sha256:" + "b" * 64),
            ("runtime_roots", []),
            ("name", "other-skill"),
        ):
            with self.subTest(field=field):
                self.setUp()
                self._rewrite("marker-v2.json", lambda marker: marker.__setitem__(field, value))
                with self.assertRaisesRegex(
                    validate.ValidationFailure, "differing only in"
                ):
                    validate.validate_shared_fixture_markers(self.expected)

    def test_writer_golden_set_members_stay_sorted_and_unique(self) -> None:
        self._rewrite(
            "marker-v2.json",
            lambda marker: marker.__setitem__("files", swapped(marker["files"], 0, 1)),
        )
        with self.assertRaisesRegex(validate.ValidationFailure, "sorted unique array"):
            validate.validate_shared_fixture_markers(self.expected)


class WorkflowRegenerationScopeTests(unittest.TestCase):
    GENERATED_FILE_INVENTORY = (
        "conformance/v1",
        "release/1.0.0-rc.5.json",
        "release/1.0.0-rc.6.json",
        "release/1.0.0-rc.7.json",
        "release/1.0.0-rc.8.json",
        "release/1.0.0-rc.9.json",
    )

    def regeneration_diff_scope(self, path: Path) -> tuple[str, ...]:
        prefix = "git diff --exit-code -- "
        matches = [
            tuple(shlex.split(raw_line.split(prefix, 1)[1]))
            for raw_line in path.read_text(encoding="utf-8").splitlines()
            if prefix in raw_line
        ]
        self.assertEqual(
            len(matches),
            1,
            f"{path.relative_to(validate.ROOT)} must have one regeneration diff gate",
        )
        return matches[0]

    def test_workflows_match_makefile_generated_file_inventory(self) -> None:
        makefile_scope = self.regeneration_diff_scope(validate.ROOT / "Makefile")
        self.assertEqual(makefile_scope, self.GENERATED_FILE_INVENTORY)
        for workflow in ("ci.yml", "release.yml"):
            with self.subTest(workflow=workflow):
                self.assertEqual(
                    self.regeneration_diff_scope(
                        validate.ROOT / ".github" / "workflows" / workflow
                    ),
                    makefile_scope,
                )

    def test_release_workflow_disables_python_bytecode_before_clean_gate(self) -> None:
        workflow = (
            validate.ROOT / ".github" / "workflows" / "release.yml"
        ).read_text(encoding="utf-8")
        self.assertIn(
            '\nenv:\n  PYTHONDONTWRITEBYTECODE: "1"\n\njobs:\n',
            workflow,
        )
        self.assertLess(
            workflow.index("PYTHONDONTWRITEBYTECODE"),
            workflow.index("python tools/validate.py"),
        )
        self.assertLess(
            workflow.index("python tools/validate.py"),
            workflow.index('python tools/release_gate.py --version "$version"'),
        )


class EnvironmentVectorTests(unittest.TestCase):
    """The environments.md section 5 determinism gate must fail closed.

    validate_environment_vectors is the production gate: tools/validate.py
    main() runs it on every `make validate` and CI run, recomputing the
    section 5 bytes independently and comparing them against the generated
    expected files. Each test narrows one rule and proves the gate rejects
    what the rule must reject.
    """

    def setUp(self) -> None:
        self.vector = validate.load_json(
            validate.SUITE / "vectors" / "environments.json"
        )

    def case(self, name: str, vector: dict | None = None) -> dict:
        source = self.vector if vector is None else vector
        return next(
            item
            for item in source["materialization_cases"]
            if item["name"] == name
        )

    def header_case(self, name: str, vector: dict) -> dict:
        return next(
            item for item in vector["header_cases"] if item["name"] == name
        )

    def test_generated_vector_passes(self) -> None:
        validate.validate_environment_vectors(self.vector)

    def test_dropped_case_fails_closed(self) -> None:
        changed = copy.deepcopy(self.vector)
        changed["materialization_cases"] = [
            item
            for item in changed["materialization_cases"]
            if item["name"] != "referenced-opencode"
        ]
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environment_vectors(changed)

    def test_transitive_drop_omission_is_byte_exact(self) -> None:
        direct = self.case("system-module-direct")
        dropped = self.case("system-module-transitive-drop")
        direct_file = next(entry for entry in direct["files"] if entry["path"] == ".agent-context/system-prompt.md")
        drop_file = next(entry for entry in dropped["files"] if entry["path"] == ".agent-context/system-prompt.md")
        self.assertEqual(drop_file["sha256"], direct_file["sha256"])
        self.assertEqual(drop_file["bytes"], direct_file["bytes"])

    def test_dropped_record_cannot_be_emptied(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("system-module-transitive-drop", changed)["dropped"] = []
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environment_vectors(changed)

    def test_error_policy_without_refusal_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        del self.case("system-module-transitive-error", changed)["error"]
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environment_vectors(changed)

    def test_drop_policy_with_refusal_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("system-module-transitive-drop", changed)["error"] = "context_system_module_transitive"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environment_vectors(changed)

    def test_header_precedence_mutation_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.header_case("composed-overlays-default", changed)["precedence"] = {
            "winner": "lower-weight",
            "placement": "winner-last",
        }
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environment_vectors(changed)

    def test_header_legacy_precedence_string_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.header_case("composed-overlays-default", changed)["precedence"] = (
            "later-overrides-earlier"
        )
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environment_vectors(changed)

    def test_header_pin_mutation_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        member = self.header_case("single-root", changed)["lock"]["members"][0]
        member["commit"] = "f" * 40
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environment_vectors(changed)

    def test_header_lock_hash_is_recomputed(self) -> None:
        # The lock: line binds the CCJ-1 hash of the case's lock; a stale
        # lock_sha256 or a lock edit that leaves expected_bytes alone fails.
        changed = copy.deepcopy(self.vector)
        self.header_case("single-root", changed)["lock_sha256"] = "sha256:" + "0" * 64
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environment_vectors(changed)
        changed = copy.deepcopy(self.vector)
        self.header_case("single-root", changed)["lock"]["members"][0]["weight"] = 7
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environment_vectors(changed)

    def test_emitted_order_mutation_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("weights-winner-higher-placement-last", changed)
        case["emitted_order"] = list(reversed(case["emitted_order"]))
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environment_vectors(changed)

    def test_weight_edit_changes_the_expected_bytes(self) -> None:
        # Raising core above umbrella moves its chapter: the expected file no
        # longer matches under winner=higher-weight placement=winner-last.
        changed = copy.deepcopy(self.vector)
        case = self.case("weights-winner-higher-placement-last", changed)
        for member in case["lock"]["members"]:
            if member["name"] == "core":
                member["weight"] = 500
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environment_vectors(changed)

    def test_no_chapter_member_cannot_gain_a_chapter(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("monolithic-composed-no-chapter", changed)
        case["packages"]["emptyoverlay"]["modules"] = [
            {"path": "00-extra.md", "content": "# Extra\n"}
        ]
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environment_vectors(changed)

    def test_schema_invalid_lock_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("monolithic-claude-code", changed)
        case["lock"]["members"][0]["overlay"] = True
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environment_vectors(changed)

    def test_mcp_env_names_union_is_recomputed(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("mcp-claude-code", changed)
        case["env_names"] = list(reversed(case["env_names"]))
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environment_vectors(changed)

    def test_mcp_selector_widening_changes_codex_bytes(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("mcp-codex-cli", changed)
        case["mcp_servers"]["docs-remote"].pop("environments")
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environment_vectors(changed)

    def test_pi_cannot_claim_an_mcp_file(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("mcp-pi-none", changed)["file_written"] = True
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environment_vectors(changed)

    def test_crlf_module_bytes_are_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        module = self.case("monolithic-claude-code", changed)["packages"][
            "companyA"
        ]["modules"][0]
        module["content"] = module["content"].replace("\n", "\r\n")
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environment_vectors(changed)

    def test_missing_trailing_lf_module_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        module = self.case("monolithic-claude-code", changed)["packages"][
            "companyA"
        ]["modules"][0]
        module["content"] = module["content"].rstrip("\n")
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environment_vectors(changed)

    def test_selector_widening_changes_the_expected_bytes(self) -> None:
        # Removing the claude_code selector makes the module applicable to
        # codex_cli, so the codex expected bytes must stop matching.
        changed = copy.deepcopy(self.vector)
        for package in self.case("monolithic-codex-selector-excluded", changed)[
            "packages"
        ].values():
            for module in package.get("modules", []):
                module.pop("environments", None)
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environment_vectors(changed)

    def test_surface_hash_mutation_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("referenced-opencode", changed)["surface_sha256"] = (
            "sha256:" + "0" * 64
        )
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environment_vectors(changed)

    def test_absent_surface_cannot_claim_a_written_file(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("no-context-directory", changed)["file_written"] = True
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environment_vectors(changed)

    def test_written_surface_cannot_claim_absence(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("monolithic-zero-modules", changed)["file_written"] = False
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environment_vectors(changed)

    def test_opencode_config_without_trailing_lf_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            source = validate.SUITE / "expected" / "environments"
            for path in source.rglob("*"):
                if not path.is_file():
                    continue
                relative = path.relative_to(validate.SUITE)
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(path.read_bytes())
            (root / "vectors").mkdir()
            (root / "vectors" / "environments.json").write_bytes(
                (validate.SUITE / "vectors" / "environments.json").read_bytes()
            )
            tampered = (
                root
                / "expected"
                / "environments"
                / "referenced-opencode"
                / "opencode.json"
            )
            tampered.write_bytes(tampered.read_bytes().rstrip(b"\n"))
            with self.assertRaises(validate.ValidationFailure):
                validate.validate_environment_vectors(suite_root=root)

    def test_hand_edited_codex_toml_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            source = validate.SUITE / "expected" / "environments"
            for path in source.rglob("*"):
                if not path.is_file():
                    continue
                relative = path.relative_to(validate.SUITE)
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(path.read_bytes())
            (root / "vectors").mkdir()
            (root / "vectors" / "environments.json").write_bytes(
                (validate.SUITE / "vectors" / "environments.json").read_bytes()
            )
            tampered = root / "expected" / "environments" / "mcp-codex-cli" / "curator-mcp.config.toml"
            # A blank separator line between tables is a plausible hand edit
            # that the byte rule forbids.
            tampered.write_bytes(
                tampered.read_bytes().replace(b"\n[mcp_servers.figma-devmode]", b"\n\n[mcp_servers.figma-devmode]")
            )
            with self.assertRaises(validate.ValidationFailure):
                validate.validate_environment_vectors(suite_root=root)

    def test_stale_expected_file_fails_the_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            source = validate.SUITE / "expected" / "environments"
            for path in source.rglob("*"):
                if not path.is_file():
                    continue
                relative = path.relative_to(validate.SUITE)
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(path.read_bytes())
            (root / "vectors").mkdir()
            (root / "vectors" / "environments.json").write_bytes(
                (validate.SUITE / "vectors" / "environments.json").read_bytes()
            )
            stale = root / "expected" / "environments" / "stale" / "CLAUDE.md"
            stale.parent.mkdir(parents=True)
            stale.write_bytes(b"orphaned\n")
            with self.assertRaises(validate.ValidationFailure):
                validate.validate_environment_vectors(suite_root=root)

    def test_environment_schema_semantics_fail_closed(self) -> None:
        commit = "0" * 40
        member = {"kind": "context", "name": "root", "source": "github.com/x/root", "version": "1.0.0", "commit": commit, "weight": 0, "required_by": [], "overlay": False}
        dep = {"kind": "context", "name": "dep", "source": "github.com/x/dep", "version": "1.0.0", "commit": commit, "weight": 0, "required_by": ["root"], "overlay": False}
        fragment_channels = validate.ENVIRONMENT_SYSTEM_PROMPT_CHANNELS["claude_code"]
        rejected = {
            "duplicate module path": (
                "agent-context-v1.schema.json",
                {"context": {"modules": [{"path": "00-base.md"}, {"path": "00-base.md", "class": "system"}]}},
            ),
            "lock members unsorted": (
                "context-lock-v1.schema.json",
                {"root": "root", "members": [member, dep]},
            ),
            "lock root missing": (
                "context-lock-v1.schema.json",
                {"root": "absent", "members": [dep, member]},
            ),
            "lock root with requirers": (
                "context-lock-v1.schema.json",
                {"root": "root", "members": [dep, dict(member, required_by=["dep"])]},
            ),
            "lock required_by unsorted": (
                "context-lock-v1.schema.json",
                {"root": "root", "members": [dict(dep, required_by=["root", "dep"]), member]},
            ),
            "lock required_by unknown": (
                "context-lock-v1.schema.json",
                {"root": "root", "members": [dict(dep, required_by=["ghost"]), member]},
            ),
            "lock required_by self": (
                "context-lock-v1.schema.json",
                {"root": "root", "members": [dict(dep, required_by=["dep", "root"]), member]},
            ),
            "marker copy outside its paths": (
                "agent-environment-marker-v1.schema.json",
                {"surfaces": {"root-context": {"paths": ["CLAUDE.md"], "copies": [{"path": "AGENTS.md", "reason": "symlink-fallback"}]}}},
            ),
            "unsorted marker surfaces": (
                "agent-environment-marker-v1.schema.json",
                {"surfaces": dict([("skills", {}), ("root-context", {})])},
            ),
            "marker root not a member": (
                "agent-environment-marker-v1.schema.json",
                {"profile": {"root": "root"}, "members": [{"name": "other", "overlay": True}]},
            ),
            "marker seeded_projects unsorted": (
                "agent-environment-marker-v1.schema.json",
                {"seeded_projects": ["/b", "/a"]},
            ),
            "fragment channels not the registry": (
                "launch-env-fragment-v1.schema.json",
                {"environment": "claude_code", "system_prompt": {"channels": fragment_channels[:1]}},
            ),
            "fragment mcp channel not the registry": (
                "launch-env-fragment-v1.schema.json",
                {"environment": "codex_cli", "mcp": {"channels": [{"kind": "flag", "flag": "-p", "argument": "name", "name": "other"}], "env_names": []}},
            ),
            "fragment env_names unsorted": (
                "launch-env-fragment-v1.schema.json",
                {"environment": "claude_code", "mcp": {"channels": validate.ENVIRONMENT_MCP_CHANNELS["claude_code"], "env_names": ["B", "A"]}},
            ),
            "fragment path_prepend outside root": (
                "launch-env-fragment-v1.schema.json",
                {"environment": "claude_code", "path_prepend": "/usr/local/bin"},
            ),
            "fragment v2 channels not the registry": (
                "launch-env-fragment-v2.schema.json",
                {"environment": "claude_code", "system_prompt": {"channels": fragment_channels[:1]}},
            ),
            "fragment v2 path_prepend outside root": (
                "launch-env-fragment-v2.schema.json",
                {"environment": "claude_code", "path_prepend": "/usr/local/bin"},
            ),
        }
        for label, (schema_name, instance) in rejected.items():
            with self.subTest(label=label):
                self.assertIsNotNone(
                    validate.validate_wire_semantics(schema_name, instance)
                )
        accepted = {
            "unique module paths": (
                "agent-context-v1.schema.json",
                {"context": {"modules": [{"path": "00-base.md"}, {"path": "10-style.md"}]}},
            ),
            "sorted lock": (
                "context-lock-v1.schema.json",
                {"root": "root", "members": [dep, member]},
            ),
            "sorted marker surfaces and members": (
                "agent-environment-marker-v1.schema.json",
                {"profile": {"root": "root"}, "members": [{"name": "root", "overlay": False}], "surfaces": dict([("root-context", {}), ("skills", {})]), "seeded_projects": ["/a", "/b"]},
            ),
            "fragment registry channels": (
                "launch-env-fragment-v1.schema.json",
                {"environment": "claude_code", "system_prompt": {"channels": fragment_channels}, "mcp": {"channels": validate.ENVIRONMENT_MCP_CHANNELS["claude_code"], "env_names": ["A", "B"]}, "path_prepend": "/manager/environments/x/bin"},
            ),
            "fragment v2 registry channels": (
                "launch-env-fragment-v2.schema.json",
                {"environment": "claude_code", "system_prompt": {"channels": fragment_channels}, "mcp": {"channels": validate.ENVIRONMENT_MCP_CHANNELS["claude_code"], "env_names": ["A", "B"]}, "path_prepend": "/manager/environments/x/bin"},
            ),
        }
        for label, (schema_name, instance) in accepted.items():
            with self.subTest(label=label):
                self.assertIsNone(
                    validate.validate_wire_semantics(schema_name, instance)
                )
        for withdrawn in ("profilefile-v1.schema.json", "context-manifest-v1.schema.json"):
            self.assertFalse((validate.SCHEMAS / withdrawn).exists(), withdrawn)


class EnvPassthroughVectorTests(unittest.TestCase):
    """The S4 passthrough/allowlist/surfacing gate must fail closed.

    validate_environments_env_passthrough_vectors is the production gate:
    tools/validate.py main() runs it on every `make validate`, recomputing
    the effective passable_env_names per profile/knob state, the
    passed/dropped/warned name sets and diagnostics, the allowlist warning
    verdict, and the surfacing output bytes from the declared inputs. Each
    test narrows one rule and proves the gate rejects what the rule must
    reject, including the review round-1 mutants.
    """

    def setUp(self) -> None:
        self.vector = validate.load_json(
            validate.SUITE / "vectors" / "environments-env-passthrough.json"
        )
        _, paths = validate.schema_registry()
        self.schema = validate.load_json(paths["manager-config-v2.schema.json"])

    def case(self, family: str, name: str, vector: dict | None = None) -> dict:
        source = self.vector if vector is None else vector
        return next(item for item in source[family] if item["name"] == name)

    def run_gate(self, vector=None, schema=None) -> None:
        validate.validate_environments_env_passthrough_vectors(
            vector=self.vector if vector is None else vector,
            schema=self.schema if schema is None else schema,
        )

    def test_published_vector_passes(self) -> None:
        self.run_gate()

    def test_review_mutant_enforce_absent_passes_is_rejected(self) -> None:
        # The review round-1 mutant: the enforcing absent-knob case flipped
        # to pass FIGMA_API_KEY and drop nothing must fail.
        changed = copy.deepcopy(self.vector)
        case = self.case("default_resolution_cases", "s4-enforce-absent-drops-all", changed)
        case["passed"] = ["FIGMA_API_KEY"]
        case["dropped"] = []
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_review_mutant_surfacing_bytes_are_rejected(self) -> None:
        # The review round-1 mutant: expected surfacing bytes replaced with
        # INVALID\n, both with stale and with refreshed length/hash pins.
        changed = copy.deepcopy(self.vector)
        self.case("surfacing_cases", "single-stdio-declaration", changed)["expected_bytes"] = "INVALID\n"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)
        changed = copy.deepcopy(self.vector)
        case = self.case("surfacing_cases", "single-stdio-declaration", changed)
        case["expected_bytes"] = "INVALID\n"
        case["expected_byte_length"] = 8
        case["expected_sha256"] = "sha256:" + hashlib.sha256(b"INVALID\n").hexdigest()
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_narrowed_list_bypass_under_enforce_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("default_resolution_cases", "s4-enforce-explicit-list-drops-with-diagnostic", changed)
        case["passed"] = ["FIGMA_API_KEY", "GITHUB_TOKEN"]
        case["dropped"] = []
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_narrowed_list_bypass_under_warn_is_rejected(self) -> None:
        # An explicit list still bounds under s4-warn, silently: passing an
        # unlisted name is a bypass even with no diagnostic expected.
        changed = copy.deepcopy(self.vector)
        case = self.case("default_resolution_cases", "s4-warn-explicit-list-bounds-silently", changed)
        case["passed"] = ["FIGMA_API_KEY", "GITHUB_TOKEN"]
        case["dropped"] = []
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_warn_absent_silence_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("default_resolution_cases", "s4-warn-absent-warns-every-passed", changed)["diagnostic"] = None
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_warn_absent_missing_migration_hint_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("default_resolution_cases", "s4-warn-absent-warns-every-passed", changed)
        case["migration_hint_names_knob"] = False
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_explicit_null_bound_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("default_resolution_cases", "explicit-null-unbounded", changed)
        case["passed"] = ["FIGMA_API_KEY"]
        case["dropped"] = ["GITHUB_TOKEN"]
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_effective_mutation_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("default_resolution_cases", "s4-enforce-absent-drops-all", changed)["effective"] = "unbounded"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_empty_allowlist_silence_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("allowlist_empty_cases", "empty-allowlist-install-warns", changed)["diagnostic"] = None
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_nonempty_allowlist_warning_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("allowlist_empty_cases", "non-empty-allowlist-silent", changed)["diagnostic"] = (
            "mcp_package_allowlist_empty"
        )
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_admitted_wording_mutation_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("allowlist_empty_cases", "empty-allowlist-install-warns", changed)["admitted"] = (
            "only listed declaration packages"
        )
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_refused_package_inside_allowlist_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("allowlist_empty_cases", "outside-non-empty-allowlist-refused", changed)
        case["mcp_package_allowlist"] = [case["package"]]
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_negative_flag_flip_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        del self.case("default_resolution_cases", "s4-enforce-absent-passes-unlisted", changed)["conforming"]
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)
        changed = copy.deepcopy(self.vector)
        self.case("default_resolution_cases", "s4-enforce-absent-drops-all", changed)["conforming"] = False
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_negative_observation_repair_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("default_resolution_cases", "s4-enforce-absent-passes-unlisted", changed)["passed"] = []
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)
        changed = copy.deepcopy(self.vector)
        self.case("allowlist_empty_cases", "non-empty-allowlist-warns", changed)["diagnostic"] = None
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)
        changed = copy.deepcopy(self.vector)
        self.case("surfacing_cases", "row-missing-env-names", changed)["row"] = (
            'mcp-declaration figma-devmode 1.2.0 stdio command=npx args=["-y"] env_names=["FIGMA_API_KEY"]'
        )
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_surfacing_order_reverted_is_rejected(self) -> None:
        # The pre-rework contradiction: update surfacing after the lock is
        # published must fail the pinned install/update order.
        changed = copy.deepcopy(self.vector)
        self.case("surfacing_order_cases", "update-surfacing-before-publish", changed)["order"] = [
            "audit-gate",
            "lock-published",
            "surfacing",
            "materialization",
        ]
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_surfacing_byte_order_mutation_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("surfacing_cases", "stdio-and-http-ordering", changed)
        lines = case["expected_bytes"].splitlines(keepends=True)
        case["expected_bytes"] = "".join(reversed(lines))
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_surfacing_row_with_space_arg_parses(self) -> None:
        # Review round-2 admission control: a valid argument containing a
        # space (agent-mcp-v1 string args) must not break the closed columns.
        row = (
            "mcp-declaration figma-devmode 1.2.0 stdio command=npx "
            'args=["-y","figma-developer-mcp","--stdio","hello world"] '
            'env_names=["FIGMA_API_KEY"]'
        )
        parsed = validate.s4_parse_surfacing_row(row)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(
            parsed["args"],
            ["-y", "figma-developer-mcp", "--stdio", "hello world"],
        )
        self.assertEqual(parsed["env_names"], ["FIGMA_API_KEY"])
        self.assertEqual(parsed["command"], "npx")

    def test_surfacing_row_with_escaped_quote_parses(self) -> None:
        row = (
            "mcp-declaration figma-devmode 1.2.0 stdio command=npx "
            'args=["say \\"hi\\"","--stdio"] '
            'env_names=["FIGMA_API_KEY"]'
        )
        parsed = validate.s4_parse_surfacing_row(row)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["args"], ['say "hi"', "--stdio"])

    def test_surfacing_row_with_delimiter_like_string_parses(self) -> None:
        # The columns are located structurally: a column marker inside a
        # JSON string value must not be mistaken for the column itself.
        row = (
            "mcp-declaration figma-devmode 1.2.0 stdio command=npx "
            'args=["a env_names=[\\"x\\"] b"] '
            'env_names=["FIGMA_API_KEY"]'
        )
        parsed = validate.s4_parse_surfacing_row(row)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["args"], ['a env_names=["x"] b'])

    def test_surfacing_row_extra_column_is_rejected(self) -> None:
        row = (
            "mcp-declaration figma-devmode 1.2.0 stdio command=npx "
            'args=["-y"] env_names=["FIGMA_API_KEY"] extra=1'
        )
        self.assertIsNone(validate.s4_parse_surfacing_row(row))

    def test_surfacing_row_padded_json_is_rejected(self) -> None:
        # Separator whitespace inside the JSON arrays is still non-compact.
        row = (
            "mcp-declaration figma-devmode 1.2.0 stdio command=npx "
            'args=["-y", "serve"] env_names=["FIGMA_API_KEY"]'
        )
        self.assertIsNone(validate.s4_parse_surfacing_row(row))

    def test_space_and_quote_cases_pass_the_gate(self) -> None:
        names = {item["name"] for item in self.vector["surfacing_cases"]}
        self.assertIn("args-with-space", names)
        self.assertIn("args-with-escaped-quote", names)
        self.run_gate()

    def test_dropped_case_fails_closed(self) -> None:
        changed = copy.deepcopy(self.vector)
        changed["surfacing_order_cases"] = [
            item
            for item in changed["surfacing_order_cases"]
            if item["name"] != "update-surfacing-before-publish"
        ]
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_schema_default_drift_is_rejected(self) -> None:
        schema = copy.deepcopy(self.schema)
        schema["$defs"]["environments"]["properties"]["passable_env_names"]["default"] = None
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(schema=schema)

    def test_schema_valid_flag_flip_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("schema_cases", "knob-invalid-name", changed)["valid"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_wrong_capability_identity_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        changed["protocol_version"] = "1.0.0-rc.8"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)


class StoreBoundaryVectorTests(unittest.TestCase):
    """The S5 protected-boundary gate must fail closed.

    validate_environments_store_boundary_vectors is the production gate:
    tools/validate.py main() runs it on every `make validate`, recomputing
    the §4 store-trust verdict from the five boundary checks plus the pin
    hash, then home currency, in enclosing → entries → pin hashes → home
    currency order, and from it the §10.1 diagnostic, the fragment verdict,
    the §12 currency, the §4 dry-run outcome (entry-class rebuilds,
    enclosing never rebuilds), and the §10.1 repair outcomes. Each named
    case is pinned to its discriminating inputs (object, check, home,
    surface). Each test narrows one rule and proves the gate rejects what
    the rule must reject.
    """

    def setUp(self) -> None:
        self.vector = validate.load_json(
            validate.SUITE / "vectors" / "environments-store-boundary.json"
        )

    def case(self, family: str, name: str, vector: dict | None = None) -> dict:
        source = self.vector if vector is None else vector
        return next(item for item in source[family] if item["name"] == name)

    def run_gate(self, vector=None) -> None:
        validate.validate_environments_store_boundary_vectors(
            vector=self.vector if vector is None else vector,
        )

    def test_published_vector_passes(self) -> None:
        self.run_gate()

    def test_fragment_emitted_for_swapped_bytes_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("resolve_cases", "swapped-system-prompt-bytes-untrusted", changed)["fragment_emitted"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_untrusted_silence_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("resolve_cases", "wrong-ownership-untrusted", changed)["diagnostic"] = None
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_untrusted_reported_current_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("resolve_cases", "symlinked-entry-root-untrusted", changed)["row_current"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_intact_refusal_is_rejected(self) -> None:
        # The gate recomputes in both directions: an intact store that
        # refuses the fragment is as wrong as an untrusted one emitting it.
        changed = copy.deepcopy(self.vector)
        case = self.case("resolve_cases", "intact-resolve-emits-fragment", changed)
        case["fragment_emitted"] = False
        case["diagnostic"] = "environment_store_untrusted"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_multi_failure_case_is_rejected(self) -> None:
        # A positive resolve case isolates exactly one failing check.
        changed = copy.deepcopy(self.vector)
        self.case("resolve_cases", "wrong-permissions-untrusted", changed)["ownership"] = False
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_swap_without_surface_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("resolve_cases", "swapped-root-context-bytes-untrusted", changed)
        case["surface"] = None
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_surface_without_pin_break_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("resolve_cases", "swapped-root-context-bytes-untrusted", changed)
        case["pin_hash_match"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_wrong_failing_check_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("resolve_cases", "containment-escape-untrusted", changed)["failing_check"] = "ownership"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_healed_negative_is_rejected(self) -> None:
        # A negative whose observation stops violating the rule must fail:
        # the flipped fragment now matches the recomputed verdict.
        changed = copy.deepcopy(self.vector)
        self.case("resolve_cases", "swapped-bytes-emits-fragment", changed)["fragment_emitted"] = False
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_dry_run_wrong_outcome_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("dry_run_cases", "dry-run-untrusted-reports-would-rebuild", changed)["outcome"] = None
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_dry_run_mutation_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("dry_run_cases", "dry-run-untrusted-reports-would-rebuild", changed)["mutated"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_repair_reapply_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("repair_cases", "repair-rebuilds-git-entry-from-snapshot", changed)["reapplied_before_trust"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_path_rebuild_is_rejected(self) -> None:
        # A path entry has no second copy: only a git entry rebuilds.
        changed = copy.deepcopy(self.vector)
        case = self.case("repair_cases", "repair-path-entry-cannot-rebuild", changed)
        case["rebuilt_from_snapshot"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_status_missing_check_name_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("status_cases", "status-names-failing-check", changed)["names_failing_check"] = None
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_case_inventory_is_exact(self) -> None:
        changed = copy.deepcopy(self.vector)
        changed["resolve_cases"] = [
            item
            for item in changed["resolve_cases"]
            if item["name"] != "marker-symlink-untrusted"
        ]
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_wrong_capability_identity_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        changed["capability"] = "agent-environments-v2"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_five_to_one_narrowing_is_rejected(self) -> None:
        # The reviewer's F4 narrowing: five named boundary branches
        # collapsed to ownership-only, with failing_check updated to match.
        # Without scenario pinning the gate accepts (5/5 coverage falls to
        # 1/5 with exit 0); the pinned gate must refuse.
        changed = copy.deepcopy(self.vector)
        narrow = {
            "wrong-permissions-untrusted": "permissions",
            "containment-escape-untrusted": "containment",
            "non-regular-component-untrusted": "regular_types",
            "symlinked-entry-root-untrusted": "link_safety",
        }
        for name, check in narrow.items():
            case = self.case("resolve_cases", name, changed)
            case[check] = True
            case["ownership"] = False
            case["failing_check"] = "ownership"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_enclosing_object_swap_is_rejected(self) -> None:
        # A named enclosing branch that no longer names its boundary is refused.
        changed = copy.deepcopy(self.vector)
        case = self.case("resolve_cases", "environments-root-wrong-owner-untrusted", changed)
        case["object"] = "store-entry"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_stale_misclassified_as_untrusted_is_rejected(self) -> None:
        # An intact updated store with an old marker is stale, never untrusted (F1).
        changed = copy.deepcopy(self.vector)
        case = self.case("resolve_cases", "intact-updated-store-old-marker-stale", changed)
        case["diagnostic"] = "environment_store_untrusted"
        case["failing_check"] = "pin_hash"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_swapped_old_marker_stale_is_rejected(self) -> None:
        # A swapped updated store with an old marker is untrusted (pin wins
        # over currency) and never adopted (F1).
        changed = copy.deepcopy(self.vector)
        case = self.case("resolve_cases", "swapped-updated-store-old-marker-untrusted", changed)
        case["diagnostic"] = "environment_home_stale"
        case["failing_check"] = "home_currency"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_unprovisioned_swap_provisioned_is_rejected(self) -> None:
        # An unprovisioned home is verified the same way: a swapped entry is
        # untrusted even with no marker (F2).
        changed = copy.deepcopy(self.vector)
        case = self.case("resolve_cases", "unprovisioned-swapped-untrusted", changed)
        case["diagnostic"] = "environment_home_stale"
        case["failing_check"] = None
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_unreadable_misreported_as_absent_is_rejected(self) -> None:
        # Absent and unreadable markers are distinct facts: the unreadable
        # marker is never reported as unprovisioned stale (F2).
        changed = copy.deepcopy(self.vector)
        case = self.case("resolve_cases", "unreadable-marker-non-current", changed)
        case["diagnostic"] = "environment_home_stale"
        case["home"] = "unprovisioned"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_enclosing_dry_run_would_rebuild_is_rejected(self) -> None:
        # Dry-run of an enclosing failure plans no rebuild (F3).
        changed = copy.deepcopy(self.vector)
        case = self.case("dry_run_cases", "dry-run-enclosing-no-rebuild", changed)
        case["outcome"] = "would-rebuild-untrusted-store"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_enclosing_rebuild_is_rejected(self) -> None:
        # An enclosing failure is never rebuilt: no protected place (F3).
        changed = copy.deepcopy(self.vector)
        case = self.case("repair_cases", "repair-enclosing-refuses-no-rebuild", changed)
        case["rebuilt_from_snapshot"] = True
        case["diagnostic"] = None
        case["fragment_emitted"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)


class PathKindAdmissionVectorTests(unittest.TestCase):
    """The E6 path-kind admission gate must fail closed.

    validate_environments_path_kind_admission_vectors is the production
    gate: tools/validate.py main() runs it on every `make validate`,
    recomputing the §2.2 MCP source-kind verdict (git only; a path
    declaration is refused naming package and declaration), the §4
    directory-boundary verdict from the five boundary checks (no pin is
    recomputed against the live directory), the §3 direct-naming verdict
    for a trusted directory, and from them the fragment verdict, the §12
    currency, and the posture naming, plus the §10.1 dry-run verdict (a
    `path` directory failure reports `environment_store_untrusted` with
    no rebuild planned, never `would-rebuild-untrusted-store`). Each
    named case is pinned to its discriminating inputs (source kind, pin
    kind, origin; failing check, directness, content, policy, role,
    origin). Each test narrows one rule and proves the gate rejects what
    the rule must reject.
    """

    def setUp(self) -> None:
        self.vector = validate.load_json(
            validate.SUITE / "vectors" / "environments-path-kind-admission.json"
        )

    def case(self, family: str, name: str, vector: dict | None = None) -> dict:
        source = self.vector if vector is None else vector
        return next(item for item in source[family] if item["name"] == name)

    def run_gate(self, vector=None) -> None:
        validate.validate_environments_path_kind_admission_vectors(
            vector=self.vector if vector is None else vector,
        )

    def test_published_vector_passes(self) -> None:
        self.run_gate()

    def test_path_mcp_admitted_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("mcp_kind_cases", "path-overlay-mcp-declaration-refused", changed)
        case["admitted"] = True
        case["diagnostic"] = None
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_git_mcp_refused_is_rejected(self) -> None:
        # The gate recomputes in both directions: a git declaration that
        # refuses is as wrong as a path declaration that admits.
        changed = copy.deepcopy(self.vector)
        case = self.case("mcp_kind_cases", "git-mcp-declaration-admitted", changed)
        case["admitted"] = False
        case["diagnostic"] = "mcp_declaration_path_source_refused"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_refusal_missing_declaration_name_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("mcp_kind_cases", "path-root-mcp-declaration-refused", changed)["names_declaration"] = None
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_refusal_wrong_diagnostic_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("mcp_kind_cases", "path-import-mcp-declaration-refused", changed)["diagnostic"] = "mcp_package_not_allowed"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_path_rewritten_as_git_is_rejected(self) -> None:
        # A named path branch rewritten as a git admission under the same
        # name — with the pin inputs updated to match — is refused.
        changed = copy.deepcopy(self.vector)
        case = self.case("mcp_kind_cases", "path-overlay-mcp-declaration-refused", changed)
        case["source_kind"] = "git"
        case["pin_kind"] = "commit"
        case["source"] = "github.com/companyA/mcp-figma-devmode"
        case["admitted"] = True
        case["diagnostic"] = None
        case["names_package"] = None
        case["names_declaration"] = None
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_healed_mcp_negative_is_rejected(self) -> None:
        # A negative whose observation stops violating the rule must fail:
        # the admitted observation now claims the recomputed refusal.
        changed = copy.deepcopy(self.vector)
        case = self.case("mcp_kind_cases", "path-mcp-declaration-admitted", changed)
        case["admitted"] = False
        case["diagnostic"] = "mcp_declaration_path_source_refused"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_world_writable_emits_fragment_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("path_boundary_cases", "path-overlay-world-writable-untrusted", changed)
        case["fragment_emitted"] = True
        case["row_current"] = True
        case["diagnostic"] = None
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_untrusted_silence_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("path_boundary_cases", "path-overlay-symlinked-component-untrusted", changed)["diagnostic"] = None
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_posture_missing_path_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("path_boundary_cases", "path-overlay-wrong-ownership-untrusted", changed)["names_path"] = None
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_wrong_failing_check_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("path_boundary_cases", "path-overlay-containment-escape-untrusted", changed)
        case["failing_check"] = "ownership"
        case["names_check"] = "ownership"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_rebuild_planned_is_rejected(self) -> None:
        # A path source has no second copy: no rebuild is ever planned.
        changed = copy.deepcopy(self.vector)
        self.case("path_boundary_cases", "path-overlay-non-regular-component-untrusted", changed)["rebuild_planned"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_healed_current_negative_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("path_boundary_cases", "path-overlay-untrusted-reported-current", changed)
        case["diagnostic"] = "environment_store_untrusted"
        case["fragment_emitted"] = False
        case["row_current"] = False
        case["failing_check"] = "permissions"
        case["names_path"] = "/Users/operator/personal"
        case["names_check"] = "permissions"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_healed_rebuild_negative_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("path_boundary_cases", "path-overlay-untrusted-rebuilds", changed)["rebuild_planned"] = False
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_five_to_one_narrowing_is_rejected(self) -> None:
        # The reviewer's narrowing: five named boundary branches collapsed
        # to ownership-only, with failing_check updated to match. Without
        # scenario pinning the gate accepts (5/5 coverage falls to 1/5
        # with exit 0); the pinned gate must refuse.
        changed = copy.deepcopy(self.vector)
        narrow = {
            "path-overlay-world-writable-untrusted": "permissions",
            "path-overlay-symlinked-component-untrusted": "link_safety",
            "path-overlay-containment-escape-untrusted": "containment",
            "path-overlay-non-regular-component-untrusted": "regular_types",
        }
        for name, check in narrow.items():
            case = self.case("path_boundary_cases", name, changed)
            case[check] = True
            case["ownership"] = False
            case["failing_check"] = "ownership"
            case["names_check"] = "ownership"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_transitive_misdiagnosed_as_untrusted_is_rejected(self) -> None:
        # A trusted directory with a transitive system module is E2's
        # refusal, never environment_store_untrusted.
        changed = copy.deepcopy(self.vector)
        case = self.case("path_boundary_cases", "path-transitive-system-module-refused", changed)
        case["diagnostic"] = "environment_store_untrusted"
        case["failing_check"] = "ownership"
        case["names_path"] = "/Users/operator/leaf"
        case["names_check"] = "ownership"
        case["names_package"] = None
        case["names_module"] = None
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_transitive_rewritten_as_direct_is_rejected(self) -> None:
        # A named transitive branch rewritten as a direct admission under
        # the same name is refused.
        changed = copy.deepcopy(self.vector)
        case = self.case("path_boundary_cases", "path-transitive-system-module-refused", changed)
        case["direct"] = True
        case["role"] = "overlay"
        case["diagnostic"] = None
        case["fragment_emitted"] = True
        case["row_current"] = True
        case["names_package"] = None
        case["names_module"] = None
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_pin_hash_comparison_is_rejected(self) -> None:
        # No pin is recomputed against the live directory (§4): a case
        # carrying a pin-hash comparison models the wrong rule.
        changed = copy.deepcopy(self.vector)
        self.case("path_boundary_cases", "path-overlay-system-module-admitted", changed)["pin_hash_match"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_multi_failure_case_is_rejected(self) -> None:
        # A positive boundary case isolates exactly one failing check.
        changed = copy.deepcopy(self.vector)
        self.case("path_boundary_cases", "path-overlay-world-writable-untrusted", changed)["ownership"] = False
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_case_inventory_is_exact(self) -> None:
        changed = copy.deepcopy(self.vector)
        changed["path_boundary_cases"] = [
            item
            for item in changed["path_boundary_cases"]
            if item["name"] != "path-transitive-system-module-refused"
        ]
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_no_system_overlay_refusal_healed_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("path_boundary_cases", "path-overlay-no-system-world-writable-untrusted", changed)
        case["permissions"] = True
        case["fragment_emitted"] = True
        case["row_current"] = True
        case["diagnostic"] = None
        case["failing_check"] = None
        case["names_path"] = None
        case["names_check"] = None
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_no_system_overlay_rewritten_as_system_is_rejected(self) -> None:
        # A named no-system branch rewritten as a system-module case
        # under the same name is refused: the check is on the directory,
        # not on the content class.
        changed = copy.deepcopy(self.vector)
        case = self.case("path_boundary_cases", "path-overlay-no-system-world-writable-untrusted", changed)
        case["carries_system_modules"] = True
        case["module"] = "90-system.md"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_no_system_import_refusal_healed_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("path_boundary_cases", "path-import-no-system-wrong-ownership-untrusted", changed)
        case["ownership"] = True
        case["fragment_emitted"] = True
        case["row_current"] = True
        case["diagnostic"] = None
        case["failing_check"] = None
        case["names_path"] = None
        case["names_check"] = None
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_no_system_import_rewritten_as_system_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("path_boundary_cases", "path-import-no-system-wrong-ownership-untrusted", changed)
        case["carries_system_modules"] = True
        case["module"] = "90-system.md"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_no_system_overlay_control_rewritten_as_system_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("path_boundary_cases", "path-overlay-no-system-modules-admitted", changed)
        case["carries_system_modules"] = True
        case["module"] = "90-system.md"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_no_system_narrowing_disagrees_with_corpus(self) -> None:
        # The reviewer's narrowing as verdicts: a manager that skips the
        # directory check for sources without system modules reports
        # trusted for them. The pinned corpus must contradict it on both
        # no-system entry classes (overlay and onboarding import).
        mismatches = []
        for case in self.vector["path_boundary_cases"]:
            if case.get("conforming") is False:
                continue
            inputs = {check: case[check] for check in validate.E6_BOUNDARY_CHECKS}
            trusted, _ = validate.e6_boundary_trusted(inputs)
            narrowed = trusted if case["carries_system_modules"] else True
            if not narrowed:
                narrowed_diag = validate.E6_DIAG_UNTRUSTED
            elif (
                case["carries_system_modules"]
                and not case["direct"]
                and case["machine_policy"]["transitive_system_modules"] == "error"
            ):
                narrowed_diag = validate.E6_DIAG_TRANSITIVE
            else:
                narrowed_diag = None
            if narrowed_diag != case["diagnostic"]:
                mismatches.append(case["name"])
        self.assertIn("path-overlay-no-system-world-writable-untrusted", mismatches)
        self.assertIn("path-import-no-system-wrong-ownership-untrusted", mismatches)

    def test_dry_run_would_rebuild_report_is_rejected(self) -> None:
        # A dry-run evaluation of a `path` directory failure that reports
        # would-rebuild-untrusted-store is refused: that outcome names
        # only a store entry, lock, or marker file failure (§4, §10.1).
        changed = copy.deepcopy(self.vector)
        self.case("dry_run_cases", "path-overlay-dry-run-untrusted-no-rebuild", changed)["outcome"] = (
            validate.S5_OUTCOME_WOULD_REBUILD
        )
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_dry_run_untrusted_silence_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("dry_run_cases", "path-overlay-dry-run-untrusted-no-rebuild", changed)["diagnostic"] = None
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_dry_run_intact_reports_untrusted_is_rejected(self) -> None:
        # The gate recomputes in both directions: an intact directory
        # that reports untrusted is as wrong as a failure that is silent.
        changed = copy.deepcopy(self.vector)
        case = self.case("dry_run_cases", "path-overlay-dry-run-intact-plans-nothing", changed)
        case["diagnostic"] = "environment_store_untrusted"
        case["failing_check"] = "permissions"
        case["names_path"] = "/Users/operator/personal"
        case["names_check"] = "permissions"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_dry_run_mutates_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("dry_run_cases", "path-overlay-dry-run-untrusted-no-rebuild", changed)["mutated"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_dry_run_rebuild_planned_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("dry_run_cases", "path-overlay-dry-run-untrusted-no-rebuild", changed)["rebuild_planned"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_dry_run_untrusted_healed_is_rejected(self) -> None:
        # A named dry-run failure branch rewritten as a passing case
        # under the same name is refused.
        changed = copy.deepcopy(self.vector)
        case = self.case("dry_run_cases", "path-overlay-dry-run-untrusted-no-rebuild", changed)
        case["permissions"] = True
        case["diagnostic"] = None
        case["failing_check"] = None
        case["names_path"] = None
        case["names_check"] = None
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_healed_dry_run_negative_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("dry_run_cases", "path-overlay-dry-run-reports-would-rebuild", changed)["outcome"] = None
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_dry_run_negative_wrong_violation_is_rejected(self) -> None:
        # The negative isolates exactly the R1 violation: healing the
        # outcome while violating elsewhere is still refused.
        changed = copy.deepcopy(self.vector)
        case = self.case("dry_run_cases", "path-overlay-dry-run-reports-would-rebuild", changed)
        case["outcome"] = None
        case["mutated"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_dry_run_inventory_is_exact(self) -> None:
        changed = copy.deepcopy(self.vector)
        changed["dry_run_cases"] = [
            item for item in changed["dry_run_cases"] if item["name"] != "path-overlay-dry-run-intact-plans-nothing"
        ]
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_wrong_capability_identity_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        changed["capability"] = "agent-environments-v2"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)


class SourceSignersVectorTests(unittest.TestCase):
    """The E1 signer-verification/merge/posture/delta gate must fail closed.

    validate_environments_source_signers_vectors is the production gate:
    tools/validate.py main() runs it on every `make validate`, recomputing
    the section 1.4 verification verdict, the section 12.2 effective
    allowlist, the section 12 posture rows, and the section 9.2 delta
    lines, trigger, and both rollout revisions' outcomes from the declared
    inputs. Each test narrows one rule and proves the gate rejects what
    the rule must reject.
    """

    def setUp(self) -> None:
        self.vector = validate.load_json(
            validate.SUITE / "vectors" / "environments-source-signers.json"
        )
        _, paths = validate.schema_registry()
        self.schema = validate.load_json(paths["manager-config-v2.schema.json"])

    def case(self, family: str, name: str, vector: dict | None = None) -> dict:
        source = self.vector if vector is None else vector
        return next(item for item in source[family] if item["name"] == name)

    def run_gate(self, vector=None, schema=None) -> None:
        validate.validate_environments_source_signers_vectors(
            vector=self.vector if vector is None else vector,
            schema=self.schema if schema is None else schema,
        )

    def test_published_vector_passes(self) -> None:
        self.run_gate()

    def test_unsigned_accepted_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("verification_cases", "unsigned-refused", changed)
        case["expected"]["verdict"] = "accepted"
        case["expected"]["diagnostic"] = None
        case["expected"]["selected"] = "1.2.0"
        case["expected"]["lock_written"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_wrong_signer_accepted_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("verification_cases", "wrong-signer-refused", changed)
        case["expected"]["verdict"] = "accepted"
        case["expected"]["diagnostic"] = None
        case["expected"]["lock_written"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_invalid_signature_accepted_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("verification_cases", "invalid-signature-refused", changed)
        case["expected"]["verdict"] = "accepted"
        case["expected"]["diagnostic"] = None
        case["expected"]["lock_written"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_fallback_selection_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("verification_cases", "no-silent-fallback-to-lower-candidate", changed)
        case["expected"]["verdict"] = "accepted"
        case["expected"]["diagnostic"] = None
        case["expected"]["selected"] = "1.9.0"
        case["expected"]["lock_written"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_require_without_allowlist_accepted_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("verification_cases", "require-without-allowlist-refused", changed)
        case["expected"]["verdict"] = "accepted"
        case["expected"]["diagnostic"] = None
        case["expected"]["lock_written"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_empty_allowlist_accepted_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("verification_cases", "empty-allowlist-signed-refused", changed)
        case["expected"]["verdict"] = "accepted"
        case["expected"]["diagnostic"] = None
        case["expected"]["lock_written"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_signers_seen_mutation_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("verification_cases", "wrong-signer-refused", changed)
        case["expected"]["signers_seen"] = []
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_path_allowlist_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("verification_cases", "path-source-never-verified", changed)
        case["allowlist"] = []
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_repaired_verification_negative_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("verification_cases", "unsigned-accepted", changed)
        case["observed"]["verdict"] = "refused"
        case["observed"]["diagnostic"] = "context_source_unsigned"
        case["observed"]["selected"] = None
        case["observed"]["lock_written"] = False
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_repaired_fallback_negative_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("verification_cases", "fallback-selection", changed)
        case["observed"]["verdict"] = "refused"
        case["observed"]["diagnostic"] = "context_source_unsigned"
        case["observed"]["selected"] = None
        case["observed"]["lock_written"] = False
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_allowlist_grammar_drift_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("verification_cases", "ssh-tag-signature-accepted", changed)
        case["allowlist"][0]["key"] = "not-an-openssh-key-line"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_locked_overlap_taking_machine_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("merge_cases", "locked-overlap-system-wins-with-warning", changed)
        case["expected"]["effective"]["github.com/example/context"] = case["machine"]["github.com/example/context"]
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_locked_overlap_warning_dropped_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("merge_cases", "locked-overlap-system-wins-with-warning", changed)
        case["expected"]["warnings"] = []
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_unlocked_merge_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("merge_cases", "unlocked-machine-replaces-whole", changed)
        case["expected"]["effective"]["github.com/example/context"] = case["system"]["github.com/example/context"]
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_enforced_row_without_allowlist_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("posture_cases", "unconfigured", changed)
        case["expected"]["rows"][0]["state"] = "enforced"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_required_missing_without_require_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("posture_cases", "unconfigured", changed)
        case["expected"]["rows"][0]["state"] = "required-missing"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_pin_fails_reported_current_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("posture_cases", "enforced-pin-fails-non-current", changed)
        case["expected"]["rows"][0]["current"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_verified_signer_outside_allowlist_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("posture_cases", "enforced-names-verified-signer", changed)
        case["local"]["github.com/example/context"]["signer"] = {
            "type": "gpg", "fingerprint": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        }
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_dropped_trigger_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("delta_cases", "new-system-module", changed)
        case["expected"]["trigger"] = []
        case["expected"]["revision_a"]["diagnostic"] = None
        case["expected"]["revision_b"]["diagnostic"] = None
        case["expected"]["revision_b"]["proceeds"] = True
        case["expected"]["revision_b"]["lock_published"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_revision_b_refusal_flipped_to_proceed_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("delta_cases", "changed-mcp-args", changed)
        case["expected"]["revision_b"]["diagnostic"] = None
        case["expected"]["revision_b"]["proceeds"] = True
        case["expected"]["revision_b"]["lock_published"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_revision_a_silence_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("delta_cases", "new-mcp-member", changed)
        case["expected"]["revision_a"]["diagnostic"] = None
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_stale_delta_line_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("delta_cases", "plain-version-bump-no-confirmation", changed)
        case["expected"]["lines"] = []
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_env_names_reorder_silenced_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("delta_cases", "mcp-env-names-reorder-triggers", changed)
        case["expected"]["trigger"] = []
        case["expected"]["revision_a"]["diagnostic"] = None
        case["expected"]["revision_a"]["hint"] = None
        case["expected"]["revision_b"]["diagnostic"] = None
        case["expected"]["revision_b"]["proceeds"] = True
        case["expected"]["revision_b"]["lock_published"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_removal_treated_as_trigger_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("delta_cases", "removed-system-member-silent", changed)
        case["expected"]["trigger"] = ["sysleaf"]
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_snapshot_covering_no_pin_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("delta_cases", "plain-version-bump-no-confirmation", changed)
        case["snapshots"]["0000000000000000000000000000000000000000"] = {"system_modules": [], "mcp": None}
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_repaired_preconfirm_negative_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("delta_cases", "config-preconfirm-claim", changed)
        case["claimed"]["diagnostic"] = "profile_update_confirmation_required"
        case["claimed"]["proceeds"] = False
        case["claimed"]["lock_published"] = False
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_repaired_silence_negative_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("delta_cases", "silent-system-introduction", changed)
        case["claimed"]["diagnostic"] = "profile_update_system_delta"
        case["claimed"]["hint"] = validate.E1_HINT_DELTA
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_all_continuing_past_refusal_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("all_cases", "all-without-flag-stops-at-first-refusal", changed)
        third = next(item for item in case["expected"]["profiles"] if item["profile"] == "third")
        third["revision_b"] = {"diagnostic": None, "proceeds": True, "lock_published": True}
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_all_wrong_stop_profile_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("all_cases", "all-without-flag-stops-at-first-refusal", changed)
        case["expected"]["stopped"]["revision_b"] = "third"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_dropped_case_fails_closed(self) -> None:
        changed = copy.deepcopy(self.vector)
        changed["delta_cases"] = [item for item in changed["delta_cases"] if item["name"] != "changed-mcp-args"]
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_wrong_capability_identity_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        changed["protocol_version"] = "1.0.0-rc.8"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_wrong_revision_pin_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        changed["revision_b"] = "flip release: warn and proceed"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_mcp_url_only_change_silenced_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("delta_cases", "changed-mcp-url", changed)
        case["expected"]["trigger"] = []
        case["expected"]["revision_a"]["diagnostic"] = None
        case["expected"]["revision_a"]["hint"] = None
        case["expected"]["revision_b"]["diagnostic"] = None
        case["expected"]["revision_b"]["proceeds"] = True
        case["expected"]["revision_b"]["lock_published"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_mcp_selector_only_change_silenced_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("delta_cases", "changed-mcp-selector", changed)
        case["expected"]["trigger"] = []
        case["expected"]["revision_a"]["diagnostic"] = None
        case["expected"]["revision_a"]["hint"] = None
        case["expected"]["revision_b"]["diagnostic"] = None
        case["expected"]["revision_b"]["proceeds"] = True
        case["expected"]["revision_b"]["lock_published"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_mcp_declaration_field_narrowed_out_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("delta_cases", "changed-mcp-url", changed)
        snapshots = case["snapshots"]
        pins = sorted(snapshots)
        snapshots[pins[1]]["mcp"]["url"] = snapshots[pins[0]]["mcp"]["url"]
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_revision_a_hint_dropped_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("delta_cases", "new-mcp-member", changed)
        case["expected"]["revision_a"]["hint"] = None
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_revision_a_hint_without_trigger_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("delta_cases", "plain-version-bump-no-confirmation", changed)
        case["expected"]["revision_a"]["hint"] = validate.E1_HINT_DELTA
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_reinstall_refusal_flipped_to_proceed_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("reinstall_cases", "reinstall-without-flag-refuses-under-b", changed)
        case["expected"]["revision_b"]["diagnostic"] = None
        case["expected"]["revision_b"]["proceeds"] = True
        case["expected"]["revision_b"]["lock_published"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_reinstall_claiming_update_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("reinstall_cases", "reinstall-with-flag-proceeds", changed)
        case["operation"] = "profile update"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_revision_selection_tag_only_evidence_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("verification_cases", "revision-selection-verifies-commit", changed)
        candidate = case["candidates"][0]
        candidate["tag_signature"] = candidate["commit_signature"]
        candidate["commit_signature"] = None
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_different_ssh_material_accepted_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("verification_cases", "ssh-different-material-rejected", changed)
        case["expected"]["verdict"] = "accepted"
        case["expected"]["diagnostic"] = None
        case["expected"]["selected"] = "1.2.0"
        case["expected"]["lock_written"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_same_key_different_comment_refused_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("verification_cases", "ssh-same-key-different-comment-accepted", changed)
        case["expected"]["verdict"] = "refused"
        case["expected"]["diagnostic"] = "context_source_signer_rejected"
        case["expected"]["selected"] = None
        case["expected"]["lock_written"] = False
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_commented_signers_seen_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("verification_cases", "ssh-tag-signature-accepted", changed)
        case["expected"]["signers_seen"] = [
            {"type": "ssh", "key": case["allowlist"][0]["key"]}
        ]
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_confirmation_posture_wrong_behavior_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("confirmation_posture_cases", "update-confirmation-revision-b-flip", changed)
        case["expected"]["row"]["behavior"] = "a triggered update delta warns and proceeds"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_confirmation_posture_unknown_revision_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("confirmation_posture_cases", "update-confirmation-revision-a-warning", changed)
        case["update_confirmation_revision"] = "C-enforcing"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_absent_optional_padding_narrowing_fails_on_new_cases(self) -> None:
        """A comparator that pads absent optional arrays with [] MUST miss the
        new absent/present vectors while the section 9.2 CCJ-1 rule triggers
        on all of them; padding the fixtures the same way MUST fail the gate
        on the pinned trigger, proving the suite occupies the former
        presence blind spot."""
        presence = (
            "absent-selector-to-present",
            "present-selector-to-absent",
            "absent-env-names-to-empty",
            "empty-env-names-to-absent",
        )
        for name in presence:
            case = self.case("delta_cases", name)
            snapshots = case["snapshots"]
            pins = sorted(snapshots)
            old = snapshots[pins[0]]["mcp"]
            new = snapshots[pins[1]]["mcp"]
            self.assertTrue(validate.e1_mcp_changed(old, new), name)
            self.assertEqual(case["expected"]["trigger"], ["figma-devmode"], name)
            self.assertEqual(case["expected"]["revision_a"]["hint"], validate.E1_HINT_DELTA, name)
            self.assertEqual(
                case["expected"]["revision_b"]["diagnostic"],
                "profile_update_confirmation_required",
                name,
            )
        for name in ("absent-env-names-to-empty", "empty-env-names-to-absent"):
            case = self.case("delta_cases", name)
            snapshots = case["snapshots"]
            pins = sorted(snapshots)
            old = dict(snapshots[pins[0]]["mcp"])
            new = dict(snapshots[pins[1]]["mcp"])
            old.setdefault("env_names", [])
            old.setdefault("environments", [])
            new.setdefault("env_names", [])
            new.setdefault("environments", [])
            self.assertFalse(validate.e1_mcp_changed(old, new), name)
        padded = copy.deepcopy(self.vector)
        for name in ("absent-env-names-to-empty", "empty-env-names-to-absent"):
            case = self.case("delta_cases", name, padded)
            for snapshot in case["snapshots"].values():
                snapshot["mcp"].setdefault("env_names", [])
        with self.assertRaises(validate.ValidationFailure) as raised:
            self.run_gate(vector=padded)
        self.assertIn("section 9.2 delta rule", str(raised.exception))


class CodexSeedVectorTests(unittest.TestCase):
    """The E3 codex-seed provisioning/posture gate must fail closed.

    validate_environments_codex_seed_vectors is the production gate:
    tools/validate.py main() runs it on every `make validate`, recomputing
    the section 7.4 provisioning outcome (seeded members and values,
    snapshot names, diagnostic and hint, marker seed record) from the
    parsed native config.toml and the seed rule revision, and the section
    12 posture rows from the manager-shipped revision and the home's
    recorded seed revision. Each test narrows one rule and proves the gate
    rejects what the rule must reject, including the review round-1
    branch-collapse replacements.
    """

    def setUp(self) -> None:
        self.vector = validate.load_json(
            validate.SUITE / "vectors" / "environments-codex-seed.json"
        )

    def case(self, family: str, name: str, vector: dict | None = None) -> dict:
        source = self.vector if vector is None else vector
        return next(item for item in source[family] if item["name"] == name)

    def run_gate(self, vector=None) -> None:
        validate.validate_environments_codex_seed_vectors(
            vector=self.vector if vector is None else vector,
        )

    def replace_body(self, changed: dict, family: str, target: str, source: str) -> None:
        donor = self.case(family, source, changed)
        recipient = self.case(family, target, changed)
        for key in list(recipient):
            if key != "name":
                del recipient[key]
        for key, value in donor.items():
            if key != "name":
                recipient[key] = copy.deepcopy(value)

    def test_published_vector_passes(self) -> None:
        self.run_gate()

    def test_review_mutant_strip_case_replaced_with_no_server_case_is_rejected(self) -> None:
        # The review round-1 mutant: the B-strip case body replaced with
        # the internally consistent no-server case under the same name.
        changed = copy.deepcopy(self.vector)
        self.replace_body(changed, "provisioning_cases", "b-strips-servers-keeps-rest", "b-without-servers-no-warning")
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_strip_case_replaced_with_subtable_only_case_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.replace_body(changed, "provisioning_cases", "b-strips-servers-keeps-rest", "b-subtable-only-form-stripped")
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_copy_case_replaced_with_inline_case_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.replace_body(changed, "provisioning_cases", "a-copies-whole-with-servers", "a-inline-table-form-inherited")
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_provisioning_revision_flip_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("provisioning_cases", "b-strips-servers-keeps-rest", changed)["revision"] = "A"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_provisioning_retained_table_dropped_from_fixture_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("provisioning_cases", "b-strips-servers-keeps-rest", changed)
        case["native_config_toml"] = case["native_config_toml"].replace("[tui]\ntheme = \"dark\"\n\n", "")
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_provisioning_retained_value_mutation_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("provisioning_cases", "b-strips-servers-keeps-rest", changed)
        case["expected"]["seeded_members"]["model"] = "gpt-5-mini"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_provisioning_diagnostic_silenced_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("provisioning_cases", "b-strips-servers-keeps-rest", changed)["expected"]["diagnostic"] = None
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_provisioning_warnings_not_interchangeable(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("provisioning_cases", "a-copies-whole-with-servers", changed)["expected"]["diagnostic"] = (
            "mcp_native_servers_not_inherited"
        )
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)
        changed = copy.deepcopy(self.vector)
        self.case("provisioning_cases", "b-strips-servers-keeps-rest", changed)["expected"]["diagnostic"] = (
            "mcp_native_servers_ungoverned"
        )
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_provisioning_hint_without_warning_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("provisioning_cases", "b-strips-servers-keeps-rest", changed)["expected"]["migration_hint"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)
        changed = copy.deepcopy(self.vector)
        self.case("provisioning_cases", "a-without-servers-no-warning", changed)["expected"]["migration_hint"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_provisioning_record_revision_mismatch_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("provisioning_cases", "b-strips-servers-keeps-rest", changed)
        case["expected"]["codex_seed_record"]["revision"] = "A"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)
        changed = copy.deepcopy(self.vector)
        case = self.case("provisioning_cases", "b-strips-servers-keeps-rest", changed)
        case["expected"]["codex_seed_record"]["revision"] = "C"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_provisioning_record_names_unsorted_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("provisioning_cases", "b-strips-servers-keeps-rest", changed)
        case["expected"]["codex_seed_record"]["native_mcp_servers"] = ["gh", "figma"]
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_provisioning_record_extra_member_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("provisioning_cases", "b-strips-servers-keeps-rest", changed)
        case["expected"]["codex_seed_record"]["commands"] = ["npx"]
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_provisioning_invalid_toml_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("provisioning_cases", "b-strips-servers-keeps-rest", changed)
        case["native_config_toml"] += "\n[unclosed"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_provisioning_seeded_flag_flip_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("provisioning_cases", "b-strips-servers-keeps-rest", changed)
        case["expected"]["seeded_has_mcp_servers"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_provisioning_seeded_members_reorder_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("provisioning_cases", "b-strips-servers-keeps-rest", changed)
        case["expected"]["seeded_top_level_members"] = ["tui", "projects", "model"]
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_provisioning_names_truncation_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("provisioning_cases", "b-strips-servers-keeps-rest", changed)
        case["expected"]["names"] = ["figma"]
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_posture_unknown_adapter_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("posture_cases", "a-home-lists-ungoverned", changed)["environment"] = "cursor"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_provisioning_extra_case_key_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("provisioning_cases", "b-strips-servers-keeps-rest", changed)["notes"] = "stale annotation"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_provisioning_non_table_mcp_servers_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("provisioning_cases", "b-empty-mcp-servers-table-no-warning", changed)
        case["native_config_toml"] = case["native_config_toml"].replace("[mcp_servers]\n", "mcp_servers = \"x\"\n")
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_posture_migration_case_replaced_with_same_revision_home_is_rejected(self) -> None:
        # The F2 replacement: the B-manager/A-home case body replaced with
        # the A/A case under the same name must fail on the shipped pin.
        changed = copy.deepcopy(self.vector)
        self.replace_body(changed, "posture_cases", "a-home-unstripped-under-b", "a-home-lists-ungoverned")
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_posture_migration_case_replaced_with_stripped_home_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.replace_body(changed, "posture_cases", "a-home-unstripped-under-b", "b-home-lists-not-inherited")
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_posture_unstripped_dropped_from_migration_case_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("posture_cases", "a-home-unstripped-under-b", changed)
        case["expected"]["status_diagnostics"] = ["mcp_native_servers_ungoverned"]
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_posture_repair_hint_rides_only_unstripped(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("posture_cases", "pre-rule-home-unstripped-under-b", changed)["expected"]["repair_hint"] = False
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)
        changed = copy.deepcopy(self.vector)
        self.case("posture_cases", "b-home-lists-not-inherited", changed)["expected"]["repair_hint"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_posture_cross_adapter_record_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("posture_cases", "non-codex-home-without-record-no-rows", changed)
        case["codex_seed_record"] = {"revision": "B", "native_mcp_servers": []}
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_posture_names_mismatch_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("posture_cases", "a-home-lists-ungoverned", changed)["expected"]["names_listed"] = []
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_posture_row_non_current_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("posture_cases", "a-home-unstripped-under-b", changed)["expected"]["row_current"] = False
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_dropped_provisioning_case_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        changed["provisioning_cases"] = [
            item for item in changed["provisioning_cases"] if item["name"] != "b-empty-mcp-servers-table-no-warning"
        ]
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_dropped_posture_case_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        changed["posture_cases"] = [
            item for item in changed["posture_cases"] if item["name"] != "a-home-unstripped-under-b"
        ]
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_revision_string_mutation_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        changed["revision_b"] = "flip release: the codex_cli seed strips everything"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(vector=changed)

    def test_derivation_corners_beyond_corpus(self) -> None:
        # Totality of the posture derivation for input combinations the
        # corpus does not carry: an empty A snapshot under a B manager
        # warns nothing, and a stripped B record never reports unstripped.
        self.assertEqual(
            validate.e3_expected_posture("B", "codex_cli", "A", []),
            {
                "codex_seed_row": "B",
                "status_diagnostics": [],
                "names_listed": [],
                "listed_as": "none",
                "repair_hint": False,
                "row_current": True,
            },
        )
        self.assertEqual(
            validate.e3_expected_posture("A", "codex_cli", "B", ["figma"]),
            {
                "codex_seed_row": "A",
                "status_diagnostics": ["mcp_native_servers_not_inherited"],
                "names_listed": ["figma"],
                "listed_as": "not-inherited",
                "repair_hint": False,
                "row_current": True,
            },
        )

    def test_gate_is_registered_in_main(self) -> None:
        import inspect

        self.assertIn("validate_environments_codex_seed_vectors", inspect.getsource(validate.main))


class ContextVersionVectorTests(unittest.TestCase):
    """The environments.md section 1.3/1.4 gate must fail closed.

    validate_context_version_vectors runs on every `make validate`. The
    Python semver, range, and resolution implementation is independent of
    the Go generator; each test mutates one expectation and proves the gate
    rejects it instead of trusting the file.
    """

    def setUp(self) -> None:
        self.vector = validate.load_json(
            validate.SUITE / "vectors" / "context-versions.json"
        )

    def resolution(self, name: str, vector: dict) -> dict:
        return next(item for item in vector["resolution_cases"] if item["name"] == name)

    def test_generated_vector_passes(self) -> None:
        validate.validate_context_version_vectors(self.vector)

    def test_coercion_table_is_exact(self) -> None:
        expected = {
            "1.2": [[">=1.2.0", "<1.3.0-0"]], ">1.2": [[">=1.3.0"]], "<3": [["<3.0.0-0"]],
            "<=1.2": [["<1.3.0-0"]], "^0.0.3": [[">=0.0.3", "<0.0.4-0"]], "^0": [[">=0.0.0", "<1.0.0-0"]],
            "~1": [[">=1.0.0", "<2.0.0-0"]], "latest": [["*"]],
        }
        for text, sets in expected.items():
            parsed = validate.range_parse(text)
            self.assertEqual([[validate.comparator_text(c) for c in s] for s in parsed], sets, text)
        for text in ("1.2.3 - 2.3.4", "v1.2.3", "", "^1 ||", "1.2.3+build"):
            with self.assertRaises(validate.RangeInvalid):
                validate.range_parse(text)

    def test_prerelease_rule(self) -> None:
        sat = lambda r, v: validate.range_satisfies(validate.range_parse(r), validate.semver_parse(v))
        self.assertTrue(sat("^2.0.0-rc.0", "2.0.0-rc.1"))
        self.assertFalse(sat("^2.0.0-rc.0", "2.1.0-rc.1"))
        self.assertFalse(sat("*", "2.0.0-rc.1"))
        self.assertFalse(sat("<3", "3.0.0-rc.1"))
        self.assertTrue(sat("<3", "2.9.9"))

    def test_flipped_satisfies_case_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        changed["satisfies_cases"][0]["satisfies"] = not changed["satisfies_cases"][0]["satisfies"]
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_context_version_vectors(changed)

    def test_stale_comparator_set_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = next(item for item in changed["range_cases"] if item["range"] == "^1.2.3")
        case["comparator_sets"] = [[">=1.2.3", "<2.0.0"]]
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_context_version_vectors(changed)

    def test_excluded_form_cannot_be_declared_valid(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = next(item for item in changed["range_cases"] if item["range"] == "1.2.3 - 2.3.4")
        case["valid"] = True
        case["comparator_sets"] = [[">=1.2.3", "<=2.3.4"]]
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_context_version_vectors(changed)

    def test_build_metadata_tag_cannot_be_a_candidate(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = next(item for item in changed["version_cases"] if item["tag"] == "v1.2.3+build.5")
        case.update({"candidate": True, "version": "1.2.3", "major": 1, "minor": 2, "patch": 3, "prerelease": []})
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_context_version_vectors(changed)

    def test_stale_lock_hash_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        changed["lock_cases"][0]["lock_sha256"] = "sha256:" + "0" * 64
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_context_version_vectors(changed)
        changed = copy.deepcopy(self.vector)
        self.resolution("worked-example-default-policy", changed)["expected"]["lock_sha256"] = "sha256:" + "0" * 64
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_context_version_vectors(changed)

    def test_hand_edited_lock_bytes_are_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = changed["lock_cases"][0]
        case["ccj1_bytes"] = case["ccj1_bytes"].replace(",", ", ", 1)
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_context_version_vectors(changed)

    def test_expected_lock_version_mutation_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        lock = self.resolution("downward-reselection", changed)["expected"]["lock"]
        for member in lock["members"]:
            if member["name"] == "lib":
                member["version"] = "2.0.0"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_context_version_vectors(changed)

    def test_conflict_cannot_be_declared_resolved(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.resolution("range-conflict-empty-intersection", changed)
        good = self.resolution("worked-example-default-policy", changed)["expected"]
        case["expected"] = copy.deepcopy(good)
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_context_version_vectors(changed)

    def test_conflict_detail_is_recomputed(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.resolution("range-conflict-empty-intersection", changed)
        case["expected"]["detail"]["candidates"] = []
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_context_version_vectors(changed)

    def test_weight_warning_cannot_be_dropped(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.resolution("weight-conflict-root-map-wins", changed)["expected"]["warnings"] = []
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_context_version_vectors(changed)

    def test_prerelease_input_narrowing_changes_the_lock(self) -> None:
        # Dropping the prerelease from the requirement makes 2.0.0-rc.1
        # inadmissible: the resolver must select 1.9.0 and the stale lock fails.
        changed = copy.deepcopy(self.vector)
        case = self.resolution("prerelease-admission", changed)
        packages = case["input"]["packages"]
        for manifest in packages["root"]["commits"].values():
            manifest["requires"][0]["range"] = "^1"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_context_version_vectors(changed)
        lock, _ = validate.resolve_closure(case["input"])
        self.assertEqual(next(m for m in lock["members"] if m["name"] == "core")["version"], "1.9.0")

    def test_dropped_required_case_fails_closed(self) -> None:
        changed = copy.deepcopy(self.vector)
        changed["resolution_cases"] = [item for item in changed["resolution_cases"] if item["name"] != "downward-reselection"]
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_context_version_vectors(changed)


class ContextDetectorVectorTests(unittest.TestCase):
    """The environments.md section 9.1 detector gate must fail closed."""

    def setUp(self) -> None:
        self.vector = validate.load_json(
            validate.SUITE / "vectors" / "context-detectors.json"
        )

    def case(self, name: str, vector: dict) -> dict:
        return next(item for item in vector["cases"] if item["name"] == name)

    def test_generated_vector_passes(self) -> None:
        validate.validate_context_detector_vectors(self.vector)

    def test_shifted_span_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        finding = self.case("secret-aws-access-key", changed)["expected"]["findings"][0]
        finding["span"] = [finding["span"][0] + 1, finding["span"][1] + 1]
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_context_detector_vectors(changed)

    def test_dropped_finding_is_rejected(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("secret-in-mcp-args", changed)
        case["expected"]["findings"] = []
        case["expected"]["installs"] = True
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_context_detector_vectors(changed)

    def test_pin_cannot_clear_a_finding(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("pin-does-not-clear-finding", changed)
        case["expected"]["installs"] = True
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_context_detector_vectors(changed)

    def test_waiver_cannot_widen_beyond_its_span(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("waived-span-clears-only-itself", changed)
        for finding in case["expected"]["findings"]:
            finding["waived"] = True
            finding["waiver_reason"] = case["waivers"][0]["reason"]
        case["expected"]["installs"] = True
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_context_detector_vectors(changed)

    def test_placeholder_cannot_be_reported(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("placeholder-example-key", changed)
        case["expected"]["findings"] = [{"class": "context-secret-material", "pattern": "aws-access-key-id", "file": "context/00-base.md", "span": [16, 36], "severity": "blocking", "waived": False}]
        case["expected"]["installs"] = False
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_context_detector_vectors(changed)

    def test_system_module_warning_cannot_be_dropped(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("system-module-present", changed)["expected"]["warnings"] = []
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_context_detector_vectors(changed)

    def test_pattern_class_cannot_be_widened(self) -> None:
        changed = copy.deepcopy(self.vector)
        changed["pattern_classes"].append({"pattern": "sha256-digest", "regexp": "(sha256:[0-9a-f]{64})", "group": 1, "placeholder_prefix": ""})
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_context_detector_vectors(changed)

    def test_invalid_manifest_case_asserts_nothing(self) -> None:
        changed = copy.deepcopy(self.vector)
        case = self.case("secret-aws-access-key", changed)
        case["files"]["agent-context.json"] = '{"schema_version":1,"name":"companyA"}\n'
        # A valid manifest without context still validates; make it invalid.
        case["files"]["agent-context.json"] = '{"schema_version":2,"name":"companyA","version":"1.0.0"}\n'
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_context_detector_vectors(changed)


class SnapshotAcquisitionVectorTests(unittest.TestCase):
    """The environments.md section 1.2 byte-exactness gate must fail closed.

    validate_snapshot_acquisition_vectors runs on every `make validate`. Each
    test narrows one rule: a normalized fixture byte, a stale hash, or a
    dropped .gitattributes entry must be rejected, not silently re-hashed.
    """

    def copy_suite(self, root: Path) -> None:
        fixture = validate.SUITE / "fixtures" / "byte-exact"
        for path in fixture.rglob("*"):
            if path.is_file():
                target = root / path.relative_to(validate.SUITE)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(path.read_bytes())
        (root / "vectors").mkdir()
        (root / "vectors" / "snapshot-acquisition.json").write_bytes(
            (validate.SUITE / "vectors" / "snapshot-acquisition.json").read_bytes()
        )
        (root / "expected").mkdir()
        (root / "expected" / "byte-exact-snapshot_sha256.txt").write_bytes(
            (validate.SUITE / "expected" / "byte-exact-snapshot_sha256.txt").read_bytes()
        )

    def test_published_vector_passes(self) -> None:
        validate.validate_snapshot_acquisition_vectors()

    def test_crlf_normalized_by_a_checkout_fails(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            self.copy_suite(root)
            crlf = root / "fixtures" / "byte-exact" / "crlf.txt"
            crlf.write_bytes(crlf.read_bytes().replace(b"\r\n", b"\n"))
            with self.assertRaises(validate.ValidationFailure):
                validate.validate_snapshot_acquisition_vectors(suite_root=root)

    def test_expanded_export_subst_fails(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            self.copy_suite(root)
            subst = root / "fixtures" / "byte-exact" / "subst.txt"
            subst.write_bytes(subst.read_bytes().replace(b"$Format:%H$", b"0" * 40))
            with self.assertRaises(validate.ValidationFailure):
                validate.validate_snapshot_acquisition_vectors(suite_root=root)

    def test_hash_that_omits_gitattributes_fails(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            self.copy_suite(root)
            fixture = root / "fixtures" / "byte-exact"
            files = {
                p.name: p.read_bytes()
                for p in fixture.iterdir()
                if p.name != ".gitattributes"
            }
            vector = validate.load_json(root / "vectors" / "snapshot-acquisition.json")
            vector["cases"][0]["expected_sha256"] = validate.environment_content_hash(files)
            with self.assertRaises(validate.ValidationFailure):
                validate.validate_snapshot_acquisition_vectors(vector, suite_root=root)

    def test_stale_expected_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            self.copy_suite(root)
            (root / "expected" / "byte-exact-snapshot_sha256.txt").write_bytes(
                b"sha256:" + b"0" * 64 + b"\n"
            )
            with self.assertRaises(validate.ValidationFailure):
                validate.validate_snapshot_acquisition_vectors(suite_root=root)


class ShellHookTrustVectorTests(unittest.TestCase):
    """Negative shapes for the section 8 trust-gate vector: each one narrows
    one rule (sourcing outcome, fixture digest, record shape, forged-record
    rejection, warning count) so that the gate must fail."""

    def setUp(self) -> None:
        self.vector = validate.load_json(
            validate.SUITE / "vectors" / "shell-hook-trust.json"
        )

    def case(self, name: str, vector=None) -> dict:
        for item in (vector or self.vector)["cases"]:
            if item["name"] == name:
                return item
        raise AssertionError(f"shell-hook-trust case {name} is missing")

    def test_published_vector_passes(self) -> None:
        validate.validate_shell_hook_trust_vectors()

    def test_flipped_sourcing_outcome_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("changed-env-sh-B-enforcing-not-sourced", changed)["sourced"] = True
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_shell_hook_trust_vectors(changed)

    def test_stale_fixture_digest_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        changed["fixtures"]["env-sh-v1"]["sha256"] = "0" * 64
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_shell_hook_trust_vectors(changed)

    def test_observed_digest_detached_from_fixture_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("approved-env-sh-A-warning-sourced", changed)["observed_sha256"] = (
            changed["fixtures"]["env-sh-v2-changed"]["sha256"]
        )
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_shell_hook_trust_vectors(changed)

    def test_forged_record_authorizing_bytes_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        forged = self.case(
            "forged-project-record-env-sh-B-enforcing-not-sourced", changed
        )
        forged["diagnostic"] = None
        forged["sourced"] = True
        forged["warns_once_per_shell_session"] = False
        forged["warning_first_activation"] = False
        forged["warnings_total_across_two_activations"] = 0
        forged["warning_names_path"] = False
        forged["warning_names_approval_command"] = False
        forged["migration_hint_names_approval_command"] = False
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_shell_hook_trust_vectors(changed)

    def test_repeated_warning_in_same_session_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        repeated = self.case("unapproved-env-sh-B-enforcing-not-sourced", changed)
        repeated["warning_second_activation_same_session"] = True
        repeated["warnings_total_across_two_activations"] = 2
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_shell_hook_trust_vectors(changed)

    def test_record_with_extra_member_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        self.case("approved-env-sh-A-warning-sourced", changed)[
            "manager_approval_record"
        ]["source"] = "manager"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_shell_hook_trust_vectors(changed)

    def test_dropped_case_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        changed["cases"] = [
            item
            for item in changed["cases"]
            if item["name"] != "forged-project-record-env-sh-A-warning-sourced-with-warning"
        ]
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_shell_hook_trust_vectors(changed)


class SecurityPostureVectorTests(unittest.TestCase):
    """Negative shapes for the section 7.1 hardened-defaults vector.

    Each test narrows one rule of validate_security_posture_vectors: the
    warn-first revision defaults, the lock direction, the three profile
    refusals, the explicit-null versus absent distinction, the gate-notice
    artifact naming, the warning count, the status-check currency
    verdict, and the codex-seed row presence, order, and shipped
    revision. The scenario-substitution tests perform exactly the
    replacements producer rule 7 forbids: a named negative case rewritten
    as an internally consistent passing case under the same name.
    """

    def setUp(self) -> None:
        self.vector = validate.load_json(
            validate.SUITE / "vectors" / "security-posture.json"
        )

    def case(self, name: str, vector=None) -> dict:
        for item in (vector or self.vector)["cases"]:
            if item["name"] == name:
                return item
        raise AssertionError(f"security-posture case {name} is missing")

    def test_published_vector_passes(self) -> None:
        validate.validate_security_posture_vectors()

    def test_flipped_revision_default_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        for entry in changed["rollout_revisions"]:
            if entry["name"] == "B":
                entry["posture_default"] = "permissive"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_security_posture_vectors(changed)

    def test_refusal_rewritten_as_passing_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        rewritten = self.case("refusal-source-allowlist-empty-explicit", changed)
        rewritten["machine"]["allowed_sources"] = [
            "https://github.com/example/skills"
        ]
        rewritten["expected"]["effective"]["allowed_sources"] = [
            "https://github.com/example/skills"
        ]
        rewritten["expected"]["diagnostics"] = []
        rewritten["expected"]["outcome"] = "proceeds"
        for rows in (
            rewritten["expected"]["curator_status_rows"],
            rewritten["expected"]["env_status_rows"],
        ):
            for row in rows:
                if row["gate"] == "source-allowlist":
                    row["value"] = 1
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_security_posture_vectors(changed)

    def test_refusal_expected_flipped_alone_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        flipped = self.case("refusal-source-allowlist-empty-explicit", changed)
        flipped["expected"]["diagnostics"] = []
        flipped["expected"]["outcome"] = "proceeds"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_security_posture_vectors(changed)

    def test_explicit_null_rewritten_as_absent_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        rewritten = self.case("refusal-passable-env-null", changed)
        del rewritten["machine"]["environments"]["passable_env_names"]
        rewritten["expected"]["effective"]["passable_env_names"] = []
        rewritten["expected"]["sources"]["passable_env_names"] = "profile"
        rewritten["expected"]["passable_env_null_explicit"] = False
        rewritten["expected"]["diagnostics"] = []
        rewritten["expected"]["outcome"] = "proceeds"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_security_posture_vectors(changed)

    def test_absent_null_claimed_explicit_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        flipped = self.case("hardened-absent-passthrough-follows-s4-warn", changed)
        flipped["expected"]["passable_env_null_explicit"] = True
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_security_posture_vectors(changed)

    def test_locked_posture_downgraded_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        downgraded = self.case("locked-posture-beats-explicit-permissive", changed)
        downgraded["system"]["security_posture"] = "permissive"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_security_posture_vectors(changed)

    def test_explicit_advisory_claimed_locked_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        flipped = self.case("explicit-knob-beats-profile-default", changed)
        flipped["expected"]["sources"]["audit_mode"] = "lock"
        for rows in (
            flipped["expected"]["curator_status_rows"],
            flipped["expected"]["env_status_rows"],
        ):
            for row in rows:
                if row["gate"] == "audit-mode":
                    row["source"] = "lock"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_security_posture_vectors(changed)

    def test_superseded_provenance_profile_default_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        changed["provenance"] = ["profile-default", "explicit", "lock", "shipped"]
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_security_posture_vectors(changed)
        changed = copy.deepcopy(self.vector)
        flawed = self.case("revision-A-default-permissive-status", changed)
        flawed["expected"]["profile_source"] = "profile-default"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_security_posture_vectors(changed)
        changed = copy.deepcopy(self.vector)
        flawed = self.case("revision-A-default-permissive-status", changed)
        flawed["expected"]["sources"]["audit_mode"] = "profile-default"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_security_posture_vectors(changed)
        changed = copy.deepcopy(self.vector)
        flawed = self.case("revision-A-default-permissive-status", changed)
        for row in flawed["expected"]["curator_status_rows"]:
            if row["gate"] == "audit-mode":
                row["source"] = "profile-default"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_security_posture_vectors(changed)

    def test_superseded_provenance_locked_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        changed["provenance"] = ["profile", "explicit", "locked", "shipped"]
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_security_posture_vectors(changed)
        changed = copy.deepcopy(self.vector)
        flawed = self.case("locked-value-beats-explicit", changed)
        flawed["expected"]["sources"]["audit_mode"] = "locked"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_security_posture_vectors(changed)
        changed = copy.deepcopy(self.vector)
        flawed = self.case("locked-posture-beats-explicit-permissive", changed)
        flawed["expected"]["profile_source"] = "locked"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_security_posture_vectors(changed)
        changed = copy.deepcopy(self.vector)
        flawed = self.case("locked-value-beats-explicit", changed)
        for row in flawed["expected"]["env_status_rows"]:
            if row["gate"] == "audit-mode":
                row["source"] = "locked"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_security_posture_vectors(changed)

    def test_unreachable_without_artifacts_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        unnamed = self.case("unreachable-registry-permissive-warns", changed)
        unnamed["operation"]["artifacts_without_evidence"] = []
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_security_posture_vectors(changed)

    def test_hardened_notice_downgraded_to_warning_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        downgraded = self.case("unreachable-registry-hardened-refuses", changed)
        downgraded["expected"]["diagnostics"][0]["severity"] = "warning"
        downgraded["expected"]["outcome"] = "proceeds"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_security_posture_vectors(changed)

    def test_mcp_error_downgraded_to_warning_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        downgraded = self.case(
            "refusal-mcp-allowlist-empty-with-declarations", changed
        )
        downgraded["expected"]["diagnostics"][0]["severity"] = "warning"
        downgraded["expected"]["outcome"] = "proceeds"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_security_posture_vectors(changed)

    def test_warning_count_flipped_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        repeated = self.case("revision-A-permissive-warning-once-install", changed)
        repeated["expected"]["diagnostics"][0]["count"] = 2
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_security_posture_vectors(changed)

    def test_status_check_contradiction_claimed_current_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        flipped = self.case(
            "hardened-contradiction-status-check-non-current", changed
        )
        flipped["expected"]["outcome"] = "current"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_security_posture_vectors(changed)

    def test_schema1_with_posture_knob_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        knobbed = self.case("schema1-machine-is-permissive", changed)
        knobbed["machine"]["security_posture"] = "hardened"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_security_posture_vectors(changed)

    def test_dropped_case_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        changed["cases"] = [
            item
            for item in changed["cases"]
            if item["name"] != "posture-rows-flipped-revisions"
        ]
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_security_posture_vectors(changed)

    def test_codex_seed_row_dropped_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        dropped = self.case("revision-A-default-permissive-status", changed)
        for rows in (
            dropped["expected"]["curator_status_rows"],
            dropped["expected"]["env_status_rows"],
        ):
            rows[:] = [row for row in rows if row["gate"] != "codex-seed"]
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_security_posture_vectors(changed)

    def test_codex_seed_row_misplaced_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        moved = self.case("revision-A-default-permissive-status", changed)
        for rows in (
            moved["expected"]["curator_status_rows"],
            moved["expected"]["env_status_rows"],
        ):
            names = [row["gate"] for row in rows]
            seed = names.index("codex-seed")
            boundary = names.index("store-boundary")
            rows[seed], rows[boundary] = rows[boundary], rows[seed]
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_security_posture_vectors(changed)

    def test_codex_seed_shipped_revision_rewritten_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        rewritten = self.case("revision-A-default-permissive-status", changed)
        rewritten["shipped_revisions"]["codex_seed"] = "B"
        profile, profile_source, effective, sources, null_explicit = (
            validate._posture_resolve(rewritten["name"], rewritten)
        )
        want_curator, want_env = validate._posture_status_rows(
            rewritten, profile, profile_source, effective, sources
        )
        rewritten["expected"]["curator_status_rows"] = want_curator
        rewritten["expected"]["env_status_rows"] = want_env
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_security_posture_vectors(changed)

    def test_mcp_refusal_rewritten_as_permissive_warning_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        rewritten = self.case(
            "refusal-mcp-allowlist-empty-with-declarations", changed
        )
        rewritten["machine"]["security_posture"] = "permissive"
        profile, profile_source, effective, sources, null_explicit = (
            validate._posture_resolve(rewritten["name"], rewritten)
        )
        expected = rewritten["expected"]
        expected.update(
            profile=profile,
            profile_source=profile_source,
            effective=effective,
            sources=sources,
            passable_env_null_explicit=null_explicit,
            diagnostics=validate._posture_diagnostics(
                rewritten["name"], rewritten, profile, effective, null_explicit
            ),
            outcome="proceeds",
        )
        want_curator, want_env = validate._posture_status_rows(
            rewritten, profile, profile_source, effective, sources
        )
        expected["curator_status_rows"] = want_curator
        expected["env_status_rows"] = want_env
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_security_posture_vectors(changed)

    def test_revision_a_default_swapped_with_locked_case_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        donor = copy.deepcopy(self.case("locked-value-beats-explicit"))
        donor["name"] = "revision-A-default-permissive-status"
        changed["cases"] = [
            donor if item["name"] == donor["name"] else item
            for item in changed["cases"]
        ]
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_security_posture_vectors(changed)

    def test_revision_b_flip_swapped_with_schema1_case_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        donor = copy.deepcopy(self.case("schema1-machine-is-permissive"))
        donor["name"] = "revision-B-default-hardened-flip-install"
        changed["cases"] = [
            donor if item["name"] == donor["name"] else item
            for item in changed["cases"]
        ]
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_security_posture_vectors(changed)

    def test_no_whole_case_substitution_survives(self) -> None:
        bodies = {item["name"]: item for item in self.vector["cases"]}
        self.assertEqual(set(bodies), validate.SECURITY_POSTURE_CASES)
        for target in sorted(bodies):
            for donor_name in sorted(bodies):
                if donor_name == target:
                    continue
                changed = copy.deepcopy(self.vector)
                donor = copy.deepcopy(bodies[donor_name])
                donor["name"] = target
                changed["cases"] = [
                    donor if item["name"] == target else item
                    for item in changed["cases"]
                ]
                with self.assertRaises(
                    validate.ValidationFailure,
                    msg=f"{target} <- {donor_name} survived",
                ):
                    validate.validate_security_posture_vectors(changed)


class WriteNofollowVectorTests(unittest.TestCase):
    """The environments §8.3.1 nofollow write discipline must fail closed.

    Each test narrows one rule of
    validate_environments_write_nofollow_vectors: a write through a
    symlinked parent, an unauthorized takeover claimed as replaced, a
    touched foreign target, a backup that dereferences the replaced link,
    a private-destination link answered with the foreign-manager stop, a
    scenario substitution under a retained name, or a dropped case must be
    rejected.
    """

    def setUp(self) -> None:
        self.vector = validate.load_json(
            validate.SUITE / "vectors" / "environments-write-nofollow.json"
        )

    def case(self, name: str, vector=None) -> dict:
        for item in (vector or self.vector)["cases"]:
            if item["name"] == name:
                return item
        raise AssertionError(f"environments-write-nofollow case {name} is missing")

    def run_main_with_vector(self, vector: dict) -> tuple[int, str]:
        """Run the real validate.main() against a substituted on-disk corpus.

        The mutated vector is written to the worktree with the manifest and
        rc.9 pins recomputed around it, so the only failing check can be the
        nofollow gate itself; all three files are restored byte-identical
        afterwards.
        """
        vector_path = validate.SUITE / "vectors" / "environments-write-nofollow.json"
        manifest_path = validate.SUITE / "manifest.json"
        rc9_path = validate.ROOT / "release" / "1.0.0-rc.9.json"
        originals = {path: path.read_bytes() for path in (vector_path, manifest_path, rc9_path)}
        try:
            vector_bytes = (json.dumps(vector, indent=2, sort_keys=True) + "\n").encode("utf-8")
            vector_path.write_bytes(vector_bytes)
            manifest = json.loads(originals[manifest_path].decode("utf-8"))
            for entry in manifest["files"]:
                if entry["path"] == "vectors/environments-write-nofollow.json":
                    entry["sha256"] = "sha256:" + hashlib.sha256(vector_bytes).hexdigest()
            manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
            manifest_path.write_bytes(manifest_bytes)
            release = json.loads(originals[rc9_path].decode("utf-8"))
            manifest_digest = "sha256:" + hashlib.sha256(manifest_bytes).hexdigest()
            release["candidate_protocol_pin"]["manifest_sha256"] = manifest_digest
            release["downstream_consumption"]["required_manifest_sha256"] = manifest_digest
            rc9_path.write_bytes((json.dumps(release, indent=2, sort_keys=True) + "\n").encode("utf-8"))
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                status = validate.main()
            return status, stderr.getvalue()
        finally:
            for path, payload in originals.items():
                path.write_bytes(payload)
            for path, payload in originals.items():
                if path.read_bytes() != payload:
                    raise AssertionError(f"{path} was not restored byte-identical")

    def test_published_vector_passes(self) -> None:
        validate.validate_environments_write_nofollow_vectors()

    def test_substituted_scenario_rejected_through_main(self) -> None:
        """Every retained name refuses an internally consistent foreign body.

        Producer rule 7: substituting another branch's passing case under a
        retained name must be rejected by the validator entry point, not
        merely inventoried. Each substitution runs through validate.main()
        against a repinned on-disk corpus.
        """
        for name in sorted(validate.WRITE_NOFOLLOW_CASES):
            with self.subTest(case=name):
                donor_name = (
                    "materialize-recorded-file-replaced"
                    if name == "materialize-clean-path-written"
                    else "materialize-clean-path-written"
                )
                donor = copy.deepcopy(self.case(donor_name))
                changed = copy.deepcopy(self.vector)
                for index, item in enumerate(changed["cases"]):
                    if item["name"] == name:
                        changed["cases"][index] = dict(donor, name=name)
                status, stderr = self.run_main_with_vector(changed)
                self.assertEqual(status, 1)
                self.assertIn("pinned scenario", stderr)

    def test_parent_link_followed_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        refused = self.case("materialize-symlinked-parent-refused", changed)
        refused["expected"]["outcome"] = "written"
        refused["expected"]["diagnostic"] = None
        refused["expected"]["entry_after"] = "managed-file"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_write_nofollow_vectors(changed)

    def test_authorized_parent_traversal_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        refused = self.case("takeover-symlinked-parent-authorized-still-refused", changed)
        refused["expected"]["outcome"] = "replaced"
        refused["expected"]["diagnostic"] = None
        refused["expected"]["entry_after"] = "managed-file"
        refused["expected"]["backup_holds_link"] = True
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_write_nofollow_vectors(changed)

    def test_unauthorized_takeover_replaced_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        stopped = self.case("takeover-symlinked-target-unauthorized-stopped", changed)
        stopped["expected"]["outcome"] = "replaced"
        stopped["expected"]["diagnostic"] = None
        stopped["expected"]["entry_after"] = "managed-file"
        stopped["expected"]["backup_holds_link"] = True
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_write_nofollow_vectors(changed)

    def test_touched_foreign_target_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        replaced = self.case("takeover-symlinked-target-authorized-replaced", changed)
        replaced["expected"]["foreign_target_sha256_after"] = "0" * 64
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_write_nofollow_vectors(changed)

    def test_stale_fixture_digest_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        changed["fixtures"]["foreign-notes"]["sha256"] = "0" * 64
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_write_nofollow_vectors(changed)

    def test_missing_link_backup_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        replaced = self.case("takeover-symlinked-target-authorized-replaced", changed)
        replaced["expected"]["backup_holds_link"] = False
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_write_nofollow_vectors(changed)

    def test_wrong_refusal_code_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        refused = self.case("takeover-inside-link-unauthorized-unmanaged-conflict", changed)
        refused["expected"]["diagnostic"] = "environment_write_would_follow_link"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_write_nofollow_vectors(changed)

    def test_backup_target_link_foreign_manager_code_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        refused = self.case("backup-symlinked-target-refused", changed)
        refused["expected"]["diagnostic"] = "environment_foreign_manager_detected"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_write_nofollow_vectors(changed)

    def test_backup_target_link_claimed_replaced_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        refused = self.case("backup-symlinked-target-refused", changed)
        refused["expected"]["outcome"] = "replaced"
        refused["expected"]["diagnostic"] = None
        refused["expected"]["entry_after"] = "managed-file"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_write_nofollow_vectors(changed)

    def test_dropped_case_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        changed["cases"] = [
            item
            for item in changed["cases"]
            if item["name"] != "repair-planted-link-replaced"
        ]
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_write_nofollow_vectors(changed)


class DotfileManagersVectorTests(unittest.TestCase):
    """The environments §9.5 dotfile-manager state table must fail closed.

    Each test narrows one rule of
    validate_environments_dotfile_managers_vectors: a table row or cell
    that drifts from the pinned table, a resolved path that drifts from
    the XDG resolution rules, a notice that misnames the first-present
    manager or fires on a symlink, a blocking heuristic, a quiet case
    rewritten as suspected (or the reverse) under a retained name, or a
    dropped case must be rejected.
    """

    VECTOR_PATH = "vectors/environments-dotfile-managers.json"

    def setUp(self) -> None:
        self.vector = validate.load_json(validate.SUITE / self.VECTOR_PATH)

    def case(self, name: str, vector=None) -> dict:
        for item in (vector or self.vector)["cases"]:
            if item["name"] == name:
                return item
        raise AssertionError(f"environments-dotfile-managers case {name} is missing")

    def run_main_with_vector(self, vector: dict) -> tuple[int, str]:
        """Run the real validate.main() against a substituted on-disk corpus.

        The mutated vector is written to the worktree with the manifest and
        rc.9 pins recomputed around it, so the only failing check can be the
        dotfile-managers gate itself; all three files are restored
        byte-identical afterwards.
        """
        vector_path = validate.SUITE / self.VECTOR_PATH
        manifest_path = validate.SUITE / "manifest.json"
        rc9_path = validate.ROOT / "release" / "1.0.0-rc.9.json"
        originals = {path: path.read_bytes() for path in (vector_path, manifest_path, rc9_path)}
        try:
            vector_bytes = (json.dumps(vector, indent=2, sort_keys=True) + "\n").encode("utf-8")
            vector_path.write_bytes(vector_bytes)
            manifest = json.loads(originals[manifest_path].decode("utf-8"))
            for entry in manifest["files"]:
                if entry["path"] == self.VECTOR_PATH:
                    entry["sha256"] = "sha256:" + hashlib.sha256(vector_bytes).hexdigest()
            manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
            manifest_path.write_bytes(manifest_bytes)
            release = json.loads(originals[rc9_path].decode("utf-8"))
            manifest_digest = "sha256:" + hashlib.sha256(manifest_bytes).hexdigest()
            release["candidate_protocol_pin"]["manifest_sha256"] = manifest_digest
            release["downstream_consumption"]["required_manifest_sha256"] = manifest_digest
            rc9_path.write_bytes((json.dumps(release, indent=2, sort_keys=True) + "\n").encode("utf-8"))
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                status = validate.main()
            return status, stderr.getvalue()
        finally:
            for path, payload in originals.items():
                path.write_bytes(payload)
            for path, payload in originals.items():
                if path.read_bytes() != payload:
                    raise AssertionError(f"{path} was not restored byte-identical")

    def test_published_vector_passes(self) -> None:
        validate.validate_environments_dotfile_managers_vectors()

    def test_substituted_scenario_rejected_through_main(self) -> None:
        """Every retained name refuses an internally consistent foreign body.

        Producer rule 7: substituting another branch's passing case under a
        retained name must be rejected by the validator entry point, not
        merely inventoried. Each substitution runs through validate.main()
        against a repinned on-disk corpus.
        """
        names = sorted(validate.DOTFILE_CASES)
        for name in names:
            with self.subTest(case=name):
                donor_name = names[1] if name == names[0] else names[0]
                donor = copy.deepcopy(self.case(donor_name))
                changed = copy.deepcopy(self.vector)
                for index, item in enumerate(changed["cases"]):
                    if item["name"] == name:
                        changed["cases"][index] = dict(donor, name=name)
                status, stderr = self.run_main_with_vector(changed)
                self.assertEqual(status, 1)
                self.assertIn("pinned scenario", stderr)

    def test_table_row_order_swap_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        changed["table"] = swapped(changed["table"], 1, 2)
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_dotfile_managers_vectors(changed)

    def test_table_manager_order_swap_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        changed["managers"] = swapped(changed["managers"], 0, 2)
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_dotfile_managers_vectors(changed)

    def test_table_none_cell_given_a_location_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        for row in changed["table"]:
            if row["manager"] == "stow":
                row["linux"] = {"base": "XDG_DATA_HOME", "leaf": "stow"}
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_dotfile_managers_vectors(changed)

    def test_table_cell_base_swap_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        for row in changed["table"]:
            if row["manager"] == "home-manager":
                row["linux"] = {"base": "XDG_DATA_HOME", "leaf": "home-manager"}
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_dotfile_managers_vectors(changed)

    def test_present_rewritten_quiet_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        suspected = self.case("chezmoi-linux-present-suspected", changed)
        suspected["states"]["chezmoi"] = "absent"
        suspected["expected"]["notice"] = None
        suspected["expected"]["names_manager"] = None
        suspected["expected"]["resolved_path"] = None
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_dotfile_managers_vectors(changed)

    def test_quiet_rewritten_suspected_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        quiet = self.case("linux-all-absent-quiet", changed)
        quiet["states"]["yadm"] = "directory"
        quiet["expected"]["notice"] = "environment_foreign_manager_suspected"
        quiet["expected"]["names_manager"] = "yadm"
        quiet["expected"]["resolved_path"] = "/home/operator/.local/share/yadm"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_dotfile_managers_vectors(changed)

    def test_none_cell_inspected_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        quiet = self.case("windows-all-absent-quiet", changed)
        quiet["states"]["home-manager"] = "absent"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_dotfile_managers_vectors(changed)

    def test_wrong_diagnostic_spelling_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        suspected = self.case("yadm-linux-present-suspected", changed)
        suspected["expected"]["notice"] = "environment_foreign_manager_detected"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_dotfile_managers_vectors(changed)

    def test_blocking_heuristic_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        suspected = self.case("chezmoi-macos-present-suspected", changed)
        suspected["expected"]["blocks"] = True
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_dotfile_managers_vectors(changed)

    def test_resolved_path_drift_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        suspected = self.case("home-manager-linux-present-suspected", changed)
        suspected["expected"]["resolved_path"] = "/home/operator/.config/home-manager.d"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_dotfile_managers_vectors(changed)

    def test_symlink_claiming_suspected_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        quiet = self.case("chezmoi-linux-symlink-quiet", changed)
        quiet["expected"]["notice"] = "environment_foreign_manager_suspected"
        quiet["expected"]["names_manager"] = "chezmoi"
        quiet["expected"]["resolved_path"] = "/home/operator/.local/share/chezmoi"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_dotfile_managers_vectors(changed)

    def test_unreadable_claiming_suspected_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        quiet = self.case("home-manager-linux-unreadable-quiet", changed)
        quiet["expected"]["notice"] = "environment_foreign_manager_suspected"
        quiet["expected"]["names_manager"] = "home-manager"
        quiet["expected"]["resolved_path"] = "/home/operator/.config/home-manager"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_dotfile_managers_vectors(changed)

    def test_xdg_relocated_claiming_default_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        relocated = self.case("chezmoi-linux-xdg-data-home-relocated", changed)
        relocated["expected"]["resolved_path"] = "/home/operator/.local/share/chezmoi"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_dotfile_managers_vectors(changed)

    def test_xdg_empty_claiming_relocated_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        defaulted = self.case("chezmoi-linux-xdg-data-home-empty-uses-default", changed)
        defaulted["expected"]["resolved_path"] = "/chezmoi"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_dotfile_managers_vectors(changed)

    def test_home_manager_relative_claiming_relocated_fails(self) -> None:
        """A relative XDG_CONFIG_HOME resolves to the default, not the relative path.

        Upstream home-manager would follow the relative value
        (${XDG_CONFIG_HOME:-$HOME/.config} with no absolute-path check);
        the section 9.5 heuristic deliberately falls back to the default,
        so a case claiming the upstream-style relocated path must fail.
        """
        changed = copy.deepcopy(self.vector)
        defaulted = self.case("home-manager-linux-xdg-config-home-relative-uses-default", changed)
        defaulted["expected"]["resolved_path"] = "rel/cfg/home-manager"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_dotfile_managers_vectors(changed)

    def test_precedence_winner_swapped_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        precedence = self.case("linux-chezmoi-and-yadm-names-chezmoi", changed)
        precedence["expected"]["names_manager"] = "yadm"
        precedence["expected"]["resolved_path"] = "/home/operator/.local/share/yadm"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_dotfile_managers_vectors(changed)

    def test_manager_private_relocation_key_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        relocated = self.case("yadm-macos-xdg-data-home-relocated", changed)
        relocated["env"] = {"YADM_DATA": "/Volumes/data"}
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_dotfile_managers_vectors(changed)

    def test_dropped_case_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        changed["cases"] = [
            item
            for item in changed["cases"]
            if item["name"] != "macos-home-manager-and-yadm-names-home-manager"
        ]
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_dotfile_managers_vectors(changed)


class ReadFailureVectorTests(unittest.TestCase):
    """The environments §8.4.1 absence-versus-read-failure gate must fail closed.

    Each test narrows one rule of
    validate_environments_read_failure_vectors: an unreadable marker, lock,
    seed, passthrough entry, or backup-record inventory answered with its
    absence-shaped outcome, a lock repair or update that rebuilds or writes,
    a failure class collapsed onto another, a currency or repair disposition
    relaxed, a scenario substitution under a retained name, a negative
    rewritten as a passing case or as a different violation, or a dropped
    case must be rejected.
    """

    def setUp(self) -> None:
        self.vector = validate.load_json(
            validate.SUITE / "vectors" / "environments-read-failure.json"
        )

    def case(self, name: str, vector=None) -> dict:
        for item in (vector or self.vector)["cases"]:
            if item["name"] == name:
                return item
        raise AssertionError(f"environments-read-failure case {name} is missing")

    def run_main_with_vector(self, vector: dict) -> tuple[int, str]:
        """Run the real validate.main() against a substituted on-disk corpus.

        The mutated vector is written to the worktree with the manifest and
        rc.9 pins recomputed around it, so the only failing check can be the
        read-failure gate itself; all three files are restored byte-identical
        afterwards.
        """
        vector_path = validate.SUITE / "vectors" / "environments-read-failure.json"
        manifest_path = validate.SUITE / "manifest.json"
        rc9_path = validate.ROOT / "release" / "1.0.0-rc.9.json"
        originals = {path: path.read_bytes() for path in (vector_path, manifest_path, rc9_path)}
        try:
            vector_bytes = (json.dumps(vector, indent=2, sort_keys=True) + "\n").encode("utf-8")
            vector_path.write_bytes(vector_bytes)
            manifest = json.loads(originals[manifest_path].decode("utf-8"))
            for entry in manifest["files"]:
                if entry["path"] == "vectors/environments-read-failure.json":
                    entry["sha256"] = "sha256:" + hashlib.sha256(vector_bytes).hexdigest()
            manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
            manifest_path.write_bytes(manifest_bytes)
            release = json.loads(originals[rc9_path].decode("utf-8"))
            manifest_digest = "sha256:" + hashlib.sha256(manifest_bytes).hexdigest()
            release["candidate_protocol_pin"]["manifest_sha256"] = manifest_digest
            release["downstream_consumption"]["required_manifest_sha256"] = manifest_digest
            rc9_path.write_bytes((json.dumps(release, indent=2, sort_keys=True) + "\n").encode("utf-8"))
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                status = validate.main()
            return status, stderr.getvalue()
        finally:
            for path, payload in originals.items():
                path.write_bytes(payload)
            for path, payload in originals.items():
                if path.read_bytes() != payload:
                    raise AssertionError(f"{path} was not restored byte-identical")

    def test_published_vector_passes(self) -> None:
        validate.validate_environments_read_failure_vectors()

    def test_substituted_scenario_rejected_through_main(self) -> None:
        """Every retained name refuses an internally consistent foreign body.

        Producer rule 7: substituting another branch's passing case under a
        retained name must be rejected by the validator entry point, not
        merely inventoried. Each substitution runs through validate.main()
        against a repinned on-disk corpus.
        """
        for name in sorted(validate.READ_FAILURE_CASES):
            with self.subTest(case=name):
                donor_name = (
                    "marker-absent-unprovisioned-stale"
                    if self.case(name)["file_class"] != "marker"
                    else "seed-absent-not-seeded-provisioned"
                )
                donor = copy.deepcopy(self.case(donor_name))
                changed = copy.deepcopy(self.vector)
                for index, item in enumerate(changed["cases"]):
                    if item["name"] == name:
                        changed["cases"][index] = dict(donor, name=name)
                status, stderr = self.run_main_with_vector(changed)
                self.assertEqual(status, 1)
                self.assertIn("pinned scenario", stderr)

    def test_unreadable_marker_reported_stale_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        unreadable = self.case("marker-open-permission-denied-unreadable", changed)
        unreadable["expected"] = dict(validate.READ_FAILURE_NEGATIVES["marker-unreadable-reported-stale"])
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_read_failure_vectors(changed)

    def test_unreadable_lock_reported_unknown_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        unreadable = self.case("lock-read-io-error-untrusted", changed)
        unreadable["expected"] = dict(validate.READ_FAILURE_NEGATIVES["lock-unreadable-reported-unknown"])
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_read_failure_vectors(changed)

    def test_unreadable_seed_provisioned_through_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        unreadable = self.case("seed-open-permission-denied-unreadable", changed)
        unreadable["expected"] = dict(validate.READ_FAILURE_NEGATIVES["seed-unreadable-skipped-as-absent"])
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_read_failure_vectors(changed)

    def test_unreadable_passthrough_reported_detached_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        unreadable = self.case("passthrough-lstat-permission-denied-unreadable", changed)
        unreadable["expected"] = dict(
            validate.READ_FAILURE_NEGATIVES["passthrough-unreadable-reported-detached"]
        )
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_read_failure_vectors(changed)

    def test_lock_repair_rebuild_or_write_fails(self) -> None:
        """A repair against an unreadable lock rebuilds nothing and writes nothing."""
        for field in ("rebuilt", "written"):
            with self.subTest(field=field):
                changed = copy.deepcopy(self.vector)
                refused = self.case("lock-unreadable-repair-refused-no-rebuild", changed)
                refused["expected"][field] = True
                with self.assertRaises(validate.ValidationFailure):
                    validate.validate_environments_read_failure_vectors(changed)

    def test_lock_update_unknown_or_rebuild_fails(self) -> None:
        """An update against an unreadable lock refuses as untrusted, never unknown."""
        changed = copy.deepcopy(self.vector)
        refused = self.case("lock-unreadable-update-refused-no-rebuild", changed)
        refused["expected"]["diagnostic"] = "profile_unknown"
        refused["expected"]["currency"] = "known"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_read_failure_vectors(changed)
        changed = copy.deepcopy(self.vector)
        refused = self.case("lock-unreadable-update-refused-no-rebuild", changed)
        refused["expected"]["rebuilt"] = True
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_read_failure_vectors(changed)

    def test_backup_unreadable_reported_empty_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        unreadable = self.case("backup-record-unreadable-status-unknown", changed)
        unreadable["expected"] = dict(
            validate.READ_FAILURE_NEGATIVES["backup-record-unreadable-reported-empty"]
        )
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_read_failure_vectors(changed)

    def test_backup_restore_write_or_silence_fails(self) -> None:
        """A restore against an unreadable inventory stops with its diagnostic."""
        changed = copy.deepcopy(self.vector)
        stopped = self.case("backup-record-unreadable-restore-stops", changed)
        stopped["expected"]["written"] = True
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_read_failure_vectors(changed)
        changed = copy.deepcopy(self.vector)
        stopped = self.case("backup-record-unreadable-restore-stops", changed)
        stopped["expected"]["diagnostic"] = None
        stopped["expected"]["currency"] = "known"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_read_failure_vectors(changed)

    def test_failure_class_collapse_refused(self) -> None:
        """Collapsing every failure class onto one is refused per scenario.

        Producer rule 7: the mutant keeps each case internally consistent —
        only the pinned failure class (and the entry shape it implies)
        changes — so only scenario pinning can catch it.
        """
        for name in sorted(validate.READ_FAILURE_CASES):
            pinned = validate.READ_FAILURE_SCENARIOS[name]
            if pinned["failure_class"] is None or pinned["failure_class"] == "permission-denied":
                continue
            with self.subTest(case=name):
                changed = copy.deepcopy(self.vector)
                collapsed = self.case(name, changed)
                collapsed["failure_class"] = "permission-denied"
                collapsed["entry_kind"] = (
                    "symlink" if pinned["file_class"] == "passthrough" else "file"
                )
                with self.assertRaises(validate.ValidationFailure):
                    validate.validate_environments_read_failure_vectors(changed)

    def test_relaxed_currency_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        unreadable = self.case("lock-parent-not-directory-untrusted", changed)
        unreadable["expected"]["currency"] = "known"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_read_failure_vectors(changed)

    def test_repair_relinks_relaxed_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        unreadable = self.case("passthrough-readlink-io-error-unreadable", changed)
        unreadable["expected"]["repair_relinks"] = True
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_read_failure_vectors(changed)

    def test_absent_rewritten_as_unreadable_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        absent = self.case("marker-absent-unprovisioned-stale", changed)
        absent["presence"] = "present"
        absent["entry_kind"] = "file"
        absent["failure_class"] = "permission-denied"
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_read_failure_vectors(changed)

    def test_negative_rewritten_as_passing_fails(self) -> None:
        """A negative rewritten as an internally consistent passing case fails.

        Producer rule 7: for every negative, the absence-shaped observation
        is replaced by the derived correct verdict and the negative verdict
        is removed; the pinned refusal must still catch the retained name.
        """
        for name, inputs in validate.READ_FAILURE_SCENARIOS.items():
            if name not in validate.READ_FAILURE_NEGATIVES:
                continue
            with self.subTest(case=name):
                changed = copy.deepcopy(self.vector)
                rewritten = self.case(name, changed)
                rewritten["expected"] = validate._read_failure_expected(
                    inputs["file_class"],
                    inputs["operation"],
                    inputs["presence"],
                    inputs["entry_kind"],
                    inputs["failure_class"],
                )
                del rewritten["conforming"]
                del rewritten["reason"]
                with self.assertRaises(validate.ValidationFailure):
                    validate.validate_environments_read_failure_vectors(changed)

    def test_negative_rewritten_as_other_violation_fails(self) -> None:
        """A negative rewritten as a different violation still fails.

        The negative pins the exact absence-shaped observation it refuses,
        not merely 'some violation': a stall reported as a fragment-emitting
        success under the retained negative name must be refused.
        """
        changed = copy.deepcopy(self.vector)
        rewritten = self.case("marker-unreadable-reported-stale", changed)
        rewritten["expected"] = {
            "diagnostic": None,
            "fragment_emitted": True,
            "row_current": True,
            "currency": "known",
        }
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_read_failure_vectors(changed)

    def test_dropped_case_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        changed["cases"] = [
            item
            for item in changed["cases"]
            if item["name"] != "passthrough-unreadable-resolve-no-fragment"
        ]
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_read_failure_vectors(changed)

    def test_relaxed_closed_set_fails(self) -> None:
        changed = copy.deepcopy(self.vector)
        changed["diagnostics"] = [
            code for code in changed["diagnostics"] if code != "profile_unknown"
        ]
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_read_failure_vectors(changed)


class UmbrellaProviderVectorTests(unittest.TestCase):
    """The environments §11 trust-root gate must fail closed.

    Each test narrows one rule of validate_umbrella_provider_vectors: an
    unknown diagnostic, a warning claimed under revision B, a warning with
    no migration-hint directory, a resolve-and-refuse outcome, a dropped
    case, or a semantic mismatch against the §11 resolver model (PATH
    selection, precedence, executable filtering, published/managed refusal,
    missing/untrusted/unreadable distinction, hint and path details) must
    be rejected.
    """

    def mutated_vector(self, root: Path, mutate) -> None:
        vector = validate.load_json(
            validate.SUITE / "vectors" / "umbrella-provider-resolution.json"
        )
        mutate(vector)
        vectors = root / "vectors"
        vectors.mkdir(parents=True, exist_ok=True)
        (vectors / "umbrella-provider-resolution.json").write_text(
            json.dumps(vector), encoding="utf-8"
        )

    def case(self, vector, name: str) -> dict:
        for item in vector["cases"]:
            if item["name"] == name:
                return item
        raise AssertionError(f"no umbrella provider case {name}")

    def test_published_vector_passes(self) -> None:
        validate.validate_umbrella_provider_vectors()

    def test_unknown_diagnostic_fails(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            self.mutated_vector(
                root,
                lambda v: self.case(v, "provider-missing").__setitem__(
                    "revision_a",
                    {"resolved": None, "diagnostic": "subcommand_provider_evil"},
                ),
            )
            with self.assertRaisesRegex(validate.ValidationFailure, "unknown diagnostic"):
                validate.validate_umbrella_provider_vectors(root=root)

    def test_warning_under_revision_b_fails(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            self.mutated_vector(
                root,
                lambda v: self.case(v, "s6-planted-path-provider-warns-then-refuses").__setitem__(
                    "revision_b",
                    {
                        "resolved": "/home/operator/work/acme/.bin/curator-run",
                        "diagnostic": "subcommand_provider_outside_trust_roots",
                        "migration_hint_directory": "/home/operator/work/acme/.bin",
                    },
                ),
            )
            with self.assertRaisesRegex(validate.ValidationFailure, "outside revision A"):
                validate.validate_umbrella_provider_vectors(root=root)

    def test_warning_without_hint_directory_fails(self) -> None:
        def drop_hint(vector) -> None:
            outcome = self.case(vector, "s6-planted-path-provider-warns-then-refuses")["revision_a"]
            del outcome["migration_hint_directory"]

        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            self.mutated_vector(root, drop_hint)
            with self.assertRaisesRegex(validate.ValidationFailure, "migration-hint directory"):
                validate.validate_umbrella_provider_vectors(root=root)

    def test_resolve_and_refuse_fails(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            self.mutated_vector(
                root,
                lambda v: self.case(v, "provider-missing").__setitem__(
                    "revision_a",
                    {"resolved": "/usr/local/bin/curator-run", "diagnostic": "subcommand_provider_untrusted"},
                ),
            )
            with self.assertRaisesRegex(validate.ValidationFailure, "both resolves and refuses"):
                validate.validate_umbrella_provider_vectors(root=root)

    def test_dropped_case_fails(self) -> None:
        def drop(vector) -> None:
            vector["cases"] = [c for c in vector["cases"] if c["name"] != "provider-missing"]

        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            self.mutated_vector(root, drop)
            with self.assertRaisesRegex(validate.ValidationFailure, "inventory is not exact"):
                validate.validate_umbrella_provider_vectors(root=root)

    def test_s6_revision_b_silent_resolution_mutant_fails(self) -> None:
        """The reviewer's mutant: a PATH-only provider resolving under B."""

        def resolve(vector) -> None:
            self.case(vector, "s6-planted-path-provider-warns-then-refuses")["revision_b"] = {
                "resolved": "/home/operator/work/acme/.bin/curator-run",
                "diagnostic": None,
            }

        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            self.mutated_vector(root, resolve)
            with self.assertRaisesRegex(validate.ValidationFailure, "§11 model expects"):
                validate.validate_umbrella_provider_vectors(root=root)

    def test_revision_a_trust_selection_mutant_fails(self) -> None:
        """Revision A must keep PATH selection, not resolve the trusted copy."""

        def resolve_trusted(vector) -> None:
            self.case(vector, "listed-directory-provider-resolved")["revision_a"] = {
                "resolved": "/opt/curator/providers/curator-run",
                "diagnostic": None,
            }

        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            self.mutated_vector(root, resolve_trusted)
            with self.assertRaisesRegex(validate.ValidationFailure, "§11 model expects"):
                validate.validate_umbrella_provider_vectors(root=root)

    def test_listed_order_second_match_mutant_fails(self) -> None:
        """First listed match wins: resolving the second entry must fail."""

        def resolve_second(vector) -> None:
            self.case(vector, "listed-order-first-match-wins")["revision_b"] = {
                "resolved": "/srv/team/curator-providers/curator-run",
                "diagnostic": None,
            }

        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            self.mutated_vector(root, resolve_second)
            with self.assertRaisesRegex(validate.ValidationFailure, "§11 model expects"):
                validate.validate_umbrella_provider_vectors(root=root)

    def test_non_executable_resolves_mutant_fails(self) -> None:
        """A non-executable trust-root file is skipped, never resolved."""

        def resolve_non_executable(vector) -> None:
            self.case(vector, "non-executable-in-trust-root-skipped")["revision_b"] = {
                "resolved": "/opt/curator/providers/curator-run",
                "diagnostic": None,
            }

        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            self.mutated_vector(root, resolve_non_executable)
            with self.assertRaisesRegex(validate.ValidationFailure, "§11 model expects"):
                validate.validate_umbrella_provider_vectors(root=root)

    def test_published_dispatch_mutant_fails(self) -> None:
        """A manager-published candidate is refused, never dispatched."""

        def dispatch(vector) -> None:
            self.case(vector, "manager-published-directory-refused")["revision_b"] = {
                "resolved": "/home/operator/.curator/bin/curator-run",
                "diagnostic": None,
            }

        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            self.mutated_vector(root, dispatch)
            with self.assertRaisesRegex(validate.ValidationFailure, "§11 model expects"):
                validate.validate_umbrella_provider_vectors(root=root)

    def test_untrusted_path_narrowing_fails(self) -> None:
        """A refusal naming the wrong path is rejected, not just a delete."""

        def wrong_path(vector) -> None:
            outcome = self.case(vector, "s6-planted-path-provider-warns-then-refuses")["revision_b"]
            outcome["untrusted_path"] = "/usr/local/bin/curator-run"

        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            self.mutated_vector(root, wrong_path)
            with self.assertRaisesRegex(validate.ValidationFailure, "untrusted_path"):
                validate.validate_umbrella_provider_vectors(root=root)

    def test_trust_roots_consulted_narrowing_fails(self) -> None:
        """A warning naming the wrong consulted roots is rejected."""

        def wrong_roots(vector) -> None:
            outcome = self.case(vector, "s6-planted-path-provider-warns-then-refuses")["revision_a"]
            outcome["trust_roots_consulted"] = ["/opt/curator/bin", "/wrong"]

        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            self.mutated_vector(root, wrong_roots)
            with self.assertRaisesRegex(validate.ValidationFailure, "trust_roots_consulted"):
                validate.validate_umbrella_provider_vectors(root=root)

    def test_path_only_reports_missing_mutant_fails(self) -> None:
        """A PATH-only provider is untrusted under B, never missing."""

        def report_missing(vector) -> None:
            self.case(vector, "s6-planted-path-provider-warns-then-refuses")["revision_b"] = {
                "resolved": None,
                "diagnostic": "subcommand_provider_missing",
                "trust_roots_consulted": ["/opt/curator/bin"],
            }

        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            self.mutated_vector(root, report_missing)
            with self.assertRaisesRegex(validate.ValidationFailure, "§11 model expects"):
                validate.validate_umbrella_provider_vectors(root=root)

    def test_unreadable_reports_absence_mutant_fails(self) -> None:
        """An unreadable root is a failure, never absence or a fallback."""

        def report_missing(vector) -> None:
            self.case(vector, "unreadable-listed-directory-fails")["revision_b"] = {
                "resolved": None,
                "diagnostic": "subcommand_provider_missing",
                "trust_roots_consulted": ["/opt/curator/bin", "/opt/gone"],
            }

        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            self.mutated_vector(root, report_missing)
            with self.assertRaisesRegex(validate.ValidationFailure, "§11 model expects"):
                validate.validate_umbrella_provider_vectors(root=root)

    def test_unreadable_directory_narrowing_fails(self) -> None:
        """An unreadable failure naming the wrong directory is rejected."""

        def wrong_directory(vector) -> None:
            outcome = self.case(vector, "unreadable-listed-directory-fails")["revision_b"]
            outcome["unreadable_directory"] = "/opt/curator/bin"

        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            self.mutated_vector(root, wrong_directory)
            with self.assertRaisesRegex(validate.ValidationFailure, "unreadable_directory"):
                validate.validate_umbrella_provider_vectors(root=root)

    def test_migration_hint_narrowing_fails(self) -> None:
        """A warning hint naming the wrong directory is rejected."""

        def wrong_hint(vector) -> None:
            outcome = self.case(vector, "s6-planted-path-provider-warns-then-refuses")["revision_a"]
            outcome["migration_hint_directory"] = "/usr/local/bin"

        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            self.mutated_vector(root, wrong_hint)
            with self.assertRaisesRegex(validate.ValidationFailure, "migration_hint_directory"):
                validate.validate_umbrella_provider_vectors(root=root)

    def test_warning_silenced_mutant_fails(self) -> None:
        """An outside-roots PATH selection must warn, never resolve silently."""

        def silence(vector) -> None:
            self.case(vector, "s6-planted-path-provider-warns-then-refuses")["revision_a"] = {
                "resolved": "/home/operator/work/acme/.bin/curator-run",
                "diagnostic": None,
            }

        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            self.mutated_vector(root, silence)
            with self.assertRaisesRegex(validate.ValidationFailure, "§11 model expects"):
                validate.validate_umbrella_provider_vectors(root=root)


class ManagerConfigVectorTests(unittest.TestCase):
    """Negative shapes for the manager-config vector gate: each one flips a
    vector, the schema, or the section 12.1 table so that the gate must fail."""

    def setUp(self) -> None:
        self.vector = validate.load_json(validate.SUITE / "vectors" / "manager-config.json")
        self.vector_v2 = validate.load_json(validate.SUITE / "vectors" / "manager-config-v2.json")
        _, paths = validate.schema_registry()
        self.schema = validate.load_json(paths["manager-config-v2.schema.json"])
        self.text = (validate.ROOT / "protocol" / "environments.md").read_text(encoding="utf-8")

    def case(self, name: str) -> dict:
        for case in [*self.vector, *self.vector_v2]:
            if case["name"] == name:
                return case
        raise AssertionError(name)

    def run_gate(self, vector=None, vector_v2=None, schema=None, text=None) -> None:
        validate.validate_manager_config_vectors(
            vector=self.vector if vector is None else vector,
            vector_v2=self.vector_v2 if vector_v2 is None else vector_v2,
            schema=self.schema if schema is None else schema,
            environments_text=self.text if text is None else text,
        )

    def test_published_vectors_pass(self) -> None:
        self.run_gate()

    def test_forged_valid_flag_on_rejected_vector_fails(self) -> None:
        self.case("schema2-negative-backup-retention")["valid"] = True
        with self.assertRaisesRegex(validate.ValidationFailure, "expected valid=True"):
            self.run_gate()

    def test_accepted_vector_flagged_invalid_fails(self) -> None:
        self.case("schema2-every-knob")["valid"] = False
        with self.assertRaisesRegex(validate.ValidationFailure, "expected valid=False"):
            self.run_gate()

    def test_schema_one_vector_carrying_environments_stays_rejected(self) -> None:
        self.case("schema1-rejects-environments")["valid"] = True
        with self.assertRaisesRegex(validate.ValidationFailure, "schema1-rejects-environments"):
            self.run_gate()

    def test_insecure_registry_is_a_semantic_rejection_on_both_schemas(self) -> None:
        self.assertEqual(
            validate.manager_config_semantic_error(
                {"audit_registries": [{"name": "r", "url": "http://r.example"}]}
            ),
            "audit registry r is not https",
        )
        self.assertIsNone(
            validate.manager_config_semantic_error(
                {"audit_registries": [{"name": "r", "url": "https://r.example"}]}
            )
        )
        self.case("insecure-registry")["valid"] = True
        with self.assertRaisesRegex(validate.ValidationFailure, "insecure-registry"):
            self.run_gate()

    def test_expected_environments_must_be_defaults_plus_input(self) -> None:
        self.case("schema2-minimal-defaults")["expected"]["environments"]["backup_retention"] = 6
        with self.assertRaisesRegex(validate.ValidationFailure, "defaults plus input"):
            self.run_gate()

    def test_schema_default_drifting_from_the_table_fails(self) -> None:
        self.schema["$defs"]["environments"]["properties"]["backup_retention"]["default"] = 6
        with self.assertRaisesRegex(validate.ValidationFailure, "default for backup_retention is 6"):
            self.run_gate()

    def test_nested_default_drifting_from_the_table_fails(self) -> None:
        self.schema["$defs"]["precedence"]["properties"]["winner"]["default"] = "lower-weight"
        with self.assertRaisesRegex(validate.ValidationFailure, "precedence.winner"):
            self.run_gate()

    def test_schema_property_missing_from_the_table_fails(self) -> None:
        properties = self.schema["$defs"]["environments"]["properties"]
        properties["backup_generations"] = properties.pop("backup_retention")
        with self.assertRaisesRegex(validate.ValidationFailure, "schema-only \\['backup_generations'\\]"):
            self.run_gate()

    def test_table_knob_missing_from_the_schema_fails(self) -> None:
        text = self.text.replace("| `backup_retention` |", "| `backup_scrub_days` | integer | `0` | 8.3 |\n| `backup_retention` |")
        with self.assertRaisesRegex(validate.ValidationFailure, "table-only \\['backup_scrub_days'\\]"):
            self.run_gate(text=text)

    def test_open_environments_object_fails(self) -> None:
        self.schema["$defs"]["environments"]["additionalProperties"] = True
        with self.assertRaisesRegex(validate.ValidationFailure, "not closed"):
            self.run_gate()

    def test_widened_enum_fails(self) -> None:
        # the scratch mutation of item 6: a value the schema admits that the
        # section 12.1 Values column does not state
        self.schema["$defs"]["precedence"]["properties"]["winner"]["enum"].append("heavier")
        with self.assertRaisesRegex(validate.ValidationFailure, "enum for precedence.winner is .*'heavier'"):
            self.run_gate()

    def test_narrowed_enum_fails(self) -> None:
        self.schema["$defs"]["environments"]["properties"]["in_place_mode"]["additionalProperties"]["enum"] = ["linked"]
        with self.assertRaisesRegex(validate.ValidationFailure, "enum for in_place_mode.<env-id> is \\['linked'\\]"):
            self.run_gate()

    def test_widened_transitive_enum_fails(self) -> None:
        self.schema["$defs"]["environments"]["properties"]["transitive_system_modules"]["enum"].append("quarantine")
        with self.assertRaisesRegex(validate.ValidationFailure, "enum for transitive_system_modules is .*'quarantine'"):
            self.run_gate()

    def test_widened_permissions_enum_fails(self) -> None:
        self.schema["$defs"]["environments"]["properties"]["permissions"]["additionalProperties"]["enum"].append("standard")
        with self.assertRaisesRegex(validate.ValidationFailure, "enum for permissions.<profile> is .*'standard'"):
            self.run_gate()

    def test_transitive_default_drifting_from_the_table_fails(self) -> None:
        self.schema["$defs"]["environments"]["properties"]["transitive_system_modules"]["default"] = "error"
        with self.assertRaisesRegex(validate.ValidationFailure, "default for transitive_system_modules is 'error'"):
            self.run_gate()

    def test_source_signers_default_drifting_from_the_table_fails(self) -> None:
        self.schema["$defs"]["environments"]["properties"]["source_signers"]["default"] = {"a": []}
        with self.assertRaisesRegex(validate.ValidationFailure, "default for source_signers"):
            self.run_gate()

    def test_require_source_signers_default_drifting_from_the_table_fails(self) -> None:
        self.schema["$defs"]["environments"]["properties"]["require_source_signers"]["default"] = True
        with self.assertRaisesRegex(validate.ValidationFailure, "default for require_source_signers is True"):
            self.run_gate()

    def test_table_value_drifting_from_the_enum_fails(self) -> None:
        text = self.text.replace("| `precedence.winner` | `higher-weight`, `lower-weight` |", "| `precedence.winner` | `higher-weight`, `lower-weight`, `heavier` |")
        self.assertNotEqual(text, self.text)
        with self.assertRaisesRegex(validate.ValidationFailure, "precedence.winner"):
            self.run_gate(text=text)

    def test_every_enum_knob_is_cross_checked(self) -> None:
        values = validate.environments_knob_values(self.text)
        closed = {knob for knob, stated in values.items() if len(stated) >= 2 and all(" " not in v for v in stated)}
        # the knobs whose Values cell is a closed literal set are exactly the cross-checked ones
        self.assertEqual(closed & set(validate.MANAGER_CONFIG_KNOB_ENUM_PATHS), set(validate.MANAGER_CONFIG_KNOB_ENUM_PATHS))
        for knob in validate.MANAGER_CONFIG_KNOB_ENUM_PATHS:
            self.assertIn(knob, values)

    def test_knob_without_a_default_fails(self) -> None:
        del self.schema["$defs"]["environments"]["properties"]["in_place_mode"]["default"]
        with self.assertRaisesRegex(validate.ValidationFailure, "without a default"):
            self.run_gate()

    def test_schema_one_family_is_byte_identical_to_the_generator_split(self) -> None:
        self.assertEqual({case["input"]["schema_version"] for case in self.vector}, {1})
        self.assertIn(2, {case["input"]["schema_version"] for case in self.vector_v2})

    def test_schema_two_case_leaking_into_the_frozen_family_fails(self) -> None:
        moved = self.case("schema2-minimal-defaults")
        leaked = [*self.vector, moved]
        rest = [case for case in self.vector_v2 if case is not moved]
        with self.assertRaisesRegex(validate.ValidationFailure, "byte-frozen schema-1 family.*\\[1, 2\\]"):
            self.run_gate(vector=leaked, vector_v2=rest)

    def test_v2_family_without_a_schema_two_case_fails(self) -> None:
        only_one = [case for case in self.vector_v2 if case["input"]["schema_version"] == 1]
        with self.assertRaisesRegex(validate.ValidationFailure, "no schema-2 case"):
            self.run_gate(vector_v2=only_one)

    def test_empty_v2_family_fails(self) -> None:
        with self.assertRaisesRegex(validate.ValidationFailure, "manager-config-v2.json is not a non-empty"):
            self.run_gate(vector_v2=[])

    def test_name_repeated_across_families_fails(self) -> None:
        with self.assertRaisesRegex(validate.ValidationFailure, "repeated: 'minimal-defaults'"):
            self.run_gate(vector_v2=[*self.vector_v2, self.case("minimal-defaults")])

    def test_missing_table_fails_rather_than_passing_vacuously(self) -> None:
        with self.assertRaisesRegex(validate.ValidationFailure, "no section 12.1"):
            self.run_gate(text="# environments without the table\n")


class SystemConfigV2SchemaTests(unittest.TestCase):
    """Negative shapes for the system-config-v2 schema gate: each one widens,
    narrows, or drifts the schema or the section 12.2 sentence so that the
    gate must fail. The unmodified inputs pass."""

    ISOLATION_ENUM = validate.SYSTEM_CONFIG_ISOLATION_ENUM_PATH
    TRANSITIVE_ENUM = validate.SYSTEM_CONFIG_TRANSITIVE_ENUM_PATH
    REQUIRE_SIGNERS_ENUM = validate.SYSTEM_CONFIG_REQUIRE_SIGNERS_ENUM_PATH
    PERMISSIONS_ENUM = validate.SYSTEM_CONFIG_PERMISSIONS_ENUM_PATH

    def setUp(self) -> None:
        _, paths = validate.schema_registry()
        self.schema = validate.load_json(paths["system-config-v2.schema.json"])
        self.schema_v1 = validate.load_json(paths["system-config-v1.schema.json"])
        self.manager = validate.load_json(paths["manager-config-v2.schema.json"])
        self.text = (validate.ROOT / "protocol" / "environments.md").read_text(encoding="utf-8")

    def run_gate(self, schema=None, schema_v1=None, manager=None, text=None) -> None:
        validate.validate_system_config_v2_schema(
            schema=self.schema if schema is None else schema,
            schema_v1=self.schema_v1 if schema_v1 is None else schema_v1,
            manager_schema=self.manager if manager is None else manager,
            environments_text=self.text if text is None else text,
        )

    def mutated(self, mutate) -> dict:
        schema = copy.deepcopy(self.schema)
        mutate(schema)
        return schema

    def test_published_inputs_pass(self) -> None:
        self.run_gate()

    def test_section_12_2_lists_the_eleven_keys_in_order(self) -> None:
        self.assertEqual(
            validate.environments_lockable_keys(self.text),
            ["overlays_allowed", "precedence", "mcp_package_allowlist", "passable_env_names",
             "require_current_profile", "transitive_system_modules", "isolation", "provider_directories",
             "source_signers", "require_source_signers", "permissions"],
        )

    def test_open_environments_object_fails(self) -> None:
        schema = self.mutated(lambda s: s["$defs"]["environments"].pop("additionalProperties"))
        with self.assertRaisesRegex(validate.ValidationFailure, "environments object is not closed"):
            self.run_gate(schema=schema)

    def test_open_root_object_fails(self) -> None:
        schema = self.mutated(lambda s: s.pop("additionalProperties"))
        with self.assertRaisesRegex(validate.ValidationFailure, "not a closed object"):
            self.run_gate(schema=schema)

    def test_extra_environments_knob_fails(self) -> None:
        def widen(s):
            s["$defs"]["environments"]["properties"]["current_profile"] = {"type": ["string", "null"]}
        with self.assertRaisesRegex(validate.ValidationFailure, "schema-only \\['current_profile'\\]"):
            self.run_gate(schema=self.mutated(widen))

    def test_missing_environments_knob_fails(self) -> None:
        schema = self.mutated(lambda s: s["$defs"]["environments"]["properties"].pop("isolation"))
        with self.assertRaisesRegex(validate.ValidationFailure, "table-only \\['isolation'\\]"):
            self.run_gate(schema=schema)

    def test_knob_grammar_not_by_reference_fails(self) -> None:
        def inline(s):
            s["$defs"]["environments"]["properties"]["overlays_allowed"] = {"type": "boolean"}
        with self.assertRaisesRegex(validate.ValidationFailure, "overlays_allowed does not take its grammar"):
            self.run_gate(schema=self.mutated(inline))

    def test_isolation_admitting_isolated_fails(self) -> None:
        def widen(s):
            node = s
            for segment in self.ISOLATION_ENUM[:-1]:
                node = node[segment]
            node["enum"] = ["shared", "isolated"]
        with self.assertRaisesRegex(validate.ValidationFailure, "permits shared alone"):
            self.run_gate(schema=self.mutated(widen))

    def test_transitive_system_modules_admitting_drop_fails(self) -> None:
        def widen(s):
            node = s
            for segment in self.TRANSITIVE_ENUM[:-1]:
                node = node[segment]
            node["enum"] = ["drop", "error"]
        with self.assertRaisesRegex(validate.ValidationFailure, "permits error alone"):
            self.run_gate(schema=self.mutated(widen))

    def test_transitive_system_modules_without_a_closed_value_set_fails(self) -> None:
        def open_values(s):
            s["$defs"]["environments"]["properties"]["transitive_system_modules"] = {"type": "string"}
        with self.assertRaisesRegex(validate.ValidationFailure, "no closed transitive_system_modules value set"):
            self.run_gate(schema=self.mutated(open_values))

    def test_require_source_signers_admitting_false_fails(self) -> None:
        def widen(s):
            node = s
            for segment in self.REQUIRE_SIGNERS_ENUM[:-1]:
                node = node[segment]
            node["enum"] = [True, False]
        with self.assertRaisesRegex(validate.ValidationFailure, "permits true alone"):
            self.run_gate(schema=self.mutated(widen))

    def test_fingerprint_with_trailing_newline_rejected_by_both_configs(self) -> None:
        registry, _ = validate.schema_registry()
        forty = "A" * 40
        cases = [
            (self.manager, {
                "schema_version": 2, "skills_root": "./skills", "projects": {},
                "environments": {"source_signers": {"github.com/example/context": [
                    {"type": "gpg", "fingerprint": forty},
                ]}},
            }),
            (self.schema, {
                "schema_version": 2,
                "locked": ["environments.source_signers"],
                "environments": {"source_signers": {"github.com/example/context": [
                    {"type": "gpg", "fingerprint": forty},
                ]}},
            }),
        ]
        for schema, instance in cases:
            validator = validate.Draft202012Validator(schema, registry=registry)
            self.assertEqual(list(validator.iter_errors(instance)), [])
            instance["environments"]["source_signers"]["github.com/example/context"][0]["fingerprint"] = forty + "\n"
            errors = list(validator.iter_errors(instance))
            self.assertTrue(errors, "a 41-character fingerprint with a trailing newline must fail")

    def test_require_source_signers_without_a_closed_value_set_fails(self) -> None:
        def open_values(s):
            s["$defs"]["environments"]["properties"]["require_source_signers"] = {"type": "boolean"}
        with self.assertRaisesRegex(validate.ValidationFailure, "no closed require_source_signers value set"):
            self.run_gate(schema=self.mutated(open_values))

    def test_isolation_without_a_closed_value_set_fails(self) -> None:
        def open_values(s):
            s["$defs"]["environments"]["properties"]["isolation"] = {"type": "object"}
        with self.assertRaisesRegex(validate.ValidationFailure, "no closed isolation value set"):
            self.run_gate(schema=self.mutated(open_values))

    def test_permissions_admitting_yolo_fails(self) -> None:
        def widen(s):
            node = s
            for segment in self.PERMISSIONS_ENUM[:-1]:
                node = node[segment]
            node["enum"] = ["native", "yolo"]
        with self.assertRaisesRegex(validate.ValidationFailure, "permits native alone"):
            self.run_gate(schema=self.mutated(widen))

    def test_permissions_without_a_closed_value_set_fails(self) -> None:
        def open_values(s):
            s["$defs"]["environments"]["properties"]["permissions"] = {"type": "object"}
        with self.assertRaisesRegex(validate.ValidationFailure, "no closed permissions value set"):
            self.run_gate(schema=self.mutated(open_values))

    def test_locked_enum_missing_a_key_fails(self) -> None:
        def drop(s):
            s["properties"]["locked"]["items"]["enum"].remove("environments.isolation")
        with self.assertRaisesRegex(validate.ValidationFailure, "locked enum is"):
            self.run_gate(schema=self.mutated(drop))

    def test_locked_enum_naming_an_unlockable_knob_fails(self) -> None:
        def widen(s):
            s["properties"]["locked"]["items"]["enum"].append("environments.current_profile")
        with self.assertRaisesRegex(validate.ValidationFailure, "locked enum is"):
            self.run_gate(schema=self.mutated(widen))

    def test_locked_without_unique_items_fails(self) -> None:
        schema = self.mutated(lambda s: s["properties"]["locked"].pop("uniqueItems"))
        with self.assertRaisesRegex(validate.ValidationFailure, "not a unique-item array"):
            self.run_gate(schema=schema)

    def test_changed_schema_one_member_fails(self) -> None:
        schema = self.mutated(lambda s: s["properties"].__setitem__("audit", {"type": "object"}))
        with self.assertRaisesRegex(validate.ValidationFailure, "changes the schema-1 shape of audit"):
            self.run_gate(schema=schema)

    def test_dropped_schema_one_member_fails(self) -> None:
        schema = self.mutated(lambda s: s["properties"].pop("projects"))
        with self.assertRaisesRegex(validate.ValidationFailure, "not schema 1 plus environments"):
            self.run_gate(schema=schema)

    def test_schema_version_not_const_two_fails(self) -> None:
        schema = self.mutated(lambda s: s["properties"].__setitem__("schema_version", {"enum": [1, 2]}))
        with self.assertRaisesRegex(validate.ValidationFailure, "schema_version is not const 2"):
            self.run_gate(schema=schema)

    def test_section_12_2_key_absent_from_12_1_fails(self) -> None:
        text = self.text.replace("`passable_env_names`, `require_current_profile`", "`passable_env_names`, `fleet_push`", 1)
        with self.assertRaisesRegex(validate.ValidationFailure, "section 12.1 does not carry: \\['fleet_push'\\]"):
            self.run_gate(text=text)

    def test_section_12_2_drift_against_schema_fails(self) -> None:
        text = self.text.replace("`provider_directories`, `source_signers`,\n`require_source_signers`, and `permissions`", "`provider_directories`", 1)
        self.assertNotEqual(text, self.text)
        with self.assertRaisesRegex(validate.ValidationFailure, "schema-only \\['permissions', 'require_source_signers', 'source_signers'\\]"):
            self.run_gate(text=text)

    def test_missing_section_12_2_fails_rather_than_passing_vacuously(self) -> None:
        with self.assertRaisesRegex(validate.ValidationFailure, "no section 12.2"):
            self.run_gate(text="# environments without the lockable text\n")

    def test_section_12_2_without_the_enumeration_fails(self) -> None:
        with self.assertRaisesRegex(validate.ValidationFailure, "no longer enumerates"):
            self.run_gate(text="### 12.2 Lockable knobs\n\nNothing is lockable.\n\n## 13\n")


class RegistryPageBoundaryVectorTests(unittest.TestCase):
    """The R1/P1 page-boundary gate must fail closed.

    validate_registry_page_boundary_vectors is the production gate:
    tools/validate.py main() runs it on every `make validate`,
    recomputing each client case's accepted, diagnostic, high-water, and
    exclusion values from its inputs. Each test narrows one rule and proves
    the gate rejects what the rule must reject.
    """

    def setUp(self) -> None:
        self.client = validate.load_json(
            validate.SUITE / "vectors" / "registry-client.json"
        )
        self.service = validate.load_json(
            validate.SUITE / "vectors" / "registry-service.json"
        )

    def case(self, name: str, vector: dict | None = None) -> dict:
        source = self.client if vector is None else vector
        return next(item for item in source["page_boundary_cases"] if item["name"] == name)

    def run_gate(self, client=None, service=None) -> None:
        validate.validate_registry_page_boundary_vectors(
            client=self.client if client is None else client,
            service=self.service if service is None else service,
        )

    def test_published_vectors_pass(self) -> None:
        self.run_gate()

    def test_stale_page_admitted_is_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        case = self.case("below-high-water-rejected", changed)
        case["accepted"] = True
        case["diagnostic"] = None
        case["registry_excluded"] = False
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_equivocated_equal_version_admitted_is_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        case = self.case("equal-version-different-body-rejected", changed)
        case["accepted"] = True
        case["diagnostic"] = None
        case["registry_excluded"] = False
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_chain_mismatch_admitted_is_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        case = self.case("chain-boundary-mismatch-rejected", changed)
        case["accepted"] = True
        case["diagnostic"] = None
        case["registry_excluded"] = False
        case["high_water_advanced"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_missing_boundary_admitted_is_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        case = self.case("missing-boundary-excluded", changed)
        case["accepted"] = True
        case["diagnostic"] = None
        case["registry_excluded"] = False
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_bad_signature_accepted_is_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        case = self.case("bad-signature-rejected", changed)
        case["accepted"] = True
        case["diagnostic"] = None
        case["registry_excluded"] = False
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_wrong_diagnostic_spelling_is_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        self.case("below-high-water-rejected", changed)["diagnostic"] = "registry_page_stale"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_swapped_diagnostics_are_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        self.case("below-high-water-rejected", changed)["diagnostic"] = (
            "registry_page_boundary_mismatch"
        )
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_missing_exclusion_is_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        self.case("below-high-water-rejected", changed)["registry_excluded"] = False
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_missing_high_water_advance_is_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        self.case("fresh-boundary-advances-high-water", changed)["high_water_advanced"] = False
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_dropped_case_is_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        changed["page_boundary_cases"] = [
            item
            for item in changed["page_boundary_cases"]
            if item["name"] != "missing-boundary-excluded"
        ]
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_dropped_emission_pin_is_rejected(self) -> None:
        changed = copy.deepcopy(self.service)
        changed["pagination"]["boundary_emitted_on_every_page"] = False
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(service=changed)

    def test_reevaluating_cursor_is_rejected(self) -> None:
        changed = copy.deepcopy(self.service)
        changed["pagination"]["cursor_boundary_cases"][0]["reevaluate_at_newer_boundary"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(service=changed)


PASSING_SCENARIO = {
    "checkpoint_configured": True,
    "signature_valid": True,
    "live_version": 8,
    "checkpoint_version": 8,
    "same_boundary_body": True,
    "prefix_reproduced": True,
    "ready": True,
    "diagnostic": None,
    "posture": None,
}

BELOW_CHECKPOINT_SCENARIO = {
    "checkpoint_configured": True,
    "signature_valid": True,
    "live_version": 7,
    "checkpoint_version": 8,
    "same_boundary_body": False,
    "prefix_reproduced": False,
    "ready": False,
    "diagnostic": "restore_below_checkpoint",
    "posture": None,
}

PREFIX_MISMATCH_SCENARIO = {
    "checkpoint_configured": True,
    "signature_valid": True,
    "live_version": 10,
    "checkpoint_version": 8,
    "same_boundary_body": False,
    "prefix_reproduced": False,
    "ready": False,
    "diagnostic": "restore_inconsistent_with_checkpoint",
    "posture": None,
}


class RegistryCheckpointVectorTests(unittest.TestCase):
    """The R3/P2 startup checkpoint gate must fail closed.

    validate_registry_checkpoint_vectors is the production gate:
    tools/validate.py main() runs it on every `make validate`,
    recomputing each checkpoint case's ready, diagnostic, and posture
    values from its inputs and pinning each required case name to its
    mandatory scenario inputs. Each test narrows one rule and proves
    the gate rejects what the rule must reject.
    """

    def setUp(self) -> None:
        self.service = validate.load_json(
            validate.SUITE / "vectors" / "registry-service.json"
        )

    def case(self, name: str, vector: dict | None = None) -> dict:
        source = self.service if vector is None else vector
        return next(item for item in source["checkpoint_cases"] if item["name"] == name)

    def run_gate(self, service=None) -> None:
        validate.validate_registry_checkpoint_vectors(
            service=self.service if service is None else service,
        )

    def test_published_vectors_pass(self) -> None:
        self.run_gate()

    def test_below_checkpoint_admitted_is_rejected(self) -> None:
        changed = copy.deepcopy(self.service)
        case = self.case("live-below-checkpoint", changed)
        case["ready"] = True
        case["diagnostic"] = None
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(service=changed)

    def test_inconsistent_equal_version_admitted_is_rejected(self) -> None:
        changed = copy.deepcopy(self.service)
        case = self.case("checkpoint-equal-inconsistent", changed)
        case["ready"] = True
        case["diagnostic"] = None
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(service=changed)

    def test_unreproduced_prefix_admitted_is_rejected(self) -> None:
        changed = copy.deepcopy(self.service)
        case = self.case("live-above-prefix-mismatch", changed)
        case["ready"] = True
        case["diagnostic"] = None
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(service=changed)

    def test_bad_signature_admitted_is_rejected(self) -> None:
        changed = copy.deepcopy(self.service)
        case = self.case("checkpoint-signature-invalid", changed)
        case["ready"] = True
        case["diagnostic"] = None
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(service=changed)

    def test_wrong_diagnostic_spelling_is_rejected(self) -> None:
        changed = copy.deepcopy(self.service)
        self.case("live-below-checkpoint", changed)["diagnostic"] = "restore_below"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(service=changed)

    def test_swapped_diagnostics_are_rejected(self) -> None:
        changed = copy.deepcopy(self.service)
        self.case("live-below-checkpoint", changed)["diagnostic"] = (
            "restore_inconsistent_with_checkpoint"
        )
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(service=changed)

    def test_dropped_posture_is_rejected(self) -> None:
        changed = copy.deepcopy(self.service)
        self.case("checkpoint-not-configured", changed)["posture"] = None
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(service=changed)

    def test_dropped_case_is_rejected(self) -> None:
        changed = copy.deepcopy(self.service)
        changed["checkpoint_cases"] = [
            item
            for item in changed["checkpoint_cases"]
            if item["name"] != "checkpoint-signature-invalid"
        ]
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(service=changed)

    def replace_scenario(self, changed: dict, name: str, scenario: dict) -> None:
        self.case(name, changed).update(copy.deepcopy(scenario))

    def test_equal_inconsistent_replaced_by_passing_is_rejected(self) -> None:
        changed = copy.deepcopy(self.service)
        self.replace_scenario(changed, "checkpoint-equal-inconsistent", PASSING_SCENARIO)
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(service=changed)

    def test_below_checkpoint_replaced_by_passing_is_rejected(self) -> None:
        changed = copy.deepcopy(self.service)
        self.replace_scenario(changed, "live-below-checkpoint", PASSING_SCENARIO)
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(service=changed)

    def test_prefix_mismatch_replaced_by_passing_is_rejected(self) -> None:
        changed = copy.deepcopy(self.service)
        self.replace_scenario(changed, "live-above-prefix-mismatch", PASSING_SCENARIO)
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(service=changed)

    def test_bad_signature_replaced_by_passing_is_rejected(self) -> None:
        changed = copy.deepcopy(self.service)
        self.replace_scenario(changed, "checkpoint-signature-invalid", PASSING_SCENARIO)
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(service=changed)

    def test_equal_consistent_replaced_by_refusal_is_rejected(self) -> None:
        changed = copy.deepcopy(self.service)
        self.replace_scenario(
            changed, "checkpoint-equal-consistent", BELOW_CHECKPOINT_SCENARIO
        )
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(service=changed)

    def test_below_live_consistent_replaced_by_refusal_is_rejected(self) -> None:
        changed = copy.deepcopy(self.service)
        self.replace_scenario(
            changed, "checkpoint-below-live-consistent", PREFIX_MISMATCH_SCENARIO
        )
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(service=changed)

    def test_not_configured_replaced_by_configured_is_rejected(self) -> None:
        changed = copy.deepcopy(self.service)
        self.replace_scenario(changed, "checkpoint-not-configured", PASSING_SCENARIO)
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(service=changed)

    def test_replacement_is_rejected_by_main_entry(self) -> None:
        changed = copy.deepcopy(self.service)
        self.case("live-below-checkpoint", changed).update(
            copy.deepcopy(PASSING_SCENARIO)
        )
        original = validate.load_json
        validate.load_json = lambda path: (
            changed
            if path == validate.SUITE / "vectors" / "registry-service.json"
            else original(path)
        )
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                with contextlib.redirect_stderr(io.StringIO()):
                    code = validate.main()
        finally:
            validate.load_json = original
        self.assertEqual(code, 1)


BOOTSTRAP_FIRST_USE_SCENARIO = {
    "phase": "bootstrap",
    "checkpoint_configured": True,
    "signature_valid": True,
    "prior_state": "missing",
    "checkpoint_version": 8,
    "stored_version": 0,
    "first_network_version": 9,
    "candidate_same_body": False,
    "group_size": 0,
    "same_log_size": False,
    "roots_equal": True,
    "policy": "advisory",
    "accepted": True,
    "state_changed": True,
    "diagnostic": None,
    "posture": None,
    "severity": None,
    "compared": False,
    "registry_excluded": False,
    "resolution_changed": False,
    "check_current": True,
}

BOOTSTRAP_TAMPERED_SCENARIO = {
    "phase": "bootstrap",
    "checkpoint_configured": True,
    "signature_valid": True,
    "prior_state": "missing",
    "checkpoint_version": 8,
    "stored_version": 0,
    "first_network_version": 7,
    "candidate_same_body": False,
    "group_size": 0,
    "same_log_size": False,
    "roots_equal": True,
    "policy": "advisory",
    "accepted": False,
    "state_changed": True,
    "diagnostic": None,
    "posture": None,
    "severity": None,
    "compared": False,
    "registry_excluded": True,
    "resolution_changed": False,
    "check_current": True,
}

BOOTSTRAP_ADVANCE_SCENARIO = {
    "phase": "rebootstrap",
    "checkpoint_configured": True,
    "signature_valid": True,
    "prior_state": "present",
    "checkpoint_version": 10,
    "stored_version": 8,
    "first_network_version": 0,
    "candidate_same_body": False,
    "group_size": 0,
    "same_log_size": False,
    "roots_equal": True,
    "policy": "advisory",
    "accepted": True,
    "state_changed": True,
    "diagnostic": None,
    "posture": None,
    "severity": None,
    "compared": False,
    "registry_excluded": False,
    "resolution_changed": False,
    "check_current": True,
}

BOOTSTRAP_NOOP_SCENARIO = {
    "phase": "rebootstrap",
    "checkpoint_configured": True,
    "signature_valid": True,
    "prior_state": "present",
    "checkpoint_version": 8,
    "stored_version": 8,
    "first_network_version": 0,
    "candidate_same_body": True,
    "group_size": 0,
    "same_log_size": False,
    "roots_equal": True,
    "policy": "advisory",
    "accepted": True,
    "state_changed": False,
    "diagnostic": None,
    "posture": None,
    "severity": None,
    "compared": False,
    "registry_excluded": False,
    "resolution_changed": False,
    "check_current": True,
}

DIVERGENCE_ADVISORY_SCENARIO = {
    "phase": "compare",
    "checkpoint_configured": False,
    "signature_valid": True,
    "prior_state": "present",
    "checkpoint_version": 0,
    "stored_version": 8,
    "first_network_version": 0,
    "candidate_same_body": True,
    "group_size": 2,
    "same_log_size": True,
    "roots_equal": False,
    "policy": "advisory",
    "accepted": True,
    "state_changed": False,
    "diagnostic": "registry_view_divergence",
    "posture": None,
    "severity": "warning",
    "compared": True,
    "registry_excluded": False,
    "resolution_changed": False,
    "check_current": True,
}

DIVERGENCE_AGREEING_SCENARIO = {
    "phase": "compare",
    "checkpoint_configured": False,
    "signature_valid": True,
    "prior_state": "present",
    "checkpoint_version": 0,
    "stored_version": 8,
    "first_network_version": 0,
    "candidate_same_body": True,
    "group_size": 2,
    "same_log_size": True,
    "roots_equal": True,
    "policy": "advisory",
    "accepted": True,
    "state_changed": False,
    "diagnostic": None,
    "posture": None,
    "severity": None,
    "compared": True,
    "registry_excluded": False,
    "resolution_changed": False,
    "check_current": True,
}


class RegistryBootstrapVectorTests(unittest.TestCase):
    """The S2 bootstrap checkpoint and view-divergence gate must fail closed.

    validate_registry_bootstrap_vectors is the production gate:
    tools/validate.py main() runs it on every `make validate`,
    recomputing each bootstrap case's accepted, state-changed,
    diagnostic, posture, severity, compared, exclusion, resolution,
    and `--check` currency values from its inputs and pinning each
    required case name to its mandatory scenario inputs. Each test
    narrows one rule and proves the gate rejects what the rule must
    reject.
    """

    def setUp(self) -> None:
        self.client = validate.load_json(
            validate.SUITE / "vectors" / "registry-client.json"
        )
        self.behavior = validate.load_json(
            validate.SUITE / "vectors" / "registry-behavior.json"
        )

    def case(self, name: str, vector: dict | None = None) -> dict:
        source = self.client if vector is None else vector
        return next(item for item in source["bootstrap_cases"] if item["name"] == name)

    def run_gate(self, client=None, behavior=None) -> None:
        validate.validate_registry_bootstrap_vectors(
            client=self.client if client is None else client,
            behavior=self.behavior if behavior is None else behavior,
        )

    def test_published_vectors_pass(self) -> None:
        self.run_gate()

    def test_below_checkpoint_network_admitted_is_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        case = self.case("checkpoint-first-network-below-tampered", changed)
        case["accepted"] = True
        case["registry_excluded"] = False
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_equal_different_network_admitted_is_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        case = self.case("checkpoint-first-network-equal-different-tampered", changed)
        case["accepted"] = True
        case["registry_excluded"] = False
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_tofu_posture_dropped_is_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        case = self.case("no-checkpoint-first-use-tofu", changed)
        case["posture"] = None
        case["severity"] = None
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_bad_signature_first_use_admitted_is_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        case = self.case("checkpoint-signature-invalid-first-use", changed)
        case["accepted"] = True
        case["state_changed"] = True
        case["registry_excluded"] = False
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_regression_admitted_is_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        case = self.case("rebootstrap-regression-refused", changed)
        case["accepted"] = True
        case["state_changed"] = True
        case["diagnostic"] = None
        case["severity"] = None
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_equal_inconsistent_regression_admitted_is_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        case = self.case("rebootstrap-equal-inconsistent-refused", changed)
        case["accepted"] = True
        case["diagnostic"] = None
        case["severity"] = None
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_bad_signature_rebootstrap_admitted_is_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        case = self.case("rebootstrap-signature-invalid-ignored", changed)
        case["accepted"] = True
        case["state_changed"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_strict_severity_downgraded_is_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        self.case("divergence-detected-strict", changed)["severity"] = "warning"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_resolution_changed_is_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        self.case("divergence-detected-advisory", changed)["resolution_changed"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_wrong_diagnostic_spelling_is_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        self.case("rebootstrap-regression-refused", changed)["diagnostic"] = (
            "registry_checkpoint_rollback"
        )
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_swapped_diagnostics_are_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        self.case("rebootstrap-regression-refused", changed)["diagnostic"] = (
            "registry_view_divergence"
        )
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_dropped_case_is_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        changed["bootstrap_cases"] = [
            item
            for item in changed["bootstrap_cases"]
            if item["name"] != "checkpoint-signature-invalid-first-use"
        ]
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def replace_scenario(self, changed: dict, name: str, scenario: dict) -> None:
        self.case(name, changed).update(copy.deepcopy(scenario))

    def test_below_tampered_replaced_by_passing_is_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        self.replace_scenario(
            changed, "checkpoint-first-network-below-tampered", BOOTSTRAP_FIRST_USE_SCENARIO
        )
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_tofu_replaced_by_checkpointed_is_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        self.replace_scenario(
            changed, "no-checkpoint-first-use-tofu", BOOTSTRAP_FIRST_USE_SCENARIO
        )
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_bad_signature_first_use_replaced_by_passing_is_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        self.replace_scenario(
            changed, "checkpoint-signature-invalid-first-use", BOOTSTRAP_FIRST_USE_SCENARIO
        )
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_regression_replaced_by_advance_is_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        self.replace_scenario(
            changed, "rebootstrap-regression-refused", BOOTSTRAP_ADVANCE_SCENARIO
        )
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_equal_inconsistent_replaced_by_noop_is_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        self.replace_scenario(
            changed, "rebootstrap-equal-inconsistent-refused", BOOTSTRAP_NOOP_SCENARIO
        )
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_divergence_replaced_by_agreeing_is_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        self.replace_scenario(
            changed, "divergence-detected-advisory", DIVERGENCE_AGREEING_SCENARIO
        )
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_strict_replaced_by_advisory_is_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        self.replace_scenario(
            changed, "divergence-detected-strict", DIVERGENCE_ADVISORY_SCENARIO
        )
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_accepted_replaced_by_tampered_is_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        self.replace_scenario(
            changed, "checkpoint-first-use-accepted", BOOTSTRAP_TAMPERED_SCENARIO
        )
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_replacement_is_rejected_by_main_entry(self) -> None:
        changed = copy.deepcopy(self.client)
        self.case("rebootstrap-regression-refused", changed).update(
            copy.deepcopy(BOOTSTRAP_ADVANCE_SCENARIO)
        )
        original = validate.load_json
        validate.load_json = lambda path: (
            changed
            if path == validate.SUITE / "vectors" / "registry-client.json"
            else original(path)
        )
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                with contextlib.redirect_stderr(io.StringIO()):
                    code = validate.main()
        finally:
            validate.load_json = original
        self.assertEqual(code, 1)

    def assert_evidence_variants_refused(self, name: str, field: str) -> None:
        for bad in (None, 0, 1, "true", "false", "yes", []):
            with self.subTest(field=field, value=bad):
                changed = copy.deepcopy(self.client)
                self.case(name, changed)[field] = bad
                with self.assertRaises(validate.ValidationFailure):
                    self.run_gate(client=changed)
        changed = copy.deepcopy(self.client)
        del self.case(name, changed)[field]
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_first_use_signature_evidence_missing_null_wrong_type_is_rejected(self) -> None:
        self.assert_evidence_variants_refused(
            "checkpoint-signature-invalid-first-use", "signature_valid"
        )

    def test_rebootstrap_signature_evidence_missing_null_wrong_type_is_rejected(self) -> None:
        self.assert_evidence_variants_refused(
            "rebootstrap-signature-invalid-ignored", "signature_valid"
        )

    def test_equal_different_body_evidence_missing_null_wrong_type_is_rejected(self) -> None:
        self.assert_evidence_variants_refused(
            "checkpoint-first-network-equal-different-tampered", "candidate_same_body"
        )

    def test_same_log_size_evidence_missing_null_wrong_type_is_rejected(self) -> None:
        self.assert_evidence_variants_refused(
            "divergence-different-sizes-skipped", "same_log_size"
        )

    def test_roots_equal_evidence_missing_null_wrong_type_is_rejected(self) -> None:
        self.assert_evidence_variants_refused(
            "divergence-detected-advisory", "roots_equal"
        )

    def test_checkpoint_configured_missing_null_wrong_type_is_rejected(self) -> None:
        self.assert_evidence_variants_refused(
            "checkpoint-first-use-accepted", "checkpoint_configured"
        )

    def test_removed_discriminating_inputs_are_rejected_by_main_entry(self) -> None:
        mutant = copy.deepcopy(self.client)
        for name, field in [
            ("checkpoint-signature-invalid-first-use", "signature_valid"),
            ("rebootstrap-signature-invalid-ignored", "signature_valid"),
            ("checkpoint-first-network-equal-different-tampered", "candidate_same_body"),
            ("divergence-different-sizes-skipped", "same_log_size"),
            ("divergence-detected-advisory", "roots_equal"),
        ]:
            del next(
                item for item in mutant["bootstrap_cases"] if item["name"] == name
            )[field]
        original = validate.load_json
        validate.load_json = lambda path: (
            mutant
            if path == validate.SUITE / "vectors" / "registry-client.json"
            else original(path)
        )
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                with contextlib.redirect_stderr(io.StringIO()):
                    code = validate.main()
        finally:
            validate.load_json = original
        self.assertEqual(code, 1)

    def test_equal_different_replaced_by_consistent_is_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        case = self.case("checkpoint-first-network-equal-different-tampered", changed)
        case["candidate_same_body"] = True
        case["accepted"] = True
        case["state_changed"] = True
        case["registry_excluded"] = False
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_sizes_skipped_replaced_by_compared_is_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        case = self.case("divergence-different-sizes-skipped", changed)
        case["same_log_size"] = True
        case["roots_equal"] = True
        case["compared"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_regression_check_current_flipped_is_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        self.case("rebootstrap-regression-refused", changed)["check_current"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_strict_check_current_flipped_is_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        self.case("divergence-detected-strict", changed)["check_current"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_tofu_check_current_flipped_is_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        self.case("no-checkpoint-first-use-tofu", changed)["check_current"] = False
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_bad_signature_first_use_check_current_flipped_is_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        self.case("checkpoint-signature-invalid-first-use", changed)["check_current"] = True
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_advisory_check_current_flipped_is_rejected(self) -> None:
        changed = copy.deepcopy(self.client)
        self.case("divergence-detected-advisory", changed)["check_current"] = False
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(client=changed)

    def test_behavior_first_fixation_source_wrong_is_rejected(self) -> None:
        changed = copy.deepcopy(self.behavior)
        changed["bootstrap"]["first_fixation_source"] = "network-or-cache"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(behavior=changed)

    def test_behavior_first_fixation_source_missing_is_rejected(self) -> None:
        changed = copy.deepcopy(self.behavior)
        del changed["bootstrap"]["first_fixation_source"]
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(behavior=changed)

    def test_behavior_tofu_posture_wrong_is_rejected(self) -> None:
        changed = copy.deepcopy(self.behavior)
        changed["bootstrap"]["tofu_posture"] = "registry_bootstrap_warn"
        with self.assertRaises(validate.ValidationFailure):
            self.run_gate(behavior=changed)


if __name__ == "__main__":
    unittest.main()
