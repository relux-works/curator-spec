# Decision 0009: hardened build execution profile

Record numbers 0007 and 0008 are reserved by sibling candidate tasks that are
not part of this change set. This record takes 0009 so that the three can land
in any order without renumbering.

## Context

Decision 0006 made the portable `manager-worker-v1` execution policy the single
execution contract of protocol 1.0 and was explicit about what it does not
provide. Six guarantees — `total-network-denial`,
`read-only-source-and-toolchain`, `private-build-root-only-writes`,
`hard-aggregate-descendant-resource-bounds`, `exact-executable-allowlisting`,
and `fail-closed-capability-preflight` — were named, attributed to
`STORY-260728-327soo`, forbidden to portable builds, and reserved together with
an execution-policy identity, `hardened-worker-v1`, and a reserved cache key in
`conformance/v1/vectors/go-host-execution-policy.json`.

That reservation left three questions open. What exactly does each guarantee
require of a host, in terms a reviewer can check and an adversarial test can
falsify? What must be true before a compiler runs, and what happens when it is
not? And how does hardened output stay distinguishable from portable output in
every reusable artifact: cache entry, receipt, install marker, and conformance
claim?

Answering those questions before any native work starts is the point of this
record. The alternative — writing a Linux sandbox first and deriving the
contract from what that sandbox happened to achieve — is how "best-effort
controls" become "guarantees" by accident, which is precisely the failure
decision 0006 spent its length avoiding.

The candidate `1.0.0-rc.5` suite is accepted and pinned: `conformance/v1` is
hashed into `release/1.0.0-rc.5.json` and that digest is consumed downstream.
Any hardened material inside that suite root would change the pin.

## Decision

The hardened profile is specified as an **additive, separately versioned**
candidate, `hardened-1.0.0-rc.1`, with its own suite root, its own schemas, and
its own release metadata:

- `protocol/hardened-execution.md` and `profiles/manager-hardened.md` are the
  normative documents;
- `schemas/hardened/v1/` holds its schemas;
- `conformance/hardened/v1/` is its suite root; and
- `release/hardened-1.0.0-rc.1.json` pins that suite and records, read-only,
  the rc.5 portable manifest digest it builds on.

Nothing under `conformance/v1`, `schemas/v1`, or `release/1.0.0-rc.5.json`
changes. The portable profile stays a complete, self-contained, weaker contract,
and a manager may implement it and never implement this one.

### The contract is all-or-nothing

All six guarantees hold, or the operation rejects. There is no partial hardened
mode, no best-effort guarantee, no warning-level degradation, and no silent
fallback from hardened to portable. An operator who wants the portable contract
selects the portable profile explicitly, and that operation is portable in every
respect including its cache key.

### Guarantees are stated as kernel refusals

Each guarantee is defined as something the kernel or hypervisor refuses to do
for every process in the build domain, and each definition carries an explicit
"not sufficient" list naming the manager-side mechanisms that must not be
presented as establishing it: configuration flags, filesystem permissions the
domain can change, per-process resource limits, empty `PATH` values, post-hoc
scans, and promises. That structure is what keeps the six names from drifting
back into the portable meanings decision 0006 separated them from.

### The graph gains one uncontained node

```text
manager parent                        (trusted, outside the build domain)
  -> identity-verified hardened supervisor
                                      (trusted, outside the build domain)
       -> domain-root worker          (first process INSIDE the build domain)
            -> fingerprinted <GOROOT>/bin/go
                 -> fingerprinted regular executables below
                    <GOROOT>/pkg/tool/<GOHOSTOS>_<GOHOSTARCH>/
```

Creating a containment object and applying its controls require operations the
contained domain must not be able to perform. A process cannot be both the
creator of its own confinement and confined by it from its first instruction, so
the supervisor is uncontained and the worker is the first process inside the
domain.

Verification runs from both sides, and the split matters. The supervisor probes
capabilities from outside before the domain exists; the worker attempts denied
operations from inside once it does. Only a contained process can observe
containment, which is why the self-test cannot precede domain entry.

### One ordered phase list, with an actor per phase

