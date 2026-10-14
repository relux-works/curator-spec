"""Specification-data checks, not a Muse or manager runtime harness."""

from __future__ import annotations

import itertools
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
VECTOR = ROOT / "conformance/environments-muse-launch-argv/vectors.json"


class MuseLaunchArgvTests(unittest.TestCase):
    def setUp(self):
        self.vector = json.loads(VECTOR.read_text(encoding="utf-8"))
        self.cases = {case["name"]: case for case in self.vector["cases"]}

    def test_closed_form_target_matrix(self):
        self.assertEqual(self.vector["capability"], "agent-environments")
        self.assertEqual(self.vector["capability_revision"], 1)
        self.assertEqual(self.vector["normative_section"], "protocol/environments.md §10.2")
        self.assertEqual(self.vector["preconditions"], {
            "environment": "muse", "managed_home": True, "root_context_form": "monolithic",
        })
        expected = {
            f"{form}-target-{state}": {
                "launch_form": form, "root_context_target_materialized": state == "materialized",
            }
            for form in ("exec", "interactive")
            for state in ("materialized", "not-materialized")
        }
        self.assertEqual(len(self.vector["cases"]), 4)
        self.assertEqual({name: case["input"] for name, case in self.cases.items()}, expected)

    def test_exclusion_independent_of_permissions_and_channel_opt_ins(self):
        self.assertEqual(self.vector["matrix"], {
            "permissions": ["native", "yolo"],
            "system_prompt_opt_in": [False, True],
            "mcp_opt_in": [False, True],
        })
        combinations = list(itertools.product(*self.vector["matrix"].values()))
        self.assertEqual(len(combinations) * len(self.cases), 32)
        for case in self.cases.values():
            # A case has one expected projection across the entire matrix;
            # per-mode or per-opt-in expectations would weaken the binding.
            self.assertEqual(set(case), {"name", "input", "expected", "forbidden_observations"})
            self.assertEqual(set(case["expected"]), {"exclusion_argv"})

    def test_exec_materialized_requires_exec_flag(self):
        self.assertEqual(self.cases["exec-target-materialized"]["expected"], {
            "exclusion_argv": ["--no-foreign-personal-context"],
        })

    def test_interactive_materialized_requires_json_boolean_override(self):
        self.assertEqual(self.cases["interactive-target-materialized"]["expected"], {
            "exclusion_argv": ["-c", "context.foreign_personal_skills=false"],
        })

    def test_absent_target_forbids_both_exclusions_on_both_forms(self):
        for form in ("exec", "interactive"):
            with self.subTest(form=form):
                case = self.cases[f"{form}-target-not-materialized"]
                self.assertEqual(case["expected"], {"exclusion_argv": []})
                self.assertEqual({item["mutation"] for item in case["forbidden_observations"]}, {
                    "emit-exec-exclusion-without-target",
                    "emit-interactive-exclusion-without-target",
                })
                self.assertEqual([item["exclusion_argv"] for item in case["forbidden_observations"]], [
                    ["--no-foreign-personal-context"],
                    ["-c", "context.foreign_personal_skills=false"],
                ])

    def test_forbidden_observations_narrow_each_form_binding(self):
        for case in self.cases.values():
            observations = case["forbidden_observations"]
            names = [item["mutation"] for item in observations]
            self.assertEqual(len(names), len(set(names)))
            for item in observations:
                with self.subTest(case=case["name"], mutation=item["mutation"]):
                    self.assertEqual(set(item), {"mutation", "exclusion_argv"})
                    self.assertNotEqual(item["exclusion_argv"], case["expected"]["exclusion_argv"])
            if case["input"]["root_context_target_materialized"]:
                self.assertIn("exclude-only-on-other-form", names)
                self.assertIn("reuse-other-form-exclusion", names)
                self.assertEqual(observations[0]["exclusion_argv"], [])
                other = (["-c", "context.foreign_personal_skills=false"]
                         if case["input"]["launch_form"] == "exec"
                         else ["--no-foreign-personal-context"])
                self.assertEqual(observations[1]["exclusion_argv"], other)
        invalid_values = {
            item["exclusion_argv"][1].split("=", 1)[1]
            for item in self.cases["interactive-target-materialized"]["forbidden_observations"][2:]
        }
        self.assertEqual(invalid_values, {"off", '"false"', '"off"', "disabled", "exclude", "never"})


if __name__ == "__main__":
    unittest.main()
