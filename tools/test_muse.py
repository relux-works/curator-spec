from __future__ import annotations

import contextlib
import copy
import io
import unittest
from unittest.mock import patch

from test_validate import validate


class MuseVectorTests(unittest.TestCase):
    def vector(self):
        return validate.load_json(validate.SUITE / "vectors" / "environments-muse.json")

    def test_generated_family_is_valid(self):
        validate.validate_environments_muse_vectors()

    def test_every_declared_link_state_is_checked(self):
        vector = self.vector()
        self.assertEqual(len(vector["cases"]), 16)
        for index, case in enumerate(vector["cases"]):
            with self.subTest(case=case["name"]):
                mutated = copy.deepcopy(vector)
                expected = mutated["cases"][index]["expected"]
                expected["emit_fragment"] = not expected["emit_fragment"]
                with self.assertRaises(validate.ValidationFailure):
                    validate.validate_environments_muse_vectors(mutated)

    def test_narrowed_fork_detection_cannot_admit_other_detached_states(self):
        for state in ("retargeted-link", "dangling-target", "metadata-unreadable", "target-unreadable"):
            vector = self.vector()
            for case in vector["cases"]:
                if case["state"] == state:
                    case["expected"] = {"status": "current", "diagnostic": "", "action": "none",
                                        "emit_fragment": True, "credential_bytes_changed": False}
            with self.subTest(state=state), self.assertRaises(validate.ValidationFailure):
                validate.validate_environments_muse_vectors(vector)

    def test_registry_cannot_claim_unknown_probes_or_replace_HOME(self):
        mutations = {"replace_HOME": True, "root_context_target": "AGENTS.md", "root_context_verified": True,
                     "skills_discovery_verified": True, "refresh_semantics": "write-through",
                     "isolation_gap": None, "serve_session": {"approvalMode": "native"}}
        for key, value in mutations.items():
            vector = self.vector()
            vector["registry"][key] = value
            with self.subTest(key=key), self.assertRaises(validate.ValidationFailure):
                validate.validate_environments_muse_vectors(vector)

    def test_absent_cases_are_not_satisfied_evidence(self):
        for name in ("cases", "registry", "fixtures"):
            vector = self.vector()
            del vector[name]
            with self.subTest(name=name), self.assertRaises(validate.ValidationFailure):
                validate.validate_environments_muse_vectors(vector)
        vector = self.vector()
        vector["cases"].pop()
        with self.assertRaises(validate.ValidationFailure):
            validate.validate_environments_muse_vectors(vector)

    def test_each_fixture_gate_rejects_changed_protected_fields(self):
        real_load = validate.load_json
        mutations = {
            "muse-home-layout.json": lambda value: value["env"].update(HOME="/manager/home"),
            "muse-fragment.json": lambda value: value["env"].update(XDG_DATA_HOME="/foreign/data"),
            "muse-marker.json": lambda value: value["passthrough"][0].update(path="auth.json"),
        }
        for filename, mutate in mutations.items():
            def altered_load(path):
                value = real_load(path)
                if path.name == filename:
                    mutate(value)
                return value
            with self.subTest(fixture=filename), patch.object(validate, "load_json", side_effect=altered_load):
                with self.assertRaises(validate.ValidationFailure):
                    validate.validate_environments_muse_vectors()

    def test_main_calls_muse_gate(self):
        vector = self.vector()
        vector["cases"][0]["expected"]["emit_fragment"] = False
        gate = validate.validate_environments_muse_vectors
        # Exercise tools/validate.py's production dispatch, isolating the
        # unrelated gates. A missing Muse call makes main return 0 and fails.
        with contextlib.ExitStack() as stack:
            for name in vars(validate):
                if name.startswith("validate_") and name not in {
                    "validate_environments_muse_vectors", "validate_wire_semantics"
                }:
                    stack.enter_context(patch.object(validate, name, return_value=None))
            stack.enter_context(patch.object(validate, "validate_environments_muse_vectors",
                                            side_effect=lambda: gate(vector)))
            stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            self.assertEqual(validate.main(), 1)


class MuseFragmentTests(unittest.TestCase):
    def setUp(self):
        self.fragment = validate.load_json(validate.SUITE / "expected" / "environments-muse" / "muse-fragment.json")
        registry, _ = validate.schema_registry()
        self.validator = validate.Draft202012Validator(
            validate.load_json(validate.SCHEMAS / "launch-env-fragment-v3.schema.json"), registry=registry)

    def valid(self, fragment):
        return not list(self.validator.iter_errors(fragment)) and not validate.validate_wire_semantics(
            "launch-env-fragment-v3.schema.json", fragment)

    def test_four_parents_at_the_admitted_boundary(self):
        self.assertTrue(self.valid(self.fragment))
        for name in self.fragment["env"]:
            with self.subTest(parent=name):
                missing = copy.deepcopy(self.fragment)
                del missing["env"][name]
                self.assertFalse(self.valid(missing))
                foreign = copy.deepcopy(self.fragment)
                foreign["env"][name] = "/foreign/" + name
                self.assertFalse(self.valid(foreign))

    def test_HOME_and_unverified_channels_are_rejected(self):
        extra = copy.deepcopy(self.fragment)
        extra["env"]["HOME"] = "/manager/home"
        self.assertFalse(self.valid(extra))
        substitution = copy.deepcopy(self.fragment)
        substitution["env"] = {"HOME": "/manager/home"}
        self.assertFalse(self.valid(substitution))
        for channel in ("mcp", "system_prompt"):
            fragment = copy.deepcopy(self.fragment)
            fragment[channel] = {"path": "/manager/file", "channels": []}
            self.assertFalse(self.valid(fragment))

    def test_permissions_remain_required_and_locked_native(self):
        fragment = copy.deepcopy(self.fragment)
        del fragment["permissions"]
        self.assertFalse(self.valid(fragment))
        fragment["permissions"] = {"mode": "yolo", "locked": True, "source": "global"}
        self.assertFalse(self.valid(fragment))

    def test_legacy_schemas_reject_muse_without_modification(self):
        registry, _ = validate.schema_registry()
        for version in (1, 2):
            fragment = copy.deepcopy(self.fragment)
            fragment["fragment"] = f"launch-env-fragment-v{version}"
            if version == 1:
                del fragment["permissions"]
            schema = validate.load_json(validate.SCHEMAS / f"launch-env-fragment-v{version}.schema.json")
            self.assertTrue(list(validate.Draft202012Validator(schema, registry=registry).iter_errors(fragment)))
