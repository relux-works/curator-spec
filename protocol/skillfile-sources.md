# Skillfile sources revision 1 (unreleased)

This is the normative, opt-in `skillfile-sources-v1` extension. It is an
unreleased working specification, not part of the rc.9 release or a claim that
any manager implements it. It extends core sections 3, 5–6 and 8–10 and manager sections
2–3 and 7 only for Skillfile schema 2. The separately scoped transport amendment is
[repository transport revisions 1 and 2](repository-transport.md).
Schemas live in [the draft source namespace](../schemas/draft-sources-v1/README.md).
A reader MUST explicitly support the extension before accepting schema 2.
All other core, registry, audit, assurance and manager requirements remain in
force. Existing schema and release artifacts are unchanged.

## 1. Acquisition and selection

Skillfile schema 1 retains its exact meaning. In particular, legacy `source`
is a path below the manager-configured source root, defaulting to the skill
name; it is not a path relative to the project. Schema 2 preserves `project`,
`agents`, `locale` and legacy skill entries by reference to schema 1. No
on-disk migration is implicit. Unsupported versions fail with an upgrade error.
Skill manifest versions remain independent and need no collection-specific edit.
The shared package identity and audit rules in this document also govern
manifest schema 9 dependency directories under core section 4.4; accepting that
manifest field does not make Skillfile schema 2 mandatory.

`sources` is an optional map of case-sensitive aliases to acquisition objects:

- `path`: a non-empty native filesystem directory path, absolute or relative
  to the declaring Skillfile's directory. No shell, tilde, environment-variable
  or URL expansion occurs. A downloaded skill cannot declare host paths.
- `git` (supported HTTPS, SSH URL or SCP spelling), or `repository` (explicit
  canonical `host/path` identity), plus exactly one `tag`, `branch`, `revision`.
  Revision is a full lowercase Git object ID. Tags and branches use the Git
  ref-name grammar. A declaration containing both identity spellings fails.

New sources intentionally admit the closed external-repository endpoint grammar
(core 6.3), not every historical core 6.1 URL scheme. Legacy entries keep their
existing grammar. Branches are admitted only in the root project; this extension
adds no floating transitive refs, package-owned local bindings or semver solver.

Each `skills` element is exactly one of:

1. An unchanged legacy named entry with its legacy acquisition/ref fields.
2. An individual `{name, from, directory}` selector.
3. A collection `{from, directory, include, exclude?}` selector.

Unknown aliases, unknown fields and mixes of forms MUST fail. `directory: "."`
selects the source root. Other directories are portable contained paths: no
absolute paths, empty/dot/parent components, backslashes, drive prefixes,
reserved device names, trailing component spaces/dots or glob metacharacters.
Resolve symlinks before containment checks; an escaping selector always fails.
Explicit source paths may point outside the project; selectors may not escape
that chosen source. An individual name MUST equal validated SKILL.md metadata
and the resolved skill manifest identity, where that manifest declares one.

