# Curator Hardened Manager Profile 1.0

Candidate `hardened-1.0.0-rc.1`. This document is normative and additive. It
states what a manager MUST do to implement the hardened execution profile of
[`protocol/hardened-execution.md`](../protocol/hardened-execution.md). It does
not modify [`profiles/manager.md`](manager.md), whose portable
`manager-worker-v1` rules stay exactly as candidate `1.0.0-rc.5` defines them.

A manager MAY implement the portable profile only. A manager that implements
this profile MUST implement all of it; there is no partial hardened mode.

## 1. Profile selection and configuration

The hardened profile is selected by operator configuration or by a manager
deployment mode. A manager MUST resolve that selection before it reads any
package byte for the operation, and MUST NOT let a manifest value, a repository
descriptor, a build root, a source file, or any other package-controlled byte
select, request, hint at, weaken, or disable it.

When the hardened profile is selected:

- the manager MUST NOT fall back to `manager-worker-v1` for any command, any
  driver, any platform, or any error;
- a portable cache entry MUST NOT be consulted, adopted, upgraded, or reported
  as a hit; and
- a failure to establish any guarantee rejects the whole operation, not the
  individual command.

When the portable profile is selected, the operation is portable in every
respect and this document does not apply to it.

## 2. The hardened operation

The ordered phase list is normative in
[`protocol/hardened-execution.md`](../protocol/hardened-execution.md) section
7.2, and that document is its sole authority. This section attaches manager
obligations to those phase names. **It publishes no ordering of its own**: the
phases below appear in the protocol's order, carry the protocol's names, and a
manager that follows this table follows section 7.2 exactly. Where this table
and section 7.2 could be read as disagreeing, section 7.2 governs.

