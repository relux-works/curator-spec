# Decision 0008: additional-language driver, version, and artifact boundary

## Context

Protocol `1.0.0-rc.5` admits exactly two compiled drivers, `go-v1` for source
inside the consuming skill snapshot and `go-repository-v1` for source in a
locked external Git repository. Decision 0004 section "Future-driver rule",
decision 0005 section "Credential, signing, and future-driver ownership", and
`protocol/core.md` section 12.3 all require a new closed identifier and an
independent review for every additional language, and forbid admitting one by
widening an existing driver or adding a generic fallback.

Rust, Swift, and Kotlin driver pairs are now being designed in parallel with a
shared toolchain-requirement contract. Each of those designs would otherwise
have to pick, on its own, a manifest schema version, a receipt numbering rule,
an artifact shape, a descriptor evolution, a process-graph story, and a platform
claim. Whichever landed first would silently fix those choices for the others,
and the resulting wire surface would be an accident rather than a decision.

The three candidate languages also differ from Go in one decisive way. `go
build` executes no package-selected code. `cargo build` runs `build.rs` and
expands procedural macros; SwiftPM compiles and executes `Package.swift` as a
program and can run plugins and macros; the mainstream Kotlin build path is
Gradle, which is a general-purpose script engine. `SECURITY.md` already names
all three of those surfaces as things a conforming manager MUST NOT invoke. The
question is therefore not how to accommodate them but whether each driver can be
defined without them at all.

Kotlin raises one further question the other languages do not. Its dominant
output is a JVM archive that cannot run without a separately installed runtime,
which does not fit the single-artifact identity that receipts, markers, shims,
currentness, and garbage collection are built on.

This decision fixes the version, source-ownership, artifact, and execution
boundary that the three driver contracts, the toolchain contract, the wire
integration, and the candidate qualification must all satisfy. It defines no
compiler pipeline, adds no schema file, regenerates no vector, creates no
release metadata, advances no pin, and makes no platform claim.

## Decision

### 1. Version boundary

The additional drivers are a new protocol surface named `1.0.0-rc.6`. It is
reserved by this decision and minted only by the wire integration task; rc.5
remains the current candidate and its conformance-manifest digest and pins are
unchanged by this decision.

| Surface | Current | Next | Status |
|---|---|---|---|
| manifest `agent-skill-vN` / `csk-skill-vN` | 7 | 8 | reserved |
| repository descriptor `skill-build.json` | 1 | 2 | reserved |
| build receipt, local source mode | 1 | 3 | reserved |
| build receipt, external source mode | 2 | 4 | reserved |
| install marker | 3 | 4 | reserved |
| conformance claim | 3 | 4 | reserved |
| execution policy, Go drivers | `manager-worker-v1` | `manager-worker-v1` | frozen, Go only |
| execution policy, additional drivers | none | `manager-worker-v2` | reserved |
| capability-evidence record | `capability-evidence-v1` | `capability-evidence-v2` | reserved |
| `Skillfile.dev.json` | 2 | 2 | unchanged |
| native-control inventory | `rc5-native-control-inventory-v1` | unchanged | unchanged |
| build-source identity | `curator-build-source-v1` | unchanged | unchanged |
| Go toolchain identity | `curator-go-toolchain-v1` | unchanged | frozen, Go only |
| toolchain requirement object | `toolchain-requirement-v1` | unchanged | owned by decision 0007 |

Manifest schemas 1 through 7, `skill-build.json` schema 1, build receipt
schemas 1 and 2, install marker schemas 1 through 3, conformance claim schemas 1
through 3, `Skillfile.dev.json` schema 2, and every rc.4 and rc.5 conformance
byte are frozen, as are `manager-worker-v1`, `capability-evidence-v1`,
`rc5-native-control-inventory-v1`, and `curator-go-toolchain-v1`. Schemas 1
through 7 MUST reject every one of the six driver identifiers below, the reserved
`manager-worker-v2` policy identity, and every schema-8-only field. A reader or
writer MUST NOT reinterpret, widen, relabel, or infer an rc.6 meaning from an
rc.4 or rc.5 object.

Build receipt schema versions are allocated per source mode per admitting
protocol version. rc.5 allocated 1 to the local Go driver and 2 to the external
Go driver. This boundary allocates 3 to the local source mode and 4 to the
external source mode for the drivers admitted at manifest schema 8. In a
schema-8 manifest `go-v1` still writes receipt schema 1 and `go-repository-v1`
still writes receipt schema 2; neither is re-versioned, re-hashed, or migrated.

`Skillfile.dev.json` schema 2 is deliberately not re-versioned. An operator
development substitution selects source acquisition only. It cannot select a
driver, a toolchain, an artifact class, or a target, so admitting more drivers
changes nothing it can express.

The three package-controlled build shapes are also allocated by name here, so
that the shapes fixed in sections 4 and 5 have exactly one place to land and a
gate can check them the moment they exist. `common.schema.json` reserves
`buildCommandV8` for the schema-8 local build command, `repositoryBuildCommandV2`
for the schema-8 external build command, and `skillBuildTargetV2` for the
descriptor schema-2 target. It also reserves one definition for the requirement
object decision 0007 owns, `toolchainRequirementV1`, because all three shapes
carry the same object and a definition per slot would let three independently
authored driver contracts drift apart. The deployed `buildCommandV6`,
`repositoryBuildCommandV1`, and `skillBuildTargetV1` definitions keep their exact
bytes and their exact three- and four-member shapes; a new member MUST NOT be
added to any of them, and the schema-8 shapes MUST NOT be expressed by widening
them.

### 2. Two disjoint closed sets: admitted wire, reserved namespace

The driver identifier space is closed by enumeration, never by grammar,
detection, or a family prefix. It is partitioned into exactly two disjoint sets
with different normative force, and every implementer, schema, validator, and
claim reader MUST keep them apart.

**Admitted wire driver set.** Exactly two values, and this is the only set any
schema, validator, manager, or claim reader may accept today:

| Driver | Language family | Source mode | Receipt schema | Execution policy | Admitted |
|---|---|---|---|---|---|
| `go-v1` | Go | local snapshot | 1 | `manager-worker-v1` | rc.4 |
| `go-repository-v1` | Go | external repository | 2 | `manager-worker-v1` | rc.5 |

**Reserved driver namespace.** Exactly six values, closed by this decision and
admitted by none of manifest schemas 1 through 7, `skill-build.json` schema 1,
receipt schemas 1 and 2, marker schemas 1 through 3, or claim schemas 1 through
3. They are names held against future admission, not wire values:

| Driver | Language family | Source mode | Receipt schema | Execution policy | Status |
|---|---|---|---|---|---|
| `rust-v1` | Rust | local snapshot | 3 | `manager-worker-v2` | reserved |
| `rust-repository-v1` | Rust | external repository | 4 | `manager-worker-v2` | reserved |
| `swift-v1` | Swift | local snapshot | 3 | `manager-worker-v2` | reserved |
| `swift-repository-v1` | Swift | external repository | 4 | `manager-worker-v2` | reserved |
| `kotlin-native-v1` | Kotlin | local snapshot | 3 | `manager-worker-v2` | reserved |
| `kotlin-native-repository-v1` | Kotlin | external repository | 4 | `manager-worker-v2` | reserved |

The union of the two sets is the complete Protocol 1.0 build-driver identifier
space. No other identifier may be coined at Protocol 1.0, in either set, by any
task, schema, profile, or implementation.

