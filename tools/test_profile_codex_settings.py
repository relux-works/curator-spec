"""Check specification schemas/data; no manager or Codex runtime is exercised."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = ROOT / "schemas/profile-codex-settings-v1"
CORPUS = ROOT / "conformance/profile-codex-settings-v1"
KEY = "cli_auth_credentials_store"


class ProfileCodexSettingsTests(unittest.TestCase):
    def setUp(self):
        self.schemas = {p.name: json.loads(p.read_text()) for p in SCHEMA_ROOT.glob("*.schema.json")}
        resources = []
        for document in list(self.schemas.values()) + [
            json.loads(p.read_text()) for p in (ROOT / "schemas/v1").glob("*.schema.json")
        ]:
            Draft202012Validator.check_schema(document)
            resources.append((document["$id"], Resource.from_contents(document)))
        self.registry = Registry().with_resources(resources)

    def validator(self, name):
        return Draft202012Validator(self.schemas[name + ".schema.json"], registry=self.registry)

    # All published structural cases have the stated result; each module has
    # valid and invalid controls. This does not validate any full wire envelope.
    def test_published_schema_cases(self):
        cases = json.loads((CORPUS / "schema-cases.json").read_text())
        self.assertEqual(len({c["name"] for c in cases}), len(cases))
        coverage = {}
        for case in cases:
            with self.subTest(case=case["name"]):
                validator = self.validator(case["schema"].removesuffix(".schema.json"))
                self.assertEqual(validator.is_valid(case["instance"]), case["valid"])
                coverage.setdefault(case["schema"], set()).add(case["valid"])
        self.assertEqual(set(coverage), set(self.schemas))
        self.assertTrue(all(values == {True, False} for values in coverage.values()))

    # D14 admits only the empty package object; both former selectors and the
    # sampled unknown/credential keys are rejected. This is structural evidence.
    def test_closed_allowlist_and_enum(self):
        validator = self.validator("codex-settings-v1")
        self.assertTrue(validator.is_valid({}))
        for value in ("file", "keyring", "auto", None, True, 0, [], {}, '"file"', "FILE", "file\n"):
            with self.subTest(value=value):
                self.assertFalse(validator.is_valid({KEY: value}))
        for key in ("sandbox_mode", "approval_policy", "mcp_servers", "model_provider",
                    "service_tier", "credential_store", "credential_source", "account",
                    KEY + ".alias", '"' + KEY + '"', KEY + "\n"):
            with self.subTest(key=key):
                self.assertFalse(validator.is_valid({key: "file"}))

    # D14 rejection holds at every package-derived carrier, paired with an empty
    # positive control; it cannot attest machine provenance of launch data.
    def test_d14_package_store_rejected_before_resolution(self):
        for store in ("file", "keyring"):
            for name in ("manifest-members-v1", "marker-members-v1", "lock-members-v1"):
                with self.subTest(store=store, carrier=name):
                    valid = {"codex_settings": {}}
                    if name == "lock-members-v1":
                        valid.update(codex_settings_contributions=[], precedence={
                            "winner": "higher-weight", "placement": "winner-last"})
                    self.assertTrue(self.validator(name).is_valid(valid))
                    invalid = copy.deepcopy(valid)
                    invalid["codex_settings"] = {KEY: store}
                    self.assertFalse(self.validator(name).is_valid(invalid))
        self.assertTrue(self.validator("manifest-members-v1").is_valid({}))

    # The fragment projection permits nonempty Codex settings only; omission is
    # valid on every adapter. It still is not a complete fragment validator.
    def test_fragment_adapter_and_empty_boundaries(self):
        validator = self.validator("fragment-members-v1")
        for env in ("codex_cli", "claude_code", "opencode", "pi", "muse"):
            with self.subTest(environment=env):
                self.assertTrue(validator.is_valid({"environment": env}))
                self.assertEqual(validator.is_valid({"environment": env, "codex_settings": {KEY: "file"}}), env == "codex_cli")
        self.assertTrue(validator.is_valid({"environment": "codex_cli", "codex_settings": {KEY: "keyring"}}))
        for value in ("auto", None, True, 0, [], {}, "file\n"):
            self.assertFalse(validator.is_valid({"environment": "codex_cli", "codex_settings": {KEY: value}}))
        self.assertFalse(validator.is_valid({"environment": "codex_cli", "codex_settings": {"account": "file"}}))
        self.assertFalse(validator.is_valid({"environment": "codex_cli", "codex_settings": {}}))
        self.assertFalse(validator.is_valid({"codex_settings": {KEY: "file"}}))
        self.assertFalse(validator.is_valid({"environment": "codex_cli", "argv": []}))

    # Empty package settings retain lock metadata; a forbidden losing
    # contribution cannot hide behind an empty effective result.
    def test_lock_rejects_invalid_contribution(self):
        validator = self.validator("lock-members-v1")
        valid = {"codex_settings": {}, "codex_settings_contributions": [],
                 "precedence": {"winner": "higher-weight", "placement": "winner-last"}}
        self.assertTrue(validator.is_valid(valid))
        for value in ("file", "keyring", "auto"):
            invalid = copy.deepcopy(valid)
            invalid["codex_settings_contributions"] = [
                {"package": "dependency", "settings": {KEY: value}}]
            self.assertFalse(validator.is_valid(invalid))
        for member in valid:
            missing = {k: v for k, v in valid.items() if k != member}
            self.assertFalse(validator.is_valid(missing), member)

    # Frozen manifest/lock/marker/fragment schemas still reject the new member
    # when injected into a previously valid published example.
    def test_frozen_envelopes_still_reject_settings(self):
        for name in ("agent-context-v1", "context-lock-v2", "agent-environment-marker-v3", "launch-env-fragment-v3"):
            schema = json.loads((ROOT / "schemas/v1" / (name + ".schema.json")).read_text())
            directory = ROOT / "conformance/v1/schema-cases" / name
            candidates = list(directory.glob("valid*.json"))
            self.assertTrue(candidates, name)
            validator = Draft202012Validator(schema, registry=self.registry)
            instance = json.loads(candidates[0].read_text())
            self.assertTrue(validator.is_valid(instance), name)
            instance["codex_settings"] = {KEY: "file"}
            self.assertFalse(validator.is_valid(instance), name)

    # The semantic corpus retains both winner directions as package refusals,
    # all six delivery forms and 16 machine storage pairings. These are inventory
    # assertions, not measured runtime behavior or correctness of a resolver.
    def test_semantic_vector_inventory_and_unknown_qualification(self):
        vector = json.loads((CORPUS / "vectors.json").read_text())
        self.assertEqual(vector["runtime_qualification"], "unverified")
        cases = {c["name"]: c for c in vector["cases"]}
        self.assertEqual(len(cases), len(vector["cases"]))
        for winner in ("higher-weight", "lower-weight"):
            for placement in ("winner-first", "winner-last"):
                self.assertIn("closure-" + winner + "-" + placement, cases)
        for form in ("interactive", "exec", "hosted-app-server", "login", "resume", "tracked-dispatch"):
            self.assertEqual(cases["delivery-" + form]["expected"]["settings_argv"], ["-c", KEY + '="file"'])
        for mode in ("shared", "isolated"):
            for native in ("absent", "file", "keyring", "auto"):
                for setting in ("file", "keyring"):
                    self.assertIn(f"storage-{mode}-{native}-{setting}", cases)
        for path in ("login", "app-server", "token-refresh", "conflicting-seed"):
            self.assertEqual(cases["qualification-" + path]["expected"], {
                "outcome": "codex_settings_unsupported", "invocation": False,
            })
        for case in cases.values():
            self.assertTrue(case["entry"])
            self.assertTrue(case["expected"])
            self.assertTrue(case["forbidden_observations"])

    # Former package-store vectors now refuse before selection with no launch
    # data. Machine selectors and absent/empty packages have positive controls;
    # vector labels remain requirements, not runtime qualification.
    def test_d14_vectors_keep_machine_and_package_sources_separate(self):
        cases = json.loads((CORPUS / "vectors.json").read_text())["cases"]
        by_name = {case["name"]: case for case in cases}
        refusals = 0
        for case in cases:
            inputs = case["input"]
            if any(c.get("settings") for c in inputs.get("contributions", [])):
                refusals += 1
                with self.subTest(case=case["name"]):
                    self.assertEqual(case["expected"], {
                        "diagnostic": "context_manifest_invalid", "fragment": False,
                        "replacement_lock": False, "launch_data": False})
            if "setting" in inputs:
                self.fail("legacy profile store selector: " + case["name"])
        self.assertGreaterEqual(refusals, 15)
        for store, selector in (("file", "file"), ("keyring", "keychain")):
            case = by_name["machine-selected-" + store]
            self.assertEqual(case["input"]["credential_store"], selector)
            self.assertEqual(case["expected"]["settings_argv"], ["-c", KEY + '="' + store + '"'])
        for name in ("package-without-settings", "package-empty-settings"):
            self.assertEqual(by_name[name]["expected"], {"settings": {}, "diagnostics": []})


if __name__ == "__main__":
    unittest.main()
