# CIP-0014: Managed-home snapshots: `curator env materialize`

- **Status:** Accepted
- **Accepted:** 2026-10-15 (owner decision 2026-10-15)
- **Normative text:** [Managed-home snapshots §§1–7](../protocol/managed-home-snapshots.md); [environments §§8.1, 9.2, 10.1, 10.5, 13](../protocol/environments.md); [schemas](../schemas/managed-home-snapshot-v1/README.md); [conformance](../conformance/managed-home-snapshot-v1/README.md); [Decision 0010 amendment](../decisions/0010-agent-environment-profiles.md#snapshot-lifetime-amendment-2026-10-15).
- **Owner:** Curator specification maintainers (orchestrator); decision: operator
- **Created:** 2026-10-15
- **Related:** owner decision 2026-10-15 (D1–D6, D9, D12, D13); CIP-0003; CIP-0011; TASK-261014-3ntl3f — interim session content copy; TASK-261014-28uxsf — attach/resume content identity
- **Affects:** environments §§5, 7, 8, 9, 10, 13; new snapshot schema and conformance family; curator; curator-agent-launcher §10; skill-agents-management; skill-project-management; swarma-dispatcher R-TRANSFER

## Summary

Curator gains `env materialize`, which exports a verified, credential-free
snapshot of an environment's agent-visible content as regular files and a
digest manifest into a caller-owned directory. A session consumes that
snapshot through a private session home, keeping its tool policy and mutable
state separate from Curator's home. In the swarm, the caller packages the
snapshot as a bounded canonical archive covered by the launch plan; the
dispatcher relays it and the executor verifies and installs it read-only.
Leaf 1 is normative at the pointers above. Acceptance does not assert that
the command, launcher integration or transport is implemented.

## Motivation and user stories

1. A session must keep the content it started with while another command
   repairs a home, changes the current profile, or synchronizes global skills.
   It must never read a live managed home: owner decision 2026-10-15 (D4).
2. A hosted Codex session needs its own tool policy and trust configuration,
   while receiving all profile instructions, skills and the declared MCP
   layer. The session manager must not maintain its own adapter inventory:
   owner decision 2026-10-15 (D1, D5).
3. An agent in another OS account needs exactly the caller's admitted content,
   without access to the caller's Curator paths, native credentials or state.
   It receives a plan-covered archive: owner decision 2026-10-15 (D6).
4. Attach and resume must detect changed instructions or launch configuration
   before an agent starts. A lock digest alone cannot attest the bytes of a
   private copy or its session policy.

## Current state

### Evidence baseline

Code citations in this section use curator `00fec196` and
skill-project-management `b057ef468`, not their moving working trees.
Specification citations use curator-spec `d34d8a6`, environments revision 1;
curator-agent-launcher SPEC `0.5.1-draft` at `9ad2f016`; and
swarma-dispatcher draft `v0.14` at `b719e230`.
The decisions supplied with this proposal are binding target requirements,
not proof of shipped behavior.

### Provisioning and concurrent mutation

- `curator/internal/envprofile/managed.go:2565` documents `Resolve`: current
  homes are verified lock-free, stale homes refuse without repair, and repair
  provisions or rewrites under the manager-home mutation lock.
  `managed.go:2744` re-reads resolution inputs under that lock before repair.
- `curator/internal/envprofile/lock.go:18` bounds lock acquisition at 30 seconds;
  `lock.go:31` describes serialization and recovery. Per-entry home payloads
  remain direct writes under the lock, rather than one atomic home swap.
- `curator/internal/envprofile/global.go:299` (`syncManagedProfile`) calls
  `Resolve` with `Repair: true` for every participating adapter. Existing Muse
  homes participate; Muse is not implicitly provisioned by every global sync.
- `curator/internal/envprofile/switch.go:153` and `switch.go:169` put
  `profile use` under the same mutation lock. Environments §9.2 specifies
  in-place rematerialization and current-pointer publication. Owner decision
  2026-10-15 (D4) additionally establishes the running-session hazard: repair,
  switching and global sync do not protect a session's content lifetime.
- Environments §§5 and 8.1 materialize from locked store entries, using links
  or copies. Section 8.3.1 replaces entries atomically, never writes through
  unmanaged links, and rejects linked intermediate components below the root.
  Section 10.1 verifies currency and store integrity; §8.4.1 distinguishes
  absence from failure to read. None of these is a snapshot lifetime contract.

### Adapter inventory and exclusions

The following inventory is from environments §§7.1, 7.3, 7.4, 7.8 and 8.1.
Paths are relative to the adapter home unless its parent layout is explicit.
This table records current surfaces; export policy is specified below.

| Adapter | Root context / skills | Inert system / MCP content | Seeds, credentials and tool state |
|---|---|---|---|
| `claude_code` | `CLAUDE.md` (always copied); `skills/` | `.agent-context/system-prompt.md`; `.agent-context/mcp/claude_code.json` with strict MCP channel | Minimal `.claude.json` seed with onboarding and project entries; per-home Keychain or file credentials depending on platform/backend; histories, trust and approvals belong to the tool |
| `codex_cli` | `AGENTS.md`; `skills/` | System-prompt channel content; `curator-mcp.config.toml`, selected by `-p curator-mcp` | Tool-owned `config.toml` provisioning seed; revision A retains native MCP, B strips it; `auth.json` passthrough for file storage; session databases and histories are state |
| `muse` | `config/muse/AGENTS.md`; `data/muse/skills/` (native discovery unverified) | No system-prompt or MCP channel in fragment v3 | Profile-sourced `config/muse/settings.json` and `trust.json` seeds; `config/muse/auth.json` credential; sessions, databases, plugins, model catalog, memory, locks, state and cache are tool state |
| `opencode` | `opencode/AGENTS.md` below the XDG config parent; skills remain the machine-global native surface | System content and MCP JSON below the adapter home's `.agent-context/`; `OPENCODE_CONFIG` channel | Allowlisted foreign XDG config links; authentication and state remain ambient through data/state XDG roots |
| `pi` | `AGENTS.md`; `skills/` | System-prompt file channel; no MCP channel | `settings.json` and `models.json` seeds; `auth.json` passthrough; tool trees, sessions and caches are state |

Environments §5.3 also materializes referenced-form support files and adapter
configuration where required. Section 5.5 defines the inert system-prompt
file; §5.8 defines the MCP file bytes, with environment variable **names**
in the fragment and no environment variable values in the MCP file.
A referenced-form support file is content, even if its suffix looks like
configuration. A provisioning seed is tool-owned after provisioning and is
not content merely because it is a regular file (§7.4).

The open isolation bounds remain visible: opencode's skills are machine-global
and split from its profile home (§7.1); Muse skill discovery and refresh writes
are unverified (§§7.1, 7.4). This proposal does not turn either into a guarantee.

### Present consumers, fragments and transfer patterns

- `skill-project-management/tools/board-cli/internal/sessionmanager/codex_host.go:1572`
  (`preparePrivateCodexHome`) makes a private `codex-home`, writes a rendered
  `config.toml`, and links `auth.json` when available. It does not copy root
  context, skills or the Curator MCP layer. `codex_host.go:1619` explains the
  tool-policy document's precedence; `codex_host.go:1713` (`codexSourceHome`)
  selects `CODEX_HOME`, otherwise the native default.
- `skill-project-management/tools/board-cli/internal/sessionmanager/claude_host.go:2427`
  (`claudeHostEnvironment`) starts from the process environment, applies owner
  environment, removes nesting markers, and sets `TERM`. This function is not
  a managed-content snapshot mechanism.
- Owner decision 2026-10-15 (D5) describes an **interim plan**, not functionality
  demonstrated at the pinned commit: task-board copies between equal-digest
  resolves, compares bytes, and separately links native `auth.json`.
- `curator/internal/envfragment/envfragment.go:54` defines `Fragment` with
  Environment, Profile, LockSHA256, Permissions, Winner, Placement, Env,
  SystemPrompt and MCP. `managed.go:2413` builds it with managed-home paths.
  Environments §10.2 and `schemas/v1/launch-env-fragment-v1.schema.json`,
  `launch-env-fragment-v2.schema.json`, `launch-env-fragment-v3.schema.json`
  define closed, versioned objects. V2 carries permissions; v3 adds Muse's
  four XDG parents. These are absolute managed-home paths, not a portable
  snapshot descriptor. The code does not yet supply the explicit root-context
  member required by owner decision 2026-10-15 (D12).
- Swarma-dispatcher §5.2, “Cross-account workspace contract (R-TRANSFER)”,
  step 1 “Materialize”, already proposes bounded canonical archives, digest
  journaling and entry-by-entry correspondence with an admitted manifest.
  Task resources travel read-only with plan-covered digests. Its archive
  format, caps and exact plan fields remain unpublished.
- Curator-agent-launcher SPEC §§10.1–10.2 require immutable plan intake on FD3,
  digest verification before harness start, and an executor that never resolves
  profiles or reconstructs launch choices. Its plan encoding and descriptor
  transport still have publication gates; §10 is a target amendment.

### Credential evidence supplied by the owner

Owner decision 2026-10-15 (D7–D11) separates readiness and credential delivery
from content. Recorded measurements: Claude Code **2.1.299 on macOS 15** can
use per-home Keychain or `.credentials.json` depending on Keychain access;
`CLAUDE_CODE_OAUTH_TOKEN` writes no credential file and is inference-only.
Muse **1.4.8 on macOS 27**, with `TBH_CREDENTIAL_BACKEND=file`, uses
`$XDG_CONFIG_HOME/muse/auth.json`; token-refresh writes remain unmeasured.
The Codex fact in the decisions has **no recorded tool version**: native
`config.toml` selects `cli_auth_credentials_store`, absent means `file`.
These are supplied observations, not probes rerun for this document.
Moving a home changes neither credential authority nor backend guarantees.

## Design

### Options considered

Each question has independent options; security consequences are explicit.

| Question / option | Mechanism | Pros | Cons and security |
|---|---|---|---|
| Inventory A: recursive home copy | Traverse everything except an auth denylist | Simple consumer | Leaks unknown credential stores, state and foreign XDG seeds; denylist drifts; rejects D1/D5 |
| Inventory B: consumer-maintained list | Each session host selects files | Small initial patch | Duplicates adapter knowledge, omits future surfaces and risks credential inclusion; rejects D1 |
| Inventory C: Curator content closure | Curator selects verified content and expands only admitted store links | One owner; regular portable output | Requires a versioned inventory and reference relocation rules; selected |
| Consistency A: two resolves | Compare fragment and copied-byte identity before/after | No long-held read lock | Fragment equality alone misses ABA and per-file mixtures; interim D5 needs additional byte checks, not a permanent proof |
| Consistency B: manager lock plus verification | Hold the mutation lock across input selection and capture; revalidate before release | Serializes cooperating writers and binds one generation | Blocks mutation during bounded capture; arbitrary external writers still need integrity checks; selected |
| Consistency C: immutable home generations | Build and retain immutable complete home generations | Cheap readers and stable generations | Much larger home lifecycle migration; tool state still needs separation; reserve for later |
| Delivery A: remote resolve | Executor selects and repairs a profile | Small payload | Requires caller state/authority in another account, can select different bytes, violates D6 and executor boundary |
| Delivery B: archive resource | Caller archives content; plan pins exact archive and manifest; executor verifies | Reuses R-TRANSFER; no home paths in dispatcher | Needs canonical format, caps and protected intake; selected |
| Delivery C: shared live directory | Point account at the managed home | No transfer | Mutable content and cross-account access violate D4/D6; path access is not content attestation |
| Runtime A: fully read-only tool home | Set home variables directly to the sealed tree | Minimal composition; strongest immutability | Tool writes may fail; cannot assume first-run, login or resume works |
| Runtime B: sealed content plus private runtime view | Keep archive extraction read-only; expose verified content in a private home with separately admitted state/policy | Preserves snapshot identity and writable tool state | Needs adapter-qualified protection/projection and plan-covered overlay; selected, subject to qualification |
| Runtime C: unverified writable copy | Copy once and trust future runs | Easy tool writes | Drift can reach attach/resume undetected; unacceptable |

### Recommendation

Adopt inventory C, consistency B, delivery B and runtime B. These implement
owner decision 2026-10-15 (D1, D4–D6), while leaving session policy, credentials
and tool state with their existing owners. The following names and JSON
members for leaf 1 are **new contracts** in the separate snapshot namespace,
not extensions to released fragment schemas. Archive bytes/caps and runtime
projection remain later-leaf publication and activation gates.

#### 1. Command and destination boundary

```text
curator env materialize <env-id> [--profile <name>] --into <dir> [--format json]
curator env materialize <env-id> [--profile <name>] --manifest-only --format json
```

The profile selection rules match `env resolve`. `--manifest-only` and
`--into` are mutually exclusive; missing both is a usage error.
`--manifest-only` requires explicit `--format json`; bare use is `usage`
before selection, lock acquisition or writes. Manifest-only
runs the same selection, read and digest algorithm, including relocation,
but publishes no output directory. It is a planning observation, never proof
that an existing session tree matches the manifest. Neither form repairs,
provisions, logs in, updates a profile, or launches a tool.

`--into` may be relative to the caller's working directory; Curator records
only its validated absolute handle internally, never in the portable manifest.
The destination MUST be absent with an existing caller-owned private parent,
or an intact prior snapshot of this version accepted only as a verified no-op.
An existing empty directory MUST refuse without writes with
`environment_materialize_destination_invalid`.
Curator MUST reject non-directory targets, non-empty unrelated directories,
unknown snapshot versions, unreadable ownership evidence and modified prior
snapshots. An existing manifest is inventory evidence, not permission to
replace arbitrary paths. There is no takeover, recursive cleanup or force flag.

Destination traversal MUST use retained directory handles and no-follow
operations for **every** component, including the target and its ancestors.
The first release refuses linked ancestors rather than resolving them.
Directories writable by other principals or with uncertain ownership refuse;
Windows uses the equivalent owner/ACL and reparse-point checks.
The target MUST NOT equal, contain or lie within the Curator manager root,
profile stores, managed homes, native tool homes, credential roots, repository
administration, or the active workspace. For a directory inside a workspace,
a launcher must instead allocate a private session directory outside it.
Checks use handle identity and ancestry, not a lexical prefix alone.

All output directories are private `0700`; non-executable files and manifests
are `0600`; executable skill assets are `0700` only when their verified source
mode carries execute permission. No set-id bits, broad permissions, ownership,
ACLs, xattrs or source hard-link identity are imported. Equivalent private
ACLs apply on Windows. File bytes are regular independent copies, never
symlinks or hard links. A skill asset's executable mode is content metadata,
not permission to execute it outside the existing execution policy.

#### 2. Content closure and portable layout

Curator owns the inventory derived from the verified lock, adapter renderer
and marker; the marker alone cannot authorize an unknown class. Include:

- Root-context target and referenced-form supporting chapters, snippets and
  managed adapter configuration required to discover them.
- Complete admitted skill package payloads for the profile's effective skill
  set, including synchronized global skills when they participate in that
  home, with their verified file identities and executable modes.
- The applicable inert system-prompt file and declared MCP layer, with their
  fragment channel descriptors and environment variable names.
- Only generated non-secret adapter content needed to preserve these surfaces.
  Render from verified inputs; do not extract arbitrary members of tool state.

Exclude credentials, credential links and values; session transcripts, goals,
resume databases, locks, caches, histories, tool binaries and downloaded tool
state; backups and journals; `.agent-environment.json` and other marker
internals; all tool-owned provisioning seeds; foreign XDG seed links; and
unmanaged files. Never copy `auth.json`, `.credentials.json`, Keychain data,
OAuth metadata, native `config.toml`, `.claude.json`, or Muse trust/settings
state merely because they are present. Explicitly declared instruction or
skill content still passes existing secret detection and admission checks;
a secret-bearing selected asset refuses export, rather than being silently
redacted into a different profile.

The layout is `home/` plus `manifest.json` and `launch.json` at the snapshot
root. For opencode, `home/` is the XDG config parent and contains `opencode/`;
for Muse it contains the four XDG parents. Other adapters use `home/` directly.
No output path escapes this layout. Empty runtime directories need not carry
state; their required creation belongs to the admitted runtime setup.

Source links are not traversed recursively. For a marker-recorded managed
link, Curator verifies its exact admitted store identity and reads the
corresponding verified store object through protected handles. It rejects
unrecorded links, nested escaping links, reparse points and special files.
The exporter never dereferences credential or foreign-XDG links. “Never
follows links” applies unconditionally to destination writes; source store
indirection is resolved by identity, not by walking arbitrary link targets.

Any generated absolute reference to the live home/store MUST be rendered
again from the same verified inputs using snapshot-relative references.
Curator verifies semantic correspondence to the locked surfaces and hashes
the **output** bytes; the raw source hash is not reused for rewritten bytes.
Opaque skill assets are not text-substituted. If an adapter requires an
absolute include and cannot preserve semantics through a qualified relocation,
that adapter/form refuses materialization until the renderer supports it.
Never leave a path back into the managed home or invent include support.

#### 3. Manifest and digest semantics

Define the closed `managed-home-snapshot-v1` manifest, canonicalized with
registry CCJ-1 and exactly one trailing LF on disk. It contains:

| Member | Meaning |
|---|---|
| `snapshot` | Exact token `managed-home-snapshot-v1` |
| `adapter` | Closed environment ID; matches the launch descriptor |
| `profile` | Name and `lock_sha256`, without source paths |
| `curator_version` | Exact producing Curator release identifier |
| `fragment_sha256` | Host-bound SHA-256 of CCJ-1 source resolve fragment, excluding presentation LF; excluded from portable comparison |
| `launch_sha256` | SHA-256 of exact canonical `launch.json` bytes, including its LF |
| `files` | Sorted entries `{path, size, sha256, mode}` for every regular content file under `home/` |

Paths are non-empty portable UTF-8 relative paths using `/`, rooted at `home/`;
no absolute, drive, UNC, empty, dot or parent segments, NUL, duplicate entries,
case/normalization collisions, or file/ancestor conflicts are admitted.
Size is the exact non-negative byte count; hashes are 64 lowercase hex;
mode is the closed string `0600` or `0700`. Sort by UTF-8 path bytes.
Directories are derived from paths and the adapter layout, never arbitrary
entries; limits apply to their count and depth too.

`launch.json` is a **new portable descriptor**, not a modified v1/v2/v3 launch
fragment. It preserves environment, profile pin, precedence, permissions and
channel semantics, but represents all home-dependent paths as validated
snapshot-relative paths. It includes the optional Muse `root_context: {"exclusive": true}` fact
exactly when verified root context is selected, coordinated with CIP-0017
and owner decision 2026-10-15 (D12); consumers never infer it from layout. No source absolute home path,
credential value or machine-local PATH prefix is exported. `path_prepend` is not admitted in descriptor v1; a source requirement
needs a separately covered tool resource or refusal; binaries
are not smuggled into this content archive.

Define `manifest_sha256 = SHA256(exact manifest.json bytes including LF)`.
The manifest does not contain its own digest and does not list itself or
`launch.json` in `files`; `launch_sha256` covers the descriptor separately.
The archive contains exactly these two metadata files and the listed content,
with only derived directories. The fragment digest binds the host-specific
source decision, whose fragment contains absolute paths. Therefore the
manifest digest is also source-home-bound; neither is the archive digest.
Portable comparison excludes only `fragment_sha256`, compares descriptor
bytes/digest and the full file inventory plus every other manifest member,
and recomputes actual entry-set/bytes/sizes/modes. Exact plan integrity still
binds the whole source-bound manifest. A different Curator version or
descriptor changes identity even if content bytes match. No timestamps,
destination paths, OS identities or random generation IDs enter portable identity.

With `--format json`, stdout is exactly one manifest document after success;
normal mode reports its digest and destination without printing content.
Both forms emit no success manifest on failure; diagnostics go to stderr.
Manifest-only and export from the same unchanged source fragment and verified
inputs yield identical bytes. Cross-home equality is portable comparison,
not equality of manifest digests.

#### 4. Consistency, publication and repeat calls

1. Validate the destination without writes. Acquire the same manager-home
   mutation lock used by repair and switching, with the existing bounded wait.
   Use a non-recovering lock path: existing `beginOperation` also recovers
   incomplete journals and cannot be reused as-is.
   Resolve profile selection and machine configuration under it, not from a
   prior unlocked lookup. Do not call a locking repair operation recursively.
2. Detect pending transaction recovery and refuse until an explicit recovery
   or repair succeeds; materialize must not silently mutate source state.
   Verify profile, lock, store, marker, surface currency and credential
   metadata through the existing read-only checks.
3. Freeze the selected content closure and fragment. Read admitted regular
   objects with no-follow handles; verify sizes, hashes and modes against
   their expected identities. Capture the output into private staging.
4. Revalidate lock, current selection, effective machine policy, marker,
   surfaces and every captured object's identity before releasing the lock.
   A mismatch or failed read aborts the invocation. External mutation is not
   serialized by the manager lock and must still fail these checks.
5. Publish the captured generation only after all checks succeed. Do not
   perform transport or wait on an external service while holding the lock.

Use existing environments diagnostics where the underlying condition matches:
`environment_home_stale` for stale or unprovisioned homes,
`environment_lock_unavailable` for contention, and existing marker, store,
path, credential-metadata and read-failure diagnostics for those failures.
The remedy for stale/unprovisioned homes is explicit `env resolve --repair`
or the preparation flow, followed by another materialize. Do not weaken
§8.4.1 by treating unreadable state as absent or falling back to native files.
The new destination, recovery, capture-drift, relocation, mismatch and
unsupported-adapter codes are frozen in [snapshot §5](../protocol/managed-home-snapshots.md#5-consistent-capture-and-refusals).
They are new normative names, not claims of existing implementation support.

For absent targets, stage beside the target and publish by no-replace rename.
For a prior snapshot, first verify its entire inventory, metadata, actual
file bytes, sizes, modes, complete entry set and absence of extras. An identical
manifest is a no-op only after this verification. A different generation MUST
refuse with `environment_materialize_snapshot_mismatch` and require a fresh
absent destination. An existing empty target refuses because no portable
operation replaces it conditionally on its retained identity under same-user
substitution; see [snapshot §2](../protocol/managed-home-snapshots.md#2-destination-and-publication).
Thus re-materialization is idempotent without mutating an active snapshot.
Failure preserves the target, including any competing replacement, and emits no success;
cleanup removes only this invocation's privately created staging entries.

#### 5. Adapter consumption and session overlays

The consumer uses Curator's portable descriptor, never another file inventory.
The launcher binds descriptor-relative paths to the admitted private runtime
root at **plan composition**, then covers exact argv, env, content identity,
and overlay bytes with the plan. The executor only verifies and applies them.

| Adapter | Private runtime home and required consumer work |
|---|---|
| Codex | Set `CODEX_HOME` to the private home view. The session owner supplies its tool-policy `config.toml`, project trust and resume state; none comes from the snapshot. Keep `curator-mcp.config.toml` unchanged and apply exactly one `-p curator-mcp` when declared. Verify its bytes immediately before launch, because a missing layer is silently ignored. |
| Claude | Set `CLAUDE_CONFIG_DIR` to the private view. Supply fresh onboarding/trust state separately; apply the descriptor's system channel and `--mcp-config` plus `--strict-mcp-config` when declared. Credentials use the admitted backend/channel, never the content archive. |
| Muse | Set all four XDG parents to the private view's `config`, `data`, `state`, `cache`; preserve `HOME`. Consume the explicit root-context descriptor; keep form-specific foreign-context exclusion. Use `TBH_CREDENTIAL_BACKEND=file` where selected under D9/D10; authentication is separate. Do not claim verified skill discovery or refresh writes. |
| opencode | Set `XDG_CONFIG_HOME` to the private parent view and apply `OPENCODE_CONFIG` from the descriptor. Do not copy foreign XDG seed links. Keep the documented project-MCP override residual. Global skills prevent a self-contained snapshot: materialize refuses this adapter until a profile-local skills target is specified and qualified; ambient data/state also require runtime qualification. |
| pi | Set `PI_CODING_AGENT_DIR` to the private view. Supply supported non-secret settings/models configuration separately, credentials separately, and apply the system-prompt file channel. No MCP channel may be synthesized. |

For Codex, the host owns its **session policy document**, not the native or
managed tool-owned config. Profile settings reach the tool through inherited
launch `-c key=value` settings under owner decision 2026-10-15 (D13).
The host MUST NOT import ambient `mcp_servers` into its base configuration;
otherwise `-p` merges unmanaged servers rather than replacing them. If host
tool isolation requires a gateway that conflicts with the profile MCP set,
plan composition must explicitly reject that combination or use an already
specified policy intersection; do not silently add, drop or rename servers.
Conflicting duplicate `-p`, weakened policy and overlay collisions refuse.
The exact resulting config bytes and settings overrides are plan-covered.

Local authentication may still use a separately admitted native credential
link where the backend permits it; that link is not materialize output and
never appears in the swarm archive. D9's Codex file-store override and Muse
backend selection are launch policy, not modifications to snapshot content.
Readiness metadata is not credential possession.

Runtime B is an interpretation of D6 awaiting operator confirmation.
A sealed extraction is not assumed to be a writable tool home. The runtime
view retains the sealed content as read-only backing while providing distinct
writable state/configuration slots. An adapter-qualified mount/projection or
protected installation must prevent replacement of content through writable
ancestors; chmod alone in an agent-owned tree is not a hostile-agent boundary.
Home variables point at this snapshot-backed private view, never the managed
home. Policy overlays cannot shadow content entries. Where a tool attempts
to rewrite protected content, refuse that adapter/runtime combination rather
than silently converting protected files to mutable state. Qualify start,
login, model turn and native resume before enabling each backend.

#### 6. Swarm delivery and verification (D6)

The caller materializes in its own private directory, validates the manifest,
and produces one canonical bounded archive. Propose an uncompressed tar
subset: regular files and derived directories only, UTF-8 sorted paths,
fixed metadata (zero timestamps and numeric owner/group, empty owner names),
private modes, no PAX/GNU extensions, links, sparse files, devices, trailing
payload or alternate path spellings. The implementation leaf must freeze
exact tar header/padding/end-block bytes and reference vectors before
interoperability is claimed. No generic permissive archive extractor is used.

The composed plan MUST cover archive SHA-256 and exact size, manifest SHA-256,
portable descriptor digest, adapter, profile lock digest, runtime projection,
overlay digests and resource bounds. These are required semantics; their wire
member names and required-understanding encoding await joint publication.
The archive is out of band like task resources, not embedded in the 48 KiB
FD3 plan. Proposed initial caps: 64 MiB archive, 64 MiB aggregate content,
16 MiB per file, 10,000 entries, depth 32 and 240 UTF-8 bytes per relative path.
All participating services enforce the smallest applicable published cap;
no truncation or implicit splitting is permitted.

The dispatcher authenticates and admits the plan through its existing
boundaries, journals archive/manifest digests and relays opaque bytes.
It does not resolve profiles, search Curator homes, rewrite the archive,
compose policy or handle credential bytes. A self-minted manifest digest is
integrity metadata, not caller authorization. The protected expected plan
digest and admission evidence must arrive through the launcher contract.

`curator-run exec` MUST, before any child code:

1. Verify the immutable FD3 plan and protected expected digest under SPEC §10.
   Require support for the snapshot contract; unknown versions or missing
   bindings refuse, with no live-home or remote-resolve fallback.
2. Verify resource length and archive digest, then parse the bounded canonical
   subset into a fresh private staging directory through retained handles.
   Reject absolute/traversal paths, aliases, links, duplicate names, special
   files, unexpected entries, excess size/depth and incomplete reads.
3. Verify exact manifest bytes/digest and descriptor digest against the plan;
   validate the closed schemas and compare the **entire** entry set, file
   bytes, sizes and semantic modes against the manifest. Reject missing or
   extra files and inconsistent adapter/profile/lock bindings.
4. Install a sealed read-only extraction in the agent account (files `0400`,
   executable assets `0500`, directories `0500`, or equivalent protected ACLs).
   These are installation permissions; manifest modes describe portable
   content, so protection does not change its semantic identity.
5. Apply only the already composed and covered runtime view and overlays;
   verify their bytes and protections, bind exact plan env/argv, and deliver
   credentials through the separate admitted credential channel. Start only
   after every check succeeds. On restart or native resume repeat integrity
   and authority checks; failed reads never count as absent resources.

Cleanup is scoped to the allocation/generation and retained transfer rules.
A retry reuses identical verified bytes or explicitly admits a new plan;
archive loss/corruption cannot trigger re-resolution. The executor never
needs the caller's managed-home path. Trusted-class and placement restrictions
remain unchanged; a snapshot does not admit an agent loop in a workplace.

## Security considerations

Threats include repository-driven path traversal, hostile archives, accidental
credential export, concurrent home repair, policy-shadowing overlays, mutable
resume content and self-supplied digest “evidence”. Selection uses Curator's
verified content closure; writing and unpacking use retained no-follow
handles; plan admission supplies authority independently of archive integrity.
A secret detector is defense in depth, not a substitute for the closed content
inventory and separate credential channel. Error output must not dump files,
credential values or native-source metadata.

The manager lock serializes cooperating Curator mutations, not arbitrary
processes or a compromised caller. Verification proves captured bytes match
one admitted identity, not that prompts are harmless. Skills retain their
existing audit and execution boundaries. Read-only extraction means an
enforced protection boundary on the swarm host; owner-writable chmod bits
alone do not qualify it. A writable runtime view requires protected content
projections and covered overlays, with no ancestor-replacement bypass.

Snapshot manifests disclose profile names, content paths and hashes; keep
local exports private and transport them only to admitted principals.
Do not include source paths, credential inventory, login identities or host
metadata. Existing log retention and allocation cleanup apply to resources.

## Compatibility and migration

The command is additive; v1/v2/v3 fragment schemas remain byte-compatible and
closed. Portable descriptors get a separate schema, not extra members hidden
in an old fragment version. D12's fragment amendment must land in coordination
with its owning proposal; consumers cannot infer root context from the layout.
The new launcher path requires explicit capability support. Lack of support
refuses managed snapshot launches after cutover; it never means live-home use.

1. Ship Curator manifest-only, export, verification and conformance together.
   Keep existing preparation/repair explicit. Qualify Claude, Codex and Muse
   hosted starts together under owner decision 2026-10-15 (D2).
2. In skill-project-management, replace the interim copy from
   TASK-261014-3ntl3f — interim session content copy — with materialize.
   Remove its adapter lists, two-resolve copy and byte-copy fallback after
   the minimum supported Curator version is enforced. Keep private policy,
   trust, resume stores and separately authorized local credential linkage.
3. For TASK-261014-28uxsf — attach/resume content identity — persist the
   manifest digest, descriptor digest and covered overlay identity in session
   metadata. Before attach and native resume, recompute from the session's
   actual content and compare with that original identity. Validate complete
   inventory, not just the stored digest string. Failure, extras or missing
   evidence refuse; never update the baseline to the observed bytes.
4. A changed profile or Curator release creates a new snapshot/session
   generation through explicit preparation, not an in-place resume upgrade.
   An existing session keeps its admitted content even after global sync.
   Legacy sessions without identity need explicit migration into a fresh
   session; do not invent identity from an unchanged profile lock alone.
5. Publish and qualify launcher/dispatcher archive intake together before
   swarm activation. Opencode's global-skills bound remains unsupported for
   cross-account parity until a separate adapter change removes it; pi needs
   its own runtime qualification. No unsupported adapter is advertised as
   covered by Claude/Codex/Muse success.

## Specification changes

Leaf 1 is frozen by the Normative text pointers above. The launcher and
dispatcher quotations below remain **target sketches** for later leaves;
acceptance does not publish their wire contracts or qualify runtime B.

- **Environments §§5, 8, 10:** “A session MUST NOT point at a live managed
  home. `env materialize` MUST capture the verified content closure under
  the manager-home mutation lock, publish independent regular files and the
  versioned manifest, and MUST NOT include credentials or mutable tool state.
  Stale or unreadable source state MUST refuse without implicit repair.”
- **Environments §7:** Add the per-adapter export inventory, runtime-home
  consumption and relocation qualification tables; preserve documented
  discovery and MCP precedence residuals. Section 8.3.1 remains the managed
  write contract; export has the stronger destination no-link boundary.
- **Launcher SPEC §10.1:** “The immutable plan MUST bind snapshot archive
  digest/size, manifest and descriptor digests, adapter/profile pin and exact
  runtime overlay identity. The resource bytes MUST NOT be interpreted as
  authorization or be substituted by an executor-side resolve.” Publish a
  versioned required-understanding contract alongside the plan encoding.
- **Launcher SPEC §10.2:** “The caller materializes and archives the snapshot.
  `curator-run exec` MUST verify the archive and every manifest entry before
  installing read-only content and applying the covered runtime view. The
  executor MUST NOT repair homes, select profiles, import native tool state
  or read caller Curator paths. Credentials MUST use their separate intake.”
- **Dispatcher R-TRANSFER Materialize:** “Alongside the repository archive and
  task resources, relay the admitted managed-content snapshot as a distinct
  bounded resource. Journal its digest; preserve bytes. Require plan coverage
  and successful executor verification before work. No Curator-home location
  is a dispatcher input. Snapshot and workspace manifests are distinct and
  neither can stand in for the other.”
- **Schemas/conformance:** Add closed snapshot/portable-descriptor schemas,
  canonical archive vectors, destination/refusal vectors and cross-service
  consumption tests. Publish new diagnostic names and caps with these
  contracts; existing unknown-field/version refusals remain fail-closed.
- **Decision record:** Adopt owner decision 2026-10-15 (D4–D6), record the
  chosen lock/inventory/runtime boundaries, and amend the old “managed home
  for concurrent sessions” guidance in environments §§8.1 and 9.2.

## Implementation plan

Ordered leaves; sizes are relative Fibonacci estimates, not elapsed time.
Leaf 1 is specified by the linked normative text; later leaves remain work.
No production implementation is claimed.

| Order | Repository / size | Deliverable and dependency |
|---|---|---|
| 1 | curator-spec / 3 | Freeze content closure, manifest/descriptor schemas, relocation, destination rules, diagnostic names and byte vectors; coordinate D12 descriptor/fragment work |
| 2 | curator / 5 | Production `env materialize`, non-recovering manager-lock acquisition (not `beginOperation` as-is), capture without implicit recovery/repair, no-follow publication, manifest-only parity and verifier; depends on 1 |
| 3 | curator-agent-launcher + skill-agents-management / 5 | Compose snapshot-backed runtime homes, exact overlay identity and launch settings; qualify Claude/Codex/Muse without live-home access; depends on 1–2 |
| 4 | skill-project-management / 3 | Replace L2 interim copy; implement L3 attach/resume comparison and legacy refusal through the real hosted entry points; depends on 2–3 |
| 5 | curator-spec + curator-agent-launcher + swarma-dispatcher / 5 | Jointly publish canonical archive bytes/caps, protected plan/resource intake and exact refusal mappings; amend SPEC §10 and R-TRANSFER; depends on 1 |
| 6 | curator + swarma-dispatcher + curator-agent-launcher / 5 | Caller archive, dispatcher relay/journal, executor verified read-only install and protected runtime projection; end-to-end qualification; depends on 2–3, 5 |
| 7 | skill-project-management + skill-agents-management / 2 | Remove compatibility fallback, enforce minimum capabilities, publish operator migration and observed adapter/platform limits; depends on 4, 6 |

## Test plan

These are required **future implementation tests**, not executed evidence for
this docs-only proposal. Drive the production entry points named below;
helper tests alone cannot qualify materialization or launch.

| Named test / production entry | Positive and negative property |
|---|---|
| `MaterializeCLI_ContentClosure` / `curator env materialize` | Root, referenced supports, skill assets, system and MCP content are exact; native seeds, hidden credentials, state and marker internals never appear |
| `MaterializeCLI_DestinationBoundary` / same | Absent destination under an existing caller-owned private parent succeeds; existing empty directory refuses without writes with `environment_materialize_destination_invalid`; nonempty foreign, protected ancestry, foreign ownership, linked ancestor/target, reparse point and concurrent replacement refuse without writes outside own staging or alteration of the target |
| `MaterializeCLI_NoTornGeneration` / same | Race repair, profile use and global sync against multi-file capture; result is one verified generation or refusal; inject same-fragment ABA and external store-byte mutation |
| `MaterializeCLI_SourceRefusals` / same | Stale/unprovisioned, lock timeout, unreadable marker/store/passthrough, unknown surface and pending recovery refuse; no repair, native fallback or credential reads |
| `MaterializeCLI_PortableIdentity` / both forms | Manifest-only equals exported bytes; relocation survives source-home removal; sizes, modes and complete entry set match; different version/descriptor changes digest |
| `MaterializeCLI_Idempotence` / same | Intact prior snapshot of this version with identical manifest is unchanged only after full verification; changed content, forged manifest, extra file or new source generation refuses with `environment_materialize_snapshot_mismatch` and preserves the target; a different generation requires a fresh absent destination |
| `HostedStart_SnapshotAndPolicy` / `curator-run --hosted` | Claude/Codex/Muse use private content, exact policy overlay and separate credentials; Codex MCP cannot disappear or merge ambient servers; missing layer and duplicate `-p` refuse |
| `HostedAttachResume_ContentDrift` / task-board attach/native resume | Exact content resumes after managed-home mutation; altered file, overlay, descriptor, extra entry, missing baseline and failed read refuse without updating baseline |
| `ExecFD3_SnapshotArchive` / `curator-run exec` | Valid admitted archive starts; wrong expected digest, self-minted plan, unknown contract, missing/extra entries, links, traversal, tar aliases, truncation and size/depth excess refuse before child code |
| `DispatcherMaterialize_SnapshotRelay` / prepare/start | Digest journal matches relayed bytes; replay/retry preserves identity; archive swap, missing resource, unauthorized caller and mismatched profile/adapter fail; dispatcher never accesses a home |
| `ExecRuntime_ProtectedContent` / actual executor start/resume | Tool state writes succeed outside content; replacing through writable ancestors, overlay shadowing or chmod cannot mutate sealed content; failed protection prevents start |

Run Curator entry-point tests on macOS, Linux and Windows for the supported
no-follow/ACL paths; no mobile build is relevant to this CLI/spec change.
Qualify swarm FD3/read-only/runtime-view behavior on each platform admitted
by the platform contract. For Claude Code 2.1.299 and Muse 1.4.8, preserve the
recorded credential backend bounds; record actual versions for every new
probe. Opencode discovery and Muse refresh uncertainty require named probes,
not inference from another adapter. Retain all committed reviewer tests under
their original names; pin source, tests, configuration and environment when
reusing green evidence.

Narrowing mutants worth killing are specified in advance:

| Mutant | Gate narrowed to | Named test expected to fail | Bound if it survives |
|---|---|---|---|
| M1 | Exclude only top-level `auth.json`, admit nested credentials | `MaterializeCLI_ContentClosure` | Nested credential exclusion is unproven |
| M2 | Check only final destination, allow linked ancestors | `MaterializeCLI_DestinationBoundary` | Ancestor traversal is unproven |
| M3 | Compare only fragment/lock digest across capture | `MaterializeCLI_NoTornGeneration` | Same-fragment torn/ABA capture is unproven |
| M4 | Treat read errors as missing optional state | `MaterializeCLI_SourceRefusals` | Absence/read-failure separation is unproven |
| M5 | Hash file bytes but ignore execute mode and extra entries | `MaterializeCLI_PortableIdentity` | Inventory/mode identity is unproven |
| M6 | Trust prior manifest without rereading target | `MaterializeCLI_Idempotence` | Existing-target verification is unproven |
| M7 | Verify only root context at attach/resume | `HostedAttachResume_ContentDrift` | Skills, MCP and overlay drift are unproven |
| M8 | Verify archive digest but skip manifest correspondence | `ExecFD3_SnapshotArchive` | Entry-set and profile binding are unproven |
| M9 | Import only ambient base MCP entries into Codex | `HostedStart_SnapshotAndPolicy` | Profile-only MCP closure is unproven |
| M10 | Enforce read-only files but allow ancestor replacement | `ExecRuntime_ProtectedContent` | Runtime content immutability is unproven |
| M11 | Journal the declared digest without checking relayed bytes | `DispatcherMaterialize_SnapshotRelay` | Relay-to-plan correspondence is unproven |

No mutant in this future implementation table has been run or killed by
leaf 1. Its metadata-checker controls are separate. Implementation handoffs must
report actual failing test names and survivors, not promote this table to
coverage evidence. Test coverage must distinguish a missing resource from a
failed read and a valid digest from admitted authority.

## Open questions for the operator

1. **Archive encoding and caps:** adopt the restricted uncompressed tar and
   proposed caps above, or choose a purpose-built framed file stream?
   Recommend tar with frozen byte vectors and strict parser; the stream
   reduces legacy parser surface but adds another transport implementation.
   Both require joint launcher/dispatcher publication before activation.
2. **Runtime protection:** approve a qualified read-only projection with
   separate writable state, or restrict initial activation to adapters proven
   to run against a wholly sealed home? Recommend the protected runtime view;
   it interprets D6 and awaits operator confirmation, without assuming tools
   never write their home. Exact
   per-platform mechanism and backend qualification remain activation gates.
3. **Opencode scope:** keep cross-account snapshot parity unsupported until
   skills have a profile-local target, or explicitly admit ambient skills?
   Recommend unsupported parity; ambient skills cannot reproduce the caller's
   admitted closure. Do not silently export a partial snapshot as a successful materialization.
4. **Resolved in leaf 1 — failure names:** the new materialize family in
   snapshot §5 covers new failure classes; exact existing source diagnostics
   retain their meanings. These names are normative, not shipped-code claims.