Seventeen ordered phases are normative, and `protocol/hardened-execution.md`
section 7.2 is their sole authority. The manager profile attaches obligations to
those phase names and publishes no ordering of its own, so the two documents
cannot present conflicting sequences; `tools/validate_hardened.py` parses both
and fails if they drift.

Every phase names the one actor that performs it — manager parent, hardened
supervisor, or domain-root worker — and no phase performed inside the build
domain may precede `domain-entry`. That rule is what makes the pre-package state
machine performable. An earlier draft ordered the in-domain guarantee self-test
before domain entry, which no actor could satisfy: the domain-root worker is by
definition the first process inside the domain.

The order is therefore `domain-establishment`, then `domain-entry`, then
`in-domain-guarantee-self-test`, then `go-list`. The worker exists before it is
asked to test from inside, and it opens no path below the source view and starts
no Go process until the supervisor accepts the test result.

### Two boundaries, stated separately

Profile selection, platform qualification, capability probing, package-independent
toolchain probing and snapshot freezing, trusted-computing-base verification,
cache lookup, and domain establishment complete **before domain entry**. Domain
entry and the in-domain self-test complete **before package exposure**. Both are
strictly before `go list`, `go build`, and any compiler.

Conflating the two would have been the easy drafting choice and a dishonest one.
Every capability, qualification, and identity rejection is in the first group, so
an unsupported host never creates a build domain at all. The self-test is in the
second group, because a test from inside a domain cannot precede that domain's
first process. A self-test that cannot be run is a failure, not a pass.

### Capability classes are exhaustive and probed per operation

Eleven classes in `hardened-capability-inventory-v1`, mapped many-to-one onto
the six guarantees, are probed on this host in this operation before domain
entry. A host label, a version comparison alone, a build-time constant, a
configuration file, and a cached result are not probes. Evidence is one closed
`hardened-capability-evidence-v1` record per operation, distinct from the
portable `capability-evidence-v1` record, and result-only.

### Identity binding

Binding model `hardened-identity-binding-v1`. One rule: every identity that
determines whether a guarantee holds is inside the hashed build input, and only
the per-operation observation is result-only.

A hardened build input is the portable input with the `execution_policy` value
replaced and exactly one closed member added, carrying the profile identity
`hardened-profile-v1` and the `curator-hardened-tcb-v1` digest of the concrete
`hardened-tcb-v1` record. That digest is domain-separated and length-framed in
the same style as `curator-build-source-v1`, so it can never be confused with a
cache key over the same canonical bytes.

Consequently the profile identity and the trusted computing base bind the cache
key, the exact receipt bytes, `receipt_sha256`, the install marker, and the
conformance claim. Cache reuse cannot cross a profile revision or a trusted
computing base, because the key is recomputed from both on every lookup. The
receipt also carries the complete record, and a marker's cache key must be
reproducible from the identities the marker itself publishes.

An earlier draft kept the profile identity and the trusted computing base out of
the hashed input in order to reproduce the cache key
`sha256:13736230d33ce59de7f7323dcd4cffd510655ad8dabd5ee9e8b6cb182ec70037` that
rc.5 recorded for an input filling only the reserved policy slot. That was
rejected. rc.5 marks that input `schema_valid: false`; it is a non-aliasing
demonstration, not a hardened build input, and preserving it would have left the
two identities that determine the guarantee unbound in cache and receipt state.
It is retained as a fourth comparison point instead, so the suite now proves five
distinct non-aliasing keys.

The residual cost is that one source produces a different key on each trusted
computing base and after a manager update that changes supervisor or worker
bytes. That is intended. An artifact carries exactly the guarantees of the
trusted computing base that produced it; reusing across a supervisor update —
including one that fixes a containment defect — would silently attribute this
revision's guarantees to a build that never ran under them.

This is not the case `decisions/0006` rejected. That decision kept per-operation
capability *evidence* out of portable cache identity so a key could not be read
as capability proof, and this profile keeps the same rule: the
`hardened-capability-evidence-v1` record stays result-only and enters no cache
key, receipt, marker, or claim. What is hashed here is identity, not observation.

### The trusted computing base record must be complete, not representative

