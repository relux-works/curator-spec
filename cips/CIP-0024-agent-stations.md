# CIP-0024: Agent stations

- **Status:** Draft
- **Owner:** orchestrator; decisions: operator
- **Created:** 2026-10-22
- **Updated:** 2026-10-23 (revision 2)
- **Related:**
  [CIP-0002](CIP-0002-project-context-in-managed-launches.md) — Werkstatt homes;
  [CIP-0009](CIP-0009-donor-side-deployment-and-bridge.md) — donor isolation;
  [CIP-0011](CIP-0011-credential-broker-and-agent-users.md) — accounts and credentials;
  [CIP-0016](CIP-0016-local-hosted-launches.md) and
  [CIP-0023](CIP-0023-exact-plan-hosted-launches.md) — hosting;
  [Decision 0021](../decisions/0021-sessions-enter-through-curator-run.md) — session entry
- **Affects:** task-board station registry and assignment; curator-run Werkstatt
  lifecycle; Curator home/context composition; dispatcher account allocation;
  credential broker and key custody; a2a delivery and scheduler admission

## Operative summary

| Field | Contract |
|---|---|
| Phase | Draft; the operator decisions of 2026-10-22/23 below are decided. No runtime capability or wire extension is published here. |
| Station | One agent, one OS account, one a2a identity, its own keys, Werkstatt home and root context. No account pooling. |
| Hierarchy | Swarm (platform) → Colony (product team; colony manifest) → Swarm cell (one project unit: one orchestrator and its workers) → Station. |
| Registry | task-board's `station` element, with fields equal to the router's station snapshot. |
| Lifecycle | curator-run: create, up, down, recycle, status, list, retire; extend FRONT-DOOR §6 and `werkstatt-record-v1`. |
| Ownership | Station record: task-board; lifecycle: curator-run; OS accounts: user manager; keys: Keymaker; credentials: broker; home, lease and composition: Curator. Dispatcher retains its authorized execution boundary. |
| Key custody | Interim: one ssh-agent per station, inaccessible key file and socket access limited to that station UID. Target: Keymaker; stations never hold identity keys. |
| Authority | Raising orchestrator and environment owner, with owner direct chat bound at raising. Services enforce grants and signed envelopes; editable text is not the enforcement boundary. |
| Platform controls | Platform-owned root context, skills and hook settings; protected trust pin; approved-release-only updates and launcher digest checks before every start. |
| a2a | One daemon / Matrix client per station identity, beside the session host. |
| Wave 1 | Explicit native-project mode; strict follows per runtime after qualification. |
| Task lifetime | Persistent stations preferred; `task-board spawn` stays as a fresh-context, one-task station wrapper. |
| First pilot | The Curator lane's 11 Werkstätten, with explicit migration and qualification gates. |

## Owner decisions (2026-10-22/23)

Draft status does not reopen these decisions. A station remains one agent with
its own OS account, a2a identity, keys, Werkstatt home and root context. Accounts
MUST NOT be pooled. The orchestrator is itself a station with role
`orchestrator`. The Curator pilot remains its 11 existing Werkstätten.

1. **Key custody — decided.** Every station MUST have distinct a2a, Git
   signing/push and other required keys from the start. Interim custody MUST use
   one ssh-agent per station. The key file MUST be outside the station's access;
   the signing socket MUST be accessible only to the station UID. The station
   can request signing but MUST NOT be able to read the key file. The target is
   the Keymaker service (`swarma-keymaker`), where stations never hold identity
   keys: **the key is the identity; the agent asks a signer**. This replaces the
   first draft's station-readable key-file exception.
2. **Platform-owned paths — decided.** Root context, skills and hook settings
   MUST be platform-owned and read-only to the station. Use an admin-owned
   skeleton, sticky writable directories and a root-owned trust pin. Before
   every start, the launcher MUST verify their digests against the approved
   profile and MUST refuse a mismatch.
3. **Approved updates — decided.** Profile changes MUST arrive only through an
   approved release. A station MAY trigger its own update, but it MUST install
   only an already-approved release and MUST be a no-op when none exists.
4. **Trust root — decided.** A station accepts tasks and commands from its
   raising orchestrator and environment owner. Services MUST enforce this
   authority through grants and signed envelopes, not through text the station
   can edit. Delegation MUST only attenuate authority. The owner's direct chat
   MUST be bound when the station is raised.
5. **Hierarchy — decided.** Swarm (platform) > Colony (a product team, described
   by a colony manifest) > Swarm cell (one project unit: one orchestrator and its
   workers) > Station. A lane is the project work stream within this structure,
   not another account or an alternative hierarchy level.
6. **a2a daemon — decided.** Each station MUST have its own a2a daemon, one
   Matrix client per identity, beside the session host.
