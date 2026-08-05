# Decision 0007: compiled-build toolchain requirement and preflight

## Context

Protocol 1.0 admits exactly one compiled language. `go-v1` and
`go-repository-v1` hard-code "Go 1.23 or newer, operator-trusted rather than
package-selected", resolve `<GOROOT>/bin/go` from manager or operator
configuration, and fingerprint the tree with `curator-go-toolchain-v1`. That
works while there is one language, one launcher relpath, one version format,
and one metadata file.

Three driver pairs are being designed on top of this base: Rust
(`TASK-260728-12pnm1`), Swift (`TASK-260728-1yhuqi`), and Kotlin
(`TASK-260728-168smo`). Each of those languages ships a toolchain selector that
the ecosystem treats as normal package data: `rust-toolchain.toml` names a
channel and can name a `path`, `swift-tools-version` and `.swift-version`
select a compiler, the Gradle wrapper downloads its own distribution, and Go's
own `GOTOOLCHAIN` will fetch and switch toolchains on demand. Every one of
those is a package-controlled path from source bytes to "which executable
compiles this", which is exactly the boundary decisions 0004 and 0006 exist to
hold. Repeating an ad-hoc answer per driver would produce four different
answers, four version formats, and four chances to leak selection.

The current ordering has a second, independent problem. `profiles/manager.md`
section 2.1 resolves and fingerprints the toolchain in phase 9, after ref
resolution, snapshot validation, closure construction, and audit; section 11.6
acquires the complete external repository before it touches a compiler. A host
with no Rust toolchain at all therefore clones, proves, hashes, and audits an
external repository before discovering that it can never build it. The
expensive and network-facing work runs before the cheapest possible rejection.

Finally, "install the missing toolchain for the user" is the obvious next step
and is not acceptable. Auto-install turns an installation failure into a
manager-initiated download and execution of third-party installer code, on the
same host, in the same operation, outside every gate this protocol defines.

## Decision

One closed contract, `toolchain-registry-v1`, is shared by every compiled
driver — local and external, current and future. The complete normative-ready
reference (registry table, grammar, ordering, diagnostics, guidance catalog and
vector inventory) is
[`docs/compiled-build-toolchain-requirements.md`](../docs/compiled-build-toolchain-requirements.md).

### 1. Closed identifiers and driver mapping

Toolchain identifiers are a closed manager-defined enumeration, not language
names a package may coin: `go`, `rust`, `swift`, `kotlin`, and the reserved
companion `jdk`. The manager-owned registry maps each build driver to exactly
one **primary** toolchain and an ordered, possibly empty list of **companion**
toolchains, and it is the only place that mapping exists. A driver whose entry
is absent is unsupported; there is no generic or inferred mapping.

Package data may constrain only the primary toolchain. Companion toolchains —
a JDK under a Kotlin/JVM artifact model, for example — carry the registry's
baseline requirement and are not expressible in a manifest or a descriptor,
because they are pipeline structure rather than a property of the source.

Every entry also declares `compatibility`: a closed, manager-owned set of
release families the manager has tested against that driver's conformance
vectors. It is a second gate, independent of any version requirement, and it is
what carries the released `profiles/manager.md` section 2.2 rule forward
unchanged — a tested Go 1.23 family, extended only by testing, with a newer
release merely ordered after a known one still rejected. A resolved Go 1.99.0
satisfies `at_least 1.23.0` and is still refused as
`build_toolchain_untested_release`, because membership is exact set membership
and never an ordering test. Package data can neither widen nor narrow the set,
and no requirement spelling can reach it.

Entries for `go` are complete in this decision. Entries for `rust`, `swift`,
`kotlin`, and `jdk` are reserved with a fixed obligation list that their own
driver decisions MUST fill. This is deliberate: naming a `swift --version`
parse or a Kotlin compiler root layout here, without a qualified host to probe,
would be a fabricated platform claim, and those decisions are downstream of
this one precisely so they can supply the evidence.

### 2. One canonical version, one grammar, one order

Cross-language determinism comes from refusing to compare native version
strings at all. Every toolchain entry defines a normalization from its bounded,
locale-independent probe output to the canonical triple
`(major, minor, patch)`, plus a prerelease flag. Comparison is then a single
lexicographic order over the triple, identical for all four languages.

Requirements are always written canonically, never in the language's display
form. The `toolchain-requirement-v1` object is exactly `id` and `version`;
`version` is exactly one of `{"kind":"exact","equals":V}`,
`{"kind":"at_least","min":V}`, or `{"kind":"range","min":V,"below":W}`, where
every literal is `major.minor.patch` with no prefix, prerelease, build metadata,
or leading zeros. Requirements combine as interval intersection, which is
associative, commutative, and order-independent, so the effective requirement
does not depend on the order in which the manager reads its sources.

"One grammar" is a property of the surfaces Curator owns — the requirement
object and the canonical triple. It is deliberately not extended to the
ecosystem files Stage B reads: those grammars belong to their ecosystems, each
entry pins the exact upstream grammar for each position it reads, and every
value is canonicalized into the triple before any comparison. The single order
is preserved by normalizing *into* it, never by imposing Curator's literal
grammar *onto* a file format Curator does not own.

**A prerelease toolchain never satisfies any requirement, and a requirement can
never name one.** Prerelease ordering is where cross-language determinism
actually dies: Go writes `1.24rc1` with no separator, Rust uses semver
`-nightly`, Kotlin uses `-Beta1`, and Swift ships dated development snapshots.
There is no shared order over those, and a compiler whose identity is not
stable between two rebuilds is a poor thing to bind into a cache key. Nightly
Rust, Swift development snapshots, and Go release candidates are therefore
rejected as hosts, not ranked.

### 3. Trusted resolution, never package selection

Resolution has exactly two admissible origins: a toolchain bundled with the
manager distribution, and trusted operator configuration in manager-owned,
owner-protected state. Everything else is forbidden and named: the ambient or
user `PATH`, any package or repository byte, a runtime root, project
`.agents/bin`, a shim, a manifest or descriptor value, an inherited environment
variable, and any version-manager shim or wrapper. The primary executable MUST
be a regular executable at the entry's fixed relpath inside the tree being
fingerprinted — the generalization of the existing "not a wrapper or an
executable outside the tree" rule for `<GOROOT>/bin/go`.

