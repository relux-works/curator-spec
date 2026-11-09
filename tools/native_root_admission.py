"""Unaccepted native admission proposals; never a production trust decision."""
from copy import deepcopy
import json
import re
from pathlib import PurePosixPath
from profile_command_roots import ROOT, SCHEMAS, CORPUS, validators, require, absolute, bounded_path, strict_pairs, Refusal
from jsonschema import Draft202012Validator

GATES = ('Joint v5 carrier', 'Protected admission policy', 'Protected-state locations',
         'Session integration', 'Journal coverage', 'Native runtime witnesses', 'Companion admission')


def check_gate_text(text):
    # Checks the seven actual packet rows, not owner acceptance or runtime state.
    require(len(GATES) == 7 and len(set(GATES)) == 7, 'gate-inventory')
    for gate in GATES:
        rows = [line for line in text.splitlines() if line.startswith('| '+gate+' — ')]
        require(len(rows) == 1 and rows[0].startswith('| '+gate+' — **CLOSED** |'), 'gate-status-'+gate)


def check_root_gate_text(text):
    # Named declarations include hook gates; this checks text, not acceptance.
    gates = (('root-emission', 'protected admission policy'),
             ('root-emission', 'protected-state locations'),
             ('root-emission', 'session integration'),
             ('root-emission', 'companion admission'),
             ('hook-activation', 'gateway naming decision'),
             ('reference-admission', 'request-epoch maintenance'),
             ('hook-activation', 'gateway aggregate and Windows pins'),
             ('hook-activation', 'registered settings adapter and proofs'))
    for kind, name in gates:
        marker = kind+' gate — '+name+':**'
        rows = [line for line in text.splitlines() if marker in line]
        require(len(rows) == 1 and rows[0].startswith('**CLOSED '+marker), 'roots-gate-status-'+name)


def home_route(home, has_pair, policy, inherited_config=None):
    # Explicit B-a routing and config consistency only; no filesystem observation.
    if home is None:
        require(not has_pair, 'native-home-required')
        return None
    require(policy is not None, 'native-policy-required')
    config = home+'/config.json'
    require(inherited_config in (None, '', config), 'native-home-conflict')
    return config


def home_delivery(config, planning_environment, tool_environment):
    # Supplied environment observations only: not SAM rendering or a real shell.
    require(planning_environment.get('CURATOR_CONFIG') == config, 'native-home-plan-delivery')
    require(tool_environment.get('CURATOR_CONFIG') == config, 'native-home-tool-delivery')


def provider_path_observations(provider, admitted_path, environments, executables, managed_packages=None):
    # Supplied PATHs, executable names and package mappings only; no real SAM,
    # package-layout validation, filesystem resolution or release probe.
    require(all(environments[stage].get('PATH') == ':'.join(admitted_path)
                for stage in ('resolve', 'probe', 'plan')), 'native-provider-admitted-path')
    require(all('CODEX_MANAGED_PACKAGE_ROOT' not in environments[stage]
                for stage in ('resolve', 'probe', 'plan')), 'native-provider-managed-package-root')
    def selected(stage):
        env = environments[stage]
        managed = ((managed_packages or {}).get(env.get('CODEX_MANAGED_PACKAGE_ROOT'))
                   if provider == 'codex' else None)
        if managed in executables:
            return managed
        return next((directory+'/'+provider for directory in env['PATH'].split(':')
                     if directory+'/'+provider in executables), None)
    return {stage: selected(stage) for stage in ('resolve', 'probe', 'plan')}


def joint_candidate():
    """Preserve sole rc7 semantics while proposing a conditional native B-a pair."""
    schema = deepcopy(json.loads((ROOT/'schemas/rc7-carriers-v1/launch-env-fragment-v5.schema.json').read_text(encoding='utf-8')))
    leaf = json.loads((SCHEMAS/'fragment-members.schema.json').read_text(encoding='utf-8'))
    schema['properties']['command_root'] = deepcopy(leaf['properties']['command_root'])
    schema['properties']['command_root']['properties']['platform'] = {'enum':['linux-arm64','linux-amd64']}
    schema.setdefault('dependentRequired', {}).update(
        command_root=['path_prepend'], path_prepend=['command_root'])
    return Draft202012Validator(schema, registry=validators()['native-admission-proposal.schema.json']._registry)


