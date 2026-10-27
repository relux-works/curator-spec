"""Offline coverage audit against pinned references; never generates release entries.

Only identifier facts are compared. Upstream code, manuals and standards pages
stay in private maintainer inputs and retain their existing license disposition.
"""
from __future__ import annotations

import io
from pathlib import Path
import re
import tarfile

import protected_inventory as p

COUNTS = {'posix': 171, 'coreutils': 109, 'bash': 61, 'zsh': 152}


def reference_names(root: Path, manifest):
    pins = {pin['id']: pin for pin in manifest['source_pins']}
    pages = {}
    for path, digest in manifest['reference_content_pins'].items():
        raw = (root / 'posix' / path).read_bytes()
        if p.sha256(raw) != digest:
            raise p.Refusal('reference_digest:posix')
        pages[path] = raw.decode('utf-8')
    utilities = set(re.findall(r'href="\.\./utilities/([A-Za-z_][A-Za-z0-9_]*)\.html"', pages['idx/utilities.html']))
    special = pages['utilities/V3_chap02.html'].split('<h3><a name="tag_19_15"', 1)[1]
    builtins = set(re.findall(r'<a name="([a-z]+)" id="\1">', special))
    if len(utilities) != 155 or len(builtins) != 15:
        raise p.Refusal('reference_shape:posix')
    result = {'posix': utilities | { {'colon': ':', 'dot': '.'}.get(n, n) for n in builtins} | {'['}}
    for source in ('coreutils', 'bash', 'zsh'):
        raw = (root / (source + '.tar.gz')).read_bytes()
        if len(raw) > 64 * 1024 * 1024 or p.sha256(raw) != pins[source]['inputs_sha256']:
            raise p.Refusal('reference_digest:' + source)
        # Read data members in memory; no extraction, execution or tar path writes.
        files = {}
        with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
            for member in archive:
                path = member.name.partition('/')[2]
                wanted = (source == 'coreutils' and path == 'build-aux/gen-lists-of-programs.sh' or
                          source == 'bash' and path.startswith('builtins/') and path.endswith('.def') or
                          source == 'zsh' and path.startswith('Src/') and path.endswith('.c'))
                if member.isfile() and wanted:
                    if member.size > 4 * 1024 * 1024:
                        raise p.Refusal('reference_bounds')
                    files[path] = archive.extractfile(member).read().decode('utf-8')
        if source == 'coreutils':
            text = files['build-aux/gen-lists-of-programs.sh']
            names = set()
            for variable in ('disabled_by_default_progs', 'build_if_possible_progs',
                             'build_if_appropriate_progs', 'normal_progs'):
                names.update(re.search(r"(?m)^" + variable + r"='([^']*)'", text).group(1).split())
            result[source] = {'install' if n == 'ginstall' else n for n in names if n != 'libstdbuf.so'}
        elif source == 'bash':
            names = set()
            for text in files.values():
                for block in re.split(r'(?m)^\$BUILTIN ', text)[1:]:
                    if re.search(r'(?m)^\$FUNCTION ', block):
                        names.add(block.splitlines()[0])
            result[source] = names
        else:
            result[source] = set().union(*(set(re.findall(r'BUILTIN\("([^"\\]+)"', text)) for text in files.values()))
            if len(set(re.findall(r'BUILTIN\("([^"\\]+)"', files['Src/builtin.c']))) != 74:
                raise p.Refusal('reference_shape:zsh_core')
    if {source: len(names) for source, names in result.items()} != COUNTS:
        raise p.Refusal('reference_counts')
    return result


def assert_coverage(inventory, references):
    # Compare membership/provenance, not just the generator's own seed counts.
    for source, names in references.items():
        actual = {entry['name'] for entry in inventory['entries']
                  if any(pin['source'] == 'seed-' + source for pin in entry['provenance'])}
        if actual != {p.normalize(name) for name in names}:
            raise p.Refusal('baseline_coverage:' + source)
