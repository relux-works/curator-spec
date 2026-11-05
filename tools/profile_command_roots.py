"""Independent bounded specification models. No installed runtime is qualified."""
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
from jsonschema import Draft202012Validator, ValidationError
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / 'schemas/profile-command-roots-v1'
CORPUS = ROOT / 'conformance/profile-command-roots-v1'

# Requirement custody is independent of the generator. Adding/removing vectors
# requires an explicit change here; generator agreement alone is insufficient.
REQUIRED = {
    'cases': set('''valid-root valid-windows valid-script realistic-shape profile-64 profile-64-windows path-240 path-241 tampered-root missing-root
        tampered-marker missing-marker tampered-receipt tampered-inventory tampered-pin
        missing-pin inventory-pin older-fragment linked-artifact hardlinked-artifact
        unsafe-mode readable-root root-object-substitution file-object-substitution
        wrong-owner platform-substitution reserved-name colliding-skills device-name
        foreign-root missing-receipt unlisted-helper unknown-fragment-field path-overflow
        command-path-overflow windows-path-list windows-alternate-stream profile-device
        profile-grammar marker-binding receipt-binding inventory-schema marker-schema
        receipt-schema receipt-command inventory-command wrong-chain script-target
        script-digest script-cycle windows-cmd-target windows-extra-suffix native-cap
        script-cap file-cap metadata-cap metadata-pin chain-depth file-mode file-owner
        empty-exports plan-union file-size chain-kind forwarder-bytes executable-pin
        chain-confinement root-dacl windows-file-dacl malformed-metadata duplicate-metadata'''.split()),
    'references': set('''reference-valid reference-second-resource reference-windows reference-gateway reference-id
        reference-command reference-binding reference-owner reference-settings
        reference-distribution reference-digest reference-revision reference-cap reference-root-cap
        reference-unexported reference-unknown reference-external reference-signature'''.split()),
    'launchers': set('''launcher-valid launcher-windows launcher-ambient-first
        launcher-root-absent launcher-path-value launcher-binding launcher-prior
        launcher-lease launcher-schema launcher-session-schema launcher-session-generation
        launcher-session-profile launcher-session-id launcher-session-phase'''.split()),
    'retention': set('''retention-valid retention-missing retention-descriptor
        retention-reference retention-binding retention-cap retention-unknown'''.split()),
    'lifecycle': set('''retained-hook session-live snapshot-live rollback-live journal-live
        descendant-live unknown-live installed-live permitted-gc missing-root-hook
        purge-live purge-empty'''.split()),
    'compatibility': set('''new-new new-old old-new old-old no-commands legacy-v4
        unfenced-activation'''.split()),
    'hooks': set('''hook-selected-valid hook-unrelated-tamper hook-selected-tamper
        hook-metadata-tamper hook-command-missing'''.split()),
    'sessions': set('''session-active session-unknown session-release session-dead-pid
        session-descendant session-break session-break-unfenced session-schema
        session-incarnation session-request session-profile session-generation session-discriminator'''.split()),
    'transactions': set('''repair-tampered-launch repair-valid-launch repair-explicit
        repair-pinned-restore repair-stale-session repair-inputs-differ repair-generation-reused repair-input-missing update-refused
        journal-preparing journal-prepared journal-committing journal-cleanup
        journal-rolling-back journal-rollback-cleanup journal-unknown'''.split()),
}


@lru_cache(maxsize=1)
def validators():
    registry = Registry()
    for directory in [ROOT/'schemas/v1', ROOT/'schemas/profile-command-path-v1',
                      ROOT/'schemas/rc7-carriers-v1', ROOT/'schemas/profile-codex-settings-v1', SCHEMAS]:
        for path in directory.glob('*.json'):
            data = json.loads(path.read_text())
            Draft202012Validator.check_schema(data)
            if '$id' in data:
                registry = registry.with_resource(data['$id'], Resource.from_contents(data))
    result = {p.name: Draft202012Validator(json.loads(p.read_text()), registry=registry)
              for p in SCHEMAS.glob('*.json')}
    # In-memory fixture composition, NOT a second normative v5 carrier. Preserve
    # rc7 Codex ownership verbatim; model only the proposed B-a member/path delta.
    model = deepcopy(json.loads((ROOT/'schemas/rc7-carriers-v1/launch-env-fragment-v5.schema.json').read_text()))
    leaf = result['fragment-members.schema.json'].schema
    model['$id'] = leaf['$id'].replace('fragment-members', 'launch-fragment-model')
    model['properties'].update(deepcopy(leaf['properties']))
    model['required'] += leaf['required']
    model['$defs']['absolutePath'] = deepcopy(leaf['$defs']['absolutePath'])
    model['properties']['profile']['properties']['name'] = deepcopy(
        result['session-pin.schema.json'].schema['properties']['profile'])
    registry = registry.with_resource(model['$id'], Resource.from_contents(model))
    result['launch-fragment-model'] = Draft202012Validator(model, registry=registry)
    return result


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