def locations(home, profile, generation, platform, session=None):
    tree = f'{home}/environments/{profile}/commands/{generation}/{platform}'
    state = home+'/state/command-roots'
    paths = dict(root=tree+'/bin', inventory=tree+'/inventory.json',
                 receipt=tree+'/bin/.curator-profile-command-root.json', marker=tree+'/generation.json',
                 selected=f'{state}/selected/{profile}.json', policy=state+'/admission.json')
    if session is not None:
        paths['session'] = f'{state}/sessions/{session}.json'
    return paths


def check_candidate(case, observed):
    require(validators()['native-admission-proposal.schema.json'].is_valid(case), 'candidate-schema')
    home_route(observed['home'], True, case['policy'], observed.get('config'))
    policy = case['policy']; selected = case['selected']; binding = selected['binding']
    # Observed home is the explicit operator launch input, not missing-policy inference.
    require(policy['manager_home'] == observed['home'] and policy['uid'] == observed['uid']
            and policy['revision'] == observed['policy_revision'], 'candidate-policy-authority')
    for name in ['manager','launcher']:
        require(absolute(policy[name]['path']) and policy[name] == observed[name], 'candidate-'+name)
    profiles = policy['profiles']
    require(len({p['profile'] for p in profiles}) == len(profiles), 'candidate-profile-duplicate')
    require(any(p['profile'] == selected['profile'] and p['lock_sha256'] == binding['lock_sha256']
                for p in profiles), 'candidate-selected-lock')
    require(binding['platform'].startswith('linux-'), 'candidate-native-linux')
    require(selected == observed['selected'], 'candidate-selection')
    sid = None
    if case['variant'] == 'pins':
        session = case['session']; req = session['request']; pin = session['pin']
        require(req['profile'] == selected['profile'] and req['binding'] == binding, 'candidate-request-binding')
        for key in ['request_id','profile','binding','supervisor_instance','boot_id','process_domain','process_started_at']:
            require(req[key] == pin[key], 'candidate-issued-'+key)
        require(pin['phase'] == 'active' and pin['revision'] == 1, 'candidate-issued-phase')
        require(pin['lease_id'] == req['request_id'], 'candidate-session-key')
        require(req == observed['request'], 'candidate-request-authority')
        sid = req['request_id']
    paths = locations(policy['manager_home'],selected['profile'],binding['generation'],binding['platform'],sid)
    require(all(bounded_path(p) for p in paths.values()), 'candidate-path-limit')
    return paths


def policy_update(current, proposed, if_revision, selected):
    # Pure CAS/postimage consistency model; atomic filesystem durability is unqualified.
    check = validators()['native-admission-proposal.schema.json']
    shape = check.evolve(schema={'$ref': check.schema['$id']+'#/$defs/policy'})
    require(shape.is_valid(proposed), 'policy-update-schema')
    revision = current['revision'] if current else 0
    require(if_revision == revision, 'policy-update-cas')
    require(proposed['revision'] == revision+1, 'policy-update-revision')
    require(all(selected.get(p['profile']) == p['lock_sha256'] for p in proposed['profiles']), 'policy-update-lock')
    return deepcopy(proposed)


def prune_candidate(automatic, operator_stopped, retained):
    # Attestation is an operator assertion, not an OS quiescence measurement.
    require(not automatic, 'prune-automatic')
    require(operator_stopped, 'prune-attestation')
    require(not retained, 'prune-retained')
    return 'operator-prune'


def decode_acquire(raw):
    try:
        request = json.loads(raw, object_pairs_hook=strict_pairs)
    except (ValueError, TypeError) as exc:
        raise Refusal('candidate-request-json') from exc
    check = validators()['native-admission-proposal.schema.json']
    acquire = check.evolve(schema={'$ref': check.schema['$id']+'#/$defs/acquire'})
    require(acquire.is_valid(request), 'candidate-acquire-schema')
    return request


