# Hardened `hardened-worker-v1` execution profile

This guide is informative. The normative rules are
[`protocol/hardened-execution.md`](../protocol/hardened-execution.md),
[`profiles/manager-hardened.md`](../profiles/manager-hardened.md),
[`decisions/0009-hardened-build-execution-profile.md`](../decisions/0009-hardened-build-execution-profile.md),
and [`SECURITY.md`](../SECURITY.md).

## Read this first

**No platform is qualified for the hardened profile in candidate
`hardened-1.0.0-rc.1`.** Every host rejects it with
`hardened_profile_unsupported`, and no conformance claim can be emitted. That
is the specification working, not a bug. What exists today is the contract,
the schemas, the diagnostics, and the adversarial vectors that six
implementation tasks must satisfy before any platform is qualified.

If you want compiled builds today, you want the portable
[`manager-worker-v1`](portable-go-execution-policy.md) profile, which is
unchanged, complete, and shipping.

## What it is

One named execution policy, `hardened-worker-v1`, under which all six
guarantees the portable profile defers are kernel- or hypervisor-enforced:

| Guarantee | What the kernel refuses |
|---|---|
| `total-network-denial` | any socket operation, any address family, including loopback and inherited endpoints |
| `read-only-source-and-toolchain` | any mutation of the frozen snapshot or `GOROOT`, whatever credentials the contained process has |
| `private-build-root-only-writes` | any mutating filesystem operation outside the operation-private build root |
| `hard-aggregate-descendant-resource-bounds` | exceeding aggregate time, CPU, memory, process, descriptor, disk, or output bounds — the whole domain dies |
| `exact-executable-allowlisting` | executing anything but the exact fingerprinted `go` launcher and `GOROOT` tools |
| `fail-closed-capability-preflight` | proceeding at all when any of the above could not be established |

It is all-or-nothing. There is no partial hardened mode, no best-effort
guarantee, and no silent fallback to the portable profile.

## The process graph

```text
manager parent                        (trusted, outside the build domain)
  -> identity-verified hardened supervisor
                                      (trusted, outside the build domain)
       -> domain-root worker          (first process INSIDE the build domain)
            -> fingerprinted <GOROOT>/bin/go
                 -> fingerprinted regular executables below
                    <GOROOT>/pkg/tool/<GOHOSTOS>_<GOHOSTARCH>/
```

The portable graph has four nodes; this one has five. The extra node is the
supervisor, and it exists because a process cannot be both the creator of its
own confinement and confined by it from its first instruction.

Each of the three trusted nodes owns a distinct part of the operation. The
parent owns policy, identity, cache lookup, graph validation, the build permit,
artifact verification, and publication. The supervisor probes capabilities,
creates the domain, launches the worker into it, and destroys it. The worker is
the only actor inside the domain, so it is the only one that can observe
containment — which is why it, and not the supervisor, runs the guarantee
self-test, and why that test comes after entry.

## For skill authors

Nothing changes. The build command surface is still exactly:

```json
{"type": "build", "driver": "go-v1", "source_dir": "build/cmd/tool"}
```

or, for schema 7:

```json
{"type": "build", "driver": "go-repository-v1", "repository": "tools", "target": "tool"}
```

There is no field for a profile, a backend, a capability, a limit, a view, an
executable, an argument, an environment value, a path, a hook, or a trust root,
and there is no out-of-band way to supply one. An attempt to influence the
hardened boundary fails with `hardened_package_influence_forbidden` before the
domain is created and before any compiler starts.

## For manager implementers

Seventeen ordered phases, normative in
[`protocol/hardened-execution.md`](../protocol/hardened-execution.md) section
7.2 and nowhere else. Every phase names the one actor that performs it, and
nothing performed inside the build domain can precede the phase that creates
the first process in it:

