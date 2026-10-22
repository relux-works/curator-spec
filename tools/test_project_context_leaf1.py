"""Leaf-1 grammar claims; no manager, filesystem or provider is exercised."""
import copy
import hashlib
import json
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator

import project_context_leaf1 as leaf

CORPUS = leaf.ROOT / 'conformance' / leaf.NAMESPACE
MANIFEST = json.loads((CORPUS / 'manifest.json').read_text())
CATALOG = leaf.schemas()


def assert_case(test, case, module=leaf, catalog=CATALOG):
    raw = (CORPUS / case['file']).read_bytes()
    if case['expected'] and case['expected']['gate'] == 'schema':
        # Assert the specific schema gate before semantic checks. A mutant that
        # lets malformed objects crash later is not a successful schema refusal.
        value = module.decode(raw)
        validator = Draft202012Validator(catalog[0][case['record']], registry=catalog[1])
        test.assertFalse(validator.is_valid(value), case['name'] + ': schema gate')
    test.assertEqual(module.verdict(case['record'], raw, catalog), case['expected'], case['name'])
    if case['expected'] is None:
        value = module.validate_bytes(case['record'], raw, catalog)
        test.assertEqual(module.ccj1_bytes(value), raw, case['name'] + ': canonical bytes')
        test.assertEqual(module.identity(value), case['record_sha256'], case['name'] + ': full identity')