Those two admissible origins are also the manager's only two **declaration
channels**, and the distinction carries the diagnostics. The manager searches
for a root in the bundled distribution and in operator configuration and nowhere
else, so a toolchain reachable only through `PATH`, the environment, or a shim
is not declared at all and its presence on the host is invisible. A forbidden
origin therefore reaches the manager only as the value of a channel entry or as
the state holding it. Declaration presence and origin admissibility are then two
tests over two disjoint inputs — the channel map, and the entry that map
produced — rather than one question asked twice.

The exclusion rule reads on two distinct surfaces, and keeping them apart is
what makes it checkable rather than contradictory.

On the **manager-defined wire surface** — the manifest build command and the
`skill-build.json` descriptor target — the field set is closed and Curator owns
it. No field naming an executable path, toolchain root, download URL, mirror,
channel or track, version manager, install or package-manager command,
environment override, `PATH` edit, credential, keyring, checksum, or trust root
exists there, and none may be added. Two rejections apply, partitioned by what
fails rather than by what a value resembles: a key outside the closed set is the
existing unknown-field schema rejection, and a value that does not match its
field's closed grammar is `build_toolchain_requirement_invalid`. Package
influence is therefore *not* a wire-surface code. Classifying a malformed
literal as smuggled influence rather than as malformed would require inferring
intent from a byte string, and two conforming managers would infer differently;
the canonical grammar rejects a path, a URL, and a track for one checkable
reason instead. The "no such field may ever be added" half is an authoring
obligation on the schemas, enforced by a release gate over published property
names — a runtime code cannot enforce it, because a field that does not exist
produces no value to diagnose.

On the **source-ecosystem metadata surface** — files the ecosystem owns, read at
Stage B — Curator does not own the field set, so each entry declares a closed
disposition table giving every field it reads exactly one of `forbidden`,
`compared`, or `ignored`. `forbidden` is reserved for values naming *where* a
toolchain comes from; a channel or track is `compared`, because Curator's
refusal to honor it is exactly what makes it harmless. Forbidden fields are
evaluated before compared ones, in a fixed lexical order, so a file carrying
both has one outcome. Where a single field's value space spans dispositions —
the Go `toolchain` directive holds a version assertion, the literal `default`,
or a name identifying a vendor distribution — the entry declares an ordered,
exhaustive **value classifier** whose classes each carry one disposition, with
`forbidden` classes first and a mandatory catch-all last. Classification is
total by construction, at the value level as well as the field level.

A version constraint is admitted on the wire surface because it can only
*filter* the manager-trusted set; it can never introduce a candidate into it,
and it cannot reach `compatibility` either.

Identity generalizes the existing algorithm family. Each entry names
`curator-<toolchain_id>-toolchain-v1`; for `go` that is the deployed
`curator-go-toolchain-v1`, unchanged. A resolved identity is the algorithm
identifier, the normalized native version string, the primary-executable
relpath, and the tree digest. Toolchain location is not portable identity.

### 4. Two-stage preflight

Stage A — platform, availability, version — runs immediately after manifest
parsing and build-command validation, for every distinct toolchain in the plan,
in Unicode-scalar lexical order of toolchain identifier, once per operation. It
reads no package byte beyond the already-validated manifest and it MUST
complete before external repository acquisition, before build-cache lookup, and
before any persistent mutation.

Platform applicability splits across Stage A rather than sitting at one step,
and the split is forced by the registry rather than chosen. `primary_relpath`
and `probe` are declared per operating system and only for the operating systems
in `platforms`, so on an unsupported host there is no relpath to resolve and no
probe to construct. The host-pair check therefore runs *before* resolution, on
manager-owned registry data alone; otherwise `platform_unsupported` would be
unreachable on exactly the hosts it describes, and an implementation would have
to report an unrelated code or invent a relpath. The second half — the
toolchain's reported host target versus the native target — necessarily follows
the probe, because the probe is what reports it. One code covers both halves and
a REQUIRED discriminant in the payload says which fired.

Stage B — source-metadata cross-check — runs per active build command after
local snapshot validation, or after exact external acquisition and audit, and
before the manager reads an artifact-cache candidate or starts a compiler
child. Its steps are ordered: re-compute the effective requirement now that the
descriptor requirement is readable, re-evaluate the resolved version against
that narrowed interval, gate on file shape, then evaluate `forbidden` and
`compared` dispositions. It checks `go.mod`, `Cargo.toml` and
`rust-toolchain.toml`, `swift-tools-version` and `.swift-version`, or the single
Kotlin metadata field that `TASK-260728-168smo` selects.

The first two steps close the one hole the descriptor asymmetry opens. A
descriptor can only narrow the interval, but narrowing can produce a *non-empty*
interval that excludes the already-resolved host — a host at 1.23.0 passing a
manifest `at_least 1.23.0` and then meeting a descriptor `at_least 1.24.0`.
Rejecting only the empty case would let that reach cache lookup and a compiler
child. `incompatible` and `requirement_unsatisfiable` therefore each have one
firing site per interval they can be evaluated against, and the payload is keyed
on the firing site so both stay unambiguous. Nothing else re-runs: the host
pair, the declaration, the probe, the normalized version, the native target,
and the `compatibility` set are all decided from manager-owned data no
descriptor byte can reach.

The file-shape gate is what makes Stage B implementation-ready rather than a
partial check with a compiler fallback. A metadata file the ecosystem's own
grammar rejects — a repeated single-occurrence directive, an unparseable file —
yields no value to classify, so it is a typed `metadata_mismatch` before cache
lookup instead of a compiler error after the manager has committed to the build.
The gate covers file syntax only and asserts nothing about the semantics of
fields the entry does not read.

Stage B reads declared metadata **as an assertion about the already-resolved
toolchain, never as a selector**. It cannot switch, download, activate, or
re-resolve anything. A `rust-toolchain.toml` `channel` is `compared` and then
discarded — a version literal or `stable` is permitted and never honored, while
`beta`, `nightly`, and dated channels are a mismatch because they assert a
prerelease host v1 never resolves. Its `components`, `targets`, and `profile`
are `ignored`; its `path` is `forbidden`, and being forbidden it is evaluated
first, so a file carrying both `path` and `nightly` is deterministically a
package-influence rejection.

