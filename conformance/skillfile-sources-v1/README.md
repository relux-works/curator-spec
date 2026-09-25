# Skillfile source and repository transport conformance

This dedicated corpus specifies the accepted source and transport revisions
separately from the frozen `conformance/v1` suite. [The source contract](../../protocol/skillfile-sources.md)
and [transport protocol](../../protocol/repository-transport.md) define its
required outcomes. `index.json` lists structural positives and negatives;
`snapshot-cases.json` contains concrete byte inventories and expected hashes;
`semantic-cases.json` records required downstream resolver/filesystem/security
outcomes (`v2-*` cases cover transport revision 2: port, mirror and alias
positives plus undeclared-mirror, unknown-alias and policy-misuse refusals). It
also records moved-tag lock replay and machine-global/project-scope schema-2
requirements from the source protocol. These hand-authored vectors remain in
this namespace rather than the generated `conformance/v1` corpus.

## Specification checks

From the repository root, with `requirements-dev.txt` installed, run this exact
standalone command. It compiles all extension and referenced schemas, checks every
indexed positive/negative, recomputes inventory hashes, and verifies that runtime
and build edits preserve SKILL.md bytes but change full package identity. It
prints measured counts and exits nonzero on failure.

```bash
python3 - <<'PY'
import copy, hashlib, json
from pathlib import Path
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
root = Path.cwd()
suite = root / 'conformance/skillfile-sources-v1'
schemas = {}
resources = []
for directory in ['schemas/v1', 'schemas/skillfile-sources-v1']:
    for path in (root / directory).glob('*.json'):
        document = json.loads(path.read_text())
        Draft202012Validator.check_schema(document)
        resources.append((document['$id'], Resource.from_contents(document)))
        if directory.endswith('skillfile-sources-v1'):
            schemas[path.name] = document
registry = Registry().with_resources(resources)
cases = json.loads((suite / 'index.json').read_text())
coverage = {}
for case in cases:
    validator = Draft202012Validator(schemas[case['schema']], registry=registry)
    actual = validator.is_valid(json.loads((suite / case['instance']).read_text()))
    assert actual == case['valid'], case
    coverage.setdefault(case['schema'], set()).add(case['valid'])
assert set(coverage) == set(schemas) - {'source-types-v1.schema.json'}
assert all(values == {True, False} for values in coverage.values())
# Exhaustive v4 migration audit, independently anchored to the frozen v4 schema.
v4 = json.loads((root / 'schemas/v1/install-marker-v4.schema.json').read_text())
v5 = schemas['install-marker-v5.schema.json']
replaced = {'source', 'git', 'ref_kind', 'ref', 'commit'}
assert set(v5['properties']) == (set(v4['properties']) - replaced) | {'package', 'lock_sha256'}
assert set(v5['required']) == (set(v4['required']) - replaced) | {'package', 'lock_sha256'}
common = json.loads((root / 'schemas/v1/common.schema.json').read_text())
for old_name, arm in zip(['buildRecordV1WithReceiptVersion', 'buildRecordV2'],
                         v5['properties']['builds']['additionalProperties']['oneOf']):
    expected = copy.deepcopy(common['$defs'][old_name])
    expected['properties']['receipt_schema_version'] = {'const': 3}
    expected = json.loads(json.dumps(expected).replace('"#/$defs/', '"../v1/common.schema.json#/$defs/'))
    assert arm == expected, old_name
# Narrow the actual schema refusal to local markers with BOTH forbidden fields.
# Each single-field negative must expose this weakening at the same validator entry.
mutant = copy.deepcopy(v5)
mutant['allOf'][0]['then']['not'] = {'required': ['attestation', 'substituted']}
for field in ['attestation', 'substituted']:
    obj = json.loads((suite / f'schema-cases/install-marker-v5/invalid-local-{field}.json').read_text())
    assert not Draft202012Validator(v5, registry=registry).is_valid(obj)
    assert Draft202012Validator(mutant, registry=registry).is_valid(obj)
# Narrow external required-evidence refusal by dropping each required field alone.
external_required = common['$defs']['buildRecordV2']['required']
for field in external_required:
    obj = json.loads((suite / f'schema-cases/install-marker-v5/invalid-external-missing-{field}.json').read_text())
    mutant = copy.deepcopy(v5)
    mutant['properties']['builds']['additionalProperties']['oneOf'][1]['required'].remove(field)
    assert not Draft202012Validator(v5, registry=registry).is_valid(obj)
    assert Draft202012Validator(mutant, registry=registry).is_valid(obj), field
print(f'Marker migration: {len(v4["properties"])}/{len(v4["properties"])} top-level fields; 2/2 build arms; narrowed refusal mutants: {2 + len(external_required)}/{2 + len(external_required)} detected')
def digest(value):
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    return 'sha256:' + hashlib.sha256(data).hexdigest()
vectors = json.loads((suite / 'snapshot-cases.json').read_text())
for vector in vectors:
    inventory = vector['inventory']
    entries = inventory['files']
    assert [f['path'] for f in entries] == sorted(vector['utf8_files'])
    for entry in entries:
        raw = vector['utf8_files'][entry['path']].encode()
        assert entry['sha256'] == 'sha256:' + hashlib.sha256(raw).hexdigest()
    assert inventory['snapshot'] == digest({k:v for k,v in inventory.items() if k != 'snapshot'})
assert len({v['inventory']['snapshot'] for v in vectors}) == len(vectors)
assert len({v['utf8_files']['SKILL.md'] for v in vectors}) == 1
negatives = sum(not c['valid'] for c in cases)
print(f'Schema cases: {len(cases)}/{len(cases)}; negatives: {negatives}/{negatives}; wire schemas: {len(coverage)}/{len(coverage)}')
print(f'Snapshot byte vectors: {len(vectors)}/{len(vectors)}')
print('Manager semantic execution: 0 cases; unverified by this specification command')
PY
```

