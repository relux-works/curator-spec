# Decision 0019: fragment consumers and one construction site

## Status

Status: proposed — not adopted

Proposed 2026-09-24. DRAFT for review. The operator chose this direction
for the launch-profile work on 2026-09-23; adoption is a separate act in
this repository. Filing this proposal authorizes no implementation,
workaround, normative amendment, or landing of amended text. If adopted,
it amends [Decision 0013](0013-execution-ownership-and-launch-plans.md)
Decisions 1, 5, 6.3 and 6.5 and the `curator run` paragraph of
[environments](../protocol/environments.md) §10.1.

Revised 2026-09-24 to align with
[Decision 0021](0021-sessions-enter-through-curator-run.md) (proposed):
primary sessions enter through `curator run`, so
task-board's session daemon hosts a composed plan and consumes no
fragment. task-board remains a fragment consumer for its tracked
children only.

## Context

Decision 0013 Decision 1 fixes four planes and one composer: Curator
resolves the launch environment fragment, `agents-management` builds an
interactive plan value, `curator-run` composes exactly one launch plan
from that plan, the fragment's channels and the native arguments, and
`ax` records and launches. Decision 5 keeps the interactive plan free of
channel flags: `BuildPlan` refuses a non-empty `Composition` in
`LaunchModeInteractive`, because "two components spelling MCP flags is
the M2 class of defect". Decision 6.3 has the launcher append the
system-prompt and MCP channel flags itself, and environments §10.1
restates that the launcher is the single composer of a launch.

Another process now needs the same fragment. task-board launches
tracked child agents in exec mode, with a process group, deadlines, an
abort fence, a run manifest, exit classification, limit observation,
retries, worktrees and goal directives. The children must run in the
profile's managed home with the profile's MCP set, so task-board must
apply the fragment's channels. The operator decided that there is no
headless `curator run`: tracked children stay with their process owner.
task-board's session daemon today builds board-bound primary sessions
itself through the module's `LaunchModeManagedSession`, which would make
it a third consumer; Decision 0021 instead routes primary sessions
through `curator run` and leaves the daemon hosting a plan that is
already composed.

Read literally, the current text leaves task-board to spell MCP and
system-prompt flags beside the launcher, and its session daemon a third
time for as long as it builds primary sessions. Separate spellings of
`--mcp-config <file> --strict-mcp-config` or `-p curator-mcp` drift, and
one forgotten strictness flag lets the machine's own MCP servers leak
into a child: the M2 class again, now across repositories.

