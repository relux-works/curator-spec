# CIP-0023: Exact-plan hosted launches with detached sessions and doorbells

- **Status:** Draft
- **Owner:** orchestrator; decision: operator
- **Created:** 2026-10-21
- **Related:** TASK-261021-vb3z6f — exact-plan-final-form;
  [CIP-0014](CIP-0014-managed-home-snapshots.md) — content snapshots;
  [CIP-0016](CIP-0016-local-hosted-launches.md) — local hosting;
  [CIP-0002](CIP-0002-project-context-in-managed-launches.md) — project admission;
  [Decision 0019](../decisions/0019-fragment-consumers-and-one-construction-site.md) — one construction site
- **Affects:** Curator snapshot capture/verification; curator-run selection
  and exact-plan protocol; agents-management hosted forms; session-manager
  preparation, records, doorbells, resume and garbage collection

## Summary

Propose `launch-exact/3`: a closed, snapshot-bound hosted launch with attached
and detached forms, a durable session result and a prepared doorbell binding.
It lets `werkstatt up` use the same exact-plan route as attached launches,
without host-side process composition. Advertise and retire delegated routing
per manager/runtime, preserving CIP-0016's initial joint Claude/Codex/Muse
release gate. An admitted CIP-0002 project composition becomes a verified
snapshot input, never a live session dependency. This Draft specifies the
intended final contract; schema publication and runtime qualification remain
owned follow-ups, not support claimed by this document.

## Motivation and user stories

- `werkstatt up` starts detached hosted sessions with doorbells while profile
  repair, switching and skill sync cannot change their admitted content.
- An operator attaches later and resumes after a known stop using the same
  snapshot, project generation and policy rather than today's live home.
- A manager moves one qualified runtime away from the interim route without
  implying that another runtime, platform or provider build is qualified.
- A crash after admission or a lost launch response does not start another
  provider, lose the session's snapshot reference or report false success.

## Current state

The examined curator-spec base is `e41f96387287f5e76604627f9e63662f7d6d86d4`
(released specification baseline rc.14).
[Local hosted launches §§1–7](../protocol/local-hosted-launches.md) and
[managed-home snapshots §§1–7](../protocol/managed-home-snapshots.md) define
exact execution, content ownership and remaining activation gates. In
particular, the snapshot manifest digest includes its source-fragment
binding; it is not a cross-home portable content digest.

