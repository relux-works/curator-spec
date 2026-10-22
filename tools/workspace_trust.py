"""A1 specification oracle, not Curator or filesystem/Git authorization.

check_corpus is called by tools/validate.py. Input observations are synthetic
facts; implementations must establish them at their real production entrypoints.
"""
from __future__ import annotations

import copy
import json
import re
from datetime import datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = 'workspace-trust-v1'
ENVIRONMENTS = {'claude_code', 'codex_cli', 'opencode', 'pi', 'muse'}
ROWS = {'add-list', 'bind', 'identity', 'binding-remove', 'trust-remove', 'retry'}
TIME = '2026-10-18T00:00:00Z'


class ContractError(ValueError):
    """Published input or verdict violates the A1 contract."""


def exact_path(value):
    if not isinstance(value, str) or not value or re.search(r'[\x00-\x1f*?\[\]{}]', value):
        return False
    cls = PureWindowsPath if '\\' in value or re.match(r'^[A-Za-z]:', value) else PurePosixPath
    path = cls(value)
    if not path.is_absolute() or str(path) == path.anchor or '..' in path.parts:
        return False
    # Reject aliases rather than normalizing caller operands into grants.
    return str(path) == value


def within(child, root):
    cls = PureWindowsPath if '\\' in root or re.match(r'^[A-Za-z]:', root) else PurePosixPath
    return cls(child).is_relative_to(cls(root))


def remote_safe(value):
    if value is None:
        return True
    if not isinstance(value, str) or not value or re.search(r'[\s\x00-\x1f?#]', value):
        return False
    if '://' in value:
        try:
            url = urlsplit(value)
            # Public SSH user names are transport identity, passwords are not.
            return (bool(url.hostname) and bool(url.path) and url.password is None
                    and (url.username is None or url.scheme == 'ssh'))
        except ValueError:
            return False
    # SCP-like SSH transport can carry a public username, not a password.
    return re.fullmatch(r'(?:[A-Za-z0-9_.-]+@)?[A-Za-z0-9.-]+:[^:@\s?#]+', value) is not None


def record_error(record, schema):
    if not Draft202012Validator(schema, format_checker=FormatChecker()).is_valid(record):
        return 'workspace_trust_ledger_unreadable'
    if not exact_path(record['path']):
        return 'workspace_trust_ledger_unreadable'
    repository = record.get('repository')
    if repository:
        if (not exact_path(repository['root']) or not remote_safe(repository['primary_remote'])
                or not within(record['path'], repository['root'])):
            return 'workspace_trust_ledger_unreadable'
    if record['event'] == 'implicit-bind':
        source = record['binding']['source_path']
        if (record['path'] != repository['root'] or not exact_path(source)
                or not within(source, repository['root'])):
            return 'workspace_trust_ledger_unreadable'
    history = record['state_history']
    states = history + [record['state']]
    times = [datetime.fromisoformat(record['time'])] + [datetime.fromisoformat(s['time']) for s in states]
    allowed = {('active',), ('active', 'revoked'), ('active', 'lapsed'), ('active', 'lapsed', 'revoked')}
    if (tuple(s['status'] for s in states) not in allowed or states[0]['time'] != record['time']
            or times != sorted(times)):
        return 'workspace_trust_ledger_unreadable'
    return None


def scope_matches(record, action):
    return record['environment'] == action['environment']


def no_links(components):
    return 'symlink' not in components


def same_identity(recorded, observed):
    return recorded == observed


def discover(facts):
    """Interpret declared observations only; never execute repository content."""
    if facts is None:
        return None, None  # known non-repository, not failed discovery
    if facts.get('read') != 'ok' or facts.get('history_complete') is not True:
        return None, 'workspace_trust_repository_unverifiable'
    roots, remotes = facts.get('roots', []), facts.get('remotes', {})
    if len(roots) != 1 or not re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', roots[0]):
        return None, 'workspace_trust_repository_unverifiable'
    if not exact_path(facts.get('root')) or len(remotes) > 1 and 'origin' not in remotes:
        return None, 'workspace_trust_repository_unverifiable'
    remote = remotes['origin'] if 'origin' in remotes else next(iter(remotes.values()), None)
    if not remote_safe(remote):
        return None, 'workspace_trust_repository_unverifiable'
    return {'root': facts['root'], 'primary_remote': remote, 'root_commit': roots[0]}, None


