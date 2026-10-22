#!/usr/bin/env python3
"""Narrow actual leaf-1 schema/decoder gates; require their named assertions red."""
import copy
import sys
import unittest
from unittest.mock import patch

from referencing import Resource

import project_context_leaf1 as leaf
from test_project_context_leaf1 import CATALOG, CORPUS, MANIFEST, assert_case

# Each source plant admits a bounded forbidden subclass while retaining the
# general gate. No fixture, expected verdict or runtime result is rewritten.
REPLACEMENTS = {
    'mode-order': ("if value['modes'] != sorted(value['modes'], key=lambda s: s.encode('utf-8')):",
                   "if len(value['modes']) != 2 and value['modes'] != sorted(value['modes'], key=lambda s: s.encode('utf-8')):"),
    'identity-sig': ("def identity(value):\n    return", "def identity(value):\n    if isinstance(value, dict):\n        value = {k: v for k, v in value.items() if k != 'sig'}\n    return"),
    'negative-zero': ('parse_int=integer', 'parse_int=int'),
    'path-component': ("component.endswith(('.', ' '))", "component in ('.', '..')"),
    'file-order': ("if paths != sorted(paths, key=lambda p: p.encode('utf-8')):",
                   "if len(paths) != 2 and paths != sorted(paths, key=lambda p: p.encode('utf-8')):"),
    'file-duplicate': ('if len(set(normalized)) != len(normalized):',
                       'if len(set(normalized)) != len(normalized) and len(set(paths)) != 1:'),
    'file-case': ("unicodedata.normalize('NFC', p).casefold()", "unicodedata.normalize('NFC', p)"),
    'file-unicode': ("unicodedata.normalize('NFC', p).casefold()", 'p.casefold()'),
    'file-ancestor': ("for n in range(1, len(p.split('/')))):", "for n in range(2, len(p.split('/')))):"),
    'generation-ids': ('if len(set(ids)) != len(ids):', 'if len(ids) != 2 and len(set(ids)) != len(ids):'),
    'surface-order': ("if value['surfaces'] != sorted(value['surfaces'], key=lambda s: s.encode('utf-8')):",
                      "if len(value['surfaces']) != 2 and value['surfaces'] != sorted(value['surfaces'], key=lambda s: s.encode('utf-8')):"),
    'fragment-digest': ("for k in ('context_ref', 'context_sha256')):", "for k in ('context_ref',)) :"),
    'fragment-ref': ("for k in ('context_ref', 'context_sha256')):", "for k in ('context_sha256',)) :"),
    'root-parent': ("and '..' not in PurePosixPath(value).parts", "and PurePosixPath(value).parts.count('..') <= 1"),
    'repository-remote': ("if not remote_safe(value['repository']['primary_remote']):",
                          "if not remote_safe(value['repository']['primary_remote'].split('?', 1)[0] if isinstance(value['repository']['primary_remote'], str) else None):"),
    'server-normalization': ("if field in server and server[field] != sorted(set(server[field]), key=lambda s: s.encode('utf-8')):",
                             "if field in server and len(server[field]) != 2 and server[field] != sorted(set(server[field]), key=lambda s: s.encode('utf-8')):"),
    'server-environments': ("{'claude_code', 'codex_cli', 'muse', 'opencode', 'pi'}", "{'claude_code', 'codex_cli', 'muse', 'opencode', 'pi', 'future'}"),
    'server-digest': ("if payload['server_sha256'] != 'sha256:' + identity(server):",
                      "if payload['server_sha256'][8:] != ('sha256:' + identity(server))[8:]:"),
    'duplicate-member': ('if key in result:', "if key in result and key != 'checkout_id':"),
    'utf8': ("raw.decode('utf-8')", "raw.decode('utf-8', errors='replace')"),
    'trailing-input': ("value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,\n                           parse_int=integer, parse_float=non_integer, parse_constant=non_integer)",
                       "value = json.JSONDecoder(object_pairs_hook=pairs, parse_int=integer, parse_float=non_integer, parse_constant=non_integer).raw_decode(raw.decode('utf-8'))[0]"),
    'oversized-integer': ('parse_int=integer', "parse_int=lambda n: 0 if len(n) > 4300 else integer(n)"),
    'fraction': ('parse_float=non_integer', "parse_float=lambda n: int(n[:-2]) if n.endswith('.0') else non_integer(n)"),
    'surrogate': ('ensure_ascii=False', 'ensure_ascii=True'),
}


