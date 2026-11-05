"""Carrier and independent semantic controls; no installed runtime claims."""
import ast
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import generate_profile_command_roots as fixtures
import profile_command_roots as subject
from jsonschema import ValidationError


class ProfileCommandRoots(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((subject.CORPUS/'cases.json').read_text())

    def test_corpus_and_regeneration(self):
        # The independent model accepts the exact committed deterministic corpus.
        subject.validate_data(self.data)
        subprocess.run([sys.executable, str(subject.ROOT/'tools/generate_profile_command_roots.py'), '--check'], check=True)

    def test_every_data_drop_and_duplicate_is_detected(self):
        # Required-ID custody rejects every single omission and duplicate.
        count = 0
        for section in subject.REQUIRED:
            for index, case in enumerate(self.data[section]):
                with self.subTest(section=section, case=case['id']):
                    data = deepcopy(self.data); del data[section][index]
                    with self.assertRaisesRegex(ValueError, 'required case IDs|does not have enough'):
                        subject.validate_data(data)
                    count += 1
            data = deepcopy(self.data); data[section].append(deepcopy(data[section][0]))
            with self.assertRaisesRegex(ValueError, 'required case IDs'):
                subject.validate_data(data)
        print(f'plants: {count} individual data drops and {len(subject.REQUIRED)} duplicates detected')

    def test_coherent_generator_drops_are_detected(self):
        # Regeneration agrees with this intentionally altered generator output;
        # the independent required IDs, not generator byte equality, catch it.
        for section in subject.REQUIRED:
            for case in self.data[section]:
                with self.subTest(section=section, case=case['id']):
                    data = fixtures.output()
                    data[section] = [c for c in data[section] if c['id'] != case['id']]
                    with self.assertRaisesRegex(ValueError, 'required case IDs'):
                        subject.validate_data(json.loads(json.dumps(data)))
        print('plants: every coherent generator drop detected by independent ID custody')

    def test_expected_flip_is_detected(self):
        # Changing a refusal into acceptance cannot pass the semantic validator.
        for section in ['cases', 'references', 'launchers', 'retention', 'sessions', 'hooks']:
            for i, case in enumerate(self.data[section]):
                if case['expected'] == 'accept':
                    continue
                data = deepcopy(self.data)
                data[section][i].update(expected='accept', reason='verified')
                with self.subTest(case=case['id']), self.assertRaises(ValueError):
                    subject.validate_data(data)

    def test_review_mutants_fail_on_intended_controls(self):
        source = Path(subject.__file__).read_text()
        # Each mutant removes exactly a contract check. A named valid-shape
        # witness must change its decision; a parser crash is not detection.
        plants = [
            ("checks['launcher-state.schema.json'].is_valid(r)", 'True', ['launcher-schema']),
            ("o[key] == t[key] and sha(t[key]) == b[key+'_sha256']", 'True', ['tampered-marker', 'tampered-receipt', 'tampered-inventory']),
            ("len({c['name'] for c in exports}) == len(exports)", 'True', ['colliding-skills']),
            ("marker['binding'] == base and marker['profile'] == t['profile']\n            and marker['receipt_sha256'] == b['receipt_sha256']", 'True', ['marker-binding']),
            ("receipt['binding'] == base and receipt['profile'] == t['profile']", 'True', ['receipt-binding']),
            ("o['root_mode'] == 0o700", "o['root_mode'] & 0o022 == 0", ['readable-root']),
            ("b['platform'] == t['platform']", 'True', ['platform-substitution']),
            ("not device(t['profile'])", 'True', ['profile-device']),
            ("all(bounded_path(p, windows) for p in all_paths)",
             "bounded_path(root+'/.curator-profile-command-root.json', windows)", ['command-path-overflow']),
            ("hop['metadata'] == metadata(a, windows)", 'True', ['file-object-substitution']),
            ("hop['sha256'] == 'sha256:'+sha(a['bytes'])", 'True', ['tampered-root', 'script-digest']),
            ("hop['target'] == expected_target", 'True', ['script-target', 'windows-cmd-target']),
            ("r['gateway'] == gateway_path(s, r['command'], r['settings_resource'])\n            and bounded_path(r['gateway'], t['platform'].startswith('windows-'))", 'True', ['reference-gateway']),
            ("r['id'] == case['id_authority']", 'True', ['reference-id']),
            ("r['command'] in t['names']", 'True', ['reference-command', 'reference-unexported']),
            ("r['effective_path'] == expected", 'True', ['launcher-ambient-first', 'launcher-root-absent']),
            ("r['path_value'] == sep.join(expected)", 'True', ['launcher-path-value']),
            ("r['command_root'] == b", 'True', ['launcher-binding']),
            ("r['references'] == case['references_authority']", 'True', ['retention-reference']),
            ("case['externally_verified']", 'True', ['reference-external']),
            ("case['observer_confirmed'] and case['descendants_quiescent']", 'True', ['session-dead-pid', 'session-descendant']),
        ]
        sections = {'cases': 'root_check', 'references': 'reference_check',
                    'launchers': 'launcher_check', 'retention': 'retention_check', 'sessions': 'session_check'}
        witnesses = {c['id']: (c, fn) for sec, fn in sections.items() for c in self.data[sec]}
        for old, new, ids in plants:
            self.assertIn(old, source)
            namespace = {'__file__': subject.__file__, '__name__': 'mutant'}
            exec(compile(source.replace(old, new), subject.__file__, 'exec'), namespace)
            for id_ in ids:
                case, fn = witnesses[id_]
                with self.subTest(mutant=old, witness=id_):
                    actual = namespace['decision'](namespace[fn], case['state'], subject.validators())
                    self.assertNotEqual(actual, (case['expected'], case['reason']))
        print(f'plants: {len(plants)} targeted review checker mutants detected without crashes')

    def test_every_root_refusal_guard_has_a_noncrashing_witness(self):
        # Every root refusal guard has a valid-shape witness that fails when removed.
        source = Path(subject.__file__).read_text(); tree = ast.parse(source)
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'root_check')
        calls = [n for n in ast.walk(function) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name) and n.func.id == 'require']
        for call in calls:
            mutant = deepcopy(tree)
            for n in ast.walk(mutant):
                if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                        and n.func.id == 'require' and n.lineno == call.lineno):
                    n.args[0] = ast.Constant(True)
            namespace = {'__file__': subject.__file__, '__name__': 'mutant'}
            exec(compile(ast.fix_missing_locations(mutant), subject.__file__, 'exec'), namespace)
            witnesses = []
            for case in self.data['cases']:
                actual = namespace['decision'](namespace['root_check'], case['state'], subject.validators())
                if actual != (case['expected'], case['reason']): witnesses.append(case['id'])
            with self.subTest(guard=ast.unparse(call.args[1])):
                self.assertTrue(witnesses, 'refusal guard has no intended noncrashing witness')
        print(f'plants: all {len(calls)} root refusal-guard removals detected without crashes')

    def test_two_version_and_hook_plants(self):
        # Concurrent versions require distinct receipt-bound bytes and valid hook roots.
        original = self.data
        for replacement in [fixtures.fixture('second', 'one'), fixtures.fixture('first', 'two')]:
            data = deepcopy(original); data['two_profiles'][1] = replacement
            with self.assertRaises(subject.Refusal):
                subject.validate_data(data)
        data = deepcopy(original)
        # Different commit and generation, but receipt-bound executable bytes
        # match: the old unbound trusted.bytes comparison missed this plant.
        s = data['two_profiles'][1]
        old = json.loads(data['two_profiles'][0]['trusted']['receipt'])['commands'][0]['executable_sha256']
        f = fixtures.first_file(s); f.update(bytes='native one', size=10)
        fixtures.edit_record(s, 'inventory', lambda r:r['commands'][0]['chain'][0].update(sha256='sha256:'+old))
        fixtures.edit_record(s, 'receipt', lambda r:r['commands'][0].update(executable_sha256=old))
        self.assertEqual(subject.verdict(s), 'accept')
        with self.assertRaisesRegex(subject.Refusal, 'two-executable-bytes'):
            subject.validate_data(data)
        for plant in ['identical', 'tamper']:
            data = deepcopy(original)
            if plant == 'identical': data['hook_upgrade'][1] = deepcopy(data['hook_upgrade'][0])
            else: data['hook_upgrade'][0]['observed']['root_kind'] = 'missing'
            with self.assertRaises(subject.Refusal): subject.validate_data(data)
        print('plants: identical receipt-bound bytes, identical hook pair and tampered hook pair detected')

    def test_hook_contract_state_machine_and_crashes(self):
        # Independent settings resources preserve pinned roots across upgrade and failed proof.
        old, new = deepcopy(self.data['hook_upgrade'])
        model = subject.HookModel(old)
        ref = model.retain('/settings/hooks', 'request')
        self.assertEqual(model.retain('/settings/hooks', 'retry'), ref)
        self.assertEqual(model.list(), [ref])  # discover after lost retain reply
        # A second project's per-agent hook resource can select the same generation.
        resource = '/projects/second/.codex/hooks.json'
        peer = model.retain(resource, 'peer-agent')
        model.activate(peer, True, model.revisions[peer])
        self.assertEqual(model.invoke(resource), old['trusted']['binding']['generation'])
        model.active.pop(resource); model.release(peer, True, model.revisions[peer])
        model.activate(ref, True, model.revisions[ref]); model.install(new); model.gc()
        self.assertEqual(model.invoke(), old['trusted']['binding']['generation'])
        with self.assertRaisesRegex(subject.Refusal, 'request-conflict'):
            model.retain('/settings/hooks', 'request')
        other = model.retain('/settings/other', 'other-resource')
        model.activate(other, True, model.revisions[other])
        self.assertEqual(model.invoke('/settings/other'), new['trusted']['binding']['generation'])
        self.assertEqual(model.invoke(), old['trusted']['binding']['generation'])
        model.active.pop('/settings/other')
        model.release(other, True, model.revisions[other])
        replacement = model.retain('/settings/hooks', 'new')
        with self.assertRaises(subject.Refusal): model.activate(replacement, False, model.revisions[replacement])
        self.assertEqual(model.invoke(), old['trusted']['binding']['generation'])
        model.activate(replacement, True, model.revisions[replacement]); model.gc()
        self.assertEqual(len(model.roots), 2)  # crash before old release retains rollback
        with self.assertRaises(subject.Refusal): model.release(ref, False, model.revisions[ref])
        model.release(ref, True, model.revisions[ref]); model.gc()
        self.assertEqual(len(model.roots), 1)
        model.roots[model.current]['observed']['root_kind'] = 'missing'
        with self.assertRaisesRegex(subject.Refusal, 'hook-root'): model.invoke()

    def test_reference_request_cap_and_terminal_replay(self):
        # The finite request cap preserves known idempotent and terminal replays.
        model = subject.HookModel(deepcopy(self.data['hook_upgrade'][0]))
        reference = model.retain('/settings/hooks', 'request-0')
        for index in range(1, 4096):
            self.assertEqual(model.retain('/settings/hooks', f'request-{index}'), reference)
        self.assertEqual(len(model.refs), 1)
        with self.assertRaisesRegex(subject.Refusal, 'reference-cap'):
            model.retain('/settings/hooks', 'request-over-cap')
        self.assertEqual(model.retain('/settings/hooks', 'request-0'), reference)
        model.release(reference, True, model.revisions[reference])
        self.assertIn(reference, model.list())
        self.assertEqual(model.retain('/settings/hooks', 'request-0'), reference)
        self.assertNotIn(reference, model.refs)
        with self.assertRaises(subject.Refusal): model.activate(reference, True, model.revisions[reference])

    def test_liveness_mutants_are_detected(self):
        # Each declared liveness edge independently prevents collection.
        for edge in ['session', 'snapshot', 'rollback', 'journal', 'descendant', 'unknown', 'installed']:
            case = next(c for c in self.data['lifecycle'] if c['state'][edge] and c['state']['operation'] == 'gc')
            state = deepcopy(case['state']); state[edge] = False
            self.assertNotEqual(subject.lifecycle(state), case['expected'])
        self.assertEqual(subject.lifecycle(next(c['state'] for c in self.data['lifecycle'] if c['id']=='permitted-gc')), 'collect')

    def test_windows_paths_and_longest_command(self):
        # Native path-list refusal and longest command preflight are both enforced.
        schema = subject.validators()['launch-fragment-model']
        s = fixtures.fixture(platform='windows-amd64')
        self.assertTrue(schema.is_valid(s['fragment']))
        for path in ['/a:/b', 'C:/a;D:/b', 'C:relative', '//host/share', 'C:/a:stream']:
            f = deepcopy(s['fragment']); f['path_prepend'] = path
            if path.startswith('//'): self.assertFalse(subject.absolute(path, True))
            else: self.assertFalse(schema.is_valid(f), path)
        case = next(c for c in self.data['cases'] if c['id'] == 'command-path-overflow')
        root = case['state']['fragment']['path_prepend']
        self.assertLessEqual(len((root+'/.curator-profile-command-root.json').encode()), 240)
        self.assertGreater(len(next(iter(case['state']['observed']['files'])).encode()), 240)

    def test_all_closed_carriers_and_decoder_failure(self):
        # Closed records refuse unknown/missing fields and malformed corpus decoding.
        checks = subject.validators(); root = self.data['cases'][0]['state']
        records = {
            'launch-fragment-model': root['fragment'],
            'fragment-members.schema.json': {k:root['fragment'][k] for k in ['command_root','path_prepend']},
            'inventory.schema.json': json.loads(root['trusted']['inventory']),
            'generation-marker.schema.json': json.loads(root['trusted']['marker']),
            'root-receipt.schema.json': json.loads(root['trusted']['receipt']),
            'persistent-reference.schema.json': self.data['references'][0]['state']['record'],
            'launcher-state.schema.json': self.data['launchers'][0]['state']['record'],
            'snapshot-retention.schema.json': self.data['retention'][0]['state']['record'],
            'session-pin.schema.json': self.data['sessions'][0]['state']['record'],
        }
        for name, record in records.items():
            with self.subTest(name=name):
                self.assertTrue(checks[name].is_valid(record))
                bad = dict(record, unknown=True); self.assertFalse(checks[name].is_valid(bad))
                bad = deepcopy(record); del bad[checks[name].schema['required'][0]]
                self.assertFalse(checks[name].is_valid(bad))
        with tempfile.TemporaryDirectory() as directory:
            corpus = Path(directory)
            dropped = deepcopy(self.data); dropped['launchers'].pop()
            for raw in ['{"version":"wrong"}', '{', json.dumps(dropped)]:
                (corpus/'cases.json').write_text(raw)
                with patch.object(subject, 'CORPUS', corpus):
                    with self.assertRaisesRegex(ValueError, '^command-root validation failed:'):
                        subject.validate()


    def test_rc7_ownership_and_non_emittable_leaf_cross_validation(self):
        # Full registry, authoritative rc7 reader, and separately labelled model.
        checks = subject.validators()
        from jsonschema import Draft202012Validator
        import rc7_carriers
        registry, schemas = rc7_carriers.registry(subject.ROOT, lambda p: json.loads(p.read_text()))
        wire = Draft202012Validator(schemas['launch-env-fragment-v5'], registry=registry)
        core = json.loads((subject.ROOT/'conformance/rc7-carriers-v1/cases/fragment-file.json').read_text())
        self.assertTrue(wire.is_valid(core))
        self.assertIn('codex_settings', core)
        self.assertNotIn('config_overrides', core['credential_store'])
        model = checks['launch-fragment-model']
        leaf = checks['fragment-members.schema.json']
        ba = deepcopy(core)
        ba.update({k:deepcopy(self.data['cases'][0]['state']['fragment'][k]) for k in leaf.schema['required']})
        self.assertTrue(model.is_valid(ba))
        self.assertTrue(leaf.is_valid({k:ba[k] for k in leaf.schema['required']}))
        self.assertFalse(leaf.is_valid(ba))  # member model cannot accept a wire envelope
        self.assertFalse(wire.is_valid(ba))  # no emission until joint carrier acceptance
        self.assertFalse(model.is_valid(core))  # B-a requiredness remains explicit
        for reader, valid in [(wire, core), (model, ba)]:
            for kind in ['legacy-only', 'mixed', 'missing', 'unknown', 'old-token']:
                bad = deepcopy(valid)
                if kind in ['legacy-only', 'mixed']:
                    bad['credential_store']['config_overrides'] = {'cli_auth_credentials_store':'file'}
                    if kind == 'legacy-only': bad.pop('codex_settings')
                elif kind == 'missing': bad.pop('codex_settings')
                elif kind == 'unknown': bad['extra'] = True
                else: bad['fragment'] = 'launch-env-fragment-v4'
                with self.subTest(reader=reader.schema['$id'], kind=kind):
                    self.assertFalse(reader.is_valid(bad))
        for member in leaf.schema['required']:
            bad = deepcopy(ba); bad.pop(member)
            self.assertFalse(model.is_valid(bad))
        windows = fixtures.fixture(platform='windows-amd64')['fragment']
        self.assertTrue(model.is_valid(windows))
        self.assertFalse(wire.is_valid(windows))
        v4 = Draft202012Validator(json.loads((subject.ROOT/'schemas/v1/launch-env-fragment-v4.schema.json').read_text()), registry=registry)
        self.assertFalse(v4.is_valid(ba))
        print('cross-validation: rc7 Codex positive, B-a member/model positives; legacy/mixed/missing/unknown/old/unmerged/windows wire negatives')

    def test_path_component_and_profile_grammar(self):
        # Schema is a wire-shape filter; semantic normalization is additionally required.
        checks = subject.validators(); model = checks['launch-fragment-model']
        for windows in [False, True]:
            prefix = 'C:/' if windows else '/'
            for tail in ['a/b', 'a-b/c_d']:
                self.assertTrue(subject.absolute(prefix+tail, windows))
            for tail in ['a//b', 'a/b/', './b', '../b', 'a./b', 'a /b',
                         'con/bin', 'CoN.txt/bin', 'a/NUL.exe', 'a/lpt9']:
                with self.subTest(windows=windows, tail=tail):
                    self.assertFalse(subject.absolute(prefix+tail, windows))
        for name, expected in [('a',True), ('a'*64,True), ('a'*65,False), ('a.',False), ('a b',False)]:
            f = deepcopy(self.data['cases'][0]['state']['fragment']); f['profile']['name'] = name
            self.assertEqual(model.is_valid(f), expected, name)

    def test_transaction_input_and_generation_guard_witnesses(self):
        # Reconstruction preserves immutable inputs and requires a fresh generation.
        source = Path(subject.__file__).read_text()
        for old, replacement, id_ in [
                ('state[\'inputs\'] and same_inputs', "state['inputs']", 'repair-inputs-differ'),
                ("state['new_generation'] != state['old_generation']", 'True', 'repair-generation-reused')]:
            self.assertIn(old, source)
            ns = {'__file__':subject.__file__, '__name__':'mutant'}
            exec(compile(source.replace(old, replacement), subject.__file__, 'exec'), ns)
            case = next(c for c in self.data['transactions'] if c['id'] == id_)
            self.assertEqual(subject.transaction(case['state']), case['expected'])
            self.assertNotEqual(ns['transaction'](case['state']), case['expected'])

    def test_hook_revision_cap_and_missing_state_guards(self):
        # CAS, missing selection/root and finite reference limits all refuse.
        old, new = deepcopy(self.data['hook_upgrade'])
        model = subject.HookModel(old)
        with self.assertRaisesRegex(subject.Refusal, 'reference-missing'): model.invoke()
        ref = model.retain('/settings/hooks', 'first')
        with self.assertRaisesRegex(subject.Refusal, 'revision-conflict'):
            model.activate(ref, True, 0)
        model.activate(ref, True, 1)
        with self.assertRaisesRegex(subject.Refusal, 'revision-conflict'):
            model.activate(ref, True, 1)
        model.install(new)
        next_ref = model.retain('/settings/hooks', 'next')
        model.activate(next_ref, True, 1)
        with self.assertRaisesRegex(subject.Refusal, 'revision-conflict'):
            model.release(ref, True, 2)  # displacement incremented the old revision
        model.release(ref, True, 3)
        model.release(ref, True, 3)  # identical terminal retry unchanged
        del model.roots[model.current]
        with self.assertRaisesRegex(subject.Refusal, 'root-missing'): model.invoke()
        bad = deepcopy(old); bad['observed']['root_kind'] = 'missing'
        with self.assertRaisesRegex(subject.Refusal, 'hook-root'): model.install(bad)
        # Synthetic selected-generation keys isolate the cardinality bound. They
        # are not materializations or runtime root witnesses.
        model = subject.HookModel(old)
        for i in range(256):
            model.current = subject.sha(str(i)); model.retain('/settings/hooks', str(i))
        self.assertEqual(len(model.refs), 256)
        self.assertEqual(model.retain('/settings/hooks', '255'), model.requests['255'][1])
        model.current = subject.sha('over-cap')
        with self.assertRaisesRegex(subject.Refusal, 'reference-cap'):
            model.retain('/settings/hooks', 'over-cap')


    def test_path_budget_boundaries_and_realistic_profiles(self):
        # Complete root admission reaches a 64-byte profile and distinguishes 240/241.
        cases = {c['id']: c for c in self.data['cases']}
        for label in ['realistic-shape', 'profile-64', 'profile-64-windows', 'path-240', 'path-241']:
            case = cases[label]
            self.assertEqual(subject.decision(subject.root_check, case['state']),
                             (case['expected'], case['reason']))
        for length in [240, 241]:
            state = cases['path-'+str(length)]['state']
            receipt = state['fragment']['path_prepend']+'/.curator-profile-command-root.json'
            self.assertEqual(len(receipt.encode()), length)
        source = Path(subject.__file__).read_text()
        self.assertIn('len(path.encode()) <= 240', source)
        ns = {'__file__': subject.__file__, '__name__': 'mutant'}
        exec(compile(source.replace('len(path.encode()) <= 240', 'len(path.encode()) <= 247'),
                     subject.__file__, 'exec'), ns)
        self.assertEqual(ns['verdict'](cases['path-241']['state']), 'accept')

    def test_hook_stability_rollback_and_active_release_mutants(self):
        # Each previously surviving guard has a positive control and a semantic mutant.
        source = Path(subject.__file__).read_text()
        old, new = deepcopy(self.data['hook_upgrade'])
        def namespace(before, after):
            self.assertIn(before, source)
            ns = {'__file__': subject.__file__, '__name__': 'mutant'}
            exec(compile(source.replace(before, after), subject.__file__, 'exec'), ns)
            return ns
        # Fault injection makes a normally pure naming invariant falsifiable.
        for fn, naming, refused in [
                (subject.hook_upgrade, subject.__dict__, True),
                (lambda states: mutated['hook_upgrade'](states), None, False)]:
            if naming is None:
                naming = mutated
            original = naming['gateway_path']
            with patch.dict(naming, gateway_path=lambda state, command:
                            original(state, command)+'/'+state['trusted']['binding']['generation']):
                if refused:
                    with self.assertRaisesRegex(subject.Refusal, 'hook-stable-path'):
                        fn([old, new])
                else:
                    fn([old, new])
            if refused:
                mutated = namespace("require(gateway_path(states[0], 'a2a') == gateway_path(states[1], 'a2a'), 'hook-stable-path')", 'pass')
        for cls, expected in [(subject.HookModel, True),
                (namespace('self.rollback.add(previous)', 'pass')['HookModel'], False)]:
            model = cls(old); first = model.retain('/settings/hooks', 'first')
            model.activate(first, True, 1); model.install(new)
            second = model.retain('/settings/hooks', 'second'); model.activate(second, True, 1)
            self.assertEqual(first in model.rollback, expected)
            if expected:
                model.restore_rollback(first, True, model.revisions[first])
                self.assertEqual(model.invoke(), old['trusted']['binding']['generation'])
            else:
                with self.assertRaisesRegex(cls.restore_rollback.__globals__['Refusal'], 'rollback-missing'):
                    model.restore_rollback(first, True, model.revisions[first])
        mutant = namespace('settings_removed and reference not in self.active.values()', 'settings_removed')
        for cls, refused in [(subject.HookModel, True), (mutant['HookModel'], False)]:
            model = cls(old); ref = model.retain('/settings/hooks', 'active')
            model.activate(ref, True, 1)
            if refused:
                with self.assertRaisesRegex(subject.Refusal, 'settings-unconfirmed'):
                    model.release(ref, True, model.revisions[ref])
            else:
                model.release(ref, True, model.revisions[ref])
                self.assertNotIn(ref, model.refs)

    def test_valid_json_tamper_fixture_custody(self):
        # Replacing a byte-pin tamper with invalid JSON cannot preserve the corpus claim.
        data = deepcopy(self.data)
        case = next(c for c in data['cases'] if c['id'] == 'tampered-marker')
        case['state']['observed']['marker'] = '{'
        with self.assertRaises(json.JSONDecodeError): subject.validate_data(data)


if __name__ == '__main__':
    unittest.main()