class Refusal(Exception):
    pass


def require(condition, reason):
    if not condition:
        raise Refusal(reason)


def valid_name(name):
    return (bool(re.fullmatch('[a-z][a-z0-9-]{0,62}', name))
            and not name.startswith('curator-') and not device(name))


def device(name):
    return name.lower().split('.')[0] in {
        'con', 'prn', 'aux', 'nul', *[f'com{i}' for i in range(1, 10)],
        *[f'lpt{i}' for i in range(1, 10)]}


def absolute(path, windows=False):
    pattern = r'[A-Za-z]:/[^:;\\\x00-\x1f\x7f]+' if windows else r'/[^:;\\\x00-\x1f\x7f]+'
    return (bool(re.fullmatch(pattern, path)) and all(
        c not in {'.', '..', ''} and not c.endswith(('.', ' ')) and not device(c)
        for c in path.split('/')[1:]))


def bounded_path(path, windows=False):
    return (absolute(path, windows) and len(path.encode()) <= 240
            and (not windows or len(path.encode('utf-16-le')) // 2 <= 240)
            and all(len(c.encode()) <= 255 for c in path.split('/')))


def root_path(state):
    t = state['trusted']; b = state['fragment']['command_root']
    return (t['manager'] + '/environments/' + t['profile'] + '/commands/'
            + b['generation'] + '/' + b['platform'] + '/bin')


def metadata(obj, windows):
    keys = ['owner', 'filesystem_id', 'object_id']
    keys += ['security_descriptor_sha256'] if windows else ['mode']
    return dict(platform='windows' if windows else 'posix', **{k: obj[k] for k in keys})


def strict_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate metadata key')
        result[key] = value
    return result


def root_check(state, checks, selected=None):
    f = state['fragment']; t = state['trusted']; o = state['observed']
    require(not device(t['profile']), 'profile-device')
    require(bool(re.fullmatch('[A-Za-z0-9](?:[A-Za-z0-9._-]{0,62}[A-Za-z0-9_-])?', t['profile'])), 'profile-grammar')
    require(checks['launch-fragment-model'].is_valid(f), 'fragment-schema')
    b = f['command_root']; names = t['names']; windows = b['platform'].startswith('windows-')
    require(f['profile'] == {'name': t['profile'], 'lock_sha256': b['lock_sha256']}
            and b == t['binding'], 'fragment-binding')
    require(b['platform'] == t['platform'], 'platform')
    require(1 <= len(names) <= 256 and names == sorted(set(names))
            and all(valid_name(n) for n in names), 'export-names')
    exports = t['exports']
    require(len({c['name'] for c in exports}) == len(exports), 'collision')
    require(sorted(c['name'] for c in exports) == names, 'plan-union')
    root = root_path(state)
    require(f['path_prepend'] == root, 'root-path')
    require(o['root_kind'] == 'directory', 'root-kind')
    require(o['root_owner'] == t['operator'], 'root-owner')
    require((o['root_security_descriptor_sha256'] == t['private_dacl'] if windows
             else o['root_mode'] == 0o700), 'root-protection')
    for key in ['marker', 'receipt', 'inventory']:
        require(len(t[key].encode()) <= 1024**2, 'metadata-cap')
        require(o[key] == t[key] and sha(t[key]) == b[key+'_sha256'], key+'-pin')
    try:
        marker, receipt, inventory = [json.loads(o[k], object_pairs_hook=strict_pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError('nonfinite')))
            for k in ['marker', 'receipt', 'inventory']]
    except (ValueError, TypeError) as exc:
        raise Refusal('metadata-json') from exc
    require(checks['generation-marker.schema.json'].is_valid(marker), 'marker-schema')
    require(checks['root-receipt.schema.json'].is_valid(receipt), 'receipt-schema')
    require(checks['inventory.schema.json'].is_valid(inventory), 'inventory-schema')
    base = {k: v for k, v in b.items() if k not in ['receipt_sha256', 'marker_sha256']}
    require(marker['binding'] == base and marker['profile'] == t['profile']
            and marker['receipt_sha256'] == b['receipt_sha256'], 'marker-binding')
    require(receipt['binding'] == base and receipt['profile'] == t['profile'], 'receipt-binding')
    root_obj = dict(owner=o['root_owner'], filesystem_id=o['root_filesystem_id'], object_id=o['root_object_id'])
    root_obj.update(security_descriptor_sha256=o.get('root_security_descriptor_sha256'), mode=o.get('root_mode'))
    require(inventory['root'] == {'path': root, 'metadata': metadata(root_obj, windows)}, 'root-object')
    require([c['name'] for c in receipt['commands']] == names, 'receipt-commands')
    require([c['name'] for c in inventory['commands']] == names, 'inventory-commands')
    commands = {c['name']: c for c in receipt['commands']}
    chains = {c['name']: c['chain'] for c in inventory['commands']}
    paths = {hop['path'] for chain in chains.values() for hop in chain}
    require(set(o['files']) == paths, 'file-inventory')
    all_paths = [root+'/.curator-profile-command-root.json', root.rsplit('/', 1)[0]+'/generation.json', *paths]
    require(all(bounded_path(p, windows) for p in all_paths), 'path-limit')
    require(len(paths) <= 1024, 'file-cap')
    require(sum(a['size'] for a in o['files'].values() if a['format'] == 'native') <= 1024**3, 'native-cap')
    require(sum(a['size'] for a in o['files'].values() if a['format'] != 'native') <= 64*1024**2, 'script-cap')
    for name, chain in chains.items():
        if selected is not None and name != selected:
            continue
        require(len({h['path'] for h in chain}) == len(chain), 'chain-cycle')
        first = root+'/'+name+('.cmd' if windows else '')
        require(chain[0]['path'] == first, 'chain-entry')
        for i, hop in enumerate(chain):
            require(any(hop['path'].startswith(p+'/') for p in t['boundaries']), 'chain-confinement')
            a = o['files'][hop['path']]
            require(a['kind'] == 'regular' and a['links'] == 1, 'file-kind')
            require(a['owner'] == t['operator'], 'file-owner')
            require((a['security_descriptor_sha256'] == t['private_dacl'] if windows
                     else a['mode'] == 0o500), 'file-protection')
            require(hop['metadata'] == metadata(a, windows), 'file-object')
            require(a['size'] == len(a['bytes'].encode()), 'file-size')
            require(hop['sha256'] == 'sha256:'+sha(a['bytes']), 'file-digest')
            terminal = i == len(chain)-1
            require(hop['kind'] == ('executable' if terminal else 'forwarder'), 'chain-kind')
            expected_target = None if terminal else chain[i+1]['path']
            require(hop['target'] == expected_target, 'chain-target')
            # This spec model uses a deliberately restricted fixed dispatcher
            # encoding, not a claim to decode real shell/batch scripts.
            require(terminal or a['bytes'] == 'FIXTURE-FORWARD/1\n'+expected_target+'\n', 'forwarder-bytes')
        require(commands[name]['executable_sha256'] == chain[-1]['sha256'].removeprefix('sha256:'), 'executable-pin')


