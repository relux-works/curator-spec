# Changelog

All notable protocol changes are recorded here. Versions follow Semantic
Versioning for the complete specification set.

## hardened-1.0.0-rc.1 - 2026-07-28

Additive candidate for the hardened execution profile. It is versioned,
validated, and pinned separately from the protocol candidate: no byte of
`conformance/v1`, `schemas/v1`, or `release/1.0.0-rc.5.json` changes, and the
portable `manager-worker-v1` profile keeps its exact contract.

### Added

- `protocol/hardened-execution.md` and `profiles/manager-hardened.md`: the
  normative hardened profile. All six guarantees deferred by protocol core
  section 4.2.1 — `total-network-denial`,
  `read-only-source-and-toolchain`, `private-build-root-only-writes`,
  `hard-aggregate-descendant-resource-bounds`, `exact-executable-allowlisting`,
  and `fail-closed-capability-preflight` — are defined as kernel- or
  hypervisor-enforced properties of a build domain, each with an explicit
  "not sufficient" list.
- The five-node hardened process graph, adding one uncontained hardened
  supervisor so that containment is created and verified before the first
  contained instruction, and the domain session state machine that still admits
  exactly one `go list` and one `go build`.
- The exhaustive `hardened-capability-inventory-v1` inventory of eleven
  capability classes, mapped many-to-one onto the six guarantees, probed on the
  host in the operation before domain entry.
- An end-of-operation re-verification that is ordered after the whole domain has
  been destroyed and joined, and that recomputes the **complete**
  `hardened-tcb-v1` record from the same canonical pinned identities rather than
  spot-checking a few binaries. Every mutable member — the three binaries, the
  toolchain, the observed host and its kernel build identity, the backend version
  and configuration, the platform and mechanism, every trusted component, and the
  frozen snapshot — must be byte-identical to the record the operation was hashed
  under, or the operation rejects with `hardened_tcb_identity_invalid` before
  publication.
- One normative ordered phase list of seventeen phases, owned by
  `protocol/hardened-execution.md` section 7.2 and mirrored — never restated —
  by the manager profile and the profile vector. Every phase names the single
  actor that performs it, and no phase performed inside the build domain may
  precede `domain-entry`, which makes the pre-package state machine performable:
  the domain-root worker exists before it is asked to self-test from inside.
- Two separately stated boundaries. Every capability, qualification, and
  trusted-computing-base rejection happens before domain entry, so an
  unsupported host creates no build domain; domain entry and the in-domain
  self-test complete before any package byte is read by any process in the
  domain. Both are strictly before `go list`, `go build`, and any compiler.
  There is no partial hardened mode and no silent fallback to the portable
  profile.
- The `hardened-identity-binding-v1` model. The hashed build input carries the
  execution policy, the profile identity, and the domain-separated
  `curator-hardened-tcb-v1` digest of the closed `hardened-tcb-v1` record, so
  both hardened identities bind the cache key, the exact receipt bytes,
  `receipt_sha256`, the install marker, and the conformance claim. Cache reuse
  cannot cross a profile revision or a trusted computing base.
- The closed `hardened-capability-evidence-v1` record, distinct from the
  portable `capability-evidence-v1` record and the one identity that stays
  result-only.
- The closed `hardened-tcb-v1` trusted-computing-base record, naming the
  complete base: the manager parent, supervisor, and worker digests, the
  observed operating-system kernel identity, its bounded release, and its
  required `curator-hardened-host-build-v1` kernel build identity, the
  enforcement backend with its observed version and the configuration the
  qualification depends on, the fingerprinted toolchain, and every additional
  mutable trusted component as a closed
  `{kind, name, algorithm, content_sha256}` record. A platform admits exactly
  the one enforcement backend it declares, exactly the one canonical kernel
  identity it declares, exactly the one kernel build identifier grammar it
  declares, and a `host.kind` of `operating-system`; a hardened
  receipt's native target admits exactly the one TCB platform it maps to; a
  trusted component's digest algorithm must be one its kind admits; and a
  claim's required configuration must be observed, and its declared minimum
  version satisfied, in the base the claim itself names.
