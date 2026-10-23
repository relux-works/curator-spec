"""Unreleased seed-C specification witnesses, not a native config writer."""
from __future__ import annotations

import copy
import json
import tomllib
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

NAMESPACE = 'codex-seed-c-v1'
MARKER = 'agent-environment-marker-v7.schema.json'
NAMES = {
    'c-strips-foreign', 'c-strips-missing', 'c-strips-existing', 'c-strips-symlink',
    'c-preserves-unrelated', 'c-empty', 'c-empty-projects', 'c-strips-trust-and-mcp',
    'c-preserves-nested-tables-and-arrays',
    'c-strips-untrusted',
    'b-retains-trust', 'a-retains-trust-and-mcp', 'c-invalid-toml',
    'c-status-empty-a',
} | {f'c-{op}-preserves-{rev}' for op in ('repair', 'status')
     for rev in ('pre-rule', 'a', 'b', 'c')}


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def load_corpus(root):
    return load(root / 'conformance' / NAMESPACE / 'cases.json')


def load_schema(root):
    return load(root / 'schemas' / NAMESPACE / MARKER)


def outcome(case):
    """Evaluate the normative data model without filesystem path inspection."""
    config = tomllib.loads(case['config']) if case['operation'] != 'provision' else {}
    record = copy.deepcopy(case['record'])
    writes, diagnostic, names = [], None, []
    revision = case['revision']
    if case['operation'] == 'provision':
        try:
            config = tomllib.loads(case['config'])
        except tomllib.TOMLDecodeError:
            return dict(config=None, record=None, writes=[],
                        diagnostic='environment_seed_unreadable', names=[])
        names = sorted(config.get('mcp_servers', {}))
        if revision != 'A':
            config.pop('mcp_servers', None)
        if revision == 'C':
            config.pop('projects', None)
        record = dict(revision=revision, native_mcp_servers=names)
        writes = ['config.toml', '.agent-environment.json']
        if names:
            diagnostic = ('mcp_native_servers_ungoverned' if revision == 'A'
                          else 'mcp_native_servers_not_inherited')
    elif record is None:
        diagnostic = 'mcp_seed_unstripped'
    else:
        names = record['native_mcp_servers']
        if names:
            diagnostic = ('mcp_seed_unstripped' if record['revision'] == 'A'
                          else 'mcp_native_servers_not_inherited')
    return dict(config=config, record=record, writes=writes,
                diagnostic=diagnostic, names=names)


def check_case(case):
    expected = case['expected']
    result = outcome(case)
    config = (None if expected['seed_config'] is None
              else tomllib.loads(expected['seed_config']))
    if result['config'] != config:
        raise ValueError(f"{case['name']}: seed configuration differs")
    for key in ('record', 'writes', 'diagnostic', 'names'):
        if result[key] != expected[key]:
            raise ValueError(f"{case['name']}: {key} differs")
    # Preservation here pins the specified output bytes, not real manager I/O.
    if case['operation'] != 'provision' and expected['seed_config'] != case['config']:
        raise ValueError(f"{case['name']}: seed configuration bytes changed")
    if case['operation'] == 'provision' and result['config'] is not None:
        native = tomllib.loads(case['config'])
        if (case['revision'] == 'C' and not {'projects', 'mcp_servers'} & native.keys()
                and expected['seed_config'] != case['config']):
            raise ValueError(f"{case['name']}: unfiltered seed configuration bytes changed")


def check_markers(root):
    predecessor = load(root / 'schemas/local-setup-token-v1/agent-environment-marker-v6.schema.json')
    expected = copy.deepcopy(predecessor)
    expected['$id'] = f'https://relux-works.github.io/curator-spec/schemas/{NAMESPACE}/{MARKER}'
    expected['title'] = 'agent-environment-marker-v7'
    expected['properties']['version']['const'] = 7
    expected['properties']['codex_seed_record']['properties']['revision']['enum'] = ['A', 'B', 'C']
    schema = load_schema(root)
    if schema != expected:
        raise ValueError('marker successor changes more than version and seed revision')
    resources = []
    for path in sorted((root / 'schemas').rglob('*.schema.json')):
        value = load(path)
        resources.append((value['$id'], Resource.from_contents(value)))
    registry = Registry().with_resources(resources)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, registry=registry)
    base = load(root / 'conformance/local-setup-token-v1/controls.json')['agent-environment-marker-v6']
    base.update(version=7, credential_source={'mode': 'per-home'}, seeds=['config.toml'])
    for revision in ('A', 'B', 'C'):
        marker = dict(base, codex_seed_record=dict(revision=revision, native_mcp_servers=[]))
        if not validator.is_valid(marker):
            raise ValueError('marker successor rejects valid recorded revision')
        if revision == 'C':
            for namespace, version in (('v1', 1), ('v1', 2), ('v1', 3),
                                       ('rc7-carriers-v1', 5), ('local-setup-token-v1', 6)):
                old = load(root / 'schemas' / namespace / f'agent-environment-marker-v{version}.schema.json')
                old_marker = copy.deepcopy(marker)
                old_marker['version'] = version
                if version < 5:
                    old_marker.pop('codex_settings')
                if version < 6:
                    old_marker.pop('credential_source')
                if version < 3:
                    old_marker.pop('hash_version')
                old_validator = Draft202012Validator(old, registry=registry)
                old_marker['codex_seed_record']['revision'] = 'B'
                if not old_validator.is_valid(old_marker):
                    raise ValueError('legacy marker positive control is invalid')
                old_marker['codex_seed_record']['revision'] = 'C'
                if old_validator.is_valid(old_marker):
                    raise ValueError('legacy marker admits revision C')
    for mutate in (
        lambda m: m.update(version=6),
        lambda m: m['codex_seed_record'].update(revision='D'),
        lambda m: m['codex_seed_record'].update(project_paths=['/work/synthetic']),
        lambda m: m['codex_seed_record'].update(native_mcp_servers='example'),
        lambda m: m['codex_seed_record'].update(native_mcp_servers=['example', 'example']),
        lambda m: m.update(codex_settings={'projects': {}}),
        lambda m: m.update(mode='linked'),
        lambda m: m.pop('credential_source'),
    ):
        bad = copy.deepcopy(marker)
        mutate(bad)
        if validator.is_valid(bad):
            raise ValueError('marker successor admits invalid control')


def check_corpus(root):
    corpus = load_corpus(root)
    if (corpus.get('corpus') != NAMESPACE or len(corpus['cases']) != len(NAMES)
            or {case['name'] for case in corpus['cases']} != NAMES):
        raise ValueError('case inventory differs')
    for case in corpus['cases']:
        check_case(case)
    check_markers(root)
    return len(corpus['cases'])


if __name__ == '__main__':
    print(f'seed-C specification cases: {check_corpus(Path(__file__).resolve().parents[1])}')