Because the `go` entry is complete, its two directives are classified
exhaustively here rather than deferred. The `go` directive has three value
classes — release literal, prerelease literal, unclassifiable — and no
`forbidden` class, because its Go-defined value space is a version and nothing
else. The `toolchain` directive has six: a path-bearing name and a
custom-distribution name (`go1.23.4-bigcorp`) are `forbidden`, because a vendor
suffix names *where* a toolchain comes from and is the `go.mod` analogue of
`rust-toolchain.toml` `path`; `default` is permitted and never honored, since it
means "do not switch", which is unconditionally what Curator does; canonical
release and prerelease names compare by base triple; and a catch-all is a
mismatch. Comparison canonicalizes `1.23` and `1.23rc1` alike to `(1, 23, 0)`,
which is exact rather than approximate: the two orders can differ only for a
comparand strictly between a language version and its release, every such value
is a prerelease, and Stage A already rejected a prerelease host.

**Upstream acceptance is the conjunction of two independent layers, and the
classifier is defined over that conjunction.** Go admits a directive value only
if `golang.org/x/mod/modfile` parses it — `GoVersionRE` for the `go` directive,
`ToolchainRE` for `toolchain` — *and* the command can represent it, through
`gover.Parse` and, for a name, `gover.FromToolchain`. Neither layer contains the
other, in either position: the shape layer accepts `go 1.23.4rc1`, which the
semantic layer cannot represent, and the semantic layer accepts a bare major
`1`, which the shape layer rejects. A classifier written against the shape layer
alone therefore permits values the Go command aborts on — measured on Go 1.25.1
and 1.25.5, `go 1.23.4rc1` parses and the command then fails with
`panic: go: internal error: missing go root module`. Every such value, in both
positions, is a typed `build_toolchain_metadata_mismatch` at Stage B, before
cache lookup and before a compiler child. Two earlier drafts got this wrong in
opposite ways: one used a single wider grammar for both positions and argued the
extra values were harmless because they are assertions rather than selectors —
which holds for selection and fails for ordering — and its successor pinned each
position to a shape artifact only, which left the semantic layer unenforced.

Alignment with Go is therefore **two properties, not one equality**. Writing `C`
for the values classified as a comparison, `F` for those classified as package
influence, and `Upstream` for what the Go command admits in that position:
**P1, no widening**, `C ⊆ Upstream`; and **P2, no narrowing outside the security
partition**, `Upstream \ F ⊆ C`. Together they give `C = Upstream \ F`.

`C = Upstream` is unsatisfiable and is not the goal. Upstream accepts custom
distribution names such as `go1.21.0-custom`, and Curator classifies exactly
those as `forbidden` because the suffix names *where* a toolchain comes from.
The security partition is a deliberate subtraction from what upstream admits, so
it appears in P2 and in neither side of P1. `F` is not bounded in the other
direction either — a path-bearing name is `forbidden` here and rejected upstream
too — so only `C` is pinned to upstream, and it is pinned exactly.

Because both layers are upstream artifacts that move independently, the
properties are **measured rather than asserted**: an executable boundary probe
drives real toolchains, measures each layer separately per value, and fails on
any disagreement with the classifier tables or any violation of P1 or P2. A
fixture table alone would only record what this decision believes upstream does.
The probe is re-run before a new Go release family enters `compatibility`.

**The semantic layer is representability, and the probe must measure it in
isolation from the host's own version.** Representability is a property of the
value; whether *this* toolchain will build the module is not. Upstream keeps the
two apart and applies them in that order — `cmd/go/internal/modload` raises
`*gover.TooNewError` only after `modfile.Parse` has succeeded and
`gover.Compare(f.Go.Version, gover.Local())` has been evaluated — so a
well-formed future release such as `go 1.99.0` is inside `Upstream` and is
refused by a third, host-dependent gate on top of it. Curator must keep them
apart for the same reason, and has its own place for the host relation: such a
value is a class-2 comparison whose base triple is above the resolved toolchain,
reported as `build_toolchain_metadata_mismatch` with a derived canonical
assertion. Folding the host gate into the grammar layers would classify one fact
twice, under two payloads, and would move every representable future release
into the unclassifiable class. The probe therefore lifts the probed toolchain's
own `gover` sources out of its `GOROOT`, builds them with that toolchain, and
evaluates representability directly; the real command is retained only as a
corroborating measurement, with its outcome classified into accepted, too-new,
and rejected rather than into pass and fail.

**That classification must be closed, and it must have a fourth state that is
not a verdict.** A classifier built from recognised forms plus a fall-through
branch is open, and the branch's verdict is asserted rather than measured for
every outcome upstream has not shown the probe yet. The consequence was already
observable: with `go build ./...` as the `toolchain`-position command, the module
loader runs after selection and exits non-zero on `toolchain default` and
`toolchain go1` with `updates to go.mod needed`, which is not a statement about
the name — and a fall-through branch that named acceptance scored both as
upstream acceptance on both probed toolchains. Two rules follow. The command is
narrowed to the one whose only failure surface is the layer under test, which for
the `toolchain` position is `go version`; and an outcome outside the recognised
set is *unknown*, fails the probe, and yields no verdict for the agreement check
to consume. Closure is what makes a green probe evidence rather than an absence
of surprises.

**A closed set is a set of outcomes, not of leads.** The first attempt at closure
still recognised *families*: a prefix with an unconstrained tail, a substring
found anywhere in the output. A family answers for every message upstream might
later render behind that lead, and none of them has been measured. Reading both
probed toolchains' `toolchain.Select` settles the case concretely: its
colon-bearing `invalid GOTOOLCHAIN %q` calls quote the *environment* setting
while interpreting it, before `go.mod` is read at all, so under the probe's fixed
`GOTOOLCHAIN=local+path` they quote `local+path` and can never name the value
under test. A branch admitting `invalid GOTOOLCHAIN "v"` plus any tail therefore
answered for a family no host produces — and answered `rejected`, which is
exactly where a fabrication hides: for a value the isolated measurement already
rejects, the fabricated verdict agrees, the crosscheck compares equal, and the
row goes green. Recognition is therefore whole-line and exact against forms
predicted before the command runs, and the rejection direction is neither safer
nor less tested than the acceptance one.

**Closure is measured rather than asserted.** The probe classifies outcomes
deliberately outside the recognised set — real unrelated command failures, every
measured outcome cross-fed against every other value, and measured diagnostics
extended the way a later release extends a message — and requires each to yield
no verdict, reporting for every fabrication which of the two laundering
directions it belongs to. The extended-diagnostic checks are constructed, and
must be: fail-closedness is a claim about outcomes that do not exist yet, which
no host can produce. Taking text upstream did emit and changing it the way a
later release would is the honest form of that check; asserting the property from
the recognised set alone is not a check at all.

