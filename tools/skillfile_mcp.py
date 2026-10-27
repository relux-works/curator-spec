"""Stage-A specification oracle over synthetic facts; no acquisition or native I/O.

The production spec validator calls check_corpus. This is not a manager, package
resolver, native writer or protected-state attestation.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from ccj1_grammar import integer as strict_integer, exact_patterns, portable_path
from mcp_url_grammar import url_valid

ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = 'skillfile-mcp-v1'
ENVIRONMENTS = frozenset({'claude_code', 'codex_cli', 'opencode', 'pi', 'muse'})
VERSION = r'(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)'
NPM_NAME = r'[a-z0-9][a-z0-9._-]{0,213}'
DIST = r'[a-z0-9](?:[a-z0-9._-]{0,212}[a-z0-9])?'
CAPABILITY = 'skillfile-mcp-stage-a-v1'
REQUIRED_REFUSALS = frozenset({'upgrade_required', 'mcp_declaration_invalid',
    'mcp_package_not_allowed', 'mcp_package_allowlist_empty',
    'mcp_inline_approval_unsupported', 'mcp_contribution_policy_refused',
    'mcp_native_entry_conflict', 'context-secret-material'})


class Refusal(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)  # never include input bytes in a diagnostic


def invalid():
    raise Refusal('mcp_declaration_invalid')


def scalar_tree(value):
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, str):
        try:
            value.encode('utf-8', errors='strict')
        except UnicodeError:
            invalid()
    elif type(value) is int:
        if abs(value) > 9007199254740991:
            invalid()
    elif isinstance(value, list):
        for child in value:
            scalar_tree(child)
    elif isinstance(value, dict):
        for key, child in value.items():
            scalar_tree(key)
            scalar_tree(child)
    else:
        invalid()


def strict_load(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                invalid()
            result[key] = value
        return result
    try:
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8', errors='strict')
        value = json.loads(raw, object_pairs_hook=pairs, parse_int=strict_integer,
                           parse_constant=lambda _: invalid())
        scalar_tree(value)
        return value
    except (ValueError, UnicodeError, TypeError):
        invalid()


def canonical(value):
    scalar_tree(value)
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return 'sha256:' + hashlib.sha256(canonical(value)).hexdigest()


@lru_cache(maxsize=8)
def registry(root=ROOT):
    documents = [exact_patterns(json.loads(p.read_text())) for p in (root/'schemas').rglob('*.schema.json')]
    for document in documents:
        Draft202012Validator.check_schema(document)
    return Registry().with_resources((d['$id'], Resource.from_contents(d)) for d in documents)


def schema_valid(name, value, root=ROOT):
    path = root/'schemas'/NAMESPACE/(name+'.schema.json')
    return Draft202012Validator(exact_patterns(json.loads(path.read_text())), registry=registry(root)).is_valid(value)



def runtime_pin(command, args):
    lower = command.lower()
    if lower.split('.')[0] in {'npx', 'uvx'} and command not in {'npx', 'uvx'}:
        return False
    if command == 'npx':
        args = args[1:] if args and args[0] in {'-y', '--yes'} else args
        return bool(args and re.fullmatch(r'(?:@'+NPM_NAME+r'/)?'+NPM_NAME+'@'+VERSION, args[0]))
    if command == 'uvx':
        if args and args[0] == '--from':
            if len(args) < 3 or not re.fullmatch(DIST+'=='+VERSION, args[1]):
                return False
            return bool(re.fullmatch(r'(?!-)(?!\.{1,2}$)[^/\\\s\x00-\x1f\x7f]{1,255}', args[2]))
        return bool(args and re.fullmatch(DIST+'@'+VERSION, args[0]))
    return True


def audit_clear(value, root=ROOT):
    # Reuse the published detector vocabulary and placeholder treatment.
    import validate
    patterns = json.loads((root/'conformance/v1/vectors/context-detectors.json').read_text())['pattern_classes']
    findings, _ = validate.detector_findings(patterns, 'synthetic-snapshot',
                                            {'agent-mcp.json': canonical(value).decode('utf-8')}, [])
    return not findings


def normalize_server(server):
    server = copy.deepcopy(server)
    server['env_names'] = sorted(server.get('env_names', []), key=lambda s: s.encode('utf-8'))
    if 'environments' in server:
        server['environments'] = sorted(server['environments'], key=lambda s: s.encode('utf-8'))
    return server


def normalize_declaration(decl):
    if isinstance(decl, str):
        decl = {'server': {'transport': 'http', 'url': decl}}
    result = copy.deepcopy(decl)
    if 'server' in result:
        result['server'] = normalize_server(result['server'])
    result.setdefault('install', {})
    return result


def server_valid(server, root=ROOT):
    return (schema_valid('declaration-v1', {'server': server}, root)
            and all(re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9_-])?', name)
                    for name in server.get('env_names', []))
            and (url_valid(server['url']) if server['transport'] == 'http'
                 else (re.fullmatch(r'(?!\.{1,2}$)[^/\\\s\x00-\x1f\x7f]{1,255}', server['command'])
                       and runtime_pin(server['command'], server['args']))))


def package_byte_bounds(server):
    """Legacy agent-mcp byte ceilings, additional to inline scalar bounds."""
    if server['transport'] == 'http':
        return len(server['url'].encode('utf-8')) <= 4096
    return (len(server['command'].encode('utf-8')) <= 255
            and all(len(arg.encode('utf-8')) <= 8192 for arg in server['args']))


def selection_matches(selector, resolved):
    """Check available internal facts; tag-to-commit attestation stays external."""
    import validate
    if 'revision' in selector and selector['revision'] != resolved['commit']:
        return False
    if 'range' in selector:
        version = validate.semver_parse(resolved['version'])
        if version is None or not validate.range_satisfies(validate.range_parse(selector['range']), version):
            return False
    return True


def package_valid(package):
    import validate
    if validate.validate_repository_git(package['git']) is not None:
        return False
    if 'directory' in package and not portable_path(package['directory']):
        return False
    if 'tag' in package and validate.validate_git_ref_name(package['tag']) is not None:
        return False
    if 'revision' in package and re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', package['revision']) is None:
        return False
    if 'range' in package:
        try:
            validate.range_parse(package['range'])
        except validate.RangeInvalid:
            return False
    return True


def declaration_valid(decl, root=ROOT):
    if not schema_valid('declaration-v1', decl, root):
        return False
    model = normalize_declaration(decl)
    return server_valid(model['server'], root) if 'server' in model else package_valid(model['package'])


def stage_a(decl):
    return isinstance(decl, dict) and 'package' in decl


def identity(git):
    import validate
    match = (validate.HTTPS_REPOSITORY.fullmatch(git)
             or validate.SSH_URI_REPOSITORY.fullmatch(git)
             or validate.SSH_SCP_REPOSITORY.fullmatch(git))
    # The grammar check precedes this function; acquisition transport stays separate.
    host = match.group('host').lower()
    path = match.group('path')
    return host+'/'+(path[:-4] if path.endswith('.git') else path)


def allowed(source, allowlist):
    return not allowlist or any(source == p or source.startswith(p+'/') for p in allowlist)


def targets(server, writable):
    return sorted(server.get('environments', writable))


def ownership_allowed(facts):
    return not facts.get('foreign', False)


def policy_allowed(facts, name, server_sha256, content_sha256):
    action = facts.get('ownership_action', 'none')
    if action == 'none':
        return True
    record = facts.get('action_record')
    # Storage protection/current policy are observations; binding is checked here.
    return (facts.get('record_protected') is True and facts.get('policy_allows_action') is True
            and isinstance(record, dict) and carrier_valid('mcp-approval-v1', record)
            and record['state'] == 'active' and record['project_id'] == facts.get('project_id')
            and record['name'] == name and record['server_sha256'] == server_sha256
            and record['content_sha256'] == content_sha256
            and record['operation'] == action and record['policy_sha256'] == facts.get('policy_sha256'))


def evaluate(raw, facts=None, root=ROOT):
    """Return a planning verdict over declared observations; never mutate inputs."""
    facts = copy.deepcopy(facts or {})
    models = {}
    manifest = {}
    try:
        manifest = strict_load(raw)
        if not isinstance(manifest, dict) or type(manifest.get('schema_version')) is not int:
            invalid()
        if (manifest.get('schema_version') != 3
                or facts.get('scope', 'project') != 'project'
                or facts.get('schema3_supported', True) is not True):
            raise Refusal('upgrade_required')
        if not schema_valid('skillfile-v3', manifest, root):
            invalid()
        declarations = manifest.get('mcp_servers', {})
        models = {}
        for name, decl in sorted(declarations.items()):
            if not declaration_valid(decl, root):
                invalid()
            if not audit_clear(decl, root):
                raise Refusal('context-secret-material')
            models[name] = normalize_declaration(decl)
        # Recognize and audit complete inline data, but never activate inline authority.
        if any(not stage_a(decl) for decl in declarations.values()):
            raise Refusal('mcp_inline_approval_unsupported')
        warnings = []
        rows = []
        entries = []
        options = []
        for name, model in models.items():
            selector = model['package'];source = identity(selector['git'])
            policy = facts.get('mcp_allowlist', [])
            if not policy:
                if facts.get('hardened', False):
                    raise Refusal('mcp_package_allowlist_empty')
                warnings = ['mcp_package_allowlist_empty']
            if not allowed(source, policy):
                raise Refusal('mcp_package_not_allowed')
            resolved = facts.get('packages', {}).get(name)
            if resolved is None:
                raise Refusal('source_snapshot_unavailable')
            if resolved.get('snapshot_matches', True) is not True:
                raise Refusal('source_snapshot_changed')
            if resolved.get('directory_components', []) and any(c != 'directory' for c in resolved['directory_components']):
                raise Refusal('profile_source_invalid')
            if facts.get('source_allowlist_empty', False):
                raise Refusal('source_allowlist_empty')
            if resolved.get('signed', True) is not True:
                raise Refusal('context_source_unsigned')
            if resolved.get('signers_present', True) is not True:
                raise Refusal('context_source_signers_missing')
            if resolved.get('version_matches', True) is not True:
                raise Refusal('context_version_mismatch')
            if resolved.get('signer_allowed', True) is not True:
                raise Refusal('context_source_signer_rejected')
            package = resolved.get('manifest')
            # Real consumers must establish committed tree/name/version/path facts.
            schema = exact_patterns(json.loads((root/'schemas/v1/agent-mcp-v1.schema.json').read_text()))
            if (not Draft202012Validator(schema, registry=registry(root)).is_valid(package)
                    or package['name'] != name or not server_valid(package['server'], root)
                    or not package_byte_bounds(package['server'])):
                invalid()
            if not audit_clear(package, root):
                raise Refusal('context-secret-material')
            if facts.get('preimage_read', 'ok') != 'ok':
                raise Refusal('environment_surface_unreadable')
            if not ownership_allowed(facts):
                raise Refusal('mcp_native_entry_conflict')
            if not policy_allowed(facts, name, digest(normalize_server(package['server'])), resolved.get('content_sha256')):
                raise Refusal('mcp_contribution_policy_refused')
            server = normalize_server(package['server'])
            writable = facts.get('writable', ['claude_code', 'codex_cli', 'muse'])
            if not set(writable) <= ENVIRONMENTS:
                invalid()
            for environment in targets(server, writable):
                supported = environment in writable
                path = facts.get('paths', {}).get(environment) if supported else None
                if supported and path is None:
                    raise Refusal('mcp_contribution_policy_refused')
                action = facts.get('ownership_action', 'none')
                outcome = {'none':'added', 'restore':'restored', 'remove':'removed',
                           'release':'released', 'replace':'updated'}[action]
                rows.append(dict(name=name, environment=environment, path=path,
                                 outcome=outcome if supported else 'skipped: unsupported', code=None))
            entries.append(dict(name=name, declaration_sha256=digest(model),
                                server_sha256=digest(server), normalized_server=server))
            options.extend(dict(name=name, option=key, handling='ignored') for key in sorted(model['install']))
        return dict(code=None, warnings=warnings, rows=rows, entries=entries,
                    install_options=options, mutated=False)
    except Refusal as error:
        rows = []
        declarations = manifest.get('mcp_servers', {}) if isinstance(manifest, dict) else {}
        if isinstance(declarations, dict):
            for name, decl in sorted(declarations.items()):
                if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}', name) and declaration_valid(decl, root):
                    models[name] = normalize_declaration(decl)
        for name, model in sorted(models.items()):
            package_manifest = facts.get('packages', {}).get(name, {}).get('manifest')
            server = model.get('server') or (package_manifest.get('server') if isinstance(package_manifest, dict) else None)
            if server is None or not server_valid(server, root):
                continue
            writable = facts.get('writable', ['claude_code', 'codex_cli', 'muse'])
            for environment in targets(server, writable):
                supported = environment in writable
                rows.append(dict(name=name, environment=environment,
                                 path=facts.get('paths', {}).get(environment) if supported else None,
                                 outcome='refused' if supported else 'skipped: unsupported',
                                 code=error.code if supported else None))
        return dict(code=error.code, rows=rows, mutated=False)


def carrier_valid(name, value, root=ROOT):
    try:
        scalar_tree(value)
    except Refusal:
        return False
    if not schema_valid(name, value, root):
        return False
    if name == 'mcp-approval-v1':
        return True  # authority/location/current policy are not structural facts
    field = 'lock_sha256' if name == 'mcp-lock-v1' else 'plan_sha256'
    if value[field] != digest({k:v for k,v in value.items() if k != field}):
        return False
    if name == 'mcp-lock-v1':
        if value['skills_lock']['manifest_sha256'] != value['manifest_sha256']:
            return False
        skill_lock = value['skills_lock']
        if skill_lock['lock_sha256'] != digest({k:v for k,v in skill_lock.items() if k != 'lock_sha256'}):
            return False
        names = [e['name'] for e in value['entries']]
        if names != sorted(set(names)):
            return False
        for entry in value['entries']:
            model = normalize_declaration(entry['declaration']);resolved = entry['resolved']
            if (not declaration_valid(model, root) or model != entry['declaration']
                    or entry['declaration_sha256'] != digest(model)
                    or not audit_clear(model, root) or not audit_clear(resolved['server'], root)
                    or not server_valid(resolved['server'], root)
                    or not package_byte_bounds(resolved['server'])
                    or not selection_matches(model['package'], resolved)
                    or resolved['server'] != normalize_server(resolved['server'])
                    or resolved['server_sha256'] != digest(resolved['server'])
                    or resolved['source'] != identity(model['package']['git'])
                    or resolved['directory'] != model['package'].get('directory')):
                return False
    else:
        keys = [(r['name'], r['environment']) for r in value['rows']]
        if keys != sorted(set(keys)):
            return False
        refusals = any(r['outcome'] in {'refused', 'conflict: foreign entry'} for r in value['rows'])
        if value['rows'] and not refusals and value['lock_sha256'] is None:
            return False
        successes = {'added','updated','unchanged','restored','removed','released'}
        for row in value['rows']:
            if (row['path'] is not None and not portable_path(row['path'])
                    or (row['outcome'] == 'refused') != (row['code'] is not None)
                    or row['outcome'] == 'skipped: unsupported' and row['path'] is not None
                    or row['outcome'] in successes and row['path'] is None
                    or refusals and row['outcome'] in successes):
                return False
        options = [(o['name'], o['option']) for o in value['install_options']]
        if options != sorted(set(options)):
            return False
    return True


def check_case(case, root=ROOT):
    if not case.get('claim'):
        raise ValueError('MCP case claim missing')
    if case['kind'] == 'admission':
        if stage_a(case['declaration']) != case['allowed']:
            raise ValueError('MCP verdict mismatch: '+case['id'])
        return not case['allowed']
    if case['kind'] == 'normalization':
        model = normalize_declaration(case['declaration'])
        if model != case['normalized'] or digest(model) != case['digest']:
            raise ValueError('MCP verdict mismatch: '+case['id'])
        return False
    if case['kind'] == 'planning':
        raw = case['raw'].encode('utf-8') if case.get('raw_bytes', False) else case['raw']
        result = evaluate(raw, case['facts'], root)
        expected = case['expected']
        actual = {key:result.get(key) for key in expected}
        if actual != expected or result.get('mutated') is not False:
            raise ValueError('MCP verdict mismatch: '+case['id'])
        return expected['code'] is not None
    actual = carrier_valid(case['schema'], case['instance'], root)
    if actual != case['valid']:
        raise ValueError('MCP carrier mismatch: '+case['id'])
    return not case['valid']


def check_corpus(root=ROOT):
    corpus = root/'conformance'/NAMESPACE
    data = strict_load((corpus/'cases.json').read_bytes())
    inventory = strict_load((corpus/'coverage.json').read_bytes())
    if [case['id'] for case in data] != inventory['cases'] or len(set(inventory['cases'])) != len(data):
        raise ValueError('MCP case inventory mismatch')
    codes = {case['expected']['code'] for case in data if case['kind'] == 'planning'}
    if not REQUIRED_REFUSALS <= codes or None not in codes:
        raise ValueError('MCP refusal coverage mismatch')
    for schema in ['mcp-lock-v1', 'mcp-plan-v1', 'mcp-approval-v1']:
        if {case['valid'] for case in data if case['kind'] == 'carrier' and case['schema'] == schema} != {True, False}:
            raise ValueError('MCP carrier coverage mismatch: '+schema)
    negatives = sum(check_case(case, root) for case in data)
    return len(data), negatives
