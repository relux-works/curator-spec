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
carry over unchanged. Decision 8 admits one additional source kind, `local`,
reserved for the builtin migration profile.

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
`environments` selector: a set of environment identifiers, or the wildcard
default meaning every environment. Version 1 is deliberately minimal —
ordered concatenation with per-module environment selection. There is no
templating, no variable substitution, no conditional syntax inside module
bytes, and no per-module remote inclusion. A module is UTF-8 markdown.
Snapshot validation rejects a module that is not valid UTF-8, contains a
line ending other than LF, or does not end with exactly one trailing LF —
the fail-closed posture of the other strict schema surfaces, chosen over
silent normalization. A module that validates is thereafter treated as
opaque bytes: materialization never rewrites it.

Materialized root context is deterministic: the applicable modules in
manifest order, joined by exactly one empty line (a single additional LF
between modules), with no other transformation. Because every module ends
with exactly one LF, the output is LF-encoded and ends with exactly one
trailing LF by construction. The output is hashed with the §8 content
hash; identical profile commit plus identical adapter set yields
byte-identical output on every platform. Determinism is what makes drift
detection and `status --check` possible, and it is a conformance-vector
surface.

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
surface; the surfaces it supports per revision; the credential passthrough
entries of Decision 7; the materialization-mode default of Decision 4; its
known shadowing paths — higher-precedence unmanaged files whose presence
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
  being silently overwritten.

Mode defaults: the four native-home adapters default to `linked` for their
in-place surfaces — the manager §5 symlink-with-copy-fallback discipline
unchanged — secondary fixed-home targets default to `copied`, and managed
homes always link from the store. An adapter MAY declare a different
in-place default; the declaration lives in the adapter registry, never in
profile data.

Every in-place surface is recorded in a per-home **environment marker**
(`.csk-environment.json`, schema 1) alongside the generalized ledger:
profile identity, source identity, effective commit, mode, and per-surface
content hashes. The §11
rule extends unchanged: Curator removes or replaces only entries its
preceding ledger owns and MUST fail rather than overwrite an unmanaged file.
A pre-existing unmanaged `~/.claude/CLAUDE.md` is never clobbered; the
operation fails with guidance to either move the file into a profile
(adoption) or pass an explicit takeover flag that backs the file up beside
the marker.

Both in-place modes and managed homes materialize from the same commit-keyed
profile store, so `linked`, `copied`, and `managed-home` cannot diverge for
one profile commit. A `local` profile (Decision 8) is keyed in the same
store by the §8 content hash of its state in place of a commit; the
non-divergence guarantee holds identically.

### 5. Current profile and switching

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

