# Claude Desktop facts for managed sessions (evidence for CIP-0035 and CIP-0036)

- **Status:** research note, not a CIP. CIP-0035 (session surface) and CIP-0036 (GUI hosts) cite it as "fact N".
- **Created:** 2026-11-25, updated 2026-11-26. Facts 1-47 come from the earlier combined draft and keep their numbers. Facts 48-66 come from probes after the first review, facts 67-72 (probes D1-D5) from the final review.
- **Verified on:** Claude Desktop 6.28899.6 and 7.37095.0 (the host updated itself during the tests, see fact 65). macOS arm64, Darwin 27.2. CLI 2.1.330 -> 2.1.331 (the session binary, SHA-256 `b76a8345f6c00c40...`). curator v0.15.0-rc.10.
- **Reproduction:** probes 48-64 and 67 run from the scripts in [probes](261126_claude-desktop-managed-sessions-probes/) (see 1.10).

## 1. Verified facts

Labels: **verified** -- observed live; **code** -- from the application, CLI or Curator code; **CLI** -- verified on the session binary without the host.

### 1.1 Config directory binding

| # | Fact | Label |
|---|---|---|
| 1 | The app's "New environment" dialog rejects `CLAUDE_CONFIG_DIR` for a single environment: "can only be set for all sessions, not for one environment". | verified |
| 2 | Config directory selection order in the app: the `CLAUDE_CONFIG_DIR` value from Desktop settings -> `CLAUDE_CONFIG_DIR` from the app process environment -> `~/.claude`. The path must be absolute, without `~`. | code |
| 3 | The app substitutes login-shell variables only if they are absent from its own environment. A value passed at launch is not overridden by `.zshrc` (confirmed live in fact 71). | code |
| 4 | `open -n -a Claude --env CLAUDE_CONFIG_DIR=<path>` passes the variable to the launched instance. A session of that instance reads `CLAUDE.md` from the given directory. | verified |

### 1.2 Instances and the data directory

| # | Fact | Label |
|---|---|---|
| 5 | The Electron single-instance lock is scoped to the data directory. A plain `open` brings the running instance forward, and new variables have no effect. `open -n ... --args --user-data-dir=<path>` starts a second instance next to the first. | verified |
| 6 | The signed build removes `CLAUDE_USER_DATA_DIR` at start. `--user-data-dir` is not in the list of forbidden launch switches. A non-default data directory disables a feature the code calls local pairing. | code |
| 7 | The app login lives in the data directory: own directory, own login, and it survives restarts. An email-code sign-in completed inside the window. The server sees the instances as different devices. | verified |
| 8 | The app passes its own authorization to sessions. No separate CLI login (`/login`) is needed in the managed home. | verified |
| 9 | Session list entries live in the data directory (`claude-code-sessions/<account>/<organization>/local_<id>.json`) and have no config directory field. Transcripts live in `<CLAUDE_CONFIG_DIR>/projects/`. A session from another config directory stays in the list but opens as "Session not found on disk" with "Import CLI sessions", "Archive" and "Delete" buttons. | verified |
| 10 | Shared between instances: the log file `~/Library/Logs/Claude/main.log` (lines interleave), the native host registration for Claude in Chrome (each instance rewrites it at start), and the "device" slot for remote tools. Instances compete for it: `[remote-tools-device] bridge error: duplicate_device_id`, and the second instance does not get it. | verified from logs |
| 11 | Theme and window zoom are per instance and stored in the data directory. | verified indirectly |

### 1.3 Curator managed home in the app

| # | Fact | Label |
|---|---|---|
| 12 | `env resolve claude_code --profile <P> --repair` assembles `CLAUDE.md` from the base profile and the overlay. The session knows the context of both. | verified |
| 13 | The app accepts the project directory trust that Curator wrote into `.claude.json`: no trust dialog appears. | verified |
| 14 | Without `claudeMdExcludes`, the native `~/.claude/CLAUDE.md` and `~/.claude/rules/**` enter the context: Claude reads the `.claude` of the project's ancestor directories. With the exclusions Curator writes, they do not. Verified with a control run. | verified |
| 15 | Skills from the managed home `skills/<name>` (links into the Curator store) are visible and callable. | verified |
| 16 | The current Curator MCP channel (the `--mcp-config <file> --strict-mcp-config` flags that `curator run` adds) does not reach app sessions: the server never starts. | verified |
| 17 | User-level `mcpServers` in the managed home `.claude.json` work: the app starts the server with the profile `CLAUDE_CONFIG_DIR` and the project `cwd`, and the tool is callable. `env resolve --repair` keeps the entry. | verified |
| 18 | `alwaysLoad: true` on an MCP server in `.claude.json` loads its tools up front, without `ToolSearch`. The same holds in a `--mcp-config` file (fact 67). | verified |

