"""Shared lexical and exact-end claims, independent of record-specific gates."""
import inspect
import json
import types
import unittest
from unittest.mock import patch

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


    # Every unsafe long integer token is rejected before int conversion; 16-digit
    # safe extrema still reach conversion. The plant removes only the length gate.
    def test_integer_length_before_conversion_and_control(self):
        for token in ('0', '-1', '9007199254740991', '-9007199254740991'):
            self.assertEqual(grammar.integer(token), int(token))
        source = inspect.getsource(grammar.integer)
        self.assertEqual(source.count('len(digits) > 16'), 1)
        namespace = dict(vars(grammar))
        exec(source.replace('len(digits) > 16', 'False'), namespace)
        for token in ('9'*17, '-'+'9'*17, '9'*5000, '-'+'9'*5000):
            with self.subTest(length=len(token)), patch.object(grammar, 'int', create=True) as conversion:
                with self.assertRaisesRegex(ValueError, '^CCJ-1 integer length$'):
                    grammar.integer(token)
                conversion.assert_not_called()
            # Instrument the exact removed gate without disabling Python's digit guard.
            with patch.dict(namespace, {'int':lambda value: ('converted', value)}):
                self.assertEqual(namespace['integer'](token), ('converted', token))

    # Each path component obeys core section 2, including intermediate names;
    # valid dotfiles, Unicode spelling and ordinary spaces are preserved.
    def test_portable_components_and_control(self):
        siblings = ('pkg/root', '.codex/config.toml', 'pkg name/root', 'é/root', 'e\u0301/root', 'COM10/root', 'console.txt')
        for path in siblings:
            self.assertTrue(grammar.portable_path(path), path)
        for path in ('', '/', '/pkg', 'pkg/', 'pkg//root', '.', '..', 'pkg/../root',
                     'pkg./root', 'pkg /root', 'pkg/root.', 'pkg/root ',
                     'pkg/a:b', 'pkg\\root', 'pkg/\x00root', 'pkg/\x85root', 'pkg/\ud800',
                     'CON/root', 'pkg/nul.txt', 'pkg/CoM9.txt', 'LPT1/root'):
            self.assertFalse(grammar.portable_path(path), repr(path))
        source = inspect.getsource(grammar.portable_path)
        anchor = "component.endswith(('.', ' '))"
        self.assertEqual(source.count(anchor), 1)
        namespace = dict(vars(grammar))
        exec(source.replace(anchor, 'False'), namespace)
        for path in ('pkg./root', 'pkg /root'):
            self.assertTrue(namespace['portable_path'](path))
        self.assertFalse(namespace['portable_path']('pkg/../root'))
