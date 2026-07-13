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

## Compatibility identifiers

The following deployed names are reserved across protocol 1.x and MUST NOT be
renamed by a conforming implementation when reading or writing shared project
state:

```text
Skillfile.json
Skillfile.dev.json
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

The legacy `agents/runtime.json` manifest and legacy skill command dependency
form remain readable in protocol 1.x. Writers MUST use `csk-skill.json` and
`dependencies.skills`.
