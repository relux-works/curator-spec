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

Candidate downstream runs consume rc.5 through an explicitly supplied
`CURATOR_CONFORMANCE_ROOT` and verify the manifest digest recorded in
`release/1.0.0-rc.5.json`. That candidate identity does not advance a
repository's committed released-suite pin and is not a published release,
platform claim, signature, or attestation.

## Hardened execution profile

Candidate `hardened-1.0.0-rc.1` is versioned, validated, and pinned separately
from the protocol candidate. It adds `protocol/hardened-execution.md`,
`profiles/manager-hardened.md`, `schemas/hardened/v1`,
`conformance/hardened/v1`, and `release/hardened-1.0.0-rc.1.json`. It changes no
byte of `conformance/v1`, `schemas/v1`, or `release/1.0.0-rc.5.json`, and it
adds no package-controlled field to any manifest or descriptor.

The hardened profile uses the execution-policy identity `hardened-worker-v1`
that rc.5 reserved. A hardened build input is the portable input with that one
value substituted plus exactly one additional closed member, `hardened`,
carrying the profile identity `hardened-profile-v1` and the domain-separated
`curator-hardened-tcb-v1` digest of the closed `hardened-tcb-v1` record. Nothing
else is added to, removed from, or reordered within the hashed input, and the
portable input schemas stay closed, so a portable reader rejects a hardened
input outright.

Five inputs over one source therefore produce five keys that cannot alias: the
pre-revision input with no execution policy, the portable input, the rc.5
reservation that fills only the policy slot, and hardened inputs under two
different trusted computing bases. rc.5 marks its reservation
`schema_valid: false`; it is a non-aliasing demonstration and not a hardened
build input, so a hardened build does not reproduce its key. One consequence is
deliberate: hardened cache identity diverges per trusted computing base, so a
change to the manager parent, supervisor, or worker bytes, to the observed
operating-system kernel, to the enforcement-backend version or the
configuration the qualification depends on, or to any additional mutable
trusted component causes a rebuild rather than reusing an artifact built under
different trusted code.

Hardened local builds write build receipt schema 3, hardened external builds
schema 4, hardened installations install marker schema 4, and hardened
conformance evidence claim schema 4. Each of those carries the execution policy,
the profile identity, and the complete `hardened-tcb-v1` record, and a hardened
marker's `cache_key` must be reproducible from exactly those identities. Receipt
schemas 1 and 2, marker schemas 1 through 3, and claim schemas 1 through 3 keep
their exact bytes and are not widened. Claim 3 admits only `manager-worker-v1`
and claim 4 only `hardened-worker-v1`. A reader that does not implement the
hardened profile rejects receipt schema 3 and 4 and marker schema 4 as
unsupported identities, as `protocol/core.md` sections 9.3 and 10 already
require; it MUST NOT parse them leniently or convert them.

The capability inventory, the evidence record, the trusted-computing-base record,
and the identity binding model are versioned separately from the execution
policy. `hardened-capability-inventory-v1` is the exhaustive authority for the
capability classes a hardened manager probes,
`hardened-capability-evidence-v1` is the closed record that reports them,
`hardened-tcb-v1` names the complete trusted computing base — manager parent,
supervisor, worker, the observed host with its required
`curator-hardened-host-build-v1` kernel build identity, observed backend version
and configuration, toolchain, and every additional mutable component as a closed
cryptographic record — and `hardened-identity-binding-v1` states where each
identity is bound. A platform admits exactly the one enforcement backend it
declares, exactly the one kernel build identifier grammar it declares, and a
hardened receipt's native target admits exactly the one TCB platform it maps to;
all three relations are enforced by the hardened schemas. `host.build` is
required and closed rather than nullable, so two materially different kernels
reporting one platform and one release cannot share a record, a cache key, a
receipt, a marker, or a claim. The evidence
record is the one that never enters a build input, an artifact, a cache key, a
receipt, a marker, or a claim: it reports a single operation's observation, not
what produced an artifact. Changing the guarantee set, the capability inventory,
or the failure boundary requires both a new profile identity and a new
execution-policy identity; it MUST NOT widen `hardened-worker-v1` in place, and
it MUST NOT widen the closed portable `manager-worker-v1` constant. Because the
profile identity is hashed, a future revision cannot silently reuse artifacts
this one produced.

No platform is qualified by `hardened-1.0.0-rc.1`. Linux, macOS, and Windows are
declared `unqualified` pending native adversarial evidence, so a conforming host
rejects the hardened profile with `hardened_profile_unsupported` and no hardened
conformance claim can be emitted. An implementation that supports only the
portable profile remains fully conforming to `1.0.0-rc.5`.

Hardened candidate downstream runs consume the suite through an explicitly
supplied `CURATOR_HARDENED_CONFORMANCE_ROOT` and verify the manifest digest
recorded in `release/hardened-1.0.0-rc.1.json`. Like the protocol candidate, that
identity advances no committed pin and is not a published release, platform
claim, signature, or attestation.