The identifier form is `<family>-v<n>` for the local source mode and
`<family>-repository-v<n>` for the external source mode, matching the deployed
Go pair. The Kotlin family segment carries the `native` backend qualifier
because Kotlin has two candidate backends and only the native one can satisfy
section 3; a later JVM-oriented driver, if it is ever reviewed and accepted,
MUST use a different family segment and MUST NOT reuse these two identifiers.

Reservation is not admission, and the two sets never overlap. A reserved
identifier leaves the reserved namespace and enters the admitted wire driver set
in exactly one way: its own driver contract is accepted, and
`TASK-260728-251p01` moves it in the same change that mints the schema version
admitting it. There is no partial state — until that move, every schema
including manifest schema 8 as first minted MUST reject it, and a manager MUST
treat it as an unknown driver. A reserved identifier whose contract is rejected
is retired unused: it MUST NOT be reassigned to a different language, backend,
artifact class, or source mode, and it MUST NOT be enabled by relaxing another
driver.

The receipt-schema and execution-policy columns of the reserved table are the
allocation each identifier will carry when it is admitted. They are binding on
the integration task and they are not wire facts today.

Every schema that expresses a driver MUST express it as a `const` inside a
`oneOf` over the admitted identifiers. A driver field MUST NOT be an open
`enum`, a pattern, a bare string, or a value derived from a file extension,
project-metadata filename, directory layout, or any other language detection. No
manifest, descriptor, repository, substitution, or receipt may contain a
`language`, `toolchain_family`, `build_system`, `backend`, or comparable
selector.

### 3. Artifact class: `native-executable-v1` only

This version admits exactly one artifact class, `native-executable-v1`:

- exactly one bounded regular file, produced into operation-private manager
  staging, hashed there, and published immutably under the manager-home
  mutation lock;
- named solely by the manager from the consuming manifest command key, as
  `bin/<command>` on Unix and `bin/<command>.exe` on Windows, exactly as
  `protocol/core.md` sections 4.2 and 4.2.2 already require;
- directly executable by the host program loader using only libraries the target
  platform provides in its base installation, as fixed by the driver's own
  platform matrix; and
- never executed by the manager during validation, installation, status, repair,
  rollback, or garbage collection.

On the wire, `native-executable-v1` is carried by the shared `buildArtifactV1`
definition, and that definition MUST be an object schema — `"type": "object"`
exactly, never omitted, never unioned with a scalar, and never expressed as a
boolean schema — requiring exactly `path`, `sha256`, and `size`, closed with
`additionalProperties: false`, with each of the three bound to the canonical
shared `portablePath`, `sha256`, and `nonNegativeSafeInteger` definitions. Each
of those clauses is load-bearing rather than stylistic, for the same reason the
toolchain requirement object needs its type: `properties`, `required`, and
`additionalProperties` constrain objects only. A definition that keeps the three
member names while declaring itself a string, an `object`/`string` union, or no
type at all admits a bare launcher name where a published file belongs, and a
definition that empties `required` admits an artifact asserting nothing — in both
cases every existing positive case still validates, so the widening is invisible
to a member-name comparison. Both readmit the rejected `runtime-bundle` class
through the definition that is supposed to exclude it, which is why the gate in
section 11 holds this definition to an exact object schema and additionally
proves against the compiled receipt validators that a scalar, an array, an empty
object, a missing member, an extra runtime member, a non-portable path, an
unprefixed digest, and a negative size are all rejected.

Binding the three members to shared definitions is a closure only while those
definitions still mean what this section fixes, so `portablePath`, `sha256`, and
`nonNegativeSafeInteger` MUST each remain exactly the schema the frozen rc.5
corpus ships. The path grammar states where a published file may live, the digest
alphabet is the whole description of what it contains, and the size ceiling is
the range in which the manager's recorded size is meaningful; none of the three
is an illustrative example. A single keyword is enough to move any of them —
`maxLength` raised by one, uppercase added to the digest alphabet, the
safe-integer ceiling lifted or dropped — and such a change leaves the pinned
`$ref` intact, leaves every published positive case valid, and leaves every
individual bad value a gate might sample still rejected, while the compiled
receipt validator begins accepting an artifact this section does not admit.
Enforcement therefore MUST be structural on those three definitions, and a proof
by sampled rejections MUST NOT be presented as covering them.

No driver may publish a second file. Debug information, separate symbol files,
program databases, import libraries, module or interface files, resource
bundles, shared libraries, sysroot copies, and incremental-build state are
compiler by-products. They remain in operation-private staging, are discarded
with it, and MUST NOT enter cache identity, the receipt, the marker, the shim
relationship, or publication.

The `runtime-bundle` class is rejected for this version. A runtime bundle is any
artifact that requires a manager-generated launcher, an interpreter or virtual
machine, a classpath or module path, a runtime image, or more than one published
file. It is rejected because:

- receipts, markers, shims, currentness, and garbage collection are all built on
  exactly one artifact path and one artifact digest, and a bundle would require
  every one of those identities to be redefined;
- a manager-generated launcher is manager-authored executable content whose
  contents would be derived from package data such as a main class and a
  classpath, which reintroduces the install-time execution surface the protocol
  exists to exclude;
- the required runtime would be an execution-time dependency the manager cannot
  fingerprint, cannot bind into cache identity, and cannot verify at install
  time, so a marker could claim currentness for an artifact that no longer runs;
  and
- `protocol/core.md` section 12.1 requires a shim to point exactly at the
  marker-selected protected artifact, which a bundle cannot satisfy without
  widening that rule.

A driver and platform pair that can only produce an artifact needing a
manager-published or manager-installed sidecar runtime file MUST NOT be admitted
for that platform in this version. It fails with
`build_artifact_class_unsupported` rather than gaining a sidecar, a launcher, or
an installer step. A future runtime-bundle profile requires its own artifact
class identity, its own receipt, marker, and claim schema versions, a launcher
generation contract, a runtime identity and verification contract, and its own
review. It MUST NOT be admitted by widening `native-executable-v1` or any of the
eight driver identifiers.

This version does not require bit-reproducible artifacts. Cache identity is
keyed on the canonical build input, and the artifact digest records what a
specific operation produced. A toolchain step that legitimately embeds
non-reproducible bytes, such as a linker-applied ad-hoc signature, is compiler
output and not a manager signing step, but it MUST be produced by the driver's
fixed argument vector without selecting a signing identity, credential, or
network interaction.

### 4. Local source ownership: context-excluded build roots

Local drivers reuse the schema-6 and schema-7 `build_roots` model without
change. A local build root MUST be a portable relative path other than `.`, MUST
name a real link-free directory in the immutable raw skill snapshot, MUST be
unique and pairwise disjoint, MUST NOT equal, contain, or be contained by a
runtime root, and MUST be referenced by at least one local build command. Build
roots are statically excluded from agent context and from the runtime copy
before cache lookup or any compiler discovery, and that exclusion applies
identically to real builds, exact cache hits, and dry-runs.

A schema-8 local build command, `buildCommandV8`, has exactly this
package-controlled surface, with `driver` drawn from whichever local identifiers
the admitted wire driver set holds when schema 8 is minted:

```json
{"type":"build","driver":"go-v1","source_dir":"build/cmd/tool",
 "toolchain":{"id":"go","version":{"kind":"at_least","min":"1.23.0"}}}
```