Binding a TCB digest is only worth something if the record behind the digest
distinguishes the trusted bases that actually differ. A first draft of this
profile named the supervisor bytes, the worker bytes, the enforcement-backend
label, and the toolchain, and left the additional trusted components as an
array of unconstrained strings. Independent review showed that record admitted
two materially different trusted bases with one digest: the manager parent was
unnamed, the observed operating system, hypervisor, and backend version were
unnamed, a "mutable interpreter" could be declared as prose with no digest at
all, and nothing stopped a macOS record from carrying a Windows backend.

`hardened-tcb-v1` is therefore the complete closed record of
`protocol/hardened-execution.md` section 2.3: the manager parent, supervisor,
and worker digests, the observed host identity, version, and build, the
enforcement backend with its observed version and the configuration settings
the qualification depends on, the fingerprinted toolchain, and every additional
mutable trusted component as a closed `{kind, name, algorithm, content_sha256}`
record. The platform-to-backend, target-to-platform, and
operating-system-to-backend relations are enforced by the schemas themselves,
the host-identity-to-platform, backend-version-series-to-backend, and
component-algorithm-to-kind relations with them,
and the conformance suite rotates every mutable member in turn and requires the
cache key to move — most of them without changing one byte a package can see,
which is what makes the binding attributable to the trusted computing base
rather than to the build.

The cost is more identity per host and one more thing an implementation must
observe honestly. That is the right trade: an implementation that cannot say
which operating system, which backend version, and which components it trusted
cannot support the claim that an artifact carries this revision's guarantees.

Hardened builds write build receipt schema 3 for `go-v1`, schema 4 for
`go-repository-v1`, install marker schema 4, and conformance claim schema 4.
Claim 3 admits only `manager-worker-v1` and claim 4 only `hardened-worker-v1`,
so the two are structurally disjoint in both directions. A reader that does not
implement the hardened profile rejects the new receipt and marker versions as
unsupported identities rather than parsing them leniently.

### A component algorithm is a construction, not a label

Naming `curator-hardened-component-file-v1` and
`curator-hardened-component-tree-v1` without defining them left the completeness
argument resting on nothing. Two implementations could hash different
projections of one installed package tree — one skipping symbolic links, one
following them, one folding a directory's mode into the digest — and both claim
the same algorithm identity, so the same `content_sha256` would not mean the
same trusted component.

Both are now defined byte for byte in `protocol/hardened-execution.md` section
2.3.1, in the same domain-separated, length-framed style as
`curator-build-source-v1` and `curator-go-toolchain-v1`. The tree construction
hashes the entry kind alongside the path and payload, which is what makes the
substitution that motivated it — replacing a symbolic link with a regular file
holding the referent's exact bytes — produce a different tree rather than the
same one. Modes, ownership, timestamps, ACLs, and extended attributes stay out,
because they change without changing what the component does; the entry kind
stays in, because it changes what the component *is*. A component that cannot be
read, is not the file type its algorithm requires, or changes between
`tcb-identity-verification` and `identity-reverification` fails closed rather
than being named without a digest — and since `identity-reverification` now
follows `domain-teardown`, that window covers the last domain member's exit.

Which algorithm a kind admits is closed too, in section 2.3.2, because a kind
that can only ever name one file has no business carrying a tree digest.

The construction is only credible if a second implementation reproduces it, so
the identity-separation vector publishes the exact bytes and expected digest of
every component fixture the suite uses. The generator computes them in Go; the
conformance validator recomputes every one of them in Python from the published
bytes, and no trusted-component digest anywhere in the suite is allowed to come
from anywhere else. Coverage is tracked per facet — kind, name, algorithm,
content, tree membership, entry type, link substitution, and the component set —
rather than per array, because rotating the array proves only that the array is
hashed.

### A declared minimum version has to be compared

Section 8.5 required an observed backend version at or above a claim's declared
`minimum_version` and nothing compared the two, so a claim declaring `999999`
was accepted against an observed version of `0`. A prose MUST that no reader
evaluates is not a contract; it is an intention.

The obstacle was that both values were free strings. Comparing arbitrary version
strings has no defensible rule, so this revision defines one:
`hardened-backend-version-v1` is a per-backend series token, `-`, and up to four
dot-separated integers. The series is closed against the backend in the schema,
so a claim cannot qualify a Linux host by quoting a macOS sandbox version, and
comparing two series is invalid rather than lower or higher — a backend's
version line has no ordering against another backend's. Missing components are
zero, and components compare as integers, which is the whole reason not to
compare strings: `cgroup2-6.9` sorts after `cgroup2-6.10` and is below it.