Neither stage may be skipped by a cache hit, a dry run, or an offline mode, and
neither may be reordered ahead of source validation or audit. Stage A moving
earlier does not weaken any gate: it consumes manager and operator
configuration plus one already-validated manifest field, and every existing
phase keeps its existing position and its existing predecessor set.

For `go` this costs nothing. Stage A reuses the three package-independent
bootstrap probes that section 4.2 already runs from the manager parent —
`go telemetry off`, `go version`, `go env -json ...` — so the five Go
argument-vector forms remain exactly five and the `manager-worker-v1` process
graph is untouched. Only the phase they sit in changes.

### 5. Typed diagnostics and manager-owned guidance

Twelve stable `build_toolchain_*` codes cover requirement validity,
unsatisfiable intersection, availability, undetermined version, incompatible
version, untested release family, prerelease host, untrusted resolution,
unsupported platform, metadata mismatch, package influence, and mid-operation
change. They are listed with their exact trigger and stage in the reference
document. Where two gates would both reject a host, the Stage A step order
decides which code is reported, so the outcome is deterministic.

Every code fires only at named steps of named stages, and the triggers that read
as overlapping are partitioned by input rather than merely ordered. On the wire
surface a malformed value is always `requirement_invalid`, so
`package_influence_forbidden` is a Stage B code only. Within Stage A, resolution
splits into declaration presence, origin admissibility, and shape, over three
disjoint inputs: the channel map, the channel entry, and the filesystem object
that entry names. `unavailable` means *nothing was declared* and is the only
code the presence sub-step produces — a toolchain installed and on `PATH` but
absent from both channels is `unavailable`, not `untrusted`, because `PATH` is
not a channel. `untrusted` means *something was declared and is unusable*, which
includes a declared root that does not exist and a missing primary executable.
The partition is declaration presence, not severity, so the reported code never
depends on how far the manager got before failing — and it matches the guidance
classes, `host` for "obtain a toolchain" and `configuration` for "fix the
configuration".

Four codes fire at more than one site, each for a structural reason rather than
an editorial one: `requirement_unsatisfiable` and `incompatible` have one site
per interval they can be evaluated against, `platform_unsupported` one per half
of platform applicability, and `metadata_mismatch` one for file shape and one
for value classification.

The diagnostic payload is therefore a discriminated union keyed on the **firing
site** — `(code, stage, discriminant)` — and its shape stays derived rather than
chosen: a payload carries exactly the values established at the site where it
fires, and because every stage's steps are totally ordered, that set is a
function of the site. A code declares at most one discriminant, a REQUIRED
closed-token member; `untrusted` declares `substep` and `platform_unsupported`
declares `check`. Keying on the code alone stopped working once one code could
fire in two stages with different values established, and it also removed the
last editorial choice in the union: `platform_unsupported` previously carried
"either the supported set or the target pair" with nothing saying which, and
`check` now selects that branch from the site. `effective_requirement` is absent
at exactly the three sites whose own interval computation produced none, and
`resolved_version` at exactly the seven that precede normalization. The two
codes that motivated the union are representable without sentinels:
`requirement_invalid` carries a location and a closed violation token, and
`requirement_unsatisfiable` carries the individually validated fragments plus
the two bounds whose ordering failed, naming every source achieving each bound
in a fixed order so the payload is as source-order-independent as the
intersection. A payload never reproduces an unvalidated package byte, which
keeps package-controlled text out of manager output and keeps the payload
bounded.

A diagnostic carries a `guidance_id`, never prose or a URL. The
`toolchain-guidance-catalog-v1` catalog is manager-owned, versioned, and total
over (toolchain, reason, supported platform) — where `reason` is exactly the
diagnostic code's suffix, so the code-to-reason mapping is the identity and
stays total as codes are added. There is therefore no runtime "guidance
missing" case for any of the twelve, including the authoring and configuration
ones. Each reason declares a `guidance_class` that fixes the admissible origin
of its `primary_source`: the language's own official origin for host reasons,
the manager's operator documentation for configuration reasons, and this
specification for authoring reasons. Every one of those is a manager-trusted
origin, and guidance is text plus URL only — never a package, a mirror, an
installer script, or a command the manager runs.

Identifiers carry an immutable revision, `toolchain.<id>.<reason>.<platform>.r<N>`,
because a bare tuple cannot name two entries and `superseded_by` would have
nothing to point at. At most one entry per tuple is active; supersession moves
to the next revision of the same tuple and retired entries are retained so an
older diagnostic stays resolvable. Because the catalog is presentation, it is
deliberately not a cache, receipt, marker, or claim input: a corrected URL or a
new revision must never invalidate an artifact.

Coverage is defined by the selection function rather than beside it, so
"one `any` entry" and "one entry per operating system" stop competing: an active
exact entry covers its operating system, an active `any` entry covers the rest,
and pure-`any`, pure-per-OS, and hybrid catalogs are all valid. The gate checks
two properties — every supported operating system resolves to exactly one active
entry, and every active entry is reachable by some request — which admits a
fallback plus overrides while rejecting dead entries and a fallback shadowed
everywhere. Append-only is likewise stated against the version rather than
against the entry: a published catalog version is immutable in whole, changes
happen only from version N to N+1, and across that boundary the entry set only
grows while `active` and `superseded_by` move one way, `true` to `false` and
absent to set. Retirement without a successor is admissible only for a tuple the
coverage gate no longer requires.

**v1 never auto-installs.** No download, install, update, activation, or switch
of a toolchain, and specifically not through `rustup`, `swiftly`, `sdkman`,
`asdf`, `mise`, Homebrew, `winget`, the Gradle wrapper, or `GOTOOLCHAIN`.

### 6. Identity effects

The resolved toolchain identity stays a build input, as today; new drivers
bind an ordered `toolchain_identities` array covering primary and companions,
while `go-v1` and `go-repository-v1` keep their existing single-field shape
byte-for-byte.

The effective requirement and the `compatibility` set are **gates, not build
inputs**. Two packages whose different constraints are both satisfied by the
same resolved toolchain produce the same artifact, so putting either in the key
would fragment cache identity while adding no guarantee — the same argument
that kept host capability evidence out of the key in decision 0006. There is no
bypass: Stage A gates before cache lookup, so a hit is only reachable when the
currently resolved toolchain passes both gates.

That ordering also settles a case that is easy to state wrongly. If the current
resolved toolchain is incompatible, the operation fails at Stage A — cache
lookup is never reached, no candidate is consulted, and nothing is rebuilt.
Rebuilding is the outcome of a *different* case: the current toolchain passes
both gates and the cached candidate carries a different resolved toolchain
identity, so the key does not match and the command rebuilds. There is no
"cache hit with an incompatible toolchain" path.

