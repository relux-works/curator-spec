# Curator Hardened Execution Profile 1.0

Candidate `hardened-1.0.0-rc.1`. This document is normative. The key words
MUST, MUST NOT, REQUIRED, SHOULD, SHOULD NOT, and MAY are used as in
[`protocol/core.md`](core.md) section 1.

## 0. Status, scope, and relationship to protocol 1.0

[`protocol/core.md`](core.md) section 4.2.1 defines exactly one execution policy
for the compiled-build drivers, the portable `manager-worker-v1` policy, and
names six guarantees that the portable policy explicitly does not provide. It
reserves the identity `hardened-worker-v1` for a separate profile and defers
those guarantees to that profile.

This document is that profile. It is **additive and separately versioned**:

- It does not modify, widen, or reinterpret any rule of protocol `1.0.0-rc.5`.
- It does not change any byte of `conformance/v1`, `schemas/v1`, or
  [`release/1.0.0-rc.5.json`](../release/1.0.0-rc.5.json). The portable suite
  keeps its own pin.
- Its conformance suite root is `conformance/hardened/v1` and its schemas are
  under `schemas/hardened/v1`. Its candidate metadata is
  [`release/hardened-1.0.0-rc.1.json`](../release/hardened-1.0.0-rc.1.json).
- The portable profile remains a complete, self-contained, weaker contract. A
  manager MAY implement the portable profile and never implement this one.

**No platform is qualified for the hardened profile in this revision.** Section
6 declares, per platform, the capability classes a host MUST provide and the
public primitives a candidate binding would use. Every declaration in this
revision carries `qualification_status: "unqualified"`, because no native
adversarial evidence exists yet. Section 7 therefore has one observable
consequence today: **every host rejects the hardened profile before any package
byte reaches any Go process.** That is the intended fail-closed behavior, not a
gap. Qualification is added by the implementation and verification tasks named
in section 11, each of which MUST supply native adversarial evidence for the
platform it qualifies.

## 1. Terms

- **build domain** — the kernel- or hypervisor-enforced containment object that
  holds every process which may observe a package byte. Membership is a
  property the contained processes cannot renounce.
- **hardened supervisor** — the trusted, uncontained, manager-owned process that
  probes capabilities, creates the build domain, and applies every control. It
  is never a package-selected program.
- **domain-root worker** — the first process inside the build domain, and the
  ancestor of every other process in it.
- **guarantee** — one of the six named properties of section 5. A guarantee is
  a statement about what the kernel or hypervisor refuses to do, never about
  what the manager chooses not to do.
- **capability class** — a platform-neutral primitive requirement, defined in
  section 6.1, whose presence is necessary to establish one or more guarantees.
- **enforcement backend** — the concrete, named, per-platform mechanism that
  supplies the capability classes on one host.
- **qualified platform** — a `(platform, minimum version, required
  configuration, enforcement backend)` tuple for which native adversarial
  evidence proves every guarantee. Qualification is a property of this
  specification revision, not of a running host.
- **hardened operation** — an install, update, repair, dry-run, status, or
  garbage-collection operation that has selected the hardened profile.

## 2. Identities

Identity binding model `hardened-identity-binding-v1`. One rule governs the
whole section: **every identity that determines whether a guarantee holds is
inside the hashed build input, and only the per-operation observation is
result-only.** Its executable form is the `identity_binding` section of
[`conformance/hardened/v1/vectors/hardened-identity-separation.json`](../conformance/hardened/v1/vectors/hardened-identity-separation.json).

### 2.1 Execution-policy identity

```json
{"execution_policy": "hardened-worker-v1"}
```

`hardened-worker-v1` is the exact identity reserved by `protocol/core.md`
section 4.2.1 and by the `reserved_hardened_execution_policy` field of
[`conformance/v1/vectors/go-host-execution-policy.json`](../conformance/v1/vectors/go-host-execution-policy.json).
A hardened operation MUST use that identity and MUST NOT introduce another. It
occupies exactly the `execution_policy` slot of the canonical build policy
object defined by `protocol/core.md` sections 9.1 and 9.2.

rc.5 also recorded a cache key over an input that fills only that slot:

```text
sha256:13736230d33ce59de7f7323dcd4cffd510655ad8dabd5ee9e8b6cb182ec70037
```

That input is marked `schema_valid: false` in rc.5 and it is **not** a hardened
build input. It demonstrates that the policy slot alone does not alias the
portable or pre-revision keys; a hardened build input additionally binds the
identities of sections 2.2 and 2.3. The hardened suite keeps that key as a
fourth non-aliasing comparison point and MUST NOT reproduce it as a hardened
cache key.

### 2.2 Profile identity

```json
{"hardened_profile": "hardened-profile-v1"}
```

The profile identity names this revision's complete contract: the six
guarantees of section 5, the capability classes of section 6, the ordering of
section 7, and the diagnostics of section 10.

It is part of the hashed build input. A hardened build input is the portable
build input for the same source, command, target, and toolchain with the
`execution_policy` value replaced and exactly one closed member added:

```json
{
  "hardened": {
    "profile": "hardened-profile-v1",
    "tcb": {"algorithm": "curator-hardened-tcb-v1", "content_sha256": "sha256:..."}
  }
}
```

No other field is added to, removed from, or reordered within the hashed build
input, and the member is closed: a reader MUST reject an unknown key inside it.
Because the portable input schemas are closed, a portable reader rejects a
hardened input outright.

In addition:

- an operation whose execution policy is `hardened-worker-v1` MUST report
  profile identity `hardened-profile-v1`, and
- an operation whose execution policy is `manager-worker-v1` MUST NOT report a
  hardened profile identity at all.

Violating either direction is `hardened_profile_claim_forbidden`. A future
revision that changes which guarantees hold, which capability classes are
required, or where the failure boundary sits MUST introduce both a new profile
identity and a new execution-policy identity; it MUST NOT reuse
`hardened-worker-v1` with a different guarantee set, and it MUST NOT be enabled
by widening the closed portable `manager-worker-v1` constant. Because the
profile identity is hashed, such a revision cannot silently reuse an artifact
this revision produced.

### 2.3 Trusted-computing-base identity

```json
{
  "record_version": "hardened-tcb-v1",
  "hardened_profile": "hardened-profile-v1",
  "execution_policy": "hardened-worker-v1",
  "platform": "macos",
  "enforcement_backend": "macos-sandbox-v1",
  "backend": {
    "version": "sandbox-2.0",
    "configuration": [{"setting": "sandbox_profile_dialect", "observed_value": "scheme-v1"}]
  },
  "host": {
    "kind": "operating-system",
    "identity": "darwin",
    "version": "25.0.0",
    "build": {
      "algorithm": "curator-hardened-host-build-v1",
      "identifier": "25A123",
      "content_sha256": "sha256:..."
    }
  },
  "parent_sha256": "sha256:...",
  "supervisor_sha256": "sha256:...",
  "worker_sha256": "sha256:...",
  "toolchain": {"algorithm": "curator-go-toolchain-v1", "content_sha256": "sha256:..."},
  "trusted_components": [
    {
      "kind": "capability-probe",
      "name": "capability-probe-suite",
      "algorithm": "curator-hardened-component-tree-v1",
      "content_sha256": "sha256:..."
    },
    {
      "kind": "enforcement-adapter",
      "name": "macos-sandbox-adapter",
      "algorithm": "curator-hardened-component-file-v1",
      "content_sha256": "sha256:..."
    }
  ]
}
```

The record is closed, and it names **every** identity of section 3.4 whose
replacement changes what the kernel actually enforces. Its members contain
exactly:

| Member | Identifies |
|---|---|
| `record_version`, `hardened_profile`, `execution_policy` | the contract the record is written under; fixed by this revision |
| `platform` | the hardened platform the operation ran on |
| `enforcement_backend` | the concrete mechanism that supplied the capability classes |
| `backend` | the **observed** backend version, as a comparable `hardened-backend-version-v1` value, and the configuration settings the qualification depends on |
| `host` | the **observed** operating-system kernel, its version, and its build, the last as the closed `curator-hardened-host-build-v1` identity of section 2.3.3 |
| `parent_sha256` | the installed manager parent bytes |
| `supervisor_sha256` | the hardened supervisor bytes |
| `worker_sha256` | the domain-root worker bytes |
| `toolchain` | the fingerprinted `go` launcher and `GOROOT` tool executables |
| `trusted_components` | every additional mutable trusted component, each as a closed cryptographic record |

The completeness requirement is the point of the record: **two materially
different trusted computing bases MUST NOT be able to produce the same
`hardened-tcb-v1` record**, because the digest of that record is what binds
cache reuse, receipt bytes, marker state, and claim identity.

