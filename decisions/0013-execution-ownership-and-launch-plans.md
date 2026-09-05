# Decision 0013: execution ownership and launch plans

## Status

Proposed 2026-09-05. Draft for review; nothing here is normative yet.

Numbering: Decision 0011 is reserved by the swift-driver draft
(`decisions/0011-swift-driver-pair.md` on the unlanded branch
`draft/TASK-260728-1yhuqi-swift-driver`, head `604d525`); Decision 0012
landed on `main` (`b4f29cd`) skipping 0011; 0013 is the next free number.
This is the decision Decision 0012's Context defers to — "the next free
number after reconciliation with the swift-driver draft's 0011" — and it
records the pre-implementation review's M1 resolution (review v3,
STORY-260901-zddtn8) together with M2, M7, M8, M15, and M16.

Acceptance authorizes four separately tracked changes: the
`curator-agent-launcher` specification at `0.2.0-draft` (Decision 6); the
`LaunchModeInteractive` addition to `agents-management` (Decision 5); a
revision of `agent-session-manager-spec` pull request #1
(`draft/curator-environment-integration`, head `d7075e1`) carrying the
`ax` changes of Decisions 3, 4, and 7 — that PR is delivered to the `ax`
maintainer and is never merged by this project; and the `curator run` rows
of the `protocol/environments.md` revision 1.1 batch, whose content
Decision 6 fixes. It changes nothing in the frozen `protocol/core.md` and
no `protocol/environments.md` text itself.

Section references: "environments §N" names `protocol/environments.md`
revision 1 as landed at `b4f29cd`; "ax §N" names
`agent-session-manager-spec/SPEC.md` v0.5.0 (`28bf96d`), and "PR #1"
names its diff at `d7075e1`; "launcher §N" names
`curator-agent-launcher/SPEC.md` `0.1.2-draft` (`6de42d8`);
"registry §N" names `protocol/registry.md`; Go identifiers name
`skill-agents-management` at `91bf945` (main; the one commit past `944c7b4`
resolves a declared model alias before argv and changes no `LaunchMode`,
`Lineup`, `StdinPayload`, or `EffortTransport` identifier).

## Context

Decision 0010 Decision 6 fixed the four planes — context (Curator), spawn
(`agents-management`), session (`ax`), execution (the launcher) — and
Decision 10 fixed that every contract between them is a CLI invocation
plus a closed object. The launcher specification `0.1.2-draft` wrote the
execution plane against that boundary: obtain a plan from the spawn plane
as a value, obtain a fragment from Curator, merge, and either exec or
"route the composed launch through `ax`'s instrumentation" (launcher
§4.5).

The pre-implementation review verified that the routing sentence names an
operation that does not exist. `ax`'s only session-creating surface is
`ax start NAME --provider ID [--profile standard|yolo] [--workspace PATH]`
(ax §14.1): no argv, no environment literal, no extension, no model, no
effort. The Launch Plan is built inside `ax` at creation (ax §13.1 step
4, "Call provider `launch` and validate its argv/env-name plan") and
provider `launch` must receive exactly the record's plan (ax §7.5). PR #1
wrote "the launcher merges the `env` variables … into the Launch Plan and
resulting `SpawnPlan` `env_literals` map" — an actor with no interface.
Two more facts compound it. `agents-management`'s closed `LaunchMode` set
is `LaunchModeExec`, `LaunchModeDryRun`, `LaunchModeManagedSession`
(`pkg/agentic/system.go`), every one a tracked-assignment shape: the
claude argv site emits `-p --output-format json --model … [--effort …]
--dangerously-skip-permissions` for every mode it accepts
(`pkg/agentic/systems/claude/args.go`), so consuming `BuildPlan` as a
value puts a headless print-mode run with permission bypass into the
operator's terminal (review M2). And the launcher builds the plan before it
has the fragment, so `LaunchRequest.Home` — "load-bearing: on-disk limit
state is keyed by (provider, home)" — points at the native home while the
process runs in the managed one (review M7). Nobody owns model and effort
defaults, so the flagship one-liner refuses every time (review M8).

The review offered two resolutions and recommended one. Option A: extend
`ax start` with a closed caller-supplied plan, validated under ax §5.1 and
embedded verbatim; `curator-run` composes, `ax` records and launches, the
plugin translates. Option B: `ax start` learns `--curator-profile` and
calls `curator env resolve` itself. The operator decided Option A, decided
the stdin question in favor of growing the plan, and decided that the
launcher is the single composer in both tracked and untracked modes. This
decision records those decisions and specifies the contracts they imply.

## Decision

### 1. Ownership model: four planes, one composer

The roles are closed:

- **Curator resolves.** `curator env resolve <env-id> --format json`
  returns the `launch-env-fragment-v1` object (environments §10.1, §10.2)
  and activates nothing. Under Decision 0012 Decision 8 the fragment's
  `profile` carries `name` and `lock_sha256`, `precedence` carries both
  primitives, and the fragment gains the `mcp` section (path, `env_names`
  union, channel descriptor).
- **`agents-management` builds an interactive plan value.** The launcher
  requests `LaunchModeInteractive` (Decision 5) through `BuildPlan` and
  receives a `Plan` — `Binary`, `Argv`, `Env`, `Stdin`, `WorkDir`
  (`pkg/agentic/plan.go`) — that starts no process.
