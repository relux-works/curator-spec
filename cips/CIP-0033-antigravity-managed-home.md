# CIP-0033: Antigravity CLI (`agy`) managed home, flag home transport, and credential contracts

- **Status:** Review
- **Normative text:** [Antigravity managed-home contract](../protocol/antigravity-managed-home.md), [Environments sections 7.1-7.2, 7.4-7.5, 7.7-7.9, 10.2-10.3, 10.5](../protocol/environments.md), [v7 / snapshot-v2 schemas](../schemas/antigravity-managed-home-v1/README.md), [conformance corpus](../conformance/antigravity-managed-home-v1/README.md).
- **Owner:** Ivan Oparin (Curator Core spec custody)
- **Created:** 2026-11-24
- **Related:** CIP-0010 (authentication nodes and inherited auth), CIP-0014 (managed-home snapshots), CIP-0015 (login readiness), CIP-0017 (Muse credential store and fragment discipline), CIP-0002 (project context -- deferred to Phase 2)
- **Affects:** environments sections 7.1, 7.2, 7.4, 7.5, 7.7, 7.8, 7.9, 10.2, 10.3, 10.5; managed-home-snapshots; login-readiness; local-setup-token-source; implementations: curator, skill-agents-management, curator-agent-launcher

## Summary

This proposal adds `antigravity` (CLI alias `agy`, Antigravity CLI) as a
`managed-home`-only environment adapter with **flag-transported home
relocation** (`--gemini_dir`), file-backed OAuth isolation
(`AGY_CLI_FORCE_FILE_TOKEN_STORAGE=true`), additive global-rule shadowing
checks, a 24,000-byte root-context advisory, and file-channel MCP delivery
(`config/mcp_config.json`).

To keep all released schemas byte-frozen, this proposal allocates closed
successors `launch-env-fragment-v7` (adding `home: {"path", "transport": "flag"}`
and `node-source-v2`) and `snapshot-launch-v2` (carrying `home: {"path": "home",
"transport": "flag"}` with empty `env: {}` and zero credential policy). It also
defines both deterministic headless node credential channels (`gemini-api-key`
and `google-adc-file`) while honestly keeping `credential-injection/1`
**unqualified (`credential_injection_unavailable`)** on `agy 1.5.16` whenever
`stdio` MCP servers, hooks, or shell children are enabled, because live probes
on both macOS ARM64 and Linux x86_64 confirmed that `agy 1.5.16` inherits
`GEMINI_API_KEY` into `stdio` MCP child processes.

Project-context / Werkstatt integration (`CIP-0002` `memory-off`,
manager-programmed permissions, and `strict` native workspace exclusion) is
explicitly tracked as **Phase 2** using the live reconnaissance (`P9`) already
recorded in this CIP.

## Motivation and user stories

Operators use Antigravity CLI (`agy`) alongside Claude Code, Codex CLI, Muse,
Pi, and OpenCode. Today `agy` shares `~/.gemini` with Gemini CLI and the
Antigravity IDE, reads `~/.agents/skills`, and defaults to a user-global macOS
Keychain entry (`service="gemini"`, `account="antigravity"`). Replacing `HOME`
is prohibited by [environments section 7.1 / section 10.2](../protocol/environments.md)
because it breaks `git`, `ssh`, and every other child tool.

Operators need:
1. Per-profile managed homes for `agy` without touching shared `~/.gemini` or
   leaking stale `~/.agents/skills`.
2. Isolated per-profile logins (multiple Google accounts on one macOS user) and
   explicit file-backed shared logins without Keychain interference.
3. Portable managed-home snapshots (`curator env materialize`) with zero
   credential policy or mutable tool state.
4. Typed headless credential contracts (`gemini-api-key` and `google-adc-file`)
   under CIP-0010 L5/L6/L7, failing closed until runtime child-env leakage is
   eliminated.

## Current state

### Baselines

- `curator-spec`: commit `cded012` (latest CIP: `CIP-0032`; latest fragment
  revision: `launch-env-fragment-v6`; latest snapshot descriptor:
  `snapshot-launch-v1`).
