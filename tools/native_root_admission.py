"""Unaccepted native admission proposals; never a production trust decision."""
from copy import deepcopy
import json
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


def identity_environment(identity, directory, inherited):
    # New native sessions scrub all three old session keys, even without identity flags.
    result = {k:v for k,v in inherited.items() if k not in {'A2A_SESSION_ID','CODEX_THREAD_ID','CLAUDE_CODE_SESSION_ID'}}
    if identity is None and directory is None:
        return result
    require(isinstance(identity, str) and bool(identity) and directory is not None,
            'native-identity-pair')
    require(isinstance(directory, str) and absolute(directory), 'native-identity-directory')
    values = dict(A2A_AGENT=identity, A2A_CONFIG_DIR=directory)
    for key, value in values.items():
        require(inherited.get(key) in (None, '', value), 'native-identity-conflict')
    return dict(result, **values)


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
    print('Native admission model: operator prune and optional pins; seven packet rows and eight named roots gates checked CLOSED; no runtime evidence')