- **`curator-run` composes exactly one launch plan** from the interactive
  plan, the fragment's channels, and the native arguments after `--`
  (Decision 6). It is the only component that composes, in both modes: on
  a machine with the `ax` integration configured it hands the composed plan
  to `ax start --launch-plan`; without the integration it execs the same
  composed argv, environment, and stdin directly.
- **`ax` validates, records immutably, and launches through its plugin.**
  `ax start --launch-plan` (Decision 3) validates the document under ax
  §5.1, embeds the resolved plan into the immutable Session Record, and
  calls provider `launch` with the record's plan as today.
- **The plugin translates without rebuilding argv.** A provider plugin that
  declares the `caller_launch_plan` capability (Decision 3) maps the
  record's plan onto its `SpawnPlan` (ax §7.5) verbatim; its own
  contribution is bounded to element 0 and its base flags in the
  `argv_suffix` form, `cwd`, `native_session_id`, and `profile_mapping`.

Every plane keeps its Decision 0010 Decision 10 ignorance: `ax` knows
nothing of Curator or `agents-management` beyond an opaque plan and three
opaque extension keys; `agents-management` knows nothing of fragments;
Curator knows nothing of launching. The launcher remains the only
component with a module edge (`agents-management`, launcher §1, §7).

### 2. Why Option A

Rejected alternatives records Option B and the review's reasoning. In
short: Option A preserves `ax`'s plugin-owned resume argv, keeps `ax`
ignorant of Curator and `agents-management`, and makes one component the
single composer in both modes, so an untracked launch and a tracked launch
differ only in who creates the process.

### 3. `ax start --launch-plan FILE|-`

#### 3.1 Surface

```text
ax start NAME --provider ID --launch-plan FILE|- [--profile standard|yolo] [--workspace PATH]
```

`--launch-plan` names a file holding the launch-plan request document, or
`-` to read the document from `ax`'s own standard input. It is the plan
document that is read, never the child's stdin. `--launch-plan` and
`--task-board` are mutually exclusive in this revision: a command carrying
both is `invalid_arguments` (ax §15.3, exit 2). Task-board launches keep
building their plan inside `ax` (ax §13.2) unchanged.

#### 3.2 Document shape

The document is JSON and closed: a reader MUST reject an unknown member,
an unknown `schema`, and a `schema_version` other than `1.0.0`, before
any Session Record exists.

```json
{
  "schema": "urn:ax:schema:launch-plan-request",
  "schema_version": "1.0.0",
  "argv_suffix": ["--model", "claude-opus-5", "--effort", "high", "--mcp-config", "/…/mcp/claude_code.json", "--strict-mcp-config"],
  "env_names": ["FIGMA_API_KEY"],
  "env_literals": { "CLAUDE_CONFIG_DIR": "/…/managed-home" },
  "stdin": null,
  "extensions": {
    "works.relux.curator.profile-name": "companyA-root-context-ios-developer-umbrella",
    "works.relux.curator.profile-pin": "sha256:bbbb…",
    "works.relux.curator.fragment-digest": "sha256:cccc…",
    "works.relux.curator.system-modules": false
  }
}
```

- `schema` is exactly `urn:ax:schema:launch-plan-request` and
  `schema_version` is `1.0.0`. The spelling follows ax §1.6, which
  requires every schema object to carry its own `schema` and
  `schema_version` and names every ax schema `urn:ax:schema:<name>`; the
  brief's `ax-launch-plan-request-v1` would be the only ax schema outside
  that convention.
