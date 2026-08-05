# Compiled-build toolchain requirements and preflight

This reference is the extended rationale behind a landed contract. The accepted
design is
[`decisions/0007-compiled-build-toolchain-preflight.md`](../decisions/0007-compiled-build-toolchain-preflight.md),
and the rules below are now normative in
[`protocol/core.md`](../protocol/core.md) section 4.2.3, with the manager
obligations in [`profiles/manager.md`](../profiles/manager.md), the trust
boundary in [`SECURITY.md`](../SECURITY.md), the wire and manager-owned shapes
in [`schemas/v1`](../schemas/v1), and the executable cases in
[`conformance/next`](../conformance/next) — the candidate suite root, because
the surface these cases exercise is minted but not yet released and
[`conformance/v1`](../conformance/v1) is pinned byte-for-byte by an accepted
release document. Where this document and `protocol/core.md` disagree,
`protocol/core.md` is the specification and the disagreement is a defect in this
file, and `tools/validate.py` makes that executable for the `source_ref` surface
token set and both value-classifier tables.

Two places where landing the contract completed it rather than restating it are
called out where they occur: the `source_ref` `surface` token set gains
`registry`, because the registry baseline is a contributing source of the
intersection (section 2.3) and a `requirement_unsatisfiable` conflict payload
has to be able to name the bound that actually failed; and a value classifier's
absence class is marked as matching absence rather than a value, because it
classifies no byte string and therefore does not participate in the section
3.1.1 forbidden-before-compared precedence that the `go` and `toolchain`
classifier tables already declare it ahead of.

Related: [`docs/portable-go-execution-policy.md`](portable-go-execution-policy.md)
for the execution boundary, and
[`docs/external-build-repositories.md`](external-build-repositories.md) for
schema 7 and the neutral descriptor.

## 1. `toolchain-registry-v1`

The registry is manager-owned, exhaustive, and versioned. It is the only
mapping from a driver to a toolchain, and it is never derived from a driver
name, a language name, a file extension, or package data.

Closed toolchain identifiers:

```text
go  rust  swift  kotlin  jdk
```

`jdk` is a companion-only identifier, admissible only if
`TASK-260728-168smo` selects a JVM artifact model. A package MUST NOT name it.

Driver mapping:

| Driver | Primary | Companions | Status |
|---|---|---|---|
| `go-v1` | `go` | none | complete |
| `go-repository-v1` | `go` | none | complete |
| rust local / repository pair | `rust` | none expected | reserved — `TASK-260728-12pnm1` |
| swift local / repository pair | `swift` | to be determined | reserved — `TASK-260728-1yhuqi` |
| kotlin local / repository pair | `kotlin` | `jdk` if JVM | reserved — `TASK-260728-168smo` |

A driver with no registry entry is unsupported and fails
`build_repository_driver_unsupported` (external) or the existing local
unknown-driver rejection. There is no generic mapping and no fallback.

### 1.1 Entry fields

Every entry declares exactly:

| Field | Meaning |
|---|---|
| `toolchain_id` | closed identifier |
| `primary_relpath` | fixed relpath of the primary executable inside the fingerprinted root, per operating system |
| `probe` | the exact package-independent argument vectors used to obtain a version, run from a manager-owned empty working directory under the operation-private environment |
| `normalization` | anchored rule from bounded probe output to the canonical triple plus prerelease flag |
| `fingerprint_algorithm` | `curator-<toolchain_id>-toolchain-v1` |
| `baseline` | requirement applied when no package requirement narrows it |
| `compatibility` | manager-owned closed set of admitted release families, evaluated in addition to the effective requirement |
| `platforms` | closed set of `(operating_system, architecture)` pairs the manager supports |
| `metadata_sources` | the source files and fields cross-checked in stage B |

`operating_system` uses the released claim vocabulary `linux`, `macos`,
`windows`. `architecture` uses `amd64` and `arm64` in v1; each entry defines
the mapping from its own architecture reporting to those tokens.

`primary_relpath` and `probe` are declared **per operating system**, and an
entry is well-formed only when both are declared for every operating system
appearing in its `platforms` set. Neither is declared outside that set, and
neither has a default: on a host whose pair is not in `platforms` there is no
relpath to resolve and no probe to construct. That is a totality obligation on
the registry, not a runtime fallback, and it is why section 4.1 evaluates
host-pair applicability *before* it resolves a relpath or builds a probe. An
entry declaring a relpath or probe for an operating system outside its
`platforms` set is unreachable and fails the same release gate that checks
guidance reachability (section 6.3).

Normalization MUST be anchored, MUST match at most one candidate in bounded
output, MUST be locale-independent, and MUST NOT guess. Ambiguous or unmatched
output is `build_toolchain_version_undetermined`, never a default.

#### 1.1.1 The `compatibility` predicate

`compatibility` is a closed set of release families the manager has tested
against that driver's conformance vectors. It is a REQUIRED entry field, and it
is a manager policy value, never wire data.

- A resolved release version is admitted only when its family is a member.
  Membership is exact set membership, never an ordering test: a family merely
  ordered after a member is not a member.
- Family granularity is declared by the entry. For `go` a family is the pair
  `(major, minor)`; a reserved entry declares its own granularity together with
  the rest of its fields.
- A manager MAY add a family only after testing that family against the
  driver's conformance vectors. It MUST NOT derive membership from version
  ordering, from the effective requirement, from probe output, or from any
  package or repository byte.
- Package data can neither widen nor narrow the set. A version requirement and
  the compatibility set are independent gates: the requirement is the
  package-narrowable one, `compatibility` is the manager-owned one, and passing
  either does not imply the other.
- A resolved version outside the set is `build_toolchain_untested_release`,
  reporting the resolved version and the admitted families.

Because a conforming manager MAY admit more families than another, the set is a
gate rather than a build input, on the same grounds as the effective
requirement (section 4.3). Conformance vectors therefore declare the
compatibility set as fixture input, so a vector outcome is deterministic across
managers.

This preserves, rather than replaces, the released `profiles/manager.md`
section 2.2 rule for Go: a tested 1.23 release family, extension only by
testing, and rejection of a pre-1.23, malformed, package-selected, or otherwise
unknown release including a newer release merely ordered after a known one.

### 1.2 The `go` entry

| Field | Value |
|---|---|
| `toolchain_id` | `go` |
| `primary_relpath` | `bin/go`, `bin/go.exe` on Windows |
| `probe` | the existing section 4.2 bootstrap vectors `go telemetry off`, `go version`, `go env -json GOROOT ...` |
| `normalization` | field 2 of normalized `go version` stdout; `^go(\d+)\.(\d+)(?:\.(\d+))?(.*)$`; absent patch is `0`; non-empty trailing remainder is a prerelease |
| `fingerprint_algorithm` | `curator-go-toolchain-v1`, unchanged |
| `baseline` | `{"kind":"at_least","min":"1.23.0"}` |
| `compatibility` | families `{(1, 23)}`; family granularity `(major, minor)` |
| `platforms` | `(linux, amd64)`, `(linux, arm64)`, `(macos, amd64)`, `(macos, arm64)`, `(windows, amd64)`, `(windows, arm64)` |
| `metadata_sources` | `go.mod` `go` directive; `go.mod` `toolchain` directive |

The entry adds no process invocation: the three vectors already run once per
operation from the manager parent, and `go version` stdout is already the
normalized `V` record of `curator-go-toolchain-v1`. The five Go argument-vector
forms remain exactly five. A `devel` or otherwise unprefixed field 2 is
`build_toolchain_version_undetermined`.

`compatibility` carries the released manager-tested-family rule unchanged. A
resolved Go 1.99.0 satisfies `at_least 1.23.0` and is still rejected, because
`(1, 99)` is not an admitted family. A manager that tests the 1.24 family
against the `go-v1` vectors adds `(1, 24)` to its own set; nothing a package
declares can add it.

### 1.3 Reserved entries

`TASK-260728-12pnm1`, `TASK-260728-1yhuqi`, and `TASK-260728-168smo` MUST each
supply, on a qualified host, every field in section 1.1 — including the
`compatibility` family granularity and its initial tested set — plus its
companion list, and MUST NOT widen section 3, admit a selector, or introduce
auto-install. Their expected metadata sources are:

| Toolchain | Expected metadata sources |
|---|---|
| `rust` | `Cargo.toml` `package.rust-version` / `workspace.package.rust-version`; `rust-toolchain.toml` or `rust-toolchain` |
| `swift` | `Package.swift` `// swift-tools-version:` header; `.swift-version` when present |
| `kotlin` | exactly one file and field, named by the artifact-model decision |
| `jdk` | companion only; no package-visible metadata |

## 2. `toolchain-requirement-v1`

### 2.1 Canonical version

A canonical version is `major.minor.patch`, matching
`^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$` with each component at
most `999999`. No `v`, `go`, or `swift-` prefix, no prerelease, no build
metadata, no leading zeros, no wildcard. Order is lexicographic over the triple.

### 2.2 Requirement object

```json
{"id": "go", "version": {"kind": "at_least", "min": "1.23.0"}}
{"id": "go", "version": {"kind": "range", "min": "1.23.0", "below": "1.25.0"}}
{"id": "go", "version": {"kind": "exact", "equals": "1.23.4"}}
```

`toolchain` contains exactly `id` and `version`. `version` contains exactly
`kind` plus that kind's own fields. `id` MUST equal the driver's registry
primary toolchain; a mismatch is `build_toolchain_requirement_invalid`. For
`range`, `min` MUST be strictly below `below`.

Placement:

- next manifest schema, local build command: `toolchain` is REQUIRED alongside
  `type`, `driver`, `source_dir`;
- next manifest schema, external build command: `toolchain` is REQUIRED
  alongside `type`, `driver`, `repository`, `target`;
- next `skill-build.json` target schema: `toolchain` is OPTIONAL;
- manifest schemas 6 and 7 and descriptor schema 1: no field, baseline applies.

### 2.3 Intervals and intersection

| Kind | Interval |
|---|---|
| `exact` V | `[V, V]` |
| `at_least` V | `[V, +inf)` |
| `range` V, W | `[V, W)` |

Effective requirement = registry baseline ∩ manifest requirement ∩ descriptor
requirement, over the sources present. Intersection takes the maximum lower
bound (always inclusive) and the minimum upper bound, preferring exclusive on a
tie. It is associative and commutative, so source order is irrelevant.

An empty intersection is `build_toolchain_requirement_unsatisfiable`, detected
without probing the host and therefore identical on every machine.

A resolved version satisfies the effective requirement when it is not a
prerelease and lies inside the interval.

Satisfying the effective requirement is necessary and not sufficient. The
entry's `compatibility` set is a separate gate that no intersection participates
in: it is not an interval, it does not combine with the requirement, and a
requirement can neither widen nor narrow it. Section 4.1 fixes the order in
which the two are evaluated.

### 2.4 Prerelease policy

A prerelease host toolchain satisfies nothing:
`build_toolchain_prerelease_unsupported`. A requirement literal can never
express one. This covers Rust nightly and beta, Swift development snapshots,
Go release candidates and betas, and Kotlin `-Beta`/`-RC` builds.

## 3. Trusted resolution

Admissible origins, exhaustively:

1. a toolchain bundled with the manager distribution;
2. trusted operator configuration held in manager-owned, owner-protected state.

Forbidden origins, exhaustively: the ambient or user `PATH`; any package or
repository byte; a runtime root; project `.agents/bin`; any shim; a manifest or
descriptor value; an inherited environment variable, including `GOROOT`,
`RUSTUP_HOME`, `CARGO_HOME`, `RUSTC`, `SWIFT_EXEC`, `TOOLCHAINS`, `JAVA_HOME`,
`KOTLIN_HOME`, and `PATH`; and any version-manager shim or wrapper, including
`rustup`, `asdf`, `mise`, `sdkman`, `swiftly`, and `jenv`. An operator MAY
configure the concrete root that a version manager produced; the manager
resolves that root directly and never through the shim.

The primary executable MUST be a regular executable at the entry's
`primary_relpath` inside the tree being fingerprinted, never a wrapper and
never outside that tree.

**Declaration channels.** The manager looks for a toolchain root in exactly two
channels and in no other place:

| Channel | Content |
|---|---|
| `bundled` | the toolchain roots shipped inside the manager distribution |
| `operator_config` | entries in manager-owned configuration state |

A **declaration** is an entry for a `toolchain_id` in one of these two channels.
The channels are ordered: `operator_config` precedes `bundled`, so an operator
who configures a root overrides the distribution's own, and exactly one entry is
selected for any identifier. Nothing else is a channel. `PATH`, the inherited
environment, shims, runtime roots, project directories, and package or
repository bytes are never searched for a root, so a toolchain reachable only
through one of them is not declared at all — its presence on the host is
invisible to the manager and cannot change any outcome.

