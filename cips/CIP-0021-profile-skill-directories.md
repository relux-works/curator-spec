# CIP-0021: Package directories in profile skill requirements

- **Status:** Accepted; decision: operator, 2026-10-18
- **Owner:** operator
- **Created:** 2026-10-18
- **Related:** [Decision 0027](../decisions/0027-profile-skill-directories.md)
- **Affects:** environments §§1.1, 1.3, 1.4, 2, 9.1, 9.4, 13.1; profile manifest and lock schemas; manager resolution, audit and materialization

## Summary

Permit an optional `directory` on a schema-2 profile's `requires.skills` entry.
It selects the skill package inside the requirement's pinned git snapshot,
using the same portable path and snapshot rules as context and MCP
requirements. The lock records the directory; audit and materialization
consume that package root. Omission retains repository-root addressing,
and legacy global-skill migration is unchanged.

## Motivation and user stories

An operator maintains several skills in subdirectories of one repository.
A profile should require one such skill without repackaging it into a new
repository or duplicating a project Skillfile in every consuming project.
The operator's inventory reported 18 of 40 installed skills affected by
repository-root-only profile addressing; this is motivation supplied with
the decision, not a reproduced inventory or implementation measurement.

## Current state

Before this amendment, environments revision 1 §2 explicitly forbade
`directory` on skill requirements while admitting it on context and MCP
requirements. Core rc.14 §3 already defines a skill package as a snapshot
or a directory within one, and Skillfile source selection already supports
directories. The profile prohibition is the missing addressing surface.
This proposal concerns the specification; it makes no claim about a
particular implementation revision or runtime probe.

## Design

### Options considered

1. **Select a directory in the profile requirement (adopted).** Add only the
   existing `directory` vocabulary. This reuses acquisition, path validation,
   lock identity and selected-root audit; it requires consumers to propagate
   the root consistently through all lifecycle stages.
2. **Repackage every skill at a repository root (rejected).** This avoids a
   selector but creates repository/release overhead and duplicate provenance
   for otherwise valid packages. Repackaging provides no stronger snapshot
   containment than the existing directory rules.
3. **Use project Skillfile selection only (rejected).** This works for
   project-local skills but cannot express the operator's profile-scoped
   global skill set. Repetition across projects is not profile adoption and
   must not bypass profile audit or managed-home isolation.

### Recommendation

Accept `requires.skills.<name>.directory` in manifest schema 2 with exactly the context/MCP
portable-path grammar, never the `path` source kind. An absent selector
addresses the snapshot root; explicit `.` is invalid under this grammar.
Read `SKILL.md`, the optional skill manifest and all package-relative files
at the selected root. Preserve core §4.4 `mode` and `commands` semantics.

Every requirer of one name must agree on source identity and directory;
disagreement uses `context_range_conflict`, as for context requirements,
with all requirers identified. Record the selector on schema-4 profile lock
members and include it in lock identity. Audit findings, capabilities and
content hashes come from the selected package tree; managed homes and
in-place surfaces link it as the skill root.

## Security considerations

Treat the git repository as hostile. A portable selector must name a real
directory inside the immutable snapshot and must not traverse any symlink,
including one whose target stays inside the snapshot. Reuse
`profile_source_invalid` and the context snapshot discipline; directory
selection grants no exception to source allowlists, signer verification,
strict audit or protected-store checks. Validate before publication, and
never execute package code during resolution, audit or materialization.

Capabilities from the repository root or a sibling must not authorize the
selected skill. Missing or unreadable selected content must not fall back
to another directory. Bind cache/audit reuse to the selected package identity;
the same repository and commit with another directory is a different root.
Use the verified immutable snapshot throughout the operation to prevent a
selection/consumption race. This adds no credential or execution authority.

## Compatibility and migration

Requirements without `directory` retain existing addressing behavior.
Reuse the already allocated rc.7 successors: context manifest schema 2 and
context lock schema 4. Both carriers are an unreleased extension and may
grow before release; this amendment adds skill-directory vocabulary to them,
retaining their complete closed shapes and required settings/precedence fields.
No new carrier identity is allocated. Published manifest schema 1 and lock
schemas 1–2 remain byte-identical; schema 1 with skill `directory` remains
refused as `context_manifest_invalid`. Readers must explicitly adopt the
successors before accepting this selector; relabeling old data is forbidden.
No marker adds fields: existing markers pin the profile lock and skill surfaces.

Legacy migration in environments §9.4 is explicitly unchanged. Its install
records carry no directory, so migrated skills keep repository-root
addressing. No discovery, selector inference or record rewriting is added.
Released rc.14 corpus bytes, candidate pins, core dependency manifests and
Skillfile vocabulary are unchanged. Specification adoption enables no runtime.

## Specification changes

[Decision 0027](../decisions/0027-profile-skill-directories.md) adopts the
amendment. Environments §2 replaces the prohibition with selected-root,
grammar and containment rules; §§1.3–1.4 bind lock identity and agreement;
§§9.1 and 9.4 bind audit and links. The already allocated unreleased
manifest-v2/lock-v4 schemas admit the selector, as recorded in
[rc.7 carriers](../protocol/rc7-carriers.md), and separate conformance vectors
name positive lifecycle observations and negative diagnostics.

## Implementation plan

1. Publish this CIP, Decision 0027, normative prose, schemas, vectors and
   changelog together in one specification change.
2. In the separate manager implementation leaf, propagate selection through
   resolve, lock, audit and both materialization forms; retain migration.
3. Qualify the real lifecycle entry points against this vector family before
   claiming implementation conformance. No implementation code belongs here.

## Test plan

Compile the affected schemas with Draft 2020-12 and run named positive and
negative schema cases, including narrowing controls against the old
root-only schema and against incorrectly constrained path validation.
Run the repository validation, Python tests, Go generator tests and
deterministic regeneration checks without changing frozen corpus pins.

The lifecycle vectors require real `profile install`, `profile update`,
`profile sync`, and first-use migration consumers to observe selected lock,
audit identity and managed-home/in-place roots. Reject absolute and parent
paths, symlinked components, missing required package content, disagreement,
and `directory` with a `path` source before publication. Include manifestless
context-skill and root-addressed controls. Spec-schema success does not prove
manager filesystem behavior; runtime narrowing mutants belong to its leaf.

## Open questions for the operator

None. The operator accepted directory selection and unchanged migration on
2026-10-18; this record implements that decision without reopening it.