def replay_acquire(saved, request):
    require(saved['request'] == request, 'session-request-conflict')
    return deepcopy(saved['pin'])


def native_route(hosted, managed_codex_gateway, has_pair, native_identity_flags):
    # Proposed routing refusals only; no provider planning or process is performed.
    require(not (hosted and has_pair), 'fragment_version_unsupported')
    require(not (managed_codex_gateway and (has_pair or native_identity_flags)),
            'native_root_gateway_unsupported')
    return 'admitted-route'


def spawn_recheck(policy_revision, selection_revision, observed):
    # Supplied observations model the final unlocked recheck, not atomic file reads.
    require(policy_revision == observed['policy_revision'], 'native-spawn-policy-revision')
    require(selection_revision == observed['selection_revision'], 'native-spawn-selection-revision')


def record_validator(name):
    check = validators()['native-admission-proposal.schema.json']
    return check.evolve(schema={'$ref':check.schema['$id']+'#/$defs/'+name})


def base_path_recheck(record, policy, platform, retained):
    # Lists are already classified/excluded by section 3; no filesystem claims.
    require(record_validator('base_path_evidence').is_valid(record), 'native-base-path-schema')
    require((record['manager_home'], record['uid'], record['policy_revision'], record['platform'])
            == (policy['manager_home'], policy['uid'], policy['revision'], platform),
            'native-base-path-binding')
    require(record['retained'] == retained, 'native-base-path-difference')
    return deepcopy(retained)


def unpinned_launch(record, profile, binding, policy_revision, selection_revision, evidence_sha256, effective_path):
    # Provenance consistency only, without a lease, runtime liveness or durability.
    require(record_validator('unpinned_launch').is_valid(record), 'native-unpinned-schema')
    require(record['command_root'] == binding, 'native-unpinned-binding')
    prior = record['prior_state']; pb = prior['binding']
    require(pb == dict(profile=profile, lock_sha256='sha256:'+binding['lock_sha256'],
                       plan_sha256='sha256:'+binding['plan_sha256'], generation=binding['generation']),
            'native-unpinned-prior')
    require(record['policy_revision'] == policy_revision
            and record['selection_revision'] == selection_revision
            and record['base_path_sha256'] == evidence_sha256, 'native-unpinned-observation')
    require(record['effective_path'] == effective_path
            and record['path_value'] == ':'.join(effective_path)
            and prior['path'] == effective_path and prior['path_value'] == record['path_value'],
            'native-unpinned-path')
    return deepcopy(record)


class StationRegistrationRefusal(Refusal):
    # One operator-facing failure, with a content-free validation sub-reason.
    code = 'native-environment-not-registered'

    def __init__(self, subreason):
        self.subreason = subreason
        super().__init__(self.code+':'+subreason)


def station_link_entries(entries):
    # Closed namespace before any entry values are inspected.
    names = {'courier.sock', 'identity', 'station.key'}
    require(not (set(entries) - names), 'native-station-extra-entry')
    require(not (names - set(entries)), 'native-station-missing-entry')


class StationKeyMetadata:
    # Observation of four metadata attributes, never a mapping of key contents.
    __slots__ = ('kind', 'uid', 'mode', 'size')

    def __init__(self, kind, uid, mode, size):
        self.kind, self.uid, self.mode, self.size = kind, uid, mode, size

    def __eq__(self, other):
        return type(self) is type(other) and all(getattr(self, n) == getattr(other, n) for n in StationKeyMetadata.__slots__)


def courier_socket_path(raw):
    # Courier v1 file bytes: UTF-8 P plus exactly one LF; byte bound excludes LF.
    require(isinstance(raw, bytes), 'native-station-socket-utf8')
    try:
        text = raw.decode('utf-8', errors='strict')
    except UnicodeDecodeError as exc:
        raise Refusal('native-station-socket-utf8') from exc
    require(text.endswith('\n'), 'native-station-socket-line')
    path = text[:-1]
    require(not any(c in path for c in ('\x00', '\r', '\n', '\ufeff')), 'native-station-socket-line')
    require(1 <= len(path.encode('utf-8')) <= 103, 'native-station-socket-length')
    require(path.startswith('/'), 'native-station-socket-absolute')
    return path