The same reasoning applies to the observed host. `host` was bound into the
record but related to nothing, so a Linux trusted computing base could report a
Windows kernel and still validate. Every enforcement backend this revision
declares is an operating-system-kernel mechanism, so `host.kind` is
`operating-system` and `host.identity` is the canonical kernel identity the
platform declares. The `hypervisor` value is removed rather than left
unenforced: a hypervisor-supplied backend would change which mechanism supplies
which capability class, which section 2.2 already requires to mint a new profile
identity and a new execution-policy identity, and that revision writes its own
record version. Narrowing costs nothing here, and an unenforced second kind
would only have been a way to detach the observed host from the platform it is
supposed to identify.

### The observed kernel needs an identity, not a description

Narrowing `host.identity` to the platform's canonical kernel left the rest of
the observed host descriptive: `host.version` was any string and `host.build`
was any string **or null**. That is not a small gap. Two kernels that expose the
same platform, the same release string, and no build value — a distribution
rebuild, a vendor patch, a locally compiled image — produced the same
`hardened-tcb-v1` record, and therefore the same digest, the same cache key, the
same receipt, the same marker, and the same claim. The record's whole reason to
exist is that two materially different trusted bases cannot do that.

So `host.build` becomes a required closed record,
`{algorithm, identifier, content_sha256}`, and
`curator-hardened-host-build-v1` is a construction rather than a name. Section
6.3 declares, per platform, an ordered closed list of build-identity sources and
which of them the identifier is read from; the digest covers the observed kernel
identity, the release, the identifier, and every declared source, each
length-framed, with the source count hashed too so a truncated list cannot alias
a full one. Two kernels now differ in the record unless every declared
observation of them agrees byte for byte.

Three choices are worth stating. First, the identifier is not free: it MUST be
the exact value of the platform's declared identifier source, so it cannot drift
away from the bytes the digest covers. Second, `host.version` gets a bounded
grammar for the same reason the backend version did — an unconstrained string
gives one kernel many spellings, and identity that admits many spellings is not
identity. Third, the construction fails closed: a declared source that cannot be
read rejects in `tcb-identity-verification`, before domain establishment, rather
than degrading to a null, a build-time constant, or an identifier without a
digest. A platform whose declared sources cannot be observed is a platform that
does not qualify.

What this does not do is make a lying kernel honest. A host that misreports
every declared source lies inside its own trusted computing base, which section
3.3 already excludes. What it does is close the case where nobody lied and the
record still could not tell two kernels apart.

As with the component algorithms, a construction is only credible if a second
implementation reproduces it, so the identity-separation vector publishes the
exact bytes of every build-identity fixture; the generator computes them in Go
and the conformance validator recomputes each one in Python. No observed host
anywhere in the suite may carry a digest a published fixture does not reproduce,
and the fixture must be the one computed over that record's own kernel identity,
release, and identifier. Two structural claims are checked rather than asserted:
a rebuilt kernel sharing the base's whole observed tuple does not share its
digest, and source bytes moved across a field boundary do not reproduce the
base. Coverage is tracked per facet — identifier, source value, release binding
— because rotating the host record proves only that the record is hashed.

### Re-verification happens after the domain is joined, and covers the whole record

The end of the operation had two defects, and they compounded. The phase list
put `identity-reverification` before `domain-teardown`, so the re-check could
not prove anything about the state after the last domain member exited — while
section 2.3.1 required exactly that. And the manager obligation re-verified four
identities (supervisor, worker, snapshot, toolchain) where phase 5 had hashed
twelve, so the observed host, the backend version and configuration, the manager
parent, and every trusted component had no end-of-operation check at all. A
component could change between the two phases, or an omitted member could change
at any point, and publication would still attribute the artifact to the phase-5
digest.

The fix is the ordering the property actually needs: destroy and **join** the
whole domain first, then re-verify. Once teardown has joined the domain, no
process that could touch a trusted component is running or can start, so the
window `tcb-identity-verification` opened is genuinely closed.