- `curator-hardened-component-file-v1` and `curator-hardened-component-tree-v1`,
  the two domain-separated, length-framed trusted-component digest
  constructions. The file algorithm hashes one regular file's bytes; the tree
  algorithm hashes a `D`/`F`/`L` walk in unsigned bytewise path order with
  relative, non-dangling, in-root links and independent hard-link records.
  Modes, ownership, timestamps, ACLs, and extended attributes are not inputs;
  the entry kind is, so a symbolic link replaced by a regular file holding the
  referent's bytes cannot reproduce the tree it replaced. An unreadable,
  wrong-type, or mid-operation-changed component is `hardened_tcb_identity_invalid`
  before domain entry. The identity-separation vector publishes the exact bytes
  and expected digest of every component fixture, so a reader recomputes them
  independently.
- `curator-hardened-host-build-v1`, the domain-separated, length-framed kernel
  build identity. `host.build` is a required closed
  `{algorithm, identifier, content_sha256}` record rather than a nullable
  descriptive string: the identifier is the immutable build identifier the
  platform documents, and the digest covers the observed kernel identity, the
  release, the identifier, and every build-identity source section 6.3 declares
  for that platform, framed and counted. Two materially different kernels that
  report one platform, one release, and one build identifier therefore produce
  different trusted-computing-base records, cache keys, receipts, markers, and
  claims. `host.version` is a bounded release grammar rather than free text, and
  a declared build-identity source that cannot be read is
  `hardened_tcb_identity_invalid` before domain establishment — never a null, a
  build-time constant, or an identifier without a digest. The identity-separation
  vector publishes the exact bytes of every build-identity fixture, so a reader
  recomputes them independently.
- `hardened-backend-version-v1`, a comparable enforcement-backend version
  identity: a per-backend series token (`cgroup2`, `sandbox`, `appcontainer`),
  `-`, and up to four dot-separated integers. Missing components are zero and
  components compare as integers, so `cgroup2-6.9` is below `cgroup2-6.10`.
  Comparing two series is invalid rather than lower or higher. A claim's
  `minimum_version` uses the same grammar and its own backend's series, and the
  conformance validator compares it against the observed version rather than
  accepting the declaration.
- Hardened build receipt schemas 3 and 4, install marker schema 4, and
  conformance claim schema 4 under `schemas/hardened/v1`, each carrying the
  execution policy, the profile identity, and the complete trusted-computing-base
  record. Claim 3 admits only `manager-worker-v1` and claim 4 only
  `hardened-worker-v1`, so the two are structurally disjoint in both directions.
- The nine stable `hardened_*` `phase: execution` diagnostics, disjoint from the
  six portable `build_execution_*` codes.
- The `conformance/hardened/v1` suite: profile, adversarial, and identity
  separation vectors, plus positive and negative schema cases. The adversarial
  vector carries twenty-six in-domain escape attempts, thirteen
  forced-unavailable preflight cases, fifteen package-influence surfaces,
  seventeen identity and protocol negatives, sixteen evidence negatives, and
  four no-fallback cases, every one marked `pending-native-validation`.
- `release/hardened-1.0.0-rc.1.json`, pinning the hardened suite manifest and
  recording the rc.5 portable manifest digest as an unmodified read-only
  baseline.
- `tools/generate-hardened` and `tools/validate_hardened.py` with their tests,
  and `make validate-hardened`, `make regenerate-hardened`, and
  `make regenerate-hardened-check`.
- Decision 0009 recording the profile, the rejected alternatives, and the
  compatibility and security impact.

### Unchanged

- The portable execution policy, its native-control inventory, its
  capability-evidence record, its diagnostics, and every byte of the accepted
  rc.5 candidate suite and its downstream pin.
- The package surface. No manifest field, descriptor field, build command field,
  environment variable, or out-of-band file selects, weakens, or observes the
  hardened profile.

### Not claimed

