"""Shared lexical CCJ-1, portable-path and schema-regex guards for additive grammar oracles.

Callers retain their record-specific refusal codes and bounds. Released schema
files are never rewritten: exact-end guards apply to private oracle catalogs.
"""
from copy import deepcopy
import unicodedata


def integer(token):
    """Bound CCJ-1 integer spelling before conversion loses lexical information."""
    digits = token[1:] if token.startswith('-') else token
    if len(digits) > 16:
        raise ValueError('CCJ-1 integer length')
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


def portable_path(value):
    """Core section 2 relative paths, preserving the original Unicode scalars.

    Record-specific size/depth limits remain with the caller. Apply filename
    rules to every component rather than just the last character of the path.
    """
    if not isinstance(value, str) or not value:
        return False
    try:
        value.encode('utf-8', errors='strict')
    except UnicodeError:
        return False
    if any(c in '\\:' or unicodedata.category(c) == 'Cc' for c in value):
        return False
    reserved = {'CON', 'PRN', 'AUX', 'NUL'} | {prefix+str(n) for prefix in ('COM', 'LPT') for n in range(1, 10)}
    for component in value.split('/'):
        if (component in {'', '.', '..'} or component.endswith(('.', ' '))
                or component.split('.', 1)[0].upper() in reserved):
            return False
    return True
