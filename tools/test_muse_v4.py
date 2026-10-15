"""CIP-0017 schema/data checks; these do not qualify a Muse runtime."""
from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_validate import validate


SCHEMA = "launch-env-fragment-v4.schema.json"
CASES = validate.ROOT / "conformance/environments-muse-v4/schema-cases"


class MuseV4Tests(unittest.TestCase):
    def candidate(self):
        return validate.load_json(CASES / "valid-muse-root.json")

    def valid(self, instance, schema=None):
        registry, paths = validate.schema_registry()
        document = schema or validate.load_json(paths[SCHEMA])
        return (not list(validate.Draft202012Validator(document, registry=registry).iter_errors(instance))
                and validate.validate_wire_semantics(SCHEMA, instance) is None)

    # All published v4 structural and cross-field cases agree with their independent verdicts.
    def test_published_cases(self):
        registry, paths = validate.schema_registry()
        for case in validate.load_json(CASES / "index.json"):
            with self.subTest(case=case["instance"]):
                instance = validate.load_json(CASES / case["instance"])
                errors = list(validate.Draft202012Validator(
                    validate.load_json(paths[case["schema"]]), registry=registry).iter_errors(instance))
                actual = not errors and validate.validate_wire_semantics(case["schema"], instance) is None
                self.assertEqual(actual, case["valid"])

    # Required-root true is accepted; false cannot weaken the declared exclusion.
    def test_root_false_rejected(self):
        self.assertTrue(self.valid(self.candidate()))
        instance = self.candidate()
        instance["root_context"]["exclusive"] = False
        self.assertFalse(self.valid(instance))

    # Backend agreement rejects shared-looking metadata paired with the native Keychain backend.
    def test_backend_keychain_rejected(self):
        self.assertTrue(self.valid(self.candidate()))
        instance = self.candidate()
        instance["env"]["TBH_CREDENTIAL_BACKEND"] = "keychain"
        self.assertFalse(self.valid(instance))

    # One foreign parent fails even though all five values have structurally valid types.
    def test_foreign_data_parent_rejected(self):
        self.assertTrue(self.valid(self.candidate()))
        instance = self.candidate()
        instance["env"]["XDG_DATA_HOME"] = "/other/data"
        self.assertFalse(self.valid(instance))

    # A Codex file policy requires the matching typed override, not merely a supported value.
    def test_codex_store_disagreement_rejected(self):
        instance = validate.load_json(CASES / "valid-codex-file.json")
        self.assertTrue(self.valid(instance))
        instance["credential_store"]["config_overrides"]["cli_auth_credentials_store"] = "keyring"
        self.assertFalse(self.valid(instance))

    # Strict JSON loading rejects duplicate root facts before schema validation.
    def test_duplicate_root_key_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"root_context":{"exclusive":true},"root_context":{"exclusive":false}}')
            with self.assertRaises(validate.ValidationFailure):
                validate.load_json(path)

    # The actual repository schema gate must consume this later corpus, not just unit-test its schema.
    def test_schema_gate_consumes_v4_cases(self):
        real_load = validate.load_json

        def altered_load(path):
            value = real_load(path)
            if path == CASES / "valid-muse-root.json":
                value = copy.deepcopy(value)
                value["root_context"]["exclusive"] = False
            return value

        with patch.object(validate, "load_json", side_effect=altered_load):
            with self.assertRaisesRegex(validate.ValidationFailure, "valid-muse-root"):
                validate.validate_schemas()


if __name__ == "__main__":
    unittest.main()