def admit(action, *, remove=False, source=False):
    path = action.get('source_path') if source else action.get('path')
    if not exact_path(path) or path == action.get('home'):
        return 'workspace_trust_path_invalid'
    components = action.get('components', [])
    if not no_links(components):
        return 'workspace_trust_symlink'
    if action.get('path_read', 'ok') != 'ok':
        return 'workspace_trust_path_missing' if action['path_read'] == 'absent' and not remove else (
            None if action['path_read'] == 'absent' and remove else 'workspace_trust_ledger_unreadable')
    if remove:
        return None
    kind = action.get('kind', 'directory')
    if kind not in ({'directory', 'file'} if source else {'directory'}):
        return 'workspace_trust_path_kind'
    return None


def transition(record, status, reason):
    if record['state']['status'] == 'active' or status == 'revoked' and record['state']['status'] == 'lapsed':
        record['state_history'].append(copy.deepcopy(record['state']))
        record['state'] = {'status': status, 'time': TIME, 'reason': reason}


def observe(state, diagnostic=None, authorized=False, listed=None):
    records = state['records']
    return {
        'diagnostic': diagnostic, 'authorized': authorized,
        'active': sorted(r['grant_id'] for r in records if r['state']['status'] == 'active'),
        'references': sorted(r['grant_id'] for r in records
                             if r['event'] == 'implicit-bind' and r['state']['status'] == 'active'),
        'installed': sorted(state['bindings']), 'pending_cleanup': state['pending_cleanup'],
        'listed': listed,
    }


def step(state, action):
    """Execute one bounded specification transition over declared facts."""
    state = copy.deepcopy(state)
    op = action['op']
    envs = action.get('environments', [action.get('environment')])
    if not envs or any(e not in ENVIRONMENTS for e in envs):
        return state, observe(state, 'workspace_trust_environment_unsupported')
    if action.get('ledger', 'ok') not in {'ok', 'absent'} or action.get('ledger') == 'absent' and state['records']:
        return state, observe(state, 'workspace_trust_ledger_unreadable')
    if action.get('transaction_read', 'ok') != 'ok':
        return state, observe(state, 'workspace_trust_ledger_unreadable')
    if op == 'list':
        listed = sorted(r['grant_id'] for r in state['records'] if scope_matches(r, action))
        return state, observe(state, listed=listed)
    if op == 'binding-remove':
        if action.get('commit', 'ok') != 'ok':
            return state, observe(state, 'workspace_trust_binding_failed')
        binding = action['binding_id']
        state['bindings'] = [b for b in state['bindings'] if b != binding]
        for record in state['records']:
            if record.get('binding', {}).get('binding_id') == binding:
                transition(record, 'revoked', 'binding removed')
        return state, observe(state)
    error = admit(action, remove=op == 'remove', source=op == 'bind')
    if error:
        return state, observe(state, error)
    if op == 'remove':
        for record in state['records']:
            if scope_matches(record, action) and record['path'] == action['path']:
                transition(record, 'revoked', 'operator removed consent')
        state['pending_cleanup'] |= action.get('cleanup') == 'unreadable'
        return state, observe(state, 'workspace_trust_ledger_unreadable' if action.get('cleanup') == 'unreadable' else None)
    if op in {'resolve', 'repair', 'update'}:
        records = [r for r in state['records'] if scope_matches(r, action)
                   and r['path'] == action['path'] and r['state']['status'] == 'active']
        identity, error = discover(action.get('repository'))
        if error:
            return state, observe(state, error)
        changed = False
        for record in records:
            if not same_identity(record.get('repository'), identity):
                transition(record, 'lapsed', 'repository identity changed')
                changed = True
        valid = any(r['state']['status'] == 'active' for r in records)
        if op == 'repair' and action.get('cleanup') == 'ok':
            state['pending_cleanup'] = False
        return state, observe(state, None if valid else 'workspace_trust_repository_changed' if changed else 'workspace_untrusted', valid)
    if op not in {'add', 'launch', 'bind'}:
        raise ContractError('unknown vector operation')
    if op == 'launch' and not action.get('selection_ok', True):
        return state, observe(state, 'workspace_trust_binding_failed')
    if op == 'bind' and action.get('repository') is not None:
        # The source may be a file; consent grants the repository directory.
        # Admit that exact grant path before identity discovery or any commit.
        facts = action['repository']
        if facts.get('root') is None:
            return state, observe(state, 'workspace_trust_repository_unverifiable')
        error = admit({
            'op': 'bind', 'path': facts.get('root'), 'home': action.get('home'),
            'components': facts.get('components', action.get('components', [])),
            'kind': facts.get('kind', 'directory'),
            'path_read': facts.get('path_read', 'ok'),
        })
        if error:
            return state, observe(state, error)
    identity, error = discover(action.get('repository'))
    if error:
        return state, observe(state, error)
    if op == 'bind' and identity is None:
        return state, observe(state, 'workspace_trust_repository_required')
    checked = action.get('source_path') if op == 'bind' else action['path']
    if identity and not within(checked, identity['root']):
        return state, observe(state, 'workspace_trust_repository_unverifiable')
    if op == 'add' and not action.get('reason', '').strip():
        return state, observe(state, 'workspace_trust_path_invalid')
    if action.get('commit', 'ok') != 'ok':
        return state, observe(state, 'workspace_trust_binding_failed')
    # Previously committed transaction replay never reinstalls or renews consent.
    transaction = action['binding_id'] if op == 'bind' else action['grant_id']
    if transaction in state['transactions']:
        return state, observe(state)
    state['transactions'].append(transaction)
    if op == 'bind':
        state['bindings'].append(action['binding_id'])
    for env in sorted(set(envs)):
        record = {
            'record': 'workspace-trust-record-v1',
            'grant_id': f"{action['binding_id']}:{env}" if op == 'bind' else action['grant_id'],
            'environment': env, 'path': identity['root'] if op == 'bind' else action['path'],
            'event': {'add': 'explicit-grant', 'launch': 'implicit-launch', 'bind': 'implicit-bind'}[op],
            'operator': {'uid': '1000', 'name': 'sample-operator'}, 'time': TIME,
            'reason': action.get('reason', f'{op} action'),
            'state': {'status': 'active', 'time': TIME, 'reason': 'consent recorded'},
            'state_history': [],
        }
        if identity is not None:
            record['repository'] = identity
        if op == 'bind':
            record['binding'] = {k: action[k] for k in ('binding_id', 'profile', 'trigger', 'source_path')}
        state['records'].append(record)
    return state, observe(state)