- No platform is qualified. Linux, macOS, and Windows are each declared
  `unqualified` pending native adversarial evidence, so every host rejects the
  hardened profile with `hardened_profile_unsupported` and no hardened
  conformance claim can be emitted. The macOS declaration records unescapable
  domain membership, atomic domain termination, and aggregate resource bounds as
  blocking; the Windows declaration records per-path execution allowlisting and
  the aggregate write-byte bound as blocking.

## 1.0.0-rc.5 - 2026-07-28

### Added

- Manifest schema 7, repository-root `skill-build.json` descriptor schema 1,
  development substitution schema 2, build receipt schema 2, install marker
  schema 3, and conformance claim schema 3 for the closed `go-repository-v1`
  driver. The descriptor filename is manager-neutral: it names the artifact a
  skill is built from, not the manager that reads it.
- Platform-neutral shared fixtures and vectors for SHA-1/SHA-256 tagged and
  untagged acquisition, HTTPS/SSH/local identities, exact Git config/refs/raw
  objects/pack/index/LFS bytes, and fail-closed repository features.
- Whole-snapshot audit ordering, cache, offline, mixed-build, rollback,
  status/repair/GC, shim/PATH, signing-boundary, and claim-qualification cases.
- Author/operator guidance and generated rc.5 metadata carrying the exact
  downstream candidate suite-manifest pin.
- The portable `manager-worker-v1` execution policy for `go-v1` and
  `go-repository-v1`: one identity-verified manager-owned worker in the fixed
  process graph, an exact worker session state machine, the mandatory portable
  control set, the exhaustive versioned `rc5-native-control-inventory-v1`
  per-platform inventory, the closed `capability-evidence-v1` reporting record,
  a single explicit failure boundary, and the `build_execution_*` stable
  diagnostics.
- An explicit statement, in normative text and in vectors, of the portable
  mechanism behind each rule and the kernel-enforced guarantee it is not, so
  `network: "none"`, the frozen snapshot, and the fixed manager-selected graph
  can no longer be read as network denial, read-only presentation, or executable
  allowlisting.
- Executable `go-host-execution-policy` vectors covering the worker graph and
  session order, mandatory controls, the per-platform native-control inventory,
  the closed capability-evidence record and its negatives, the six deferred
  hardened guarantees with their non-rejection guards, worker identity and
  protocol negatives, closed package-influence surfaces, and distinct portable,
  reserved-hardened, and pre-revision cache identities.
- Decision 0006 recording the portable execution policy, the rejected
  hardened-Linux-only and direct-Go alternatives, and the deferral of the
  fail-closed profile to `STORY-260728-327soo`.

### Changed

- The shared-suite manifest and repository version metadata now identify
  `1.0.0-rc.5`.
- Claim v3 qualification requires immutable native evidence for every emitted
  driver/platform tuple. This candidate emits no native manager claim; macOS
  and Windows remain pending downstream evidence and Linux remains excluded
  until `TASK-260728-1skseh`.
- `goBuildPolicyV1` and `goRepositoryBuildPolicyV1` require
  `execution_policy: "manager-worker-v1"`; marker-v3 build records and claim-v3
  driver assertions require the same closed constant. Every `go-v1` logical
  cache key and the generated `go-v1` receipt example change accordingly.
- Decision 0004 supersedes its direct-Go process-graph clause before
  publication.

### Compatibility

- Manifest schemas 1 through 6, the `build-receipt-v1`, `install-marker-v2`,
  and `conformance-claim-v2` schema bytes, markers v1/v2, claim v1/v2, and the
  `go-v1` package-controlled surface retain their prior meaning and frozen
  guards. No manifest or descriptor gains a package-controlled field.
- The unreleased execution-policy revision intentionally changes `go-v1` cache
  identity so a pre-revision candidate entry misses instead of aliasing. The
  exact rc.4 candidate key
  `sha256:3fcd714a40e8918eb67dbd35d435875dcce6c9047da811a1fa26626e5e57be48`
  is retained in the suite only as that non-aliasing proof.