def canonical_station_home(managed_home, station_uid, resolution):
    # Supplied EvalSymlinks result and complete canonical ancestor facts only.
    # No live resolution; Courier stores no enroll-time station path.
    require(isinstance(managed_home, str) and absolute(managed_home), 'native-identity-directory')
    require(isinstance(resolution, dict) and resolution.get('requested_home') == managed_home
            and isinstance(resolution.get('canonical_home'), str) and absolute(resolution['canonical_home']),
            'native-station-home-resolution')
    canonical = resolution['canonical_home']
    expected = [str(p) for p in reversed(PurePosixPath(canonical).parents)] + [canonical]
    ancestors = resolution.get('ancestors')
    require(isinstance(ancestors, list) and all(isinstance(a, dict) for a in ancestors)
            and [a.get('path') for a in ancestors] == expected
            and all(a.get('kind') == 'directory' and type(a.get('uid')) is int
                    and type(a.get('mode')) is int for a in ancestors),
            'native-station-ancestor-observation')
    require(ancestors[-1]['uid'] == station_uid, 'native-station-home-owner')
    require(all(a['uid'] in (0, station_uid) for a in ancestors), 'native-station-ancestor-owner')
    require(all(a['mode'] & 0o022 == 0 or (a['uid'] == 0 and a['mode'] & 0o1000 != 0)
                for a in ancestors), 'native-station-ancestor-writable')
    return canonical


def station_link(managed_home, identity, station_uid, observed, pinned_contract):
    # Supplied no-follow metadata and two public values only; no secret bytes,
    # filesystem observation, peer authentication or Courier registration.
    # The supplied pin represents a2a courier.ProtocolVersion/StationKeyLen;
    # actual Go module-version pinning/lookup is curator-run implementation work.
    require(isinstance(managed_home, str) and absolute(managed_home), 'native-identity-directory')
    require(isinstance(pinned_contract, dict) and pinned_contract.get('ProtocolVersion') == 1
            and pinned_contract.get('StationKeyLen') == 32,
            'native-station-contract-unresolved')
    expected_secret_size = pinned_contract['StationKeyLen']
    directory = observed['path']
    require(isinstance(directory, str) and absolute(directory), 'native-station-directory-absolute')
    require(isinstance(observed.get('resolved_path'), str) and absolute(observed['resolved_path']),
            'native-station-directory-resolution')
    require(observed['resolved_path'] == directory, 'native-station-directory-noncanonical')
    require(directory == managed_home.rstrip('/')+'/.a2a', 'native-station-directory-location')
    require(observed['complete'], 'native-station-unreadable')
    require(observed['exists'], 'native-station-directory-missing')
    require(observed['kind'] == 'directory', 'native-station-directory-type')
    require(observed['mode'] == 0o700, 'native-station-directory-mode')
    require(observed['uid'] == station_uid, 'native-station-directory-owner')
    entries = observed['entries']
    station_link_entries(entries)
    key = entries['station.key']
    require(key.kind == 'file' and all(entries[n]['kind'] == 'file' for n in ('courier.sock', 'identity')),
            'native-station-entry-type')
    require(key.uid == station_uid and all(entries[n]['uid'] == station_uid for n in ('courier.sock', 'identity')),
            'native-station-entry-owner')
    require(key.mode == 0o600, 'native-station-key-mode')
    require(key.size == expected_secret_size, 'native-station-key-size')
    identity_line = entries['identity']['value']
    require(isinstance(identity_line, str) and re.fullmatch(r'[a-z0-9._=-]{1,64}\n', identity_line) is not None,
            'native-station-identity-format')
    require(identity_line[:-1] == identity, 'native-station-identity')
    courier_socket_path(entries['courier.sock']['value'])
    return managed_home.rstrip('/')+'/.a2a'


