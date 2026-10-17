# Draft source namespace conformance (draft-sources-v2)

This unreleased draft corpus specifies the manifest schema-9
dependency-directory amendment and the canonical ownership/no-manifest
source-marker amendment separately from the accepted
[skillfile-sources-v1 corpus](../skillfile-sources-v1/README.md) and the core
`conformance/v1` suite. It is not part of any release claim. The
[`manifest.json`](manifest.json) pins this draft corpus, its schemas, and the
amended [source contract](../../protocol/skillfile-sources.md) input; the
accepted rc.14 manifest stays byte-frozen and takes that document input from
its tag. [Core section 4.4](../../protocol/core.md#44-dependencies) and the
source contract define the required outcomes. `index.json` lists structural
positives and negatives; `manifest-dependency-directories.json` covers
schema-9 subfolder selection, root-default identity, missing package paths,
audit/lock identity and same-repository diamond unification.
`marker-ownership-cases.json` specifies canonical-store ownership refusals and
re-derivation, separately from marker schema validity. `marker-writer-cases.json`
specifies v5/v6 writer selection, package declaration restrictions and
invalid/unreadable-manifest refusal without fallback. These
hand-authored vectors remain in this namespace rather than the accepted
`skillfile-sources-v1` or generated `conformance/v1` corpora.

## Specification checks

From the repository root, with `requirements-dev.txt` installed, run this exact
standalone command. It compiles all draft and referenced schemas, checks every
indexed positive/negative (the accepted marker-v5 rejection pin resolves
against the frozen accepted schema), and audits the v6 carrier shape and the
shared directory-grammar reuse. It prints measured counts and exits nonzero
on failure.

```bash
python3 - <<'PY'
import copy, json
from pathlib import Path
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
root = Path.cwd()
suite = root / 'conformance/draft-sources-v2'
schemas = {}
accepted = {}
resources = []
for directory in ['schemas/v1', 'schemas/skillfile-sources-v1', 'schemas/draft-sources-v2']:
    for path in (root / directory).glob('*.json'):
        document = json.loads(path.read_text())
        Draft202012Validator.check_schema(document)
        resources.append((document['$id'], Resource.from_contents(document)))
        if directory.endswith('draft-sources-v2'):
            schemas[path.name] = document
        elif directory.endswith('skillfile-sources-v1'):
            accepted[path.name] = document
registry = Registry().with_resources(resources)
cases = json.loads((suite / 'index.json').read_text())
coverage = {}
for case in cases:
    document = schemas.get(case['schema'], accepted.get(case['schema']))
    assert document is not None, case
    validator = Draft202012Validator(document, registry=registry)
    actual = validator.is_valid(json.loads((suite / case['instance']).read_text()))
    assert actual == case['valid'], case
    coverage.setdefault(case['schema'], set()).add(case['valid'])
assert set(coverage) - {'install-marker-v5.schema.json'} == set(schemas)
assert all(values == {True, False} for name, values in coverage.items() if name in schemas)
assert coverage.get('install-marker-v5.schema.json') == {False}
# Accepted marker v5 admits manifest versions through 8 only, so the draft
# needs its own v6 carrier for schema-9 installs.
v5 = accepted['install-marker-v5.schema.json']
assert v5['properties']['skill_schema_version'] == {'type': 'integer', 'minimum': 1, 'maximum': 8}
# Marker v6 is v5 plus version 6, manifest versions through 9 and the
# constrained null no-manifest form. No accepted v5 bytes change.
v6 = schemas['install-marker-v6.schema.json']
assert v6['properties']['schema_version'] == {'const': 6}
assert v6['properties']['skill_schema_version'] == {'type': ['integer', 'null'], 'minimum': 1, 'maximum': 9}
assert v6['properties']['package'] == {'$ref': '../skillfile-sources-v1/source-types-v1.schema.json#/$defs/package'}
manifestless = {
    'if': {'properties': {'skill_schema_version': {'type': 'null'}},
           'required': ['skill_schema_version']},
    'then': {
        'properties': {
            **{k: {'maxItems': 0} for k in ['commands', 'dependencies', 'runtime_roots', 'build_roots']},
            'builds': {'maxProperties': 0},
            'activation': {'properties': {'commands': {'maxItems': 0}}},
        },
        'not': {'anyOf': [{'required': [k]} for k in ['build_source', 'requirements', 'mcp_servers']]},
    },
}
assert v6['allOf'] == v5['allOf'] + [manifestless]
v6_as_v5 = copy.deepcopy(v6)
v6_as_v5['allOf'].pop()
v6_as_v5['properties']['schema_version'] = {'const': 5}
v6_as_v5['properties']['skill_schema_version'] = {'type': 'integer', 'minimum': 1, 'maximum': 8}
v6_as_v5['properties']['package'] = {'$ref': 'source-types-v1.schema.json#/$defs/package'}
assert {k: v for k, v in v6_as_v5.items() if k != '$id'} == {k: v for k, v in v5.items() if k != '$id'}
# Schema 9 reuses the accepted Skillfile directory grammar by reference.
ref = '../skillfile-sources-v1/source-types-v1.schema.json#/$defs/directory'
for name in ['agent-skill-v9.schema.json', 'csk-skill-v9.schema.json']:
    requirement = schemas[name]['$defs']['skillRequirementV9']['properties']['directory']
    assert requirement == {'$ref': ref}, name
negatives = sum(not c['valid'] for c in cases)
print(f'Schema cases: {len(cases)}/{len(cases)}; negatives: {negatives}/{negatives}; draft schemas: {len(schemas)}/{len(schemas)}')
print('Manager semantic execution: 0 cases; unverified by this specification command')
PY
```

Also run `make validate` for the platform-neutral corpus and the accepted
extension. Its `tools/validate.py` entry point calls
`validate_source_marker_ownership_vectors`: all 21 ownership rows are checked
against section 4.1 independently of their file hashes. Required scenarios
are anchored to frozen accepted positive marker seeds; outcomes are recomputed
from no-follow/read/identity evidence, the serialized recheck, and the separate
schema validity test. A refusal must name every unowned path, assert zero
destructive publications, and preserve every prior state component. Positive
controls cover new destinations, owned stale cleanup and v5/v6 invalid-evidence
re-derivation. Substituting a positive scenario for a required negative fails.
These are executable specification-data checks, not observed manager effects.
Neither command is a manager installation. Do not claim the
resolution cases passed just because their JSON parsed or a helper reproduced
their expected labels.

## Required implementation checks

A future manager harness MUST drive its real resolve/install/refresh/launch
entrypoints for every resolution case and report passed/total, not merely
inspect this file. For each ownership case, drive install (or the named
status/repair operation), inspect every reported path, and assert preservation
of the prior lock, canonical entries, adapters, runtime and shims on refusal.
Neither these checks nor schema validation execute a manager. Establish filesystem fixtures from each input and assert
the exact error/state, no partial publication, and the observed package
identity including the normalized directory.

In particular test subfolder selection, absent and explicit root equivalence,
missing folders, folders without SKILL.md, symlinked-directory escape,
same-repository diamond unification by full package identity, and
same-name/different-directory conflict. These bounds are deliberate and
remain unverified until consumed.

Marker-v6 schema and ownership-vector controls run with:

```bash
python3 -B -m unittest discover -s tools -p 'test_source_marker.py' -v
```

Each forbidden no-manifest field has a single-field negative and an
integer-manifest positive. The same required version member holds either an
integer or null, never both; arrays and parallel version/absence flags refuse.
The owned-invalid-evidence semantic row retains the accepted
`external-evidence-mismatch-execution_policy` outcome. Unknown v6 readers
refuse before destructive changes. The named ownership tests include
`test_ownership_unowned_sibling_preserves_and_names_all_paths`,
`test_ownership_unowned_selected_destination_refuses_without_partial_change`,
and `test_ownership_invalid_evidence_rederived_not_refused`. Their controls
plant sibling-only acceptance, selected-destination partial publication and
invalid-evidence ownership refusal; each must be rejected by the public
validator for its ownership outcome, rather than a hash or setup failure.
Ownership runtime execution remains
unverified here; this repository publishes the contract and fixtures only.
