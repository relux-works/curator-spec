"""Offline maintainer controls for the pinned YAML adapter and complete regeneration."""
from __future__ import annotations

import argparse
import copy
import os
from pathlib import Path
import subprocess
import tempfile

import protected_inventory as p
import protected_inventory_generator as g


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    args = parser.parse_args()
    env = dict(os.environ)
    for name in ('GIT_DIR', 'GIT_WORK_TREE', 'SSH_AUTH_SOCK', 'GOFLAGS'):
        env.pop(name, None)
    # These positive/negative controls exercise real YAML parsing, not post-parser JSON alone.
    cases = [
        ('literal-and-anchor', b'packages:\n- &base\n  type: http\n  files: [{name: acme-tool}]\n- *base\n', None),
        ('syntax', b'packages: [\n', 'Psych::SyntaxError'),
        ('documents', b'packages: []\n---\npackages: []\n', 'yaml_document_count'),
        ('duplicate', b'packages: []\npackages: []\n', 'duplicate_or_complex_yaml_key'),
        ('object-tag', b'packages: !ruby/object:Object {}\n', 'Psych::DisallowedClass'),
        ('cycle', b'packages: &cycle [*cycle]\n', 'yaml_expansion_bounds'),
        ('coercion', b'packages: [{type: http, files: [{name: true}]}]\n', 'invalid_source_aqua_name'),
        ('template', b'packages: [{type: http, files: [{name: "{{.Future}}"}]}]\n', 'unresolved_name'),
    ]
    with tempfile.TemporaryDirectory(prefix='protected-source-controls-') as directory:
        path = Path(directory) / 'fixture.yaml'
        for name, raw, expected in cases:
            path.write_bytes(raw)
            result = subprocess.run(['ruby', str(g.ROOT / 'tools/protected_inventory_prepare.rb'), str(path)],
                                    env=env, capture_output=True, check=False)
            if expected in ('invalid_source_aqua_name', 'unresolved_name') or expected is None:
                if result.returncode:
                    raise AssertionError((name, result.stderr.decode()))
                try:
                    names, _ = g.aqua(p.decode(result.stdout))
                except p.Refusal as exc:
                    if str(exc) != expected: raise
                else:
                    if expected is not None or names != {'acme-tool'}:
                        raise AssertionError((name, names, expected))
            elif result.returncode == 0 or expected not in result.stderr.decode():
                raise AssertionError((name, result.returncode, result.stderr.decode()))
            if path.read_bytes() != raw:
                raise AssertionError('source preimage changed')
    prepared = subprocess.run(['ruby', str(g.ROOT / 'tools/protected_inventory_prepare.rb'),
                               str(args.inputs / 'aqua/registry.yaml')], env=env, capture_output=True, check=True)
    if prepared.stdout != (args.inputs / 'aqua/registry.json').read_bytes():
        raise AssertionError('prepared_source_mismatch')
    # Two complete offline runs, pinned hashes and independent coverage counts must all agree.
    first = g.generate(args.inputs)
    with subprocess_env_locale():
        second = g.generate(args.inputs)
    if first != second or first != (g.DATA / 'inventory.json').read_bytes():
        raise AssertionError('regeneration_mismatch')
    manifest = p.decode((g.DATA / 'sources.lock.json').read_bytes())
    bad = copy.deepcopy(manifest); bad['coverage']['counts']['aqua'] -= 1
    try:
        g.generate(args.inputs, bad)
    except p.Refusal as exc:
        if str(exc) != 'coverage_witness': raise
    else:
        raise AssertionError('independent coverage plant was not detected')
    print('PASS: 8 YAML adapter controls; pinned YAML preparation; 2 full offline regenerations; coverage plant; ' + p.sha256(first))


class subprocess_env_locale:
    """Generation uses neither locale sorting nor ambient PATH execution."""
    def __enter__(self):
        self.before = {key: os.environ.get(key) for key in ('LC_ALL', 'LANG')}
        os.environ.update(LC_ALL='C', LANG='C')
    def __exit__(self, *_):
        for key, value in self.before.items():
            if value is None: os.environ.pop(key, None)
            else: os.environ[key] = value


if __name__ == '__main__': main()