def hook_check(case, checks):
    require(case['command'] in case['root']['trusted']['names'], 'hook-command')
    root_check(case['root'], checks, selected=case['command'])


def gateway_path(state, command, resource='/settings/hooks'):
    t = state['trusted']; windows = t['platform'].startswith('windows-')
    return t['manager']+'/command-gateways/'+t['profile']+'/'+sha(resource)+'/bin/'+command+('.cmd' if windows else '')


def reference_check(case, checks):
    s = case['root']; r = case['record']; t = s['trusted']; b = s['fragment']['command_root']
    require(checks['persistent-reference.schema.json'].is_valid(r), 'reference-schema')
    require(r['id'] == case['id_authority'], 'reference-id')
    require(r['profile'] == t['profile'] and r['binding'] == b, 'reference-binding')
    require(r['command'] in t['names'], 'reference-command')
    require(r['owner'] == t['operator'] == case['caller'], 'reference-owner')
    require(r['settings_resource'] == case['settings_authority']
            and bounded_path(r['settings_resource'], t['platform'].startswith('windows-')), 'reference-settings')
    require(r['gateway'] == gateway_path(s, r['command'], r['settings_resource'])
            and bounded_path(r['gateway'], t['platform'].startswith('windows-')), 'reference-gateway')
    require(r['distribution_sha256'] == case['distribution_authority'], 'reference-distribution')
    require(r['gateway_sha256'] == sha(case['gateway_bytes']), 'reference-digest')
    require(r['revision'] == case['revision_authority'], 'reference-revision')
    require(case['reference_count'] <= 256 and case['root_count'] <= 256, 'reference-cap')
    require(case['externally_verified'], 'reference-external')
    require(case['signature_verified'], 'reference-signature')
    root_check(s, checks)


