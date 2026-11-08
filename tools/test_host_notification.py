"""Bounded instrument plants against the draft carrier checker and schemas."""
import copy
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import host_notification as notification


class NotificationTests(unittest.TestCase):
    # The actual publication corpus passes; this is not native qualification.
    def test_corpus(self):
        output = io.StringIO()
        self.assertEqual(notification.run(output=output), 0, output.getvalue())

    # Each plant weakens precisely one published rule; its named independent
    # vector must change from the intended refusal to admission (or vice versa
    # for the /2 identity plant). Compilation/setup failure never counts.
    def test_five_intended_reason_plants(self):
        plants = [
            ('schema7-admit', 'extensions-v7.schema.json', 'schema7'),
            ('host-extra', 'extensions.schema.json', 'host'),
            ('off-extra', 'extensions.schema.json', 'off'),
            ('uppercase-digest', 'extensions.schema.json', 'digest'),
            ('projection-8', 'launcher-config-v2.schema.json', 'projection'),
        ]
        original_cases = notification.load_cases(notification.ROOT)
        for witness, filename, kind in plants:
            with self.subTest(plant=kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                shutil.copytree(notification.ROOT / 'schemas', root / 'schemas')
                path = root / 'schemas' / notification.NAMESPACE / filename
                schema = json.loads(path.read_text())
                if kind == 'schema7':
                    source = json.loads((root / 'schemas' / notification.NAMESPACE / 'extensions.schema.json').read_text())
                    schema['properties']['notification'] = source['properties']['notification']
                elif kind in ('host', 'off'):
                    schema['properties']['notification']['oneOf'][1 if kind == 'host' else 0]['additionalProperties'] = True
                elif kind == 'digest':
                    schema['properties']['notification']['oneOf'][1]['properties']['workflow_sha256']['pattern'] = '^[0-9A-Fa-f]{64}$'
                else:
                    schema['properties']['schema']['const'] = 'curator.launcher-config/1'
                path.write_text(json.dumps(schema))
                compiled = notification.validators(root)
                case = next(c for c in original_cases if c['id'] == witness)
                actual = notification.verdict(case, compiled)
                expected_plant = ('launcher_projection_invalid', 'schema') if kind == 'projection' else notification.VALID
                self.assertEqual(actual, expected_plant)
                output = io.StringIO()
                self.assertGreater(notification.check_cases(original_cases, compiled, output), 0)
                self.assertIn('FAIL ' + witness + '\n', output.getvalue())
        self.assertEqual(notification.run(output=io.StringIO()), 0)

    # Wrong expected accept and reject each fail with exit 1, later cases still
    # run and raw input never appears. Strict malformed corpus is setup exit 2.
    def test_checker_controls(self):
        original = notification.load_cases(notification.ROOT)
        for verdict in ('ok', 'launcher_selection_invalid'):
            cases = copy.deepcopy(original)
            case = next(c for c in cases if c['expected'][0] == verdict)
            case['expected'] = ['wrong', '$']
            output = io.StringIO()
            with patch.object(notification, 'load_cases', return_value=cases):
                self.assertEqual(notification.run(output=output), 1)
            self.assertIn('FAIL ' + case['id'], output.getvalue())
            self.assertIn('PASS ' + cases[-1]['id'], output.getvalue())
            self.assertNotIn('HOSTILE', output.getvalue())
        with patch.object(notification, 'load_cases', side_effect=ValueError('HOSTILE')):
            output = io.StringIO()
            self.assertEqual(notification.run(output=output), 2)
            self.assertEqual(output.getvalue(), 'FAIL notification-corpus-setup\n')

    # Editor fixtures pin preservation and reject a downgrade carrying metadata;
    # no real plan/apply/restore or state mutation is performed by this check.
    def test_edit_contract_fixtures(self):
        compiled = notification.validators(notification.ROOT)
        path = notification.ROOT / 'conformance' / notification.NAMESPACE / 'edit-cases.json'
        for case in notification.strict(path.read_bytes()):
            self.assertEqual(case['before']['extensions'], case['after']['extensions'])
            self.assertEqual(case['after']['schema_version'], 8)
            valid = dict(entry='configuration', input_json=json.dumps(case['after']))
            self.assertEqual(notification.verdict(valid, compiled), notification.VALID)
            downgrade = copy.deepcopy(case['after'])
            downgrade['schema_version'] = 7
            valid['input_json'] = json.dumps(downgrade)
            self.assertEqual(notification.verdict(valid, compiled), ('launcher_selection_invalid', 'extensions'))

    # Strict decoder detects escaped duplicates and invalid UTF-8 independent
    # of a schema verdict; a nearby valid object still loads.
    def test_strict_decode(self):
        self.assertEqual(notification.strict(b'{"backend":"off"}'), {'backend': 'off'})
        for raw in (b'{"a":1,"a":2}', b'{"a":1,"\\u0061":2}', b'"\xff"', b'{"a":NaN}'):
            with self.assertRaises((ValueError, UnicodeError)):
                notification.strict(raw)
