# Curator Manager Profile 1.0

This document is normative for implementations claiming the **manager**
conformance class. It defines behavior around the portable objects in the
protocol core. It does not prescribe an executable name or machine-home path.

## 1. Machine state and configuration

Each manager selects its own `<manager-home>`, user-config environment
variable, and system-config path. It MUST document them and MUST keep its
caches, runtime store, audit state, and global/hybrid state below that home.
Different implementations do not share machine-local state by default.

The logical user configuration conforms to `manager-config-v1.schema.json` and
contains a source root, project registrations, manager defaults, source
allowlist, audit policy, and pinned registries. The configuration file SHOULD be
readable and writable only by its owner where the platform supports
permissions.

Managers MUST reject unknown configuration fields and apply schema defaults
before use. `projects` member names, `project_alias`, and `checkout_alias` are
portable identifiers; the latter two default to the member name when absent or
null. They are derived machine matching keys, distinct from the operator-facing
Unicode `Skillfile.json` `project.alias`. Agent lists are sets of portable
identifiers. `preferred_locale: null` means no machine preference.

An audit registry requires `name` and canonical `url`; `public_keys` defaults to
an empty set and `enabled` defaults to true. A registry with no pinned key is
not trusted and produces a warning. Registry record cache TTL defaults to 3600
seconds, offline grace to 604800 seconds, snapshot maximum age to 604800
seconds, and future clock skew to 300 seconds. Zero cache TTL disables fresh
cache hits; zero offline grace disables stale fallback; zero clock skew permits
no future offset. The backend request limit defaults to 1048576 bytes and MUST
NOT exceed 10485760 bytes.

An OPTIONAL system configuration conforms to `system-config-v1.schema.json`
and is merged before parsing the effective user configuration:

1. `locked` contains only `audit_registries`,
   `disable_builtin_registries`, `allowed_sources`, and `audit`;
2. a locked key MUST be set by the system file and overrides a user value with
   a warning naming the system file;
3. an unlocked system key is a default and a user value wins;
4. malformed or unreadable enforced configuration fails closed.

Configuration writes MUST use a same-directory temporary file followed by
atomic replacement. Implementations SHOULD serialize concurrent writers with a
per-config lock and MUST never expose a partially written JSON object.

## 2. Installation lifecycle

For each project, the manager performs these phases in order:

1. load `Skillfile.json`, or skip an absent manifest;
2. determine effective agents and locale;
3. verify generated project and adapter paths are ignored by git;
4. load development substitutions and reject them under strict audit;
5. add applicable hybrid declarations;
6. build the dependency closure, including allowlist and snapshot checks;
7. validate every skill package and manifest;
8. reject active command collisions;
9. verify system and legacy command dependencies;
10. verify MCP requirements and emit static availability warnings;
11. run source-audit policy;
12. resolve trusted audit registries and reject revocation or strict unknown;
13. detect moved tags;
14. stop before mutation for a dry run;
15. materialize runtime, context, markers, environment files, and adapters;
16. remove stale managed skills and shims;
17. record the consumer and collect unreferenced runtime/cache entries.

A failure before phase 15 MUST leave the existing installation unchanged. A
failure during materialization MUST roll the affected target back to its
previous complete state. A manager MUST serialize concurrent installation of
the same project. It MAY install independent projects concurrently.

The managed `.gitignore` comment is implementation-specific. Conformance
depends on the generated paths being ignored, not on comment spelling.

## 3. Runtime and project environment

Runtime files are machine-local and keyed by skill name and resolved commit.
Context installs under `.agents/skills/<name>/`; command shims install under
`.agents/bin/`. Runtime-only nodes receive a marker-only directory and are not
mirrored into agent adapters.

Runtime roots are copied atomically. An existing commit-keyed entry MAY be
reused only after verifying that every required path exists. Unix shims are
relative symlinks to executable runtime files. Windows shims are `.cmd`
wrappers that quote the runtime path and forward all arguments. Stale shims
owned by the previous plan are removed.

`.agents/env.sh` and `.agents/env.ps1` prepend `.agents/bin` to `PATH` and set
the portable `CSK_PROJECT_ROOT` to the resolved project root. They MUST locate
themselves rather than rely on the caller's current directory. A manager MAY
also set tool-specific variables.

## 4. Install scopes

### 4.1 Project

Project declarations materialize inside the project checkout. Different
projects may install different commits independently.

### 4.2 Global

Global declarations use a machine-local `Skillfile.json`, context store,
runtime shims, and environment files. Their physical location is
implementation-specific. Global adapters mirror to each selected agent's home
discovery directory. Global command precedence is below project shims and above
the pre-activation system `PATH`.

### 4.3 Hybrid

