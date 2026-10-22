"""Profile MCP writer specification model; synthetic observations, no native I/O."""
import copy
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import skillfile_mcp as stage
from ccj1_grammar import exact_patterns

ROOT = Path(__file__).resolve().parents[1]
CAPABILITY = 'profile-mcp-native-writer-v1'
NAMESPACE = 'mcp-native-writer-v1'
PATHS = {'claude_code': '.agent-context/mcp/claude_code.json',
         'codex_cli': 'curator-mcp.config.toml'}
PINS = {
    'claude_code': ('2.1.305', 'ea3ea3c08d2a9634a4651e687fcf900d410c489bce2b00f22bd7352b91ba704f'),
    'codex_cli': ('0.162.1', '74c6a6d263f40d65f99c27a815275f5b4ed0bcc2baecc396b4cf3255498bdfc0'),
}
POLICY = 'mcp_contribution_policy_refused'
CONFLICT = 'mcp_native_entry_conflict'
UNREADABLE = 'environment_surface_unreadable'
SUCCESS = {'added', 'updated', 'unchanged', 'restored', 'removed', 'released'}
REQUIRED = frozenset({
    'claude-added', 'codex-added', 'markerless-claude', 'markerless-codex',
    'foreign-equal-claude', 'foreign-equal-codex', 'drift-skip-claude',
    'drift-skip-codex', 'restore-claude', 'restore-codex', 'scope-project',
    'muse-required', 'codex-a-collision', 'codex-b-late-collision',
    'mixed-refusal-total', 'schema1-no-effect', 'schema2-no-effect',
})


def byte_digest(text):
    return 'sha256:' + hashlib.sha256(text.encode('utf-8')).hexdigest()


def schema_valid(name, value):
    schema = exact_patterns(json.loads((ROOT/'schemas'/NAMESPACE/(name+'.schema.json')).read_text()))
    return Draft202012Validator(schema, registry=stage.registry()).is_valid(value)


def ownership_valid(document):
    if not schema_valid('ownership-v1', document):
        return False
    names = [record['name'] for record in document['records']]
    return names == sorted(set(names))


def owns(observation, profile, environment, path, name):
    document = observation.get('ownership')
    if (observation.get('protected') is not True or not isinstance(document, dict)
            or not ownership_valid(document)
            or any(document.get(k) != v for k, v in
                   [('profile_id', profile), ('environment', environment), ('path', path)])):
        return None
    return next((r for r in document['records'] if r['name'] == name), None)


def foreign_conflict(entry, owned):
    return entry is not None and owned is None


def qualified(facts, environment, server):
    pin = facts.get('pins', {}).get(environment, {})
    return (environment in PINS and facts.get('platform') == 'darwin-arm64'
            and (pin.get('version'), pin.get('sha256')) == PINS[environment]
            and server['transport'] == 'stdio')


def native_entry(environment, name, server):
    # Pure encoding of new owned bytes. This is not a lossless native parser.
    if environment == 'claude_code':
        return stage.canonical({'type': 'stdio', 'command': server['command'],
                                'args': server['args']}).decode('utf-8')
    quote = lambda value: json.dumps(value, ensure_ascii=False)
    return (f'[mcp_servers.{name}]\ncommand = {quote(server["command"])}\n'
            f'args = {quote(server["args"])}\n')


def action_allowed(facts, environment, name, operation, server_hash, content_hash):
    record = facts.get('actions', {}).get(environment, {}).get(name)
    wanted = dict(scope='profile', profile_id=facts['profile_id'],
                  environment=environment, path=PATHS[environment], name=name,
                  server_sha256=server_hash, content_sha256=content_hash,
                  operation=operation, policy_sha256=facts['policy_sha256'], state='active')
    return (facts.get('action_protected') is True and facts.get('policy_allows') is True
            and isinstance(record, dict) and schema_valid('action-v1', record)
            and all(record.get(key) == value for key, value in wanted.items()))


