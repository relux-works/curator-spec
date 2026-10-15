"""CIP-0016 semantic corpus checks; no launcher or provider qualification."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


CORPUS = Path(__file__).resolve().parents[1] / "conformance/local-hosted-launches/cases.json"


class LocalHostedSelectionTests(unittest.TestCase):
    def setUp(self):
        self.vector = json.loads(CORPUS.read_text(encoding="utf-8"))
        self.cases = {case["name"]: case for case in self.vector["cases"]}

    def expect(self, name, route, lookup, diagnostic=None, exit_code=None):
        self.assertEqual(self.cases[name]["expected"], {
            "route": route, "receiver_lookup": lookup,
            "diagnostic": diagnostic, "exit": exit_code,
        })

    # Pins all 18 scenarios and three required runtimes, not runtime behavior.
    def test_closed_case_and_runtime_matrix(self):
        self.assertEqual(self.vector["kind"], "semantic-selection-cases-not-wire-payloads")
        self.assertEqual(self.vector["normative"], "protocol/local-hosted-launches.md §§1–2, 7–8")
        self.assertEqual(self.vector["runtimes"], ["claude_code", "codex_cli", "muse"])
        self.assertEqual(len(self.vector["cases"]), len(self.cases))
        self.assertEqual(set(self.cases), {
            "native-no-selection", "explicit-native", "backend-does-not-enable-hosting",
            "native-legacy-ax", "explicit-hosted-absent-backend", "explicit-hosted-local-backend",
            "migrated-operator-default", "unmigrated-operator-default", "machine-default-gated",
            "ax-conflict-before-default-gate", "ax-conflict-explicit-hosted", "dispatcher-unimplemented",
            "receiver-missing", "receiver-unreachable", "hosted-network-before-contact",
            "hosted-terminal-before-contact", "hosted-piped-stdin-before-contact",
            "hosted-attached-stdin-before-handoff",
        })
        self.assertEqual(len(self.cases) * len(self.vector["runtimes"]), 54)

    # Cases isolate the named condition against a common valid selection context.
    def test_inputs_bind_each_scenario_without_hidden_failure(self):
        base = dict(host="native", backend="absent", ax=False, receiver="ready",
                    operator_migrated=False, network=False, terminal=True, stdin="terminal")
        changes = {
            "native-no-selection": {},
            "explicit-native": {"host": "explicit-native"},
            "backend-does-not-enable-hosting": {"backend": "local-task-board"},
            "native-legacy-ax": {"ax": True},
            "explicit-hosted-absent-backend": {"host": "explicit-hosted"},
            "explicit-hosted-local-backend": {"host": "explicit-hosted", "backend": "local-task-board"},
            "migrated-operator-default": {"host": "operator-hosted", "operator_migrated": True,
                                           "backend": "local-task-board"},
            "unmigrated-operator-default": {"host": "operator-hosted"},
            "machine-default-gated": {"host": "machine-hosted", "backend": "local-task-board"},
            "ax-conflict-before-default-gate": {"host": "machine-hosted", "ax": True},
            "ax-conflict-explicit-hosted": {"host": "explicit-hosted", "ax": True},
            "dispatcher-unimplemented": {"host": "explicit-hosted", "backend": "dispatcher"},
            "receiver-missing": {"host": "explicit-hosted", "receiver": "missing"},
            "receiver-unreachable": {"host": "explicit-hosted", "receiver": "unreachable"},
            "hosted-network-before-contact": {"host": "explicit-hosted", "network": True},
            "hosted-terminal-before-contact": {"host": "explicit-hosted", "terminal": False},
            "hosted-piped-stdin-before-contact": {"host": "explicit-hosted", "stdin": "piped"},
            "hosted-attached-stdin-before-handoff": {"host": "explicit-hosted", "stdin": "attached"},
        }
        for name, delta in changes.items():
            with self.subTest(case=name):
                self.assertEqual(self.cases[name]["input"], base | delta)

    # Native and legacy ax rows forbid receiver contact, even with backend config.
    def test_native_and_ax_never_probe_receiver(self):
        for name in ("native-no-selection", "explicit-native", "backend-does-not-enable-hosting"):
            with self.subTest(case=name):
                self.expect(name, "native", False)
        self.expect("native-legacy-ax", "ax", False)
        self.assertEqual(self.cases["backend-does-not-enable-hosting"]["input"]["backend"], "local-task-board")
        self.assertTrue(self.cases["native-legacy-ax"]["input"]["ax"])

    # Explicit hosted absence selects local; explicit local is the positive control.
    def test_explicit_hosted_absence_is_stably_local(self):
        for name, backend in (("explicit-hosted-absent-backend", "absent"),
                              ("explicit-hosted-local-backend", "local-task-board")):
            with self.subTest(case=name):
                self.assertEqual(self.cases[name]["input"]["host"], "explicit-hosted")
                self.assertEqual(self.cases[name]["input"]["backend"], backend)
                self.expect(name, "local-task-board", True)

    # Receiver absence and unreachability remain separate refusals without fallback.
    def test_missing_and_unreachable_refuse_without_native_fallback(self):
        for state, diagnostic in (("missing", "session_host_missing"),
                                  ("unreachable", "session_host_unavailable")):
            name = f"receiver-{state}"
            with self.subTest(state=state):
                self.assertEqual(self.cases[name]["input"]["receiver"], state)
                self.expect(name, "refuse", True, diagnostic, 1)
        self.expect("explicit-hosted-local-backend", "local-task-board", True)

    # Migration admits the operator row, never the still-gated machine default.
    def test_defaults_require_migration_and_machine_gate(self):
        self.assertTrue(self.cases["migrated-operator-default"]["input"]["operator_migrated"])
        self.assertFalse(self.cases["unmigrated-operator-default"]["input"]["operator_migrated"])
        self.expect("migrated-operator-default", "local-task-board", True)
        self.expect("unmigrated-operator-default", "refuse", False)
        self.expect("machine-default-gated", "refuse", False, "session_host_default_not_ready", 16)

    # ax conflict takes priority over machine-default refusal; native ax still routes.
    def test_ax_conflict_precedes_default_gate(self):
        for name in ("ax-conflict-before-default-gate", "ax-conflict-explicit-hosted"):
            with self.subTest(case=name):
                self.assertTrue(self.cases[name]["input"]["ax"])
                self.expect(name, "refuse", False, "host_configuration_conflict", 2)
        self.assertEqual(self.cases["ax-conflict-before-default-gate"]["input"]["host"], "machine-hosted")
        self.expect("native-legacy-ax", "ax", False)

    # Unimplemented dispatcher refuses; no diagnostic is invented before publication.
    def test_dispatcher_selection_never_becomes_local(self):
        self.assertEqual(self.cases["dispatcher-unimplemented"]["input"]["backend"], "dispatcher")
        self.expect("dispatcher-unimplemented", "refuse", False)
        self.expect("explicit-hosted-local-backend", "local-task-board", True)

    # Invalid ingress refuses; attached-plan stdin has no preparation-contact count claim.
    def test_ingress_gates_refuse_before_contact(self):
        for name, key, value, diagnostic, exit_code in (
            ("hosted-network-before-contact", "network", True, "network_scope_unsupported", 16),
            ("hosted-terminal-before-contact", "terminal", False, "session_host_terminal_required", 6),
            ("hosted-piped-stdin-before-contact", "stdin", "piped", "session_host_stdin_unsupported", 6),
            ("hosted-attached-stdin-before-handoff", "stdin", "attached", "session_host_stdin_unsupported", 6),
        ):
            with self.subTest(case=name):
                self.assertEqual(self.cases[name]["input"][key], value)
                self.expect(name, "refuse", None if key == "stdin" and value == "attached" else False, diagnostic, exit_code)
        self.expect("explicit-hosted-local-backend", "local-task-board", True)

    # Every negative observation contradicts exactly one independently pinned outcome.
    def test_forbidden_observations_narrow_one_outcome(self):
        for name, case in self.cases.items():
            with self.subTest(case=name):
                positive, negative = case["expected"], case["forbidden_observation"]
                self.assertEqual(set(positive), set(negative))
                changed = [key for key in positive if positive[key] != negative[key]]
                if positive["route"] in ("native", "ax"):
                    self.assertEqual(changed, ["receiver_lookup"])
                    self.assertTrue(negative["receiver_lookup"])
                else:
                    self.assertEqual(changed, ["route"])
                    self.assertEqual(negative["route"], "native" if positive["route"] == "refuse" else "dispatcher")


if __name__ == "__main__":
    unittest.main()