### 1.4 Surface control from the managed home `settings.json`

| # | Mechanism | Effect | Label |
|---|---|---|---|
| 19 | `disableBundledSkills: true` | Hides the bundled CLI skills (`init`, `security-review`, `loop`, `schedule`, `claude-api`, `simplify`, `code-review`, ...) and the Code tab skills (`dataviz`, `artifact-*`, `run`, `ship`, `steward`). | verified |
| 20 | `skillOverrides: {"<skill>": "off"}` | Works for home skills and plugin skills (`plugin-authoring`). Has no effect on account skills (`anthropic-skills:*`) in any name form. Values: `on`, `name-only`, `user-invocable-only`, `off`. | verified |
| 21 | `enabledPlugins: {"anthropic-skills@inline": false}` | Turns the account skills plugin off in this instance. The account does not change; a neighbor instance under the same account keeps the skills. | verified |
| 22 | `permissions.deny: ["mcp__<server>"]` | Removes all tools of a server: built-in app MCP servers (browser, Chrome, computer-use, iOS Simulator, terminal, scheduled-tasks, mcp-registry, visualize), plugin tools (`easel`), the service `ccd_*` servers and connectors. Connectors are named by UUID. | verified |
| 23 | `permissions.deny: ["<Tool>"]` | Removes a built-in tool by name: `Bash`, `Read`, `Edit`, `Agent`, `WebSearch`, `ToolSearch` and so on. With `Agent` the agent types disappear too. | verified |
| 24 | `allowedMcpServers: [{"serverName": "<name>"}]` | MCP allowlist. In the strict run it was combined with denies. After the review it was checked alone in the CLI (50, 52): a server outside the list does not start, but the project can widen the list. Servers the host provides, `ccd_*` and connectors are not restricted by the allowlist (68). | verified |
| 25 | `disableClaudeAiConnectors: true` | From user settings it does not block the connectors the Code tab provides. Per the CLI description only a managed or server settings source does that. | verified |
| 26 | What remains after denies | A deny in `settings.json` takes tools away but does not remove mentions. Prompt sections the host appends (`<browsers>`, `<built_in_browser>`, `<simulator_tools>`) and the instructions of denied MCP servers remain. The model describes such servers as "connected, schemas not loaded". Instance toggles remove host sections (1.4a). | verified |

#### 1.4a Host instance toggles (`claude_desktop_config.json` -> `preferences` in the data directory)

The host enables its built-in servers itself and appends their prompt sections (`promptAppendSnapshot` in the session record). Instance settings toggles control this. There is no launch switch for them, but the data directory belongs to the profile, so the launcher can set them before launch. Verified with the instance stopped:

| # | Key | Result | Label |
|---|---|---|---|
| 26.1 | `chicagoEnabled: false` ("chicago" is the internal name of computer use) | The computer-use server and every computer-use mention vanished from the prompt | verified |
| 26.2 | `claudeIosSimulatorAccessEnabled: false` | The `<simulator_tools>` section and the simulator server vanished | verified |
| 26.3 | `chromeExtensionEnabled: false` | No Claude in Chrome section; one Chrome mention remains inside the built-in browser section | verified |
| 26.4 | `claudeAndroidEmulatorAccessEnabled: false` | No visible effect (no emulator on the machine) | verified |
| 26.5 | `ccdScheduledTasksEnabled: false` | The app flipped the value back to `true`; the task tools are denied in the strict profile anyway | verified |
| 26.6 | Built-in browser | No instance-level toggle found (`builtinBrowserEnabled` is computed from app flags). The `<built_in_browser>` section remains; the tools are denied | code and verified |
| 26.7 | Account connectors (Claude Docs) | No instance-level toggle found. The connector instructions remain; the tools are denied | code and verified |
| 26.8 | The app's own prompt sections (link format, file pane, terminal, CI watching, sessions) | Remain; without `ccd_*` the app turns some off itself (`toolSets.turnBox: false`) | verified |

