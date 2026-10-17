# Managed-home snapshots

This document is normative for `managed-home-snapshot-v1`, adopted by
[CIP-0014](../cips/CIP-0014-managed-home-snapshots.md), implementation-plan
leaf 1, under owner decision 2026-10-15 (D1, D4–D6). It extends
[environments](environments.md) without changing released schemas or launch
fragment versions. Publication specifies a contract, not shipped support.

## 1. Ownership and command

A live agent session MUST NOT point at a Curator managed home. Repair,
profile switching and global skill synchronization may rewrite that home
in place. Curator owns content selection, verification and export; a
launcher consumes the resulting descriptor. Session policy, trust, goals,
resume state and credentials remain separately owned. A consumer MUST NOT
reconstruct Curator's content inventory by inspecting a home.

```text
curator env materialize <env-id> [--profile <name>] --into <dir> [--format json]
curator env materialize <env-id> [--profile <name>] --manifest-only --format json
```

Profile selection follows environments §10.1. Exactly one of `--into` and
`--manifest-only` is REQUIRED. `--manifest-only` requires explicit
`--format json`; bare `--manifest-only`, an unsupported format, or combining
the two destinations MUST fail with `usage` before selection, lock acquisition
or writes. Manifest-only runs the same capture, relocation and hashing as
export but publishes no directory; it is an observation, not attestation of
an existing session. Both forms MUST NOT repair, provision, recover a
transaction, log in, change a profile or launch a tool.

On success `--format json` emits exactly the manifest bytes defined in §4.
Without it, export reports the destination and manifest digest without file
contents. Failure emits no success manifest; diagnostics go to stderr and
MUST NOT disclose content, secrets or credential-source metadata.

## 2. Destination and publication

`--into` may be caller-relative. The validated absolute handle is internal
and MUST NOT be serialized. The destination MUST be absent with an existing
caller-owned private parent, or an intact prior snapshot of this version
accepted only as a verified no-op. An existing empty directory MUST refuse
with `environment_materialize_destination_invalid`. Non-directories, unrelated nonempty directories,
unknown versions, uncertain ownership and modified snapshots MUST refuse.
An existing manifest does not authorize replacing arbitrary paths. There is
no force, takeover or recursive-cleanup mode.

Validation and writes MUST retain directory handles and use no-follow
operations for every component, including all ancestors and the target.
Linked ancestors are refused, not resolved. Reparse points, directories
writable by other principals and uncertain owner/ACL evidence MUST refuse.
Windows requires equivalent handle, owner/ACL and reparse-point checks.
The target MUST NOT equal, contain or lie within the manager root, profile
stores, managed homes, native tool homes, credential roots, repository
administration or active workspace. Identity and ancestry checks MUST use
handles rather than lexical prefixes. A host must allocate its private
session destination outside the active workspace.

Directories MUST be private `0700`; metadata and ordinary files `0600`;
skill assets `0700` only when the verified source is executable. Equivalent
private ACLs apply on Windows. Output files MUST be independent regular
copies. Symlinks, hard links, set-id bits, source ownership, ACLs, xattrs and
hard-link identity MUST NOT be imported. Executability does not grant
authority to execute outside the existing execution policy.

Validate without writes first. After capture and revalidation (§5), stage
beside the absent target and publish by no-replace rename. For a prior snapshot, verify all
metadata, actual file bytes, sizes, modes, the complete entry set and absence
of extras. Identical manifest bytes are a no-op only after this verification.
A different generation MUST refuse with `environment_materialize_snapshot_mismatch`
and require a fresh absent destination.
Failure MUST preserve the target, including any competing replacement, and emit no success. Cleanup may
remove only staging entries privately created by this invocation.

An existing empty target cannot be replaced portably conditional on its
retained identity. No-replace rename refuses an existing name; rechecking
then removing or replacing the entry can affect a same-user competing
replacement. Advisory locks do not exclude that substitution. Requiring an
absent target permits no-replace publication without replacing a competing entry.

## 3. Content closure and relocation

Select the closure from the verified lock, adapter renderer and marker.
A marker alone MUST NOT authorize an unknown content class. Include:

- Root context and referenced-form support chapters, snippets and generated
  adapter content needed to discover them.
- Complete admitted skill payloads, including synchronized global skills
  that participate in the home, with verified bytes and execute metadata.
- Applicable inert system-prompt and declared MCP content, their channel
  descriptors and environment variable names, never variable values.
- Only non-secret generated adapter content required by those surfaces,
  rendered from verified inputs rather than extracted from tool state.

Exclude credentials and their links/values; OAuth metadata; session history,
goals, resume databases, locks, caches, tool binaries/downloads, backups and
journals; marker internals; provisioning seeds; foreign XDG seeds and
unmanaged files. In particular native `config.toml`, `.claude.json`, Muse
trust/settings state, `auth.json`, `.credentials.json` and Keychain data
MUST NOT be copied merely because present. Existing admission and secret
detection apply to selected content; a secret-bearing selected asset MUST
refuse export, not be silently redacted or omitted.

The snapshot root contains `manifest.json`, `launch.json` and `home/`.
For Muse `home/` contains the four XDG parents; for opencode it would be the
XDG config parent containing `opencode/`. Other adapters use `home/` directly.
Directories are derived from file paths and the adapter layout, not arbitrary
inventory entries. Runtime creation of empty state directories is separate.

Do not recursively follow source links. For a marker-recorded managed link,
verify its admitted store identity and read the verified store object through
protected handles. Reject unrecorded links, nested escaping links, reparse
points and special files; never dereference credential or foreign-XDG links.
Destination no-follow rules have no exception for managed links.

Generated live-home/store references MUST be rendered again from the same
verified inputs using snapshot-relative references. Verify semantic
correspondence and hash the output bytes, not the raw source hash. Opaque
skill assets MUST NOT undergo text substitution. A form requiring an absolute
include without qualified relocation MUST refuse; it cannot retain live-home
references or invent include support.

## 4. Manifest, descriptor and identities

The closed schemas are
[`managed-home-snapshot-v1`](../schemas/managed-home-snapshot-v1/managed-home-snapshot-v1.schema.json)
and [`snapshot-launch-v1`](../schemas/managed-home-snapshot-v1/snapshot-launch-v1.schema.json).
Unknown members or versions MUST refuse. Both files are registry CCJ-1 bytes
followed by exactly one LF. All hashes below are bare lowercase SHA-256 hex.

| Manifest member | Required meaning |
|---|---|
| `snapshot` | `managed-home-snapshot-v1` |
| `adapter` | Closed environment ID, equal to descriptor `environment` |
| `profile` | `name` and `lock_sha256`, equal to descriptor `profile` |
| `curator_version` | Exact producing Curator release identifier |
| `fragment_sha256` | SHA-256 of the source resolve fragment's CCJ-1 bytes **without** presentation LF |
| `launch_sha256` | SHA-256 of exact `launch.json` bytes **including** LF |
| `files` | Every content file under `home/`, sorted by UTF-8 path bytes, as `{path, size, sha256, mode}` |

Paths use the existing portable-path grammar, MUST start with `home/`, and
MUST NOT have absolute, drive, UNC, empty, dot or parent segments, NUL,
duplicates, case/Unicode-normalization collisions or file/ancestor conflicts.
Apply environments §5 platform-path collision rules, including directory
components. Sizes are exact nonnegative CCJ-1 safe integers. Modes are only
`0600` or `0700`. Directory identities are derived, never file entries.

`launch.json` is a portable descriptor, **not** a launch fragment revision.
It carries `descriptor: "snapshot-launch-v1"`, `environment`, `profile`,
`precedence`, `env`, `permissions` and applicable `system_prompt`, `mcp` and
`root_context`. Precedence, permissions and channel semantics retain
environments §§10.2–10.3 meanings; channel selection remains adapter-defined,
not arbitrary data supplied by a consumer. Home bindings and content `path`
members are snapshot-root-relative. A channel's fixed `filename` retains its
existing adapter-home-relative meaning.

