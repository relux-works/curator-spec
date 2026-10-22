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
            for witness in sorted(m.REQUIRED):
                cases = [c for c in self.cases.values() if c['id'] != witness]
                (corpus/'cases.json').write_text(json.dumps(cases))
                (corpus/'coverage.json').write_text(json.dumps({'cases': [c['id'] for c in cases]}))
                with self.subTest(witness=witness), self.assertRaisesRegex(ValueError, '^MCP writer case inventory mismatch$'):
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

    # Claim: new private carriers enforce CCJ scalar types in addition to JSON
    # Schema: integral floats and unpaired surrogates refuse beside valid actions.
    # Removing the actual shared scalar guard reproduces both named violations.
    def test_carrier_scalar_gate(self):
        valid = self.cases['restore-claude']['input']['actions']['claude_code']['docs']
        self.assertTrue(m.schema_valid('action-v1', valid))
        variants = [dict(valid, schema_version=1.0), dict(valid, approver='\ud800')]
        for value in variants:
            self.assertFalse(m.schema_valid('action-v1', value))
        with patch.object(m.stage, 'scalar_tree', return_value=None):
            self.assertTrue(m.schema_valid('action-v1', valid))
            for value in variants:
                self.assertTrue(m.schema_valid('action-v1', value))
                with self.assertRaises(AssertionError):
                    self.assertFalse(m.schema_valid('action-v1', value))

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

    # Claim: all 19 independent review witnesses now match their full declared
    # plans, beside valid protected-neighbor and single-NAME controls.
    def test_review_regressions(self):
        witnesses = []
        for suffix in ['claude', 'codex']:
            witnesses += ['neighbor-'+variant+'-'+suffix for variant in
                          ['unprotected', 'other-profile', 'other-environment', 'other-path', 'missing-owner']]
            witnesses += ['joint-add-'+str(n)+'-'+suffix for n in [2, 3]]
            witnesses += ['joint-'+op+'-'+suffix for op in ['remove', 'release']]
            m.check_case(self.cases['neighbor-valid-'+suffix])
            m.check_case(self.cases[suffix+'-added'])
        witnesses.append('codex-del-roundtrip')
        self.assertEqual(len(witnesses), 19)
        self.assertTrue(set(witnesses) <= m.REQUIRED)
        for witness in witnesses:
            with self.subTest(witness=witness):
                m.check_case(self.cases[witness])
                result = m.evaluate(self.cases[witness]['input'])
                self.assertEqual(sum(e['write_ownership'] for e in result['effects']), 1)

    # Claim: provenance, profile binding and marker-owner gates prevent neighbor
    # adoption; relaxing only the selected gate changes its exact full verdict.
    def test_neighbor_adoption_narrowing_controls(self):
        for variant, old, new in [
            ('unprotected', "observation.get('protected') is not True", 'False'),
            ('other-profile', 'document.get(k) != v', "document.get(k) != v and k != 'profile_id'"),
        ]:
            source = inspect.getsource(m.trusted_ownership)
            self.assertEqual(source.count(old), 1)
            namespace = dict(vars(m))
            exec(compile(source.replace(old, new), '<neighbor-adoption-control>', 'exec'), namespace)
            with patch.object(m, 'trusted_ownership', namespace['trusted_ownership']):
                for suffix in ['claude', 'codex']:
                    m.check_case(self.cases['neighbor-valid-'+suffix])
                    witness = 'neighbor-'+variant+'-'+suffix
                    result = m.evaluate(self.cases[witness]['input'])
                    self.assertIsNone(result['code'])
                    self.assertEqual([r['name'] for r in result['effects'][0]['ownership']['records']], ['docs', 'other'])
                    with self.assertRaisesRegex(ValueError, 'MCP writer verdict mismatch: '+witness+'$'):
                        m.check_case(self.cases[witness])
        original = m.schema_valid
        def missing_owner(name, value):
            if name != 'ownership-v1':
                return original(name, value)
            schema = json.loads((m.ROOT/'schemas'/m.NAMESPACE/'ownership-v1.schema.json').read_text())
            schema['properties']['records']['items']['required'].remove('owner')
            return Draft202012Validator(exact_patterns(schema), registry=m.stage.registry()).is_valid(value)
        with patch.object(m, 'schema_valid', side_effect=missing_owner):
            for suffix in ['claude', 'codex']:
                m.check_case(self.cases['neighbor-valid-'+suffix])
                witness = 'neighbor-missing-owner-'+suffix
                with self.assertRaisesRegex(ValueError, 'MCP writer verdict mismatch: '+witness+'$'):
                    m.check_case(self.cases[witness])

    # Claim: cross-environment/path envelopes fail the actual ownership schema
    # beside valid ledgers. Removing only its cross-field constraints admits
    # both malformed shapes; independent binding checks still prevent adoption.
    def test_neighbor_path_environment_schema_control(self):
        original = m.schema_valid
        def relaxed(name, value):
            if name != 'ownership-v1':
                return original(name, value)
            schema = json.loads((m.ROOT/'schemas'/m.NAMESPACE/'ownership-v1.schema.json').read_text())
            schema.pop('allOf')
            return Draft202012Validator(exact_patterns(schema), registry=m.stage.registry()).is_valid(value)
        for suffix in ['claude', 'codex']:
            env = 'claude_code' if suffix == 'claude' else 'codex_cli'
            positive = self.cases['neighbor-valid-'+suffix]
            m.check_case(positive)
            for variant in ['other-environment', 'other-path']:
                witness = self.cases['neighbor-'+variant+'-'+suffix]
                document = witness['input']['observations'][env]['docs']['ownership']
                self.assertFalse(m.ownership_valid(document))
                with patch.object(m, 'schema_valid', side_effect=relaxed):
                    self.assertTrue(m.ownership_valid(positive['input']['observations'][env]['docs']['ownership']))
                    self.assertTrue(m.ownership_valid(document))
                    with self.assertRaises(AssertionError):
                        self.assertFalse(m.ownership_valid(document))
                    m.check_case(witness)

    # Claim: disabling only ledger composition reproduces every multi-NAME
    # review violation; existing single-NAME publications still pass.
    def test_joint_ledger_narrowing_control(self):
        with patch.object(m, 'compose_ownership', return_value=None) as plant:
            for suffix in ['claude', 'codex']:
                m.check_case(self.cases['neighbor-valid-'+suffix])
                for stem in ['joint-add-2', 'joint-add-3', 'joint-remove', 'joint-release']:
                    witness = stem+'-'+suffix
                    with self.assertRaisesRegex(ValueError, 'MCP writer verdict mismatch: '+witness+'$'):
                        m.check_case(self.cases[witness])
            self.assertGreater(plant.call_count, 0)

    # Claim: adds compose with unchanged siblings and preserve an
    # untouched neighbor; partial remove/release keeps only the remaining marker.
    def test_mixed_ledger_operations(self):
        for env, suffix in [('claude_code', 'claude'), ('codex_cli', 'codex')]:
            f = copy.deepcopy(self.cases[suffix+'-unchanged']['input'])
            observed = f['observations'][env]['docs']
            neighbor = copy.deepcopy(observed['ownership']['records'][0]); neighbor['name'] = 'neighbor'
            observed['ownership']['records'].append(neighbor)
            f['servers'].append(dict(copy.deepcopy(f['servers'][0]), name='other'))
            f['observations'][env]['other'] = dict(copy.deepcopy(observed), entry=None)
            result = m.evaluate(f)
            self.assertIsNone(result['code'])
            self.assertEqual([r['outcome'] for r in result['rows']], ['unchanged', 'added'])
            written = [e for e in result['effects'] if e['write_ownership']]
            self.assertEqual(len(written), 1)
            self.assertEqual([r['name'] for r in written[0]['ownership']['records']], ['docs', 'neighbor', 'other'])
            self.assertEqual(written[0]['ownership']['records'][1], neighbor)
            for operation in ['remove', 'release']:
                f = copy.deepcopy(self.cases['joint-'+operation+'-'+suffix]['input'])
                f['servers'] = f['servers'][:1]
                result = m.evaluate(f)
                self.assertIsNone(result['code'])
                self.assertEqual([r['name'] for r in result['effects'][0]['ownership']['records']], ['other'])

    # Claim: two authorized restores/replacements compose their new digests and
    # observed preimages into one ledger, preserving the untouched third marker.
    def test_joint_updates(self):
        for env, suffix in [('claude_code', 'claude'), ('codex_cli', 'codex')]:
            for operation in ['restore', 'replace']:
                f = copy.deepcopy(self.cases[operation+'-'+suffix]['input'])
                ledger = f['observations'][env]['docs']['ownership']
                neighbor = dict(ledger['records'][0], name='neighbor')
                other = dict(ledger['records'][0], name='other')
                ledger['records'] += [neighbor, other]
                f['servers'].append(dict(copy.deepcopy(f['servers'][0]), name='other'))
                f['observations'][env]['other'] = copy.deepcopy(f['observations'][env]['docs'])
                if operation == 'restore':
                    f['observations'][env]['other']['entry'] = 'other external edit'
                else:
                    # A clean original Codex NAME has different selected bytes.
                    server = self.cases[suffix+'-added']['input']['servers'][0]['server']
                    original = m.native_entry(env, 'other', server)
                    f['observations'][env]['other']['entry'] = original
                    other['installed_sha256'] = m.byte_digest(original)
                    f['observations'][env]['other']['ownership'] = copy.deepcopy(ledger)
                f['actions'][env]['other'] = dict(f['actions'][env]['docs'], name='other')
                result = m.evaluate(f)
                self.assertIsNone(result['code'])
                self.assertEqual([r['outcome'] for r in result['rows']],
                                 ['restored' if operation == 'restore' else 'updated']*2)
                written = [e for e in result['effects'] if e['write_ownership']]
                self.assertEqual(len(written), 1)
                records = {r['name']: r for r in written[0]['ownership']['records']}
                self.assertEqual(set(records), {'docs', 'neighbor', 'other'})
                self.assertEqual(records['neighbor'], neighbor)
                for effect in result['effects']:
                    record = records[effect['name']]
                    self.assertEqual(record['installed_sha256'], m.byte_digest(effect['entry']))
                    self.assertEqual(record['preimage_sha256'], m.byte_digest(f['observations'][env][effect['name']]['entry']))
                    self.assertEqual(record['server_sha256'], f['actions'][env][effect['name']]['server_sha256'])

    # Claim: conflicting protected preimages of one physical ledger refuse the
    # whole set without planned writes; identical snapshots remain installable.
    def test_inconsistent_ledger_preimages(self):
        for env, suffix in [('claude_code', 'claude'), ('codex_cli', 'codex')]:
            f = copy.deepcopy(self.cases['joint-add-2-'+suffix]['input'])
            m.check_case(self.cases['joint-add-2-'+suffix])
            f['observations'][env]['other'].update(
                protected=True, ownership=copy.deepcopy(self.cases['neighbor-valid-'+suffix]['input']['observations'][env]['docs']['ownership']))
            before = copy.deepcopy(f)
            result = m.evaluate(f)
            self.assertEqual(result['code'], m.UNREADABLE)
            self.assertEqual(result['effects'], [])
            self.assertEqual([(r['outcome'], r['code']) for r in result['rows']],
                             [('refused', m.UNREADABLE), ('skipped: drift', None)])
            self.assertEqual(f, before)
            source = inspect.getsource(m.compose_ownership)
            old = 'any(document != documents[0] for document in documents[1:])'
            self.assertEqual(source.count(old), 1)
            namespace = dict(vars(m))
            exec(compile(source.replace(old, 'False'), '<conflicting-ledger-control>', 'exec'), namespace)
            with patch.object(m, 'compose_ownership', namespace['compose_ownership']):
                m.check_case(self.cases['joint-add-2-'+suffix])
                self.assertIsNone(m.evaluate(f)['code'])

    # Claim: the final shape guard refuses a malformed composed record with no
    # effects. A bounded faulty-producer plant reaches that exact guard; removing
    # only it lets the invalid ledger escape beside an unaffected valid install.
    def test_final_ledger_validation_control(self):
        original = m.pair
        def malformed(*args):
            row, effect, code = original(*args)
            if effect['write_ownership']:
                effect['ownership']['records'][0]['owner'] = 'foreign'
            return row, effect, code
        m.check_case(self.cases['claude-added'])
        with patch.object(m, 'pair', side_effect=malformed):
            result = m.evaluate(self.cases['claude-added']['input'])
            self.assertEqual(result['code'], m.UNREADABLE)
            self.assertEqual(result['effects'], [])
            self.assertEqual(result['rows'][0]['outcome'], 'refused')
        source = inspect.getsource(m.compose_ownership)
        old = 'not ownership_valid(document)'
        self.assertEqual(source.count(old), 1)
        namespace = dict(vars(m))
        exec(compile(source.replace(old, 'False'), '<final-ledger-shape-control>', 'exec'), namespace)
        with patch.object(m, 'compose_ownership', namespace['compose_ownership']):
            m.check_case(self.cases['claude-added'])
            with patch.object(m, 'pair', side_effect=malformed):
                result = m.evaluate(self.cases['claude-added']['input'])
                self.assertIsNone(result['code'])
                self.assertFalse(m.ownership_valid(result['effects'][0]['ownership']))

    # Claim: every admitted ASCII control argument, quotes, slashes and Unicode
    # round-trip through independent native parsers; removing only DEL escaping
    # reproduces TOMLDecodeError while its ordinary sibling still parses.
    def test_native_control_roundtrip(self):
        import tomllib
        values = [chr(n) for n in range(32)] + ['\x7f', 'plain', 'é 😀', 'a\\b', 'a"b', '\x80', '\uffff']
        def parse(env, text):
            return (tomllib.loads(text)['mcp_servers']['docs'] if env == 'codex_cli' else json.loads(text))['args']
        for env, suffix in [('claude_code', 'claude'), ('codex_cli', 'codex')]:
            for value in values:
                with self.subTest(environment=env, value=repr(value)):
                    f = copy.deepcopy(self.cases[suffix+'-added']['input'])
                    server = f['servers'][0]['server']; server['args'] = ['a'+value+'b']
                    self.assertTrue(m.stage.server_valid(server))
                    self.assertTrue(m.stage.package_byte_bounds(server))
                    self.assertTrue(m.stage.audit_clear(server))
                    result = m.evaluate(f)
                    self.assertIsNone(result['code'])
                    self.assertEqual(parse(env, result['effects'][0]['entry']), server['args'])
        source = inspect.getsource(m.native_entry)
        old = ".replace('\\x7f', r'\\u007F')"
        self.assertEqual(source.count(old), 1)
        namespace = dict(vars(m))
        exec(compile(source.replace(old, ''), '<DEL-encoding-control>', 'exec'), namespace)
        with patch.object(m, 'native_entry', namespace['native_entry']):
            m.check_case(self.cases['codex-added'])
            result = m.evaluate(self.cases['codex-del-roundtrip']['input'])
            with self.assertRaisesRegex(tomllib.TOMLDecodeError, 'Illegal character'):
                parse('codex_cli', result['effects'][0]['entry'])
            with self.assertRaisesRegex(ValueError, 'MCP writer verdict mismatch: codex-del-roundtrip$'):
                m.check_case(self.cases['codex-del-roundtrip'])

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