Currentness is unchanged and stays a property of recorded identity. A toolchain
upgrade already changes the fingerprint, the cache key, and therefore
currentness. Read-only status and audit report a Stage A or Stage B failure as
a finding and MUST NOT mark an otherwise valid marker non-current because of
it; install, upgrade, repair, and coverage-claiming audit fail with the typed
diagnostic before mutation.

## Rejected alternatives

- **Per-driver toolchain rules.** Rejected: four drivers would produce four
  version formats, four resolution stories, and four independent chances to
  admit a package-selected path. The shared contract is the only place the
  exclusion list can be exhaustive.
- **Honor `rust-toolchain.toml`, `GOTOOLCHAIN`, `.swift-version`, or the Gradle
  wrapper as selectors, since they are the ecosystem norm.** Rejected: each is
  a direct package-bytes-to-executable-selection path, which is the boundary
  decisions 0004 and 0006 exist to hold. They are retained as assertions
  because cross-checking them produces a better diagnostic than a compiler
  error, and discarded as selectors.
- **Auto-install a missing toolchain.** Rejected: it makes the manager download
  and execute third-party installer code outside every gate in this protocol,
  and it converts a clean fail-fast into the largest untrusted action in the
  operation. Guidance IDs to primary sources give the user the same outcome
  with the decision left where it belongs.
- **Free-form version constraint strings** (`">=1.23, <1.25"`). Rejected: a
  mini-language invites two conforming managers to parse the same package
  differently. A closed object with three kinds has one reading.
- **Native version strings as the comparison domain.** Rejected: `go1.23.4`,
  `1.79.0-nightly`, `5.10`, and `2.1.0-Beta1` have no shared order. Normalizing
  to a triple at the entry boundary moves all per-language messiness into one
  reviewed rule per toolchain.
- **Rank prereleases instead of rejecting them.** Rejected: it requires a
  cross-language prerelease order that does not exist, and it binds an unstable
  compiler identity into a cache key that promises reproducibility.
- **Let the version requirement alone decide admissibility, with no tested-family
  set.** Rejected: it silently weakens the released rule. `profiles/manager.md`
  section 2.2 requires rejecting an otherwise unknown release including one
  merely ordered after a known one, and under a bare `at_least 1.23.0` an
  untested Go 1.99.0 would be admitted. Ordering is not evidence of testing, so
  the manager-owned set is the only thing that can carry that rule.
- **Let a package narrow or widen the tested-family set, or express it as a
  requirement.** Rejected: it is the same package-selects-the-compiler path in a
  different spelling. The requirement filters within what the manager already
  trusts; nothing on the wire surface may reach the trusted set itself.
- **Treat every channel-valued field as forbidden package influence.** Rejected:
  it conflates the surface Curator owns with the surface the ecosystem owns. On
  the manifest and descriptor there is no channel field to forbid, so the rule
  is vacuous there; in source metadata a channel is the ecosystem's normal way
  of stating an expectation, and refusing to honor it while comparing it gives a
  better diagnostic than a compiler error at no cost. Forbidding it outright
  would reject ordinary packages and prove nothing.
- **Classify a wire value that looks like a path, URL, or track as package
  influence rather than as a malformed literal.** Rejected: it makes the code
  depend on inferring intent from a byte string, and two conforming managers
  would draw the line differently — is `1.23-corp` a bad literal or a smuggled
  distribution name? The closed canonical grammar answers without inference, and
  the field-addition half of the rule moves to a schema release gate, where it
  is actually checkable. Keeping a runtime code for a field that a closed schema
  cannot admit would have been dead text.
- **Order the Stage A availability and trust triggers by severity instead of
  partitioning them.** Rejected: severity ordering still leaves both descriptions
  true for a declared-but-broken root, so the reported code would depend on how
  far the manager happened to get before failing. Partitioning on declaration
  presence gives each code one producing sub-step and matches the two remedies
  the guidance classes already distinguish.
- **Route a declared root that does not exist to `unavailable`.** Rejected: it
  reads naturally — nothing is there — but it splits one operator mistake across
  two codes depending on whether the missing thing is the root or the executable
  inside it, and it sends "your configuration points at nothing" to `host`
  guidance that says "install a toolchain".
- **Treat a custom Go toolchain name such as `go1.23.4-bigcorp` as a metadata
  mismatch.** Rejected: a mismatch says "the assertion is false about the
  resolved toolchain", which invites a later implementation to *check* the
  assertion by consulting the named distribution — reopening the selection path.
  The suffix names where a toolchain comes from, which is exactly what
  `forbidden` is reserved for.
- **Reject `toolchain default` as unclassifiable.** Rejected: it is the one
  metadata value that asserts precisely Curator's own unconditional behavior, so
  rejecting it would fail a package for agreeing with the manager.
- **Give the unavailable payload values a sentinel, or echo the offending value
  back.** Rejected: a sentinel is an invented representation each implementation
  would spell differently, which is the outcome the typed union exists to
  prevent; and echoing puts unvalidated, unbounded package bytes into manager
  output. A location plus a closed violation token identifies the defect exactly
  and carries nothing the package controls.
- **Forbid hybrid guidance coverage, allowing only pure `any` or pure per-OS.**
  Rejected: the selection function already resolves a fallback plus overrides
  deterministically, so the rejected catalogs are not ambiguous, merely
  disallowed — and forcing full per-OS duplication to add one platform-specific
  note is how a catalog goes stale. Reachability is the property actually worth
  gating, and it rejects dead entries that a mode rule would have permitted.
- **Identify guidance by `(toolchain, reason, platform)` alone.** Rejected: the
  tuple cannot name a second entry, so `superseded_by` has no distinct target
  and the "new identifier on a change of meaning" rule is unimplementable. An
  immutable revision component is the smallest fix that keeps selection a tuple
  lookup.
- **Restrict guidance to host-remediable reasons.** Rejected: it leaves an
  authoring or configuration failure with a `guidance_id` field and nothing to
  put in it, which is exactly the runtime "guidance missing" case the catalog
  exists to remove. Classing reasons instead keeps totality mechanical and keeps
  `primary_source` honest for each kind of failure.
- **Make the effective requirement or the compatibility set a cache-key input.**
  Rejected: identical source, toolchain, and policy would produce different keys
  per constraint spelling or per manager policy, fragmenting the cache while
  adding nothing — and it invites a reader to treat a key as constraint proof.