| Phase | Actor | Manager obligation |
|---|---|---|
| `profile-selection` | manager parent | Record the profile identity `hardened-profile-v1` and the execution-policy identity `hardened-worker-v1`. Any package-sourced attempt to influence the selection is `hardened_package_influence_forbidden`. |
| `platform-qualification` | manager parent | Compare the host platform, version, and required configuration against the platform declarations of `protocol/hardened-execution.md` section 6.3 for this revision. Compare the observed enforcement-backend version against the declared minimum with the `hardened-backend-version-v1` comparison of section 2.3.4, in the series that backend declares; a version outside the grammar or from another series is not a lower or higher result but an invalid comparison. A platform whose declaration is `unqualified`, or a host below the declared minimum version or outside the required configuration, rejects with `hardened_profile_unsupported`. |
| `capability-probe` | hardened supervisor | Probe, on this host and in this operation, every class of the `hardened-capability-inventory-v1` inventory. A host label, an operating-system version comparison alone, a build-time constant, a configuration file, and a cached result from an earlier operation are not probes. Any class that is `unavailable`, inconclusive, or `unprobed` rejects with `hardened_capability_unavailable`. |
| `toolchain-probe-and-snapshot-freeze` | manager parent | Run the package-independent toolchain probes with exactly the probe argument vectors, environment, and canonical working directories of `profiles/manager.md` section 2.2. Fingerprint `GOROOT` with `curator-go-toolchain-v1` and freeze the validated source snapshot. No Go process sees a package byte here. |
| `tcb-identity-verification` | manager parent | Resolve the manager parent, the supervisor, and the worker to canonical regular installed files, reject symbolic link, reparse point, and hard-link substitution, record strong file identity, hash the bytes, and verify the fingerprinted `go` launcher and `GOROOT` tool executables. Observe the host operating-system kernel identity and release, read every build-identity source `protocol/hardened-execution.md` section 6.3 declares for the platform in the declared order, and build the closed `curator-hardened-host-build-v1` identity of section 2.3.3 from them; a source that cannot be read, is empty, or is unavailable is `hardened_tcb_identity_invalid` before domain establishment, never a null, a build-time constant, or an identifier without a digest. Observe the enforcement backend's own version and the configuration settings the qualification depends on. Fingerprint every additional mutable trusted component — interpreter, installed package tree, script, shared library, policy file, helper executable, enforcement adapter, capability probe, or identity verifier — as a closed `{kind, name, algorithm, content_sha256}` record, digesting it with the section 2.3.1 algorithm its kind admits: `curator-hardened-component-file-v1` over one regular file, `curator-hardened-component-tree-v1` over one directory tree. A component that cannot be read, is not the file type its algorithm requires, or changes before `identity-reverification` fails closed rather than being named without a digest. Recheck identity at each launch boundary so a replacement race cannot widen the graph. Build the complete `hardened-tcb-v1` record of `protocol/hardened-execution.md` section 2.3 from what was actually observed and verified, never narrower. Any failure, any unnamed trusted component, and any platform, backend, or target relation that does not hold is `hardened_tcb_identity_invalid`. |
| `build-input-and-cache-lookup` | manager parent | Construct the hardened build input of `protocol/hardened-execution.md` section 2.2 from the verified trusted computing base, compute the logical cache key, and look it up under section 4 of this document. An exact verified hit skips every phase through `identity-reverification` and continues at `publication`; it starts no compiler, creates no build domain, and therefore has nothing to re-verify. |
| `domain-establishment` | hardened supervisor | Create the containment object, apply every control the platform declaration names, install the read-only source and toolchain views, the private write root, the executable allowlist, the network denial, and the aggregate bounds, and revoke every pre-existing endpoint. Open the session channel as pre-opened descriptors or handles. Any failure is `hardened_domain_establishment_failed`. |
| `domain-entry` | hardened supervisor | Launch the domain-root worker into the established domain as the first process inside it. The worker proves the same executable identity and hash, closes standard input, releases unrelated descriptors or handles, and acknowledges the fresh session nonce. Any failure is `hardened_domain_establishment_failed`. |
| `in-domain-guarantee-self-test` | domain-root worker | From inside the domain, attempt one representative operation per guarantee and require the kernel to deny it, then report the result and the `hardened-capability-evidence-v1` record over the session channel. Until the supervisor accepts that result the worker opens no path below the source view and starts no Go process. A self-test that cannot be run, or that is not denied, is `hardened_domain_establishment_failed` and tears the domain down. |
| `go-list` | domain-root worker | Run exactly one `go list` with exactly the vector of `profiles/manager.md` section 2.2 from the command's canonical `source_dir`, and return bounded, redacted output and exit metadata. The worker cannot proceed to a build on its own. |
| `parent-graph-validation` | manager parent | Apply every dependency, containment, directive, and native-input rejection of `profiles/manager.md` section 2.3 to the complete stream. Nothing in this profile relaxes those rejections; containment is not a substitute for the compile-only boundary. |
| `build-permit` | manager parent | Issue exactly one authenticated build permit. Any other message, repetition, or reordering tears the session down with `hardened_domain_protocol_invalid` and starts no compiler. |
| `go-build` | domain-root worker | Run exactly one `go build` with exactly the vector of `profiles/manager.md` section 2.2 to the manager-derived output path. |
| `artifact-verification` | manager parent | Return one bounded regular artifact through manager-controlled private staging, apply manager-defined permissions, and verify type, size, link safety, identity, and digest without executing it. |
| `domain-teardown` | hardened supervisor | Destroy the whole domain as a unit and join it, so no domain member is running and none can start when re-verification begins. A surviving member is `hardened_domain_breach_detected`. Discard all private state. |
| `identity-reverification` | manager parent | After the whole domain has been destroyed and joined, observe every trusted identity again from the same canonical pinned paths, resolved the same way and with the same substitution rejections `tcb-identity-verification` used, and **recompute the complete `hardened-tcb-v1` record**: the manager parent, supervisor, and worker bytes; the fingerprinted `go` launcher and `GOROOT` tool executables; the observed host kernel identity, release, and `curator-hardened-host-build-v1` build identity recomputed from its declared sources; the observed enforcement-backend version and configuration; the platform and enforcement backend; every trusted component re-digested by the algorithm its kind admits; and the frozen source snapshot. Require the recomputed record to be byte-identical to the one built in `tcb-identity-verification` and its `curator-hardened-tcb-v1` digest to equal the one the hashed build input carries. Re-verifying a subset of the record, restating the earlier record, or comparing the earlier digest against itself does not discharge this obligation. Any difference in any member is `hardened_tcb_identity_invalid` and rejects before publication. |
| `publication` | manager parent | Publish under the serialization, locking, journal, and rollback rules of `profiles/manager.md` section 2.5, unchanged. |

A failure at any phase fails the operation before publication and preserves the
installation, consumers, markers, shims, and live caches byte-for-byte as they
were when the operation began. Failures through `domain-establishment` occur
**before domain entry**; failures at `domain-entry` and
`in-domain-guarantee-self-test` occur after entry but **before any package byte
is read by any process in the domain**. Both boundaries are strictly before
`go list`, `go build`, and any compiler, exactly as
`protocol/hardened-execution.md` section 7.3 states.

## 3. Evidence

The manager emits exactly one `hardened-capability-evidence-v1` record per
hardened operation, with the exact fields, cardinality, and consistency rules of
`protocol/hardened-execution.md` section 6.4. It reports the record in install,
dry-run plan, and status results.

The record is result-only. The manager MUST NOT place it into a cache key, a
receipt, an install marker, or a conformance claim. It reports what one
operation observed; it is not the identity of what produced an artifact.

