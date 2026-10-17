"""Executable A1 specification vectors; no native runtime qualification."""
from __future__ import annotations

import copy
import json
import unittest
from unittest.mock import patch

import workspace_trust as trust
from test_validate import validate

CORPUS = trust.ROOT / 'conformance/workspace-trust-v1'
SCHEMA = json.loads((trust.ROOT / 'schemas/workspace-trust-v1/workspace-trust-record-v1.schema.json').read_text())
VECTORS = json.loads((CORPUS / 'vectors.json').read_text())


class WorkspaceTrustTests(unittest.TestCase):
    # The actual repository publication entry executes schema and transition
    # cases. This proves corpus consistency, not Curator implementation support.
    def test_publication_entry(self):
        self.assertEqual(trust.check_corpus(), (61, 72))
        validate.validate_workspace_trust()

    # Plant one wrong cross-environment verdict through the real publication
    # entry; rejection must identify that exact vector, not a setup failure.
    def test_publication_entry_rejects_wrong_scope_verdict(self):
        original = trust.Path.read_text

        def planted(path, *args, **kwargs):
            text = original(path, *args, **kwargs)
            if path == CORPUS / 'vectors.json':
                vectors = json.loads(text)
                vector = next(v for v in vectors if v['name'] == 'explicit-scope-and-list')
                vector['steps'][2]['expected']['listed'] = ['explicit']
                return json.dumps(vectors)
            return text

        with patch.object(trust.Path, 'read_text', new=planted):
            with self.assertRaisesRegex(validate.ValidationFailure, 'explicit-scope-and-list step 2'):
                validate.validate_workspace_trust()

    # Every private-record required field and semantic counterexample has the
    # published verdict, with valid neighbors. No filesystem claim is made.
    def test_schema_cases(self):
        cases = json.loads((CORPUS / 'schema-cases.json').read_text())
        self.assertEqual(len(cases), 61)
        self.assertTrue(any(c['expected'] is None for c in cases))
        self.assertTrue(any(c['expected'] is not None for c in cases))
        for case in cases:
            with self.subTest(case=case['name']):
                self.assertEqual(trust.record_error(case['instance'], SCHEMA), case['expected'])

    # Explicit removal after identity lapse retains both transitions and ends
    # revoked; no active grant or rewritten consent provenance survives.
    def test_remove_after_lapse_retains_history(self):
        vector = next(v for v in VECTORS if v['name'] == 'lapse-then-remove')
        state = trust.run_vector(vector, SCHEMA)
        record = state['records'][0]
        self.assertEqual(record['state']['status'], 'revoked')
        self.assertEqual([s['status'] for s in record['state_history']], ['active', 'lapsed'])
        self.assertEqual(record['event'], 'explicit-grant')
        self.assertEqual(record['reason'], 'Inspect sample workspace')

    # Private consent cannot be inserted into published portable envelopes;
    # positive controls come from those same released full-envelope fixtures.
    def test_portable_carriers_reject_private_ledger(self):
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource
        resources = []
        for path in (trust.ROOT / 'schemas/v1').glob('*.schema.json'):
            schema = json.loads(path.read_text())
            resources.append((schema['$id'], Resource.from_contents(schema)))
        registry = Registry().with_resources(resources)
        record = json.loads((CORPUS / 'schema-cases.json').read_text())[0]['instance']
        for name in ('agent-context-v1', 'context-lock-v2', 'agent-environment-marker-v3', 'launch-env-fragment-v3'):
            schema = json.loads((trust.ROOT / 'schemas/v1' / (name + '.schema.json')).read_text())
            validator = Draft202012Validator(schema, registry=registry)
            fixtures = sorted((trust.ROOT / 'conformance/v1/schema-cases' / name).glob('valid*.json'))
            self.assertTrue(fixtures, name)
            value = json.loads(fixtures[0].read_text())
            self.assertTrue(validator.is_valid(value), name)
            for field in ('workspace_trust', 'trust_ledger'):
                invalid = copy.deepcopy(value)
                invalid[field] = [record]
                self.assertFalse(validator.is_valid(invalid), (name, field))


def vector_test(vector):
    # Each vector checks its named positive/negative sequence against an
    # independent published verdict, including post-refusal grants/references.
    def test(self):
        state = {'records': [], 'bindings': [], 'transactions': [], 'pending_cleanup': False}
        for index, item in enumerate(vector['steps']):
            before = copy.deepcopy(state)
            state, actual = trust.step(state, item['action'])
            with self.subTest(step=index):
                self.assertEqual(actual, item['expected'], vector['name'])
                for record in state['records']:
                    self.assertIsNone(trust.record_error(record, SCHEMA))
                if item['action']['op'] == 'list':
                    self.assertEqual(state, before, 'list must be read-only')
                if actual['diagnostic'] in {
                    'workspace_trust_binding_failed', 'workspace_trust_symlink',
                    'workspace_trust_repository_unverifiable', 'workspace_trust_environment_unsupported',
                    'workspace_trust_path_invalid', 'workspace_trust_path_missing', 'workspace_trust_path_kind',
                }:
                    self.assertEqual(state, before, 'refusal must preserve private state')
    return test


for vector in VECTORS:
    setattr(WorkspaceTrustTests, 'test_vector_' + vector['name'].replace('-', '_'), vector_test(vector))


if __name__ == '__main__':
    unittest.main()
