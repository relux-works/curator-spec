# Decision 0021: sessions enter through curator run and are hosted through the ax contract

## Revision: accepted architecture-review findings (2026-10-13)

The naming-rule cross-reference distinguishes owner-published identifier categories; it grants no activation.

## Status

Status: adopted 2026-10-01 by the operator

Amendment v3 below is a **proposed documentary target** for trusted same-user
non-chat work. It explicitly scopes the original no-headless-human statements;
it is not adoption of a shipped entry or evidence of qualification. Amendments
v1/v2 and their activation/compatibility gates retain their own scope.

Proposed 2026-09-24; adopted 2026-10-01. Amendment v1 below records the
operator's D-EXECUTOR decision confirmed 2026-10-11. The amendment permits
a narrow agent-account execution mode, subject to its activation gate;
it is not evidence that the mode is implemented or qualified. This decision
builds on
[Decision 0019](0019-fragment-consumers-and-one-construction-site.md)
(proposed). Its original adoption amends
[Decision 0013](0013-execution-ownership-and-launch-plans.md) Decisions 1
and 6.4 and the launcher specification's §3 flag table and §4.6 hand-off
rule. [Decision 0018](0018-curator-run-permission-interface.md) is
unchanged.

Numbering: Decision 0020 is reserved for the inference-plane decision and
is not filed yet; 0021 is the next free number after that reservation.

Original section references: "launcher §N" names `curator-agent-launcher/SPEC.md`
`0.4.1-draft`; "ax §N" names the `ax` specification sections that
Decision 0013 cites.

## Context

A person reaches an agent through three doors today:

- `curator run <env-id>`, the launcher, for an interactive session in a
  profile's managed home. With the `ax` integration configured on the
  machine (the launcher's `ax.json`, schema `curator-run-ax-v1`, where
  the machine's file decides whenever it exists and the operator's file
  only where the machine is silent), the launcher always hands the
  composed plan to `ax start <name> --provider <id> --launch-plan - …`
  (launcher §4.6; Decision 0013 Decision 6.4). A configured integration
  is not a per-launch option: "there is no `--no-ax` flag, and bypassing
  tracking is a configuration change, not a flag" (launcher §4.6).
- task-board's own interactive commands (`task-board claude|codex` and
  their aliases), which start an orchestrator's primary session hosted by
  task-board's session daemon. The daemon builds that launch itself
  through the module's `LaunchModeManagedSession`, holds the session's
  terminal, binds the board goal, types run notices into the session and
  resumes it. task-board also offers a `--native-home` mode that starts
  the harness outside Curator.
- `task-board spawn`, for tracked non-interactive children. There is no
  headless human `curator run` (operator decision, restated in Decision
  0019). Amendment v1 adds a separate agent-account executor entry.

Two of the three doors start interactive sessions, with two builders and
two sets of flags, and a person has to know which door a task needs. The
hosted door gives an orchestrator's session what it needs (resume, run
notices, the board goal, and somewhere to deliver messages from other
agents, which requires a process that holds the session's terminal), but
only to sessions started through task-board. The Curator door already has
the right shape for hosting: one composer and a hand-off to the session
plane through `ax start --launch-plan` (Decision 0013 Decisions 1 and 3).
But no `ax` implementation has been released to receive the hand-off, and
a machine that turns the integration on keeps no way to start a single
direct session short of editing a file.

Decision 0019 moves every channel and harness flag into the
`agents-management` launch plane. A host that receives a composed plan
therefore needs no knowledge of fragments or harness flags.

## Decision

### 1. One entry point for a person

`curator run <env-id>` is the one interactive entry point for a person.
Every interactive session, a person's plain session and an orchestrator's
board session alike, starts there, in the profile's managed home, with
the plan composed once (Decision 0013 Decision 1) and spelled at one
construction site (Decision 0019).

### 2. Hosted from birth through the `ax` contract