The profile identity and the `hardened-tcb-v1` record are the opposite case:
the manager MUST bind both into the cache key, the receipt, the marker, and the
claim, exactly as `protocol/hardened-execution.md` sections 2 and 8 require.
The record it binds MUST be the complete one of section 2.3 — manager parent,
supervisor, worker, observed host, observed backend version and configuration,
toolchain, and every additional mutable trusted component. A record that omits
any of them would let a different trusted base reuse this one's cache entries,
receipts, markers, and claims.

The manager MUST NOT emit the portable `capability-evidence-v1` record for a
hardened operation, and MUST NOT emit the hardened record for a portable
operation. Mixing them is `hardened_profile_claim_forbidden`.

## 4. Cache, receipt, and marker handling

The manager derives the complete build input, logical cache key, canonical
receipt, receipt hash, and artifact-relative path exactly as
`protocol/core.md` section 9 specifies, with
`execution_policy: "hardened-worker-v1"` in the policy object and the closed
`hardened` member of `protocol/hardened-execution.md` section 2.2 carrying the
profile identity and the `curator-hardened-tcb-v1` digest of the trusted
computing base verified in `tcb-identity-verification`.

On lookup, the manager recomputes build-source identity, cache key, complete
expected input, exact canonical receipt bytes and hash, manager-derived artifact
path, artifact hash, and byte length without following links or executing the
artifact, and revalidates the protected-cache boundary of `protocol/core.md`
section 9.3. Because the key covers the profile identity and the TCB digest, an
entry produced under another execution policy, another profile revision, or
another trusted computing base has a different key and never collides. The
manager additionally treats as a **miss** any entry whose receipt `tcb` record
is not byte-identical to the one it verified for this operation, and any entry
whose `input.hardened.tcb.content_sha256` is not the `curator-hardened-tcb-v1`
digest of that receipt's own `tcb` record. On a miss the manager rebuilds; it
MUST NOT adopt, upgrade, re-label, or re-sign such an entry.

A manager that implements both profiles keeps the two sets of entries logically
disjoint and revalidates the boundary independently for each. Physical layout
remains implementation-specific, and no portable path may be inferred.

Hardened builds write build receipt schema 3 for `go-v1` and schema 4 for
`go-repository-v1`, and install marker schema 4 for both manifest schema-6 and
schema-7 packages. Every one of those records carries the execution policy, the
profile identity, and the complete `hardened-tcb-v1` record, and a marker's
`cache_key` MUST be reproducible from the identities the marker itself
publishes. The manager MUST reject receipt schemas 3 and 4 and marker schema 4
when it does not implement this profile, as unsupported identities under
`protocol/core.md` section 9.3 and section 10; it MUST NOT parse them leniently
or convert them to a portable shape.

## 5. Dry run, status, repair, and garbage collection

A hardened dry run performs the read-only planning and package-independent
toolchain probes of `profiles/manager.md` section 2.4, plus the phases of
`protocol/hardened-execution.md` section 7.2 up to and including
`build-input-and-cache-lookup`. It MUST NOT reach `domain-establishment`,
`domain-entry`, `go-list`, or `go-build`, MUST NOT start a compiler or linker,
and removes all operation-private state before returning. It reports, per build
command, `cache-hit`, `would-preflight-and-build`,
`would-rebuild-untrusted-cache`, `corrupt`, or `unsupported`, and it reports
`unsupported` with `hardened_profile_unsupported` or
`hardened_capability_unavailable` when the host does not qualify.

Status is read-only. It reports the hardened profile identity, the qualification
status of the host, and the capability-evidence record, and it MUST NOT
establish a domain, run a compiler, or mutate state.

Repair and garbage collection follow `profiles/manager.md` sections 2.6 and 10
unchanged, with two additions: a hardened entry MUST NOT be made live by a
portable marker record or vice versa, and an entry whose execution policy cannot
be proved MUST be conservatively retained rather than adopted.

## 6. Package-controlled behavior

`protocol/hardened-execution.md` section 9 lists exactly what package data MUST
NOT influence. The manager rejects any attempt with
`hardened_package_influence_forbidden` before domain entry and before any
compiler starts. The build command surfaces stay exactly as
`protocol/core.md` sections 4.2 and 4.2.2 define them; this profile adds no
package-visible field, option, flag, or file.

## 7. Stable diagnostics

The manager uses exactly the nine hardened `phase: execution` diagnostics of
`protocol/hardened-execution.md` section 10. They take precedence over the
generic schema and descriptor codes of `profiles/manager.md` section 11.10 for
hardened operations. The six portable execution codes of
`profiles/manager.md` section 2.2.1 keep their exact meanings and MUST NOT be
emitted for a hardened operation.

## 8. Qualification

A manager MUST NOT report a platform as hardened-qualified on the basis of this
document. Qualification requires the native adversarial evidence listed in
`protocol/hardened-execution.md` section 11, produced on that platform by the
task that owns it. Until then every host rejects in `platform-qualification` with
`hardened_profile_unsupported`, and no conformance claim schema 4 document can
be emitted.
