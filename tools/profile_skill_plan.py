"""Proposed carrier publication oracle; no manager/filesystem/build execution."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from assurance import ccj1_sha256
from ccj1_grammar import exact_patterns

ROOT = Path(__file__).resolve().parents[1]
FAMILY = 'profile-skill-plan-v1'
PIN = ('source', 'commit', 'directory')


def catalog(root=ROOT):
    documents = [exact_patterns(json.loads(p.read_text(encoding='utf-8')))
                 for p in (root / 'schemas').rglob('*.schema.json')]
    for document in documents:
        Draft202012Validator.check_schema(document)
    registry = Registry().with_resources(
        (d['$id'], Resource.from_contents(d)) for d in documents)
    return {d['$id'].split('/schemas/', 1)[1]:
            Draft202012Validator(d, registry=registry) for d in documents}


def edge_key(edge):
    return edge['consumer']['kind'], edge['consumer']['name'], edge['provider']


def pin(value):
    return tuple(value[k] for k in PIN)


def context_identity_agrees(member, package):
    if package is None or package.get('version') != member['version']:
        return False
    if 'state_sha256' in member:
        return (package.get('state_sha256') == member['state_sha256']
                and not any(k in package for k in PIN))
    return ('state_sha256' not in package
            and package.get('source') == member['source']
            and package.get('commit') == member['commit']
            and package.get('directory', '.') == member.get('directory', '.'))


def reserved_command(command, case_insensitive):
    name = command.casefold() if case_insensitive else command
    return name.startswith('curator-')


def prepare(baseline, case):
    """Apply explicit corpus edits to an isolated JSON copy, never source files."""
    data = deepcopy(baseline)
    for edit in case.get('patch', []):
        parent = data
        for key in edit['path'][:-1]:
            parent = parent[key]
        key = edit['path'][-1]
        if edit.get('delete'):
            del parent[key]
        else:
            parent[key] = deepcopy(edit['value'])
    if case.get('rebind', True) and data['lock'].get('schema_version') == 5:
        data['lock']['skill_plan_sha256'] = ccj1_sha256(data['lock']['skill_plan'])
        data['runtime_lock_sha256'] = ccj1_sha256(data['lock'])
    return data


def plan_error(data, validators):
    lock = data['lock']
    if lock.get('schema_version') != 5 or data['reader_version'] != 5:
        return 'profile_skill_plan_required'
    if not validators[FAMILY + '/context-lock-v5.schema.json'].is_valid(lock):
        return 'profile_skill_plan_invalid'
    plan = lock['skill_plan']
    if (lock['skill_plan_sha256'] != ccj1_sha256(plan)
            or data['runtime_lock_sha256'] != ccj1_sha256(lock)):
        return 'profile_skill_plan_binding_invalid'
    for values, key in ((plan['nodes'], lambda n: n['name']),
                        (plan['edges'], edge_key),
                        (plan['direct_constraints'], lambda n: n['name']),
                        (lock['members'], lambda n: (n['kind'], n['name']))):
        keys = [key(value) for value in values]
        if keys != sorted(set(keys)):
            return 'profile_skill_plan_invalid'
    nodes = {n['name']: n for n in plan['nodes']}
    # Overlap is checked against observed declarations, not a trusted plan claim.
    directs = [d for d in data['direct'] if d['name'] in nodes]
    for direct in directs:
        if pin(direct) != pin(nodes[direct['name']]):
            return 'profile_skill_pin_conflict'
    expected_direct = [{k: d[k] for k in (*PIN, 'name', 'ref')} |
                       {'declaration_sha256': ccj1_sha256(d['declaration'])}
                       for d in directs]
    if plan['direct_constraints'] != sorted(expected_direct, key=lambda d: d['name']):
        return 'profile_skill_plan_invalid'

    packages = {(p['kind'], p['name']): p for p in data['packages']}
    if len(packages) != len(data['packages']):
        return 'profile_skill_plan_invalid'
    expected_edges, visited, visiting = [], set(), set()

    def visit(kind, name):
        key = kind, name
        if key in visiting or key not in packages:
            raise ValueError('missing package or cycle')
        if key in visited:
            return
        visiting.add(key)
        package = packages[key]
        for requirement in package['requirements']:
            provider = requirement['provider']
            node = nodes.get(provider)
            if node is None or pin(node) != pin(requirement):
                raise ValueError('requirement pin disagreement')
            expected_edges.append({
                'consumer': {'kind': kind, 'name': name},
                'provider': provider, 'ref': requirement['ref'],
                'mode': requirement.get('mode', 'full'),
                **({'commands': requirement['commands']}
                   if 'commands' in requirement else {})})
            visit('skill', provider)
        visiting.remove(key)
        visited.add(key)

    try:
        for member in lock['members']:
            if member['kind'] == 'context':
                package = packages.get(('context', member['name']))
                # Facts come from the admitted snapshot, not from the graph's
                # consumer name or a rehashed but substituted lock identity.
                if not context_identity_agrees(member, package):
                    raise ValueError('context identity disagreement')
                visit('context', member['name'])
    except ValueError:
        return 'profile_skill_plan_invalid'
    if nodes.keys() != {name for kind, name in visited if kind == 'skill'}:
        return 'profile_skill_plan_invalid'
    for direct in directs:
        expected_edges.append({'consumer': {'kind': 'machine', 'name': direct['name']},
                               'provider': direct['name'], 'ref': direct['ref'],
                               'mode': 'full'})
    if plan['edges'] != sorted(expected_edges, key=edge_key):
        return 'profile_skill_plan_invalid'
    members = {m['name']: m for m in lock['members'] if m['kind'] == 'skill'}
    retained = {m['name']: dict(m, directory=m.get('directory', '.'))
                for m in data.get('retained_members', [])}
    if (nodes.keys() & retained.keys() or members.keys() != nodes.keys() | retained.keys()
            or any(members.get(name) != member for name, member in retained.items())):
        return 'profile_skill_plan_invalid'
    for name, node in nodes.items():
        package = packages['skill', name]
        if (pin(node) != pin(package) or node['content_sha256'] != package['content_sha256']
                or pin(members[name]) != pin(node)):
            return 'profile_skill_plan_invalid'
        required_by = sorted({e['consumer']['name'] for e in plan['edges']
                              if e['provider'] == name and e['consumer']['kind'] != 'machine'})
        if members[name]['required_by'] != required_by:
            return 'profile_skill_plan_invalid'
    for edge in plan['edges']:
        package = packages['skill', edge['provider']]
        ref = edge['ref']
        if ref['kind'] == 'revision' and ref['value'] != package['commit']:
            return 'profile_skill_plan_invalid'
        if ref['kind'] == 'tag':
            if package['admitted_tags'].get(ref['value']) != package['commit']:
                return 'profile_skill_plan_invalid'
            observed = package.get('observed_tags', {}).get(ref['value'], package['commit'])
            if observed != package['commit']:
                return 'profile_skill_pin_changed'
        commands = edge.get('commands')
        if commands is not None:
            if commands != sorted(commands):
                return 'profile_skill_plan_invalid'
            if any(package['commands'].get(c) not in ('script', 'build') for c in commands):
                return 'profile_skill_command_invalid'
    return None


def activation(data):
    result = {}
    for node in data['lock']['skill_plan']['nodes']:
        name = node['name']
        package = next(p for p in data['packages'] if p['kind'] == 'skill' and p['name'] == name)
        exports = {k for k, v in package['commands'].items() if v in ('script', 'build')}
        context, commands = False, set()
        for edge in data['lock']['skill_plan']['edges']:
            if edge['provider'] != name:
                continue
            context |= edge['mode'] in ('full', 'context')
            if edge['mode'] == 'full' or (edge['mode'] == 'runtime' and 'commands' not in edge):
                commands |= exports
            elif edge['mode'] == 'runtime':
                commands.update(edge['commands'])
        result[name] = {'context': context, 'commands': sorted(commands)}
    return result


def drift(data):
    selected = {n['name'] for n in data['lock'].get('skill_plan', {}).get('nodes', [])}
    result = []
    for direct in data['direct']:
        if direct['name'] in selected:
            continue
        observed = direct['observed']
        state = ('unknown' if observed == 'unreadable' else
                 'in-sync' if observed == direct['commit'] else 'drift')
        result.append({'name': direct['name'], 'declared': direct['ref'],
                       'observed': observed, 'state': state})
    return sorted(result, key=lambda d: d['name'])


def outcome(data, validators):
    """Pure abstract decision/effect contract; outputs are obligations, not events."""
    old = {'records': 'old', 'runtime': 'old', 'routing': 'old', 'surfaces': 'old'}
    result = {'diagnostic': None, 'activation': {}, 'drift': drift(data),
              'state': old, 'effects': [], 'unrelated': 'preserved', 'global_manifest': 'preserved',
              'unrelated_calls': [], 'removed': [], 'domain': 'open', 'convergence': 'selected-only'}

    def refuse(code):
        result['diagnostic'] = code
        return result

    error = plan_error(data, validators)
    if error:
        return refuse(error)
    # These statuses model independently supplied acceptance/qualification
    # records. They are not caller flags that grant runtime authority.
    requested = data.get('requested_outcome', 'slice-a-model')
    required = {'protected-command-adoption': ['profile-command-admission'],
                'managed-session-adoption': ['managed-session-skill-cli'],
                'owner-two-requirement-delivery': ['profile-command-admission', 'managed-session-skill-cli']}
    if requested != 'slice-a-model':
        if (requested not in required or any(
                data.get('companions', {}).get(name) != 'qualified'
                for name in required[requested])):
            return refuse('profile_skill_companion_required')
    active = activation(data)
    if data['operation'] == 'status':
        result['activation'] = active
        if data['phase'] != 'absent':
            result['diagnostic'] = 'profile_skill_recovery_pending'
        return result
    live = data['operation'] not in ('inactive', 'scoped-use')
    if live and data['routing'] != 'exclusive':
        return refuse('profile_skill_routing_unproven')
    if data['phase'] not in ('absent', 'preparing', 'prepared', 'committing', 'cleanup',
                             'rolling_back', 'rollback_cleanup'):
        result['domain'] = 'closed'
        return refuse('profile_skill_recovery_failed')
    for stale in data['stale']:
        if stale['owners'] == 'unknown':
            return refuse('profile_skill_ownership_unknown')
    names = {}
    for provider, surfaces in active.items():
        for command in surfaces['commands']:
            name = command.casefold() if data['case_insensitive'] else command
            if reserved_command(command, data['case_insensitive']):
                return refuse('environment_reserved_command_name')
            if name in names and names[name] != provider:
                return refuse('profile_skill_command_conflict')
            names[name] = provider
    for retained in data['retained_commands']:
        name = retained['command'].casefold() if data['case_insensitive'] else retained['command']
        if name in names and names[name] != retained['provider']:
            return refuse('profile_skill_command_conflict')
    for destination in data['unmanaged']:
        name = destination.casefold() if data['case_insensitive'] else destination
        if name in names:
            return refuse('environment_surface_unmanaged_conflict')
    if data['operation'] != 'recover':
        errors = {'signer': 'context_source_signer_rejected',
                  'audit': 'audit.capability.network-undeclared',
                  'driver': 'unsupported_build_driver', 'compile': 'profile_skill_compile_failed',
                  'receipt': 'profile_skill_plan_binding_invalid'}
        if data['fault'] in errors:
            return refuse(errors[data['fault']])
    if data['operation'] == 'recover':
        if data['phase'] in ('absent', 'preparing', 'rolling_back', 'rollback_cleanup'):
            result['effects'] = ['recover-old']
            return result
        result['effects'] = ['recover-new']
    else:
        result['effects'] = ['audit-selected', 'compile-selected', 'verify-receipts',
                             'journal-prepare', 'publish-lock-and-generation']
    result['activation'] = active
    result['state'] = {'records': 'new', 'runtime': 'new', 'routing': 'new' if live else 'old',
                       'surfaces': 'new' if data['operation'] != 'inactive' else 'old'}
    if data['fault'] == 'handled-adapter-conflict':
        result['diagnostic'] = 'environment_surface_unmanaged_conflict'
        result['state'].update(routing='old', surfaces='old')
        result['effects'].append('restore-in-place-preimages')
    elif data['fault'] == 'partial-adapter':
        result['diagnostic'] = 'profile_use_partial'
        result['state'].update(routing='old', surfaces='per-entry')
    result['removed'] = sorted(s['name'] for s in data['stale'] if s['owners'] == ['profile'])
    return result


def check_corpus(root=ROOT):
    validators = catalog(root)
    corpus = root / 'conformance' / FAMILY
    baseline = json.loads((corpus / 'baseline.json').read_text(encoding='utf-8'))
    cases = json.loads((corpus / 'cases.json').read_text(encoding='utf-8'))
    schemas = json.loads((corpus / 'schema-cases.json').read_text(encoding='utf-8'))
    for case in schemas:
        if validators[case['schema']].is_valid(case['instance']) != case['valid']:
            raise ValueError('schema verdict differs: ' + case['id'])
    for case in cases:
        if outcome(prepare(baseline, case), validators) != case['expected']:
            raise ValueError('semantic verdict differs: ' + case['id'])
    return len(schemas), len(cases)


if __name__ == '__main__':
    print('profile skill-plan specification cases:', check_corpus())