def pair(facts, server, environment):
    name = server['name']; definition = server['server']
    path = PATHS.get(environment) if qualified(facts, environment, definition) else None
    row = dict(name=name, environment=environment, path=path,
               outcome='skipped: unsupported', code=None)
    observation = facts.get('observations', {}).get(environment, {}).get(name, {})
    effect = dict(name=name, environment=environment,
                  entry=observation.get('entry'), ownership=copy.deepcopy(observation.get('ownership')),
                  foreign_bytes=observation.get('foreign_bytes', ''), write_native=False, write_ownership=False)
    if environment not in {'claude_code', 'codex_cli', 'muse'}:
        return row, effect, None
    def refuse(code):
        row.update(outcome='refused', code=code)
        return row, effect, code
    if facts.get('scope') != 'profile':
        return refuse(POLICY)
    if path is None:
        return refuse(POLICY)
    if facts.get('source_gate'):
        return refuse(facts['source_gate'])
    if observation.get('read', 'ok') != 'ok' or observation.get('marker_read', 'ok') != 'ok':
        return refuse(UNREADABLE)
    if observation.get('legacy_link'):
        return refuse(POLICY)
    if environment == 'codex_cli':
        base = facts.get('codex_base', {})
        if base.get('read', 'ok') != 'ok':
            return refuse(UNREADABLE)
        if name in base.get('names', []):
            row['outcome'] = 'conflict: foreign entry'
            return row, effect, CONFLICT
    owned = owns(observation, facts['profile_id'], environment, path, name)
    current = observation.get('entry')
    if foreign_conflict(current, owned):
        row['outcome'] = 'conflict: foreign entry'
        return row, effect, CONFLICT
    operation = facts.get('operation', 'none')
    removed = server.get('removed', False)
    if removed and owned is None:
        return refuse(POLICY)
    desired = native_entry(environment, name, definition)
    server_hash = stage.digest(stage.normalize_server(definition))
    content_hash = server['content_sha256']
    drift = owned is not None and (current is None or byte_digest(current) != owned['installed_sha256'])
    changed = owned is not None and (server_hash != owned['server_sha256'] or content_hash != owned['content_sha256'])
    if operation != 'none':
        if owned is None:
            return refuse(POLICY)
        if operation in {'remove', 'release'}:
            server_hash, content_hash = owned['server_sha256'], owned['content_sha256']
        if not action_allowed(facts, environment, name, operation, server_hash, content_hash):
            return refuse(POLICY)
    elif drift or removed:
        row['outcome'] = 'skipped: drift'
        return row, effect, None
    elif changed:
        return refuse(POLICY)
    if operation == 'replace' and drift:
        return refuse(POLICY)  # drift needs restore, not an incidental update
    if operation in {'remove', 'release'}:
        row['outcome'] = 'removed' if operation == 'remove' else 'released'
        remaining = copy.deepcopy(observation['ownership'])
        remaining['records'] = [r for r in remaining['records'] if r['name'] != name]
        effect.update(ownership=remaining if remaining['records'] else None, write_ownership=True)
        if operation == 'remove':
            effect.update(entry=None, write_native=current is not None)
    elif owned is not None and not drift and not changed:
        row['outcome'] = 'unchanged'
    else:
        row['outcome'] = 'restored' if operation == 'restore' else ('updated' if owned else 'added')
        record = dict(name=name, owner='curator', server_sha256=server_hash,
                      content_sha256=content_hash,
                      preimage_sha256=byte_digest(current) if current is not None else None,
                      installed_sha256=byte_digest(desired))
        records = [r for r in (observation.get('ownership') or {}).get('records', []) if r['name'] != name]
        records.append(record); records.sort(key=lambda r: r['name'])
        effect.update(entry=desired, write_native=current != desired, write_ownership=True,
                      ownership=dict(schema_version=1, capability=CAPABILITY, scope='profile',
                                     profile_id=facts['profile_id'], environment=environment,
                                     path=path, records=records))
    return row, effect, None


def evaluate(facts):
    """Observe supplied facts, return intended effects; never publish them."""
    facts = copy.deepcopy(facts)
    if facts.get('manifest_version') in {1, 2}:
        return dict(code=None, rows=[], effects=[], mutated=False)
    rows = []; effects = []; codes = []
    for server in sorted(facts['servers'], key=lambda s: s['name']):
        writable = [env for env in PATHS if qualified(facts, env, server['server'])]
        environments = server['server'].get('environments', writable)
        for environment in sorted(environments):
            if environment not in stage.ENVIRONMENTS:
                return dict(code='mcp_declaration_invalid', rows=[], effects=[], mutated=False)
            row, effect, code = pair(facts, server, environment)
            rows.append(row); effects.append(effect)
            if code:
                codes.append(code)
    code = codes[0] if codes else None
    if code:
        # No planned mutation or false successful row survives a set-level refusal.
        for row in rows:
            if row['outcome'] in SUCCESS:
                row.update(outcome='refused', code=code)
        effects = []
    return dict(code=code, rows=rows, effects=effects, mutated=False)


def check_case(case):
    result = evaluate(case['input'])
    if result != case['expected']:
        raise ValueError(f"MCP writer verdict mismatch: {case['id']}")


def check_corpus(root=ROOT):
    corpus = root/'conformance'/NAMESPACE
    cases = json.loads((corpus/'cases.json').read_text())
    inventory = json.loads((corpus/'coverage.json').read_text())
    ids = [c['id'] for c in cases]
    if len(ids) != len(set(ids)) or inventory['cases'] != ids or not REQUIRED <= set(ids):
        raise ValueError('MCP writer case inventory mismatch')
    for case in cases:
        check_case(case)
    return len(cases), sum(c['expected']['code'] is not None for c in cases)