def run_vector(vector, schema):
    state = {'records': [], 'bindings': [], 'transactions': [], 'pending_cleanup': False}
    for index, item in enumerate(vector['steps']):
        state, actual = step(state, item['action'])
        if actual != item['expected']:
            raise ContractError(f"{vector['name']} step {index}: expected {item['expected']!r}, got {actual!r}")
        for record in state['records']:
            if record_error(record, schema):
                raise ContractError(f"{vector['name']} step {index}: invalid resulting private record")
    return state


def check_corpus(root=ROOT):
    schema = json.loads((root / 'schemas' / NAMESPACE / 'workspace-trust-record-v1.schema.json').read_text(encoding='utf-8'))
    Draft202012Validator.check_schema(schema)
    corpus = root / 'conformance' / NAMESPACE
    cases = json.loads((corpus / 'schema-cases.json').read_text(encoding='utf-8'))
    vectors = json.loads((corpus / 'vectors.json').read_text(encoding='utf-8'))
    if len({c['name'] for c in cases}) != len(cases) or len({v['name'] for v in vectors}) != len(vectors):
        raise ContractError('duplicate corpus name')
    for case in cases:
        actual = record_error(case['instance'], schema)
        if actual != case['expected']:
            raise ContractError(f"{case['name']}: expected {case['expected']!r}, got {actual!r}")
    if {v['row'] for v in vectors} != ROWS:
        raise ContractError('six-row coverage differs')
    for vector in vectors:
        run_vector(vector, schema)
    return len(cases), len(vectors)


if __name__ == '__main__':
    try:
        cases, vectors = check_corpus()
    except (ValueError, OSError) as exc:
        raise SystemExit(f'workspace-trust publication failed: {exc}')
    print(f'workspace-trust: {cases}/{cases} schema cases; {vectors}/{vectors} transition vectors; runtime cases: unrun')
