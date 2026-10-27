"""Paired CIP-0020 publication checks; no vendor/runtime qualification."""
from __future__ import annotations

import copy
import json
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator

import workspace_policy_grant as grant
from test_validate import validate

CORPUS = grant.ROOT / 'conformance' / grant.NAMESPACE
BASE = grant.load(CORPUS / 'positive.json')
SCHEMA = grant.load(grant.ROOT / 'schemas' / grant.NAMESPACE / (grant.NAMESPACE + '.schema.json'))


class PolicyGrantTests(unittest.TestCase):
    # The real publication entry executes both schema and opposite-verdict
    # cases. This checks specification consistency, not runtime admission.
    def test_publication_entry(self):
        self.assertEqual(grant.check_corpus(), (49, 28))
        validate.validate_workspace_policy_grants()

    # A planted permissive package verdict must fail in the real entry with
    # that case's name; an unrelated setup failure does not satisfy this check.
    def test_publication_entry_detects_forbidden_grant(self):
        original = grant.Path.read_text

        def planted(path, *args, **kwargs):
            text = original(path, *args, **kwargs)
            if path == CORPUS / 'vectors.json':
                pairs = json.loads(text)
                pair = next(p for p in pairs if p['name'] == 'package-trust')
                pair['negative']['expected'] = pair['positive']['expected']
                return json.dumps(pairs)
            return text

        with patch.object(grant.Path, 'read_text', new=planted):
            with self.assertRaisesRegex(validate.ValidationFailure, 'package-trust negative'):
                validate.validate_workspace_policy_grants()

    # Synthetic final-admission decisions cannot mutate their event or inputs;
    # each refusal has no event or granted surface, with a nearby admitted case.
    def test_paired_verdicts_preserve_inputs(self):
        for pair in grant.load(CORPUS / 'vectors.json'):
            for side in ('positive', 'negative'):
                scenario = copy.deepcopy(BASE)
                for change in pair[side]['changes']:
                    target = scenario
                    for member in change['path'][:-1]:
                        target = target[member]
                    target[change['path'][-1]] = change['value']
                before = copy.deepcopy(scenario)
                with self.subTest(pair=pair['name'], side=side):
                    self.assertEqual(grant.decision(scenario['record'], scenario['facts'], SCHEMA), pair[side]['expected'])
                    self.assertEqual(scenario, before)

    # Policy identity is the entire approved CCJ-1 entry, including approval,
    # scope, hooks and expiry. Key ordering is irrelevant; changed bytes are not.
    def test_policy_digest_covers_complete_entry(self):
        policy = BASE['facts']['policy']
        expected = BASE['record']['policy']['sha256']
        self.assertEqual(validate.ccj1_sha256(dict(reversed(list(policy.items())))), 'sha256:' + expected)
        for field, value in {
            'reason': 'Different reason', 'review_by': '2026-11-28T00:00:00Z',
            'lanes': ['lane:other'], 'hooks': [], 'project_trust': False,
            'issuer': dict(policy['issuer'], approval_ref='f' * 64),
        }.items():
            changed = dict(policy, **{field: value})
            with self.subTest(field=field):
                self.assertNotEqual(validate.ccj1_sha256(changed), 'sha256:' + expected)

    # The original closed v1 carrier remains valid for its own positive control
    # and rejects policy-grant rather than relabeling it explicit-grant.
    def test_original_carrier_is_not_widened(self):
        root = grant.ROOT
        schema = grant.load(root / 'schemas/workspace-trust-v1/workspace-trust-record-v1.schema.json')
        record = grant.load(root / 'conformance/workspace-trust-v1/schema-cases.json')[0]['instance']
        validator = Draft202012Validator(schema)
        self.assertTrue(validator.is_valid(record))
        record['event'] = 'policy-grant'
        self.assertFalse(validator.is_valid(record))
        self.assertIsNone(grant.record_error(BASE['record'], SCHEMA))
        wrong = dict(BASE['record'], event='explicit-grant')
        self.assertEqual(grant.record_error(wrong, SCHEMA), 'workspace_trust_ledger_unreadable')

    # Both direct operator and approved keeper provenance can issue the same
    # scoped event. Merely switching the actor without current approval fails.
    def test_operator_and_keeper_provenance(self):
        self.assertTrue(grant.decision(BASE['record'], BASE['facts'], SCHEMA)['admitted'])
        scenario = copy.deepcopy(BASE)
        issuer = scenario['record']['issuer']
        issuer['actor'] = {'kind': 'operator', 'principal_ref': issuer['principal_ref']}
        scenario['record']['state']['by'] = copy.deepcopy(issuer)
        scenario['facts']['approval_source'] = 'operator-command'
        self.assertEqual(grant.decision(scenario['record'], scenario['facts'], SCHEMA)['diagnostic'],
                         'workspace_trust_policy_authority')
        scenario['facts']['approved_issuer'] = copy.deepcopy(issuer)
        scenario['facts']['policy']['issuer'] = copy.deepcopy(issuer)
        scenario['record']['policy']['sha256'] = validate.ccj1_sha256(scenario['facts']['policy'])[7:]
        self.assertTrue(grant.decision(scenario['record'], scenario['facts'], SCHEMA)['admitted'])

    # A direct HTTPS destination also admits; equivalent explicit-default-port
    # spelling refuses, establishing that the rule is exact rather than SSH-only.
    def test_https_canonical_spelling(self):
        scenario = copy.deepcopy(BASE)
        destination = {'transport': 'https', 'host': 'code.example', 'port': 443,
                       'repository_path': '/team/project.git'}
        remote = 'https://code.example/team/project.git'
        record, facts = scenario['record'], scenario['facts']
        record['subject']['canonical_destination'] = destination
        record['subject']['repository']['primary_remote'] = remote
        facts['repository']['primary_remote'] = remote
        facts['policy']['canonical_destination'] = destination
        facts['policy']['remote_spellings'] = [remote]
        facts['remote_spelling'] = remote
        record['policy']['sha256'] = validate.ccj1_sha256(facts['policy'])[7:]
        self.assertTrue(grant.decision(record, facts, SCHEMA)['admitted'])
        facts['remote_spelling'] = 'https://code.example:443/team/project.git'
        self.assertEqual(grant.decision(record, facts, SCHEMA)['diagnostic'],
                         'workspace_trust_destination_mismatch')

    # Automatic lapse retains consent history but cannot authorize reuse;
    # subsequent operator revocation retains the lapse, never reactivates it.
    def test_lapse_then_revoke_retains_history(self):
        record = copy.deepcopy(BASE['record'])
        self.assertTrue(grant.decision(record, BASE['facts'], SCHEMA)['admitted'])
        record['state_history'] = [record['state']]
        record['state'] = {'status': 'lapsed', 'time': '2026-10-27T09:15:00Z',
                           'reason': 'Retained identity changed', 'by': None}
        self.assertIsNone(grant.record_error(record, SCHEMA))
        self.assertEqual(grant.decision(record, BASE['facts'], SCHEMA)['diagnostic'], 'workspace_untrusted')
        revoked, _ = grant.revoke([record], [], record['policy']['entry_id'], record['issuer'],
                                  '2026-10-27T09:30:00Z', 'Withdraw expired approval')
        self.assertIsNone(grant.record_error(revoked[0], SCHEMA))
        self.assertEqual([s['status'] for s in revoked[0]['state_history']], ['active', 'lapsed'])
        self.assertEqual(revoked[0]['state']['status'], 'revoked')

    # An empty hook list is usable only with qualified absence/approval lookup;
    # emptiness cannot turn an unqualified adapter into unattended admission.
    def test_hook_free_checkout_still_requires_qualification(self):
        scenario = copy.deepcopy(BASE)
        scenario['facts']['policy']['hooks'] = []
        scenario['record']['surfaces']['hooks'] = []
        scenario['facts']['effective_hooks'] = []
        scenario['facts']['native_hook_approvals'] = []
        scenario['record']['policy']['sha256'] = validate.ccj1_sha256(scenario['facts']['policy'])[7:]
        self.assertTrue(grant.decision(scenario['record'], scenario['facts'], SCHEMA)['admitted'])
        scenario['facts']['adapter_qualified'] = False
        self.assertEqual(grant.decision(scenario['record'], scenario['facts'], SCHEMA)['diagnostic'],
                         'workspace_trust_adapter_unqualified')

    # Policy edit and removal revoke all derived digests before conservative
    # cleanup. Conflicts/read failures preserve present keys; other active
    # support survives. Retry is idempotent and no revoked event is renewed.
    def test_policy_revocation_cleanup_and_retry(self):
        for reason in ('Policy edited', 'Policy removed'):
            records = [copy.deepcopy(BASE['record']) for _ in range(3)]
            records[1]['grant_id'] = 'grant:older-digest'
            records[1]['policy']['sha256'] = 'e' * 64
            records[2]['grant_id'] = 'grant:independent'
            records[2]['policy']['entry_id'] = 'other-policy'
            journal = [
                {'home': '/homes/build', 'key': key, 'grant_ids': ids, 'owned_unchanged': owned,
                 'readable': readable, 'present': True, 'pending_cleanup': False}
                for key, ids, owned, readable in [
                    ('trust', ['grant:build'], True, True),
                    ('modified', ['grant:build'], False, True),
                    ('unreadable', ['grant:older-digest'], True, False),
                    ('shared', ['grant:build', 'grant:independent'], True, True),
                    ('unrelated', ['grant:independent'], True, True),
                ]
            ]
            args = ('project-lanes', BASE['record']['issuer'], '2026-10-27T09:30:00Z', reason)
            with self.subTest(reason=reason):
                revoked, cleaned = grant.revoke(records, journal, *args)
                self.assertEqual([r['state']['status'] for r in revoked], ['revoked', 'revoked', 'active'])
                self.assertEqual([(k['present'], k['pending_cleanup']) for k in cleaned],
                                 [(False, False), (True, True), (True, True), (True, False), (True, False)])
                for original, result in zip(records, revoked):
                    self.assertEqual(result['policy'], original['policy'])
                    self.assertEqual(result['issuer'], original['issuer'])
                    self.assertIsNone(grant.record_error(result, SCHEMA))
                self.assertEqual(grant.revoke(revoked, cleaned, *args), (revoked, cleaned))
                self.assertTrue(all(k['present'] for k in journal), 'inputs remain unchanged')
                self.assertEqual(grant.decision(revoked[0], BASE['facts'], SCHEMA)['diagnostic'],
                                 'workspace_trust_grant_revoked')


if __name__ == '__main__':
    unittest.main()