| # | Phase | Actor |
|---|---|---|
| 1 | `profile-selection` — operator configuration or deployment mode, never package data | manager parent |
| 2 | `platform-qualification` — reject `hardened_profile_unsupported` unless this platform, version, and configuration is a qualified declaration | manager parent |
| 3 | `capability-probe` — probe all eleven capability classes on this host in this operation; reject `hardened_capability_unavailable` on any failure, inconclusive result, or unprobed class | hardened supervisor |
| 4 | `toolchain-probe-and-snapshot-freeze` — package-independent probes, `GOROOT` fingerprint, frozen snapshot | manager parent |
| 5 | `tcb-identity-verification` — supervisor, worker, `go`, and `GOROOT` tools | manager parent |
| 6 | `build-input-and-cache-lookup` — build the hardened input, compute the key, look it up | manager parent |
| 7 | `domain-establishment` — create the domain, apply every control | hardened supervisor |
| 8 | `domain-entry` — launch the worker into the domain | hardened supervisor |
| 9 | `in-domain-guarantee-self-test` — from inside, attempt one representative operation per guarantee and require the kernel to deny it | domain-root worker |
| 10 | `go-list` | domain-root worker |
| 11–17 | `parent-graph-validation`, `build-permit`, `go-build`, `artifact-verification`, `domain-teardown`, `identity-reverification`, `publication` | parent, worker, supervisor |

Two boundaries, and they are different:

- **before domain entry** — phases 1 through 7. Every capability, qualification,
  and identity rejection lands here, so an unsupported host never creates a
  build domain.
- **before package exposure** — phases 8 and 9. The domain exists and holds one
  trusted fingerprinted process that has read no package byte.

Both are strictly before `go list`, `go build`, and any compiler.

A host label, a version comparison alone, a build-time constant, a
configuration file, and a cached result from an earlier operation are **not**
probes. A self-test that cannot be run is a failure, not a pass. An exact
verified cache hit at phase 6 skips phases 7 through 16 entirely: nothing is
compiled, so no domain is created.

### The capability inventory

Version `hardened-capability-inventory-v1`, exhaustive, normative:

| Capability class | Serves |
|---|---|
| `domain-membership-enforcement` | four guarantees |
| `domain-atomic-termination` | resource bounds |
| `network-syscall-denial` | network denial |
| `preexisting-endpoint-revocation` | network denial |
| `read-only-source-view` | read-only source and toolchain |
| `read-only-toolchain-view` | read-only source and toolchain |
| `write-path-confinement` | private-build-root-only writes |
| `filesystem-view-restriction` | read-only views and write confinement |
| `exec-path-allowlist` | executable allowlisting |
| `aggregate-resource-bounds` | resource bounds |
| `active-capability-probe` | fail-closed preflight |

The executable authority is the `capability_inventory` section of
[`conformance/hardened/v1/vectors/hardened-execution-profile.json`](../conformance/hardened/v1/vectors/hardened-execution-profile.json).

### Platform status

| Platform | Enforcement backend | Status | What blocks it |
|---|---|---|---|
| `linux` | `linux-namespace-seccomp-v1` | `unqualified` | nothing identified; needs native adversarial evidence, a `cgroup2`-series minimum version, and a required configuration |
| `macos` | `macos-sandbox-v1` | `unqualified` | `domain-membership-enforcement`, `domain-atomic-termination`, `aggregate-resource-bounds`: no unescapable per-operation process domain, and no aggregate private storage, memory, or process-count accounting |
| `windows` | `windows-appcontainer-job-v1` | `unqualified` | `exec-path-allowlist`: child-process creation policy is all-or-none, with no supported per-path execution allowlist for a contained token. `aggregate-resource-bounds`: no supported facility bounds the bytes a job writes below the private build root |

Those blocking findings restate the analysis in
[`decisions/0006`](../decisions/0006-portable-manager-worker-execution.md), the
same analysis that made the portable profile necessary in the first place.

### Evidence

Exactly one `hardened-capability-evidence-v1` record per operation, with one
entry per capability class and one entry per guarantee. It is result-only:
report it in install, dry-run plan, and status results, and never put it in a
cache key, a receipt, an install marker, or a conformance claim. It is a
different record version from the portable `capability-evidence-v1`; the two
must never be merged, aliased, or converted.

## Identity, and why hardened output cannot be mistaken for portable output

Binding model `hardened-identity-binding-v1`. One rule: **everything that
decides whether a guarantee holds is hashed; only the per-operation observation
is result-only.**

The hardened build input is the portable build input with the execution-policy
value replaced and exactly one closed member added:

```json
{
  "policy": {"execution_policy": "hardened-worker-v1"},
  "hardened": {
    "profile": "hardened-profile-v1",
    "tcb": {"algorithm": "curator-hardened-tcb-v1", "content_sha256": "sha256:…"}
  }
}
```