- Exactly one of `argv` and `argv_suffix` is present.
  - `argv_suffix` (array of strings) is appended after the plugin's own
    base argv: the provider executable as the plugin resolves it, followed
    by the flags the plugin emits for the persisted execution profile (ax
    §2.4, §7.7). The composer always uses this form (Decision 6.4).
  - `argv` (array of strings) is the complete argv; element 0 is the
    provider executable spelled as the plugin would resolve it (the bare
    name of the ax §5.1 example, `["codex"]`, or the absolute path the
    plugin's `doctor` reports), and the plugin MUST append nothing to it.
    Because the execution-profile flags are plugin-owned and this form
    admits no plugin contribution, `argv` combined with `--profile yolo`
    is `invalid_arguments`; a caller that owns the whole line owns the
    whole line. The composer never uses this form; it exists so that a
    non-Curator caller can drive `ax` without the suffix contract.
  - Why element 0 is not caller-invented: the plugin's `ResolveBinary`-class
    knowledge (`agents-management` resolves on the launch `PATH`; ax
    plugins resolve their provider executable) is the one fact two
    components would otherwise both own.
- `env_names` (array of strings, MAY be absent = empty) is the plan's
  environment-name allowlist under the unchanged ax §5.1 grammar
  (`[A-Za-z_][A-Za-z0-9_]{0,127}`, sorted, unique, at most 64): values
  resolve destination-locally and are never in the document. The composer
  populates it with the fragment's `mcp.env_names` union, which is how
  Decision 0012 Decision 6's "adds the fragment's `env_names` to the launch
  plan's environment-name allowlist" reaches the Session Record. The brief's
  premise — that `env_names` is not caller-supplied from the fragment side
  except through this addition — holds: no other member of the fragment
  feeds it.
- `env_literals` (map, MAY be absent = empty) carries non-secret literals
  under the unchanged ax §5.1 rules: at most 64 entries, each value at most
  4,096 UTF-8 bytes, keys sorted in canonical form and disjoint from
  `env_names`.
- `stdin` (object or null, absent = null) is the Decision 4 shape.
- `extensions` (object, MAY be absent = empty) follows ax §1.6: reverse-DNS
  keys, at most 64, the canonical object at most 65,536 bytes. Its members
  are copied verbatim into the Session Record's top-level `extensions`
  (where PR #1 places the `works.relux.curator.*` keys); a key that collides
  with one `ax` sets itself is `launch_plan_invalid` with `field:
  "extensions"`.
- The document carries no `contains_secrets`, `cwd_workspace_id`, or
  `cwd_relative`: `ax` derives the workspace members from `--workspace` as
  today and records `contains_secrets: false` only after its own check.

#### 3.3 Validation and refusal

Every ax §5.1 limit and secret rule applies to the caller-supplied members
exactly as it applies to a plan `ax` builds itself: argv elements 1–4,096
bytes each, 1..128 elements and at most 65,536 encoded bytes for the
resolved final argv; `env_names` 0..64; `env_literals` 0..64 × 4,096
bytes and non-secret; ax §16.2's environment-secret and credential
exclusions. A violation refuses `ax start` before any Session Record,
lease, terminal entry, or process exists, with the Structured Error (ax
§15.1) code `launch_plan_invalid`, exit class 2 alongside
`invalid_arguments`, and a `details` map carrying `field` — the JSON
member name at fault (`argv_suffix`, `env_literals`, `stdin`,
`extensions`, …). `launch_plan_invalid` covers shape, limits, `argv` /
`argv_suffix` exclusivity, unknown members, and extension-key collisions
only. A secret-rule violation in a caller document (an `env_literals`
value or a `stdin` payload that the ax §5.1 rule or the ax §16.2
exclusions classify as a secret) refuses with the existing ax §15.3 code
`secret_policy_violation`, exit class 16, with `details.field` naming the
member — one condition keeps one code and one exit class across every
path that reaches it. `launch_plan_invalid` is a new stable code; ax §15.3
admits new codes in a compatible minor version.

The record-side bound is checked at the same time: the caller's
`extensions` (for a composed document, the four `works.relux.curator.*`
keys of Decision 6.4 are among them — `ax` is generic and knows no such
class) together with the `ax.launch-plan-request` key (§3.4)
MUST fit the ax §1.6 extensions bound (at most 64 keys, canonical object
at most 65,536 bytes) as they will be persisted; a document that would not
is refused here with `launch_plan_invalid`, `field: "extensions"`, so no
document that passes §3.3 can yield a record `ax` cannot persist.

#### 3.4 What the record stores

The Session Record's `launch_plan.argv` MUST hold the final argv — the
plugin's base argv followed by the `argv_suffix`, or the complete `argv`
— so that the immutable record answers "what launched" without
re-deriving anything. Because ax §13.1 persists the record (step 2) before
it calls `launch` (step 4), `ax start --launch-plan` adds one step before
persistence for both forms: `ax` calls provider `launch` with the
candidate record in planning role, takes the returned `SpawnPlan.argv` as
the resolved final argv (for the `argv` form, the plugin's verbatim
translation plus its §3.6 profile-flag check), validates it under §3.3,
and only then persists the record — so a §3.6 refusal, like every §3.3
refusal, fires before any Session Record exists. Provider `launch` is already a plan-returning operation that
creates no process (ax §7.5, "the trusted terminal backend performs process
creation"); a plugin declaring `caller_launch_plan` MUST answer that call
deterministically, and step 4's `launch` against the persisted record MUST
return an argv equal to the recorded one, else `provider_protocol_error`.

The caller document is recorded under the ax-generic top-level extension
key `ax.launch-plan-request`, an object `{ form: "argv" | "argv_suffix",
base_argv_length: <n>, request_digest: "sha256:<hex>" }`. The `ax` label mirrors the `urn:ax` authority of every
ax schema identifier; `dev.ax` or `works.relux.*` would assert a domain
this key does not belong to. The document itself is not stored: the ax §1.6
extension bound is 65,536 canonical bytes, and a document may carry 65,536
bytes of argv plus 65,536 bytes of stdin. For the same reason the extension
value carries no copy of the suffix: the record's own `launch_plan.argv`
already holds it, and the suffix is defined as
`launch_plan.argv[base_argv_length:]` (for the `argv` form
`base_argv_length` is 0 and the suffix is the whole argv). That definition
is what resume replays (§3.5) and what lets a reader split the recorded
final argv into its two owners; the extension value is a few dozen bytes
regardless of the plan's size. `request_digest` is the ax §1.6 digest of
the canonical request bytes and lets an operator prove which document
produced the record. What remains bounded by ax §1.6 is the caller's own
`extensions` plus this key plus the Curator keys, and §3.3 refuses a
document that would not fit before any record exists.

#### 3.5 Plugin contract and resume

The ax §7.3 `capability_names` registry gains `caller_launch_plan` as its
eighth name, appended in order; the manifest text "the exact seven-name
ordered registry" becomes eight, and the PR states the manifest schema
consequence for the ax maintainer's decision. A `launch` for a record
carrying `ax.launch-plan-request` against a plugin whose manifest does not
declare `caller_launch_plan` is refused by `ax` with `capability_unavailable`
(ax §15.3, exit 6), `details.capability: "caller_launch_plan"`, before the
plugin is invoked and before any process exists. A plugin that declares it
MUST translate the record's plan onto its `SpawnPlan` verbatim: `argv` as
recorded, `env_names` and `env_literals` as recorded, `stdin` as recorded
(Decision 4); it MUST NOT reorder, deduplicate, or rewrite a caller element,
and it MUST NOT emit a second spelling of a flag the caller supplied. A
caller element that collides with the plugin's base flags other than a
profile flag (§3.6) is the plugin's to refuse (`capability_unavailable`
with `details.argv_index`) or to pass through; which is Open question 2.

The ax §7.5 `resume` request gains a `launch_plan: Launch Plan` member —
the record's — so the plugin has what it must replay. Resume argv stays
plugin-owned: the plugin builds its native resume argv as today and appends
the recorded suffix `launch_plan.argv[base_argv_length:]`, with
`base_argv_length` read from `ax.launch-plan-request` (for the `argv`
form, nothing is appended and the record's `argv` is informative to resume);
`env_names` and `env_literals` are replayed from the record on every resume;
`stdin` is replayed only under Decision 4's rule. A plugin without
`caller_launch_plan` never sees such a record (the refusal above applies to
resume as to launch).

#### 3.6 Execution profile

`--profile standard|yolo` remains `ax`'s (ax §2.4): the plugin's profile
mapping is the only source of a permission-bypass or unrestricted-mode
spelling in the final argv. A caller plan MUST NOT carry one; the composer
never emits one (Decision 5 forbids it in the interactive plan, and native
arguments after `--` are the operator's own typing). A `caller_launch_plan`
plugin MUST refuse, before process creation, any caller-supplied element —
in `argv` or in `argv_suffix` — that equals a flag of its own ax §7.7
`yolo` profile mapping, in the long form or a documented alias (ax §7.7
names `--yolo` as the accepted Codex alias), with `launch_plan_invalid`,
`reason: "profile_flag"`, and `details.argv_index` the element's index in
the final argv. This decision lists no spelling: the rule keys on the ax
§7.7 mapping the plugin already emits under `--profile yolo`, so the
information needed to refuse is inside the plugin, and a new provider's
spelling is covered the day its mapping is. The refusal is required, not
optional, because a bypass flag that arrives through the caller plan
would launch an unrestricted process under a record that says
`execution_profile: standard`, skipping the ax §2.4 confirmation — the
immutable record would misstate the one fact Option A relies on it for.
Decision 7 makes the negative case part of the PR's required conformance.

### 4. `stdin` on the Launch Plan and on `SpawnPlan`

Both the ax §5.1 Launch Plan and the ax §7.5 `SpawnPlan` gain an OPTIONAL
`stdin` member:

```json
"stdin": { "encoding": "utf-8", "bytes": "<string>" }
```

- `encoding` is exactly `utf-8` or `base64url`; `bytes` is the payload in
  that encoding, `base64url` being the unpadded RFC 4648 URL-safe form ax
  §1.6 prescribes for bytes in every ax schema object. Two encodings, one
  object: a `utf-8` payload stays readable in the record (the common case
  is a short JSON control stream), and `base64url` admits bytes that are
  not valid UTF-8 without a second member shape.
- The decoded payload is at most 65,536 bytes — the same bound as the total
  encoded argv, because stdin and argv are the two launch-time inputs of the
  same size class, and the ax §1.6 extension object carries the same figure;
  one number is easier to hold than three. A larger payload is
  `launch_plan_invalid`, `field: "stdin"`.
- The payload is non-secret under exactly the `env_literals` rule of ax §5.1
  and the ax §16.2 exclusions; `contains_secrets` covers it.
- It is recorded immutably in the Session Record as given and copied verbatim
  into `SpawnPlan.stdin` by a `caller_launch_plan` plugin.
- Absent or `null` means the child's standard input is the terminal, exactly
  as today. Present means the terminal backend delivers the decoded bytes as
  the child's complete standard input and closes it after the last byte;
  output and signals stay on the terminal. Attaching keyboard input after a
  payload is not specified in this revision (Open question 4).
- A resume does not replay `stdin` by default. A plugin replays it only when
  its manifest declares the `stdin_resume_replay` capability (ninth name of
  the registry, appended after `caller_launch_plan`); Open question 4 leaves
  the per-provider answer to the plugin.

Mapping from `agents-management`: the composer sets `stdin` exactly when the
interactive plan's `StdinPayload.Attached` is true, with `Bytes` as the
payload (`utf-8` when the bytes are valid UTF-8, else `base64url`); `Attached`
false is `null` — the "no stdin" versus "empty attached stream" distinction
`StdinPayload` exists to make (`pkg/agentic/system.go`) is preserved as
"terminal" versus "present with zero bytes". Under Decision 5, interactive
mode attaches stdin only for a system whose effort transport is stdin. At
`91bf945` the only such system is `qwen` (`EffortTransportStdin`,
`pkg/agentic/systems/qwen/qwen.go`; its stdin is the two-frame stream-json
control stream whose first frame carries `effort`); `pi` declares
`EffortTransportNone` and attaches nothing (`pkg/agentic/systems/pi/pi.go`,
`stdin.go`). None of the launcher §4.2 mapped systems (`claude-code`,
`codex`, `pi`) uses stdin transport, so in revision 1 the composer's
`stdin` member is `null` for every launchable environment; the mapping
above is fixed now so that the next stdin-transport system needs no
decision.

### 5. `LaunchModeInteractive` in `agents-management`

A fourth `LaunchMode`, `LaunchModeInteractive`, joins `LaunchModeExec`,
`LaunchModeDryRun`, and `LaunchModeManagedSession` (`pkg/agentic/system.go`;
`Valid()` and `String()` extend accordingly). Its grammar constraints,
closed:

- The argv contains only **model selection** and the **effort transport**
  for the requested effort. It contains no print or headless mode, no
  output-format flag, no permission bypass or unrestricted-mode flag, no
  goal or assignment-prompt machinery, no budget flag, and no service-tier
  flag. What it may not contain is the invariant; what it does contain is
  the system plugin's to spell.
- `Composition.Prefix` — the MCP composition argv prefix
  (`compositionArgvPrefix` in `pkg/agentic/systems/claude/args.go`) — is
  NOT part of the interactive argv, and `BuildPlan` MUST refuse a request
  carrying a non-empty `Composition` in this mode (`ErrUnsupportedLaunchMode`
  class is wrong for it; a new `ErrCompositionNotInteractive`). The
  fragment's MCP channel is the composer's (Decision 6.5); two components
  spelling MCP flags is the M2 class of defect.
- `StdinPayload` is `Attached: false` unless the system's `EffortTransport`
  is `EffortTransportStdin`, in which case it is exactly the effort encoding
  that system declares and nothing else (no assignment text).
- `LaunchRequest.Home` and `WorkDir` carry as today; the launcher sets both
  (Decision 6.1).
- `Model` is required as today; effort follows the model's `EffortSupport`
  (`EffortSupportRequired` refuses a missing effort with `ErrEffortMissing`,
  `pkg/agentic/plan.go`; `EffortSupportNone` carries none). The module
  injects no default in this mode either — default ownership is the
  launcher's (Decision 6.2).
- A system that does not list the mode in `Capabilities.LaunchModes` is
  refused by `BuildPlan` with `ErrUnsupportedLaunchMode`
  (`pkg/agentic/plan.go`), as for any undeclared mode.

Per-system argv is the system plugin's to spell — the single-construction-site
invariant of `docs/architecture.md` ("Single source per fact") — and this
decision fixes no spelling. It requires one argv-parity golden per system
for the new mode under the module's existing parity bar ("Observable launch
surface is the parity bar": argv, environment, stdin bytes, side effects),
and a negative golden per system proving that the exec-mode markers
(`-p`, `--output-format`, `--dangerously-skip-permissions`, `exec`,
`--dangerously-bypass-approvals-and-sandbox`, `--max-budget-usd`, and each
system's goal machinery) are absent from the interactive argv — a gate that
admits what it must reject fails the golden.

The consumer is named: launcher §4.1 at `0.2.0-draft` requests
`LaunchModeInteractive` by name and never spells a provider flag itself —
the review's "reject launcher-owned interactive argv" (M2) is a launcher
non-goal, not an `agents-management` one.

### 6. Launcher specification `0.2.0-draft`

Decision 0010 Decision 6 left the launcher's flags, consumption, handoff,
and warnings to its own specification. This decision fixes what that
specification's next revision must say; launcher §5 (system-prompt
application) and §6 (diagnostics) stand unless named here.

#### 6.1 Ordering and homes (M7)

The composition algorithm resolves the fragment (launcher §4.3) before it
builds the plan (launcher §4.1). The fragment's `env` value for the
adapter's home variable — the managed-home path for the environment — is
passed as `LaunchRequest.Home`, and `WorkDir` is the launcher's current
working directory. Provider-limit state is therefore keyed by the managed
home the process runs in, never by the native home; a profile A launch
never gates a profile B launch through shared evidence.

#### 6.2 Model and effort defaults (M8)

The launcher owns default resolution. Precedence, closed:

1. `--model` and `--effort` flags;
2. a closed launcher machine-configuration mapping env-id → `{model,
   effort}`, per environment, lockable by the operator;
3. the lineup fallback: the highest-ranked model of `vendorplugin.Lineup`
   (`pkg/vendorplugin/lineup.go`, `Lineup(models []Model) []RankedModel`,
   capability score descending) among the models the module's runtime
   compatibility registry admits for the mapped system, with that model's
   declared `Effort.Recommended` (`pkg/vendorplugin/vendor.go`) as the
   effort, or no effort when its support is `EffortSupportNone`.

Each level is consulted only for the member the previous level left unset
(`--model` with a configured effort is admitted). The resolved pair and the
level that produced it are printed on stderr at every launch. The module's
"no default is injected at any call site" invariant is intact: the default
is chosen by the launcher and passed as an explicit request member, and a
refusal (`ErrEffortMissing`) still names the model, vocabulary, and
recommendation, which the launcher completes with `--effort` (launcher §3).

#### 6.3 Composition rule

The composed launch is one plan. Its members, closed:

- **argv** = interactive plan `Argv` ++ system-prompt channel flags
  (only under the launcher §5 opt-in, from the fragment's `system_prompt`
  descriptors) ++ MCP channel flags (from the fragment's `mcp` descriptor
  and Decision 0012 Decision 6: for `claude_code` the `flag` with its
  `argument: path` and `with` companions; for `codex_cli` `-p curator-mcp`;
  for `opencode` no argv — its channel is a variable) ++ native arguments
  after `--`, verbatim, uninspected. The interactive plan `Binary` is the
  executable. Order is contract: for some tools everything after the last
  recognized flag is the user turn, so a channel flag after the native
  arguments would become prompt text. The general rule is fixed here;
  per-tool verification of the boundary is the launcher specification's
  under the environments §7.3 pinned-release discipline.
- **environment** = inherited ⊕ plan `Env` ⊕ fragment `env` ⊕ the
  `variable`-kind channel of an engaged descriptor (`OPENCODE_CONFIG`),
  later overriding earlier per name; the fragment wins on exactly its own
  registry-declared names (launcher §4.4, unchanged, with the SHOULD-warn on
  a displaced plan name).
- **env_names** = the fragment's `mcp.env_names` union, bounded by the
  reserved set and the lockable passable-names list (environments §10.3
  as rewritten by Decision 0012), minus every name that also appears in
  the composed `env_literals` (plan `Env` ⊕ fragment `env` ⊕ variable-kind
  channel). A literal the composer set is an explicit intent and wins over
  a destination-local lookup; the composer drops the name from `env_names`
  and prints a warning on stderr naming the variable. The reserved-name
  exclusion of Decision 0012 Decision 6 keeps registry adapter names out of
  `env_names`, but a system plugin's plan `Env` is not bounded by it, so
  this rule is what makes the composed document disjoint by construction:
  ax §5.1 disjointness never fires for a composed document, and a
  collision is never an `ax_handoff_failed`.
- **stdin** = the interactive plan's `Stdin` under the Decision 4 mapping.

#### 6.4 Tracked mode delegates; untracked mode execs

With the `ax` integration configured, `curator-run` composes the Decision
3.2 document and invokes:

```text
ax start <name> --provider <id> --launch-plan - [--profile <ax-profile>] --workspace <cwd>
```

writing the document to `ax`'s stdin. The document's members, from the
composed plan: `argv_suffix` = the composed argv without its element 0
(the interactive plan's `Argv` is already the tail after the executable;
`Binary` is the plugin's to resolve, so the composer never sends element
0); `env_names` as composed; `env_literals` = plan `Env` ⊕ fragment `env`
⊕ variable-kind channel — the composer's own names only, never a copy of
its inherited environment, because the inherited layer of a tracked launch
is whatever `ax`'s terminal backend gives the child on the destination —
with the Decision 6.3 collision rule already applied, so `env_names` and
`env_literals` are disjoint before `ax` sees them; `stdin` as composed; `extensions` = the four `works.relux.curator.*` keys
below. The provider id comes from a second column of the launcher §4.2
mapping (`claude_code` → `claude`, `codex_cli` → `codex`, `pi` → `pi`,
the ax §7.1 built-in ids). The launcher never passes `--profile yolo`
unless the operator asked for it by a launcher flag the `0.2` specification
introduces for exactly that; absent the flag, `ax`'s default profile
applies.

The session name is `<env-id>-<utc-stamp>` with the stamp
`YYYYMMDDTHHMMSSZ`, overridden by a `--name <name>` launcher flag. The
profile name is not part of it: it already travels in
`works.relux.curator.profile-name`, and a name carrying it would exceed the
ax §2.1 limit for ordinary profile names (the Decision 6.2 example profile
name alone is 44 characters). The derived name MUST satisfy the ax
session-name grammar (`[A-Za-z0-9][A-Za-z0-9._-]{0,63}`, 1–64 characters,
ax §2.1); the env-id identifier grammar falls inside it, and the default
always fits: the launcher §4.2 mapping is a closed table whose longest
env-id (`claude_code`) is 11 characters, and any env-id of up to 47
characters would still fit beside the 16-character stamp and the
separator. An operator `--name` that violates the
grammar or exceeds 64 characters is a `usage` error naming `--name`, never
a silent truncation (Open question 1).

The extension keys of PR #1 are set by the composer:

- `works.relux.curator.profile-name`: the fragment's `profile.name`;
- `works.relux.curator.profile-pin`: the fragment's `profile.lock_sha256`,
  spelled `sha256:<64 lowercase hex>`. PR #1 wrote "the full lowercase-hex
  commit of a git profile or the state hash of a local profile"; under
  Decision 0012 Decision 3 the lock hash is the profile's effective pin
  everywhere Decision 0010 used a commit, including this key, so the pin
  becomes the lock sha256 and the PR revision says so (Decision 7);
- `works.relux.curator.fragment-digest`: `sha256:` over the CCJ-1
  canonicalization (registry §1) of the parsed fragment object (M16;
  Decision 7);
- `works.relux.curator.system-modules`: boolean, true exactly when the
  fragment carries a `system_prompt` section — environments §10.2 makes that
  presence equivalent to "the resolved chain carries at least one
  applicable system module" (Decision 7).

Untracked mode execs the composed plan directly — `Binary`, the composed
argv, the composed environment, the composed stdin — with no `ax` residue,
exactly the launcher §4.5 second shape. `ax_handoff_failed` stays terminal:
a non-zero `ax start`, a refused document (`launch_plan_invalid`,
`capability_unavailable`, `invalid_arguments`), or an `ax` that cannot be
started is reported with `ax`'s Structured Error passed through, and the
launcher MUST NOT fall back to an untracked exec (launcher §4.5, unchanged).

#### 6.5 Non-goals restated

The launcher still never spells a provider flag of its own (Decision 5),
still never rebuilds the plan (launcher §1) — appending channel flags and
native arguments to a plan value is composition, not rebuilding — and still
imports nothing but `agents-management`. The MCP channel is applied by the
launcher because the fragment is data about a channel (environments §7.3,
Decision 0012 Decision 6) and applying it is exactly the launcher's plane.

### 7. Revision items for ax PR #1

The revision of PR #1 carries, and this decision names, these changes to
the `d7075e1` diff:

1. **ax §7.5 paragraph.** The paragraph "the launcher merges the `env`
   variables of the resolved Curator `launch-env-fragment-v1` object into
   the Launch Plan and resulting `SpawnPlan` `env_literals` map" is
   replaced by the `--launch-plan` operation of Decision 3: a caller
   supplies a validated plan; nothing merges anything inside `ax`. The
   sentence "The integration adds no member to `SpawnPlan`" is withdrawn:
   Decision 4 adds `stdin`, an ax-generic member, not a Curator one.
2. **ax §5.1.** The Launch Plan table gains the `stdin` row (Decision 4);
   the Session Record extension paragraph gains the fourth key
   `works.relux.curator.system-modules` (boolean) and rewrites
   `profile-pin` to the Decision 0012 lock identity — "the `sha256:`-prefixed
   lock hash of the profile as resolved at launch" — in place of "commit or
   state hash". The three existing keys remain.
3. **ax §7.3 and §7.5.** `caller_launch_plan` and `stdin_resume_replay`
   join `capability_names`; `SpawnPlan` gains `stdin`; `resume` gains
   `launch_plan` (Decision 3.5, Decision 4).
4. **ax §13.1.** The planning-role `launch` step of Decision 3.4 for both
   forms, and the required negative conformance cases of the
   caller-plan path: a document whose `argv` or `argv_suffix` carries the provider's
   own ax §7.7 `yolo` flag (long form or documented alias) under
   `--profile standard` is refused with `launch_plan_invalid`,
   `reason: "profile_flag"`, before any Session Record or process exists
   (Decision 3.6); a document whose `env_literals` carries a value the
   secret rule classifies is refused with `secret_policy_violation`
   (Decision 3.3); a document whose `extensions` would not fit ax §1.6
   together with the ax and Curator keys is refused with
   `launch_plan_invalid`, `field: "extensions"` (Decision 3.3). Each case
   is proven by a test that fails when the gate admits the input.
5. **ax §13.10 drift.** When the Session Record carries
   `works.relux.curator.system-modules: true`, a resolved
   `profile.lock_sha256` that differs from the recorded `profile-pin`
   MUST refuse the resume or fork by default (`policy_refused`, ax §15.3,
   exit 16; `details.reason: "environment_drift"`), because a system
   module is instructions the agent cannot see through and a drifted set
   is a different agent (M15). Otherwise the PR's warn-and-continue default
   stands, and the strict mode that refuses on any drift stays available.
   The record knows through the fourth key because a drift check must not
   re-resolve to learn what it is checking against — the fragment is not
   stored (Decision 3.4's size argument applies) and the fresh resolution is
   the thing being compared; one boolean set by the composer from the
   fragment's `system_prompt` presence is the smallest sufficient record.
   A failed resolution remains a distinct fact from drift and from
   currency, as the PR already says.
6. **`fragment-digest`.** Keyed over the CCJ-1 canonical bytes (registry
   §1) of the parsed fragment object, not the pretty-printed `--format json`
   output, so a printer change is not drift (M16).
7. **ax §14.1.** The `ax start` grammar row gains `--launch-plan FILE|-`
   with the exclusivity of Decision 3.1; the `curator session` informative
   note stands.
8. **Version.** The PR proposes v0.6.0 (a compatible minor: new optional
   members, new capability names, new error code, new flag); the ax
   maintainer decides.

### 8. Reconciliation of PR #1 and Decision 0012

Under Decision 0012 the fragment's `profile` carries `lock_sha256` and no
commit; PR #1 was written against the revision-1 fragment with `commit` or
`state_sha256`. Decision 6.4 fixes the composer's spelling of `profile-pin`
and Decision 7 item 2 fixes the PR's text; nothing else in PR #1 depends on
the pin shape. A Session Record written before the revision (a `commit`
pin) and one written after (a lock hash) are distinguishable by the
`sha256:` prefix, and a drift check compares only like with like: a resume
of a pre-revision record against a post-revision fragment is drift by
construction and is reported as such.

## Rejected alternatives

- **Option B — `ax` owns spawn.** `ax start` gains `--curator-profile P |
  --curator-env E [--model --effort]`; `ax`'s owner calls `curator env
  resolve` itself and merges into its plugin's `env_literals`; the launcher
  delegates in tracked mode and composes only when untracked. The review's
  reasoning against it, recorded verbatim: Option A "preserves ax's
  plugin-owned resume argv, keeps ax ignorant of Curator and
  agents-management, and makes one component (curator-run) the single
  composer in both modes." Option B "keeps ax free of a caller-supplied
  plan but puts Curator-awareness inside ax" — and, since `ax` does not
  import `agents-management`, it would also have to learn model and effort
  vocabularies or grow a second composer, so the two modes would compose
  differently.
- **Refusing the `ax` route for non-empty stdin.** The review's other stdin
  option. It would make the tracked and untracked modes diverge for exactly
  the systems whose effort is not in argv; growing `SpawnPlan` by one bounded
  optional member is smaller than a mode-dependent refusal.
- **A launcher-owned interactive argv.** The launcher spelling `--model`
  per tool is a second flag-spelling site — the drift the module's single-
  construction-site invariant exists to prevent (M2).
- **Recording the caller document whole.** Exceeds the extension bound
  (Decision 3.4); the resolved final argv plus the suffix and a digest is
  what resume and audit need.
- **Recording only the suffix and leaving the final argv to
  `provider.launched`.** Keeps ax §13.1's step order untouched, but the
  immutable record would then not answer "what launched" on its own, which
  is the property the review's Option A rests on. The planning-role
  `launch` call costs one deterministic plugin invocation.
- **Folding the system-modules fact into a stored fragment.** Storing the
  fragment stores paths and a descriptor list that drift themselves and
  sit against the extension bound; the boolean is the fact the drift rule
  needs.
- **A permission-bypass denylist in this decision.** The spellings are the
  vendors' and change with releases; naming them here would freeze the
  wrong document. The plugin refuses; the composer never emits.

## Compatibility impact

- **`agent-session-manager-spec`**: a compatible minor bump, proposed
  v0.6.0, carried by the PR #1 revision — `--launch-plan`, the
  `launch-plan-request` schema, `launch_plan_invalid`, `stdin` on Launch
  Plan and `SpawnPlan`, `launch_plan` on `resume`, two capability names,
  one ax-generic and one Curator extension key. Existing records, plugins
  without the capability, and deployments without Curator are unaffected;
  the ax maintainer decides the version.
- **`agents-management`**: a compatible minor — `LaunchModeInteractive` is
  additive; a system that does not declare it is refused as any undeclared
  mode is; one new sentinel error and the per-system goldens.
- **`curator-agent-launcher`**: `0.2.0-draft`; draft versions may change
  incompatibly (launcher §8). The behavioral contract of tracked mode is
  unimplementable until the `ax` change lands, and the specification says
  so.
- **`protocol/environments.md`**: unchanged by this decision; the revision
  1.1 batch's `curator run` rows say what Decision 6 fixes.
- **`protocol/core.md`**: frozen, unchanged.

## Security impact

- The profile-influence boundary (environments §10.3) extends to the plan
  document: profile bytes never reach argv except through registry-declared
  channel descriptors whose arguments are manager-owned managed-home paths
  or the fixed reserved layer name; the composer is the only writer of
  `argv_suffix`, and it writes the interactive plan (vendor-owned
  spellings), channel flags (registry-owned), and the operator's own
  arguments after `--`.
- No permission bypass in interactive mode: the only source of an
  unrestricted-mode flag is `ax`'s plugin under `--profile yolo`, recorded
  in the immutable record and repeated on every launch event (ax §2.4).
- Secrets are excluded by ax §5.1 and §16.2 over every caller member;
  `env_names` carry names only and resolve destination-locally; `stdin` is
  bounded and non-secret.
- `env_names` from a fragment are bounded twice: by the reserved-name
  exclusion of Decision 0012 Decision 6 and by the lockable passable-names
  allowlist, before they reach the composer.
- Refuse-on-drift for system-module chains means a resume never silently
  runs an agent under different system instructions than the one that was
  started; the boolean that triggers it is set by the composer from fragment
  data, never from profile bytes.
- The record's `request_digest` is a record, not a signature (the core §10
  discipline).

## Consequences

- One component composes launches on every machine; a tracked and an
  untracked launch differ only in who creates the process, and the
  operator's `curator run codex_cli --profile companyA -- resume --last`
  works on both.
- `ax` gains a generic caller-supplied-plan surface that any composer can
  use; Curator is its first caller, not its only one.
- `agents-management` gains the launch shape the review found missing, and
  its argv-parity discipline now covers the interactive terminal.
- The launcher specification gains default ownership and the fragment-first
  ordering; the review's M2, M7, and M8 close with it.
- The PR #1 revision closes M15 and M16.

## Open questions

1. **Session-name derivation.** Whether `<env-id>-<utc-stamp>`
   should carry a shorter stamp or a counter to avoid same-second
   collisions, and whether `--name` should be the only derivation on a
   machine that locks names. Recommendation: keep the stamp, add the
   counter only if a collision is observed.
2. **Caller argv colliding with plugin base flags.** Whether a
   `caller_launch_plan` plugin refuses a suffix element that duplicates or
   contradicts a base flag, or passes it through and lets the tool decide
   last-wins. Recommendation: pass through in revision 1 and record the
   collision in `provider.launched`; the operator typed it.
3. **Task-board launches and `--launch-plan`.** Whether ax §13.2 adopts the
   caller-supplied plan later so that a tracked-assignment launch can carry
   a Curator fragment. Not in this revision.
4. **Stdin replay on resume per provider.** Which plugins declare
   `stdin_resume_replay`, and whether a payload-then-terminal stdin shape
   is needed for an interactive tool whose effort rides stdin. Both are the
   plugin's to answer with the pinned provider release.
5. **Native `resume`-class arguments in a replayed suffix.** An operator's
   `-- resume --last` is a one-shot turn; replaying it on an `ax resume`
   may double-resume. Whether the composer marks the native tail as
   non-replayable (a split of `argv_suffix` into replayed and one-shot
   parts) belongs to the launcher `0.2` review together with question 2.