A hybrid manifest extends Skillfile schema 1 with REQUIRED per-skill `targets`.
A target is a project alias, exact resolved path, or path glob. The glob syntax
is `/`-separated and implements only `*`, `?`, and `**`; matching is
case-sensitive and does not depend on the host OS.

Applicable hybrid declarations join the project closure. Precedence is
project, hybrid, global. Project declarations shadow hybrid declarations with a
message. Hybrid-only closure nodes render once in a machine store with the
machine locale and are mirrored into targeted project adapters without writing
skill context into the project checkout.

## 5. Agent adapters

The standard agent identifiers and discovery surfaces are:

| Agent | Project surface | Global surface |
|---|---|---|
| `claude_code` | `.claude/skills` | `~/.claude/skills` |
| `codex_cli` | `.codex/skills` | `~/.codex/skills` |
| `cursor` | `.cursor/rules` | `~/.cursor/rules` |
| `gemini` | `.gemini/skills` | `~/.gemini/skills` |
| `opencode` | native `.agents/skills` | `~/.agents/skills` |
| `windsurf` | native `.agents/skills` | `~/.agents/skills` |

Adapter entries are symlinks, copies, or automatic symlink-with-copy-fallback.
Every root carries the adapter ledger from Protocol Core section 10. Refresh is
atomic per entry. Unknown agent identifiers produce a warning and no output.

## 6. MCP requirements

MCP verification is read-only. A manager MUST NOT launch, install, enable, or
modify an MCP server while checking a skill requirement.

| Agent | Project surface | User surface |
|---|---|---|
| `claude_code` | `.mcp.json` | `~/.claude.json` |
| `cursor` | `.cursor/mcp.json` | `~/.cursor/mcp.json` |
| `codex_cli` | `.codex/config.toml` | `~/.codex/config.toml` |
| `gemini` | `.gemini/settings.json` | `~/.gemini/settings.json` |
| `opencode` | `opencode.json`, `opencode.jsonc` | `~/.config/opencode/opencode.json(c)` |
| `windsurf` | none | `~/.codeium/windsurf/mcp_config.json` |

JSON surfaces use `mcpServers`, Codex TOML uses `mcp_servers`, and OpenCode uses
`mcp`. A disabled entry does not count. Missing or malformed files configure no
servers and produce a warning naming the file.

`required_in: any` succeeds when at least one target agent configures the
server. `all` requires every target. Failures name missing agents and include
the declared hint. Markers record sorted agents where each server was found.

A configured stdio server whose command is absent from `PATH` produces a
warning when every discovered entry is positively stdio. Project-only server
configuration produces a checkout-trust warning.

## 7. Source audit policy

Source audit is a machine-local policy layer. Detectors and analysis backends
may differ; decisions do not.

For each snapshot a manager computes the raw-tree content hash, runs a static
canary, runs deterministic detectors, optionally invokes a configured backend,
and records findings. A canary failure always blocks. Cloud backends receive
only sources classified public by explicit policy; other egress attempts block.
Secret redaction is REQUIRED before permitted cloud egress.

Decisions are `allow`, `warn`, `block`, or `require_pin`:

- local hash or source revocation always blocks;
- strict mode requires an operator pin for pre-capability schemas;
- a verifiable finding at or above `fail_on` blocks in strict mode;
- advisory mode warns;
- backend failure blocks in strict mode and warns in advisory mode;
- `block` and `require_pin` fail installation.

Pins record content hash, operator identity, reason, and creation time. Pins do
not override local or registry revocation.

## 8. Shell activation

Shell activation searches upward from the current directory for the nearest
`.agents/env.sh` or `.agents/env.ps1`. Entering or switching projects restores
the saved pre-project `PATH` before sourcing the new environment. Leaving all
projects restores that `PATH` and clears activation state. Nested projects use
the nearest environment.

Bash integrates through `PROMPT_COMMAND`; zsh integrates through `precmd` and
`chpwd`; PowerShell wraps the existing global `prompt` function while
preserving its output and invokes activation before each prompt. Hook
installation also invokes activation once immediately. Re-loading a hook MUST
NOT stack duplicate wrappers or PATH entries.

Global activation is OPTIONAL and enabled by default by conforming CLI
profiles. It is sourced once per global environment version and has lower PATH
precedence than a project environment.

## 9. Status and garbage collection

Read-only status validates marker schema, recomputes content hashes, reports
manifest and activation drift, and MAY re-resolve registry attestations. A
check mode returns non-zero for drift without mutating state.

Garbage collection scans registered consumers and valid markers. It removes
only machine-local runtime and snapshot entries not referenced by any existing
consumer. Unreadable consumer state fails safe: uncertain entries are retained.
