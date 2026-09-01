# Decision 0010: agent environment profiles and global context management

## Status

Proposed 2026-08-31. Draft for review; nothing in this document is normative
yet. Acceptance authorizes authoring the normative surfaces it names — a
`protocol/environments.md` document, manager-profile sections, JSON Schemas,
and conformance vectors — as separately tracked work. Section numbers cited
without a document name refer to `protocol/core.md`.

## Context

Curator manages skills. The protocol resolves skill closures from canonical
git sources with exact refs, materializes agent-facing context into project
and global adapter surfaces under a managed ledger, verifies MCP requirements
read-only, and audits every source before installation. The manager profile
already defines a global scope: a machine-local `Skillfile.json` whose skills
mirror into each agent's home discovery directory (`~/.claude/skills`,
`~/.codex/skills`, and the rest of the manager §5 table) as symlinks or copies
beside a `.csk-managed.json` ledger.

Everything else in those homes is unmanaged. The root instruction file
(`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`), MCP server configuration, settings,
prompts, and subagent definitions are hand-maintained per tool, drift
independently, carry no provenance, and cannot be switched between contexts. A
user who works for company A, company B, and themselves maintains N divergent
copies of the same intent across M agent environments, and every agent session
silently absorbs whatever happens to be in the home at launch.

Two external facts make this solvable now.

First, every major agent CLI has converged on home-directory isolation. The
supported environments accept one environment variable that relocates the
whole global home: `CLAUDE_CONFIG_DIR` (Claude Code), `CODEX_HOME` (Codex),
`PI_CODING_AGENT_DIR` (pi), `XDG_CONFIG_HOME` (opencode), `GEMINI_CLI_HOME`
(Gemini CLI), `CURSOR_CONFIG_DIR` (Cursor CLI), `COPILOT_HOME` (Copilot CLI),
`GOOSE_PATH_ROOT` (goose). The variables disagree about whether they name the
home itself or its parent, and a minority of tools support only config-file
overrides or nothing, but the mechanism is established practice — Xcode's
CodingAssistant ships its embedded Claude and Codex agents with exactly this
shape, a dedicated fixed home per agent, recorded from vendor documentation
as `~/Library/Developer/Xcode/CodingAssistant/` since Xcode 26.3 (the
parent path and the version attribution are docs-confidence; open question
6 verifies them). The verified per-tool matrix,
with local-binary evidence for Claude Code 2.1.251, Codex 0.151.0, pi 0.84.2,
and Gemini CLI 0.54.4, is recorded in the research resource attached to
`TASK-260831-hbq9n6`.

Second, the agent-session-manager specification (`ax`, v0.5.0) launches every
provider process from a `SpawnPlan` containing `argv`, an explicit working
directory, an environment-name allowlist, and literal environment values,
never through a shell. An environment expressed as literal variables is
therefore directly injectable into `ax`-managed sessions without any new `ax`
mechanism.

This decision moves Curator from a skill manager to an agent environment
manager: the global home of each agent environment becomes managed,
versioned, profile-switchable state with the same source identity, audit,
ledger, and determinism discipline the protocol already applies to skills.

## Decision

### 1. Environment profile

An **environment profile** is a named, versioned set of global agent context
installed from a git source. A profile carries:

- a **root context**: an ordered set of environment-agnostic instruction
  modules (the intermediate representation of `AGENTS.md`/`CLAUDE.md`-class
  content);
- an optional **skill set**: a profile-scoped `Skillfile.json` with the
  existing schema, resolved through the existing closure, audit, and runtime
  machinery;
- future surface declarations (MCP servers, settings fragments) admitted only
  by later revisions of this capability, each under its own review.

Profile names are portable identifiers (§2). Profile sources use the §6.1
canonical git identity, the §6.2 git safety rules, and §6.3-style exact
references. A directly installed profile MAY track a branch — the same
allowance `Skillfile.json` gives direct project declarations — and the
resolved commit is recorded as the effective pin; `--strict-tags` semantics
carry over unchanged. Two additional source kinds exist beside `git`:
`local`, reserved for the builtin migration profile of Decision 8, and
`path` — an operator-local profile directory installed by absolute or
project-relative path instead of a URL, snapshotted and keyed by the §8
content hash of its state. `path` is the vehicle for first-run onboarding
imports (Decision 5) and for authoring profiles before they have a
repository; it is delivered with the onboarding import story, not in
revision 1.

### 2. Profile repository shape

A profile repository declares its profiles in a root `Profilefile.json`
(strict schema, version 1): a map of profile names to repository-relative
portable paths. Each profile directory contains:

```text
<profile-root>/
  context/
    context.json        # module manifest, schema 1
    00-base.md          # ordered instruction modules
    10-style.md
    20-claude.md
  Skillfile.json        # optional profile-scoped skill declarations
  PROFILE.md            # optional human-facing description
```

`context.json` declares an ordered module list. Each entry names a module
file (a portable relative path below `context/`) and an optional
`environments` selector: the set of environment identifiers the module
applies to. An absent selector means every environment. The selector is how
one profile serves different tools without duplication — `00-base.md` with
no selector reaches every materialized root context, while `20-claude.md`
with `"environments": ["claude_code"]` appears only in `CLAUDE.md` and never
in a `codex_cli` or `pi` output. An entry MAY also declare
`class: "system"`, marking the module as system-prompt content under the
system-prompt rules below; the default class is `root`. Version 1 is
deliberately minimal — ordered selection with no templating, no variable
substitution, no conditional syntax inside module bytes, and no per-module
remote inclusion. A module is UTF-8 markdown. Snapshot validation rejects a
module that is not valid UTF-8, contains a line ending other than LF, or
does not end with exactly one trailing LF — the fail-closed posture of the
other strict schema surfaces, chosen over silent normalization. A module
that validates is thereafter treated as opaque bytes: materialization never
rewrites it.

