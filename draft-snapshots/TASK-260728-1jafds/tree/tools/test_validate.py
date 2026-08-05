from __future__ import annotations

import copy
import importlib.util
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

    def test_rc5_release_metadata_pins_exact_suite_without_claims(self) -> None:
        validate.validate_manifest()
        release = validate.load_json(
            validate.ROOT / "release" / "1.0.0-rc.5.json"
        )
        self.assertEqual(
            release["candidate_protocol_pin"]["manifest_sha256"],
            release["downstream_consumption"]["required_manifest_sha256"],
        )
        self.assertFalse(
            release["downstream_consumption"]["committed_release_pin_advanced"]
        )
        self.assertEqual(release["claim_v3"]["claims_emitted"], [])


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


if __name__ == "__main__":
    unittest.main()
