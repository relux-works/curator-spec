# Antigravity CLI (`agy`) managed-home contract, revision 1

This normative amendment specifies
[CIP-0033](../cips/CIP-0033-antigravity-managed-home.md) (Phase 1 implementation
in review, 2026-11-24). It supplements [environments](environments.md),
[managed-home snapshots](managed-home-snapshots.md),
[login readiness](login-readiness.md), and
[local setup-token source](local-setup-token-source.md) without modifying any
released or corpus-pinned predecessor schema or document bytes.

## 1. Adapter identity, flag home transport, and layout

- **Environment ID:** `antigravity` (CLI alias `agy`).
- **Mode scope:** `managed-home`-only. Curator MUST NOT write in-place into
  shared `~/.gemini` and MUST NOT replace `HOME`.
- **Home transport:** Closed `HomeTransport` enum `"env"` (existing five
  adapters) | `"flag"` (`antigravity`). Curator emits `home: {"path":
  <absolutePath>, "transport": "flag"}` in `launch-env-fragment-v7` and
  `home: {"path": "home", "transport": "flag"}` in `snapshot-launch-v2`.
- **Path-isolation and basename invariants:** The managed home MUST NOT resolve
  (including through symlinks or case-insensitive filesystem aliases) to,
  contain, or lie inside the native `~/.gemini` directory. In addition, the
  managed-home directory basename MUST NOT be `.gemini` (Curator uses
  `antigravity`). Verified on `agy 1.5.16` (macOS ARM64 and Linux x86_64,
  probes P3a-P3b): non-`.gemini` basenames skip `~/.agents/skills` completely.