Installation follows the operator's intent without magic: `curator profile
install <git-url>` installs every profile the repository declares as
independent pinned profiles. It sets the current profile only when the
machine has none (first install — activation is reported, not silent) or when
the operator passes `--use <name>` (`--use` alone is valid when the
repository declares exactly one profile). In every other case it prints the
installed profiles and how to activate one.

### 6. Launcher

Two commands, one contract:

- `curator env resolve <env-id> [--profile <name>] [--format json|env|shell]`
  — the composable primitive. Resolves a profile to a **launch environment
  fragment**: the adapter's environment variable set to the managed-home
  path, plus the profile identity, effective commit, and fragment schema
  version. `--format env` prints `NAME=value` lines; `shell` prints export
  statements; `json` prints the closed `launch-env-fragment-v1` object.
  Resolution verifies the managed home is materialized and current, and
  repairs it from the store when it is not.
- `curator launch <env-id> [--profile <name>] [--] <native args…>` — resolves
  the fragment, merges it into the inherited environment, and replaces itself
  with the environment's native executable, forwarding the argument vector
  verbatim with no reinterpretation. Resume flags, prompts, and every other
  native argument pass through untouched; launch adds no shell between the
  operator and the tool.

Fragment variable names come from the closed adapter registry, and fragment
values are managed-home paths below the manager-owned environments root.
Profile bytes MUST NOT select an environment-variable name and MUST NOT
move a value outside that root; the only profile-derived component of a
value is the profile-name path segment, which the §2 identifier grammar
bounds — no separators, no traversal. A profile chooses what the context
says, never how the process is launched. This is the same package-influence
boundary the execution policies draw, applied to environment injection.

The command names above are the contract; a short standalone alias
(`cual`-style) is packaging and deliberately not decided here (open question
1).

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
unregistered adapters, and any declared shadowing path that exists
(Decision 3), with the existing exit-code discipline (`--check`
non-zero on any non-current row). Both are read-only and follow the manager
§10 status discipline: recompute and report, never mutate.

### 10. Composition with the agent session manager

Curator and `ax` compose without depending on each other; the entire
contract is one closed JSON object and one CLI invocation.

- **Standalone Curator**: `curator launch` execs the tool directly. No `ax`,
  no session tracking — fine for everyday use.
- **Standalone ax**: sessions launch against native default homes, exactly as
  today. No Curator, no profiles.
- **Composed**: `ax` is the outer layer and owns the session lifecycle;
  Curator is the inner resolver and owns environment resolution. An `ax`
  integration (host logic or provider plugin) obtains the fragment by
  invoking `curator env resolve <env> --profile <p> --format json` and merges
  the fragment's variables into the `SpawnPlan` `env_literals` it already
  emits. The fragment is stateless and idempotent; the session state lives
  where it already lives, in `ax`.

For resume fidelity, the `ax` side SHOULD record the profile name, effective
commit, and fragment digest in its Session Record extensions at launch, and
re-resolve the same profile on resume. A resolved commit that differs from
the recorded one is drift: the recommended behavior is to warn and continue,
with a strict flag to refuse. The recommendation direction — `ax` calls
Curator, never the reverse — follows from state: session leases,
checkpoints, and takeover semantics are `ax`'s domain, while resolution is a
pure function from (profile, environment, machine config) to a fragment, and
the pure function belongs on the inside. `cual`-style wrapping of `ax` is
rejected as a dependency direction (see Rejected alternatives), not as a
workflow: an operator can still type one command, because the `ax` side is
free to expose profile selection in its own UX.

### 11. Revision phasing

| Surface | Revision 1 | Revision 2 | Revision 3 |
|---|---|---|---|
| Root context (IR → `CLAUDE.md`/`AGENTS.md`) | claude_code, codex_cli, opencode, pi | gemini, cursor | — |
| Skills | already shipped; becomes profile-scoped | — | — |
| Profiles, switching, launcher, fragments | ✓ | — | — |
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
- **Curator-side session management.** Continue/resume UX beyond verbatim
  argument pass-through duplicates `ax`'s reason to exist; `curator launch`
  deliberately stays a resolver plus `exec`.

## Compatibility impact

Additive only. No existing portable object, schema, identifier, or behavior
changes. New separately versioned surfaces: `Profilefile.json` (profile
index, schema 1), `context.json` (context module manifest, schema 1), the
environment marker (`.csk-environment.json`, schema 1), and
`launch-env-fragment-v1`. Each gets a JSON
Schema under `schemas/v1/`, positive and negative conformance vectors, and —
for root-context materialization — byte-exact determinism vectors. The new
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
  Curator is absent.
- Multi-machine profile distribution needs no new mechanism: profiles are
  git repositories; installing the same pinned profiles on another machine
  is the sync story.

## Open questions

1. **Launcher alias naming.** `curator env resolve` / `curator launch` are
   the contract; is a short standalone binary (`cual`, `agx`, …) wanted at
   revision 1, and under what name? Recommendation: ship the subcommands
   first; decide the alias in packaging once the contract is exercised.
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
7. **`pi` `APPEND_SYSTEM.md`.** pi reads an additional system-prompt append
   file from its agent dir; whether the IR grows a distinct `append_system`
   module class for it in revision 1 or the surface waits — recommendation:
   wait; one root-context class keeps revision 1 small.