- A future hardened execution profile requires a new execution-policy identity
  and a new claim schema version; claim v3 cannot express one.
- Schema-7 mixed builds keep receipt v1 for local `go-v1`, use receipt v2 only
  for `go-repository-v1`, and write marker v3.
- Candidate suite consumption is explicit and digest-pinned; no committed
  downstream released-suite pin is advanced by this candidate metadata.

### Security

- Exact source and raw-object proof, full-snapshot validation, Git LFS
  rejection, and independent external audit precede both artifact-cache lookup
  and compiler execution.
- Compiled builds apply their mandatory controls inside an identity-verified
  manager-owned worker before any package byte reaches a compiler, and reject
  the build before the worker or Go when a mandatory control is unavailable.
- The portable policy does not claim total network denial, kernel-enforced
  read-only source and toolchain, private-build-root-only writes, hard aggregate
  descendant resource bounds, exact executable allowlisting, or fail-closed
  capability preflight. Those six guarantees are deferred to
  `STORY-260728-327soo`, their absence never rejects a portable build, and
  recording them under `manager-worker-v1` is an error.
- Exactly one control set can reject at this boundary: a mandatory portable
  control that cannot be applied rejects before the worker starts. An unavailable
  inventory native control is reported and never rejects, and capability evidence
  stays out of cache, receipt, marker, and claim identity.
- Source hooks, helpers, filters, submodules, LFS hydration, alternates,
  replacements, grafts, promisor/lazy fetch, package PATH/output control,
  package influence over the execution boundary, and install-time signing remain
  outside the closed driver.

## 1.0.0-rc.4 - 2026-07-20

### Added

- Manifest schema 6 with the closed compile-only local `go-v1` build command.
- Build receipt schema 1, install marker schema 2, conformance claim schema 2,
  protected artifact-cache rules, mixed lifecycle planning, and deterministic
  build vectors.

### Compatibility

- Schemas 1 through 5 and marker schema 1 retain their published bytes and
  meanings. Schema 6 is selected only by exact `schema_version`.

### Security

- Package source is compiler input only. Package-controlled recipes, hooks,
  argv, environment, output selection, dynamic/native toolchains, produced
  program execution, and receipt self-attestation are rejected.

## 1.0.0-rc.3 - 2026-07-14

### Added

- Canonical `agent-skill.json` schemas for skill runtime, capability, command,
  skill, and MCP dependency declarations.
- Shared manifest-resolution vectors covering canonical-only, legacy-only,
  equal dual manifests, conflicting dual manifests, invalid-manifest
  fail-closed behavior, and `agents/runtime.json` fallback.

### Changed

- Made `agent-skill.json` the implementation-neutral filename that conforming
  writers emit.
- Reserved `csk-skill.json` as a protocol 1.x read alias and preserved its
  published schema bytes unchanged.
- Required readers to reject unequal dual manifests with
  `conflicting_skill_manifests` instead of choosing one silently.

### Compatibility

- Existing `csk-skill.json` packages remain readable without migration.
- Packages may temporarily ship equal canonical and legacy manifests during a
  staged rollout; `agent-skill.json` is authoritative in that case.
- `agents/runtime.json` remains readable only when neither modern filename is
  present.

### Security

- The rename adds no execution surface. Dual-file ambiguity and attempts to
  hide an invalid manifest behind a fallback now fail closed.

## 1.0.0-rc.2 - 2026-07-13

### Added

- A normative registry-service profile for stable pagination, serialized
  append transactions, durability, recovery, backup/restore, key operations,
  resource controls, health, observability, and an explicit threat model.
- Executable registry-service and registry-client vectors covering conjunctive
  queries, exact artifact identity, snapshot-bound cursors, auditor-scoped
  idempotency, concurrent writers, rollback, recovery, retry safety, and limits.
- A decision record separating the registry HTTP wire contract from production
  service guarantees without changing deployed response objects.
- A machine-validated independent review report format, stable-release gate,
  and release checklist that forbid normative drift after review.
