# Changelog

All notable protocol changes are recorded here. Versions follow Semantic
Versioning for the complete specification set.

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
- Decision 0007 and its reference guide recording the shared compiled-build
  toolchain requirement contract: closed toolchain identifiers and driver
  mapping, one canonical version grammar and interval intersection, the
  manager-owned tested-release-family gate that carries the existing Go
  allowlist rule forward, the two declaration channels behind trusted
  resolution and fingerprint identity, the two-stage preflight order with
  host-pair applicability ahead of resolution and the descriptor-narrowed
  requirement re-evaluated before compiler work, the wire-surface versus
  source-metadata disposition split behind package-influence rejection, the
  source-file shape gate, exhaustive value classifiers for the `go.mod` `go` and
  `toolchain` directives defined over upstream's two-layer acceptance — the
  `modfile` shape grammar conjoined with `gover` version semantics, with the
  ecosystem's own host-version gate kept out of both — under a no-widening and a
  no-narrowing-outside-the-security-partition property that an executable
  boundary probe measures against real toolchains from an isolated semantic
  measurement and a closed command classifier that recognises whole diagnostics
  exactly rather than message leads, whose unrecognised outcomes fail rather than
  becoming verdicts, and whose closure is itself measured in both laundering
  directions, including `default`, custom distribution names
  and releases newer than the runner's own, the twelve `build_toolchain_*`
  diagnostics with disjoint triggers and a payload union derived from the
  firing site, the manager-owned guidance catalog with revisioned identifiers,
  total reason coverage, resolution-and-reachability coverage modes and
  immutable version transitions, and the no-auto-install rule. This is a design
  record for the next manifest and descriptor schemas.
  It changes no `1.0.0-rc.5` wire surface, schema, vector, cache key, receipt,
  marker, or claim.

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