**Materialization forms.** Granularity is preserved end to end where the
tool allows it. Each adapter declares which root-context forms the
environment supports:

- **`monolithic`** — one file, the applicable modules concatenated. Always
  supported; the only form for `codex_cli` and `pi` (neither tool reads
  imports from its root file; verified for pi from the loader source,
  docs-confidence for codex).
- **`referenced`** — the modules materialize as individual files beside the
  root file, and the root file references them through the tool's native
  mechanism: `@path` imports for `claude_code` (documented up to five hops),
  the `instructions` file list in `opencode.json` for `opencode`. A team
  that already maintains a reference-structured `CLAUDE.md` migrates by
  turning each referenced file into a module — the materialized shape is
  what they already have.

The effective form per environment is chosen by machine configuration with
the adapter's default, never by profile data. Where the tool itself gates
the referenced form, the adapter consults the tool's own configuration
before selecting it — `claude_code` gates external imports behind a
per-project approval recorded in `.claude.json`
(`hasClaudeMdExternalIncludesApproved`), so the adapter emits `referenced`
CLAUDE.md content only where that approval is present or the references
stay inside the home, and falls back to `monolithic` otherwise. Surveying
the remaining environments' import semantics is a research item of open
question 7.

**Generation header.** Every materialized root-context file begins with a
deterministic HTML comment that markdown renderers do not display:
generated-by Curator (project URL), the profile identity and effective
commit (or state hash for a `local` profile), the composition chain when
Decision 5 composition is active, the declared precedence, and the notice
that direct edits are unsupported and will be detected as drift — update
the profile repository, or the managed context it composes, instead. The
header contains no timestamp, machine path, or operator identity, so the
output stays byte-deterministic and carries no personal data.

Materialized root context is deterministic: the header, then the applicable
modules in manifest order, joined by exactly one empty line (a single
additional LF between parts), with no other transformation. Under Decision 5
composition, each composed profile's modules form a titled chapter — a
readable separator line and a heading naming the source profile — so a
reader and the agent can always tell which profile a passage came from.
Because every module ends with exactly one LF, the output is LF-encoded and
ends with exactly one trailing LF by construction. The output is hashed with
the §8 content hash; identical profile commit plus identical adapter set,
form, and composition yields byte-identical output on every platform.
Determinism is what makes drift detection and `status --check` possible,
and it is a conformance-vector surface.

**System prompt.** A profile MAY carry `class: "system"` modules: an
environment-agnostic system-prompt overlay for tools that expose a
system-prompt override channel. The channel is adapter-declared and varies:
`claude_code` takes `--system-prompt`/`--append-system-prompt`(-file)
arguments (verified in 2.1.251), `pi` takes the same flags and additionally
reads `APPEND_SYSTEM.md` from its agent dir (verified in 0.84.2),
`codex_cli` takes a `model_instructions_file` configuration override
(verified key in 0.151.0; full replacement), and `gemini` — a revision-2
adapter — takes the `GEMINI_SYSTEM_MD` variable (full replacement,
docs-recorded). Because a system-prompt override changes tool behavior far
more than instructions the model merely reads, it never materializes into a
native in-place home where it would silently apply to every session: system
modules materialize only into managed homes and activate only through the
launcher's explicit opt-in (Decision 6) or through natively typed commands.
Secondary fixed-home targets never receive system modules in revision 1;
whether an embedded host offers any override channel at all is open
question 8.

Profile repositories are data. No file in a profile repository is executed,
sourced, or interpreted as configuration for Curator itself. The existing
source-audit pipeline (manager §7) applies to profile snapshots as it does
to skill snapshots: raw-tree hashing, the static canary whose failure always
blocks, deterministic detectors, and revocation. That pipeline alone does
not block credentials — today's deterministic detectors cover undeclared
network hosts and undeclared executable names, not secrets in context
modules — so this decision adds two rules. Profile installation always runs
the audit in strict mode; an advisory profile install does not exist. And
the normative work this decision authorizes includes a secret-detection
detector class over context modules and the profile manifest, making
credential-like material a verifiable finding at blocking severity, so a
profile that carries it fails installation.

### 3. Environment adapter registry

The manager §5 adapter table generalizes from one surface (skills) to an
**environment adapter registry**. Revision 1 defines four adapters:

| Environment | Home mechanism | Home shape | Root context target | Skills target |
|---|---|---|---|---|
| `claude_code` | `CLAUDE_CONFIG_DIR=<home>` | variable names the home | `<home>/CLAUDE.md` | `<home>/skills/` |
| `codex_cli` | `CODEX_HOME=<home>` | variable names the home | `<home>/AGENTS.md` | `<home>/skills/` |
| `opencode` | `XDG_CONFIG_HOME=<parent>` | tool reads `<parent>/opencode/` | `<home>/AGENTS.md` | `<home>/skills/` |
| `pi` | `PI_CODING_AGENT_DIR=<home>` | variable names the home | `<home>/AGENTS.md` (also honors `APPEND_SYSTEM.md`; not managed in revision 1) | `<home>/skills/` |