Also run `make validate` for the pre-existing platform-neutral corpus. Neither
command is a manager installation. Do not claim the semantic cases passed just
because their JSON parsed or a helper reproduced their expected labels.

## Required implementation checks

A future manager harness MUST drive its real resolve/install/refresh/launch
entrypoints for every semantic case and report passed/total, not merely inspect
this file. Establish filesystem fixtures from each input and assert the exact
error/state, no partial publication, and the observed endpoint attempt count.

In particular test physical symlink/casing equivalence and write-boundary
retargeting; freeze membership across launches; mutate live input during capture
and the frozen copy between audit and publication; edit runtime/build alone
then refresh; and observe that TLS/host-key/integrity/ref/audit errors make zero
alternate attempts. Pair authorization positives with absent/unreadable evidence
negatives. The narrow forbidden fallback classes must each be exercised, not
just a mutant that removes the whole gate. Implementations must supplement the
corpus with their native race and process controls; no such evidence is bundled
here. These bounds are deliberate and remain unverified until consumed.

Marker coverage includes attested network and legacy skill substitution positives,
local packages with mixed builds and external committed-source substitution,
malformed attestation/substitution negatives, and every required external record
field missing in turn. The command audits all frozen v4 fields and both build
arms, then narrows applicability and required-evidence refusals at the actual
`Draft202012Validator(...).is_valid(...)` specification entrypoint. These are
schema gate proofs, not tests of a manager's authorization path.

The added semantic cases require real manager section 2.1 planning and core
section 10 status/repair entrypoints to reject missing, unreadable, stale,
revoked and mismatching evidence. Strict substitution refusal must be attacked
with the marker field omitted, including external substitution of a local
package. Status must not mutate or fetch; repair must not adopt candidate bytes;
failed refresh must preserve prior state. No semantic execution is claimed here.

Marker schema fixtures use synthetic digest values and are structural examples,
not linked receipt/artifact bundles or current-installation attestations. A
manager conformance harness must construct actual matching receipt-3 hashes and
protected artifacts for the positive currentness cases before applying the
negative mutations.
