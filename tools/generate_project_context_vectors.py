#!/usr/bin/env python3
"""Regenerate leaf-1 grammar bytes/verdicts, not runtime qualification evidence."""
import copy
import hashlib
import json
import re
import sys
from pathlib import Path

import project_context_leaf1 as leaf

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / 'conformance' / leaf.NAMESPACE
H = 'a' * 64


def examples():
    profile = {'name': 'sample', 'lock_sha256': H}
    registration = dict(kind='project-registration/1', checkout_id='sample',
                        project_root='/example/project', root_identity=H, profile=profile,
                        environment='codex_cli', home_ref='home:sample', worktree_ref='worktree:sample')
    context = dict(version=1, mode='admitted', context_ref='composition:sample',
                   context_sha256=H, project_root='/example/project', lease_ref='lease:sample')
    command = dict(version=1, operation='checked-d-path/1', tool_ref='tool:sample',
                   dispatcher_ref='dispatcher:sample', context_ref='composition:sample', context_sha256=H)
    files = [{'path': 'context/root.md', 'size': 2, 'sha256': H, 'mode': '0600'}]
    return {
        'registration': registration,
        'item': dict(kind='project-item/1', id='context', type='context', environment='codex_cli',
                     required=True, payload=dict(snapshot_ref='snapshot:sample', snapshot_sha256=H,
                                                lock_ref='lock:sample', lock_sha256=H)),
        'approval': dict(kind='project-approval/1', checkout_id='sample', item_id='context',
                         item_sha256=H, environment='codex_cli', approver_ref='principal:sample', ceiling_sha256=H),
        'generation': dict(kind='project-generation/1', registration_ref='registration:sample',
                           registration_sha256=H, items=[dict(item_id='context', item_sha256=H, approval_ref='approval:sample')]),
        'composition': dict(kind='project-composition/1', registration_ref='registration:sample',
                            registration_sha256=H, generation_sha256=H, profile=profile, environment='codex_cli',
                            adapter_ref='adapter:sample', adapter_sha256=H, policy_ref='policy:sample', policy_sha256=H,
                            memory='off', home_ref='home:sample', worktree_ref='worktree:sample',
                            materialization_sha256=H, command_owners=[dict(name='sample', item_id='skill', artifact_sha256=H)],
                            omitted=[dict(item_id='optional', reason='disabled')]),
        'lease': dict(kind='project-lease/1', lease_id='sample', context_ref='composition:sample', context_sha256=H,
                      checkout_id='sample', environment='codex_cli', home_ref='home:sample', owner_ref='principal:sample',
                      session_ref='session:sample', generation=1),
        'project-context': context,
        'command-environment': command,
        'fragment-members': {'project_context': context, 'command_environment': command},
        'root-binding': {'repository': {'root': '/example/project', 'primary_remote': None, 'root_commit': 'b' * 40},
                         'filesystem': {'device': '0', 'inode': '18446744073709551615'}},
        'snapshot-manifest': dict(version=1, files=files),
        'control-receipt': dict(version=1, files=files, adapter_sha256=H, policy_sha256=H, worktree_ref='worktree:sample'),
        'adapter': dict(kind='project-adapter/1', environment='codex_cli', provider_version='0.162.1', platform='linux',
                        surfaces=['commands', 'context', 'mcp', 'memory-off', 'native-source-exclusion', 'permissions', 'skills']),
    }


def set_at(value, path, replacement):
    result = copy.deepcopy(value)
    node = result
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = replacement
    return result


def schema_mutant(schema, path, value, *, terminal=True):
    # Preserve exact-end enforcement when narrowing another pattern gate.
    if path[-1] == 'pattern' and terminal:
        file = ROOT / 'schemas' / ((schema if '/' in schema else leaf.NAMESPACE + '/' + schema) + '.schema.json')
        original = json.loads(file.read_text())
        for key in path:
            original = original[key]
        guard = r'(?![\s\S])'
        if original.endswith(guard) and not value.endswith(guard):
            value += guard
    return dict(schema=schema, path=path, value=value)