def mutated(case):
    control = case['mutant']
    catalog = CATALOG
    module = leaf
    if 'schema' in control:
        name = control['schema']
        uri = ('https://relux-works.github.io/curator-spec/schemas/' +
               (name if '/' in name else leaf.NAMESPACE + '/' + name) + '.schema.json')
        schema = copy.deepcopy(catalog[1].contents(uri))
        node = schema
        for key in control['path'][:-1]:
            node = node[key]
        key = control['path'][-1]
        present = key in node if isinstance(node, dict) else key < len(node)
        if present:
            if node[key] == control['value']:
                raise ValueError('mutation did not change the schema')
        node[key] = control['value']
        records = copy.deepcopy(catalog[0])
        if name in records:
            records[name] = schema
        catalog = records, catalog[1].with_resource(uri, Resource.from_contents(schema))
    else:
        import types
        module = types.ModuleType('leaf1_mutant')
        source = leaf.Path(leaf.__file__).read_text()
        if 'source' in control:
            old, new = REPLACEMENTS[control['source']]
            if source.count(old) != 1:
                raise ValueError('source mutation anchor is not unique')
            source = source.replace(old, new, 1)
        module.__file__ = leaf.__file__
        exec(compile(source, leaf.__file__, 'exec'), module.__dict__)
        if 'constant' in control:
            if getattr(module, control['constant']) == control['value']:
                raise ValueError('constant mutation did not apply')
            setattr(module, control['constant'], control['value'])
    return module, catalog


def run_case(case):
    positives = {c['name']: c for c in MANIFEST['cases'] if c['expected'] is None}
    test = unittest.TestCase()
    assert_case(test, positives[case['positive']])
    assert_case(test, case)
    module, catalog = mutated(case)
    assert_case(test, positives[case['positive']], module, catalog)
    # Keep a different closed record's unknown-member rejection, so a whole
    # validator bypass cannot masquerade as a narrowing control.
    neighbor = next(c for c in MANIFEST['cases'] if c['name'].endswith('-unknown')
                    and c['record'] != case['record'])
    assert_case(test, neighbor, module, catalog)
    result = unittest.TestResult()
    unittest.FunctionTestCase(lambda: assert_case(unittest.TestCase(), case, module, catalog),
                              description=case['name']).run(result)
    if result.errors or result.skipped or len(result.failures) != 1 or result.testsRun != 1:
        raise ValueError(f"{case['name']}: not the intended assertion failure: {result.errors}")
    if case['name'] not in result.failures[0][1]:
        raise ValueError('failure did not name the target case')
    print('EXPECTED RED ' + case['name'])


def file_count_control():
    from test_project_context_leaf1 import ProjectContextLeaf1Tests
    case = {'mutant': {'schema': 'common', 'path': ['$defs', 'files', 'maxItems'], 'value': 10001}}
    _, catalog = mutated(case)
    with patch.object(leaf, 'schemas', return_value=catalog):
        result = unittest.TestResult()
        ProjectContextLeaf1Tests('test_file_count_schema_cap').run(result)
    if result.errors or result.skipped or len(result.failures) != 1 or 'file count gate' not in result.failures[0][1]:
        raise ValueError('file-count plant did not fail its intended assertion')
    print('EXPECTED RED file-count-schema')


def identity_control():
    from test_project_context_leaf1 import ProjectContextLeaf1Tests
    module, _ = mutated({'mutant': {'source': 'identity-sig'}})
    with patch.object(leaf, 'identity', module.identity):
        result = unittest.TestResult()
        ProjectContextLeaf1Tests('test_identity_includes_every_member').run(result)
    if (result.errors or result.skipped or len(result.failures) != 1
            or 'test_identity_includes_every_member' not in result.failures[0][1]):
        raise ValueError('identity plant did not fail its intended assertion')
    print('EXPECTED RED identity-includes-sig')


def main():
    negatives = [c for c in MANIFEST['cases'] if c['expected'] is not None]
    selected = sys.argv[2] if len(sys.argv) == 3 and sys.argv[1] == '--mutant' else None
    if sys.argv[1:] and selected is None:
        raise ValueError('usage: check_project_context_leaf1_controls.py [--mutant NAME]')
    if selected:
        case = next((c for c in negatives if c['name'] == selected), None)
        if case is None:
            raise ValueError('unknown mutant')
        run_case(case)
        return 1  # explicit single control is intentionally red
    leaf.check_corpus()
    for case in negatives:
        run_case(case)
    file_count_control()
    identity_control()
    leaf.check_corpus()
    print(f'{len(negatives) + 2} narrowing controls killed by their named assertions; runtime unverified')
    return 0


if __name__ == '__main__':
    sys.exit(main())