Each adapter normatively declares: the environment-variable name and whether
it names the home or a parent; the home-relative path of every managed
surface; the surfaces it supports per revision; the root-context forms of
Decision 2 it supports (`monolithic` always; `referenced` where the tool has
a native reference mechanism) and its form default; its system-prompt
override channel of Decision 2, when the tool has one; the credential
passthrough entries of Decision 7; the materialization-mode default of
Decision 4; its known shadowing paths — higher-precedence unmanaged files whose presence
makes a managed surface inert, such as pi's `AGENTS.override.md`, which the
tool's discovery chain prefers over `AGENTS.md`; and its secondary
fixed-home targets below. The §11 ledger protects only managed paths, so
materialization and `env status` warn when a declared shadowing path exists
on the machine. Unknown environment identifiers keep their manager §5
behavior: a warning and no output.

One fragment is wider than its tool: `XDG_CONFIG_HOME` is a generic XDG
variable, so every XDG-conforming child of a launched opencode session —
git, editors, anything honoring the spec — resolves its configuration under
the managed parent instead of the operator's `~/.config` for the whole
process tree. This is a bounded relative of the side-effect class that
disqualifies `HOME` substitution (Rejected alternatives). Revision 1 accepts
the tradeoff and narrows it: when the launcher provisions a managed opencode
parent, Curator seeds it with symlinks to the operator's existing
`~/.config` entries other than `opencode/`, and a dedicated opencode home
variable, should the vendor ship one, supersedes the XDG mechanism.

**Secondary fixed-home targets.** Some hosts embed an agent environment at a
fixed home no environment variable can retarget, but with the same internal
layout the primary home has. An adapter MAY declare a closed list of such
targets: a probe path, the home path, and the subset of surfaces the embedded
host honors. Revision 1 declares two, both introduced by Xcode's
CodingAssistant (docs-recorded as of Xcode 26.3; path and version verify
under open question 6):

| Adapter | Target id | Home | Surfaces honored |
|---|---|---|---|
| `claude_code` | `xcode-coding-assistant` | `~/Library/Developer/Xcode/CodingAssistant/ClaudeAgentConfig/` | root context, skills (embedded host also reads `commands/` and `.claude.json` MCP state, unmanaged in revision 1) |
| `codex_cli` | `xcode-coding-assistant` | `~/Library/Developer/Xcode/CodingAssistant/codex/` | root context, skills (embedded host reads `config.toml`, unmanaged in revision 1) |

A secondary target is an in-place surface set like any other: it carries the
same environment marker and ledger discipline, defaults to `copied` mode
(Decision 4), and always reflects the current profile — an embedded host
launches its agent itself, so the launcher and managed homes can never reach
it. Target participation is governed by machine configuration, not by profile
data: `auto` (default — the target participates exactly when its probe path
exists on the machine), `off`, or an explicit per-target enable. Under `auto`
a machine without Xcode materializes nothing there and reports nothing
missing; a machine with Xcode gets its embedded agents flashed on every
install, `use`, and `sync` without further ceremony. Probe results appear in
`env status` so an operator can see which targets are live.

Adapters are manager code, never package code. Admitting a new adapter is a
specification revision with its own review — the same closed-set discipline
§12.3 applies to build drivers. `gemini`, `cursor`, and `windsurf` remain
skills-only adapters under the existing manager §5 table in revision 1 and
are candidates for revision 2; tools with no isolation mechanism (Factory
droid) or config-file-only overrides (amp, aider) are out of scope until
their vendors ship one.

### 4. Materialization modes

A profile materializes into an environment in one of three modes:

- **`managed-home`** — Curator provisions a complete home directory per
  (profile × environment) under its machine home, for example
  `<curator-home>/environments/<profile>/<env-id>/`. Managed surfaces inside
  it are symlinks into the commit-keyed profile store (copies where a surface
  or platform requires bytes). The environment's own mutable state — session
  logs, history, caches, trust records — lives beside them, owned by the
  tool, giving each profile naturally isolated session state. Managed homes
  are activated exclusively through the launcher (Decision 6).
- **`linked`** — in-place materialization into the environment's native
  default home (`~/.claude`, `~/.codex`, …) as symlinks into the profile
  store. This is today's global-scope skill mechanism extended to root
  context. Only the current profile (Decision 5) is materialized in-place.
- **`copied`** — in-place materialization as plain files with recorded
  content hashes, for surfaces or targets where symlinks are unreliable:
  secondary fixed-home targets (the Xcode CodingAssistant homes of Decision
  3, which run their agents in a restricted environment), sandboxed tools
  that refuse links, or network filesystems. Drift is detected by hash
  comparison; a hash mismatch marks the installation non-current rather than
  being silently overwritten, and the diagnostic states both halves
  explicitly — the surface was modified outside the manager, the file was
  left untouched, the installation is non-current, and `repair` restores the
  managed bytes.

Mode defaults: the four native-home adapters default to `linked` for their
in-place surfaces — the manager §5 symlink-with-copy-fallback discipline
unchanged — secondary fixed-home targets default to `copied`, and managed
homes always link from the store. An adapter MAY declare a different
in-place default; the declaration lives in the adapter registry, never in
profile data.