def main():
    check = sys.argv[1:] == ['--check']
    if sys.argv[1:] and not check:
        raise ValueError('usage: generate_project_context_vectors.py [--check]')
    generated = {}
    records, _ = leaf.schemas()
    base = examples()
    cases = []

    def add(name, record, value=None, *, raw=None, gate=None, positive=None, mutant=None, claim=None):
        if raw is None:
            raw = leaf.ccj1_bytes(value)
        filename = 'bytes/' + name + '.json'
        generated[filename] = raw
        case = dict(name=name, record=record, file=filename, bytes_sha256=hashlib.sha256(raw).hexdigest(),
                    expected=None if gate is None else dict(code=leaf.INVALID, gate=gate),
                    claim=claim or (f'{record}: accepts this closed record' if gate is None else f'{record}: refuses {name}'))
        if gate is None:
            case['record_sha256'] = leaf.identity(value)
        else:
            case.update(positive=positive or record + '-valid', mutant=mutant)
        cases.append(case)
        return name

    def positive(name, record, value):
        return add(name, record, value)

    def bad(name, record, value, mutant, gate='schema', sibling=None):
        return add(name, record, value, gate=gate, positive=sibling, mutant=mutant)

    for record, value in base.items():
        positive(record + '-valid', record, value)
        schema = records[record]
        # Each closed top-level record rejects absent/null required members and
        # one unknown member. Controls relax only that field, never the object.
        for field in schema['required']:
            missing = copy.deepcopy(value); del missing[field]
            bad(record + '-missing-' + field, record, missing,
                schema_mutant(record, ['required'], [f for f in schema['required'] if f != field]))
            nullable = copy.deepcopy(schema['properties'][field])
            if field == 'payload':  # conditional arm still constrains payload
                continue
            bad(record + '-null-' + field, record, set_at(value, [field], None),
                schema_mutant(record, ['properties', field], {'anyOf': [nullable, {'type': 'null'}]}))
        bad(record + '-unknown', record, {**value, 'future': True},
            schema_mutant(record, ['properties', 'future'], {'type': 'boolean'}))
        discriminator = 'kind' if 'kind' in value else ('version' if 'version' in value else None)
        if discriminator:
            token = 'project-future/2' if discriminator == 'kind' else 2
            bad(record + '-future-version', record, set_at(value, [discriminator], token),
                schema_mutant(record, ['properties', discriminator], {'enum': [value[discriminator], token]}))
        if 'environment' in value:
            bad(record + '-later-environment', record, {**value, 'environment': 'pi'},
                schema_mutant('common', ['$defs', 'environment', 'enum'], ['claude_code', 'codex_cli', 'muse', 'pi']))
            for env in ('claude_code', 'muse'):
                positive(record + '-' + env, record, {**value, 'environment': env})

    # Nested objects are closed independently of their containing record.
    nested = [
        ('registration', ['profile'], 'common', ['$defs', 'profile']),
        ('item', ['payload'], 'item', ['allOf', 0, 'then', 'properties', 'payload']),
        ('generation', ['items', 0], 'generation', ['properties', 'items', 'items']),
        ('composition', ['command_owners', 0], 'composition', ['properties', 'command_owners', 'items']),
        ('composition', ['omitted', 0], 'composition', ['properties', 'omitted', 'items']),
        ('fragment-members', ['project_context'], 'project-context', []),
        ('fragment-members', ['command_environment'], 'command-environment', []),
        ('root-binding', ['repository'], 'workspace-trust-v1/workspace-trust-record-v1', ['$defs', 'repository']),
        ('root-binding', ['filesystem'], 'root-binding', ['properties', 'filesystem']),
        ('snapshot-manifest', ['files', 0], 'common', ['$defs', 'file']),
        ('control-receipt', ['files', 0], 'common', ['$defs', 'file']),
    ]
    for record, path, schema_name, schema_path in nested:
        schema_file = (ROOT / 'schemas' / (schema_name + '.schema.json') if '/' in schema_name else
                       ROOT / 'schemas' / leaf.NAMESPACE / (schema_name + '.schema.json'))
        node = json.loads(schema_file.read_text())
        for part in schema_path: node = node[part]
        current = base[record]
        for part in path: current = current[part]
        label = record + '-nested-' + '-'.join(map(str, path))
        bad(label + '-unknown', record, set_at(base[record], path, {**current, 'future': True}),
            schema_mutant(schema_name, schema_path + ['properties', 'future'], {'type': 'boolean'}))
        for field in node['required']:
            changed = copy.deepcopy(current); del changed[field]
            bad(label + '-missing-' + field, record, set_at(base[record], path, changed),
                schema_mutant(schema_name, schema_path + ['required'], [k for k in node['required'] if k != field]))

    # Positive boundaries and all payload/optional arms prevent reject-all fixes.
    skill = {**base['item'], 'id': 'skill', 'type': 'skill',
             'payload': {'snapshot_ref': 'snapshot:sample', 'snapshot_sha256': H}}
    positive('item-skill', 'item', skill)
    for transport in ('stdio', 'http'):
        server = ({'transport': 'stdio', 'command': 'sample-tool', 'args': ['--mode', 'sample']}
                  if transport == 'stdio' else {'transport': 'http', 'url': 'https://example.invalid/mcp'})
        server.update(env_names=['SAMPLE_A', 'SAMPLE_B'], environments=['claude_code', 'codex_cli'])
        item = {**base['item'], 'id': 'mcp', 'type': 'mcp', 'required': False,
                'payload': {'name': 'Sample_1', 'server': server, 'server_sha256': 'sha256:' + leaf.identity(server)}}
        positive('item-mcp-' + transport, 'item', item)
        bad('item-mcp-' + transport + '-mixed', 'item',
            set_at(item, ['payload', 'server', 'url' if transport == 'stdio' else 'command'],
                   'https://example.invalid/mcp' if transport == 'stdio' else 'sample-tool'),
            schema_mutant('v1/agent-mcp-v1', ['properties', 'server', 'oneOf', 0 if transport == 'stdio' else 1,
                                           'properties', 'url' if transport == 'stdio' else 'command'], {'type': 'string'}),
            sibling='item-mcp-' + transport)
        # A relaxed arm would reach digest validation; keep the changed record's
        # digest consistent so this is specifically a closed-arm counterexample.
        mixed = cases[-1]
        mixed_value = json.loads(generated[mixed['file']])
        mixed_value['payload']['server_sha256'] = 'sha256:' + leaf.identity(mixed_value['payload']['server'])
        raw = leaf.ccj1_bytes(mixed_value); generated[mixed['file']] = raw
        mixed['bytes_sha256'] = hashlib.sha256(raw).hexdigest()

    mcp = json.loads(generated['bytes/item-mcp-stdio.json'])
    def mcp_bad(name, path, value, mutant, gate='schema', rehash=True):
        changed = set_at(mcp, ['payload', 'server'] + path, value)
        if rehash:
            changed['payload']['server_sha256'] = 'sha256:' + leaf.identity(changed['payload']['server'])
        bad(name, 'item', changed, mutant, gate, 'item-mcp-stdio')

    positive('approval-grant', 'approval', {**base['approval'], 'grant_ref': 'grant:sample'})
    positive('project-context-off', 'project-context', {**base['project-context'], 'mode': 'off'})
    positive('fragment-no-command', 'fragment-members', {'project_context': base['project-context']})
    positive('composition-no-command', 'composition', {**base['composition'], 'command_owners': []})
    positive('generation-empty', 'generation', {**base['generation'], 'items': []})
    positive('lease-max-generation', 'lease', {**base['lease'], 'generation': leaf.SAFE_INTEGER})
    positive('root-binding-remote', 'root-binding', set_at(base['root-binding'], ['repository', 'primary_remote'], 'https://example.invalid/repo.git'))
    positive('adapter-macos', 'adapter', {**base['adapter'], 'platform': 'macos'})
    positive('adapter-no-capabilities', 'adapter', {**base['adapter'], 'surfaces': []})
    positive('snapshot-empty', 'snapshot-manifest', {'version': 1, 'files': []})
    positive('control-empty', 'control-receipt', {**base['control-receipt'], 'files': []})
    positive('id-max', 'registration', {**base['registration'], 'checkout_id': 'a' * 64})
    for name, invalid, pattern in (
            ('uppercase', 'Sample', '^[A-Za-z][a-z0-9_-]{0,63}$'),
            ('too-long', 'a' * 65, '^[a-z][a-z0-9_-]{0,64}$')):
        bad('id-' + name, 'registration', {**base['registration'], 'checkout_id': invalid},
            schema_mutant('common', ['$defs', 'id', 'pattern'], pattern))
    for name, invalid, pattern in (
            ('short', 'a' * 63, '^[0-9a-f]{63,64}$'),
            ('uppercase', 'A' * 64, '^[0-9a-fA]{64}$'),
            ('prefixed', 'sha256:' + H, '^(?:sha256:)?[0-9a-f]{64}$')):
        bad('hex-' + name, 'registration', {**base['registration'], 'root_identity': invalid},
            schema_mutant('common', ['$defs', 'hex', 'pattern'], pattern))

    # Every referenced tag is exercised at its real field, including nested arms.
    ref_fields = [
        ('registration', ['home_ref'], 'home'), ('registration', ['worktree_ref'], 'worktree'),
        ('item', ['payload', 'snapshot_ref'], 'snapshot'), ('item', ['payload', 'lock_ref'], 'lock'),
        ('approval', ['approver_ref'], 'principal'), ('approval', ['grant_ref'], 'grant'),
        ('generation', ['registration_ref'], 'registration'), ('generation', ['items', 0, 'approval_ref'], 'approval'),
        ('composition', ['adapter_ref'], 'adapter'), ('composition', ['policy_ref'], 'policy'),
        ('lease', ['context_ref'], 'composition'), ('lease', ['session_ref'], 'session'),
        ('project-context', ['lease_ref'], 'lease'), ('command-environment', ['tool_ref'], 'tool'),
        ('command-environment', ['dispatcher_ref'], 'dispatcher'),
    ]
    for record, path, tag in ref_fields:
        value = copy.deepcopy(base[record])
        if tag == 'grant': value['grant_ref'] = 'grant:sample'
        sibling = 'approval-grant' if tag == 'grant' else record + '-valid'
        bad('ref-' + tag + '-wrong-tag', record, set_at(value, path, 'command:sample'),
            schema_mutant('common', ['$defs', tag + '_ref', 'pattern'], '^(?:' + tag + '|command):[a-z][a-z0-9_-]{0,63}$'), sibling=sibling)
    bad('ref-url', 'registration', {**base['registration'], 'home_ref': 'https://example.invalid/home'},
        schema_mutant('common', ['$defs', 'home_ref', 'pattern'], '^(?:home:[a-z][a-z0-9_-]{0,63}|https://example[.]invalid/home)$'))
    bad('item-skill-context-leak', 'item', {**skill, 'payload': {**skill['payload'], 'lock_ref': 'lock:sample'}},
        schema_mutant('item', ['allOf', 1, 'then', 'properties', 'payload', 'properties', 'lock_ref'], {'$ref': 'common.schema.json#/$defs/lock_ref'}), sibling='item-skill')
    bad('item-required-not-boolean', 'item', {**base['item'], 'required': 1},
        schema_mutant('item', ['properties', 'required'], {'anyOf': [{'type': 'boolean'}, {'const': 1}]}))
    bad('composition-memory-on', 'composition', {**base['composition'], 'memory': 'on'},
        schema_mutant('composition', ['properties', 'memory'], {'enum': ['off', 'on']}))
    bad('lease-zero', 'lease', {**base['lease'], 'generation': 0},
        schema_mutant('lease', ['properties', 'generation', 'minimum'], 0))
    bad('filesystem-leading-zero', 'root-binding', set_at(base['root-binding'], ['filesystem', 'device'], '00'),
        schema_mutant('common', ['$defs', 'u64', 'pattern'], '^(?:00|0|[1-9][0-9]{0,19})$'))
    bad('filesystem-overflow', 'root-binding', set_at(base['root-binding'], ['filesystem', 'inode'], str(leaf.MAX_U64 + 1)),
        {'constant': 'MAX_U64', 'value': leaf.MAX_U64 + 1}, 'filesystem-u64')

    def files_case(name, files, mutant, gate='schema', record='snapshot-manifest', sibling=None):
        bad(name, record, {**base[record], 'files': files}, mutant, gate, sibling)
    entry = base['snapshot-manifest']['files'][0]
    for record in ('snapshot-manifest', 'control-receipt'):
        files_case(record + '-bad-mode', [{**entry, 'mode': '0644'}],
                   schema_mutant('common', ['$defs', 'file', 'properties', 'mode', 'enum'], ['0600', '0700', '0644']), record=record)
        positive(record + '-executable', record, {**base[record], 'files': [{**entry, 'mode': '0700'}]})
    for name, field, number, boundary in [('negative-size', 'size', -1, 'minimum'), ('file-too-big', 'size', 16777217, 'maximum')]:
        files_case(name, [{**entry, field: number}], schema_mutant('common', ['$defs', 'file', 'properties', field, boundary], number))
    for name, paths, mutant, gate in [
        ('files-unsorted', ['b', 'a'], {'source': 'file-order'}, 'file-order'),
        ('files-duplicate', ['a', 'a'], {'source': 'file-duplicate'}, 'file-alias'),
        ('files-case-alias', ['A', 'a'], {'source': 'file-case'}, 'file-alias'),
        ('files-unicode-alias', ['e\u0301', 'é'], {'source': 'file-unicode'}, 'file-alias'),
        ('files-ancestor', ['a', 'a/b'], {'source': 'file-ancestor'}, 'file-ancestor'),
        ('path-too-deep', ['/'.join(['a'] * 33)], {'constant': 'MAX_PATH_DEPTH', 'value': 33}, 'path-depth'),
        ('path-too-long', ['a' * 241], {'constant': 'MAX_PATH', 'value': 241}, 'string-bytes'),
    ]:
        files_case(name, [{**entry, 'path': p} for p in paths], mutant, gate)
    total = [{**entry, 'path': str(i), 'size': 16777216 if i < 4 else 1} for i in range(5)]
    files_case('inventory-too-big', total, {'constant': 'MAX_TOTAL', 'value': leaf.MAX_TOTAL + 1}, 'inventory-size')
    positive('inventory-max-bytes', 'snapshot-manifest', {'version': 1, 'files': total[:4]})
    # 10,000 entries cannot fit in a 1 MiB record with SHA-256 fields. Test the
    # file-count schema independently below; do not invent an unreachable record.
    # Keep complete-record fixtures below the earlier byte cap.
    bad('generation-duplicate-ids', 'generation', {**base['generation'], 'items': base['generation']['items'] * 2},
        {'source': 'generation-ids'}, 'generation-ids')
    maximum = [{**base['generation']['items'][0], 'item_id': f'i{i}'} for i in range(256)]
    positive('generation-max-items', 'generation', {**base['generation'], 'items': maximum})
    bad('generation-too-many', 'generation', {**base['generation'], 'items': maximum + [{**maximum[0], 'item_id': 'last'}]},
        schema_mutant('generation', ['properties', 'items', 'maxItems'], 257))
    bad('composition-too-many-commands', 'composition', {**base['composition'], 'command_owners': [base['composition']['command_owners'][0], {'name': 'other', 'item_id': 'other', 'artifact_sha256': H}]},
        schema_mutant('composition', ['properties', 'command_owners', 'maxItems'], 2))
    bad('fragment-digest-mismatch', 'fragment-members', set_at(base['fragment-members'], ['command_environment', 'context_sha256'], 'b' * 64),
        {'source': 'fragment-digest'}, 'fragment-context')
    bad('fragment-ref-mismatch', 'fragment-members', set_at(base['fragment-members'], ['command_environment', 'context_ref'], 'composition:other'),
        {'source': 'fragment-ref'}, 'fragment-context')
    bad('fragment-forbidden-path-prepend', 'fragment-members', {**base['fragment-members'], 'path_prepend': ['/example/bin']},
        schema_mutant('fragment-members', ['properties', 'path_prepend'], {'type': 'array', 'items': {'type': 'string'}}))
    bad('adapter-surfaces-unsorted', 'adapter', {**base['adapter'], 'surfaces': ['skills', 'context']},
        {'source': 'surface-order'}, 'surface-order')
    bad('adapter-surfaces-duplicate', 'adapter', {**base['adapter'], 'surfaces': ['context', 'context']},
        schema_mutant('adapter', ['properties', 'surfaces', 'uniqueItems'], False))
    bad('adapter-version-range', 'adapter', {**base['adapter'], 'provider_version': '^1.0.0'},
        schema_mutant('adapter', ['properties', 'provider_version', 'pattern'], r'^[^\s*<>=~|,]+$'))
    bad('root-parent', 'registration', {**base['registration'], 'project_root': '/example/../project'},
        {'source': 'root-parent'}, 'root-path')
    positive('root-max-bytes', 'registration', {**base['registration'], 'project_root': '/' + 'é' * 2047 + 'a'})
    bad('root-utf8-too-long', 'registration', {**base['registration'], 'project_root': '/' + 'é' * 2048},
        {'constant': 'MAX_ROOT', 'value': 4097}, 'string-bytes')
    bad('string-utf8-too-long', 'adapter', {**base['adapter'], 'provider_version': 'é' * 128 + 'a'},
        {'constant': 'MAX_STRING', 'value': 257}, 'string-bytes')
    positive('string-max-bytes', 'adapter', {**base['adapter'], 'provider_version': 'é' * 128})
    bad('repository-unsafe-remote', 'root-binding', set_at(base['root-binding'], ['repository', 'primary_remote'], 'https://example.invalid/repo?mode=1'),
        {'source': 'repository-remote'}, 'repository-remote')
    # MCP normalized objects have no absent/default ambiguity, preserve arg
    # order, use the owning character bounds and carry a prefixed digest.
    mcp_bad('mcp-env-order', ['env_names'], ['SAMPLE_B', 'SAMPLE_A'], {'source': 'server-normalization'}, 'server-normalization')
    mcp_bad('mcp-future-env', ['environments'], ['future'], {'source': 'server-environments'}, 'server-environments')
    changed = copy.deepcopy(mcp); changed['payload']['server_sha256'] = 'sha256:b' + leaf.identity(changed['payload']['server'])[1:]
    bad('mcp-wrong-digest', 'item', changed, {'source': 'server-digest'}, 'server-digest', 'item-mcp-stdio')
    absent = copy.deepcopy(mcp); del absent['payload']['server']['env_names']; absent['payload']['server_sha256'] = 'sha256:' + leaf.identity(absent['payload']['server'])
    bad('mcp-absent-normalized-env', 'item', absent, schema_mutant('common', ['$defs', 'server', 'allOf', 1, 'required'], []), sibling='item-mcp-stdio')
    mcp_bad('mcp-reserved-env', ['env_names'], ['PATH'], schema_mutant('v1/agent-mcp-v1', ['$defs', 'envNames', 'items', 'allOf', 1, 'not', 'pattern'], json.loads((ROOT / 'schemas/v1/agent-mcp-v1.schema.json').read_text())['$defs']['envNames']['items']['allOf'][1]['not']['pattern'].replace('PATH|HOME', 'HOME')))
    mcp_bad('mcp-env-duplicate', ['env_names'], ['SAMPLE_A', 'SAMPLE_A'], schema_mutant('v1/agent-mcp-v1', ['$defs', 'envNames', 'uniqueItems'], False))
    mcp_bad('mcp-command-path', ['command'], '/sample-tool', schema_mutant('v1/agent-mcp-v1', ['$defs', 'bareCommand', 'pattern'], r'^(?!\.{1,2}$)[^\\\s\u0000-\u001f\u007f]+$'))
    mcp_bad('mcp-argument-too-long', ['args'], ['a' * 8193], schema_mutant('v1/agent-mcp-v1', ['properties', 'server', 'oneOf', 0, 'properties', 'args', 'items', 'maxLength'], 8193))
    long_args = copy.deepcopy(mcp); long_args['payload']['server']['args'] = ['é' * 8192]; long_args['payload']['server_sha256'] = 'sha256:' + leaf.identity(long_args['payload']['server'])
    positive('mcp-owning-argument-bound', 'item', long_args)
    no_selectors = copy.deepcopy(mcp); del no_selectors['payload']['server']['environments']; no_selectors['payload']['server']['env_names'] = []; no_selectors['payload']['server_sha256'] = 'sha256:' + leaf.identity(no_selectors['payload']['server'])
    positive('mcp-absent-environments', 'item', no_selectors)

    bad('mcp-name-final-newline', 'item', set_at(mcp, ['payload', 'name'], 'Sample_1\n'),
        schema_mutant('item', ['allOf', 2, 'then', 'properties', 'payload', 'properties', 'name', 'pattern'], '^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$', terminal=False), sibling='item-mcp-stdio')
    bad('provider-version-final-newline', 'adapter', {**base['adapter'], 'provider_version': '0.162.1\n'},
        schema_mutant('adapter', ['properties', 'provider_version', 'pattern'], r'^[^\s*<>=^~|,]+$', terminal=False))
    bad('id-final-newline', 'registration', {**base['registration'], 'checkout_id': 'sample\n'},
        schema_mutant('common', ['$defs', 'id', 'pattern'], '^[a-z][a-z0-9_-]{0,63}$', terminal=False))
    bad('hex-final-newline', 'registration', {**base['registration'], 'root_identity': H + '\n'},
        schema_mutant('common', ['$defs', 'hex', 'pattern'], '^[0-9a-f]{64}$', terminal=False))
    bad('ref-final-newline', 'registration', {**base['registration'], 'home_ref': 'home:sample\n'},
        schema_mutant('common', ['$defs', 'home_ref', 'pattern'], '^home:[a-z][a-z0-9_-]{0,63}$', terminal=False))
    for record, path, token, schema_name, schema_path, allowed in [
        ('item', ['type'], 'shell', 'item', ['properties', 'type', 'enum'], ['context', 'skill', 'mcp']),
        ('project-context', ['mode'], 'automatic', 'project-context', ['properties', 'mode', 'enum'], ['off', 'admitted']),
        ('composition', ['omitted', 0, 'reason'], 'missing', 'composition', ['properties', 'omitted', 'items', 'properties', 'reason', 'enum'], ['disabled', 'unsupported']),
        ('adapter', ['platform'], 'windows', 'adapter', ['properties', 'platform', 'enum'], ['macos', 'linux']),
        ('adapter', ['surfaces'], ['hooks'], 'adapter', ['properties', 'surfaces', 'items', 'enum'], ['context', 'skills', 'mcp', 'commands', 'permissions', 'memory-off', 'native-source-exclusion']),
    ]:
        bad(record + '-forbidden-' + str(path[-1]), record, set_at(base[record], path, token),
            schema_mutant(schema_name, schema_path, allowed + ([token] if isinstance(token, str) else token)))
    bad('command-forbidden-operation', 'command-environment', {**base['command-environment'], 'operation': 'shell/1'},
        schema_mutant('command-environment', ['properties', 'operation'], {'enum': ['checked-d-path/1', 'shell/1']}))

    raw = leaf.ccj1_bytes(base['registration'])
    for name, data, gate, mutant in [
        ('json-duplicate-member', raw[:-1] + b',"checkout_id":"sample"}', 'duplicate-member', {'source': 'duplicate-member'}),
        ('json-invalid-utf8', raw.replace(b'sample', b'sam\xffle', 1), 'encoding', {'source': 'utf8'}),
        ('json-trailing-input', raw + b' {}', 'encoding', {'source': 'trailing-input'}),
        ('json-record-too-big', raw + b' ' * (leaf.MAX_BYTES + 1 - len(raw)), 'record-size', {'constant': 'MAX_BYTES', 'value': leaf.MAX_BYTES + 1}),
        ('json-too-deep', b'{"future":' + b'[' * 16 + b'0' + b']' * 16 + b'}', 'record-depth', {'constant': 'MAX_DEPTH', 'value': 17}),
        ('json-fraction', leaf.ccj1_bytes(base['lease']).replace(b'"generation":1', b'"generation":1.0'), 'ccj1', {'source': 'fraction'}),
        ('json-unsafe-integer', leaf.ccj1_bytes(base['lease']).replace(b'"generation":1', b'"generation":9007199254740992'), 'ccj1', {'constant': 'SAFE_INTEGER', 'value': leaf.SAFE_INTEGER + 1}),
        ('json-oversized-integer', leaf.ccj1_bytes(base['lease']).replace(b'"generation":1', b'"generation":' + b'9' * 5000), 'ccj1', {'source': 'oversized-integer'}),
        ('json-unpaired-surrogate', raw.replace(b'sample', b'\\ud800', 1), 'encoding', {'source': 'surrogate'}),
    ]:
        record = 'lease' if name in ('json-fraction', 'json-unsafe-integer', 'json-oversized-integer') else 'registration'
        add(name, record, raw=data, gate=gate, mutant=mutant)


    # Review regression witnesses preserve valid siblings, independent MCP
    # digests and exact refusal gates. Each plant narrows only its own rule.
    for record in ('snapshot-manifest', 'control-receipt'):
        zero = set_at(base[record], ['files', 0, 'size'], 0)
        sibling = positive(record + '-zero-size', record, zero)
        add(record + '-negative-zero', record,
            raw=leaf.ccj1_bytes(zero).replace(b'"size":0', b'"size":-0'),
            gate='ccj1', positive=sibling, mutant={'source': 'negative-zero'})
        for label, path in [('middle-dot', 'context./root.md'), ('middle-space', 'context /root.md')]:
            bad(record + '-' + label, record, set_at(base[record], ['files', 0, 'path'], path),
                {'source': 'path-component'}, 'path-component')
        old_path = json.loads((ROOT/'schemas/v1/common.schema.json').read_text())['$defs']['portablePath']['pattern']
        bad(record + '-path-final-lf', record,
            set_at(base[record], ['files', 0, 'path'], 'context/root.md\n'),
            schema_mutant('v1/common', ['$defs', 'portablePath', 'pattern'], old_path, terminal=False))
    legacy = json.loads((ROOT/'schemas/v1/common.schema.json').read_text())
    identifier = legacy['$defs']['identifier']['allOf'][0]['pattern']
    for record, path in [('registration', ['profile', 'name']), ('composition', ['profile', 'name']),
                         ('composition', ['command_owners', 0, 'name'])]:
        bad(record + '-' + '-'.join(map(str, path)) + '-final-lf', record,
            set_at(base[record], path, 'sample\n'),
            schema_mutant('v1/common', ['$defs', 'identifier', 'allOf', 0, 'pattern'], identifier, terminal=False))
    owning = json.loads((ROOT/'schemas/v1/agent-mcp-v1.schema.json').read_text())
    for label, path, replacement, schema_name, schema_path, original, sibling in [
        ('command', ['command'], 'sample-tool\n', 'v1/agent-mcp-v1', ['$defs', 'bareCommand', 'pattern'], owning['$defs']['bareCommand']['pattern'], 'item-mcp-stdio'),
        ('env', ['env_names'], ['SAMPLE_A\n'], 'v1/common', ['$defs', 'identifier', 'allOf', 0, 'pattern'], identifier, 'item-mcp-stdio'),
        ('url', ['url'], 'https://example.invalid/mcp\n', 'v1/agent-mcp-v1', ['$defs', 'httpsUrl', 'pattern'], owning['$defs']['httpsUrl']['pattern'], 'item-mcp-http'),
    ]:
        changed = set_at(json.loads(generated['bytes/' + sibling + '.json']), ['payload', 'server'] + path, replacement)
        changed['payload']['server_sha256'] = 'sha256:' + hashlib.sha256(
            json.dumps(changed['payload']['server'], ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        bad('mcp-' + label + '-final-lf', 'item', changed,
            schema_mutant(schema_name, schema_path, original, terminal=False), sibling=sibling)
    commit_pattern = json.loads((ROOT/'schemas/workspace-trust-v1/workspace-trust-record-v1.schema.json').read_text())['$defs']['repository']['properties']['root_commit']['pattern']
    for length in (40, 64):
        sibling = positive('root-commit-' + str(length), 'root-binding',
            set_at(base['root-binding'], ['repository', 'root_commit'], 'b' * length))
        bad('root-commit-final-lf-' + str(length), 'root-binding',
            set_at(base['root-binding'], ['repository', 'root_commit'], 'b' * (length - 1) + '\n'),
            schema_mutant('workspace-trust-v1/workspace-trust-record-v1', ['$defs', 'repository', 'properties', 'root_commit', 'pattern'], commit_pattern, terminal=False), sibling=sibling)
    for index, token in enumerate(('x', 'X', '1.x', '1.X', '1.2.x', '1.x.2', 'v1.x', '1.x-beta')):
        bad('adapter-wildcard-' + str(index), 'adapter', {**base['adapter'], 'provider_version': token},
            schema_mutant('adapter', ['properties', 'provider_version', 'pattern'], r'^[^\s*<>=^~|,]+$'))
    positive('adapter-concrete-prerelease', 'adapter', {**base['adapter'], 'provider_version': '1.2.3-x+build.4'})

    # Adopted CIP-0022 Q3 applies to normalized inline HTTP items too.
    # Rehash each server independently so a digest error cannot mask its URL.
    http = json.loads(generated['bytes/item-mcp-http.json'])
    def http_url(url):
        changed = set_at(http, ['payload', 'server', 'url'], url)
        changed['payload']['server_sha256'] = 'sha256:' + hashlib.sha256(
            json.dumps(changed['payload']['server'], ensure_ascii=False, sort_keys=True,
                       separators=(',', ':')).encode()).hexdigest()
        return changed
    for label, suffix in [('unicode', '/é'), ('encoded-dollar', '/%24')]:
        positive('mcp-url-' + label, 'item', http_url('https://example.invalid' + suffix))
    url_guard = json.loads((ROOT/'schemas'/leaf.NAMESPACE/'common.schema.json').read_text())[
        '$defs']['server']['allOf'][2]['properties']['url']['not']['pattern']
    for label, char in [('nul', '\0'), ('control', '\1'), ('del', '\x7f'), ('c1', '\x80'),
                        ('format', '\u200b'), ('bom', '\ufeff'), ('dollar', '$'),
                        ('brace-open', '{'), ('brace-close', '}'), ('backslash', '\\')]:
        add('mcp-url-' + label, 'item', http_url('https://example.invalid/a' + char + 'b'),
            gate='schema', positive='item-mcp-http',
            mutant=schema_mutant('common', ['$defs', 'server', 'allOf', 2,
                'properties', 'url', 'not', 'pattern'], '(?!' + re.escape(char) + ')' + url_guard),
            claim='item: a correctly hashed HTTP server refuses literal URL ' + label +
                  ' under adopted CIP-0022 Q3; ordinary HTTP sibling remains valid')

    manifest = dict(version=1, scope='closed member grammar only; no carrier or runtime qualification', cases=cases)
    generated['manifest.json'] = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    existing = {str(path.relative_to(CORPUS)) for path in CORPUS.rglob('*.json')}
    if existing - set(generated):
        raise ValueError('obsolete corpus files: ' + ', '.join(sorted(existing - set(generated))))
    for filename, raw in generated.items():
        path = CORPUS / filename
        if check:
            if not path.is_file() or path.read_bytes() != raw:
                raise ValueError(filename + ': regeneration differs')
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    print(f'{len(cases)} leaf-1 grammar cases: ' + ('regeneration matches' if check else 'written'))


if __name__ == '__main__':
    main()
