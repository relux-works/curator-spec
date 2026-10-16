"""Tests of the T0 publication gate, not credential execution qualification."""
import copy
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator

import local_setup_token as local
import validate

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / 'conformance' / local.NAMESPACE


class LocalSourceTests(unittest.TestCase):
    def setUp(self):
        self.schemas, self.resources = local.registry(ROOT, validate.load_json)
        self.corpus = validate.load_json(CORPUS / 'cases.json')
        self.controls = validate.load_json(CORPUS / 'controls.json')

    def evaluate(self, case):
        before = copy.deepcopy(case['input'])
        result = local.policy_error(case, self.schemas, self.resources, validate.validate_wire_semantics)
        self.assertEqual(case['input'], before, case['name'])
        self.assertEqual(result, case['diagnostic'], case['name'])
        if result:
            self.assertNotIn('SYNTHETIC', result)
        return result

    def row(self, row):
        cases = [c for c in self.corpus['cases'] if c['row'] == row]
        outcomes = set()
        for case in cases:
            with self.subTest(case=case['name']):
                outcomes.add(self.evaluate(case) is None)
        self.assertEqual(outcomes, {True, False})

    # ST-01: actual closed machine/package/system carriers reject source authority,
    # invalid selectors, non-native node stores and explicit shared isolation.
    # This is metadata-only policy checking, with unchanged input on refusal.
    def test_st01_authority_store_and_isolation(self):
        self.row('ST-01')

    # ST-06: adoption witnesses distinguish native conflict, unreadable evidence,
    # lock conflict and old-marker repair from explicit admitted apply.
    # It does not execute migration or prove filesystem preservation.
    def test_st06_native_preservation_and_explicit_adoption(self):
        self.row('ST-06')

    # ST-07: full plan metadata rejects old/unknown semantics and mismatched local
    # identity/generations. A matching tuple is structurally admissible only.
    def test_st07_local_binding_and_required_understanding(self):
        self.row('ST-07')

    def source_carriers(self):
        # Paths are the published source semantics, not arbitrary JSON traversal.
        return [
            ('node-source-v1', ()),
            ('source-projection-v1', ('source',)),
            ('agent-environment-marker-v6', ('credential_source', 'source')),
            ('launch-env-fragment-v6', ('credential_source', 'source')),
            ('local-final-exec-v1', ('required_extensions', 'works.relux.curator.credential/1')),
            ('local-final-exec-v1', ('fragment', 'credential_source', 'source')),
        ]

    def metadata_case(self, schema, value, diagnostic):
        self.evaluate({'name': schema, 'kind': 'schema', 'schema': schema,
                       'input': value, 'diagnostic': diagnostic})
        if schema == 'local-final-exec-v1':
            case = copy.deepcopy(next(c for c in self.corpus['cases']
                                      if c['name'] == 'matching-local-tuple'))
            case['input']['plan'] = value
            case['diagnostic'] = diagnostic
            self.evaluate(case)

    # Regression: unknown source modes at every published source location use
    # unavailable, including the fragment independently of the required extension.
    # Malformed fields of a known branch remain usage; all inputs stay unchanged.
    def test_st07_nested_unknown_source_diagnostic(self):
        for schema, path in self.source_carriers():
            with self.subTest(schema=schema, path=path):
                self.metadata_case(schema, copy.deepcopy(self.controls[schema]), None)
                for mode in ('future-node', 'broker', 'helper'):
                    value = copy.deepcopy(self.controls[schema])
                    source = value
                    for member in path:
                        source = source[member]
                    source['mode'] = mode
                    self.metadata_case(schema, value, local.UNAVAILABLE)
                for field, invalid in [('source_ref', 'invalid'), ('token', 'SYNTHETIC-TOKEN')]:
                    value = copy.deepcopy(self.controls[schema])
                    source = value
                    for member in path:
                        source = source[member]
                    source[field] = invalid
                    self.metadata_case(schema, value, 'usage')

    # Regression: nonobject required extensions and their enclosing plan/source
    # containers refuse usage without exceptions. Missing/unknown required
    # extensions are unavailable; a supported but incomplete branch is usage.
    def test_st07_malformed_extension_typed_refusal(self):
        paths = [(), ('fragment',), ('fragment', 'credential_source'),
                 ('fragment', 'credential_source', 'source'),
                 ('required_extensions',),
                 ('required_extensions', 'works.relux.curator.credential/1')]
        for path in paths:
            for invalid in (None, False, 17, 1.5, 'node', [], ['node']):
                with self.subTest(path=path, invalid=invalid):
                    value = copy.deepcopy(self.controls['local-final-exec-v1'])
                    if path:
                        parent = value
                        for member in path[:-1]:
                            parent = parent[member]
                        parent[path[-1]] = invalid
                    else:
                        value = invalid
                    self.metadata_case('local-final-exec-v1', value, 'usage')
        for extensions, diagnostic in [({}, local.UNAVAILABLE),
                ({'works.relux.curator.future/1': {}}, local.UNAVAILABLE),
                ({'works.relux.curator.credential/1': {}}, 'usage')]:
            value = copy.deepcopy(self.controls['local-final-exec-v1'])
            value['required_extensions'] = extensions
            self.metadata_case('local-final-exec-v1', value, diagnostic)
        value = copy.deepcopy(self.controls['local-final-exec-v1'])
        del value['required_extensions']
        self.metadata_case('local-final-exec-v1', value, local.UNAVAILABLE)
        self.metadata_case('local-final-exec-v1',
                           copy.deepcopy(self.controls['local-final-exec-v1']), None)

    # Repeated review regression: unsupported whole-carrier revisions are
    # unavailable, including an independently nested fragment. Wrong JSON kinds
    # and missing discriminators remain usage; valid siblings preserve inputs.
    def test_st07_unknown_carrier_discriminators_typed_refusal(self):
        carriers = [
            ('manager-config-v6', 'schema_version', (5, 99, 99.0)),
            ('agent-environment-marker-v6', 'version', (5, 99, 99.0)),
            ('launch-env-fragment-v6', 'fragment',
             ('launch-env-fragment-v4', 'launch-env-fragment-v99')),
            ('env-status-v2', 'status', ('env-status-v1', 'env-status-v99')),
            ('local-final-exec-v1', 'plan', ('local-final-exec-v0', 'local-final-exec-v99')),
        ]
        for schema, field, unsupported in carriers:
            with self.subTest(schema=schema):
                control = copy.deepcopy(self.controls[schema])
                self.metadata_case(schema, control, None)
                for token in unsupported:
                    value = copy.deepcopy(control)
                    value[field] = token
                    self.metadata_case(schema, value, local.UNAVAILABLE)
                    if schema == 'launch-env-fragment-v6':
                        plan = copy.deepcopy(self.controls['local-final-exec-v1'])
                        plan['fragment'] = value
                        self.metadata_case('local-final-exec-v1', plan, local.UNAVAILABLE)
                invalid_kinds = (None, False, 1.5, [], {})
                invalid_kinds += ('6',) if isinstance(control[field], int) else (6,)
                for token in invalid_kinds:
                    value = copy.deepcopy(control)
                    value[field] = token
                    self.metadata_case(schema, value, 'usage')
                value = copy.deepcopy(control)
                del value[field]
                self.metadata_case(schema, value, 'usage')

    # Repeated review regression: route intent inside the actual plan cannot
    # borrow headless admission. Missing/nonstring routes are malformed usage;
    # supported route plus otherwise malformed metadata also stays usage.
    def test_st13_unsupported_plan_route_typed_refusal(self):
        control = copy.deepcopy(self.controls['local-final-exec-v1'])
        self.metadata_case('local-final-exec-v1', control, None)
        for route in ('direct-only', 'interactive-hosted-pty', 'tb-sessiond-restart',
                      'remote-archive-only', 'future-route'):
            with self.subTest(route=route):
                value = copy.deepcopy(control)
                value['route'] = route
                self.metadata_case('local-final-exec-v1', value, local.UNAVAILABLE)
        for route in (None, False, 17, 1.5, [], {}):
            value = copy.deepcopy(control)
            value['route'] = route
            self.metadata_case('local-final-exec-v1', value, 'usage')
        value = copy.deepcopy(control)
        del value['route']
        self.metadata_case('local-final-exec-v1', value, 'usage')
        value = copy.deepcopy(control)
        value['invocation']['endpoint'] = 'invalid'
        self.metadata_case('local-final-exec-v1', value, 'usage')

    # These exact repeated-review witnesses reach the corpus gate used by the
    # public CLI, with expected typed refusals and untouched valid siblings.
    def test_repeated_semantic_regressions_reach_publication_gate(self):
        original = validate.load_json

        def load(path):
            value = original(path)
            if path == CORPUS / 'cases.json':
                for schema, field, token in [
                        ('launch-env-fragment-v6', 'fragment', 'launch-env-fragment-v99'),
                        ('agent-environment-marker-v6', 'version', 99),
                        ('local-final-exec-v1', 'route', 'direct-only')]:
                    document = copy.deepcopy(self.controls[schema])
                    document[field] = token
                    value['cases'].append(dict(name='repeated-review-' + schema,
                        row='ST-13' if field == 'route' else 'ST-07', kind='schema',
                        schema=schema, input=document, diagnostic=local.UNAVAILABLE))
            return value

        count, negative = local.check_corpus(ROOT, load, validate.validate_wire_semantics)
        self.assertEqual(count, len(self.corpus['cases']) + 3)
        self.assertEqual(negative, sum(c['diagnostic'] is not None for c in self.corpus['cases']) + 3)
        local.check_corpus(ROOT, original, validate.validate_wire_semantics)

    # The two exact review witnesses drive the corpus entry point used by the
    # public checker CLI; no fixture mutation persists and valid siblings pass.
    def test_st07_review_regressions_reach_publication_gate(self):
        original = validate.load_json

        def load(path):
            value = original(path)
            if path == CORPUS / 'cases.json':
                base = next(c for c in value['cases'] if c['name'] == 'matching-local-tuple')
                unknown = copy.deepcopy(base)
                unknown.update(name='unknown-fragment-node-branch', diagnostic=local.UNAVAILABLE)
                unknown['input']['plan']['fragment']['credential_source']['source']['mode'] = 'future-node'
                malformed = copy.deepcopy(base)
                malformed.update(name='null-required-extension', diagnostic='usage')
                malformed['input']['plan']['required_extensions']['works.relux.curator.credential/1'] = None
                value['cases'].extend([unknown, malformed])
            return value

        count, negative = local.check_corpus(ROOT, load, validate.validate_wire_semantics)
        self.assertEqual(count, len(self.corpus['cases']) + 2)
        self.assertEqual(negative, sum(c['diagnostic'] is not None for c in self.corpus['cases']) + 2)
        local.check_corpus(ROOT, original, validate.validate_wire_semantics)

    # ST-09: closed objects reject forbidden fields, reserved input names and
    # source metadata in snapshot carriers; diagnostic codes never echo sentinels.
    # Arbitrary encoded values and archive execution are outside this checker.
    def test_st09_secret_fields_and_closed_snapshots(self):
        self.row('ST-09')

    # ST-13: direct-only, self-declared, caller-presence and snapshot evidence do
    # not satisfy the separate headless fixture tuple. No runtime is qualified.
    def test_st13_route_and_snapshot_are_not_authority(self):
        self.row('ST-13')

    # Every schema has both real positive and negative corpus controls, and the
    # main validation entrypoint invokes the checker instead of leaving it unused.
    def test_production_gate_and_complete_inventory(self):
        count, negative = local.check_corpus(ROOT, validate.load_json, validate.validate_wire_semantics)
        self.assertEqual(count, len(self.corpus['cases']))
        self.assertGreater(negative, 0)
        self.assertEqual(local.ST_ROWS, {'ST-01', 'ST-06', 'ST-07', 'ST-09', 'ST-13'})
        with patch.object(local, 'check_corpus', return_value=(count, negative)) as check:
            validate.validate_local_setup_token()
            check.assert_called_once()
        self.assertIn('validate_local_setup_token,', (ROOT / 'tools/validate.py').read_text())

    # Old closed readers admit their own controls and reject successor fields
    # even if an attacker restores an old token; new readers reject old tokens.
    def test_old_readers_and_discriminators(self):
        for new, old, field, token, path in [
            ('manager-config-v6', 'manager-config-v5', 'schema_version', 5, 'config-valid.json'),
            ('agent-environment-marker-v6', 'agent-environment-marker-v5', 'version', 5, 'marker-empty.json'),
            ('launch-env-fragment-v6', 'launch-env-fragment-v5', 'fragment', 'launch-env-fragment-v5', 'fragment-claude_code-native.json'),
        ]:
            with self.subTest(carrier=new):
                schema = self.resources.contents(f'https://relux-works.github.io/curator-spec/schemas/rc7-carriers-v1/{old}.schema.json')
                reader = Draft202012Validator(schema, registry=self.resources)
                self.assertTrue(reader.is_valid(validate.load_json(ROOT / 'conformance/rc7-carriers-v1/cases' / path)))
                self.assertFalse(reader.is_valid(self.controls[new]))
                forged = copy.deepcopy(self.controls[new]); forged[field] = token
                self.assertFalse(reader.is_valid(forged))
        v4 = self.resources.contents('https://relux-works.github.io/curator-spec/schemas/v1/launch-env-fragment-v4.schema.json')
        value = copy.deepcopy(self.controls['launch-env-fragment-v6']); value.pop('credential_source'); value['fragment'] = 'launch-env-fragment-v4'
        self.assertTrue(Draft202012Validator(v4, registry=self.resources).is_valid(value))
        value['credential_source'] = self.controls['source-projection-v1']
        self.assertFalse(Draft202012Validator(v4, registry=self.resources).is_valid(value))

    # Frozen readiness admits node/native/file/caller without adding lifecycle or
    # command codes. The containing successor rejects a node Keychain claim.
    def test_frozen_readiness_and_separate_lifecycle(self):
        row = self.controls['env-status-v2']['rows'][0]['readiness']
        reader = Draft202012Validator(self.resources.contents(
            'https://relux-works.github.io/curator-spec/schemas/login-readiness-v1/login-row-v1.schema.json'), registry=self.resources)
        self.assertTrue(reader.is_valid(row))
        for field in ('source_ref', 'expires_at', 'registration'):
            v = copy.deepcopy(row); v['login_detail'][field] = 'unknown'
            self.assertFalse(reader.is_valid(v))
        for state in ('active', 'revoked', 'recovery-required'):
            v = copy.deepcopy(self.controls['registration-v1']); v['state'] = state
            self.assertIsNone(local.metadata_error('registration-v1', v, self.schemas, self.resources, validate.validate_wire_semantics))

    # A plan/fragment generation mismatch is stale even though both independent
    # schemas validate. Required source metadata cannot be dropped at transport.
    def test_plan_projection_agrees(self):
        control = self.controls['local-final-exec-v1']
        self.assertIsNone(local.metadata_error('local-final-exec-v1', control, self.schemas, self.resources, validate.validate_wire_semantics))
        for field in ('source_generation', 'policy_generation'):
            value = copy.deepcopy(control); value[field] += 1
            self.assertEqual(local.metadata_error('local-final-exec-v1', value, self.schemas, self.resources, validate.validate_wire_semantics), 'credential_source_stale')
        value = copy.deepcopy(control)
        value['required_extensions']['works.relux.curator.credential/1']['source_ref'] = 'local:' + 'e' * 32
        self.assertEqual(local.metadata_error('local-final-exec-v1', value, self.schemas, self.resources, validate.validate_wire_semantics), 'credential_source_stale')

    # A checker plant is detected as the intended publication mismatch, not as
    # a setup crash; a clean sibling is accepted immediately afterwards.
    def test_forbidden_field_and_unknown_branch_plants(self):
        from check_local_setup_token_controls import run_plant
        for plant in ('secret', 'branch'):
            self.assertEqual(run_plant(plant), 1)
        local.check_corpus(ROOT, validate.load_json, validate.validate_wire_semantics)

    # Text pins cover the local-only C7 exception, public in-process seam and
    # hosted prohibition; they do not attest whether an implementation follows it.
    def test_normative_boundary_publication(self):
        text = (ROOT / 'protocol/local-setup-token-source.md').read_text()
        for clause in ('No local operation uses broker `lease_*` diagnostics.',
                       'tb-sessiond lookup/restart | Refused',
                       'func AuthorizeAndStart(context.Context, StartRequest, ProcessIO) (Process, error)',
                       'caller-side token sealing or daemon lookup.',
                       'Snapshot descriptors, manifests and archives MUST contain neither material,',
                       'The source selector is not an executable path, environment name or secret.'):
            self.assertIn(clause, text)
        cip = (ROOT / 'cips/CIP-0010-credentials-setup-token-and-inherited-auth.md').read_text()
        self.assertIn('## Narrow C7 amendment: local same-user publication (2026-10-16)', cip)
        self.assertIn('before C7\'s\nbroker-first sequence', cip)


if __name__ == '__main__':
    unittest.main()
