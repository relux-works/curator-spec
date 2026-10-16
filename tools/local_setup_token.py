"""Publication conformance only: metadata admission, never runtime authorization.

The production spec validator invokes check_corpus. Protected filesystem, stdin,
process and vendor behavior belong to implementation leaves, not this checker.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

import rc7_carriers

NAMESPACE = 'local-setup-token-v1'
SCHEMAS = {
    'credential-source-config-v1', 'node-source-v1', 'source-projection-v1',
    'registration-v1', 'refusal-v1', 'local-binding-v1', 'local-final-exec-v1',
    'manager-config-v6', 'agent-environment-marker-v6',
    'launch-env-fragment-v6', 'env-status-v2',
}
ST_ROWS = {'ST-01', 'ST-06', 'ST-07', 'ST-09', 'ST-13'}
UNAVAILABLE = 'credential_injection_unavailable'


class ContractError(ValueError):
    """Corpus verdict or publication shape differs from its contract."""


def registry(root, load):
    resources = []
    schemas = {}
    for namespace in ('v1', 'login-readiness-v1', 'profile-codex-settings-v1',
                      'rc7-carriers-v1', NAMESPACE, 'managed-home-snapshot-v1'):
        for path in sorted((root / 'schemas' / namespace).glob('*.schema.json')):
            value = load(path)
            Draft202012Validator.check_schema(value)
            resources.append((value['$id'], Resource.from_contents(value)))
            if namespace == NAMESPACE:
                name = path.name.removesuffix('.schema.json')
                if value['$id'] != f'https://relux-works.github.io/curator-spec/schemas/{NAMESPACE}/{path.name}':
                    raise ContractError('schema identity differs')
                schemas[name] = value
    if set(schemas) != SCHEMAS:
        raise ContractError('schema inventory differs')
    return schemas, Registry().with_resources(resources)


def required_source_error(name, value):
    """Separate unsupported source semantics from malformed supported metadata.

    Walk only published source locations, checking object kinds before access.
    Full schema validation still owns missing/invalid fields of known branches.
    """
    if not isinstance(value, dict):
        return 'usage'
    discriminator = {
        'manager-config-v6': ('schema_version', 6, 'integer'),
        'agent-environment-marker-v6': ('version', 6, 'integer'),
        'launch-env-fragment-v6': ('fragment', 'launch-env-fragment-v6', 'string'),
        'env-status-v2': ('status', 'env-status-v2', 'string'),
        'local-final-exec-v1': ('plan', 'local-final-exec-v1', 'string'),
    }.get(name)
    if discriminator:
        field, expected, kind = discriminator
        token = value.get(field)
        is_discriminator = Draft202012Validator.TYPE_CHECKER.is_type(token, kind)
        if is_discriminator and token != expected:
            return UNAVAILABLE
        if not is_discriminator:
            return 'usage'
    if name == 'node-source-v1':
        mode = value.get('mode')
        if isinstance(mode, str) and mode != 'node':
            return UNAVAILABLE
    if name == 'source-projection-v1' and 'source' in value:
        return required_source_error('node-source-v1', value['source'])
    if name in ('agent-environment-marker-v6', 'launch-env-fragment-v6') and 'credential_source' in value:
        projection = value['credential_source']
        if name == 'agent-environment-marker-v6' and isinstance(projection, dict) and 'mode' in projection:
            mode = projection['mode']
            return UNAVAILABLE if isinstance(mode, str) and mode != 'per-home' else None
        return required_source_error('source-projection-v1', projection)
    if name == 'local-final-exec-v1':
        route = value.get('route')
        if isinstance(route, str) and route != 'task-board-headless-local':
            return UNAVAILABLE
        if not isinstance(route, str):
            return 'usage'
        if 'required_extensions' not in value:
            return UNAVAILABLE
        extensions = value['required_extensions']
        if not isinstance(extensions, dict):
            return 'usage'
        if set(extensions) != {'works.relux.curator.credential/1'}:
            return UNAVAILABLE
        error = required_source_error('node-source-v1', extensions['works.relux.curator.credential/1'])
        if error:
            return error
        if 'fragment' in value:
            fragment = value['fragment']
            if not isinstance(fragment, dict):
                return 'usage'
            return required_source_error('launch-env-fragment-v6', fragment)
    return None


def metadata_error(name, value, schemas, resources, wire_semantics):
    """Validate a full metadata object without modifying it or producing a launch."""
    error = required_source_error(name, value)
    if error:
        return error
    if not Draft202012Validator(schemas[name], registry=resources).is_valid(value):
        return 'usage'
    predecessor = {
        'manager-config-v6': ('schema_version', 5, 'manager-config-v5'),
        'agent-environment-marker-v6': ('version', 5, 'agent-environment-marker-v5'),
        'launch-env-fragment-v6': ('fragment', 'launch-env-fragment-v5', 'launch-env-fragment-v5'),
        'env-status-v2': ('status', 'env-status-v1', 'env-status-v1'),
    }.get(name)
    if predecessor:
        field, token, previous = predecessor
        old = copy.deepcopy(value)
        old[field] = token
        old.pop('credential_source', None)
        if name == 'manager-config-v6':
            old.get('environments', {}).pop('credential_source', None)
        old_schema = resources.contents(f'https://relux-works.github.io/curator-spec/schemas/rc7-carriers-v1/{previous}.schema.json')
        if rc7_carriers.carrier_error(previous, old, {previous: old_schema}, resources, wire_semantics):
            return 'usage'
    if name == 'manager-config-v6':
        env = value.get('environments', {})
        for profile, entries in env.get('credential_source', {}).items():
            if entries.get('claude_code', 'per-home').startswith('node:'):
                if env.get('credential_store', {}).get(profile, {}).get('claude_code', 'native') != 'native':
                    return 'environment_credential_store_unsupported'
                if env.get('isolation', {}).get(profile, {}).get('claude_code') == 'shared':
                    return 'credential_source_conflict'
    if name == 'local-final-exec-v1':
        fragment = value['fragment']
        error = metadata_error('launch-env-fragment-v6', fragment, schemas, resources, wire_semantics)
        if error:
            return error
        projection = fragment['credential_source']
        if (value['required_extensions']['works.relux.curator.credential/1'] != projection['source']
                or any(value[k] != projection[k] for k in ('source_generation', 'policy_generation'))):
            return 'credential_source_stale'
    return None


def policy_error(case, schemas, resources, wire_semantics):
    """Evaluate published metadata witnesses; this is not a protected-store API."""
    kind, value = case['kind'], case['input']
    if kind == 'schema':
        return metadata_error(case['schema'], value, schemas, resources, wire_semantics)
    if kind == 'authority':
        # Apply the actual closed containing schema, including losing packages.
        schema = resources.contents(value['schema_id'])
        return None if Draft202012Validator(schema, registry=resources).is_valid(value['document']) else 'usage'
    if kind == 'adoption':
        if value['isolation_lock'] == 'shared':
            return 'environment_isolation_lock_conflict'
        if value['native_evidence'] == 'unreadable':
            return 'credential_store_unreadable'
        if value['native_evidence'] in ('credential', 'link', 'competing-settings'):
            return 'credential_source_conflict'
        if value['marker_source'] != value['selected_source'] and value['operation'] != 'admitted-apply':
            return 'credential_source_migration_required'
        return None
    if kind == 'final-boundary':
        plan = value['plan']
        error = metadata_error('local-final-exec-v1', plan, schemas, resources, wire_semantics)
        if error:
            return error
        if value['qualification'] != 'qualified-fixture-tuple' or value['route'] != 'task-board-headless-local':
            return UNAVAILABLE
        binding = value['binding']
        if binding is None:
            return 'credential_binding_mismatch'
        error = metadata_error('local-binding-v1', binding, schemas, resources, wire_semantics)
        if error:
            return 'credential_store_unreadable'
        projection = plan['fragment']['credential_source']
        if (binding['source_ref'] != projection['source']['source_ref']
                or any(binding[k] != plan[k] for k in ('source_generation', 'policy_generation'))):
            return 'credential_source_stale'
        expected = value['executing_context']
        if (any(binding[k] != expected[k] for k in ('executing_uid', 'host_ref', 'harness', 'harness_channel'))
                or binding['profile'] != plan['fragment']['profile']['name']
                or binding['approved_endpoint'] != plan['invocation']['endpoint']
                or binding['executable_sha256'] != plan['invocation']['executable_sha256']):
            return 'credential_binding_mismatch'
        return None
    if kind == 'snapshot':
        schema = resources.contents(value['schema_id'])
        return None if Draft202012Validator(schema, registry=resources).is_valid(value['document']) else 'usage'
    raise ContractError('unknown case kind')


def check_corpus(root, load, wire_semantics):
    schemas, resources = registry(root, load)
    corpus = load(root / 'conformance' / NAMESPACE / 'cases.json')
    if corpus['runtime_qualification'] != 'unverified':
        raise ContractError('metadata fixtures cannot qualify runtime')
    names, coverage, schema_coverage = set(), {}, {}
    for case in corpus['cases']:
        before = copy.deepcopy(case['input'])
        error = policy_error(case, schemas, resources, wire_semantics)
        if error != case['diagnostic'] or case['input'] != before:
            raise ContractError(f"{case['name']}: expected {case['diagnostic']}, got {error}; input preservation required")
        if case['name'] in names:
            raise ContractError('duplicate case name')
        names.add(case['name'])
        coverage.setdefault(case['row'], set()).add(error is None)
        if case['kind'] == 'schema':
            schema_coverage.setdefault(case['schema'], set()).add(error is None)
    if set(coverage) != ST_ROWS or any(v != {True, False} for v in coverage.values()):
        raise ContractError('paired ST coverage differs')
    if set(schema_coverage) != SCHEMAS or any(v != {True, False} for v in schema_coverage.values()):
        raise ContractError('paired schema coverage differs')
    return len(names), sum(c['diagnostic'] is not None for c in corpus['cases'])


def main():
    import validate
    total, negative = check_corpus(Path(__file__).resolve().parents[1], validate.load_json, validate.validate_wire_semantics)
    print(f'local source publication cases: {total}/{total}; negatives: {negative}/{negative}; runtime qualification: unverified')


if __name__ == '__main__':
    main()