A forbidden origin therefore reaches the manager only as the **value of a
channel entry, or as the state holding that entry**: an entry whose value is a
`PATH` lookup rather than a concrete root, an environment-variable reference, a
shim or wrapper path, a runtime or project path, a manifest or descriptor value,
or an `operator_config` state that is not owner-protected.

This is what makes declaration presence and origin admissibility two tests over
two disjoint inputs rather than one test asked twice. Presence reads the channel
map and yields present or absent; admissibility reads the entry that presence
found. Neither can answer the other's question, so no input satisfies both
triggers. Section 4.1 sub-steps 3a and 3b are exactly these two tests.

### 3.1 Two package surfaces, one exclusion rule

Package and repository data reach the manager on two distinct surfaces, and the
exclusion rule reads differently on each. Confusing them is what makes "a
channel is forbidden" and "a channel is compared" look contradictory, so the
split is normative.

**Surface 1 — the manager-defined wire surface**: the manifest build command and
the `skill-build.json` descriptor target. Curator owns these field sets and they
are closed. No field naming an executable path, toolchain root, download URL,
mirror, channel or track, distribution version manager, install or
package-manager command, environment override, `PATH` edit, credential,
keyring, checksum, or trust root exists on this surface, and none may be added.
`toolchain` is exactly `id` and `version` (section 2.2).

Two distinct rejections apply here, and they are partitioned by *what fails*,
never by what a value looks like:

| Input | Rejection |
|---|---|
| a key outside the closed field set | the existing schema rejection: `protocol/core.md` section 4 already requires schemas 2 through 7 to reject unknown fields, and every wire object is `additionalProperties: false`. No `build_toolchain_*` code. |
| a value in a field of the closed set that does not match that field's closed grammar — including a `version` literal carrying a path, prefix, URL, mirror, track, or command | `build_toolchain_requirement_invalid` |

`build_toolchain_package_influence_forbidden` therefore never fires on the wire
surface. That is the partition rule, and it is deliberate: deciding that a
malformed literal is *smuggled influence* rather than merely *malformed*
requires inferring intent from a byte string, and two conforming managers would
infer differently. The canonical version grammar (section 2.1) is closed and
anchored, so `/usr/local/go`, `https://example.test/go.tgz`, `nightly`, and
`go1.23.4` all fail it for one checkable reason — none of them is
`major.minor.patch`. One input, one code, no intent inference.

The closed-field-set constraint is an authoring obligation on this
specification rather than a runtime code, which is what makes it enforceable: no
manifest or descriptor schema version may introduce a field of the kinds listed
above. `TASK-260728-2jaw7h` lands a release gate that enumerates the wire
build-command and descriptor-target property names of every published schema
version and fails on such a name. A runtime diagnostic cannot carry this rule,
because a field that does not exist produces no value to diagnose.

**Surface 2 — source-ecosystem metadata**: files the source ecosystem owns
(`go.mod`, `Cargo.toml`, `rust-toolchain.toml`, the `swift-tools-version`
header, `.swift-version`, the selected Kotlin file), read at Stage B. Curator
does not own these field sets, so each entry declares a closed disposition table
assigning every field it reads exactly one disposition:

| Disposition | Meaning |
|---|---|
| `forbidden` | the field's value is a resolution input — an executable path, toolchain root, URL, mirror, registry, credential, install command, environment override, or trust root. `build_toolchain_package_influence_forbidden`. |
| `compared` | the field's value is a version-domain assertion about the already-resolved toolchain. Compared, then discarded. Never a selector. |
| `ignored` | the field is neither. Read past, never acted on. |

A field not present in the entry's disposition table is `ignored`. A channel- or
track-valued field on this surface is `compared`, never `forbidden`, precisely
because Curator refuses to honor it: reading it as an assertion is what makes it
harmless, while its native ecosystem meaning as a selector is discarded. The
`forbidden` disposition is reserved for values that would name *where* a
toolchain comes from, not *which version* one is claimed to be.

Precedence is fixed so a file carrying both kinds has one deterministic outcome.
Within Stage B for one build command, the manager evaluates every
`forbidden`-disposition field first, then every `compared` field, each group in
Unicode-scalar lexical order of relative source path and then of field path;
the first failure is the reported diagnostic. A `rust-toolchain.toml` carrying
both `path` and `channel = "nightly"` is therefore always
`build_toolchain_package_influence_forbidden`, never
`build_toolchain_metadata_mismatch`.

#### 3.1.1 Value classifiers inside one field

One field can have a value space that spans dispositions. The Go `toolchain`
directive is the concrete case: the same directive holds either a version
assertion, the literal `default`, or a name that identifies a specific toolchain
*distribution*. Splitting such a field across two disposition rows would
misdescribe the file format, so an entry instead declares a **value classifier**
for it — an ordered, exhaustive list of value classes, each class carrying
exactly one disposition and exactly one outcome.

Every class also declares what it matches, because a field can be absent as well
as present and the two are not the same kind of thing:

| `matches` | Meaning |
|---|---|
| `absence` | the class matches the field not being present. It classifies no byte string. |
| `value` | the class matches a byte string the field carries. |

- Classes are matched in declaration order and the first match wins.
- At most one class MUST declare `matches` `absence`, and it MUST be declared
  first. A field is either absent or carries a value, so a second absence class
  could never match and an absence class declared later would be shadowed.
- Every classifier MUST end with a catch-all class, and that class MUST declare
  `matches` `value`, so classification is total: no byte string is left
  unclassified and no value falls through to a default.
- `forbidden` classes MUST be declared before `compared` and `ignored` classes.
  The rule is stated over the `value` classes only: it keeps the section 3.1
  forbidden-before-compared precedence true at the value level exactly as it is
  at the field level, and an `absence` class classifies no byte string, so it
  cannot shadow a `forbidden` one and does not participate. This is why the `go`
  and `toolchain` classifier tables can put their absence class at position 1
  with `forbidden` classes at 2 and 3 without inverting the precedence.
- A classifier MUST consult nothing but the field's own value and the
  already-resolved toolchain version. It never reads the host, the network,
  another file, or another field.

A field carrying a classifier records `classified` in the disposition column,
and its effective disposition for a given value is that of the matched class.

### 3.2 Resolved identity

Resolved identity is `{algorithm, version, primary_relpath, content_sha256}`.
Location is not portable identity. Fingerprinting proves stability across an
operation and identity across operations; it does not prove upstream
authenticity, and v1 verifies no toolchain signature.

## 4. Ordering

### 4.1 Stage A — platform, availability, version

Runs immediately after manifest parsing and build-command validation
(`profiles/manager.md` section 2.1 phase 4), for every distinct toolchain in
the plan, in Unicode-scalar lexical order of toolchain identifier, once per
operation, memoized only in operation-private state. For each toolchain:

1. compute the effective requirement from registry baseline, manifest, and
   descriptor sources available at this point, rejecting an empty intersection;
2. verify the host `(operating_system, architecture)` pair is in the entry's
   `platforms` set; if it is not, `build_toolchain_platform_unsupported` with
   `check` `host_pair`;
3. resolve and verify the toolchain root, in three ordered sub-steps whose
   inputs are disjoint:
   - **3a — declaration presence.** Look up `toolchain_id` in the
     `operator_config` channel and then the `bundled` channel (section 3), and
     select the first entry found. The test is presence and nothing else: it
     does not read an entry's value, its holding state, the host filesystem, or
     the environment, and it therefore cannot judge an origin. If neither
     channel carries an entry, `build_toolchain_unavailable`. This sub-step is
     the *only* producer of that code, and it produces no other.
   - **3b — origin admissibility.** An entry exists; classify **the entry** —
     its value together with the state holding it. If the value names or defers
     to a forbidden origin of section 3 rather than a concrete root — an ambient
     `PATH` lookup, an inherited environment variable, a version-manager shim or
     wrapper path, a runtime root, a project directory, or a manifest,
     descriptor, or package value — or if the `operator_config` state holding it
     is not owner-protected, `build_toolchain_untrusted` with `substep` `origin`
     and the matched `origin_class`. This sub-step reads no filesystem object.
   - **3c — shape.** The entry is admissible and names a concrete root;
     classify **the filesystem object** it denotes. If the declared root does
     not exist, the `primary_relpath` entry is absent, is not a regular file, is
     not executable, resolves outside the fingerprinted tree, or is on disk a
     wrapper or a version-manager shim, `build_toolchain_untrusted` with
     `substep` `shape`.
4. run the entry probe from a manager-owned empty working directory under the
   operation-private environment;
5. normalize to the canonical triple and reject a prerelease;
6. verify the toolchain's own reported host target equals the manager's native
   target — cross-compilation stays forbidden; a difference is
   `build_toolchain_platform_unsupported` with `check` `native_target`;
7. evaluate the effective requirement;
8. evaluate the entry's `compatibility` set.

Steps run in this order and the first failure is the reported diagnostic, so
every gate is deterministic and all remain reachable. A resolved
Go 1.22.0 fails step 7 as `build_toolchain_incompatible`, because it is below
the baseline. A resolved Go 1.99.0 passes step 7 under `at_least 1.23.0` and
fails step 8 as `build_toolchain_untested_release`, because `(1, 99)` is not an
admitted family.

Step 1 precedes step 2 for the same reason it precedes everything else: an empty
intersection is a defect of the manifest, decidable from package and registry
data alone, and it fails identically on every host. Reporting it ahead of the
host-pair check keeps the cheapest and most portable diagnostic first, and it
means an author never sees a platform message for a requirement that no platform
could satisfy.

**Why platform applicability is split, and why its first half is step 2.**
`primary_relpath` and `probe` are declared per operating system and only for the
operating systems in `platforms` (section 1.1). On a host outside that set there
is no relpath to resolve and no probe to run, so a manager that checked
applicability after resolution would have to invent one or fail with an
unrelated code — and `build_toolchain_platform_unsupported` would become
unreachable for exactly the hosts it exists to describe. Step 2 therefore reads
only manager-owned registry data and the host pair: no declaration, no
filesystem, no probe, no package byte. Its outcome is fixed before anything
host-specific is constructed. The second half — reported target versus native
target — necessarily follows the probe, because the probe is what reports the
target; it is step 6. One code covers both halves, and the payload's REQUIRED
`check` member (section 5.1) says which half fired.

Sub-steps 3a through 3c exist to partition a case that otherwise reads as two
codes at once: an operator-configured root whose `primary_relpath` is absent.
The partition is **declaration presence**, not severity, and it is total —
either something was declared or nothing was.

- `build_toolchain_unavailable` means *nothing was declared*, so the remedy is
  to obtain and configure a toolchain. That is why its guidance class is
  `host` (section 6.1).
- `build_toolchain_untrusted` means *something was declared and the declaration
  is not usable*, so the remedy is to correct the operator configuration. That
  is why its guidance class is `configuration`.

A declared-but-broken root is therefore always `build_toolchain_untrusted`,
including when the declared root directory does not exist at all. Routing
"declared but absent on disk" to `unavailable` instead would make the reported
code depend on how far the manager happened to get before failing, which is
exactly the non-determinism this partition removes. `unavailable` never
describes a resolution attempt, and `untrusted` never describes a missing
declaration.

The converse case is fixed by the same partition and is worth stating, because
it is the one a reader is most likely to get backwards. A host that has the
toolchain installed and on `PATH`, with no entry in either channel, is
`build_toolchain_unavailable` from 3a — not `build_toolchain_untrusted`. `PATH`
is not a channel (section 3), so there is nothing for 3a to find and nothing for
3b to classify, and the code does not depend on whether the toolchain happens to
be installed. `build_toolchain_untrusted` from 3b requires a channel entry whose
value defers to `PATH`; that is an operator-configuration defect, which is what
its `configuration` guidance class addresses. The two inputs are different — an
empty channel map versus a channel entry with a `PATH`-deferring value — so
exactly one sub-step fires for each.

Stage A MUST complete before external repository acquisition, before
build-cache lookup, and before any persistent mutation. It reads no package
byte beyond the already-validated manifest.

Tree fingerprinting MAY stay in phase 9 for cost, but MUST cover the same
resolved root, and the version bound into the fingerprint MUST equal the
version Stage A normalized. A difference is `build_toolchain_changed`.

A descriptor requirement is not readable at Stage A for an external command,
because the descriptor arrives with the repository. Stage A therefore gates on
baseline ∩ manifest, and the descriptor requirement joins the intersection at
Stage B. This is the only ordering asymmetry and it is deliberate: the
consuming manifest requirement is REQUIRED precisely so the cheap gate always
has something to evaluate.

Because the descriptor can only *narrow* the interval, Stage A's verdict on the
resolved version is provisional for an external command, and Stage B re-runs
both requirement gates against the narrowed interval before any compiler work
(section 4.2 steps 1 and 2). Stage A's other verdicts are final: the host pair,
the declaration, the probe, the normalized version, the native target, and the
`compatibility` set are all decided from manager-owned data that no descriptor
byte can reach, so none of them is re-evaluated at Stage B.

Failure of any toolchain in the plan fails the operation. Partial installation
of a closure is already forbidden by the journal and rollback rules.

