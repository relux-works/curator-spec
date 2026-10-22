"""Profile native-writer model claims; no runtime or filesystem qualification."""
import copy
import json
import inspect
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator
from ccj1_grammar import exact_patterns
import mcp_native_writer as m
import validate


class NativeWriterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = {c['id']: c for c in json.loads((m.ROOT/'conformance'/m.NAMESPACE/'cases.json').read_text())}

    # Claim: every independently authored verdict is consumed by the public spec gate.
    # Limit: synthetic observations do not establish source admission or filesystem effects.
    def test_corpus(self):
        count, negatives = m.check_corpus()
        self.assertEqual(count, len(self.cases))
        self.assertGreater(negatives, 0)
        self.assertLess(negatives, count)

    # Claim: supplied observations remain unchanged; each modeled successful edit
    # carries identical foreign spans and every refusal discards all intended effects.
    def test_foreign_bytes_and_refusal_state(self):
        for case in self.cases.values():
            with self.subTest(case=case['id']):
                original = copy.deepcopy(case['input'])
                result = m.evaluate(case['input'])
                self.assertEqual(case['input'], original)
                self.assertFalse(result['mutated'])
                if result['code']:
                    self.assertEqual(result['effects'], [])
                    self.assertFalse(any(r['outcome'] in m.SUCCESS for r in result['rows']))
                for effect in result['effects']:
                    observed = original['observations'].get(effect['environment'], {}).get(effect['name'], {})
                    self.assertEqual(effect['foreign_bytes'], observed.get('foreign_bytes', ''))
                    if effect['ownership'] is not None:
                        self.assertTrue(m.ownership_valid(effect['ownership']))

    # Claim: removing only the ownership marker requirement admits a known
    # markerless existing record, and the intended verdict mismatch detects it.
    def test_missing_owner_marker_narrowing_control(self):
        original = m.schema_valid
        def relaxed(name, value):
            if name != 'ownership-v1':
                return original(name, value)
            schema = json.loads((m.ROOT/'schemas'/m.NAMESPACE/'ownership-v1.schema.json').read_text())
            schema['properties']['records']['items']['required'].remove('owner')
            return Draft202012Validator(exact_patterns(schema), registry=m.stage.registry()).is_valid(value)
        with patch.object(m, 'schema_valid', side_effect=relaxed):
            for suffix in ['claude', 'codex']:
                m.check_case(self.cases[suffix+'-added'])
                with self.assertRaisesRegex(ValueError, 'MCP writer verdict mismatch: marker-owner-missing-'+suffix+'$'):
                    m.check_case(self.cases['marker-owner-missing-'+suffix])

    # Claim: deleting only marker publication from an otherwise planned native
    # install is caught by the exact added-state witness; unchanged remains valid.
    def test_native_write_without_marker_publication_control(self):
        source = inspect.getsource(m.pair)
        statement = '    return row, effect, None\n'
        position = source.rfind(statement)
        self.assertGreater(position, 0)
        plant = ("    if effect['write_native']:\n"
                 "        effect.update(ownership=None, write_ownership=False)\n")
        namespace = dict(vars(m))
        source = source[:position] + plant + source[position:]
        exec(compile(source, '<missing-marker-publication-control>', 'exec'), namespace)
        with patch.object(m, 'pair', namespace['pair']):
            for suffix in ['claude', 'codex']:
                m.check_case(self.cases[suffix+'-unchanged'])
                result = m.evaluate(self.cases[suffix+'-added']['input'])
                self.assertTrue(result['effects'][0]['write_native'])
                self.assertFalse(result['effects'][0]['write_ownership'])
                with self.assertRaisesRegex(ValueError, 'MCP writer verdict mismatch: '+suffix+'-added$'):
                    m.check_case(self.cases[suffix+'-added'])

    # Claim: bypassing only the same-NAME foreign conflict plans an overwrite;
    # a typed conflict witness detects that defect beside its valid first install.
    def test_foreign_overwrite_narrowing_control(self):
        with patch.object(m, 'foreign_conflict', return_value=False):
            for suffix in ['claude', 'codex']:
                m.check_case(self.cases[suffix+'-added'])
                case = self.cases['foreign-equal-'+suffix]
                result = m.evaluate(case['input'])
                self.assertEqual(result['rows'][0]['outcome'], 'added')
                self.assertTrue(result['effects'][0]['write_ownership'])
                with self.assertRaisesRegex(ValueError, 'MCP writer verdict mismatch: foreign-equal-'+suffix+'$'):
                    m.check_case(case)

    # Claim: each additional model gate has a bounded actual-code relaxation
    # detected by its named negative while a nearby qualified install still passes.
    # These are synthetic checker controls, not production writer mutants.
    def test_additional_narrowing_controls(self):
        controls = [
            ('pair', "facts.get('scope') != 'profile'", 'False', 'scope-project', 'claude-added'),
            ('pair', "observation.get('read', 'ok') != 'ok'", 'False', 'unreadable-read-claude', 'claude-added'),
            ('pair', "observation.get('marker_read', 'ok') != 'ok'", 'False', 'unreadable-marker_read-claude', 'claude-added'),
            ('pair', "observation.get('legacy_link')", 'False', 'legacy-link-claude', 'claude-added'),
            ('pair', "base.get('read', 'ok') != 'ok'", 'False', 'codex-base-unreadable', 'codex-added'),
            ('pair', "name in base.get('names', [])", "name in base.get('names', []) and base.get('revision') == 'A'", 'codex-b-late-collision', 'codex-b-clean'),
            ('pair', 'elif drift or removed:', 'elif drift:', 'cleanup-pending-claude', 'claude-unchanged'),
            ('pair', 'elif changed:', 'elif False:', 'replace-no-action-claude', 'claude-unchanged'),
            ('pair', "operation == 'replace' and drift", 'False', 'replace-drift-claude', 'replace-claude'),
            ('action_allowed', "facts.get('action_protected') is True", 'True', 'action-repository-record-claude', 'restore-claude'),
            ('action_allowed', "facts.get('policy_allows') is True", 'True', 'action-policy-denied-claude', 'restore-claude'),
            ('qualified', "facts.get('platform') == 'darwin-arm64'", 'True', 'pin-platform-claude', 'claude-added'),
            ('qualified', "(pin.get('version'), pin.get('sha256')) == PINS[environment]", "pin.get('version') == PINS[environment][0]", 'pin-digest-claude', 'claude-added'),
            ('qualified', "(pin.get('version'), pin.get('sha256')) == PINS[environment]", "pin.get('sha256') == PINS[environment][1]", 'pin-version-claude', 'claude-added'),
        ]
        for function, old, new, witness, positive in controls:
            with self.subTest(function=function, witness=witness):
                source = inspect.getsource(getattr(m, function))
                self.assertEqual(source.count(old), 1)
                namespace = dict(vars(m))
                exec(compile(source.replace(old, new), '<bounded-writer-control>', 'exec'), namespace)
                with patch.object(m, function, namespace[function]):
                    m.check_case(self.cases[positive])
                    with self.assertRaisesRegex(ValueError, 'MCP writer verdict mismatch: '+witness+'$'):
                        m.check_case(self.cases[witness])

    # Claim: dropping one effective action identity binding reproduces its exact
    # replay violation beside a valid protected restore, without disabling schemas.
    def test_action_binding_narrowing_controls(self):
        for field in ['profile_id', 'name', 'server_sha256', 'content_sha256',
                      'policy_sha256', 'operation', 'state']:
            with self.subTest(field=field):
                source = inspect.getsource(m.action_allowed)
                old = '    return (facts.get'
                self.assertEqual(source.count(old), 1)
                namespace = dict(vars(m))
                source = source.replace(old, f"    wanted.pop({field!r})\n"+old)
                exec(compile(source, '<bounded-action-control>', 'exec'), namespace)
                with patch.object(m, 'action_allowed', namespace['action_allowed']):
                    m.check_case(self.cases['restore-claude'])
                    witness = 'action-replay-'+field+'-claude'
                    with self.assertRaisesRegex(ValueError, 'MCP writer verdict mismatch: '+witness+'$'):
                        m.check_case(self.cases[witness])

    # Claim: the production dispatcher fails for the planted exact model error.
    def test_production_dispatch(self):
        with patch.object(m, 'check_corpus', side_effect=ValueError('planted native writer violation')) as plant:
            with self.assertRaisesRegex(validate.ValidationFailure, 'planted native writer violation'):
                validate.validate_mcp_native_writer()
            plant.assert_called_once_with(validate.ROOT)
        validate.validate_mcp_native_writer()

    # Claim: dropping a required case coherently from both files is still rejected.
    def test_missing_required_witness(self):
        with tempfile.TemporaryDirectory(prefix='writer-corpus-') as directory:
            root = Path(directory); corpus = root/'conformance'/m.NAMESPACE; corpus.mkdir(parents=True)
            cases = [c for c in self.cases.values() if c['id'] != 'markerless-claude']
            (corpus/'cases.json').write_text(json.dumps(cases))
            (corpus/'coverage.json').write_text(json.dumps({'cases': [c['id'] for c in cases]}))
            with self.assertRaisesRegex(ValueError, '^MCP writer case inventory mismatch$'):
                m.check_corpus(root)

    # Claim: closed carriers reject unknown members, final-LF binds, wrong paths,
    # project action replay and unsorted/duplicate records beside valid controls.
    def test_closed_carriers(self):
        f = self.cases['restore-claude']['input']
        action = f['actions']['claude_code']['docs']
        owned = f['observations']['claude_code']['docs']['ownership']
        self.assertTrue(m.schema_valid('action-v1', action))
        self.assertTrue(m.ownership_valid(owned))
        for field, value in [('profile_id', 'sample\n'), ('path', 'curator-mcp.config.toml'),
                             ('server_sha256', action['server_sha256']+'\n'),
                             ('scope', 'project'), ('extra', True)]:
            with self.subTest(field=field):
                changed = copy.deepcopy(action); changed[field] = value
                self.assertFalse(m.schema_valid('action-v1', changed))
        changed = copy.deepcopy(owned); changed['records'] *= 2
        self.assertFalse(m.ownership_valid(changed))
        changed = copy.deepcopy(owned); other = copy.deepcopy(changed['records'][0]); other['name'] = 'aaa'
        changed['records'].append(other)
        self.assertFalse(m.ownership_valid(changed))

    # Claim: release/remove preserve neighboring ownership records in the same
    # protected ledger; marker removal is per NAME, not ownership of the whole file.
    def test_cleanup_preserves_neighbor_marker(self):
        for operation in ['remove', 'release']:
            for suffix, environment in [('claude', 'claude_code'), ('codex', 'codex_cli')]:
                with self.subTest(operation=operation, environment=environment):
                    f = copy.deepcopy(self.cases[operation+'-'+suffix]['input'])
                    owned = f['observations'][environment]['docs']['ownership']
                    other = copy.deepcopy(owned['records'][0]); other['name'] = 'other'
                    owned['records'].append(other)
                    result = m.evaluate(f)
                    self.assertIsNone(result['code'])
                    self.assertEqual(result['effects'][0]['ownership']['records'], [other])

    # Claim: these model entrypoints do not invoke process/network APIs for a valid
    # install/restore; a bounded direct call confirms the execution tripwire fires.
    def test_no_execution(self):
        with patch('subprocess.run', side_effect=AssertionError('execution tripwire')) as run, \
             patch('subprocess.Popen', side_effect=AssertionError('spawn tripwire')) as spawn, \
             patch('socket.create_connection', side_effect=AssertionError('network tripwire')) as connect:
            for case in ['claude-added', 'codex-added', 'restore-claude', 'restore-codex', 'muse-required']:
                m.check_case(self.cases[case])
            run.assert_not_called(); spawn.assert_not_called(); connect.assert_not_called()
            with self.assertRaisesRegex(AssertionError, '^execution tripwire$'):
                __import__('subprocess').run(['inert-control'])


if __name__ == '__main__':
    unittest.main()