def launcher_check(case, checks):
    s = case['root']; r = case['record']; b = s['fragment']['command_root']
    require(checks['launcher-state.schema.json'].is_valid(r), 'launcher-schema')
    require(r['command_root'] == b, 'launcher-binding')
    prior = r['prior_state']; pb = prior['binding']
    require(pb['profile'] == s['trusted']['profile']
            and pb['lock_sha256'] == 'sha256:'+b['lock_sha256']
            and pb['plan_sha256'] == 'sha256:'+b['plan_sha256'], 'launcher-prior')
    pin = case['session_pin']
    require(checks['session-pin.schema.json'].is_valid(pin), 'launcher-session-schema')
    require(r['lease_id'] == case['lease_authority'] == pin['lease_id']
            and pin['profile'] == s['trusted']['profile'] and pin['binding'] == b
            and pin['phase'] == 'active', 'launcher-lease')
    expected = case['protected_tools']+[s['fragment']['path_prepend']]+case['base_path']
    require(r['effective_path'] == expected, 'launcher-order')
    sep = ';' if b['platform'].startswith('windows-') else ':'
    require(r['path_value'] == sep.join(expected), 'launcher-path-value')
    root_check(s, checks)


def retention_check(case, checks):
    r = case['record']
    require(len(r['roots']) <= 256 and len(r['references']) <= 256, 'retention-cap')
    require(checks['snapshot-retention.schema.json'].is_valid(r), 'retention-schema')
    require(r['descriptor_sha256'] == sha(case['descriptor']), 'retention-descriptor')
    require(r['roots'] == case['roots_authority'], 'retention-roots')
    require(r['references'] == case['references_authority'], 'retention-references')
    require(all(p in case['available_roots'] for p in r['roots'])
            and all(i in case['available_references'] for i in r['references']), 'retention-missing')


def session_check(case, checks):
    r = case['record']
    require(checks['session-pin.schema.json'].is_valid(r), 'session-schema')
    require(r['profile'] == case['profile_authority']
            and r['binding'] == case['binding_authority'], 'session-binding')
    require(r['request_id'] == case['request_authority'], 'session-request')
    require((r['boot_id'], r['process_domain'], r['process_started_at'])
            == tuple(case['incarnation_authority']), 'session-incarnation')
    if case['operation'] == 'release':
        require(case['observer_confirmed'] and case['descendants_quiescent'], 'session-unconfirmed')
    if case['operation'] == 'break':
        require(case['operator'] and case['fenced'] and case['revision'] == r['revision']
                and bool(case['reason']) and case['audit_durable'], 'session-break-unconfirmed')


def decision(check, state, checks=None):
    try:
        check(state, validators() if checks is None else checks)
    except Refusal as exc:
        reason = str(exc)
        if reason in {'reference-cap', 'retention-cap'}:
            code = 'profile_command_reference_limit'
        elif reason == 'reference-owner':
            code = 'profile_command_reference_authority'
        elif reason in {'reference-id', 'reference-settings', 'reference-revision', 'session-request'}:
            code = 'profile_command_reference_conflict'
        elif reason in {'session-unconfirmed', 'session-break-unconfirmed'}:
            code = 'profile_command_reference_unconfirmed'
        else:
            code = 'profile_command_root_invalid'
        return (code, reason)
    return ('accept', 'verified')


def verdict(state, checks=None):
    return decision(root_check, state, checks)[0]


def lifecycle(state):
    live = any(state[k] for k in ['reference', 'session', 'snapshot', 'rollback',
                                  'journal', 'descendant', 'unknown', 'installed'])
    if state['operation'] == 'purge':
        return 'profile_command_root_in_use' if live else 'collect'
    if state['reference']:
        return 'profile_command_root_invalid' if state['missing'] else 'accept'
    return 'retain' if live else 'collect'