Result of the strict run with toggles: only `Skill` and `profile_codeword` are callable, there are no deferred tools at all, and the only "foreign" prompt content left is the built-in browser section, the Claude Docs connector instructions and the app's own sections.

**The strict run** (recipe in Appendix A) produced the surface "two profile skills and one profile MCP server":
- only `Skill` and `mcp__profile-test-mcp__profile_codeword` are callable;
- skills: only `profile-test-skill` and `profile-test-skill-2`;
- both secrets and the MCP codeword were received;
- the profile and overlay context is present. **verified**

### 1.5 Links, service sign-in, account

| # | Fact | Label |
|---|---|---|
| 27 | macOS hands a `claude://` link to the primary (first started) instance, not to the frontmost one. Controlled test: the profile instance was frontmost, `claude://code/needs-input?source=desktop_action` was sent, and the primary instance received it. | verified |
| 28 | When signing in to the Google plugin from a profile instance, the browser callback did not return to that instance. The connection still appeared in all instances: it is stored in the account. GitHub was also connected at account level. | verified |
| 29 | On a repeated launch against the same lock, the macOS app only raises the window and does not parse a link from the arguments. | code |

### 1.6 Wrappers and signing

| # | Fact | Label |
|---|---|---|
| 30 | A Swift app built on the machine and ad-hoc signed (`codesign -s -`), without a quarantine attribute, launches without Gatekeeper prompts. | verified |
| 31 | A copy with a modified `Info.plist` fails `codesign --verify`, although it launched. After another ad-hoc signature it passes. So the template is copied and re-signed. | verified |

### 1.7 `HOME` replacement (rejected for Claude)

| # | Fact | Label |
|---|---|---|
| 32 | Foundation directories (`NSHomeDirectory`, `~/Library/Application Support`) ignore a `HOME` replacement: the app data directory does not move. | verified |
| 33 | With a replaced `HOME`, `security` cannot find the keychain. A `Library/Keychains` link to the real directory helps. | verified |
| 34 | ssh ignores the replacement. zsh and git read their files from the replaced `HOME`. | verified |
| 35 | The CLI takes the home directory from `os.homedir()`, that is from `HOME`, and builds its protected path list from it (`.ssh`, `.aws`, `.gnupg`, `.gitconfig`, `Library/Keychains`, `.claude/state/...`). With a replacement the protection moves to the replaced directory. `HOME` cannot be replaced from inside a session: the CLI returns the value it started with. | code |
| 36 | Consent records in `~/.claude/state/` are tied to the real home on purpose and do not follow `CLAUDE_CONFIG_DIR`. | code |

### 1.8 Policy and test machine environment

| # | Fact | Label |
|---|---|---|
| 37 | The test machine has no managed policy: no `managed-settings.json`, no Claude MDM domains, no configuration profiles. The app reports `managedConfig type: none`; the plan has no server-managed settings. | verified |
| 38 | The CLI supports a managed settings folder named by `CLAUDE_CODE_MANAGED_SETTINGS_PATH`. In Claude Desktop sessions it is **not read**: the host tells the CLI that system managed settings are absent ("the host attests the 'system' space absent ... policy folder (or the one CLAUDE_CODE_MANAGED_SETTINGS_PATH names) is not read"), and the host passes the session's managed settings itself. Verified: the variable reached the instance CLI processes, but `disableClaudeAiConnectors: true` from such a folder did not disable the connector. | code and verified |
| 39 | The app lays out account skills as the `anthropic-skills` plugin in the instance data directory (`local-agent-mode-sessions/skills-plugin/<organization>/<account>/`, with a `manifest.json` holding an `enabled` flag per skill) and passes it to the session. The plugin gets the identifier `anthropic-skills@inline`. | verified and code |

### 1.9 Curator rc.10 limitations met along the way