The same shape carries a reserved identifier once its contract is accepted and
it has moved into the admitted wire driver set — for instance
`{"type":"build","driver":"rust-v1","source_dir":"build/cmd/tool",
"toolchain":{"id":"rust","version":{"kind":"at_least","min":"1.82.0"}}}` — and
until that move a manifest naming it is rejected as an unknown driver.

The object MUST contain exactly `type`, `driver`, `source_dir`, and `toolchain`,
all four REQUIRED, with `additionalProperties` false. `toolchain` is the closed
`toolchain-requirement-v1` object owned by decision 0007: exactly `id` and
`version`, where `id` MUST equal the driver's registry primary toolchain and
`version` is exactly one of the three closed kinds. It is admitted as the fourth
member for one reason and no other — it can only *filter* within the
manager-trusted toolchain set. It cannot name, add, locate, download, activate,
or switch a candidate, and it cannot reach the registry's tested-release
`compatibility` set. Its shape, grammar, ordering, intersection, and diagnostics
are decision 0007's, are not restated here, and MUST NOT be redefined by a
driver contract.

Placement is by reference to one shared definition and never by an inline
object. In `schemas/v1/common.schema.json` the requirement object is the single
definition `toolchainRequirementV1`, and in every slot that carries it the
property schema MUST be exactly `{"$ref":"#/$defs/toolchainRequirementV1"}` with
no sibling keyword. `toolchainRequirementV1` itself MUST be an object schema —
`"type": "object"` exactly, never omitted and never unioned with another type —
declaring exactly `id` and `version`, both REQUIRED, with `additionalProperties`
false; decision 0007 owns everything inside `version`. The object type carries
the closure rather than decorating it: `properties`, `required`, and
`additionalProperties` constrain objects and say nothing about a string, so a
definition that keeps the two members while admitting a scalar hands the package
a free-text toolchain value through a slot the wire still calls closed. Naming
the member is not carrying the object,
so a slot declaring `toolchain` as a string, as an inline object, as an object
carrying a path, root, URL, channel, mirror, or credential member, or as a
reference to any other definition — in particular the resolved
`goToolchainIdentityV1` toolchain identity, which is a build input rather than a
gate — is not the requirement object and MUST be rejected. One definition, one
reference form, and one closed member set is also what keeps the three slots
from drifting apart once three driver contracts land independently.

`buildCommandV6` is frozen at exactly `type`, `driver`, and `source_dir` and
MUST NOT gain `toolchain` or any other member; a schema-6 or schema-7 command
takes its driver's registry baseline requirement, exactly as decision 0007
states.

Beyond those four members no driver may add a package-controlled member. In
particular a manifest MUST NOT express a binary, product, crate, module,
target-name, feature, profile, configuration, optimization level, argv,
environment, flag, tag, linker option, toolchain path, toolchain root, download
location, mirror, channel or track, version-manager reference, install or
package-manager command, output name or path, install destination, alias, PATH
edit, signing identity, credential, trust root, hook, plugin, macro, generator,
recipe, post-build action, fallback, or secondary artifact. A version constraint
inside the closed `toolchain` object is the single admitted exception to the
toolchain-related half of that list, and it is admitted only in the filtering
sense above.

Each local driver MUST bind exactly one closed driver-defined project-metadata
file that MUST exist directly in the build root and MUST be the nearest ancestor
of `source_dir`, exactly as `go-v1` binds `go.mod`. A manager MUST NOT discover,
search for, or infer that file, the module, the target, the command, or the
output. Every non-standard module, package, source, embedded, and vendored input
selected by the driver's fixed graph phase MUST remain below the command's build
root.

Each local driver MUST define a deterministic, non-discovering mapping from
`source_dir` to exactly one compiled program. A driver that cannot define such a
mapping without a new package-controlled member MUST be rejected for this
version. Widening the command object is not an option, because the consuming
manifest command key is the sole executable name and the sole naming authority.

### 5. External source ownership: `skill-build.json` schema 2

The external envelope of decision 0005 is unchanged. The consuming manifest owns
`build_repositories` and the command key; the repository owns only the
descriptor; the manager owns acquisition, validation, audit, naming,
publication, and every process.

The schema-8 external build command, `repositoryBuildCommandV2`, MUST contain
exactly `type`, `driver`, `repository`, `target`, and `toolchain`, all five
REQUIRED, with `additionalProperties` false. `toolchain` is the same closed
`toolchain-requirement-v1` object, admitted under exactly the reasoning of
section 4. `repositoryBuildCommandV1` is frozen at its four members and MUST NOT
gain a fifth.

`skill-build.json` remains the sole descriptor filename, at the repository root
and nowhere else, with no alias and no implementation-specific name. Schema 2
changes exactly two things and nothing else, in the target object
`skillBuildTargetV2`:

1. `driver` becomes a `oneOf` over the admitted external identifiers; and
2. one OPTIONAL member is added, `toolchain`, the same closed
   `toolchain-requirement-v1` object, carried by exactly the same
   `{"$ref":"#/$defs/toolchainRequirementV1"}` reference as the two schema-8
   commands. OPTIONAL governs whether the member must be present, never what it
   means: a present descriptor `toolchain` is the identical closed object, and
   the malformed shapes rejected in section 4 are rejected here too.

`driver`, `build_root`, and `source_dir` stay REQUIRED and keep their schema-1
meaning, `additionalProperties` stays false, and the document still contains
exactly `schema_version` and a non-empty `targets` map. `skillBuildTargetV1` is
frozen at its three members and MUST NOT gain a fourth.

The descriptor requirement is OPTIONAL rather than REQUIRED because the
repository, not the consuming skill, is the party that knows what its own source
needs, and a repository written before schema 2 must stay readable: an absent
`toolchain` contributes no interval and the effective requirement is decided by
the registry baseline intersected with the consuming manifest's REQUIRED
requirement. Where both are present they intersect, which is associative and
commutative, so no ownership question arises and an empty intersection is a
deterministic host-independent rejection rather than a precedence rule.

Beyond that OPTIONAL member, a descriptor MUST NOT express a build, install,
test, or run command, argv, environment, feature, profile, configuration,
product, target name, output name or path, toolchain path, toolchain root,
channel or track, download location, mirror, version-manager reference, install
or package-manager command, trust root, platform list, signing identity,
credential, hook, plugin, macro, generator, recipe, post-build action, fallback,
or secondary artifact. A repository declaring a version constraint can only
narrow within the manager-trusted set; it can never introduce a candidate into
it.

The repository owns the descriptor schema version and the consuming manifest
owns nothing about it. A manager that supports schema 8 MUST read descriptor
schemas 1 and 2. Descriptor schema 1 remains frozen and can express only
`go-repository-v1` targets. A `rust-repository-v1`, `swift-repository-v1`, or
`kotlin-native-repository-v1` command therefore requires a schema-2 descriptor;
against a schema-1 descriptor it MUST fail closed with
`build_descriptor_driver_unsupported`, and against an unsupported descriptor
version with `build_descriptor_schema_unsupported`. Neither failure may fall
back to another target, another driver, `go-v1`, a script, a system command, or
a generic build facility.

The command and descriptor drivers MUST be equal, and both MUST name the same
external identifier. The whole repository snapshot remains the validation,
identity, and audit subject; only the selected build root is compiler-visible;
and no external repository byte is agent-facing or runtime-copied. The
schema-6 prohibition on a local `build_root` equal to `.` is unaffected by the
descriptor's admission of `.` as a repository root.

