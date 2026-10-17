"""Source-marker specification checks; no manager filesystem execution is claimed."""
from __future__ import annotations

import copy
import contextlib
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator

import validate


SUITE = validate.DRAFT_SOURCES_SUITE
CASES = SUITE / 'schema-cases' / 'install-marker-v6'


def load(path: Path):
    return json.loads(path.read_text())


class SourceMarkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry, cls.draft, cls.accepted = validate.draft_sources_schema_registry()
        cls.schema = load(cls.draft['install-marker-v6.schema.json'])

    def validator(self, schema=None):
        return Draft202012Validator(self.schema if schema is None else schema, registry=self.registry)

    # These claims concern the published schema entry point, not installation.
    def test_manifestless_positive_and_all_single_field_refusals(self):
        self.assertTrue(self.validator().is_valid(load(CASES / 'valid-manifestless.json')))
        for field in ('commands', 'dependencies', 'runtime_roots', 'build_roots',
                      'builds', 'build_source', 'requirements', 'mcp_servers', 'activation'):
            with self.subTest(field=field):
                self.assertFalse(self.validator().is_valid(load(CASES / f'invalid-manifestless-{field}.json')))
                self.assertTrue(self.validator().is_valid(load(CASES / f'valid-manifest-{field}.json')))

    def test_manifest_absence_and_version_are_exclusive(self):
        for name in ('invalid-manifestless-with-manifest-version',
                     'invalid-manifest-and-no-manifest-flag',
                     'invalid-manifest-version-and-null-array',
                     'invalid-fabricated-version-zero', 'invalid-absent-skill-schema-version'):
            with self.subTest(name=name):
                self.assertFalse(self.validator().is_valid(load(CASES / (name + '.json'))))
        for version in (1, 8, 9, None):
            marker = load(CASES / 'valid-manifestless.json')
            marker['skill_schema_version'] = version
            self.assertTrue(self.validator().is_valid(marker))
        marker['skill_schema_version'] = 10
        self.assertFalse(self.validator().is_valid(marker))

    # Each mutant retains the null branch but limits a refusal to populated
    # evidence or to two items. A single-item/empty-member witness defeats it.
    def test_narrowing_manifestless_field_mutants_have_witnesses(self):
        killed = 0
        for field in ('commands', 'dependencies', 'runtime_roots', 'build_roots',
                      'builds', 'build_source', 'requirements', 'mcp_servers', 'activation'):
            mutant = copy.deepcopy(self.schema)
            constraint = mutant['allOf'][-1]['then']
            if field in ('commands', 'dependencies', 'runtime_roots', 'build_roots'):
                constraint['properties'][field]['maxItems'] = 1
            elif field == 'builds':
                constraint['properties'][field]['maxProperties'] = len(load(CASES / 'invalid-manifestless-builds.json')['builds'])
            elif field == 'activation':
                constraint['properties']['activation']['properties']['commands']['maxItems'] = 1
            else:
                # Admit an otherwise-valid one-field marker by narrowing the
                # presence rejection to markers carrying a second field too.
                arm = next(a for a in constraint['not']['anyOf'] if a['required'] == [field])
                arm['required'].append('requirements' if field == 'build_source' else 'build_source')
            witness = load(CASES / f'invalid-manifestless-{field}.json')
            with self.subTest(mutant=field):
                self.assertFalse(self.validator().is_valid(witness))
                self.assertTrue(self.validator(mutant).is_valid(witness))
                killed += 1
        self.assertEqual(killed, 9)

    # Frozen v5 refuses absence; draft v6 admits it without weakening local
    # attestation/substitution restrictions inherited from v5.
    def test_v5_absence_refused_and_v6_local_restrictions_retained(self):
        marker = load(CASES / 'valid-manifestless.json')
        marker['schema_version'] = 5
        v5 = load(self.accepted['install-marker-v5.schema.json'])
        self.assertFalse(self.validator(v5).is_valid(marker))
        marker['schema_version'] = 6
        marker['package'] = {'kind': 'local-snapshot', 'snapshot': 'sha256:' + 'a' * 64}
        self.assertTrue(self.validator().is_valid(marker))
        for field, value in (('substituted', 'dev'),
                             ('attestation', {'registry': 'example', 'status': 'audited'})):
            changed = dict(marker, **{field: value})
            self.assertFalse(self.validator().is_valid(changed))
            changed['package'] = load(CASES / 'valid-manifestless.json')['package']
            self.assertTrue(self.validator().is_valid(changed))

    # Both published repair witnesses are structurally invalid only in build
    # evidence yet retain recognizable ownership fields. This tests fixture
    # integrity and the required outcome, not an implemented ownership gate.
    def test_owned_invalid_execution_policy_retains_rederive_vectors(self):
        rows = load(SUITE / 'marker-ownership-cases.json')
        for version in (5, 6):
            row = next(r for r in rows if r['id'] == f'owned-v{version}-invalid-execution-policy-rederived')
            marker = row['input']['canonical_entries']['review']['marker']['json']
            schema = self.schema if version == 6 else load(self.accepted['install-marker-v5.schema.json'])
            errors = list(self.validator(schema).iter_errors(marker))
            self.assertTrue(errors)
            repaired = copy.deepcopy(marker)
            original = load(validate.ROOT / 'conformance/skillfile-sources-v1/schema-cases/install-marker-v5/valid-external-substitution.json')
            for key in repaired['builds']:
                repaired['builds'][key]['execution_policy'] = original['builds'][key]['execution_policy']
            self.assertTrue(self.validator(schema).is_valid(repaired))
            self.assertEqual(marker['name'], 'review')
            self.assertEqual(marker['schema_version'], version)
            self.assertEqual(row['retained_case'], 'external-evidence-mismatch-execution_policy')
            self.assertEqual(row['expected']['ownership'], 'proven')
            self.assertEqual(row['expected']['repair'], 'revalidate-exact-locked-source-rebuild-not-adopt')

    # These execute the specification checker on every mandatory modeled
    # scenario; they make no assertion about a manager's actual filesystem.
    def test_ownership_refusal_vectors_contract(self):
        validate.validate_source_marker_ownership_vectors()

    def test_ownership_unowned_sibling_preserves_and_names_all_paths(self):
        validate.validate_source_marker_ownership_vectors(case_ids={
            'unowned-sibling-preserved-and-named', 'all-unowned-paths-named',
            'owned-stale-cleanup', 'new-destination-without-preceding-marker'})

    def test_ownership_unowned_selected_destination_refuses_without_partial_change(self):
        validate.validate_source_marker_ownership_vectors(case_ids={
            'unowned-selected-destination-no-partial-change',
            'ownership-changed-before-publication', 'new-destination-without-preceding-marker'})

    def test_ownership_invalid_evidence_rederived_not_refused(self):
        validate.validate_source_marker_ownership_vectors(case_ids={
            'owned-v5-invalid-execution-policy-rederived',
            'owned-v6-invalid-execution-policy-rederived', 'owned-stale-cleanup'})

    # Each control narrows one required outcome while retaining the neighboring
    # rows. Check the intended assertion and main's actual nonzero verdict.
    def assert_ownership_mutant_refused_through_main(self, case_id, change):
        path = SUITE / 'marker-ownership-cases.json'
        rows = load(path)
        row = next(r for r in rows if r['id'] == case_id)
        change(row)
        original = validate.load_json
        def mutated_load(candidate):
            return rows if candidate == path else original(candidate)
        diagnostic = f'source marker ownership {case_id}: outcome differs'
        with patch.object(validate, 'load_json', side_effect=mutated_load):
            with self.assertRaisesRegex(validate.ValidationFailure, diagnostic):
                validate.validate_source_marker_ownership_vectors()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
                self.assertEqual(validate.main(), 1)
            self.assertIn(diagnostic, stderr.getvalue())

    def test_control_sibling_only_destructive_acceptance_rejected(self):
        self.assert_ownership_mutant_refused_through_main(
            'unowned-sibling-preserved-and-named',
            lambda row: row.update(expected={'status': 'accepted', 'destructive_publications': 1}))

    def test_control_selected_destination_partial_publication_rejected(self):
        def change(row):
            row['expected']['canonical_entries'] = 'new-node-published-before-refusal'
            row['expected']['destructive_publications'] = 1
        self.assert_ownership_mutant_refused_through_main(
            'unowned-selected-destination-no-partial-change', change)

    def test_control_invalid_evidence_ownership_refusal_rejected(self):
        self.assert_ownership_mutant_refused_through_main(
            'owned-v6-invalid-execution-policy-rederived',
            lambda row: row.update(expected={'status': 'refused', 'error': 'source_ownership_unproven'}))

    # Every preservation component and both diagnostic paths are independently
    # required. Pair these attacks with the unchanged 21-row positive control.
    def test_ownership_preservation_and_path_narrowings_rejected(self):
        path = SUITE / 'marker-ownership-cases.json'
        original = validate.load_json
        for field in ('canonical_entries', 'lock', 'adapters', 'runtime', 'shims',
                      'destructive_publications', 'error', 'paths'):
            rows = load(path)
            row = next(r for r in rows if r['id'] == 'all-unowned-paths-named')
            row['expected'][field] = (row['expected'][field][:1] if field == 'paths' else
                                      1 if field == 'destructive_publications' else 'changed')
            with self.subTest(field=field), patch.object(
                    validate, 'load_json', side_effect=lambda p: rows if p == path else original(p)):
                with self.assertRaisesRegex(validate.ValidationFailure,
                                            'all-unowned-paths-named: outcome differs'):
                    validate.validate_source_marker_ownership_vectors()

    # A repinned pair of input/outcome edits cannot replace mandatory negative
    # scenarios with positive ones, and dropping/duplicating rows is refused.
    def test_ownership_scenario_substitution_and_inventory_refused(self):
        path = SUITE / 'marker-ownership-cases.json'
        original = validate.load_json
        for kind in ('substitution', 'missing', 'duplicate'):
            rows = load(path)
            if kind == 'substitution':
                rows[0]['input']['canonical_entries'].pop('personal')
                rows[0]['expected'] = {'status': 'accepted'}
            elif kind == 'missing':
                rows.pop()
            else:
                rows[-1] = copy.deepcopy(rows[0])
            with self.subTest(kind=kind), patch.object(
                    validate, 'load_json', side_effect=lambda p: rows if p == path else original(p)):
                with self.assertRaisesRegex(validate.ValidationFailure,
                                            'required scenario (inputs|inventory) differ'):
                    validate.validate_source_marker_ownership_vectors()


if __name__ == '__main__':
    unittest.main()