| # | Observation | Label |
|---|---|---|
| 40 | Requirements with `file://` URLs and local paths are refused (`profile_source_invalid`). For the tests a local `git daemon` served the packages at `git://localhost/...`. | verified |
| 41 | Skill names with the `curator-` prefix are reserved (`environment_reserved_command_name`). | verified |
| 42 | A new MCP server requires `--confirm-system-delta`, but `profile compose add` has no such flag. An overlay cannot add an MCP server; only the root profile requirements and `profile install` can. | verified |
| 43 | After a manifest edit of a path profile, `profile update` reports `unchanged`. Only a repeated `profile install` picks the change up (this is the specified behavior of `path` sources). | verified |
| 44 | The Homebrew tap serves 0.14.0, which does not implement `profile compose`. | verified |
| 45 | `claude` is not on `PATH`, so Curator reports `environment_tool_version_unverified` and assumes version 2.1.261. | verified |
| 46 | The audit blocks the swarma-memory `memory` skill (`audit.capability.network-undeclared`). Tracked separately. | verified |
| 47 | CIP-0006 (`profile_settings`, including `enabledPlugins`) is accepted but not implemented in rc.10. | code |

### 1.10 Probes after the reviews (2026-11-25 and 2026-11-26)

**CLI method (facts 48-64).**
- The same binary that runs Desktop sessions: CLI 2.1.331 from the data directory.
- Mode: `-p --output-format stream-json --verbose`, each run with its own throwaway `CLAUDE_CONFIG_DIR` and project directory.
- A cleared environment. `ANTHROPIC_BASE_URL` points at a closed local port, so no API request leaves the machine.
- Only the `system/init` message is captured: tools, MCP servers with their source, skills, plugins.
- The test MCP server logs its start and how a variable reached it. Only a hash is logged, never the value.
- The scripts are in [probes](261126_claude-desktop-managed-sessions-probes/). The **CLI** label means "verified on the session binary without the host"; behavior inside a Desktop session is marked separately.