And re-verification is defined as recomputing the *complete* record from the
same canonical pinned identities, requiring byte identity against the phase-5
record and digest equality against the hashed build input — not a spot check.
Restating the earlier record, or comparing its digest against itself, explicitly
does not discharge the obligation, because both are things an implementation
would otherwise be free to call re-verification. The alternative — keeping the
old order and proving immutability with immutable handles or a snapshot
construction — is defensible in principle, but it would need a per-platform
handle model this revision has no qualified platform to validate, and it buys
nothing over joining a domain that is being torn down anyway.

The executable form follows the same rule as the phase list itself: the member
set is derived from the closed record rather than restated, so a future member is
covered the moment it is added, and every re-verified member carries its own
adversarial omission case alongside the phase-order and restated-record cases.

### No platform is qualified in this revision

Linux, macOS, and Windows each get a declaration naming an enforcement backend
and the public primitives a candidate binding would use, and each carries
`qualification_status: "unqualified"` with the task that owns qualification. The
macOS declaration records `domain-membership-enforcement`,
`domain-atomic-termination`, and `aggregate-resource-bounds` as blocking, because
the platform exposes no unescapable per-operation process domain — a contained
process can leave the process group or session — and no aggregate private
storage, memory, or process-count accounting. The Windows declaration records
`exec-path-allowlist` as blocking, because child-process creation policy is
all-or-none with no supported per-path execution allowlist for a contained
token, and `aggregate-resource-bounds`, because no supported facility bounds the
bytes a job writes below the private build root. Every one of those findings
restates the `no-private-aggregate-domain` analysis decision 0006 already
recorded, rather than contradicting it.

The observable consequence today is that every host rejects the hardened profile
in `platform-qualification` with `hardened_profile_unsupported`, and that no conformance claim
schema 4 document can be emitted. That is the specification working as intended,
and it is recorded honestly in the candidate metadata as `claims_emitted: []`.

## Rejected alternatives

- **Add hardened material to `conformance/v1`.** Rejected: it changes
  `conformance/v1/manifest.json` and therefore the accepted
  `release/1.0.0-rc.5.json` pin that downstream consumes, for a profile that no
  platform can satisfy yet.
- **Widen `goExecutionPolicyV1`, receipt v1/v2, marker v3, or claim v3.**
  Rejected by decision 0006's own follow-up clause, and unsafe on the merits: a
  widened constant lets a portable implementation emit hardened-shaped output
  without establishing a single guarantee.
- **Put the enforcement backend, platform, or TCB digest in the cache key.**
  Rejected: it fragments identity per host and per manager update without adding
  a guarantee a reader may rely on, and it invites treating a cache key as
  capability proof — the same reasoning decision 0006 applied to portable
  capability evidence. The real risk, a host silently losing a capability, is
  answered by re-probing and re-establishing every guarantee on every operation.
- **Allow a partial hardened mode that reports which guarantees held.**
  Rejected: a per-guarantee report is a capability claim a reader will rely on,
  and the combinations are not independently meaningful — write confinement
  without domain membership enforcement, for instance, is not a weaker
  guarantee, it is no guarantee.
- **Let the hardened profile fall back to portable when the host does not
  qualify.** Rejected: the fallback would produce portable output for an
  operator who asked for hardened output, and the cache key would silently
  change under them. Rejecting is the honest answer, and selecting the portable
  profile explicitly remains available.
- **Reuse the portable four-node graph and apply controls in the worker.**
  Rejected: the worker would have to create and enter its own confinement,
  leaving a window in which it is uncontained, and it would need the very
  privileges the domain must not have.
- **Keep the profile identity and the trusted computing base out of the hashed
  input so the rc.5 policy-slot cache key is reproduced.** Rejected: rc.5 marks
  that input `schema_valid: false`, so it is a non-aliasing demonstration rather
  than a hardened build input, and preserving its key would leave the two
  identities that decide whether a guarantee holds unbound in cache and receipt
  state. The key is retained as a comparison point instead.
- **Name the additional trusted components as free-text strings, and leave the
  manager parent, the observed host, and the backend version out of the TCB
  record.** Rejected: it produced one digest for two materially different
  trusted bases, so cache entries, receipts, markers, and claims could be shared
  across them. Every member of `hardened-tcb-v1` is now a closed, cryptographic,
  or enumerated value, and each one is rotated in the conformance suite to prove
  it reaches the cache key.
