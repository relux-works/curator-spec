"""Specification-data controls; no manager execution or vendor qualification."""
import copy
import inspect
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator, SchemaError
from referencing import Registry, Resource
from referencing.exceptions import Unresolvable

import codex_seed_c as seed
import validate

ROOT = Path(__file__).resolve().parents[1]


class CodexSeedCTests(unittest.TestCase):
    def setUp(self):
        self.cases = validate.load_json(
            ROOT / 'conformance/codex-seed-c-v1/cases.json')

    # The publication gate rejects retained trust/MCP, unrelated-setting loss,
    # legacy repair writes and wrong diagnostics/records against nearby controls.
    # These are specification witnesses, not filesystem-preservation evidence.
    def test_expected_outcome_controls(self):
        for case in self.cases['cases']:
            with self.subTest(case=case['name']):
                seed.check_case(case)
                bad = copy.deepcopy(case)
                bad['expected']['seed_config'] = 'model = "wrong"\n'
                with self.assertRaisesRegex(ValueError, 'seed configuration'):
                    seed.check_case(bad)
                for key, wrong in (
                    ('writes', ['config.toml']), ('record', None),
                    ('diagnostic', 'wrong'), ('names', ['wrong']),
                ):
                    bad = copy.deepcopy(case)
                    if bad['expected'][key] == wrong:
                        wrong = [] if key == 'writes' else {'wrong': True}
                    bad['expected'][key] = wrong
                    with self.assertRaisesRegex(ValueError, key):
                        seed.check_case(bad)

    # Each narrowed oracle must be caught by the committed corpus; success
    # cannot be obtained by silently retaining projects, erasing other settings,
    # rewriting a legacy home, changing its marker or losing MCP diagnostics.
    def test_narrowing_controls(self):
        controls = {
            'retain-projects': lambda result: result['config'].update(
                {'projects': {'/work/synthetic-retained': {'trust_level': 'trusted'}}}),
            'retain-mcp': lambda result: result['config'].update(
                {'mcp_servers': {'example': {'command': 'synthetic-server'}}}),
            'erase-model': lambda result: result['config'].pop('model', None),
            'repair-refresh': lambda result: result.update(writes=['config.toml'])
                if not result['writes'] and result['config'] is not None else None,
            'relabel-record': lambda result: result['record'].update(revision='C')
                if not result['writes'] and result['record']
                and result['record']['revision'] in ('A', 'B') else None,
            'drop-mcp-warning': lambda result: result.update(diagnostic=None, names=[]),
        }
        original = seed.outcome
        for name, mutate in controls.items():
            def narrowed(case, mutate=mutate):
                result = original(case)
                mutate(result)
                return result
            pattern = {
                'repair-refresh': 'c-repair-preserves-pre-rule: writes differs',
                'relabel-record': 'c-repair-preserves-a: record differs',
                'drop-mcp-warning': 'c-strips-trust-and-mcp: diagnostic differs',
            }.get(name, 'seed configuration differs')
            with self.subTest(control=name), patch.object(seed, 'outcome', narrowed):
                with self.assertRaisesRegex(ValueError, pattern):
                    seed.check_corpus(ROOT)

    # The committed filtered positive preserves every unrelated decoded value.
    # Altering a top-level or deeply nested array element must fail that exact
    # production preservation assertion, rather than an import or setup check.
    # This data check does not establish real serializer determinism.
    def test_nested_array_preservation_controls(self):
        name = 'c-preserves-nested-tables-and-arrays'
        case = next(c for c in self.cases['cases'] if c['name'] == name)
        seed.check_case(case)
        validate.validate_codex_seed_c()
        original = seed.outcome
        for path in (('fallback_models', 1),
                     ('profiles', 'example', 'routes', 0, 'args', 1)):
            def narrowed(case, path=path):
                result = original(case)
                if case['name'] == name:
                    value = result['config']
                    for member in path[:-1]:
                        value = value[member]
                    value[path[-1]] = 'mutated-array-element'
                return result
            with self.subTest(path=path), patch.object(seed, 'outcome', narrowed):
                with self.assertRaisesRegex(
                    validate.ValidationFailure,
                    name + ': seed configuration differs',
                ):
                    validate.validate_codex_seed_c()

    # The complete inherited node-source positive resolves through the public
    # registry; malformed source refs reject beside the valid synthetic source.
    # No private aliases, protected state or per-home substitution are involved.
    def test_full_node_source_carrier(self):
        resources = []
        for path in sorted((ROOT / 'schemas').rglob('*.schema.json')):
            value = seed.load(path)
            resources.append((value['$id'], Resource.from_contents(value)))
        registry = Registry().with_resources(resources)
        marker = seed.load(ROOT / 'conformance/local-setup-token-v1/controls.json')[
            'agent-environment-marker-v6']
        predecessor = seed.load(ROOT / 'schemas/local-setup-token-v1/agent-environment-marker-v6.schema.json')
        self.assertTrue(Draft202012Validator(predecessor, registry=registry).is_valid(marker))
        marker['version'] = 7
        marker['codex_seed_record'] = dict(revision='C', native_mcp_servers=[])
        validator = Draft202012Validator(seed.load_schema(ROOT), registry=registry)
        self.assertTrue(validator.is_valid(marker))
        marker['credential_source']['source']['source_ref'] = 'local:invalid'
        self.assertFalse(validator.is_valid(marker))

    # Full marker 7 admits C and retained A/B records; old carriers still
    # reject C. Closed records, versions and unrelated v6 fields stay enforced.
    def test_marker_schema_and_narrowing(self):
        seed.check_markers(ROOT)
        schema = seed.load_schema(ROOT)
        for mutate in (
            lambda s: s['properties']['codex_seed_record']['properties']['revision'].update(enum=['A', 'B', 'C', 'D']),
            lambda s: s['properties']['codex_seed_record'].update(additionalProperties=True),
            lambda s: s['properties']['version'].update(const=6),
        ):
            bad = copy.deepcopy(schema)
            mutate(bad)
            with patch.object(seed, 'load_schema', return_value=bad):
                with self.assertRaisesRegex(ValueError, 'marker successor'):
                    seed.check_markers(ROOT)

    # The production dispatcher must traverse the complete inherited node
    # branch: restoring the old relative reference raises Unresolvable.
    def test_production_old_node_reference_is_unresolvable(self):
        validate.validate_codex_seed_c()
        schema = seed.load_schema(ROOT)
        schema['properties']['credential_source']['oneOf'][1]['properties']['source'][
            '$ref'] = 'node-source-v1.schema.json'
        with patch.object(seed, 'load_schema', return_value=schema):
            with self.assertRaisesRegex(Unresolvable, 'node-source-v1.schema.json'):
                validate.validate_codex_seed_c()

    # The invalid source_ref and node-seed controls are executable, not just
    # declared data: accepting either exact violation must fail the checker.
    def test_production_node_source_rejection_narrowing(self):
        validate.validate_codex_seed_c()
        original = Draft202012Validator.is_valid
        for violation in ('source_ref', 'seeds'):
            def admit_invalid(validator, instance, *args, **kwargs):
                if isinstance(instance, dict):
                    source = instance.get('credential_source', {}).get('source', {})
                    if (violation == 'source_ref' and source.get('source_ref') == 'local:invalid'
                            or violation == 'seeds' and source and instance.get('seeds')):
                        return True
                return original(validator, instance, *args, **kwargs)

            with self.subTest(violation=violation), patch.object(
                Draft202012Validator, 'is_valid', admit_invalid,
            ):
                with self.assertRaisesRegex(
                    validate.ValidationFailure,
                    'marker successor admits invalid node-source control',
                ):
                    validate.validate_codex_seed_c()

    # The relocation exception cannot admit other predecessor changes, and
    # malformed schema references still fail the schema's own meta-validation.
    def test_marker_predecessor_pin_and_malformed_schema(self):
        schema = seed.load_schema(ROOT)
        schema['properties']['credential_source']['oneOf'][1]['properties'][
            'source_generation']['maximum'] -= 1
        with patch.object(seed, 'load_schema', return_value=schema):
            with self.assertRaisesRegex(ValueError, 'marker successor changes more'):
                seed.check_markers(ROOT)
        schema = seed.load_schema(ROOT)
        schema['properties']['codex_settings']['$ref'] = None
        with patch.object(seed, 'load_schema', return_value=schema):
            with self.assertRaises(SchemaError):
                seed.check_markers(ROOT)

    # Removing a witness cannot silently weaken the gate, and production
    # validation must dispatch it rather than leaving it as an optional test.
    def test_inventory_and_dispatch(self):
        for name in ('c-strips-foreign',
                     'c-preserves-nested-tables-and-arrays'):
            cases = copy.deepcopy(self.cases)
            cases['cases'] = [c for c in cases['cases'] if c['name'] != name]
            with self.subTest(removed=name), patch.object(seed, 'load_corpus', return_value=cases):
                with self.assertRaisesRegex(ValueError, 'case inventory'):
                    seed.check_corpus(ROOT)
        self.assertIn('validate_codex_seed_c', inspect.getsource(validate.main))

    # The production entrypoint detects a known retained-trust output plant;
    # a comment-only rewrite of an unfiltered seed also violates exact bytes.
    def test_production_plant_and_unfiltered_bytes(self):
        cases = copy.deepcopy(self.cases)
        case = cases['cases'][0]
        case['expected']['seed_config'] = case['config']
        with patch.object(seed, 'load_corpus', return_value=cases):
            with self.assertRaisesRegex(validate.ValidationFailure, 'seed configuration differs'):
                validate.validate_codex_seed_c()
        case = copy.deepcopy(next(c for c in self.cases['cases']
                                  if c['name'] == 'c-preserves-unrelated'))
        seed.check_case(case)
        case['expected']['seed_config'] += '# rewritten\n'
        with self.assertRaisesRegex(ValueError, 'unfiltered seed configuration bytes changed'):
            seed.check_case(case)


if __name__ == '__main__':
    unittest.main()
