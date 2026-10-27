"""Publication consistency and bounded controls; no Curator install is run."""
from copy import deepcopy
import json
import re
import unittest
from unittest.mock import patch

import profile_skill_plan as plan
from assurance import ccj1_sha256


class ProfileSkillPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validators = plan.catalog()
        cls.corpus = plan.ROOT / 'conformance' / plan.FAMILY
        cls.baseline = json.loads((cls.corpus / 'baseline.json').read_text(encoding='utf-8'))
        cls.cases = json.loads((cls.corpus / 'cases.json').read_text(encoding='utf-8'))
        cls.schemas = json.loads((cls.corpus / 'schema-cases.json').read_text(encoding='utf-8'))

    # Every published structural/semantic verdict matches the proposal oracle.
    # Abstract state labels do not establish filesystem effects or runtime safety.
    def test_published_vectors(self):
        self.assertEqual(plan.check_corpus(), (42, 144))

    # Every uppercase MUST belongs to a unique catalog clause with admitted and
    # rejected controls. Shared positive controls prove only their named inputs.
    def test_obligation_inventory(self):
        text = (plan.ROOT / 'protocol/profile-skill-plan-proposal.md').read_text(encoding='utf-8')
        ids = re.findall(r'\*\*\[(PS[PR]\d\d)\]\*\*', text)
        self.assertEqual(len(ids), 12)
        self.assertEqual(len(set(ids)), len(ids))
        chunks = re.split(r'\*\*\[PS[PR]\d\d\]\*\*', text)
        self.assertNotRegex(chunks[0], r'\bMUST\b')
        for clause in chunks[1:]:
            self.assertEqual(len(re.findall(r'\bMUST\b', clause)), 1)
        all_cases = self.cases + self.schemas
        self.assertEqual(len({c['id'] for c in all_cases}), len(all_cases))
        self.assertEqual(set(ids), {o for c in all_cases for o in c['obligations']})
        for obligation in ids:
            verdicts = {c.get('valid', not c.get('negative',
                        c.get('expected', {}).get('diagnostic') is not None))
                        for c in all_cases if obligation in c['obligations']}
            self.assertEqual(verdicts, {True, False}, obligation)
        codes = {c['expected']['diagnostic'] for c in self.cases}
        # Every named refusal in this proposal has a semantic counterexample.
        for code in re.findall(r'`((?:profile_skill_|environment_|context_source_|build_|audit\.)[a-z_.-]+)`', text):
            self.assertIn(code, codes)

    # Literal baseline digests bind exact bytes; changing graph/ref/mode/command,
    # directory, content or direct provenance changes plan and whole-lock hashes.
    def test_digest_binding(self):
        lock = self.baseline['lock']
        self.assertEqual(lock['skill_plan_sha256'], ccj1_sha256(lock['skill_plan']))
        self.assertEqual(self.baseline['runtime_lock_sha256'], ccj1_sha256(lock))
        edits = [(['edges', 0, 'mode'], 'full'),
                 (['edges', 0, 'commands'], ['doctor']),
                 (['edges', 0, 'ref', 'value'], '8' * 40),
                 (['nodes', 0, 'directory'], 'skills/helper'),
                 (['nodes', 0, 'content_sha256'], 'f' * 64),
                 (['direct_constraints'], [{'declaration_sha256': 'sha256:' + '0' * 64}]),
                 (['edges'], [])]
        for path, value in edits:
            with self.subTest(path=path):
                other = deepcopy(lock)
                parent = other['skill_plan']
                for key in path[:-1]:
                    parent = parent[key]
                parent[path[-1]] = value
                self.assertNotEqual(lock['skill_plan_sha256'], ccj1_sha256(other['skill_plan']))
                self.assertNotEqual(self.baseline['runtime_lock_sha256'], ccj1_sha256(other))

    # Even weakening selection computation to activate every command is caught
    # by the concrete runtime-narrow vector, through the real corpus entry.
    def test_narrowing_control(self):
        original = plan.activation

        def widened(data):
            value = original(data)
            value['memory']['commands'] = ['doctor', 'memory']
            return value

        with patch.object(plan, 'activation', widened):
            with self.assertRaisesRegex(ValueError, 'runtime-narrow-transitive'):
                plan.check_corpus()

    # A bridge that touches unrelated packages cannot pass the published effect
    # inventory. This detects an oracle mutant, not an actual installer call.
    def test_global_reconciliation_control(self):
        original = plan.outcome

        def global_bridge(data, validators):
            value = original(data, validators)
            value['unrelated_calls'] = ['global-install']
            value['unrelated'] = 'rebuilt'
            return value

        with patch.object(plan, 'outcome', global_bridge):
            with self.assertRaisesRegex(ValueError, 'runtime-narrow-transitive'):
                plan.check_corpus()

    # Omitting digest verification is detected at the intended tampered-digest
    # vector; neighboring complete, correctly bound locks pass above.
    def test_binding_control(self):
        original = plan.plan_error

        def omit_binding(data, validators):
            code = original(data, validators)
            return None if code == 'profile_skill_plan_binding_invalid' else code

        with patch.object(plan, 'plan_error', omit_binding):
            with self.assertRaisesRegex(ValueError, 'bad-plan-digest'):
                plan.check_corpus()

    # A schema mutant allowing context narrowing is rejected by the actual
    # concrete structural case; this control cannot pass on setup failure.
    def test_schema_narrowing_control(self):
        key = plan.FAMILY + '/profile-skill-plan-v1.schema.json'
        validators = dict(self.validators)
        schema = deepcopy(validators[key].schema)
        del schema['properties']['edges']['items']['allOf']
        plan.Draft202012Validator.check_schema(schema)
        validators[key] = validators[key].evolve(schema=schema)
        # The full lock references the registry's original plan; this plant
        # deliberately exercises the standalone published plan schema instead.
        with patch.object(plan, 'catalog', return_value=validators):
            with self.assertRaisesRegex(ValueError, 'shape-context-narrowing'):
                plan.check_corpus()

    # A case-sensitive reservation mutant reproduces review R3 and fails on
    # the uppercase reserved alias, with ordinary/case-sensitive controls nearby.
    def test_reserved_alias_control(self):
        with patch.object(plan, 'reserved_command',
                          side_effect=lambda command, insensitive: command.startswith('curator-')):
            with self.assertRaisesRegex(ValueError, 'reserved-alias-CURATOR-poison'):
                plan.check_corpus()

    # Ignoring context snapshot identity reproduces review R4: a rehashed lock
    # with substituted source fails its exact expected refusal, not a crash.
    def test_context_identity_control(self):
        with patch.object(plan, 'context_identity_agrees', return_value=True):
            with self.assertRaisesRegex(ValueError, 'context-member-mismatch-source'):
                plan.check_corpus()


if __name__ == '__main__':
    unittest.main()
