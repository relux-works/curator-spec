# Draft source namespace conformance (draft-sources-v2)

This unreleased draft corpus specifies the manifest schema-9
dependency-directory amendment separately from the accepted
[skillfile-sources-v1 corpus](../skillfile-sources-v1/README.md) and the core
`conformance/v1` suite. It is not part of any release claim. The
[`manifest.json`](manifest.json) pins this draft corpus, its schemas, and the
amended [source contract](../../protocol/skillfile-sources.md) input; the
accepted rc.14 manifest stays byte-frozen and takes that document input from
its tag. [Core section 4.4](../../protocol/core.md#44-dependencies) and the
source contract define the required outcomes. `index.json` lists structural
positives and negatives; `manifest-dependency-directories.json` covers
schema-9 subfolder selection, root-default identity, missing package paths,
audit/lock identity and same-repository diamond unification. These
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
# Marker v6 is v5 with schema_version 6 and skill_schema_version through 9.
v6 = schemas['install-marker-v6.schema.json']
assert v6['properties']['schema_version'] == {'const': 6}
assert v6['properties']['skill_schema_version'] == {'type': 'integer', 'minimum': 1, 'maximum': 9}
assert v6['properties']['package'] == {'$ref': '../skillfile-sources-v1/source-types-v1.schema.json#/$defs/package'}
v6_as_v5 = copy.deepcopy(v6)
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
extension. Neither command is a manager installation. Do not claim the
resolution cases passed just because their JSON parsed or a helper reproduced
their expected labels.

## Required implementation checks

A future manager harness MUST drive its real resolve/install/refresh/launch
entrypoints for every resolution case and report passed/total, not merely
inspect this file. Establish filesystem fixtures from each input and assert
the exact error/state, no partial publication, and the observed package
identity including the normalized directory.

In particular test subfolder selection, absent and explicit root equivalence,
missing folders, folders without SKILL.md, symlinked-directory escape,
same-repository diamond unification by full package identity, and
same-name/different-directory conflict. These bounds are deliberate and
remain unverified until consumed.
