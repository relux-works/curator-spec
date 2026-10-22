# CIP-0024: Agent stations

- **Status:** Draft
- **Owner:** orchestrator; decisions: operator
- **Created:** 2026-10-22
- **Related:** TASK-261022-vnrm0o;
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
| Phase | Draft; the six operator decisions below are decided. No runtime capability or wire extension is published here. |
| Station | One agent, one OS account, one a2a identity, its own keys, Werkstatt home and root context. No account pooling. |
| Lane | A project work stream with one orchestrator and many stations; the orchestrator is also a station. |
| Registry | task-board's `station` element, with fields equal to the router's station snapshot. |
| Lifecycle | curator-run: create, up, down, recycle, status, list, retire; extend FRONT-DOOR §6 and `werkstatt-record-v1`. |
| Account and keys | swarma-dispatcher, user-manager and credential broker; Curator owns home, lease and composition. |
| Authority | Raising orchestrator and, by default, the environment owner; other material is information. Target enforcement is service-checked, attenuating grants. |
| Task lifetime | Persistent stations preferred; `task-board spawn` stays as a fresh-context, one-task station wrapper. |
| First pilot | The Curator lane's 11 Werkstätten, with explicit migration and qualification gates. |

## Owner decisions (2026-10-22)

These decisions constrain this first draft; Draft status does not reopen them.

1. **Station and lane — decided.** A station has its own OS account, a2a
   identity, keys, Werkstatt home and root context. Every station gets a separate
   account; sharing accounts to reduce provisioning cost is not an option. The
   lane's orchestrator is a station with role `orchestrator`.
2. **Ownership — decided.** task-board owns the `station` record, registry and
   assignment. Its fields equal the router's station snapshot. curator-run owns
   lifecycle through the FRONT-DOOR §6 / `werkstatt-record-v1` extension.
   swarma-dispatcher, user-manager and the credential broker own account/key
   provisioning. Curator owns the CIP-0002 home, lease and context composition.
3. **Root context and trust — decided.** The raising orchestrator prepares root
   context from templates using ordinary Curator composition. It admits a2a
   tasks/commands from that orchestrator and, by default, the environment owner
   (the human operator). Everything else is information. Interim checks use
   the record's `orchestrator` field and the root-context rule on the station
   side. The target is signed grants checked by the acting service, with
   delegation only by attenuation: `agent.spawn` at the dispatcher and
   `credential.lease` at the broker, mapped to the general `grant/1` model.
4. **Own keys — decided.** Each station has its own a2a, Git signing/push and
   other required keys from the start. Interim keys are generated inside the
   station's own account, private files mode `0600`, inaccessible to other UIDs.
   The broker target supplies issuance and short-lived credential leases.
   Identity signing follows the platform principle: **the key is the identity;
   the agent asks a signer**. A keykeeper holds the identity key and signs for
   the agent. Self-held identity keys are an interim exception, replaced by the
   keykeeper; prompt injection can read a key file accessible to the agent's
   own UID despite `0600`.
5. **Spawn remains — decided.** `task-board spawn` is retained, not deprecated.
   It becomes a thin curator-run wrapper creating a task-lifetime station with
   `context_mode=fresh`, retired when the task is done. Root contexts prefer
   persistent stations and reserve spawn for work needing a bare context.
6. **Pilot — decided.** Convert the Curator lane's 11 Werkstätten first.

## Summary

Make the agent station the durable unit that joins task assignment, identity,
context, account isolation and hosted execution. A station can run successive
tasks without rebuilding its identity and admitted root context. A lane assigns
work to stations; it does not become an OS account or a shared credential pool.
The same lifecycle also supports a fresh station for one task.

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
`06243265be6c5691399bf9acc401eeafb941e8a5` (rc.14 work line).
[Project context §§5–7](../protocol/project-context.md) separates generated
controls from mutable native state and defines managed homes, session leases,
busy mutation refusal and original-composition resume. These are contracts to
reuse, not evidence that the station integration is implemented.

On the inspected Curator main revision
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

## Design

### Ownership and records

| Owner | Responsibility | Boundary |
|---|---|---|
| task-board | `station` element, registry, lane/role relationships, task assignment | Same fields and semantics as router station snapshot; no parallel routing schema or OS-user authority. |
| curator-run | create/up/down/recycle/status/list/retire and durable operation reconciliation | Extend FRONT-DOOR §6 / `werkstatt-record-v1`; no direct bypass of dispatcher physical-start authority. |
| Curator | Managed home, admitted root/project context, composition and lease | One construction site; no home mutation while a live or unknown session retains its lease. |
| swarma-dispatcher / user-manager | Authorized allocation, distinct OS account, execution under that account, cleanup | CIP-0011 grants, allocation records, capacity and narrow helper operations. |
| Credential broker / keykeeper | Credential issuance/leases and protected identity signing | Credential delivery is not identity-key custody; no borrowed operator or lane-wide key. |
| a2a-swarm | Authenticated identities, task kinds and Codex doorbell transport | Transport delivery does not authorize assignment or prove task completion. |
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
identity and the lane, and states which a2a requests count as commands. Check
authenticated sender identity, addressed recipient, room/task binding and the
protected orchestrator record before acting; display names or quoted messages
do not establish authority. Other agents, files, tools and issues supply data.

