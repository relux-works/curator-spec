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

Protocol rc.4 introduced manifest schema 6, the closed local `go-v1` driver,
build receipt v1, install marker v2, and claim v2. Their schema bytes, driver
meaning, package-controlled surface, and marker relationships are frozen. An
rc.5 reader continues to accept them and never treats local `go-v1` input as an
external repository.

Protocol rc.5 adds manifest schema 7, `skill-build.json` schema 1,
`Skillfile.dev.json` schema 2, the closed `go-repository-v1` driver, build
receipt v2, install marker v3, and claim v3. A schema-7 local `go-v1` command
still uses receipt v1; an external command uses receipt v2; marker v3 records
local, external, or mixed commands with those explicit receipt versions.
Schemas 1 through 6, receipt v1, markers v1/v2, claim v1/v2, and the rc.4
conformance bytes do not acquire repository fields or new semantics.

Protocol rc.5 also names the execution policy under which both compiled drivers
run. `go-v1` and `go-repository-v1` declare the portable `manager-worker-v1`
policy of `protocol/core.md` section 4.2.1. Neither rc.4 nor rc.5 has been
released or pinned, so this revision lands in place. It is byte neutral for
manifest schemas 1 through 6 and for the `build-receipt-v1`,
`install-marker-v2`, and `conformance-claim-v2` schema files, and it adds no
package-controlled field to any manifest or descriptor.

It is deliberately not byte neutral for `go-v1` cache identity. The generated
`go-v1` receipt example and every `go-v1` logical cache key change, because the
execution-policy identity is inside the canonical build input. A pre-revision
candidate entry therefore misses instead of aliasing a portable entry, and a
future hardened execution profile must use a new execution-policy identity and a
new claim schema version rather than widening the closed `manager-worker-v1`
constant. Marker v3 build records and claim v3 driver assertions state the
policy explicitly; marker v2 binds it transitively through its recorded cache
key and receipt hash.

The per-platform native-control inventory and the capability-evidence record are
versioned separately from the execution policy. `rc5-native-control-inventory-v1`
is the exhaustive authority for which native controls a portable manager applies,
and `capability-evidence-v1` is the closed record that reports them. Extending or
re-scoping the inventory requires a new inventory version and a protocol
revision, but not a new execution-policy identity, because neither the inventory
nor the evidence record enters a build input, an artifact, a cache key, a
receipt, a marker, or a claim. An unavailable inventory control never rejects a
build; only a missing mandatory portable control does.

The toolchain requirement contract adds manifest schema 8 and
`skill-build.json` schema 2 and nothing else on the wire. Schema 8 changes
exactly one thing: every build command carries a REQUIRED `toolchain`
requirement of exactly `id` and `version`. Descriptor schema 2 changes exactly
one thing: a target MAY carry the same object, OPTIONAL. No other schema is
re-versioned — build receipts stay at 1 and 2, install markers at 2 and 3,
conformance claims at 3, `Skillfile.dev.json` at 2, the execution policy at
`manager-worker-v1`, and the fingerprint algorithm at `curator-go-toolchain-v1`.

Manifest schemas 1 through 7 and descriptor schema 1 keep their exact bytes and
their exact package surface. `buildCommandV6` remains exactly `type`, `driver`,
`source_dir`; `repositoryBuildCommandV1` remains exactly `type`, `driver`,
`repository`, `target`; `skillBuildTargetV1` remains exactly `driver`,
`build_root`, `source_dir`. They gain the two-stage preflight without gaining a
field, because a command that declares no requirement takes its driver's
registry baseline — `at_least 1.23.0` for `go` — and the `go` entry's tested
family set `{(1, 23)}`, which together are exactly the rule those schemas
already state in prose. No currently admitted release becomes inadmissible and
no currently rejected release becomes admissible. Schemas 1 through 7 MUST
reject `toolchain`, top-level or on a command, exactly as they reject every
other later field.

The contract is byte neutral for cache identity. The effective requirement, the
`compatibility` set, and the guidance catalog are gates rather than build
inputs: none of them enters a build input, a cache key, a receipt, a marker, or
a claim, so changing a requirement, adding a tested family, or publishing a new
guidance revision never invalidates an artifact. `curator-go-toolchain-v1`,
`curator-build-source-v1`, `build-receipt-v1`, `build-receipt-v2`,
`install-marker-v2`, `install-marker-v3`, the rc.4 byte-frozen digests, and
every published cache key keep their exact bytes and values.

Two behavioral changes are visible. A host missing a required toolchain now
fails before external acquisition rather than after audit, so a previously
network-and-disk-expensive failure becomes cheap and its diagnostic changes from
a compiler or driver error to a typed `build_toolchain_*` code. And `blocked`
joins the local dry-run report vocabulary of `profiles/manager.md` section 2.4,
which previously listed it only for external commands in section 11.7;
`unsupported` continues to mean an unknown driver and is never reused for a
toolchain failure.

The rc.5 suite identity is unchanged by this contract. Manifest schema 8,
descriptor schema 2, and the three manager-owned toolchain documents are minted
in `schemas/v1`, but their generated cases live under `conformance/next`, the
candidate suite root, so `conformance/v1/manifest.json`,
`conformance/v1/schema-cases/index.json`, and `release/1.0.0-rc.5.json` keep the
exact bytes an accepted candidate published. `release/frozen.json` records those
three digests, is authored rather than generated, and is enforced by the
generator, the validator, and the release gate; a regeneration that rewrote the
suite would also rewrite the document pinning it, and comparing the pair against
each other would accept the rewrite. Promoting the candidate root into a
released suite root, and pinning it, belongs to the release that admits the
surface.

Candidate downstream runs consume rc.5 through an explicitly supplied
`CURATOR_CONFORMANCE_ROOT` and verify the manifest digest recorded in
`release/1.0.0-rc.5.json`. `CURATOR_CONFORMANCE_ROOT` names a released suite
root; the candidate root is not offered through it and carries no protocol
version. That candidate identity does not advance a repository's committed
released-suite pin and is not a published release, platform claim, signature, or
attestation.
