"""Specification-data controls; no manager execution or vendor qualification."""
import copy
import inspect
import unittest
from pathlib import Path
from unittest.mock import patch

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

    # Full marker 7 admits C and retained A/B records; old carriers still
    # reject C. Closed records, versions and unrelated v6 fields stay enforced.
    def test_marker_schema_and_narrowing(self):
        seed.check_markers(ROOT)
        schema = seed.load_schema(ROOT)
        for mutate in (
            lambda s: s['properties']['codex_seed_record']['properties']['revision'].update(enum=['A', 'B', 'C', 'D']),
            lambda s: s['properties']['codex_seed_record'].update(additionalProperties=True),
            lambda s: s['properties']['version'].update(const=6),
            lambda s: s['properties']['codex_settings'].update(type='object', additionalProperties=True, **{'$ref': None}),
        ):
            bad = copy.deepcopy(schema)
            mutate(bad)
            with patch.object(seed, 'load_schema', return_value=bad):
                with self.assertRaisesRegex(ValueError, 'marker successor'):
                    seed.check_markers(ROOT)

    # Removing a witness cannot silently weaken the gate, and production
    # validation must dispatch it rather than leaving it as an optional test.
    def test_inventory_and_dispatch(self):
        cases = copy.deepcopy(self.cases)
        cases['cases'].pop()
        with patch.object(seed, 'load_corpus', return_value=cases):
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