- **Put the guidance catalog in the cache key, receipt, or claim.** Rejected:
  fixing a stale upstream URL would invalidate every artifact built before the
  fix. Guidance is presentation.
- **Let a package declare platform applicability for a toolchain.** Rejected:
  it creates a package-controlled path to silently skip a command, which
  changes what gets installed without an error. Platform support is a registry
  property; an unsupported host is a typed failure, not a skip.
- **Let a package constrain companion toolchains.** Rejected: companions are
  manager pipeline structure. Exposing them would leak internals into the wire
  contract and let a package construct an unsatisfiable pair it has no way to
  reason about.
- **Keep toolchain resolution in phase 9 and add only the metadata check.**
  Rejected: it leaves the "clone, prove, hash, and audit an external repository,
  then discover the compiler is absent" path intact, which is the concrete cost
  this decision exists to remove.
- **Run Stage A before source validation and audit for everything, including
  the metadata check.** Rejected: the metadata check reads package bytes, so
  hoisting it would read unvalidated, unaudited source. The split is exactly
  the line between manager-owned inputs and package-owned inputs.
- **One combined `toolchain` field per driver instead of primary plus
  companions.** Rejected: a Kotlin/JVM model needs a compiler and a JDK, and
  collapsing them would either hide one from the build input or force a package
  to describe both.
- **Ask the declaration sub-step whether a root was declared by an *admissible*
  origin.** Rejected: it decides origin twice. A `PATH`-deferring configuration
  entry would answer "no admissible declaration" and produce `unavailable`,
  while the origin sub-step is specified to produce `untrusted` for the same
  input — two codes for one input, resolved only by whichever rule an
  implementation happened to consult first. Presence is now a pure lookup over
  the two declaration channels and cannot judge an origin at all, so the two
  sub-steps read disjoint inputs instead of being ordered around an overlap.
- **Let the manager search `PATH` so it can report "found, but not trusted".**
  Rejected: it makes the diagnostic depend on what is installed on the host,
  reintroduces an ambient lookup into resolution in order to remove one from a
  message, and buys nothing the `unavailable` guidance does not already say.
  `PATH` is not a declaration channel, so a toolchain reachable only through it
  is invisible and the outcome is the same on every host.
- **Check platform applicability once, after the probe.** Rejected: it makes
  `platform_unsupported` unreachable on exactly the hosts it describes. The
  registry declares `primary_relpath` and `probe` per operating system and only
  for supported ones, so on an unsupported host the manager would have to invent
  a relpath or fail earlier with `untrusted` or `version_undetermined`. The
  host-pair half moves ahead of resolution, where it needs nothing but registry
  data and the host pair; only the reported-target half stays after the probe,
  because the probe is what reports it.
- **Give `platform_unsupported` a total relpath and probe for every host instead
  of moving the check.** Rejected: it invents manager behavior for hosts the
  manager does not support, purely to keep one step ordering. A registry entry
  that declares a relpath for an operating system outside its `platforms` set is
  unreachable data, and the release gate now rejects it.
- **Let Stage B re-check only for an empty intersection once the descriptor
  requirement joins.** Rejected: narrowing can produce a non-empty interval that
  excludes the already-resolved host, and nothing would reject it before cache
  lookup and a compiler child — Stage A evaluated a wider interval, and the
  emptiness test passes. Stage B re-evaluates the resolved version against the
  narrowed interval as its own ordered step, so `incompatible` has a firing site
  per interval rather than a blind spot.
- **Re-run the whole of Stage A at Stage B for external commands.** Rejected: it
  re-probes the host, re-resolves the root, and re-checks a `compatibility` set
  no package byte can reach, for one input that actually changed. Only the two
  requirement gates depend on the descriptor, so only they re-run.
- **Keep the payload union keyed on the code alone.** Rejected: once one code
  fires in two stages, the same code carries different established values in
  each, and "shape is a function of the code" becomes false rather than
  restrictive. Keying on the firing site keeps the shape derived, and it removed
  the union's last editorial choice by giving `platform_unsupported` a
  discriminant instead of an unlabeled either/or.
- **Keep one shared Go version literal grammar, wider than upstream, on the
  grounds that these values are assertions rather than selectors.** Rejected:
  the assertion argument is sound for selection and unsound for ordering. A
  wider grammar admits values Go itself rejects — `go 1`, `go 0`, `go 1.023` —
  as permitted comparisons, so they pass Stage B and fail later as a compiler
  error, after cache lookup and after a compiler child starts. That is exactly
  the deferral a pre-compiler cross-check exists to remove. Go also does not use
  one grammar in the two directive positions, so a single grammar was
  simultaneously too wide for the `go` directive and too narrow for a toolchain
  name.
- **Give each classifier its own repeated-directive class.** Rejected: a
  repeated directive is a defect of file shape, not of any value, and a file
  that does not parse yields no value to classify. Per-classifier cases also
  left the `go` directive without the outcome the `toolchain` directive had. One
  file-shape gate ahead of both classifiers covers every directive and every
  other shape the ecosystem's grammar rejects.
- **Define the `go`-directive classifier by `modfile.GoVersionRE` alone.**
  Rejected: the regex is only the shape layer of a two-layer acceptance
  pipeline. It matches `go 1.23.4rc1`, which `gover.Parse` cannot represent, so
  the value passed Stage B as a permitted comparison and reached cache lookup
  and a compiler child — measured as
  `panic: go: internal error: missing go root module` on Go 1.25.1 and 1.25.5.
  That is the same deferral the wider-grammar draft was rejected for, arrived at
  by pinning to one upstream artifact instead of to upstream's behavior. The
  classifier is defined over the conjunction of both layers.
- **Route a shape-valid but semantically unrepresentable value to the file-shape
  gate.** Rejected: the gate's premise is that the file yields no value to
  classify. `go 1.23.4rc1` parses, and the field extracts cleanly; what fails is
  the ecosystem's version semantics, not its file grammar. Routing it to the
  gate would make the gate's stated scope — file syntax only — false, and would
  make the two sites indistinguishable for a value that has one. It is a
  classifier case, and the code and payload are identical either way.
- **Give the patch-prerelease case its own diagnostic code or `assertion`
  token.** Rejected: the payload's closed token set would grow to carry a
  distinction no consumer can act on differently. Both routes into the
  unclassifiable class mean the same thing to a caller — the ecosystem cannot
  use this value — and section 5.1 keys the payload on the firing site, which
  already separates the file-shape gate from the classifier.