A trusted component is `{kind, name, algorithm, content_sha256}` and nothing
else. `algorithm` is `curator-hardened-component-file-v1` for a single file or
`curator-hardened-component-tree-v1` for a directory tree; section 2.3.1 defines
both constructions, and section 2.3.2 states which kinds admit which algorithm.
An implementation that starts, loads, or consults a mutable interpreter, an
installed package tree, a script, a shared library, a sandbox policy file, a
helper executable, an enforcement adapter, a capability probe, or an identity
verifier that is not one of the three named binaries MUST name it here with its
digest. A component named by an unconstrained string is not an identity, and
this revision has no field that accepts one. Reporting a record narrower than
what the implementation actually trusts is `hardened_tcb_identity_invalid`.

Eight relations are structural, not advisory:

- **platform to backend.** A platform admits exactly the one enforcement
  backend section 6.3 declares for it. The pairs are closed in both directions.
- **target to platform.** `platform` MUST be the hardened platform of the host
  the operation runs on, and the hashed build input's native target MUST map to
  it: `darwin` to `macos`, `linux` to `linux`, `windows` to `windows`. A
  hardened build input MUST NOT target any other `GOOS`, because no other
  platform has a declaration.
- **toolchain agreement.** `toolchain` MUST be the same
  `curator-go-toolchain-v1` identity the build input carries.
- **host identity to platform.** `host.identity` MUST be exactly the canonical
  kernel identity section 6.3 declares for `platform`. Section 2.3.3 states the
  contract this narrows and why.
- **host build identifier to platform.** `host.build.identifier` MUST match the
  immutable kernel-build identifier grammar section 6.3 declares for `platform`,
  and MUST be exactly the value of that platform's declared identifier source.
  Section 2.3.3 defines both.
- **host build digest to observed host.** `host.build.content_sha256` MUST be
  the `curator-hardened-host-build-v1` digest of the very `identity`, `version`,
  `identifier`, and declared build-identity sources the same record reports.
- **backend version series to backend.** `backend.version` MUST be a
  `hardened-backend-version-v1` value whose series token is the one section 6.3
  declares for `enforcement_backend`. Section 2.3.4 defines the grammar and the
  comparison.
- **component algorithm to kind.** A component's `algorithm` MUST be one its
  `kind` admits under section 2.3.2.

Seven of the eight are enforced by the hardened schemas themselves; the
conformance suite additionally checks them against every published receipt,
marker, and claim. The eighth — the host build digest against the observed host
it is supposed to identify — is a construction over bytes rather than a shape, so
the conformance validator recomputes it from the published build-identity
fixtures instead. Section 8.5 adds the three relations that tie a claim's
declared qualification to the trusted computing base the claim names.

#### 2.3.1 Trusted-component digest algorithms

A component digest names *what the implementation trusts*, not where it happens
to sit, so neither algorithm hashes the component's own location. The record
around it carries `kind` and `name`, and `curator-hardened-tcb-v1` hashes that
record, so a renamed or reclassified component still moves the trusted-computing-
base digest.

Both algorithms fingerprint the component **as it is at the
`tcb-identity-verification` phase of section 7.2**, before domain establishment
and before any package byte is exposed. Neither is defined over a path that is
resolved through a symbolic link: the named path is used exactly as the trusted
configuration gives it.

##### `curator-hardened-component-file-v1`

The named path MUST be a regular file at fingerprint time. A directory, a
symbolic link, a device, a FIFO, a socket, or any other file type is not a
component file, and the implementation MUST NOT resolve one to reach a regular
file. Initialize SHA-256 with exact ASCII
`curator-hardened-component-file-v1` followed by `0x00`, then append:

```text
ASCII("F") || uint64be(content_byte_length) || file_bytes
```

Prefix the lowercase digest with `sha256:`. An empty file hashes the domain
prefix followed by `F` and `uint64be(0)`, which is a different value from the
domain prefix alone.

##### `curator-hardened-component-tree-v1`

The named path MUST be a directory at fingerprint time. Walk it without
following links; the root itself is not a record. Every relative path component
MUST contain valid Unicode scalar values; join components with `/` without
normalization or case folding and encode the result as UTF-8. Duplicate encoded
relative paths and platform path collisions are invalid.

Exactly three entry kinds are admitted, and any other file type — device,
FIFO, socket, door, whiteout, or anything the host adds — makes the whole tree
invalid rather than being skipped:

| `kind` | Entry | Payload |
|---|---|---|
| ASCII `D` | directory | empty |
| ASCII `F` | regular file | the exact file bytes |
| ASCII `L` | symbolic link | the exact UTF-8 `readlink` value |

A symbolic link MUST be relative, non-dangling, and resolve within the tree
root; an absolute, dangling, or escaping link is invalid. Its referent has its
own independent record of its own kind, so a link and its target are both
hashed. Hard links are independent regular-file records: the same bytes appear
once per path that names them.

Sort the entry path bytes in unsigned bytewise order. Initialize SHA-256 with
exact ASCII `curator-hardened-component-tree-v1` followed by `0x00`, then append
for every entry:

```text
kind || uint64be(path_byte_length) || path_utf8 ||
uint64be(payload_byte_length) || payload
```

Prefix the lowercase digest with `sha256:`. An empty tree hashes only the domain
prefix.

Permissions, ownership, timestamps, ACLs, and extended attributes are not hash
inputs, exactly as in `curator-go-toolchain-v1`. The entry kind **is** an input:
replacing a symbolic link with a regular file that holds the referent's bytes
changes both the kind byte and the payload, so a link substitution cannot
reproduce the digest of the tree it replaced.

##### Fail-closed semantics

Both algorithms fail closed, and a failure is `hardened_tcb_identity_invalid`
reported before domain entry:

- a component path that cannot be stat'd, opened, read, or walked, or that is
  not the file type its algorithm requires, is invalid; no partial digest is
  computed, cached, or published;
- a component that changes between the `tcb-identity-verification` and
  `identity-reverification` phases of section 7.2 is invalid. Section 7.2 orders
  `identity-reverification` after `domain-teardown` has destroyed and **joined**
  the whole domain, so that window already covers the last domain member's exit:
  each component MUST remain byte-for-byte unchanged across it, under the same
  rule section 5.2 applies to the snapshot and `GOROOT`; and
- an implementation MUST NOT retry a failed component against another path,
  substitute a cached digest, or degrade to naming the component without one.

Both are domain-separated and length-framed for the reason
`curator-build-source-v1` is: a component digest MUST NOT be confusable with a
tree digest, a toolchain digest, a build-source digest, a cache key, or any
other SHA-256 taken over the same bytes.

#### 2.3.2 Which algorithm a component kind admits

A kind that can only ever name one file admits only the file algorithm, and the
kind that names a tree admits only the tree algorithm. Three kinds admit either,
because an implementation may legitimately ship one binary or a directory of
them:

| `kind` | Admitted `algorithm` |
|---|---|
| `installed-package-tree` | `curator-hardened-component-tree-v1` |
| `helper-executable`, `interpreter`, `sandbox-policy-file`, `script`, `shared-library` | `curator-hardened-component-file-v1` |
| `capability-probe`, `enforcement-adapter`, `identity-verifier` | either |

#### 2.3.3 The observed-host contract

`host` identifies the observed kernel that supplies the capability classes, and
`host.kind` is `operating-system` in `hardened-profile-v1`. Every enforcement
backend section 6.3 declares is an operating-system-kernel mechanism, so there
is no revision-legal record in which the observed host is anything else. A
hypervisor-supplied backend would change which mechanism supplies which
capability class, which section 2.2 already requires to mint a new profile
identity and a new execution-policy identity; that revision defines its own
record version and its own host contract. Narrowing here is therefore free, and
an unenforced `hypervisor` value would only have been a way to detach the
observed host from the platform it is supposed to identify.

`host.identity` is the canonical kernel identity of section 6.3 and nothing
else, so a record cannot report a `linux` platform observed on a Windows kernel.

`host.version` is the observed kernel release. It is not compared against
anything — it identifies, it does not qualify — but it is not free-form either:
it is `number ( "." number ){0,3}` optionally followed by `"-"` and a bounded
platform-local suffix, where each `number` is `0` or a nonzero digit followed by
at most eight more. The value carries no surrounding whitespace and no trailing
newline, for the reason section 2.3.4 gives. An unconstrained string here would
let one observed kernel have arbitrarily many spellings, and identity that admits
many spellings is not identity.

##### `curator-hardened-host-build-v1`

`host.build` is the **kernel build identity**, and it is a closed record rather
than a descriptive string:

```json
{
  "algorithm": "curator-hardened-host-build-v1",
  "identifier": "25A123",
  "content_sha256": "sha256:..."
}
```

It is REQUIRED and MUST NOT be null, absent, or a bare string. A trusted
computing base that claims completeness while reporting no kernel build identity
is `hardened_tcb_identity_invalid`, because two kernels that expose the same
platform and the same release string — a distribution rebuild, a patched
vendor kernel, a locally recompiled image — would otherwise produce the same
record, the same digest, the same cache key, the same receipt, the same marker,
and the same claim.

`identifier` is the immutable build identifier the platform documents, in the
grammar section 6.3 declares for that platform, and it MUST be exactly the value
of that platform's declared **identifier source**. It is what a human reads.

