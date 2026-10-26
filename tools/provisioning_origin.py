"""Provisioning-origin/1 schema and authority vectors; no filesystem execution."""
from __future__ import annotations

import json
import ntpath
import posixpath
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = 'provisioning-origin-v1'
SELECTORS = {'claude_code': 'CLAUDE_CONFIG_DIR', 'codex_cli': 'CODEX_HOME',
             'opencode': 'XDG_CONFIG_HOME', 'pi': 'PI_CODING_AGENT_DIR',
             'muse': 'XDG_CONFIG_HOME'}


def clean_absolute(value):
    """Check spelling only; existing-ancestor identity belongs to the manager."""
    if value.startswith('/'):
        return not value.startswith('//') and posixpath.normpath(value) == value
    return ntpath.isabs(value) and ntpath.normpath(value) == value


def record_valid(record, schema):
    if not Draft202012Validator(schema, format_checker=FormatChecker()).is_valid(record):
        return False
    profile = record['binding']['profile']
    base = profile.split('.', 1)[0].upper()
    if (profile.endswith('.') or base in {'CON', 'PRN', 'AUX', 'NUL'}
            or (len(base) == 4 and base[:3] in {'COM', 'LPT'} and base[3] in '123456789')):
        return False
    if record['selector']['name'] != SELECTORS[record['adapter']]:
        return False
    return all(clean_absolute(value) for value in (
        record['operator_home'], record['native_root'], record['binding']['managed_target']))


def authority(case, schema):
    """Pure expected-authority projection, independent of today's selector."""
    record = case['record']
    if record is None:
        return {'diagnostic': 'environment_provisioning_origin_required', 'writes': []}
    if (not record_valid(record, schema) or record['adapter'] != case['adapter']
            or record['binding'] != case['binding']):
        return {'diagnostic': 'environment_provisioning_origin_invalid', 'writes': []}
    native = record['native_root']
    # This corpus uses the Codex file backend and POSIX fixture paths only.
    if case['credential_link'] not in (None, native + '/auth.json'):
        return {'diagnostic': 'environment_credential_conflict', 'writes': []}
    if case['credential_link'] is None and not case['repair']:
        return {'diagnostic': 'environment_home_stale', 'writes': []}
    return {'diagnostic': None, 'native_root': native,
            'writes': ['link-to-recorded-origin'] if case['credential_link'] is None else []}


def check_corpus(root=ROOT):
    schema = json.loads((root / 'schemas' / NAMESPACE / 'provisioning-origin-v1.schema.json').read_text())
    Draft202012Validator.check_schema(schema)
    suite = root / 'conformance' / NAMESPACE
    cases = json.loads((suite / 'schema-cases.json').read_text())
    vectors = json.loads((suite / 'authority-cases.json').read_text())
    if not cases or not any(c['valid'] for c in cases) or not any(not c['valid'] for c in cases):
        raise ValueError('schema corpus requires positive and negative cases')
    for case in cases:
        if record_valid(case['record'], schema) != case['valid']:
            raise ValueError('schema verdict differs: ' + case['name'])
    if not vectors or not any(c['expected']['diagnostic'] is None for c in vectors):
        raise ValueError('authority corpus requires valid controls')
    for case in vectors:
        if authority(case, schema) != case['expected']:
            raise ValueError('authority verdict differs: ' + case['name'])
    return len(cases), len(vectors)


if __name__ == '__main__':
    print('provisioning-origin specification cases:', check_corpus())