| Adapter | Exact descriptor `env` map |
|---|---|
| `claude_code` | `CLAUDE_CONFIG_DIR: home` |
| `codex_cli` | `CODEX_HOME: home` |
| `muse` | `XDG_CONFIG_HOME: home/config`, `XDG_DATA_HOME: home/data`, `XDG_STATE_HOME: home/state`, `XDG_CACHE_HOME: home/cache` |
| `opencode` | `XDG_CONFIG_HOME: home` (reserved; materialize refuses, §6) |
| `pi` | `PI_CODING_AGENT_DIR: home` |

`root_context`, when present, is exactly `{"exclusive": true}`, only for
Muse. Curator MUST emit it iff verified current Muse root context is selected;
failed reads or missing required content cannot silently omit it. This is
the D12 fact coordinated with CIP-0017, whose fragment revision remains a
separate leaf. The consumer MUST use this fact rather than infer it from file
layout. It requires the existing form-specific foreign-context exclusion;
no runtime qualification is implied. `system_prompt.path` and `mcp.path`
MUST reference listed files; Muse has neither channel and pi has no MCP.
Required discovery/support content MUST be in the inventory. HOME is preserved.

No absolute source paths, credentials or machine-local PATH prefixes may
appear in the descriptor. `path_prepend` is not admitted by this version:
a source fragment requiring it MUST refuse until a separately covered tool
resource contract exists. The descriptor does not export tool binaries,
profile Codex settings or credential backend policy; their separate owning
contracts must cover them at plan composition.

`manifest_sha256` is SHA-256 of exact `manifest.json` bytes including LF.
It is external, never self-listed. `files` excludes both metadata files;
`launch_sha256` covers the descriptor. **The fragment binding and therefore
the manifest digest are source-home-bound.** Absolute paths in the source
fragment change `fragment_sha256` even when portable output is identical.
It is not a portable content digest and MUST NOT be used alone for cross-home
equivalence. No source path itself is exported.

Portable comparison MUST compare the descriptor bytes/digest, entire file
inventory and all remaining manifest members, excluding only
`fragment_sha256`. It MUST recompute actual file bytes, sizes, modes and
entry set. Version, adapter, profile pin and producer version still bind
identity. Plan/resource integrity binds exact manifest bytes, including the
source binding; it is distinct from portable comparison and archive identity.
Attach/resume retains its originally admitted baseline and overlay identity;
it MUST NOT replace them with newly observed values after a mismatch.
Manifest-only and export from the **same unchanged source fragment and
verified inputs** MUST yield identical manifest bytes. Cross-home equality
applies to the portable comparison above, not the manifest digest.
Timestamps, destination paths, OS identities and random generation IDs are
not portable identity inputs.

## 5. Consistent capture and refusals

Acquire the manager-home mutation lock used by repair and switching with
the existing bounded wait, but through a **non-recovering acquisition path**.
The current implementation's `beginOperation` also recovers journals and
MUST NOT be reused as-is. Under that lock:

1. Select the profile and effective machine policy anew; do not reuse an
   unlocked selection or recursively call a locking repair operation.
2. Refuse pending recovery. Verify profile, lock, store, marker, currency,
   credential metadata and source boundaries through read-only checks.
3. Freeze the closure and fragment; read admitted regular objects through
   protected handles, verify sizes/hashes/modes and capture private output.
4. Revalidate selection, policy, lock, marker, surfaces and every captured
   object's identity before releasing the lock. Any mismatch or failed read
   aborts; equal fragments alone do not prove a consistent generation.
5. Publish only after verification. Do not transport or wait on external
   services under this lock.

The lock serializes cooperating writers, not arbitrary external processes.
Existing environments diagnostics retain their meanings, notably
`environment_home_stale` for stale/unprovisioned homes,
`environment_lock_unavailable` for contention, and existing store, marker,
surface, path, passthrough and credential metadata refusals. Read failure is
never absence, detachment or a reason for native fallback. Stale sources
require explicit repair/preparation and a new invocation.

The following **new** codes are frozen here; publication does not claim an
implementation already emits them. Every refusal emits no success manifest,
preserves the source and prior destination, and permits only own-staging cleanup.