- `curator`: commit `c1a79cae1` (no `antigravity` or `agy` adapter in
  `internal/envregistry`, `internal/envprofile`, `internal/envfragment`, or
  `internal/envsnapshot`).
- `skill-agents-management` (SAM): commit `937d672` (`v0.5.78`).
  `pkg/agentic/systems/agy/agy.go` declares stale `--mcp-config`,
  `EffortTransportNone`, `HomeEnvVar: ""`, unfiltered `ChildEnv`, no
  interactive mode, and outdated `gemini-3.x` models.
- `curator-agent-launcher`: commit `13800a0`. `internal/defaults/lineup.go`
  registers `antigravity` only to satisfy the `google` vendor contract and
  maps no Curator launches to it.

### Verified empirical evidence (`agy 1.5.16`, 2026-11-24)

Read-only binary inspection (`agy 1.5.16` Mach-O arm64) followed by live
disposable-runner probes (`P0-P9`, `Q2-Q4`) on GitHub Actions `macos-15`
(`macOS-15.8.2-arm64`, SHA-256
`b746bd68eb150f594e53af1e5577c8b101eaf33bd44ca10ac683af90e0630cf3`) and
`ubuntu-latest` (`Linux x86_64`, glibc 2.43, SHA-256
`05245f4346d16b679fd059a73081af0161607a76b4a164642bd007430934e785`) in
`relux-works/curator-spec` on temporary branch `probe/agy-managed-home-ci`
(deleted immediately after capture; runs `45378215323`, `45379392288`,
`45380774715`) established identical behavior across both platforms:

- **Home relocation (`P0`, `P6`):** Root CLI accepts `--gemini_dir=<abs>`
  (underscore only; `--gemini-dir` exits 2). `agy acp --login` accepts
  `--gemini-dir` / `--gemini_dir`. Subcommands (`agy mcp list`, `agy plugin
  list`) honor `--gemini_dir` only when placed **before** the subcommand.
  `ANTIGRAVITY_GEMINI_DIR` is ignored by the CLI (read only by plugin shims).
  Across all runs, zero files were written to `~/.gemini` or
  `~/.config/antigravity`.
- **Global rules and shadowing (`P1a-P1j`, `P2a-P2b`):** All five global paths
  (`config/AGENTS.md`, `config/GEMINI.md`, `config/rules/*.md`,
  `<home>/GEMINI.md`, `<home>/AGENTS.md`) load and **merge additively**;
  none shadows another. Symlinks targeting files outside `--gemini_dir` load
  identically to regular files (`P1f-P1h`). A 24,847-byte rule file loaded its
  head marker and truncated its tail marker (`P2a`), confirming the documented
  24,000-byte per-file cap. Relative at-include directives (syntax
  `@[label]` with `./part.md`) in `config/AGENTS.md` resolve relative to
  `<gemini_dir>` rather than `config/`, whereas absolute at-include targets
  expand arbitrary external files (`P2b`).
- **Skills isolation (`P3a-P3b`):** `config/skills/` loads both symlinked and
  copied skill directories. When `filepath.Base(geminiDir) != ".gemini"` (for
  example basename `antigravity`), `~/.agents/skills` is completely skipped
  (`P3a`: zero native leak). When basename equals `.gemini`, `agy` reads sibling
  `<parent>/.agents/skills`, not `$HOME/.agents/skills` (`P3b`).
- **File token storage and Keychain bypass (`P4a-P4c`):** On macOS with a
  synthetic Keychain entry (`service="gemini"`, `account="antigravity"`),
  `AGY_CLI_FORCE_FILE_TOKEN_STORAGE=true` bypassed Keychain completely (`P4a`:
  `composite_token_storage.go:207`), while `false` read Keychain (`P4b`).
  A symlinked `antigravity-cli/antigravity-oauth-token` was read through the
  symlink without unlinking it (`P4c`). Live OAuth token refresh write behavior
  remains unmeasured (static inspection shows in-place `os.WriteFile(..., 0600)`
  without a lockfile).