### 6. Toolchain boundary

The manifest toolchain requirement, trusted resolution, version grammar and
comparison, two-stage preflight ordering, diagnostics, and installation-guidance
catalog are defined by the shared toolchain contract, decision 0007
(`TASK-260728-1g0z69`), and integrated by `TASK-260728-2jaw7h`. This decision
does not restate or redefine them. It supplies the two things that contract
leaves to this one — the version numbers of the schemas that carry it, fixed in
section 1, and the exact wire slots it lands in, fixed in sections 4 and 5 —
and it fixes the boundary properties the version and artifact model depends on:

1. Every new driver's canonical build input MUST bind a complete trusted
   toolchain identity produced by that contract, as an ordered
   `toolchain_identities` array covering the registry primary toolchain and any
   companions. `curator-go-toolchain-v1` stays frozen and Go-only, `go-v1` and
   `go-repository-v1` keep their existing single-field toolchain identity shape
   byte-for-byte, and no other driver may reuse, extend, or alias either.
2. The trusted toolchain is operator-owned. No manifest, descriptor, repository,
   substitution, or environment value may supply a toolchain path, URL, channel
   or track, mirror, trust root, installer, version-manager reference, or
   package-manager command, and no version of any driver may auto-install a
   toolchain. The closed `toolchain-requirement-v1` object of sections 4 and 5 is
   not an exception to this: it selects nothing, it only intersects an interval
   against the set the operator already trusts, and it cannot reach the
   registry's tested-release `compatibility` set.
3. Every executable started below the worker MUST be a fingerprinted member of
   the driver's declared trusted toolchain closure. When a compiler requires a
   platform linker, SDK, sysroot, runtime library, or archiver that is not inside
   the fingerprinted distribution, the driver MUST bind that component into its
   toolchain identity or MUST reject that platform. A host-resolved tool outside
   the closure is not admissible.
4. Because the toolchain identity is inside the canonical build input, two
   toolchains never alias in the cache, the receipt, the marker, or a claim.
5. Host availability and version preflight runs before source acquisition, and
   the project-metadata compatibility cross-check runs after local validation or
   exact external acquisition and audit and before any compiler work. This
   ordering is owned by the toolchain contract and is restated here only because
   the artifact and audit boundary assumes it.

### 7. Execution policy and process graph

Decision 0006 defines `manager-worker-v1` with a Go-bound process graph —
`<GOROOT>/bin/go` and executables below
`<GOROOT>/pkg/tool/<GOHOSTOS>_<GOHOSTARCH>/` — and a Go-bound session of exactly
one `go list` and exactly one `go build`. Its own rejected-alternatives list
records why that is load-bearing: a semantic change to the process graph without
a cache-identity change would let one entry alias another. Reading that identity
generically so it also covers a Rust, Swift, or Kotlin pipeline would reinterpret
a definition that is already bound into frozen rc.4 and rc.5 bytes, and the label
in a published receipt or claim would then no longer mean what the decision that
minted it says.

This boundary therefore mints a second portable execution-policy identity,
`manager-worker-v2`, and leaves `manager-worker-v1` untouched.

**`manager-worker-v1` is frozen and Go-only.** Its definition, process graph,
session shape, and wording in decision 0006, `protocol/core.md` section 4.2.1,
and `profiles/manager.md` section 2.2.1 keep their exact meaning and exact
bytes. It stays the policy of `go-v1` and `go-repository-v1` for the whole of
Protocol 1.0. No `go-v1` or `go-repository-v1` canonical build input, logical
cache key, receipt byte sequence, marker record, or claim changes, and the rc.5
candidate is untouched, because nothing that Go binds is re-read.

**`manager-worker-v2` is a concurrent sibling, not a successor.** The two
identities are both live at Protocol 1.0. v1 is not deprecated, not superseded,
not migrated, and not reinterpreted, and v2 does not replace it. The integer is
an identity discriminator only: a reader MUST NOT infer recency, precedence,
supersession, or containment strength from it, and strength may be compared only
where a specification states the comparison in words. The binding is fixed by
the closed table of section 2, is chosen by neither package data nor operator
configuration, and admits no third combination:

| Driver | Execution policy |
|---|---|
| `go-v1`, `go-repository-v1` | `manager-worker-v1` |
| the six reserved identifiers | `manager-worker-v2` |

`manager-worker-v2` carries the identical portable containment contract. The
mandatory portable control set of `protocol/core.md` section 4.2.1, the
exhaustive `rc5-native-control-inventory-v1` inventory, the single
`build_execution_control_unavailable` failure boundary, the exclusion of host
capability evidence from cache identity, and the six deferred hardened
guarantees are the same under both identities, byte for byte and control for
control. No control is added, removed, re-scoped, or weakened. The inventory
keeps its `rc5-` name because its membership is unchanged and inventory
membership never enters a build input, an artifact, or a hashed identity.

Exactly two things differ, and they are exactly the two things that could not be
said generically about v1 without reinterpreting it.

First, the two lower graph nodes are bound per driver rather than to Go:

```text
manager parent
  -> identity-verified manager-owned worker
       -> the driver's fingerprinted trusted launcher
            -> fingerprinted regular executables inside that driver's
               fingerprinted trusted toolchain closure
```

The launcher and the tool set are the members of that driver's declared trusted
toolchain closure required by section 6 item 3, resolved through decision 0007
and bound into the canonical build input. The upper two nodes — the manager
parent and the identity-verified manager-owned worker — are identical to v1.

Second, the worker session admits a driver with no graph phase. One v2 session
performs **at most one** read-only graph phase of at most one driver-defined
command, waits while the parent validates the complete graph, accepts exactly
one authenticated build permit, and performs exactly one compile phase of
exactly one driver-defined command. v1 requires exactly one `go list` and
exactly one `go build`; v2's "at most one" graph phase is a different session
shape, which is a second independent reason the identity must differ. The v2
session admits no retry, second graph phase, second compile phase, additional
executable, shell, VCS operation, dependency download, generator, test, run, or
tool request. A driver that cannot map its pipeline onto that session shape MUST
NOT be admitted in this version; widening the session shape further requires yet
another execution-policy identity, a new claim schema version, and its own
review.

Because both identities are closed constants inside the canonical build input, a
v1 entry and a v2 entry can never alias in the cache, a receipt, a marker, or a
claim, and a reader that knows only v1 cannot mistake a v2 artifact for a
portable Go artifact.

The per-operation host capability evidence record is re-versioned to
`capability-evidence-v2`, reserved here and minted by the integration task, for
two reasons that are both semantic rather than structural. `capability-evidence-v1`
is normatively closed to `execution_policy: "manager-worker-v1"` — any other
value is `build_execution_hardened_claim_forbidden` — so it cannot report a v2
operation at all. And because section 9 admits a manifest mixing Go and
additional-driver commands in one operation, one operation can be active under
both identities, which v1's exactly-one-record-per-operation cardinality cannot
express. `capability-evidence-v2` keeps the closed member set
`{record_version, execution_policy, platform, controls}` and the probe-once-per-
operation rule unchanged; it admits `execution_policy` drawn from exactly
`{manager-worker-v1, manager-worker-v2}`, and the manager emits one record per
distinct execution-policy identity active in the operation, all sharing that
operation's single probe result and `probed_at`. Any other `execution_policy`
value, including a hardened one, remains
`build_execution_hardened_claim_forbidden`. The record stays result-only and
MUST NOT enter a cache key, receipt input, marker record, or claim, so
re-versioning it moves no frozen byte and `capability-evidence-v1` keeps its
exact meaning for every v1-only operation.