With the `ax` integration configured, every such session is hosted from
birth by whatever implements the `ax start --launch-plan` contract of
Decision 0013 Decision 3. The launcher composes the Decision 3.2 document
and hands it over exactly as launcher §4.6 specifies; it neither knows nor
cares which implementation answers. Until an `ax` implementation ships,
task-board's session daemon implements the contract through a bridge
(open question 1).

A host receives a composed plan and never composes. It resolves no
fragment and spells no harness flag or channel (Decision 0019), and it
validates the document as the contract requires (Decision 0013 Decision
3.3 and Decision 7 item 4).

### 3. `--untracked` for one launch

The launcher gains one flag, `--untracked`, which execs the composed plan
directly for this launch (launcher §4.6's untracked shape) even though the
integration is configured:

- it is honoured when the operator's `ax.json` enables the integration and
  the machine has no `ax.json`: the operator chose tracking for
  themselves and may step out of it for one launch;
- it is a `usage` error naming the machine file when the machine's
  `ax.json` enables the integration, because whether sessions on a
  machine are tracked is machine policy, with the same precedence as
  launcher §4.6;
- it is accepted and has no effect on a machine where the integration is
  not configured, because the launch is untracked already.

A launch under `--untracked` is untracked for every rule that depends on
tracking. `--ax-profile` with it is a `usage` error and `--name` has no
effect, as on an untracked machine (launcher §3), and Decision 0018's
untracked rules apply.

The flag amends Decision 0013 Decision 6.4 and launcher §4.6, which today
offer no per-launch way out. It is named `--untracked` rather than
`--native` because "native" already names the harness-native arguments
after `--` (Decision 0013 Decision 1), a harness's native home, and the
`native` permission mode of Decision 0018.

### 4. Board behaviour follows the workspace

The board goal, run notices and resume of an orchestrator's session attach
because the host sees that the workspace it was handed
(`--workspace <cwd>`) carries a board. The launcher gains no board flag
and learns nothing about boards. `ax`'s own `--task-board` assignment path
(ax §13.2), which is mutually exclusive with `--launch-plan` (Decision
0013 Decision 3.1), is a different path and is unchanged.

### 5. Compatibility of task-board's commands

task-board's `task-board claude|codex` commands and their aliases become
thin aliases that invoke `curator run` in the project. task-board's
`--native-home` mode is withdrawn: a session outside Curator is the
harness binary itself, which the launcher never forbids (launcher §1,
"Not the only door").

### 6. Children and the agent-account exception

The original adoption leaves tracked non-interactive children with
`task-board spawn` and its own exec machinery. There is no headless human
`curator run` (Decision 0019). Amendment v1 below permits the qualified
Swarma one-shot path through the dispatcher and an agent-account
`curator-run` executor; it supplies no human headless composition command.

The separate [amendment v3 target](#amendment-v3--same-user-trusted-development-member-non-chat-target)
is the explicit proposed exception for trusted same-user development, review
and assessment, not an interpretation of v1 or the original interactive API.
Until its gates are met, the no-headless-human boundary remains operative.

### 7. Preconditions before a machine turns hosting on by default

A machine, or an operator for themselves, turns the integration on only
when:

1. replacing or upgrading the host does not hang up the sessions it
   hosts. Today, replacing task-board's session daemon ends every session
   it holds (open question 2);
2. the bridge passes a conformance check against the
   `ax start --launch-plan` contract, including the refusal cases of
   Decision 0013 Decision 7 item 4;
3. resume keeps the fidelity of Decision 0013 Decision 7: the profile pin
   is re-resolved and compared, and drift refuses by default when the
   record carries `works.relux.curator.system-modules: true` (Decision 7
   item 5).

### 8. What changes

- Decision 0013 Decision 1: the sentence "on a machine with the `ax`
  integration configured it hands the composed plan to
  `ax start --launch-plan`" gains the `--untracked` exception of
  Decision 3.
- Decision 0013 Decision 6.4 and launcher §4.6: a configured integration
  admits the per-launch `--untracked` of Decision 3 when the operator's
  file enables it, and the machine file stays authoritative. "There is
  no `--no-ax` flag" becomes "no flag overrides the machine file".
- Launcher §3 gains the `--untracked` row.
- Unchanged: the `ax.json` schema and precedence, the Decision 3.2
  document and its extension keys, `ax_handoff_failed` with no untracked
  fallback (a failed hand-off never turns into `--untracked`), Decision
  0018, and the rule that there is no headless human `curator run`.
  Amendment v1 is the sole agent-account exception to that scope.

The no-headless-human clauses in Context, Decision 6 and this original change
list are explicitly subject to the distinct proposed amendment v3 below. This
cross-reference adds no native-argument shortcut and does not change the
agent-account exception or local-hosted amendment v2.

## Amendment v1 — agent-account one-shot execution (2026-10-11)

### Authority and scope

D-EXECUTOR selects the narrow `curator-run` executor, with the rails
confirmed by the operator on 2026-10-11. It resolves the amendment and
first-consumer questions in contract-table N6/P1/C9 and audit
A09.1/A09.6/A09.10/A10.9. This is amendment v1 of this decision, not a
launcher release number or a new wire schema. The original interactive
human mode, including composition, `ax` handoff and `--untracked` policy,
is unchanged.

The documentary baseline is the
[contract table at `177cb554`](https://github.com/relux-works/curator/blob/177cb55417fc1d0c1630842c07aca714ebb3db9e/.research/261010_platform-contract-table.md)
and [audit R-LR1 at `48789217`](https://github.com/relux-works/curator/blob/48789217c815ebc45edb7d1d0c282879c83450bf/.research/261010_platform-docs-audit.md).
D-EXECUTOR, D-PATH and D-WIRE-NAMES in the supplied owner decisions of
2026-10-10/11 override the table's corresponding open questions; the
other open questions below retain their explicit options.

The accepted one-shot path is local and headless in dispatcher v0.
`curator-run` executes under `worker-<label>`, distinct from the root
`swarma-user-launcher`. Under the agent account it never composes a plan,
resolves a profile or fragment, repairs a home, or selects harness flags.
It only verifies and executes an immutable plan composed on the caller
side. A dedicated entry such as `curator-run exec --plan-fd N` separates
this intake from the human composition command; its exact CLI and plan
version belong to the launcher specification. A verification failure
never falls back to composition or profile resolution.

One launch library is shared with `swarma-session-runner`, so verification
and execution have one implementation contract. This narrowly amends the
launcher's original single-module/no-shared-library boundary; it does
not give either executor profile-composition or session-service authority.
A separate minimal executor binary remains a later option, not the
selected first consumer.

### Launch, transport and evidence owners

The versioned one-shot intake amendment of
[`curator-agent-launcher/SPEC.md`](https://github.com/relux-works/curator-agent-launcher/blob/main/SPEC.md)
owns the closed plan grammar, transport, credential intake, signals,
exit propagation, executor receipts and typed refusals. Its current
interactive §§1, 3, 4.4–4.6, 6 and 8 are the boundaries to amend, not an
already-published one-shot contract. Decision 0013's interactive `ax`
request is not implicitly the agent-account input schema.

The launcher amendment must preserve these contract-table values:

| Boundary | Required contract and owner |
|---|---|
| Caller and dispatcher | The caller composes once; the dispatcher admits, provisions, tracks and cleans up. Account generation, dispatcher execution ID, board run/attempt ID and broker correlation-only `launch_id` remain distinct (I2/I3). The plan binds its digest and resolved launch-scoped PATH; D-PATH orders the protected launch tool directory, the user's admitted base PATH in its existing order, then one protected manager dispatcher directory. A repository `.agents/bin` is never executed in a managed launch. |
| Privileged launcher | `swarma-user-launcher` validates the active owned generation, approved executor path/digest and home, resets descriptors/environment, and writes the atomic start receipt before clearing groups, setting GID/UID and exec. An existing receipt refuses a second start (P2). |
| Plan transport | FD3 carries only the immutable plan; there is no inherited broker connection. The caller prepares the value before the privilege boundary; the agent executor verifies it without recomposition. The launcher spec must publish the approved FD carrier and digest/validation rules (L2/P1/P2). |
| Message bounds | Decoded plan 48 KiB, base64 plan 64 KiB; privileged launcher request 80 KiB/5 s; dispatcher v0 stdin request 96 KiB/5 s, v1 frame 128 KiB; broker frame 64 KiB. These are separate bounds. Refuse the launch path's smallest applicable bound before provisioning (L1/L2). |
| Credential intake | `curator-run` under the agent account is the first broker consumer (D-EXECUTOR/C9). The board runner and session host embed no broker client; they ask the dispatcher, which launches through `curator-run`. The executor connects as the agent principal and obtains only the credential admitted by its broker binding; UID/label or `launch_id` alone is no authority (I2/I3). |
| Network and provider channel | The agent-account `curator-run` executor has no network except the broker. This rail applies to the executor; the launched harness has its separately admitted egress policy. Slice 0 requires cross-user peer/binding proof and one protected Claude launch: explicitly enrolled setup-token, `CLAUDE_CODE_OAUTH_TOKEN` at harness exec, no credential file, native fallback or refresh (C3/C9). Codex and networking work are later qualified slices, not first-slice capabilities. |
| Receipts, signals and exit | The root start receipt is privilege-boundary evidence, not proof that the harness initialized or became ready. The launcher spec must define executor outcome receipts, signal ownership and exit propagation and distinguish refusal, failed start and observed exit. Dispatcher/helper `exec.stop` checks owned generation/execution and receipt/process identity, then TERM/KILL and confirmed absence; no sudo signal relay or PID-only proof (P2/P6). |
| Refusals | The launcher spec must publish typed refusals for invalid/unsupported or oversized plan intake, digest/principal/binding mismatch, unreadable evidence, disallowed executor and unavailable/unqualified credential channel. Read failure is never absence; no refusal admits native credentials, recomposition, or untracked fallback. Exact new codes and receipt fields are not invented here. |

### Activation gate and remaining owner questions

The mode stays disabled until the launcher publishes its versioned
one-shot intake contract and qualification establishes the plan/FD
boundary, shared-library executor behavior, broker peer/binding checks,
protected first-provider launch, signal/exit/receipt behavior and the
refusal paths above. Qualification must identify the supported releases
and measured scope; a decision, draft, fixture-only pass or privileged
start receipt alone is insufficient. These requirements are an activation
gate, not a claim that qualification has run. Interactive launches keep
their existing contract while the gate is closed.

The supplied owner decisions do not settle the following later contracts:

1. **Helper v2 signed-request grammar (W3).** Adopt an explicit
   component-specific signed format, or a versioned shared adapter?
   v0/v1 sudo-caller role checks do not imply v2 grant verification.
2. **SH2 launch ticket and host role (I4).** Jointly version the ticket
   signature/host-role schema and activate that gate, or leave the SH2
   backend disabled? The dispatcher issues the ticket and the helper
   redeems it once for the authenticated host; account generation,
   execution ID, ticket epoch and controller epoch stay distinct.
3. **Codex personal-plan lane (C4).** Adopt a single authentication owner
   with named supported-release evidence, or defer the lane? Its target
   is external-token delivery into a per-session app-server, with no
   launch `auth.json` or broker-mode `codex exec`; the one-shot decision
   supplies no evidence that this later channel is qualified.

D-WIRE-NAMES resolves the naming rule: versioned platform wire identifiers
carry the repository name, `swarma-<component> <object>/<n>`. This sentence is scoped by the [disposition's D-WIRE-NAMES scope sentence](../cips/platform-contract-disposition.md#wire-naming-rule), which distinguishes signing domains, wire kind discriminators, transport/schema labels and provisional design labels. Nothing has
shipped, so no migration is needed. That rule does not publish W3's
canonical signed bytes or I4's closed schema; neither open gate is
silently enabled by a name. These follow-on questions do not reopen
D-EXECUTOR or admit their capabilities into slice 0.

## Consequences

- A person learns one command. An orchestrator's session and a plain
  session differ only in the workspace they start in.
- Primary sessions have one builder instead of two. The plan that
  task-board's daemon used to build is now composed by the launcher and
  spelled by the module, so an orchestrator's session sees the same MCP
  set as any other launch of the profile.
- Every hosted session can receive run notices and messages from other
  agents, because the host holds its terminal from birth.
- Hosted sessions are tracked launches under Decision 0018 item 5.
  Silence resolves `native`, and an effective `yolo` is refused
  (`permission_mode_tracked_unsupported`) until a versioned `ax`
  capability admits a permission posture. An operator who needs the
  untracked posture for one session uses `--untracked` where the machine
  allows it.
- task-board's daemon loses its own launch path for primary sessions and
  gains a bridge. The module's managed-session mode is no longer needed
  for them.
- `ax_handoff_failed` still never falls back. A broken host stays
  visible, and stepping out of hosting is an explicit `--untracked`.

## Alternatives considered

- **Keep three doors.** Rejected: two builders of interactive sessions
  with two sets of flags, a choice the person has to make for every task,
  and hosting only for sessions started through task-board.
- **Name the flag `--native`.** Rejected: "native" already names the
  arguments after `--`, a harness's native home, and a permission mode of
  Decision 0018. One word with four meanings on one command line invites
  mistakes.
- **No per-launch opt-out.** This keeps launcher §4.6 as written, where
  stepping out of tracking is a configuration change. It is kept for a
  machine file, where tracking is policy. Rejected for an operator's own
  file: a person who chose hosting for themselves would have to edit and
  restore a file for a single direct session, for example while the host
  is being upgraded or when the session needs the untracked permission
  posture.
- **`curator-run` hosts sessions itself.** Rejected: the launcher holds
  no session state ("Fire is the launcher's verb; manage is `ax`'s",
  launcher §1), and the four planes of
  [Decision 0010](0010-agent-environment-profiles.md) put session
  management in the session plane.

## Open questions

1. **Bridge shape.** Either an `ax` shim executable over task-board's
   session daemon, which leaves the launcher unchanged because it invokes
   `ax` as today, or the daemon exposing `ax start` directly. Also open:
   how the bridge reports Structured Errors, and how it is retired when an
   `ax` implementation ships.
2. **Upgrade without hang-up.** How a host is replaced without ending the
   sessions it holds: handing the sessions' terminals to the new process,
   a separate host process per session, or draining before replacement.
3. **Session names.** Every interactive session is now named at birth.
   Do same-second collisions (Decision 0013 open question 1) need the
   counter now?
4. **Board discovery by other hosts.** How a host that is not task-board's
   daemon learns that a workspace carries a board, and whether that
   belongs to an `ax` extension or to a host plug-in.
5. **Notices from other sources.** Whether messages that do not come from
   the board, such as coordination messages between orchestrators, share
   the notice path and its rules.
6. **Diagnostics.** The exact error for `--untracked` refused by a
   machine file, and whether the launcher records an `--untracked` launch
   on a configured machine anywhere beyond its stderr provenance.

## Compatibility and security impact

The original adoption requires the launcher specification to gain one
flag and one exception in §4.6. The `ax.json` schema, its precedence and
the Decision 3.2 document do not
change, so a machine without the integration behaves exactly as today,
and task-board's commands keep working as aliases. Amendment v1 adds only
the gated agent-account one-shot contract above; publication and
qualification of its launcher intake remain prerequisites to activation.

Security:

- The machine file stays authoritative: the per-launch flag cannot step
  out of a machine's policy.
- A host never composes, so the strict MCP rule and every channel flag
  keep their single owner (Decision 0019).
- Hosted sessions inherit Decision 0018's tracked rules, so no bypass
  reaches a hosted session implicitly.
- A failed hand-off still refuses instead of falling back.


## Amendment v2 — local hosted launches (2026-10-15)

Status: adopted by owner decision 2026-10-15 through
[CIP-0016](../cips/CIP-0016-local-hosted-launches.md).

### Context and decision

Waiting for the dispatcher delays local hosted entry through `curator-run`.
Live managed homes can be rewritten by repair, profile switching and skill
sync. The adopted [local hosted contract](../protocol/local-hosted-launches.md)
freezes the curator-spec portion of CIP-0016 leaf 1: explicit same-user local
selection, preparation before composition, Curator-owned snapshots, caller
composition, exact daemon execution, private provenance, typed resume and
acknowledged goals. Claude Code, Codex and Muse gate the first supported
release together. Snapshot verification and credential exceptions stay with
Curator; the host never maintains its own home-content list.

For this local mode, this amendment supersedes original decisions 1, 2, 5
and 7 only where they conflict: the running session uses a private snapshot,
not the live managed home; hosting uses the selected board's authenticated
`tb-sessiond` transport without waiting for `ax` or the dispatcher; legacy
`task-board claude|codex` commands remain supported and wrapper conversion is
recommended rather than required. Existing operator hosted defaults need an
explicit backend migration; machine hosted defaults retain the
upgrade-without-hangup gate. Explicit `--hosted` does not enable defaults.
Native and legacy `ax` routes, host precedence/locks and conflict refusals
retain their launcher meanings. Restart uses the persisted session snapshot,
receipt and Curator-defined protected inputs rather than re-resolving a live
profile. There is no native fallback after a hosted refusal.

Amendment v1 and launcher §10 dispatcher/agent-account activation gates remain
unchanged. `task-board spawn` remains separate, including its snapshot gap.
The four CIP publication questions remain open: wire family/version and
capabilities/preparation schema, backend configuration, supported Codex policy
layering and Curator-owned credential exceptions. Adoption publishes no answer
by implication, no successor schema and no operational capability.

### Alternatives

Waiting for dispatcher violates the adopted local-entry priority. Routing
through legacy wrappers recomposes instead of executing the sealed process.
Reusing a live home or selecting files in the receiver duplicates Curator
ownership and fails snapshot isolation. A complete prepared Codex app-server
plan is selected over receiver conversion or an unqualified stdio redesign.

### Compatibility and security impact

No released schema, wire identifier or old-route semantics is extended.
The successor contract and real adapters must be published and qualified
before activation; old/new compatibility remains a required qualification.
Receiver failure never becomes native or remote execution. The bearer still
authorizes same-user processes and confers no cross-account isolation.
Digests prove byte consistency, not authorship. Endpoint handover and
same-user validation/use races remain explicit residuals. Secret-safe
persistence and cleanup must preserve native/managed homes. Neither launcher
nor receiver rewrites runtime-owned Codex config, even in a private snapshot;
cold-resume policy enforcement is an activation gate with a stop rule.

## Amendment v3 — same-user trusted development-member non-chat target

Documentary amendment revision: **v3**, corresponding to launcher documentary
**same-user-nonchat-contract/1**. Status: **target proposal; not implemented,
qualified or activated**. This is neither a Curator release/wire version nor
source acceptance. Paired exact-head source review and each owner's publication
remain prerequisites, followed by separate implementation/qualification grants.

### Explicit exception and retained boundaries

The original interactive/no-headless-human scope gains a distinct gated target
for trusted development, independent source review and separate recipient
assessment under the already admitted **current user**. This is an explicit
scope amendment, not authority inferred from non-TTY input, native arguments,
permission defaults, existing `task-board` children or local-hosted v2. No
current command, flag, parser, fragment or manager schema is extended here.
The eventual adapter belongs to the canonical Curator/launcher route, not a
third wrapper or ad hoc execution entry.

The owning [launcher contract/1](https://github.com/relux-works/curator-agent-launcher/blob/968d8576f3de8d3001970d09409fc98c99d60ab1/docs/same-user-nonchat-contract.md)
contains the single admission/execution/result target and qualification PLAN.
This amendment fixes Curator's boundary to that document revision; it does not
create a second wire/result contract. A matched source change must preserve
both owners' exact reviewed heads and their separate landing custody.

The follow-up [executor protocol source revision 2](https://github.com/relux-works/curator-agent-launcher/blob/301b2dbf38c04960273a022e9353f755cc3967dc/docs/same-user-executor-wire.md)
and its closed schema/inert manual cases concretize contract/1. The proposed
canonical entry is the same binary's `curator-run member`, with explicit
controller-owned descriptors, exact-byte frozen input, closed intake/result/error/
replay records and durable admission/start/result/cancellation/reconciliation
barriers. This is a new source allocation, not a released CLI/parser/native flag
or an operational alias for interactive execution. There is one launcher-owned
wire, not a parallel Curator schema. Its proposed transport exits never stand in
for observed native outcome, task acceptance or complete cleanup.

The [Stage2 bounded-decoder source clarification](https://github.com/relux-works/curator-agent-launcher/blob/25349bcdb9d4cb63e68ed9a41ed3639934bb845a/docs/same-user-executor-wire.md#2-bytes-schema-and-limits)
is a separate launcher source candidate. The Stage1 baseline at
`301b2dbf38c04960273a022e9353f755cc3967dc` remains frozen; neither this locator
nor bounded decoding establishes admission, a supported tuple, qualification
or activation.

Amendments v1/v2 remain intact. Launcher SPEC §10 continues as the separately
protected dispatcher/worker-account/broker target, unimplemented/unqualified
under its own intake/FD/privilege/network/provider/lifecycle/activation gates.
Same-user work is not its implementation, fallback or qualification. The v2
snapshot/hosted decision does not already admit this fresh non-chat invocation.

### Curator compatibility, effective configuration and preservation

The launcher consumes only a Curator/runtime-owner-supported exact tuple:
tool/source identities, profile source closure and config/lock digests, actual
runtime/model/effort, home/auth provenance and any required manager compatibility.
Explicit compatible manager absence is different from an unavailable required
manager; no fallback is admitted. Core retains fragment/manager/native-origin
and managed-home compatibility ownership. The launcher owns execution/result;
the runtime owner owns native context, discovery and provider semantics.

Core's existing non-repair profile resolution verifies recorded managed state;
release detection can still probe a runtime. No live resolve/probe is admitted
by this source unit, and profile/fragment identity cannot attest full effective
discovery or fresh history. [Decision0019](0019-fragment-consumers-and-one-construction-site.md)
retains agents-management as the single argv/channel constructor, without process
launch or profile-resolution ownership. The launcher cannot shell around the
interactive forced-repair route or introduce a competing composer.

[Decision0029](0029-provisioning-origin.md) and the adopted
[provisioning-origin/1](../protocol/provisioning-origin.md) retain exclusive local
origin authority and recoverable whole-home lifecycle. The private sidecar,
paths and credentials never enter member intake objects, fragments, portable
snapshots or public evidence. Opaque verification digests neither transfer that
authority nor manufacture a source-owned verification API. Missing/invalid origin,
ambient HOME/selector/link reconstruction or incomplete origin implementation
refuses; no member-specific fallback/adoption/repair is created. Its separate
source implementation, lifecycle/contribution custody and native qualification
remain dependencies, not results of this documentary amendment.

Actual inspected Curator producer at `933d2785e2544edd5b9b1bc345dbf41674e8c4aa`
emits ordinary v2 and managed Muse v4 fragments; publication of later carrier
shapes alone does not enable emission/support. Source closure comes from verified
lock/store, never extra fragment fields. No shipped member compatibility receipt
or positive required-manager/compatible-absence tuple is supplied. The proposed
launcher catalog begins empty and matches exact owner-published tuple bytes;
caller metadata or a digest alone cannot populate it or prove actual compatibility.

Each bounded assignment consumes frozen declared instructions/artifacts in a
**NEW native context**, never a parent/producer/resumed conversation, transcript,
auto-loaded prior memory or seeded continuity. A stable accountable member is
controller-side metadata, not persistent native conversation state or child
chat identity. Independent source review and frozen-input recipient assessment
are separate assignments/consumers/results; one is not evidence of the other.
The source author/reviewer threads do not qualify this target property.

The initial target subset permits only declared static instructions/settings,
inert artifacts and explicitly admitted tools. It excludes executable startup
hooks, messaging/board integration, arbitrary MCP, ambient skills/plugins and
presence instructions. Effective configuration/discovery must be enumerated,
excluded or pinned across user/system/workspace/nested/home surfaces and inherited
handles, not just scrubbed environment. Unknown/contaminated or unsupported
config refuses; excluded profile content is not silently stripped. Candidate
control files stay inert outside discovery; discovery-capable entry requires
a qualified strict-context adapter. Digest/profile identity alone does not
prove exclusion or authority.

The child has no a2a identity/chat registration, parent messaging credentials,
hooks/binding or board presence. The existing controller submits and receives
through its admitted route; no parent identity is lent to the child. Same-user
separation is cooperative and supplies no hostile-same-UID, cross-account,
broker/service-credential or untrusted-workplace isolation/authority.

Native/managed homes, source/user config, credentials, hooks, existing consumers,
identities and processes remain preserved. Only declared task-owned scratch is
materialized. Existing authentication/policy/home refusals remain effective;
no credential copying, login repair, policy relaxation or runtime-config rewrite
is authorized to make a tuple pass. If the runtime cannot provide fresh-context,
effective-config or cleanup evidence without forbidden effects, that tuple
remains refused with a recorded owner-resolvable gap.

### Intake, result and activation custody

Launcher contract/1 owns frozen exact-byte intake, proposed bounded transport,
actual invocation/native outcomes, result validation, replay/conflict behavior
and cleanup evidence. No published CLI/wire member, numeric refusal exit or
provider capability is inferred from its documentary record concepts/limits.
Admission, actual start/failed start, native exit/signal, cancellation,
missing/partial/unknown result and cleanup remain distinct; exit zero, argv,
fragment or build evidence is neither task acceptance nor clean-stop proof.
Failure preserves unrelated state and existing records, starts no weaker child
and never treats timeout/process disappearance as confirmed absence.

Qualification is a **PLAN only**: pair valid controls with stale/incompatible
tuples, wrong/missing input, inherited history/effective discovery/presence,
duplicate/conflicting invocation/result, abnormal native outcome and interrupted
cleanup. Each row asserts exact state/effect preservation and bounded cleanup.
Isolated fixture sensitivity is not real native qualification; actual supported
tuples require separately commissioned native witnesses. No such run is admitted
or claimed by this amendment.

Source acceptance/publication, bounded implementation admission, fixture/native
qualification, host adoption and independent task acceptance are separate gates.
The concrete entry/handle/schema/refusal source candidate above requires paired
exact-head acceptance and each source owner's publication. It establishes no
supported native tuple: runtime strict discovery/fresh creation, exact model/
effort, local home/auth/origin, non-repair preparation/probe policy, compatible
composition and recoverable complete-scope semantics still need owning inputs.
Process-group wait, root exit or PID disappearance never prove escaped-descendant
absence or crash survival. Unknown start/native/result/cleanup remains uncertain,
blocks replacement/consumption and preserves original evidence. Stage2 source
implementation requires accepted published Stage1 plus its separately recorded
scoped assignment; native qualification/adoption requires a further concrete
tuple, finite effect budgets and custodian admission. Core retains
Curator-spec default-branch landing; launcher retains its own source landing.
No installation, authentication change, host grant, runtime operation or worker
wake/lifecycle implementation follows from this source proposal.
