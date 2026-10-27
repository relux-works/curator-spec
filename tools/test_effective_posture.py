"""Specification evidence only; no launcher, sandbox or provider certification."""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import ValidationError

import effective_posture as ep
import home_leases

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "conformance/effective-posture-v1"


class EffectivePostureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = ep.validator(ROOT)
        cls.fixtures = json.loads((SUITE / "fixtures.json").read_text())["fixtures"]
        cls.cases = json.loads((SUITE / "cases.json").read_text())["pairs"]
        cls.golden = (SUITE / "default-yolo.ccj").read_bytes()

    # Every published negative has its adjacent admitted control and exact named verdict.
    def test_published_corpus(self):
        self.assertEqual(ep.check_corpus(ROOT), 26)
        before = ep.ccj(self.fixtures)
        ep.check_pairs(self.fixtures, self.cases, self.schema)
        self.assertEqual(ep.ccj(self.fixtures), before, "oracle must not repair fixture input")

    # Literal counterexamples independently exercise the requested families, without vector mutation machinery.
    def test_independent_required_counterexamples(self):
        for fixture, path, value, reason in [
            ("native", ("permission", "mode"), "automatic", "posture_invalid"),
            ("native", ("binding", "lock_sha256"), "sha256:" + "f" * 64, "posture_binding_stale"),
            ("native", ("binding", "plan_sha256"), "sha256:" + "e" * 64, "posture_binding_stale"),
            ("strict", ("project", "mode"), "none", "posture_downgrade"),
            ("no-tools", ("project", "no_tools"), False, "posture_downgrade"),
        ]:
            with self.subTest(fixture=fixture, path=path):
                valid = copy.deepcopy(self.fixtures[fixture])
                self.assertEqual(ep.relation_verdict(valid, self.schema), "admit")
                bad = copy.deepcopy(valid)
                bad["posture"][path[0]][path[1]] = value
                self.assertEqual(ep.relation_verdict(bad, self.schema), reason)
        valid = copy.deepcopy(self.fixtures["native"])
        self.assertEqual(ep.relation_verdict(valid, self.schema), "admit")
        del valid["posture"]
        self.assertEqual(ep.relation_verdict(valid, self.schema), "posture_missing")
        for negative, positive, reason in [
            ("unqualified-native-project", "native-project", "posture_unqualified"),
            ("policy-suffix", "native", "posture_suffix_conflict"),
            ("unsupported-strict", "strict", "posture_strict_unsupported"),
            ("unsupported-no-tools", "no-tools", "posture_no_tools_unsupported"),
        ]:
            with self.subTest(fixture=negative):
                self.assertEqual(ep.relation_verdict(self.fixtures[positive], self.schema), "admit")
                self.assertEqual(ep.relation_verdict(self.fixtures[negative], self.schema), reason)

    # Strict wins both selectors; no-tools is still mandatory; all resolution sources preserve provenance, not approval.
    def test_precedence_sources_and_approval(self):
        f = self.fixtures["strict-both-no-tools"]
        self.assertTrue(f["posture"]["project"]["requested"]["strict"])
        self.assertTrue(f["posture"]["project"]["requested"]["native_project"])
        self.assertTrue(f["posture"]["project"]["no_tools"])
        self.assertEqual(ep.relation_verdict(f, self.schema), "admit")
        # An internally consistent rewrite with a fresh digest still differs from protected intent.
        bad = copy.deepcopy(f)
        bad["posture"]["project"].update(
            requested={"strict": False, "native_project": False, "no_tools": True}, mode="none")
        self.schema.validate(bad["posture"])
        self.assertNotEqual(ep.digest(bad["posture"]), ep.digest(f["posture"]))
        self.assertEqual(ep.relation_verdict(bad, self.schema), "posture_downgrade")
        for source in ("default", "profile", "machine", "lane-record", "flag"):
            with self.subTest(source=source):
                f = copy.deepcopy(self.fixtures["default-yolo"])
                for permission in (f["posture"]["permission"], f["context"]["resolved_permission"]):
                    permission["source"] = source
                self.assertEqual(ep.relation_verdict(f, self.schema), "admit")
                f["context"]["lane"]["approved"] = False
                self.assertEqual(ep.relation_verdict(f, self.schema), "posture_lane_unapproved")

    # Re-hashing a changed suffix cannot turn a policy selector into a permitted argument; a known policy-free suffix works.
    def test_suffix_parsing_is_independent_of_digest(self):
        f = copy.deepcopy(self.fixtures["native"])
        f["posture"]["native_suffix"] = {"argv": ["--model", "fixture-model"],
                                            "sha256": ep.digest(["--model", "fixture-model"])}
        self.assertEqual(ep.relation_verdict(f, self.schema), "admit")
        for argv in (["--sandbox", "danger-full-access"], ["--unknown"], ["-c", "approval_policy=never"]):
            with self.subTest(argv=argv):
                f["posture"]["native_suffix"] = {"argv": argv, "sha256": ep.digest(argv)}
                self.assertEqual(ep.relation_verdict(f, self.schema), "posture_suffix_conflict")

    # Exact CCJ-1 wire bytes are required; each malformed spelling is paired with the same valid golden.
    def test_canonical_wire_pairs(self):
        for raw, reason in [
            (self.golden + b"\n", "noncanonical"),
            (b"\xef\xbb\xbf" + self.golden, "BOM"),
            (self.golden.replace(b'"record":"effective-posture/1"', b'"record":"effective-posture/1","record":"effective-posture/1"'), "duplicate"),
            (self.golden.replace(b'"generation":"fixture-generation-1"', b'"generation":"\\ud800"'), "surrogate"),
            (self.golden.replace(b'"no_tools":false', b'"no_tools":NaN', 1), "non-CCJ-1"),
            (self.golden.replace(b'"no_tools":false', b'"no_tools":1.0', 1), "non-CCJ-1"),
            (self.golden.replace(b'"no_tools":false', b'"no_tools":-0', 1), "integer spelling"),
            (self.golden.replace(b'"no_tools":false', b'"no_tools":9007199254740992', 1), "unsafe integer"),
        ]:
            with self.subTest(reason=reason):
                self.assertEqual(ep.decode_record(self.golden, self.schema)["record"], "effective-posture/1")
                with self.assertRaises((ValueError, UnicodeError)):
                    ep.decode_record(raw, self.schema)
        # Size and depth fail at their intended parser bounds, rather than a later schema rejection.
        with self.assertRaisesRegex(ValueError, "record size"):
            ep.decode_record(b" " * (ep.LIMIT + 1), self.schema)
        with self.assertRaisesRegex(ValueError, "record depth"):
            ep.decode_record(b"[" * 14 + b"0" + b"]" * 14, self.schema)

    # Every object instance rejects unknown fields; schema-valid negatives remain relational refusals.
    def test_closed_schema_and_types(self):
        p = copy.deepcopy(self.fixtures["hosted"]["posture"])
        self.schema.validate(p)
        paths = [(), ("permission",), ("native_policy",), ("native_suffix",), ("project",),
                 ("project", "requested"), ("provider",), ("qualification",), ("binding",),
                 ("provenance",), ("provenance", "launcher_state"), ("provenance", "home_lease")]
        for path in paths:
            with self.subTest(path=path):
                bad = copy.deepcopy(p)
                target = bad
                for key in path:
                    target = target[key]
                target["unexpected"] = True
                with self.assertRaises(ValidationError):
                    self.schema.validate(bad)
        for path, value in [(("permission", "source"), "global"),
                            (("native_policy", "policy_sha256"), "sha256:" + "A" * 64),
                            (("provenance", "home_lease", "revision"), True)]:
            bad = copy.deepcopy(p)
            target = bad
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            with self.assertRaises(ValidationError):
                self.schema.validate(bad)
        for case in self.cases:
            if case["id"] in {"EP07-stale-lock", "EP08-stale-plan", "EP09-strict-downgrade", "EP04-suffix-policy"}:
                bad = ep.materialize(self.fixtures, case["refuse"])
                self.schema.validate(bad["posture"])
                self.assertEqual(ep.relation_verdict(bad, self.schema), case["refuse"]["expected"])

    # Provenance binds a complete prepared #193 record; terminal replay, foreign launch and altered state never admit.
    def test_provenance_relations_and_lease_schema(self):
        valid = copy.deepcopy(self.fixtures["hosted"])
        home_leases.validators(ROOT)["record"].validate(valid["context"]["home_lease"])
        self.assertEqual(ep.relation_verdict(valid, self.schema), "admit")
        for target in ("launch-id", "binding", "lease-lock", "request", "terminal"):
            with self.subTest(target=target):
                f = copy.deepcopy(valid)
                if target == "launch-id":
                    f["posture"]["provenance"]["launch_id"] = "a" * 32
                elif target == "binding":
                    f["context"]["launcher_state"]["binding"]["profile"] = "foreign-profile"
                elif target == "lease-lock":
                    f["context"]["home_lease"]["lock_sha256"] = "f" * 64
                elif target == "request":
                    f["posture"]["provenance"]["home_lease"]["request_id"] = "foreign-request"
                else:
                    f["context"]["home_lease"]["phase"] = "broken"
                self.assertEqual(ep.relation_verdict(f, self.schema),
                                 "posture_lease_unavailable" if target == "terminal" else "posture_provenance_mismatch")

    # Plants establish that the corpus checker catches an accept-all or refuse-all oracle, and missing controls/coverage.
    def test_checker_control_plants(self):
        ep.check_pairs(self.fixtures, self.cases, self.schema)
        with patch.object(ep, "relation_verdict", return_value="admit"):
            with self.assertRaisesRegex(ValueError, "refuse mismatch EP01-missing: admit"):
                ep.check_pairs(self.fixtures, self.cases, self.schema)
        with patch.object(ep, "relation_verdict", return_value="posture_missing"):
            with self.assertRaisesRegex(ValueError, "admit mismatch EP01-missing"):
                ep.check_pairs(self.fixtures, self.cases, self.schema)
        bad = copy.deepcopy(self.cases)
        del bad[0]["admit"]
        with self.assertRaisesRegex(ValueError, "missing paired control"):
            ep.check_pairs(self.fixtures, bad, self.schema)
        with self.assertRaisesRegex(ValueError, "pair coverage mismatch"):
            ep.check_pairs(self.fixtures, self.cases[1:], self.schema)


if __name__ == "__main__":
    unittest.main()