One consequence of that reservation is stated here rather than discovered later.
The rc.5 corpus and release gate already use `capability-evidence-v2` as their
example of a record version that MUST be rejected: the
`unknown-evidence-record-version-is-rejected` case in
`conformance/v1/vectors/go-host-execution-policy.json` and the "drifted
capability-evidence record" release-gate case both name it. Both are correct at
rc.5, where the version does not exist, and both stay frozen and correct for
rc.5. When rc.6 mints the record, `TASK-260728-251p01` MUST move those two
literals to a version that remains unminted and MUST NOT change the rc.5 corpus
bytes or the rc.5 pin to do so. The boundary gate proves the current state
positively rather than by absence: it requires the frozen corpus to keep
rejecting the reserved version.

Before the compile phase, each driver MUST apply an exhaustive, deterministic,
pre-compile rejection matrix computed from the validated snapshot and its graph
phase, in the same position where `go-v1` rejects `SysoFiles`, native inputs,
and the non-standard `//go:cgo_import_dynamic` directive. The matrix MUST reject
every package-selected code-execution surface for that language, including build
scripts, procedural and compiler macros, compiler and build-system plugins,
annotation processors, source generators, manifest programs, build tasks and
recipes, response files, package-selected linkers and native libraries, and
network or registry access. A surface that cannot be rejected deterministically
before the compile phase MUST cause the driver to be rejected, and MUST NOT be
answered by a runtime allowance, an advisory warning, or a sandbox promise. The
shared semantic class for such a rejection is
`build_package_code_execution_forbidden`; each driver contract defines its own
per-surface diagnostics beneath it.

### 8. Cache, receipt, marker, and claim identity

`curator-build-source-v1` is unchanged and is reused as the source identity for
every driver in both source modes. It hashes bytes, not language, so no new
source-identity algorithm is created. The protected external snapshot key of
`protocol/core.md` section 9.4 is likewise unchanged.

Each logical cache key remains the SHA-256 of `CCJ-1` over the complete build
input. Every new build input MUST bind its receipt schema version, driver,
source state for its mode, consuming command name, build root and source
directory selection, native target, complete trusted toolchain identity, and a
closed per-driver policy object whose `execution_policy` is the `const`
`manager-worker-v2`. Inputs from different drivers cannot alias, because
`driver` and the policy object differ, and a v1 input can never alias a v2 input
because the policy constant differs.

The effective toolchain requirement and the registry `compatibility` set are
gates rather than build inputs, exactly as decision 0007 fixes them, so the
`toolchain` object admitted in sections 4 and 5 never enters a cache key,
receipt, marker, or claim. What enters the build input is the resolved toolchain
identity, not the constraint that filtered it. This is why adding a REQUIRED
fourth member to the schema-8 local command changes no `go-v1` identity: a
schema-8 Go command carries a `toolchain` requirement on the wire and its
canonical build input is byte-identical to the schema-6 and schema-7 input it
already produces.

Build receipt schema 3 covers the local source mode and schema 4 covers the
external source mode, each as a strict `oneOf` discriminated by the `driver`
`const`, and each carrying that driver's own toolchain identity, native target,
and closed policy object. Receipt schemas 1 and 2 keep their bytes and meanings,
including their `goExecutionPolicyV1` constant `manager-worker-v1`.

Install marker schema 4 permits `skill_schema_version` through 8 and represents
local-only, external-only, and mixed command sets across receipt schemas 1
through 4 and both execution-policy identities. Every build entry MUST
explicitly record its driver, its `receipt_schema_version`, and its
`execution_policy`, and a reader MUST validate both recorded values against the
two closed tables of section 2 and reject a mismatch rather than infer an absent
value from a driver name. A marker-v4 entry naming a Go driver with
`manager-worker-v2`, or a reserved driver with `manager-worker-v1`, is a
mismatch and MUST be rejected. Marker schemas 1 through 3 keep their shapes.

Marker v4 generalizes exactly one schema-6 rule. Top-level `build_source` is
REQUIRED exactly when at least one active local build command of any admitted
local driver exists, and MUST otherwise be absent; marker v3's `go-v1`-only
wording does not survive into v4, and marker v3 itself is unchanged. External
entries continue to bind source per entry and MUST NOT use the consuming skill's
raw snapshot as external compiled-source identity.

Conformance claim schema 4 pins `protocol_version` to the rc.6 candidate and
admits driver assertions for **exactly the admitted wire driver set as it stands
when claim schema 4 is minted** — no fewer, and never one more. Membership is
therefore not a fixed count of eight. Section 2 admits a reserved identifier only
when its own contract is accepted and `TASK-260728-251p01` moves it, and a
rejected contract retires its identifiers unused, so the claim schema is minted
against the outcome rather than against the reservation. It admits eight
identifiers if and only if all six reserved contracts are accepted; if, for
instance, no Kotlin backend satisfies section 3 and both Kotlin identifiers are
retired, claim schema 4 admits six, and a retired identifier is then
structurally unassertable rather than merely unclaimed. A claim schema MUST NOT
carry an assertion for an identifier that is not in the admitted wire driver set
at minting time; admitting one later requires a further claim version minted in
the same change that admits the driver.

The assertion list carries that admission, so the list itself is closed. Every
element MUST be reached by the single `items.oneOf` over the admitted assertions,
and the array MUST NOT declare a second element path. This is not style: under
Draft 2020-12 `items` applies only to the elements `prefixItems` did not already
cover, so one `prefixItems` entry exempts the leading assertion from the closed
`oneOf` entirely and a reserved or retired identifier becomes assertable while
every listed branch still reads correctly. The same holds for any array
applicator added later, so the container admits only keywords that cannot reach
an element — `type`, `items`, `minItems`, `maxItems`, `uniqueItems`, and
annotations — and anything else is rejected rather than interpreted. A claim
version MUST also declare the driver member: the newest claim schema is the
current one whether or not it asserts drivers, and a newer claim that simply
omits the member would otherwise hand currency back to a frozen predecessor and
assert nothing while the older schema was read as covering the admitted set.

Each assertion requires exactly `driver`, `language`, `execution_policy`, and
`operating_systems`, with `additionalProperties` false, and is an object schema —
for the same reason `toolchainRequirementV1` is, since those three keywords do
not constrain a non-object element. `execution_policy` is not
free within an assertion: it is a `const` selected by the assertion's own
`driver` `const`, `manager-worker-v1` for the two Go drivers and
`manager-worker-v2` for each admitted reserved driver, so the section 2 binding
is structural rather than a prose rule a claim author could violate. That
per-driver pairing is retained whatever the admitted set turns out to be. The
schema admits exactly those two policy identities and no other, so a hardened
claim remains structurally impossible and needs a later claim version. Claim
schemas 1 through 3 keep their bytes, continue to admit only
`manager-worker-v1`, and remain valid because they assert a subset of an
admitted set that only ever grows by an accepted contract.

### 9. Mixed commands, platform claims, credentials, and signing

