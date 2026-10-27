"""Closed companion data and bounded witnesses; no launcher or filesystem qualification."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / 'conformance/profile-command-path'
SCHEMAS = ROOT / 'schemas/profile-command-path-v1'
UNIX_DEFAULT_PATH = ('/usr/bin', '/bin', '/usr/sbin', '/sbin')


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(text):
    return 'sha256:' + hashlib.sha256(text.encode('utf-8')).hexdigest()


def merge(base, changes):
    result = deepcopy(base)
    for key, value in changes.items():
        result[key] = merge(result[key], value) if isinstance(value, dict) else deepcopy(value)
    return result


def metadata_safe(value, kind='executable'):
    # The semantic filesystem examples are POSIX. Windows shape validity below
    # does not establish native descriptor interpretation or ACL enforcement.
    if value['platform'] != 'posix' or value['owner'] != 'uid:1000':
        return False
    if kind == 'symlink':
        return True  # Link mutation is governed by the checked parent directory.
    required = 0o400 if kind == 'receipt' else 0o500
    return value['mode'] & 0o7022 == 0 and value['mode'] & required == required


def root_violations(data, receipt_validator):
    admitted, observed = data['trusted'], data['observed']
    receipt = data['receipt']
    if not receipt_validator.is_valid(receipt):
        return ['receipt-shape']
    if receipt['binding'] != admitted['binding']:
        return ['receipt-binding']
    if receipt != admitted['receipt']:
        return ['receipt-authority']
    if data['routing'] != 'exclusive':
        return ['routing-unproven']
    root = receipt['root']
    if observed['root_status'] != 'readable':
        return ['root-' + observed['root_status']]
    if observed['root_metadata'] != root['metadata'] or not metadata_safe(observed['root_metadata']):
        return ['root-metadata']
    if observed['root_kind'] != 'directory':
        return ['root-type']
    if (observed['receipt_kind'] != 'regular'
            or observed['receipt_metadata'] != admitted['receipt_metadata']
            or not metadata_safe(observed['receipt_metadata'], 'receipt')):
        return ['receipt-boundary']
    if observed['root_entries'] != ['.curator-profile-command-root.json'] + [c['name'] for c in receipt['commands']]:
        return ['root-inventory']
    for command in receipt['commands']:
        chain = command['chain']
        if chain[0]['path'] != root['path'] + '/' + command['name']:
            return ['shim-entry']
        seen = set()
        for index, hop in enumerate(chain):
            path = hop['path']
            if path in seen or not any(PurePosixPath(path).is_relative_to(PurePosixPath(b))
                                       for b in admitted['boundaries']):
                return ['chain-confinement']
            seen.add(path)
            actual = observed['objects'].get(path)
            if actual is None or not actual['readable']:
                return ['chain-unreadable']
            if actual['metadata'] != hop['metadata'] or not metadata_safe(actual['metadata'], hop['kind']):
                return ['chain-metadata']
            if actual['kind'] != hop['kind'] or actual['links'] != 1:
                return ['chain-type']
            if digest(actual['bytes']) != hop['sha256']:
                return ['chain-digest']
            final = index == len(chain) - 1
            if final:
                if hop['kind'] != 'executable' or hop['target'] is not None:
                    return ['chain-terminal']
            else:
                target = chain[index + 1]['path']
                if hop['kind'] not in ('symlink', 'forwarder'):
                    return ['chain-type']
                # Synthetic corpus forwarder format, not a product shell grammar.
                if hop['kind'] == 'forwarder' and not (
                        actual['bytes'].startswith('FIXTURE-FORWARD/1\n')
                        and actual['bytes'].endswith('\n')):
                    return ['chain-format']
                decoded = (actual['bytes'] if hop['kind'] == 'symlink' else
                           actual['bytes'].removeprefix('FIXTURE-FORWARD/1\n').removesuffix('\n'))
                if hop['target'] != target or decoded != target:
                    return ['chain-target']
    return []


def admit_path(data, protected, entries=None):
    kept, issues, exclusions = [], [], []
    seen_paths = set(protected)
    seen_ids = {data['path_facts'][p]['identity'] for p in protected}
    root_ids = set(data['trusted']['profile_root_ids'])
    for entry in data['base_path'] if entries is None else entries:
        fact = data['path_facts'].get(entry)
        predicate = None
        if entry == '':
            predicate = 'empty'
        elif not posixpath.isabs(entry):
            predicate = 'relative'
        elif any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in entry):
            predicate = 'control-characters'
        elif any(part in ('.', '..') for part in entry.split('/')):
            predicate = 'non-canonical'
        elif fact is None or not fact['readable'] or fact['kind'] != 'directory':
            predicate = 'unreadable'
        elif fact['identity'] in root_ids:
            exclusions.append(entry)
            continue
        elif fact['mode'] & 0o002:
            predicate = 'world-writable'
        elif posixpath.normpath(entry) in seen_paths:
            predicate = 'duplicate'
        elif fact['identity'] in seen_ids:
            predicate = 'alias'
        if predicate:
            action = ('refuse' if data['policy'] == 'managed' and
                      predicate in ('unreadable', 'world-writable') else 'drop')
            issues.append({'entry': entry, 'predicate': predicate, 'action': action})
        else:
            kept.append(entry)
            seen_paths.add(posixpath.normpath(entry))
            seen_ids.add(fact['identity'])
    return kept, issues, exclusions


def decision(data, receipt_validator):
    launch = data['launch']
    availability, reason = 'active', None
    if not launch['exports']:
        availability = 'none'
    elif launch['route'] == 'hosted' and not launch['hosted_carrier']:
        availability, reason = 'empty', 'hosted-carrier-unavailable'
    elif launch['current_profile'] != data['trusted']['binding']['profile']:
        availability, reason = 'empty', 'slice-a-non-current'
    violations = root_violations(data, receipt_validator) if availability == 'active' else []
    protected = data['protected_tools']
    if protected and not metadata_safe(data['protected_metadata']):
        violations.append('protected-boundary')
    root = data['trusted']['receipt']['root']['path'] if availability == 'active' else None
    # Known roots are excluded independently; selected root enters only here.
    kept, admission, exclusions = admit_path(data, protected)
    default_path_used = not kept and not any(i['action'] == 'refuse' for i in admission)
    if default_path_used:
        kept, default_issues, default_exclusions = admit_path(data, protected, UNIX_DEFAULT_PATH)
        admission.extend(default_issues)
        exclusions.extend(default_exclusions)
    if any(i['action'] == 'refuse' for i in admission):
        violations.append('base-path-unsafe')
    path = protected + ([root] if root else []) + kept
    if not path and not violations:
        violations.append('launch_path_unavailable')
    command = None
    if availability == 'active':
        final = data['trusted']['receipt']['commands'][0]['chain'][-1]
        command = {'path': final['path'], 'sha256': final['sha256']}
    return {'violations': violations, 'starts': int(not violations), 'availability': availability,
            'reason': reason, 'path_prepend': root, 'path': path,
            'path_value': ':'.join(path) if path else None,
            'command': command, 'binding': data['trusted']['binding'], 'admission': admission,
            'profile_root_exclusions': exclusions,
            'default_path_used': default_path_used,
            'diagnostic_lines': int(bool(reason)) + int(bool(admission or exclusions or default_path_used)),
            'final_path_claim': launch['route'] == 'native' or launch['hosted_carrier'],
            'live_preimage': 'unchanged', 'fallbacks': 0}


def witness_violations(expected, supplied):
    if supplied is None:
        return ['missing-child-witness']
    failures = []
    for key, label in [('path', 'child-path'), ('path_value', 'child-path-value'),
                       ('command', 'child-command'), ('binding', 'child-binding')]:
        if supplied[key] != expected[key]:
            failures.append(label)
    return failures


def check_cases(base, cases, validator):
    for case in cases:
        result = decision(merge(base, case['changes']), validator)
        for key, expected in case['expected'].items():
            if result[key] != expected:
                raise ValueError(case['name'] + ':' + key)


def state_violations(state, expected, base, validator):
    if not validator.is_valid(state):
        return ['state-shape']
    fields = ['path', 'path_value', 'binding', 'availability', 'reason', 'admission',
              'profile_root_exclusions']
    failures = ['state-' + key for key in fields if state[key] != expected[key]]
    if state['fragment_sha256'] != digest('synthetic complete fragment bytes'):
        failures.append('state-fragment')
    receipt = base['receipt']
    root = receipt['root'] if expected['availability'] == 'active' else None
    receipt_hash = digest(json.dumps(receipt, indent=2) + '\n') if root else None
    if state['root'] != root or state['receipt_sha256'] != receipt_hash:
        failures.append('state-receipt')
    return failures


class ProfileCommandPathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = load(CORPUS / 'baseline.json')
        cls.cases = load(CORPUS / 'cases.json')
        cls.schemas = {p.name: load(p) for p in SCHEMAS.glob('*.schema.json')}
        cls.validators = {n: Draft202012Validator(s) for n, s in cls.schemas.items()}
        cls.receipt_validator = cls.validators['root-receipt.schema.json']

    # Closed receipt/state shapes, including required fields, unknown members,
    # exact-end digests and native metadata variants. No native ACL is queried.
    def test_closed_schemas(self):
        for schema in self.schemas.values():
            Draft202012Validator.check_schema(schema)
        for case in load(CORPUS / 'schema-cases.json'):
            with self.subTest(case=case['name']):
                self.assertEqual(self.validators[case['schema']].is_valid(case['document']), case['valid'])

    # Pins explicit paired outcomes for B1/B2, G1–G4 and the former integrity
    # refusals. These are independent literals, never generated by decision().
    def test_published_cases(self):
        names = {c['name'] for c in self.cases}
        self.assertEqual(len(names), len(self.cases))
        check_cases(self.base, self.cases, self.receipt_validator)
        for name in ['current-native', 'no-export', 'non-current', 'hosted-without-carrier',
                     'hosted-with-carrier', 'interactive-drops', 'managed-drops',
                     'managed-refuses-world-writable', 'managed-refuses-unreadable',
                     'missing-root', 'tampered-root', 'stale-lock', 'foreign-root-excluded']:
            self.assertIn(name, names)
        for case in self.cases:
            with self.subTest(case=case['name']):
                data = merge(self.base, case['changes'])
                result = decision(data, self.receipt_validator)
                for key, value in case['expected'].items():
                    self.assertEqual(result[key], value, key)
                control = next(c for c in self.cases if c['name'] == case['positive_control'])
                self.assertEqual(control['expected']['starts'], 1)

    # Baseline lock and plan identities are independently recomputed from the
    # existing admitted-plan fixture; this does not re-qualify its source pins.
    def test_baseline_lock_binding(self):
        from assurance import ccj1_sha256
        source = load(CORPUS.parent / 'profile-skill-plan-v1/baseline.json')
        self.assertEqual(self.base['trusted']['binding']['lock_sha256'], ccj1_sha256(source['lock']))
        self.assertEqual(self.base['trusted']['binding']['plan_sha256'], ccj1_sha256(source['lock']['skill_plan']))

    # Persisted native-state data must bind the exact fragment and receipt bytes
    # and effective PATH, not just pass the closed shape. No real file is written.
    def test_native_state_bindings(self):
        state = load(CORPUS / 'launcher-state.json')
        expected = decision(self.base, self.receipt_validator)
        validator = self.validators['launcher-state.schema.json']
        self.assertEqual(state_violations(state, expected, self.base, validator), [])
        for changes, failure in [({'path_value': '/ambient'}, 'state-path_value'),
                                 ({'fragment_sha256': digest('other')}, 'state-fragment'),
                                 ({'receipt_sha256': digest('other')}, 'state-receipt'),
                                 ({'binding': {'lock_sha256': digest('other')}}, 'state-binding'),
                                 ({'binding': {'plan_sha256': digest('other')}}, 'state-binding'),
                                 ({'binding': {'generation': 'other'}}, 'state-binding')]:
            self.assertEqual(state_violations(merge(state, changes), expected, self.base, validator), [failure])
        for name in ['no-export', 'non-current', 'hosted-without-carrier']:
            case = next(c for c in self.cases if c['name'] == name)
            outcome = decision(merge(self.base, case['changes']), self.receipt_validator)
            unavailable = deepcopy(state)
            for key in ['path', 'path_value', 'binding', 'availability', 'reason', 'admission',
                        'profile_root_exclusions']:
                unavailable[key] = outcome[key]
            unavailable.update(root=None, receipt_sha256=None)
            self.assertEqual(state_violations(unavailable, outcome, self.base, validator), [])

    # Regression: unavailable commands still need a nonempty safe PATH. Fixed
    # defaults are admitted, or a distinct PATH-safety refusal prevents start.
    def test_nonempty_path_regression(self):
        defaults = ['/usr/bin', '/bin', '/usr/sbin', '/sbin']
        for launch in [{'exports': False}, {'current_profile': 'other'}]:
            for usable in [True, False]:
                with self.subTest(launch=launch, defaults_usable=usable):
                    data = merge(self.base, {'launch': launch, 'base_path': ['', 'relative']})
                    for entry in defaults:
                        data['path_facts'][entry] = {
                            'identity': entry, 'readable': usable, 'kind': 'directory', 'mode': 0o755}
                    result = decision(data, self.receipt_validator)
                    self.assertEqual(result['starts'], int(usable))
                    self.assertEqual(result['violations'], [] if usable else ['launch_path_unavailable'])
                    if usable:
                        self.assertEqual(result['path'], defaults)
                        self.assertEqual(result['path_value'], ':'.join(defaults))

    # Regression: benign spelling drops compose with the mandatory state shape
    # for both interactive and managed launches, without lexical rewriting.
    def test_path_state_composition_regression(self):
        safe = '/fixture/base-safe'
        bad = ['/fixture/base/../bin', '/fixture/./bin', '/fixture/base\nname',
               '/fixture/base\x7fname', '/fixture/base\x85name']
        for policy in ['interactive-native', 'managed']:
            data = merge(self.base, {'launch': {'exports': False}, 'policy': policy,
                                     'base_path': [safe] + bad})
            for entry in [safe] + bad:
                data['path_facts'][entry] = {
                    'identity': entry, 'readable': True, 'kind': 'directory', 'mode': 0o755}
            result = decision(data, self.receipt_validator)
            self.assertEqual(result['starts'], 1)
            self.assertEqual(result['path'], [safe])
            self.assertEqual(result['admission'], [
                {'entry': entry, 'predicate': ('non-canonical' if i < 2 else 'control-characters'),
                 'action': 'drop'} for i, entry in enumerate(bad)])
            state = load(CORPUS / 'launcher-state.json')
            for field in ['path', 'path_value', 'binding', 'availability', 'reason', 'admission',
                          'profile_root_exclusions']:
                state[field] = result[field]
            state.update(root=None, receipt_sha256=None)
            self.assertEqual(state_violations(state, result, data,
                             self.validators['launcher-state.schema.json']), [])

    # Each new successful policy row passes unchanged through PATH serialization,
    # supplied-child comparison and mandatory state validation. Refusals emit no
    # successful state; these abstract checks do not observe product writes.
    def test_composed_path_and_state_cases(self):
        for case in self.cases:
            if 'compose_state' not in case:
                continue
            with self.subTest(case=case['name']):
                data = merge(self.base, case['changes'])
                result = decision(data, self.receipt_validator)
                self.assertEqual(bool(result['starts']), case['compose_state'])
                if not case['compose_state']:
                    self.assertEqual(result['starts'], 0)
                    continue
                self.assertGreater(len(result['path']), 0)
                self.assertTrue(result['path_value'])
                self.assertEqual(result['path_value'].split(':'), result['path'])
                self.assertEqual(witness_violations(result, result), [])
                state = load(CORPUS / 'launcher-state.json')
                for field in ['path', 'path_value', 'binding', 'availability', 'reason', 'admission',
                              'profile_root_exclusions']:
                    state[field] = result[field]
                if result['availability'] != 'active':
                    state.update(root=None, receipt_sha256=None)
                self.assertEqual(state_violations(state, result, data,
                                 self.validators['launcher-state.schema.json']), [])

    # A lookup-only POSIX control reproduces empty-PATH CWD search; retained or
    # fallback absolute PATHs cannot find the private fixture. Never execute it.
    @unittest.skipUnless(os.name == 'posix' and Path('/bin/sh').is_file(), 'POSIX shell lookup only')
    def test_default_path_does_not_search_cwd(self):
        with tempfile.TemporaryDirectory(prefix='profile-path-') as directory:
            name = 'lookup_' + Path(directory).name
            probe = Path(directory) / name
            probe.write_text('#!/bin/sh\nexit 99\n', encoding='utf-8')
            probe.chmod(0o700)
            def lookup(path):
                return subprocess.run(['/bin/sh', '-c', 'command -v "$1"', 'sh', name],
                                      cwd=directory, env={'PATH': path}, capture_output=True, text=True)
            unsafe = lookup('')
            self.assertEqual(unsafe.returncode, 0)
            self.assertIn(name, unsafe.stdout)
            for control in ['no-export-default-path', 'non-current-default-path', 'no-export']:
                case = next(c for c in self.cases if c['name'] == control)
                result = decision(merge(self.base, case['changes']), self.receipt_validator)
                safe = lookup(result['path_value'])
                self.assertEqual(safe.returncode, 1, safe.stderr)
                self.assertEqual(safe.stdout, '')

    # Actual byte changes are detected against separately pinned artifact
    # hashes. Owner/mode, object identity, shim chain and confinement are isolated.
    def test_root_verifier_controls(self):
        self.assertEqual(root_violations(self.base, self.receipt_validator), [])
        root = self.base['receipt']['root']['path']
        artifact = self.base['receipt']['commands'][0]['chain'][-1]['path']
        plants = [
            ({'observed': {'root_metadata': {'owner': 'uid:2000'}}}, 'root-metadata'),
            ({'observed': {'root_metadata': {'mode': 0o777}}}, 'root-metadata'),
            ({'observed': {'root_metadata': {'object_id': 'replaced'}}}, 'root-metadata'),
            ({'observed': {'root_kind': 'symlink'}}, 'root-type'),
            ({'observed': {'objects': {artifact: {'bytes': 'tampered'}}}}, 'chain-digest'),
            ({'observed': {'objects': {artifact: {'metadata': {'object_id': 'other'}}}}}, 'chain-metadata'),
            ({'observed': {'objects': {artifact: {'links': 2}}}}, 'chain-type'),
            ({'observed': {'objects': {root + '/memory': {'readable': False}}}}, 'chain-unreadable'),
        ]
        for changes, wanted in plants:
            with self.subTest(wanted=wanted, changes=changes):
                self.assertEqual(root_violations(merge(self.base, changes), self.receipt_validator), [wanted])
        # Re-pin both abstract trusted record and receipt to isolate the chain
        # relation from digest authenticity; outside-root lookalikes still fail.
        for kind in ['confinement', 'target', 'terminal', 'type']:
            data = deepcopy(self.base)
            chain = data['receipt']['commands'][0]['chain']
            if kind == 'confinement':
                chain[1]['path'] = '/fixture/cache-foreign/sample'
                chain[0]['target'] = chain[1]['path']
                chain[0]['sha256'] = digest(chain[1]['path'])
                data['observed']['objects'][root + '/memory']['bytes'] = chain[1]['path']
            elif kind == 'target':
                chain[0]['target'] = '/fixture/cache/other'
            elif kind == 'type':
                chain[0]['kind'] = 'executable'
                chain[0]['metadata'] = deepcopy(chain[1]['metadata'])
                data['observed']['objects'][root + '/memory'].update(
                    kind='executable', metadata=deepcopy(chain[1]['metadata']))
            else:
                chain[-1]['target'] = '/fixture/cache/other'
            data['trusted']['receipt'] = deepcopy(data['receipt'])
            self.assertEqual(root_violations(data, self.receipt_validator), ['chain-' + kind])
        # The synthetic forwarder positive and unknown-format negative exercise
        # decoding separately from a mere bytes/digest mismatch.
        data = deepcopy(self.base)
        hop = data['receipt']['commands'][0]['chain'][0]
        actual = data['observed']['objects'][hop['path']]
        for content, wanted in [('FIXTURE-FORWARD/1\n' + artifact + '\n', []),
                                (artifact, ['chain-format'])]:
            hop.update(kind='forwarder', metadata=deepcopy(self.base['receipt']['root']['metadata']),
                       sha256=digest(content))
            actual.update(kind='forwarder', metadata=deepcopy(hop['metadata']), bytes=content)
            data['trusted']['receipt'] = deepcopy(data['receipt'])
            self.assertEqual(root_violations(data, self.receipt_validator), wanted)

    # Every active success needs all three correlated child witnesses; omission,
    # order, path/digest, lock binding or late ambient substitution is detected.
    def test_child_witness_controls(self):
        expected = decision(self.base, self.receipt_validator)
        self.assertEqual(witness_violations(expected, expected), [])
        plants = [({'path': expected['path'][1:]}, 'child-path'),
                  ({'path_value': '/ambient/bin'}, 'child-path-value'),
                  ({'command': {'path': '/foreign/sample'}}, 'child-command'),
                  ({'command': {'sha256': digest('foreign')}}, 'child-command'),
                  ({'binding': {'lock_sha256': digest('stale')}}, 'child-binding')]
        for changes, wanted in plants:
            self.assertEqual(witness_violations(expected, merge(expected, changes)), [wanted])
        self.assertEqual(witness_violations(expected, None), ['missing-child-witness'])
        for route in ['native', 'hosted']:
            with self.subTest(route=route):
                data = merge(self.base, {'launch': {'route': route, 'hosted_carrier': True}})
                result = decision(data, self.receipt_validator)
                self.assertEqual(result['starts'], 1)
                self.assertEqual(witness_violations(result, result), [])
                self.assertEqual(witness_violations(result, merge(result, {'path': result['path'][1:]})),
                                 ['child-path'])

    # Bounded checker mutants must fail the intended corpus assertions, rather
    # than merely crashing. Positive controls exclude an always-refuse checker.
    def test_policy_mutants(self):
        original = decision
        for name, field, wrong in [('non-current', 'starts', 0),
                                   ('hosted-without-carrier', 'starts', 0),
                                   ('no-export', 'path_prepend', '/foreign/root'),
                                   ('managed-refuses-world-writable', 'starts', 1),
                                   ('no-export-no-admitted-path', 'starts', 1),
                                   ('interactive-drop-parent-segment', 'path',
                                    ['/fixture/base/../bin', '/fixture/base-safe'])]:
            case = next(c for c in self.cases if c['name'] == name)
            selected = merge(self.base, case['changes'])
            def mutant(data, validator):
                actual = original(data, validator)
                if data == selected:
                    actual[field] = wrong
                return actual
            with patch(__name__ + '.decision', mutant):
                with self.assertRaisesRegex(ValueError, name + ':' + field):
                    check_cases(self.base, self.cases, self.receipt_validator)


if __name__ == '__main__':
    unittest.main()
