"""CIP-0020 policy-grant specification oracle, not a runtime trust manager.

All admission observations are synthetic trusted facts. Production code must
establish them at authenticated command and final launch entrypoints.
"""
from __future__ import annotations

import copy
import json
from datetime import datetime
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from ccj1_grammar import exact_patterns, integer
from workspace_trust import exact_path

ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = 'workspace-trust-policy-grant-v1'


def timestamp(value):
    return datetime.fromisoformat(value)


def canonical_remote(destination):
    path = destination['repository_path']
    if (not path.startswith('/') or any(part in {'', '.', '..'} for part in path[1:].split('/'))
            or any(c in path for c in '%?#\\') or any(c.isspace() or ord(c) < 32 for c in path)):
        return None
    ssh = destination['transport'] == 'ssh'
    authority = (destination['user'] + '@' if ssh else '') + destination['host']
    if destination['port'] != (22 if ssh else 443):
        authority += ':' + str(destination['port'])
    return destination['transport'] + '://' + authority + path


def record_error(record, schema):
    if not Draft202012Validator(exact_patterns(schema), format_checker=FormatChecker()).is_valid(record):
        return 'workspace_trust_ledger_unreadable'
    subject = record['subject']
    if (not exact_path(subject['path']) or subject['path'] != subject['repository']['root']
            or subject['repository']['primary_remote'] != canonical_remote(subject['canonical_destination'])
            or len(subject['path'].encode('utf-8')) > 4096):
        return 'workspace_trust_ledger_unreadable'
    hooks = record['surfaces']['hooks']
    if len({h['hook_id'] for h in hooks}) != len(hooks):
        return 'workspace_trust_ledger_unreadable'
    states = record['state_history'] + [record['state']]
    times = [timestamp(s['time']) for s in states]
    if (tuple(s['status'] for s in states) not in {
            ('active',), ('active', 'revoked'), ('active', 'lapsed'), ('active', 'lapsed', 'revoked')}
            or times != sorted(times) or states[0]['time'] != record['time']
            or states[0]['by'] != record['issuer']
            or timestamp(record['review_by']) <= timestamp(record['time'])
            or any((s['by'] is None) != (s['status'] == 'lapsed') for s in states)):
        return 'workspace_trust_ledger_unreadable'
    return None


def decision(record, facts, schema):
    """Evaluate an event against independent synthetic launch/approval evidence.

    approval_source authenticates the earlier policy-approval command, not the
    current launch caller. A valid stored approval requires no new owner prompt.
    """
    from validate import ccj1_sha256

    def refuse(code):
        return {'diagnostic': code, 'admitted': False, 'event': None, 'surfaces': None}

    error = record_error(record, schema)
    if error:
        return refuse(error)
    if not all(facts[k] for k in ('policy_readable', 'ledger_readable', 'journal_readable')):
        return refuse('workspace_trust_ledger_unreadable')
    issuer = record['issuer']
    if (facts['approval_source'] not in {'operator-command', 'keeper-command'}
            or not facts['authenticated_approval'] or facts['approved_issuer'] != issuer
            or facts['approval_source'] != issuer['actor']['kind'] + '-command'):
        return refuse('workspace_trust_policy_authority')
    policy = facts['policy']
    registration = facts['registration']
    if policy is None or registration is None:
        return refuse('workspace_untrusted')
    if record['policy'] != {'entry_id': policy['entry_id'], 'sha256': ccj1_sha256(policy)[7:]}:
        return refuse('workspace_trust_policy_digest')
    if record['state']['status'] == 'revoked' or record['grant_id'] in facts['revoked_ids']:
        return refuse('workspace_trust_grant_revoked')
    if (record['state']['status'] == 'lapsed' or record['review_by'] != policy['review_by']
            or timestamp(facts['now']) >= timestamp(record['review_by'])
            or timestamp(record['time']) < timestamp(policy['time'])
            or timestamp(record['time']) > timestamp(facts['now'])
            or timestamp(record['state']['time']) > timestamp(facts['now'])):
        return refuse('workspace_untrusted')
    subject, identity = record['subject'], record['identity']
    if (subject['checkout_id'] != registration['checkout_id']
            or subject['registration_sha256'] != registration['sha256']
            or subject['path'] != registration['path']
            or identity['root_identity'] != registration['root_identity']
            or subject['repository'] != facts['repository'] or not facts['nofollow_identity_matches']
            or subject['repository']['root_commit'] != policy['root_commit']):
        return refuse('workspace_trust_repository_changed')
    if (subject['canonical_destination'] != policy['canonical_destination']
            or not facts['destination_verified'] or not facts['ssh_pins_match']
            or not facts['command_free_routing']
            or facts['remote_spelling'] != canonical_remote(subject['canonical_destination'])
            or facts['remote_spelling'] not in policy['remote_spellings']):
        return refuse('workspace_trust_destination_mismatch')
    if (identity['environment'] != facts['environment'] or identity['lane_id'] != facts['lane_id']
            or identity['environment'] not in policy['environments'] or identity['lane_id'] not in policy['lanes']
            or policy['issuer'] != issuer
            or (record['surfaces']['project_trust'] and not policy['project_trust'])):
        return refuse('workspace_untrusted')
    if not facts['adapter_qualified']:
        return refuse('workspace_trust_adapter_unqualified')
    allowed = policy['hooks']
    granted = record['surfaces']['hooks']
    if (not facts['hook_state_readable']
            or any(h not in allowed for h in granted)
            or any(h not in granted for h in facts['effective_hooks'] + facts['native_hook_approvals'])):
        return refuse('workspace_trust_hook_digest')
    return {'diagnostic': None, 'admitted': True, 'event': 'policy-grant',
            'surfaces': copy.deepcopy(record['surfaces'])}