- **Let a platform declare any enforcement backend, and let a receipt's native
  target disagree with its TCB platform.** Rejected: both pairs are closed
  one-to-one relations in this revision, and leaving them open let a record
  claim a mechanism the host never had. They are enforced in the schemas, so a
  reader that only validates against the published schema catches them too.
- **Order the in-domain guarantee self-test before domain entry so that every
  rejection can be described as pre-entry.** Rejected: no actor could perform
  it. The domain-root worker is the first process inside the domain, so a test
  from inside cannot precede entry. Stating two boundaries honestly —
  pre-entry and pre-package-exposure — costs one sentence and is executable.
- **Let the manager profile restate the phase sequence in its own words.**
  Rejected: two exact sequences drifted apart in the first draft. The protocol
  document owns the order; the manager profile attaches obligations to its phase
  names and a validator parses both.
- **Define the guarantees per platform, so each host promises what it can.**
  Rejected: that is the portable profile with extra words. The value of a
  hardened profile is that one name means one thing on every qualified host.
- **Qualify Linux now on the strength of the primitive binding.** Rejected: no
  native adversarial evidence exists, no Linux host was available to this task,
  and a binding is a design, not a proof. Qualification is a separate task with
  a stated evidence bar.
- **Wait for a working implementation and write the contract afterwards.**
  Rejected: it is how best-effort controls become advertised guarantees, and it
  gives the six implementation tasks nothing to build against or to be reviewed
  against.

## Compatibility impact

Additive in both directions. Schemas 1 through 7, receipt schemas 1 and 2,
marker schemas 1 through 3, claim schemas 1 through 3, the portable execution
policy, the portable native-control inventory, the portable capability-evidence
record, the six portable diagnostics, and every byte of `conformance/v1`,
`schemas/v1`, and `release/1.0.0-rc.5.json` are unchanged.

The package surface is unchanged. No manifest field, descriptor field, build
command field, environment variable, or out-of-band file selects, weakens, or
observes any part of this profile.

An rc.5 manager that never implements the hardened profile stays fully
conforming. It encounters receipt schema 3 or 4 and marker schema 4 only in
state a hardened manager wrote, and it rejects them as unsupported identities,
which is the behavior `protocol/core.md` sections 9.3 and 10 already require.

## Security impact

The profile adds the hardened supervisor, the enforcement-backend adapters, the
capability probes, the domain session channel, and the operating-system kernel
primitives to the trusted computing base, and it requires an
implementation to name every one of them cryptographically in a complete
`hardened-tcb-v1` record: the manager parent, supervisor, and worker digests,
the observed host and backend identity and version, the toolchain, and every
additional mutable component — an interpreter, an installed package tree, a
script, a shared library, a policy file — as a closed component record with its
own digest. A record narrower than the base the implementation actually runs on
is `hardened_tcb_identity_invalid`.

It does not claim that adversarial Go source is safe, that the Go toolchain is
free of defects, that the compiled artifact is authenticated, that a
same-principal or administrator adversary is excluded, or that side channels are
closed. The compile-only rejection policy of `SECURITY.md` remains mandatory and
is not relaxed by containment.

Its main security value before any implementation exists is negative: it makes
it impossible to claim a hardened guarantee without an exhaustive probe, an
in-domain self-test, a named backend, a named trusted computing base, a distinct
receipt, marker, and claim version, and a distinct cache identity.

## Follow-up

`TASK-260728-3ihgfq`, `TASK-260728-3n67j6`, and `TASK-260728-1v71sx` implement
and qualify the Curator Linux, macOS, and Windows backends;
`TASK-260728-ns5yk7`, `TASK-260728-jis03f`, and `TASK-260728-2hcmtg` do the same
for csk; `TASK-260728-1itx7a` verifies independently. Each qualification task
supplies the native adversarial evidence listed in
`protocol/hardened-execution.md` section 11 and advances exactly one platform
declaration. None of them may qualify a platform by asserting a primitive
binding, and none may relax a guarantee to fit a host.