| # | Fact | Label |
|---|---|---|
| 48 | **Login-free init.** The CLI emits `system/init` before calling the API; no login is needed (`apiKeySource: none`). The message has everything an inventory needs: `tools`, `mcp_servers` (name, status, source `user`/`project`), `skills`, `plugins`, `slash_commands`, `agents`. It is a ready automatic inventory for qualification: a few seconds, no network, no account. | CLI |
| 49 | **Composition without the host.** 22 built-in tools: Task, Bash, CronCreate, CronDelete, CronList, Edit, EnterWorktree, ExitWorktree, ListAgents, Monitor, NotebookEdit, Read, ReportFindings, ScheduleWakeup, SendMessage, Skill, TaskStop, ToolSearch, WebFetch, WebSearch, Workflow, Write. Plus 16 bundled skills, 3 `cc-plugin-*@builtin` plugins and 5 agent types. Everything else visible in a Desktop session (Artifact, AskUserQuestion, SendUserFile, `ccd_*`, built-in MCP servers) is added by the host and can be inventoried only in a host session. Names depend on the host too: the subagent tool is `Task` here and `Agent` in a Desktop session (23). | CLI |
| 50 | **`allowedMcpServers` works on its own** in the user `settings.json`: a server outside the list does not start and is absent from init. | CLI |
| 51 | **`deniedMcpServers`** in the user `settings.json`: the server does not start. A user deny beats a project allow (`allowedMcpServers` and `enableAllProjectMcpServers` in `.claude/settings.json`). A mask in `serverName` (`be*`) does not work; exact names are needed. | CLI |
| 52 | **The allowlist merges across levels.** If the user has `[alpha]` and the project `[beta]`, both are allowed. The project can widen the user allowlist. | CLI |
| 53 | **A project can bring its own servers**: `.mcp.json` plus `enableAllProjectMcpServers: true` in `.claude/settings.json`. The user allowlist blocks such a server until the project widens it (52). | CLI |
| 54 | **Masks in `permissions.deny`** match the full tool name `mcp__<server>__<tool>`, case-sensitively. `mcp__*` and `mcp__*__*` remove all MCP tools, `mcp__al*` servers by prefix, `mcp__alpha__*` a whole server. `mcp__ALPHA` has no effect on `alpha`. **The server process still starts**: the deny removes only the tools. | CLI |
| 55 | **The mask `mcp__*-*-*-*-*`** removes the tools of servers with a UUID in the name when the tool name has no hyphens (`batch`). It does not touch servers `acme-tracker` or `a-b-c-d`. All hyphens of the full name count, so a server with hyphens in a tool name is hit too. As a way to close connectors the mask is usable only together with a check of the profile server names. | CLI |
| 56 | **The Claude Docs connector UUID (`1a59c906-...`) is compiled into the CLI binary.** So built-in connector identifiers are constants of the CLI version, not account data, and can be denied before the first session. In the instance data directory the UUID appears only in the Chromium cache (`Cache/Cache_Data`), not in readable JSON files. Where to get the UUIDs of the account's own (non-built-in) connectors is not known. | code and verified |
| 57 | **`ENABLE_TOOL_SEARCH`.** `false` removes `ToolSearch`, and all MCP tools load up front. `true` keeps it. `env` in `settings.json` overrides the process environment in both directions, and the project `env` overrides the user `env`. | CLI |
| 58 | **`${VAR}` substitution** in `mcpServers.<s>.env` and `args` in `.claude.json` works: the value comes from the process environment and from `env` in `settings.json`. `${VAR:-default}` gives a default. If the variable is missing and no default is given, the server receives the literal string `${VAR}` and still starts. | CLI |
| 59 | **The project overrides user "setting" keys.** In `.claude/settings.json`: `disableBundledSkills: false` brings bundled skills back; `skillOverrides: {"x": "on"}` brings a skill back; `enabledPlugins: {"p@inline": true}` brings an `@inline` plugin back, the same mechanism as `anthropic-skills@inline`. With `--setting-sources user` project settings are not read and bundled skills stay hidden. Curator already qualified this flag for `curator run` (curator `docs/qualification/project-source-exclusion-claude.md`). The host does not pass this flag. | CLI |
| 60 | **A user `permissions.deny` holds** against a project `permissions.allow`: `WebFetch` stayed denied. | CLI |
| 61 | **The rules `Skill(<name>)` and `Skill(<plugin>:*)`** in `deny` do not remove a skill from the init list. Whether they block the call cannot be checked without a model. Denying the `Skill` tool removes the tool itself; the skill list remains. | CLI |
| 62 | A plugin passed through `--plugin-dir` gets the identifier `<name>@inline`. | CLI |
| 63 | **Each data directory has its own CLI copy**: `<data dir>/claude-code/<version>/<hash>/claude.app`. The test instance currently has the same 2.1.331 with the same SHA-256 as the primary one, but the copies update independently. | verified |
| 64 | A server named `claude-in-chrome` declared in `.claude.json` did not appear in init. The name seems reserved. Observed once. | CLI, one run |
| 65 | **The host updated itself during the tests**, without user action: 6.28899.6 -> 7.37095.0. The log has "Update downloaded and ready to install ... Claude 7.37095.0" on 2026-11-25 at 04:46 and 04:50; the bundle on disk was replaced at 04:49:58. The test instance used for the toggles (26.1-26.8) started at 06:40, so those facts belong to 7.37095.0. Earlier facts belong to 6.28899.6. The CLI stayed at 2.1.331. | verified from log and bundle |
| 66 | `Claude.app` (`com.anthropic.claudefordesktop`) and the CLI binary in the data directory (`com.anthropic.claude-code`) are signed by the same Team ID: `Q6L2SF6YDW`. | verified |
| 67 | **`alwaysLoad` works in a `--mcp-config` file (probe D5).** Launch with `--mcp-config <file> --strict-mcp-config` and `ENABLE_TOOL_SEARCH=true`, as in `curator run`. A server with `alwaysLoad: true` delivers its tool up front: the full schema is in `tools` of the first model request. Without the key the tool is deferred: it is absent from `tools`, its name appears only in the deferred tool list in the messages, and `ToolSearch` is present. `.claude.json` behaves the same (the CLI analog of fact 18). With the default `ENABLE_TOOL_SEARCH`, a tool with `alwaysLoad: true` also loads up front. Init does not show this difference, so the method differs: a local mock API on `127.0.0.1` records the first request and answers 400. The API key is a dummy value, no login is used, and nothing leaves the machine (`probe_load.py`). | CLI |

**Desktop session probes D1-D4 (2026-11-26).** Host 7.37095.0, Team ID `Q6L2SF6YDW`, CLI 2.1.331 (`b76a8345f6c00c40...`) in the test instance data directory. The home is the managed home of the `curator-test` profile. Before each probe the test instance was stopped and the probe `settings.json` written, then a new Code session was opened in the window. Instance toggles remained from the strict run: `chicagoEnabled`, `chromeExtensionEnabled` and `claudeIosSimulatorAccessEnabled` were off. So computer-use, Claude in Chrome and the simulator were absent from the sessions, and the probes do not concern them. A second test server, `probe-env-mcp` (no `alwaysLoad`, tool `probe-env-mcp_codeword`), was declared in `.claude.json` next to `profile-test-mcp`.