Manifest schema 8 MAY mix script commands, system commands, and build commands
of any admitted driver in one manifest and one closure node. Activation,
dependency-command selection, portable-name collision, shim collision, and
provider-first closure rules are unchanged, and active build command names are
still processed in Unicode-scalar lexical order within a closure node. Each
command independently derives its own artifact name, build input, cache key,
receipt, marker entry, and shim, whichever driver it names.

Mixing therefore reaches both execution-policy identities in one operation. That
is admitted, and it has exactly three consequences, all already fixed above:
each command's own build input binds its own policy constant, so nothing aliases;
`capability-evidence-v2` reports one record per distinct active policy; and the
marker records the policy per entry rather than per marker. The mandatory
portable control set is identical under both identities, so a mixed operation
applies one set of controls, not two.

This decision makes no platform claim. Each of the six reserved identifiers
starts with an empty qualified-platform set. macOS and Windows remain the
platforms of the portable policy and Linux remains excluded until
`TASK-260728-1skseh`. A driver and platform tuple may enter a claim only when
its driver contract is accepted, its conformance vectors exist, and immutable
native evidence for that exact tuple exists; qualification verifies this. A
platform that cannot satisfy section 3's artifact class or section 6's toolchain
closure is excluded from the claim rather than shipped with a compensating
sidecar, host-resolved tool, or downgraded control.

Credentials, host-verification state, transport executables, proxy policy,
timeouts, and authentication modes stay operator-owned for every driver and MUST
NOT appear in a manifest, descriptor, repository, compiler environment, receipt
trust field, or marker.

No driver admitted by this boundary performs manager post-build signing,
timestamping, or notarization, and no package data may select a signing
identity, certificate, entitlement, or notarization credential. A platform
policy that requires a locally signed binary MUST reject the build until the
separately versioned and reviewed signer profile of `protocol/core.md` section
12.2 exists.

### 10. Downstream obligations

- `TASK-260728-1g0z69`, then `TASK-260728-2jaw7h`: the shared toolchain
  requirement, resolution, comparison, two-stage preflight, diagnostics, and
  guidance catalog, satisfying section 6 items 1 through 5 and adding no
  package-controlled installation data. `TASK-260728-2jaw7h` lands the
  `toolchain` object in exactly the three slots section 1 names and sections 4
  and 5 shape — REQUIRED in `buildCommandV8` and `repositoryBuildCommandV2`,
  OPTIONAL in `skillBuildTargetV2` — as the single shared definition
  `toolchainRequirementV1` referenced identically from all three slots, and MUST
  NOT place it anywhere else, MUST NOT inline it, MUST NOT add it to
  `buildCommandV6`, `repositoryBuildCommandV1`, or `skillBuildTargetV1`, and MUST
  NOT add a second member alongside it.
- `TASK-260728-12pnm1` (Rust), `TASK-260728-1yhuqi` (Swift),
  `TASK-260728-168smo` (Kotlin): one accepted contract per pair, each defining
  the local project-metadata file and `source_dir` mapping of section 4, the
  descriptor target semantics of section 5, the fingerprinted toolchain closure
  of section 6 item 3, the single graph and compile commands and the exhaustive
  pre-compile rejection matrix of section 7, the closed policy object and native
  target of section 8, and the per-platform proof that section 3's artifact
  class is met. `TASK-260728-168smo` additionally decides the Kotlin backend
  within, not around, section 3; if no Kotlin backend satisfies it, both Kotlin
  identifiers are retired unused.
- `TASK-260728-251p01`: integrate only the accepted contracts into manifest
  schema 8, descriptor schema 2, receipt schemas 3 and 4, marker schema 4, claim
  schema 4 over exactly the identifiers it moves in that same change,
  `capability-evidence-v2`, the profiles, `SECURITY.md`,
  `COMPATIBILITY.md`, `CHANGELOG.md`, and the generated positive and negative
  corpus, keeping schemas 1 through 7 and every Go identity byte-stable. It also
  defines `manager-worker-v2` normatively in `protocol/core.md` section 4.2.1 and
  `profiles/manager.md` section 2.2.1 as a section headed in its own right rather
  than as an edit to the `manager-worker-v1` text, moves each admitted identifier
  from the reserved namespace to the admitted wire driver set in the same change
  that mints the schema admitting it, extends the boundary gate's exact
  member-set table with the schema-8 and descriptor schema-2 definitions, and
  moves the two `capability-evidence-v2` negative literals identified in section
  7 to a version that remains unminted without touching the rc.5 corpus bytes or
  the rc.5 pin.
- `TASK-260728-2bu2q6`: qualify the candidate, recompute every identity, and
  emit only evidence-backed driver and platform claims.
- `STORY-260728-327soo` continues to own the six deferred hardened guarantees.
  None of them may be named, claimed, or implied by any driver admitted here.

### 11. Enforcement while the reservation stands

`tools/validate.py` carries a deterministic boundary gate that runs on every
validation. It:

1. requires this decision to fix both closed sets by name, both artifact
   classes, the boundary failure classes, both execution-policy identities, the
   reserved evidence-record version, and the toolchain requirement object;
2. forbids this decision from naming a deferred hardened guarantee;
3. rejects any occurrence of a reserved driver identifier or the reserved policy
   identity on a surface file outside `decisions/`, because a decision record is
   where an identifier is proposed, reserved, and retired while every other
   surface is admission;
4. proves the reserved capability-evidence record version un-admitted
   positively rather than by absence, by requiring the frozen corpus to keep
   rejecting it — absence would be the wrong test, because that version already
   appears in the rc.5 corpus and release gate as the example of a version that
   MUST be rejected;
5. requires every driver-bearing schema definition to close `driver` with a
   `const` over the admitted wire driver set and to require it;
6. checks every driver-bearing definition against a **closed exact member-set
   table** rather than a deny-list — each definition's property set, required
   set, `additionalProperties: false`, and `"type": "object"` must match the
   table exactly, and a driver-bearing definition missing from the table is
   itself a failure, so no optional selector, command, install, or bundle member
   can be added anywhere without the gate rejecting it; the object type is part
   of the check because a member set closed over a definition that is not an
   object closes nothing;
7. holds the reserved shapes of `buildCommandV8`, `repositoryBuildCommandV2`,
   and `skillBuildTargetV2` in that same table, so the schema-8 and descriptor
   schema-2 surfaces are enforced exactly from the moment they are minted, and
   rejects a reserved shape minted without a `driver`, which would otherwise not
   be driver-bearing and so would escape the table entirely;
8. holds the `toolchain` property of those three shapes to the **exact** schema
   `{"$ref":"#/$defs/toolchainRequirementV1"}` rather than to the member name,
   rejecting a string, an inline or open object, a path-bearing object, and a
   reference to any other definition, and requires the referenced
   `toolchainRequirementV1` to exist, to be an object schema, and to be closed to
   exactly `id` and `version` — a member set alone would let the
   trusted-preflight boundary be named on the wire without being carried, and a
   member set over a non-object would let it be carried in name while the slot
   accepted free text;
9. requires every conformance claim schema that asserts build drivers to assert
   only identifiers in the admitted wire driver set, to pair each with the
   execution policy the closed table binds to it, and to keep each assertion an
   object schema closed to its four members and to its four keywords; closes the
   assertion list so `items.oneOf` is its only element path, rejecting
   `prefixItems` and every other array applicator that could carry an assertion
   the `oneOf` never sees; and selects the current claim schema as the newest one
   *before* inspecting any of them, requiring that schema to declare the driver
   member and to assert every admitted driver — so a claim can never assert a
   reserved or retired identifier, a newer claim cannot drop the member and hand
   currency back to a frozen predecessor, and the claim version minted with an
   admission covers exactly the set that admission produced;
