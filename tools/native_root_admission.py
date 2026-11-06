"""Unaccepted native admission proposals; never a production trust decision."""
from copy import deepcopy
import json
from profile_command_roots import ROOT, SCHEMAS, CORPUS, validators, require, absolute, bounded_path, strict_pairs, Refusal
from jsonschema import Draft202012Validator


def joint_candidate():
    """Preserve sole rc7 semantics while proposing a conditional native B-a pair."""
    schema = deepcopy(json.loads((ROOT/'schemas/rc7-carriers-v1/launch-env-fragment-v5.schema.json').read_text()))
    leaf = json.loads((SCHEMAS/'fragment-members.schema.json').read_text())
    schema['properties']['command_root'] = deepcopy(leaf['properties']['command_root'])
    schema['properties']['command_root']['properties']['platform'] = {'enum':['linux-arm64','linux-amd64']}
    schema.setdefault('dependentRequired', {}).update(
        command_root=['path_prepend'], path_prepend=['command_root'])
    return Draft202012Validator(schema, registry=validators()['native-admission-proposal.schema.json']._registry)


def locations(home, profile, generation, platform, lease, request):
    tree = f'{home}/environments/{profile}/commands/{generation}/{platform}'
    state = home+'/state/command-roots'
    return dict(root=tree+'/bin', inventory=tree+'/inventory.json',
                receipt=tree+'/bin/.curator-profile-command-root.json', marker=tree+'/generation.json',
                generation=f'{state}/g/{generation}.json', selected=f'{state}/selected/{profile}.json',
                session=f'{state}/sessions/{lease}.json', replay=f'{state}/requests/{profile}/{request}.json',
                policy=state+'/admission.json')


def check_candidate(case, trusted):
    require(validators()['native-admission-proposal.schema.json'].is_valid(case), 'candidate-schema')
    policy = case['policy']; req = case['acquire']; replay = case['replay']; pin = replay['pin']
    require(policy['manager_home'] == trusted['home'] and policy['uid'] == trusted['uid']
            and policy['revision'] == trusted['policy_revision'], 'candidate-policy-authority')
    for name in ['manager','launcher','entry_point']:
        require(absolute(policy[name]['path']) and policy[name] == trusted[name], 'candidate-'+name)
    require(all(absolute(v) for v in [policy['manager_home'],policy['entry_point']['path']]), 'candidate-path')
    profiles = policy['profiles']
    require(len({p['profile'] for p in profiles}) == len(profiles), 'candidate-profile-duplicate')
    require(any(p['profile'] == req['profile'] and p['lock_sha256'] == req['binding']['lock_sha256']
                for p in profiles), 'candidate-selected-lock')
    require(req['binding']['platform'].startswith('linux-'), 'candidate-native-linux')
    require(case['selected']['profile'] == req['profile']
            and case['selected']['binding'] == req['binding']
            and case['selected']['revision'] == trusted['selected_revision'], 'candidate-selection')
    require(req == replay['request'], 'session-request-conflict')
    for key in ['request_id','profile','binding','supervisor_instance','boot_id','process_domain','process_started_at']:
        require(req[key] == pin[key], 'candidate-issued-'+key)
    require(pin['phase'] == 'active' and pin['revision'] == 1, 'candidate-issued-phase')
    # The transport cannot supply its own authority: the launcher retained this
    # full request before acquire; manager and response must agree with it.
    require(req == trusted['request'], 'candidate-request-authority')
    paths = locations(policy['manager_home'],req['profile'],req['binding']['generation'],
                      req['binding']['platform'],pin['lease_id'],req['request_id'])
    generation = case['generation']
    require(generation['profile'] == req['profile'] and generation['binding'] == req['binding'], 'candidate-generation-binding')
    require(generation['root'] == paths['root'] and generation['inventory'] == paths['inventory'], 'candidate-generation-location')
    require(all(bounded_path(p) for p in paths.values()), 'candidate-path-limit')
    return paths


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
    # Operator inputs scope configuration; this supplies no identity enforcement.
    if identity is None and directory is None:
        return deepcopy(inherited)
    require(isinstance(identity, str) and bool(identity) and directory is not None,
            'native-identity-pair')
    require(isinstance(directory, str) and absolute(directory), 'native-identity-directory')
    values = dict(A2A_AGENT=identity, A2A_CONFIG_DIR=directory)
    for key, value in values.items():
        require(inherited.get(key, value) == value, 'native-identity-conflict')
    return dict(inherited, **values)


def validate():
    case = json.loads((CORPUS/'native-admission-proposal.json').read_text())
    # Fixture authority is literal in the tests; validation here checks the
    # committed candidate structure, not signatures or runtime provisioning.
    policy=case['policy']
    trusted=dict(home='/m',uid=1000,policy_revision=1,selected_revision=1,
                 request=deepcopy(case['acquire']), **{k:deepcopy(policy[k]) for k in ['manager','launcher','entry_point']})
    check_candidate(case,trusted)
    print('Native root admission candidate: shape/path/replay consistency only; all gates CLOSED')
