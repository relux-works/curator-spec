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
        }
        for label, (schema_name, instance) in accepted.items():
            with self.subTest(label=label):
                self.assertIsNone(
                    validate.validate_wire_semantics(schema_name, instance)
                )
        for withdrawn in ("profilefile-v1.schema.json", "context-manifest-v1.schema.json"):
            self.assertFalse((validate.SCHEMAS / withdrawn).exists(), withdrawn)


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

    def test_section_12_2_lists_the_six_keys_in_order(self) -> None:
        self.assertEqual(
            validate.environments_lockable_keys(self.text),
            ["overlays_allowed", "precedence", "mcp_package_allowlist", "passable_env_names",
             "require_current_profile", "isolation"],
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

    def test_isolation_without_a_closed_value_set_fails(self) -> None:
        def open_values(s):
            s["$defs"]["environments"]["properties"]["isolation"] = {"type": "object"}
        with self.assertRaisesRegex(validate.ValidationFailure, "no closed isolation value set"):
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
        text = self.text.replace("`require_current_profile`, and `isolation`", "and `require_current_profile`", 1)
        with self.assertRaisesRegex(validate.ValidationFailure, "schema-only \\['isolation'\\]"):
            self.run_gate(text=text)

    def test_missing_section_12_2_fails_rather_than_passing_vacuously(self) -> None:
        with self.assertRaisesRegex(validate.ValidationFailure, "no section 12.2"):
            self.run_gate(text="# environments without the lockable text\n")

    def test_section_12_2_without_the_enumeration_fails(self) -> None:
        with self.assertRaisesRegex(validate.ValidationFailure, "no longer enumerates"):
            self.run_gate(text="### 12.2 Lockable knobs\n\nNothing is lockable.\n\n## 13\n")


if __name__ == "__main__":
    unittest.main()