- **Plugin secret storage residual (`P4d`):** On Linux, `auth_store.go:199`
  stores plugin secrets at `$XDG_CONFIG_HOME/antigravity/plugin-secrets.json`
  (defaulting to `~/.config/antigravity/plugin-secrets.json`). Setting
  `XDG_CONFIG_HOME` redirects it inside the managed home, while macOS uses
  Keychain plus `~/Library/Application Support/antigravity/`. Phase 1 leaves
  `XDG_CONFIG_HOME` untouched so agent-spawned tools (`git`, `gh`, `gcloud`)
  keep reading operator config, recording plugin secrets as an explicit
  unmanaged-plugin residual.
- **`GEMINI_API_KEY` activation and `AGY_ADC_AUTH` conflict (`P0`, `P4e`,
  `Q2a-Q2b`, `Q4`):** Exporting `GEMINI_API_KEY` alone does **not** activate
  API-key auth (`rc=1`). `main.geminiAPIRoutingDecision` requires
  `modelProvider: "gemini"` via `--settings '{"modelProvider":"gemini"}'` or
  `antigravity-cli/settings.json`, and fails closed (`rc=1`) when
  `modelProvider: "gemini"` is set without `GEMINI_API_KEY`. `--settings`
  accepts inline JSON or a file path (`Q2a`), does not persist overrides into
  `settings.json` (`Q4`, though `agy` sparse-marshals defaults out of
  `settings.json`), and is **last-wins** when repeated (`Q2b`). When both
  `AGY_ADC_AUTH=true` and `modelProvider: "gemini"` + `GEMINI_API_KEY` are
  present, **`AGY_ADC_AUTH` wins precedence** (`P4e`).
- **MCP isolation and `stdio` env leakage (`P5`):** Native
  `~/.gemini/config/mcp_config.json` never started (`native_mcp_started: false`).
  Managed `<home>/config/mcp_config.json` started, initialized, and executed
  `tools/call` (`rc=0`). However, the `stdio` MCP child process inherited the
  full parent environment, including **`GEMINI_API_KEY`** (`has_gemini_api_key:
  true`) on both macOS and Linux. Static inspection found no child-env
  scrubbing in `agy 1.5.16`.
- **Auto-update, onboarding, and builtin skills (`P0`, `P8`, `Q3`):**
  `AGY_CLI_DISABLE_AUTO_UPDATE=true` disables the updater (`auto_updater.go:285`).
  `antigravity-cli/cache/onboarding.json` (`0600`) carries three booleans
  (`consumerOnboardingComplete`, `enterpriseOnboardingComplete`,
  `onboardingComplete`); headless `-p` succeeds with all three `false`.
  Builtin skills load by default (`P8a`), and `--settings` rejects both
  `includeDefaultCustomizations` and `pluginControls` as unknown settings.
- **Phase 2 workspace reconnaissance (`P9a-P9b`):** On a workspace containing
  `AGENTS.md`, `GEMINI.md`, `.agents/skills/`, and `.agents/plugins/*/{rules,
  mcp_config.json}`, `agy 1.5.16` loaded all five workspace surfaces
  automatically, including **starting the workspace plugin `stdio` MCP server**,
  with no CLI flag to suppress them.

## Design

### Options considered

#### Home relocation transport

| Option | Mechanism | Pros | Cons | Security |
|---|---|---|---|---|
| A: wait for upstream env var | Wait for `agy` to honor `ANTIGRAVITY_GEMINI_DIR` in CLI | Uses existing env-only fragment shape | Indefinite upstream block; `ANTIGRAVITY_GEMINI_DIR` is confirmed ignored by `agy 1.5.16` | Delays isolation while operators run on shared `~/.gemini` |
| B: override `HOME` | Set `HOME=<managed-home>` | Needs no flag | Violates environments sections 7.1 and 10.2; breaks `git`, `ssh`, and every child tool | High collateral blast radius |
| C: typed flag home transport (`home: {path, transport: "flag"}`) | Emit typed `home` binding in `launch-env-fragment-v7` and `snapshot-launch-v2`; SAM renders `--gemini_dir` | 100% consistent with Decision 0013 D5; zero `HOME` mutation; zero writes to `~/.gemini`; fails closed on `--format env|shell` | Requires coordinated v7/snapshot-v2 consumers | Closed schema rejects unknown revisions and conflicting `--gemini_dir` / `--app_data_dir` in `NativeArgs` |