def compatibility(state):
    if not state['commands']:
        return 'legacy-no-prepend'
    if not state['fenced'] or not state['manager_new']:
        return 'refuse-before-resolve'
    if state['fragment'] != 5:
        return 'refuse-before-start'
    return 'verify-v5' if state['launcher_new'] else 'reject-v5'


def transaction(state):
    op = state['operation']; old = state['before']; staged = state['staged']
    if op == 'resolve-repair':
        outcome = 'unchanged' if state['valid'] else 'refuse-unchanged'
    elif op == 'explicit-repair':
        same_inputs = all(staged[k] == old[k] for k in
                          ['lock', 'source', 'plan', 'executable', 'build_receipt', 'unrelated'])
        outcome = ('fresh-generation-preserve-old' if state['inputs'] and same_inputs
                   and state['new_generation'] != state['old_generation'] else 'refuse-unchanged')
    elif op == 'refused-update':
        outcome = 'all-preimages-old'
    else:
        outcome = {'preparing': 'all-preimages-old', 'prepared': 'complete-new',
                   'committing': 'complete-new', 'cleanup': 'complete-new',
                   'rolling_back': 'all-preimages-old', 'rollback_cleanup': 'all-preimages-old'
                   }.get(state['phase'], 'refuse-preserve-journal')
    publish = outcome in {'complete-new', 'fresh-generation-preserve-old'}
    return dict(outcome=outcome, live=staged if publish else old,
                preserved_old=old, pending_journal=outcome == 'refuse-preserve-journal',
                evidence_generations=([state['old_generation'], state['new_generation']]
                                      if publish or outcome == 'refuse-preserve-journal'
                                      else [state['old_generation']]))


class HookModel:
    """Executable contract state machine, not a filesystem/process witness."""
    def __init__(self, root):
        self.roots = {root['fragment']['command_root']['generation']: root}
        self.current = next(iter(self.roots)); self.refs = {}; self.requests = {}; self.terminal = set()
        self.active = {}; self.rollback = set(); self.serial = 0; self.revisions = {}; self.release_revisions = {}

    def install(self, root):
        require(verdict(root) == 'accept', 'hook-root')
        self.current = root['fragment']['command_root']['generation']
        self.roots[self.current] = root

    def retain(self, resource, request):
        key = (resource, self.current)
        if request in self.requests:
            require(self.requests[request][0] == key, 'request-conflict')
            return self.requests[request][1]
        require(len(self.requests) < 4096, 'reference-cap')
        existing = next((i for i, r in self.refs.items() if r == key), None)
        require(existing is not None or len(self.refs) < 256, 'reference-cap')
        if existing is None:
            self.serial += 1; existing = sha(str(self.serial)); self.refs[existing] = key; self.revisions[existing] = 1
        self.requests[request] = (key, existing)
        return existing

    def list(self):
        return sorted({*self.refs, *self.terminal})

    def activate(self, reference, settings_proved, if_revision):
        require(reference in self.refs and settings_proved, 'settings-unconfirmed')
        require(self.revisions[reference] == if_revision, 'revision-conflict')
        resource = self.refs[reference][0]
        previous = self.active.get(resource)
        if previous is not None and previous != reference:
            self.rollback.add(previous)
            self.revisions[previous] += 1
        self.rollback.discard(reference)
        self.active[resource] = reference
        self.revisions[reference] += 1

    def release(self, reference, settings_removed, if_revision):
        require(settings_removed and reference not in self.active.values(), 'settings-unconfirmed')
        if reference in self.terminal:
            require(self.release_revisions[reference] == if_revision, 'revision-conflict')
            return
        require(reference in self.revisions and self.revisions[reference] == if_revision, 'revision-conflict')
        self.rollback.discard(reference)
        if reference in self.refs:
            self.release_revisions[reference] = if_revision
            self.terminal.add(reference)
            del self.refs[reference]
            self.revisions[reference] += 1

    def restore_rollback(self, reference, settings_proved, if_revision):
        require(reference in self.rollback, 'rollback-missing')
        self.activate(reference, settings_proved, if_revision)

    def gc(self):
        live = {self.current, *(generation for _, generation in self.refs.values())}
        self.roots = {g: s for g, s in self.roots.items() if g in live}

    def invoke(self, resource='/settings/hooks'):
        reference = self.active.get(resource)
        require(reference in self.refs, 'reference-missing')
        generation = self.refs[reference][1]
        require(generation in self.roots, 'root-missing')
        require(decision(hook_check, dict(root=self.roots[generation], command='a2a'))[0] == 'accept', 'hook-root')
        return generation


