"""Shared adopted CIP-0022 URL predicate for additive record grammars.

Extracted unchanged from the stage-A oracle. Callers own refusal codes; the
predicate checks literal scalars without normalization or percent decoding.
"""
import re
import unicodedata


def url_valid(url):
    return (isinstance(url, str) and 9 <= len(url) <= 4096
            and not any(c.isspace() or unicodedata.category(c) in {'Cc', 'Cf'}
                        or c in '${}\\' for c in url)
            and re.fullmatch(r'https://[A-Za-z0-9][A-Za-z0-9.-]*(?::[0-9]{1,5})?(?:/[^\s?#@]*)?', url) is not None)
