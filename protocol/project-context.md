# Project context, leaf 1

This normative amendment adopts the leaf-1 subset of
[CIP-0002](../cips/CIP-0002-project-context-in-managed-launches.md#leaf-1-candidate-grammar)
under [Decision 0028](../decisions/0028-project-context-and-werkstatt-leases.md)
and the operator's 2026-10-22 additive-context ruling. It extends
[environments](environments.md) and the [manager profile](../profiles/manager.md).
Publication specifies a contract, not implementation or native qualification.

## 1. Capability and authority

Project context is an optional, separately versioned capability per environment.
Adopting it MUST NOT reinterpret the existing environments capability or turn
an unenrolled launch into a strict launch. Existing unenrolled launches remain
explicitly reported legacy compatibility, with their native discovery limits.
New registrations MUST default to `mode: "strict"` and `admission: "off"`.
Source mode is exactly `strict` or `native-project`; admission is independently
`off` or `admitted`. Off admission MUST deliver no project items; admitted MUST
deliver only the selected approved generation within its mode's limits. Strict
MUST suppress unadmitted project-native discovery even with off admission.
Native-project MUST require explicit protected operator enablement per
Werkstatt and retains native discovery even with off admission (§5). Fleet
policy MAY refuse legacy or native-project launches. An unsupported strict
request MUST refuse, never downgrade to legacy or native-project.

Repository files MUST be treated as candidate data, never manager authority.
Discovery and preview MUST NOT execute parser hooks, source shell files, fetch
referenced URLs, install packages or contact MCP servers. Admission MUST use
protected immutable snapshots and an itemized semantic diff covering content,
transitive references, command owners, MCP transport/endpoints and permissions.
The manager MUST bind attributed approval to the exact checkout, item digest,
environment and effective ceiling, and MUST check current revocation and grants
at preparation, start and command dispatch. Agent approval MUST require a live
manager-issued grant for that act; human approval MUST NOT exceed hard denies.
Category enablement, native trust, identical hashes or repository-shipped
approval files MUST NOT substitute for this approval.

Manager policy and protected grants MUST program harness permissions with
default deny. Project allow/deny settings MUST NOT apply, even as restrictions;
they MAY be displayed as inert requests for a separate grant. Every first-slice
composition MUST carry `memory: "off"`; repository knowledge approval MUST NOT
opt into native memory. Credentials MUST NOT enter project records, snapshots,
receipts, leases or diagnostics. Claude setup-token delivery MUST use its
separately admitted [credential contract](local-setup-token-source.md), never
copied native login state or a fallback credential source.

## 2. Closed records and identities

Readers MUST reject duplicate or unknown members, invalid UTF-8, trailing input,
unsupported versions, nulls and out-of-bound values before authority lookup.
All members listed below are REQUIRED unless explicitly optional. ID is
`[a-z][a-z0-9_-]{0,63}`. HEX is exactly 64 lowercase hexadecimal characters.
REF is `TAG:ID`, at most 96 ASCII bytes; TAG is one of `registration`, `snapshot`,
`approval`, `composition`, `lease`, `home`, `worktree`, `policy`, `adapter`,
`session`, `principal`, `grant`, `tool`, `dispatcher`, `command` or `lock`.
References MUST have the field's tag and resolve only in protected state of the
issuing manager to an immutable allocation; they MUST NOT act as paths, URLs or
bearer credentials. Equal text issued by another manager grants no authority.

Record identity is SHA-256 of CCJ-1 bytes with no trailing LF, excluding no
member; a record MUST NOT contain its own digest. Arrays preserve order unless
specified as sets; sets MUST be unique and sorted by UTF-8 bytes. Each record
MUST be at most 1 MiB and depth 16, each generation at most 256 items, ordinary
strings at most 256 bytes unless an owning schema states another bound.
Absolute root paths MUST be at most 4096 UTF-8 bytes and validated using retained
filesystem identity, not lexical prefixes. ENV is exactly `claude_code`,
`codex_cli` or `muse`; profile names use the existing profile grammar.

| Record | Closed members |
|---|---|
| Registration | `kind: "project-registration/1"`, `checkout_id: ID`, `project_root: absolute path`, `root_identity: HEX`, `profile: {name, lock_sha256}`, `environment: ENV`, `mode: "strict" \| "native-project"`, `home_ref`, `worktree_ref`. |
| Item | `kind: "project-item/1"`, `id: ID`, `type: "context" \| "skill" \| "mcp"`, `environment: ENV`, `required: boolean`, `payload`. Context payload is exactly `{snapshot_ref, snapshot_sha256, lock_ref, lock_sha256}`; skill payload exactly `{snapshot_ref, snapshot_sha256}`; MCP payload exactly `{name, server, server_sha256}` (§4). |
| Approval | `kind: "project-approval/1"`, `checkout_id`, `item_id`, `item_sha256`, `environment`, `approver_ref`, `ceiling_sha256`, optional `grant_ref`. Approver references have tag `principal`. |
| Generation | `kind: "project-generation/1"`, `registration_ref`, `registration_sha256`, `items: [{item_id, item_sha256, approval_ref}]`. Item IDs are unique and the list is the approved rendering order. |
| Composition | `kind: "project-composition/1"`, `registration_ref`, `registration_sha256`, `generation_sha256`, `profile: {name, lock_sha256}`, `environment`, `mode: "strict" \| "native-project"`, `adapter_ref`, `adapter_sha256`, `policy_ref`, `policy_sha256`, `memory: "off"`, `home_ref`, `worktree_ref`, `materialization_sha256`, `command_owners: [{name, item_id, artifact_sha256}]`, `omitted: [{item_id, reason}]`. |
| Lease binding | `kind: "project-lease/1"`, `lease_id`, `context_ref`, `context_sha256`, `checkout_id`, `environment`, `home_ref`, `owner_ref`, `session_ref`, `generation`. Generation is a positive integer at most 2^53-1; owner has tag `principal`, context has tag `composition`. State/liveness are stored separately from these immutable bytes. |

All digest fields except `server_sha256` are HEX; `server_sha256` has the
`sha256:` prefix (§4). IDs, tagged references and closed nested objects MUST
retain the common types; no raw native-settings, permissions, hooks, plugins
or shell payload arm is admitted. The composition's policy reference MUST name
protected manager-programmed policy, never repository permission bytes.
Command owner names MUST follow the existing command grammar, be unique, bind
full audited artifact identity and select an effective skill from the approved
generation or selected profile lock; at most one command is enabled in leaf 1.
Omission reason is exactly `disabled` or `unsupported`; an omitted item MUST
have approved optionality and effective preview. A required item MUST NOT be
omitted. Protected generation bytes MUST be retained under their digest.

The registration's `root_identity` hashes exactly `{repository, filesystem}`.
`repository` is the closed [workspace-trust repository object](environments.md#7102-repository-identity-and-lapse)
with `root`, `primary_remote`, `root_commit`, including its null-remote case.
`filesystem` is exactly `{device, inode}`, each a canonical unsigned decimal
string, no leading zeros except `0`, at most 20 digits and at most 2^64-1.
The manager MUST prove the launch CWD belongs to that registered root and that
both repository and native identities still match. Nested registrations MUST
select the most specific registered containing root; ambiguous, replaced,
unreadable or moved roots MUST NOT inherit authority through a reused path.
Repair/rebinding MUST be explicit. This macOS/Linux binding defines no Windows
identity grammar.

## 3. Snapshot, context selection and rendering

A context/skill snapshot manifest is exactly
`{version: 1, files: [{path, size, sha256, mode}]}`. Paths MUST be unique, sorted
portable relative paths, with no absolute/dot/parent/empty components, links,
case/normalization aliases or file/ancestor collisions. Modes are exactly
`0600` or `0700`; size is the exact nonnegative byte count. Caps are 10,000 files,
depth 32, 240 UTF-8 bytes per path, 16 MiB per file and 64 MiB total.
The manifest digest covers its CCJ-1 bytes. Consumers MUST verify the complete
entry set, actual bytes, sizes and modes, not only the asserted manifest hash.
References/imports MUST close over this inventory. A skill snapshot MUST also
pass the existing whole-package manifest, pin, audit and activation contracts;
an arbitrary executable directory MUST NOT be admitted as a skill.

A context item MUST select one context-package root containing schema-2
`agent-context.json` under [environments §2](environments.md#2-context-package-shape).
Only explicit `context.modules` selects package-local regular files below
`context/`; leaf 1 MUST require `context` at the selected root. An umbrella with
no local modules MUST declare `context: {modules: []}` explicitly. A bare
instruction file without that manifest MUST refuse; the manager MUST NOT
synthesize entry selection. Non-selected files remain inert inventory/audit
content. Duplicate paths, including different root/system roles for the same
file, and duplicate JSON keys such as `class` MUST refuse.

Context validation, module selectors/classes, manifest module order, effective
weights, topological ties, system-module admission, bytes and rendering MUST
follow [environments §§3–6](environments.md#3-context-modules). Markdown modules
MUST be opaque UTF-8 with LF endings and exactly one trailing LF; the manager
MUST NOT normalize, template or include them. Every selected file MUST remain
inside the complete verified snapshot without symlink traversal or aliases.

`lock_ref` MUST resolve to the retained schema-4 context lock with its complete
closure, selected directory, exact pins, versions, effective weights, requirers
and overlay records. The root pin MUST match the selected snapshot bytes;
recorded precedence MUST equal the selected profile's protected precedence.
Each member MUST resolve to its verified protected store snapshot under
environments §4. Content pins MUST use their owning hash framing; the snapshot
inventory digest MUST NOT substitute for a content pin. `lock_sha256` is the
unprefixed SHA-256 of CCJ-1(lock) without LF. The manager MUST retain the manifest,
lock and complete closure before approval, and MUST NOT re-resolve during
preparation. Missing, stale, unknown or inconsistent evidence MUST refuse.

The item's closure MUST contain context members only. Non-empty `requires.skills`,
`requires.mcp` or `codex_settings` in any member MUST refuse; the inherited lock
MUST carry empty `codex_settings` and `codex_settings_contributions`. Context
requirements, weights and their owning conflict checks remain supported.
At least one applicable root module MUST exist in the pinned closure for the
item's environment. An explicit empty-module umbrella MAY select it through
requirements; discovery or a root without `context` MUST NOT supply that surface.

In strict mode, each context item MUST render its pinned closure in `monolithic` form with
environments §5's exact header/chapter/module/LF rules and selected environment.
The approved generation list MUST order project-general before environment-specific
context and deeper approved scope after shallower scope within those groups.
In the managed home's composed `AGENTS.md` / `CLAUDE.md`, the profile root-context
document MUST remain first; each approved project root-context document MUST
follow in item order, separated by exactly one additional LF between non-empty
documents. Applicable root modules within each package retain manifest order;
package weights and topological ties retain inherited emitted order.
Profile system context MUST remain present; admitted project system parts MUST
append in the same item order through environments §§5.5/7.3's separate channel
and owning part-joining rule, never promoted into root context. A project MUST
NOT replace profile root or system context, now or in any later slice; the
separate replacement item is withdrawn, not deferred. An adapter unable to
reproduce these additive strict-mode outputs MUST refuse, never choose a
different entry. Native-project MUST NOT admit a context item in its selected
generation or append project root/system documents. Its managed instruction
document MUST be exactly the selected profile root document; the profile system
channel is retained. Whole-skill content retains its owning skill channel.

In strict mode, a native control-file import the qualified adapter would follow MUST refuse,
even when its target is inventoried; leaf 1 admits no native import dialect.
Ordinary prose references remain opaque data. Changing the manifest selection,
order, class, selectors, weights, closure or supporting bytes MUST change the
snapshot and/or lock digest, hence item identity and required approval.
An output hash MUST NOT retroactively approve an entry choice. Selection changed
under the old approval is unapproved; changed/missing protected bytes under an
approved digest are drift, as distinguished in the diagnostic registry.

The composition's `materialization_sha256` covers exactly
`{version: 1, files, adapter_sha256, policy_sha256, worktree_ref}` with the same
complete sorted file-entry grammar. It inventories generated agent-visible
control outputs relative to the Werkstatt home only. Native mutable state,
credentials and the source worktree MUST NOT enter that receipt. Before start,
the consumer MUST verify outputs and the mode-specific qualified adapter
contract against the receipt; it MUST NOT bless changed files by replacing the baseline.
The receipt contains metadata, never credential bytes.

## 4. Individually approved skills and inline MCP

Composition MUST use the selected profile's lock, never machine-current state.
Identical skill pins MUST deduplicate. A same-identity project skill overlay
MUST substitute the whole skill, including its context, commands and providers;
all requirements MUST be rechecked against it. Incompatible required providers,
multiple skill identities exporting one command and unapproved MCP conflicts
MUST refuse. A derived composition MUST NOT mutate or replace the profile lock.
Whole-skill context does not authorize overriding the profile's root/system
context (§3). Hybrid inputs MUST first become explicit admitted project members.
Identical MCP stable ID and normalized server digest MUST deduplicate; a
differing same-ID server MUST require explicit approval or refuse.

Inline MCP NAME/SERVER MUST follow
[CIP-0022's approved companion grammar](../cips/CIP-0022-mcp-server-declarations-in-project-skillfile.md#schema-and-scope)
and environments §2.2; activation MUST additionally wait for that grammar's
normative publication and reader support. SERVER is closed: `transport`, either
`command`/`args` for `stdio` or `url` for `http`, optional `env_names` and
`environments`, retaining all owning bounds and secret-name rules. Expand URL
shorthand; default absent `env_names` to `[]`; sort unique names and explicit
environments; preserve argument order and scalar bytes; leave absent
`environments` absent. `server_sha256` is `sha256:` plus SHA-256(CCJ-1(normalized
SERVER)) with no LF. Approval MUST bind checkout, NAME and that digest; item
approval MUST also bind environment, required flag and effective policy.
Endpoint, argument, environment-name or selector changes MUST require new
approval. Moving/renaming MUST NOT replay approval, and raw manifest identity
MUST remain distinct from normalized declaration identity. Writer-local
`install` options MUST NOT gain control authority; an effective configuration
option without a separately specified approved contract MUST refuse.

## 5. Werkstatt materialization and native exclusion

The native home is stable per checkout × profile × environment at
`environments/project-views/<checkout-id>/<profile>/<env>/`; adapter-owned
native layouts remain intact. The home and sparse Werkstatt worktree MUST be
protected manager allocations outside the source tree; the worktree MUST also
be outside manager authority/store roots. Preparation MUST bind source checkout,
sparse selection and worktree identity, and MUST NOT sync changed inputs
implicitly. Immutable composition records MUST reside in protected manager
state; a fragment MUST bind their digest, never a mutable current alias.
Generated control surfaces MUST be recorded separately from native mutable state.

The manager MUST project only approved control items into this home. In strict
mode, native trust MUST apply
only to the prepared worktree and MUST NOT approve another item or grant a
permission. A strict-certified adapter MUST suppress unadmitted ancestor/current/nested
instructions, native/project config and permissions, compatibility/native skill
roots, MCP, hooks/plugins and automatic memory, including startup, reload, late
discovery, resume and child entry. It MUST re-admit only selected protected
context, skills and MCP, enforcing an explicit empty MCP set when none is
approved. Copying selected files, a home path, one suppression flag or native
trust alone MUST NOT count as qualification. Trusted mode is the first delivery
target; this loader boundary does not contain hostile same-user executable code.

A protected adapter record is exactly
`{kind: "project-adapter/1", environment, provider_version, platform, modes, surfaces}`.
Platform is `macos` or `linux`; provider_version is an exact bounded release
string, never a range. Surfaces form a unique sorted set from `context`, `skills`,
`mcp`, `commands`, `permissions`, `memory-off`, `native-source-exclusion`.
The unique UTF-8-sorted `modes` set contains only `native-project` and `strict`.
Every launch MUST require its advertised mode, certified `permissions`,
`memory-off` and every required selected surface. Strict MUST additionally
require certified `native-source-exclusion`; absence MUST refuse without a
native-project fallback. Advertisement MUST
bind real qualification for that exact environment/release/platform; one runtime
MUST NOT borrow another's evidence. Unsupported required surfaces or consumers
MUST refuse without optional omission, native fallback or a downgraded claim.

### 5.1 Explicit native-project mode

The protected registration selects the mode per checkout × profile × environment;
the composition and fragment MUST carry the same value. Unknown modes or
inconsistent bindings MUST refuse `project_context_invalid` before publication.
Changing mode MUST require an explicit operator update and new registration/
composition identities, preserving busy-home and lease rules. Repository files,
a failed strict qualification or an adapter default MUST NOT enable this mode.

In native-project the harness reads repository-native instructions, config,
skills, MCP, hooks and plugins under its own rules. Curator MUST deliver from
the project only approved whole skills and approved MCP; their pins, audit,
item approval and protected ownership remain required. Curator MUST NOT
concatenate project root/system context into the managed-home instruction
document: it is the profile root only, avoiding a second managed copy of
instructions that the harness reads natively. A selected context item MUST
refuse `project_context_unsupported`, including when optional; the operator may
choose a generation without that item, never an implicit omission.

Manager-programmed permissions MUST remain default deny; project permission
files MUST NOT alter that policy, even as restrictions. Native memory MUST
remain off. An adapter unable to enforce either contract MUST refuse
`project_context_unsupported`. Qualification covers their actual effects at
startup, reload, resume and child entry, not merely advertised booleans. Status
and launch output MUST name the selected mode and say exactly
**project sources not isolated** for native-project. Off admission does not
remove this notice or suppress native discovery.

This mode protects the approved Curator-delivered whole-skill/MCP pins and
audits, manager permission policy and memory-off contract. It provides no
isolation from repository content. Native instructions, config, skills, MCP,
hooks and plugins may load beyond Curator's approved inventory under the
harness's rules; native trust is not Curator item approval. It does not contain
hostile same-user executable code. Strict retains exclusion and additive
approved project context, and remains refused until its exact runtime tuple
qualifies. Native-project qualification MUST NOT be reported as strict
qualification or used for the unaccepted-candidate R-TRANSFER boundary.

## 6. Leases, busy updates, resume and collection

One home MUST have at most one materialized composition while leased.
Concurrent launches MAY share that composition only when the adapter supports
concurrent state access. Preparation MUST reserve the session and create a
`prepared` lease before fragment publication or collection can occur. Durable
transfer to the actual reserved session/runner MUST establish `active` before
provider start; detach, descendants and caller exit MUST NOT release it.
A failed pre-start preparation MAY release only after proving no child started.
An active lease MUST become `released` only after authoritative termination
and reconciliation of session authority/state ownership. Interrupted recovery
MUST enter `unknown` and retain the home/artifacts; returning to `active` or
`released` MUST require session and process-generation reconciliation. PID reuse
or elapsed TTL alone MUST NOT establish termination or release authority.

Repair, profile switching, skill/CLI sync and changed compositions targeting
that home MUST wait for every live/unknown lease to end or refuse
`project_view_busy` before writes. An idle update MUST be transactional and
recheck lease state before publication, serialized against acquisition so that
a concurrent lease cannot race a write. A separately named home requires explicit
operator choice, never an automatic fallback. Resume MUST use the original
composition and current authority; failure MUST NOT create a fresh launch.
Revocation MUST block new launches and dispatch admissions; replacing files
MUST NOT be treated as revocation of already-loaded native context.

Read-only control/status MUST report the admitted generation, candidate drift,
leased home, owning session and unknown/unreadable evidence without fetching,
repairing, approving or rebaselining. Busy refusal MUST identify the owning
session and advise waiting or ending it. Garbage collection MUST retain leased
homes, compositions and referenced artifacts, plus existing resumable, snapshot
and transaction roots. Unreadable liveness/reference evidence MUST remain
unknown, never absent; uncertainty MUST retain the corresponding roots.

## 7. Fragment members, commands and launch routes

The required member is exactly
`project_context: {version: 1, mode: "strict" | "native-project",
admission: "off" | "admitted", context_ref,
context_sha256, project_root, lease_ref}`. Context names the protected
composition; lease names its binding. `project_root` MUST equal its registration;
context/lease MUST match the same checkout, environment, home and generation.
`admission: "off"` MUST have no project items. Strict still requires certified
exclusion; native-project still permits native discovery and emits its notice.
No arbitrary env map, append list or executable text is admitted through it.

The optional member is exactly
`command_environment: {version: 1, operation: "checked-d-path/1", tool_ref,
dispatcher_ref, context_ref, context_sha256}`. It MUST name the same composition,
require a command-certified adapter and MUST NOT coexist with `path_prepend`.
After child-environment admission, the destination MUST resolve protected
Werkstatt tool/dispatcher directories, reject aliases between them, missing or
excluded PATH, unreadable roots, unsafe base components, shadowing and
stale/ambiguous command owners. It MUST prepend the tool directory once,
deduplicate base entries by filesystem identity retaining first admitted order,
retain an already-present dispatcher at its admitted position or otherwise
append it once. Empty, relative, CWD-sensitive or repository-writable base
components MUST refuse. It MUST NOT import caller PATH literals, run repository
`.agents/bin`, source repository initialization or let native settings overwrite
the result. Dispatch MUST authenticate the managed session and revalidate full
owner/artifact activation. Unsupported protected command execution MUST refuse;
this contract grants no exception to existing enforced-worker requirements.

The effective launch identity MUST bind context, lease, transform and actual
resolved PATH; exact-plan execution MUST additionally cover them with the
complete process digest. Unsupported old forwarders that would shadow the
admitted owner MUST be migrated through the protected dispatcher or refused;
unmanaged collisions MUST refuse ambiguous ordinary-command availability.
All `curator-*` names MUST remain reserved, and protected dispatcher/skill
command directories MUST be excluded from umbrella provider discovery even
inside configured provider trust roots.

These are separately versioned members, not fields in any frozen outer carrier.
Readers MUST negotiate support for a complete project-capable outer carrier
before reading these members or looking up authority. Existing fragment v1–v6
and hosted/tracked request/record shapes MUST NOT gain these fields by inference.
A producer MUST NOT emit until the complete new outer carrier and corresponding
required-understanding consumer are published and supported. This amendment
allocates no outer revision token or tracking extension; lacking support MUST
refuse with the outer carrier's published version diagnostic before project lookup.

Before either supported local route, the launcher MUST acquire the Werkstatt
lease and use the shared construction site with the approved composition.
The [accepted delegated transition](local-hosted-launches.md) retains live-home
provenance. Its general home-lease/exclusive-profile conditions were separately
confirmed by owner decision 2026-10-27 in the [home-lease contract](home-leases.md);
that typed profile-home record does not replace this project-specific binding.
Delegated delivery MUST bind the tuple
through its own required-understanding
contract, verify the fragment digest, preserve resolved values and use the
leased Werkstatt home without claiming snapshot provenance. An incapable
shared-profile-home-only consumer MUST refuse. Exact delivery MUST use
Curator-owned capture of the approved inventory, bind snapshot/manifest,
policy and resolved PATH in the sealed complete process, and MUST NOT copy
an arbitrary home or allow host recomposition/repair. The original-home session
lease MUST remain until termination and authority/state reconciliation;
successful capture alone MUST NOT release it. Snapshot capture/activation and
project source exclusion require separate qualification. Hosted refusals or
resume failures MUST NOT fall back to native execution or mint a new session.

## 8. Diagnostics, publication and deferred surfaces

The typed refusal registry is
[environments §10.6](environments.md#106-project-context-diagnostics).
Unknown or inconsistent modes/admission use `project_context_invalid`. Missing
mode advertisement, required permissions/memory-off or strict exclusion, and
selected native-project context items use `project_context_unsupported`. No
new diagnostic code is allocated. Failures MUST preserve existing home/approval state and emit no success fragment,
child, MCP connection or partial control publication. Permitted refusal telemetry
MUST be redacted. Read failure MUST NOT become absence, optional omission or a
new baseline. Existing version and credential diagnostics retain their ownership.

The member schemas and paired positive/negative vectors are a separate leaf-1
publication. A standalone schema case proves structure only. Complete authority,
filesystem, rendering, lease/race/recovery, command and real native-adapter
qualification remain required before advertising a tuple; publication alone
MUST NOT advertise support. Unknown or unmeasured tuples MUST remain refused.

Multi-profile alternatives/stacks, profile-only/null-root command transforms,
general remote/account/tracked transform transport, simultaneous same-home
writers, conditional rule dialects, mutable knowledge/private-memory delivery,
native settings/hooks/plugins, multi-command integrations, OpenCode/Pi,
Windows, bare instruction-file items and native imports remain deferred.
Project permission-file import remains forbidden, not future authority.
Opted-in private memory retains the accepted per-Werkstatt explicit-deletion
policy but has no delivery grammar in leaf 1. Profile root/system replacement
is withdrawn permanently, not deferred. No launch support, credential operation
or native qualification is claimed by this publication.
