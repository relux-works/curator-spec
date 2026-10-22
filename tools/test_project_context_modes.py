"""Static policy and instruction bytes only; no manager/native qualification."""
import copy
import json
import re
import types
import unittest
from unittest.mock import patch

import project_context_leaf1 as leaf

CASES = json.loads((leaf.ROOT / 'conformance' / leaf.NAMESPACE / 'mode-cases.json').read_text())['cases']
BY_NAME = {case['name']: case for case in CASES}

# Each plant relaxes one source-mode clause or changes one byte projection;
# other malformed-mode/item refusals remain enforced. No fixture is rewritten.
PLANTS = {
    'off-required-permissions': ("required = {'permissions', 'memory-off'}", "required = {'permissions', 'memory-off'} - ({'permissions'} if admission == 'off' else set())"),
    'off-required-memory-off': ("required = {'permissions', 'memory-off'}", "required = {'permissions', 'memory-off'} - ({'memory-off'} if admission == 'off' else set())"),
    'off-required-exclusion': ("if mode == 'strict':", "if mode == 'strict' and admission != 'off':"),
    'native-root': ("if mode == 'strict' and admission == 'admitted':", "if admission == 'admitted':"),
    'strict-root': ("if mode == 'strict' and admission == 'admitted':", "if mode == 'strict' and admission == 'admitted' and not facts['project_roots']:"),
    'strict-off-root': ("if mode == 'strict' and admission == 'admitted':", "if mode == 'strict':"),
    'native-notice': ("if mode == 'native-project' else None", "if mode == 'native-project' and admission == 'admitted' else None"),
    'unknown-mode': ("mode not in ('strict', 'native-project')", "mode not in ('strict', 'native-project', 'automatic')"),
    'unknown-admission': ("admission not in ('off', 'admitted')", "admission not in ('off', 'admitted', 'automatic')"),
    'registration-binding': ("facts['registration_mode'] != mode or facts['composition_mode'] != mode", "facts['composition_mode'] != mode"),
    'composition-binding': ("facts['registration_mode'] != mode or facts['composition_mode'] != mode", "facts['registration_mode'] != mode"),
    'mode-advertisement-native': ("mode not in facts['advertised_modes'] or not required.issubset", "(mode not in facts['advertised_modes'] and mode != 'native-project') or not required.issubset"),
    'mode-advertisement-strict': ("mode not in facts['advertised_modes'] or not required.issubset", "(mode not in facts['advertised_modes'] and mode != 'strict') or not required.issubset"),
    'required-permissions': ("required = {'permissions', 'memory-off'}", "required = {'memory-off'}"),
    'required-memory-off': ("required = {'permissions', 'memory-off'}", "required = {'permissions'}"),
    'required-native-source-exclusion': ("if mode == 'strict':", "if mode == 'strict' and types != ['context', 'skill', 'mcp']:"),
    'native-context': ("if mode == 'native-project' and 'context' in types:", "if mode == 'native-project' and 'context' in types and types != ['context']:"),
    'off-items': ("if admission == 'off' and types:", "if admission == 'off' and types and len(types) != 1:"),
    'selected-skill': ("MODE_ITEM_SURFACES[t] not in facts['surfaces'] for t in types", "MODE_ITEM_SURFACES[t] not in facts['surfaces'] and t != 'skill' for t in types"),
    'selected-mcp': ("MODE_ITEM_SURFACES[t] not in facts['surfaces'] for t in types", "MODE_ITEM_SURFACES[t] not in facts['surfaces'] and t != 'mcp' for t in types"),
}


def mutated(name):
    source = leaf.Path(leaf.__file__).read_text()
    module = types.ModuleType('mode_contract_mutant')
    module.__file__ = leaf.__file__
    if name != 'unknown-item':
        before, after = PLANTS[name]
        if source.count(before) != 1:
            raise ValueError('mode plant anchor is not unique: ' + name)
        source = source.replace(before, after, 1)
    exec(compile(source, leaf.__file__, 'exec'), module.__dict__)
    if name == 'unknown-item':
        module.MODE_ITEM_SURFACES = {**module.MODE_ITEM_SURFACES, 'rules': 'skills'}
    return module


class ModePolicyVectorTests(unittest.TestCase):
    # Publication reaches every enumerated static mode policy and byte output;
    # it does not establish that any advertised runtime surface is certified.
    def test_publication_entry(self):
        self.assertEqual(leaf.check_mode_vectors(), 26)
        import validate
        validate.validate_project_context_leaf1()

    # Each new required mode/admission member participates in the complete CCJ-1
    # record identity; changing it cannot retain the old digest.
    def test_modes_bind_record_identities(self):
        import hashlib
        import generate_project_context_vectors as generator
        examples = generator.examples()
        for record in ('registration', 'composition', 'project-context'):
            value = examples[record]
            changed = {**value, 'mode': 'native-project'}
            expected = json.dumps(changed, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
            self.assertEqual(leaf.identity(changed), hashlib.sha256(expected).hexdigest())
            self.assertNotEqual(leaf.identity(value), leaf.identity(changed))
        context = examples['project-context']
        self.assertNotEqual(leaf.identity(context), leaf.identity({**context, 'admission': 'off'}))
        adapter = examples['adapter']
        self.assertNotEqual(leaf.identity(adapter), leaf.identity({**adapter, 'modes': ['native-project']}))

    # Every named mutant must preserve a valid sibling and a different refusal,
    # fail the intended assertion (no crash/skip), and reach publication as the
    # first affected named mode case, with a green baseline before and after.
    def test_narrowing_controls_through_publication(self):
        import validate
        for case in CASES:
            if 'mutant' not in case:
                continue
            with self.subTest(case=case['name']):
                module = mutated(case['mutant'])
                sibling = BY_NAME[case['positive']]
                self.assertEqual(module.mode_projection(sibling['facts']), sibling['expected'])
                neighbor = BY_NAME['mode-admission-unknown' if case['name'] == 'mode-unknown' else 'mode-unknown']
                self.assertEqual(module.mode_projection(neighbor['facts']), neighbor['expected'])
                result = unittest.TestResult()
                unittest.FunctionTestCase(lambda: self.assertEqual(
                    module.mode_projection(case['facts']), case['expected'], case['name'])).run(result)
                self.assertFalse(result.errors)
                self.assertFalse(result.skipped)
                self.assertEqual(len(result.failures), 1)
                self.assertIn(case['name'], result.failures[0][1])
                first = next(c for c in CASES if module.mode_projection(c['facts']) != c['expected'])
                self.assertEqual(first['mutant'], case['mutant'])
                with patch.object(leaf, 'mode_projection', module.mode_projection):
                    with self.assertRaisesRegex(validate.ValidationFailure, re.escape(first['name']) + ': expected'):
                        validate.validate_project_context_leaf1()
        leaf.check_mode_vectors()


def vector_test(case):
    def test(self):
        before = copy.deepcopy(case['facts'])
        self.assertEqual(leaf.mode_projection(case['facts']), case['expected'], case['name'])
        self.assertEqual(case['facts'], before, 'static checks must not mutate supplied records/documents')
    test.__doc__ = case['claim'] + ' Static metadata/byte projection, not native execution.'
    return test


for case in CASES:
    setattr(ModePolicyVectorTests, 'test_' + case['name'].replace('-', '_'), vector_test(case))