def hook_upgrade(states):
    require(len(states) == 2, 'hook-pair')
    for state in states:
        require(verdict(state) == 'accept', 'hook-root')
    require(states[0]['trusted']['profile'] == states[1]['trusted']['profile'], 'hook-profile')
    old, new = [s['fragment']['command_root']['generation'] for s in states]
    require(old != new, 'hook-generation')
    require(json.loads(states[0]['trusted']['receipt'])['commands'][0]['executable_sha256']
            != json.loads(states[1]['trusted']['receipt'])['commands'][0]['executable_sha256'], 'hook-version')
    require(gateway_path(states[0], 'a2a') == gateway_path(states[1], 'a2a'), 'hook-stable-path')
    model = HookModel(states[0]); first = model.retain('/settings/hooks', 'first')
    require(model.retain('/settings/hooks', 'retry') == first, 'hook-idempotency')
    model.activate(first, True, model.revisions[first]); model.install(states[1]); model.gc()
    require(model.invoke() == old, 'hook-old-retention')
    second = model.retain('/settings/hooks', 'second')
    require(set(model.list()) == {first, second}, 'hook-list')
    model.activate(second, True, model.revisions[second]); model.gc()
    require(old in model.roots and model.invoke() == new, 'hook-rollback-retention')
    model.release(first, True, model.revisions[first]); model.gc()
    require(old not in model.roots and model.invoke() == new, 'hook-final-release')


def validate_data(data, checks=None):
    checks = validators() if checks is None else checks
    checks['corpus.schema.json'].validate(data)
    for section, required in REQUIRED.items():
        ids = [c['id'] for c in data[section]]
        if len(ids) != len(set(ids)) or set(ids) != required:
            raise ValueError(section+': required case IDs differ')
    for case in data['cases']:
        if case['id'] in {'tampered-marker', 'tampered-receipt', 'tampered-inventory'}:
            key = case['id'].removeprefix('tampered-')
            json.loads(case['state']['observed'][key], object_pairs_hook=strict_pairs)
    functions = {'cases': root_check, 'references': reference_check,
                 'launchers': launcher_check, 'retention': retention_check, 'sessions': session_check, 'hooks': hook_check}
    for section, check in functions.items():
        for case in data[section]:
            actual = decision(check, case['state'], checks)
            if actual != (case['expected'], case['reason']):
                raise ValueError(f"{case['id']}: {actual} != {(case['expected'], case['reason'])}")
    for section, check in [('lifecycle', lifecycle), ('compatibility', compatibility), ('transactions', transaction)]:
        for case in data[section]:
            if check(case['state']) != case['expected']:
                raise ValueError(case['id']+': transition differs')
    profiles = data['two_profiles']
    require(all(verdict(s, checks) == 'accept' for s in profiles), 'two-profile-acceptance')
    require(profiles[0]['trusted']['profile'] != profiles[1]['trusted']['profile'], 'two-profile-identities')
    pins = [json.loads(s['trusted']['receipt'])['commands'][0] for s in profiles]
    require(pins[0]['commit'] != pins[1]['commit'], 'two-version-pins')
    require((pins[0]['source'], pins[0]['directory'], pins[0]['name'])
            == (pins[1]['source'], pins[1]['directory'], pins[1]['name']), 'two-command-source')
    require(pins[0]['executable_sha256'] != pins[1]['executable_sha256'], 'two-executable-bytes')
    require(profiles[0]['fragment']['path_prepend'] != profiles[1]['fragment']['path_prepend'], 'two-root-paths')
    hook_upgrade(data['hook_upgrade'])


def validate():
    try:
        data = json.loads((CORPUS/'cases.json').read_text())
        validate_data(data)
    except (Refusal, ValidationError, ValueError, KeyError, TypeError, OSError) as exc:
        raise ValueError('command-root validation failed: '+str(exc)) from exc
    print('Slice B-a: '+', '.join(f'{len(data[k])} {k}' for k in REQUIRED)
          + '; two profiles and executable hook lifecycle model; runtime unqualified')


if __name__ == '__main__':
    validate()