- Manager lifecycle vectors for self-contained command launchers, idempotent
  bootstrap, closure-scoped upgrades, and side-effect-free dry runs.

### Changed

- Defined artifact identity as name, source identity, commit, and content hash,
  preserving evidence when one source and commit produce different content.
- Bound every pagination chain to one immutable signed snapshot boundary.
- Scoped idempotency keys to an auditor and compared the submitted record's
  CCJ-1 digest.
- Required snapshot creation time to remain fixed for one committed boundary
  and registry-service snapshot version to equal log size.
- Defined an external high-water checkpoint as a signed registry snapshot and
  made stable release artifacts conditional on two passing independent reports.
- Added review-report schema v2, requiring separate public reviewer identities
  and explicit non-maintainer/non-author attestations, with executable
  stable-gate regression tests. Draft v1 reports remain readable but are not
  valid stable-release evidence.
- Separated durable client rollback state from disposable response caches and
  required existing corruption and persistence failures to fail closed.
- Made shell activation an explicitly optional interactive convenience and
  required agent command execution to remain independent from user profiles.
- Defined portable direct project-shim locations and safe, non-destructive
  publication of global forwarding shims.
- Clarified finite upward search, activation reentrancy guards, Git Bash
  handling of native Windows paths, and cached hook installation.
- Added manager guidance for warning about prompt-visible runtime source paths
  and missing shell-neutral command resolution.
- Required command launchers to carry their runtime dependency environment on
  Unix and Windows while preserving inherited `PATH`, arguments, and exit
  status.
- Defined selected-closure upgrade behavior, cross-project fetch
  deduplication, create-if-absent bootstrap, and dry-run purity across source,
  cache, security-state, runtime, and project surfaces.
- Accepted GitHub-verified protected-main merge commits as release targets
  while retaining maintainer-signed release tags and exact-target checks.

### Compatibility

- Existing protocol filenames, signed object schemas, endpoints, and response
  shapes are unchanged.
- Registry services must tighten behavior before claiming the production
  registry-service class; existing clients continue to parse the same wire
  objects.

## 1.0.0-rc.1 - 2026-07-13

### Added

- Split normative protocol core, registry, manager profile, and conformance
  documents from the implementation-specific Curator CLI guide.
- Draft 2020-12 JSON Schemas for every versioned wire object and HTTP response.
- Authoritative positive and negative conformance vectors with deterministic
  regeneration.
- Compatibility, security, governance, and release policies.
- Cross-platform CI and shared Go/Python conformance gates.
- A repository-pinned SSH signer allowlist verified by release CI for both the
  release tag and its target commit.
- GitHub Actions dependencies pinned to verified full commit IDs.

### Changed

- Declared machine-home paths, command names, global environment variables,
  cache layouts, and managed comment text implementation-specific.
- Replaced implementation-oracle conformance language with schema, prose, and
  vector authority.
- Defined Curator Canonical JSON 1, complete snapshot validation, Merkle byte
  layout, bundle authentication, HTTP errors and limits, and key rotation.
- Defined deterministic closure ordering and portable Windows path rules.
- Added shared identifier, expanded path, source-identity, and signed-number
  rejection vectors.
- Clarified that project aliases are operator-facing Unicode labels while
  canonical registry source identities remain whitespace-free lowercase-host
  values of bounded length.
- Made paginated record envelopes tolerant of individually malformed object
  candidates so federation can ignore one bad record without dropping a page.
- Aligned manager and system configuration schemas with both implementations:
  strict unknown fields, portable matching aliases, registry key and URL
  validation, explicit defaults, and configurable cache/snapshot time bounds.
- Removed the undefined per-registry `required` flag; strict registry policy is
  the protocol 1.0 fail-closed mechanism for unknown artifacts.

### Compatibility

- Existing deployed wire filenames and `.agents/` layout are preserved.
- The signed JSON profile preserves bytes for all valid pre-RC registry
  objects; previously ambiguous numeric and string forms are now rejected.
