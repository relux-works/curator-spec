# Changelog

All notable protocol changes are recorded here. Versions follow Semantic
Versioning for the complete specification set.

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