`curator-hardened-tcb-v1` is the domain-separated, length-framed digest of the
closed `hardened-tcb-v1` record. That record names the **complete** trusted
base, because a digest is only useful if it distinguishes bases that really
differ:

| Member | What it identifies |
|---|---|
| `parent_sha256`, `supervisor_sha256`, `worker_sha256` | the three trusted binaries, by content |
| `host` | the observed operating-system kernel, its release, and its `curator-hardened-host-build-v1` kernel build identity; `kind` is `operating-system`, `identity` is the canonical kernel identity the platform declares, and `build` is a required closed record whose digest covers the platform's declared build-identity sources |
| `enforcement_backend` + `backend` | the mechanism, its observed version, and the configuration settings the qualification depends on |
| `toolchain` | the fingerprinted `go` launcher and `GOROOT` tools |
| `trusted_components` | every other mutable component — interpreter, installed package tree, script, shared library, policy file — as `{kind, name, algorithm, content_sha256}` |
| `platform` | closed one-to-one against `enforcement_backend`, and against the build input's native target |

There is no field that accepts a trusted component as free text. Naming one
without a digest, omitting the manager parent, pairing a platform with another
platform's backend, or building for `darwin` while claiming a `linux` base are
all rejected by the schemas.

There is no field that accepts the observed kernel as free text either. `build`
is not a descriptive string and MUST NOT be null: it is
`{algorithm, identifier, content_sha256}`, where the identifier is the immutable
build identifier the platform documents and the digest covers the kernel
identity, the release, the identifier, and every build-identity source section
6.3 declares for that platform. Two kernels that report one platform, one
release, and one build identifier — a rebuild, a vendor patch, a locally
compiled image — still produce different records, and therefore different cache
keys. A declared source that cannot be read rejects the operation before the
build domain exists; it never degrades to an identifier without a digest.

The end of the operation mirrors the start. `domain-teardown` destroys the
domain and joins it, and only then does `identity-reverification` recompute the
**complete** record from the same canonical pinned identities and require it to
be byte-identical to the one phase 5 built. Re-verifying a subset, or restating
the earlier record, does not discharge that check.

### Component digests are constructions, not names

A component's `algorithm` is one of two digests that protocol section 2.3.1
defines byte for byte, so two implementations hash the same thing:

- **`curator-hardened-component-file-v1`** — one regular file. Domain prefix,
  `0x00`, then `F` and the length-framed bytes. The path is not hashed; the
  record around it carries `kind` and `name`, and the whole record is inside the
  TCB digest.
- **`curator-hardened-component-tree-v1`** — one directory tree. Domain prefix,
  `0x00`, then one length-framed record per entry in unsigned bytewise path
  order: `D` for a directory with an empty payload, `F` for a regular file with
  its bytes, `L` for a symbolic link with its `readlink` value. Links must be
  relative, non-dangling, and inside the root; hard links are independent
  records; any other file type invalidates the tree.

The entry kind is hashed, which is the point: replacing a link with a regular
file holding the referent's bytes produces a different tree. Modes, ownership,
timestamps, ACLs, and extended attributes are not inputs, and a component that
cannot be read, is the wrong file type, or changes mid-operation is
`hardened_tcb_identity_invalid` before domain entry. Which kinds admit which
algorithm is closed: `installed-package-tree` is a tree, `interpreter`,
`script`, `shared-library`, `sandbox-policy-file`, and `helper-executable` are
files, and the three prober/adapter/verifier kinds may be either.

`conformance/hardened/v1/vectors/hardened-identity-separation.json` publishes
the fixture bytes and the expected digest for every component the suite uses, so
a reader recomputes them without running the generator.

### Backend versions are compared, not quoted

`backend.version` and a claim's `minimum_version` are
`hardened-backend-version-v1` values: a per-backend series token, `-`, and up to
four dot-separated integers. The series is closed against the backend
(`cgroup2`, `sandbox`, `appcontainer`), missing components are zero, and
components compare as integers, so `cgroup2-6.9` is **below** `cgroup2-6.10`
even though it sorts after it as a string. Two series are not ordered against
each other at all: that comparison is invalid, not lower or higher. A claim
whose own trusted computing base observes a version below the minimum that claim
declares is invalid rather than optimistic.

So the same source, command, target, and toolchain produce five keys that
cannot alias:

