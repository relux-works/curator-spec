from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import shlex
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("validate.py")
SPEC = importlib.util.spec_from_file_location("curator_spec_validate", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
validate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validate)


def swapped(values: list, first: int, second: int) -> list:
    result = list(values)
    result[first], result[second] = result[second], result[first]
    return result


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


if __name__ == "__main__":
    unittest.main()
