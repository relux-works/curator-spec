# Profile skill directory conformance vectors

This unreleased family adopts [CIP-0021](../../cips/CIP-0021-profile-skill-directories.md)
and [environments §13.1](../../protocol/environments.md#131-profile-skill-directory-amendment).
It does not change `conformance/v1`, a release manifest or a candidate pin.

## Structural cases

[`schema-cases.json`](schema-cases.json) contains named positive and negative
Draft 2020-12 cases for the unreleased rc.7 manifest-v2/lock-v4 successors.
The 55 round-1 cases are retained: former manifest-v1 and lock-v2 cases are
retargeted to the successors and named `manifest-v2-retargeted-*` and
`lock-v4-retargeted-*`; the original successor cases keep their names.
One added case proves manifest schema 1 still refuses skill `directory`,
for 56 structural cases total. Historical lock-v1 still rejects it too.
Published schemas, frozen negatives and pins remain byte-identical.
`expected_diagnostic` describes the consuming operation's error; JSON Schema
validation itself returns structural errors, not manager diagnostics.

With the repository's `requirements-dev.txt` installed, run this command
from the repository root. It uses the actual local schemas, with no network
resolution or substitute validator. Store logs under `.temp/`.

```bash
python3 - <<'PY'
import json
from pathlib import Path
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

schemas = [json.loads(p.read_text()) for p in Path('schemas').rglob('*.schema.json')]
registry = Registry().with_resources((s['$id'], Resource.from_contents(s)) for s in schemas)
cases = json.loads(Path('conformance/profile-skill-directories-v1/schema-cases.json').read_text())
for case in cases:
    schema = json.loads(Path(case['schema']).read_text())
    Draft202012Validator.check_schema(schema)
    actual = Draft202012Validator(schema, registry=registry).is_valid(case['instance'])
    assert actual == case['valid'], case['name']
    print('PASS', case['name'])
print(len(cases), 'schema cases passed')
PY
```

These data cases are separate from `make validate`'s frozen schema-case
index. Run both the command above and the repository's `make validate` and
`make regenerate-check`; a structural pass does not override a release
history failure. No published schema bytes or frozen cases are amended.

## Lifecycle vectors

[`fixtures.json`](fixtures.json) supplies exact UTF-8 file bytes, a profile
schema-2 manifest, symbolic source commits and a schema-4 candidate lock.
The lock retains required `precedence`, `codex_settings: {}` and
`codex_settings_contributions: []`. All 24 lifecycle vectors use these
successors; the corpus envelope's `schema_version: 1` versions the vector
format, not a context manifest. Requirer context manifests also use schema 2.
[`vectors.json`](vectors.json) declares real manager lifecycle entry points
and their observations. Each case starts from the base fixture, independently.
Apply `changes` as follows:

- `requirement.*` edits the `formatter` requirement; `requirement.remove`
  deletes the listed fields. A whole `requirement` replaces it.
- `snapshot.files.<path>` replaces those exact file bytes; `snapshot.remove`
  deletes files; `snapshot.symlinks` supplies link entries instead of regular
  entries at those paths. Ancestor directories are implicit. For an inside
  symlink witness, construct its target as a real directory containing the
  otherwise valid selected package, so rejection cannot rely on absence.
- `snapshot` selects the named alternate snapshot in `fixtures.json`.
- `requirers` constructs two pure context consumers with the stated skill
  requirements and a root requiring both. Commit/source disagreements are
  deliberate; the agreement control must produce exactly one skill member.
- `legacy_install_record` supplies a legacy global record before first-use
  profile migration. The selected directory remains absent.

Materialize repository fixtures as immutable git commits; `commit_symbol`
is a placeholder, not a claim that these bytes hash to that OID. Bind it
and the profile root commit to the real fixture OIDs in requirements and
lock members before invoking the manager. The root source is the candidate
lock's context source, holding `profile_manifest` as `agent-context.json`.
For update/sync, preinstall the base profile; sync consumes its existing
lock. Compute expected lock pins from the substituted/edited lock, and
include extra consumer members and their requirer edges for diamond cases.
The literal pin in the base lifecycle expectations corresponds only to the
unsubstituted lock fixture. No external network call or system command
execution is needed to inspect, audit or link this package.

Capture the actual lock member and CCJ-1 lock pin, selected-root content
hash (core §8 framing 2), audit capability provenance and findings, and both
managed-home and in-place skill links. Compare every stated observation;
the expected `skill_link_targets` are paths relative to the acquired skill
snapshot, not native-home paths. Content paths and findings are relative
to the selected package. In identity-comparison cases, compare against the
base selected tree, never the repository-root tree.

[`lock-identity.json`](lock-identity.json) independently pins canonical lock
bytes and SHA-256 for a directory-only change. Its alternate lock is an
identity fixture, not an assertion that an alternate package exists.
Rejecting lifecycle cases preserve the pre-operation lock and surfaces;
`published_writes: []` allows disposable acquisition/audit scratch work but
no profile/store/surface publication.

The missing-runtime-manifest case requests `format`, absent without the
selected manifest, while the nearby manifestless context-skill control
must succeed. Pure context skills are not required to invent a manifest.
The repository-root manifest is valid and grants the selected host, so
the selected-root undeclared-contact negative catches borrowed authority.
The sibling contact must not become a selected-skill finding.

## Coverage and limits

The 24 lifecycle cases cover install/update/sync root selection, lock
identity, audit scope, manifestless context, unchanged root addressing,
path grammar, inside/outside symlinks, missing directory/content, invalid
manifest, source/directory disagreement, agreement, path-kind refusal and
unchanged legacy migration. All negative cases name expected diagnostics.

The structural cases execute schema admission only. Lifecycle, filesystem,
audit and materialization observations require the separate manager leaf;
this specification change does not claim those entry points ran or killed
runtime mutants. Narrowing controls for implementations should include
root-only selection, prefix-only parent-path checking, outside-only symlink
checking, directory-insensitive lock/audit identity, borrowed capability
authority and one-form-only materialization.