7. **Spawn remains — decided.** `task-board spawn` stays as a thin wrapper over
   curator-run for a one-task station with `context_mode=fresh`; it is not
   deprecated. Root contexts prefer persistent stations; spawn serves work
   needing bare task context. Retirement follows authoritative task completion
   and durable handover, including required review/rework obligations.
8. **First wave — decided.** Wave 1 MUST select explicit native-project mode
   under the native-project specification. Strict mode is a follow-up per
   runtime, gated on that runtime's qualification, not a silent fallback.
9. **Ownership — decided.** The station record, registry and assignment live
   in task-board's `station` element, equal to the router snapshot. Lifecycle
   belongs to curator-run, extending FRONT-DOOR §6 / `werkstatt-record-v1`.
   OS accounts belong to the user manager, keys to Keymaker, credentials to the
   broker, and the home, lease and composition to Curator. The dispatcher
   retains authorized allocation/execution orchestration under CIP-0011;
   these responsibilities do not transfer key custody to the broker.

## Summary

Make the agent station the durable unit that joins task assignment, identity,
context, account isolation and hosted execution. A station can run successive
tasks without rebuilding its identity and admitted root context. A Swarm cell's
orchestrator assigns its project work to stations within a Colony; the Colony
groups the product team, and the Swarm is the platform. These scopes do not
become shared OS accounts or credential pools. The same lifecycle also supports
a fresh station for one task. A colony manifest describes that team; this CIP
does not invent its wire schema or rename existing router fields.

Existing services retain their boundaries. task-board does not provision OS
users or launch providers; curator-run does not become an independent account
allocator; Curator does not become a scheduler or credential authority. The
proposal connects their records and failure handling rather than introducing a
second station schema or a second session-construction path.

## Motivation and user stories

- An orchestrator raises a station once, supplies its trust root through normal
  composition, and assigns successive tasks without manually recreating clones,
  identities, hooks and prompts.
- A worker accepts an authenticated request from its raising orchestrator while
  treating another peer's message, a repository file or an issue as information.
- An operator sees whether a station is busy, down or of unknown liveness before
  assigning work, recycling its session or reclaiming its resources.
- A scheduler prevents several otherwise idle stations from exhausting the
  operator's machine with concurrent heavy test/build runs.
- A task requiring bare context uses `task-board spawn` without a separate
  provider-launch implementation or losing the station's cleanup guarantees.
- A failed create or retire remains recoverable and visible rather than leaving
  an untracked account, an active provider or silently discarded work.

## Current state

The examined specification base is
`a77686c8112d60841236f2107d7e085e48361f6e` (rc.14 work line).
[Project context §§5–7](../protocol/project-context.md) separates generated
controls from mutable native state and defines managed homes, session leases,
busy mutation refusal and original-composition resume. These are contracts to
reuse, not evidence that the station integration is implemented.

