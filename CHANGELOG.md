# Changelog

All notable protocol changes are recorded here. Versions follow Semantic
Versioning for the complete specification set.

## 1.0.0-rc.1 - 2026-07-13

### Added

- Split normative protocol core, registry, manager profile, and conformance
  documents from the implementation-specific Curator CLI guide.
- Draft 2020-12 JSON Schemas for every versioned wire object and HTTP response.
- Authoritative positive and negative conformance vectors with deterministic
  regeneration.
- Compatibility, security, governance, and release policies.
- Cross-platform CI and shared Go/Python conformance gates.

### Changed

- Declared machine-home paths, command names, global environment variables,
  cache layouts, and managed comment text implementation-specific.
- Replaced implementation-oracle conformance language with schema, prose, and
  vector authority.
- Defined Curator Canonical JSON 1, complete snapshot validation, Merkle byte
  layout, bundle authentication, HTTP errors and limits, and key rotation.
- Defined deterministic closure ordering and portable Windows path rules.

### Compatibility

- Existing deployed wire filenames and `.agents/` layout are preserved.
- The signed JSON profile preserves bytes for all valid pre-RC registry
  objects; previously ambiguous numeric and string forms are now rejected.