| # | Fact | Label |
|---|---|---|
| 68 | **`allowedMcpServers` does not restrict what the host provides (D1).** With only `allowedMcpServers: [profile-test-mcp]` and no denies, `probe-env-mcp` did not start (its log stayed empty), while the session kept the built-in host MCP servers (`Claude_Browser`, `terminal`, `visualize`, `scheduled-tasks`, `mcp-registry`), all `ccd_*` and both account connectors (Claude Docs `1a59c906-...`, Gmail `f44f6d41-...`). The allowlist applies only to servers from configuration. Host servers and connectors can be closed only with `permissions.deny`. | verified |
| 69 | **The `mcp__*-*-*-*-*` mask in a Desktop session (D2).** The tools of both connectors disappeared from both the loaded and the deferred lists. The Claude Docs instructions stayed in the prompt. `profile-test-mcp` and all `ccd_*` remained, and `profile_codeword` was called. The mask also hit an unrelated server: the `probe-env-mcp` process started, but the tool `mcp__probe-env-mcp__probe-env-mcp_codeword` (four hyphens in the full name) was nowhere, and `ToolSearch` did not find it. Facts 54-55, confirmed in the host. | verified |
| 70 | **`ENABLE_TOOL_SEARCH: "false"` in the `settings.json` `env` works in a Desktop session (D3).** `ToolSearch` and `DeferredToolPlaceholder` disappeared, there was no deferred list, and all 183 tools went to the API up front, including `probe-env-mcp` without `alwaysLoad`, the connectors and `ccd_*`. Only the server-side `advisor` kept its own `defer_loading` flag. | verified |
| 71 | **`${NAME}` in `.claude.json` from `open --env`, and precedence over `.zshrc` (D4).** The instance started with `--env CURATOR_PROBE_SECRET=...`, and `probe-env-mcp` in `.claude.json` had `"PROBE_SECRET": "${CURATOR_PROBE_SECRET}"`. The server received the launch value (hash `b30fe8c39af7`), not the literal reference (`f3ecb9c14d27`). In a second run `.zshrc` exported a different value of the same variable and the login shell saw it (`91f11430b927`), but the server again received the launch value. Fact 3 confirmed live. The temporary `.zshrc` line was removed afterwards. | verified |
| 72 | **A Desktop session transcript records the exact request composition.** `<CLAUDE_CONFIG_DIR>/projects/<project>/<session>.jsonl` has an `api-request-shape` record with the `tools` array sent to the API, plus `deferred_tools_delta` attachments with deferred tool names and `mcp_instructions_delta` attachments with the servers whose instructions entered the prompt. D1-D3 were read from these records objectively, without asking the model. This is a ready source for the local host smoke (CIP-0036, section 7). | verified |

**What the probes settled from the review list:**

| Review question | Answer |
|---|---|
| `allowedMcpServers` without denies | Works for servers from configuration; the project can widen it (50, 52). Does not restrict host servers, `ccd_*` or connectors (68) |
| `ENABLE_TOOL_SEARCH` through `env` in `settings.json` | Works in the CLI (57) and in a Desktop session (70) |
| `${VAR}` in `.claude.json` | Works; a missing variable is passed literally (58). A value from `open --env` arrives and wins over `.zshrc` (71) |
| Connectors before the first session | Built-in connector UUIDs are CLI constants (56). The `mcp__*-*-*-*-*` mask removes connectors in the host too, but hits tool names with four hyphens (55, 69) |
| `strict` weakness against the project | Confirmed: only denies hold (59-61) |

**Open:** whether MCP OAuth 2.1 tokens are isolated between two different `CLAUDE_CONFIG_DIR` values is not checked. `${VAR}` in `headers` of a remote `http` MCP no longer needs checking for CIP-0037: with `curator-mcp-bridge`, `curator-auth-gateway` adds the authorization header over the broker Unix socket.

## Appendices

### A. Strict surface: the managed home `settings.json` (Claude Desktop 6.28899.6, CLI 2.1.331)