`content_sha256` is what actually separates two kernels. Section 6.3 declares,
per platform, an ordered closed list of **build-identity sources**: named
observations of the running kernel whose bytes an implementation reads on the
host it is about to trust. Initialize SHA-256 with exact ASCII
`curator-hardened-host-build-v1` followed by `0x00`, then append:

```text
uint64be(len(identity))   || identity_utf8   ||
uint64be(len(version))    || version_utf8    ||
uint64be(len(identifier)) || identifier_utf8 ||
uint64be(source_count)    ||
for every declared source, in the declared order:
    uint64be(len(source_name))  || source_name_utf8 ||
    uint64be(len(source_value)) || source_value_bytes
```

Prefix the lowercase digest with `sha256:`. The observed identity, release, and
identifier are inside the digest, so a build digest cannot be carried over to a
host that reports a different tuple. Every variable-length field is framed by its
own length for the reason `curator-build-source-v1` frames its inputs: without
that, two different field lists whose bytes concatenate identically would produce
one hash. The source count is hashed as well, which states the cardinality
explicitly rather than leaving it to be inferred from the framing. The algorithm
is domain-separated so a build identity cannot be confused with a component
digest, a tree digest, a toolchain digest, a TCB digest, or a cache key.

The construction fails closed. A declared source that cannot be read, is empty,
or is unavailable on the host is `hardened_tcb_identity_invalid` reported in
`tcb-identity-verification`, before domain establishment and before any package
byte is exposed. No partial digest is computed, no source is skipped, no cached
or build-time constant is substituted, and the operation MUST NOT degrade to
reporting an identifier without a digest. A platform whose declared sources
cannot be observed is a platform that does not qualify, not a platform that
qualifies with a weaker identity.

What the digest does **not** promise is that a kernel is honest about itself: a
host that lies about every declared source lies inside its own trusted computing
base, which section 3.3 already places outside this profile. What it does
promise is that two materially different kernels, observed truthfully, cannot
produce one `hardened-tcb-v1` record.

#### 2.3.4 `hardened-backend-version-v1`

An enforcement-backend version is compared, not just recorded, so it is a
grammar rather than a string. A value is:

```text
series "-" number ( "." number ){0,3}
```

`series` is the lowercase token section 6.3 declares for the enforcement backend
the record names. The value is exactly those characters: no surrounding
whitespace, and no trailing newline. A pattern anchored with a construct that
also matches before a final newline does not implement this grammar, because it
would give one backend two spellings of one version. Each `number` is `0` or a nonzero decimal digit followed by at
most eight more digits, so no component carries a leading zero and every
component fits an exact integer. A value outside this grammar is invalid.

Two values are comparable only when their `series` tokens are equal. Compare the
numeric components as integers from left to right, treating a missing component
as `0`, so `sandbox-2` and `sandbox-2.0.0` are equal and `cgroup2-6.12` is above
`cgroup2-6.1`. Comparing values across two series is not a lower or higher
result: it is invalid, because a backend's version line has no ordering against
another backend's. Both `tcb.backend.version` and a claim entry's
`minimum_version` use this grammar and the series their own backend declares;
section 8.5 states the comparison a claim MUST satisfy.

#### `curator-hardened-tcb-v1`

The record has one digest, and it is what the hashed build input carries.
Initialize SHA-256 with exact ASCII `curator-hardened-tcb-v1` followed by
`0x00`, then append `uint64be(length)` and the exact `CCJ-1` canonical bytes of
the record, using the canonicalization `protocol/registry.md` defines and
`protocol/core.md` section 9 already uses for build inputs and receipts. Prefix
the lowercase digest with `sha256:`.

The algorithm is domain-separated and length-framed for the same reason
`curator-build-source-v1` is: the digest MUST NOT be confusable with a cache
key, a receipt hash, or any other SHA-256 taken over the same canonical bytes.

Consequently the TCB binds cache reuse, receipt bytes, `receipt_sha256`, the
install marker, and the conformance claim. Section 8 states each binding and
section 8.3 states why the resulting per-host key divergence is intended.

### 2.4 Capability-evidence identity

```json
{"record_version": "hardened-capability-evidence-v1"}
```

Section 6.4 defines the record. It is a distinct record version from the
portable `capability-evidence-v1` record of `protocol/core.md` section 4.2.1;
the two MUST NOT be merged, aliased, or converted into one another.

### 2.5 Enforcement-backend identity

An enforcement backend is named by a closed identifier declared in section 6.3.
It is a member of the closed TCB record, so it is bound wherever that record or
its digest is bound. It has no separate slot of its own.

### 2.6 Identity binding summary

| Identity | Value in this revision | In hashed build input | In receipt bytes | In install marker | In conformance claim | Binds cache reuse |
|---|---|---|---|---|---|---|
| execution policy | `hardened-worker-v1` | yes | yes | yes | yes | yes |
| profile | `hardened-profile-v1` | yes | yes | yes | yes | yes |
| TCB record | `hardened-tcb-v1` | yes, as its `curator-hardened-tcb-v1` digest | yes, as the complete record | yes, as the complete record | yes, as the complete record | yes |
| enforcement backend | section 6.3 | inside the TCB digest | inside the TCB record | inside the TCB record | inside the TCB record | yes |
| capability evidence | `hardened-capability-evidence-v1` | no | no | no | no | no |

The last row is the only result-only identity, and section 6.4 states why: it
reports what was observed in one operation, not what the artifact was produced
under. Every other row is reproducible by a reader from bytes it already holds.

## 3. Threat model

### 3.1 Adversary

The adversary supplies every package byte: manifest values, build-root contents,
Go source, vendored dependency source, embedded inputs, external repository
contents, and the repository build descriptor. The adversary may also observe
the manager's public behavior and may retry an operation arbitrarily often.

The adversary is assumed able to:

- exploit a defect in the Go parser, type checker, compiler, assembler, or
  linker and obtain arbitrary code execution as the compiling process;
- spawn descendants, threads, and detached processes from that position;
- attempt any system call the host permits;
- write, rename, unlink, and link filesystem objects the host permits;
- attempt to reach the network on any address family, including loopback and
  unix-domain endpoints;
- attempt to execute any file it can reach, including a file it just wrote;
- exhaust CPU, memory, descriptors, processes, disk, and diagnostic output; and
- attempt to outlive the operation.

### 3.2 What the profile promises

Under a qualified platform, an adversary in that position MUST NOT be able to:

1. reach any network endpoint (section 5.1);
2. modify the frozen source snapshot or the Go toolchain (section 5.2);
3. write anywhere outside the operation-private build root (section 5.3);
4. exceed the aggregate process, memory, disk, time, and output bounds, or
   survive the operation (section 5.4);
5. execute any program outside the exact fingerprinted allowlist (section 5.5);
   or
6. cause the operation to proceed to a compiler when any of 1 through 5 could
   not be established (section 5.6).

### 3.3 What the profile does not promise

- It does not make adversarial Go source safe, and it does not claim the Go
  toolchain is free of defects. The compile-only rules of `protocol/core.md`
  sections 4.2 and 4.2.2 and of [`SECURITY.md`](../SECURITY.md) remain in force
  and are not relaxed by containment.
- It does not authenticate the compiled artifact. The artifact remains untrusted
  package code, executed later under the consuming environment's own
  authorization policy. `protocol/core.md` section 9.3 continues to govern.
- It does not defend against an adversary who already runs as the manager's
  operating-system principal, as an administrator or root, in the kernel, or
  below the operating system. Such an adversary can replace the supervisor, the
  worker, the markers, and the receipts.
- It does not defend against a compromised or dishonest enforcement backend. A
  backend is trusted computing base, which is why section 2.3 requires it to be
  named.
- It does not promise timing, cache, power, or other side-channel isolation
  between the build domain and the host.
- It does not promise that a qualified platform stays qualified: a host that
  loses a capability between operations rejects the next operation rather than
  degrading it.

### 3.4 Trusted computing base

The following are trusted, and a defect in any of them defeats the profile:

- the installed manager parent, hardened supervisor, and domain-root worker
  bytes, and the code that verifies their identities;
- the domain session framing, authentication, nonce handling, and state machine;
- the capability probes and the enforcement-backend adapters;
- the operating-system kernel primitives those adapters use;
- the fingerprinted `go` launcher and the fingerprinted `GOROOT` tool
  executables;
- source and build-root canonicalization, fingerprinting, and input validation;
- the operation-private roots, the artifact verifier, and the publication path;
  and
- the policy, cache, receipt, marker, and claim canonicalization code.

Every item above is named by the `hardened-tcb-v1` record of section 2.3, and
this correspondence is normative rather than illustrative:

