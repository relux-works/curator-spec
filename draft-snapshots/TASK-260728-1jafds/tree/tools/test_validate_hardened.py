from __future__ import annotations

import contextlib
import copy
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("validate_hardened.py")
SPEC = importlib.util.spec_from_file_location("curator_spec_validate_hardened", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
hardened = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(hardened)

REPO = Path(__file__).resolve().parents[1]


def load_profile() -> dict:
    return hardened.load_json(
        hardened.HARDENED_SUITE / "vectors" / "hardened-execution-profile.json"
    )


@contextlib.contextmanager
def sandbox_tree():
    """A writable copy of the schema, conformance, and release surfaces."""
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        for name in ("schemas", "conformance", "release"):
            shutil.copytree(REPO / name, root / name)
        saved = {
            "ROOT": hardened.ROOT,
            "PORTABLE_SCHEMAS": hardened.PORTABLE_SCHEMAS,
            "HARDENED_SCHEMAS": hardened.HARDENED_SCHEMAS,
            "PORTABLE_SUITE": hardened.PORTABLE_SUITE,
            "HARDENED_SUITE": hardened.HARDENED_SUITE,
        }
        hardened.ROOT = root
        hardened.PORTABLE_SCHEMAS = root / "schemas" / "v1"
        hardened.HARDENED_SCHEMAS = root / "schemas" / "hardened" / "v1"
        hardened.PORTABLE_SUITE = root / "conformance" / "v1"
        hardened.HARDENED_SUITE = root / "conformance" / "hardened" / "v1"
        try:
            yield root
        finally:
            for name, value in saved.items():
                setattr(hardened, name, value)


def rewrite(path: Path, mutate) -> None:
    document = json.loads(path.read_text(encoding="utf-8"))
    mutate(document)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


class ProfileSemanticsTests(unittest.TestCase):
    def test_real_suite_passes_every_check(self) -> None:
        self.assertEqual(hardened.main(), 0)

    def test_guarantee_set_must_equal_the_portable_deferral(self) -> None:
        profile = load_profile()
        profile["guarantees"] = [
            item for item in profile["guarantees"] if item["name"] != "total-network-denial"
        ]
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_guarantee_agreement(profile)
        self.assertIn("six deferred guarantees", str(caught.exception))

    def test_guarantee_cannot_claim_establishment_without_native_evidence(self) -> None:
        profile = load_profile()
        profile["guarantees"][0]["established_in_this_revision"] = True
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_guarantee_agreement(profile)
        self.assertIn("without native evidence", str(caught.exception))

    def test_guarantee_cannot_be_claimable_under_the_portable_profile(self) -> None:
        profile = load_profile()
        profile["guarantees"][0]["claimable_under_portable"] = True
        with self.assertRaises(hardened.ValidationFailure):
            hardened.validate_guarantee_agreement(profile)

    def test_guarantee_must_state_what_is_not_sufficient(self) -> None:
        profile = load_profile()
        profile["guarantees"][0]["not_sufficient"] = []
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_guarantee_agreement(profile)
        self.assertIn("not sufficient", str(caught.exception))

    def test_capability_class_mapping_must_agree_in_both_directions(self) -> None:
        profile = load_profile()
        for item in profile["capability_inventory"]["classes"]:
            if item["name"] == "exec-path-allowlist":
                item["serves"] = ["total-network-denial"]
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_capability_inventory(profile)
        self.assertIn("disagrees with the guarantee-to-class mapping", str(caught.exception))

    def test_capability_class_cannot_be_optional(self) -> None:
        profile = load_profile()
        profile["capability_inventory"]["classes"][0]["optional"] = True
        with self.assertRaises(hardened.ValidationFailure):
            hardened.validate_capability_inventory(profile)

    def test_capability_probe_must_be_per_operation_before_domain_entry(self) -> None:
        profile = load_profile()
        profile["capability_inventory"]["probe_timing"] = "post-domain-entry"
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_capability_inventory(profile)
        self.assertIn("before domain entry", str(caught.exception))

    def test_platform_cannot_be_qualified_without_native_evidence(self) -> None:
        profile = load_profile()
        profile["platform_declarations"][0]["qualification_status"] = "qualified"
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_platform_declarations(profile)
        self.assertIn("without native adversarial evidence", str(caught.exception))

    def test_blocking_class_requires_a_stated_reason(self) -> None:
        profile = load_profile()
        for item in profile["platform_declarations"]:
            if item["platform"] == "macos":
                item["blocking_reason"] = None
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_platform_declarations(profile)
        self.assertIn("without a reason", str(caught.exception))

    def test_no_go_process_may_see_package_bytes_before_domain_entry(self) -> None:
        profile = load_profile()
        for item in profile["ordered_phases"]:
            if item["name"] == "capability-probe":
                item["package_bytes_reach_go_process"] = True
                item["before_domain_entry"] = False
        with self.assertRaises(hardened.ValidationFailure):
            hardened.validate_ordered_phases(profile)

    def test_phase_order_is_normative(self) -> None:
        profile = load_profile()
        phases = profile["ordered_phases"]
        phases[2], phases[3] = phases[3], phases[2]
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_ordered_phases(profile)
        self.assertIn("out of order", str(caught.exception))

    def test_self_test_cannot_be_ordered_before_the_domain_it_tests(self) -> None:
        """The exact ordering an earlier draft published, and no actor could run."""
        profile = load_profile()
        entry = hardened.ORDERED_PHASES.index(hardened.DOMAIN_ENTRY_PHASE)
        test = hardened.ORDERED_PHASES.index("in-domain-guarantee-self-test")
        phases = profile["ordered_phases"]
        phases[entry], phases[test] = phases[test], phases[entry]
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_ordered_phases(profile)
        self.assertIn("out of order", str(caught.exception))

    def test_an_in_domain_actor_cannot_run_before_domain_entry(self) -> None:
        profile = load_profile()
        for item in profile["ordered_phases"]:
            if item["name"] == "capability-probe":
                item["actor"] = hardened.IN_DOMAIN_ACTOR
                item["actor_in_build_domain"] = True
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_ordered_phases(profile)
        self.assertIn("inside the build domain before", str(caught.exception))

    def test_self_test_block_must_name_a_contained_actor(self) -> None:
        profile = load_profile()
        profile["in_domain_self_test"]["actor"] = "hardened-supervisor"
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_self_test(profile)
        self.assertIn("inside the build domain", str(caught.exception))

    def test_self_test_cannot_be_moved_after_package_exposure(self) -> None:
        profile = load_profile()
        profile["in_domain_self_test"]["phase"] = "go-build"
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_self_test(profile)
        self.assertIn("after a Go process sees package bytes", str(caught.exception))

    def test_self_test_failure_cannot_permit_a_partial_mode(self) -> None:
        profile = load_profile()
        profile["in_domain_self_test"]["on_failure_partial_mode_permitted"] = True
        with self.assertRaises(hardened.ValidationFailure):
            hardened.validate_self_test(profile)

    def test_ordering_invariants_must_hold_in_the_phase_list(self) -> None:
        profile = load_profile()
        for item in profile["ordering_invariants"]:
            if item["name"] == "self-test-before-package-exposure":
                item["earlier"], item["later"] = item["later"], item["earlier"]
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_ordering_invariants(profile)
        self.assertIn("does not hold", str(caught.exception))

    def test_ordering_invariants_cannot_be_dropped(self) -> None:
        profile = load_profile()
        profile["ordering_invariants"] = [
            item
            for item in profile["ordering_invariants"]
            if item["name"] != "domain-entry-before-in-domain-self-test"
        ]
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_ordering_invariants(profile)
        self.assertIn("missing", str(caught.exception))

    def test_a_phase_must_have_exactly_one_actor_in_the_graph(self) -> None:
        profile = load_profile()
        for item in profile["process_graph"]:
            if item["node"] == "manager-parent":
                item["performs_phases"] = [
                    phase for phase in item["performs_phases"] if phase != "publication"
                ]
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_profile_vector_document(profile)
        self.assertIn("no actor in the process graph", str(caught.exception))

    def test_graph_node_cannot_claim_a_phase_that_names_another_actor(self) -> None:
        profile = load_profile()
        for item in profile["process_graph"]:
            if item["node"] == "hardened-supervisor":
                item["performs_phases"] = item["performs_phases"] + ["publication"]
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_profile_vector_document(profile)
        self.assertIn("names another actor", str(caught.exception))

    def test_capability_rejection_must_not_publish(self) -> None:
        profile = load_profile()
        profile["failure_boundary"]["unavailable_capability_class"]["published"] = True
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_failure_boundary(profile)
        self.assertIn("starts a compiler or publishes", str(caught.exception))

    def test_capability_rejection_must_precede_domain_entry(self) -> None:
        profile = load_profile()
        profile["failure_boundary"]["unqualified_platform"]["before_domain_entry"] = False
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_failure_boundary(profile)
        self.assertIn("domain entry", str(caught.exception))

    def test_a_pre_entry_rejection_cannot_be_moved_past_domain_entry(self) -> None:
        """Moving a capability rejection after entry must fail both ways."""
        profile = load_profile()
        case = profile["failure_boundary"]["unavailable_capability_class"]
        case["fails_before"] = "in-domain-guarantee-self-test"
        case["before_domain_entry"] = False
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_failure_boundary(profile)
        self.assertIn("before domain entry", str(caught.exception))

    def test_a_rejection_after_package_exposure_is_detected(self) -> None:
        profile = load_profile()
        profile["failure_boundary"]["self_test_not_denied"]["before_package_exposure"] = False
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_failure_boundary(profile)
        self.assertIn("before any package byte", str(caught.exception))

    def test_hardened_diagnostic_cannot_collide_with_a_portable_code(self) -> None:
        profile = load_profile()
        profile["diagnostics"][0]["code"] = "build_execution_control_unavailable"
        with self.assertRaises(hardened.ValidationFailure):
            hardened.validate_diagnostics(profile)

    def test_diagnostics_must_be_the_specified_nine(self) -> None:
        profile = load_profile()
        profile["diagnostics"] = profile["diagnostics"][:-1]
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_diagnostics(profile)
        self.assertIn("do not match the specified set", str(caught.exception))

    def test_evidence_cannot_establish_a_guarantee_without_its_classes(self) -> None:
        profile = load_profile()
        record = copy.deepcopy(
            profile["capability_evidence_record"]["examples"]["established"]
        )
        for entry in record["capabilities"]:
            if entry["name"] == "network-syscall-denial":
                entry["availability"] = "unavailable"
                entry["status"] = "not-applied"
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.check_evidence_consistency("mutated", record, profile)
        self.assertIn("without every mapped class applied", str(caught.exception))

    def test_evidence_outcome_must_match_its_guarantee_entries(self) -> None:
        profile = load_profile()
        record = copy.deepcopy(
            profile["capability_evidence_record"]["examples"]["established"]
        )
        record["guarantees"][0]["established"] = False
        with self.assertRaises(hardened.ValidationFailure):
            hardened.check_evidence_consistency("mutated", record, profile)


def load_identity() -> dict:
    return hardened.load_json(
        hardened.HARDENED_SUITE / "vectors" / "hardened-identity-separation.json"
    )


class IdentitySeparationTests(unittest.TestCase):
    def test_hardened_cache_key_is_not_the_rc5_policy_slot_key(self) -> None:
        """rc.5 recorded a policy-slot input and marked it schema invalid.

        A hardened build input additionally binds the profile identity and the
        trusted computing base, so it must not reproduce that key.
        """
        vector = load_identity()
        portable = hardened.load_json(
            hardened.PORTABLE_SUITE / "vectors" / "go-host-execution-policy.json"
        )
        reserved = portable["cache_identity"]["reserved_hardened"]
        case = vector["cache_identity"]["hardened"]
        slot = vector["cache_identity"]["rc5_reserved_policy_slot_only"]
        self.assertEqual(hardened.ccj1_sha256(case["input"]), case["cache_key"])
        self.assertEqual(slot["cache_key"], reserved["cache_key"])
        self.assertNotEqual(case["cache_key"], reserved["cache_key"])
        self.assertFalse(reserved["schema_valid"])
        self.assertFalse(slot["is_hardened_input"])

    def test_five_execution_contracts_produce_five_keys(self) -> None:
        vector = load_identity()
        keys = {
            vector["cache_identity"][name]["cache_key"]
            for name in (
                "hardened",
                "hardened_rotated_tcb",
                "rc5_reserved_policy_slot_only",
                "portable",
                "legacy_rc4_without_execution_policy",
            )
        }
        self.assertEqual(len(keys), 5)

    def test_hardened_input_adds_exactly_one_closed_member(self) -> None:
        vector = load_identity()
        hardened_input = copy.deepcopy(vector["cache_identity"]["hardened"]["input"])
        portable_input = copy.deepcopy(vector["cache_identity"]["portable"]["input"])
        member = hardened_input.pop("hardened")
        self.assertEqual(sorted(member), ["profile", "tcb"])
        self.assertEqual(member["profile"], hardened.HARDENED_PROFILE_IDENTITY)
        hardened_input["policy"].pop("execution_policy")
        portable_input["policy"].pop("execution_policy")
        self.assertEqual(hardened_input, portable_input)

    def test_the_tcb_digest_is_recomputable_and_domain_separated(self) -> None:
        vector = load_identity()
        case = vector["cache_identity"]["hardened"]
        digest = hardened.tcb_digest(case["tcb"])
        self.assertEqual(case["input"]["hardened"]["tcb"]["content_sha256"], digest)
        self.assertNotEqual(digest, hardened.ccj1_sha256(case["tcb"]))

    def test_rotating_the_trusted_computing_base_moves_the_cache_key(self) -> None:
        vector = load_identity()
        base = vector["cache_identity"]["hardened"]
        rotated = vector["cache_identity"]["hardened_rotated_tcb"]
        self.assertNotEqual(base["cache_key"], rotated["cache_key"])
        stripped_base = {k: v for k, v in base["input"].items() if k != "hardened"}
        stripped_rotated = {k: v for k, v in rotated["input"].items() if k != "hardened"}
        self.assertEqual(stripped_base, stripped_rotated)

    def test_an_unbound_profile_identity_is_rejected(self) -> None:
        vector = load_identity()
        for item in vector["identity_binding"]["identities"]:
            if item["identity"] == "hardened-profile":
                item["in_hashed_build_input"] = False
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_identity_binding(vector)
        self.assertIn("does not bind", str(caught.exception))

    def test_an_unbound_trusted_computing_base_is_rejected(self) -> None:
        vector = load_identity()
        for item in vector["identity_binding"]["identities"]:
            if item["identity"] == "trusted-computing-base":
                item["binds_cache_reuse"] = False
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_identity_binding(vector)
        self.assertIn("does not bind", str(caught.exception))

    def test_capability_evidence_may_not_enter_a_reusable_output(self) -> None:
        vector = load_identity()
        for item in vector["identity_binding"]["identities"]:
            if item["identity"] == "capability-evidence":
                item["in_receipt_bytes"] = True
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_identity_binding(vector)
        self.assertIn("leaks into a reusable output", str(caught.exception))

    def test_cross_tcb_reuse_may_not_be_permitted(self) -> None:
        vector = load_identity()
        vector["identity_binding"]["cross_tcb_reuse"] = True
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_identity_binding(vector)
        self.assertIn("permits cross_tcb_reuse", str(caught.exception))

    def test_receipt_schemas_cannot_accept_each_other(self) -> None:
        hardened.validate_schema_level_separation()
        vector = load_identity()
        portable_receipt = hardened.validator_for("build-receipt-v1.schema.json")
        hardened_receipt = hardened.validator_for("hardened-build-receipt-v3.schema.json")
        document = {
            "schema_version": 3,
            "cache_key": vector["cache_identity"]["hardened"]["cache_key"],
            "input": vector["cache_identity"]["hardened"]["input"],
            "tcb": vector["cache_identity"]["hardened"]["tcb"],
            "artifact": {"path": "bin/tool", "sha256": "sha256:" + "d" * 64, "size": 1},
        }
        self.assertEqual(list(hardened_receipt.iter_errors(document)), [])
        self.assertTrue(list(portable_receipt.iter_errors(document)))

    def test_a_hardened_receipt_without_a_tcb_record_is_rejected(self) -> None:
        vector = load_identity()
        hardened_receipt = hardened.validator_for("hardened-build-receipt-v3.schema.json")
        document = {
            "schema_version": 3,
            "cache_key": vector["cache_identity"]["hardened"]["cache_key"],
            "input": vector["cache_identity"]["hardened"]["input"],
            "artifact": {"path": "bin/tool", "sha256": "sha256:" + "d" * 64, "size": 1},
        }
        self.assertTrue(list(hardened_receipt.iter_errors(document)))

    def test_portable_claim_schema_cannot_express_a_hardened_claim(self) -> None:
        index = hardened.load_json(hardened.HARDENED_SUITE / "schema-cases" / "index.json")
        case = next(
            item
            for item in index
            if item["schema"] == "hardened-conformance-claim-v4.schema.json" and item["valid"]
        )
        claim = hardened.load_json(hardened.HARDENED_SUITE / "schema-cases" / case["instance"])
        portable = hardened.validator_for("conformance-claim-v3.schema.json")
        self.assertTrue(list(portable.iter_errors(claim)))

    def test_portable_execution_policy_constant_is_still_closed(self) -> None:
        common = hardened.load_json(hardened.PORTABLE_SCHEMAS / "common.schema.json")
        self.assertEqual(
            common["$defs"]["goExecutionPolicyV1"], {"const": "manager-worker-v1"}
        )


def load_adversarial() -> dict:
    return hardened.load_json(
        hardened.HARDENED_SUITE / "vectors" / "hardened-adversarial-vectors.json"
    )


def valid_case(schema: str) -> dict:
    index = hardened.load_json(hardened.HARDENED_SUITE / "schema-cases" / "index.json")
    case = next(item for item in index if item["schema"] == schema and item["valid"])
    return hardened.load_json(hardened.HARDENED_SUITE / "schema-cases" / case["instance"])


RECEIPT_V3 = "hardened-build-receipt-v3.schema.json"
RECEIPT_V4 = "hardened-build-receipt-v4.schema.json"
MARKER_V4 = "hardened-install-marker-v4.schema.json"
CLAIM_V4 = "hardened-conformance-claim-v4.schema.json"
EVIDENCE_V1 = "hardened-capability-evidence-v1.schema.json"

PLATFORM_GOOS = {platform: goos for goos, platform in hardened.GOOS_TO_PLATFORM.items()}


class TcbCompletenessTests(unittest.TestCase):
    """Review cycle 2 finding R2-1.

    A trusted computing base that names only the supervisor, the worker, and
    the toolchain lets two materially different bases hash to one digest, and
    therefore share a cache key, a receipt binding, a marker, and a claim. Each
    test below is an adversarial instance that must not survive.
    """

    def errors(self, schema: str, document: dict) -> list:
        return list(hardened.validator_for(schema).iter_errors(document))

    def test_review_cycle_2_probes_are_rejected(self) -> None:
        """The four instances the reviewer's probe accepted with zero errors."""
        receipt = valid_case(RECEIPT_V3)
        claim = valid_case(CLAIM_V4)

        mismatched = copy.deepcopy(receipt)
        mismatched["tcb"]["enforcement_backend"] = "linux-namespace-seccomp-v1"
        self.assertTrue(self.errors(RECEIPT_V3, mismatched))

        wrong_host = copy.deepcopy(receipt)
        wrong_host["tcb"]["platform"] = "linux"
        wrong_host["tcb"]["enforcement_backend"] = "linux-namespace-seccomp-v1"
        self.assertTrue(self.errors(RECEIPT_V3, wrong_host))

        interpreter = copy.deepcopy(receipt)
        interpreter["tcb"]["trusted_components"] = [
            "mutable-interpreter-with-no-cryptographic-identity"
        ]
        self.assertTrue(self.errors(RECEIPT_V3, interpreter))

        windows_backend = copy.deepcopy(claim)
        windows_backend["tcb"]["platform"] = "macos"
        windows_backend["tcb"]["enforcement_backend"] = "windows-appcontainer-job-v1"
        self.assertTrue(self.errors(CLAIM_V4, windows_backend))

    def test_the_manager_parent_and_the_observed_host_are_bound(self) -> None:
        record = valid_case(RECEIPT_V3)["tcb"]
        self.assertEqual(sorted(record), hardened.TCB_FIELDS)
        self.assertIn("parent_sha256", record)
        self.assertIn("host", record)
        self.assertIn("backend", record)
        self.assertEqual(sorted(record["host"]), hardened.TCB_HOST_FIELDS)
        self.assertEqual(sorted(record["backend"]), hardened.TCB_BACKEND_FIELDS)

    def test_every_bound_field_omission_is_rejected_everywhere(self) -> None:
        receipt = valid_case(RECEIPT_V3)
        repository = valid_case(RECEIPT_V4)
        marker = valid_case(MARKER_V4)
        claim = valid_case(CLAIM_V4)
        for field in hardened.TCB_FIELDS:
            with self.subTest(field=field):
                mutant = copy.deepcopy(receipt)
                del mutant["tcb"][field]
                self.assertTrue(self.errors(RECEIPT_V3, mutant))

                repo_mutant = copy.deepcopy(repository)
                del repo_mutant["tcb"][field]
                self.assertTrue(self.errors(RECEIPT_V4, repo_mutant))

                marker_mutant = copy.deepcopy(marker)
                for record in marker_mutant["builds"].values():
                    del record["tcb"][field]
                self.assertTrue(self.errors(MARKER_V4, marker_mutant))

                claim_mutant = copy.deepcopy(claim)
                del claim_mutant["tcb"][field]
                self.assertTrue(self.errors(CLAIM_V4, claim_mutant))

    def test_a_trusted_component_needs_a_cryptographic_identity(self) -> None:
        receipt = valid_case(RECEIPT_V3)
        for components in (
            ["mutable-interpreter"],
            [{"kind": "interpreter", "name": "python", "algorithm": "curator-hardened-component-file-v1"}],
            [{"kind": "interpreter", "name": "python", "content_sha256": "sha256:" + "a" * 64}],
            [{"kind": "not-a-known-kind", "name": "x", "algorithm": "curator-hardened-component-file-v1", "content_sha256": "sha256:" + "a" * 64}],
            [{"kind": "interpreter", "name": "python", "algorithm": "sha256", "content_sha256": "sha256:" + "a" * 64}],
        ):
            with self.subTest(components=components):
                mutant = copy.deepcopy(receipt)
                mutant["tcb"]["trusted_components"] = components
                self.assertTrue(self.errors(RECEIPT_V3, mutant))

    def test_the_unconstrained_string_component_field_cannot_be_revived(self) -> None:
        mutant = valid_case(RECEIPT_V3)
        mutant["tcb"]["additional_trusted_components"] = ["mutable-interpreter"]
        self.assertTrue(self.errors(RECEIPT_V3, mutant))

    def test_a_platform_cannot_carry_another_platforms_backend(self) -> None:
        receipt = valid_case(RECEIPT_V3)
        evidence = valid_case(EVIDENCE_V1)
        for platform, backend in hardened.PLATFORM_BACKENDS.items():
            for other, other_backend in hardened.PLATFORM_BACKENDS.items():
                if other == platform:
                    continue
                with self.subTest(platform=platform, backend=other):
                    mutant = copy.deepcopy(receipt)
                    mutant["input"]["target"]["goos"] = PLATFORM_GOOS[platform]
                    mutant["tcb"]["platform"] = platform
                    mutant["tcb"]["enforcement_backend"] = other_backend
                    self.assertTrue(self.errors(RECEIPT_V3, mutant))

                    report = copy.deepcopy(evidence)
                    report["platform"] = platform
                    report["enforcement_backend"] = other_backend
                    self.assertTrue(self.errors(EVIDENCE_V1, report))
            self.assertEqual(hardened.PLATFORM_BACKENDS[platform], backend)

    def test_a_receipt_target_cannot_contradict_its_own_tcb_platform(self) -> None:
        for schema, case in ((RECEIPT_V3, valid_case(RECEIPT_V3)), (RECEIPT_V4, valid_case(RECEIPT_V4))):
            for goos, platform in hardened.GOOS_TO_PLATFORM.items():
                for other in hardened.PLATFORM_BACKENDS:
                    if other == platform:
                        continue
                    with self.subTest(schema=schema, goos=goos, platform=other):
                        mutant = copy.deepcopy(case)
                        mutant["input"]["target"]["goos"] = goos
                        mutant["tcb"]["platform"] = other
                        mutant["tcb"]["enforcement_backend"] = hardened.PLATFORM_BACKENDS[other]
                        self.assertTrue(self.errors(schema, mutant))

    def test_a_hardened_build_cannot_target_a_platform_with_no_declaration(self) -> None:
        mutant = valid_case(RECEIPT_V3)
        mutant["input"]["target"]["goos"] = "freebsd"
        self.assertTrue(self.errors(RECEIPT_V3, mutant))

    def test_a_claim_cannot_name_a_tcb_for_an_undeclared_operating_system(self) -> None:
        claim = valid_case(CLAIM_V4)
        claim["tcb"] = copy.deepcopy(claim["tcb"])
        # Move the whole trusted computing base onto macOS consistently — the
        # backend, the canonical kernel identity, and the backend version series
        # all follow the platform — so the only rule left to break is that the
        # claim never declared macOS.
        claim["tcb"]["platform"] = "macos"
        claim["tcb"]["enforcement_backend"] = "macos-sandbox-v1"
        # The whole observed host moves too, since review cycle 4 bound the
        # kernel build identity and its identifier grammar to the platform.
        claim["tcb"]["host"] = copy.deepcopy(valid_case(RECEIPT_V3)["tcb"]["host"])
        claim["tcb"]["backend"]["version"] = "sandbox-2.0"
        hardened.check_tcb_record("internally consistent", claim["tcb"])
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.check_claim_qualification("mutated", claim)
        self.assertIn("operating system it does not claim", str(caught.exception))

    def test_a_claim_cannot_declare_one_backend_and_run_another(self) -> None:
        claim = valid_case(CLAIM_V4)
        claim["enforcement_backends"][0]["operating_system"] = "macos"
        claim["operating_systems"] = ["macos"]
        with self.assertRaises(hardened.ValidationFailure):
            hardened.check_claim_qualification("mutated", claim)

    def test_a_claim_cannot_require_configuration_its_own_tcb_never_observed(self) -> None:
        claim = valid_case(CLAIM_V4)
        claim["enforcement_backends"][0]["required_configuration"].append(
            {"setting": "seccomp.enabled", "required_value": "yes"}
        )
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.check_claim_qualification("mutated", claim)
        self.assertIn("did not observe", str(caught.exception))

        drifted = valid_case(CLAIM_V4)
        drifted["enforcement_backends"][0]["required_configuration"][0]["required_value"] = "1"
        with self.assertRaises(hardened.ValidationFailure):
            hardened.check_claim_qualification("mutated", drifted)

    def test_a_narrower_or_wider_record_is_not_the_closed_record(self) -> None:
        record = valid_case(RECEIPT_V3)["tcb"]
        narrower = {k: v for k, v in record.items() if k != "parent_sha256"}
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.check_tcb_record("narrower", narrower)
        self.assertIn("closed hardened-tcb-v1 record", str(caught.exception))
        wider = dict(record, additional_trusted_components=["interpreter"])
        with self.assertRaises(hardened.ValidationFailure):
            hardened.check_tcb_record("wider", wider)

    def test_unsorted_or_duplicated_components_are_rejected(self) -> None:
        record = valid_case(RECEIPT_V3)["tcb"]
        unsorted_record = copy.deepcopy(record)
        unsorted_record["trusted_components"] = list(reversed(record["trusted_components"]))
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.check_tcb_record("unsorted", unsorted_record)
        self.assertIn("sorted unique set", str(caught.exception))

        duplicated = copy.deepcopy(record)
        duplicated["backend"]["configuration"] = [
            {"setting": "a", "observed_value": "1"},
            {"setting": "a", "observed_value": "2"},
        ]
        with self.assertRaises(hardened.ValidationFailure):
            hardened.check_tcb_record("duplicated", duplicated)


class TcbRotationTests(unittest.TestCase):
    """Rotating a bound identity must move the cache key, receipt, marker, claim."""

    def test_every_rotation_moves_the_cache_key_and_none_alias(self) -> None:
        vector = load_identity()
        base = vector["cache_identity"]["hardened"]["cache_key"]
        keys = {base}
        for case in vector["tcb_rotation_cases"]:
            self.assertEqual(hardened.ccj1_sha256(case["input"]), case["cache_key"])
            self.assertEqual(hardened.tcb_digest(case["tcb"]), case["tcb_digest"])
            self.assertNotIn(case["cache_key"], keys)
            keys.add(case["cache_key"])
        self.assertEqual(len(keys), len(vector["tcb_rotation_cases"]) + 1)

    def test_the_manager_parent_alone_moves_the_cache_key(self) -> None:
        """Nothing a package can see differs, so only the TCB moved the key."""
        vector = load_identity()
        base = vector["cache_identity"]["hardened"]
        case = next(
            item
            for item in vector["tcb_rotation_cases"]
            if item["name"] == "rotate-parent-identity"
        )
        self.assertFalse(case["package_visible_input_changed"])
        visible = {k: v for k, v in case["input"].items() if k != "hardened"}
        base_visible = {k: v for k, v in base["input"].items() if k != "hardened"}
        self.assertEqual(visible, base_visible)
        self.assertNotEqual(case["cache_key"], base["cache_key"])
        self.assertEqual(case["tcb"]["supervisor_sha256"], base["tcb"]["supervisor_sha256"])
        self.assertEqual(case["tcb"]["worker_sha256"], base["tcb"]["worker_sha256"])
        self.assertNotEqual(case["tcb"]["parent_sha256"], base["tcb"]["parent_sha256"])

    def test_every_mutable_bound_field_has_a_rotation(self) -> None:
        vector = load_identity()
        rotated = {
            item["field"]: item["rotated_by"] for item in vector["tcb_completeness"]["bound_fields"]
        }
        for field in hardened.TCB_FIELDS:
            if field in hardened.TCB_CONSTANT_FIELDS:
                self.assertEqual(rotated[field], [])
            else:
                self.assertTrue(rotated[field], f"{field} is never rotated")

    def test_an_identity_that_does_not_move_the_key_is_detected(self) -> None:
        vector = load_identity()
        vector["tcb_rotation_cases"][0]["cache_key_differs_from_base"] = False
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_tcb_rotation(vector)
        self.assertIn("does not move the cache key", str(caught.exception))

    def test_a_bound_field_without_a_rotation_is_detected(self) -> None:
        vector = load_identity()
        for item in vector["tcb_completeness"]["bound_fields"]:
            if item["field"] == "parent_sha256":
                item["rotated_by"] = []
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_tcb_rotation(vector)
        self.assertIn("never rotated", str(caught.exception))

    def test_a_rotation_that_hides_a_package_visible_change_is_detected(self) -> None:
        vector = load_identity()
        case = next(
            item
            for item in vector["tcb_rotation_cases"]
            if item["name"] == "rotate-platform-and-backend"
        )
        case["package_visible_input_changed"] = False
        case["package_visible_change_reason"] = None
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_tcb_rotation(vector)
        self.assertIn("misreports whether a package-visible value changed", str(caught.exception))

    def test_a_rotation_that_lies_about_its_own_digest_is_detected(self) -> None:
        vector = load_identity()
        vector["tcb_rotation_cases"][0]["tcb"]["worker_sha256"] = "sha256:" + "3" * 64
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_tcb_rotation(vector)
        self.assertIn("digest its own record disproves", str(caught.exception))

    def test_completeness_must_cover_the_whole_closed_record(self) -> None:
        vector = load_identity()
        vector["tcb_completeness"]["bound_fields"] = [
            item for item in vector["tcb_completeness"]["bound_fields"] if item["field"] != "host"
        ]
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_tcb_completeness(vector)
        self.assertIn("closed record members", str(caught.exception))

    def test_completeness_cannot_readmit_unconstrained_string_components(self) -> None:
        vector = load_identity()
        vector["tcb_completeness"]["unconstrained_string_components_permitted"] = True
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_tcb_completeness(vector)
        self.assertIn("unconstrained string trusted component", str(caught.exception))

    # Rotating one member of the record in a published receipt or marker,
    # without recomputing the digest and key, must be caught. This is the
    # "prove receipt/marker rejection" half of the rotation requirement.
    ROTATIONS = {
        "parent_sha256": "sha256:" + "a" * 64,
        "supervisor_sha256": "sha256:" + "b" * 64,
        "worker_sha256": "sha256:" + "c" * 64,
    }

    def test_a_receipt_whose_bound_identity_moved_is_rejected(self) -> None:
        for field, value in self.ROTATIONS.items():
            with self.subTest(field=field), sandbox_tree() as root:
                receipt = (
                    root
                    / "conformance"
                    / "hardened"
                    / "v1"
                    / "schema-cases"
                    / "hardened-build-receipt-v3"
                    / "valid.json"
                )
                rewrite(receipt, lambda document: document["tcb"].__setitem__(field, value))
                with self.assertRaises(hardened.ValidationFailure) as caught:
                    hardened.validate_identity_binding_chain()
                self.assertIn("does not reproduce its own TCB record", str(caught.exception))

    def test_a_receipt_whose_observed_host_or_backend_moved_is_rejected(self) -> None:
        mutations = {
            "host.version": lambda tcb: tcb["host"].update({"version": "26.0.0"}),
            # host.identity and host.kind are no longer free values: section
            # 2.3.3 binds them, so moving either is a schema rejection rather
            # than a digest mismatch. The two observed values still free to move
            # are covered here. The kernel build identity is a closed record
            # since review cycle 4, so the value that moves is its digest.
            "host.build.content_sha256": lambda tcb: tcb["host"]["build"].update(
                {"content_sha256": "sha256:" + "b" * 64}
            ),
            "host.build.identifier": lambda tcb: tcb["host"]["build"].update(
                {"identifier": "25A124"}
            ),
            "backend.version": lambda tcb: tcb["backend"].update({"version": "sandbox-9.9"}),
            "backend.configuration": lambda tcb: tcb["backend"].update(
                {"configuration": [{"setting": "sandbox_profile_dialect", "observed_value": "scheme-v9"}]}
            ),
            "trusted_components": lambda tcb: tcb["trusted_components"][0].update(
                {"content_sha256": "sha256:" + "e" * 64}
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(field=label), sandbox_tree() as root:
                receipt = (
                    root
                    / "conformance"
                    / "hardened"
                    / "v1"
                    / "schema-cases"
                    / "hardened-build-receipt-v3"
                    / "valid.json"
                )
                rewrite(receipt, lambda document: mutate(document["tcb"]))
                with self.assertRaises(hardened.ValidationFailure) as caught:
                    hardened.validate_identity_binding_chain()
                self.assertIn("does not reproduce its own TCB record", str(caught.exception))

    def test_a_marker_whose_bound_identity_moved_is_rejected(self) -> None:
        for field, value in self.ROTATIONS.items():
            with self.subTest(field=field), sandbox_tree() as root:
                marker = (
                    root
                    / "conformance"
                    / "hardened"
                    / "v1"
                    / "schema-cases"
                    / "hardened-install-marker-v4"
                    / "valid.json"
                )

                def swap(document: dict) -> None:
                    for record in document["builds"].values():
                        record["tcb"][field] = value

                rewrite(marker, swap)
                with self.assertRaises(hardened.ValidationFailure) as caught:
                    hardened.validate_identity_binding_chain()
                self.assertIn("does not follow from its own identities", str(caught.exception))

    def test_every_bound_field_needs_an_adversarial_omission_case(self) -> None:
        profile = load_profile()
        with sandbox_tree() as root:
            vector = (
                root
                / "conformance"
                / "hardened"
                / "v1"
                / "vectors"
                / "hardened-adversarial-vectors.json"
            )

            def drop(document: dict) -> None:
                document["tcb_completeness_cases"] = [
                    case
                    for case in document["tcb_completeness_cases"]
                    if not (case["kind"] == "omission" and case["field"] == "parent_sha256")
                ]

            rewrite(vector, drop)
            with self.assertRaises(hardened.ValidationFailure) as caught:
                hardened.validate_adversarial_vector(profile)
            self.assertIn("without an omission case", str(caught.exception))


class ComponentDigestTests(unittest.TestCase):
    """Review cycle 3 finding R3-1.

    curator-hardened-component-file-v1 and curator-hardened-component-tree-v1
    were names with no construction, so a component digest was not independently
    reproducible and two implementations could hash different projections of one
    installed tree while claiming the same algorithm identity.
    """

    def fixtures(self) -> dict:
        block = load_identity()["component_digest_fixtures"]
        return {item["name"]: item for item in block["fixtures"]}

    def test_every_published_fixture_is_reproduced_from_its_own_bytes(self) -> None:
        for name, fixture in self.fixtures().items():
            with self.subTest(fixture=name):
                self.assertEqual(
                    hardened.recompute_component_fixture(name, fixture),
                    fixture["expected_sha256"],
                )

    def test_the_two_algorithms_are_domain_separated(self) -> None:
        """An empty file and an empty tree must not share one digest."""
        self.assertNotEqual(
            hardened.component_file_digest(b""), hardened.component_tree_digest([])
        )

    def test_a_link_substitution_does_not_reproduce_the_tree_it_replaced(self) -> None:
        referent = b"#!probe network\ndeny-all\n"
        base = [
            ("D", b"probes", b""),
            ("F", b"probes/network.probe", referent),
            ("L", b"probes/current.probe", b"network.probe"),
        ]
        substituted = [
            ("D", b"probes", b""),
            ("F", b"probes/network.probe", referent),
            # The adversarial case: a regular file holding the referent's exact
            # bytes, in the link's place.
            ("F", b"probes/current.probe", referent),
        ]
        self.assertNotEqual(
            hardened.component_tree_digest(base), hardened.component_tree_digest(substituted)
        )

    def test_tree_membership_and_entry_type_each_move_the_digest(self) -> None:
        base = [("D", b"probes", b""), ("F", b"probes/a", b"x")]
        added = base + [("F", b"probes/b", b"y")]
        retyped = [("D", b"probes", b""), ("D", b"probes/a", b"")]
        digests = {
            hardened.component_tree_digest(base),
            hardened.component_tree_digest(added),
            hardened.component_tree_digest(retyped),
        }
        self.assertEqual(len(digests), 3)

    def test_entry_order_is_not_an_input(self) -> None:
        entries = [("F", b"probes/b", b"y"), ("D", b"probes", b""), ("F", b"probes/a", b"x")]
        self.assertEqual(
            hardened.component_tree_digest(entries),
            hardened.component_tree_digest(sorted(entries, key=lambda item: item[1])),
        )

    def test_a_duplicate_encoded_path_is_rejected(self) -> None:
        with self.assertRaises(hardened.ValidationFailure):
            hardened.component_tree_digest([("F", b"probes/a", b"x"), ("F", b"probes/a", b"y")])

    def test_an_unknown_entry_kind_is_rejected(self) -> None:
        with self.assertRaises(hardened.ValidationFailure):
            hardened.component_tree_digest([("S", b"probes/socket", b"")])

    def test_a_fixture_that_lies_about_its_digest_is_detected(self) -> None:
        vector = load_identity()
        vector["component_digest_fixtures"]["fixtures"][0]["expected_sha256"] = "sha256:" + "0" * 64
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_component_digest_fixtures(vector)
        self.assertIn("its own bytes produce", str(caught.exception))

    def test_a_fixture_that_misreports_a_byte_length_is_detected(self) -> None:
        vector = load_identity()
        for fixture in vector["component_digest_fixtures"]["fixtures"]:
            if fixture["file"] is not None:
                fixture["file"]["content_byte_length"] += 1
                break
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_component_digest_fixtures(vector)
        self.assertIn("misreports its own byte length", str(caught.exception))

    def test_a_link_substitution_fixture_that_proves_nothing_is_detected(self) -> None:
        vector = load_identity()
        for fixture in vector["component_digest_fixtures"]["fixtures"]:
            if fixture["name"] != "capability-probe-suite-link-substituted":
                continue
            for entry in fixture["entries"]:
                if entry["path"] == "probes/current.probe":
                    entry["payload"] = "not-the-referent-bytes"
                    entry["payload_byte_length"] = len(entry["payload"])
            fixture["expected_sha256"] = hardened.recompute_component_fixture(
                fixture["name"], fixture
            )
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_component_digest_fixtures(vector)
        self.assertIn("does not hold the referent's exact bytes", str(caught.exception))

    def test_a_component_digest_no_fixture_reproduces_is_detected(self) -> None:
        with sandbox_tree() as root:
            receipt = (
                root
                / "conformance"
                / "hardened"
                / "v1"
                / "schema-cases"
                / "hardened-build-receipt-v3"
                / "valid.json"
            )
            rewrite(
                receipt,
                lambda document: document["tcb"]["trusted_components"][0].update(
                    {"content_sha256": "sha256:" + "b" * 64}
                ),
            )
            with self.assertRaises(hardened.ValidationFailure) as caught:
                hardened.validate_component_digest_fixtures(load_identity())
            self.assertIn("invented identity", str(caught.exception))

    def test_a_kind_that_names_one_file_cannot_carry_a_tree_digest(self) -> None:
        record = valid_case(RECEIPT_V3)["tcb"]
        record["trusted_components"] = [
            {
                "kind": "interpreter",
                "name": "supervisor-launcher-interpreter",
                "algorithm": hardened.COMPONENT_TREE_ALGORITHM,
                "content_sha256": "sha256:" + "a" * 64,
            }
        ]
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.check_tcb_record("mutated", record)
        self.assertIn("does not admit", str(caught.exception))

    def test_the_tree_kind_cannot_carry_a_file_digest(self) -> None:
        record = valid_case(RECEIPT_V3)["tcb"]
        record["trusted_components"] = [
            {
                "kind": "installed-package-tree",
                "name": "vendored-runtime",
                "algorithm": hardened.COMPONENT_FILE_ALGORITHM,
                "content_sha256": "sha256:" + "a" * 64,
            }
        ]
        with self.assertRaises(hardened.ValidationFailure):
            hardened.check_tcb_record("mutated", record)

    def test_the_shipped_schemas_reject_an_algorithm_its_kind_does_not_admit(self) -> None:
        validator = hardened.validator_for(RECEIPT_V3)
        mutant = valid_case(RECEIPT_V3)
        mutant["tcb"]["trusted_components"] = [
            {
                "kind": "script",
                "name": "policy-installer",
                "algorithm": hardened.COMPONENT_TREE_ALGORITHM,
                "content_sha256": "sha256:" + "a" * 64,
            }
        ]
        self.assertTrue(list(validator.iter_errors(mutant)))

    def test_a_tree_fixture_that_skips_a_parent_directory_is_detected(self) -> None:
        fixture = {
            "algorithm": hardened.COMPONENT_TREE_ALGORITHM,
            "file": None,
            "entries": [
                {
                    "kind": "F",
                    "path": "probes/network.probe",
                    "path_byte_length": len("probes/network.probe"),
                    "payload": "x",
                    "payload_byte_length": 1,
                }
            ],
        }
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.recompute_component_fixture("orphan", fixture)
        self.assertIn("without its parent directory", str(caught.exception))

    def test_a_dangling_or_escaping_link_fixture_is_detected(self) -> None:
        def tree(link_target: str) -> dict:
            entries = [
                ("D", "probes", ""),
                ("F", "probes/network.probe", "x"),
                ("L", "probes/current.probe", link_target),
            ]
            return {
                "algorithm": hardened.COMPONENT_TREE_ALGORITHM,
                "file": None,
                "entries": [
                    {
                        "kind": kind,
                        "path": path,
                        "path_byte_length": len(path),
                        "payload": payload,
                        "payload_byte_length": len(payload),
                    }
                    for kind, path, payload in entries
                ],
            }

        hardened.recompute_component_fixture("resolves", tree("network.probe"))
        for target, expected in (
            ("missing.probe", "dangling symbolic link"),
            ("../../outside", "escaping its root"),
            ("/etc/passwd", "absolute symbolic link"),
        ):
            with self.subTest(target=target):
                with self.assertRaises(hardened.ValidationFailure) as caught:
                    hardened.recompute_component_fixture("bad", tree(target))
                self.assertIn(expected, str(caught.exception))

    def test_every_component_facet_has_its_own_rotation(self) -> None:
        vector = load_identity()
        coverage = {
            item["aspect"]: item["rotated_by"]
            for item in vector["tcb_completeness"]["component_rotation_coverage"]
        }
        self.assertEqual(set(coverage), hardened.COMPONENT_ASPECTS)
        for aspect, rotations in coverage.items():
            self.assertTrue(rotations, f"component facet {aspect} is never rotated")

    def test_a_facet_without_a_rotation_is_detected(self) -> None:
        vector = load_identity()
        for item in vector["tcb_completeness"]["component_rotation_coverage"]:
            if item["aspect"] == "link-substitution":
                item["rotated_by"] = []
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_tcb_rotation(vector)
        self.assertIn("link-substitution is never rotated", str(caught.exception))

    def test_crediting_a_rotation_with_a_facet_it_does_not_declare_is_detected(self) -> None:
        """The exact shortcut review cycle 3 rejected: array coverage for all."""
        vector = load_identity()
        for item in vector["tcb_completeness"]["component_rotation_coverage"]:
            if item["aspect"] == "kind":
                item["rotated_by"] = ["add-trusted-component"]
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_tcb_rotation(vector)
        self.assertIn("does not declare", str(caught.exception))

    def test_every_component_rotation_moves_the_cache_key(self) -> None:
        vector = load_identity()
        base = vector["cache_identity"]["hardened"]["cache_key"]
        component_cases = [
            case
            for case in vector["tcb_rotation_cases"]
            if case["rotated_component_aspects"]
        ]
        self.assertGreaterEqual(len(component_cases), len(hardened.COMPONENT_ASPECTS))
        keys = {base}
        for case in component_cases:
            self.assertEqual(hardened.ccj1_sha256(case["input"]), case["cache_key"])
            self.assertNotIn(case["cache_key"], keys)
            keys.add(case["cache_key"])


class BackendVersionTests(unittest.TestCase):
    """Review cycle 3 finding R3-2.

    Section 8.5 required the observed backend version to be at or above the
    claim's declared minimum and nothing compared them, so a claim declaring
    999999 was accepted against an observed version of 0.
    """

    def test_the_grammar_accepts_only_a_series_and_bounded_numbers(self) -> None:
        for value in ("sandbox-2", "sandbox-2.0.0", "cgroup2-6.12", "appcontainer-10.0.26100.1"):
            with self.subTest(value=value):
                self.assertIsNotNone(hardened.parse_backend_version(value))
        for value in (
            "2.0",
            "cgroup2-06.1",
            "cgroup2-",
            "cgroup2-1.2.3.4.5",
            "latest",
            "-1.0",
            "Sandbox-2.0",
            "sandbox-1234567890",
            "",
            None,
            2,
        ):
            with self.subTest(value=value):
                self.assertIsNone(hardened.parse_backend_version(value))

    def test_a_missing_component_is_zero(self) -> None:
        self.assertEqual(
            hardened.parse_backend_version("sandbox-2"),
            hardened.parse_backend_version("sandbox-2.0.0.0"),
        )

    def test_comparison_is_integer_and_not_lexical(self) -> None:
        self.assertEqual(hardened.backend_version_at_least("cgroup2-6.10", "cgroup2-6.9"), (True, True))
        self.assertEqual(hardened.backend_version_at_least("cgroup2-6.9", "cgroup2-6.10"), (False, True))

    def test_below_equal_and_above_are_all_decided(self) -> None:
        self.assertEqual(hardened.backend_version_at_least("sandbox-2.1", "sandbox-2.0"), (True, True))
        self.assertEqual(hardened.backend_version_at_least("sandbox-2.0", "sandbox-2.0"), (True, True))
        self.assertEqual(hardened.backend_version_at_least("sandbox-1.9", "sandbox-2.0"), (False, True))

    def test_two_series_are_not_comparable(self) -> None:
        self.assertEqual(
            hardened.backend_version_at_least("cgroup2-6.12", "sandbox-2.0"), (False, False)
        )

    def test_a_malformed_value_is_not_comparable(self) -> None:
        self.assertEqual(hardened.backend_version_at_least("6.1", "cgroup2-6.1"), (False, False))
        self.assertEqual(hardened.backend_version_at_least("cgroup2-6.1", "newest"), (False, False))

    def test_the_reviewer_probe_no_longer_qualifies(self) -> None:
        """Backend version 0 against a declared minimum of 999999."""
        claim = valid_case(CLAIM_V4)
        claim["tcb"]["backend"]["version"] = "cgroup2-0"
        claim["enforcement_backends"][0]["minimum_version"] = "cgroup2-999999"
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.check_claim_qualification("reviewer-probe", claim)
        self.assertIn("does not satisfy", str(caught.exception))

    def test_a_claim_at_exactly_the_minimum_qualifies(self) -> None:
        claim = valid_case(CLAIM_V4)
        claim["enforcement_backends"][0]["minimum_version"] = claim["tcb"]["backend"]["version"]
        hardened.check_claim_qualification("at-minimum", claim)

    def test_a_claim_quoting_another_backend_series_is_rejected(self) -> None:
        claim = valid_case(CLAIM_V4)
        claim["enforcement_backends"][0]["minimum_version"] = "sandbox-1.0"
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.check_claim_qualification("cross-series", claim)
        self.assertIn("cannot be compared", str(caught.exception))

    def test_the_shipped_schema_rejects_a_minimum_outside_the_grammar(self) -> None:
        validator = hardened.validator_for(CLAIM_V4)
        for value in ("6.1", "cgroup2-06.1", "sandbox-2.0", "latest"):
            with self.subTest(minimum=value):
                mutant = valid_case(CLAIM_V4)
                mutant["enforcement_backends"][0]["minimum_version"] = value
                self.assertTrue(list(validator.iter_errors(mutant)))

    def test_a_trailing_newline_is_not_a_version(self) -> None:
        """The version pattern must not end at a trailing newline.

        Several regular-expression engines let ``$`` match before a final
        newline, which would admit "sandbox-2.0\\n" as a version and give one
        backend two spellings of the same value.
        """
        self.assertIsNone(hardened.parse_backend_version("sandbox-2.0\n"))
        validator = hardened.validator_for(RECEIPT_V3)
        mutant = valid_case(RECEIPT_V3)
        mutant["tcb"]["backend"]["version"] = "sandbox-2.0\n"
        self.assertTrue(list(validator.iter_errors(mutant)))
        claim_validator = hardened.validator_for(CLAIM_V4)
        claim = valid_case(CLAIM_V4)
        claim["enforcement_backends"][0]["minimum_version"] = "cgroup2-6.1\n"
        self.assertTrue(list(claim_validator.iter_errors(claim)))

    def test_a_published_comparison_verdict_that_is_wrong_is_detected(self) -> None:
        vector = load_identity()
        vector["backend_version_comparison"]["cases"][0]["satisfied"] = False
        vector["backend_version_comparison"]["cases"][0]["claim_qualifies"] = False
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_backend_version_comparison(vector)
        self.assertIn("comparison disproves", str(caught.exception))

    def test_the_comparison_cases_cover_every_outcome(self) -> None:
        hardened.validate_backend_version_comparison(load_identity())


class ObservedHostTests(unittest.TestCase):
    """Review cycle 3 finding R3-2: the observed host was unrelated to the
    platform it is supposed to identify."""

    def test_the_reviewer_probe_is_rejected_by_the_shipped_schemas(self) -> None:
        """A linux claim whose trusted base reports a Windows kernel."""
        validator = hardened.validator_for(CLAIM_V4)
        mutant = valid_case(CLAIM_V4)
        mutant["tcb"]["host"]["identity"] = "windows-nt"
        mutant["tcb"]["host"]["version"] = "10.0.26100"
        self.assertTrue(list(validator.iter_errors(mutant)))

    def test_every_platform_admits_exactly_its_own_kernel_identity(self) -> None:
        for platform, identity in hardened.CANONICAL_HOST_IDENTITY.items():
            for other, wrong in hardened.CANONICAL_HOST_IDENTITY.items():
                if other == platform:
                    continue
                with self.subTest(platform=platform, observed=wrong):
                    record = valid_case(RECEIPT_V3)["tcb"]
                    record["platform"] = platform
                    record["enforcement_backend"] = hardened.PLATFORM_BACKENDS[platform]
                    record["backend"]["version"] = (
                        hardened.BACKEND_VERSION_SERIES[hardened.PLATFORM_BACKENDS[platform]] + "-1.0"
                    )
                    record["host"]["identity"] = wrong
                    with self.assertRaises(hardened.ValidationFailure) as caught:
                        hardened.check_tcb_record("mutated", record)
                    self.assertIn("another platform declares", str(caught.exception))
            _ = identity

    def test_a_hypervisor_host_is_outside_this_revision(self) -> None:
        record = valid_case(RECEIPT_V3)["tcb"]
        record["host"]["kind"] = "hypervisor"
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.check_tcb_record("mutated", record)
        self.assertIn("operating-system-kernel mechanism", str(caught.exception))
        self.assertTrue(
            list(hardened.validator_for(RECEIPT_V3).iter_errors(
                {**valid_case(RECEIPT_V3), "tcb": record}
            ))
        )

    def test_a_backend_version_from_another_series_is_rejected(self) -> None:
        record = valid_case(RECEIPT_V3)["tcb"]
        record["backend"]["version"] = "cgroup2-6.12"
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.check_tcb_record("mutated", record)
        self.assertIn("another backend declares", str(caught.exception))

    def test_a_malformed_backend_version_is_rejected(self) -> None:
        record = valid_case(RECEIPT_V3)["tcb"]
        record["backend"]["version"] = "2.0"
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.check_tcb_record("mutated", record)
        self.assertIn("outside the hardened-backend-version-v1 grammar", str(caught.exception))


class HostBuildIdentityTests(unittest.TestCase):
    """Review cycle 4 finding R4-1.

    ``host.build`` was a nullable descriptive string, so two materially
    different kernels reporting one platform and one release produced one
    hardened-tcb-v1 record — and therefore one cache key, one receipt, one
    marker, and one claim.
    """

    def fixtures(self) -> dict:
        return {item["name"]: item for item in load_identity()["host_build_fixtures"]["fixtures"]}

    def test_the_reviewer_probe_is_rejected_by_the_shipped_schemas(self) -> None:
        """The exact cycle-4 probe: a valid receipt with tcb.host.build null."""
        validator = hardened.validator_for(RECEIPT_V3)
        mutant = valid_case(RECEIPT_V3)
        mutant["tcb"]["host"]["build"] = None
        self.assertTrue(list(validator.iter_errors(mutant)))

    def test_the_reviewer_probe_is_rejected_by_the_semantic_check(self) -> None:
        record = valid_case(RECEIPT_V3)["tcb"]
        record["host"]["build"] = None
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.check_tcb_record("mutated", record)
        self.assertIn("reports no kernel build identity", str(caught.exception))

    def test_a_bare_string_build_is_no_longer_an_identity(self) -> None:
        validator = hardened.validator_for(RECEIPT_V3)
        for value in ("25A123", "", "unknown"):
            with self.subTest(build=value):
                mutant = valid_case(RECEIPT_V3)
                mutant["tcb"]["host"]["build"] = value
                self.assertTrue(list(validator.iter_errors(mutant)))
                record = valid_case(RECEIPT_V3)["tcb"]
                record["host"]["build"] = value
                with self.assertRaises(hardened.ValidationFailure):
                    hardened.check_tcb_record("mutated", record)

    def test_every_published_fixture_is_reproduced_from_its_own_bytes(self) -> None:
        for name, fixture in self.fixtures().items():
            with self.subTest(fixture=name):
                self.assertEqual(
                    hardened.recompute_host_build_fixture(name, fixture),
                    fixture["expected_sha256"],
                )

    def test_two_kernels_with_one_tuple_do_not_share_a_digest(self) -> None:
        """The finding itself: same platform, same release, same identifier."""
        base = self.fixtures()["macos-host-build"]
        rebuilt = self.fixtures()["macos-host-build-recompiled-kernel"]
        for field in ("platform", "host_identity", "host_version", "identifier"):
            self.assertEqual(base[field], rebuilt[field])
        self.assertNotEqual(base["expected_sha256"], rebuilt["expected_sha256"])

    def test_the_construction_is_length_framed(self) -> None:
        """Two source lists whose hashed byte stream concatenates identically.

        ``a|bc`` and ``ab|c`` produce the same bytes without framing, so an
        unframed construction would give them one digest. Only the uint64be
        lengths separate them.
        """
        left = [(b"a", b"bc")]
        right = [(b"ab", b"c")]
        self.assertEqual(b"".join(b"".join(pair) for pair in left),
                         b"".join(b"".join(pair) for pair in right))
        self.assertNotEqual(
            hardened.host_build_digest("darwin", "25.0.0", "25A123", left),
            hardened.host_build_digest("darwin", "25.0.0", "25A123", right),
        )
        # The same property across the leading fields, which are adjacent in the
        # hashed stream: identity || version || identifier.
        self.assertNotEqual(
            hardened.host_build_digest("darwin", "25.0", "025A123", []),
            hardened.host_build_digest("darwin", "25.0025", "A123", []),
        )

    def test_a_truncated_observation_list_is_a_different_input(self) -> None:
        """The framing already separates them; the count states the cardinality.

        Both implementations must agree on it, which is what the
        cross-implementation fixture recomputation proves.
        """
        full = [(b"kern.osversion", b"25A123"), (b"kern.version", b"x")]
        self.assertNotEqual(
            hardened.host_build_digest("darwin", "25.0.0", "25A123", full),
            hardened.host_build_digest("darwin", "25.0.0", "25A123", full[:1]),
        )

    def test_hashing_only_the_observed_values_would_alias(self) -> None:
        """What the boundary-shift fixture proves, stated as the probe it is."""
        base = self.fixtures()["macos-host-build"]
        shifted = self.fixtures()["macos-host-build-source-boundary-shift"]
        self.assertEqual(
            "".join(entry["value"] for entry in base["sources"]),
            "".join(entry["value"] for entry in shifted["sources"]),
        )
        self.assertNotEqual(
            [entry["value"] for entry in base["sources"]],
            [entry["value"] for entry in shifted["sources"]],
        )
        self.assertNotEqual(base["expected_sha256"], shifted["expected_sha256"])

    def test_the_construction_is_domain_separated(self) -> None:
        """A build identity must not collide with a component digest."""
        self.assertNotEqual(
            hardened.host_build_digest("", "", "", []), hardened.component_tree_digest([])
        )
        self.assertNotEqual(
            hardened.host_build_digest("", "", "", []), hardened.component_file_digest(b"")
        )

    def test_the_observed_tuple_is_inside_the_digest(self) -> None:
        sources = [(b"kern.osversion", b"25A123")]
        base = hardened.host_build_digest("darwin", "25.0.0", "25A123", sources)
        self.assertNotEqual(base, hardened.host_build_digest("linux", "25.0.0", "25A123", sources))
        self.assertNotEqual(base, hardened.host_build_digest("darwin", "25.1.0", "25A123", sources))
        self.assertNotEqual(base, hardened.host_build_digest("darwin", "25.0.0", "25A124", sources))

    def test_a_fixture_that_lies_about_its_digest_is_detected(self) -> None:
        with sandbox_tree() as root:
            vector = (
                root / "conformance" / "hardened" / "v1" / "vectors"
                / "hardened-identity-separation.json"
            )
            rewrite(
                vector,
                lambda document: document["host_build_fixtures"]["fixtures"][0].__setitem__(
                    "expected_sha256", "sha256:" + "0" * 64
                ),
            )
            with self.assertRaises(hardened.ValidationFailure) as caught:
                hardened.validate_host_build_fixtures(hardened.load_json(vector))
            self.assertIn("its own bytes produce", str(caught.exception))

    def test_a_fixture_whose_identifier_is_not_its_declared_source_is_detected(self) -> None:
        fixture = copy.deepcopy(self.fixtures()["macos-host-build"])
        fixture["identifier"] = "25A999"
        fixture["identifier_byte_length"] = len("25A999")
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.recompute_host_build_fixture("mutated", fixture)
        self.assertIn("not the value of its own", str(caught.exception))

    def test_a_fixture_that_drops_a_declared_source_is_detected(self) -> None:
        fixture = copy.deepcopy(self.fixtures()["macos-host-build"])
        fixture["sources"] = fixture["sources"][:2]
        fixture["source_count"] = 2
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.recompute_host_build_fixture("mutated", fixture)
        self.assertIn("declares", str(caught.exception))

    def test_a_fixture_that_observes_an_empty_source_is_detected(self) -> None:
        fixture = copy.deepcopy(self.fixtures()["macos-host-build"])
        fixture["sources"][2]["value"] = ""
        fixture["sources"][2]["value_byte_length"] = 0
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.recompute_host_build_fixture("mutated", fixture)
        self.assertIn("fails closed", str(caught.exception))

    def test_a_build_digest_no_fixture_reproduces_is_detected(self) -> None:
        with sandbox_tree() as root:
            receipt = (
                root / "conformance" / "hardened" / "v1" / "schema-cases"
                / "hardened-build-receipt-v3" / "valid.json"
            )
            rewrite(
                receipt,
                lambda document: document["tcb"]["host"]["build"].__setitem__(
                    "content_sha256", "sha256:" + "c" * 64
                ),
            )
            vector = hardened.load_json(
                root / "conformance" / "hardened" / "v1" / "vectors"
                / "hardened-identity-separation.json"
            )
            with self.assertRaises(hardened.ValidationFailure) as caught:
                hardened.validate_host_build_fixtures(vector)
            self.assertIn("no published fixture", str(caught.exception))

    def test_a_build_digest_carried_to_another_host_tuple_is_detected(self) -> None:
        with sandbox_tree() as root:
            receipt = (
                root / "conformance" / "hardened" / "v1" / "schema-cases"
                / "hardened-build-receipt-v3" / "valid.json"
            )
            # A real fixture digest, published beside a release it was not
            # computed over.
            rewrite(receipt, lambda document: document["tcb"]["host"].__setitem__("version", "25.9.0"))
            vector = hardened.load_json(
                root / "conformance" / "hardened" / "v1" / "vectors"
                / "hardened-identity-separation.json"
            )
            with self.assertRaises(hardened.ValidationFailure) as caught:
                hardened.validate_host_build_fixtures(vector)
            self.assertIn("computed over", str(caught.exception))

    def test_every_platform_admits_only_its_own_identifier_grammar(self) -> None:
        foreign = {
            "linux": "4f2a1c8e6b90d3574a1e2f8c0b7d69315ae4c2f8",
            "macos": "25A123",
            "windows": "26100.1",
        }
        for schema in (RECEIPT_V3, RECEIPT_V4, CLAIM_V4, MARKER_V4):
            document = valid_case(schema)
            records = (
                list(document["builds"].values()) if schema == MARKER_V4 else [document]
            )
            platform = records[0]["tcb"]["platform"]
            for other, identifier in foreign.items():
                if other == platform:
                    continue
                with self.subTest(schema=schema, identifier=other):
                    mutant = copy.deepcopy(document)
                    targets = (
                        list(mutant["builds"].values()) if schema == MARKER_V4 else [mutant]
                    )
                    for record in targets:
                        record["tcb"]["host"]["build"]["identifier"] = identifier
                    self.assertTrue(list(hardened.validator_for(schema).iter_errors(mutant)))

    def test_the_release_grammar_rejects_a_trailing_newline(self) -> None:
        """$ alone would admit this in an engine where it matches before \\n."""
        validator = hardened.validator_for(RECEIPT_V3)
        for value in ("25.0.0\n", "25.0.0 ", "twenty-five", "25.00.0", ""):
            with self.subTest(version=value):
                mutant = valid_case(RECEIPT_V3)
                mutant["tcb"]["host"]["version"] = value
                self.assertTrue(list(validator.iter_errors(mutant)))

    def test_the_schema_and_the_profile_declare_one_identifier_grammar(self) -> None:
        hardened.validate_schema_closed_value_sets()
        with sandbox_tree() as root:
            common = root / "schemas" / "hardened" / "v1" / "hardened-common.schema.json"

            def widen(document: dict) -> None:
                relation = document["$defs"]["hardenedHostBuildIdentifierPlatformRelationV1"]
                branch = relation["allOf"][0]
                branch["then"]["properties"]["host"]["properties"]["build"]["properties"][
                    "identifier"
                ]["pattern"] = "^.*$"

            rewrite(common, widen)
            with self.assertRaises(hardened.ValidationFailure) as caught:
                hardened.validate_schema_closed_value_sets()
            self.assertIn("kernel build identifiers", str(caught.exception))

    def test_the_normative_document_declares_the_sources_the_tools_hash(self) -> None:
        hardened.validate_host_build_declaration_document()

    def test_a_document_that_declares_another_source_list_is_detected(self) -> None:
        saved = dict(hardened.HOST_BUILD_SOURCES)
        try:
            hardened.HOST_BUILD_SOURCES = dict(
                saved, macos=["kern.osversion", "kern.osproductversion"]
            )
            with self.assertRaises(hardened.ValidationFailure) as caught:
                hardened.validate_host_build_declaration_document()
            self.assertIn("but the profile hashes", str(caught.exception))
        finally:
            hardened.HOST_BUILD_SOURCES = saved

    def test_a_construction_probe_cannot_be_a_conforming_observed_host(self) -> None:
        with sandbox_tree() as root:
            receipt = (
                root / "conformance" / "hardened" / "v1" / "schema-cases"
                / "hardened-build-receipt-v3" / "valid.json"
            )
            vector_path = (
                root / "conformance" / "hardened" / "v1" / "vectors"
                / "hardened-identity-separation.json"
            )
            probe = next(
                item
                for item in hardened.load_json(vector_path)["host_build_fixtures"]["fixtures"]
                if item["name"] == "macos-host-build-source-boundary-shift"
            )

            def adopt(document: dict) -> None:
                host = document["tcb"]["host"]
                host["version"] = probe["host_version"]
                host["build"]["identifier"] = probe["identifier"]
                host["build"]["content_sha256"] = probe["expected_sha256"]

            rewrite(receipt, adopt)
            with self.assertRaises(hardened.ValidationFailure) as caught:
                hardened.validate_host_build_fixtures(hardened.load_json(vector_path))
            self.assertIn("construction probe rather than an observed host", str(caught.exception))

    def test_the_kernel_build_identity_facets_each_have_a_rotation(self) -> None:
        vector = load_identity()
        coverage = {
            item["aspect"]: item
            for item in vector["tcb_completeness"]["host_build_identity"][
                "host_build_rotation_coverage"
            ]
        }
        self.assertEqual(set(coverage), hardened.HOST_BUILD_ASPECTS)
        cases = {item["name"]: item for item in vector["tcb_rotation_cases"]}
        for aspect, item in coverage.items():
            with self.subTest(aspect=aspect):
                self.assertTrue(item["rotated_by"])
                for name in item["rotated_by"]:
                    self.assertIn(aspect, cases[name]["rotated_host_build_aspects"])

    def test_a_facet_credited_to_a_rotation_that_does_not_declare_it_is_detected(self) -> None:
        with sandbox_tree() as root:
            vector = (
                root / "conformance" / "hardened" / "v1" / "vectors"
                / "hardened-identity-separation.json"
            )

            def strip(document: dict) -> None:
                for case in document["tcb_rotation_cases"]:
                    if case["name"] == "rotate-host-build-source":
                        case["rotated_host_build_aspects"] = []

            rewrite(vector, strip)
            with self.assertRaises(hardened.ValidationFailure) as caught:
                hardened.validate_tcb_rotation(hardened.load_json(vector))
            self.assertIn("does not declare", str(caught.exception))

    def test_the_recompiled_kernel_rotation_moves_the_cache_key(self) -> None:
        cases = {item["name"]: item for item in load_identity()["tcb_rotation_cases"]}
        rebuilt = cases["rotate-host-build-source"]
        self.assertTrue(rebuilt["cache_key_differs_from_base"])
        self.assertNotEqual(rebuilt["cache_key"], rebuilt["base_cache_key"])
        # Nothing a package can see differs, so only the observed kernel moved it.
        self.assertFalse(rebuilt["package_visible_input_changed"])


class IdentityReverificationTests(unittest.TestCase):
    """Review cycle 4 finding R4-2.

    ``identity-reverification`` ran before ``domain-teardown``, so it could not
    prove the trusted computing base was unchanged through the last domain
    member's exit, and the manager obligation rechecked four of the twelve
    members the record hashes.
    """

    def test_teardown_precedes_reverification_which_precedes_publication(self) -> None:
        order = hardened.ORDERED_PHASES
        self.assertLess(order.index("domain-teardown"), order.index("identity-reverification"))
        self.assertLess(order.index("identity-reverification"), order.index("publication"))

    def test_the_documents_and_the_vector_agree_on_the_new_order(self) -> None:
        hardened.validate_phase_list_documents()

    def test_the_normative_documents_state_the_complete_check(self) -> None:
        hardened.validate_reverification_documents()

    def test_a_manager_obligation_that_drops_the_complete_record_is_detected(self) -> None:
        saved = hardened.MANAGER_DOCUMENT
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "manager-hardened.md"
            text = saved.read_text(encoding="utf-8")
            row = next(
                line
                for line in text.splitlines()
                if line.startswith("| `identity-reverification` |")
            )
            path.write_text(
                text.replace(
                    row,
                    "| `identity-reverification` | manager parent | Re-verify the supervisor, "
                    "worker, source-snapshot, and fingerprinted toolchain identities. |",
                ),
                encoding="utf-8",
            )
            hardened.MANAGER_DOCUMENT = path
            try:
                with self.assertRaises(hardened.ValidationFailure) as caught:
                    hardened.validate_reverification_documents()
                self.assertIn("does not state", str(caught.exception))
            finally:
                hardened.MANAGER_DOCUMENT = saved

    def test_a_protocol_section_that_drops_a_member_is_detected(self) -> None:
        saved = hardened.PROTOCOL_DOCUMENT
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "hardened-execution.md"
            text = saved.read_text(encoding="utf-8")
            path.write_text(
                text.replace(
                    "| `trusted_components` | every component of section 2.3.1",
                    "| `some_components` | some components of section 2.3.1",
                ),
                encoding="utf-8",
            )
            hardened.PROTOCOL_DOCUMENT = path
            try:
                with self.assertRaises(hardened.ValidationFailure) as caught:
                    hardened.validate_reverification_documents()
                self.assertIn("trusted_components", str(caught.exception))
            finally:
                hardened.PROTOCOL_DOCUMENT = saved

    def test_reverification_covers_every_mutable_member_and_the_snapshot(self) -> None:
        check = load_profile()["identity_reverification"]
        expected = sorted(
            (set(hardened.TCB_FIELDS) - hardened.TCB_CONSTANT_FIELDS) | {"source-snapshot"}
        )
        self.assertEqual(check["reverified_members"], expected)
        for field in ("host", "backend", "parent_sha256", "trusted_components"):
            self.assertIn(field, check["reverified_members"])

    def test_a_partial_reverification_is_detected(self) -> None:
        profile = load_profile()
        profile["identity_reverification"]["reverified_members"] = [
            member
            for member in profile["identity_reverification"]["reverified_members"]
            if member != "host"
        ]
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_identity_reverification(profile)
        self.assertIn("missing=['host']", str(caught.exception))

    def test_reverifying_before_teardown_is_detected(self) -> None:
        profile = load_profile()
        saved = hardened.ORDERED_PHASES
        try:
            reordered = list(saved)
            teardown = reordered.index("domain-teardown")
            reverify = reordered.index("identity-reverification")
            reordered[teardown], reordered[reverify] = reordered[reverify], reordered[teardown]
            hardened.ORDERED_PHASES = reordered
            with self.assertRaises(hardened.ValidationFailure) as caught:
                hardened.validate_identity_reverification(profile)
            self.assertIn("destroyed and joined", str(caught.exception))
        finally:
            hardened.ORDERED_PHASES = saved

    def test_a_restated_record_does_not_discharge_the_obligation(self) -> None:
        profile = load_profile()
        for field in ("restating_earlier_record_permitted", "partial_reverification_permitted"):
            with self.subTest(field=field):
                mutant = copy.deepcopy(profile)
                mutant["identity_reverification"][field] = True
                with self.assertRaises(hardened.ValidationFailure) as caught:
                    hardened.validate_identity_reverification(mutant)
                self.assertIn(field, str(caught.exception))

    def test_a_weaker_comparison_than_byte_identity_is_detected(self) -> None:
        profile = load_profile()
        profile["identity_reverification"]["comparison"] = "digest-only"
        with self.assertRaises(hardened.ValidationFailure) as caught:
            hardened.validate_identity_reverification(profile)
        self.assertIn("weaker than a byte-identical record", str(caught.exception))

    def test_every_reverified_member_has_an_adversarial_omission_case(self) -> None:
        cases = {item["name"]: item for item in load_adversarial()["reverification_cases"]}
        omitted = {
            case["omitted_member"] for case in cases.values() if case["kind"] == "omitted-member"
        }
        expected = sorted(
            (set(hardened.TCB_FIELDS) - hardened.TCB_CONSTANT_FIELDS) | {"source-snapshot"}
        )
        self.assertEqual(sorted(omitted), expected)
        self.assertEqual(
            {case["kind"] for case in cases.values()}, hardened.REVERIFICATION_CASE_KINDS
        )
        for name, case in cases.items():
            with self.subTest(case=name):
                self.assertFalse(case["published"])
                self.assertFalse(case["cache_entry_written"])
                self.assertFalse(case["marker_updated"])
                self.assertEqual(case["expected_error"], "hardened_tcb_identity_invalid")

    def test_a_dropped_omission_case_is_detected(self) -> None:
        with sandbox_tree() as root:
            vector = (
                root / "conformance" / "hardened" / "v1" / "vectors"
                / "hardened-adversarial-vectors.json"
            )

            def drop(document: dict) -> None:
                document["reverification_cases"] = [
                    case
                    for case in document["reverification_cases"]
                    if case["omitted_member"] != "trusted_components"
                ]

            rewrite(vector, drop)
            with self.assertRaises(hardened.ValidationFailure) as caught:
                hardened.validate_adversarial_vector(load_profile())
            self.assertIn("without an omission case", str(caught.exception))

    def test_an_exact_cache_hit_skips_the_reverification_it_has_nothing_to_check(self) -> None:
        phases = {item["name"]: item for item in load_profile()["ordered_phases"]}
        self.assertTrue(phases["identity-reverification"]["skipped_on_exact_cache_hit"])
        self.assertTrue(phases["domain-teardown"]["skipped_on_exact_cache_hit"])
        self.assertFalse(phases["publication"]["skipped_on_exact_cache_hit"])


class SuiteIntegrityTests(unittest.TestCase):
    def test_portable_suite_still_matches_its_own_release_pin(self) -> None:
        hardened.validate_portable_profile_unchanged()

    def test_a_hardened_file_under_the_portable_suite_is_detected(self) -> None:
        with sandbox_tree() as root:
            manifest = root / "conformance" / "v1" / "manifest.json"
            rewrite(
                manifest,
                lambda document: document["files"].insert(
                    0, {"path": "hardened/leak.json", "sha256": "sha256:" + "0" * 64}
                ),
            )
            with self.assertRaises(hardened.ValidationFailure):
                hardened.validate_portable_profile_unchanged()

    def test_tampered_hardened_vector_fails_the_manifest_digest(self) -> None:
        with sandbox_tree() as root:
            vector = (
                root
                / "conformance"
                / "hardened"
                / "v1"
                / "vectors"
                / "hardened-execution-profile.json"
            )
            vector.write_text(vector.read_text(encoding="utf-8") + " ", encoding="utf-8")
            with self.assertRaises(hardened.ValidationFailure) as caught:
                hardened.validate_hardened_manifest()
            self.assertIn("digest mismatch", str(caught.exception))

    def test_untracked_hardened_file_fails_the_manifest_inventory(self) -> None:
        with sandbox_tree() as root:
            extra = root / "conformance" / "hardened" / "v1" / "vectors" / "stray.json"
            extra.write_text("{}\n", encoding="utf-8")
            with self.assertRaises(hardened.ValidationFailure) as caught:
                hardened.validate_hardened_manifest()
            self.assertIn("inventory mismatch", str(caught.exception))

    def test_release_metadata_cannot_fabricate_a_qualified_platform(self) -> None:
        with sandbox_tree() as root:
            release = root / "release" / "hardened-1.0.0-rc.1.json"
            rewrite(
                release,
                lambda document: document.__setitem__("qualified_platforms", ["linux"]),
            )
            with self.assertRaises(hardened.ValidationFailure) as caught:
                hardened.validate_hardened_release()
            self.assertIn("fabricates a qualified platform", str(caught.exception))

    def test_release_metadata_cannot_fabricate_a_claim(self) -> None:
        with sandbox_tree() as root:
            release = root / "release" / "hardened-1.0.0-rc.1.json"
            rewrite(
                release,
                lambda document: document["claim_v4"].__setitem__(
                    "claims_emitted", [{"implementation": "example"}]
                ),
            )
            with self.assertRaises(hardened.ValidationFailure) as caught:
                hardened.validate_hardened_release()
            self.assertIn("fabricates conformance claims", str(caught.exception))

    def test_release_metadata_cannot_misreport_the_portable_baseline(self) -> None:
        with sandbox_tree() as root:
            release = root / "release" / "hardened-1.0.0-rc.1.json"
            rewrite(
                release,
                lambda document: document["portable_baseline"].__setitem__("modified", True),
            )
            with self.assertRaises(hardened.ValidationFailure) as caught:
                hardened.validate_hardened_release()
            self.assertIn("misreports the portable baseline", str(caught.exception))

    def test_adversarial_vector_cannot_claim_native_evidence(self) -> None:
        with sandbox_tree() as root:
            vector = (
                root
                / "conformance"
                / "hardened"
                / "v1"
                / "vectors"
                / "hardened-adversarial-vectors.json"
            )
            rewrite(
                vector,
                lambda document: document.__setitem__("evidence_status", "validated"),
            )
            profile = hardened.load_json(
                hardened.HARDENED_SUITE / "vectors" / "hardened-execution-profile.json"
            )
            with self.assertRaises(hardened.ValidationFailure) as caught:
                hardened.validate_adversarial_vector(profile)
            self.assertIn("claim evidence this revision does not have", str(caught.exception))

    def test_every_capability_class_needs_a_forced_unavailable_case(self) -> None:
        with sandbox_tree() as root:
            vector = (
                root
                / "conformance"
                / "hardened"
                / "v1"
                / "vectors"
                / "hardened-adversarial-vectors.json"
            )

            def drop(document: dict) -> None:
                document["capability_preflight_cases"] = [
                    case
                    for case in document["capability_preflight_cases"]
                    if case["forced_unavailable"] != "exec-path-allowlist"
                ]

            rewrite(vector, drop)
            profile = hardened.load_json(
                hardened.HARDENED_SUITE / "vectors" / "hardened-execution-profile.json"
            )
            with self.assertRaises(hardened.ValidationFailure) as caught:
                hardened.validate_adversarial_vector(profile)
            self.assertIn("forced-unavailable case", str(caught.exception))

    def test_preflight_case_cannot_fall_back_to_the_portable_profile(self) -> None:
        with sandbox_tree() as root:
            vector = (
                root
                / "conformance"
                / "hardened"
                / "v1"
                / "vectors"
                / "hardened-adversarial-vectors.json"
            )

            def allow_fallback(document: dict) -> None:
                document["capability_preflight_cases"][0]["falls_back_to_portable"] = True

            rewrite(vector, allow_fallback)
            profile = hardened.load_json(
                hardened.HARDENED_SUITE / "vectors" / "hardened-execution-profile.json"
            )
            with self.assertRaises(hardened.ValidationFailure) as caught:
                hardened.validate_adversarial_vector(profile)
            self.assertIn("fail-closed boundary", str(caught.exception))

    def test_a_receipt_whose_tcb_digest_lies_is_detected(self) -> None:
        with sandbox_tree() as root:
            receipt = (
                root
                / "conformance"
                / "hardened"
                / "v1"
                / "schema-cases"
                / "hardened-build-receipt-v3"
                / "valid.json"
            )

            def swap(document: dict) -> None:
                document["tcb"]["worker_sha256"] = "sha256:" + "9" * 64

            rewrite(receipt, swap)
            with self.assertRaises(hardened.ValidationFailure) as caught:
                hardened.validate_identity_binding_chain()
            self.assertIn("does not reproduce its own TCB record", str(caught.exception))

    def test_a_receipt_whose_cache_key_ignores_the_binding_is_detected(self) -> None:
        with sandbox_tree() as root:
            receipt = (
                root
                / "conformance"
                / "hardened"
                / "v1"
                / "schema-cases"
                / "hardened-build-receipt-v3"
                / "valid.json"
            )

            def unbind(document: dict) -> None:
                stripped = {k: v for k, v in document["input"].items() if k != "hardened"}
                document["cache_key"] = hardened.ccj1_sha256(stripped)

            rewrite(receipt, unbind)
            with self.assertRaises(hardened.ValidationFailure) as caught:
                hardened.validate_identity_binding_chain()
            self.assertIn("not the digest of its own input", str(caught.exception))

    def test_a_marker_reporting_another_trusted_computing_base_is_detected(self) -> None:
        with sandbox_tree() as root:
            marker = (
                root
                / "conformance"
                / "hardened"
                / "v1"
                / "schema-cases"
                / "hardened-install-marker-v4"
                / "valid.json"
            )

            def swap(document: dict) -> None:
                for record in document["builds"].values():
                    record["tcb"]["supervisor_sha256"] = "sha256:" + "8" * 64

            rewrite(marker, swap)
            with self.assertRaises(hardened.ValidationFailure) as caught:
                hardened.validate_identity_binding_chain()
            self.assertIn("does not follow from its own identities", str(caught.exception))

    def test_a_protocol_phase_list_that_drifts_is_detected(self) -> None:
        with sandbox_tree() as root:
            shutil.copytree(REPO / "protocol", root / "protocol")
            shutil.copytree(REPO / "profiles", root / "profiles")
            saved = (hardened.PROTOCOL_DOCUMENT, hardened.MANAGER_DOCUMENT)
            hardened.PROTOCOL_DOCUMENT = root / "protocol" / "hardened-execution.md"
            hardened.MANAGER_DOCUMENT = root / "profiles" / "manager-hardened.md"
            try:
                text = hardened.PROTOCOL_DOCUMENT.read_text(encoding="utf-8")
                text = text.replace(
                    "| 9 | `in-domain-guarantee-self-test` |",
                    "| 9 | `domain-guarantee-self-test` |",
                )
                hardened.PROTOCOL_DOCUMENT.write_text(text, encoding="utf-8")
                with self.assertRaises(hardened.ValidationFailure) as caught:
                    hardened.validate_phase_list_documents()
                self.assertIn("does not state the ordered phase list", str(caught.exception))
            finally:
                hardened.PROTOCOL_DOCUMENT, hardened.MANAGER_DOCUMENT = saved

    def test_a_manager_profile_that_restates_its_own_order_is_detected(self) -> None:
        with sandbox_tree() as root:
            shutil.copytree(REPO / "protocol", root / "protocol")
            shutil.copytree(REPO / "profiles", root / "profiles")
            saved = (hardened.PROTOCOL_DOCUMENT, hardened.MANAGER_DOCUMENT)
            hardened.PROTOCOL_DOCUMENT = root / "protocol" / "hardened-execution.md"
            hardened.MANAGER_DOCUMENT = root / "profiles" / "manager-hardened.md"
            try:
                text = hardened.MANAGER_DOCUMENT.read_text(encoding="utf-8")
                text = text.replace(
                    "| `in-domain-guarantee-self-test` |",
                    "| `domain-guarantee-self-test` |",
                )
                hardened.MANAGER_DOCUMENT.write_text(text, encoding="utf-8")
                with self.assertRaises(hardened.ValidationFailure) as caught:
                    hardened.validate_phase_list_documents()
                self.assertIn("does not mirror the ordered phase list", str(caught.exception))
            finally:
                hardened.PROTOCOL_DOCUMENT, hardened.MANAGER_DOCUMENT = saved

    def test_schema_cases_require_positive_and_negative_coverage(self) -> None:
        with sandbox_tree() as root:
            index = root / "conformance" / "hardened" / "v1" / "schema-cases" / "index.json"

            def drop_negatives(document: list) -> None:
                document[:] = [
                    case
                    for case in document
                    if not (
                        case["schema"] == "hardened-build-receipt-v3.schema.json"
                        and not case["valid"]
                    )
                ]

            rewrite(index, drop_negatives)
            with self.assertRaises(hardened.ValidationFailure) as caught:
                hardened.validate_hardened_schemas()
            self.assertIn("without negative cases", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
