"""Closed carrier, independent authority verdicts and publication controls."""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

import provisioning_origin as origin
from test_validate import validate


class ProvisioningOriginTests(unittest.TestCase):
    # The publication entry checks every declared positive and negative case;
    # this establishes specification consistency, never runtime atomicity.
    def test_publication_entry(self):
        self.assertEqual(origin.check_corpus(), (48, 10))
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


if __name__ == '__main__':
    unittest.main()
