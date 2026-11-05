"""Successor corpus controls preserve the frozen rc.14 authority and release history."""
import copy
import json
import unittest
from unittest.mock import patch
import validate
import release_gate

V1 = "rc5-native-control-inventory-v1"
V2 = "rc5-native-control-inventory-v2"

class NativeControlSuccessorTests(unittest.TestCase):
    def vector(self):
        return validate.load_json(validate.ROOT / "conformance/go-native-controls-v2/go-host-execution-policy.json")

    # Both published identities are valid only in their own selected corpus.
    def test_both_corpora_have_positive_controls(self):
        validate.validate_go_host_execution_policy()
        validate.validate_go_native_controls_v2()
        for version, vector in ((V1, validate.load_json(validate.SUITE / "vectors/go-host-execution-policy.json")), (V2, self.vector())):
            validate.validate_go_host_execution_policy(vector, inventory_version=version)

    # A predecessor, unknown identity, lost Linux platform or record is rejected.
    def test_successor_rejects_drift_and_missing_linux(self):
        base = self.vector()
        for kind in ("predecessor", "unknown", "drop-linux-platform", "drop-linux-record"):
            with self.subTest(kind=kind):
                vector = copy.deepcopy(base)
                inv = vector["native_control_inventory"]
                if kind in {"predecessor", "unknown"}:
                    inv["version"] = V1 if kind == "predecessor" else "rc5-native-control-inventory-v999"
                elif kind == "drop-linux-platform":
                    inv["platforms"].remove("linux")
                else:
                    del inv["controls"][0]["platforms"]["linux"]
                with self.assertRaises(validate.ValidationFailure):
                    validate.validate_go_host_execution_policy(vector, inventory_version=V2)

    # Historical release metadata cannot claim v2; future v2 metadata cannot claim v1/unknown.
    def test_release_inventory_is_versioned_and_bound_to_corpus(self):
        for version in ("1.0.0-rc.5", "1.0.0-rc.6"):
            release_gate.validate_execution_inventory(version, V1)
            with self.assertRaises(release_gate.ReleaseFailure):
                release_gate.validate_execution_inventory(version, V2)
        release_gate.validate_execution_inventory("1.0.0-rc.15", V2)
        for bad in (V1, "unknown", None):
            with self.assertRaises(release_gate.ReleaseFailure):
                release_gate.validate_execution_inventory("1.0.0-rc.15", bad)
        with patch.object(release_gate, "load_json", return_value={"native_control_inventory": {"version": "unknown"}}):
            with self.assertRaisesRegex(release_gate.ReleaseFailure, "authority"):
                release_gate.validate_execution_inventory("1.0.0-rc.15", V2)

    # Neither valid corpus can be silently relabelled or sent through the other's validator.
    def test_frozen_and_successor_corpus_selection_is_not_interchangeable(self):
        frozen = validate.load_json(validate.SUITE / "vectors/go-host-execution-policy.json")
        relabelled = copy.deepcopy(frozen)
        relabelled["native_control_inventory"]["version"] = V2
        for vector, version in ((relabelled, V1), (self.vector(), V1), (frozen, V2)):
            with self.subTest(version=version):
                with self.assertRaisesRegex(validate.ValidationFailure, "inventory"):
                    validate.validate_go_host_execution_policy(vector, inventory_version=version)

    def check_release(self, version, current, reported, *, authority=V2):
        import hashlib
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            def write(path, value):
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(value), encoding="utf-8")
            (root / "README.md").write_text(f"**Version:** {version}\n", encoding="utf-8")
            (root / "CHANGELOG.md").write_text(f"## {version}\n", encoding="utf-8")
            write("conformance/v1/manifest.json", {"protocol_version": version, "files": []})
            digest = "sha256:" + hashlib.sha256((root / "conformance/v1/manifest.json").read_bytes()).hexdigest()
            metadata = {
                "protocol_version": version,
                "candidate_protocol_pin": {"manifest_sha256": digest},
                "downstream_consumption": {"required_manifest_sha256": digest},
                "assurance": {
                    "default_mode": "portable", "portable_execution_policy": "manager-worker-v1",
                    "verified_provider_contract": "host-execution-provider-v1",
                    "verified_implementations": [], "verified_platform_claims": [],
                    "silent_downgrade_permitted": False, "skill_vendored_provider_allowed": False,
                },
            }
            if reported is not None:
                metadata["execution_policy"] = {
                    "portable": "manager-worker-v1", "hardened_profile_claimed": False,
                    "hardened_profile_owner": "STORY-260728-327soo",
                    "capability_evidence_record_version": "capability-evidence-v1",
                    "native_control_inventory_version": reported,
                }
            write(f"release/{version}.json", metadata)
            write("conformance/go-native-controls-v2/go-host-execution-policy.json",
                  {"native_control_inventory": {"version": authority}})
            with patch.object(release_gate, "ROOT", root), patch.object(release_gate, "PROTOCOL_VERSION", current):
                release_gate.validate_version(version)

    # Real validate_version paths preserve history and reject current-candidate lies/omissions.
    def test_validate_version_enforces_successor_on_current_and_future_candidates(self):
        for current in ("1.0.0-rc.14", "1.0.0-rc.15"):
            self.check_release("1.0.0-rc.15", current, V2)
            for reported in (V1, "bogus", "", None):
                with self.subTest(current=current, reported=reported):
                    with self.assertRaisesRegex(release_gate.ReleaseFailure, "inventory mismatch"):
                        self.check_release("1.0.0-rc.15", current, reported)
            with self.assertRaisesRegex(release_gate.ReleaseFailure, "authority"):
                self.check_release("1.0.0-rc.15", current, V2, authority="bogus")
        for number in (5, 6):
            version = f"1.0.0-rc.{number}"
            self.check_release(version, "1.0.0-rc.14", V1)
            with self.assertRaisesRegex(release_gate.ReleaseFailure, "inventory mismatch"):
                self.check_release(version, "1.0.0-rc.14", V2)
        for number in range(7, 15):
            self.check_release(f"1.0.0-rc.{number}", "1.0.0-rc.14", None)