Recommend **Option C**.

#### `AGY_CLI_DISABLE_AUTO_UPDATE` placement

| Option | Mechanism | Pros | Cons |
|---|---|---|---|
| A: put in `fragment.env` | Emit two constants in `fragment.env` | Visible in JSON fragment | Widens environments section 10.3 beyond credential-backend exception; absent from `snapshot-launch-v2` (`env: {}`) |
| B: put in SAM `systems/agy/env.go` (`ChildEnv`) | Own plugin literal in SAM | Applies uniformly across direct, snapshot, and `local-final-exec` runs; preserves section 10.3 single-constant discipline | Lives in SAM plugin rather than fragment |

Recommend **Option B**.

### Recommendation

#### 1. Adapter registration and managed-home layout

- Canonical environment ID: `antigravity`; CLI alias: `agy`.
- Mode scope: `managed-home`-only (never writes in-place to `~/.gemini`,
  matching Muse).
- `HomeTransport`: closed enum `"env"` (existing five adapters) | `"flag"`
  (`antigravity`). `nativeHome("antigravity")` is `<userHome>/.gemini`.
- Path-isolation and basename invariants: the managed home MUST NOT resolve
  (including through symlinks or case-insensitive filesystem aliases) to,
  contain, or lie inside the native `~/.gemini` directory. In addition, the
  managed-home leaf directory basename MUST NOT be `.gemini` (Curator uses
  `antigravity`), guaranteeing `~/.agents/skills` is not scanned.