| Trusted item | Where it is named |
|---|---|
| manager parent bytes | `parent_sha256` |
| supervisor bytes | `supervisor_sha256` |
| worker bytes | `worker_sha256` |
| identity verifiers, session state machine, canonicalization, artifact verifier, publication path | inside the parent, supervisor, and worker binaries above, or, when the implementation separates them, as `trusted_components` entries of kind `identity-verifier` or `helper-executable` |
| capability probes and enforcement-backend adapters | inside those binaries, or as `trusted_components` entries of kind `capability-probe` or `enforcement-adapter` |
| the enforcement backend itself | `enforcement_backend` with its observed `backend.version` and `backend.configuration` |
| the operating-system kernel primitives | `host`, whose `identity` is the canonical kernel identity section 6.3 declares for the platform |
| the `go` launcher and `GOROOT` tools | `toolchain` |
| any interpreter, installed package tree, script, shared library, or policy file the implementation depends on | `trusted_components`, each digested by the section 2.3.1 algorithm its kind admits |

An implementation whose trusted base is not fully covered by that record MUST
NOT report the record. This is what makes the concrete-TCB claim of section 2.3
checkable rather than asserted.

## 4. Process graph and the build domain

### 4.1 Fixed graph

```text
manager parent                        (trusted, outside the build domain)
  -> identity-verified hardened supervisor
                                      (trusted, outside the build domain)
       -> domain-root worker          (first process INSIDE the build domain)
            -> fingerprinted <GOROOT>/bin/go
                 -> fingerprinted regular executables below
                    <GOROOT>/pkg/tool/<GOHOSTOS>_<GOHOSTARCH>/
```

The graph has exactly five node kinds and no others. The supervisor exists
because creating a containment object and applying its controls require
operations that the contained domain MUST NOT be able to perform; a process
cannot be both the creator of its own confinement and confined by it from its
first instruction.

The three trusted nodes are the only actors in section 7.2, and each phase
names exactly one of them:

| Node | In the build domain | Performs |
|---|---|---|
| manager parent | no | profile selection, qualification, toolchain probe and snapshot freeze, TCB verification, cache lookup, graph validation, build permit, artifact verification, identity re-verification, publication |
| hardened supervisor | no | capability probe, domain establishment, domain entry, domain teardown |
| domain-root worker | yes | the in-domain guarantee self-test, the one `go list`, and the one `go build` |

The supervisor creates the domain and then launches the worker into it, so the
worker is the first process that can observe the domain from inside. Every
phase performed by the worker is therefore strictly after domain entry. That
ordering is normative and mechanically checked; see section 7.2.

The parent and the supervisor MAY be the same executable in two different fixed
hidden modes, provided each mode's identity is verified independently. The
supervisor and the worker MUST NOT be a shell, an interpreter invocation, a
package file, a `PATH` lookup, a manifest value, a descriptor value, an
environment value, or a user option. `protocol/core.md` section 4.2.1's
statement that no package input selects a program applies here unchanged and is
extended by section 9.

### 4.2 Domain membership

Every process created by any process in the build domain MUST itself be in the
build domain. Membership MUST NOT be renounceable from inside: a contained
process MUST NOT be able to detach, re-parent out, daemonize out, join another
domain, or create a process that outlives the domain.

### 4.3 Session

One hardened operation runs exactly one domain session, and the session performs
exactly one `go list` and exactly one `go build`, using exactly the two argument
vectors fixed by `protocol/core.md` section 4.2. In order, the session:

1. proves the worker's identity to the supervisor and acknowledges a fresh
   session nonce;
2. performs the in-domain guarantee self-test of section 7.2 and returns its
   result, before opening, reading, mapping, or executing any package byte;
3. performs the one `go list`;
4. returns bounded output and waits;
5. accepts exactly one authenticated build permit issued by the parent after the
   parent has applied every dependency, containment, directive, and native-input
   rejection of `protocol/core.md` section 4.2 and `profiles/manager.md` section
   2.3 to the complete stream; and
6. performs the one `go build`.

Any other message, any repetition, any reordering, and any additional executable,
shell, VCS, module download, generator, test, run, or tool request tears the
session down without starting a compiler and reports
`hardened_domain_protocol_invalid`. Step 3 MUST NOT begin until the supervisor
has accepted the step 2 result.

### 4.4 The session channel

The domain session channel MUST be established before domain entry, MUST consist
only of descriptors or handles the supervisor pre-opened and explicitly passed,
and MUST NOT be a network endpoint, a filesystem path reachable from inside the
domain, or any object the domain can re-open, re-bind, duplicate to another
peer, or use to write outside the private build root. Establishing the channel
MUST NOT weaken section 5.1.

## 5. The six guarantees

Each guarantee below is a kernel- or hypervisor-enforced property of the build
domain. For each, the "not sufficient" list names mechanisms that a conforming
implementation MUST NOT present as establishing the guarantee, because the
contained adversary can defeat or change them.

### 5.1 `total-network-denial`

Every process in the build domain is denied every network operation: socket
creation, bind, connect, listen, accept, sendto, sendmsg, and any equivalent, on
every address family, including loopback, IPv4, IPv6, unix-domain endpoints that
lead outside the domain, and any other transport the host provides. No inherited,
pre-opened, or pre-connected endpoint survives domain entry.

Not sufficient: `GOPROXY=off`, `GOVCS=*:off`, `GOFLAGS`, vendor-only module
mode, an empty `PATH`, an unset proxy environment, a DNS blackhole, a userspace
resolver stub, a firewall rule the domain can change, or a post-hoc check that
no connection was observed.

### 5.2 `read-only-source-and-toolchain`

The frozen source snapshot and the fingerprinted `GOROOT` are presented to every
process in the build domain through a view the kernel refuses to mutate. Write,
create, rename, unlink, truncate, permission change, ownership change, extended
attribute change, and hard-link creation against those views are denied
regardless of the contained process's own credentials.

Not sufficient: filesystem permissions or an access-control list the domain can
change; a copy the manager promises not to write to; re-verifying the snapshot
digest after the fact.

Post-operation identity re-verification of the snapshot, the toolchain, the
supervisor, and the worker remains REQUIRED by section 7, but it is a detection
mechanism layered on top of this guarantee, never a substitute for it.

### 5.3 `private-build-root-only-writes`

Every mutating filesystem operation by every process in the build domain
succeeds only below the operation-private build root, and is denied everywhere
else. This covers writes, creates, renames, unlinks, links, permission and
ownership changes, extended attributes, device-node creation, and filesystem
IPC objects. Paths outside the declared views MUST NOT be reachable from inside
the domain at all.

The operation-private build root, the private user, configuration, cache,
temporary, staging, and output roots, and every view boundary are resolved
independently of package data.

Not sufficient: a private temporary directory the domain can escape by absolute
path; a `TMPDIR` value; a manager promise to write only to private roots; a
post-hoc scan for unexpected files.

### 5.4 `hard-aggregate-descendant-resource-bounds`

Every bound below is over the whole build domain in aggregate, not per process,
and covers every descendant:

| Quantity | Bound |
|---|---|
| wall-clock time | aggregate deadline over the domain |
| CPU time | aggregate limit over the domain |
| resident and committed memory | aggregate limit over the domain |
| live processes and threads | aggregate limit over the domain |
| open descriptors or handles | aggregate limit over the domain |
| bytes written below the private build root | aggregate limit over the domain |
| combined standard output and standard error | aggregate limit over the domain |

For each quantity, either the host accounts for and enforces the bound itself,
or the supervisor accounts for it from outside the domain and enforces it by
destroying the domain. Both forms are admissible, and exactly one property makes
them equivalent: **no process in the domain can evade the accounting, prevent
the enforcement, or survive it.** That property is supplied by
`domain-membership-enforcement` and `domain-atomic-termination`, which is why
section 6.2 requires both for this guarantee.

Exceeding any bound MUST destroy the entire domain as a unit, not the offending
process alone, and the operation MUST NOT return, publish, or report success
while any domain member is alive.

Not sufficient: a per-process `RLIMIT`; a parent-side deadline that kills only
the direct child, or that a descendant can outlive by detaching; a periodic
sweep for stray processes; an accounting-only control with no enforcement; a
bound over a process group or session that a contained process can leave.

This is the exact point where the portable profile stops. Its parent-enforced
deadline and output bounds are supervisor-side accounting without unescapable
membership or atomic termination, so a detached descendant escapes them.

### 5.5 `exact-executable-allowlisting`

The host denies execution of every program except the exact fingerprinted paths
the manager selected: `<GOROOT>/bin/go` and the regular executables below
`<GOROOT>/pkg/tool/<GOHOSTOS>_<GOHOSTARCH>/`. The allowlist is by exact path and
verified identity. A file written inside the private build root MUST NOT be
executable from inside the domain, and neither a shell, an interpreter, a
dynamic loader invoked as a program, a VCS client, an external compiler,
assembler or linker, nor any other host program may start.

Not sufficient: an empty `PATH`; a manager promise to start nothing else; a
`noexec` mount over only part of the reachable filesystem; identity verification
of the programs the manager itself starts.

The manager's own selection and per-program identity verification of
`protocol/core.md` section 4.2 remain REQUIRED. This guarantee adds the property
that a program the manager did not select cannot start at all.

### 5.6 `fail-closed-capability-preflight`

