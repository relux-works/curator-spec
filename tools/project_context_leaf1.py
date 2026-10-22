"""CIP-0002 leaf-1 closed member grammar and publication oracle.

No filesystem authorization, protected-state resolution or native qualification
is performed. Complete carriers and runtime vector families remain separate.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path, PurePosixPath

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from ccj1_grammar import integer, exact_patterns
from mcp_url_grammar import url_valid

ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = 'project-context-leaf1-v1'
RECORDS = (
    'registration', 'item', 'approval', 'generation', 'composition', 'lease',
    'project-context', 'command-environment', 'fragment-members', 'root-binding',
    'snapshot-manifest', 'control-receipt', 'adapter',
)
INVALID = 'project_context_invalid'
MAX_BYTES = 1048576
MAX_DEPTH = 16
MAX_STRING = 256
MAX_ROOT = 4096
MAX_PATH = 240
MAX_PATH_DEPTH = 32
MAX_TOTAL = 67108864
MAX_U64 = 18446744073709551615
SAFE_INTEGER = 9007199254740991


class ContractError(ValueError):
    """A typed grammar refusal; messages contain no input bytes."""

    def __init__(self, gate):
        super().__init__(f'{INVALID}: {gate}')
        self.gate = gate
        self.code = INVALID


def ccj1_bytes(value):
    """Canonicalize all members, including sig; unlike signed-record helpers."""
    def check(node):
        if node is None or isinstance(node, (str, bool)):
            return
        if isinstance(node, int) and abs(node) <= SAFE_INTEGER:
            return
        if isinstance(node, list):
            for child in node:
                check(child)
            return
        if isinstance(node, dict) and all(isinstance(k, str) for k in node):
            for child in node.values():
                check(child)
            return
        raise ContractError('ccj1')
    check(value)
    try:
        return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                          separators=(',', ':')).encode('utf-8')
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ContractError('encoding') from exc


def identity(value):
    return hashlib.sha256(ccj1_bytes(value)).hexdigest()


def decode(raw):
    if len(raw) > MAX_BYTES:
        raise ContractError('record-size')

    def pairs(entries):
        result = {}
        for key, value in entries:
            if key in result:
                raise ContractError('duplicate-member')
            result[key] = value
        return result

    def non_integer(_value):
        raise ContractError('ccj1')

    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                           parse_int=integer, parse_float=non_integer, parse_constant=non_integer)
    except ContractError:
        raise
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ContractError('encoding') from exc
    except ValueError as exc:
        # Python's integer digit ceiling may fire before CCJ-1 range checks.
        # Keep that parser refusal typed, without echoing the number.
        raise ContractError('ccj1') from exc

    def depth(node, level=0):
        if isinstance(node, (dict, list)):
            if level + 1 > MAX_DEPTH:
                raise ContractError('record-depth')
            children = node.values() if isinstance(node, dict) else node
            for child in children:
                depth(child, level + 1)
    depth(value)
    ccj1_bytes(value)  # safe integers and unpaired Unicode escapes
    return value


def schemas(root=ROOT):
    resources, records = [], {}
    for namespace in ('v1', 'workspace-trust-v1', NAMESPACE):
        for path in sorted((root / 'schemas' / namespace).glob('*.schema.json')):
            schema = json.loads(path.read_text(encoding='utf-8'))
            if namespace != NAMESPACE:
                schema = exact_patterns(schema)
            Draft202012Validator.check_schema(schema)
            resources.append((schema['$id'], Resource.from_contents(schema)))
            if namespace == NAMESPACE and path.stem != 'common.schema':
                records[path.name.removesuffix('.schema.json')] = schema
    if set(records) != set(RECORDS):
        raise ValueError('leaf-1 schema inventory differs')
    return records, Registry().with_resources(resources)


def strings(value, path=()):
    if isinstance(value, str):
        # Owning MCP schemas bound these in characters, not UTF-8 bytes.
        if 'server' in path and ('args' in path or path[-1] in ('command', 'url')):
            return
        limit = MAX_ROOT if path[-1:] in (('root',), ('project_root',)) else (
            MAX_PATH if path[-1:] == ('path',) else MAX_STRING)
        if len(value.encode('utf-8')) > limit:
            raise ContractError('string-bytes')
    elif isinstance(value, dict):
        for key, child in value.items():
            strings(child, path + (key,))
    elif isinstance(value, list):
        for child in value:
            strings(child, path + ('[]',))


def exact_root(value):
    return (value.startswith('/') and str(PurePosixPath(value)) == value
            and '..' not in PurePosixPath(value).parts
            and re.search(r'[\x00-\x1f\x7f]', value) is None)


def files_error(files):
    paths = [entry['path'] for entry in files]
    if paths != sorted(paths, key=lambda p: p.encode('utf-8')):
        raise ContractError('file-order')
    if any(len(p.split('/')) > MAX_PATH_DEPTH for p in paths):
        raise ContractError('path-depth')
    if any(component.endswith(('.', ' ')) for p in paths for component in p.split('/')):
        raise ContractError('path-component')
    # Aliases are refused, not silently normalized into a different manifest.
    normalized = [unicodedata.normalize('NFC', p).casefold() for p in paths]
    if len(set(normalized)) != len(normalized):
        raise ContractError('file-alias')
    inventory = set(normalized)
    if any('/'.join(p.split('/')[:n]) in inventory
           for p in normalized for n in range(1, len(p.split('/')))):
        raise ContractError('file-ancestor')
    if sum(entry['size'] for entry in files) > MAX_TOTAL:
        raise ContractError('inventory-size')


def semantic(record, value):
    strings(value)
    if record in ('registration', 'project-context') and not exact_root(value['project_root']):
        raise ContractError('root-path')
    if record == 'root-binding':
        from workspace_trust import remote_safe
        if not exact_root(value['repository']['root']):
            raise ContractError('root-path')
        if not remote_safe(value['repository']['primary_remote']):
            raise ContractError('repository-remote')
        if any(int(v) > MAX_U64 for v in value['filesystem'].values()):
            raise ContractError('filesystem-u64')
    if record == 'generation':
        ids = [i['item_id'] for i in value['items']]
        if len(set(ids)) != len(ids):
            raise ContractError('generation-ids')
    if record in ('snapshot-manifest', 'control-receipt'):
        files_error(value['files'])
    if record == 'adapter':
        if value['surfaces'] != sorted(value['surfaces'], key=lambda s: s.encode('utf-8')):
            raise ContractError('surface-order')
    if record == 'item' and value['type'] == 'mcp':
        payload = value['payload']
        server = payload['server']
        if server['transport'] == 'http' and not url_valid(server['url']):
            raise ContractError('schema')
        for field in ('env_names', 'environments'):
            if field in server and server[field] != sorted(set(server[field]), key=lambda s: s.encode('utf-8')):
                raise ContractError('server-normalization')
        if any(e not in {'claude_code', 'codex_cli', 'muse', 'opencode', 'pi'}
               for e in server.get('environments', [])):
            raise ContractError('server-environments')
        if payload['server_sha256'] != 'sha256:' + identity(server):
            raise ContractError('server-digest')
    if record == 'fragment-members':
        semantic('project-context', value['project_context'])
        command = value.get('command_environment')
        if command and any(command[k] != value['project_context'][k]
                           for k in ('context_ref', 'context_sha256')):
            raise ContractError('fragment-context')


def validate_bytes(record, raw, catalog=None):
    if record not in RECORDS:
        raise ValueError('unknown record schema')
    value = decode(raw)
    records, registry = catalog if catalog is not None else schemas()
    if not Draft202012Validator(records[record], registry=registry).is_valid(value):
        raise ContractError('schema')
    semantic(record, value)
    return value


def verdict(record, raw, catalog=None):
    try:
        validate_bytes(record, raw, catalog)
    except ContractError as exc:
        return {'code': exc.code, 'gate': exc.gate}
    return None


def check_corpus(root=ROOT):
    corpus = root / 'conformance' / NAMESPACE
    manifest = json.loads((corpus / 'manifest.json').read_text(encoding='utf-8'))
    catalog = schemas(root)
    cases = manifest['cases']
    names = {case['name'] for case in cases}
    if len(names) != len(cases):
        raise ValueError('duplicate case name')
    positives, negatives = {}, {}
    for case in cases:
        raw = (corpus / case['file']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != case['bytes_sha256']:
            raise ValueError(f"{case['name']}: fixture bytes differ")
        actual = verdict(case['record'], raw, catalog)
        if actual != case['expected']:
            raise ValueError(f"{case['name']}: expected {case['expected']}, got {actual}")
        if actual is None:
            value = validate_bytes(case['record'], raw, catalog)
            if raw != ccj1_bytes(value) or identity(value) != case['record_sha256']:
                raise ValueError(f"{case['name']}: noncanonical bytes or wrong identity")
            positives[case['name']] = case
        else:
            negatives[case['name']] = case
    for case in negatives.values():
        sibling = positives.get(case['positive'])
        if sibling is None or sibling['record'] != case['record']:
            raise ValueError(f"{case['name']}: missing valid sibling")
        if 'mutant' not in case:
            raise ValueError(f"{case['name']}: missing narrowing control")
    if {c['record'] for c in positives.values()} != set(RECORDS) or {
            c['record'] for c in negatives.values()} != set(RECORDS):
        raise ValueError('every record needs positive and negative bytes')
    return len(positives), len(negatives)


if __name__ == '__main__':
    positive, negative = check_corpus()
    print(f'leaf-1 member grammar: {positive} positive, {negative} negative; runtime unverified')
