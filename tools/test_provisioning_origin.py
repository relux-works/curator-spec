"""Closed carrier, independent authority verdicts and publication controls."""
from __future__ import annotations

import copy
import json
import unittest
from unittest.mock import patch

import provisioning_origin as origin
from jsonschema import Draft202012Validator
from test_validate import validate


class ProvisioningOriginTests(unittest.TestCase):
    # The publication entry checks every declared positive and negative case;
    # this establishes specification consistency, never runtime atomicity.
    def test_publication_entry(self):
        self.assertEqual(origin.check_corpus(), (66, 16))
        validate.validate_provisioning_origin()

    # A deliberately wrong A/B authority verdict fails through the actual
    # publication entry, at the intended vector rather than an unrelated error.
    def test_publication_rejects_wrong_authority(self):
        original = origin.Path.read_text

        def planted(path, *args, **kwargs):
            text = original(path, *args, **kwargs)
            if path.name == 'authority-cases.json' and path.parent.name == origin.NAMESPACE:
                cases = json.loads(text)
                cases[0]['expected']['native_root'] = '/fixture/native-B'
                return json.dumps(cases)
            return text

        with patch.object(origin.Path, 'read_text', new=planted):
            with self.assertRaisesRegex(validate.ValidationFailure, 'unchanged-A-under-B'):
                validate.validate_provisioning_origin()

    # Removing closed-carrier checking must be detected by the missing-record
    # vector; passing positive controls in the unmodified entry are above.
    def test_schema_admission_control(self):
        with patch.object(origin, 'record_valid', return_value=True):
            with self.assertRaisesRegex(validate.ValidationFailure, 'missing-record'):
                validate.validate_provisioning_origin()

    # Schema admission independently rejects every control-character case;
    # the same complete valid record remains an admitted positive control.
    def test_schema_control_boundaries(self):
        schema = json.loads((origin.ROOT / 'schemas' / origin.NAMESPACE / 'provisioning-origin-v1.schema.json').read_text())
        cases = json.loads((origin.ROOT / 'conformance' / origin.NAMESPACE / 'schema-cases.json').read_text())
        validator = Draft202012Validator(schema)
        self.assertTrue(validator.is_valid(cases[0]['record']))
        controls = [case for case in cases if case['name'].startswith('control-')]
        self.assertEqual(len(controls), 18)
        for case in controls:
            with self.subTest(case=case['name']):
                self.assertFalse(validator.is_valid(case['record']))

    # With schema checking deliberately permissive, the semantic boundary
    # still rejects controls in all six fields, beside an unchanged valid record.
    # This checks the independent semantic barrier, not general schema coverage.
    def test_semantic_control_boundary(self):
        cases = json.loads((origin.ROOT / 'conformance' / origin.NAMESPACE / 'authority-cases.json').read_text())
        base = cases[0]['record']
        self.assertTrue(origin.record_valid(base, {}))
        for path in [('operator_home',), ('native_root',), ('binding', 'managed_target'),
                     ('binding', 'profile'), ('binding', 'lock_sha256'), ('selector', 'value')]:
            for suffix in ['\n', '\r', '\n/trailing']:
                with self.subTest(path=path, suffix=repr(suffix)):
                    record = copy.deepcopy(base)
                    container = record
                    for key in path[:-1]:
                        container = container[key]
                    container[path[-1]] += suffix
                    self.assertFalse(origin.record_valid(record, {}))


if __name__ == '__main__':
    unittest.main()
