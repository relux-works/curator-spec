"""Shared lexical and exact-end claims, independent of record-specific gates."""
import inspect
import json
import types
import unittest

import ccj1_grammar as grammar
from jsonschema import Draft202012Validator


class CCJ1GrammarTests(unittest.TestCase):
    # Lexical -0 is refused at arbitrary JSON depths; 0 and signed integers
    # remain valid. Replacing the lexical guard admits precisely the witness.
    def test_integer_spelling_and_control(self):
        for token in ('0', '-1', '1'):
            self.assertEqual(grammar.integer(token), int(token))
        for raw in ('-0', '{"nested":[-0]}'):
            with self.assertRaisesRegex(ValueError, 'integer spelling'):
                json.loads(raw, parse_int=grammar.integer)
        mutant = types.ModuleType('integer_mutant')
        source = inspect.getsource(grammar.integer)
        self.assertEqual(source.count("token == '-0'"), 1)
        exec(source.replace("token == '-0'", "token == '-00'"), mutant.__dict__)
        self.assertEqual(json.loads('{"nested":[-0]}', parse_int=mutant.integer), {'nested': [0]})
        self.assertEqual(mutant.integer('-1'), -1)

    # Private catalogs close Python's final-LF loophole without mutating frozen
    # schemas or turning intentional prefix/substring patterns into full matches.
    def test_exact_patterns_and_control(self):
        original = {'allOf': [{'pattern': '^[a-z]+$'}, {'not': {'pattern': '^reserved(?:[.]|$)'}}]}
        guarded = grammar.exact_patterns(original)
        validator = Draft202012Validator(guarded)
        self.assertTrue(validator.is_valid('sample'))
        self.assertFalse(validator.is_valid('sample\n'))
        self.assertFalse(validator.is_valid('reserved'))
        self.assertFalse(validator.is_valid('reserved.extension'))
        self.assertEqual(original['allOf'][0]['pattern'], '^[a-z]+$')
        self.assertEqual(guarded['allOf'][1], original['allOf'][1])
        self.assertEqual(grammar.exact_patterns(guarded), guarded)
        # Removing only the exact-end guard admits the known LF violation.
        planted = {'allOf': [original['allOf'][0], guarded['allOf'][1]]}
        self.assertTrue(Draft202012Validator(planted).is_valid('sample\n'))