class ProjectContextLeaf1Tests(unittest.TestCase):
    # Every published positive and typed negative is reached by make validate;
    # missing siblings, changed bytes and incomplete record coverage also fail.
    def test_publication_entry(self):
        self.assertEqual(leaf.check_corpus(), (53, 341))
        import validate
        validate.validate_project_context_leaf1()

    # A deliberately wrong lease-zero verdict must fail at the repository
    # publication entry with its exact case name, not an unrelated setup error.
    def test_publication_entry_control(self):
        import validate
        original = leaf.Path.read_text

        def planted(path, *args, **kwargs):
            text = original(path, *args, **kwargs)
            if path == CORPUS / 'manifest.json':
                value = json.loads(text)
                next(c for c in value['cases'] if c['name'] == 'lease-zero')['expected'] = None
                return json.dumps(value)
            return text

        with patch.object(leaf.Path, 'read_text', planted):
            with self.assertRaisesRegex(validate.ValidationFailure, 'lease-zero: expected None'):
                validate.validate_project_context_leaf1()
        self.assertEqual(leaf.check_corpus(), (53, 341))

    # The publication oracle reaches the lexical negative-zero gate. Its
    # ordinary-zero sibling stays valid when only the shared integer hook is
    # narrowed, and the publication failure names the forbidden spelling.
    def test_negative_zero_publication_control(self):
        import validate
        sibling = next(c for c in MANIFEST['cases'] if c['name'] == 'snapshot-manifest-zero-size')
        assert_case(self, sibling)
        with patch.object(leaf, 'integer', int):
            assert_case(self, sibling)
            with self.assertRaisesRegex(validate.ValidationFailure, 'snapshot-manifest-negative-zero: expected'):
                validate.validate_project_context_leaf1()
        validate.validate_project_context_leaf1()

    # Deterministic regeneration checks the actual committed bytes without
    # rewriting them. Every CI unit-test invocation executes this command path.
    def test_regeneration(self):
        import generate_project_context_vectors as generator
        with patch('sys.argv', ['generate_project_context_vectors.py', '--check']):
            generator.main()

    # The aggregate control command must kill actual narrowing mutants with
    # named assertion failures; crashes and skips do not satisfy this check.
    def test_narrowing_controls(self):
        import contextlib
        import io
        import check_project_context_leaf1_controls as controls
        output = io.StringIO()
        with patch('sys.argv', ['check_project_context_leaf1_controls.py']):
            with contextlib.redirect_stdout(output):
                self.assertEqual(controls.main(), 0)
        self.assertIn('343 narrowing controls killed', output.getvalue())

    # Record identity includes all members, including sig; JSON spelling/order
    # and optional-member presence do not silently drop bytes from CCJ-1 input.
    def test_identity_includes_every_member(self):
        self.assertEqual(leaf.ccj1_bytes({'z': 1, 'a': 'é'}), b'{"a":"\xc3\xa9","z":1}')
        self.assertNotEqual(leaf.identity({'a': 1}), leaf.identity({'a': 1, 'sig': 'sample'}))
        self.assertEqual(leaf.identity({'a': 1}), hashlib.sha256(b'{"a":1}').hexdigest())
        self.assertNotEqual(leaf.identity({'a': 1}), hashlib.sha256(b'{"a":1}\n').hexdigest())
        self.assertNotEqual(leaf.identity({'grant_ref': 'grant:sample'}), leaf.identity({}))

    # The file-count schema accepts 10,000 and refuses 10,001 entries in memory.
    # Such complete records exceed the earlier 1 MiB cap; this is not a claim
    # that a 10,000-file record can be emitted within that independent cap.
    def test_file_count_schema_cap(self):
        catalog = leaf.schemas()
        schema = catalog[1].contents('https://relux-works.github.io/curator-spec/schemas/' + leaf.NAMESPACE + '/common.schema.json')
        validator = Draft202012Validator({'$ref': schema['$id'] + '#/$defs/files'}, registry=catalog[1])
        files = [{'path': 'f', 'size': 0, 'sha256': 'a' * 64, 'mode': '0600'}] * 10000
        self.assertTrue(validator.is_valid(files))
        self.assertFalse(validator.is_valid(files + [files[0]]), 'file count gate')

    # The depth decoder accepts 16 containers, rejects 17, and preserves valid
    # JSON whitespace/order. These decoder inputs alone are not record schemas.
    def test_decode_boundaries(self):
        value = 0
        for _ in range(16):
            value = [value]
        self.assertEqual(leaf.decode(b'[' * 16 + b'0' + b']' * 16), value)
        with self.assertRaisesRegex(leaf.ContractError, 'record-depth'):
            leaf.decode(b'[' * 17 + b'0' + b']' * 17)
        self.assertEqual(leaf.decode(b' { "b": 2, "a": 1 }\n'), {'a': 1, 'b': 2})
        self.assertEqual(leaf.decode(b'{}' + b' ' * (leaf.MAX_BYTES - 2)), {})
        with self.assertRaisesRegex(leaf.ContractError, 'record-size'):
            leaf.decode(b'{}' + b' ' * (leaf.MAX_BYTES - 1))

    # Released full fragments remain strict and unchanged: valid legacy bytes
    # pass and the new project members are refused before runtime resolution.
    def test_frozen_fragments_refuse_new_members(self):
        from referencing import Registry, Resource
        resources = []
        for namespace in ('v1', 'rc7-carriers-v1', 'profile-codex-settings-v1'):
            for path in (leaf.ROOT / 'schemas' / namespace).glob('*.schema.json'):
                schema = json.loads(path.read_text())
                resources.append((schema['$id'], Resource.from_contents(schema)))
        registry = Registry().with_resources(resources)
        project = json.loads((CORPUS / 'bytes/project-context-valid.json').read_bytes())
        for version in (4, 5):
            name = f'launch-env-fragment-v{version}'
            namespace = 'v1' if version == 4 else 'rc7-carriers-v1'
            schema = json.loads((leaf.ROOT / 'schemas' / namespace / (name + '.schema.json')).read_text())
            validator = Draft202012Validator(schema, registry=registry)
            if version == 4:
                paths = sorted((leaf.ROOT / 'conformance/environments-muse-v4/schema-cases').glob('valid*.json'))
            else:
                paths = [leaf.ROOT / 'conformance/rc7-carriers-v1/canonical/launch-env-fragment-v5.ccj']
            valid = [json.loads(p.read_text()) for p in paths]
            valid = [v for v in valid if isinstance(v, dict) and validator.is_valid(v)]
            self.assertTrue(valid, name + ': existing positive control')
            value = copy.deepcopy(valid[0])
            value['project_context'] = project
            self.assertFalse(validator.is_valid(value), name + ': new member rejected')


def vector_test(case):
    # Each case's manifest claim names the exact accepted or refused input;
    # every negative links to a passing sibling of the same record schema.
    def test(self):
        assert_case(self, case)
    test.__doc__ = case['claim']
    return test


for _case in MANIFEST['cases']:
    setattr(ProjectContextLeaf1Tests, 'test_vector_' + _case['name'].replace('-', '_'), vector_test(_case))


if __name__ == '__main__':
    unittest.main()