- Managed surfaces:
  - `root-context`: `config/AGENTS.md`, `monolithic` only, symlink (or copy
    fallback), `root_context_size_advisory_bytes = 24000`.
  - Shadowing (environments section 7.5): `config/GEMINI.md`, `config/rules`, `GEMINI.md`,
    `AGENTS.md` (all four merge additively and must report
    `environment_shadowing_path_present` when present).
  - `skills`: `config/skills/` (`<name>/SKILL.md`, symlink or copy). Project
    scope `.agents/skills/` is added to `NativeDiscoveryAgents`.
  - `system-prompt`: none.
  - `mcp`: `config/mcp_config.json` (`{"mcpServers": {...}}`, `0600`), channel
    `{"kind": "file", "filename": "config/mcp_config.json"}`. For `antigravity`,
    `mcp.env_names` MUST unconditionally forbid (case-insensitively)
    `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `AGY_ADC_AUTH`,
    `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_CLOUD_QUOTA_PROJECT`,
    `AGY_CLI_FORCE_FILE_TOKEN_STORAGE`, and `AGY_CLI_DISABLE_AUTO_UPDATE` across
    Curator admission, `launch-env-fragment-v7` validation, launcher composition,
    and SAM `ChildEnv`, even when `credential_source` is absent (preventing an
    MCP declaration from bypassing file-backed OAuth via ambient ADC or API keys).
- Unmanaged / tool-owned state excluded from snapshots: `antigravity-cli/**`,
  `config/{.migrated,config.json,hooks.json,plugins/,projects/}`.

#### 2. Interactive `per-home` credentials

Following CIP-0017's single decision table for Muse:
- `credential_store` unset or `native` resolves to effective `file` without
  rewriting machine config; explicit `file` resolves to `file`; explicit
  `keychain` refuses with `environment_credential_store_unsupported`.
- `fragment.env` MUST contain exactly `{"AGY_CLI_FORCE_FILE_TOKEN_STORAGE":
  "true"}`. Ambient `AGY_CLI_FORCE_FILE_TOKEN_STORAGE=false` is overridden by
  the fragment literal (`antigravityPolicy` in `curator-agent-launcher`);
  conflicting explicit plan overrides refuse `environment_credential_conflict`.
- `isolated`: no passthrough link; login runs
  `AGY_CLI_FORCE_FILE_TOKEN_STORAGE=true agy acp --login --gemini-dir <home>`,
  storing `<home>/antigravity-cli/antigravity-oauth-token` (`0600`).
- `shared`: `file-link` from `<home>/antigravity-cli/antigravity-oauth-token`
  to `~/.gemini/antigravity-cli/antigravity-oauth-token`, requiring a prior
  native file-backed login and mandatory every-resolve liveness checks.
  Keychain credentials are never exported. Live OAuth refresh write behavior is
  admitted optimistically as a recorded residual (matching CIP-0017 D10).
- Login readiness (`env-status-v2`): strictly metadata-only inspection of
  `antigravity-cli/antigravity-oauth-token` (regular, owner, `0600`, size > 0;
  verified link target in `shared`), never executing `agy` or reading bytes.

#### 3. Headless `node:<label>` credentials (`gemini-api-key` and `google-adc-file`, schema reservations in revision 1)

Both deterministic channels are allocated as schema reservations in
`node-source-v2` and `launch-env-fragment-v7` (neither is enabled for live
injection on `agy 1.5.16` in revision 1):
- `gemini-api-key`: `harness_channel = "GEMINI_API_KEY"`; requires final
  executor private env `GEMINI_API_KEY=<value>` + `AGY_CLI_FORCE_FILE_TOKEN_STORAGE=true`,
  plus SAM argv `--settings '{"modelProvider":"gemini"}'`.
- `google-adc-file`: `harness_channel = "GOOGLE_APPLICATION_CREDENTIALS"`;
  requires final executor private env `AGY_ADC_AUTH=true` +
  `GOOGLE_APPLICATION_CREDENTIALS=<0600-node-secret-path>` (+ optional
  `GOOGLE_CLOUD_QUOTA_PROJECT=<id>` from non-secret node metadata) +
  `AGY_CLI_FORCE_FILE_TOKEN_STORAGE=true`, without `modelProvider: "gemini"`.
- **L7 qualification gate:** Under [local-setup-token-source section 7](../protocol/local-setup-token-source.md#7-entry-point-and-qualification-l7)
  and [CIP-0010 C3.4](CIP-0010-credentials-setup-token-and-inherited-auth.md),
  `credential-injection/1` MUST NOT be advertised on `agy 1.5.16` while
  `stdio` MCP servers, hooks, or shell children inherit the harness environment
  (`P5`). A syntactically valid `launch-env-fragment-v7` carrying
  `credential_source` for `antigravity` MUST be refused operationally by SAM
  and final executors with `credential_injection_unavailable` (not reported as
  a malformed fragment) until upstream `agy` scrubs injected credentials from
  child processes (or a separately qualified zero-child route is established).

#### 4. Coordinated closed carriers (`launch-env-fragment-v7`, `snapshot-launch-v2`) and `environments.md` section 10.5 rollout posture

- `launch-env-fragment-v7` extends `v6` with top-level `home: {"path":
  absolutePath, "transport": "flag"}` (required for `antigravity`, forbidden
  for env-based adapters), `antigravity` environment rules (including
  unconditional exclusion of the seven Antigravity auth/policy variables from
  `mcp.env_names`), and `node-source-v2`. `--format env` and `--format shell`
  refuse fail-closed with `environment_flag_home_unsupported` and zero bytes on
  stdout.
- `snapshot-launch-v2` extends `snapshot-launch-v1` with `home: {"path":
  "home", "transport": "flag"}` and `env: {}` (no credential policy) for
  `antigravity`. Only verified managed files (`home/config/AGENTS.md`,
  `home/config/skills/**`, `home/config/mcp_config.json`) enter the snapshot.
- **`environments.md` section 10.5 temporary rollout posture (`O11 (a)`):**
  `protocol/environments.md` section 10.5 states that a launcher MUST refuse a
  managed-profile session when it cannot consume the snapshot contract rather
  than falling back to a live managed home. Because `curator env materialize`
  and per-adapter snapshot qualification are not yet shipped, Phase 1 live
  Antigravity launches (`--gemini_dir <managed home>`) operate directly against
  the managed home under the same recorded temporary non-conformance as the
  other pre-snapshot adapters (`codex_cli`, `muse`, `pi`, tracked under owner
  decision `O11 (a)` and spec note `C6`). `snapshot-launch-v2` is defined now
  as an additive schema, while the Antigravity snapshot route remains
  unqualified until `env materialize` and the Runtime B credential channel are
  explicitly qualified for `antigravity`.

#### 5. Phase 2 / Deferred: Project-Context & Werkstatt (`CIP-0002`)

Explicitly deferred to a dedicated Phase 2 follow-up leaf immediately after
Phase 1 stabilization, grounded in `P9` evidence:
- Implement `internal/projectadapter/antigravity.go` and
  `docs/qualification/project-source-exclusion-antigravity.md`.
- Close the three `project-context.md` certification gates:
  1. `memory-off` (verifying `knowledge/` suppression under OAuth/ADC as well as
     API-key sessions).
  2. Manager-programmed permissions precedence (`--settings` vs
     `config/projects/*.json` and workspace rules, respecting `Q2b` last-wins
     `--settings` and `Q4` sparse marshalling).
  3. Native workspace source exclusion (`strict` vs `native-project`): because
     `P9a` proved `agy 1.5.16` unconditionally loads `AGENTS.md`, `GEMINI.md`,
     `.agents/skills/`, `.agents/plugins/*/rules/`, and starts
     `.agents/plugins/*/mcp_config.json`, `strict` MUST refuse on `1.5.16`
     whenever any workspace native surface exists (and account for `P2b`
     absolute at-include expansion).

## Security considerations

- **Child-process credential leakage (`P5`):** `agy 1.5.16` passes
  `GEMINI_API_KEY` to `stdio` MCP children and has no child-env scrubber. This
  blocks L7 `credential-injection/1` admission on `1.5.16`; `per-home` OAuth is
  unaffected because the token lives in a `0600` file, never in the process
  environment.
- **L6 conflict inventory for node mode:** Before accessing node material, the
  final executor MUST refuse `credential_source_conflict` if
  `antigravity-cli/antigravity-oauth-token` exists, if `settings.json` sets
  conflicting `modelProvider`/`customModelsConfig`/`gcp`, if any reserved auth
  or endpoint env var is present (`GEMINI_API_KEY`, `GOOGLE_API_KEY`,
  `AGY_ADC_AUTH`, `GOOGLE_APPLICATION_CREDENTIALS`,
  `GOOGLE_CLOUD_QUOTA_PROJECT`, `GOOGLE_CLOUD_PROJECT`, `AGY_LLM_GATEWAY_*`,
  `CLOUD_CODE_URL`, `AICODE_ENDPOINT_URL`, `GEMINI_BASE_URL`,
  `GOOGLE_GEMINI_BASE_URL`, `AGY_CDE_*`, `ANTIGRAVITY_REMOTE_OOB_AUTH`,
  `LD_*`, `DYLD_*`, `NODE_*`, `PYTHON*`), or if `NativeArgs` carries
  `--gemini_dir`, `--gemini-dir`, `--app_data_dir`, `--app-data-dir`,
  `--settings`, `--use_host_auth`, `--host_bridge_url`,
  `--read_host_bridge_token_from_stdin`, `--use_stubby_auth`, or
  `--cloud_code_endpoint`.
- **`--settings` last-wins (`Q2b`):** SAM MUST reject conflicting `--settings`
  in `NativeArgs` whenever managed session settings are emitted.
- **Linux plugin secrets (`P4d`) and workspace plugin MCP (`P9a`):** Documented
  Phase 1 residuals; managed homes never copy native `config/plugins/` or
  `config/projects/`.

## Compatibility and migration

- Predecessor schemas (`launch-env-fragment-v1`..`v6`, `node-source-v1`,
  `snapshot-launch-v1`) retain their exact bytes and semantics and reject
  `antigravity`.
- Existing five adapters continue emitting their prior fragment and snapshot
  revisions unchanged; `launch-env-fragment-v7` and `snapshot-launch-v2` are
  emitted for `antigravity` (and valid for all six adapters).
- No native `~/.gemini` files are modified or migrated in place.

## Specification changes

- `protocol/environments.md`: sections 7.1, 7.2, 7.4, 7.5, 7.7, 7.8, 7.9, 10.2, 10.3.
- `protocol/managed-home-snapshots.md`: `snapshot-launch-v2` table and rules.
- `protocol/login-readiness.md`: section 1.1 `antigravity` row.
- `protocol/local-setup-token-source.md`: `antigravity` node-channel scope and
  L7 child-leak qualification gate.
- `schemas/antigravity-managed-home-v1/`: `node-source-v2.schema.json`,
  `launch-env-fragment-v7.schema.json`, `snapshot-launch-v2.schema.json`.
- `conformance/antigravity-managed-home-v1/`: positive and negative vectors and
  validator checks in `tools/antigravity_managed_home.py` + `tools/validate.py`.

## Implementation plan

1. **`curator-spec` (this CIP):** normative prose, closed schemas, conformance
   vectors, validator integration.
2. **`skill-agents-management` (SAM):** `CuratorContext` v7 (`Home` binding),
   complete `pkg/agentic/systems/agy/` refactor (`--gemini_dir`, `--effort`,
   interactive mode, filtered `ChildEnv` with `AGY_CLI_DISABLE_AUTO_UPDATE=true`,
   `argvguard_test.go`, removal of nonexistent `--mcp-config`), updated
   `google` model catalog against `agy 1.5.16 models`.
3. **`curator`:** `envregistry` (`HomeTransport: "flag"`, `antigravity` + `agy`
   alias, 24,000B advisory, 4 shadowing paths), `harness/antigravity`,
   `adapters` (`NativeDiscoveryAgents`), `envprofile` (credential policy,
   managed home layout, `file-link`, metadata-only readiness), `envfragment` v7
   (fail-closed `env|shell`), `envsnapshot` v2 (`env: {}`).
4. **`curator-agent-launcher`:** `mapping`, `fragment` v7 decoder,
   `composition` (`antigravityPolicy`), `plan` (SAM version gate, `agy 1.5.16`
   pins, L7 refusal for unqualified node mode), `defaults/lineup`.
5. **Phase 2 (separate follow-up leaf):** `project-context` / Werkstatt adapter
   (`internal/projectadapter/antigravity.go`) and qualification doc.

## Test plan

- Schema & conformance: positive/negative `launch-env-fragment-v7` and
  `snapshot-launch-v2` vectors; byte-immutability and rejection of
  `antigravity` by `v6` and `snapshot-launch-v1`.
- SAM unit/golden tests: `--gemini_dir` argv rendering, `argvguard_test.go`,
  conflict refusal (`--gemini_dir`, `--gemini-dir`, `--app_data_dir`,
  `--settings`, yolo `--mode`/`--sandbox`), `AGY_CLI_DISABLE_AUTO_UPDATE=true`
  and `AGY_CLI_FORCE_FILE_TOKEN_STORAGE=true` in filtered `ChildEnv`.
- Curator unit tests: managed-home provisioning, `config/AGENTS.md` symlink +
  24,000B advisory, all 4 shadowing paths, `isolated` vs `shared` liveness and
  refusal of `keychain`, `v7` JSON emission, fail-closed `env|shell` refusal
  (`environment_flag_home_unsupported`, 0 stdout bytes), `snapshot-launch-v2`
  emission with `env: {}` and zero tool state.
- Launcher unit tests: `v7` decoding, `antigravityPolicy` ambient override
  protection, end-to-end plan composition to SAM `antigravity` argv
  `--gemini_dir <home>`, refusal of unqualified node injection on `1.5.16`.

## Open questions for the operator

1. **Interactive live OAuth refresh probe (`P4` live Google account):**
   Admitted optimistically under Phase 1 (matching Muse CIP-0017 D10). Confirm
   whether to run a disposable-account OAuth refresh + interactive TUI
   `onboarding.json` UX check before recommending `shared` mode widely.
   *(Recommended: yes, as a non-blocking follow-up lab check.)*
2. **Phase 2 (`project-context` / Werkstatt) priority:** Schedule immediately
   after Phase 1 merges, starting with `native-project` mode and explicit
   `strict` refusal on `agy 1.5.16`. *(Recommended: yes.)*
3. **Upstream `agy` requests:** Track two upstream asks -- (a) env-scrubbing of
   `GEMINI_API_KEY` / `GOOGLE_APPLICATION_CREDENTIALS` before spawning MCP /
   hook / shell children (unblocks L7 `credential-injection/1`), and (b)
   workspace-customization exclusion flags (unblocks Phase 2 `strict` mode).