10. keeps a small residual deny-list of names that can never carry protocol
    meaning — generic language and build-system selectors, package-controlled
    installation and trust fields, and runtime-bundle members — as defense in
    depth behind the tables, so a definition added later cannot introduce one;
11. requires the published artifact to stay a single closed file by holding
    `buildArtifactV1` to an **exact object schema** — `"type": "object"`,
    `required` exactly `path` plus `sha256` plus `size`, those three and only
    those three properties, `additionalProperties: false`, and each property
    pinned to its canonical shared definition — and by holding each of the three
    referenced definitions, `portablePath`, `sha256`, and
    `nonNegativeSafeInteger`, to its **exact canonical schema**, keyword for
    keyword, so a pinned reference cannot be satisfied by a target that has been
    widened underneath it; a name-only comparison is not a closure here, because
    the object keywords say nothing about a scalar, a union, an array, or a
    boolean schema, and an emptied `required` set leaves the same three names
    admitting nothing; it separately proves against the compiled
    `build-receipt-v1` and `build-receipt-v2` validators that a launcher string,
    a bundle list, a boolean, an empty object, an extra runtime member, a
    traversing or absolute path, an unprefixed digest, a negative size, a
    non-integer size, and each of the three members omitted are all rejected —
    a behavioural layer that catches a target opened wholesale, and that is
    finite by construction and so is not what closes the three targets; it also
    keeps the reserved schema slots unallocated; and
12. proves against the compiled validators that each frozen manifest,
    descriptor, receipt, marker, and claim schema rejects each of the six
    reserved identifiers.

An integration task admits a driver by moving it from the reserved namespace to
the admitted wire driver set in that gate, together with the schemas and the
matching exact member-set entries, never by weakening the gate.

## Stable failure classes

These architecture-level outcomes are interoperable semantic classes and MUST
remain distinguishable from each other and from a cache hit, an audit success, a
source unavailability, or a generic fallback:

- `build_descriptor_schema_unsupported`;
- `build_descriptor_driver_unsupported`;
- `build_artifact_class_unsupported`; and
- `build_package_code_execution_forbidden`.

The stable failure classes of decision 0005 and the `build_execution_*`
diagnostics of decision 0006 continue to apply unchanged to every driver.

## Rejected alternatives

- **One driver identifier per language covering both source modes.** Rejected:
  the local and external modes have different source identities, receipts, audit
  subjects, and lifecycle rules, exactly as `go-v1` and `go-repository-v1` do,
  and collapsing them would make the receipt version unreadable from the wire.
- **A generic `native-v1` driver parameterized by a language field, or language
  detection from project-metadata filenames.** Rejected: it is the generic
  fallback that decisions 0004 and 0005 and `protocol/core.md` section 12.3
  forbid, and detection would let repository layout choose a compiler.
- **One receipt schema version per driver, giving six new receipt schemas.**
  Rejected: it multiplies frozen artifacts without adding discrimination, since
  the driver `const` already discriminates inside one schema and the marker
  records the receipt version explicitly.
- **Reusing receipt schemas 1 and 2 for the new drivers.** Rejected: it would
  change frozen rc.4 and rc.5 schema bytes and let a reader that only knows Go
  believe it understands a Rust, Swift, or Kotlin receipt.
- **Admitting a `runtime-bundle` artifact class so Kotlin/JVM could ship.**
  Rejected for the four reasons in section 3. The honest consequence is that
  Kotlin is admitted only through a native backend or not at all, and that
  outcome is `TASK-260728-168smo`'s to establish, not to negotiate away.
- **Letting a driver publish a sidecar runtime or redistributable library
  alongside the executable on platforms that need one.** Rejected: it is the
  runtime-bundle class under a different name, and it would make the artifact
  digest describe only part of what runs.
- **Adding package-controlled members such as a binary, product, feature,
  profile, or configuration to the local command or the descriptor target.**
  Rejected: the consuming command key is the sole executable name, and any
  additional selector hands output and pipeline control back to untrusted data.
  The closed `toolchain` requirement is admitted while those are refused because
  it is the one member that cannot select anything: it intersects an interval
  against a set the operator already trusts, and no spelling of it can add a
  candidate, name a location, or reach the tested-release set.
- **Keeping the schema-8 local command at exactly three members and finding
  another home for the toolchain requirement, such as a top-level manifest
  object or a manager-side configuration file.** Rejected: decision 0007 fixes
  the requirement as a property of one build command, and a top-level object
  would either apply to commands that name different drivers with different
  primary toolchains or need its own per-command keying, which is the command
  object again with an indirection. A manager-side home would move a
  source-derived expectation out of the artifact the author controls and leave
  no way to fail an authoring mistake deterministically. The narrower fix — one
  closed non-selecting member on the command — was taken instead.
- **Making the descriptor requirement REQUIRED like the manifest one, or
  dropping it entirely.** Rejected: REQUIRED would make every schema-2
  descriptor restate a constraint the repository may have no opinion about and
  would invite a repository to be treated as authoritative over the consuming
  skill; dropping it would discard the one party that actually knows what its own
  source needs. OPTIONAL plus interval intersection is order-independent, so
  neither party owns the answer and there is no precedence rule to get wrong.
- **Running the additional drivers under `manager-worker-v1` and restating its
  process graph and session generically.** Rejected: decision 0006 binds that
  identity to `<GOROOT>/bin/go`, to executables below
  `<GOROOT>/pkg/tool/<GOHOSTOS>_<GOHOSTARCH>/`, and to exactly one `go list` plus
  exactly one `go build`, and the same decision rules that a process-graph
  semantic change without a cache-identity change is unacceptable. Re-reading the
  identity generically would change what a frozen rc.4 and rc.5 label means after
  the fact, which is the one thing a versioned identity exists to prevent. It
  would also have to swallow a real difference — v1 requires a graph command, v2
  merely permits one.
- **Migrating `go-v1` and `go-repository-v1` to `manager-worker-v2` so one
  identity covers everything.** Rejected: this is the variant that would change
  every Go cache key, rewrite every Go receipt and marker, and invalidate the
  frozen rc.5 candidate, and it buys nothing — the two identities carry the
  identical portable containment contract, so collapsing them adds no guarantee.
  Minting v2 for the six reserved drivers alone changes no Go byte, which is why
  it is the version that was taken.
- **Naming the new identity outside the `manager-worker-` family to avoid the
  successor reading.** Rejected, with the cost acknowledged. A distinct family
  name would remove the one real drawback of `manager-worker-v2` — a casual
  reader taking the integer for supersession — but it would state something
  worse and untrue, that the additional drivers run under a different containment
  contract. They do not: the mandatory controls, inventory, failure boundary, and
  deferred guarantees are identical, and only the graph binding and the graph-phase
  cardinality differ. Continuing the family and attaching an explicit
  non-ordering rule keeps the name honest about what is shared, and the rule is
  the narrower thing to get wrong. A reader MUST NOT rank the two by integer;
  section 7 says so normatively rather than leaving it to naming convention.
