"""Shared lexical CCJ-1 and schema-regex guards for additive grammar oracles.

Callers retain their record-specific refusal codes and bounds. Released schema
files are never rewritten: exact-end guards apply to private oracle catalogs.
"""
from copy import deepcopy


def integer(token):
    """Refuse negative zero before JSON decoding loses its lexical spelling."""
    if token == '-0':
        raise ValueError('CCJ-1 integer spelling')
    return int(token)


def exact_patterns(document):
    """Make anchored whole-string schema patterns consume a true string end.

    Prefix/substring patterns keep their meaning, including reserved-name
    searches. The returned copy leaves released source documents untouched.
    """
    result = deepcopy(document)

    def visit(node):
        if isinstance(node, dict):
            pattern = node.get('pattern')
            if isinstance(pattern, str) and pattern.startswith('^') and pattern.endswith('$'):
                node['pattern'] = pattern + r'(?![\s\S])'
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)
    visit(result)
    return result
