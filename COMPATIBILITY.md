# Compatibility policy

The Curator Protocol versions documents, schemas, and conformance vectors as
one release. Semantic versions apply to this complete set.

## Stability

- A release candidate may tighten or correct behavior before `1.0.0` when the
  change is recorded in `CHANGELOG.md` and represented by a vector.
- A stable patch release clarifies prose or adds vectors that do not reject an
  object accepted by the preceding patch.
- A stable minor release may add OPTIONAL fields and new schema versions. Old
  readers MUST continue to reject unsupported schema versions explicitly.
- A stable major release may change required behavior or remove deprecated
  features.

Every JSON wire object carrying `schema_version` is governed by its own schema
series. Implementations MUST reject an unsupported version and MUST NOT guess
its meaning. Unknown-field behavior is defined per schema; it is never inferred
from the protocol release number.

An incompatible structured-wire change requires a new `schema_version`, a new
schema file, positive and negative vectors for both versions, and a migration
note in `CHANGELOG.md`. A release never redefines old schema bytes in place.
Changes to query evaluation, transaction guarantees, durability, or recovery
may tighten a conformance profile without changing a JSON object. Such a
service advertises the production profile only after it passes that profile's
executable vectors.

## Compatibility identifiers

The following deployed names are reserved across protocol 1.x and MUST NOT be
renamed by a conforming implementation when reading or writing shared project
state:

```text
Skillfile.json
Skillfile.dev.json
agent-skill.json
csk-skill.json
.csk-install.json
.csk-managed.json
.agents/
CSK_PROJECT_ROOT
```

`CSK_PROJECT_ROOT` is written by the portable project environment files. All
other command names, machine-home paths, global environment variables, managed
comment text, cache layouts, and executable distribution mechanisms are
tool-specific and are not wire identifiers.

## Deprecation

A feature is deprecated only when the changelog names its replacement and the
earliest release in which removal is permitted. Stable features receive at
least one minor release of overlap before removal. Security-critical behavior
may be disabled sooner through a published advisory.

The legacy `csk-skill.json` filename, `agents/runtime.json` manifest, and skill
command dependency form remain readable in protocol 1.x. Writers MUST use
`agent-skill.json` and `dependencies.skills`. When both modern filenames exist,
readers accept them only when their decoded JSON values are equal and otherwise
fail with `conflicting_skill_manifests`.

Registry RC.2 preserves every endpoint and response envelope from RC.1. It
defines multiple supplied filters as conjunctive, treats content hash as part
of exact artifact identity, and binds pagination to one snapshot. Clients that
already bounded responses and treated cursors as opaque require no wire
migration. Registry services must complete their state and index migration
before claiming the `registry-service` class.

Independent review evidence uses `reviews/review-report-v2.schema.json` for a
stable 1.0.0 release. Schema v2 adds explicit non-maintainer and non-author
attestations; producers migrate by adding both fields with truthful boolean
values. The original schema v1 remains available for draft evidence, but a v1
report is not accepted by the stable release gate.
