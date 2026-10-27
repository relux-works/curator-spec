"""27 paired specification witnesses; no Curator runtime or real credential access."""
from __future__ import annotations

import copy
import dataclasses
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

import protected_inventory as p
import protected_inventory_generator as g

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/protected-commands/v1'
VECTORS = ROOT / 'conformance/protected-command-inventory-v1/vectors.json'


class InventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = (DATA / 'inventory.json').read_bytes()
        cls.metadata = p.decode((DATA / 'artifact.json').read_bytes())
        cls.identity = cls.metadata['command_inventory']
        cls.inventory = p.load_artifact(cls.raw, cls.identity)

    def setUp(self):
        # Synthetic fixture bytes only. All observed effects are captured immediately per call.
        self.temp = tempfile.TemporaryDirectory(prefix='protected-inventory-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.bin = self.root / 'base'; self.bin.mkdir()
        self.other = self.root / 'outside'; self.other.mkdir()
        self.admission = p.Admission((self.directory(self.bin),))

    def directory(self, path):
        info = path.lstat()
        return p.Directory(path, info.st_dev, info.st_ino)

    def executable(self, name, directory=None, data=b'fixture executable\n'):
        path = (directory or self.bin) / name
        path.write_bytes(data); path.chmod(0o755)
        return path

    def snapshot(self):
        result = {}
        for path in sorted(self.root.rglob('*')):
            info = path.lstat()
            result[str(path.relative_to(self.root))] = (
                info.st_dev, info.st_ino, info.st_mode, info.st_mtime_ns,
                os.readlink(path) if path.is_symlink() else path.read_bytes() if path.is_file() else None)
        return result

    def readonly(self, call):
        before = self.snapshot()
        try:
            # Neither arbitrary tree enumeration, process nor network belongs in the measured checker.
            with patch('os.scandir', side_effect=AssertionError('disk scan')), \
                 patch('subprocess.Popen', side_effect=AssertionError('subprocess')), \
                 patch('socket.socket', side_effect=AssertionError('network')):
                call()
            return 'ok'
        except p.Refusal as exc:
            return str(exc)
        finally:
            self.assertEqual(self.snapshot(), before, 'preimage changed after this call')

    def check(self, names, admission=None, artifacts=None, **kwargs):
        return self.readonly(lambda: p.check_exports(names,
            [self.inventory] if artifacts is None else artifacts,
            self.admission if admission is None else admission, **kwargs))

    def parse(self, artifact, identity=None):
        raw = artifact if isinstance(artifact, bytes) else p.ccj1(artifact)
        ident = dict(self.identity) if identity is None else identity
        if identity is None:
            ident['sha256'] = p.sha256(raw)
        return self.readonly(lambda: p.load_artifact(raw, ident))

    def wrapper(self):
        path = self.executable('acme-tool')
        info = path.stat()
        f = p.Forwarder(str(path), info.st_dev, info.st_ino, p.sha256(path.read_bytes()), 'owner-a', 'generation-a')
        return dataclasses.replace(self.admission, owned_forwarders=(f,),
                                   owners=((str(path), 'owner-a', 'generation-a'),))

    def source_fixture(self):
        # Expected names are independent requirements, not generated from the candidate output.
        aq = {'packages': [
            {'type': 'github_release', 'repo_owner': 'vendor', 'repo_name': 'default-tool'},
            {'type': 'go_install', 'path': 'example.invalid/tool/cmd/go-leaf'},
            {'type': 'github_release', 'repo_owner': 'vendor', 'repo_name': 'root', 'name': 'suite/subpackage',
             'overrides': [{'files': [{'name': 'platform-bin'}], 'build': {'files': [{'name': 'built-bin'}]}}],
             'version_overrides': [{'files': [{'name': 'old-bin'}]}]},
        ]}
        mi = {'ripgrep.toml': b'aliases=["rg"]\nbins=["rg", "rga"]\n',
              'multi.toml': b'bins=["first-bin", "second-bin"]\n'}
        expected = {'default-tool', 'go-leaf', 'subpackage', 'platform-bin', 'built-bin', 'old-bin',
                    'ripgrep', 'rg', 'rga', 'multi', 'first-bin', 'second-bin'}
        names, _ = g.aqua(aq)
        actual = names | set().union(*g.mise(mi).values())
        return actual, expected

    def execute(self, case):
        if case.startswith('baseline-'):
            # Independent reviewer regressions: no ambient PATH, no executable
            # in the admitted directory, no supplemental shell-name witness.
            names = {
                'baseline-absent': ('base64', 'sha256sum', 'file', 'comm', 'shopt', 'bindkey'),
                'baseline-case': ('BaSe64', 'SHA256SUM', 'FiLe', 'CoMm', 'ShOpT', 'BiNdKeY'),
                'baseline-suffix': ('base64.EXE.CmD', 'sha256sum.cmd', 'file.exe', 'comm.ps1', 'shopt.BAT', 'bindkey.COM'),
                'baseline-positive-absent': ('acme-base64', 'acme-sha256sum', 'acme-file', 'acme-comm', 'acme-shopt', 'acme-bindkey'),
                'baseline-positive-case': ('AcMe-BaSe64', 'ACME-SHA256SUM', 'AcMe-FiLe', 'AcMe-CoMm', 'AcMe-ShOpT', 'AcMe-BiNdKeY'),
                'baseline-positive-suffix': ('acme-base64.EXE.CmD', 'acme-sha256sum.cmd', 'acme-file.exe', 'acme-comm.ps1', 'acme-shopt.BAT', 'acme-bindkey.COM'),
            }[case]
            self.assertEqual(list(self.bin.iterdir()), [])
            results = []
            with patch.dict(os.environ):
                os.environ.pop('PATH', None)
                for i, name in enumerate(names):
                    result = self.check([name])
                    expected = 'ok' if case.startswith('baseline-positive-') else (
                        'static_overlap' if i < 4 else 'reserved_namespace')
                    self.assertEqual(result, expected, (case, name))
                    results.append(result)
            return results
        if case in ('git-script', 'ssh-alias'):
            return [self.check(['git' if case == 'git-script' else 'ssh'])]
        if case in ('unique-export', 'unique-alias', 'declared-alias', 'renamed-jq', 'explicit-admission'):
            return [self.check(['acme-jq' if case == 'renamed-jq' else 'acme-report'])]
        if case == 'manager-variants':
            return [self.check([n]) for n in ('curator', 'curator-run', 'curator-test', 'CuRaToR.EXE.CmD')]
        if case == 'git-variants':
            return [self.check([n]) for n in ('Git', 'GIT.exe', 'git.CMD', 'Git.EXE.CmD')]
        if case == 'distinct-dot-name': return [self.check(['git.helper'])]
        if case == 'shell-words': return [self.check([n]) for n in ('printf', 'eval', 'if')]
        if case == 'context-only': return [self.check([], artifacts=[])]
        if case == 'duplicate-exports': return [self.check(['acme-tool', 'ACME-TOOL.exe'])]
        if case == 'distinct-exports': return [self.check(['acme-tool', 'acme-tool-other'])]
        if case in ('forged-static-grants', 'changed-approval-tuples'):
            # There is no grant input/authority in this contract, irrespective of purported tuple values.
            fields = ('absent', 'package-carried', 'same-signer', 'yes') if case == 'forged-static-grants' else (
                'source', 'commit', 'directory', 'output-digest', 'alias', 'inventory', 'scope')
            return [self.check(['jq']) for _ in fields]
        if case in ('jq-on-base', 'custom-on-base', 'destination-collision'):
            name = 'jq' if case == 'jq-on-base' else 'acme-tool'
            self.executable(name)
            return [self.check([name])]
        if case in ('custom-outside-base', 'caller-collision-only'):
            self.executable('acme-tool', self.other)
            with patch.dict(os.environ, {'PATH': str(self.other)}):
                return [self.check(['acme-tool'])]
        if case in ('late-base-arrival', 'unrelated-base-arrival'):
            self.assertEqual(self.check(['acme-tool']), 'ok')  # Preflight positive, before drift.
            self.executable('acme-tool' if case == 'late-base-arrival' else 'unrelated-tool')
            return [self.check(['acme-tool'])]
        if case == 'invalid-admissions':
            missing = dataclasses.replace(self.admission, directories=())
            relative = p.Admission((p.Directory(Path('workspace/.agents/bin'), 0, 0),))
            stale = p.Admission((dataclasses.replace(self.directory(self.bin), inode=0),))
            results = [self.check(['acme-tool'], admission=a) for a in (missing, relative, stale)]
            results.append(self.readonly(lambda: p.check_exports(['acme-tool'], [self.inventory], None)))
            def unreadable():
                with patch.object(Path, 'lstat', side_effect=PermissionError('fixture')):
                    p.check_exports(['acme-tool'], [self.inventory], self.admission)
            results.append(self.readonly(unreadable))
            return results
        if case in ('mixed-forwarder-real', 'exact-forwarder'):
            admission = self.wrapper()
            if case == 'mixed-forwarder-real':
                self.executable('acme-other')
                return [self.check(['acme-tool', 'acme-other'], admission)]
            return [self.check(['acme-tool'], admission)]
        if case == 'fake-stale-foreign':
            admission = self.wrapper()
            results = [self.check(['acme-tool'])]  # Executable bytes alone confer no ownership.
            results.append(self.check(['acme-tool'], dataclasses.replace(admission, owners=())))
            (self.bin / 'acme-tool').write_bytes(b'changed same inode\n')
            results.append(self.check(['acme-tool'], admission))
            return results
        if case == 'colliding-or-unsafe-link':
            target = self.executable('real-target', self.other)
            (self.bin / 'acme-tool').symlink_to(target)
            allowed = dataclasses.replace(self.admission, allowed_link_roots=(self.other,))
            results = [self.check(['acme-tool'], allowed), self.check(['acme-tool'])]
            target.unlink()
            results.append(self.check(['acme-tool'], allowed))
            return results
        if case == 'nonexecutable-or-unrelated-link':
            (self.bin / 'acme-tool').write_bytes(b'not executable\n')
            target = self.executable('other-target', self.other)
            (self.bin / 'unrelated').symlink_to(target)
            return [self.check(['acme-tool'])] if os.name != 'nt' else [self.check(['acme-absent'])]
        if case == 'swapped-dir-or-owner':
            self.assertEqual(self.check(['acme-tool']), 'ok')
            self.bin.rename(self.root / 'previous'); self.bin.mkdir()
            results = [self.check(['acme-tool'])]
            self.admission = p.Admission((self.directory(self.bin),))
            admission = self.wrapper()
            self.assertEqual(self.check(['acme-tool'], admission), 'ok')
            results.append(self.check(['acme-tool'], dataclasses.replace(admission, owners=())))
            return results
        if case == 'stable-two-checks': return [self.check(['acme-tool']), self.check(['acme-tool'])]
        if case == 'invalid-artifacts':
            results = [self.parse(self.raw, {**self.identity, 'sha256': 'sha256:' + '0' * 64}),
                       self.parse(self.raw, {**self.identity, 'normalization': 'unknown'}),
                       self.parse(self.raw, {}), self.parse(self.raw[:-1]),
                       self.parse(b'{"schema_version":1,"schema_version":1}')]
            for mutate in (lambda x: x.update(schema_version=2),
                           lambda x: x['entries'].append(x['entries'][0]),
                           lambda x: x.update(extra=True)):
                bad = copy.deepcopy(self.inventory); mutate(bad); results.append(self.parse(bad))
            return results
        if case == 'known-artifact': return [self.parse(self.raw)]
        if case in ('newly-reserved', 'old-and-new-clean'):
            old = copy.deepcopy(self.inventory)
            old['entries'] = [e for e in old['entries'] if e['name'] != 'jq']
            self.assertEqual(self.check(['jq'], artifacts=[old]), 'ok')
            return [self.check(['jq' if case == 'newly-reserved' else 'acme-tool'], artifacts=[old, self.inventory])]
        if case in ('omitted-source-facts', 'complete-source-facts'):
            actual, expected = self.source_fixture()
            if case == 'omitted-source-facts':
                # Bounded control plants: omitting each independent source fact must fail this oracle.
                for omitted in ('default-tool', 'go-leaf', 'platform-bin', 'old-bin', 'rg', 'second-bin'):
                    self.assertNotEqual(actual - {omitted}, expected)
                return ['coverage_witness'] if actual - {'default-tool'} != expected else ['ok']
            self.assertEqual(actual, expected); return ['ok']
        if case == 'bad-source-names':
            calls = [lambda: g.aqua({'packages': [{'type': 'http', 'files': [{'name': '{{.Future}}'}]}]}),
                     lambda: g.aqua({'packages': [{'type': 'http', 'files': [{'name': True}]}]}),
                     lambda: g.mise({'tool.toml': b'bins=["a"]\nbins=["b"]\n'}),
                     lambda: g.mise({'tool.toml': b'bins=[false]\n'})]
            return [self.readonly(call) for call in calls]
        if case == 'literal-source':
            self.assertEqual(g.aqua({'packages': [{'type': 'http', 'files': [{'name': 'acme-tool'}]}]})[0], {'acme-tool'})
            return ['ok']
        if case in ('wrong-recipe-facts', 'correct-recipe-facts'):
            facts = (g.recipe_facts('coreutils', 'cat ginstall libstdbuf.so'),
                     g.recipe_facts('bash', '$BUILTIN variables\n$SHORT_DOC help\n$BUILTIN conditional\n$FUNCTION conditional_builtin\n'),
                     g.recipe_facts('zsh', 'BUILTIN("module-builtin", 0, 0)'))
            expected = ({'cat', 'install'}, {'conditional'}, {'module-builtin'})
            self.assertEqual(facts, expected)
            return ['coverage_witness'] if case == 'wrong-recipe-facts' and facts != ({'cat', 'ginstall', 'libstdbuf.so'}, {'variables', 'conditional'}, set()) else ['ok']
        if case == 'undeclared-hook': return [self.check(['acme-tool'], undeclared_surface=True)]
        if case == 'reordered-artifact':
            bad = copy.deepcopy(self.inventory); bad['entries'].reverse(); return [self.parse(bad)]
        if case == 'deterministic-and-real-change':
            a = {'z': ['seed-a'], 'a': '2026-10-27.1'}
            b = dict(reversed(list(a.items())))
            self.assertEqual(p.ccj1(a), p.ccj1(b))
            b['z'] = ['seed-b']; b['a'] = '2026-10-27.2'
            self.assertNotEqual(p.sha256(p.ccj1(a)), p.sha256(p.ccj1(b)))
            return ['ok']
        self.fail('unimplemented vector: ' + case)

    # Every research failure class has a working current-policy positive control; neither path writes fixtures.
    def test_27_paired_vectors(self):
        pairs = p.decode(VECTORS.read_bytes())['pairs']
        self.assertEqual([v['id'] for v in pairs], [f'PCI-{i:02}' for i in range(1, 28)])
        for vector in pairs:
            for side in ('negative', 'positive'):
                with self.subTest(vector=vector['id'], side=side):
                    # Each side has an independent namespace; no negative contaminates its control.
                    self.setUp()
                    outcomes = self.execute(vector[side]['case'])
                    self.assertTrue(outcomes)
                    expected = vector[side].get('reasons', ['ok'])
                    self.assertTrue(all(outcome in expected for outcome in outcomes), (outcomes, expected))

    # Counts are independent research requirements, not read from sources.lock.
    # Exact membership is separately audited against pinned upstream references.
    def test_required_system_shell_baselines(self):
        for source, count in [('posix', 171), ('coreutils', 109), ('bash', 61), ('zsh', 152)]:
            names = {entry['name'] for entry in self.inventory['entries']
                     if any(pin['source'] == 'seed-' + source for pin in entry['provenance'])}
            self.assertEqual(len(names), count, source)

    # The released artifact satisfies closed schemas, semantic ordering, full-byte identity and cleared provenance.
    def test_release_shape_and_identity(self):
        schemas = [p.decode(f.read_bytes()) for f in (ROOT / 'schemas/protected-command-inventory-v1').glob('*.schema.json')]
        registry = Registry().with_resources((s['$id'], Resource.from_contents(s)) for s in schemas)
        by_name = {s['$id'].rsplit('/', 1)[-1]: s for s in schemas}
        for name, value in [('inventory', self.inventory), ('artifact', self.metadata),
                            ('sources', p.decode((DATA / 'sources.lock.json').read_bytes())), ('identity', self.identity)]:
            validator = Draft202012Validator(by_name[name + '.schema.json'], registry=registry)
            validator.validate(value)
            for field in value:
                bad = copy.deepcopy(value); del bad[field]
                self.assertFalse(validator.is_valid(bad), (name, 'missing', field))
            self.assertFalse(validator.is_valid({**value, 'extra': True}))
        self.assertEqual(self.metadata['bytes'], len(self.raw))
        self.assertEqual(self.metadata['entry_count'], len(self.inventory['entries']))
        self.assertEqual(self.inventory['extractor_sha256'], g.extractor_digest())
        for entry in self.inventory['entries']:
            self.assertFalse(any(next(s for s in self.inventory['source_pins'] if s['id'] == x['source'])['status'] == 'reference-only' for x in entry['provenance']))

    # Bounds reject without truncation; suffix folding and export grammar remain distinct.
    def test_bounds_and_parser_controls(self):
        for raw, reason in [(b'{"a":1,"a":2}', 'duplicate_json_key'), (b'-0', 'unsafe_number'),
                            (b'1.0', 'noninteger_number'), (b'"\\ud800"', 'invalid_json'),
                            (b' ' * (p.MAX_BYTES + 1), 'artifact_too_large')]:
            with self.assertRaisesRegex(p.Refusal, '^' + reason + '$'): p.decode(raw)
        self.assertEqual(p.decode(b'{"a":0}'), {'a': 0})
        for name in ('a' * 129, 'CON.exe', 'acme.', '../git', 'git\n'):
            with self.assertRaises(p.Refusal): p.export_key(name)
        self.assertEqual(p.export_key('a' * 128), 'a' * 128)
        for field, value in [('source_pins', []), ('entries', self.inventory['entries'] * 25)]:
            bad = copy.deepcopy(self.inventory); bad[field] = value
            self.assertEqual(self.parse(bad), 'inventory_bounds')
        bad = copy.deepcopy(self.inventory); bad['entries'][0]['spellings'] *= 33
        self.assertEqual(self.parse(bad), 'inventory_bounds')
        self.assertEqual(p.normalize('Git.EXE.CmD'), 'git')
        # Known bypass plant: disabling fold admits uppercase Git; the expected static assertion detects it.
        with patch.object(p, 'normalize', side_effect=lambda x: x):
            self.assertEqual(self.check(['Git']), 'ok')
        self.assertEqual(self.check(['Git']), 'static_overlap')


if __name__ == '__main__': unittest.main()