def identity_environment(identity, managed_home, inherited):
    # Every native launch scrubs parent session keys before planning, including resume.
    # This pure carrier step alone does not admit a station link; use native_identity_launch.
    result = {k:v for k,v in inherited.items() if k not in {'A2A_SESSION_ID','CODEX_THREAD_ID','CLAUDE_CODE_SESSION_ID'}}
    if identity is None:
        return result
    require(isinstance(identity, str) and bool(identity) and managed_home is not None,
            'native-identity-pair')
    require(isinstance(managed_home, str) and absolute(managed_home), 'native-identity-directory')
    directory = managed_home.rstrip('/')+'/.a2a'
    values = dict(A2A_AGENT=identity, A2A_CONFIG_DIR=directory)
    for key, value in values.items():
        require(inherited.get(key) in (None, '', value), 'native-identity-conflict')
    # Existing recommended removal variant; the owner choice is unchanged.
    result = {k:v for k,v in result.items() if k not in {'A2A_MATRIX_URL','A2A_MATRIX_SERVER_NAME','A2A_SECRET_STORE','A2A_MATRIX_REGISTRATION_TOKEN'}}
    return dict(result, **values)


def native_identity_launch(identity, managed_home, inherited, station_uid, observed,
                           pinned_contract, legacy_directory_flag=False):
    # Native-only pre-plan handover: no plan/provider starts or input writes.
    require(not legacy_directory_flag, 'native-a2a-config-dir-unsupported')
    if identity is not None:
        try:
            managed_home = canonical_station_home(managed_home, station_uid, observed.get('resolution'))
            station_link(managed_home, identity, station_uid, observed, pinned_contract)
        except Refusal as exc:
            if str(exc) == 'native-identity-directory':
                raise
            raise StationRegistrationRefusal(str(exc)) from exc
    return identity_environment(identity, managed_home, inherited)


def a2a_published_name(name):
    # Observed executable basename only; not a native process scan or image test.
    require(name.startswith('a2a'), 'native-a2a-published-prefix')


def a2a_upgrade_observation(selected_image, hook_image, consumer_image):
    # Supplied Linux dev/inode observations only; not settings install or bind.
    require((hook_image, consumer_image) == (selected_image, selected_image),
            'native-a2a-upgrade-image')
    return consumer_image


def validate():
    case = json.loads((CORPUS/'native-admission-proposal.json').read_text(encoding='utf-8'))
    policy = case['policy']
    observed = dict(home='/home/agent/.curator',uid=1000,policy_revision=1,
                    selected=deepcopy(case['selected']), **{k:deepcopy(policy[k]) for k in ['manager','launcher']})
    check_candidate(case,observed)
    case['variant'] = 'pins'
    case['session'] = json.loads((CORPUS/'native-pins-alternative.json').read_text(encoding='utf-8'))
    observed['request'] = deepcopy(case['session']['request'])
    check_candidate(case,observed)
    check_gate_text((ROOT/'protocol/profile-command-root-admission.md').read_text(encoding='utf-8'))
    check_root_gate_text((ROOT/'protocol/profile-command-roots.md').read_text(encoding='utf-8'))
    station = dict(path='/managed/home/.a2a', resolved_path='/managed/home/.a2a', complete=True, exists=True, kind='directory', mode=0o700, uid=1000, resolution=dict(requested_home='/managed/home', canonical_home='/managed/home',
        ancestors=[
            dict(path='/', kind='directory', uid=0, mode=0o755),
            dict(path='/managed', kind='directory', uid=0, mode=0o755),
            dict(path='/managed/home', kind='directory', uid=1000, mode=0o700)]), entries={
        'courier.sock': dict(kind='file', uid=1000, value=b'/run/courier/service.sock\n'),
        'identity': dict(kind='file', uid=1000, value='agent-one\n'),
        'station.key': StationKeyMetadata(kind='file', uid=1000, mode=0o600, size=32)})
    require(native_identity_launch('agent-one', '/managed/home', {}, 1000, station, dict(ProtocolVersion=1, StationKeyLen=32))
            == dict(A2A_AGENT='agent-one', A2A_CONFIG_DIR='/managed/home/.a2a'), 'native-station-delivery')
    print('Native admission model: stateless canonical station-path checks, ancestor checks, Courier v1 file/metadata rules; operator prune and optional pins; seven packet rows and eight named roots gates checked CLOSED; no runtime evidence')