Every capability class of section 6.1 is actively probed, on this host, in this
operation, before the build domain is entered. If any probe fails, is
inconclusive, is unsupported, or reports a result the implementation cannot
attribute to an actual observation, the operation rejects before domain entry,
starts no Go process, and publishes nothing.

Not sufficient: a host label; a build-time constant; an operating-system version
comparison alone; a configuration file; a cached result from an earlier
operation; a probe performed after domain entry; a probe of a subset of the
classes.

## 6. Capability classes, evidence, and platform declarations

### 6.1 The exhaustive capability-class inventory

Inventory version `hardened-capability-inventory-v1`. Its normative authority is
the `capability_inventory` section of
[`conformance/hardened/v1/vectors/hardened-execution-profile.json`](../conformance/hardened/v1/vectors/hardened-execution-profile.json).
The inventory is exhaustive: a manager MUST probe exactly these classes, MUST
NOT probe, apply, or report a class outside it, and MUST NOT treat a class as
optional.

| Capability class | Requirement |
|---|---|
| `domain-membership-enforcement` | every descendant of the domain-root worker is a domain member and cannot renounce membership |
| `domain-atomic-termination` | the whole domain is destroyed as one unit, with no survivor and no reparenting |
| `network-syscall-denial` | the kernel denies every network operation on every address family for every domain member |
| `preexisting-endpoint-revocation` | no inherited socket, handle, or connected endpoint is usable after domain entry |
| `read-only-source-view` | the frozen source snapshot is presented through a kernel-enforced read-only view |
| `read-only-toolchain-view` | the fingerprinted `GOROOT` is presented through a kernel-enforced read-only view |
| `write-path-confinement` | every mutating filesystem operation outside the private build root is denied by the kernel |
| `filesystem-view-restriction` | paths outside the declared views are unreachable from inside the domain |
| `exec-path-allowlist` | execution is denied for every path outside the exact fingerprinted allowlist |
| `aggregate-resource-bounds` | the host accounts for and enforces every bound of section 5.4 over the domain in aggregate |
| `active-capability-probe` | every class above is actively probed on this host in this operation before domain entry |

Adding, removing, or re-scoping a class requires a new capability-inventory
version, and, because the guarantee set would change, a new profile identity and
a new execution-policy identity per section 2.2.

A probe MAY establish and destroy an operation-private **probe domain** in order
to observe whether a class is actually available. A probe domain contains no
package byte, runs no Go process, and produces no artifact. It is not the build
domain: creating one satisfies neither `domain-establishment`, nor
`domain-entry`, nor the `in-domain-guarantee-self-test` of section 7.2, and its
teardown is not `domain-teardown`.

### 6.2 Guarantee-to-class mapping

A guarantee is established only when every class mapped to it is available and
applied. This mapping is normative and exhaustive.

| Guarantee | Required capability classes |
|---|---|
| `total-network-denial` | `network-syscall-denial`, `preexisting-endpoint-revocation`, `domain-membership-enforcement` |
| `read-only-source-and-toolchain` | `read-only-source-view`, `read-only-toolchain-view`, `filesystem-view-restriction` |
| `private-build-root-only-writes` | `write-path-confinement`, `filesystem-view-restriction`, `domain-membership-enforcement` |
| `hard-aggregate-descendant-resource-bounds` | `aggregate-resource-bounds`, `domain-membership-enforcement`, `domain-atomic-termination` |
| `exact-executable-allowlisting` | `exec-path-allowlist`, `domain-membership-enforcement` |
| `fail-closed-capability-preflight` | `active-capability-probe` |

### 6.3 Platform declarations

A platform declaration binds one platform to one enforcement backend, the public
primitives that backend would use per capability class, a qualification status,
and the task that owns qualification. The declarations are normative; their
executable form is the `platform_declarations` section of
`conformance/hardened/v1/vectors/hardened-execution-profile.json`.

| Platform | Enforcement backend | Canonical host identity | Backend version series | Qualification status |
|---|---|---|---|---|
| `linux` | `linux-namespace-seccomp-v1` | `linux` | `cgroup2` | `unqualified` |
| `macos` | `macos-sandbox-v1` | `darwin` | `sandbox` | `unqualified` |
| `windows` | `windows-appcontainer-job-v1` | `windows-nt` | `appcontainer` | `unqualified` |

The canonical host identity is the kernel identity a `hardened-tcb-v1` record
MUST report in `host.identity` for that platform, per section 2.3.3. It is a
kernel identity and deliberately not a `GOOS` value: `windows-nt` names the
kernel that enforces, where `windows` names a Go target.

The backend version series is the `hardened-backend-version-v1` token of section
2.3.4 that both `tcb.backend.version` and a claim's `minimum_version` MUST carry
for that backend. Versions from two series are not comparable, so a claim cannot
qualify a Linux host by quoting a macOS sandbox version.

#### Kernel build identity per platform

Each platform declares the immutable build identifier grammar and the ordered,
closed list of build-identity sources that section 2.3.3 hashes into
`host.build.content_sha256`. The **identifier source** is the one whose exact
value `host.build.identifier` MUST carry.

| Platform | Identifier grammar | Identifier source | Ordered build-identity sources |
|---|---|---|---|
| `linux` | lowercase hex, 32 to 128 digits | `kernel.build-id` | `kernel.build-id`, `kernel.osrelease`, `kernel.version-string` |
| `macos` | `[0-9]{1,3}` `[A-Z]` `[0-9]{1,6}` optional lowercase letter | `kern.osversion` | `kern.osversion`, `kern.osproductversion`, `kern.version` |
| `windows` | `[0-9]{1,7}` `.` `[0-9]{1,7}` | `kernel.current-build-and-ubr` | `kernel.current-build-and-ubr`, `kernel.build-lab-ex`, `kernel.image-file-version` |

Each source names one observation of the running kernel:

- **`kernel.build-id`** — the `NT_GNU_BUILD_ID` note of the running kernel image,
  lowercase hex, as the kernel exposes it in `/sys/kernel/notes`.
- **`kernel.osrelease`** — the exact bytes of `/proc/sys/kernel/osrelease`.
- **`kernel.version-string`** — the exact bytes of `/proc/version`, which carry
  the build number, the compiler, and the build timestamp.
- **`kern.osversion`** — the Darwin build identifier the kernel reports.
- **`kern.osproductversion`** — the product version the kernel reports.
- **`kern.version`** — the full kernel version string, which carries the xnu
  version, the build configuration, and the build timestamp.
- **`kernel.current-build-and-ubr`** — `CurrentBuildNumber` and `UBR` joined by
  `.`, as the kernel's own version state reports them.
- **`kernel.build-lab-ex`** — the `BuildLabEx` value, which carries the build,
  the revision, the branch, and the build date.
- **`kernel.image-file-version`** — the file-version resource of the running
  kernel image.

The list is closed per platform and ordered: an implementation reads exactly
these, in exactly this order, and a source it cannot read is a rejection under
section 2.3.3 rather than a source it omits. Section 11 requires the owning
qualification task to confirm, natively, that every declared source is readable
on that platform and that replacing the kernel moves at least one of them. A
platform whose declared sources do not distinguish two materially different
kernels MUST NOT be advanced to `qualified`.

Candidate primitive bindings, and the classes that currently block
qualification, are:

- **`linux-namespace-seccomp-v1`** — user, mount, PID, network, IPC, UTS, and
  cgroup namespaces for domain membership; read-only bind mounts for the source
  and toolchain views; an empty network namespace; `seccomp-BPF` with
  `no_new_privs` for the execution allowlist and residual syscall denial; a
  size-bounded private filesystem, such as a size-limited `tmpfs` or a
  quota-backed subvolume, for the aggregate write-byte bound; and cgroup v2
  `pids.max`, `memory.max`, and CPU limits with `cgroup.kill` for the remaining
  aggregate bounds and atomic termination. No class is currently identified as
  unreachable on this platform; qualification nonetheless requires native
  adversarial evidence and a declared minimum kernel version and required
  configuration, and is owned by `TASK-260728-3ihgfq` for Curator and
  `TASK-260728-ns5yk7` for csk.
- **`macos-sandbox-v1`** — a `(deny default)` sandbox profile with explicit
  `file-read*` allowances for the snapshot and `GOROOT`, `file-write*` allowance
  restricted to the private build root, `(deny network*)`, and
  `(deny process-exec*)` with exact-path allowances; process-group and session
  teardown; and `RLIMIT_*` for per-process bounds. Blocking classes today:
  `domain-membership-enforcement`, `domain-atomic-termination`, and
  `aggregate-resource-bounds`, because the platform exposes no unescapable
  per-operation process domain — a contained process can leave the process group
  or session — and no aggregate private storage, memory, or process-count
  accounting. That is the same `no-private-aggregate-domain` finding the portable
  `rc5-native-control-inventory-v1` inventory already records. The public dynamic
  sandbox interface is deprecated and the packaged App Sandbox path is
  entitlement- and packaging-dependent, so a qualifying implementation MUST state
  which supported delivery it depends on. Owned by `TASK-260728-3n67j6` for
  Curator and `TASK-260728-jis03f` for csk.
