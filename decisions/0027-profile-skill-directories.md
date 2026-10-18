# Decision 0027: Package directories in profile skill requirements

## Status

Accepted; decision: operator, 2026-10-18.
Adopts [CIP-0021](../cips/CIP-0021-profile-skill-directories.md).

## Context

Environments §2 admitted directory selection for context and MCP
requirements but forbade it for skills, despite core §3 and Skillfile
selection supporting skill packages within a repository. Profiles could
not name existing shared-repository skills without repackaging.

## Decision

Permit optional `directory` on manifest-schema-2 `requires.skills` using the context/MCP
portable-relative-path grammar and immutable snapshot discipline. The
selected package root supplies `SKILL.md`, manifests and relative content.
Core §4.4 activation and command semantics are unchanged. Requirements use
git sources; `directory` on a `path` source remains invalid.

Require all requirers of one skill name to agree on canonical source and
directory, using `context_range_conflict` rather than a new diagnostic.
Schema-4 lock skill members record the selector and bind it into lock
identity. Audit findings, capabilities and content identity are scoped
below it; managed-home and in-place links use it as their skill root.
No escape or symlink traversal is allowed, with `profile_source_invalid`
as for context directories. Missing required skill content is
`manifest_invalid`; pure context skills still may omit a manifest.

## Alternatives

Repackaging every skill at a repository root adds needless repository and
release ownership. Project Skillfile-only selection cannot express a
profile's global skill set. Both are rejected in favor of the existing
directory vocabulary on profile requirements.

## Compatibility impact

Omitted selectors retain repository-root addressing. Reuse the already
allocated rc.7 manifest-v2 and lock-v4 carriers: both are an unreleased
extension and may grow before release. Retain their complete closed shapes,
including required lock precedence and empty settings fields. No new
identity is allocated. Published manifest schema 1 and lock schemas 1–2
stay byte-identical. Schema 1 carrying skill `directory` remains refused
as `context_manifest_invalid`; readers explicitly adopt the successors,
never relabel old data. No marker field is needed: its lock pin already
binds selection. The allocation is recorded in [rc.7 carriers](../protocol/rc7-carriers.md).
Legacy global migration (§9.4) is unchanged because its install records
carry no directory; no layout discovery or inferred selector is introduced.
No core manifest, released vector, candidate pin or implementation is changed.

## Security impact

Selection reuses containment, no-symlink, source admission, strict audit and
protected-store rules. Sibling/root manifests cannot lend capabilities to a
selected skill, and missing selected content cannot fall back to them.
Lock and audit identity bind the package directory. There is no new package
execution, trust exemption or credential surface.

## Adoption evidence and limits

Normative changes are in [environments](../protocol/environments.md) §§1.1,
1.3, 1.4, 2, 9.1, 9.4 and 13.1. The separate
[conformance family](../conformance/profile-skill-directories-v1/README.md)
contains schema cases and lifecycle vectors with named diagnostics.
The manager implementation and real lifecycle qualification follow separately.
