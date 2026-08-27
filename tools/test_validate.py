from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
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


class AdditionalDriverBoundaryTests(unittest.TestCase):
    def test_candidate_reserves_the_six_identifiers_without_admitting_them(self) -> None:
        validate.validate_additional_driver_boundary()

    def test_reserved_identifier_set_is_exactly_six_closed_pairs(self) -> None:
        self.assertEqual(len(validate.RESERVED_DRIVER_FAMILIES), 3)
        self.assertEqual(len(validate.RESERVED_BUILD_DRIVERS), 6)
        self.assertEqual(
            validate.RESERVED_BUILD_DRIVERS,
            tuple(sorted(set(validate.RESERVED_BUILD_DRIVERS))),
        )
        for family in validate.RESERVED_DRIVER_FAMILIES:
            self.assertIn(family + validate.LOCAL_DRIVER_SUFFIX, validate.RESERVED_BUILD_DRIVERS)
            self.assertIn(
                family + validate.REPOSITORY_DRIVER_SUFFIX, validate.RESERVED_BUILD_DRIVERS
            )
        # Reservation must not collide with the two admitted Go identifiers.
        self.assertEqual(
            set(validate.RESERVED_BUILD_DRIVERS).intersection(validate.ADMITTED_BUILD_DRIVERS),
            set(),
        )

    def test_absence_guard_fires_when_a_reserved_driver_reaches_a_surface(self) -> None:
        for driver in validate.RESERVED_BUILD_DRIVERS:
            with self.subTest(driver=driver), tempfile.TemporaryDirectory() as directory:
                planted = Path(directory) / "protocol-surface.md"
                planted.write_text(f"The driver is `{driver}`.\n", encoding="utf-8")
                original = validate.surface_files
                validate.surface_files = lambda: [planted]
                try:
                    with self.assertRaises(validate.ValidationFailure) as raised:
                        validate.validate_additional_driver_boundary()
                finally:
                    validate.surface_files = original
                self.assertIn("is not admitted by any schema version", str(raised.exception))

    def test_decision_records_may_name_a_reserved_driver(self) -> None:
        boundary = validate.ROOT / validate.ADDITIONAL_DRIVER_BOUNDARY_DECISION
        self.assertTrue(validate.is_decision_record(boundary))
        self.assertFalse(validate.is_decision_record(validate.ROOT / "protocol" / "core.md"))
        self.assertFalse(validate.is_decision_record(Path("/tmp") / "core.md"))
        # A future driver-contract decision may name its own identifier without
        # tripping the guard; only wire surfaces are admission.
        contract = validate.ROOT / "decisions" / "0008-example-contract.md"
        original = validate.surface_files
        validate.surface_files = lambda: [contract]
        try:
            validate.validate_additional_driver_boundary()
        finally:
            validate.surface_files = original

    def test_guard_and_its_tests_never_match_their_own_source(self) -> None:
        # The absence guard scans every surface file, including these two, so
        # both assemble the reserved names from parts instead of spelling them.
        for source_path in (MODULE_PATH, Path(__file__)):
            source = source_path.read_text(encoding="utf-8")
            for identifier in validate.reserved_boundary_identifiers():
                self.assertNotIn(identifier, source, source_path.name)
        guard_source = MODULE_PATH.read_text(encoding="utf-8")
        for family in validate.RESERVED_DRIVER_FAMILIES:
            self.assertIn(f'"{family}"', guard_source)

    def test_reserved_policy_identity_is_not_admitted_on_a_surface(self) -> None:
        # The additional drivers get their own execution-policy identity, and
        # until the integration task mints it no surface may name it either.
        self.assertIn(
            validate.RESERVED_DRIVER_EXECUTION_POLICY,
            validate.reserved_boundary_identifiers(),
        )
        self.assertNotEqual(
            validate.RESERVED_DRIVER_EXECUTION_POLICY, validate.PORTABLE_EXECUTION_POLICY
        )
        with tempfile.TemporaryDirectory() as directory:
            planted = Path(directory) / "profile-surface.md"
            planted.write_text(
                f"Builds run under `{validate.RESERVED_DRIVER_EXECUTION_POLICY}`.\n",
                encoding="utf-8",
            )
            with _Patch(validate, "surface_files", lambda: [planted]):
                with self.assertRaises(validate.ValidationFailure) as raised:
                    validate.validate_additional_driver_boundary()
        self.assertIn("is not admitted by any schema version", str(raised.exception))

    def test_reserved_evidence_record_version_is_rejected_by_the_frozen_corpus(
        self,
    ) -> None:
        # A record version legitimately appears in the frozen corpus as the
        # example of a version that must be rejected, so non-admission is
        # proved positively rather than by absence.
        self.assertNotIn(
            validate.RESERVED_CAPABILITY_EVIDENCE_RECORD,
            validate.reserved_boundary_identifiers(),
        )
        validate.check_reserved_evidence_record_is_rejected()
        vector = validate.SUITE / "vectors" / "go-host-execution-policy.json"
        for mutation in ("record_valid", "expected_error", "drop"):
            with self.subTest(mutation=mutation):
                document = validate.load_json(vector)
                cases = document["capability_evidence_cases"]
                reserved = [
                    case
                    for case in cases
                    if case["record_version"]
                    == validate.RESERVED_CAPABILITY_EVIDENCE_RECORD
                ]
                self.assertEqual(len(reserved), 1)
                if mutation == "drop":
                    document["capability_evidence_cases"] = [
                        case for case in cases if case not in reserved
                    ]
                elif mutation == "record_valid":
                    reserved[0]["record_valid"] = True
                    reserved[0]["build_permitted"] = True
                else:
                    reserved[0]["expected_error"] = "build_execution_control_unavailable"
                with self._patched_json({vector: document}):
                    with self.assertRaises(validate.ValidationFailure):
                        validate.check_reserved_evidence_record_is_rejected()

    def test_every_frozen_schema_rejects_every_reserved_driver(self) -> None:
        registry, paths = validate.schema_registry()
        for schema_name, case, path in validate.FROZEN_DRIVER_CASES:
            schema = validate.load_json(paths[schema_name])
            validator = validate.Draft202012Validator(schema, registry=registry)
            positive = validate.load_json(
                validate.case_root(schema_name) / case / "valid.json"
            )
            self.assertEqual(list(validator.iter_errors(positive)), [])
            for driver in validate.RESERVED_BUILD_DRIVERS:
                with self.subTest(schema=schema_name, case=case, driver=driver):
                    instance = copy.deepcopy(positive)
                    validate.set_at(instance, path, driver)
                    self.assertNotEqual(list(validator.iter_errors(instance)), [])

    def test_frozen_case_table_covers_manifest_descriptor_receipt_marker_and_claim(
        self,
    ) -> None:
        covered = {schema for schema, _, _ in validate.FROZEN_DRIVER_CASES}
        for required in (
            "agent-skill-v6.schema.json",
            "agent-skill-v7.schema.json",
            "csk-skill-v6.schema.json",
            "csk-skill-v7.schema.json",
            "skill-build-v1.schema.json",
            "build-receipt-v1.schema.json",
            "build-receipt-v2.schema.json",
            "install-marker-v2.schema.json",
            "install-marker-v3.schema.json",
            "conformance-claim-v3.schema.json",
        ):
            self.assertIn(required, covered)

    def test_open_driver_enum_is_rejected(self) -> None:
        common = validate.load_json(validate.SCHEMAS / "common.schema.json")
        definitions = validate.driver_bearing_definitions(common)
        self.assertIn("buildCommandV6", definitions)
        self.assertIn("skillBuildTargetV1", definitions)
        widened = copy.deepcopy(common)
        widened["$defs"]["skillBuildTargetV1"]["properties"]["driver"] = {
            "enum": [validate.ADMITTED_BUILD_DRIVERS[0], validate.RESERVED_BUILD_DRIVERS[0]]
        }
        with self.assertRaises(validate.ValidationFailure) as raised:
            self._run_with_common(widened)
        self.assertIn("is not a const over the admitted drivers", str(raised.exception))

    def test_generic_language_selector_cannot_replace_the_driver_const(self) -> None:
        common = validate.load_json(validate.SCHEMAS / "common.schema.json")
        generic = copy.deepcopy(common)
        generic["$defs"]["buildCommandV6"]["properties"]["driver"] = {
            "type": "string",
            "maxLength": 64,
        }
        with self.assertRaises(validate.ValidationFailure) as raised:
            self._run_with_common(generic)
        self.assertIn("is not a const over the admitted drivers", str(raised.exception))

    # --- closed member-set coverage -------------------------------------
    #
    # A deny-list accepts every member nobody thought to forbid. These are the
    # three concrete false accepts an independent review demonstrated against
    # the previous deny-list gate, plus the shapes that must stay closed.

    def test_optional_language_selector_on_the_local_command_is_rejected(self) -> None:
        widened = self._common_with(
            "buildCommandV6", properties={"language": {"type": "string"}}
        )
        with self.assertRaises(validate.ValidationFailure) as raised:
            self._run_with_common(widened)
        self.assertIn("is not its closed member set", str(raised.exception))
        self.assertIn("'language'", str(raised.exception))

    def test_arbitrary_command_on_the_descriptor_target_is_rejected(self) -> None:
        widened = self._common_with(
            "skillBuildTargetV1", properties={"command": {"type": "string"}}
        )
        with self.assertRaises(validate.ValidationFailure) as raised:
            self._run_with_common(widened)
        self.assertIn("is not its closed member set", str(raised.exception))
        self.assertIn("'command'", str(raised.exception))

    def test_runtime_files_member_on_a_build_record_is_rejected(self) -> None:
        widened = self._common_with(
            "buildRecordV2", properties={"runtime_files": {"type": "array"}}
        )
        with self.assertRaises(validate.ValidationFailure) as raised:
            self._run_with_common(widened)
        self.assertIn("is not its closed member set", str(raised.exception))
        self.assertIn("'runtime_files'", str(raised.exception))

    def test_runtime_bundle_members_are_rejected_on_a_build_record(self) -> None:
        widened = self._common_with(
            "buildRecordV2", properties={"launcher": {"type": "string"}}
        )
        with self.assertRaises(validate.ValidationFailure) as raised:
            self._run_with_common(widened)
        self.assertIn("is not its closed member set", str(raised.exception))

    def test_toolchain_cannot_be_added_to_a_frozen_wire_shape(self) -> None:
        # Decision 0007 places the requirement in the next schema versions. A
        # schema-6 or schema-7 command taking it would silently change what a
        # frozen manifest may express.
        for name in ("buildCommandV6", "repositoryBuildCommandV1", "skillBuildTargetV1"):
            with self.subTest(definition=name):
                widened = self._common_with(
                    name, properties={"toolchain": {"type": "object"}}
                )
                with self.assertRaises(validate.ValidationFailure) as raised:
                    self._run_with_common(widened)
                self.assertIn("is not its closed member set", str(raised.exception))

    def test_open_additional_properties_is_rejected(self) -> None:
        opened = validate.load_json(validate.SCHEMAS / "common.schema.json")
        opened["$defs"]["skillBuildTargetV1"]["additionalProperties"] = True
        with self.assertRaises(validate.ValidationFailure) as raised:
            self._run_with_common(opened)
        self.assertIn("does not close additionalProperties", str(raised.exception))

    def test_relaxing_a_required_member_is_rejected(self) -> None:
        relaxed = validate.load_json(validate.SCHEMAS / "common.schema.json")
        target = relaxed["$defs"]["buildCommandV6"]
        target["required"] = [name for name in target["required"] if name != "source_dir"]
        with self.assertRaises(validate.ValidationFailure) as raised:
            self._run_with_common(relaxed)
        self.assertIn("required set is not closed", str(raised.exception))

    def test_driver_bearing_definitions_are_exactly_the_boundary_table(self) -> None:
        common = validate.load_json(validate.SCHEMAS / "common.schema.json")
        definitions = validate.driver_bearing_definitions(common)
        # The toolchain contract minted the three shapes decision 0008 reserved,
        # so the driver-bearing set is now the union of both tables and nothing
        # else. An unlisted shape is still an unreviewed package surface.
        self.assertEqual(
            set(definitions),
            set(validate.CLOSED_DRIVER_SHAPES) | set(validate.TOOLCHAIN_WIRE_SHAPES),
        )
        for name in validate.TOOLCHAIN_WIRE_SHAPES:
            self.assertIn(name, definitions)

    def test_unlisted_driver_bearing_definition_is_rejected(self) -> None:
        smuggled = validate.load_json(validate.SCHEMAS / "common.schema.json")
        smuggled["$defs"]["buildCommandV9"] = {
            "type": "object",
            "required": ["type", "driver", "source_dir"],
            "properties": {
                "type": {"const": "build"},
                "driver": {"const": validate.ADMITTED_BUILD_DRIVERS[1]},
                "source_dir": {"type": "string"},
            },
            "additionalProperties": False,
        }
        with self.assertRaises(validate.ValidationFailure) as raised:
            self._run_with_common(smuggled)
        self.assertIn("outside the closed boundary member-set table", str(raised.exception))

    def test_removing_a_closed_definition_is_rejected(self) -> None:
        stripped = validate.load_json(validate.SCHEMAS / "common.schema.json")
        del stripped["$defs"]["buildCommandV6"]
        with self.assertRaises(validate.ValidationFailure) as raised:
            self._run_with_common(stripped)
        self.assertIn("no longer declares the closed", str(raised.exception))

    def test_reserved_schema_eight_shapes_are_enforced_the_moment_they_exist(
        self,
    ) -> None:
        # The reserved shapes carry decision 0007's toolchain placement:
        # REQUIRED on both schema-8 commands, OPTIONAL on the schema-2 target.
        for name, (required, optional) in validate.TOOLCHAIN_WIRE_SHAPES.items():
            with self.subTest(definition=name):
                exact = self._minted(name, required, optional)
                self._run_with_common(exact)

                without_toolchain = self._minted(
                    name,
                    tuple(member for member in required if member != "toolchain"),
                    tuple(member for member in optional if member != "toolchain"),
                )
                with self.assertRaises(validate.ValidationFailure) as raised:
                    self._run_with_common(without_toolchain)
                self.assertIn("is not its closed member set", str(raised.exception))

                flipped_required = tuple(sorted(set(required) | set(optional)))
                if set(flipped_required) != set(required):
                    flipped = self._minted(name, flipped_required, ())
                    with self.assertRaises(validate.ValidationFailure) as raised:
                        self._run_with_common(flipped)
                    self.assertIn("required set is not closed", str(raised.exception))

                extra = self._minted(name, required, optional + ("profile",))
                with self.assertRaises(validate.ValidationFailure) as raised:
                    self._run_with_common(extra)
                self.assertIn("is not its closed member set", str(raised.exception))

    def test_reserved_toolchain_slot_carries_the_exact_requirement_reference(
        self,
    ) -> None:
        # Placement is one shared definition referenced identically from all
        # three slots, with no sibling keyword to reinterpret it.
        self.assertEqual(set(validate.TOOLCHAIN_REQUIREMENT_REF), {"$ref"})
        self.assertTrue(
            validate.TOOLCHAIN_REQUIREMENT_REF["$ref"].endswith(
                validate.TOOLCHAIN_REQUIREMENT_DEFINITION
            )
        )
        # The table pins property schemas for more than the toolchain now, so
        # the invariant is that the three reserved slots are exactly the shapes
        # carrying the requirement reference — not that they are the only
        # entries in the table.
        carrying = {
            name
            for name, members in validate.EXACT_PROPERTY_SCHEMAS.items()
            if validate.TOOLCHAIN_REQUIREMENT_REF in members.values()
        }
        self.assertEqual(carrying, set(validate.TOOLCHAIN_WIRE_SHAPES))
        for name, (required, optional) in validate.TOOLCHAIN_WIRE_SHAPES.items():
            with self.subTest(definition=name):
                self.assertEqual(
                    validate.EXACT_PROPERTY_SCHEMAS[name],
                    {"toolchain": validate.TOOLCHAIN_REQUIREMENT_REF},
                )
                self._run_with_common(self._minted(name, required, optional))

    def test_reserved_toolchain_slot_rejects_every_shape_but_that_reference(
        self,
    ) -> None:
        # Each of these satisfies the member set — the property is spelled
        # `toolchain` and nothing else is added — while carrying something other
        # than the closed requirement object, which is exactly how a name-only
        # check leaves the trusted-preflight boundary unenforced.
        malformed = {
            "bare string": {"type": "string"},
            "open object": {"type": "object"},
            "path-bearing object": {
                "type": "object",
                "properties": {"toolchain_path": {"type": "string"}},
                "additionalProperties": False,
            },
            "wrong requirement reference": {"$ref": "#/$defs/goToolchainIdentityV1"},
            "resolved identity instead of the gate": {
                "$ref": "common.schema.json#/$defs/goToolchainIdentityV1"
            },
            "reference with a sibling keyword": {
                **validate.TOOLCHAIN_REQUIREMENT_REF,
                "description": "the closed toolchain requirement",
            },
        }
        for name, (required, optional) in validate.TOOLCHAIN_WIRE_SHAPES.items():
            for shape, schema in malformed.items():
                with self.subTest(definition=name, shape=shape):
                    minted = self._minted(name, required, optional, toolchain=schema)
                    with self.assertRaises(validate.ValidationFailure) as raised:
                        self._run_with_common(minted)
                    self.assertIn("is not exactly", str(raised.exception))
                    self.assertIn(f"{name}.toolchain", str(raised.exception))

    def test_reserved_slot_cannot_reference_a_missing_requirement_definition(
        self,
    ) -> None:
        # A reference that resolves to nothing is a hole, not a boundary.
        for name, (required, optional) in validate.TOOLCHAIN_WIRE_SHAPES.items():
            with self.subTest(definition=name):
                minted = self._minted(
                    name, required, optional, with_requirement=False
                )
                with self.assertRaises(validate.ValidationFailure) as raised:
                    self._run_with_common(minted)
                self.assertIn("which does not exist", str(raised.exception))

    def test_requirement_definition_is_closed_to_id_and_version(self) -> None:
        name = "buildCommandV8"
        required, optional = validate.TOOLCHAIN_WIRE_SHAPES[name]
        base = self._requirement()
        self.assertEqual(
            validate.TOOLCHAIN_REQUIREMENT_MEMBERS, (("id", "version"), ())
        )
        widened = copy.deepcopy(base)
        widened["properties"]["toolchain_path"] = {"type": "string"}
        opened = copy.deepcopy(base)
        opened["additionalProperties"] = True
        relaxed = copy.deepcopy(base)
        relaxed["required"] = ["id"]
        cases = {
            "extra member": (widened, "is not its closed member set"),
            "open object": (opened, "does not close additionalProperties"),
            "optional version": (relaxed, "required set is not closed"),
        }
        for case, (requirement, message) in cases.items():
            with self.subTest(case=case):
                minted = self._minted(
                    name, required, optional, requirement=requirement
                )
                with self.assertRaises(validate.ValidationFailure) as raised:
                    self._run_with_common(minted)
                self.assertIn(message, str(raised.exception))
                self.assertIn(
                    validate.TOOLCHAIN_REQUIREMENT_DEFINITION, str(raised.exception)
                )

    def test_reserved_shape_minted_without_a_driver_is_rejected(self) -> None:
        # Without a driver the definition is not driver-bearing, so neither the
        # member-set table nor the exact property schemas would ever see it.
        name = "buildCommandV8"
        required, optional = validate.TOOLCHAIN_WIRE_SHAPES[name]
        minted = self._minted(name, required, optional)
        del minted["$defs"][name]["properties"]["driver"]
        minted["$defs"][name]["required"] = [
            member for member in minted["$defs"][name]["required"] if member != "driver"
        ]
        with self.assertRaises(validate.ValidationFailure) as raised:
            self._run_with_common(minted)
        self.assertIn("was minted without a driver", str(raised.exception))

    def test_driver_policy_table_binds_every_identifier_exactly_once(self) -> None:
        table = validate.DRIVER_EXECUTION_POLICIES
        self.assertEqual(
            set(table),
            set(validate.ADMITTED_BUILD_DRIVERS) | set(validate.RESERVED_BUILD_DRIVERS),
        )
        self.assertEqual(len(table), 8)
        for driver in validate.ADMITTED_BUILD_DRIVERS:
            self.assertEqual(table[driver], validate.PORTABLE_EXECUTION_POLICY)
        for driver in validate.RESERVED_BUILD_DRIVERS:
            self.assertEqual(table[driver], validate.RESERVED_DRIVER_EXECUTION_POLICY)

    def test_current_claim_schema_asserts_exactly_the_admitted_driver_set(self) -> None:
        path, claim = self._current_claim()
        asserted = [
            assertion["properties"]["driver"]["const"]
            for assertion in self._claim_assertions(claim)
        ]
        self.assertEqual(sorted(asserted), sorted(validate.ADMITTED_BUILD_DRIVERS))
        shortened = copy.deepcopy(claim)
        self._claim_assertions(shortened).pop()
        with self.assertRaises(validate.ValidationFailure) as raised:
            self._run_with_documents({path: shortened})
        self.assertIn("does not assert every admitted wire driver", str(raised.exception))

    def test_a_frozen_claim_may_assert_a_subset_but_the_current_one_may_not(
        self,
    ) -> None:
        # Admission only ever grows by an accepted contract, so an older claim
        # asserting fewer drivers stays valid while the newest claim must cover
        # exactly the set admitted when it was minted.
        path, claim = self._current_claim()
        subset = copy.deepcopy(claim)
        self._claim_assertions(subset).pop()
        # The shipped claim schema stays untouched on both runs; only the
        # synthetic sibling moves, so the frozen corpus checks are unaffected.
        older = path.with_name("conformance-claim-v0.schema.json")
        newer = path.with_name("conformance-claim-v99.schema.json")
        with _Patch(
            validate, "conformance_claim_schemas", lambda: [(0, older), (3, path)]
        ):
            self._run_with_documents({older: subset})
        with _Patch(
            validate, "conformance_claim_schemas", lambda: [(3, path), (99, newer)]
        ):
            with self.assertRaises(validate.ValidationFailure) as raised:
                self._run_with_documents({newer: subset})
        self.assertIn("does not assert every admitted wire driver", str(raised.exception))

    def test_claim_schema_cannot_assert_a_reserved_or_retired_driver(self) -> None:
        # A reserved identifier whose contract is rejected is retired unused, so
        # a claim must be structurally unable to assert it — not merely expected
        # not to.
        path, claim = self._current_claim()
        for driver in validate.RESERVED_BUILD_DRIVERS:
            with self.subTest(driver=driver):
                smuggled = copy.deepcopy(claim)
                self._claim_assertions(smuggled)[0]["properties"]["driver"] = {
                    "const": driver
                }
                with self.assertRaises(validate.ValidationFailure) as raised:
                    self._run_with_documents({path: smuggled})
                self.assertIn(
                    "is not in the admitted wire driver set", str(raised.exception)
                )

    def test_claim_assertion_must_pair_its_driver_with_the_closed_policy(self) -> None:
        path, claim = self._current_claim()
        mispaired = copy.deepcopy(claim)
        self._claim_assertions(mispaired)[0]["properties"]["execution_policy"] = {
            "const": validate.RESERVED_DRIVER_EXECUTION_POLICY
        }
        with self.assertRaises(validate.ValidationFailure) as raised:
            self._run_with_documents({path: mispaired})
        self.assertIn("instead of", str(raised.exception))

        freed = copy.deepcopy(claim)
        self._claim_assertions(freed)[0]["properties"]["execution_policy"] = {
            "type": "string"
        }
        with self.assertRaises(validate.ValidationFailure) as raised:
            self._run_with_documents({path: freed})
        self.assertIn("neither a const nor a shared const reference", str(raised.exception))

        foreign = copy.deepcopy(claim)
        self._claim_assertions(foreign)[0]["properties"]["execution_policy"] = {
            "$ref": "conformance-claim-v3.schema.json#/properties/result"
        }
        with self.assertRaises(validate.ValidationFailure) as raised:
            self._run_with_documents({path: foreign})
        self.assertIn("outside the shared definitions", str(raised.exception))

    def test_claim_assertion_member_set_is_closed(self) -> None:
        path, claim = self._current_claim()
        self.assertEqual(
            validate.CLAIM_ASSERTION_MEMBERS,
            ("driver", "execution_policy", "language", "operating_systems"),
        )
        widened = copy.deepcopy(claim)
        assertion = self._claim_assertions(widened)[0]
        assertion["properties"]["artifacts"] = {"type": "array"}
        with self.assertRaises(validate.ValidationFailure) as raised:
            self._run_with_documents({path: widened})
        self.assertIn("is not the closed assertion member set", str(raised.exception))

        opened = copy.deepcopy(claim)
        self._claim_assertions(opened)[0]["additionalProperties"] = True
        with self.assertRaises(validate.ValidationFailure) as raised:
            self._run_with_documents({path: opened})
        self.assertIn("does not close additionalProperties", str(raised.exception))

        duplicated = copy.deepcopy(claim)
        assertions = self._claim_assertions(duplicated)
        assertions.append(copy.deepcopy(assertions[0]))
        with self.assertRaises(validate.ValidationFailure) as raised:
            self._run_with_documents({path: duplicated})
        self.assertIn("more than once", str(raised.exception))

    def test_requirement_definition_must_be_an_object_schema(self) -> None:
        # Object keywords constrain objects and nothing else. A requirement
        # declared as a string — or with no type, or unioned with one — carries
        # the exact closed member set while accepting whatever text the package
        # puts in the slot, which is the trusted-preflight boundary as decoration.
        name = "buildCommandV8"
        required, optional = validate.TOOLCHAIN_WIRE_SHAPES[name]
        base = self._requirement()
        text = copy.deepcopy(base)
        text["type"] = "string"
        untyped = copy.deepcopy(base)
        del untyped["type"]
        union = copy.deepcopy(base)
        union["type"] = ["object", "string"]

        # The escape is real: the closed members say nothing about a string.
        escape = {
            "$defs": {validate.TOOLCHAIN_REQUIREMENT_DEFINITION: text},
            "$ref": "#/$defs/" + validate.TOOLCHAIN_REQUIREMENT_DEFINITION,
        }
        self.assertEqual(
            list(validate.Draft202012Validator(escape).iter_errors("swiftc --whatever")),
            [],
        )

        for case, requirement in {
            "string type": text,
            "omitted type": untyped,
            "object or string union": union,
        }.items():
            with self.subTest(case=case):
                minted = self._minted(name, required, optional, requirement=requirement)
                with self.assertRaises(validate.ValidationFailure) as raised:
                    self._run_with_common(minted)
                self.assertIn("is not an object schema", str(raised.exception))
                self.assertIn(
                    validate.TOOLCHAIN_REQUIREMENT_DEFINITION, str(raised.exception)
                )

    def test_current_claim_schema_cannot_drop_the_driver_member(self) -> None:
        # Choosing the current schema from those that happen to declare the
        # member is admission by omission: the newest claim asserts nothing while
        # the gate reports a frozen predecessor as covering the admitted set.
        path, claim = self._current_claim()
        stripped = copy.deepcopy(claim)
        del stripped["properties"][validate.CLAIM_DRIVER_MEMBER]
        newer = path.with_name("conformance-claim-v99.schema.json")
        with _Patch(
            validate, "conformance_claim_schemas", lambda: [(3, path), (99, newer)]
        ):
            with self.assertRaises(validate.ValidationFailure) as raised:
                self._run_with_documents({newer: stripped})
        self.assertIn(
            f"does not declare {validate.CLAIM_DRIVER_MEMBER}", str(raised.exception)
        )
        self.assertIn("conformance-claim-v99", str(raised.exception))

    def test_reserved_driver_cannot_be_reached_by_a_parallel_array_applicator(
        self,
    ) -> None:
        # Draft 2020-12 ``items`` applies only to the elements ``prefixItems``
        # did not cover, so reading ``items.oneOf`` alone reports what the listed
        # branches say rather than what the list admits.
        path, claim = self._current_claim()
        driver = validate.RESERVED_BUILD_DRIVERS[0]
        smuggled = copy.deepcopy(claim)
        member = smuggled["properties"][validate.CLAIM_DRIVER_MEMBER]
        reserved = copy.deepcopy(member["items"]["oneOf"][0])
        reserved["properties"]["driver"] = {"const": driver}
        member["prefixItems"] = [reserved]

        registry, _ = validate.schema_registry()
        instance = validate.load_json(
            validate.SUITE / "schema-cases" / "conformance-claim-v3" / "valid.json"
        )
        validate.set_at(instance, ("build_drivers", 0), driver)
        self.assertTrue(
            list(validate.Draft202012Validator(claim, registry=registry).iter_errors(instance)),
            "the unmutated claim schema must already reject the reserved driver",
        )
        self.assertEqual(
            list(
                validate.Draft202012Validator(smuggled, registry=registry).iter_errors(
                    instance
                )
            ),
            [],
            "prefixItems must be demonstrated to admit what items.oneOf forbids",
        )

        # A claim version that does not exist on disk is reachable by no other
        # check, so the container closure is the only thing standing here.
        newer = path.with_name("conformance-claim-v99.schema.json")
        for keyword, value in (
            ("prefixItems", [reserved]),
            ("contains", reserved),
            ("unevaluatedItems", True),
            ("additionalItems", reserved),
        ):
            with self.subTest(keyword=keyword):
                mutant = copy.deepcopy(claim)
                mutant["properties"][validate.CLAIM_DRIVER_MEMBER][keyword] = copy.deepcopy(
                    value
                )
                with _Patch(
                    validate,
                    "conformance_claim_schemas",
                    lambda: [(3, path), (99, newer)],
                ):
                    with self.assertRaises(validate.ValidationFailure) as raised:
                        self._run_with_documents({newer: mutant})
                self.assertIn("outside the closed container set", str(raised.exception))
                self.assertIn(keyword, str(raised.exception))

    def test_claim_driver_container_must_stay_an_items_only_array(self) -> None:
        path, claim = self._current_claim()
        cases = {
            "non-array container": ({"type": "object", "items": {"oneOf": []}}, "is not an array schema"),
            "open items": (
                {"type": "array", "items": {"type": "object"}},
                "does not constrain every element with exactly items.oneOf",
            ),
            "items with a sibling applicator": (
                {
                    "type": "array",
                    "items": {"oneOf": [], "anyOf": [{"type": "object"}]},
                },
                "does not constrain every element with exactly items.oneOf",
            ),
            "empty assertion list": (
                {"type": "array", "items": {"oneOf": []}},
                "is not a closed oneOf over driver assertions",
            ),
        }
        for case, (container, message) in cases.items():
            with self.subTest(case=case):
                mutant = copy.deepcopy(claim)
                mutant["properties"][validate.CLAIM_DRIVER_MEMBER] = copy.deepcopy(container)
                with self.assertRaises(validate.ValidationFailure) as raised:
                    self._run_with_documents({path: mutant})
                self.assertIn(message, str(raised.exception))

    def test_claim_assertion_without_an_object_type_is_rejected(self) -> None:
        # Same failure class as the requirement definition: the closed member set
        # constrains an object, so an assertion that never says it is one leaves
        # a bare list element unconstrained by everything below it.
        path, claim = self._current_claim()
        untyped = copy.deepcopy(claim)
        del self._claim_assertions(untyped)[0]["type"]
        with self.assertRaises(validate.ValidationFailure) as raised:
            self._run_with_documents({path: untyped})
        self.assertIn("is not an object schema", str(raised.exception))

        widened = copy.deepcopy(claim)
        self._claim_assertions(widened)[0]["allOf"] = [{"type": "object"}]
        with self.assertRaises(validate.ValidationFailure) as raised:
            self._run_with_documents({path: widened})
        self.assertIn("outside the closed assertion set", str(raised.exception))

    def test_forbidden_build_member_on_a_non_driver_definition_is_rejected(self) -> None:
        common = validate.load_json(validate.SCHEMAS / "common.schema.json")
        for member in ("language", "toolchain_family", "build_system", "backend"):
            with self.subTest(member=member):
                self.assertIn(member, validate.FORBIDDEN_BUILD_MEMBERS)
                smuggled = copy.deepcopy(common)
                smuggled["$defs"]["buildRepositoryV1"]["properties"][member] = {
                    "type": "string"
                }
                with self.assertRaises(validate.ValidationFailure) as raised:
                    self._run_with_common(smuggled)
                self.assertIn("forbidden build members", str(raised.exception))

    def test_forbidden_members_do_not_collide_with_the_deployed_surface(self) -> None:
        # The deny-list is defense in depth, so it must not be able to fire on
        # a member the protocol already ships.
        deployed: set[str] = set()
        for required, optional in {
            **validate.CLOSED_DRIVER_SHAPES,
            **validate.TOOLCHAIN_WIRE_SHAPES,
        }.values():
            deployed.update(required)
            deployed.update(optional)
        self.assertEqual(deployed.intersection(validate.FORBIDDEN_BUILD_MEMBERS), set())

    def test_multi_file_artifact_is_rejected(self) -> None:
        common = validate.load_json(validate.SCHEMAS / "common.schema.json")
        bundled = copy.deepcopy(common)
        bundled["$defs"]["buildArtifactV1"]["properties"]["extra_path"] = {"type": "string"}
        with self.assertRaises(validate.ValidationFailure) as raised:
            self._run_with_common(bundled)
        self.assertIn("closed single-file artifact", str(raised.exception))

    # --- artifact closure -----------------------------------------------
    #
    # Comparing property names and ``additionalProperties`` is not a closure.
    # ``properties``, ``required`` and ``additionalProperties`` constrain
    # objects only, so a definition keeping all three names while typing itself
    # a scalar, a union, or nothing at all readmits ``runtime-bundle`` with
    # every shipped positive case still validating. Dropping ``required`` is
    # the same failure from the other side. These are the same object-keyword
    # and container escapes already closed for the requirement definition and
    # the claim assertions.

    def _artifact_mutant(self, **changes: object) -> dict:
        common = validate.load_json(validate.SCHEMAS / "common.schema.json")
        mutant = copy.deepcopy(common)
        mutant["$defs"][validate.ARTIFACT_DEFINITION].update(copy.deepcopy(changes))
        return mutant

    def test_artifact_must_be_an_object_schema(self) -> None:
        cases = {
            "scalar type": ("string", "is not an object schema"),
            "object-or-scalar union": (["object", "string"], "is not an object schema"),
        }
        for case, (declared, message) in cases.items():
            with self.subTest(case=case):
                with self.assertRaises(validate.ValidationFailure) as raised:
                    self._run_with_common(self._artifact_mutant(type=declared))
                self.assertIn("closed single-file artifact", str(raised.exception))
                self.assertIn(message, str(raised.exception))

        omitted = self._artifact_mutant()
        del omitted["$defs"][validate.ARTIFACT_DEFINITION]["type"]
        with self.assertRaises(validate.ValidationFailure) as raised:
            self._run_with_common(omitted)
        self.assertIn("is not an object schema", str(raised.exception))

        # A boolean is a valid Draft 2020-12 schema, and ``true`` accepts every
        # instance, so the definition need not even be an object to be minted.
        boolean = self._artifact_mutant()
        boolean["$defs"][validate.ARTIFACT_DEFINITION] = True
        with self.assertRaises(validate.ValidationFailure) as raised:
            self._run_with_common(boolean)
        self.assertIn("is not a schema object", str(raised.exception))

    def test_scalar_artifact_type_lets_a_launcher_pass_the_real_validator(self) -> None:
        # The point of the type requirement: it is not a style rule. With the
        # union in place the compiled receipt validator accepts a launcher name
        # where a published file belongs, while the generated positive case is
        # unaffected — which is exactly why a name-only check cannot see it.
        registry, paths = validate.schema_registry()
        schema = validate.load_json(paths["build-receipt-v2.schema.json"])
        valid = validate.load_json(
            validate.SUITE / "schema-cases" / "build-receipt-v2" / "valid.json"
        )
        strict = validate.Draft202012Validator(schema, registry=registry)
        self.assertEqual(list(strict.iter_errors(valid)), [])
        launcher = copy.deepcopy(valid)
        launcher["artifact"] = "bin/golden-tool-launcher"
        self.assertNotEqual(list(strict.iter_errors(launcher)), [])

        widened = self._artifact_mutant(type=["object", "string"])
        registry = registry.with_resource(
            widened["$id"], validate.Resource.from_contents(widened)
        )
        loose = validate.Draft202012Validator(schema, registry=registry)
        self.assertEqual(list(loose.iter_errors(valid)), [])
        self.assertEqual(list(loose.iter_errors(launcher)), [])

    def test_artifact_cannot_drop_a_required_member(self) -> None:
        members = validate.ARTIFACT_MEMBERS[0]
        self.assertEqual(sorted(members), ["path", "sha256", "size"])
        for member in members:
            with self.subTest(member=member):
                mutant = self._artifact_mutant(
                    required=[name for name in members if name != member]
                )
                with self.assertRaises(validate.ValidationFailure) as raised:
                    self._run_with_common(mutant)
                self.assertIn("required set is not closed", str(raised.exception))

        with self.assertRaises(validate.ValidationFailure) as raised:
            self._run_with_common(self._artifact_mutant(required=[]))
        self.assertIn("closed single-file artifact", str(raised.exception))
        self.assertIn("required set is not closed", str(raised.exception))

    def test_artifact_properties_are_pinned_to_the_shared_definitions(self) -> None:
        widenings = {
            "path": {"type": "string"},
            "sha256": {"type": "string"},
            "size": {"type": "number"},
        }
        for member, widened in widenings.items():
            with self.subTest(member=member):
                mutant = self._artifact_mutant()
                mutant["$defs"][validate.ARTIFACT_DEFINITION]["properties"][member] = widened
                with self.assertRaises(validate.ValidationFailure) as raised:
                    self._run_with_common(mutant)
                self.assertIn(f"{validate.ARTIFACT_DEFINITION}.{member} is not exactly",
                              str(raised.exception))

    def test_artifact_reference_targets_cannot_be_widened_underneath(self) -> None:
        # Pinning the three ``$ref`` values is satisfied by a reference to a
        # definition that has itself been opened. The structural pin rejects
        # each of these first; the behavioural proof is asserted separately
        # here so it stays a second, independent reason each one is closed.
        widenings = {
            "portablePath": ({}, "a path that escapes the published tree"),
            "sha256": ({"type": "string"}, "an unprefixed digest"),
            "nonNegativeSafeInteger": ({"type": "integer"}, "a negative size"),
        }
        for target, (widened, behavioural) in widenings.items():
            with self.subTest(target=target):
                mutant = self._artifact_mutant()
                mutant["$defs"][target] = widened
                with self.assertRaises(validate.ValidationFailure) as raised:
                    self._run_with_common(mutant)
                self.assertIn(f"$defs.{target} is not its canonical schema",
                              str(raised.exception))

                documents = {validate.SCHEMAS / "common.schema.json": mutant}
                with self._patched_json(documents):
                    registry, paths = validate.schema_registry()
                    with self.assertRaises(validate.ValidationFailure) as caught:
                        validate.check_build_artifact_rejections(registry, paths)
                self.assertIn(behavioural, str(caught.exception))

    # --- artifact identity targets ---------------------------------------
    #
    # The behavioural proof samples finitely many bad values, so it sees a
    # target opened wholesale and misses one widened by a single keyword. Each
    # mutant below leaves the artifact ``$ref`` values untouched and every
    # sampled negative still rejected, while the compiled receipt validator
    # starts accepting an artifact the boundary fixed as invalid.

    def _target_mutant(self, target: str, **changes: object) -> dict:
        mutant = self._artifact_mutant()
        mutant["$defs"][target].update(copy.deepcopy(changes))
        return mutant

    def _narrow_widenings(self) -> dict[str, tuple[dict, str, dict]]:
        """(mutated common, expected keyword change, newly admitted artifact)."""
        artifact = validate.load_json(
            validate.SUITE / "schema-cases" / "build-receipt-v2" / "valid.json"
        )["artifact"]
        return {
            "portablePath": (
                self._target_mutant("portablePath", maxLength=4097),
                "maxLength changed from 4096 to 4097",
                {**artifact, "path": "a" * 4097},
            ),
            "sha256": (
                self._target_mutant("sha256", pattern="^sha256:[0-9a-fA-F]{64}$"),
                "pattern changed from",
                {**artifact, "sha256": "sha256:" + "A" * 64},
            ),
            "nonNegativeSafeInteger": (
                self._target_mutant(
                    "nonNegativeSafeInteger", maximum=validate.SAFE_INTEGER + 1
                ),
                f"maximum changed from {validate.SAFE_INTEGER} to "
                f"{validate.SAFE_INTEGER + 1}",
                {**artifact, "size": validate.SAFE_INTEGER + 1},
            ),
        }

    def test_pinned_targets_are_the_shipped_shared_definitions(self) -> None:
        common = validate.load_json(validate.SCHEMAS / "common.schema.json")
        for name, expected in validate.ARTIFACT_REFERENCE_TARGETS.items():
            with self.subTest(target=name):
                self.assertEqual(common["$defs"][name], expected)
        self.assertEqual(
            sorted(validate.ARTIFACT_REFERENCE_TARGETS),
            ["nonNegativeSafeInteger", "portablePath", "sha256"],
        )

    def test_artifact_identity_target_cannot_be_widened_by_one_keyword(self) -> None:
        for target, (mutant, expected, _) in self._narrow_widenings().items():
            with self.subTest(target=target):
                with self.assertRaises(validate.ValidationFailure) as raised:
                    self._run_with_common(mutant)
                message = str(raised.exception)
                self.assertIn(validate.ADMITTED_ARTIFACT_CLASS, message)
                self.assertIn(f"$defs.{target} is not its canonical schema", message)
                self.assertIn(expected, message)

    def test_one_keyword_widening_survives_every_sampled_rejection(self) -> None:
        # Why the structural pin is required rather than more samples: each
        # mutant keeps the whole finite negative set rejected, so the
        # behavioural proof passes while the definition has moved.
        for target, (mutant, _, _) in self._narrow_widenings().items():
            with self.subTest(target=target):
                documents = {validate.SCHEMAS / "common.schema.json": mutant}
                with self._patched_json(documents):
                    registry, paths = validate.schema_registry()
                    validate.check_build_artifact_rejections(registry, paths)

    def test_one_keyword_widening_lets_the_real_validator_accept_it(self) -> None:
        # And why it is not a style rule: the compiled build-receipt-v2
        # validator accepts an over-long path, an uppercase digest and an
        # out-of-range size under these mutants, with the generated positive
        # case unaffected in every one.
        registry, paths = validate.schema_registry()
        schema = validate.load_json(paths["build-receipt-v2.schema.json"])
        valid = validate.load_json(
            validate.SUITE / "schema-cases" / "build-receipt-v2" / "valid.json"
        )
        strict = validate.Draft202012Validator(schema, registry=registry)
        for target, (mutant, _, admitted) in self._narrow_widenings().items():
            with self.subTest(target=target):
                instance = copy.deepcopy(valid)
                instance["artifact"] = admitted
                self.assertNotEqual(list(strict.iter_errors(instance)), [])
                loose = validate.Draft202012Validator(
                    schema,
                    registry=registry.with_resource(
                        mutant["$id"], validate.Resource.from_contents(mutant)
                    ),
                )
                self.assertEqual(list(loose.iter_errors(instance)), [])
                self.assertEqual(list(loose.iter_errors(valid)), [])

    def test_artifact_identity_target_cannot_drop_a_bound(self) -> None:
        # Removing a bound widens the same way raising it does, and the
        # safe-integer ceiling can only be widened this way on disk: raising it
        # past the safe integer makes the file unparseable under CCJ-1 long
        # before the boundary gate reads it.
        removals = {
            "portablePath": ("maxLength", "maxLength removed, was 4096"),
            "portablePath.not": ("not", "not removed, was"),
            "sha256": ("pattern", "pattern removed, was '^sha256:[0-9a-f]{64}$'"),
            "nonNegativeSafeInteger": (
                "maximum",
                f"maximum removed, was {validate.SAFE_INTEGER}",
            ),
        }
        for case, (keyword, expected) in removals.items():
            with self.subTest(case=case):
                target = case.split(".")[0]
                mutant = self._artifact_mutant()
                del mutant["$defs"][target][keyword]
                with self.assertRaises(validate.ValidationFailure) as raised:
                    self._run_with_common(mutant)
                message = str(raised.exception)
                self.assertIn(f"$defs.{target} is not its canonical schema", message)
                self.assertIn(expected, message)

    def test_artifact_identity_target_cannot_disappear(self) -> None:
        for target in validate.ARTIFACT_REFERENCE_TARGETS:
            with self.subTest(target=target):
                mutant = self._artifact_mutant()
                del mutant["$defs"][target]
                with self.assertRaises(validate.ValidationFailure) as raised:
                    self._run_with_common(mutant)
                self.assertIn("expected a schema object, found None",
                              str(raised.exception))

    def test_every_artifact_reference_must_be_pinned(self) -> None:
        # The pin table and the artifact's references are one contract: a
        # member repointed at an unpinned definition, or a pin kept for a
        # definition the artifact no longer names, is a gap rather than a
        # cleanup.
        unpinned = {
            **validate.ARTIFACT_PROPERTY_SCHEMAS,
            "path": {"$ref": "#/$defs/relaxedPath"},
        }
        with _Patch(validate, "ARTIFACT_PROPERTY_SCHEMAS", unpinned):
            with self.assertRaises(validate.ValidationFailure) as raised:
                validate.validate_additional_driver_boundary()
        self.assertIn("unpinned ['relaxedPath']", str(raised.exception))

        stale = {
            **validate.ARTIFACT_REFERENCE_TARGETS,
            "retiredPath": {"type": "string"},
        }
        with _Patch(validate, "ARTIFACT_REFERENCE_TARGETS", stale):
            with self.assertRaises(validate.ValidationFailure) as raised:
                validate.validate_additional_driver_boundary()
        self.assertIn("pinned but unreferenced ['retiredPath']", str(raised.exception))

    def test_artifact_member_pinned_outside_the_shared_definitions(self) -> None:
        external = {
            **validate.ARTIFACT_PROPERTY_SCHEMAS,
            "path": {"$ref": "https://example.invalid/path.schema.json"},
        }
        with _Patch(validate, "ARTIFACT_PROPERTY_SCHEMAS", external):
            with self.assertRaises(validate.ValidationFailure) as raised:
                validate.validate_additional_driver_boundary()
        self.assertIn("is not a shared definition", str(raised.exception))

    def test_artifact_definition_cannot_disappear(self) -> None:
        removed = self._artifact_mutant()
        del removed["$defs"][validate.ARTIFACT_DEFINITION]
        with self.assertRaises(validate.ValidationFailure) as raised:
            self._run_with_common(removed)
        self.assertIn("no longer declares the closed single-file artifact",
                      str(raised.exception))

    def test_artifact_rejections_cover_the_frozen_receipt_surfaces(self) -> None:
        # The behavioural proof must run against every shipped surface that
        # publishes an artifact, or a receipt version could drift unwatched.
        referencing = set()
        for path in sorted(validate.SCHEMAS.glob("*.json")):
            text = path.read_text(encoding="utf-8")
            if f"#/$defs/{validate.ARTIFACT_DEFINITION}" in text:
                referencing.add(path.name)
        self.assertEqual(
            referencing,
            {schema for schema, _, _ in validate.FROZEN_ARTIFACT_CASES},
        )

    def test_reserved_schema_slots_are_unallocated(self) -> None:
        for slot in validate.reserved_schema_slot_paths():
            self.assertFalse(slot.exists(), slot.name)
        self.assertEqual(
            [slot.name for slot in validate.reserved_schema_slot_paths()],
            list(validate.RESERVED_SCHEMA_SLOTS),
        )

    def test_reserved_slot_guard_fires_when_a_slot_is_minted_early(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            planted = Path(directory) / validate.RESERVED_SCHEMA_SLOTS[0]
            planted.write_text("{}\n", encoding="utf-8")
            original = validate.reserved_schema_slot_paths
            validate.reserved_schema_slot_paths = lambda: [planted]
            try:
                with self.assertRaises(validate.ValidationFailure) as raised:
                    validate.validate_additional_driver_boundary()
            finally:
                validate.reserved_schema_slot_paths = original
        self.assertIn("was created outside the integration task", str(raised.exception))

    def test_boundary_decision_must_fix_every_closed_term(self) -> None:
        decision = validate.ROOT / validate.ADDITIONAL_DRIVER_BOUNDARY_DECISION
        text = decision.read_text(encoding="utf-8")
        for term in (
            *validate.RESERVED_BUILD_DRIVERS,
            validate.ADMITTED_ARTIFACT_CLASS,
            validate.REJECTED_ARTIFACT_CLASS,
            *validate.BOUNDARY_FAILURE_CLASSES,
            validate.HARDENED_EXECUTION_OWNER,
        ):
            self.assertIn(term, text)
        stripped = text.replace(validate.ADMITTED_ARTIFACT_CLASS, "")
        with self._patched_read(decision, stripped):
            with self.assertRaises(validate.ValidationFailure) as raised:
                validate.validate_additional_driver_boundary()
        self.assertIn("boundary does not fix", str(raised.exception))

    def test_boundary_decision_must_separate_admission_from_reservation(self) -> None:
        # Reservation is not admission, so the decision must carry two
        # separately named closed sets rather than one ambiguous table.
        decision = validate.ROOT / validate.ADDITIONAL_DRIVER_BOUNDARY_DECISION
        text = decision.read_text(encoding="utf-8")
        for label in (
            validate.ADMITTED_DRIVER_SET_LABEL,
            validate.RESERVED_DRIVER_SET_LABEL,
        ):
            with self.subTest(label=label):
                self.assertIn(label, text)
                with self._patched_read(decision, text.replace(label, "the drivers")):
                    with self.assertRaises(validate.ValidationFailure) as raised:
                        validate.validate_additional_driver_boundary()
                self.assertIn("boundary does not fix", str(raised.exception))

    def test_boundary_decision_must_fix_the_toolchain_placement_and_policies(
        self,
    ) -> None:
        # The toolchain object and the second execution-policy identity are the
        # two things a downstream integration task cannot land without.
        decision = validate.ROOT / validate.ADDITIONAL_DRIVER_BOUNDARY_DECISION
        text = decision.read_text(encoding="utf-8")
        for term in (
            validate.TOOLCHAIN_REQUIREMENT_OBJECT,
            validate.PORTABLE_EXECUTION_POLICY,
            validate.RESERVED_DRIVER_EXECUTION_POLICY,
            validate.RESERVED_CAPABILITY_EVIDENCE_RECORD,
            *validate.TOOLCHAIN_WIRE_SHAPES,
        ):
            with self.subTest(term=term):
                self.assertIn(term, text)
                with self._patched_read(decision, text.replace(term, "something")):
                    with self.assertRaises(validate.ValidationFailure) as raised:
                        validate.validate_additional_driver_boundary()
                self.assertIn("boundary does not fix", str(raised.exception))

    def test_boundary_decision_may_not_name_a_deferred_hardened_guarantee(self) -> None:
        decision = validate.ROOT / validate.ADDITIONAL_DRIVER_BOUNDARY_DECISION
        text = decision.read_text(encoding="utf-8")
        for guarantee in validate.DEFERRED_HARDENED_GUARANTEES:
            self.assertNotIn(guarantee, text)
        claimed = text + "\nThis boundary provides total-network-denial.\n"
        with self._patched_read(decision, claimed):
            with self.assertRaises(validate.ValidationFailure) as raised:
                validate.validate_additional_driver_boundary()
        self.assertIn("deferred hardened guarantee", str(raised.exception))

    def _patched_read(self, target: Path, replacement: str):
        original = Path.read_text

        def patched(self_path: Path, *args, **kwargs):  # type: ignore[no-untyped-def]
            if self_path == target:
                return replacement
            return original(self_path, *args, **kwargs)

        return _Patch(Path, "read_text", patched)

    def _patched_json(self, documents: dict):
        original = validate.load_json
        resolved = {Path(path): document for path, document in documents.items()}

        def patched(path: Path):  # type: ignore[no-untyped-def]
            document = resolved.get(Path(path))
            if document is not None:
                return copy.deepcopy(document)
            return original(path)

        return _Patch(validate, "load_json", patched)

    def _common_with(self, definition: str, properties: dict) -> dict:
        """The shipped common schema with extra members on one definition."""
        common = validate.load_json(validate.SCHEMAS / "common.schema.json")
        common["$defs"][definition]["properties"].update(copy.deepcopy(properties))
        return common

    def _requirement(self) -> dict:
        """A minimal closed toolchain requirement definition.

        Only the two members both decisions fix are asserted here; everything
        inside ``version`` belongs to decision 0007 and is not restated.
        """
        return {
            "type": "object",
            "required": ["id", "version"],
            "properties": {"id": {"type": "string"}, "version": {"type": "object"}},
            "additionalProperties": False,
        }

    def _minted(
        self,
        definition: str,
        required: tuple[str, ...],
        optional: tuple[str, ...],
        *,
        toolchain: dict | None = None,
        requirement: dict | None = None,
        with_requirement: bool = True,
    ) -> dict:
        """The shipped common schema with one toolchain wire shape re-minted.

        The three shapes are now published, so a synthetic stub would break the
        end-to-end rejection proof for reasons that have nothing to do with the
        member set under test. Every property the shipped definition already
        declares is therefore reused verbatim, and only the member set, the
        toolchain property and the requirement definition are varied.
        """
        common = validate.load_json(validate.SCHEMAS / "common.schema.json")
        shipped = common["$defs"].get(definition, {}).get("properties", {})
        members = {
            member: copy.deepcopy(shipped[member])
            if member in shipped
            else ({"const": "build"} if member == "type" else {"type": "string"})
            for member in sorted(set(required) | set(optional))
        }
        if "driver" not in shipped:
            members["driver"] = {"const": validate.ADMITTED_BUILD_DRIVERS[0]}
        if "toolchain" in members:
            members["toolchain"] = copy.deepcopy(
                validate.TOOLCHAIN_REQUIREMENT_REF if toolchain is None else toolchain
            )
        if with_requirement:
            common["$defs"][validate.TOOLCHAIN_REQUIREMENT_DEFINITION] = copy.deepcopy(
                self._requirement() if requirement is None else requirement
            )
        else:
            common["$defs"].pop(validate.TOOLCHAIN_REQUIREMENT_DEFINITION, None)
        common["$defs"][definition] = {
            "type": "object",
            "required": sorted(required),
            "properties": members,
            "additionalProperties": False,
        }
        return common

    def _current_claim(self) -> tuple[Path, dict]:
        """The newest claim schema on disk, with its parsed document."""
        _, path = validate.conformance_claim_schemas()[-1]
        return path, validate.load_json(path)

    def _claim_assertions(self, claim: dict) -> list:
        return claim["properties"][validate.CLAIM_DRIVER_MEMBER]["items"]["oneOf"]

    def _run_with_common(self, common: dict) -> None:
        with self._patched_json({validate.SCHEMAS / "common.schema.json": common}):
            validate.validate_additional_driver_boundary()

    def _run_with_documents(self, documents: dict) -> None:
        with self._patched_json(documents):
            validate.validate_additional_driver_boundary()




class ToolchainContractTests(unittest.TestCase):
    """Negative probes for the decision 0007 gates.

    Each test plants exactly one defect the contract forbids and asserts the
    gate names it. A gate nobody can make fail is not a gate.
    """

    def setUp(self) -> None:
        self.common = validate.load_json(validate.SCHEMAS / "common.schema.json")
        self.registry = validate.load_json(
            validate.CANDIDATE_SUITE / "vectors" / "toolchain-registry.json"
        )["registry"]
        self.catalog = validate.load_json(
            validate.CANDIDATE_SUITE / "vectors" / "toolchain-guidance-catalog.json"
        )["catalog"]

    def _go_entry(self, registry: dict) -> dict:
        return next(
            entry for entry in registry["entries"] if entry["toolchain_id"] == "go"
        )

    def _entry(self, catalog: dict, guidance_id: str) -> dict:
        return next(
            entry for entry in catalog["entries"] if entry["guidance_id"] == guidance_id
        )

    # --- wire surface -----------------------------------------------------

    def test_shipped_wire_surface_passes(self) -> None:
        enumerated = validate.toolchain_gate.check_wire_surface(
            self.common, validate.ValidationFailure
        )
        self.assertEqual(
            set(enumerated), set(validate.toolchain_gate.WIRE_SURFACE_DEFINITIONS)
        )
        self.assertIn("toolchain", enumerated["buildCommandV8"])
        self.assertIn("toolchain", enumerated["skillBuildTargetV2"])

    def test_wire_surface_rejects_a_resolution_input_property(self) -> None:
        for name, value in (
            ("toolchain_path", "/usr/local/go/bin/go"),
            ("download_url", "https://example.test/go.tgz"),
            ("channel", "nightly"),
            ("install_command", "brew install go"),
            ("trust_root", "https://example.test/roots.pem"),
            ("env", {"GOROOT": "/opt/go"}),
        ):
            with self.subTest(property=name):
                common = copy.deepcopy(self.common)
                common["$defs"]["buildCommandV8"]["properties"][name] = {"type": "string"}
                with self.assertRaises(validate.ValidationFailure) as raised:
                    validate.toolchain_gate.check_wire_surface(
                        common, validate.ValidationFailure
                    )
                self.assertIn("names a resolution input", str(raised.exception))

    def test_wire_surface_reaches_inside_the_requirement_object(self) -> None:
        common = copy.deepcopy(self.common)
        constraint = common["$defs"]["toolchainVersionConstraintV1"]["oneOf"][0]
        constraint["properties"]["mirror"] = {"type": "string"}
        with self.assertRaises(validate.ValidationFailure) as raised:
            validate.toolchain_gate.check_wire_surface(common, validate.ValidationFailure)
        self.assertIn("mirror", str(raised.exception))

    def test_wire_surface_rejects_a_missing_published_definition(self) -> None:
        common = copy.deepcopy(self.common)
        del common["$defs"]["buildCommandV8"]
        with self.assertRaises(validate.ValidationFailure) as raised:
            validate.toolchain_gate.check_wire_surface(common, validate.ValidationFailure)
        self.assertIn("is missing", str(raised.exception))

    def test_build_root_is_the_only_exemption_and_it_is_reasoned(self) -> None:
        exemptions = validate.toolchain_gate.WIRE_NAME_EXEMPTIONS
        self.assertEqual(set(exemptions), {"build_root"})
        self.assertTrue(exemptions["build_root"].strip())

    # --- registry ---------------------------------------------------------

    def test_shipped_registry_passes(self) -> None:
        validate.toolchain_gate.check_registry(self.registry, validate.ValidationFailure)

    def test_registry_rejects_a_missing_per_operating_system_table(self) -> None:
        for table in ("primary_relpath", "probe"):
            with self.subTest(table=table):
                registry = copy.deepcopy(self.registry)
                del self._go_entry(registry)[table]["windows"]
                with self.assertRaises(validate.ValidationFailure) as raised:
                    validate.toolchain_gate.check_registry(
                        registry, validate.ValidationFailure
                    )
                self.assertIn("nothing to resolve", str(raised.exception))

    def test_registry_rejects_an_unreachable_per_operating_system_entry(self) -> None:
        for table in ("primary_relpath", "probe"):
            with self.subTest(table=table):
                registry = copy.deepcopy(self.registry)
                entry = self._go_entry(registry)
                entry[table]["freebsd"] = entry[table]["linux"]
                with self.assertRaises(validate.ValidationFailure) as raised:
                    validate.toolchain_gate.check_registry(
                        registry, validate.ValidationFailure
                    )
                self.assertIn("unreachable", str(raised.exception))

    def test_registry_rejects_normalizing_an_undeclared_probe(self) -> None:
        registry = copy.deepcopy(self.registry)
        self._go_entry(registry)["normalization"]["probe"] = "banner"
        with self.assertRaises(validate.ValidationFailure) as raised:
            validate.toolchain_gate.check_registry(registry, validate.ValidationFailure)
        self.assertIn("a probe it does not declare", str(raised.exception))

    def test_registry_rejects_a_classifier_without_a_trailing_catch_all(self) -> None:
        registry = copy.deepcopy(self.registry)
        field = self._go_entry(registry)["metadata_sources"][0]["fields"][0]
        del field["classes"][-1]["catch_all"]
        with self.assertRaises(validate.ValidationFailure) as raised:
            validate.toolchain_gate.check_registry(registry, validate.ValidationFailure)
        self.assertIn("classification is not total", str(raised.exception))

    def test_registry_rejects_forbidden_after_compared(self) -> None:
        registry = copy.deepcopy(self.registry)
        field = self._go_entry(registry)["metadata_sources"][0]["fields"][1]
        classes = field["classes"]
        # `default` is compared; move the custom-distribution forbidden class
        # after it, which is exactly the precedence inversion section 3.1.1
        # forbids at the value level.
        forbidden = classes.pop(2)
        classes.insert(4, forbidden)
        with self.assertRaises(validate.ValidationFailure) as raised:
            validate.toolchain_gate.check_registry(registry, validate.ValidationFailure)
        self.assertIn("precedence is not true at the value level", str(raised.exception))

    def test_registry_permits_the_absence_class_before_a_forbidden_one(self) -> None:
        # The shipped `toolchain` classifier already has this shape; the point of
        # the test is that it is admitted deliberately rather than by accident.
        field = self._go_entry(self.registry)["metadata_sources"][0]["fields"][1]
        self.assertEqual(field["classes"][0]["matches"], "absence")
        self.assertEqual(field["classes"][1]["disposition"], "forbidden")
        validate.toolchain_gate.check_registry(self.registry, validate.ValidationFailure)

    def test_registry_rejects_an_absence_class_that_is_not_first(self) -> None:
        registry = copy.deepcopy(self.registry)
        classes = self._go_entry(registry)["metadata_sources"][0]["fields"][0]["classes"]
        classes[0], classes[1] = classes[1], classes[0]
        with self.assertRaises(validate.ValidationFailure) as raised:
            validate.toolchain_gate.check_registry(registry, validate.ValidationFailure)
        self.assertIn("at most one class matches absence", str(raised.exception))

    def test_registry_rejects_a_driver_it_is_not_assigned(self) -> None:
        registry = copy.deepcopy(self.registry)
        entry = next(item for item in registry["entries"] if item["toolchain_id"] == "rust")
        entry["status"] = "complete"
        entry["drivers"] = ["go-v1"]
        with self.assertRaises(validate.ValidationFailure):
            validate.toolchain_gate.check_registry(registry, validate.ValidationFailure)

    def test_registry_rejects_dropping_an_admitted_driver(self) -> None:
        registry = copy.deepcopy(self.registry)
        self._go_entry(registry)["drivers"] = ["go-v1"]
        with self.assertRaises(validate.ValidationFailure) as raised:
            validate.toolchain_gate.check_registry(registry, validate.ValidationFailure)
        self.assertIn("closed admitted driver set", str(raised.exception))

    # --- guidance catalog -------------------------------------------------

    def test_shipped_catalog_passes(self) -> None:
        validate.toolchain_gate.check_guidance_catalog(
            self.catalog, self.registry, validate.ValidationFailure
        )

    def test_catalog_rejects_a_missing_reason(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["entries"] = [
            entry for entry in catalog["entries"] if entry["reason"] != "changed"
        ]
        with self.assertRaises(validate.ValidationFailure) as raised:
            validate.toolchain_gate.check_guidance_catalog(
                catalog, self.registry, validate.ValidationFailure
            )
        self.assertIn("does not resolve", str(raised.exception))

    def test_catalog_rejects_two_active_entries_for_one_tuple(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        duplicate = copy.deepcopy(self._entry(catalog, "toolchain.go.changed.any.r1"))
        duplicate["guidance_id"] = "toolchain.go.changed.any.r2"
        catalog["entries"].append(duplicate)
        with self.assertRaises(validate.ValidationFailure) as raised:
            validate.toolchain_gate.check_guidance_catalog(
                catalog, self.registry, validate.ValidationFailure
            )
        self.assertIn("at most one entry per tuple is active", str(raised.exception))

    def test_catalog_rejects_a_superseded_by_that_is_not_a_greater_revision(self) -> None:
        for successor in (
            "toolchain.go.untrusted.windows.r1",
            "toolchain.go.untrusted.windows.r9",
            "toolchain.go.unavailable.windows.r1",
        ):
            with self.subTest(successor=successor):
                catalog = copy.deepcopy(self.catalog)
                retired = self._entry(catalog, "toolchain.go.untrusted.windows.r1")
                retired["superseded_by"] = successor
                with self.assertRaises(validate.ValidationFailure):
                    validate.toolchain_gate.check_guidance_catalog(
                        catalog, self.registry, validate.ValidationFailure
                    )

    def test_catalog_rejects_superseded_by_on_an_active_entry(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        active = self._entry(catalog, "toolchain.go.untrusted.windows.r2")
        active["superseded_by"] = "toolchain.go.untrusted.windows.r1"
        with self.assertRaises(validate.ValidationFailure) as raised:
            validate.toolchain_gate.check_guidance_catalog(
                catalog, self.registry, validate.ValidationFailure
            )
        self.assertIn("an active entry carries superseded_by", str(raised.exception))

    def test_catalog_rejects_an_unreachable_fallback(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        for operating_system in ("linux", "macos"):
            entry = copy.deepcopy(self._entry(catalog, "toolchain.go.untrusted.any.r1"))
            entry["platform"] = operating_system
            entry["guidance_id"] = f"toolchain.go.untrusted.{operating_system}.r1"
            catalog["entries"].append(entry)
        with self.assertRaises(validate.ValidationFailure) as raised:
            validate.toolchain_gate.check_guidance_catalog(
                catalog, self.registry, validate.ValidationFailure
            )
        self.assertIn("the fallback is unreachable", str(raised.exception))

    def test_catalog_rejects_an_unreachable_override(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        registry = copy.deepcopy(self.registry)
        self._go_entry(registry)["platforms"] = [
            pair
            for pair in self._go_entry(registry)["platforms"]
            if pair["operating_system"] != "linux"
        ]
        self._go_entry(registry)["primary_relpath"].pop("linux")
        self._go_entry(registry)["probe"].pop("linux")
        with self.assertRaises(validate.ValidationFailure) as raised:
            validate.toolchain_gate.check_guidance_catalog(
                catalog, registry, validate.ValidationFailure
            )
        self.assertIn("unreachable", str(raised.exception))

    def test_catalog_rejects_a_class_that_is_not_its_reasons_class(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        self._entry(catalog, "toolchain.go.changed.any.r1")["guidance_class"] = "host"
        with self.assertRaises(validate.ValidationFailure) as raised:
            validate.toolchain_gate.check_guidance_catalog(
                catalog, self.registry, validate.ValidationFailure
            )
        self.assertIn("section 6.1 class", str(raised.exception))

    def test_catalog_rejects_an_identifier_that_disagrees_with_its_tuple(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        self._entry(catalog, "toolchain.go.changed.any.r1")["platform"] = "macos"
        with self.assertRaises(validate.ValidationFailure) as raised:
            validate.toolchain_gate.check_guidance_catalog(
                catalog, self.registry, validate.ValidationFailure
            )
        self.assertIn("disagrees with its own tuple", str(raised.exception))

    def test_selection_prefers_an_exact_entry_over_the_fallback(self) -> None:
        resolve = validate.toolchain_gate.resolve_guidance
        self.assertEqual(
            resolve(self.catalog, "go", "untrusted", "windows"),
            "toolchain.go.untrusted.windows.r2",
        )
        for operating_system in ("linux", "macos"):
            self.assertEqual(
                resolve(self.catalog, "go", "untrusted", operating_system),
                "toolchain.go.untrusted.any.r1",
            )

    def test_a_superseded_entry_stays_resolvable(self) -> None:
        retired = self._entry(self.catalog, "toolchain.go.untrusted.windows.r1")
        self.assertFalse(retired["active"])
        self.assertEqual(retired["superseded_by"], "toolchain.go.untrusted.windows.r2")

    # --- diagnostics ------------------------------------------------------

    def test_diagnostic_rejects_guidance_for_another_reason(self) -> None:
        payload = {
            "code": "build_toolchain_unavailable",
            "stage": "A",
            "driver": "go-v1",
            "toolchain_id": "go",
            "guidance_id": "toolchain.go.incompatible.any.r1",
        }
        with self.assertRaises(validate.ValidationFailure) as raised:
            validate.toolchain_gate.check_diagnostic_payloads(
                [payload], self.catalog, validate.ValidationFailure
            )
        self.assertIn("the code-to-reason mapping is the identity", str(raised.exception))

    def test_diagnostic_rejects_a_retired_guidance_identifier(self) -> None:
        payload = {
            "code": "build_toolchain_untrusted",
            "stage": "A",
            "driver": "go-v1",
            "toolchain_id": "go",
            "guidance_id": "toolchain.go.untrusted.windows.r1",
        }
        with self.assertRaises(validate.ValidationFailure) as raised:
            validate.toolchain_gate.check_diagnostic_payloads(
                [payload], self.catalog, validate.ValidationFailure
            )
        self.assertIn("retired identifier", str(raised.exception))

    def test_diagnostic_rejects_prose_guidance_and_urls(self) -> None:
        for member in ("guidance", "url", "hint", "message"):
            with self.subTest(member=member):
                payload = {
                    "code": "build_toolchain_unavailable",
                    "stage": "A",
                    "driver": "go-v1",
                    "toolchain_id": "go",
                    "guidance_id": "toolchain.go.unavailable.macos.r1",
                    member: "run brew install go",
                }
                with self.assertRaises(validate.ValidationFailure) as raised:
                    validate.toolchain_gate.check_diagnostic_payloads(
                        [payload], self.catalog, validate.ValidationFailure
                    )
                self.assertIn("a guidance_id and no prose or URL", str(raised.exception))

    # --- requirement semantics -------------------------------------------

    def test_requirement_semantics_are_not_schema_rejections(self) -> None:
        check = validate.toolchain_gate.check_requirement
        self.assertIsNone(
            check({"id": "go", "version": {"kind": "at_least", "min": "1.23.0"}}, "go-v1")
        )
        self.assertIn(
            "not the registry primary",
            check({"id": "rust", "version": {"kind": "at_least", "min": "1.23.0"}}, "go-v1"),
        )
        self.assertIn(
            "strictly below",
            check(
                {"id": "go", "version": {"kind": "range", "min": "1.25.0", "below": "1.23.0"}},
                "go-repository-v1",
            ),
        )
        self.assertIn(
            "strictly below",
            check(
                {"id": "go", "version": {"kind": "range", "min": "1.23.0", "below": "1.23.0"}},
                "go-v1",
            ),
        )

    def test_manifest_schemas_before_eight_reject_a_toolchain_requirement(self) -> None:
        for version in range(1, 8):
            for prefix in ("agent-skill", "csk-skill"):
                with self.subTest(schema=f"{prefix}-v{version}"):
                    name = f"{prefix}-v{version}.schema.json"
                    self.assertIsNotNone(
                        validate.validate_wire_semantics(
                            name, {"schema_version": version, "toolchain": {"id": "go"}}
                        )
                    )
                    self.assertIsNotNone(
                        validate.validate_wire_semantics(
                            name,
                            {
                                "schema_version": version,
                                "commands": {
                                    "tool": {
                                        "type": "build",
                                        "driver": "go-v1",
                                        "source_dir": "build/cmd/tool",
                                        "toolchain": {"id": "go"},
                                    }
                                },
                            },
                        )
                    )

    # --- inventory and probe agreement ------------------------------------

    def test_inventory_is_complete(self) -> None:
        found = validate.toolchain_gate.collect_case_identifiers(validate.CANDIDATE_SUITE)
        missing = [
            case
            for case in validate.toolchain_gate.REQUIRED_INVENTORY_CASES
            if case not in found
        ]
        self.assertEqual(missing, [])

    def test_inventory_gate_fires_on_a_dropped_case(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            suite = Path(directory)
            (suite / "vectors").mkdir()
            for name in validate.toolchain_gate.TOOLCHAIN_VECTOR_FILES:
                (suite / "vectors" / name).write_text("{}", encoding="utf-8")
            with self.assertRaises(validate.ValidationFailure) as raised:
                validate.toolchain_gate.check_inventory(suite, validate.ValidationFailure)
            self.assertIn("inventory is incomplete", str(raised.exception))

    def test_probe_case_tables_are_parsed_and_non_trivial(self) -> None:
        cases = validate.toolchain_gate.parse_probe_cases(
            validate.ROOT, validate.ValidationFailure
        )
        positions = {position for position, _ in cases}
        self.assertEqual(positions, {"go", "toolchain"})
        self.assertGreaterEqual(len([key for key in cases if key[0] == "go"]), 16)
        self.assertGreaterEqual(len([key for key in cases if key[0] == "toolchain"]), 13)

    def test_probe_agreement_fires_on_a_drifted_class(self) -> None:
        metadata = validate.load_json(
            validate.CANDIDATE_SUITE / "vectors" / "toolchain-go-metadata.json"
        )
        rows = copy.deepcopy(metadata["alignment"]["rows"])
        row = next(
            item for item in rows if item["position"] == "go" and item["value"] == "1.23"
        )
        row["class"] = 3
        with self.assertRaises(validate.ValidationFailure) as raised:
            validate.toolchain_gate.check_probe_agreement(
                rows, validate.ROOT, validate.ValidationFailure
            )
        self.assertIn("the probe says", str(raised.exception))

    def test_probe_agreement_fires_on_a_dropped_measured_value(self) -> None:
        metadata = validate.load_json(
            validate.CANDIDATE_SUITE / "vectors" / "toolchain-go-metadata.json"
        )
        rows = [
            row
            for row in metadata["alignment"]["rows"]
            if not (row["position"] == "toolchain" and row["value"] == "go1.99.0-custom")
        ]
        with self.assertRaises(validate.ValidationFailure) as raised:
            validate.toolchain_gate.check_probe_agreement(
                rows, validate.ROOT, validate.ValidationFailure
            )
        self.assertIn("the alignment table does not carry it", str(raised.exception))

    def test_probe_agreement_fires_on_a_falsely_measured_row(self) -> None:
        metadata = validate.load_json(
            validate.CANDIDATE_SUITE / "vectors" / "toolchain-go-metadata.json"
        )
        rows = copy.deepcopy(metadata["alignment"]["rows"])
        row = next(
            item
            for item in rows
            if item["position"] == "toolchain" and item["value"] == "go1.23.4"
        )
        self.assertFalse(row["probe_measured"])
        row["probe_measured"] = True
        with self.assertRaises(validate.ValidationFailure) as raised:
            validate.toolchain_gate.check_probe_agreement(
                rows, validate.ROOT, validate.ValidationFailure
            )
        self.assertIn("the probe's", str(raised.exception))

    def test_boundary_probe_is_present(self) -> None:
        self.assertTrue(
            (validate.ROOT / validate.toolchain_gate.BOUNDARY_PROBE).is_file()
        )

    def test_probe_absence_is_a_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(validate.ValidationFailure) as raised:
                validate.toolchain_gate.parse_probe_cases(
                    Path(directory), validate.ValidationFailure
                )
            self.assertIn("boundary probe is missing", str(raised.exception))

    # --- alignment properties ---------------------------------------------

    def test_alignment_properties_hold_on_the_shipped_table(self) -> None:
        metadata = validate.load_json(
            validate.CANDIDATE_SUITE / "vectors" / "toolchain-go-metadata.json"
        )
        validate.check_go_alignment_properties(metadata)

    def test_p1_fires_when_a_non_upstream_value_is_compared(self) -> None:
        metadata = validate.load_json(
            validate.CANDIDATE_SUITE / "vectors" / "toolchain-go-metadata.json"
        )
        row = next(
            item
            for item in metadata["alignment"]["rows"]
            if item["position"] == "go" and item["value"] == "1.23.4rc1"
        )
        row["outcome"] = "compare_base_triple"
        row["class"] = 3
        with self.assertRaises(validate.ValidationFailure) as raised:
            validate.check_go_alignment_properties(metadata)
        self.assertIn("P1 violated", str(raised.exception))

    def test_p2_fires_when_an_upstream_value_is_neither_forbidden_nor_compared(self) -> None:
        metadata = validate.load_json(
            validate.CANDIDATE_SUITE / "vectors" / "toolchain-go-metadata.json"
        )
        row = next(
            item
            for item in metadata["alignment"]["rows"]
            if item["position"] == "go" and item["value"] == "1.23"
        )
        row["outcome"] = "unclassifiable"
        with self.assertRaises(validate.ValidationFailure) as raised:
            validate.check_go_alignment_properties(metadata)
        self.assertIn("P2 violated", str(raised.exception))

    def test_the_go_directive_may_not_acquire_a_forbidden_class(self) -> None:
        metadata = validate.load_json(
            validate.CANDIDATE_SUITE / "vectors" / "toolchain-go-metadata.json"
        )
        row = next(
            item
            for item in metadata["alignment"]["rows"]
            if item["position"] == "go" and item["value"] == "1.23/4"
        )
        row["disposition"] = "forbidden"
        row["outcome"] = "package_influence_forbidden"
        with self.assertRaises(validate.ValidationFailure) as raised:
            validate.check_go_alignment_properties(metadata)
        self.assertIn("has no forbidden class", str(raised.exception))

    def test_the_security_partition_must_keep_subtracting(self) -> None:
        metadata = validate.load_json(
            validate.CANDIDATE_SUITE / "vectors" / "toolchain-go-metadata.json"
        )
        for row in metadata["alignment"]["rows"]:
            if row["disposition"] == "forbidden":
                row["upstream_admitted"] = False
                row["shape_layer"] = False
        with self.assertRaises(validate.ValidationFailure) as raised:
            validate.check_go_alignment_properties(metadata)
        self.assertIn("does not subtract", str(raised.exception))

    def test_upstream_admission_must_be_the_conjunction_of_both_layers(self) -> None:
        metadata = validate.load_json(
            validate.CANDIDATE_SUITE / "vectors" / "toolchain-go-metadata.json"
        )
        row = next(
            item
            for item in metadata["alignment"]["rows"]
            if item["position"] == "go" and item["value"] == "1.23.4rc1"
        )
        row["upstream_admitted"] = True
        with self.assertRaises(validate.ValidationFailure) as raised:
            validate.check_go_alignment_properties(metadata)
        self.assertIn("conjunction of both layers", str(raised.exception))

    # --- whole-gate -------------------------------------------------------

    def test_the_whole_gate_passes_on_the_shipped_repository(self) -> None:
        validate.validate_toolchain_contract()


class FrozenReleaseIdentityTests(unittest.TestCase):
    """The guard that a self-consistent regeneration cannot launder.

    Regenerating the corpus rewrites the suite manifest and the release document
    that pins it in one pass, so the two agree afterwards and comparing them
    against each other accepts the rewrite. Every test here is written against
    that specific failure: the pair is always made consistent before the guard
    runs.
    """

    def _root(self) -> Path:
        directory = Path(self.enterContext(tempfile.TemporaryDirectory()))
        for relative in (
            "release/frozen.json",
            "release/1.0.0-rc.5.json",
            "conformance/v1/manifest.json",
            "conformance/v1/schema-cases/index.json",
        ):
            target = directory / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((validate.ROOT / relative).read_bytes())
        return directory

    @staticmethod
    def _write(path: Path, document: object) -> None:
        path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def _repin(root: Path) -> None:
        """Make the release document agree with the suite manifest it pins.

        This is exactly what regeneration does, and exactly what makes an
        internal comparison useless.
        """
        manifest = root / "conformance" / "v1" / "manifest.json"
        digest = "sha256:" + hashlib.sha256(manifest.read_bytes()).hexdigest()
        document_path = root / "release" / "1.0.0-rc.5.json"
        document = json.loads(document_path.read_text(encoding="utf-8"))
        document["candidate_protocol_pin"]["manifest_sha256"] = digest
        document["downstream_consumption"]["required_manifest_sha256"] = digest
        FrozenReleaseIdentityTests._write(document_path, document)

    def test_the_shipped_repository_matches_its_authored_record(self) -> None:
        self.assertIn(
            "1.0.0-rc.5",
            validate.check_frozen_release_identity(validate.ROOT, validate.ValidationFailure),
        )
        validate.validate_frozen_releases()

    def test_a_rewritten_suite_manifest_fails_although_the_document_agrees(self) -> None:
        root = self._root()
        manifest_path = root / "conformance" / "v1" / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["files"].append(
            {"path": "vectors/toolchain-preflight.json", "sha256": "sha256:" + "0" * 64}
        )
        self._write(manifest_path, manifest)
        self._repin(root)
        # The pair is now internally consistent, which is the whole point.
        document = json.loads((root / "release" / "1.0.0-rc.5.json").read_text(encoding="utf-8"))
        self.assertEqual(
            document["candidate_protocol_pin"]["manifest_sha256"],
            "sha256:" + hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        )
        with self.assertRaises(validate.ValidationFailure) as raised:
            validate.check_frozen_release_identity(root, validate.ValidationFailure)
        self.assertIn("was rewritten", str(raised.exception))

    def test_a_rewritten_suite_manifest_fails_when_the_document_is_left_alone(self) -> None:
        """The manifest is pinned in its own right, not only through the document.

        Without this, a rewrite that kept the release document byte-stable —
        by moving a file the pin does not cover — would pass.
        """
        root = self._root()
        manifest_path = root / "conformance" / "v1" / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["files"].append(
            {"path": "vectors/toolchain-preflight.json", "sha256": "sha256:" + "0" * 64}
        )
        self._write(manifest_path, manifest)
        document = root / "release" / "1.0.0-rc.5.json"
        self.assertEqual(
            hashlib.sha256(document.read_bytes()).hexdigest(),
            hashlib.sha256((validate.ROOT / "release" / "1.0.0-rc.5.json").read_bytes()).hexdigest(),
        )
        with self.assertRaises(validate.ValidationFailure) as raised:
            validate.check_frozen_release_identity(root, validate.ValidationFailure)
        self.assertIn("conformance/v1/manifest.json", str(raised.exception))

    def test_a_rewritten_schema_case_index_fails(self) -> None:
        root = self._root()
        index_path = root / "conformance" / "v1" / "schema-cases" / "index.json"
        index = json.loads(index_path.read_text(encoding="utf-8"))
        index.append(
            {"schema": "agent-skill-v8.schema.json", "instance": "agent-skill-v8/valid.json", "valid": True}
        )
        self._write(index_path, index)
        with self.assertRaises(validate.ValidationFailure) as raised:
            validate.check_frozen_release_identity(root, validate.ValidationFailure)
        self.assertIn("schema-cases/index.json", str(raised.exception))

    def test_a_release_document_pointing_at_another_suite_root_fails(self) -> None:
        root = self._root()
        document_path = root / "release" / "1.0.0-rc.5.json"
        document = json.loads(document_path.read_text(encoding="utf-8"))
        document["candidate_protocol_pin"]["suite_root"] = "conformance/next"
        self._write(document_path, document)
        with self.assertRaises(validate.ValidationFailure) as raised:
            validate.check_frozen_release_identity(root, validate.ValidationFailure)
        # The document's own bytes moved too, so the byte comparison is what
        # fires first; either way the rewrite does not pass.
        self.assertIn("release/1.0.0-rc.5.json", str(raised.exception))

    def test_a_record_naming_a_missing_artifact_fails(self) -> None:
        root = self._root()
        (root / "conformance" / "v1" / "manifest.json").unlink()
        with self.assertRaises(validate.ValidationFailure) as raised:
            validate.check_frozen_release_identity(root, validate.ValidationFailure)
        self.assertIn("missing artifact", str(raised.exception))

    def test_an_empty_record_list_fails(self) -> None:
        root = self._root()
        self._write(root / "release" / "frozen.json", {"schema_version": 1, "releases": []})
        with self.assertRaises(validate.ValidationFailure) as raised:
            validate.check_frozen_release_identity(root, validate.ValidationFailure)
        self.assertIn("records no frozen release", str(raised.exception))


class CandidateSuiteBoundaryTests(unittest.TestCase):
    """The split that keeps an unreleased case out of a released digest."""

    def test_the_shipped_repository_passes(self) -> None:
        validate.validate_candidate_manifest()

    def test_case_root_splits_the_candidate_schemas_from_the_released_ones(self) -> None:
        for name in validate.CANDIDATE_CASE_SCHEMAS:
            with self.subTest(schema=name):
                self.assertEqual(
                    validate.case_root(name), validate.CANDIDATE_SUITE / "schema-cases"
                )
        for name in ("agent-skill-v7.schema.json", "skill-build-v1.schema.json"):
            with self.subTest(schema=name):
                self.assertEqual(validate.case_root(name), validate.SUITE / "schema-cases")

    def test_every_candidate_schema_has_cases_under_the_candidate_root(self) -> None:
        indexed = {
            case["schema"]
            for case in validate.load_json(
                validate.CANDIDATE_SUITE / "schema-cases" / "index.json"
            )
        }
        self.assertEqual(indexed, set(validate.CANDIDATE_CASE_SCHEMAS))
        released = {
            case["schema"]
            for case in validate.load_json(validate.SUITE / "schema-cases" / "index.json")
        }
        self.assertEqual(released & set(validate.CANDIDATE_CASE_SCHEMAS), set())

    def test_a_candidate_case_indexed_under_the_released_root_fails(self) -> None:
        released = validate.load_json(validate.SUITE / "schema-cases" / "index.json")
        released.append(
            {
                "schema": "agent-skill-v8.schema.json",
                "instance": "agent-skill-v8/valid.json",
                "valid": True,
            }
        )
        original = validate.load_json
        path = validate.SUITE / "schema-cases" / "index.json"

        def patched(target: Path):  # type: ignore[no-untyped-def]
            if Path(target) == path:
                return copy.deepcopy(released)
            return original(target)

        with _Patch(validate, "load_json", patched):
            with self.assertRaises(validate.ValidationFailure) as raised:
                validate.validate_schemas()
        self.assertIn("belong to conformance/next/schema-cases", str(raised.exception))

    def test_an_unindexed_case_file_fails(self) -> None:
        """A case nothing indexes is a case nothing validates.

        The generator writes and never prunes, so a renamed case leaves its old
        file behind; the suite manifest then walks the directory and hashes it
        into a pinned digest. Two such orphans were already shipping when this
        check was written.
        """
        for suite in (validate.SUITE, validate.CANDIDATE_SUITE):
            root = suite / "schema-cases"
            index = validate.load_json(root / "index.json")
            planted = index[0]["instance"].rsplit("/", 1)[0] + "/valid-orphan.json"
            original = validate.load_json
            rglob = Path.rglob

            def patched_rglob(self_path, pattern, *, _root=root, _planted=planted):  # type: ignore[no-untyped-def]
                found = list(rglob(self_path, pattern))
                if Path(self_path) == _root and pattern == "*.json":
                    found.append(_root / _planted)
                return found

            with self.subTest(suite=root.name), _Patch(Path, "rglob", patched_rglob):
                with self.assertRaises(validate.ValidationFailure) as raised:
                    validate.validate_schemas()
            self.assertIn("no index entry names", str(raised.exception))
            self.assertIn("valid-orphan.json", str(raised.exception))
            self.assertIs(validate.load_json, original)

    def test_a_protocol_version_on_the_candidate_manifest_fails(self) -> None:
        manifest = validate.load_json(validate.CANDIDATE_SUITE / "manifest.json")
        manifest["protocol_version"] = "1.0.0-rc.5"
        with self._patched_manifest(manifest):
            with self.assertRaises(validate.ValidationFailure) as raised:
                validate.validate_candidate_manifest()
        self.assertIn("names a protocol version", str(raised.exception))

    def test_a_candidate_manifest_claiming_release_fails(self) -> None:
        manifest = validate.load_json(validate.CANDIDATE_SUITE / "manifest.json")
        manifest["released"] = True
        with self._patched_manifest(manifest):
            with self.assertRaises(validate.ValidationFailure) as raised:
                validate.validate_candidate_manifest()
        self.assertIn("unreleased", str(raised.exception))

    def test_a_toolchain_vector_inside_the_pinned_suite_fails(self) -> None:
        released = validate.load_json(validate.SUITE / "manifest.json")
        released["files"].append(
            {"path": "vectors/toolchain-preflight.json", "sha256": "sha256:" + "0" * 64}
        )
        original = validate.load_json
        released_path = validate.SUITE / "manifest.json"

        def patched(target: Path):  # type: ignore[no-untyped-def]
            if Path(target) == released_path:
                return copy.deepcopy(released)
            return original(target)

        with _Patch(validate, "load_json", patched):
            with self.assertRaises(validate.ValidationFailure) as raised:
                validate.validate_candidate_manifest()
        self.assertIn("inside the pinned rc.5 suite", str(raised.exception))

    def _patched_manifest(self, manifest: dict) -> _Patch:
        original = validate.load_json
        path = validate.CANDIDATE_SUITE / "manifest.json"

        def patched(target: Path):  # type: ignore[no-untyped-def]
            if Path(target) == path:
                return copy.deepcopy(manifest)
            return original(target)

        return _Patch(validate, "load_json", patched)


class ReferenceDocumentDriftTests(unittest.TestCase):
    """The reference declares its own disagreement a defect; this executes that.

    Both rules checked here are ones the reference already stated in its header
    and contradicted in its body, which is why the guard reads the body rather
    than trusting the summary.
    """

    COPIED = (
        "docs/compiled-build-toolchain-requirements.md",
        "protocol/core.md",
        "schemas/v1/common.schema.json",
        "schemas/v1/toolchain-registry-v1.schema.json",
        "conformance/next/vectors/toolchain-registry.json",
    )

    def _root(self) -> Path:
        directory = Path(self.enterContext(tempfile.TemporaryDirectory()))
        for relative in self.COPIED:
            target = directory / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((validate.ROOT / relative).read_bytes())
        return directory

    def _patched(self, root: Path) -> list[_Patch]:
        return [
            _Patch(validate, "ROOT", root),
            _Patch(validate, "SCHEMAS", root / "schemas" / "v1"),
            _Patch(validate, "CANDIDATE_SUITE", root / "conformance" / "next"),
        ]

    def _fails_with(self, root: Path, fragment: str) -> None:
        patches = self._patched(root)
        for patch in patches:
            patch.__enter__()
        try:
            with self.assertRaises(validate.ValidationFailure) as raised:
                validate.validate_reference_document()
        finally:
            for patch in reversed(patches):
                patch.__exit__()
        self.assertIn(fragment, str(raised.exception))

    def test_the_shipped_reference_agrees_with_the_normative_contract(self) -> None:
        validate.validate_reference_document()

    def test_the_reference_names_every_surface_the_schema_closes(self) -> None:
        tokens = validate.load_json(validate.SCHEMAS / "common.schema.json")["$defs"][
            "toolchainSourceRefV1"
        ]["properties"]["surface"]["enum"]
        self.assertIn("registry", tokens)
        reference = (validate.ROOT / validate.REFERENCE_DOCUMENT).read_text(encoding="utf-8")
        match = validate.REFERENCE_SURFACE_TOKENS.search(" ".join(reference.split()))
        assert match is not None
        self.assertEqual(sorted(validate.BACKTICKED.findall(match.group(1))), sorted(tokens))

    def test_a_reference_that_drops_the_registry_surface_fails(self) -> None:
        root = self._root()
        path = root / validate.REFERENCE_DOCUMENT
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "`surface` is `manifest`, `descriptor`, `registry`, or `source_metadata`",
                "`surface` is `manifest`, `descriptor`, or `source_metadata`",
            ),
            encoding="utf-8",
        )
        self._fails_with(root, "states source_ref surfaces")

    def test_a_core_document_that_drops_the_registry_surface_fails(self) -> None:
        root = self._root()
        path = root / "protocol" / "core.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "`registry`, or `source_metadata`", "or `source_metadata`"
            ),
            encoding="utf-8",
        )
        self._fails_with(root, "protocol/core.md states source_ref surfaces")

    def test_a_classifier_row_that_relabels_absence_as_a_value_fails(self) -> None:
        root = self._root()
        path = root / validate.REFERENCE_DOCUMENT
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "| 1 | `absent` | `absence` | the directive is not present |",
                "| 1 | `absent` | `value` | the directive is not present |",
            ),
            encoding="utf-8",
        )
        self._fails_with(root, "classifier as")

    def test_a_classifier_table_missing_a_row_fails(self) -> None:
        root = self._root()
        path = root / validate.REFERENCE_DOCUMENT
        lines = [
            line
            for line in path.read_text(encoding="utf-8").splitlines()
            if not line.startswith("| 4 | `default` | `value` |")
        ]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self._fails_with(root, "classifier as")

    def test_a_legend_that_drops_a_matches_token_fails(self) -> None:
        root = self._root()
        path = root / validate.REFERENCE_DOCUMENT
        lines = [
            line
            for line in path.read_text(encoding="utf-8").splitlines()
            if not line.startswith("| `absence` |")
        ]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self._fails_with(root, "legends the matches tokens")

    def test_a_registry_schema_that_stops_requiring_matches_fails(self) -> None:
        root = self._root()
        path = root / "schemas" / "v1" / "toolchain-registry-v1.schema.json"
        schema = json.loads(path.read_text(encoding="utf-8"))
        schema["$defs"]["valueClass"]["required"] = [
            member for member in schema["$defs"]["valueClass"]["required"] if member != "matches"
        ]
        path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
        self._fails_with(root, "does not require a value class to declare what it matches")


class _Patch:
    def __init__(self, owner: object, name: str, replacement: object) -> None:
        self.owner = owner
        self.name = name
        self.replacement = replacement
        self.original = getattr(owner, name)

    def __enter__(self) -> None:
        setattr(self.owner, self.name, self.replacement)

    def __exit__(self, *exception: object) -> None:
        setattr(self.owner, self.name, self.original)


if __name__ == "__main__":
    unittest.main()