The interim station-side rule is a cooperative control. It does not make an
injected agent unable to misuse its own filesystem or credentials. In the
target, each acting service checks an action-specific signed grant and current
revocation/binding state. The dispatcher checks `agent.spawn`; the broker
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
clone creation, a2a registration, doorbell installation, distinct key setup and
record publication under one durable operation identity. Bind trust/context
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
after proven quiescence and key cleanup, normal retirement deletes the account
home; partial cleanup remains journalled. Retain only the permitted closed,
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

Adopt option 4 under the six decided constraints. Deliver the leaves below in
order; label interim isolation and self-held keys honestly, and advertise only
capabilities whose versioned interfaces and native behavior are qualified.
Do not deprecate spawn or replace account isolation with a cheaper shared UID.

## Security considerations

**Keys and credentials.** Distinct keys are required from the first station;
never reuse the operator's identity or a common lane signing key. Private key
files and containing directories must exclude other UIDs, including inherited
ACLs and accidental publication through Git, logs or resources. `0600` is an
interim cross-UID protection, not protection against the station itself. A
compromised prompt can read its own key file. Keykeeper custody removes that
file from the agent and mediates signing requests; provider credential leases
remain action/audience/lifetime bounded. Rotation, revocation, renewal and
failure behavior must be qualified before claiming broker/keykeeper support.

**Before separate accounts.** The interim same-account migration posture
requires a Seatbelt deny profile covering the operator's CloudStorage, Mobile Documents,
Mail, Messages, Photos and Keychains directories. Resolve policy against the
protected operator home, cover aliases and child processes, and qualify the
actual named station host as TCC responsible process, not a generic interpreter.
Do not grant a shared interpreter broader TCC access. This interim posture is
not a target station, does not isolate same-UID key files, and does not waive
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
move a live home underneath an existing session. New account-local keys and
clones need their own grants and source/result transfer admission. Keep legacy
sessions labelled and reconcile them before retiring their resources.

The first lifecycle/registry leaves may stage interfaces and same-account
rehearsals while account support is pending; they must not advertise target
isolation. The account slice is required before the pilot qualifies as stations.
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
  assignment concurrency rules and the protected orchestrator binding.
- Bind account allocation and grant adapters to CIP-0011's published service
  contracts; keep general grants and broker signed envelopes distinct.
- Reference CIP-0002's home/lease/composition rules and CIP-0016/CIP-0023's
  qualified hosting/doorbell capabilities rather than copying their schemas.
- Publish scheduler admission and task-lifetime retirement mappings with the
  owning services. Allocate new versions/capabilities where closed carriers
  cannot represent the extension; this CIP assigns no wire version numbers.

## Implementation plan

These are proposed leaves in the analysis order, not completed deliveries.
Cross-owner publication and recovery tests are prerequisites to activation.

| Order | Leaf and owner | Deliverable and gate |
|---|---|---|
| 1 | **Werkstatt create** — curator-run with Curator and account-service owners | Extend the existing lifecycle record; provision home, clone, identity, doorbell and keys as a reconciled transaction. Reuse §6.5 for up/down/recycle/status/list; add safe retire. Account-dependent target activation waits for leaf 4. |
| 2 | **Station element** — task-board and router owners | Publish the identical station snapshot fields/version, registry, protected orchestrator binding, assignment fencing and lifecycle projection. No independent schema. |
| 3 | **a2a task kinds and Codex doorbell** — a2a-swarm owner | Publish and qualify authenticated task/result/verdict routing and Codex wake-up delivery, replay/dedup and failure visibility, coordinated with hosting doorbells. |
| 4 | **OS accounts, slice 0** — swarma-dispatcher, user-manager, credential broker owners | One account per station; separate keys, authorized source/result transfer, dispatcher starts, allocation cleanup, grant/revocation checks and explicit interim key-custody limits. Qualify the 11-station pilot only after these gates. |
| 5 | **Spawn over curator-run** — task-board and curator-run owners | Keep `task-board spawn`; create fresh task-lifetime stations, reconcile retries, retire after authoritative task completion and durable delivery. |

Across leaves, wire scheduler host-budget admission before qualifying heavy
parallel runs. Root templates must carry the decided trust rule and preference
for persistent stations. Track keykeeper replacement separately from interim
self-held key readiness; an interim pass cannot close that residual.

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
| Isolation matches the declared stage | Separate UID accesses its own home; approved named host runs fixture workload | Other UID cannot read keys; denied personal-directory fixtures remain unreadable via aliases/children. Mutate UID/ACL and Seatbelt admission separately. Preserve the explicit own-UID self-held-key residual. |
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

The six decisions above are settled. The following remaining policy choices
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
broker/keykeeper issuance, revocation and native qualification. These remain
the named service owners' follow-ups, with no support inferred from this Draft.