The module already owns each harness's argv, model and effort spelling
(Decision 0013 Rejected alternatives: a second flag-spelling site is "the
drift the module's single-construction-site invariant exists to
prevent"), and [Decision 0018](0018-curator-run-permission-interface.md)
puts the permission mode there as a `LaunchRequest` member. The context
channels are the only launch flags still spelled outside it.

## Decision

### 1. One construction site

Every argv element and context channel of a harness launch is spelled in
one place: the `agents-management` launch plane. `LaunchRequest` gains a
typed context member that carries the fragment's channel descriptors, not
the fragment itself:

- the managed home (already `LaunchRequest.Home`);
- the MCP channel: the descriptor from the fragment's `mcp` section and
  its path;
- the system-prompt channel: the fragment's `system_prompt` descriptors,
  present only when the consumer's opt-in engages them;
- the variable-kind channel, for a tool that takes its configuration
  through an environment variable.

The system plugin of each harness spells these channels in every launch
mode (interactive and exec, and managed session while a consumer still
uses it), together with model, effort and permission mode, and resolves
conflicts between them in one place. For example, a tool that accepts a
single profile flag gives it to the MCP channel and receives a custom
model provider as configuration overrides instead. The order rule of
Decision 0013 Decision 6.3 moves with the spelling: channel flags
precede the native arguments, which remain the consumer's to append
verbatim after the plan's argv.

### 2. Several fragment consumers

A fragment consumer resolves the fragment with `curator env resolve …
--format json`, maps its channel fields one to one into the context
member, and owns everything else about its process. The consumers are:

- `curator-run`, the human's interactive door, for untracked execution
  and for the `ax start --launch-plan` handoff of Decision 0013
  Decision 3, including the hand-off of primary sessions to a session
  host under Decision 0021;
- task-board, for tracked child agents in exec mode.

A session host, task-board's session daemon included, receives a
composed plan and is not a fragment consumer: it resolves no fragment
and spells no channel. A consumer never spells a channel or a harness
flag. Each consumer's
fragment parser keeps running the fragment conformance vectors, as the
current text requires.

### 3. What changes in Decision 0013

- Decision 1: "one composer" becomes "one construction site, several
  fragment consumers". `agents-management` learns the fragment's channel
  descriptor vocabulary, never how a fragment is resolved, locked or
  discovered.
- Decision 5: `LaunchModeInteractive` accepts the typed context member.
  The raw `Composition` prefix stays refused in that mode; the typed
  member is the only way a channel reaches the plan.
- Decisions 6.3 and 6.5: the launcher appends only the native arguments
  after the plan's argv; the channel flags come from the plan. The
  environment and `env_names` rules of Decision 6.3 stay with the
  consumer until open question 2 is settled.
- Unchanged: fragment resolution and its schemas, the `ax` plan contract
  and its extension keys (set by the consumer that resolved the
  fragment), the permission-mode mapping of Decision 0018, and the
  decision that there is no headless `curator run`.

## Consequences

- A strictness flag such as `--strict-mcp-config` has one owner and one
  set of per-harness golden tests; no consumer can forget it.
- `curator-run` and task-board build identical channel flags from the
  same fragment, so an interactive launch, a hosted primary session
  (Decision 0021) and a tracked child of one profile see the same MCP
  set.
- Each consumer can assert in its own test suite that no harness flag is
  spelled outside the module, extending the guard task-board already
  keeps for model, effort and argv.
- `agents-management` grows descriptor types, per-plugin spelling,
  conflict rules and golden tests. It still starts no process and imports
  nothing from Curator.
- A new tool's channel lands once, in its plugin, instead of in every
  consumer.

## Alternatives considered

- **Each process owner spells its own channels.** This is what the
  current text implies once task-board (and, before Decision 0021, its
  session daemon) consumes fragments. Rejected: separate spellings of
  one channel drift, and a
  missing strictness flag leaks machine MCP servers into a child (the M2
  class of Decision 0013).
- **`curator-run` as the only launcher, headless children included.**
  Tracked children would start through the launcher binary. Rejected: the
  operator decided there is no headless `curator run`. Tracked children
  need exec machinery (process groups, abort fences, run manifests, exit
  classification, limit observation, retries, worktrees, goal directives)
  that belongs to their process owner; moving it into the launcher, or
  splitting it between two binaries, costs more than sharing one
  construction site.
- **A composition library extracted from the launcher.** Every consumer
  would call a shared composition package. Not chosen: it would be a
  second place that knows harness flags beside the module, which already
  owns each harness's argv, and the channel flags belong next to the
  flags they conflict with.

## Open questions

1. **Shape of the context member.** Typed per-channel structures that
   mirror the fragment's descriptors, or the fragment's `mcp` and
   `system_prompt` sections passed verbatim with a revision tag; and how
   the member follows fragment revisions (`launch-env-fragment-v1`,
   `launch-env-fragment-v2`).
2. **Environment composition.** Whether the fragment `env`, the
   variable-kind channel and the `env_names` bound of Decision 0013
   Decision 6.3 move into the module with the flags or stay with each
   consumer.
3. **System-prompt opt-in.** Where the opt-in lives (launcher defaults,
   task-board policy, a request flag) once the module spells the channel.
4. **Plane ignorance.** Whether a descriptor-only contract keeps
   `agents-management` within the ignorance rule of Decision 0010
   Decision 10, or that decision needs an explicit exception.
5. **Unknown descriptors.** A module older than the fragment must refuse
   an unknown channel kind instead of dropping it; the refusal class and
   where it surfaces are open.
6. **Conformance.** Per-harness golden vectors for channel spelling in
   the module, fragment-parser vectors in each consumer, and where the
   vectors live.
7. **Rollout.** The module version that introduces the member, the
   minimum each consumer requires, and the order of the launcher
   specification, environments text and consumer changes.

## Compatibility and security impact

Filing changes no normative text, schema or vector. At adoption the
module change is additive: a request without the context member builds
the same plan as today. The fragment schemas do not change; the launcher
specification and the environments §10.1 `curator run` paragraph need a
text revision. Security improves by construction: the strict MCP rule
and every other channel flag are enforced and tested in one place, and
the unknown-descriptor refusal of open question 5 keeps a newer fragment
from silently losing a channel on an older module.