- **Versioning the native-control inventory alongside the new drivers.**
  Rejected: inventory membership is unchanged, and it never enters a build input,
  artifact, or hashed identity, so a rename would carry no semantic content.
- **Keeping `capability-evidence-v1` for the additional drivers.** Rejected: it
  is normatively closed to `manager-worker-v1` and to exactly one record per
  operation, so it can neither report a v2 operation nor describe a mixed
  operation that runs under both identities. The record is result-only, so
  re-versioning it moves no frozen byte; leaving it alone would instead force
  either a false `execution_policy` value or a silent gap in reporting.
- **Bumping `Skillfile.dev.json` to schema 3.** Rejected: substitution selects
  source acquisition only and cannot express a driver, toolchain, target, or
  artifact class.
- **Deferring the version and artifact boundary until the three driver contracts
  are written.** Rejected: each contract would then choose its own versions,
  artifact shape, and descriptor evolution, and the first one merged would define
  the wire by accident.
- **Allowing each driver, or each language family, to state its own
  execution-policy identity.** Rejected: policy identity is a security-strength
  statement, and per-driver or per-family identities would let one driver's
  weaker contract be read as the portable policy, and would multiply the
  identities a claim reader has to compare. All six reserved drivers share
  `manager-worker-v2` precisely because they share one contract; a driver that
  needs a different contract is not admitted rather than given its own label.

## Compatibility impact

This decision changes no bytes. It adds no schema, no vector, no generated case,
and no release metadata; it does not alter the rc.5 conformance manifest digest
or any pin. Manifest schemas 1 through 7, `skill-build.json` schema 1, receipt
schemas 1 and 2, marker schemas 1 through 3, claim schemas 1 through 3,
`Skillfile.dev.json` schema 2, `manager-worker-v1`, `capability-evidence-v1`,
`rc5-native-control-inventory-v1`, `curator-go-toolchain-v1`,
`curator-build-source-v1`, and all rc.4 and rc.5 conformance bytes keep their
exact contents and meanings, and every `go-v1` and `go-repository-v1` identity is
unchanged.

Three of the reservations deserve their compatibility statement said plainly,
because each could be misread as a change to something frozen.

`manager-worker-v2` is additive. It does not modify, deprecate, supersede, or
re-scope `manager-worker-v1`, which stays the policy of both Go drivers for the
whole of Protocol 1.0. No Go cache key, receipt, marker, or claim changes,
because no Go build input names the new constant. A reader that knows only
`manager-worker-v1` continues to read every existing artifact correctly and
rejects a v2 artifact as an unknown policy, which is the intended outcome.

`capability-evidence-v2` is additive and result-only. It never enters a cache
key, receipt, marker, or claim, so no frozen byte and no published identity
depends on it. A v1-only operation may continue to emit
`capability-evidence-v1`, whose meaning is unchanged.

The REQUIRED `toolchain` member of `buildCommandV8` and
`repositoryBuildCommandV2` is a schema-8 authoring requirement, not a rebuild
trigger. `buildCommandV6`, `repositoryBuildCommandV1`, and `skillBuildTargetV1`
gain nothing; a schema-6 or schema-7 manifest and a schema-1 descriptor stay
byte-valid and keep taking the registry baseline. Because the requirement is a
gate and not a build input, a `go-v1` command that moves from schema 7 to schema
8 produces a byte-identical canonical build input, the same logical cache key,
and the same artifact, and causes no rebuild.

When the reserved versions are minted, they are explicit reader and writer
version transitions. Readers never infer them from fields, MUST reject an
unsupported version rather than downgrade it, and MUST write the version the
active feature requires. Schemas 1 through 7 MUST reject the six reserved driver
identifiers, the reserved execution-policy identity, and every schema-8-only
field.

## Security impact

The security posture of the portable policy is unchanged, and no hardened
guarantee is added, implied, or claimed. The six deferred guarantees remain
deferred to `STORY-260728-327soo` and MUST NOT appear in a mandatory-control set,
the native-control inventory, or a capability-evidence record.

Minting `manager-worker-v2` claims no additional containment and removes none.
It carries the same mandatory portable control set, the same inventory, the same
single failure boundary, and the same honest limits as `manager-worker-v1`; the
whole of its security content is that a Rust, Swift, or Kotlin build is labelled
as what it is rather than as a Go build. The one real security effect is
negative-by-design: because the identity is a `const` in the build input, a v2
artifact cannot be presented to a v1 reader as portable Go output, and a claim
cannot assert a policy its driver does not run under.

The `toolchain` member admitted on the wire is the narrowest surface that could
carry decision 0007's requirement, and its safety rests on one checkable
property: intersection can only remove candidates from a manager-trusted set. No
spelling of it names a path, a URL, a channel, a mirror, a version manager, an
installer, or a trust root, none of those fields exists to be spelled, and it
cannot reach the registry's tested-release `compatibility` set. That holds only
if each slot carries the object rather than the member name, which is why all
three slots are held to the exact `toolchainRequirementV1` reference and the
definition to an object schema carrying exactly `id` and `version`: a slot
declaring `toolchain` as a string, an open object, or a path-bearing object —
or a definition that keeps those two members while declaring itself a string, no
type at all, or an object-or-string union — would satisfy a member-set check
while reopening precisely the surface this paragraph claims does not exist. A package can
therefore make a build fail, which it could already do with any invalid input,
and cannot make a build use a compiler the operator did not trust.

The exposure that does change is compiler input. Admitting three more compiler
front ends under the same portable, non-hardened controls widens the untrusted
parsing, code-generation, and resource-consumption surface, and each of the three
languages ships a mainstream build path whose normal operation executes
package-selected code. That is why section 7 requires a deterministic
pre-compile rejection matrix rather than a runtime allowance, why section 6 item
3 requires every started executable to be inside a fingerprinted closure, and why
a surface that cannot be rejected before compilation disqualifies its driver.
Each driver contract MUST state its own compiler-input denial-of-service and
vulnerability exposure honestly and MUST NOT rely on containment this protocol
does not yet provide.

Section 3 also closes a currentness gap rather than opening one: a single
self-contained executable is fully described by one digest the manager computed,
whereas a bundle plus an external runtime could be reported current while the
runtime it needs is gone. That guarantee is only as strong as how
`buildArtifactV1` is expressed, and it is the same failure class as the
requirement definition above: a definition that keeps `path`, `sha256`, and
`size` while declaring itself a string, an `object`/`string` union, no type at
all, or a boolean schema — or that keeps all three names and requires none of
them — readmits a launcher, a bundle, or an artifact with no computed digest at
all, while every shipped positive case still validates. That is the rejected
`runtime-bundle` class re-entering through the definition this section relies on
to exclude it, so the gate holds the definition to an exact object schema and
proves the rejection against the compiled receipt validators rather than by
comparing member names.

The same guarantee rests equally on what the three referenced definitions mean.
A digest alphabet that also admits uppercase makes the receipt digest ambiguous
under byte comparison, so two spellings of one artifact stop being one identity;
a path grammar widened by one character stops describing where a published file
may live; and a size range lifted past the safe integer records a size the
protocol's own canonical encoding cannot represent. Each is a one-keyword edit
that leaves the artifact definition, its `$ref` values, and every shipped
positive case untouched, so the gate pins all three structurally and treats its
sampled rejections as a second, deliberately finite check rather than as the
closure. Artifact execution remains a later user action, and the compiled result
remains untrusted package code.
