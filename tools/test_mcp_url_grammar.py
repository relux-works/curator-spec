"""Adopted literal URL guard claims shared by the two additive oracles."""
import inspect
import types
import unittest

import mcp_url_grammar as grammar


class MCPURLGrammarTests(unittest.TestCase):
    # The literal lexical guard refuses each missing class/metacharacter;
    # ordinary, Unicode and percent-escaped paths retain their scalar sequence.
    def test_literal_url_guards(self):
        for suffix in ('/path', '/é', '/%24', '/%00', '/%7B', '/%5C'):
            self.assertTrue(grammar.url_valid('https://example.invalid' + suffix), suffix)
        for char in ('\0', '\1', '\x7f', '\x80', '\u200b', '\ufeff', '$', '{', '}', '\\', ' ', '\t', '\n'):
            self.assertFalse(grammar.url_valid('https://example.invalid/a' + char + 'b'), repr(char))
        for url in ('http://example.invalid', 'https://user@example.invalid/',
                    'https://example.invalid/?q=x', 'https://example.invalid/#x',
                    'https://é.invalid/', None):
            self.assertFalse(grammar.url_valid(url), repr(url))
        self.assertTrue(grammar.url_valid('https://a/' + 'é' * 4086))
        self.assertFalse(grammar.url_valid('https://a/' + 'é' * 4087))

    # Removing only Cf or only dollar from the real predicate admits that
    # witness while preserving the ordinary sibling and neighboring refusals.
    def test_narrowing_controls(self):
        source = inspect.getsource(grammar.url_valid)
        for old, new, witness, neighbor in (
                ("{'Cc', 'Cf'}", "{'Cc'}", '\u200b', '\0'),
                ("'${}\\\\'", "'{}\\\\'", '$', '{')):
            self.assertEqual(source.count(old), 1)
            mutant = types.ModuleType('url_mutant')
            exec('import re\nimport unicodedata\n' + source.replace(old, new), mutant.__dict__)
            self.assertTrue(mutant.url_valid('https://example.invalid/a' + witness + 'b'))
            self.assertTrue(mutant.url_valid('https://example.invalid/path'))
            self.assertFalse(mutant.url_valid('https://example.invalid/a' + neighbor + 'b'))