### 4.2 Stage B — source-metadata cross-check

Runs per active build command after local snapshot validation, or after exact
external acquisition and audit (`profiles/manager.md` section 11.6 steps 1
through 6), and before the manager reads an artifact-cache candidate or starts
a compiler child. Its steps are ordered and the first failure is the reported
diagnostic:

1. **re-compute the effective requirement**, now including the descriptor
   requirement, by the section 2.3 intersection. An empty intersection is
   `build_toolchain_requirement_unsatisfiable`;
2. **re-evaluate the resolved version** — the one Stage A normalized, unchanged
   — against that re-computed interval. A resolved version outside it is
   `build_toolchain_incompatible`;
3. **file-shape gate** over each `metadata_sources` file present in the
   validated tree;
4. every `forbidden` disposition and `forbidden` value class;
5. every `compared` disposition and `compared` value class.

Steps 4 and 5 keep the section 3.1 ordering within themselves: each group in
Unicode-scalar lexical order of relative source path and then of field path.

Steps 1 and 2 are what make the descriptor asymmetry safe. Without step 2 a
descriptor could narrow the interval to a non-empty range that excludes the
already-resolved host — say a host at `1.23.0` passing a manifest `at_least
1.23.0` and then meeting a descriptor `at_least 1.24.0` — and nothing would
reject it: step 1 sees a non-empty intersection, and Stage A's step 7 evaluated
a wider interval. `build_toolchain_incompatible` therefore has two firing sites,
Stage A step 7 and Stage B step 2, one per interval it can be evaluated against;
`build_toolchain_requirement_unsatisfiable` likewise fires at validation and at
Stage B step 1. Section 5.1 keys the payload on the firing site, so both remain
representable and unambiguous.

The `compatibility` set is deliberately *not* re-evaluated here. It is
manager-owned, no package or repository byte can widen or narrow it
(section 1.1.1), and the resolved version did not change between the stages, so
its Stage A outcome is already final.

The descriptor's own `toolchain` requirement is validated as part of descriptor
validation inside the acquisition audit, before Stage B runs. A malformed
descriptor requirement is therefore `build_toolchain_requirement_invalid` at the
validation stage, exactly as a malformed manifest requirement is, and that code
keeps its single firing site.

**Step 3 — the file-shape gate.** The manager MUST read an entry's declared
metadata fields through the source ecosystem's own grammar. A
`metadata_sources` file that is present and that the ecosystem's own grammar
rejects — including a directive or key that the ecosystem permits at most once
appearing more than once — is `build_toolchain_metadata_mismatch` with
`assertion` `unclassifiable` and a `source_ref` naming the file, or the field
path when a repeated field is the cause. Files are evaluated in Unicode-scalar
lexical order of relative source path.

The gate precedes steps 4 and 5 by necessity rather than by preference: a field
that cannot be extracted cannot be classified, so there is no forbidden-versus-
compared precedence question to answer for a file that does not parse. It is
also what keeps Stage B implementation-ready — a value the ecosystem itself
rejects gets a typed outcome *here*, before cache lookup and before a compiler
child, instead of being deferred to a compiler error the manager would have to
translate after mutation work had already started.

The gate is about file **syntax** only. It asserts nothing about the semantics
of fields the entry does not read: whether a `require`d module resolves, whether
a declared dependency exists, and every other semantic property remain the
ecosystem's business and are never a `build_toolchain_*` outcome.

Metadata is an assertion about the already-resolved toolchain. It never
selects, downloads, activates, switches, or re-resolves anything. Every field
carries exactly one section 3.1 disposition, and forbidden fields are evaluated
before compared fields.

| Toolchain | Field | Disposition | Rule |
|---|---|---|---|
| `go` | `go.mod` `go` directive | `classified` | section 4.2.2 |
| `go` | `go.mod` `toolchain` directive | `classified` | section 4.2.3 |
| `rust` | `Cargo.toml` `rust-version` | `compared` | above resolved → mismatch |
| `rust` | `rust-toolchain.toml` `channel` | `compared` | see the channel table below |
| `rust` | `rust-toolchain.toml` `components`, `targets`, `profile` | `ignored` | read past |
| `rust` | `rust-toolchain.toml` `path` | `forbidden` | names a toolchain root → package influence |
| `swift` | `// swift-tools-version:` header | `compared` | above resolved → mismatch |
| `swift` | `.swift-version` | `compared` | above resolved, or naming a development snapshot → mismatch |
| `kotlin` | the single selected file and field | `compared` | same shape |

A compared channel- or track-valued field is classified before it is compared:

| Channel value | Outcome |
|---|---|
| a canonicalizable version literal (`1.79`, `1.79.0`; absent patch is `0`) | assertion `at_least` that literal — above resolved → mismatch, at or below → permitted and never honored |
| `stable` | permitted and never honored: it asserts a release toolchain, which section 2.4 already guarantees |
| `beta`, `nightly`, or a dated channel such as `nightly-2026-01-01` | mismatch: it asserts a prerelease host, which v1 never resolves |
| anything else | `build_toolchain_metadata_mismatch`, never a default and never a selector |

`stable` is permitted rather than rejected because it is the ecosystem default
and asserts exactly the property Curator enforces unconditionally; rejecting it
would fail nearly every real package while proving nothing.

#### 4.2.1 Go version literals and canonical comparison

The `go` entry is complete, so its classifiers are exhaustive here and are not
deferred to a driver decision.

Go accepts a directive value through **two layers**, not one, and the layers are
independent. Curator pins both, because either one alone admits values the Go
command cannot use:

| Layer | Artifact | What it decides |
|---|---|---|
| shape | `golang.org/x/mod/modfile` — `GoVersionRE`, `ToolchainRE` | whether `go.mod` parses at all |
| semantic | `internal/gover.Parse`, and `cmd/go/internal/gover.FromToolchain` for a name | whether the Go command can *represent* the value it parsed |

**Upstream acceptance in a position is the conjunction of both layers.** Neither
layer contains the other: the shape layer accepts `1.23.4rc1`, which the
semantic layer cannot represent, and the semantic layer accepts a bare major
`1`, which the shape layer rejects in the `go` directive. A contract written
against the shape layer alone would therefore permit values the Go command
aborts on.

**The semantic layer is representability, and representability is a property of
the value alone.** It is deliberately *not* "the Go command on this host would
succeed". Those differ for one whole region of values: a well-formed future
release such as `go 1.99.0` is represented perfectly by an older toolchain,
which then declines to build it, reporting
`go.mod requires go >= 1.99.0 (running go 1.25.5)`. Upstream reaches that
outcome only after representation — `cmd/go/internal/modload` raises
`*gover.TooNewError` after `modfile.Parse` has returned and
`gover.Compare(f.Go.Version, gover.Local())` has been evaluated — so the value
is inside `Upstream` and the refusal is a *host-version* verdict layered on top.

Curator must not fold that verdict into either grammar layer, because Curator
already reaches the same conclusion by its own rule and at its own firing site:
`go 1.99.0` is class 2 below, its base triple is compared against the resolved
toolchain, it is above, and Stage B reports
`build_toolchain_metadata_mismatch` with a *derived canonical assertion*. Folding
the host relation into the semantic layer would classify the identical fact
twice — once as an ungrammatical value and once as a failed comparison — and the
two answers carry different payloads. One relation, one firing site: grammar
layers decide what the value *is*, and section 4.2.2's comparison decides how it
stands against this host.

The three grammars, writing `INT` for `(0|[1-9][0-9]*)`:

| Grammar | Layer and position | Definition |
|---|---|---|
| `goModVersionShape` | shape, the whole value of the `go` directive | `^([1-9][0-9]*)\.(0\|[1-9][0-9]*)(\.(0\|[1-9][0-9]*))?([a-z]+[0-9]+)?$` |
| `goToolchainNameShape` | shape, the whole value of the `toolchain` directive | `^default$\|^go1($\|\.)` |
| `goSemanticVersion` | semantic, a version wherever upstream must represent one | `^INT(\.INT(\.INT\|[a-z]+(INT)?)?)?$` |

`goModVersionShape` is `modfile.GoVersionRE` verbatim: a nonzero major, a
**required** minor, an optional patch, and an optional prerelease suffix, each
component free of leading zeros. `goToolchainNameShape` is `modfile.ToolchainRE`
verbatim. `goSemanticVersion` is the language accepted by `gover.Parse`: a bare
major is admitted (`gover.Parse("1")` is `1.0.0`), and a prerelease suffix after
an explicit patch is **not**, because upstream rejects `1.21.3rc1` on the stated
grounds that it would order opposite to `1.21 < 1.21rc1`.

Composing them gives the value set each position actually admits:

| Position | Admitted value set |
|---|---|
| `go` directive | `goModVersionShape` ∧ `goSemanticVersion` |
| `toolchain` directive | `goToolchainNameShape` ∧ (`default` ∨ version part ∈ `goSemanticVersion`) |

The `go` row is the correction the two layers force. `goModVersionShape` and
`goSemanticVersion` are *incomparable*: their difference in each direction is
non-empty, so the conjunction is strictly smaller than either. The values in
`goModVersionShape` \ `goSemanticVersion` are exactly those carrying an explicit
patch **and** a prerelease suffix — `1.23.4rc1`, `1.24.0alpha1`, `1.21.3beta2` —
and they are class 4 below, not comparisons.

An admitted value yields a **base triple** — absent minor and patch components
are `0` — and a prerelease flag set by the trailing `[a-z]+` group. Comparison
against the resolved toolchain uses the base triple only, under the canonical
order of section 2.1.

Using the base triple is exact rather than approximate, which matters because
Go's own order is `1.21 < 1.21rc1 < 1.21.0`: a bare language version sorts
*below* its own release candidates. Both canonicalizations — language version
`1.21` to `(1, 21, 0)` and prerelease `1.21rc1` to `(1, 21, 0)` — can differ
from Go's order only for a comparand strictly between `1.21` and `1.21.0`, and
every such value is itself a prerelease. The resolved toolchain is never a
prerelease, because Stage A step 5 rejected one before Stage B ran. The two
orders therefore agree on every comparison Stage B can actually perform.

#### 4.2.1.1 The two alignment properties

Let `Upstream(p)` be the set of values the Go command admits in position `p` by
the conjunction above, and let `C(p)`, `F(p)`, `U(p)` be the values this
contract's classifier for `p` disposes as `compared`, as `forbidden`, and as
unclassifiable. `C`, `F`, `U` partition all strings, because each classifier is
ordered, first-match-wins, and total.

Curator's alignment with Go is **two properties, not one equality**:

- **P1, no widening.** `C(p) ⊆ Upstream(p)`. Every value Curator compares is one
  the Go command can use. This is the property that keeps Stage B meaningful: a
  value outside `Upstream(p)` must not pass as a permitted comparison and reach
  cache lookup and a compiler child, where it becomes a compiler-side failure
  after the manager has already committed to the build.
- **P2, no narrowing outside the security partition.**
  `Upstream(p) \ F(p) ⊆ C(p)`. Every value the Go command accepts and that
  Curator does not classify as package influence is compared, so no Go-valid,
  non-forbidden file is failed for a grammar reason.

Together they give `C(p) = Upstream(p) \ F(p)`.

**`C(p) = Upstream(p)` is false and cannot be repaired, deliberately.** Upstream
accepts custom distribution names such as `go1.21.0-custom` — `FromToolchain`
strips the suffix and documents `FromToolchain("go1.2.3-bigcorp") == "1.2.3"` —
while section 4.2.3 class 3 classifies exactly those as `forbidden`, because the
suffix names *where* a toolchain comes from. The security partition is a
deliberate subtraction from what upstream admits, so any statement asserting set
*equality* with upstream is unsatisfiable. P1 and P2 are stated separately for
that reason, and `F` appears in P2 and in neither side of P1.

`F(p)` is not a subset of `Upstream(p)` either: `toolchain go1.23/../evil` is
class 2 `forbidden` and upstream rejects it as well, for its own reason. So `F`
is bounded by neither property, and both properties remain exact statements
about `C`.

For the `go` directive `F` is empty — that directive's Go-defined value space is
a version and nothing else — so P2 collapses to `C = Upstream` there.

An earlier draft used one wider literal grammar for both directives and argued
that the extra values were harmless because they are assertions rather than
selectors. That is true of *selection* and false of *ordering*, which is what P1
now states: `go 1`, `go 0`, `go 1.023` and `go 1.23.4rc1` all become typed
`build_toolchain_metadata_mismatch` outcomes as `go`-directive class 4, and
`toolchain go1.` and `toolchain go2.0.0` as `toolchain`-directive class 7,
instead of comparisons.