def revoke(records, journal, entry_id, issuer, time, reason):
    """Model durable revocation before conservative owned-key cleanup."""
    records, journal = copy.deepcopy(records), copy.deepcopy(journal)
    affected = set()
    for record in records:
        if record['policy']['entry_id'] == entry_id:
            affected.add(record['grant_id'])
            if record['state']['status'] != 'revoked':
                record['state_history'].append(record['state'])
                record['state'] = {'status': 'revoked', 'time': time, 'reason': reason, 'by': issuer}
    active = {r['grant_id'] for r in records if r['state']['status'] == 'active'}
    for key in journal:
        if not affected.intersection(key['grant_ids']):
            continue
        if active.intersection(key['grant_ids']):
            continue
        if key['owned_unchanged'] and key['readable']:
            key['present'], key['pending_cleanup'] = False, False
        else:
            key['pending_cleanup'] = True
    return records, journal


def load(path):
    return json.loads(path.read_text(), parse_int=integer)


def check_corpus(root=ROOT):
    schema = load(root / 'schemas' / NAMESPACE / (NAMESPACE + '.schema.json'))
    Draft202012Validator.check_schema(schema)
    corpus = root / 'conformance' / NAMESPACE
    base = load(corpus / 'positive.json')
    if record_error(base['record'], schema):
        raise ValueError('positive event is invalid')
    cases = load(corpus / 'schema-cases.json')
    for case in cases:
        record = copy.deepcopy(base['record'])
        target = record
        for member in case['path'][:-1]:
            target = target[member]
        if case['op'] == 'remove':
            del target[case['path'][-1]]
        else:
            target[case['path'][-1]] = case['value']
        if record_error(record, schema) != case['expected']:
            raise ValueError(f"schema case {case['name']}")
    pairs = load(corpus / 'vectors.json')
    required = {'package-trust', 'package-hooks', 'stale-digest', 'revoked',
                'hook-digest', 'unknown-project', 'destination-spelling'}
    if not required <= {p['name'] for p in pairs}:
        raise ValueError('missing required paired vectors')
    for pair in pairs:
        for side in ('positive', 'negative'):
            scenario = copy.deepcopy(base)
            for change in pair[side]['changes']:
                target = scenario
                for member in change['path'][:-1]:
                    target = target[member]
                target[change['path'][-1]] = change['value']
            actual = decision(scenario['record'], scenario['facts'], schema)
            if actual != pair[side]['expected']:
                raise ValueError(f"vector {pair['name']} {side}: {actual}")
            if actual['admitted'] != (side == 'positive'):
                raise ValueError(f"vector {pair['name']} lacks opposite controls")
    return len(cases), len(pairs)


if __name__ == '__main__':
    cases, pairs = check_corpus()
    print(f'policy-grant: {cases} schema cases, {pairs} positive/negative pairs; runtime unverified')