- **Surfaces:**
  - `root-context`: `<home>/config/AGENTS.md` (`monolithic` only, symlink or
    copy fallback, `root_context_size_advisory_bytes = 24000`).
  - Shadowing (environments section 7.5): `config/GEMINI.md`, `config/rules`,
    `GEMINI.md`, `AGENTS.md` (all four merge additively with `config/AGENTS.md`).
  - `skills`: `<home>/config/skills/` (`<name>/SKILL.md`, symlink or copy).
  - `system-prompt`: none.
  - `mcp`: `<home>/config/mcp_config.json` (`{"mcpServers": {...}}`, `0600`),
    channel `{"kind": "file", "filename": "config/mcp_config.json"}`. For
    `antigravity`, `mcp.env_names` MUST unconditionally exclude (case-insensitively)
    `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `AGY_ADC_AUTH`,
    `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_CLOUD_QUOTA_PROJECT`,
    `AGY_CLI_FORCE_FILE_TOKEN_STORAGE`, and `AGY_CLI_DISABLE_AUTO_UPDATE`,
    regardless of whether `credential_source` is present.
- **Fail-closed env/shell projection:** `curator env resolve --format env` and
  `--format shell` MUST refuse `antigravity` with
  `environment_flag_home_unsupported` and zero bytes on stdout.

## 2. Credentials, login readiness, and headless node gate

- **Interactive `per-home`:** `credential_store` unset or `native` resolves to
  effective `file` without rewriting machine config; explicit `file` resolves
  to `file`; explicit `keychain` refuses `environment_credential_store_unsupported`.
  `launch-env-fragment-v7` carries exact `env:
  {"AGY_CLI_FORCE_FILE_TOKEN_STORAGE": "true"}` (bypassing global macOS
  Keychain `service="gemini"`, `account="antigravity"`). `isolated` runs
  `AGY_CLI_FORCE_FILE_TOKEN_STORAGE=true agy acp --login --gemini-dir <home>`;
  `shared` creates a `file-link` from `<home>/antigravity-cli/antigravity-oauth-token`
  to `~/.gemini/antigravity-cli/antigravity-oauth-token` with mandatory
  every-resolve liveness checks.
- **Login readiness (`login-row-v1` / `env-status-v2`):** Metadata-only
  inspection of `<home>/antigravity-cli/antigravity-oauth-token` (regular,
  owner, `0600`, size > 0; verified native link in `shared`). Global Keychain
  items never establish managed readiness. Status MUST NOT invoke `agy` or
  read token bytes.
- **Headless `node:<label>` channels (`node-source-v2`, schema reservation in
  revision 1):** Allocates `GEMINI_API_KEY` (`gemini-api-key`, requiring SAM
  `--settings '{"modelProvider":"gemini"}'`) and
  `GOOGLE_APPLICATION_CREDENTIALS` (`google-adc-file`, requiring
  `AGY_ADC_AUTH=true`). Both channels are schema reservations only in revision
  1: because live probes (`P5`) on `agy 1.5.16` confirmed that `agy` inherits
  `GEMINI_API_KEY` into `stdio` MCP children and lacks child-env scrubbing,
  `credential-injection/1` remains **unqualified** on `agy 1.5.16`. Readers and
  executors MUST treat a syntactically valid `launch-env-fragment-v7` carrying
  `credential_source` for `antigravity` as an operational refusal with
  `credential_injection_unavailable` (not a schema/malformed-fragment error).

## 3. Portable snapshots (`snapshot-launch-v2`) and section 10.5 rollout posture

[`snapshot-launch-v2`](../schemas/antigravity-managed-home-v1/snapshot-launch-v2.schema.json)
extends `snapshot-launch-v1` with `antigravity`: `home: {"path": "home",
"transport": "flag"}` and empty `env: {}` (zero credential policy). Only
verified managed files (`home/config/AGENTS.md`, `home/config/skills/**`,
`home/config/mcp_config.json`) enter the snapshot; `antigravity-cli/**` and
unmanaged `config/` state are excluded. `AGY_CLI_FORCE_FILE_TOKEN_STORAGE=true`
belongs to destination credential preparation, and
`AGY_CLI_DISABLE_AUTO_UPDATE=true` belongs to SAM `ChildEnv`.

**Relationship to `environments.md` section 10.5 (temporary rollout posture):**
`environments.md` section 10.5 requires a launcher to refuse a managed-profile
session when it cannot consume the snapshot contract rather than falling back
to a live managed home. Because `curator env materialize` and per-adapter
snapshot qualification are not yet shipped, Phase 1 live Antigravity launches
(`--gemini_dir <managed home>`) operate directly against the managed home under
the same recorded, temporary non-conformance as the other pre-snapshot adapters
(`codex_cli`, `muse`, `pi`, tracked under owner decision `O11 (a)` and spec
note `C6`). `snapshot-launch-v2` is allocated now so the schema is stable,
while the Antigravity snapshot route remains unqualified until `env materialize`
and the Runtime B credential channel are explicitly qualified for `antigravity`.

## 4. Launcher and SAM boundary

SAM is the sole renderer of Antigravity CLI flags (Decision 0013 D5):
- `home.path` -> `--gemini_dir <path>` on CLI launches (`--gemini-dir <path>`
  on `agy acp --login`; before subcommand name on `mcp`/`plugin` subcommands).
- `PermissionModeYolo` -> `--dangerously-skip-permissions`.
- `GEMINI_API_KEY` node channel -> `--settings '{"modelProvider":"gemini"}'`.
- Every Curator-managed Antigravity launch requires the verified release pin
  (`1.5.16`) until a successor release is qualified.
- Reject conflicting `NativeArgs`: `--gemini_dir`, `--gemini-dir`,
  `--app_data_dir`, `--app-data-dir`, `--cli_dir_name`, `--cli-dir-name`,
  `--settings` (last-wins on `agy 1.5.16`, probe Q2b), conflicting
  `--mode`/`--sandbox` in yolo mode, and auth/endpoint override flags in node
  mode.
- SAM `ChildEnv` filters inherited env, unconditionally drops the seven
  forbidden Antigravity auth/policy variables even if listed in `mcp.env_names`,
  overlays `AGY_CLI_FORCE_FILE_TOKEN_STORAGE=true`, and sets
  `AGY_CLI_DISABLE_AUTO_UPDATE=true`.