| Input | Distinguished by | A hardened input? |
|---|---|---|
| pre-revision rc.4 | no execution policy at all | no |
| portable | `manager-worker-v1` | no |
| rc.5 reserved policy slot | `hardened-worker-v1` and nothing else | no |
| hardened | profile identity and TCB digest A | yes |
| hardened after a manager update | profile identity and TCB digest B | yes |

The third row is the key `sha256:13736230…` that `conformance/v1` recorded
before this profile existed. rc.5 marks it `schema_valid: false`: it shows the
policy slot alone does not alias, and it is deliberately **not** what a
hardened build produces.

Above the cache key:

- hardened local builds write **build receipt schema 3**, external builds
  **schema 4**, each carrying the complete `hardened-tcb-v1` record beside the
  input that carries its digest; portable receipt schemas 1 and 2 are unchanged
  and unwidened;
- hardened installations write **install marker schema 4**, carrying the
  execution policy, the profile identity, and the `hardened-tcb-v1` record, and
  its `cache_key` must be reproducible from exactly those identities;
- hardened conformance claims use **schema 4**, which admits only
  `hardened-worker-v1`; claim 3 admits only `manager-worker-v1`, so the two are
  structurally disjoint in both directions.

**What this costs you.** One source produces a different cache key on each
trusted computing base, so a manager update that changes parent, supervisor, or
worker bytes, an operating-system upgrade, or a change to an enforcement-backend
setting the qualification depends on causes a rebuild. That is intended: an
artifact carries exactly the guarantees of the trusted computing base that
produced it, and reusing across such a change — including one that fixes a
containment defect — would silently attribute this revision's guarantees to a
build that never ran under them. The conformance suite rotates every member of
the record in turn and requires the key to move; most of those rotations change
nothing a package can see, which is what makes the divergence attributable to
the trusted base rather than to the build.

The per-operation `hardened-capability-evidence-v1` record is the one thing
that stays out of every reusable output. It reports what one operation
observed, so putting it in a key would invite reading a cache key as capability
proof.

## Diagnostics

| Code | State | Meaning |
|---|---|---|
| `hardened_profile_unsupported` | `unsupported` | the host is not a qualified hardened platform |
| `hardened_capability_unavailable` | `unsupported` | a capability class probe failed, was inconclusive, or was not run |
| `hardened_tcb_identity_invalid` | `blocked` | an identity, substitution, or replacement check failed |
| `hardened_domain_establishment_failed` | `blocked` | the domain could not be created, or a self-test was not denied |
| `hardened_domain_protocol_invalid` | `blocked` | session framing, nonce, ordering, or permit sequence is invalid |
| `hardened_domain_breach_detected` | `corrupt` | a guarantee was violated, or a domain member survived teardown |
| `hardened_evidence_invalid` | `corrupt` | the evidence record is inconsistent or contradicts the applied profile |
| `hardened_profile_claim_forbidden` | `unsupported` | a hardened identity was claimed without a hardened domain, or identities were mixed |
| `hardened_package_influence_forbidden` | `unsupported` | package data tried to influence the boundary |

None of these collides with the six portable `build_execution_*` codes, and a
manager never emits a portable code for a hardened operation or the reverse.

## What qualification will take

[`conformance/hardened/v1/vectors/hardened-adversarial-vectors.json`](../conformance/hardened/v1/vectors/hardened-adversarial-vectors.json)
carries the required adversarial cases: twenty-six in-domain escape attempts
across the five containment guarantees, thirteen forced-unavailable preflight
cases, fifteen package-influence surfaces, seventeen identity and protocol
negatives, sixteen evidence negatives, and four no-fallback cases. Every one is
marked `pending-native-validation` today.

Qualifying a platform means running those on that platform and observing the
kernel deny each attack. Owners: `TASK-260728-3ihgfq`, `TASK-260728-3n67j6`,
`TASK-260728-1v71sx` for Curator; `TASK-260728-ns5yk7`, `TASK-260728-jis03f`,
`TASK-260728-2hcmtg` for csk; independent verification by
`TASK-260728-1itx7a`.

## Running the gates

```bash
make validate-hardened            # hardened schemas, vectors, manifest, pins
make regenerate-hardened          # regenerate conformance/hardened/v1
make regenerate-hardened-check    # prove byte stability, and that rc.5 is untouched
```