- **State the Go alignment as one equality, `compared` equals what upstream
  accepts.** Rejected: it is unsatisfiable, not merely strict. Upstream accepts
  custom distribution names such as `go1.21.0-custom`, and this decision
  classifies exactly those as package influence, so the two sets differ by
  construction and no implementation could satisfy the statement. Splitting it
  into P1 (`C ⊆ Upstream`) and P2 (`Upstream \ F ⊆ C`) keeps both halves exact
  and makes the security subtraction explicit instead of a contradiction.
- **Prove P1 and P2 with fixture vectors only.** Rejected: a fixture's upstream
  column records what this decision believes upstream does, so a shared
  misreading of upstream produces a green suite — which is how the
  `GoVersionRE`-only classifier survived a review cycle. Both layers are
  upstream artifacts that move independently, so the properties are measured by
  an executable probe against real toolchains, and the fixtures assert the
  partition the probe validates.
- **Measure the semantic layer with a command's exit status** (`go mod tidy`
  exits 0 ⇔ upstream can represent the value). Rejected: it is not the semantic
  layer, it is the semantic layer conjoined with the host-version gate, and the
  probe cannot tell the two apart from a status. It scores every representable
  release above the runner's own — `go 1.99.0`, `go 1.26.0`, `go 1.99rc1` — as
  outside `Upstream`, so the probe fails P1 against classes this decision
  deliberately keeps as comparisons. The failure mode is the dangerous kind: the
  probe is green until the corpus first names a version above the runner, then
  goes red for a defect that is entirely in the probe, and it goes red on the
  release gate rather than in review. Rejected alongside it: **matching the
  too-new message loosely**, since a substring of an error string is not a
  measurement of anything; the retained corroborating check requires the version
  the command echoes back to equal the value under test, which upstream can only
  produce by having represented it.
- **Drop the command measurement once the isolated one exists.** Rejected: the
  isolated harness is upstream's code but not upstream's composition, so on its
  own it could be wired up wrongly and still look self-consistent. Keeping both
  and requiring them to agree wherever the shape layer accepts the value costs
  one comparison per case and catches exactly that class of error. The
  disagreement itself is the check; neither measurement is authoritative alone.
- **Let the command classifier fall through to a verdict for outcomes it does
  not recognise.** Rejected, in either direction. Falling through to acceptance
  scores every unrelated failure as upstream acceptance, which is what happened
  to `toolchain default` and `toolchain go1` under `go build ./...`: a
  module-tidiness exit was read as evidence about a toolchain name, on both
  probed toolchains, in four of twenty-six measurements, and the agreement check
  could not catch it because the fabricated verdict agreed with the isolated one.
  Falling through to rejection is no better — it merely moves the laundering to
  values the isolated measurement already rejects, where the two again agree for
  the wrong reason. The recognised set is therefore closed against upstream's own
  `Fatalf` forms, each required to name the value under test, and anything else
  is unknown and fails. The cost is that a future upstream message change turns
  the probe red instead of quietly changing what it measures, which is the
  correct direction for a check whose whole purpose is to notice upstream moving.
- **Keep `go build ./...` as the `toolchain`-position command and widen the
  recognised set to cover the module loader's outcomes.** Rejected: it makes the
  recognised set grow with a subsystem that has nothing to do with toolchain-name
  acceptance, and every entry added to it is a new opportunity to recognise an
  unrelated failure as a verdict. Narrowing the command to `go version` removes
  the outcomes instead of classifying them, and leaves a form whose entire
  failure surface is `toolchain.Select` — so exit 0 means the name was accepted,
  rather than meaning nothing else happened to go wrong.
- **Recognise a diagnostic lead plus whatever tail follows it.** Rejected: that
  is a family, not an outcome, and its members have not been measured. On both
  probed toolchains the colon-bearing `invalid GOTOOLCHAIN %q` diagnostics quote
  the environment setting rather than the `go.mod` name, so a branch recognising
  `invalid GOTOOLCHAIN "v"` plus any tail was answering for outcomes no host
  produces — in the rejection direction, where the fabrication agrees with the
  isolated measurement and the crosscheck cannot see it. Whole-line matching
  against a form predicted from the value under test and the probe's own fixed
  constants removes the family without removing any measured outcome. The same
  argument retires the substring and lead-and-tail matchers at the `go` position,
  which were open in the same way and had not yet been challenged.
- **State fail-closedness as a property of the recognised set.** Rejected: the
  claim is about outcomes outside that set, so nothing inside it can witness the
  claim. The probe therefore carries a closure section that feeds it unrelated
  real failures, every measured outcome under the wrong value, and measured
  diagnostics extended as a later release would extend them, and requires each to
  produce no verdict. Constructing the extended forms is unavoidable and is
  disclosed as such — an outcome upstream has not yet written cannot be measured
  on any host — and it is still a stronger check than an assertion, because a
  regression makes it fail.
- **Keep the superseded classifications only in review history.** Rejected: each
  one produced a green probe, and a property that was silently dropped is
  indistinguishable from one that never existed. The five superseded
  classifications, command forms and recognition families stay runnable from the
  probe binary as controls that are required to fail, so a change that
  reintroduces one is caught by a control that stops failing. Two of the five
  guard closure and neither subsumes the other: restoring the command form
  injects a real unrelated failure and reaches the acceptance direction;
  restoring the recognition families reaches the rejection direction, because
  every family they bring back names `rejected`.

## Compatibility impact

Manifest schemas 1 through 5 are untouched. Schemas 6 and 7 keep their exact
bytes and their exact package surface: `buildCommandV6` remains exactly `type`,
`driver`, `source_dir`, `repositoryBuildCommandV1` remains exactly `type`,
`driver`, `repository`, `target`, and `skillBuildTargetV1` remains exactly
`driver`, `build_root`, `source_dir`. They gain two-stage preflight without a
new field because a command that declares no requirement takes its driver's
registry baseline — `go` `at_least 1.23.0` — and its `compatibility` set —
`{(1, 23)}` — which together are exactly the rule schemas 6 and 7 already state
in prose and `profiles/manager.md` section 2.2 already requires. No currently
admitted release becomes inadmissible and no currently rejected release becomes
admissible.

The REQUIRED `toolchain` object lands in the next manifest schema, and the
OPTIONAL descriptor-target requirement in the next `skill-build.json` schema.
This decision fixes their shape and semantics; `TASK-260728-2spy93` owns the
version numbers and `TASK-260728-2jaw7h` lands the schemas and vectors.