The owner accepted the interim delegated direction on 2026-10-21. The
candidate [CIP-0016 amendment](https://github.com/relux-works/curator-spec/blob/3a3e041b3fbf76292e69b6abb4a0eca855524007/cips/CIP-0016-local-hosted-launches.md#revision-delegated-local-launches-2026-10-21)
on `cip16-delegated-launches` records live-home/caller-composition limits and
per-runtime retirement once exact support includes detach. It was in review
at this baseline; its proposed home-lease and exclusive-profile conditions
are not accepted conditions and are not prerequisites invented here.

Task-supplied launcher FRONT-DOOR appendix A and §5.8 state that
`launch-exact/2` cannot return a session record or carry a doorbell;
detached requests and `werkstatt up` therefore use `launch-delegated/1`.
The withdrawn trial flag does not gate accepted delegated launches. These
are supplied interface facts, not newly measured implementation probes.

The named `cip02-ready-for-acceptance` branch was absent in a successful
remote-head lookup during this task. The project interface below explicitly
assumes the current [CIP-0002 admission/composition contract](CIP-0002-project-context-in-managed-launches.md#admission-and-composition)
and its stable-home/lease proposal. Adoption must reconcile it with the
candidate when published. No runtime source audit, provider launch, credential
read or native qualification is claimed.

## Design

### Options considered

| Option | Mechanism | Tradeoff |
|---|---|---|
| Extend exact/2 implicitly | Append detach/doorbell/session metadata to the old request. | Breaks closed-reader and digest expectations; cannot prove old peers implement the new lifecycle. Rejected. |
| Keep detached delegated indefinitely | Exact snapshots for attached only; live homes for automated sessions. | Preserves today's compatibility but leaves the primary automation path without snapshot isolation. Rejected. |
| Publish exact/3 as a complete successor | Versioned preparation, full plan, session result and per-runtime qualification. | Requires coordinated owners, but one execution contract covers attached, detached and automation. Recommended. |

### Recommendation

File a **new Draft CIP** rather than change CIP-0016's Accepted status or
rewrite its historical release requirements. CIP-0001 assigns new identities
to successor proposals; this one proposes a new capability and references
both the accepted target and interim amendment. CIP-0022 is already allocated
to the separately filed MCP proposal. Capitalized requirements below are
proposed, not normative changes to the linked published contracts.

#### 1. Complete capability and qualification

`launch-exact/3` is a new capability family; it does not extend frozen plan
`1.0.0`, control protocol 9, or exact/2. Launcher and manager owners MUST
jointly allocate its containing control version and publish closed schemas
before activation. Merely recognizing the capability string grants nothing.

A manager advertisement has a closed per-runtime row with members:
`runtime`, `provider_build`, `adapter_build`, `protocol`, `forms`,
`doorbell_contract`, `session_record_contract`, `qualification_sha256`, and
`registration_generation`. `runtime` is one of `claude_code`, `codex_cli`,
`muse`; `protocol` is `launch-exact/3`; `forms` is exactly
`["attached","detached"]`; doorbells and session records identify the v1
contracts below. Build identities and the qualification digest MUST match
the actual registered adapter/provider and local platform. Rows lacking any
required operation are not exact/3 rows. No generic factory or another
runtime's passing result can fill a missing cell.

| Runtime | Required real path | Qualification includes |
|---|---|---|
| Claude Code | Daemon-owned PTY, exact Claude process | Attached/detached readiness, later attach, typed cold resume, acknowledged goal revision and doorbell delivery; no host-added Remote Control/context/plugins. |
| Codex | Private app-server plus managed client | Exact prepared endpoint, detach without terminal, later client attach, thread/cold resume, conflicting-config policy enforcement, text goals with native goals disabled, doorbells. |
| Muse | Registered `musepty` factory | Four snapshot XDG roots, explicit root-context fact and qualified exclusions, detach/attach, typed resume, goal adapter and doorbells; no MSP/test-factory substitute. |

Qualify each runtime/build/platform independently. Preserve CIP-0016 §1:
the **first public exact-plan release requires all three rows together**,
now including detached, record and doorbell properties. Internal partial
results remain unadvertised staging evidence. After that joint release,
advertisement and retirement are per manager/runtime/platform/build; adding
support for one runtime retires nothing for another. Relaxing the initial
joint gate needs an explicit owner decision, not an incidental partial row.
An unsupported tuple MUST refuse rather than borrowing another platform's
qualification. Record measured/required rows and every skipped/unknown row.

#### 2. Preparation and closed exact/3 payload

The same-user, same-machine registered-manager control channel remains the
boundary. The manager prepares private locations, a session id/generation,
expiry, required runtime endpoint and optional doorbell binding **before**
composition. Preparation runs no provider, resolves no profile and cannot
execute caller-provided commands. It returns the reservation and a digest
of its protected record. Attachment/doorbell intent is reservation-bound.

The proposed payload has **exactly** the following members; every member is
required, with explicit `null` only where stated. Nested records are closed.
There is no arbitrary metadata/extensions bag or runtime command tail.
Identifiers/references are nonempty opaque UTF-8 strings, at most 256 bytes,
with no control characters; hashes below are bare lowercase SHA-256 hex.
References name authenticated protected records, never bearer authorization
or paths to execute. The producer version is a nonempty release string;
its commit is a full lowercase Git OID. Unknown fields/versions, duplicate
keys, invalid UTF-8, trailing JSON and unsafe CCJ-1 numbers refuse.

| Member | Closed shape / meaning |
|---|---|
| `protocol` | Constant `launch-exact/3`. |
| `request_id` | Caller-generated idempotency id, bound to this authenticated owner and exact payload digest. |
| `producer` | `{version, commit}`: the caller build, separately checked for compatibility. |
| `registration` | `{manager_id, generation, qualification_sha256}`: matches the negotiated active runtime row. |
| `preparation` | `{reservation_id, record_sha256}`: identifies the unexpired protected preparation, binding board, owner, account, runtime, session generation, locations, endpoint and doorbell. |
| `session` | `{id, generation, board_id, owner_id, runtime, form, goal}`: `form` is `attached` or `detached`; `goal` is null or `{ref, revision}` for a protected board goal binding. |
| `inputs` | `{profile_name, profile_lock_sha256, fragment_sha256, system_modules, launch_policy_sha256, project}`: original admitted input identities. `system_modules` is a boolean; `project` is null or the closed project record in §6. |
| `process` | `{binary, argv, env, cwd, home, stdin}`: absolute binary/cwd/private home, ordered string argv, complete name-to-string environment, and `stdin` exactly `host_pty` for Claude/Muse or `none` for the Codex app-server, in either session form. Caller attachment is a separate ingress contract. No deferred environment lookup or shell expansion. |
| `snapshot` | `{manifest_sha256, descriptor_sha256, materialization_ref, materialization_sha256, projection_ref, projection_sha256}`: exact manifest bytes, launch descriptor bytes and protected Curator receipt/projection bindings. Locations come from preparation; no caller-selected alternate root. |
| `policy` | `{ref, sha256}`: exact prepared closed host tool-policy/trust record; effective policy is composed before sealing, never chosen by the daemon. |
| `restart` | `{template_ref, template_sha256}`: module-owned closed typed restart recipe, bound to the admitted runtime and snapshot. |
| `resume` | Exactly `{kind:"fresh"}` or `{kind:"resume", session_id, expected_generation, native_ref, continuation_sha256}`; the latter matches persisted provenance and typed native identity. |
| `doorbell` | Null or `{contract:"session-doorbell-v1", binding_ref, binding_sha256}` as specified in §4. |
| `content_digest` | SHA-256 of CCJ-1 of the entire payload excluding only this member, with no presentation LF. |

Generations and revisions are positive CCJ-1 safe integers. Environment names
use the existing launcher environment grammar. All nested records reached
through refs MUST themselves have jointly published closed versioned schemas;
validating their hash alone cannot accept unknown policy/projection semantics.
Their protected bytes are part of admission, not a way to move arbitrary
configuration outside the digest boundary.

Retain existing hosted §4.9 bounds and use the stricter bound where they
intersect: at most 1 MiB per launch object, depth 16, absolute paths at most
4096 bytes, and existing argv/env/literal bounds. Record refs do not waive
limits on the resolved policy/template/projection. Sealing covers all runtime
args, environment values, prepared delivery variables, snapshot and project
identities, goal, doorbell, form and policy. The private receiver transports;
**neither its client nor daemon composes**, normalizes or repairs the process.

Curator materializes and verifies the snapshot in the absent private
reservation destination using CIP-0014, including relocation and byte/mode/
entry-set checks. SHA-256 of `manifest.json` and `launch.json` includes their
canonical LF, as defined by that contract. The plan digest is different;
portable snapshot comparison never replaces exact manifest binding.
The receiver verifies Curator's receipt and its path/snapshot/preparation
binding at start, rather than inventing a second content inventory.

Admission rechecks registration/build, owner/board/account/generation,
reservation/expiry, protected references, exec guard, snapshot and effective
policy. It records provenance and all resource references durably before
consuming the reservation once and starting exactly the process. An identical
request retry returns its recorded result; the same id/reservation with changed
bytes refuses. A crash between durable admission and observed start creates
an indeterminate outcome requiring reconciliation, never permission to start
again. Endpoint bind failure records failure; a new endpoint needs a fresh
reservation and newly sealed plan, never daemon argv substitution.

#### 3. Session result, detached form and transport

Both forms return the same private durable record, constant
`session-record-exact-v1`, with exactly:
`record`, `manager_id`, `registration_generation`, `session_id`,
`session_generation`, `board_id`, `owner_id`, `runtime`, `form`,
`request_id`, `plan_sha256`, `snapshot_manifest_sha256`,
`project_composition_sha256` (null without project), `state`,
`attach_ref`, `resume_ref`, `doorbell_status`, `goal_revision` (null if none),
and `failure` (null or `{code, reason}`). Record/id/hash types follow §2;
`attach_ref`/`resume_ref` are nullable protected manager handles, not public
endpoints or tokens. `reason` is a registered diagnostic reason, not free text.
`doorbell_status` is `none`, `pending`, `delivered`, or `failed`.
The record echoes and verifies the requested identity/digests; it contains
no argv/env/credential values. `goal_revision` is the last acknowledged
revision, null until acknowledgment; it is not an echo claiming application.
A `ready` record has usable non-null attach/resume handles. `failed` carries
a registered typed failure; an untyped provider exit is recorded as stopped
without inventing a refusal code. Status reads do not mutate content or launch.

States are `admitted`, `starting`, `ready`, `stopped`, `failed`, `unknown`.
Only `ready` is launch success: admission/factory registration alone is not
readiness. A bounded start operation returns this record; indeterminate confirmation
uses `state: unknown` with the same request/session identity for authenticated
status reconciliation, not a second unversioned receipt shape. A timeout or lost response MUST NOT be treated as a safe
fresh retry. Launch success does not claim requested goals were applied:
the existing runtime acknowledgment gate runs before ordinary work.

Attached mode retains private plan stdin, terminal fd3 and length-prefixed
status fd4 with the 64 KiB bound and close-on-exec discipline. Piped/attached
payload stdin and source-side network flags retain their refusals. Detached
mode explicitly admits **no caller terminal**, fd3 or payload input;
provider stdin remains exactly the sealed host-PTY/app-server mode above.
The private control request carries the plan separately from provider input. Status/descriptor validation is form-specific; a detached request
cannot evade validation by relabeling malformed attached fds. Do not synthesize
a TTY or require an interactive caller for `werkstatt up`.

Claude/Muse still have host-owned PTYs for their provider even without an
attached client; Codex remains an app-server, not a simulated PTY process.
Successful detach or caller exit MUST NOT stop the session, drop its goal/
doorbell route or release its snapshot refs. `attach_ref` later opens the
runtime's qualified terminal/client path without recomposing. Repeated attach
changes geometry/client state only. Closing the original client is not proof
of process death. Machine hosted-default activation still requires its
upgrade-without-hangup qualification; exact/3 does not waive it.

#### 4. Doorbells without post-digest process changes

A doorbell is a **host control-plane delivery**, never a runtime hook,
executable command, environment patch or provider argument. Before preparation,
the caller selects an authorized manager-owned notification binding. Its
protected closed record binds owner, permitted destination, transport contract,
allowed event kinds, routing generation and delivery policy. Preparation binds
that record to the reserved session/runtime/generation. The exact binding
bytes are covered by `binding_sha256` and the plan; the host cannot add a
notification destination after sealing. Provider-side delivery variables, if
a qualified adapter requires any, are prepared and already in `process.env`.

`session-doorbell-v1` has event kinds `ready`, `input_required`, `stopped`,
`failed`. Each closed event carries exactly `contract`, `session_id`,
`session_generation`, `sequence`, `kind`, `plan_sha256` and
`binding_sha256`; `contract` is `session-doorbell-v1` and sequence is a
positive monotonically increasing integer for that generation. No prompt,
transcript, goal prose, env, credential, host path or raw endpoint is sent.
Only permitted events flow through the protected binding. The concrete
transport/destination record schema is a manager-owner publication, not a
repository-selected socket, executable or arbitrary URL.

An invalid/unavailable binding discovered before start refuses admission.
After start, persist event and delivery state atomically in a private outbox;
retry notification independently of provider lifetime and never relaunch to
retry a bell. Recommend bounded at-least-once delivery with recipient dedup
by session/generation/sequence: exactly-once external delivery is not claimed.
Outbox failure becomes visible `pending`/`failed` status, never a false
`delivered` or a launch rollback that kills a working session. Retain pending
outbox and session references through recovery/GC. `werkstatt up` MUST request
detached exact/3 **with a valid doorbell**, and verify a matching session record.

#### 5. Selection and per-runtime delegated retirement

Select host mode and the registered manager under the accepted front-door
rules first. Repository data cannot select a manager endpoint. Native mode
performs zero manager lookup. Registry absence/unreachability, locked settings,
explicit hosted mode, named environments and withdrawn trial behavior retain
their respective contracts; this successor does not revive older absent-backend
semantics from before the delegated amendment.

| Selected manager/runtime state | Fresh attached, detached or doorbell launch |
|---|---|
| Exact/3 row active, all required contracts match | Prepare/materialize/compose exact/3; delegated/1 is retired for this tuple. |
| No active exact/3 row, delegated/1 available and not previously retired | Use the accepted interim selection: exact/2 where the existing rule allows, delegated for detached/doorbell. Report live-home limits on delegated sessions. |
| Exact/3 row malformed, incomplete, incompatible or qualification withdrawn after retirement | Refuse; do not downgrade to delegated/1, exact/2, another manager/runtime or native. |
| No suitable route | Refuse using the specific missing capability/manager condition. |

The manager durably records retirement keyed by manager registration identity,
canonical runtime and qualified platform/build lineage; it is not merely a
client cache of the latest capability list. Once a valid complete row is
activated, all fresh launches for that tuple use exact/3. The launcher checks
the manager's authenticated retirement/registration generation at preparation
and admission; a stale row or changed generation requires renegotiation and
resealing, never retry through delegated. Removing an advertisement or upgrading
to an unqualified build does not clear retirement. A new registration cannot
silently resurrect an older one; replacement/import of retirement state must
be an explicit owner-controlled migration, not a project request.

Reject new delegated launches at the retired receiver as well as in
curator-run; a stale client cannot bypass retirement. Existing delegated
sessions may still attach/status/stop/resume through their recorded legacy
contract. Such continuation must identify the existing session and retain
legacy limits; it cannot create a new delegated session or pass itself off
as exact/3. Retirement of one runtime does not affect another runtime's state.

#### 6. Admitted project composition as snapshot input

Assume CIP-0002 supplies a protected registration, selected profile lock,
individually admitted project generation, derived composition record and
stable-home lease. Add a Curator-owned capture input for that **exact admitted
composition**, not a receiver command to copy the project or its stable home.
The closed `inputs.project` is:
`{project_ref, admitted_generation, admission_sha256, composition_sha256,
profile_lock_sha256, capture_lease_ref, capture_lease_sha256}`.
Its profile lock equals `inputs.profile_lock_sha256`. The protected composition
record binds checkout identity, adapter/release, policy ceilings, approved
item/closure digests and canonical CWD membership. The lease is authenticated
protected state, never an on-repository approval or a bearer substitute.

Acquire/revalidate the composition capture lease under CIP-0002's stable-home
rules. Curator captures the effective admitted project-plus-profile closure
through its renderer/store, including approved instructions, knowledge, skill
payloads and supported MCP/context surfaces. Unaccepted candidate files, native
project configuration, executable discovery, credentials, memory and session
state MUST NOT enter the snapshot by traversal. Include transitive approved
imports, effective policy and command-owner bindings; runtime/tool resources
need their own covered contracts, not an implicit repository PATH exception.

The profile-only frozen snapshot-v1 carrier cannot silently grow project
members. Curator must publish a successor manifest/descriptor or a separately
versioned composition receipt binding exact snapshot bytes to the full project
input. Refuse until that owning contract and verification API exist. Recheck
admission, ceilings, revocation, project/CWD identity, snapshot correspondence
and the lease at final admission, and bind them in the immutable session record.

At durable admission transfer the required lifetime roots to the session:
sealed snapshot/receipt, immutable composition and approved dependencies,
protected tool artifacts, policy and any independently required resource
leases. Release a **capture-only** stable-home lease only after this transfer,
and only when the qualified projection proves no later live-home dependency.
If a resource still requires a session lease, retain it explicitly; cannot
qualify a snapshot route with an accidental live stable-home read.
The stable home remains CIP-0002's authoring/provisioning input, not the running
session home. Native discovery exclusion still needs real adapter qualification
at startup, reload, nested reads, resume and child entry: copying approved
files alone cannot keep unapproved checkout control files inert.

#### 7. Resume, recycle, recovery and GC

Attach uses the recorded running session and never starts another provider.
Cold resume requires known stopped liveness, the exact stored snapshot baseline,
Curator-defined protected-input verification, native identity and closed restart
template. The caller may resolve fresh allowed secrets, prepare a new endpoint
and seal a **new resume plan** with the same content/composition identity and
next session generation; the host never mutates an old admitted process or
resolves credentials. The new generation and resources publish atomically with
handoff. Missing snapshot or receipt, failed reads, changed protected inputs,
wrong project/board/owner/location/runtime and unknown liveness refuse distinctly.
No fallback to current profile resolution, recapture or a fresh session.

Revocation/ceiling checks apply to new launch and cold resume, while mere attach
does not pretend to revoke already loaded context. A native resumed state is
not rehashed as initial snapshot content; verify the protected baseline and
separately enforce the qualified mutable-state/projection contract. Do not
rewrite an initial receipt to bless provider writes.

Define **session recycle** explicitly: stop and establish terminal liveness,
then either typed resume on its retained baseline or an explicitly requested
fresh session with a fresh snapshot and identity. A fresh recycle never carries
forward an old native resume identity. Define **manager recycle** separately:
retain live children/control state under the qualified upgrade protocol, or
refuse recycle while live/unknown sessions remain; never restart a daemon merely
to resolve build skew. Recover reservations, admitted/start-unknown records,
lifetime refs and doorbell outbox before allowing fresh work. PID/TTL alone
cannot prove death or justify a duplicate start.

GC runs under the owning lifecycle serialization. Roots include prepared
reservations, admitted/starting/ready/unknown sessions, stopped but resumable
session records, retained resume generations, in-flight journals, leases and
pending doorbell deliveries. Retain every referenced snapshot, manifest,
projection, composition, artifact and policy record. Client detach/exit,
profile removal and elapsed reservation TTL do not collect a live/unknown
session's roots. Release resumable generations only by explicit session forget
or a documented operator retention policy after liveness/ref checks; pending
notifications remain separately rooted or are explicitly cancelled and recorded.
Unreadable records/ref graphs fail safe, retaining uncertain resources.
Expired **unconsumed** preparations may release only their own allocations once
no admission/recovery root exists. Cleanup uses protected handles/no-follow
operations and never follows links into managed/native homes or workspaces.

#### 8. Refusals and lifecycle outcomes

Reuse existing registry codes where their meaning fits; additions below are
proposed for joint publication, not strings a consumer may emit early.
All fresh hosted refusals forbid route fallback and provider start.

| Condition | Code | Exit |
|---|---|---:|
| Unknown negotiated version/closed record contract | `session_host_protocol_unsupported` | 6 |
| Missing complete runtime/form/doorbell/record capability before retirement | `session_host_capability_missing` | 6 |
| Unsupported runtime | `session_host_provider_unsupported` | 6 |
| Invalid payload/digest, replay with changed bytes, reservation mismatch | `launch_plan_invalid` | 2 |
| Exact retirement active but peer requests delegated or tries downgrade after withdrawn qualification | Proposed `session_host_delegated_retired` | 16 |
| Registration/retirement generation changed since preparation | Proposed `session_host_registration_stale` | 6 |
| Invalid, unauthorized or unavailable doorbell binding before start | Proposed `session_host_doorbell_refused` | 16 |
| Snapshot, project admission, protected input or policy verification fails | `policy_refused` | 16 |
| Secret persistence/delivery forbidden | `secret_policy_violation` | 16 |
| Missing/unreadable/mismatched typed resume | Existing `session_resume_*` distinctions | 1 |
| Session process/start liveness cannot be established | `session_liveness_unknown` | 1 |
| Control unavailable or clean truncated response | `session_host_unavailable` | 1 |
| Malformed complete status/record, even before later truncation | `session_host_protocol_error` | 6 |

Snapshot capture keeps Curator's specific materialization diagnostics; project
admission keeps CIP-0002's owning codes. Do not collapse read failure into
absence or invent unregistered `reason` values. A post-start notification
failure is a session delivery outcome, not a typed pre-start refusal or
permission to kill/relaunch the provider. Process exit alone without typed
status cannot become a fabricated registry refusal.

## Security considerations

Same-user private authentication is not process identity, and a self-computed
digest is not authorization. Revalidate owner, registration, exec guard,
reservation and Curator bindings at start; keep plans, receipts, restart
records and outbox private. Credential values can transit only under the
existing admitted secret policy; do not persist argv/env merely to implement
resume. Persist non-secret restart recipes plus protected secret references;
new secrets require a caller-sealed resume plan. No Keychain export, receiver
login or invented credential symlink is authorized.

The threat model includes hostile project control files, same-user path
replacement, capability downgrade, request replay, lost responses and forged
notification destinations. Protected handles/no-follow checks, atomic reference
publication and strict adapters preserve the stated boundary; chmod/hashing
alone cannot constrain another process with unrestricted same-user authority.
Snapshot runtime projection/protection and CIP-0014 credential exceptions are
still activation gates. A proposed contract must refuse unsupported real native
behavior rather than rewrite native config or hide the gap behind mocks.

The host executes the complete sealed process with no ambient env, added hooks,
Remote Control, MCP channels or defaults. Policy/trust is the declared bounded
overlay; Codex `config.toml` rewriting remains forbidden and cold-resume policy
must be qualified. Muse root-context/exclusion and refresh behavior need actual
release evidence. Doorbells carry metadata only, use authorized routes and never
execute code. A forged or failed bell cannot grant launch/approval authority.

## Compatibility and migration

This proposal leaves published schemas, snapshot-v1 bytes, accepted corpora,
release pins and older capability meanings unchanged. No new wire schema is
published here. Unknown exact/3 peers refuse or keep their existing **not yet
retired** route under the interim selection rules. The signed-off delegated
route needs no trial flag; this proposal cannot reintroduce that gate.

Existing delegated sessions retain live-home provenance and their legacy attach/
resume contract. Never convert them in place or label them snapshot-isolated.
An operator may stop and deliberately create a fresh exact/3 session with a
new snapshot; native state transfer requires its own admitted migration and
is not implied by retirement. The retirement tombstone blocks fresh delegated
launches, not authorized continuation of the recorded legacy session.

Project snapshot activation waits for the first adopted CIP-0002 slice and
Curator's composition-capture/verification interface. Profile-only exact/3
qualification need not claim project isolation. An adapter cannot advertise
project-exact support merely because its profile-only row passes. Dispatcher,
remote/account execution and `task-board spawn` retain separate adoption gates.

## Specification changes

After owner review, record a Decision for exact/3, the complete detached/
doorbell lifecycle and retirement lineage. Amend local hosted §§1–7 and
CIP-0016's interim retirement pointer without changing historical acceptance.
Coordinate CIP-0014 composition capture, protected-input verification and
runtime projection with CIP-0002 approved generations and lifetime roots.

The **launcher and manager owners jointly publish** preparation, exact payload,
record/status, capability/retirement, notification binding/event and restart
schemas, limits and registry diagnostics. Curator owns any successor composition
snapshot manifest/descriptor/receipt and verification API; agents-management owns
closed hosted/restart forms. Containing control versions must be allocated
jointly rather than inferring them from `/3`. No partial publication can activate
a producer, bypass the three-runtime release gate or extend a frozen carrier.
Draft conformance vectors are listed below; CIP-0001 does not require stubs at
proposal filing. This change adds only the CIP and discovery/index pointers.

## Implementation plan

| Order | Leaf | Size | Required exit |
|---|---|---|---|
| 1 | Review owner questions; reconcile CIP-0002 candidate | S | Decisions recorded, assumed project interface resolved. |
| 2 | Joint wire/registry and Curator companion publication | M per owner | Closed contracts, byte vectors, full plan bindings and snapshot/lease verification agree before producer activation. |
| 3 | Per-runtime exact forms and host lifecycle | M per runtime | Real Claude/Codex/Muse matrix including detached, doorbells, cold resume and recovery; no host composer. |
| 4 | Selection, durable retirement and legacy continuation | M | Stale clients cannot launch delegated after retirement; native zero lookup and no fallback preserved. |
| 5 | Project snapshot capture after first CIP-0002 slice | M | Exact approved generation captured, leases transferred, unapproved native discovery excluded or refused. |
| 6 | Joint qualification, rollout and lifecycle/GC | M | All three initial rows, crash/recycle/outbox/GC controls and upgrade-without-hangup evidence; then per-runtime retirement. |

Each implementation leaf uses real entry points and disposable private homes;
no installation, provider process or service restart is authorized by filing
this Draft. Stop activation for an unsupported native mechanism decision rather
than add an alternate composer, config rewrite or live-home fallback.

## Test plan

These are **vectors and runtime tests to add**, not executed implementation
results. Every new gate pairs valid controls with the stated negative case
and a narrowing mutant that must fail for its intended reason.

| Family / claim | Positive and forbidden outcomes | Narrowing mutant |
|---|---|---|
| Closed payload and full digest | All three runtimes in both valid forms use the exact declared process; unknown/null/duplicate/trailing/oversized members refuse. Mutate each snapshot/project/form/policy/doorbell field independently. | Hash only process fields or ignore doorbell. |
| Runtime and joint qualification | Every initial runtime has attached/detached/doorbell/record/goal/resume evidence; partial internal support never advertises the public cohort. Later one-runtime withdrawal blocks that tuple without downgrading others. | Treat a registered factory or Claude row as all-runtime qualification. |
| Route retirement | Active complete exact/3 row selects exact for attached, detached and `werkstatt up`; not-yet-retired delegated still works. Stale client, missing row after retirement, wrong manager/runtime generation and runtime mismatch refuse. Legacy continuation is allowed only for its exact recorded session. | Keep delegated fallback for one detached case, clear tombstone on upgrade, or let continuation mint a fresh id. |
| Detached result | Real caller without TTY gets one durable ready session/record; later attach works. Lost response, timeout, detach and client exit never double-launch or release roots. Attached invalid fds/stdin still refuse. | Return success at admission, require fd3 for detach, or kill provider at client exit. |
| Doorbell | Authorized binding yields metadata-only events once per recipient dedup key; delayed/retried delivery does not relaunch. Wrong owner/destination/generation, unbound route, unavailable pre-start route and secret-bearing event refuse. | Add delivery vars after sealing or retry notification by starting a provider. |
| Reservation/recovery | Exact retry returns recorded outcome; expired/mismatched or changed-payload retry refuses. Crash before/after admission/start/outbox persistence preserves one-start and references; unknown liveness blocks new execution. | Treat timeout or missing PID as no prior start. |
| Runtime-specific enforcement | Real Claude PTY, Codex app-server/cold-resume policy, Muse musepty/exclusions and goals survive poisoned daemon defaults, conflicting config and repeated attach. | Merge ambient env, rewrite Codex config, or infer Muse context from layout. |
| Project capture | Approved P plus selected profile Y yields correct snapshot; candidate changes, revoked item, wrong project/CWD/profile, symlinked input or lease drift refuse. Live-home update cannot change admitted bytes. | Copy stable home wholesale or bind root generation without transitive item digests. |
| Resume/recycle | Known stopped typed resume retains baseline; explicit fresh recycle gets new identity. Missing/read-failed/mismatched receipt, changed protected content, revoked admission and unknown liveness refuse without resolve/new-session fallback. | Re-materialize current profile on a missing snapshot or rehash mutable state as original. |
| Lifetime/GC | Live, detached, resumable, indeterminate, journal and pending-outbox refs survive profile removal and expiry. Explicit forget of unreferenced terminal state permits collection; unreadable graph retains it. | Root only ready sessions, omit stopped resume refs, collect by TTL or unlink through a substituted path. |

Run through production curator-run selection/composition, Curator capture,
private control transport, receiver admission/recovery and real registered
runtime adapters. Record exact supported versions and macOS/Linux results for
each claimed tuple; unsupported/unmeasured tuples remain refused. Windows or
other platforms require separate qualification. Specification-data checks
alone do not qualify projection, credential refresh, goals or native discovery.

For this documentation delta, check template and Draft/index agreement, links,
closed-payload/record inventories and consistency with the supplied interim
retirement rule; run the repository validator and a bounded broken-link
control. Verify normative/schema/corpus/tool paths remain unchanged. No product
behavior changed, so runtime regression execution/mutants are inapplicable
here; their future acceptance requirements are listed above.

## Open questions for the operator

1. **Initial cohort and retirement lineage:** recommend retaining the joint
   first Claude/Codex/Muse release gate, then per-runtime retirement with durable
   manager-owned tombstones. Partial staging is not public support. If independent
   initial public rollout is desired, explicitly amend CIP-0016 §1; do not infer
   that amendment from per-runtime retirement alone.
2. **Wire publication:** recommend exact/3 plus the closed records above,
   with containing control versions and existing argv/env limits jointly frozen
   by launcher/manager owners. Is a major protocol revision preferred over a
   separately negotiated family? Neither may extend an older closed payload.
3. **Doorbell delivery:** recommend a prepared protected route and private
   outbox with bounded at-least-once delivery, recipient dedup and visible pending/
   failed status. Transport schema, retry horizon and cancellation/retention policy
   must be frozen by its owner; do not promise exactly-once external delivery.
4. **Project capture interface:** recommend Curator-owned capture of exact
   admitted composition, with a successor carrier or closed companion receipt
   and explicit capture-to-session lease transfer. Reconcile the absent candidate
   branch before adoption; no receiver-authored inventory or live-home shortcut.
5. **Projection, credentials and native policy:** retain CIP-0014's pending
   protection/shared-login decisions and CIP-0016's real Codex cold-resume policy
   gate. Recommend supported native APIs and separately verified state slots;
   if unavailable, refuse that capability and seek a supported mechanism decision.
6. **Legacy session retention:** recommend grandfathered typed continuation
   with visible delegated limits, fresh exact migration by explicit new session,
   and explicit forget/operator retention before deleting resumable roots. No
   automatic state import, daemon restart or retirement reset on upgrade.