Every in-place surface is recorded in a per-home **environment marker**
(`.agent-environment.json`, schema 1) alongside the generalized ledger:
profile identity, source identity, effective commit, mode, and per-surface
content hashes. The marker name deliberately joins the `agent-skill.json`
family rather than the legacy `csk-` family: new identifiers introduced by
this capability carry no `csk` spelling. The frozen §1.1 identifiers
(`.csk-install.json`, `.csk-managed.json`, `CSK_PROJECT_ROOT`) are wire
compatibility surfaces and stay as they are here; retiring them follows the
`csk-skill.json` → `agent-skill.json` alias precedent and is separately
tracked cleanup work, not part of this decision. The §11
rule extends unchanged: Curator removes or replaces only entries its
preceding ledger owns and MUST fail rather than overwrite an unmanaged file.
A pre-existing unmanaged `~/.claude/CLAUDE.md` is never clobbered by an
ordinary operation; first-run onboarding (Decision 5) is the supported path
that turns such files into managed state with an explicit backup, and the
takeover flag remains the manual equivalent.

Both in-place modes and managed homes materialize from the same commit-keyed
profile store, so `linked`, `copied`, and `managed-home` cannot diverge for
one profile commit. A `local` profile (Decision 8) is keyed in the same
store by the §8 content hash of its state in place of a commit; the
non-divergence guarantee holds identically.

### 5. Current profile, composition, and switching

The machine configuration records at most one **current profile**. `curator
profile use <name>`:

1. re-materializes every in-place surface of every registered adapter —
   native default homes and every participating secondary fixed-home target —
   from the selected profile atomically per entry, under the manager-home
   mutation lock, journaled like any other manager-home transaction (manager
   §2.5);
2. updates the recorded current profile;
3. warns that already-running agent sessions keep the previous context in
   memory and may write state derived from it, and recommends the launcher
   for concurrent multi-profile work.

**Scoped switching.** `profile use` accepts `--env <env-id>` and
`--target <target-id>` to narrow the switch to a subset of adapters or to
one secondary fixed-home target. The motivating case is Xcode: its embedded
agents are unreachable by the launcher, so pinning only
`--target xcode-coding-assistant` to a company profile while terminal
sessions run personal profiles through the launcher is the only way to hold
those two apart. A scoped switch records a per-scope current profile;
`env status` and `profile list` surface every scope whose current profile
differs from the machine default, so a split-brain configuration is always
visible, never implicit.

**Composition.** A machine MAY declare, per installed profile, an ordered
overlay list: additional installed profiles whose root context and skills
are appended when that profile is activated or resolved. Any profile can
serve as an overlay — an overlay is not a distinct package shape — and the
declaration lives in Curator's machine configuration, never in profile
data, so activating `companyA` on one machine composes `personal` into it
while another machine's `companyA` stays pure. The declaration also names
the precedence direction; the default is `later-overrides-earlier` — an
overlay is typically the operator's refinement of an organizational base,
and the closest declaration winning matches how operators already expect
configuration layers to resolve — with the reverse available explicitly.
Decision 2's generation header states the effective direction and the
chapter joining makes it legible; instruction text cannot be merged
mechanically, so precedence is declared to the reader and the agent rather
than silently resolved.
Skill-set composition is mechanical: the composed closure resolves with the
declared precedence picking the winner when two composed profiles declare
the same skill, and a version divergence between them is reported. The
composed output is deterministic — profiles in declared order, chapters per
Decision 2 — and the composition chain enters the environment marker and
the launch fragment, so drift detection and `ax` resume fidelity see
composed state exactly as they see a single profile.