Frozen artifacts are unaffected because neither gate is a build input:
`curator-go-toolchain-v1`, `curator-build-source-v1`, `build-receipt-v1`,
`build-receipt-v2`, `install-marker-v2`, `install-marker-v3`, the rc.4
byte-frozen digests, and every published cache key keep their exact bytes and
values. No rebuild is caused by adopting this contract.

Two behavioral changes are visible. A host missing a required toolchain now
fails before external acquisition rather than after audit, so a previously
network-and-disk-expensive failure becomes cheap and its diagnostic changes
from a compiler or driver error to a typed `build_toolchain_*` code. And
`blocked` joins the local dry-run report vocabulary of `profiles/manager.md`
section 2.4, which currently lists it only for external commands in section
11.7; `unsupported` continues to mean an unknown driver and MUST NOT be reused
for a toolchain failure.

## Security impact

The contract closes the package-to-compiler-selection path for three languages
before their drivers exist, rather than after. Its central claim is narrow and
checkable: a version constraint can only filter a manager-trusted set, so no
manifest, descriptor, or source file can add a candidate, a path, a URL, a
channel, an install command, or a trust root. The `compatibility` set is what
keeps "filter" from degenerating: the trusted set is bounded by manager testing,
not by version ordering, so no constraint spelling can reach a release the
manager has never tested.

Fingerprinting is honest about what it proves. It proves that the tree is
stable across an operation and identical across operations; it does not prove
upstream authenticity. Verifying that the configured toolchain is genuinely
the vendor's remains the operator's responsibility at configuration time, and
v1 performs no signature verification of a toolchain. Naming this explicitly is
the point: a `content_sha256` in a receipt must not be read as provenance.

Refusing auto-install keeps the largest untrusted action out of the operation.
Refusing prerelease hosts keeps an unstable compiler identity out of a cache
key that promises reproducibility. Neither refusal claims that a trusted
release toolchain compiling adversarial source is safe; the compiler-input
rejection policy of decision 0004 and the portable containment boundary and six
deferred hardened guarantees of decision 0006 are unchanged and still apply.

Stage A widens no boundary. It runs earlier on inputs the manager already
trusted at that point — its own configuration and one validated manifest field
— and every gate that preceded compilation still precedes it.

## Downstream obligations

- `TASK-260728-2spy93` fixes the next manifest and descriptor schema versions
  and places the `toolchain` object defined here.
- `TASK-260728-2jaw7h` lands the schemas, canonical grammar, ordering, error
  taxonomy, diagnostic payload union, guidance-catalog identifiers, and the
  positive and negative vector inventory listed in the reference document. It
  also lands the wire-surface release gate: an enumeration of the build-command
  and descriptor-target property names of every published schema version,
  failing on a field that names an executable path, toolchain root, URL, mirror,
  channel or track, version manager, install command, environment override,
  credential, keyring, checksum, or trust root.
- `TASK-260728-2jaw7h` also lands the section 4.2.1.2 boundary probe as a
  maintained check: it measures each ecosystem's shape and semantic acceptance
  layers separately per value and fails on any disagreement with a classifier
  table or any violation of P1 or P2. Its semantic measurement MUST be isolated
  from the running host's version, MUST be corroborated by a classified — not
  exit-status — command outcome, and MUST carry the five regression controls as
  checks that are required to fail. That corroborating classifier MUST be closed:
  a recognised outcome is one whole diagnostic line, matched exactly against a
  form predicted before the command ran from the value under test and the
  probe's own fixed constants; an unrecognised outcome is unknown and fails the
  probe; and no branch maps an unrecognised outcome to a verdict. A lead with an
  unconstrained tail, or a substring found anywhere in the output, is a family
  rather than an outcome and MUST NOT be recognised. Each command form MUST be
  the narrowest one that still exercises the layer under test, so that exit 0 is
  a measurement of acceptance rather than of nothing having gone wrong. Closure
  MUST itself be measured by a section that classifies outcomes outside the
  recognised set and requires each to yield no verdict, covering and separately
  reporting both laundering directions. Fixture cases 126 through 126d assert
  the partition; the probe supplies the observed upstream column they are
  checked against.
- `TASK-260728-12pnm1`, `TASK-260728-1yhuqi`, and `TASK-260728-168smo` MUST
  each complete their reserved registry entry — probe argv, normalization rule,
  prerelease markers, root layout, primary-executable relpath, fingerprint
  algorithm identifier, companion toolchains, supported platforms, baseline
  version, `compatibility` family granularity and initial tested set, and the
  metadata-source disposition table — on a qualified host, and MUST NOT widen
  the exclusion list, reclassify a `forbidden` field as `compared`, admit a
  selector, or introduce auto-install. Each MUST also identify its ecosystem's
  acceptance layers, state whether they are independent as Go's are, and extend
  the boundary probe with both sides of every boundary between them; a
  disposition table asserted from one artifact's grammar without that
  measurement does not satisfy this obligation. Each MUST also state where its
  ecosystem applies a host-version gate on top of representability — `rustc`
  `rust-version`, `swift-tools-version`, and a Kotlin or Gradle JVM target all
  have one — and MUST keep it out of the probe's semantic measurement, since a
  gate that depends on the runner cannot be part of a value's grammar. Each MUST
  further enumerate its ecosystem's recognised command outcomes as a closed set
  drawn from that toolchain's own diagnostics, name the narrowest command form
  that exercises the layer under test, and treat anything outside that set as
  unknown. Each entry MUST be one whole diagnostic matched exactly, not a lead
  admitting whatever tail follows it, and each reserved driver MUST extend the
  closure section to its own recognised forms and report both laundering
  directions for them. `cargo`, `swift build` and a Gradle invocation all run
  substantial work after their version check, so each of them has the failure
  surface that produced the `updates to go.mod needed` outcome on the Go side;
  each also renders diagnostics that share a lead with unrelated ones, which is
  the surface that produced the `invalid GOTOOLCHAIN "v":` family.
- `TASK-260728-ypbuav` owns guidance-catalog maintenance under the lifecycle
  rules: a published catalog version immutable in whole, every change a version
  transition whose entry set only grows and whose `active` and `superseded_by`
  move one way, a new revision of the same tuple for any change of meaning,
  `superseded_by` naming a strictly greater revision of that tuple, at most one
  active entry per tuple, and totality over all twelve reasons enforced by a
  release gate that checks resolution and reachability across the `any`,
  `per_os`, and hybrid coverage shapes.