- **`windows-appcontainer-job-v1`** — an AppContainer or LPAC token with a
  per-operation package SID and no network capability SIDs; a Job Object with
  `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, `ActiveProcessLimit`, `JobMemoryLimit`,
  `JobTime`, and `PROC_THREAD_ATTRIBUTE_JOB_LIST` for unescapable membership,
  atomic termination, and aggregate process, memory, and CPU bounds; an explicit
  handle-inheritance list; and access-control entries that grant the package SID
  read-only access to the snapshot and `GOROOT` and write access only below the
  private build root. Blocking classes today: `exec-path-allowlist`, because
  child-process creation policy is all-or-none and exposes no supported per-path
  execution allowlist for a contained token, and `aggregate-resource-bounds`,
  because no supported facility bounds the bytes a job writes below the private
  build root — the same gap the portable inventory records as an unavailable
  `per-file-size-limit`. Owned by `TASK-260728-1v71sx` for Curator and
  `TASK-260728-2hcmtg` for csk.

A declaration MUST NOT be advanced to `qualified` by asserting a primitive
binding. It is advanced only by native adversarial evidence that exercises every
guarantee on that platform, as required by section 11.

An implementation MUST NOT invent a platform, a backend, or a class outside
these declarations, and MUST NOT claim a guarantee on the basis of a mechanism
the declaration does not name.

### 6.4 The closed hardened capability-evidence record

A hardened operation emits exactly one record:

```json
{
  "record_version": "hardened-capability-evidence-v1",
  "hardened_profile": "hardened-profile-v1",
  "execution_policy": "hardened-worker-v1",
  "platform": "linux",
  "enforcement_backend": "linux-namespace-seccomp-v1",
  "qualification_status": "unqualified",
  "outcome": "rejected",
  "rejected_before": "domain-entry",
  "diagnostic": "hardened_profile_unsupported",
  "capabilities": [
    {"name": "domain-membership-enforcement", "availability": "unprobed", "status": "not-applied", "probed_at": "pre-domain-entry"}
  ],
  "guarantees": [
    {"name": "total-network-denial", "established": false}
  ]
}
```

The record contains exactly `record_version`, `hardened_profile`,
`execution_policy`, `platform`, `enforcement_backend`, `qualification_status`,
`outcome`, `rejected_before`, `diagnostic`, `capabilities`, and `guarantees`.
`rejected_before` and `diagnostic` are `null` when `outcome` is `established`.

`capabilities` contains exactly one entry per capability class of section 6.1,
and each entry contains exactly `name`, `availability`, `status`, and
`probed_at`. `availability` is `available`, `unavailable`, or `unprobed`.
`status` is `applied` or `not-applied`. `probed_at` is `pre-domain-entry`.

`guarantees` contains exactly one entry per guarantee of section 5, and each
entry contains exactly `name` and `established`.

Each condition below is an error, not a permitted variation:

| Condition | Diagnostic |
|---|---|
| an `available` capability reported with a status other than `applied` | `hardened_evidence_invalid` |
| an `unavailable` or `unprobed` capability reported as `applied` | `hardened_evidence_invalid` |
| a missing, duplicated, extra, or unknown capability or guarantee entry | `hardened_evidence_invalid` |
| an unknown `record_version` | `hardened_evidence_invalid` |
| `outcome: "established"` while any capability is not `applied` or any guarantee is not `established` | `hardened_evidence_invalid` |
| `outcome: "rejected"` without both `rejected_before` and `diagnostic` | `hardened_evidence_invalid` |
| a guarantee reported `established` while any class mapped to it by section 6.2 is not `applied` | `hardened_evidence_invalid` |
| an availability value that was not obtained by a probe in this operation | `hardened_evidence_invalid` |
| a portable `capability-evidence-v1` record emitted for a hardened operation, or this record emitted for a portable operation | `hardened_profile_claim_forbidden` |
| an `execution_policy` other than `hardened-worker-v1`, or a `hardened_profile` other than `hardened-profile-v1` | `hardened_profile_claim_forbidden` |

The record is result-only. It is exposed in install, dry-run plan, and status
results, and it MUST NOT appear in a cache key, a receipt input, an install
marker, or a conformance claim.

## 7. Ordering and the fail-closed boundary

### 7.1 Profile selection

The hardened profile is selected by operator configuration or by a manager
deployment mode. It MUST NOT be selected, requested, hinted, weakened, or
disabled by a manifest value, a descriptor value, a build root, a source file,
an environment value read from package data, or any other package-controlled
byte.

When the hardened profile is selected, a manager MUST NOT silently fall back to
`manager-worker-v1`. If the hardened profile cannot be established, the
operation rejects. An operator who wants the portable contract selects the
portable profile explicitly, and that operation is a portable operation in every
respect, including its cache key.

### 7.2 Ordered phases

This table is the **single normative ordered phase list** for the hardened
profile. [`profiles/manager-hardened.md`](../profiles/manager-hardened.md)
attaches manager obligations to these phase names and MUST NOT publish an
ordering of its own; the `ordered_phases` section of
[`conformance/hardened/v1/vectors/hardened-execution-profile.json`](../conformance/hardened/v1/vectors/hardened-execution-profile.json)
is its executable form. All three MUST agree exactly.

A hardened operation MUST perform these phases in exactly this order. Every
phase names the one actor that performs it, and the actor determines what the
phase can possibly do.

| # | Phase | Actor | Rejection diagnostic |
|---|---|---|---|
| 1 | `profile-selection` | manager parent | `hardened_profile_claim_forbidden` |
| 2 | `platform-qualification` | manager parent | `hardened_profile_unsupported` |
| 3 | `capability-probe` | hardened supervisor | `hardened_capability_unavailable` |
| 4 | `toolchain-probe-and-snapshot-freeze` | manager parent | inherits `protocol/core.md` sections 4.2 and 8 |
| 5 | `tcb-identity-verification` | manager parent | `hardened_tcb_identity_invalid` |
| 6 | `build-input-and-cache-lookup` | manager parent | inherits `protocol/core.md` section 9.3 |
| 7 | `domain-establishment` | hardened supervisor | `hardened_domain_establishment_failed` |
| 8 | `domain-entry` | hardened supervisor | `hardened_domain_establishment_failed` |
| 9 | `in-domain-guarantee-self-test` | domain-root worker | `hardened_domain_establishment_failed` |
| 10 | `go-list` | domain-root worker | `hardened_domain_breach_detected` |
| 11 | `parent-graph-validation` | manager parent | inherits `profiles/manager.md` section 2.3 |
| 12 | `build-permit` | manager parent | `hardened_domain_protocol_invalid` |
| 13 | `go-build` | domain-root worker | `hardened_domain_breach_detected` |
| 14 | `artifact-verification` | manager parent | inherits `protocol/core.md` section 9 |
| 15 | `domain-teardown` | hardened supervisor | `hardened_domain_breach_detected` |
| 16 | `identity-reverification` | manager parent | `hardened_tcb_identity_invalid` |
| 17 | `publication` | manager parent | inherits `profiles/manager.md` section 2.5 |

The list is executable, not merely enumerated. The following relations are
normative and are checked against the list itself:

- `capability-probe` precedes `domain-establishment`: a control cannot be
  applied before the host is known to provide it.
- `tcb-identity-verification` precedes `build-input-and-cache-lookup`: the
  cache key carries the TCB digest of section 2.3, so the TCB must be verified
  before the key exists.
- `build-input-and-cache-lookup` precedes `domain-establishment`: an exact
  verified hit compiles nothing, so phases 7 through 16 do not run and the
  operation continues at `publication`. Nothing ran that could have changed a
  trusted component, so there is nothing to re-verify.
- `domain-entry` precedes `in-domain-guarantee-self-test`: the domain-root
  worker is the first process inside the domain, so no actor can test from
  inside before it exists.
- `in-domain-guarantee-self-test` precedes `go-list`: the package-exposure
  boundary.
- `parent-graph-validation` precedes `build-permit` and `build-permit` precedes
  `go-build`.
- `domain-teardown` precedes `identity-reverification`: re-verifying while a
  domain member may still be running would prove nothing about the state at the
  end of the operation.
- `identity-reverification` precedes `publication`, and therefore
  `domain-teardown` precedes `publication`: nothing is published under a trusted
  computing base that has not been proved unchanged, and nothing is published
  while a domain member is alive.

**No phase performed by a process inside the build domain may precede
`domain-entry`.** That is what makes the pre-package state machine performable:
phases 1 through 8 are performed by uncontained trusted actors, and the first
contained actor — created by phase 8 — acts only from phase 9 onward.

#### The in-domain guarantee self-test

Phase 9 is performed by the domain-root worker, from inside the domain it is
contained by, and verified by the supervisor over the pre-opened session
channel of section 4.4. The worker MUST attempt, and MUST observe the kernel
deny, at least one representative operation for each guarantee of section 5.

Until the supervisor accepts that result, the worker MUST NOT open, read, map,
stat, or execute any path below the source view, MUST NOT start a Go process,
and MUST NOT accept any other session message. The domain therefore holds no
package byte that any process has observed when the self-test runs, even though
the read-only source view is already installed.

A self-test that cannot be performed is a failure, not a pass. On failure the
supervisor tears the domain down, the operation rejects with
`hardened_domain_establishment_failed`, no compiler starts, and nothing is
published. There is no partial mode and no fallback.

#### End-of-operation re-verification

Phase 15 destroys the domain as a unit and **joins** it, so when phase 16 begins
no domain member is running and none can start: every process that could have
touched a trusted component has exited and been reaped. Only then does the
manager parent re-verify.

Phase 16 is not a spot check of a few binaries. The manager parent **recomputes
the complete `hardened-tcb-v1` record of section 2.3** from the same canonical
pinned identities phase 5 used — the same paths, resolved the same way, with the
same substitution rejections — and requires the recomputed record to be
byte-identical to the one phase 5 built and its `curator-hardened-tcb-v1` digest
to equal the digest the hashed build input carries. Every mutable member is
therefore rechecked, not only the ones an implementation finds convenient:

| Re-verified | Includes |
|---|---|
| `parent_sha256`, `supervisor_sha256`, `worker_sha256` | the three installed binaries, re-resolved without following links |
| `toolchain` | the fingerprinted `go` launcher and `GOROOT` tool executables |
| `host` | the observed kernel identity, release, and the `curator-hardened-host-build-v1` build identity, recomputed from its declared sources |
| `backend` | the observed enforcement-backend version and every configuration setting the qualification depends on |
| `platform`, `enforcement_backend` | the platform and mechanism the record attributes the artifact to |
| `trusted_components` | every component of section 2.3.1, re-digested by the algorithm its kind admits |
| the frozen source snapshot | under the same rule section 5.2 applies throughout |

Re-verifying a subset is not re-verification: a member phase 5 placed in the
hashed record and phase 16 does not recheck is a member that may change during
the operation while publication still attributes the artifact to the phase-5
digest. Restating the phase-5 record, or comparing the phase-5 digest against
itself, does not discharge this obligation either; the values MUST be observed
again.

Any difference — in any member, of any size — is `hardened_tcb_identity_invalid`.
The operation rejects before `publication`, nothing is published, no cache entry
is written, no marker is updated, and the installation is left exactly as it was
when the operation began.

### 7.3 The failure boundary

The hardened profile has two boundaries, and this specification states them
separately rather than conflating them.

**Before domain entry — phases 1 through 7.** No containment object holding a
package byte exists yet:

- If the requested profile mixes hardened and portable identities, or asks for a
  silent fallback, the operation rejects in `profile-selection` with
  `hardened_profile_claim_forbidden`. If package data attempted to reach the
  selection, it rejects with `hardened_package_influence_forbidden` instead.
- If the platform is not qualified for the hardened profile, the operation
  rejects in `platform-qualification` with `hardened_profile_unsupported`.
- If any capability class is unavailable, inconclusive, or unprobed, the
  operation rejects in `capability-probe` with
  `hardened_capability_unavailable`.
- If the TCB identities do not verify, the operation rejects in
  `tcb-identity-verification` with `hardened_tcb_identity_invalid`.
- If the domain cannot be created or a control cannot be applied, the operation
  rejects in `domain-establishment` with
  `hardened_domain_establishment_failed`.

**Before package exposure — phases 8 and 9.** The domain exists and holds one
trusted, fingerprinted process that has read no package byte:

- If entry fails, or the self-test does not observe the expected denial, the
  operation rejects with `hardened_domain_establishment_failed`.

Every rejection in either group happens before `go list`, before `go build`,
before any compiler, and before any package byte is read by any process in the
domain. Every one of them publishes nothing, mutates no installation, consumer,
marker, shim, or cache state, and leaves the installation byte-for-byte as it
was.

Every capability, qualification, and identity rejection is in the first group,
so an unsupported host never reaches the point where a domain is created.

There is no partial hardened mode. A guarantee that cannot be established is
never reported as best-effort, never downgraded to a warning, and never
compensated for by a portable mechanism.

### 7.4 Breach handling

If, after domain entry, the implementation observes a guarantee violation — a
domain escape, a write outside the private build root, an exec outside the
allowlist, a network operation that succeeded, an exceeded aggregate bound, or a
surviving domain member — it MUST tear the domain down, reject with
`hardened_domain_breach_detected`, publish nothing, and MUST NOT reuse, adopt,
cache, or record any byte produced by that operation.

## 8. Cache, receipt, marker, and claim separation

### 8.1 Cache identity

The logical cache key is computed exactly as in `protocol/core.md` sections 9.1
and 9.2, over the canonical hardened build input of section 2.2 — the portable
input with the hardened `execution_policy` value and the closed `hardened`
member carrying the profile identity and the `curator-hardened-tcb-v1` digest.

Consequently, for one identical source, command, target, and toolchain, these
five inputs produce five different keys and none of them aliases another. Their
executable form is
[`conformance/hardened/v1/vectors/hardened-identity-separation.json`](../conformance/hardened/v1/vectors/hardened-identity-separation.json).

| Input | Distinguished by | Valid hardened input |
|---|---|---|
| pre-revision rc.4 candidate | no execution policy at all | no |
| portable | `manager-worker-v1` | no |
| rc.5 reserved policy slot only | `hardened-worker-v1` and nothing else | no |
| hardened | profile identity and TCB digest A | yes |
| hardened, after a manager update | profile identity and TCB digest B | yes |

**Cache reuse is bound to the profile identity and to the concrete trusted
computing base.** On lookup a manager recomputes the key from the profile
identity of this revision and the TCB record it verified in
`tcb-identity-verification`. An entry produced under another execution policy,
another profile revision, or another trusted computing base therefore has a
different key and is structurally a miss; there is nothing to relabel.

In addition, a manager MUST treat as a miss any entry whose receipt does not
carry a `hardened-tcb-v1` record byte-identical to the one it verified for this
operation, and MUST NOT adopt, upgrade, downgrade, re-label, or re-sign such an
entry in place. A manager that implements both profiles MUST keep their entries
logically disjoint and MUST revalidate the protected-cache boundary of
`protocol/core.md` section 9.3 for each profile independently.

The hardened capability-evidence record does not participate in the cache key
or in the hit comparison.

### 8.2 Receipts

A hardened local `go-v1` build writes **build receipt schema 3**. A hardened
external `go-repository-v1` build writes **build receipt schema 4**. Both keep
the receipt structure of `protocol/core.md` sections 9.1 and 9.2 — schema
version, logical cache key, complete build input, and artifact path, SHA-256,
and byte length — and both add one member:

```json
{"tcb": {"record_version": "hardened-tcb-v1", "...": "..."}}
```

A hardened receipt therefore binds all three identities: the execution policy
and the profile identity inside the input, the TCB as the complete record plus
its digest inside the input. A reader MUST reject a receipt whose
`input.hardened.tcb.content_sha256` is not the `curator-hardened-tcb-v1` digest
of its own `tcb` record, and MUST reject a receipt whose `cache_key` is not the
digest of its own input.

Receipt schemas 1 and 2 remain exactly as candidate `1.0.0-rc.5` defines them
and MUST NOT be widened. A reader that does not implement the hardened profile
MUST reject receipt schema 3 and 4 as unsupported receipt identities under
`protocol/core.md` section 9.3; it MUST NOT parse them leniently, convert them,
or treat them as schema 1 or 2.

`receipt_sha256` is computed exactly as in `protocol/core.md` section 9.1 over
the exact stored canonical bytes, so it covers the TCB record as well.

The hardened capability-evidence record MUST NOT appear in a receipt. It
reports what one operation observed, not what the artifact was produced under.

### 8.3 Why the trusted computing base is hashed

Hashing the TCB digest makes one source, toolchain, and contract produce a
different key on each trusted computing base, and therefore after a manager
update that changes the supervisor or worker bytes. That divergence is intended
and is the point of the binding.

An artifact carries exactly the guarantees of the trusted computing base that
produced it. If a supervisor is updated — including to fix a containment defect
— then reusing an artifact built under the previous supervisor would silently
attribute this revision's guarantees to a build that never ran under them. The
fail-closed answer is the same one section 7 gives everywhere else: rebuild
rather than assume. A hardened cache miss costs a compile; a wrong attribution
costs the guarantee.

This is not the case `decisions/0006` rejected. That decision kept *per-operation
capability evidence* out of portable cache identity, because evidence is an
observation and a reader must not read a cache key as capability proof. The
same rule still holds here: section 6.4's record stays result-only. What is
hashed is not evidence but identity — which trusted code, which backend, which
toolchain — which a reader can verify independently and which does not vary
within one operation.

The residual risk in the other direction — a host that silently loses a
capability between operations — is answered by section 7, which re-probes and
re-establishes every guarantee on every operation.

### 8.4 Install markers

A hardened installation writes **install marker schema 4**. Its build records
carry `execution_policy: "hardened-worker-v1"`, the profile identity, and the
complete TCB record, in addition to the receipt schema version, cache key,
`receipt_sha256`, artifact digest, and artifact path.

Those three identities MUST be the ones the recorded build actually used: the
marker's `cache_key` MUST be reproducible from a build input carrying the
marker's own `execution_policy`, `hardened_profile`, and
`curator-hardened-tcb-v1(tcb)`. A marker that reports one trusted computing
base beside a key produced under another is invalid, not merely inconsistent.

Marker schema 4 is written for a hardened installation of a manifest schema-6
or schema-7 package alike, so `skill_schema_version` is `6` or `7`. That
replaces the portable rule of `profiles/manager.md` section 2.2 — marker 2 for
schema 1 through 6, marker 3 for schema 7 — for hardened operations only,
because a marker 2 or 3 build record cannot express the hardened identities.
Manifest schemas 1 through 5 have no build commands, so they never produce a
hardened marker.

Marker schemas 1, 2, and 3 keep their exact candidate `1.0.0-rc.5` shapes and
MUST NOT be widened. A marker-v4 build record MUST NOT appear in a marker of
schema 1, 2, or 3, and a portable build record MUST NOT carry a hardened
profile or TCB identity.

A marker MUST NOT record a hardened build record for an operation that did not
establish the hardened domain. Doing so is `hardened_profile_claim_forbidden`.

### 8.5 Conformance claims

A hardened claim uses **conformance claim schema 4**. It carries the hardened
profile identity, the execution-policy identity `hardened-worker-v1`, the
enforcement backend per operating system, the TCB record, the capability
inventory version, and the hardened suite digest.

A claim declares exactly one enforcement-backend entry per operating system it
claims, and each entry carries the backend, the minimum version, and the
required configuration as closed `{setting, required_value}` records rather
than prose. Three relations bind the declared qualification to the trusted
computing base the claim names:

- the claim's `tcb.platform` MUST be an operating system the claim itself
  declares, and the entry for that operating system MUST name exactly the
  claim's `tcb.enforcement_backend`;
- every `required_configuration` setting of that entry MUST appear in
  `tcb.backend.configuration` with exactly the required value; and
- the observed `tcb.backend.version` MUST be at or above that entry's
  `minimum_version` under the `hardened-backend-version-v1` comparison of
  section 2.3.4.

The third relation is a comparison, not a string match, and it is checked rather
than declared. `minimum_version` carries the same series token as the entry's
own backend, which the schema enforces, so the two values are always comparable;
a malformed version on either side, a version from another series, or an
observed version below the minimum makes the claim invalid. A claim that
declares a qualification its own trusted computing base does not satisfy is
invalid, not merely optimistic.

Claim schema 3 admits only `manager-worker-v1` and therefore cannot express a
hardened claim; it MUST NOT be widened. Claim schema 4 admits only
`hardened-worker-v1` and therefore cannot express a portable claim. The two are
structurally disjoint in both directions.

A claim-4 operating system MUST be a platform whose declaration in section 6.3
is `qualified` in the revision the claim names. Because every declaration in
`hardened-profile-v1` is `unqualified`, **no conforming claim-4 document can be
emitted against this revision**, and the candidate metadata records that as
`claims_emitted: []`.

## 9. Package-influence exclusions

Package-controlled bytes are compiler input and nothing else. In a hardened
operation they MUST NOT select, modify, weaken, disable, widen, or observe:

- the hardened profile selection, the profile identity, or the execution-policy
  identity;
- the trusted-computing-base record, any of its members, or its
  `curator-hardened-tcb-v1` digest;
- the supervisor or worker executable, its hidden mode, or its identity;
- the enforcement backend, the build domain, its membership, its lifetime, or
  its teardown;
- any capability probe, capability class, guarantee, self-test, or evidence
  record;
- the source, toolchain, or write views, the private roots, the permitted paths,
  or the executable allowlist;
- the network policy or any trust root, key, pin, allowlist, or certificate;
- the `go` or tool executable paths, any argument vector, environment value,
  working directory, build tag, or flag;
- any resource bound or deadline;
- the session channel, session nonce, session messages, or the parent's build
  permit;
- the graph-validation result, the artifact verifier, the artifact path, the
  cache key, the receipt, the marker, the claim, or the publication step; or
- any hook, plugin, generator, post-build action, or fallback.

There is no package field, descriptor field, out-of-band file, environment
variable, or side channel that supplies any of the above, and none is added by
this profile. Generator comments and profile-guided-optimization paths remain
inert input and MUST NOT cause a command to run. An attempt to influence any of
the above is `hardened_package_influence_forbidden`, reported before domain
entry and before any compiler starts.

## 10. Stable diagnostics

Hardened execution results use these stable `phase: execution` diagnostics. They
are disjoint from the six portable execution codes of `profiles/manager.md`
section 2.2.1, which keep their exact meanings and MUST NOT be reused here.

| Code | State | Severity | Meaning |
|---|---|---|---|
| `hardened_profile_unsupported` | `unsupported` | `error` | The host platform, version, or configuration is not a qualified hardened platform |
| `hardened_capability_unavailable` | `unsupported` | `error` | A required capability class probe reported unavailable, inconclusive, or unprobed |
| `hardened_tcb_identity_invalid` | `blocked` | `error` | A supervisor, worker, launcher, or tool identity, substitution, or replacement check failed |
| `hardened_domain_establishment_failed` | `blocked` | `error` | The build domain could not be created, a control could not be applied, or a guarantee self-test did not observe the expected denial |
| `hardened_domain_protocol_invalid` | `blocked` | `error` | Domain session framing, nonce, ordering, size, message kind, or permit sequence is invalid |
| `hardened_domain_breach_detected` | `corrupt` | `error` | A guarantee was violated during the operation, or a domain member survived teardown |
| `hardened_evidence_invalid` | `corrupt` | `error` | The hardened capability-evidence record is inconsistent, incomplete, or contradicts the applied profile |
| `hardened_profile_claim_forbidden` | `unsupported` | `error` | A hardened identity was claimed by an operation that did not establish the hardened domain, or hardened and portable identities were mixed |
| `hardened_package_influence_forbidden` | `unsupported` | `error` | Package data attempted to influence the hardened boundary, controls, views, limits, permits, evidence, or publication |

A manager MUST NOT emit a portable execution diagnostic for a hardened
operation, and MUST NOT emit a hardened diagnostic for a portable operation.

## 11. Conformance evidence

The executable authority for this profile is the suite root
`conformance/hardened/v1`, pinned by
[`release/hardened-1.0.0-rc.1.json`](../release/hardened-1.0.0-rc.1.json). The
portable suite `conformance/v1` and its pin are unchanged and remain the
authority for `manager-worker-v1`.

A platform declaration advances from `unqualified` to `qualified` only when the
owning task supplies native adversarial evidence, executed on that platform,
that observes the kernel deny at least one representative attack per guarantee:

| Guarantee | Minimum adversarial evidence |
|---|---|
| `total-network-denial` | a domain member's outbound connection, loopback connection, and unix-domain connection each fail, and an inherited endpoint is unusable |
| `read-only-source-and-toolchain` | a domain member's write, rename, unlink, permission change, and hard link against the snapshot and against `GOROOT` each fail |
| `private-build-root-only-writes` | a domain member's write outside the private build root fails by absolute path, by relative traversal, by symbolic link, and through a temporary directory |
| `hard-aggregate-descendant-resource-bounds` | a fork bomb, a memory bomb, a disk-filling loop, an output flood, and a detached survivor each terminate the whole domain |
| `exact-executable-allowlisting` | a domain member's attempt to execute a shell, an interpreter, a host binary, and a file it just wrote each fail |
| `fail-closed-capability-preflight` | with each capability class forced unavailable in turn, the operation rejects before domain entry with the mapped diagnostic and publishes nothing |

Qualification additionally requires, on that platform, that every build-identity
source section 6.3 declares for it is readable in `tcb-identity-verification`,
that an unreadable source rejects with `hardened_tcb_identity_invalid` before
domain establishment, and that replacing the running kernel with a materially
different one moves at least one declared source and therefore
`host.build.content_sha256`. A platform whose declared sources cannot show that
separation stays `unqualified`.

Qualification tasks: `TASK-260728-3ihgfq`, `TASK-260728-3n67j6`,
`TASK-260728-1v71sx` for Curator; `TASK-260728-ns5yk7`, `TASK-260728-jis03f`,
`TASK-260728-2hcmtg` for csk; independent verification by
`TASK-260728-1itx7a`.

Related documents: [`profiles/manager-hardened.md`](../profiles/manager-hardened.md),
[`decisions/0009-hardened-build-execution-profile.md`](../decisions/0009-hardened-build-execution-profile.md),
[`docs/hardened-build-execution-profile.md`](../docs/hardened-build-execution-profile.md),
and [`SECURITY.md`](../SECURITY.md).
