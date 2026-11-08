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
    def test_schema_intended_reason_plants(self):
        plants = [
            ('schema7-admit', 'extensions-v7.schema.json', 'schema7'),
            ('host-extra', 'extensions.schema.json', 'host'),
            ('off-extra', 'extensions.schema.json', 'off'),
            ('uppercase-digest', 'extensions.schema.json', 'digest'),
            ('reference-newline', 'extensions.schema.json', 'newline'),
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
                elif kind == 'newline':
                    del schema['properties']['notification']['oneOf'][1]['properties']['workflow_reference']['not']
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
            before, after = case['before'], case['after']
            old, new = before.get('extensions', {}), after.get('extensions', {})
            self.assertEqual(old.get('notification'), new.get('notification'))
            self.assertEqual(old.get('proxy'), new.get('proxy'))
            self.assertEqual(after['schema_version'], 7 if before['schema_version'] == 2 else before['schema_version'])
            if case['expected'] == 'stale-plan':
                self.assertNotEqual(case['planned_before']['extensions']['notification'], old['notification'])
                self.assertEqual(before, after)
            elif case['operation'] == 'claude-auth-plan':
                self.assertEqual(before, after)
                planned = case['planned_after']['extensions']
                self.assertNotEqual(old['claude_auth'], planned['claude_auth'])
                for member in ('proxy', 'notification'):
                    self.assertEqual(old[member], planned[member])
            elif case['operation'].startswith('claude-auth-'):
                self.assertNotEqual(old.get('claude_auth'), new.get('claude_auth'))
                for member in before.keys() | after.keys():
                    if member not in ('schema_version', 'extensions'):
                        self.assertEqual(before.get(member), after.get(member))
            else:
                self.assertEqual(old, new)
                self.assertNotEqual(before, after)
            valid = dict(entry='configuration', input_json=json.dumps(case['after']))
            self.assertEqual(notification.verdict(valid, compiled), notification.VALID)
            if 'notification' in new:
                downgrade = copy.deepcopy(after)
                downgrade['schema_version'] = 7
                valid['input_json'] = json.dumps(downgrade)
                self.assertEqual(notification.verdict(valid, compiled), ('launcher_selection_invalid', 'extensions'))
            else:
                self.assertEqual(after['schema_version'], 7)
                self.assertNotIn('notification', new)

    # The revised corpus distinguishes Core's name-first order from the former
    # version/extension-first model. Replaying reviewer E now is a valid control;
    # reverting that order fails all three original mixed-defect witnesses.
    def test_precedence_regression_plant(self):
        compiled = notification.validators(notification.ROOT)
        cases = notification.load_cases(notification.ROOT)
        real_verdict = notification.verdict
        def wrong_order(case, compiled):
            if case['id'].startswith('precedence-unknown-'):
                value = notification.strict(case['input_json'])
                value.pop('unknown')
                case = dict(case, input_json=json.dumps(value))
            return real_verdict(case, compiled)
        for version in (9, 8, 1):
            case = next(c for c in cases if c['id'] == f'precedence-unknown-{version}')
            self.assertEqual(real_verdict(case, compiled), ('config_shape_invalid', '$'))
            expected = {9: ('config_schema_unsupported', 'schema_version'),
                        8: ('launcher_selection_invalid', 'extensions'),
                        1: ('launcher_extensions_schema', 'extensions')}[version]
            self.assertEqual(wrong_order(case, compiled), expected)
        output = io.StringIO()
        with patch.object(notification, 'verdict', side_effect=wrong_order):
            self.assertEqual(notification.run(output=output), 1)
        for version in (9, 8, 1):
            self.assertIn(f'FAIL precedence-unknown-{version}\n', output.getvalue())
        self.assertEqual(notification.run(output=io.StringIO()), 0)

    # Relaxing the two environment members reproduces the review defect, with
    # valid list/object controls still admitted and both null witnesses detected.
    def test_environment_null_plant(self):
        cases = notification.load_cases(notification.ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(notification.ROOT / 'schemas', root / 'schemas')
            for version in (7, 8):
                path = root / 'schemas' / notification.NAMESPACE / f'manager-config-v{version}.schema.json'
                schema = json.loads(path.read_text())
                members = schema['properties']['environments']['properties']
                for name in ('provider_directories', 'source_signers'):
                    members[name] = {'anyOf': [members[name], {'type': 'null'}]}
                path.write_text(json.dumps(schema))
            compiled = notification.validators(root)
            for case in cases:
                if case['id'].startswith(('env-provider-directories-', 'env-source-signers-')):
                    self.assertEqual(notification.verdict(case, compiled), notification.VALID)
            output = io.StringIO()
            self.assertGreater(notification.check_cases(cases, compiled, output), 0)
            for version in (7, 8):
                for member in ('provider-directories', 'source-signers'):
                    self.assertIn(f'FAIL env-{member}-null-{version}\n', output.getvalue())
        self.assertEqual(notification.run(output=io.StringIO()), 0)

    # The new schema-8 containing schema and checker enforce integer tokens;
    # predecessor numeric spellings have their own positive controls below.
    def test_integer_token_profile(self):
        compiled = notification.validators(notification.ROOT)
        for token in ('8', '8.0', '8e0', '"8"', '8.5', 'null', 'true'):
            raw = '{"schema_version":' + token + ',"skills_root":"x","projects":{}}'
            value = notification.strict(raw)
            self.assertEqual(compiled['manager-config-v8'].is_valid(value), token == '8')
            result = notification.verdict(dict(entry='configuration', input_json=raw), compiled)
            self.assertEqual(result, notification.VALID if token == '8' else ('config_schema_unsupported', 'schema_version'))

    # Released predecessor integer/decimal/exponent spellings remain admitted
    # by the schema and model with /1. Fractional/string/bool/null versions refuse.
    # These bounded structural controls do not execute Core or a real projection.
    def test_predecessor_version_admission(self):
        compiled = notification.validators(notification.ROOT)
        for version in (1, 2, 3, 5, 7):
            for suffix in ('', '.0', 'e0'):
                raw = '{"schema_version":' + str(version) + suffix + ',"skills_root":"x","projects":{}}'
                self.assertTrue(compiled[f'manager-config-v{version}'].is_valid(notification.strict(raw)))
                self.assertEqual(notification.verdict(dict(entry='configuration', input_json=raw), compiled), notification.VALID)
                raw = '{"schema":"curator.launcher-config/1","config_schema":' + str(version) + suffix + ',"config_path":"/example/config.json","extensions":{}}'
                self.assertTrue(compiled['launcher-config-v1'].is_valid(notification.strict(raw)))
                self.assertEqual(notification.verdict(dict(entry='projection', input_json=raw), compiled), notification.VALID)
            for token in (str(version) + '.5', '"' + str(version) + '"', 'true', 'null'):
                raw = '{"schema_version":' + token + ',"skills_root":"x","projects":{}}'
                self.assertFalse(compiled[f'manager-config-v{version}'].is_valid(notification.strict(raw)))
                self.assertEqual(notification.verdict(dict(entry='configuration', input_json=raw), compiled),
                                 ('config_schema_unsupported', 'schema_version'))

    # Re-extending integer-token typing to v7 rejects the named 7.0 witness;
    # integer 7 remains valid, and the unmodified checker accepts both controls.
    def test_predecessor_token_scope_plant(self):
        cases = notification.load_cases(notification.ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(notification.ROOT / 'schemas', root / 'schemas')
            path = root / 'schemas' / notification.NAMESPACE / 'manager-config-v7.schema.json'
            schema = json.loads(path.read_text())
            schema['properties']['schema_version']['type'] = 'integer'
            path.write_text(json.dumps(schema))
            compiled = notification.validators(root)
            self.assertTrue(compiled['manager-config-v7'].is_valid(dict(schema_version=7, skills_root='x', projects={})))
            witness = next(c for c in cases if c['id'] == 'version7-decimal-predecessor')
            self.assertFalse(compiled['manager-config-v7'].is_valid(notification.strict(witness['input_json'])))
            output = io.StringIO()
            self.assertGreater(notification.check_cases(cases, compiled, output), 0)
            self.assertIn('FAIL version7-decimal-predecessor\n', output.getvalue())
        self.assertEqual(notification.run(output=io.StringIO()), 0)

    # Version-token strictness must not narrow the published predecessor's
    # numeric integer fields: integral retention is valid, fractional is not.
    def test_predecessor_integer_admission(self):
        compiled = notification.validators(notification.ROOT)
        for value, expected in ((5.0, True), (5.5, False)):
            carrier = dict(schema_version=8, skills_root='x', projects={},
                           environments=dict(backup_retention=value))
            self.assertEqual(compiled['manager-config-v8'].is_valid(carrier), expected)
            case = dict(entry='configuration', input_json=json.dumps(carrier))
            self.assertEqual(notification.verdict(case, compiled), notification.VALID
                             if expected else ('config_shape_invalid', '$'))

    # Target selection is explicit: a clean Windows path is not a POSIX path.
    # Projection tests use the POSIX target on every runner, including Windows CI.
    def test_target_paths(self):
        for target, good, bad in (('posix', '/example/credential', r'C:\cred'),
                                  ('windows', r'C:\cred', 'relative/credential')):
            self.assertTrue(notification.absolute(good, target))
            self.assertFalse(notification.absolute(bad, target))
            self.assertFalse(notification.absolute(good + '/..', target))

    # Strict decoder detects escaped duplicates and invalid UTF-8 independent
    # of a schema verdict; a nearby valid object still loads.
    def test_strict_decode(self):
        self.assertEqual(notification.strict(b'{"backend":"off"}'), {'backend': 'off'})
        for raw in (b'{"a":1,"a":2}', b'{"a":1,"\\u0061":2}', b'"\xff"', b'{"a":NaN}'):
            with self.assertRaises((ValueError, UnicodeError)):
                notification.strict(raw)
