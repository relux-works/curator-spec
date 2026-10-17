#!/usr/bin/env python3
"""Bounded narrowing mutants of the A1 specification oracle, not runtime."""
from __future__ import annotations

import argparse
import copy
import sys
import unittest
from unittest.mock import patch

import workspace_trust as trust
from test_workspace_trust import WorkspaceTrustTests, VECTORS

BASE_STEP = trust.step
BASE_TRANSITION = trust.transition
BASE_ADMIT = trust.admit


def source_path_only_bind_admission(action, *, remove=False, source=False):
    # Retain all source checks and non-bind admission; omit only the resulting
    # bind grant path. This reproduces the reviewed home-root bypass.
    if action.get('op') == 'bind' and not source:
        return None
    return BASE_ADMIT(action, remove=remove, source=source)


def active_reference_replay_gate(state, action):
    # Narrow durable deduplication to live references: a committed but revoked
    # binding is forgotten, while a repeated active binding still deduplicates.
    state = copy.deepcopy(state)
    if action['op'] == 'bind':
        binding = action['binding_id']
        live = any(r.get('binding', {}).get('binding_id') == binding
                   and r['state']['status'] == 'active' for r in state['records'])
        if not live and binding in state['transactions']:
            state['transactions'].remove(binding)
    return BASE_STEP(state, action)


def profile_add_only_removal(record, status, reason):
    # Keep revocation for profile adds, explicit removes and identity changes;
    # narrow only binding-removal support to exclude context-extract bindings.
    if reason == 'binding removed' and record.get('binding', {}).get('trigger') == 'context-extract':
        return
    BASE_TRANSITION(record, status, reason)


class RemovalControlTests(unittest.TestCase):
    # Both binding triggers must lose their last reference on removal; this
    # checks logical authorization only, not disk recovery or vendor cleanup.
    def test_binding_removal_covers_context_extraction(self):
        source = next(v for v in VECTORS if v['name'] == 'context-extract')['steps'][0]['action']
        for trigger in ('profile-add', 'context-extract'):
            with self.subTest(trigger=trigger):
                state = {'records': [], 'bindings': [], 'transactions': [], 'pending_cleanup': False}
                action = copy.deepcopy(source)
                action['trigger'] = trigger
                state, result = trust.step(state, action)
                self.assertEqual(result['references'], ['binding-a:codex_cli'])
                state, result = trust.step(state, {
                    'op': 'binding-remove', 'environment': 'codex_cli', 'binding_id': 'binding-a'})
                self.assertEqual(result['references'], [])
                self.assertEqual(result['active'], [])
                self.assertEqual(result['installed'], [])


MUTANTS = {
    'source-path-only-bind': ('admit', source_path_only_bind_admission,
        'retain source-path admission but omit repository-root grant admission',
        'test_vector_review_bind_home_root'),
    'profile-scope': ('scope_matches',
        lambda record, action: record.get('binding', {}).get('profile') == action.get('profile'),
        'retain equality gate but scope by profile rather than adapter',
        'test_vector_profile_not_environment_scope'),
    'final-component-only': ('no_links',
        lambda components: not components or components[-1] != 'symlink',
        'retain link rejection only at final component, admitting linked ancestors',
        'test_vector_reject_link_ancestor'),
    'remote-only': ('same_identity',
        lambda recorded, observed: (recorded is None and observed is None or
            recorded is not None and observed is not None and recorded['primary_remote'] == observed['primary_remote']),
        'retain identity equality only for remote, admitting replacement root history',
        'test_vector_same_remote_new_root_commit'),
    'profile-add-only-removal': ('transition', profile_add_only_removal,
        'retain profile-add revocation but omit context-extract binding revocation',
        'test_binding_removal_covers_context_extraction'),
    'active-only-replay': ('step', active_reference_replay_gate,
        'retain active-bind deduplication but forget revoked binding transactions',
        'test_vector_bind_retry_idempotent'),
}


def run(name, *, details=False):
    target, replacement, narrowing, test = MUTANTS[name]
    with patch.object(trust, target, new=replacement):
        result = unittest.TestResult()
        cls = RemovalControlTests if test.startswith('test_binding_removal_') else WorkspaceTrustTests
        cls(test).run(result)
    # The intended named assertion must fail; unrelated exceptions are survivors.
    killed = bool(result.failures) and not result.errors and not result.skipped
    print(f"| {name} | {narrowing} | {test if killed else 'none'} | "
          f"{'none; killed' if killed else 'UNPROVEN: named assertion did not fail'} |")
    if details:
        for _, failure in result.failures:
            print(failure, file=sys.stderr)
    if result.errors:
        for _, error in result.errors:
            print(error, file=sys.stderr)
    return killed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mutant', choices=sorted(MUTANTS))
    args = parser.parse_args()
    # Both added state-machine controls must pass before any narrowing plant.
    baseline = unittest.TestResult()
    RemovalControlTests('test_binding_removal_covers_context_extraction').run(baseline)
    WorkspaceTrustTests('test_vector_bind_retry_idempotent').run(baseline)
    WorkspaceTrustTests('test_vector_review_bind_home_root').run(baseline)
    WorkspaceTrustTests('test_vector_bind_grant_root_valid_controls').run(baseline)
    if not baseline.wasSuccessful() or baseline.skipped:
        print('Positive controls failed; no mutant verdict is admissible', file=sys.stderr)
        return 2
    print('| Mutant | Narrowing | Named failing test | Survivor bound |')
    print('|---|---|---|---|')
    if args.mutant:
        # An intended assertion failure is a real failing control, exit 1.
        return 1 if run(args.mutant, details=True) else 0
    killed = sum(run(name) for name in MUTANTS)
    print(f'Narrowing mutants killed: {killed}/{len(MUTANTS)}; runtime mutants: unrun')
    return int(killed != len(MUTANTS))


if __name__ == '__main__':
    raise SystemExit(main())