```json
{
  "claudeMdExcludes": ["<home>/.claude/CLAUDE.md", "<home>/.claude/rules/**"],
  "disableBundledSkills": true,
  "enabledPlugins": { "anthropic-skills@inline": false },
  "skillOverrides": { "plugin-authoring": "off" },
  "disableClaudeAiConnectors": true,
  "allowedMcpServers": [{ "serverName": "profile-test-mcp" }],
  "permissions": {
    "deny": [
      "mcp__Claude_Browser", "mcp__claude-in-chrome", "mcp__computer-use", "mcp__Claude_Code_iOS_Simulator",
      "mcp__terminal", "mcp__scheduled-tasks", "mcp__mcp-registry", "mcp__visualize", "mcp__easel", "mcp__claude-artifacts",
      "mcp__<connector-uuid-1>", "mcp__<connector-uuid-2>",
      "mcp__ccd_session", "mcp__ccd_turn", "mcp__ccd_session_mgmt", "mcp__ccd_view", "mcp__ccd_window", "mcp__ccd_sidebar",
      "mcp__ccd_pr", "mcp__ccd_settings", "mcp__ccd_connectors", "mcp__ccd_directory", "mcp__ccd_host",
      "Agent", "Artifact", "ArtifactComments", "ArtifactData", "AskUserQuestion", "Bash", "CronCreate", "CronDelete", "CronList",
      "DesignSync", "Edit", "EnterPlanMode", "ExitPlanMode", "EnterWorktree", "ExitWorktree", "Glob", "Grep", "ListAgents",
      "ListPlugins", "ListSkills", "McpTaskCheck", "Monitor", "NotebookEdit", "PushNotification", "Read", "RemoteTrigger",
      "ReportFindings", "ScheduleWakeup", "SearchPlugins", "SearchSkills", "SendMessage", "SendToProject", "SendToProjectContext",
      "SendUserFile", "SuggestPluginInstall", "SuggestSkills", "TaskStop", "TodoWrite", "ToolSearch", "WebFetch", "WebSearch", "Write"
    ]
  }
}
```

Curator writes `claudeMdExcludes` itself; `<home>` is the user's real home directory. In the test `skillOverrides` also held `off` entries for every `anthropic-skills:*` skill; they have no effect, and `enabledPlugins` replaces them.

### B. Claude Desktop 6.28899.6 / CLI 2.1.331 surface inventory (observed in sessions)

| Group | Members |
|---|---|
| Built-in tools, loaded up front | Agent, Artifact, AskUserQuestion, Bash, Edit, ListAgents, Read, ReportFindings, ScheduleWakeup, SearchPlugins, SendUserFile, Skill, SuggestPluginInstall, SuggestSkills, ToolSearch, Write |
| Built-in tools, on demand | ArtifactComments, ArtifactData, CronCreate, CronDelete, CronList, DesignSync, EnterPlanMode, ExitPlanMode, EnterWorktree, ExitWorktree, ListPlugins, ListSkills, McpTaskCheck, Monitor, NotebookEdit, PushNotification, RemoteTrigger, SearchSkills, SendMessage, SendToProject, SendToProjectContext, TaskStop, WebSearch |
| Built-in host MCP servers | Claude_Browser, claude-in-chrome, computer-use, Claude_Code_iOS_Simulator, terminal, scheduled-tasks, mcp-registry, visualize |
| Service host MCP servers | ccd_session, ccd_turn, ccd_session_mgmt, ccd_view, ccd_window, ccd_sidebar, ccd_pr, ccd_settings, ccd_connectors, ccd_directory, ccd_host |
| Host plugins | `anthropic-skills@inline` (account skills), `plugin-authoring`, `easel` |
| Account connectors (example) | Claude Docs, visualize, Gmail, claude-artifacts -- named by UUID from session records in rules |
| Bundled CLI and Code tab skills | init, security-review, loop, schedule, claude-api, update-config, keybindings-help, simplify, code-review, fewer-permission-prompts, dataviz, artifact-design, artifact-diagramming, artifact-capabilities, run, ship, steward |
| Account skills (example) | built-in-browser, chrome-browser, computer-use, consolidate-memory, deep-research, docs, docx, explain-usage, import-memory, morning, pdf, pptx, setup-claude, setup-writing-style, skill-creator, xlsx |
| Agent types (with `Agent`) | claude, claude-code-guide, Explore, general-purpose, Plan, statusline-setup, web-fetch |

The instance toggles from the strict run (26.1-26.5) are in CIP-0036, Appendix A. The profile MCP entry is in CIP-0036, Appendix B.