| Condition | Code |
|---|---|
| Invalid, linked, protected, foreign-owned or unrelated destination, including failed destination ownership reads | `environment_materialize_destination_invalid` |
| Pending source transaction recovery; explicit recovery/repair required | `environment_materialize_recovery_required` |
| Source generation/identity changes during capture or final revalidation | `environment_materialize_capture_drift` |
| Selected form cannot be relocated without changing semantics; nonportable launch requirement | `environment_materialize_relocation_unsupported` |
| Prior snapshot malformed, modified, incomplete, unreadable, has extras, or differs from requested generation | `environment_materialize_snapshot_mismatch` |
| Adapter cannot supply the self-contained admitted closure (currently opencode) | `environment_materialize_adapter_unsupported` |
| Selected content is secret-bearing under existing admission checks | Existing secret/admission refusal; no new alias |

## 6. Adapter and consumer boundaries

Consumers MUST use the descriptor, not maintain a second export inventory.
Bind relative paths only at plan composition, covering exact argv, env,
content and policy-overlay bytes. Executor behavior remains verification and
application. Credentials are a separately admitted channel, never snapshot
content. Local credential linkage, where supported, is separate too.

Codex receives the profile MCP layer unchanged, exactly one `-p curator-mcp`
when declared, with bytes verified immediately before launch (a missing layer
is silently ignored by the tool). The session owner supplies policy config,
trust and resume state separately and MUST NOT import ambient `mcp_servers`.
A conflicting gateway/profile MCP set, duplicate selector, weakened policy
or overlay collision MUST refuse unless an owning contract already specifies
the intersection. Profile settings use separate inherited launch overrides
under D13; native `config.toml` is never rewritten by this export.

Claude uses its system channel and declared `--mcp-config` plus
`--strict-mcp-config`; onboarding/trust and credentials are separate. Muse
uses all four XDG parents and the root-context fact, preserving HOME;
credential backend selection belongs to launch policy. No claim is made
about Muse skill discovery or refresh writes. Pi uses its specified system
channel, with settings/models and credentials separate; no MCP is synthesized.
Opencode materialization MUST refuse until a profile-local skills target is
specified and qualified. Existing opencode resolve support is unchanged.

Runtime B (sealed content with distinct writable state/policy slots) is an
**interpretation of D6 awaiting operator confirmation**, not an assertion
that D6 already approves that refinement. No adapter/runtime may activate
until its protection and start/login/model-turn/native-resume behavior are
qualified. Chmod in an agent-owned tree alone does not prevent ancestor
replacement. Overlays MUST NOT shadow content; an attempted protected-content
rewrite MUST refuse that runtime combination rather than make content mutable.

## 7. Deferred transport and conformance bounds

Swarm delivery must bind archive digest/size, exact manifest and descriptor
digests, adapter/profile pin, bounds, runtime projection and overlay identity
to an independently admitted immutable plan. The dispatcher relays opaque
bytes and journals digests; it neither resolves profiles nor learns home
paths. Executor verification before child code must establish full manifest
correspondence, not just an archive hash. Self-minted digests are integrity
metadata, never authorization. Missing evidence, failed reads, unknown
contracts or corruption MUST NOT trigger resolve or live-home fallback.

Exact archive encoding, header/padding/end bytes, caps, plan wire names and
cross-service refusal mappings remain leaf 5 work. CIP-0014's proposed tar
subset and numbers are **not frozen by leaf 1**; no interoperable archive
claim is admitted yet. Runtime projection/protection and operator confirmation
remain leaves 3/6 activation gates. Snapshot schemas do not authorize launch.

The [separate conformance corpus](../conformance/managed-home-snapshot-v1/README.md)
freezes metadata bytes, hashes, structural cases and semantic counterexamples.
It is not merged into the released core corpus. Repository checks prove
schema/byte/semantic-vector consistency only, not execution of materialize,
destination syscalls, race handling, secret detection, or transport/runtime
protection. Required production-entry tests remain in CIP-0014's test plan.
The corpus's operation-vector notes freeze required refusals and state
invariants for those future entry-point tests without claiming to run them.