These are the canonical directory grammar and containment rules for selected
skill packages. A manifest schema-9 `dependencies.skills` entry reuses them
for its repository-relative `directory`; see [core section 4.4](core.md#44-dependencies).
In both forms the selected path is relative to the acquired repository or
source root, and the resolved package directory must contain its own
`SKILL.md`.

Collections enumerate immediate child directories only. `include` is a
non-empty unique list of literal portable folder identifiers or `*`; `exclude`
is a unique list of literals only. `*` selects all immediate directories after
mandatory generated-output pruning. It does not recurse. `**`, partial globs,
files as members and path-valued members fail. Include literals are checked for
existence and directory type before exclusions; missing explicit members fail
even if excluded. Exclusions then remove matching names; a missing exclusion
is harmless. Every remaining directory, including one found by `*`, MUST have
valid SKILL.md frontmatter with the required name and description and satisfy
the ordinary package/manifest rules. Invalid discovered candidates fail the
whole operation rather than being skipped. An empty expanded collection fails.

Expand in ascending UTF-8 folder-name byte order. Validate the entire expanded
set and dependency closure before publication. Repeated direct selections of an installed skill
name (even identical selections), filesystem-equivalent destination names, or
conflicting dependency identities fail. Identical transitive requirements
unify under the existing closure rules, including diamond dependencies. No renaming, last-writer-wins or multiple
versions under one installed name is introduced. A collection is acquisition
syntax; each skill remains the dependency, audit, command-owner and installation
unit. Existing dependency resolution, trust, cycles, command collision and
readiness rules apply to the full closure.

## 2. Physical boundaries and admitted local inputs

`agents/skills` is authored input; `.agents/skills`, `.agents/bin`, adapter
skill directories and generated context surfaces are managed output. A broad
alias `path: "."` is legal: evaluate selected packages and effective inputs,
not just the alias root. Manager runtime stores, build caches, transaction
staging and the source snapshot store are outputs too.

Before traversing or copying, resolve physical paths with symlink and actual
filesystem case-equivalence rules. Reject a selected package within any managed
output. Prune every managed/generated output subtree, `.git` metadata and the
snapshot/staging trees deterministically before collection discovery and input
enumeration. Pruning a selected package or explicitly declared runtime/build
input is an error, not permission to install an incomplete package. Preserve
unmanaged-path conflict protection. A destination MUST NOT overwrite any
admitted context, runtime, build or dependency input, including through links,
adapters, casing aliases or a changed parent directory.

Selecting the project root as the package requires explicit `root_inputs` for
that source alias in machine-owned `source-policy.json` (source-policy schema 1).
Each listed path is source-relative, portable, link-free and disjoint from
outputs; a file selects itself, a directory its recursive contents. Unknown aliases and duplicate or overlapping root-input entries fail. Each
listed path MUST exist; missing or unreadable input is an error. The list
must include SKILL.md, the effective manifest and every required context,
runtime and build input. No required declared root may be omitted. The manager
MUST reject if it cannot prove separation, rather than infer author intent from
a recursively copied project root. Other packages admit their full regular-file
tree after the same mandatory pruning. `root_inputs` is admission configuration,
not a package-provided install hook. Changing it requires explicit refresh.

Recheck physical identity and destination separation immediately before each
publication write, under the existing serialized transaction. Do not follow
newly introduced links. A changed boundary fails and rolls back unpublished
state. Planning-time string prefixes alone are insufficient. The root-input
allowlist does not authorize takeover of unmanaged destinations.

## 3. Local snapshots and lock identity

A local `path` always means admitted filesystem bytes, including dirty, staged
and untracked files, whether or not `.git` exists. It never means Git HEAD.
Read regular files into a private staged snapshot; reject special files and
links in admitted inputs. Revalidate file identities, contents and the complete
admitted path set after capture; concurrent mutation fails with
`source_snapshot_changed`, requiring a new explicit attempt. All audit, build,
projection and install operations consume the frozen copy, never reread the
mutable original. Rehash the frozen copy before publication; mutation fails.

`local-snapshot-v1` defines a deterministic inventory. Each entry contains
package-relative portable `path`, `sha256` of raw bytes and `executable` (whether
any POSIX execute bit is set; false on filesystems without that metadata).
Directories themselves carry no entry. Sort entries by UTF-8 path bytes;
duplicates and filesystem-equivalent path collisions fail. Do not normalize
line endings, Unicode, file contents or executable bits. The digest is SHA-256
of CCJ-1 of exactly `{schema_version:1, algorithm:"curator-local-snapshot-v1",
files:[...]}`, prefixed `sha256:`. The inventory's `snapshot` holds that result
and is excluded from its own preimage. Empty files participate. Absolute source
paths, timestamps, owner IDs, `.git`, pruned output and traversal order do not.

A package identity is the disjoint union in source-types schema 1:

- `{kind:"local-snapshot", snapshot:<digest>}`; or
- `{kind:"network-git", repository:<canonical identity>,
  commit:{object_format,hex}, directory:<selector>}`; or
- `{kind:"configured-git", source:<legacy configured-root relative path>,
  commit:{object_format,hex}, directory:"."}` for legacy entries whose Git
  repository has no canonical network identity. `source` defaults to the skill
  name exactly as in schema 1. This is a scoped configured-root identity, not
  a network trust identity; existing Git commit semantics remain unchanged.

For a schema-9 transitive dependency, the package's directory is the manifest
selection normalized to `.` when absent. Distinct directories of one Git
repository at one commit are distinct package identities; the same directory
selected repeatedly for one skill name is one identity and unifies under core
section 7.

Git snapshots retain existing raw-object and integrity requirements. Every
member from one Git alias uses the same resolved commit. A local collection
freezes each package and the expanded membership together in one transaction.
Re-enumerate the admitted member set before lock publication; any membership
change during capture fails `source_snapshot_changed`.
A context hash is still computed by core section 8 and is not a substitute for
the local inventory digest: script-only and build-only changes change package
identity even when SKILL.md and projected context remain byte-identical.

`Skillfile.lock.json` uses skillfile-lock schema 1. `manifest_sha256` is the
CCJ-1 SHA-256 of the entire parsed declaring Skillfile, including declared paths;
it excludes no manifest fields. Machine-resolved absolute paths and endpoint
choices MUST NOT enter the lock. `members` records the resolved full closure,
sorted by UTF-8 skill name. Root members carry their zero-based `selection`
index; transitive members carry null. Each carries its source-relative
`directory`, package identity and context `content_sha256`. For both Git identity kinds these two
directory fields MUST agree. For legacy entries the directory is `.` relative
to that entry's selected repository. Duplicate names fail. `lock_sha256` is the
CCJ-1 SHA-256 of the lock with only `lock_sha256` omitted.

Initial explicit resolve/install creates the lock after all gates succeed.
Update/refresh is the only way to replace refs, admitted bytes or membership.
Launch and status never rescan collections, advance branches or replace a local
snapshot. Installation with an existing lock consumes the locked snapshot;
unavailable snapshots fail with `source_snapshot_unavailable`, and changed
manifest hashes fail with `source_lock_stale`. Do not silently recreate a local
snapshot from current bytes. Machine-private bindings record canonical physical
source location and root-input configuration for refresh; changes require
explicit refresh and never reinterpret an existing lock. Rebinding the same
bytes on another machine preserves package identity. Shared manifests with
absolute paths remain intentionally machine-specific, but locks do not copy
those paths into identity fields.

## 4. Runtime, builds, audit and persistent records

Local acquisition feeds the complete existing package pipeline. Context
projection retains its eligibility rules: `scripts/` is context only when no
commands are exported; runtime and build roots remain excluded from context;
build roots never enter installed script runtime. Declared script runtime goes
to the protected store, compiled artifacts to the immutable cache, and declared
commands to `.agents/bin`. Capabilities, dependencies, system-command readiness,
script-worker controls, toolchain admission, closed build drivers and assurance
preflight all remain mandatory. No arbitrary package install hooks, compiler
bootstrap or prebuilt binary-distribution route is added. External repositories
of a local package still obey manager section 11; local skill acquisition does
not turn their committed-HEAD substitutions into dirty-byte snapshots.

For schema-2 installations write marker schema 5, regardless of skill manifest
version. A core schema-9 installation also writes marker 5, including when its
root project still uses Skillfile schema 1. Its `package` replaces legacy
`source/git/ref_kind/ref/commit` fields;
its `lock_sha256` binds the installed selection and declared ref through the
validated lock and matching manifest. The following migration is exhaustive;
fields not replaced here retain core section 10 meaning, including applicability,
requiredness and canonical set ordering.

| Marker v4 fields | Marker v5 representation |
|---|---|
| `schema_version` | `5` |
| `source`, `git`, `ref_kind`, `ref`, `commit` | Effective `package`; declaration/ref selection in the manifest and bound lock. Never infer these from a transport endpoint. |
| `skill_schema_version` | Actual manifest version, 1 through 9 |
| `name`, `content_sha256`, `locale`, `agents`, `commands`, `dependencies`, `runtime_roots`, `build_roots`, `installed_at`, `files` | Retained, required |
| `build_source`, `requirements`, `mcp_servers`, `activation`, `requirers` | Retained with existing conditional/optional meaning |
| `attestation` | Retained registry/status/optional key ID summary for eligible Git packages; forbidden for `local-snapshot` |
| `substituted` | Retained non-empty legacy skill development-substitution identifier; forbidden for `local-snapshot` |
| `builds` | Retained driver-specific records below, with receipt version 3 |
| No predecessor | Required `package` and `lock_sha256` |

`attestation` MUST be present exactly when the effective plan selects existing
registry evidence and MUST equal its registry, status and key ID (including key
absence). Both `network-git` and legacy `configured-git` packages may record it
only when existing registry rules establish the exact canonical repository,
name, commit and context hash. A configured source path alone is not a registry
identity. This summary is not authorization: signed records and current trust,
revocation, freshness and assurance policy MUST still be checked when required.
A missing, unreadable, malformed, stale or mismatching required evidence record
MUST NOT become an unattested successful installation or current status.
`source-audit-v1` supplements this evidence; it does not replace it.

Top-level `substituted` applies only to unchanged legacy individual entries with
an admitted operator development substitution. Its value MUST equal the
existing substitution identifier in the effective plan and MUST otherwise be
absent. New `from` selectors do not gain development substitution support.
For legacy substitution, `package` records the effective Git source and actual
committed identity using the applicable Git arm; the bound manifest/lock retains
the declared selection. Existing legacy substitution acquisition remains
unchanged, including its committed-source rules. Substitution is not silently
converted to a dirty-byte local snapshot. Strict audit MUST reject development
substitutions during manager section 2.1 planning, before cache reads, compiler
execution or publication. Omitting the marker field cannot bypass that gate.
External repository substitution is independent: it remains the Boolean and
typed `substitution` inside each external build record, even for a local package.

Status MUST compare package, lock, attestation and substitution against the
effective plan in addition to every retained core section 10 comparison.
Changed registry/status/key, substitution identifier, declared ref, package or
lock makes the installation non-current. Missing/unreadable evidence is unknown
where the existing profile distinguishes it, never current; checking status
returns nonzero and stays read-only. Repair MUST revalidate the exact locked
source and required evidence; it MUST NOT adopt marker summaries as trust or
silently refresh a lock. Explicit refresh reruns all gates and atomically
replaces the lock and marker only after success. Failure preserves prior state.
Old markers remain readable on legacy lanes but MUST NOT attest schema-2
installation currency. Unknown marker versions fail closed.
Runtime store keys are `(skill name, SHA-256(CCJ-1(package)))`, with a distinct
`source-v1` namespace; never substitute a snapshot hash into a Git commit field.
Status, repair, rollback and GC follow those keys and lock references. A runtime
edit followed by refresh changes the key and requires new runtime publication.

Build receipt schema 3 wraps the existing closed driver input in
`input:{schema_version:3,package,build}`. `cache_key` is SHA-256 of CCJ-1 of that
whole input. Existing driver-input schema versions 1 and 2 and their required
execution policies, toolchain and dependency fingerprints remain unchanged
inside `build`. Use a distinct receipt-3 cache namespace; no legacy cache hit
can satisfy it. Marker-5 build entries bind receipt version 3, exact receipt
hash, cache key, artifact hash/path, driver and execution policy. Local `go-v1`
records retain every `buildRecordV1WithReceiptVersion` field. External
`go-repository-v1` records retain every `buildRecordV2` field: repository,
declared identity and locked commit, optional declared tag, effective identity,
object format and commit, Boolean substituted and conditional typed substitution,
external build_source and descriptor_target, as well as the common fields.
Only receipt_schema_version changes to 3. External substitution shape, commit
length, exact-tag provenance and all cross-field equality rules remain intact.
An external record MUST NOT omit these fields in favor of a receipt hash alone.
Compare the record with receipt-3 `input.build` under the existing external
receipt-input rules; compare receipt-3 `input.package` with marker `package`.
Receipt/cache hashes are recomputed over the new wrapper, not copied from v4.
Top-level `build_source` remains required exactly for active local `go-v1`
commands and absent otherwise; an external-only build binds its source solely
per external record. Validate all
cross-record equality and artifact bytes before activation. Preserve existing
whole-snapshot audit-before-cache/compiler ordering and atomic rollback.

Machine-local source audit schema 1 binds the package identity, context hash,
policy digest, full evidence digest, timestamp and decision. Evidence is the
persisted complete existing audit report, including findings, pins, revocations
and effective script/assurance policy labels. A missing, unreadable or
mismatching report fails; the source-audit object is not a self-authorizing
attestation. Recompute/validate it under trusted machine policy. Local inputs
have no network registry identity: registry audit-record-v1 remains unchanged
and MUST NOT be forged for local content. Where policy requires a network
attestation that local content cannot supply, installation fails. Existing
operator-pin policy may admit local content only where already authorized;
canary, revocation and required assurance gates cannot be bypassed by a pin.
Network-Git members may use existing registry evidence only with exact name,
canonical repository, commit and context hash matching. No registry redesign
or new signed record format is implied.

For a schema-9 dependency, the source-audit record's package identity carries
the normalized selected directory. Audit-cache equality includes the complete
package identity, so a decision for another directory in the same repository
and commit is not reusable. Registry records keep their existing repository
and content matching rules; they do not replace this package-specific audit
record.

Assurance permits, execution receipts and checkpoints retain their versioned
shapes: bind the exact receipt-3 build input digest in `build_input_sha256`.
This adds no verified-provider script operation; script-worker rules retain
their existing supported operation surface.
Their provider, nonce, freshness, artifact and checkpoint bindings remain
required. An implementation unable to bind that input MUST reject execution;
it MUST NOT downgrade or claim compatibility based on a context-only hash.

## 5. Diagnostics and conformance bounds

Required stable error classes are `source_alias_unknown`, `source_selection_invalid`,
`source_member_missing`, `source_member_invalid`, `source_name_conflict`,
`source_output_overlap`, `source_snapshot_changed`, `source_snapshot_unavailable`
and `source_lock_stale`. Report the selector/member and reason without secrets.
Selection, snapshot, closure, audit or publication failure changes neither the
previous lock nor installed state. Schema failures precede filesystem/network
work. The [draft vectors](../conformance/draft-sources-v1/README.md) distinguish
structural checks from filesystem, resolver and execution requirements. Passing
schema cases is not evidence of a local installation or native containment.
