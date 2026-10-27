"""Profile PATH specification-data witnesses; no process or runtime qualification."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest


CORPUS = Path(__file__).resolve().parents[1] / "conformance/profile-command-path/cases.json"
BINDINGS = ("profile", "lock_sha256", "plan_sha256", "generation")


def merge(base, changes):
    result = copy.deepcopy(base)
    for key, value in changes.items():
        if isinstance(value, dict):
            result[key] = merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def candidate_violations(evidence):
    """Compare abstract start-boundary evidence, without authenticating its inputs."""
    admitted, candidate = evidence["admitted"], evidence["candidate"]
    violations = []
    if admitted["root_state"] != "verified":
        violations.append("root-integrity")
    if admitted["current_profile"] != admitted["binding"]["profile"]:
        violations.append("isolated-current-profile")
    if admitted["routing"] != "exclusive":
        violations.append("exclusive-routing")
    if candidate["transport"] != "supported":
        violations.append("required-understanding")
    if candidate["path_prepend"] != admitted["root"] or candidate["receipt"]["root"] != admitted["root"]:
        violations.append("verified-root")
    for prefix, binding in (("receipt", candidate["receipt"]["binding"]),
                            ("process", candidate["binding"])):
        for field in BINDINGS:
            if binding.get(field) != admitted["binding"][field]:
                violations.append(f"{prefix}-{field.removesuffix('_sha256')}-binding")
    expected_path = admitted["protected_tools"] + [admitted["root"]] + admitted["base_path"]
    if candidate["path"] != expected_path:
        violations.append("effective-path")
    if candidate["command"] != admitted["command"]:
        violations.append("reached-command")
    return violations


def child_violations(evidence, child):
    """Compare a supplied final-child witness with admitted identity and order."""
    violations = candidate_violations(evidence)
    if child is None:
        return violations + ["missing-child-witness"]
    candidate = evidence["candidate"]
    if child["path"] != candidate["path"] or child["path_value"] != ":".join(child["path"]):
        violations.append("child-path")
    if child["command"] != candidate["command"]:
        violations.append("child-command")
    if child["binding"] != candidate["binding"]:
        violations.append("child-binding")
    return violations


class ProfileCommandPathTests(unittest.TestCase):
    def setUp(self):
        self.corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
        self.cases = {case["name"]: case for case in self.corpus["cases"]}

    # Pins the required fault inventory and route/form matrix, not product support.
    def test_case_matrix(self):
        self.assertEqual(self.corpus["kind"], "profile-command-path-evidence-not-wire")
        self.assertEqual(self.corpus["slice"], "A")
        self.assertEqual(self.corpus["launch_forms"], [
            "interactive", "managed-one-shot", "new-child-on-resume-or-restart"])
        self.assertEqual(len(self.cases), len(self.corpus["cases"]))
        self.assertEqual(set(self.cases), {
            "verified-root", "empty-command-set", "missing-root", "tampered-root", "unreadable-root",
            "stale-lock", "wrong-plan", "wrong-generation", "foreign-inherited-root",
            "hosted-drops-root", "inert-path-prepend", "root-before-protected-tools",
            "ambient-path-recomputed", "wrong-reached-path", "wrong-reached-digest",
            "missing-lock-binding", "unsupported-transport", "other-current-profile", "routing-unproven",
        })
        for name, case in self.cases.items():
            self.assertEqual(case["routes"], ["hosted"] if name == "hosted-drops-root" else ["native", "hosted"])

    # Every row detects its named assertion failure; successful controls require
    # all three child witnesses. Refusals preserve preimages and forbid starts/fallback.
    def test_paired_start_boundary_and_child_witnesses(self):
        for case in self.cases.values():
            evidence = merge(self.corpus["base"], case["changes"])
            expected = case["expected"]
            for route in case["routes"]:
                for form in self.corpus["launch_forms"]:
                    with self.subTest(case=case["name"], route=route, form=form):
                        violations = candidate_violations(evidence)
                        self.assertEqual(violations, expected["violations"])
                        self.assertEqual(not violations, expected["admissible"])
                        self.assertEqual(expected["fallbacks"], 0)
                        self.assertEqual(expected["live_preimage"], "unchanged")
                        if expected["admissible"]:
                            self.assertEqual(expected["provider_starts"], 1)
                            self.assertEqual(child_violations(evidence, expected["child"]), [])
                        else:
                            self.assertEqual(expected["provider_starts"], 0)
                            self.assertIsNone(expected["child"])

    # Bounded instrument controls: corrupt actual-child PATH, reached path/digest
    # or lock binding, and require the intended failure alongside a valid control.
    def test_forged_successful_child_is_rejected(self):
        evidence = self.corpus["base"]
        child = self.cases["verified-root"]["expected"]["child"]
        self.assertEqual(child_violations(evidence, child), [])
        plants = [
            ({"path": child["path"][1:], "path_value": ":".join(child["path"][1:])}, "child-path"),
            ({"command": {"path": "/fixture/foreign/sample"}}, "child-command"),
            ({"command": {"sha256": "sha256:" + "0" * 64}}, "child-command"),
            ({"binding": {"lock_sha256": "sha256:" + "0" * 64}}, "child-binding"),
        ]
        for changes, failure in plants:
            with self.subTest(changes=changes):
                self.assertEqual(child_violations(evidence, merge(child, changes)), [failure])
        self.assertEqual(child_violations(evidence, None), ["missing-child-witness"])


if __name__ == "__main__":
    unittest.main()
