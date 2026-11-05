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