Installation follows the operator's intent without magic: `curator profile
install <git-url>` installs every profile the repository declares as
independent pinned profiles — one repository MAY declare several (that is
what `Profilefile.json` is for), and profiles installed from any number of
repositories coexist as one machine profile set. `install` sets the current
profile only when the machine has none (first install — activation is
reported, not silent) or when the operator passes `--use <name>` (`--use`
alone is valid when the repository declares exactly one profile). In every
other case it prints the installed profiles and how to activate one.

**First-run onboarding.** A machine that already has hand-maintained global
context must reach managed state without loss and, in the common case,
without ceremony. Onboarding — run on bootstrap or on the first profile
operation that meets unmanaged state — proceeds:

1. **Inventory.** Detect, per adapter: existing unmanaged root-context
   files; existing global skills; and surfaces that are already symlinks
   pointing outside Curator's store — evidence of another manager, which
   stops onboarding with the finding and an explicit choice (abort, or take
   over with backup) rather than silently absorbing a foreign tool's state.
2. **Classification.** Report whether an import into managed state would be
   lossless (every detected surface maps onto a Curator-supported surface)
   or lossy (something detected — an unsupported surface, an unreadable
   file — would not carry over), naming exactly what would be lost.
3. **Consent gate.** A lossless import proceeds without stopping; a lossy
   import stops and asks with the loss list; either way the operator is told
   that the native global contexts are being replaced by Curator-managed
   ones and where the backup lands.
4. **Backup, always.** Every replaced file is backed up beside the
   environment marker before the first write, whether or not an import was
   requested.
5. **Import (optional).** The detected context is reassembled into a
   profile-shaped directory inside Curator's machine home, marked as
   imported-from-native, and installed through the ordinary profile pipeline
   with a directory path in place of a git URL — Decision 1's `path` source
   kind. Pre-existing globally installed skills import into that profile's
   Skillfile with a warning that they were managed by other means and SHOULD
   be re-declared from their upstream sources to receive updates.
6. Authentication is never part of import or takeover: credential files
   stay where the Decision 7 passthrough expects them, untouched.

Revision 1 ships steps 1–4 — detection, foreign-manager stop, backup, and
takeover are prerequisites for a safe `install` on a used machine. The
import machinery of step 5 (the `path` source kind, lossless/lossy
classification, native-skill migration) is designed here but delivered as
its own tracked story on this decision's epic, targeted between revisions 1
and 2.

### 6. Resolution primitive, umbrella subcommands, and the launcher

Curator's own execution surface is exactly one primitive:

- `curator env resolve <env-id> [--profile <name>] [--format json|env|shell]`
  resolves a profile to a **launch environment fragment**: the adapter's
  environment variable set to the managed-home path, the profile identity,
  effective commit, active composition chain, and fragment schema version,
  plus — when the profile carries system modules — an inert system-prompt
  section: the materialized system file's path and the adapter's declared
  channel descriptor (flag-class, configuration-key, or variable-class).
  `--format env` prints `NAME=value` lines; `shell` prints export
  statements; `json` prints the closed `launch-env-fragment-v1` object.
  Resolution verifies the managed home is materialized and current, and
  repairs it from the store when it is not.

Fragment variable names come from the closed adapter registry, and fragment
values are managed-home paths below the manager-owned environments root.
Profile bytes MUST NOT select an environment-variable name and MUST NOT
move a value outside that root; the only profile-derived component of a
value is the profile-name path segment, which the §2 identifier grammar
bounds — no separators, no traversal. A profile chooses what the context
says, never how the process is launched. This is the same package-influence
boundary the execution policies draw, applied to environment injection. The
system-prompt section is data about a channel, never an applied override:
resolving a fragment activates nothing.

**Umbrella subcommands.** Curator adopts the established external-subcommand
convention: a subcommand Curator does not implement resolves to an
executable named `curator-<name>` on `PATH` and is executed with the
remaining arguments — the `git`/`kubectl`/`docker` plugin model. Curator
knows only the discovery rule; it carries no knowledge of any provider. A
missing provider fails with the provider name and installation guidance.
The first two providers are `curator run` (the launcher below) and
`curator session` (a shim delegating to the `ax` agent session manager).

**The launcher (`curator run`).** Launching is not Curator's plane.
Executing an agent composes three independent contracts, and the launcher —
a separate component with its own repository and its own specification — is
their composer:

1. the **spawn plane** (the `agents-management` module): which agentic
   system, model, reasoning effort, and vendor, and whether provider limits
   admit a launch right now — consumed as a built launch plan
   (binary/argv/environment), never rebuilt;
2. the **context plane** (Curator): the fragment above, obtained through
   `curator env resolve --format json` and merged into the child
   environment;
3. the **session plane** (`ax`): when the machine has the `ax` integration
   configured, the launcher always launches through `ax`'s instrumentation
   so the session is tracked from birth — a configured integration is not a
   per-launch option, and bypassing it is a configuration change, not a
   flag. Without the integration the launcher execs directly.

The launcher holds no session state of its own — fire is the launcher's
verb, manage is `ax`'s — and it is the component that applies the
system-prompt channel: an explicit opt-in engages the fragment's channel
descriptor (`--system-prompt-file`-class arguments for `claude_code` and
`pi`, a `model_instructions_file` override for `codex_cli`, the
`GEMINI_SYSTEM_MD` variable once the `gemini` adapter lands), and every
activation prints a warning that the run's system prompt is customized,
that replacement channels discard the tool's built-in behavior entirely,
and that a custom system prefix can change how requests are cached and
therefore billed (Claude Code's default system prompt participates in
shared prompt caching; a custom one forms its own cache prefix — exact
per-tool behavior is open question 8's research). Without the opt-in,
managed homes carry no active system-prompt file — in particular pi's
`APPEND_SYSTEM.md`, which the tool applies unconditionally when present, is
materialized only under the per-profile×environment machine setting — and
native in-place homes never receive one at all (Decision 2). An operator
can always pass the tool's own flags by hand; the launcher's job is to make
the managed path explicit, warned, and reproducible, not to be the only
door.

In plain terms: `curator env resolve` answers "what would you set?" — it
prints the environment variables that point a tool at a profile home, for a
human to eyeball, a script to `eval`, or another tool to merge into its
spawn plan. `curator run` answers "just run it" — the operator types
`curator run codex_cli --profile companyA -- resume --last` and gets
exactly the codex they know, in the companyA home, on an admitted model,
tracked by `ax` when the integration is configured. Everything after `--`
belongs to the tool, untouched.

This decision fixes the umbrella name `curator run` and the boundary above;
the launcher's own specification defines its flags, its `agents-management`
consumption, its `ax` handoff, and its warnings, and this document does not
constrain them further.

### 7. Credentials and mutable state

Credentials are never profile content and never managed surfaces. Each
adapter declares its credential passthrough set — the auth entries a managed
home shares with the native home by symlink or seeding (`auth.json` for
`codex_cli` and `pi`; `claude_code` splits by platform — macOS Keychain
entries are ambient and need nothing, Linux keeps `.credentials.json` inside
the home and passes it through, and Windows needs the open question 6
verification; opencode keeps auth in the XDG data directory, which the
config swap never touches). Default is `shared`: every profile home reuses the
operator's existing authentication. A profile×environment pair MAY be
configured `isolated` — no passthrough, the tool authenticates fresh inside
the profile home — which is the supported shape for genuinely separate
accounts (a company profile on a company account beside a personal one).

Environment-owned mutable state (sessions, history, caches, trust records)
is never touched by materialization, refresh, switch, or garbage collection.
Session state living inside a profile home is a feature: a session created
under profile P resumes under profile P's home, which is exactly the
affinity the launcher and `ax` contract preserve.

### 8. Profile-scoped skills

The existing global scope becomes profile-scoped. Each profile's
`Skillfile.json` resolves through the unchanged closure, audit, build, and
runtime machinery; the resolved skills materialize into that profile's
managed homes and — for the current profile — the in-place adapter surfaces.
`curator global add|remove|…` continues to work against the current profile
and gains `--profile <name>` and `--all-profiles`; `curator profile sync`
re-materializes every installed profile across every registered adapter,
which is also the actualization path when a new adapter is registered on the
machine.

Migration: on first use of the profile surface, the existing machine-local
global scope is renamed into a builtin profile `default` with its current
Skillfile and no root context. `default` carries the source kind `local`
(Decision 1): no git identity, no pinned ref, no effective commit. Its
store key is the §8 content hash of its state (Decision 4), `profile list`
reports it accordingly (Decision 9), and switching, `profile sync`, and
`env status` treat a `local` profile exactly like an installed one. Nothing
else changes for a machine that never installs another profile — `default`
simply is the current profile, and existing global installations keep their
behavior byte-for-byte.

### 9. Inventory and status

`curator profile list` reports installed profiles: name, source identity,
pinned ref, effective commit, current marker; a `local` profile (Decision 8)
reports `local` as its source, `-` for ref, and its §8 state hash in the
effective-pin column. `curator env status [--check]
[--json]` reports the profile × environment × surface matrix: mode,
materialized commit, content-hash currency, drift, missing surfaces,
unregistered adapters, any declared shadowing path that exists (Decision
3), the active composition chain per activation, every scope whose current
profile differs from the machine default (Decision 5 scoped switching), and
secondary-target probe results, with the existing exit-code discipline
(`--check` non-zero on any non-current row). Both are read-only and follow
the manager §10 status discipline: recompute and report, never mutate.

### 10. Composition across the planes

Four components, four owners, and every contract between them is a CLI
invocation plus a closed object — no shared libraries, no import edges
between Curator, the launcher, `agents-management`, and `ax` beyond the
launcher's declared consumption of the `agents-management` module:

| Plane | Owner | Question it answers |
|---|---|---|
| Context | Curator | what the agent reads: profiles, homes, skills |
| Spawn | `agents-management` | who runs: system, vendor, model, effort, limits → launch plan |
| Session | `ax` | what happens to a running session: leases, checkpoints, resume |
| Execution | the launcher (`curator run`) | compose the three planes and exec |

Degradation is graceful in every direction. Curator alone: `env resolve`
plus in-place materialization — every natively started tool already sees
the current profile. `ax` alone: sessions against native homes, exactly as
today. The launcher without `ax`: resolve, plan, exec — untracked. With the
`ax` integration configured, the launcher always goes through `ax` and
every launch is tracked from birth (Decision 6).

For resume fidelity, the `ax` side SHOULD record the profile name, effective
commit, and fragment digest in its Session Record extensions at launch, and
re-resolve the same profile on resume. A resolved commit that differs from
the recorded one is drift: the recommended behavior is to warn and continue,
with a strict flag to refuse. Direction follows from state: session leases,
checkpoints, and takeover semantics are `ax`'s domain, while resolution is a
pure function from (profile, environment, machine config) to a fragment, and
the pure function belongs on the inside — `ax` and the launcher call
Curator, never the reverse. Merging any two of these components is rejected
(see Rejected alternatives); the umbrella subcommand convention of Decision
6 gives the operator one brand over four codebases without coupling one
release train to another.

Every change this decision asks of `ax` — the extension keys, the resume
drift policy, any fragment-consumption note — is delivered to the
`agent-session-manager-spec` repository as one detailed pull request opened
after this decision and its normative surfaces are finalized, never as
piecemeal edits; until that PR lands, nothing here constrains `ax`.

### 11. Revision phasing

| Surface | Revision 1 | Revision 2 | Revision 3 |
|---|---|---|---|
| Root context (IR → `CLAUDE.md`/`AGENTS.md`) | claude_code, codex_cli, opencode, pi | gemini, cursor | — |
| Root-context forms (Decision 2) | monolithic everywhere; referenced for claude_code, opencode | referenced for gemini as research admits | — |
| Composition (overlay profiles, chapters, precedence) | ✓ | — | — |
| System-prompt modules: materialization + fragment channel description | claude_code, codex_cli, pi (managed homes only) | gemini (`GEMINI_SYSTEM_MD`), opencode | embedded hosts, if open question 8 admits any |
| System-prompt application + warnings | launcher's own specification | — | — |
| Skills | already shipped; becomes profile-scoped | — | — |
| Profiles, switching (incl. scoped `--env`/`--target`), `env resolve`, fragments | ✓ | — | — |
| Umbrella subcommand discovery (`curator-<name>`) | ✓ | — | — |
| Launcher (`curator run`) and `curator session` shim | own repositories and specification, tracked on this epic | — | — |
| Onboarding: detect, foreign-manager stop, backup, takeover | ✓ | — | — |
| Onboarding import (`path` source kind, lossless/lossy, skill migration) | — | ✓ own story between rev 1 and 2 | — |
| Secondary fixed-home targets (Xcode CodingAssistant, auto-probed) | ✓ root context + skills | commands, MCP state | — |
| MCP server write management | read-only verification stays (manager §6) | ✓ own decision | — |
| Settings/permissions/model fragments | — | ✓ own decision | — |
| Prompts / commands surfaces | — | ✓ | — |
| Subagents | — | — | ✓ |
| Hooks | — | — | ✓ own security decision |
| Memory / knowledge | — | — | ✓ |
| Third-party adapter plugin contract | — | — | ✓ |
| Additional environments (copilot, goose, …) | — | — | as vendors permit |

MCP write management and hooks are explicitly deferred: both widen the attack
surface from "instructions an agent reads" to "processes a machine runs", and
each needs its own decision with audit rules before Curator writes a byte of
them. Revision 1 keeps MCP exactly where manager §6 has it — verified
read-only.

## Rejected alternatives

- **Status quo** — hand-synchronized homes. This is the problem, not an
  option; it has no provenance, no audit, no switching, and no determinism.
- **Shell-level workarounds as the mechanism** — aliases, direnv blocks, or
  wrapper scripts exporting `CLAUDE_CONFIG_DIR` by hand. They prove the
  demand but manage nothing: no ledger, no drift detection, no audit, no
  cross-environment consistency, and every user reinvents them.
- **`HOME` substitution as the primary mechanism.** It relocates every tool
  uniformly but drags `~/.gitconfig`, `~/.ssh`, npm state, and shell config
  with it and breaks Keychain-backed auth. It stays available to future
  adapters as an explicit last-resort mechanism for tools with no dedicated
  variable, never the default.
- **Launcher-only (no in-place modes).** Sessions started outside the
  launcher — a bare `claude` in a terminal, an IDE integration, Xcode's
  embedded agents — would see unmanaged homes forever. In-place
  materialization is what makes the default path managed.
- **In-place-only (no managed homes).** Switching becomes globally racy —
  every concurrent session on the machine flips context at once, which is
  exactly the failure the operator warning in Decision 5 exists for — and
  per-profile session-state isolation is lost. Both modes are required; each
  covers the other's blind side.
- **Symlink-only in-place materialization.** Fixed-home embedded
  environments and link-hostile tools exist today; `copied` mode with hash
  ledgers is the portable answer the adapter model already uses for skills.
- **Templating in the context IR.** Variables, includes, and conditionals in
  version 1 would buy convenience and cost determinism, auditability, and
  the byte-equality conformance surface. Ordered modules with environment
  selectors cover the known cases; a future revision can add more after real
  profiles show the need.
- **Making `ax` depend on Curator or Curator on `ax`.** Either direction
  couples release trains and forces both tools on users who want one. The
  fragment contract keeps each fully usable alone.
- **Merging `ax` under Curator as one specification and binary.** Considered
  explicitly and rejected in favor of the Decision 6 umbrella: the `ax`
  domain (leases, checkpoints, terminal backends, provider plugins) is a
  large, separately reviewed, actively evolving normative surface, and
  stapling it to this protocol's frozen-surface discipline would slow both.
  One brand over independent codebases delivers the "one full manager"
  experience without the coupling.
- **A rich launcher inside Curator.** An earlier draft of this decision had
  `curator launch` growing binary maps and system-prompt argv handling —
  spawn-plane concerns that belong to `agents-management` and to the
  launcher's own specification. Curator keeps exactly `env resolve`;
  `curator run` is umbrella discovery, not Curator code.
- **Curator-side session management.** Continue/resume UX beyond verbatim
  argument pass-through duplicates `ax`'s reason to exist; the execution
  plane deliberately stays a composer plus `exec`.

## Compatibility impact

Additive only. No existing portable object, schema, identifier, or behavior
changes. New separately versioned surfaces: `Profilefile.json` (profile
index, schema 1), `context.json` (context module manifest, schema 1), the
environment marker (`.agent-environment.json`, schema 1), and
`launch-env-fragment-v1`. Each gets a JSON
Schema under `schemas/v1/`, positive and negative conformance vectors, and —
for root-context materialization, including the generation header, chapter
composition, and both forms of Decision 2 — byte-exact determinism vectors. The new
filenames join the §1.1 compatibility identifier list. The manager profile
gains sections for the adapter registry, materialization modes, profile
lifecycle, launcher, and credential passthrough, and a secret-detection
detector class over context modules joins the manager §7 audit pipeline
(Decision 2); `cli/curator.md` gains the
informative command table. The capability lands as `protocol/environments.md`
in the pattern `assurance.md` established: a separately versioned document
that adds identities without widening existing objects. Managers that do not
implement it remain conforming skill managers; a manager that implements it
MUST implement the closed revision-1 surface exactly.

## Security impact

- Profile repositories pass the same gates as skill repositories: canonical
  source identity, allowlist, snapshot validation, and the manager §7 audit
  pipeline. Profile installation is always strict, and the Decision 2
  secret-detection detector class makes credential-like material a blocking
  finding instead of an unscanned surface. Root-context modules are prompt
  material and SHOULD be surfaced by audit tooling as such (prompt-injection
  review is human work; the pipeline guarantees provenance and immutability,
  not intent).
- No code execution: profiles are data end to end. No adapter, materializer,
  hook, or generator is ever selected by profile bytes.
- A system-prompt override is the sharpest instruction surface a profile
  carries, so it is inert by default: never materialized into a native
  in-place home, never applied by a plain launch, active only under the
  Decision 6 explicit opt-in with its warning, and every composed chapter
  and generation header keeps its provenance readable.
- Composition widens what one activation reads to several audited sources;
  each composed profile passes the gates independently, the declared
  precedence is stated in the generated output rather than resolved
  silently, and the composition chain is recorded in the marker and
  fragment, so status and resume always see exactly what was assembled.
- Environment-variable injection is bounded: fragment names come from the
  closed adapter registry and values are paths below the manager-owned
  environments root. Profile data cannot add, rename, or retarget a
  variable; its only reach into a value is the profile-name path segment,
  bounded by the §2 identifier grammar.
- In-place materialization keeps the §11 ledger guarantee: an unmanaged file
  is never overwritten; takeover is explicit and backed up. Secondary
  fixed-home targets live inside another application's support directory, so
  the guarantee matters doubly there: Curator touches only its ledgered
  surface entries and never the host application's own files (`.claude.json`,
  `config.toml`, caches) in revision 1.
- Credentials: never profile content — the always-strict install audit and
  the Decision 2 secret-detection detectors block credential-like material —
  and never copied between homes by default; `isolated` mode exists
  precisely so account separation does not degenerate into credential
  copying.
- The switch warning in Decision 5 is a real hazard, not ceremony: a live
  session under the old profile can still write trust records and state into
  in-place homes. The launcher path avoids the race entirely, which is why
  the warning recommends it.
- MCP write management and hooks are deferred because they change the threat
  model; each returns as its own decision with its own audit rules.

## Consequences

- Curator's machine home grows a commit-keyed profile store (state-hash-keyed
  for a `local` profile) and a managed
  environment-home tree; garbage collection gains their live roots (§9.4
  pattern).
- The manager §5 skills table becomes a special case of the adapter
  registry; the existing global scope becomes the `default` profile via the
  Decision 8 migration.
- `status` output, documentation, and conformance suites grow the
  environment matrix.
- `ax` gains an optional, contract-shaped integration and loses nothing when
  Curator is absent; once the integration is configured on a machine, the
  launcher path always runs through it.
- Two repositories are authorized alongside the normative work: the launcher
  implementation (consuming `agents-management` as a module and Curator/`ax`
  as CLI contracts) and its specification, per open question 1's layout
  recommendation; `curator session` ships as a thin shim from the `ax` side.
- Multi-machine profile distribution needs no new mechanism: profiles are
  git repositories; installing the same pinned profiles on another machine
  is the sync story.

## Open questions

1. **Launcher specification home and `agents-management` decomposition.**
   The launcher needs its own specification, and its implementation
   repository is new; three layouts compete: (a) specification and
   implementation inside the existing `skill-agents-management` repository;
   (b) a full split of that repository into library, CLI, and skill; (c) a
   new launcher repository consuming `agents-management` as a Go module,
   with the specification either in a sibling `-spec` repository (the
   `curator-spec` / `agent-session-manager-spec` pattern) or as an in-repo
   draft promoted to a `-spec` repository at stabilization.
   Recommendation: (c) — the launcher composes three planes and must not
   live inside one of them, and `skill-agents-management` stays unsplit
   until a consumer besides the launcher needs its CLI apart from its
   module, since a Go module imports cleanly from a skill-carrying
   repository today and a second consecutive extraction without a second
   consumer is decomposition ahead of evidence.
2. **`Profilefile.json` vs directory-convention discovery.** Recommendation:
   the strict descriptor file — discovery-by-layout invites accidental
   profiles and unvalidated shapes.
3. **Module manifest vs frontmatter.** Recommendation: the `context.json`
   manifest — YAML frontmatter inside modules would leak into materialized
   output or require stripping, and stripping breaks byte-opacity.
4. **opencode skills placement.** Whether the opencode adapter's skills
   surface moves into `<home>/skills/` (config-dir native) or keeps the
   `.agents/skills` native surface of manager §5 needs implementation-time
   verification against a pinned opencode release. Recommendation: keep the
   manager §5 native surface until a pinned release proves `<home>/skills/`.
5. **`ax` extension fields.** Exact Session Record extension keys for
   profile name, commit, and fragment digest, and whether resume drift
   defaults to warn-and-continue (recommended) with a strict refuse flag —
   to be settled with the `ax` spec once revision 1 stabilizes.
6. **Windows and embedded-target verification.** The four revision-1
   variables inject identically on Windows, but opencode's `XDG_CONFIG_HOME`
   behavior and the claude_code credential passthrough shape there (Decision
   7) need platform evidence before the conformance vectors freeze. The
   Xcode secondary-target homes are recorded (`ClaudeAgentConfig/` with
   `.claude.json`, `skills/`, `commands/`; `codex/` with `config.toml`), but
   the CodingAssistant parent path, the Xcode 26.3 attribution, and whether
   the embedded Codex honors `AGENTS.md` from its fixed home exactly as
   `CODEX_HOME` semantics imply need implementation-time verification
   against a pinned Xcode release. Recommendation: hold the
   conformance-vector freeze on that platform evidence and draft against the
   recorded shapes meanwhile.
7. **Import semantics per environment.** claude_code `@path` imports
   (documented, five hops, external-include approval in `.claude.json`) and
   opencode `instructions` lists are recorded; whether gemini's `GEMINI.md`
   import mechanism is real and stable enough for a `referenced` form, and
   whether codex or pi grow one, is research to complete before the
   `referenced` conformance vectors freeze. Recommendation: ship revision 1
   with the two verified referenced targets and re-survey at revision 2.
8. **System-prompt channels: exact behavior and embedded hosts.** Per-tool
   research to finish before the system-module vectors freeze: the precise
   cache/billing consequence of a custom system prompt per tool (Claude
   Code's shared-prompt-cache interaction is the recorded example), whether
   codex's `model_instructions_file` is injectable per-invocation through
   its `-c` override safely, and whether any embedded host — the Xcode
   CodingAssistant agents first — exposes a system-prompt override channel
   at all (none is currently recorded; claude_code output styles inside
   `ClaudeAgentConfig/` are the one candidate worth testing).
   Recommendation: keep system modules launcher-only and
   managed-home-only exactly as Decision 2 states until this research
   lands; never widen activation to native homes on partial evidence.
