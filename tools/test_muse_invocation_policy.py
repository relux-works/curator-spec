"""Closed specification-data declarations; no native parser or launch simulation."""

from __future__ import annotations

import itertools
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
VECTOR = ROOT / "conformance/environments-muse-invocation-policy/vectors.json"


def unique_members(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate member: {key}")
        result[key] = value
    return result


def load_document(text):
    return json.loads(text, object_pairs_hook=unique_members)


class MuseInvocationPolicyTests(unittest.TestCase):
    def setUp(self):
        self.vector = load_document(VECTOR.read_text(encoding="utf-8"))
        self.groups = {}
        for group in ("selection_cases", "identity_cases", "argument_cases", "fidelity_cases"):
            rows = self.vector[group]
            self.groups[group] = {row["name"]: row for row in rows}
            self.assertEqual(len(rows), len(self.groups[group]), f"duplicate case in {group}")

    def assert_json_equal(self, actual, expected, claim):
        # JSON comparison distinguishes boolean false from number 0 (Python == does not).
        self.assertEqual(json.dumps(actual, sort_keys=True, allow_nan=False),
                         json.dumps(expected, sort_keys=True, allow_nan=False), claim)

    def selection_input(self, choice=None, form="interactive", present=True, **overrides):
        # These labels describe corpus scenarios, not a proposed consumer wire/API grammar.
        result = {"runtime": "muse", "execution_kind": "native", "form": form,
                  "headless": False, "choice": choice, "root_context_present": present,
                  "raw_fact": {"exclusive": True} if present else None,
                  "selector_source": "none" if choice is None else "explicit"}
        result.update(overrides)
        return result

    def declaration(self, effective, argv):
        return {"verdict": "permit-declaration" if effective else "refuse",
                "effective": effective, "exclusion_argv": argv, "enabling_argv": [],
                "forces_cached_true": False}

    def assert_selection(self, name, inputs, effective, argv):
        row = self.groups["selection_cases"][name]
        self.assert_json_equal(row["input"], inputs, f"{name}: independent scenario required")
        self.assert_json_equal(row["expected"], self.declaration(effective, argv),
                               f"{name}: required declaration differs")

    def test_closed_corpus_and_required_case_inventory(self):
        # Pins finite coverage/closed metadata; not a schema for any runtime carrier.
        self.assertEqual(set(self.vector), {
            "capability", "capability_revision", "normative_section", "claim",
            "argument_matrix", "selection_cases", "identity_cases", "argument_cases", "fidelity_cases",
        })
        self.assert_json_equal([self.vector[k] for k in (
            "capability", "capability_revision", "normative_section", "claim")],
            ["agent-environments", 1, "protocol/environments.md §10.2",
             "specification-data-consistency-only"], "closed corpus identity")
        selection_names = {
            "default-interactive", "explicit-strict-interactive", "default-exec", "default-dry-run",
            "strict-absent-fact", "explicit-interactive-mixed",
            *(f"allowance-{form}" for form in ("exec", "serve", "dry-run", "hosted", "headless", "other-runtime")),
            *(f"allowance-fact-{shape}" for shape in ("absent", "null", "false", "empty", "string", "extra")),
            *(f"inherited-{source}-{form}" for source, form in itertools.product(
                ("environment", "configuration", "profile", "permission-yolo", "default"),
                ("interactive", "exec", "dry-run"))),
            *(f"invalid-choice-{shape}" for shape in (
                "upper-mixed", "lower-mixed", "title-allowance", "boolean-true", "empty-string",
                "unknown-token", "boolean-false", "number-zero", "number-one", "explicit-null")),
        }
        self.assertEqual(set(self.groups["selection_cases"]), selection_names)
        self.assertEqual(set(self.groups["identity_cases"]), {"strict-identity", "allowance-identity"})
        for group, keys in {
            "selection_cases": {"name", "input", "expected"},
            "identity_cases": {"name", "requested_choice", "retained_choice", "original", "retained"},
            "argument_cases": {"name", "metadata", "expected"},
            "fidelity_cases": {"name", "route", "failure", "expected"},
        }.items():
            for name, row in self.groups[group].items():
                self.assertEqual(set(row), keys, f"closed {group}/{name}")

    def test_strict_and_mixed_positive_declarations(self):
        # §10.2: default strict exact argv; only explicit interactive allowance declares MIXED.
        interactive = ["-c", "context.foreign_personal_skills=false"]
        for name, form, choice, present, effective, argv in (
            ("default-interactive", "interactive", None, True, "strict", interactive),
            ("explicit-strict-interactive", "interactive", "strict", True, "strict", interactive),
            ("default-exec", "exec", None, True, "strict", ["--no-foreign-personal-context"]),
            ("default-dry-run", "dry-run", None, True, "strict", ["--no-foreign-personal-context"]),
            ("strict-absent-fact", "interactive", None, False, "strict", []),
            ("explicit-interactive-mixed", "interactive", "allowance", True, "MIXED", []),
        ):
            with self.subTest(case=name):
                self.assert_selection(name, self.selection_input(choice, form, present), effective, argv)

    def test_selector_boundary_no_inheritance_aliases_or_coercion(self):
        # §10.2: non-invocation selectors never opt in; explicit aliases/coerced values refuse.
        # These closed declarations test neither native input parsing nor runtime policy selection.
        interactive = ["-c", "context.foreign_personal_skills=false"]
        self.assert_selection("explicit-strict-interactive", self.selection_input("strict"), "strict", interactive)
        self.assert_selection("explicit-interactive-mixed", self.selection_input("allowance"), "MIXED", [])
        for source, form in itertools.product(
            ("environment", "configuration", "profile", "permission-yolo", "default"),
            ("interactive", "exec", "dry-run"),
        ):
            with self.subTest(source=source, form=form):
                self.assert_selection(f"inherited-{source}-{form}",
                    self.selection_input(form=form, selector_source=source), "strict",
                    interactive if form == "interactive" else ["--no-foreign-personal-context"])
        # Boolean/number neighbours remain distinct; explicit null is not outer-option absence.
        for shape, choice in (
            ("upper-mixed", "MIXED"), ("lower-mixed", "mixed"), ("title-allowance", "Allowance"),
            ("boolean-true", True), ("empty-string", ""), ("unknown-token", "unknown-choice"),
            ("boolean-false", False), ("number-zero", 0), ("number-one", 1), ("explicit-null", None),
        ):
            with self.subTest(invalid_choice=shape):
                self.assert_selection(f"invalid-choice-{shape}",
                    self.selection_input(choice, selector_source="explicit"), None, [])

    def test_forbidden_form_allowances_must_refuse(self):
        # §10.2: these otherwise-valid allowances MUST NOT declare MIXED on any forbidden route.
        for form in ("exec", "serve", "dry-run"):
            with self.subTest(form=form):
                self.assert_selection(f"allowance-{form}", self.selection_input("allowance", form), None, [])
        for name, override in (
            ("hosted", {"execution_kind": "hosted"}), ("headless", {"headless": True}),
            ("other-runtime", {"runtime": "other"}),
        ):
            with self.subTest(route=name):
                self.assert_selection(f"allowance-{name}", self.selection_input("allowance", **override), None, [])

    def test_absent_invalid_fact_allowances_must_refuse(self):
        # §10.2 raw fact is exactly {exclusive:true}; even absent fact cannot authorize allowance.
        for shape, present, fact in (
            ("absent", False, None), ("null", True, None), ("false", True, {"exclusive": False}),
            ("empty", True, {}), ("string", True, {"exclusive": "true"}),
            ("extra", True, {"exclusive": True, "extra": True}),
        ):
            with self.subTest(shape=shape):
                self.assert_selection(f"allowance-fact-{shape}",
                    self.selection_input("allowance", present=present, raw_fact=fact), None, [])

    def test_complete_fragment_and_profile_identity_preserved(self):
        # §10.2: compare entire retained declaration, not only echoed digest or exclusive flag.
        fragment = {
            "fragment": "launch-env-fragment-v4", "environment": "muse",
            "profile": {"name": "example-profile", "lock_sha256": "1" * 64},
            "precedence": {"winner": "higher-weight", "placement": "winner-last"},
            "permissions": {"mode": "native", "locked": False, "source": "default"},
            "env": {"XDG_CONFIG_HOME": "/fixture/managed/config", "XDG_DATA_HOME": "/fixture/managed/data",
                    "XDG_STATE_HOME": "/fixture/managed/state", "XDG_CACHE_HOME": "/fixture/managed/cache",
                    "TBH_CREDENTIAL_BACKEND": "file"},
            "credential_store": {"selection": "file"}, "root_context": {"exclusive": True},
        }
        original = {"fragment": fragment, "whole_fragment_digest": "2" * 64,
                    "provenance": {"manager": "fixture-manager", "binding": "3" * 64},
                    "inherited_HOME": "/fixture/native"}
        for name, row in self.groups["identity_cases"].items():
            with self.subTest(case=name):
                self.assert_json_equal(row["original"], original, "independent original identity required")
                self.assert_json_equal(row["retained"], original, "complete retained identity must be unchanged")

    def test_typed_choice_must_not_be_dropped_or_replaced(self):
        # A changed choice cannot pass merely because the replacement strict launch could qualify.
        for choice in ("strict", "allowance"):
            row = self.groups["identity_cases"][f"{choice}-identity"]
            self.assertEqual(row["requested_choice"], choice, "original parsed choice must be retained")
            self.assertEqual(row["retained_choice"], choice, "typed choice must not be dropped or replaced")

    def test_both_dimensions_combined_equivalent_options_and_opaque_data(self):
        # §10.2 protects both choices/modes. Metadata positions/spellings are NOT native parsing.
        self.assert_json_equal(self.vector["argument_matrix"], {
            "choices": ["strict", "allowance"], "permissions": ["native", "yolo"],
        }, "neither permission mode nor strict/MIXED can bypass conflict declarations")
        expected = {}
        for dimension, value, spelling, position in itertools.product(
            ("rules", "skills"), (False, True), ("config-separated", "config-joined"),
            ("option-before", "option-after"),
        ):
            name = f"{dimension}-{str(value).lower()}-{spelling}-{position}"
            expected[name] = ({"dimension": dimension, "value": value, "spelling": spelling,
                               "position": position}, "refuse")
        for value, position in itertools.product(("exclude", "enable"), ("option-before", "option-after")):
            expected[f"combined-{value}-{position}"] = ({"dimension": "combined", "value": value,
                "spelling": "combined-switch", "position": position}, "refuse")
        for form in ("exec", "serve"):
            expected[f"command-{form}"] = ({"dimension": "form", "value": form,
                "spelling": "command-word", "position": "command"}, "refuse")
        for name, text in (
            ("rules", "context.foreign_personal_rules=true"),
            ("skills", "context.foreign_personal_skills=false"),
            ("combined", "--no-foreign-personal-context"), ("exec", "exec"), ("serve", "serve"),
        ):
            expected[f"opaque-{name}"] = ({"dimension": "opaque", "value": text,
                "spelling": "literal-data", "position": "after-provider-separator"}, "preserve-data")
        for semantic in ("unknown", "unparseable"):
            expected[f"{semantic}-policy"] = ({"dimension": "unknown", "value": semantic,
                "spelling": "unqualified-policy-syntax", "position": "option-before"}, "refuse")
        self.assertEqual(set(self.groups["argument_cases"]), set(expected), "both dimensions/positions required")
        for name, (metadata, disposition) in expected.items():
            row = self.groups["argument_cases"][name]
            with self.subTest(case=name):
                self.assert_json_equal(row["metadata"], metadata, "native options and opaque data stay distinct")
                self.assertEqual(row["expected"], disposition, "policy conflicts refuse; opaque data is preserved")

    def test_vendor_and_system_only_capability_and_fidelity_declarations(self):
        # §10.2: both routes require one decision; no legacy/strict success for a dropped request.
        failures = ("none", "dropped-choice", "replaced-choice", "unsupported-capability",
                    "unsupported-fidelity", "missing-seal", "unsupported-version")
        expected = {f"{route}-{failure}": (route, failure)
                    for route, failure in itertools.product(("vendor", "system-only"), failures)}
        self.assertEqual(set(self.groups["fidelity_cases"]), set(expected))
        for name, (route, failure) in expected.items():
            row = self.groups["fidelity_cases"][name]
            with self.subTest(case=name):
                self.assertEqual((row["route"], row["failure"]), (route, failure))
                self.assertEqual(row["expected"], "preserve-bound-decision" if failure == "none" else "refuse",
                                 "unsupported/dropped/replaced policy must refuse on each route")

    def test_duplicate_json_members_are_rejected(self):
        # The corpus decoder refuses duplicate declarations; this does not qualify a runtime decoder.
        self.assertEqual(load_document('{"choice":"strict"}'), {"choice": "strict"})
        with self.assertRaisesRegex(ValueError, "^duplicate member: choice$"):
            load_document('{"choice":"strict","choice":"allowance"}')


if __name__ == "__main__":
    unittest.main()
