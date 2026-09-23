# Decision 0021: sessions enter through curator run and are hosted through the ax contract

## Status

Status: proposed — not adopted

Proposed 2026-09-24. DRAFT for review. The operator chose this direction
on 2026-09-24; adoption is a separate act in this repository. Filing this
proposal authorizes no implementation, workaround, normative amendment, or
landing of amended text. It builds on
[Decision 0019](0019-fragment-consumers-and-one-construction-site.md)
(proposed). If adopted, it amends
[Decision 0013](0013-execution-ownership-and-launch-plans.md) Decisions 1
and 6.4 and the launcher specification's §3 flag table and §4.6 hand-off
rule. [Decision 0018](0018-curator-run-permission-interface.md) is
unchanged.

Numbering: Decision 0020 is reserved for the inference-plane decision and
is not filed yet; 0021 is the next free number after that reservation.

Section references: "launcher §N" names `curator-agent-launcher/SPEC.md`
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
  headless `curator run` (operator decision, restated in Decision 0019).

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

### 6. Children are unchanged

Tracked non-interactive children stay with `task-board spawn` and its own
exec machinery. There is no headless `curator run` (Decision 0019).

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
  0018, and the rule that there is no headless `curator run`.

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

Filing changes no normative text, schema or vector. At adoption the
launcher specification gains one flag and one exception in §4.6. The
`ax.json` schema, its precedence and the Decision 3.2 document do not
change, so a machine without the integration behaves exactly as today,
and task-board's commands keep working as aliases.

Security:

- The machine file stays authoritative: the per-launch flag cannot step
  out of a machine's policy.
- A host never composes, so the strict MCP rule and every channel flag
  keep their single owner (Decision 0019).
- Hosted sessions inherit Decision 0018's tracked rules, so no bypass
  reaches a hosted session implicitly.
- A failed hand-off still refuses instead of falling back.