Upstream sources: `go.dev/ref/mod` (`go` and `toolchain` directive grammar),
`go.dev/doc/toolchain` and `go.dev/doc/toolchain#name` (`default`, named
toolchains, and the custom-suffix name contract), and the vendored
`golang.org/x/mod/modfile` `GoVersionRE` and `ToolchainRE` together with
`internal/gover.Parse` and `cmd/go/internal/gover.FromToolchain`.
`FromToolchain` rejects a name containing `/` or `\`, requires the `go` prefix,
strips a custom suffix introduced by `-`, space, or tab, and then requires the
remaining version part to satisfy `gover.Parse`. `modfile` additionally rejects
a repeated `go` or `toolchain` statement as a parse error, which is why both
land in the section 4.2 file-shape gate rather than in a classifier class.

#### 4.2.1.2 The boundary probe

Both layers and both properties are **measured, not asserted**. Fixture-only
vectors cannot establish P1 or P2, because a fixture records what this contract
believes upstream does; only a probe against a real toolchain records what it
does.

The boundary probe MUST, for every value named in sections 4.2.1 through 4.2.3
and for both sides of every boundary they draw:

1. measure the shape layer on its own — for `go.mod`, `go mod edit -json`, which
   parses through `modfile` and stops;
2. measure the semantic layer on its own, **isolated from the running host's
   version**, as detailed below;
3. derive upstream acceptance as the conjunction, and fail if it disagrees with
   the class this contract assigns;
4. evaluate P1 and P2 over the measured verdicts and fail if either is violated,
   and fail if the `forbidden` partition of a position with one does not
   subtract at least one upstream-admitted value.

It MUST run offline — no probe or harness module has a dependency, `GOPROXY` is
off — and MUST NOT require any named toolchain to be installed. It MUST be
re-run against each newly supported Go release family before that family is
added to `compatibility`, since both layers are upstream artifacts that can move
independently.

**Step 2 MUST NOT be an exit code.** The commands that force the go command to
represent a `go` directive value all do so as part of module loading, and module
loading applies the host-version gate of section 4.2.1 in the same step:
`cmd/go/internal/modload` raises `*gover.TooNewError` immediately after
`modfile.Parse` has returned. An exit status therefore answers a strictly
stronger question than this contract asks, and it cannot be decomposed back into
its parts. A probe that reads only the status reports every representable future
release as outside `Upstream` and fails P1 against its own classifier — and it
does so silently, starting on the day the case corpus first names a version
above the runner's.

Step 2 MUST therefore be satisfied by an **isolated measurement**, and SHOULD be
corroborated by a **classified command outcome**:

- *Isolated.* Take the probed toolchain's own `internal/gover` and its own
  `gover.FromToolchain`, from its `GOROOT` and without transcription, build them
  with that same toolchain, and evaluate `gover.IsValid(v)` for a `go`-directive
  value and `v == "default" ∨ FromToolchain(v) ≠ ""` for a `toolchain` name.
  Neither entry point consults the local version, so this measures
  representability and nothing else. The probe MUST record the path and SHA-256
  of each source it lifts, and MUST refuse to run if the lifted `FromToolchain`
  is no longer self-contained, so a future upstream refactor fails the probe
  instead of being quietly worked around.
- *Corroborating.* Run the real command and classify its outcome into **three**
  verdicts — accepted, too-new, rejected — where too-new counts as
  representable. Too-new MUST be recognised structurally rather than by a loose
  message match: upstream renders `TooNewError` as
  `"%v requires go >= %v (running go %v%v)"`, and the probe MUST require the
  echoed version to equal the value under test, which the command can only
  produce by having parsed and compared it.
- **The command classifier MUST be closed and fail-closed.** It has a fourth
  state — *unknown* — which is not a verdict but the absence of one, and an
  outcome that reaches it MUST fail the probe rather than being mapped to any
  verdict. A classifier without that state is open: some branch absorbs the
  outcomes it does not recognise, and whichever verdict that branch names
  becomes an unearned measurement of every failure the command grows later.
- The command MUST be chosen so that exit 0 is itself a measurement. For the
  `toolchain` position the form is `GOTOOLCHAIN=local+path` with `go version`,
  which runs `toolchain.Select` and then prints a string, so its whole failure
  surface is that selection. `go build` is **not** an admissible form here: it
  runs the module loader after selection, and the loader's own failures say
  nothing about the value under test — under it, `toolchain default` and
  `toolchain go1` exit non-zero with `updates to go.mod needed` on a probed
  toolchain, which an open classifier scores as upstream acceptance.
- **A recognised outcome MUST be one whole diagnostic line, matched exactly
  against a form predicted before the command ran.** A lead plus an
  unconstrained tail, or a substring found anywhere in the output, is not one
  outcome but a *family*: it answers for every message upstream might later
  render behind that lead, none of which has been measured. Each expected line
  MUST therefore be constructed from the value under test together with
  constants the probe itself fixes — the module file name as the command renders
  it, the directive's line number in that file, the `GOTOOLCHAIN` setting in
  force, and the probed toolchain's own local version — so that matching is a
  prediction the command meets or fails rather than a search through its output.
  Two recognised forms disagreeing inside one output is not a measurement
  either, and MUST be unknown rather than first-wins.
- The recognised set for the `toolchain` position is exactly the `Select`
  outcomes reachable under that form that quote a name derived from `go.mod`,
  each in upstream's own `%q` rendering: exit 0; `go: cannot find "v" in PATH`,
  the accepting outcome, since the name was represented and then searched for;
  `go: invalid toolchain "v" in go.mod` and `go: invalid GOTOOLCHAIN "v"`, the
  two refusals that precede any search. `Select`'s other `invalid GOTOOLCHAIN
  %q` calls quote the *environment* setting while interpreting it, before
  `go.mod` is read at all; under `GOTOOLCHAIN=local+path` they quote
  `local+path`, and the two that carry a colon-separated tail are unreachable
  for the same reason. They are therefore absent from the set, and an outcome
  carrying that lead MUST be unknown: it is not a statement about the `go.mod`
  name. Admitting the lead plus any tail — as an earlier revision of the probe
  did — reintroduces the defect in the rejection direction.
- The recognised set for the `go` position is exit 0;
  `go: <file> requires go >= v (running go <local>; GOTOOLCHAIN=<setting>)`, the
  too-new form above; `<file>:<line>: invalid go version 'v': must match format
  1.23.0` from `modfile`, naming the value; and the fixed
  `panic: go: internal error: missing go root module` abort that follows a
  `gover.Parse` zero version. Everything else is unknown. The abort is the one
  recognised form that names no value, because it is a fixed internal abort; the
  probe MUST record that exception and MUST NOT extend the exception to any
  value-bearing form.
- The two MUST agree wherever the shape layer accepts the value and the command
  outcome is recognised, and a disagreement MUST fail the probe. Where the shape
  layer rejects the value the command is measuring the conjunction rather than
  the semantic layer, and the comparison is not applicable; where the outcome is
  unknown there is no verdict to compare, and the unknown outcome is the
  reported failure.
- **Closure MUST be measured, not asserted.** The probe MUST include a section
  that classifies outcomes deliberately outside the recognised set and requires
  each to produce no verdict. It MUST cover, at minimum: a real unrelated
  non-zero outcome of a real command in each position; every measured outcome
  classified against every other case's value, excluding only outcomes that name
  no value, which MUST be listed with that reason; and measured recognised
  diagnostics extended the way a later release extends a message — a tail
  appended, a wrapper in front, the line embedded in a longer one.
- **Both laundering directions MUST be covered and reported separately.** A
  fabricated verdict that happens to agree with the isolated measurement makes
  the crosscheck compare equal, so the row goes green for a reason nobody
  measured. Fabricating `accepted` hides behind an isolated-accepted value and
  fabricating `rejected` behind an isolated-rejected one, and neither direction
  is safer than the other. For every fabrication the closure section MUST report
  which of the two it is, and MUST NOT count a fabrication the crosscheck would
  have caught as evidence that the other direction is covered.
- The extended-diagnostic checks are constructed rather than measured, and the
  probe MUST label them as such. That is not a weakness of the method but its
  subject: fail-closedness is a claim about outcomes that do not exist yet, so
  no host can produce them. Taking text upstream did emit and changing it in the
  way a later release would is the honest form of the check; asserting the
  property from the recognised set alone is not a check at all.

The probe run recorded for this contract covers 16 `go`-directive and 13
`toolchain`-directive values on Go 1.25.1 and Go 1.25.5 — 58 measured cases —
plus 331 closure checks per toolchain, with zero divergences, zero
isolated-versus-command disagreements, every command outcome inside the
recognised set, and no outcome outside it producing a verdict. Five measurements
carry the design:

- both toolchains accept `go 1.23.4rc1` at the shape layer, and the command then
  aborts with `panic: go: internal error: missing go root module`, while the
  isolated `gover.Parse` returns the zero version. That is the concrete failure
  P1 exists to prevent, and it is why the `go`-directive classifier is defined
  over the conjunction rather than over `GoVersionRE` alone;
- both toolchains represent `go 1.99.0`, `go 1.26.0` and `go 1.99rc1` — isolated
  verdict valid, command outcome too-new — so all three are inside `Upstream`
  and stay class 2 and class 3 comparisons. The exit-code-only classifier scored
  them as rejected;
- both toolchains represent `toolchain go1.99.0-custom`, which this contract
  nevertheless classifies `forbidden`; that measurement is what makes
  `C = Upstream` unsatisfiable rather than merely unproven;
- under the retired `go build ./...` form, both toolchains exit non-zero on
  `toolchain default` and `toolchain go1` with `updates to go.mod needed` — a
  module-tidiness outcome, not a statement about the name — while the isolated
  measurement represents both. Four of the twenty-six `toolchain` measurements
  therefore reached an open classifier's fall-through branch and were scored as
  upstream acceptance. That measurement is why the command form is narrowed to
  `go version` and why the classifier is required to be closed: the unrecognised
  outcome was not a hypothetical, and neither is the next one;
- on both toolchains, every one of `Select`'s colon-bearing `invalid GOTOOLCHAIN
  %q` diagnostics quotes the environment setting, which the probe fixes at
  `local+path`, so none of them can name a `go.mod` value. A revision that
  nevertheless recognised `invalid GOTOOLCHAIN "v"` plus any tail was therefore
  answering `rejected` for a family no host produces — and, restored as a
  control, it fabricates verdicts on 24 of the 331 closure checks per toolchain
  that the crosscheck cannot catch, in both laundering directions. That is why
  recognition is required to be whole-line and exact rather than lead-based.

Five regression controls MUST remain runnable from the probe itself rather than
from a hand-edited copy of it, and each MUST fail for one named reason:

| Control | Restores | Fails with |
|---|---|---|
| exit-code semantics | the retired step-2 classifier | P1 violated by `1.26.0`, `1.99.0`, `1.99rc1` |
| patch-prerelease compared | the superseded shape-only classifier | P1 violated by `1.23.4rc1`, `1.24.0alpha1`, `1.21.3beta2` |
| `C = Upstream` | custom distributions as ordinary names | the `forbidden` partition no longer subtracts |
| unrelated command failure | the retired `go build ./...` toolchain-position form | unknown command outcome for `default` and `go1` |
| open classifier | the four retired recognition families — two leads, one substring, one lead-and-tail | fabricated verdicts in the closure section, in both laundering directions |

The last two are the closure property's own regression checks, and they are
separate because they fail at different layers. The fourth restores a *command
form* rather than fabricating an error, so the unrelated failure it injects is
one upstream really produces, for two values that are shape-valid and
isolated-representable — the shape of outcome an open classifier turns into an
unearned acceptance. The fifth restores the *recognition* and is the only one
that reaches the rejection direction, because the retired families it brings
back all name `rejected` and therefore hide behind values the isolated
measurement already rejects. Neither control substitutes for the other, and the
control inventory MUST NOT be reduced to one of them.

#### 4.2.2 Classifier — `go.mod` `go` directive

Ordered, first match wins, total:

| # | Class | `matches` | Match | Disposition | Outcome |
|---|---|---|---|---|---|
| 1 | `absent` | `absence` | the directive is not present | `ignored` | no assertion; permitted |
| 2 | `release-literal` | `value` | matches `goModVersionShape` **and** `goSemanticVersion`, with no prerelease group | `compared` | base triple above resolved → `build_toolchain_metadata_mismatch`; at or below → permitted |
| 3 | `prerelease-literal` | `value` | matches `goModVersionShape` **and** `goSemanticVersion`, with a prerelease group | `compared` | same base-triple comparison as class 2 |
| 4 | `unclassifiable` | `value` | anything else — the catch-all | `compared` | `build_toolchain_metadata_mismatch`, `assertion` `unclassifiable` |

Class 1 matches absence, so it classifies no byte string and the section 3.1.1
precedence rule does not reach it; classes 2 through 4 are the value classes and
carry no `forbidden` disposition, because a `go` directive names a version and
never a location.

Classes 2 and 3 are jointly the value set of section 4.2.1's `go` row, so class
4 is exactly its complement: every value the Go command cannot use in this
directive gets one typed outcome here rather than a compiler-side failure later.
Class 4 is reached in two ways, and the second is the one a shape-only reading
misses:

- **the shape layer rejects it** — `go 1` and `go 0` (no minor, or a zero
  major), `go 1.023` (leading zero), `go 1.23rc` (a prerelease letter group with
  no number), `go v1.23` (prefixed), and `go 1.23/4` (a path separator, which is
  not a location under any Go reading of this directive);
- **the shape layer accepts it and the semantic layer cannot represent it** —
  a prerelease suffix after an explicit patch: `go 1.23.4rc1`, `go 1.24.0alpha1`,
  `go 1.21.3beta2`. `modfile.GoVersionRE` matches these, so `go.mod` parses and
  `go mod edit -json` succeeds, but `gover.Parse` returns the zero version and
  the Go command then aborts —
  `panic: go: internal error: missing go root module` on Go 1.25.1 and 1.25.5.
  Curator classifies them here, before cache lookup and before a compiler child.

Both routes carry the same code, the same `assertion` token, and the same Stage
B firing site, so class 4 is one outcome with one payload shape. They are named
separately only because the second is invisible to the shape layer.

The distinction from the section 4.2 file-shape gate is the layer that rejects,
not the severity. A repeated directive or an unparseable file is rejected by the
ecosystem's **file grammar**, yields no value, and is the gate's business. A
value like `go 1.23.4rc1` parses — the file is well-formed and the field
extracts — and is rejected by the ecosystem's **version semantics**, so it is a
classifier case. No value is subject to both.

A **future release is not class 4.** `go 1.99.0` on a host that resolved
`1.23.4` is well-formed in both layers, so it is class 2, and it fails on the
comparison in that class's own outcome column: its base triple is above the
resolved version, and Stage B reports `build_toolchain_metadata_mismatch` with a
derived canonical assertion rather than the `unclassifiable` token. The code is
the same; the payload and the reason are not. Classes 2 and 4 must not be
collapsed here, because the one thing a package author can act on differs — a
class-2 comparison says the host is too old, a class-4 assertion says the file
is not Go-valid at all. This is also the boundary the section 4.2.1.2 probe
isolates: the Go command's own too-new refusal is the ecosystem's version of the
class-2 outcome, and treating it as a grammar rejection would make every
representable future release class 4.

The `go` directive has no `forbidden` class. Its Go-defined value space is a
version and nothing else, so no value of it names *where* a toolchain comes
from, and `go 1.23/4` is class 4 rather than package influence. Stating this
fixes the outcome instead of leaving it to an implementation's analogy with the
`toolchain` directive, and it is why `F` is empty for this position and P2
collapses to `C = Upstream` there.

#### 4.2.3 Classifier — `go.mod` `toolchain` directive

Let `rest` be the value with a leading `go` removed, `v` the maximal prefix of
`rest` containing no `-`, space, or tab, and `suffix` the remainder. This is
upstream's own split.

Ordered, first match wins, total:

| # | Class | `matches` | Match | Disposition | Outcome |
|---|---|---|---|---|---|
| 1 | `absent` | `absence` | the directive is not present | `ignored` | no assertion; permitted |
| 2 | `path-bearing-name` | `value` | the value contains `/` or `\` | `forbidden` | `build_toolchain_package_influence_forbidden` |
| 3 | `custom-distribution-name` | `value` | the value matches `goToolchainNameShape` and `suffix` is non-empty (`go1.23.4-bigcorp`) | `forbidden` | `build_toolchain_package_influence_forbidden` |
| 4 | `default` | `value` | the value is exactly `default` | `compared` | permitted and never honored |
| 5 | `release-name` | `value` | the value matches `goToolchainNameShape` and `v` matches `goSemanticVersion` with no prerelease group | `compared` | base triple above resolved → `build_toolchain_metadata_mismatch`; at or below → permitted and never honored |
| 6 | `prerelease-name` | `value` | as class 5, with a prerelease group (`go1.24rc1`) | `compared` | same base-triple comparison as class 5 |
| 7 | `unclassifiable` | `value` | anything else — the catch-all | `compared` | `build_toolchain_metadata_mismatch`, `assertion` `unclassifiable` |

This is the table the `absence`/`value` distinction is load-bearing for. The
absence class is at position 1 and the two `forbidden` classes are at 2 and 3,
which reads as a violation of the section 3.1.1 forbidden-before-compared rule
until the rule is read over the `value` classes it is stated over. Class 1
matches absence and classifies no byte string, so among the value classes the
`forbidden` ones are still first.

This position composes the same two layers as section 4.2.1, in the same order:
classes 4 through 6 are `goToolchainNameShape` — the shape layer — narrowed by
`goSemanticVersion` on the version part `v` — the semantic layer. Class 7 is the
complement, and like class 4 of the `go` directive it is reached both ways: a
value outside `goToolchainNameShape` (`go2.0.0`, `go1x`, `godefault`, a bare
`1.23.4` with no prefix), and a value inside that shape whose version part fails
`goSemanticVersion` (`go1.` and `go1.99.0rc1x`, where upstream's own
`FromToolchain` returns the empty string and the Go command reports
`invalid toolchain "..." in go.mod`). `go1` is *not* class 7: upstream reads it
as `1.0.0`, so it is class 5 and compares as `(1, 0, 0)`.

Three of these classes decide cases the earlier draft left open, and each
follows from a rule already fixed above rather than from a new judgment.

- **`toolchain default` is permitted and never honored** (class 4). In Go it
  means "use the default toolchain; do not switch", which is exactly and
  unconditionally what Curator does. It is the one metadata value that asserts
  Curator's own behavior, so rejecting it would reject a package for agreeing.
- **A custom-distribution name is package influence** (class 3), not a
  mismatch. The suffix names a specific vendor build — *where* the toolchain
  comes from — which is precisely the boundary section 3.1 reserves `forbidden`
  for, and it is the `go.mod` analogue of `rust-toolchain.toml` `path`. Class 2
  covers the same thing spelled as a path; upstream rejects that spelling too,
  because it would otherwise resolve relative to a directory.
  Class 3 is the whole reason section 4.2.1.1 states P1 and P2 rather than one
  equality: upstream **accepts** `go1.21.0-custom` and Curator refuses it, so
  `C` is strictly smaller than `Upstream` in this position by exactly `F`. Class
  2 shows the converse is not available either — upstream rejects
  `go1.23/../evil` and Curator also classifies it `forbidden` — so `F` is
  neither contained in nor disjoint from `Upstream`, and only `C` is pinned.
- **Classes 2 and 3 precede 4 through 7**, as section 3.1.1 requires, so
  `go1.23.4-bigcorp` is package influence even though its version part would
  compare cleanly, and a path-bearing value never reaches version comparison.

A repeated `go` or `toolchain` directive is not a classifier case at all. Both
classifiers are total over *values*, and a repeated directive is a defect of
*file shape*: upstream `modfile` reports "repeated go statement" and "repeated
toolchain statement" as parse errors, so such a file never yields a value to
classify. It is `build_toolchain_metadata_mismatch` from the section 4.2
file-shape gate, with `assertion` `unclassifiable`. One rule covers both
directives and every other shape defect the ecosystem's grammar rejects, so
Stage B is total over file shapes and over values without either classifier
carrying a shape case.

Absence of `go.mod` itself is not a Stage B failure; a driver that requires the
file rejects it under its own existing rule.

#### 4.2.4 Go metadata sources are closed at two files' worth of fields

The `go` entry's `metadata_sources` are exactly the `go` and `toolchain`
directives of `go.mod`. A `go.work` file in the tree carries the same two
directives, and it is deliberately not a metadata source, because it cannot
affect the build: `protocol/core.md` section 4.2 already fixes `GOWORK=off` in
the operation-private build environment, so a workspace file is inert. Adding it
would create a Stage B rejection for a file the compiler never reads.

The `rust`, `swift`, and `kotlin` rows are the expected dispositions their
reserved entries MUST confirm or correct on a qualified host. The disposition
framework, the precedence rule, and the channel classification above are fixed
here and a driver decision MUST NOT reopen them.

A Stage B classification case is host-independent: it takes the resolved
version as fixture input, so vectors for a reserved toolchain's disposition
table need no toolchain of that language on the runner.

### 4.3 Cache, dry-run, status

Neither stage may be skipped by a cache hit, a dry run, or an offline mode. A
cache hit is only reachable after Stage A and Stage B pass, so no hit can bypass
the effective requirement or the `compatibility` gate.

Two situations are routinely conflated and have different outcomes:

| Situation | Outcome |
|---|---|
| the currently resolved toolchain fails Stage A — unsupported platform, unavailable, untrusted, undetermined, prerelease, outside the effective requirement, or outside `compatibility` | the operation fails at Stage A with the typed code. Cache lookup is never reached, no candidate is consulted, nothing is rebuilt, and no mutation occurs. |
| the resolved toolchain passes Stage A but fails Stage B — a descriptor narrows the requirement past it, or a metadata assertion or forbidden field rejects | the operation fails at Stage B with the typed code, still before the first cache candidate is read and before any compiler child starts. |
| the currently resolved toolchain passes both stages, and a cache candidate was built under a different toolchain identity | the resolved identity is part of the cache key, so the candidate simply does not match: cache miss, rebuild under the current identity. |

There is no "cache hit with an incompatible toolchain" path to rebuild from.
Incompatibility is decided before lookup — at Stage A against the manifest
interval, and at Stage B against the descriptor-narrowed one — while identity
difference is decided by the key. Only the third case produces a rebuild.

Dry-run runs both stages — neither needs a compiler or a mutation — and reports
an affected command as `blocked` with the typed diagnostic, returning failure
and leaving no mutation. `blocked` therefore joins the local dry-run vocabulary
of section 2.4, matching section 11.7. `unsupported` continues to mean an
unknown driver and MUST NOT be reused for a toolchain failure.

Read-only status and audit report a Stage A or Stage B failure as a finding and
MUST NOT mark an otherwise valid marker non-current because of it. Install,
upgrade, repair, and coverage-claiming audit fail before mutation.

## 5. Diagnostics

| Code | Firing site | Trigger |
|---|---|---|
| `build_toolchain_requirement_invalid` | validation | malformed object, unknown identifier, identifier not the driver's primary, a value that does not match its field's closed grammar — including a literal carrying a path, prefix, URL, mirror, track, or command — prerelease literal, `min` not below `below` |
| `build_toolchain_requirement_unsatisfiable` | validation | empty intersection of baseline and manifest requirements |
| | B step 1 | empty intersection once the descriptor requirement joins |
| `build_toolchain_unavailable` | A step 3a | no entry for the identifier in either declaration channel |
| `build_toolchain_untrusted` | A step 3b | the channel entry's value defers to a forbidden origin, or its holding state is not owner-protected |
| | A step 3c | the root the entry names is missing, or its primary is absent, non-regular, non-executable, a wrapper or shim on disk, or outside the fingerprinted tree |
| `build_toolchain_version_undetermined` | A step 4 | probe output unbounded, unmatched, or ambiguous |
| `build_toolchain_prerelease_unsupported` | A step 5 | resolved toolchain is a prerelease, nightly, beta, or development snapshot |
| `build_toolchain_platform_unsupported` | A step 2 | host `(operating_system, architecture)` pair outside `platforms` (`check` `host_pair`) |
| | A step 6 | reported host target differs from the native target (`check` `native_target`) |
| `build_toolchain_incompatible` | A step 7 | resolved release version outside the Stage A effective requirement |
| | B step 2 | resolved release version outside the effective requirement once the descriptor requirement joins |
| `build_toolchain_untested_release` | A step 8 | resolved release family outside the entry's `compatibility` set |
| `build_toolchain_metadata_mismatch` | B step 3 | a `metadata_sources` file the ecosystem's own grammar rejects, including a repeated single-occurrence directive |
| | B step 5 | a `compared` field or value class is incompatible with the resolved toolchain, or is unclassifiable |
| `build_toolchain_package_influence_forbidden` | B step 4 | a `forbidden`-disposition metadata field, or a `forbidden` value class (section 3.1.1), is present in source-ecosystem metadata |
| `build_toolchain_changed` | A, publication | resolved identity or version changed during the operation |

Twelve codes. A code fires at one or more **firing sites**, and every site is a
named step of a named stage, so no site is discretionary and no input reaches
two sites. Four codes have more than one site, and each has a stated reason that
is structural rather than editorial:

- `requirement_unsatisfiable` and `incompatible` each have one site per interval
  they can be evaluated against, because the descriptor requirement is not
  readable at Stage A (section 4.1). Without the Stage B sites a descriptor
  could narrow the interval past the resolved host with nothing to reject it.
- `platform_unsupported` has one site per half of platform applicability: the
  host pair is decidable from registry data before anything host-specific is
  built, the native target is only reported by the probe.
- `metadata_mismatch` has one site for file shape and one for value
  classification, because a file that does not parse yields no value to
  classify. The split is by the ecosystem layer that rejects, not by severity:
  its **file grammar** at B step 3, its **value semantics** at B step 5. A value
  such as `go 1.23.4rc1`, whose file parses and whose field extracts but which
  the Go command cannot represent (section 4.2.1), is therefore a step 5
  outcome, and no input reaches both sites.

Two overlaps a reader can reasonably infer are closed above rather than left to
precedence: a malformed wire value is `requirement_invalid` and never package
influence (section 3.1), and a declared-but-broken toolchain root is `untrusted`
and never `unavailable` (section 4.1). `package_influence_forbidden` is a
Stage B code only, and `unavailable` has exactly one site in the whole
contract.

A code MUST NOT carry prose guidance or a URL of its own; it carries a
`guidance_id`.

### 5.1 Diagnostic payload

The payload is a discriminated union keyed by the **firing site**. Its shape is
not an editorial choice: **a payload carries exactly the values that are
established at the site where it fires**, and because every stage's steps are
totally ordered (sections 4.1 and 4.2), the established set is a function of the
site. Nothing is optional-by-judgment and there are no sentinels.

A firing site is `(code, stage, discriminant)`. `stage` is one of the closed
tokens `validation`, `A`, `B`, `publication`, and a code declares at most one
**discriminant** member — a REQUIRED closed-token member that names which of its
sites within one stage fired. Exactly two codes declare one: `untrusted`
declares `substep`, and `platform_unsupported` declares `check`. Keying on the
site rather than on the code alone is what keeps the union representable now
that four codes fire at more than one site; keying on the code alone would
force the same code to carry different member sets in different stages, which
is the ambiguity this section exists to remove.

Common members, REQUIRED in every payload:

| Member | Value |
|---|---|
| `code` | one of the twelve |
| `stage` | the firing site's stage, one of `validation`, `A`, `B`, `publication` |
| `driver` | the closed driver identifier being planned |
| `toolchain_id` | the registry primary or companion identifier; always known, because the driver is resolved before its requirement is read (section 6.2) |
| `guidance_id` | resolved per section 6.2 |

Conditional members, each present exactly when its establishing step completed
**before** the firing site:

| Member | Establishing step | Value |
|---|---|---|
| `effective_requirement` | the interval computation of the firing site's own stage — A step 1, or B step 1 | the non-empty effective interval that site evaluated against |
| `resolved_version` | A step 5 normalization | canonical triple |
| `prerelease` | A step 5 normalization | boolean |

Applied to the site table above, that is total and needs no per-code judgment:

| Firing site | `effective_requirement` | `resolved_version`, `prerelease` |
|---|---|---|
| `requirement_invalid` @ validation | absent | absent |
| `requirement_unsatisfiable` @ validation | absent | absent |
| `requirement_unsatisfiable` @ B step 1 | absent | present |
| `unavailable` @ A step 3a | present | absent |
| `untrusted` @ A step 3b (`substep` `origin`) | present | absent |
| `untrusted` @ A step 3c (`substep` `shape`) | present | absent |
| `version_undetermined` @ A step 4 | present | absent |
| `platform_unsupported` @ A step 2 (`check` `host_pair`) | present | absent |
| `platform_unsupported` @ A step 6 (`check` `native_target`) | present | present |
| `prerelease_unsupported` @ A step 5 | present | present |
| `incompatible` @ A step 7 | present | present |
| `incompatible` @ B step 2 | present | present |
| `untested_release` @ A step 8 | present | present |
| `metadata_mismatch` @ B step 3, B step 5 | present | present |
| `package_influence_forbidden` @ B step 4 | present | present |
| `changed` @ A, publication | present | present |

`effective_requirement` is absent at exactly the three sites whose own interval
computation had not produced an interval, and `resolved_version` at exactly the
seven sites that precede normalization. The two Stage B sites of `incompatible`
and `requirement_unsatisfiable` differ from their Stage A or validation
counterparts only in that the descriptor requirement is now a contributing
source, which `stage` records and which `fragments` already names for
`unsatisfiable`.

`source_ref` is not conditional on a step. It is `{surface, location}`, where
`surface` is `manifest`, `descriptor`, `registry`, or `source_metadata` and
`location` is a JSON pointer or a relative source path plus a field path, and it
appears exactly where the per-code table below lists it: in `requirement_invalid`,
`metadata_mismatch`, and `package_influence_forbidden`, and once inside each
element of the `requirement_unsatisfiable` `fragments` array. It appears nowhere
else, because no other code is attributable to a single input.

`registry` is in that token set because the registry baseline is a contributing
source of the intersection (section 2.3), so it can be the bound that fails. The
most common unsatisfiable case is a manifest range that falls entirely below the
baseline, and `requirement_unsatisfiable` carries every contributing requirement
as a `fragments` element of `{source_ref, requirement}`. With three tokens the
baseline fragment has no surface to name and the payload cannot say which
requirement it was. `registry` is the only manager-owned token of the four: the
other three locate a package byte, and this one locates a registry entry.

The two bound lists of the `conflict` object are a separate shape and not this
one. Each bound source there is either the literal `registry_baseline` or a
`source_ref`, because a bound achieved by the baseline is achieved by the
registry as a whole rather than at a location inside it.

Per-code extensions:

| Code | Extension members |
|---|---|
| `build_toolchain_requirement_invalid` | `source_ref`; `violation`, one of the closed tokens `not_an_object`, `unknown_id`, `id_not_primary`, `unknown_kind`, `missing_field`, `unexpected_field`, `version_literal_malformed`, `version_literal_prerelease`, `range_bounds_not_ordered` |
| `build_toolchain_requirement_unsatisfiable` | `fragments`: the contributing requirements, each `{source_ref, requirement}`, every one of them already validated; `conflict`: `{lower_bound, lower_sources, upper_bound, upper_sources}` |
| `build_toolchain_unavailable` | none |
| `build_toolchain_untrusted` | `substep`, the discriminant, one of `origin`, `shape`; `origin_class`, one of the closed forbidden-origin tokens of section 3, present exactly for `substep` `origin` |
| `build_toolchain_version_undetermined` | `probe`: which entry probe vector produced the output; `reason`, one of `unmatched`, `ambiguous`, `output_unbounded` |
| `build_toolchain_prerelease_unsupported` | none beyond `resolved_version` and `prerelease` |
| `build_toolchain_platform_unsupported` | `check`, the discriminant, one of `host_pair`, `native_target`; `host_platform`; `supported_platforms` present exactly for `check` `host_pair`; `reported_target` and `native_target` present exactly for `check` `native_target` |
| `build_toolchain_incompatible` | none beyond the common and conditional members |
| `build_toolchain_untested_release` | `admitted_families` |
| `build_toolchain_metadata_mismatch` | `source_ref`; `assertion`, either a canonical requirement derived from the matched value class or the token `unclassifiable` — always `unclassifiable` at the B step 3 file-shape site, because no value was classified |
| `build_toolchain_package_influence_forbidden` | `source_ref`; `value_class`: the matched `forbidden` class name from the entry's disposition table or value classifier |
| `build_toolchain_changed` | `identity_before`, `identity_after` |

`platform_unsupported` previously carried "either `supported_platforms` or
`reported_target` plus `native_target`" with nothing in the payload saying
which. Now that its two halves are separate firing sites (section 4.1), the
`check` discriminant selects the branch, so the choice is derived from the site
rather than left to the emitter — the same construction `untrusted` already uses
for `substep`.

Two rules make the union representable in the two cases that motivated it.

- **`requirement_invalid` fires before a requirement exists**, so it carries no
  requirement. It carries a location and a closed violation token instead. It
  MUST NOT echo the offending value: the payload never reproduces an
  unvalidated package byte, which keeps package-controlled text out of manager
  output and keeps the payload bounded. A location plus a violation token
  identifies the defect exactly, and the authoring guidance for the reason
  explains the grammar.
- **`requirement_unsatisfiable` has no effective interval**, because the
  intersection is empty. It carries the individually valid `fragments` — these
  *are* validated source fragments, so reproducing them is safe — plus the two
  bounds whose ordering failed. `lower_bound` is the maximum lower bound and
  `upper_bound` the minimum upper bound; each is unique, and each names every
  source achieving it, in Unicode-scalar order of `source_ref`. The payload is
  therefore independent of the order in which sources were read, exactly as the
  intersection itself is (section 2.3). This holds identically at both of its
  sites: the B step 1 site simply has a descriptor `fragment` the validation
  site cannot have, and it additionally carries `resolved_version`, because
  Stage A normalized one before Stage B ran.

Every other value the payload carries — probe output classification, resolved
version, admitted families, identities, platform tokens — originates in
manager-trusted data, so the no-echo rule constrains nothing else.

## 6. `toolchain-guidance-catalog-v1`

Manager-owned and versioned. Each entry is
`{guidance_id, toolchain_id, reason, platform, guidance_class, primary_source,
summary, active}` and `superseded_by` when retired.

### 6.1 Total code-to-reason mapping

`reason` is exactly the diagnostic code's `build_toolchain_` suffix. The mapping
is the identity, so it is total by construction and cannot drift as codes are
added: a new code is a new reason, and the release gate below then demands its
entries.

| Diagnostic code | `reason` | `guidance_class` |
|---|---|---|
| `build_toolchain_requirement_invalid` | `requirement_invalid` | `authoring` |
| `build_toolchain_requirement_unsatisfiable` | `requirement_unsatisfiable` | `authoring` |
| `build_toolchain_unavailable` | `unavailable` | `host` |
| `build_toolchain_untrusted` | `untrusted` | `configuration` |
| `build_toolchain_version_undetermined` | `version_undetermined` | `host` |
| `build_toolchain_prerelease_unsupported` | `prerelease_unsupported` | `host` |
| `build_toolchain_platform_unsupported` | `platform_unsupported` | `host` |
| `build_toolchain_incompatible` | `incompatible` | `host` |
| `build_toolchain_untested_release` | `untested_release` | `host` |
| `build_toolchain_metadata_mismatch` | `metadata_mismatch` | `host` |
| `build_toolchain_package_influence_forbidden` | `package_influence_forbidden` | `authoring` |
| `build_toolchain_changed` | `changed` | `configuration` |

`guidance_class` fixes the admissible origin of `primary_source`, which is why
authoring and configuration reasons can carry guidance at all:

| Class | Admissible `primary_source` | Reads as |
|---|---|---|
| `host` | the language's own official origin | install, upgrade, or select a supported release |
| `configuration` | the manager's own operator documentation origin | correct the operator toolchain configuration |
| `authoring` | this specification's own published origin | correct the manifest, descriptor, or source metadata |

In every class `primary_source` is a manager-trusted origin — never a package, a
repository, a mirror, a third-party installer script, or a command the manager
runs. Guidance is text plus URL only.

`guidance_class` classifies the **origin of the guidance**, not who must act.
That is what lets one class serve a reason whose remedy can sit on either side.
`metadata_mismatch` is `host` because every one of its sites — a version
assertion above the resolved toolchain, an unclassifiable value, a file the
ecosystem's own grammar rejects — is documented at the language's own official
origin, which is where a reader has to go whether the fix is a newer toolchain
or a corrected directive. The payload is what localizes the defect: `source_ref`
names the file and field, and `assertion` distinguishes a derived comparison
from the `unclassifiable` token.

### 6.2 Identifier grammar and lifecycle

```text
toolchain.<toolchain_id>.<reason>.<platform>.r<N>
```

`platform` is `linux`, `macos`, `windows`, or `any`. `N` is a decimal revision
with no leading zeros, starting at `1` and strictly increasing per
`(toolchain_id, reason, platform)` tuple. The revision component is what makes
the lifecycle implementable: the tuple alone cannot name two entries, so without
it `superseded_by` has no distinct identifier to point at.

- A published `guidance_id` is immutable. Its `summary`, `primary_source`, and
  `guidance_class` never change after publication.
- Any change of meaning, of `primary_source` origin, or of class is a new entry
  at the next revision of the same tuple. The old entry sets `active: false` and
  `superseded_by` to the new identifier.
- `superseded_by` MUST name an existing entry with the same
  `(toolchain_id, reason, platform)` tuple and a strictly greater revision, so
  the supersession chain is acyclic and terminates at the single active entry.
- At most one entry per tuple is `active`. Retired entries are retained, never
  deleted, so an older diagnostic's identifier stays resolvable.

#### 6.2.1 Catalog versions and the transitions between them

"Append-only" and "retirement flips `active`" are only compatible if it is
stated *when* each applies, so both are fixed against the catalog version.

A published catalog version is **immutable in whole**. No entry in it is added,
removed, or edited after publication — including `active` and `superseded_by`.
The catalog version advances with the specification release, and every change is
a transition from version N to version N+1.

From N to N+1, exactly these transitions are admissible:

| Transition | Rule |
|---|---|
| carry forward | an entry present in N is present in N+1 with identical `guidance_id`, `toolchain_id`, `reason`, `platform`, `guidance_class`, `primary_source`, and `summary` |
| add | N+1 may add the next revision of an existing tuple, or revision `1` of a tuple absent from N |
| retire with a successor | an entry `active` in N may be `active: false` in N+1 **iff** N+1 contains an entry of the same tuple at a strictly greater revision, and the retired entry's `superseded_by` names it |
| retire without a successor | an entry `active` in N may be `active: false` in N+1 with `superseded_by` absent **iff** its tuple is not required by the section 6.3 coverage gate in N+1 — the only cause being that the tuple's platform or toolchain left the registry |

And exactly these are inadmissible: removing an entry present in N; changing any
immutable member of a carried-forward entry; reactivating an entry that is
`active: false` in N; setting or changing `superseded_by` on an entry that is
`active` in N+1; and retiring the last active entry of a tuple the gate still
requires.

The entry set is therefore append-only across versions, and `active` and
`superseded_by` are one-way monotone: `true` to `false`, absent to set, never
back. That is the precise sense in which the catalog is append-only, and it is
what the release gate checks.

Selection resolves the *tuple*, not the identifier: exact
`(toolchain_id, reason, platform)` active entry, else the `(toolchain_id,
reason, any)` active entry. The emitted diagnostic carries the resolved
identifier including its revision.

Selection always has a `toolchain_id` to key on, including for a
`build_toolchain_requirement_invalid` whose declared `id` is absent or outside
the closed set: the diagnostic resolves guidance under the **driver's registry
primary toolchain**, which is known because the driver was resolved before its
requirement was read. A driver with no registry entry never reaches a
`build_toolchain_*` code at all — it is the existing unknown-driver rejection.

### 6.3 Coverage modes and the totality gate

The catalog MUST be total over supported toolchains × all twelve reasons ×
supported platforms, where a supported toolchain is one with a complete registry
entry.

Coverage is defined by the selection function of section 6.2 rather than
alongside it, which is what removes the earlier ambiguity between "one `any`
entry" and "one entry per operating system". For a `(toolchain_id, reason)`
pair, an active exact-platform entry covers that operating system, and an
active `any` entry covers every operating system not covered by an exact entry.
Three coverage shapes therefore exist, and **all three are valid**:

| Mode | Shape |
|---|---|
| `any` | one active `any` entry, no active exact entries |
| `per_os` | one active exact entry for every operating system in the toolchain's registry `platforms`, no active `any` entry |
| hybrid | one active `any` entry plus active exact entries for some, but not all, of those operating systems |

Hybrid coverage is admitted because selection already defines it: exact wins,
`any` is the fallback. Forbidding it would reject a catalog that resolves every
request deterministically, and forcing `per_os` duplication for one
platform-specific note is how catalogs go stale.

The release gate checks exactly two properties over each
`(toolchain_id, reason)` pair, plus the lifecycle rules:

1. **Resolution** — every operating system in that toolchain's registry
   `platforms` set resolves, through the section 6.2 selection function, to
   exactly one active entry.
2. **Reachability** — every active entry is reachable by some request. An
   active exact entry whose platform is not in the registry `platforms` set is
   unreachable and fails the gate. An active `any` entry that is shadowed by
   active exact entries for *every* operating system in that set is likewise
   unreachable and fails the gate.

Reachability is what keeps hybrid coverage honest: it admits a fallback plus
overrides, and rejects both dead entries and a fallback that can never be
selected. Together the two properties are exactly "every request resolves and
every entry serves a request".

The gate additionally checks revision monotonicity per tuple, `superseded_by`
well-formedness (same tuple, strictly greater revision, existing target), that
no tuple has two active entries, and every version-transition rule of section
6.2.1. There is therefore no runtime guidance-missing case for any diagnostic. A
driver decision that completes a reserved entry lands that toolchain's catalog
rows in the same change, because the gate starts demanding them the moment the
entry is complete.

The same gate applies the two properties to the **registry** as well, over each
complete entry's per-operating-system `primary_relpath` and `probe` (section
1.1): every operating system in that entry's `platforms` set resolves to exactly
one declared relpath and one declared probe, and a relpath or probe declared for
an operating system outside that set is unreachable and fails. That is what
makes the Stage A step 2 host-pair check total — every host the manager reaches
past step 2 has a relpath and a probe by construction, and no host outside
`platforms` has one to resolve.

The catalog is not a cache, receipt, marker, or claim input, so correcting a URL
or publishing a new revision never invalidates an artifact.

`TASK-260728-ypbuav` owns catalog maintenance under these rules.

## 7. No auto-install

v1 never downloads, installs, updates, activates, or switches a toolchain, and
specifically not through `rustup`, `swiftly`, `sdkman`, `asdf`, `mise`,
Homebrew, `winget`, the Gradle wrapper, or `GOTOOLCHAIN`. A missing or
incompatible toolchain is an installation error with a typed code and a
guidance identifier. Introducing auto-install requires a new decision, a new
trust model for installer code, and its own review.

## 8. Vector inventory

`TASK-260728-2jaw7h` MUST land at least these cases. Every case declares the
manager's `compatibility` set and, where relevant, the resolved version as
fixture input, so outcomes are deterministic across conforming managers and
across runners without a given language toolchain installed.

Positive:

1. schema 6 local `go-v1` command with no requirement, baseline satisfied,
   family admitted;
2. schema 7 external `go-repository-v1` command with no requirement, baseline
   satisfied;
3. next-schema command with `at_least` satisfied exactly at the bound;
4. next-schema command with `range` satisfied strictly inside;
5. next-schema command with `exact` satisfied;
6. manifest and descriptor requirements intersecting to a non-empty interval,
   resolved version inside it;
7. **compatibility preserve** — resolved version satisfies the effective
   requirement and its family is in the manager's set, so the build proceeds;
8. `go.mod` `go` directive a release literal strictly below the resolved
   version;
9. **language-version canonicalization** — `go.mod` `go 1.23` against resolved
   `1.23.0`, permitted, showing `(1, 23, 0)` and Go's own `1.23 < 1.23.0` agree
   whenever the comparand is a release;
10. `go.mod` `go` directive a prerelease literal (`1.23rc1`) whose base triple
    is at or below resolved, permitted;
11. `go.mod` `toolchain` a canonical release name at or below resolved,
    permitted and not honored;
12. **`toolchain default`** — permitted and not honored;
13. `go.mod` `toolchain` a prerelease name (`go1.23rc1`) whose base triple is at
    or below resolved, permitted and not honored;
14. `go.mod` with no `toolchain` directive — no assertion, permitted;
15. `rust-toolchain.toml` `channel = "stable"`, permitted and never honored;
16. `rust-toolchain.toml` `channel` a version literal at or below the resolved
    version, permitted and never honored;
17. two commands in one plan on the same toolchain, probed once;
18. cache hit reachable only after both stages pass;
19. **cache miss by identity** — both stages pass on a compatible current
    toolchain, and the cache candidate was built under a different toolchain
    identity, so the key does not match and the command rebuilds under the
    current identity.

Negative — requirement and wire surface. Cases 27 and 28 belong to the manifest
and descriptor schema suites rather than the toolchain suite, because a field
outside the closed set never reaches a `build_toolchain_*` code:

20. malformed requirement object; 21. identifier not the driver's primary;
22. prerelease literal in a requirement; 23. `min` not below `below`;
24. **wire overlap** — `version` literal carrying an executable path, reported
`build_toolchain_requirement_invalid` and explicitly not
`build_toolchain_package_influence_forbidden`;
25. `version` literal carrying a URL, same code; 26. `version` literal carrying
a track such as `nightly`, same code;
27. manifest build command carrying an added field naming a toolchain path,
rejected by the closed schema with no `build_toolchain_*` code;
28. descriptor target carrying an added field of the same kind, same rejection;
29. empty intersection.

Negative — Stage A. Cases 33 and 34 are the availability/trust overlap:

30. no entry for the identifier in either declaration channel, reported
`build_toolchain_unavailable` from sub-step 3a; 31. an `operator_config` entry
whose value defers to a `PATH` lookup rather than naming a concrete root,
reported `build_toolchain_untrusted` from 3b with the `PATH` `origin_class`;
32. an `operator_config` entry naming a version-manager shim path, same code and
sub-step;
33. **declared root absent on disk** — trusted declaration, root directory does
not exist, reported `build_toolchain_untrusted` from 3c and explicitly not
`build_toolchain_unavailable`;
34. **declared primary absent** — trusted declaration, root present,
`primary_relpath` missing, same code and sub-step;
35. primary executable outside the fingerprinted tree; 36. unparseable probe
output; 37. `devel` Go version; 38. prerelease host; 39. unsupported
`(operating_system, architecture)` pair; 40. reported host target differing from
the native target; 41. resolved version below `min`; 42. resolved version at
`below`;
43. **compatibility reject** — resolved Go `1.99.0` satisfying `at_least 1.23.0`
with `(1, 99)` outside the manager's set, rejected
`build_toolchain_untested_release`, proving `at_least` alone admits nothing;
44. **gate precedence** — resolved Go `1.22.0`, reported
`build_toolchain_incompatible` from step 7 and not
`build_toolchain_untested_release`, although both gates would reject it.

Negative — Stage B, Go classifiers (sections 4.2.2 and 4.2.3), one per class
and per class boundary:

45. `go` directive release literal above resolved; 46. `go` directive
unclassifiable literal; 47. **classifier boundary** — `go` directive value
containing a path separator, reported `build_toolchain_metadata_mismatch` as
class 4 and explicitly not package influence, because that directive has no
`forbidden` class; 48. `toolchain` canonical release name above resolved;
49. `toolchain` prerelease name whose base triple is above resolved;
50. **custom distribution** — `toolchain go1.23.4-bigcorp`, reported
`build_toolchain_package_influence_forbidden`;
51. `toolchain` value containing `/`, same code; 52. `toolchain` value with no
`go` prefix and not `default`, reported `build_toolchain_metadata_mismatch`;
53. a repeated `toolchain` directive in one file, reported
`build_toolchain_metadata_mismatch` from the **B step 3 file-shape gate** with
`assertion` `unclassifiable`, and explicitly not from a classifier class;
54. **value-class precedence** — `toolchain go1.99.0-bigcorp`, whose version
part would compare cleanly, reported
`build_toolchain_package_influence_forbidden` because a `forbidden` class is
matched first.

Negative — Stage B, other metadata, ordering, and cache:

55. `rust-toolchain.toml` `channel = "nightly"`; 56. `channel` a dated
`nightly-YYYY-MM-DD`; 57. `channel = "beta"`; 58. `channel` unclassifiable as
either a version literal or a known track; 59. `rust-toolchain.toml` with
`path`;
60. **disposition precedence** — `rust-toolchain.toml` carrying both `path` and
`channel = "nightly"`, reported `build_toolchain_package_influence_forbidden`
and not `build_toolchain_metadata_mismatch`;
61. toolchain tree changed between Stage A and fingerprinting;
62. external command failing Stage A with no acquisition performed;
63. **fail-fast before lookup** — the current resolved toolchain fails Stage A,
so the operation fails there with no cache lookup, no candidate consulted, no
rebuild, and no mutation; 64. dry-run reporting `blocked` rather than
`unsupported`.

Diagnostic payload shape (section 5.1):

65. `build_toolchain_requirement_invalid` carries `source_ref` and a closed
    `violation` token, carries neither `effective_requirement` nor
    `resolved_version`, and does not reproduce the offending value;
66. `build_toolchain_requirement_unsatisfiable` carries validated `fragments`
    and the conflicting bounds, carries no `effective_requirement`, and is
    byte-identical under a reordered source list;
67. `build_toolchain_unavailable` carries `effective_requirement` and no
    `resolved_version`;
68. `build_toolchain_prerelease_unsupported` carries `resolved_version` and
    `prerelease`;
69. `build_toolchain_untested_release` carries `admitted_families`;
70. `build_toolchain_metadata_mismatch` carries `source_ref` plus either a
    derived canonical assertion or the `unclassifiable` token;
71. `build_toolchain_untrusted` carries `substep`, and `origin_class` exactly
    for the `origin` sub-step.

Guidance catalog:

72. every one of the twelve reasons resolves to an active entry for every
    supported toolchain and platform;
73. a catalog missing one reason for one supported toolchain fails the release
    gate;
74. two active entries for one `(toolchain_id, reason, platform)` tuple fail the
    gate;
75. `superseded_by` naming a lower, equal, or non-existent revision fails the
    gate;
76. `superseded_by` naming a different tuple fails the gate;
77. a superseded entry stays resolvable while selection returns the active
    revision;
78. each of the twelve codes emits a `guidance_id` whose revision component is
    present and whose entry is active;
79. **`any` mode** — one active `any` entry and no exact entries passes;
80. **`per_os` mode** — one active exact entry per registry operating system and
    no `any` entry passes;
81. **hybrid coverage** — an active `any` entry plus an exact override for one
    operating system passes, and the overridden system resolves to the exact
    entry while the others resolve to `any`;
82. **unreachable fallback** — an active `any` entry shadowed by active exact
    entries for every registry operating system fails the gate;
83. **unreachable override** — an active exact entry for an operating system
    outside the toolchain's registry `platforms` fails the gate;
84. an operating system with neither an exact nor an `any` entry fails the gate;
84a. **registry relpath resolution** — a complete entry missing a
    `primary_relpath` or a `probe` for an operating system in its `platforms`
    set fails the gate;
84b. **registry relpath reachability** — a complete entry declaring a
    `primary_relpath` or a `probe` for an operating system outside its
    `platforms` set fails the gate.

Catalog version transitions (section 6.2.1):

85. retire with a successor across versions passes;
86. retire without a successor passes only when the tuple is no longer required
    by the coverage gate;
87. an entry present in version N and absent from N+1 fails;
88. a carried-forward entry whose `summary`, `primary_source`, or
    `guidance_class` differs from N fails;
89. an entry `active: false` in N and `active: true` in N+1 fails;
90. any edit inside an already-published catalog version fails.

Identity guards:

91. `curator-go-toolchain-v1` bytes unchanged; 92. rc.4 byte-frozen digests
unchanged; 93. a requirement change alone producing an identical cache key;
94. a `compatibility`-set change alone producing an identical cache key;
95. a catalog `primary_source` or revision change alone producing an identical
cache key.

Stage A step ordering — platform applicability (section 4.1 steps 2 and 6). Each
case asserts both the reported code and that no later step ran:

96. **unsupported operating system** — host pair `(freebsd, amd64)` against the
    `go` entry's `platforms`, reported `build_toolchain_platform_unsupported`
    with `check` `host_pair`, with no declaration channel consulted, no relpath
    resolved, and no probe executed;
97. **unsupported architecture on a supported operating system** — host pair
    `(linux, riscv64)`, same code, same `check`, same non-execution assertions;
98. **applicability precedes availability** — an unsupported host pair *and* no
    entry in either declaration channel, reported
    `build_toolchain_platform_unsupported` from step 2 and explicitly not
    `build_toolchain_unavailable`, because step 2 precedes 3a;
99. **applicability precedes trust** — an unsupported host pair *and* an
    `operator_config` entry deferring to `PATH`, same code from step 2 and
    explicitly not `build_toolchain_untrusted`;
100. **`host_pair` payload** — carries `check` `host_pair`, `host_platform`, and
    `supported_platforms`, carries `effective_requirement`, and carries neither
    `resolved_version` nor `prerelease` nor `reported_target`;
101. **`native_target` payload** — the case-40 host, carrying `check`
    `native_target`, `host_platform`, `reported_target`, `native_target`, and
    `resolved_version`, and no `supported_platforms`.

Stage A declaration-channel partition (section 3, section 4.1 sub-steps 3a
and 3b). The overlap case follows the algorithm text literally:

102. **installed on `PATH`, declared nowhere** — the toolchain is present on the
    host `PATH` and neither the `bundled` nor the `operator_config` channel
    carries an entry for the identifier, reported `build_toolchain_unavailable`
    from 3a and explicitly not `build_toolchain_untrusted`, with no origin
    classification performed;
103. **declared nowhere, absent from the host entirely** — same channels, same
    code and sub-step, proving the outcome does not depend on what is installed;
104. **`bundled` and `operator_config` both empty for one identifier while
    another identifier in the same plan resolves** — the failing identifier is
    `unavailable`, and the reported code is per identifier;
105. **origin classification reads only the entry** — an `operator_config` entry
    naming a `GOROOT` environment reference, reported `untrusted` from 3b with
    the environment-variable `origin_class`, asserted without any filesystem
    access;
106. **shape classification reads only the filesystem** — an admissible entry
    naming a concrete root whose primary is on disk a shim script, reported
    `untrusted` from 3c with `substep` `shape` and no `origin_class`.

Stage B late requirement narrowing (section 4.2 steps 1 and 2). All are external
`go-repository-v1` commands whose descriptor is unreadable at Stage A:

107. **non-empty late intersection excluding the resolved host** — resolved
    `1.23.0`, manifest `at_least 1.23.0`, descriptor `at_least 1.24.0`;
    Stage A passes, and Stage B step 2 reports
    `build_toolchain_incompatible` with `stage` `B`, carrying the re-computed
    `effective_requirement` `[1.24.0, +inf)` and `resolved_version` `1.23.0`,
    before any artifact-cache candidate is read and before any compiler child
    starts;
108. **empty late intersection** — manifest `range [1.23.0, 1.25.0)` and
    descriptor `exact 1.26.0`; Stage A passes and Stage B step 1 reports
    `build_toolchain_requirement_unsatisfiable` with `stage` `B`, carrying
    `fragments` including the descriptor fragment plus `resolved_version`, and
    no `effective_requirement`;
109. **late narrowing that still admits the host** — descriptor `at_least
    1.23.0` against resolved `1.23.4`, both Stage B steps pass and the command
    proceeds;
110. **step 1 precedes step 2** — an empty late intersection on a host that
    would also fail step 2, reported `requirement_unsatisfiable` and not
    `incompatible`;
111. **requirement gates precede metadata work** — a late intersection excluding
    the resolved host in a tree that also carries a `rust-toolchain.toml`
    `path`-equivalent forbidden field, reported `build_toolchain_incompatible`
    from step 2 and not `build_toolchain_package_influence_forbidden`;
112. **`compatibility` is not re-evaluated at Stage B** — a descriptor
    requirement that narrows the interval cannot change the Stage A
    `compatibility` verdict,
    and a command whose family was admitted at Stage A is never reported
    `build_toolchain_untested_release` from Stage B;
113. **local commands are unaffected** — a local `go-v1` command has no
    descriptor, so its Stage B step 1 interval equals its Stage A interval and
    step 2 cannot newly fail.

Stage B file-shape gate and upstream Go grammar alignment (sections 4.2, 4.2.1
through 4.2.3). Every case asserts the outcome is produced before cache lookup
and before a compiler child:

114. **repeated `go` directive** — `build_toolchain_metadata_mismatch` from the
    B step 3 file-shape gate with `assertion` `unclassifiable`;
115. **repeated `toolchain` directive** — same site, same assertion, matching
    case 53;
116. **unparseable `go.mod`** — same site and assertion;
117. **shape gate precedes disposition evaluation** — a `go.mod` that fails to
    parse in a tree that also carries a `forbidden` metadata field, reported
    `metadata_mismatch` from step 3 and not
    `build_toolchain_package_influence_forbidden`;
118. **`go 1`** — no minor component, rejected by the shape layer
    (`goModVersionShape`) although `goSemanticVersion` would admit it, reported
    `metadata_mismatch` as `go`-directive class 4 rather than permitted as a
    comparison; this is the shape-narrower-than-semantic half of the boundary,
    as case 122 is the semantic-narrower-than-shape half;
119. **`go 0`** — zero major, same code and class;
120. **`go 1.023`** — leading zero in a component, same code and class;
121. **`go 1.23rc`** — prerelease letters with no number, same code and class;
122. **`go 1.23.4rc1`** — matches `goModVersionShape` and so parses, but is
    outside `goSemanticVersion`; reported `metadata_mismatch` as `go`-directive
    class 4 with `assertion` `unclassifiable`, and explicitly **not** permitted
    as a class-3 comparison against a resolved `1.23.4`. The case asserts the
    outcome is produced at Stage B step 5, before cache lookup and before a
    compiler child;
122a. **`go 1.24.0alpha1`** — same boundary with the `alpha` kind, same code,
    class, and assertion;
122b. **`go 1.21.3beta2`** — same boundary with the `beta` kind, same code,
    class, and assertion;
122c. **layer attribution** — `go 1.23.4rc1` and a repeated `go` directive in
    the same suite report the same code with the same `assertion`, from
    **different firing sites**: the repeated directive from the B step 3
    file-shape gate, the patch-prerelease value from the B step 5 classifier,
    because its file parses and its field extracts;
122d. **`go 1.23rc1` stays permitted** — a prerelease after a minor with no
    patch is inside both layers, so it remains class 3 and is compared by base
    triple, proving 122 narrows only the patch-prerelease region;
122e. **future release is a comparison, not a grammar failure** — `go 1.99.0`
    against a resolved `1.23.4`: inside both layers, classified class 2, and
    reported `build_toolchain_metadata_mismatch` carrying a **derived canonical
    assertion** `(1, 99, 0)` and explicitly **not** the `unclassifiable` token
    that case 122 requires. The case pins that a representable value above the
    host fails on the section 4.2.2 comparison and never on the section 4.2.1
    grammar;
122f. **future prerelease, same route** — `go 1.99rc1` against the same resolved
    version, class 3, same code, same derived assertion, distinguishing it from
    122a and 122b, which are the same shape of literal in the unrepresentable
    region;
122g. **a future release below the host is permitted** — `go 1.26.0` against a
    resolved `1.26.1`, class 2, permitted, proving 122e turns on the comparison
    and not on the value being newer than any particular runner;
123. **`toolchain go1`** — accepted by upstream as `1.0.0`, classified as class
    5 and compared as `(1, 0, 0)`, permitted and never honored, and explicitly
    not unclassifiable;
124. **`toolchain go1.`** — inside `goToolchainNameShape` but rejected by
    `goSemanticVersion`, reported `metadata_mismatch` as class 7;
124a. **`toolchain go1.99.0rc1x`** — same boundary, same code and class;
125. **`toolchain go2.0.0`** — outside `goToolchainNameShape`, same code and
    class;
126. **P1, no widening** — for both directives, every value the suite classifies
    as a permitted comparison is a value the Go command admits in that position
    under the section 4.2.1 conjunction of the shape and semantic layers. The
    fixture table carries both layers' verdicts per value, so a case that
    matches only the shape layer fails the property;
126a. **P2, no narrowing outside the security partition** — for both directives,
    every value the Go command admits and that the classifier does not dispose
    `forbidden` is classified as a comparison. `go1.21.0-custom` is admitted
    upstream and disposed `forbidden`, so it is excluded from this property and
    is *not* required to be compared;
126b. **the security partition genuinely subtracts** — `toolchain
    go1.21.0-custom` is asserted to be both upstream-admitted and
    `build_toolchain_package_influence_forbidden`, which is what makes
    `C = Upstream` unsatisfiable and P1 and P2 separate properties rather than
    one equality;
126c. **the security partition is not bounded by upstream either** — `toolchain
    go1.23/../evil` is asserted to be upstream-rejected and also
    `build_toolchain_package_influence_forbidden`, so `F` is neither a subset of
    nor disjoint from the upstream-admitted set, and only the `compared`
    partition is pinned to upstream;
126d. **empty `F` for the `go` directive** — the suite asserts that no
    `go`-directive value is disposed `forbidden`, so P2 collapses to
    `C = Upstream` at that position and case 47's path-separator value is
    covered by class 4.

Cases 126 through 126d are fixture assertions about *this contract's* partition.
They are necessary and not sufficient, because their upstream column is authored
rather than observed. The section 4.2.1.2 boundary probe supplies the observed
column and is a separate obligation:

127. **boundary probe** — an executable check meeting section 4.2.1.2, run
    against at least one real Go toolchain of each family in the manager's
    `compatibility` set, measuring the shape and semantic layers independently
    per value, failing on any disagreement with the classifier tables and on any
    violation of P1 or P2. Its recorded output is the evidence for cases 126
    through 126d; a fixture table that disagrees with a probe run is a defect in
    the fixture, not in the probe;
127a. **the semantic measurement is isolated from the host version** — the probe
    carries at least one value inside both layers and above the runner's own
    release, measures it representable, and records the real command's outcome
    as too-new rather than as a rejection. A probe whose step-2 verdict is a bare
    exit status does not satisfy case 127;
127b. **the isolated and command measurements agree** — for every value the shape
    layer accepts and whose command outcome is recognised, the probe compares its
    isolated verdict against the classified command outcome and fails on any
    disagreement, so neither measurement can drift alone;
127c. **the command classifier is closed** — every command outcome falls inside
    the recognised set of section 4.2.1.2, and an outcome outside it fails the
    probe instead of being mapped to a verdict. A probe whose classifier has a
    fall-through branch that names a verdict does not satisfy case 127, since
    that branch measures nothing and would absorb any acceptance or rejection
    layer upstream adds later;
127d. **regression controls** — the five superseded classifications, command
    forms and recognition families of section 4.2.1.2 are runnable from the
    probe binary and each fails for its named reason, and the inventory covers
    both laundering directions. A control that passes means the property it
    guards is no longer being tested;
127e. **recognition is exact, and its closure is measured** — every recognised
    form is one whole diagnostic line predicted before the command ran, and the
    probe carries a closure section that classifies outcomes outside the
    recognised set and requires each to yield no verdict, in both laundering
    directions, reported separately. A probe that recognises a lead plus an
    unconstrained tail, or a substring anywhere in the output, does not satisfy
    case 127c: such a branch is a family rather than an outcome, and the
    direction it names is where its fabrications hide.