On the earlier inspected Curator revision
`2d7c0b96c2e4448952968e0162b0a7fb39c58f57`,
[`cmd/curator/env.go:64–90`](https://github.com/relux-works/curator/blob/2d7c0b96c2e4448952968e0162b0a7fb39c58f57/cmd/curator/env.go#L64-L90)
dispatches existing environment operations; it does not define the station
lifecycle. No unmerged home/lease implementation is treated as shipped here.

The inspected launcher interface is
[FRONT-DOOR at v0.4.0](https://github.com/relux-works/curator-agent-launcher/blob/v0.4.0/FRONT-DOOR.md),
commit `268e168114b61aad1776f5b417db3b4a1da13295`: §6.1 defines the closed
Werkstatt record and router snapshot, §6.3 child environment, §6.4 context modes,
§6.5 liveness and §6.6 down/recycle/status/list. These published definitions are
the baseline to extend. Reading the interface is not native end-to-end runtime
qualification. The task-supplied analysis describes manual setup/assignment,
incomplete a2a task/doorbell integration and no shared host budget; this draft
does not claim to have measured those deployments.

[Decision 0021](../decisions/0021-sessions-enter-through-curator-run.md)
already selects curator-run as the session entry. CIP-0016 and CIP-0023 own the
hosted launch contract, exact-plan detach and doorbell qualification. CIP-0011
still distinguishes architecture decisions from unpublished account, grant and
host-start interfaces. No station feature can infer their availability from
acceptance of this proposal.

Wave 1 references the
[explicit native-project specification, §5.1](https://github.com/relux-works/curator-spec/blob/2510171ca9e7a4a9d2b69e7b2e7ec23b6d11bb8a/protocol/project-context.md#51-explicit-native-project-mode).
That proposal is pinned separately from the examined main base; this revision
does not merge it, publish its carriers or claim runtime support. Native-project
and strict are distinct explicit modes, not inferred qualification levels.

## Design

### Ownership and records

| Owner | Responsibility | Boundary |
|---|---|---|
| task-board | `station` element, registry, lane/role relationships, task assignment | Same fields and semantics as router station snapshot; no parallel routing schema or OS-user authority. |
| curator-run | create/up/down/recycle/status/list/retire and durable operation reconciliation | Extend FRONT-DOOR §6 / `werkstatt-record-v1`; no direct bypass of dispatcher physical-start authority. |
| Curator | Managed home, admitted root/project context, composition and lease | One construction site; no home mutation while a live or unknown session retains its lease. |
| User manager | One OS account per station and authorized account cleanup | CIP-0011 narrow helper operations; curator-run does not allocate users itself. |
| swarma-dispatcher | Authorized allocation/execution orchestration under station accounts | CIP-0011 grants, allocation records, capacity and physical-start authority; not the account or key custodian. |
| Keymaker | Station identity-key custody and signing | Interim dedicated ssh-agent; target Keymaker service. No station-readable private key or shared lane signer. |
| Credential broker | Credential issuance and bounded leases | Credential delivery is not identity-key custody; no borrowed operator credentials. |
| a2a-swarm | Per-station daemon / Matrix client, authenticated task kinds and Codex doorbell transport | Beside the session host; transport delivery does not authorize assignment or prove task completion. |
| Scheduler | Heavy-run admission per host | Idle stations do not imply available host capacity. |

The task-board station representation must equal the router snapshot's fields
from FRONT-DOOR §6.1:
`id`, `identity`, `role`, `project`, `runtime`, `model`, `effort`, `weights_id`,
`trust_class`, `state`, `current_task`, `queue_depth`, `last_heartbeat_at`,
`config_decision_id`. This is the upstream list, not a new station schema.
Do not create a hand-copied subset with independently evolving meanings. The
owners must freeze the shared version and mapping before enabling writes.
Distinguish that registry projection from curator-run's execution record and the dispatcher's
allocation record: they are not three writers to one closed JSON document.
Bind their identities and generations in a jointly specified adapter. Refuse
unrecognized versions rather than attaching extra members to a closed carrier.

FRONT-DOOR §6.1 reads `task-board station get <id> --json` when available,
otherwise the checked local Werkstatt record; the board wins when both exist,
with a warning on disagreement. Preserve that source selection during
migration. The router field list is not the whole launcher configuration:
profile, clone/Git layout, room, orchestrator, context mode and child environment
remain governed by the Werkstatt record. §6.5 also calls for mirroring `session`
when station exists, although it is outside the fourteen-field snapshot list;
the owners must publish that projection/version binding, not silently append
it to either closed record.

The interim `orchestrator` binding is protected lifecycle/registry metadata,
not an agent-editable checkout setting. Reassignment or reparenting cannot be
achieved by editing a root-context file. Concurrent assignment must check the
current station/task assignment and execution generation; uncertain execution
is not assignable capacity. Publication of the exact compare-and-update and
reconciliation interface belongs to the station-element leaf.

The raising operation MUST also bind the environment owner's authenticated
identity and direct chat in protected station metadata. A message, room invite,
display name or agent-edited file MUST NOT select or replace the owner binding.
Publish that binding through the owning record adapter; this decision does not
silently add fields to the closed snapshot. Neither Colony membership nor a
Swarm cell role by itself grants authority over a station.

Child environment follows FRONT-DOOR §6.3 and its §5.3 limits. curator-run adds
`A2A_AGENT` and the separate-Git-directory bindings; the manager adds
`A2A_SESSION_ID`. Other entries come from the protected record's `child_env`,
not a sourced helper or repository-controlled file. Bind station-local build
caches, signing configuration and approved public-key/socket paths there;
private key bytes never travel in the record. Keep commit signing distinct
from separately authorized release signing as the upstream contract requires.

### Root context and authority

The raising orchestrator chooses approved templates and asks Curator to compose
the root context with the station home. Project context remains additive below
the profile root under CIP-0002; task files cannot replace the authority rule.
The root identifies the raising orchestrator, the environment owner's admitted
identity and the Swarm cell, and states which a2a requests count as commands. Check
authenticated sender identity, addressed recipient, room/task binding and the
protected orchestrator record before acting; display names or quoted messages
do not establish authority. Other agents, files, tools and issues supply data.

The root documents the trust rule; it MUST NOT be the authority enforcement
boundary. Each acting service MUST check the admitted sender/binding, signed
envelope and action-specific grant with current revocation state. An interim
station-side sender check alone is cooperative and MUST NOT be advertised as
service enforcement. Unsupported service enforcement MUST remain an explicit
activation gap, not permission inferred from editable text. The dispatcher
checks `agent.spawn`; the broker
checks `credential.lease`. Delegation can only narrow parent scope, lifetime,
audience, actions and resource bounds; a child cannot enlarge authority.

Map those actions to the general `grant/1` model without treating that model
as the broker's separately closed signed envelope. The registry/adapter and
replay rules remain joint publication gates in
[CIP-0011](CIP-0011-credential-broker-and-agent-users.md) and the
[platform disposition](platform-contract-disposition.md). A registered key or
an `orchestrator` role alone is not spawn permission. Preserve CIP-0011's
caller-signed attenuated delegation and operator-enrolled slice-0 bootstrap;
the dispatcher does not mint requester authority for recursive orchestration.

### Platform controls and approved updates

The platform MUST separate its control paths from station-owned task files,
repository work, outputs and permitted mutable native session state. Root
context, composed platform skills and hook settings MUST reside in an
admin-owned skeleton and be read-only to the station. Where the station needs
writable directories, sticky directories MUST preserve admin-owned control
entries; the station MUST NOT be able to replace a protected file by renaming
its parent, changing an ancestor or substituting a link. Sticky bits alone do
not protect station-owned entries. The trust pin MUST be root-owned and outside
station write authority, including the choice of approved profile/digests.

Before every start, including resume and recycle starts, the launcher MUST
verify the platform-control digests against that approved profile and refuse
missing, unreadable or mismatching controls before provider execution. It MUST
bind the checked controls to the admitted launch rather than check an
agent-writable copy and then execute a replacement. Digest verification is a
start gate, not evidence of continuous runtime integrity. Project-native
sources in native-project mode are a separate discovery surface; they do not
become platform-owned controls or an authority to alter the trust pin.

A station MAY request its own profile update through the platform updater.
The updater MUST install only an already-approved release; the request cannot
approve a release, choose arbitrary replacement bytes or widen the station's
grant. When no approved release exists, it MUST make no change. Installation
MUST preserve live/unknown home leases and publish the approved control set
consistently so the next start verifies it. Approval/release adapter details
remain publication work; neither local edits nor a self-update request bypass
that boundary.

### Per-station a2a daemon

Each station MUST run its own a2a daemon beside the session host, with one
Matrix client bound to that station's identity. A shared daemon using a pooled
identity does not meet this decision. Lifecycle provisioning MUST correlate
daemon setup, identity, owner-chat binding and doorbell routing with the same
station operation. Recovery MUST reconcile an existing client before creating
another after a lost acknowledgement. Daemon failure MUST be visible and MUST
NOT imply that the agent session stopped or that its leases can be released.
Authenticated delivery, replay/dedup and service authorization remain distinct
checks; neither a heartbeat nor an accepted doorbell proves task completion.

### Wave 1 project mode

Wave 1 MUST explicitly select `native-project` through the protected
registration/composition/fragment binding defined by the pinned specification.
An adapter default, repository instruction or failed strict check MUST NOT
select it. Startup and status MUST name the mode and display
**project sources not isolated**, including when project item admission is off.

In this mode the harness discovers repository-native instructions, config,
skills, MCP, hooks and plugins under its own rules. Curator-delivered project
material remains limited to approved whole skills and approved MCP with their
pins, audit, admission and protected ownership. The managed-home instruction
document MUST remain profile-root-only; selected project context items MUST
refuse `project_context_unsupported`, including optional ones, rather than
create a second managed copy of native instructions. Manager-programmed
permissions MUST remain default deny and immune to project permission files;
native memory MUST remain off. An adapter unable to enforce these requirements
MUST refuse. Native discovery may exceed the Curator-approved inventory; this
mode does not isolate repository content or hostile same-user executable code.

Strict mode remains a follow-up for each exact runtime/release/platform tuple,
requiring its own exclusion and surface qualification. Native-project evidence
MUST NOT be reported as strict qualification, used for the unaccepted-candidate
transfer boundary or used to excuse missing platform-control/service trust
checks. A mode change requires the explicit operator update and new protected
registration/composition identities while preserving lease/busy rules.

### Lifecycle and failure handling

Use FRONT-DOOR §§6.5–6.6 as the authority for liveness, busy checks, recycle and
unknown liveness. The router's five states are `idle`, `busy`, `starting`,
`draining`, `down`; the launcher additionally records `unknown`, which is not
dispatchable. The following table states station consequences, not new
serialized state names. Replay the upstream cases against the pinned record
version rather than translating uncertainty to idle.

| Operation / observation | Proposed transition and invariant |
|---|---|
| create | Absent station → recorded provisioning → usable, stopped station only after all required resources and trust/context bindings are durable. Partial provisioning is visible and reconciled. |
| up | Known stopped and admitted station → prepared/starting → running through the supported hosted route, under its own account. A lost response does not authorize another start. |
| status / list | Preserve §6.6's `werkstatt-status-v1` projection; status may refresh the protected liveness mirror from manager evidence, without silently terminating or declaring completion. |
| busy | Retain task assignment, home/session lease and host claims; refuse conflicting mutation or recycle under the upstream busy rules. |
| down | Request a fenced stop; report stopped only after authoritative termination/reconciliation. Preserve identity, task history and resumable state. |
| recycle | Under one lock, graceful `down` with `not-busy`, then `up --new` for a new conversation; preserve station identity/account and admitted home. Refused down prevents the new start. |
| unknown | Retain leases, allocation and scheduling claims; surface uncertainty and reconcile. A PID lookup, TTL, quiet inbox or launcher exit is not proof of absence. |
| retire | Quiesce, prove absence, resolve task/output/retention obligations, then release resources with durable cleanup progress. Never silently erase unresolved work. |

Preserve §6.5's bound-manager identity and exact expected-value
`(manager, operation_id, generation)` fencing. A generation is local to its
manager, not a cross-manager counter. The manager's session record supplies
execution state; a2a heartbeat is displayed separately, never merged into a
termination verdict. `last_heartbeat_at` is the time of a manager read, and
staleness means nobody looked. Unreadable manager records produce `unknown`
while preserving the previous non-state bindings. Assignment edits require a
non-null session; a never-started or override-only station is not dispatchable.

`--abandon-operation` is an explicit operator override, not proof that anything
stopped remotely. Preserve that provenance and the abandoned-operation fence;
it cannot authorize destructive retirement or lease release. Rebinding a
manager requires the upstream exact-session read. Normal `down` uses the
manager's atomically checked `not-busy` precondition and expected generation;
its explicit force path does not remove generation fencing. During recycle,
`draining` is not down: poll under §6.6's bound (one second, twenty seconds),
then refuse `werkstatt_busy` rather than start a second generation.

**Create is a reconciled transaction.** Correlate account allocation, home and
clone creation, a2a registration and daemon setup, owner-chat binding, doorbell
installation, distinct signer setup and record publication under one durable
operation identity. Bind verified platform controls and trust/context
before marking the station usable. Retry the same operation idempotently; do
not allocate another account, register a second identity or start another
provider after a lost acknowledgement. If a step fails, roll back only resources
created by that transaction, in reverse dependency order. Failed compensation
remains a visible partial operation for reconciliation; it cannot be reported
as clean absence or delete resources whose ownership is uncertain.

Cross-account clones must satisfy CIP-0011's F16: each account owns its private
Git administrative state (common directory, refs, index, config and hooks).
Linked worktrees with writable back-links into the operator's Git directory do
not qualify. Existing same-account worktrees remain legacy behavior, not a
cross-UID isolation mechanism. Source/result transfer requires the published
authorized boundary, not broad access to the operator's home.

**Retire is deliberate resource release.** Distinguish stopping a session,
recycling it and retiring the station. Confirm no live or unknown execution,
preserve accepted results through the authorized result boundary, and resolve
pending task/review work before irreversible cleanup. Follow CIP-0011's F1:
after proven quiescence and authorized signer/credential cleanup, normal
retirement deletes the account home; partial cleanup remains journalled. Retain
only the permitted closed,
service-authored metadata, not a raw home archive or agent-authored secret
payloads. Explicit operator retention is a separate authorized operation with
its stated confidentiality limits. CIP-0011's standing identity is preserved
for historical attribution; station retirement does not automatically revoke
that identity. One-shot identity cleanup follows its separate owner contract.

### Host budget

The scheduler admits concurrent heavy test, build and mutant runs against a
host budget before they start. Budget applies across stations and lanes on
that host, including task-lifetime stations. OS-account count and process
permissions do not replace this admission. Queuing, rejection and reservations
must be visible; a retry cannot acquire duplicate capacity. Release only on
authoritative completion or reconciled absence; unknown execution retains its
claim. Publish admission/fencing and crash recovery with the scheduler owner.
The initial numeric policy is Q1, not an assumed portable machine limit.

### Persistent stations and task-lifetime spawn

Persistent stations are the preferred root-context workflow. Keep
`task-board spawn` as the existing user-facing task operation, implemented over
curator-run's station lifecycle rather than a second provider runner. A spawn
requests `context_mode=fresh` and receives its own station account, identity,
keys, home and trust binding. Fresh means bare task context composed with the
required trust/security root, not omission of that root or unchecked ambient
configuration. Task retry does not silently reuse another task's fresh context.
Preserve §6.4's distinction: persistent `continue` resumes its native thread;
`fresh` recycles before a new task, while review rework may continue the same
task thread in either mode. A new task and rework are not interchangeable.

Retire the task-lifetime station when the task is done, after durable handover
and required review/rework obligations. Provider exit or delivery of a doorbell
alone is not task completion. The exact board terminal-state/retention mapping
is Q2; it must preserve recoverable outputs and apply the same retire failure
handling as a persistent station.

### Options considered

1. **Keep setup scripts and manual station bookkeeping.** Low migration cost,
   but no shared assignment/lifecycle authority, transactional provisioning or
   host budget. Reject as the target.
2. **Pool OS accounts or share lane keys.** Reduces setup work but merges
   filesystem and identity authority across agents. Rejected by the operator;
   `0600` cannot isolate stations sharing a UID.
3. **Put provisioning and execution in task-board.** Convenient single API,
   but duplicates the dispatcher, Curator and curator-run ownership. Reject.
4. **Compose existing services around stations.** Use the router-compatible
   registry, curator-run lifecycle, Curator composition and dispatcher/broker
   boundaries. Recommended; its joint publication and recovery costs are
   explicit implementation gates.

### Recommendation

Adopt option 4 under the decided constraints. Deliver the leaves below in
order; distinguish interim signer custody from Keymaker and advertise only
capabilities whose versioned interfaces and native behavior are qualified.
Do not deprecate spawn or replace account isolation with a cheaper shared UID.

## Security considerations

**Keys and credentials.** Distinct keys are required from the first station;
never reuse the operator's identity or a common cell/lane signing key. Interim
custody MUST provide one ssh-agent per station with key files outside station
access and socket permissions limited to that station UID. A `0600` private
file owned by the station does not meet this contract. Key paths, inherited
ACLs, aliases, socket replacement and child-process access must be qualified
without exporting private bytes in records, Git, logs or resources. Socket
access allows signing, not key-file reading; a compromised station can still
misuse signing operations within its permitted authority. A verifying signature
alone is not evidence of operation authorization. Keymaker
replaces interim custody without exposing identity keys to stations; credential
issuance and action/audience/lifetime-bounded leases remain the broker's role.
Rotation, revocation, renewal and failure behavior require owning-service
qualification before either target capability is advertised.

**Controls and trust.** Service-checked grants and signed envelopes enforce
the raising-orchestrator/owner binding. Platform read-only files, the root-owned
trust pin and launcher digest gate prevent a local edit from rewriting that
binding or disabling hooks. Approved-release-only self-update is not
self-approval. Native-project discovery can load repository material; it MUST
NOT widen service grants, replace protected controls or be represented as
strict isolation. Root prose alone cannot contain prompt injection.

**Before separate accounts.** The interim same-account migration posture
requires a Seatbelt deny profile covering the operator's CloudStorage, Mobile Documents,
Mail, Messages, Photos and Keychains directories. Resolve policy against the
protected operator home, cover aliases and child processes, and qualify the
actual named station host as TCC responsible process, not a generic interpreter.
Do not grant a shared interpreter broader TCC access. This interim posture is
not a target station, does not establish a separate UID boundary, and does not waive
the one-account-per-station decision. Test denial on isolated fixture trees;
do not probe the operator's real personal data to qualify it. Platforms without
Seatbelt need their own declared supported boundary; no macOS result implies
portable sandbox qualification.

**Account and execution authority.** No arbitrary `sudo -u`, shared writable
Git administration or caller-composed privilege escalation is introduced.
Follow CIP-0011's dispatcher physical-start and host lifecycle permit rules,
including current grant/revocation checks. Root-context text cannot authorize
an OS account, credential lease or hosted start. Busy/unknown state must retain
the claims that prevent concurrent execution or destructive home mutation.

**Related isolation contracts.** CIP-0009 distinguishes donor harness/bridge
isolation from same-UID precautions. This proposal neither qualifies a donor
variant nor imports its private key into a station. CIP-0002's home lease and
CIP-0023's original-home versus snapshot-capture leases remain distinct;
station retirement cannot shorten them by deleting a registry row.

## Compatibility and migration

This Draft changes no released schema, CLI behavior or conformance claim.
Extend versioned interfaces with their owners; do not add station members to
closed rc.14 fragments or older exact-plan carriers. Unsupported account,
doorbell, grant or hosting capabilities must be reported as unavailable rather
than falling back to shared credentials or an ungoverned provider launch.

Start with the Curator lane's 11 existing Werkstätten. Inventory active tasks,
sessions, identities, homes and required outputs; then quiesce and migrate each
under explicit ownership. Preserve historical attribution and accepted Git
results. Do not copy an operator's credential store into a station account or
move a live home underneath an existing session. New station-specific signers and
clones need their own grants and source/result transfer admission. Keep legacy
sessions labelled and reconcile them before retiring their resources.

The first lifecycle/registry leaves may stage interfaces and same-account
rehearsals while account support is pending; they must not advertise target
isolation. The account slice is required before the pilot qualifies as stations.
Wave 1 uses explicit native-project mode with its visible non-isolation notice;
no pilot result advertises strict until the corresponding runtime qualifies.
The pilot is not an exemption from signed delivery, exact-head review, host
budget or remaining native hosting qualification. Existing spawn behavior stays
available until its qualified wrapper can replace the implementation without
changing its task contract.

## Specification changes

After design acceptance and joint interface publication, prepare separate
adoption artifacts under [governance](../GOVERNANCE.md):

- Amend Decision 0021 for station lifecycle entry and the retained spawn
  wrapper, without adding another session-construction site.
- Extend FRONT-DOOR §6 / `werkstatt-record-v1` with create/retire and their
  transaction/reconciliation rules; preserve §6.5 liveness semantics.
- Publish task-board's `station` element equal to the pinned router snapshot,
  assignment concurrency rules and protected orchestrator/owner-chat bindings.
- Bind account allocation and grant adapters to CIP-0011's published service
  contracts; keep general grants and broker signed envelopes distinct.
- Publish Keymaker's identity-signing adapter separately from the broker's
  credential leases, including the dedicated ssh-agent interim custody.
- Publish platform/station path ownership, the protected profile/trust pin,
  start-time digest verification and approved-release-only update entry.
- Bind the per-station a2a daemon to its identity and session host, with
  authenticated delivery and recoverable lifecycle rather than a pooled client.
- Reference CIP-0002's home/lease/composition rules and CIP-0016/CIP-0023's
  qualified hosting/doorbell capabilities rather than copying their schemas.
- Adopt the native-project mode publication jointly with its owners before
  wave-1 activation; retain strict as separately qualified per runtime.
- Publish scheduler admission and task-lifetime retirement mappings with the
  owning services. Allocate new versions/capabilities where closed carriers
  cannot represent the extension; this CIP assigns no wire version numbers.

## Implementation plan

These are proposed leaves in the analysis order, not completed deliveries.
Cross-owner publication and recovery tests are prerequisites to activation.

| Order | Leaf and owner | Deliverable and gate |
|---|---|---|
| 1 | **Werkstatt create** — curator-run with Curator and account-service owners | Extend the existing lifecycle record; provision home, clone, identity, daemon, owner chat, doorbell and signer bindings as a reconciled transaction. Reuse §6.5 for lifecycle; add safe retire, protected controls, start digest gate and approved-only updater. Account-dependent activation waits for leaf 4. |
| 2 | **Station element** — task-board and router owners | Publish the identical station snapshot fields/version, registry, protected orchestrator/owner-chat bindings, assignment fencing and lifecycle projection. Map Colony/Swarm cell relationships through owner-approved adapters; do not invent a colony manifest schema. |
| 3 | **a2a task kinds and Codex doorbell** — a2a-swarm owner | One daemon / Matrix client per station beside the session host; authenticated task/result/verdict routing, owner-chat binding and Codex wake-up delivery. Qualify replay/dedup, restart reconciliation and failure visibility with hosting doorbells. |
| 4 | **OS accounts, slice 0** — user-manager, dispatcher, Keymaker and broker owners | One account per station; dedicated ssh-agent with key outside station access and UID-restricted socket; authorized source/result transfer, dispatcher starts, allocation cleanup and service grant/envelope checks. Target keys belong to Keymaker and credential leases to broker. Qualify the 11-station native-project pilot only after these gates. |
| 5 | **Spawn over curator-run** — task-board and curator-run owners | Keep `task-board spawn`; create fresh task-lifetime stations, reconcile retries, retire after authoritative task completion and durable delivery. |

Across leaves, wire scheduler host-budget admission before qualifying heavy
parallel runs. Root templates must carry the decided trust rule and preference
for persistent stations. Track Keymaker replacement separately from interim
signer readiness; no interim pass establishes target issuance/revocation support.
Native-project and platform-release adapters are activation gates for wave 1;
strict requires subsequent qualification for each runtime rather than a blanket
station capability.

## Test plan

This task changes proposal prose only. Repository validation and link checks
check document integration; they do not prove station runtime behavior. Each
implementation leaf must state its executable claims beside tests, retain a
nearby valid positive control for every rejection, and demonstrate each new
gate with a bounded narrowing mutant that removes that gate. An unrelated
crash or setup failure is not a successful mutant control.

| Claim to prove in the owning implementation | Positive control | Negative witness and narrowing mutant |
|---|---|---|
| Provisioning is recoverable and idempotent | Create once; retry the acknowledged operation without extra resources | Inject failure/lost acknowledgement at each provision/publication step; assert owned rollback or visible partial state, no duplicate account/key/identity. Mutate durable operation matching. |
| Assignment respects current registry and execution generation | Assign an eligible known-idle station once | Concurrent/stale assignment and busy/unknown station refuse without starting work. Mutate generation/busy admission checks separately. |
| Authority follows admitted sender and grant scope | Raising orchestrator/owner request and attenuated current grants succeed | Foreign sender, quoted request, edited root file, widened/expired/revoked grant refuse without launch/lease. Mutate sender binding and each service's action/scope check. |
| Signing does not expose identity keys | Station signs through its own interim socket; target signs through Keymaker | Station UID cannot read its key file, another station cannot use the socket, and station-controlled socket substitution refuses. Mutate custody/UID/socket binding gates separately; a valid signature alone must not grant extra authority. |
| Platform controls remain protected at every start | Approved immutable skeleton, skills, hook settings and trust pin admit start/resume/recycle | Station write/rename through sticky parents, ancestor/link substitution, missing or modified controls and edited digest pin cannot admit start. Mutate path ownership, protected pin and digest checks separately; assert no provider child. |
| Self-update installs only approved releases | Station request installs an already-approved release; no available approved release is a no-op | Unapproved bytes/release, self-approval, widened grants and leased-home mutation refuse without partial control changes. Mutate approved-release selection and lease/publication gates separately. |
| Owner and daemon bindings survive routing/restart | Raising binds owner chat; one identity client resumes after an acknowledged restart | Message-selected owner, pooled identity, duplicate client after lost reply and foreign/quoted requests cannot authorize work. Mutate protected owner binding and daemon operation dedup separately; daemon loss cannot release session leases. |
| Wave 1 is explicit native-project, not implied strict | Matching protected mode records admit a qualified runtime with its required notice, permissions default-deny and memory off | Unknown/mismatched/default-selected mode, selected context item, project permissions changing policy, memory on, missing notice or unsupported adapter refuse; native discovery is never reported as isolation. Mutate mode binding, each required surface and notice gate separately; strict has its own exclusion controls. |
| Isolation matches the declared stage | Separate UID accesses its own home; approved named host runs fixture workload | Denied personal-directory fixtures remain unreadable via aliases/children. Mutate UID/ACL and Seatbelt admission separately. Neither this nor native-project qualification proves hostile same-user code containment. |
| Lifecycle preserves uncertain and resumable work | Known completed stop/recycle preserves identity and permitted resume | Upstream §6.5 busy/unknown cases, PID reuse, detached launcher exit and lease retention cannot become idle or destructive cleanup. Mutate authoritative absence/lease checks. |
| Heavy-run capacity is shared per host | Admitted run completes and releases its claim | Competing stations, crash/retry and unknown liveness cannot oversubscribe or double-release. Mutate scheduler admission and claim fencing. |
| Cross-UID clone and retirement preserve the authorized boundary | Private clone/result handover; proven-quiescent normal retirement | Foreign writable Git backlinks, unfinished review/output obligations and partial cleanup cannot leak access or silently lose state. Mutate clone-boundary and retire eligibility checks. |
| Spawn retains its task contract | Fresh one-task station delivers durably and retires on authoritative done | Existing task context is not reused; provider exit, duplicated doorbell or pending rework does not trigger early retirement. Mutate fresh selection and completion binding. |
| Published capability boundaries remain closed | Qualified versions admit a supported launch | Unsupported snapshot/record/grant/doorbell versions refuse rather than invent fields or fall back. Mutate the corresponding version/capability checks. |

Run destructive account/key/cleanup and sandbox probes only in isolated,
authorized fixtures. Record exact versions, platform, head and exit codes;
native TCC, cold-resume and doorbell qualification cannot be replaced by mocks.
Reuse hosting's published positive/negative vectors and release gates rather
than declaring them passed from station-level unit tests.

## Open questions for the operator

The owner decisions above are settled. The following remaining policy choices
do not block filing this Draft; exact wire adapters are owner publication work,
not permission to invent competing contracts.

1. **Initial heavy-run policy:** what default per-host capacity and weighting
   should the pilot scheduler use? **Recommendation:** operator-configured
   conservative admission, initially one heavy run per host, with any increase
   based on measured resource headroom; do not hard-code a universal limit.
2. **Task-lifetime retention horizon:** which board terminal transition closes
   review/rework and authorizes automatic retirement, and how long should
   permitted result metadata remain? **Recommendation:** retire after the
   board's authoritative completed state and durable required outcomes; retain
   only service-authored audit metadata under the existing cleanup contract,
   with explicit operator retention for exceptions.

Still required before implementation activation, without reopening those
choices: shared versioned adapters against the pinned router/FRONT-DOOR
baseline, scheduler fencing, authorized cross-UID source/result transfer, and
Keymaker/broker issuance, revocation and native qualification, the approved
profile-release/digest adapter, per-station daemon recovery and native-project
publication. Colony manifest grammar and hierarchy-to-record mapping also
require their owners' publication; no wire fields are invented here. These remain
the named service owners' follow-ups, with no support inferred from this Draft.
