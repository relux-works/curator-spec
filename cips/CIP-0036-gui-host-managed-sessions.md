# CIP-0036: GUI-host managed sessions (instance per profile, Claude Desktop)

- **Status:** Draft
- **Owner:** Ivan Oparin (decision)
- **Created:** 2026-11-25
- **Numbering:** reserved by the coordinating S0 change (relux-works/curator-spec#233), which also reserves the shared `launch-env-fragment-v8` and `manager-config-v10`. The CIP-0037 and CIP-0038 draft is relux-works/curator-spec#234.
- **Depends on:**
  - CIP-0035 (session surface);
  - CIP-0034 rev 2 (qualification);
  - home leases (curator #208, `protocol/home-leases.md`). This CIP extends them with a new holder variant (6.6);
  - CIP-0037 r3 (tool and MCP credential mediation, the `curator-credential-broker` plugin). It is needed only to launch profiles with secrets from the Dock (6.5, stage A4). The base v1 does not depend on it.
- **Related:**
  - CIP-0006;
  - CIP-0011 and CIP-0025 (Tier 2: separate OS users and microVMs);
  - CIP-0014 (managed-home snapshots);
  - CIP-0033 (precedent for the O11 (a) record);
  - environments sections 7.8, 10.3, 10.5, 11.
- **Affects:**
  - environments: a new "GUI hosts" section and the `native-user-config` MCP channel;
  - home leases: a new holder variant `gui-host`, for which the Curator observer is authoritative for both `bind` and `release`;
  - machine configuration (`manager-config-v10`): host records, the expected account, the MCP delivery mode `mcp_delivery`.
- **Implementations:**
  - curator: host registry and `HostAdapter`, data directory, MCP channel, the `gui-host` lease observer, status;
  - curator-agent-launcher: the `curator-app` executable (`curator app ...` commands), `PlatformDriver`, Dock wrappers, `Curator.app`;
  - curator-credential-broker: the broker session for stage A4 (CIP-0037 r3).
- **Evidence:** [Claude Desktop evidence note](../.research/261126_claude-desktop-managed-sessions-evidence.md). Below, "fact N" refers to that note.

## 1. Summary

A GUI host (here Claude Desktop) launches agent sessions itself. By default it reads one config directory for the whole application and mixes the sessions, account and extensions of all profiles in one list.

This CIP proposes **one host instance per profile**:
- the instance config directory is the profile managed home (`CLAUDE_CONFIG_DIR` in the instance environment);
- the instance has its own host data directory (`--user-data-dir`): login, session list, instance settings. Curator owns this directory, and it lives outside the managed homes;
- CIP-0035 sets the session surface, and instance toggles switch built-in host features off;
- the profile MCP servers reach the session through `mcpServers` in the managed home `.claude.json`. This is the new `native-user-config` channel, enabled by the profile setting `mcp_delivery`. Secrets are written only as `${NAME}` references.

**Home lease.** While the instance runs, it holds the lease on its home, so Curator writers do not touch the live home. Claude.app has no session manager, so the holder is a new variant, `gui-host`. Curator's own observer confirms both `bind` and `release` from the kernel and `SingletonLock`, not from a launcher message (6.6).

**Section 10.5.** Working directly on the live managed home is the same recorded temporary incompatibility with section 10.5 that other adapters have until snapshots exist (O11 (a)).

**Who does what.** The Curator core provides the home, the surface, the data directory and the host record. curator-agent-launcher launches, builds Dock wrappers and forwards links.

## 2. Motivation

1. **A profile in the GUI.** A project opens in the app with the profile context, skills and MCP servers, without the native `~/.claude` (12-15, 17).
2. **Several profiles at once.** Each in its own window with its own session list (5, 9).
3. **Surface** per CIP-0035: from full to "two skills and one MCP server".
4. **Different accounts.** The work profile runs under the company account and the personal one under a personal account (7).
5. **Launch from the Dock.** A profile wrapper is easy to tell apart by its ribboned icon and name.
6. **Sign-in to services.** The browser callback after sign-in must reach the right profile (27, 28).
7. **Freshness.** The home is repaired before every launch, as in `curator run`.
8. **Platforms.** macOS first, then Linux with its own verification, then other hosts.

## 3. Terms

| Term | Meaning |
|---|---|
| **GUI host** | A desktop application that launches agent sessions itself. |
| **Instance** | A running host process with its own data directory. |
| **Data directory** | The application directory (Electron `userData`): login, session list, instance settings, a copy of the CLI (63). |
| **Wrapper** | A small per-profile application that launches the profile instance from the Dock. |
| **`Curator.app`** | One signed Curator application. It accepts its own link scheme and forwards a link to the right instance. Later it also hosts the CIP-0037 confirmation GUI. |

## 4. Current state

**Already works manually:**
- an instance per profile: facts 2-9;
- context and trust from the managed home: 12-14;
- skills: 15;
- MCP through `.claude.json`: 17, 18;
- surface: CIP-0035.

**Missing:**
- **MCP channel.** The current `curator run` channel (`--mcp-config --strict-mcp-config`, section 7.8) does not reach GUI sessions (16). CLI launches ignore `.claude.json` `mcpServers` because of `--strict-mcp-config`, so the new channel does not disturb them.
- **Host self-update.** The host updated itself during the tests, from 6.28899.6 to 7.37095.0 (65). Also, each data directory has its own copy of the CLI (63).

**Rejected:** replacing `HOME` for Claude (32-36).

## 5. Options considered

| Question | Chosen | Rejected, and why |
|---|---|---|
| How to pass the home | Instance process environment (2-4) | Shell profile: edits `.zshrc`, one profile for everything. Desktop setting: one for the whole app. `HOME` replacement: the data directory does not move, Keychain breaks, the CLI protected paths move (32-35) |
| How to separate instances | Own data directory (`--user-data-dir`) (5-7, 9) | Shared data directory: one instance, sessions of other profiles show as "not found on disk" (9) |
| How to deliver MCP | `mcpServers` in the managed home `.claude.json` (17) | `--mcp-config`: the host passes no flags (16). `claude_desktop_config.json`: it configures chat, not Code sessions |
| Launch form | Launcher command plus thin Swift wrappers | Script application: no Dock menu, the icon disappears |
| Link forwarding | Own scheme through the signed `Curator.app` | Launch arguments: on macOS a repeated launch does not parse a link from arguments (29) |

## 6. Design

### 6.1 Division of responsibility

| Part | Repository | Does |
|---|---|---|
| Core | curator | Host registry and `HostAdapter`, data directory and its ownership, the `mcp_delivery` mode and the `native-user-config` channel, the `gui-host` lease observer, data for instance toggles, the expected account, `env status` rows |
| Launcher | curator-agent-launcher (`curator-app` executable) | `PlatformDriver`, instance launch, pre-launch checks (preflight), lease requests (`acquire`, `bind`, `release`), post-launch check, Dock wrappers, `Curator.app` |

**The command name is `curator app`.** It works through umbrella subcommand discovery (environments section 11):
- curator-agent-launcher installs the `curator-app` executable into the trusted install directory next to `curator`, or into one of the `provider_directories`;
- the operator runs `curator app launch|install|repair|remove|list`. The core does not implement `app`, finds `curator-app` and passes the arguments verbatim;
- the core knows nothing about the launcher code: no provider registry and no provider flags (section 11). `curator-run` works the same way.

**Two interfaces from day one.** Host knowledge and OS knowledge are separate.

- **`HostAdapter`** (curator: interface in `internal/hostapi`, registry in `internal/hostregistry`, adapters in `internal/host/<host_id>`). Modeled on `internal/harnessboundary`, it knows everything about a specific host:
  - the host record (6.2);
  - setting paths and keys, instance toggles;
  - the account skills plugin identifier;
  - the inventory for qualification.

  Strings specific to Claude Desktop (paths, `claude_desktop_config.json` keys, `anthropic-skills@inline`) never leave the `claude_desktop` adapter. The next adapters are `opencode_desktop` and `codex_app`. `antigravity_ide` needs its own CIP (6.15).
- **`PlatformDriver`** (curator-agent-launcher) -- the mechanics of a specific OS:

  | Method | Does | macOS, stage 1 |
  |---|---|---|
  | `VerifyBundle` | Checks the host bundle by path and signature | `CFBundleIdentifier` and Team ID (6.12) |
  | `SpawnInstance` | Launches the instance with environment and arguments, returns the PID | `NSWorkspace.openApplication`, PID from `NSRunningApplication` |
  | `ObserveProcess` | Reads the process start environment for the post-launch check | `KERN_PROCARGS2` |
  | `ActivateRunning` | Brings the window of a running instance forward | `NSRunningApplication` |
  | `CheckDataLock` | Determines who holds the data directory | `SingletonLock` |
  | `ExcludeFromBackup` | Excludes the data directory from backups and indexing | `tmutil addexclusion` (6.3) |
  | `InstallShortcut` | Installs the profile wrapper | thin Swift wrapper (6.13) |

  The lease observer (6.6) lives in the core and does not call `PlatformDriver`: lease evidence cannot come from the launcher. Its platform sources are the ones defined in home leases.

### 6.2 Host record

| Field | Claude Desktop (macOS) |
|---|---|
| `host_id` | `claude_desktop` |
| `env_id` | `claude_code` |
| `app` | `/Applications/Claude.app`; `CFBundleIdentifier` `com.anthropic.claudefordesktop`; Team ID `Q6L2SF6YDW` (66) |
| `config_dir_channel` | env `CLAUDE_CONFIG_DIR` |
| `data_dir_channel` | arg `--user-data-dir=<path>` |
| `instance_scope` | data directory (`SingletonLock`) |
| `host_override_check` | the `CLAUDE_CONFIG_DIR` value in Desktop settings must be empty |
| `cli_location` | `<data dir>/claude-code/<version>/<hash>/claude.app` (63) |
| `link_scheme` | `claude` |
| `capabilities` | the CIP-0034 capabilities from section 7 |

The record has no list of "verified versions": that is the verdict of the CIP-0034 registry.

### 6.3 Host data directory

- **Where:** `~/.curator/hosts/<host_id>/<profile>/`, mode `0700`.
- **Why not under `~/.curator/environments/`.** That tree holds deterministic managed homes, scanned by `status`, `gc`, `profile remove` and CIP-0014 snapshots. The data directory is hundreds of megabytes of mutable Chromium state, including the account login.
- **Exclusions.** The data directory:
  - never enters context packages (`contextpkg`) or managed-home snapshots (CIP-0014);
  - is secret state for backups: either not copied, or copied as a secret;
  - is excluded from Time Machine (`tmutil addexclusion`, the marker lives on the directory itself);
  - is excluded from Spotlight. The method must be verified on target macOS versions: `.metadata_never_index` works reliably only at a volume root.
- **`profile remove`** deletes the data directory only with explicit confirmation: it holds the login and the session list.
- **CLI copy** inside the directory (63). Its version and SHA-256 are checked on every launch (section 7).
- **`env status`** shows a host row:
  - whether the data directory exists and the instance runs;
  - whether the wrapper is installed;
  - host and CLI versions, the qualification verdict;
  - toggle drift.

### 6.4 The `native-user-config` MCP channel and the `mcp_delivery` mode

**The delivery mode is a profile setting.** The operator sets it in machine configuration, next to `surface` (CIP-0035):

```json
"mcp_delivery": "launch-flag | native-user-config"
```

- **`launch-flag`** is the default and the current behavior: MCP arrives only through the `--mcp-config --strict-mcp-config` flags of `curator run` (section 7.8). `.claude.json` does not change, so the frozen `internal/harnessparity` golden tests for ordinary CLI profiles stay green.
- **`native-user-config`.** The `--mcp-config` channel of `curator run` stays as is. In addition Curator writes `mcpServers` into the managed home `.claude.json`. The profile MCP servers then reach GUI host sessions and a manual `CLAUDE_CONFIG_DIR=<home> claude`.
- **Effective mode:**
  - `native-user-config` if a GUI host is bound to the profile, that is, a host record from `curator app install` exists;
  - otherwise the operator value, an explicit opt-in for manual CLI use;
  - otherwise `launch-flag`.

  `env status` shows the mode and its source: `default`, `operator` or `host-binding`. When both the binding and the opt-in are gone, `--repair` removes Curator's entries from `.claude.json`.

**The `native-user-config` channel:**
- **What is written.** User-level `mcpServers.<name>` in the managed home `.claude.json`. The set comes from the same resolved MCP set as the `curator run` `--mcp-config`, so there is one source.
- **Ownership by key.** Curator edits only its own entries and preserves the rest of the file, which Claude maintains. The channel does not only append: `--repair` restores its entries and removes those no longer needed.
- **Who writes and when.** Only `env resolve --repair` (W01), and only while the home is not leased by a live instance (6.6). The host itself rewrites `.claude.json` while it runs.
- **`curator run` is unaffected in this mode too:** `--strict-mcp-config` ignores `.claude.json` `mcpServers` (section 7.8).
- **Loading mode.** CIP-0035 `load.mcp` is written as `alwaysLoad` (18).

### 6.5 Environment and secrets

- **Only references on disk:** `"env": {"TOKEN": "${TOKEN}"}`. Substitution works (58, 71). The values themselves are not in `.claude.json`.
- **This CIP introduces no secret mechanism of its own.** Curator has no general secret store for arbitrary MCP `env_names` (for example `ACME_TOKEN`) today, and a Dock-only solution would be a workaround. The general architecture is CIP-0037; this CIP connects to it at stage A4.

**Base v1 (before CIP-0037 A4):**
- **Terminal launch.** `curator app launch` takes the values for `${NAME}` references from the calling process environment and passes them into the instance environment. Only names from `passable_env_names` are passed (section 10.3).
- **No value.** The launch refuses with `mcp_env_reference_unset` beforehand. Otherwise the server would receive the literal string `${NAME}` (58).
- **Launch from the Dock.** The wrapper has no operator environment. A profile with `env_names` refuses from the Dock with `mcp_env_reference_unset`. Profiles without `env_names` launch from the Dock normally.

**With CIP-0037 r3 (stage A4):**
- **Separate plugin.** The mediator is the `relux-works/curator-credential-broker` plugin, attached through environments section 11 like `curator-app`. The Linux-only `swarma-credential-broker` stays with CIP-0011: model subscriptions, no HTTP forwarding and no plugins.
- **Two processes.**
  - `curator-auth-custody` keeps the values in Keychain, Secret Service or Credential Manager.
  - `curator-auth-gateway` works strictly over a Unix socket, with no TCP ports.
- **Broker session.**
  - `CURATOR_AUTH_SESSION` is issued per `(profile, host_instance)` and shared by all sessions and MCP servers of that instance.
  - The session has its own mandatory `max_ttl`, for example 12 hours, extended while the instance lives.
  - The lease `release` (6.6) revokes it early.
  - The session does not have to depend hard on the curator #208 leases.
- **Remote HTTP MCP servers (mode A)** go through `curator-mcp-bridge`: `stdio` <-> Streamable HTTP over the broker Unix socket. There is no `127.0.0.1:<port>` anywhere. The gateway adds the authorization header, so no `${VAR}` in `headers` is needed.
- **Legacy `stdio` MCP servers (mode C)** start through `curator-mcp-exec`.
- CIP-0037 defines the shape of the `.claude.json` entries for both modes.

**What this gives on Tier 1** (one OS user, macOS and Linux). The threat model is stated honestly, same-UID:
- **Removed.** CIP-0037 removes secrets from disk, from `.claude.json`, from argv and from the model context. Launch from the Dock works.
- **Not provided.** There is no isolation from a hostile agent or from `Bash` in the session. Any process of the same UID, including `Bash` in the session, can read the environment of a child `curator-mcp-exec` or `CURATOR_AUTH_SESSION` through `KERN_PROCARGS2` or `/proc/<pid>/environ`.
- **Real isolation** exists only on Tier 2: separate OS users (CIP-0011) or microVMs (CIP-0025). There, mode C under the `hardened` posture is forbidden without an explicit waiver.

**Incompatibility with section 10.3 (S4).** The host itself merges the user's login-shell environment into sessions (3). So the `passable_env_names` allowlist cannot be honored in GUI sessions: any variable from `.zshrc` reaches the sessions. A value passed at launch still wins over a `.zshrc` variable of the same name (71).
- This is recorded as a limitation. CIP-0037 removes MCP secrets from the environment, but not the other login-shell variables.
- Under the `hardened` posture the launch refuses with `host_env_unbounded` until the operator explicitly acknowledges it.
- Whether the merge can be disabled is not known yet (question 4).

### 6.6 Live instance and writers (home leases)

The instance holds the home lease for as long as it runs.

**Why not the `curator-run` holder.** Per `protocol/home-leases.md`:
- a `bound` holder is tied to a registered session manager: `manager_id`, `manager_registered_at`, a session and a positive `generation` (HL05);
- `bind` compares the tuple with the authoritative manager observation, which Curator obtains through the read-only `curator-run session-manager observe --schema v2` (HL07, HL23);
- `release` requires Curator to reconcile the termination of the session and all descendants itself (HL09). The specification explicitly does not accept a cooperative `release`: a launcher message "the app exited, release the lease" is not evidence.

Claude.app has no session manager: LaunchServices starts the instance, and no manager spawns or retains it. So the `curator-run` holder passes neither `bind` nor `release`. This replaces the `curator-run` holder chosen in an earlier draft.

**New holder variant `gui-host`** (working name; alternative `app-instance`, question 9). It extends the closed HL05 union; the `curator-run` variant does not change:
- `kind`: `prepared` or `bound`, with the same lifecycle and `request_id` rules (HL06);
- `launcher`: `curator-app`;
- `host_id` from the host registry (6.2);
- `instance` -- the instance launch identifier; null in `prepared`;
- `process` -- the same `{pid, uid, boot_id, start_time}` tuple, but of the **host main process**. It is mandatory in `bound`, as in HL05. A wrapper PID does not qualify.
- The variant has no `manager_id`, `manager_registered_at`, `werkstatt`, `session` or `generation`.
- The holder carries no paths (HL05). Curator derives the data directory `~/.curator/hosts/<host_id>/<profile>/` itself from `host_id` and the lease profile.

**The observer is Curator itself.** For `gui-host` Curator's independent observer is authoritative. It reads the kernel and the data directory; `curator-run session-manager observe` is not called. The launcher PID (from `NSRunningApplication`) is only an input, not evidence.

`bind` succeeds only if one observation pass establishes all of:
1. the `{pid, uid, boot_id, start_time}` tuple is re-read from the kernel and is byte-equal to the requested one. The sources are those of "Independent observer before bind": on macOS `proc_pidinfo`/`PROC_PIDTBSDINFO` and `kern.bootsessionuuid`, on Linux `/proc`;
2. `uid` is the user Curator runs as;
3. the process executable is the main executable of the bundle in the host record (`proc_pidpath` on macOS, `/proc/<pid>/exe` on Linux);
4. `SingletonLock` in the data directory exists and points to this process. On macOS and Linux Chromium makes it a symbolic link `<hostname>-<pid>`.

Otherwise the observer refusal rows of home leases apply. A mismatch gives `environment_lease_holder_mismatch/process_incarnation_mismatch`; an unreadable field gives `environment_lease_authority_refused/authority_unavailable`. The lease stays `prepared` and blocks writers.

`release` succeeds only if Curator itself has proven termination (HL09):
1. the recorded incarnation is gone: the PID is absent or belongs to another incarnation (another `start_time` or `boot_id`);
2. `SingletonLock` in the data directory is absent or points to a process that does not exist;
3. no live process of this user has this home as `CLAUDE_CONFIG_DIR` in its start environment (`KERN_PROCARGS2` on macOS, `/proc/<pid>/environ` on Linux). These are the HL09 descendants: CLI processes and session MCP servers that may outlive the host main process.

Otherwise the result is `environment_lease_release_unconfirmed/termination_unconfirmed`, and the lease stays. An unreadable field or missing permission also retains protection (HL08).

Check 3 sees not only orphaned GUI descendants but any other live session on this home, for example a parallel `curator run claude_code --profile <P>` or a manual `CLAUDE_CONFIG_DIR=<home> claude`. `release` then waits for them to end too. This is intended: for protecting a live home (HL09) the behavior is conservative and safe, not a collision.

**Who requests `release`.** Curator gathers the evidence itself, so anyone may request `release`:
- `curator-app` after the instance exits;
- the next `curator app launch` of the same profile;
- the operator, with `curator env lease release`.

This also covers a Dock launch: the wrapper exits right after start and does not hold the lease.

**Launch order:**
1. `env resolve --repair` (W01): a fresh home and the MCP channel.
2. `acquire` with a `gui-host` holder in state `prepared`. `request_id` is persisted before the first attempt (HL06). op.json `lease_requested` is written as HL21 requires of `curator-run`.
3. Instance toggles (6.8).
4. Launch.
5. `bind` from Curator's observation.
6. After the instance exits: `release` on Curator's evidence and a toggle reconciliation.

**While the lease is alive,** W01-W06 refuse with `environment_home_leased` (HL14, HL19): `env resolve --repair`, `profile update`, `profile use`, `profile install` and migrations.

**An instance started outside the launcher** (for example manually with `open -n`) has no lease. So writers also check the data directory lock (`SingletonLock`) of hosts bound to the home and refuse with `host_instance_running`.

### 6.7 Section 10.5 and O11 (a)

- **Incompatibility.** A GUI instance is a long-lived session directly on the live managed home. It is the same recorded temporary incompatibility with section 10.5 as for `codex_cli`, `muse`, `pi` and `antigravity`: decision O11 (a), note C6.
- **The snapshot route is harder for a GUI.** The session list in the data directory refers to transcripts in `<CLAUDE_CONFIG_DIR>/projects` (9). A snapshot per launch would make older sessions "not found on disk". This needs either a persistent transcript directory outside the snapshot or a stable snapshot path per generation (question 5).

### 6.8 Instance toggles

- **What is written.** CIP-0035 `host_mcp` keys go into `claude_desktop_config.json` -> `preferences` of the data directory (26.1-26.5): `chicagoEnabled`, `claudeIosSimulatorAccessEnabled`, `chromeExtensionEnabled`, `claudeAndroidEmulatorAccessEnabled`, `ccdScheduledTasksEnabled`.
- **When.** Only while the instance is stopped, and only Curator's own keys. After the instance exits the values are reconciled: the host, for example, flips `ccdScheduledTasksEnabled` back (26.5). `env status` shows the drift.
- **What does not exist.** There are no toggles for the built-in browser or for connectors (26.6, 26.7). Only the CIP-0035 denies remain for them.

### 6.9 Surface in a GUI: what is guaranteed

- **The deny layer** holds (CIP-0035, section 7).
- **The setting layer** is checked before launch if the project is passed to the launcher (`--project <dir>`). These keys in the project `.claude/settings.json` and `.claude/settings.local.json` count as widening:
  - `disableBundledSkills: false`;
  - `skillOverrides` with a value other than `off`;
  - `enabledPlugins` with `true`;
  - `allowedMcpServers`, `enableAllProjectMcpServers`, `enabledMcpjsonServers`;
  - `env`.

  For `strict` this refuses with `surface_project_widening`; for `curated` it warns. Folders opened from the host UI skip the check. This limitation is documented (facts 52, 53, 57, 59).
- **Connectors from the first session.**
  - Built-in connector UUIDs come from qualification data (CLI constants, 56) and are denied from the first launch.
  - The account's own connectors are closed by the mask or by an explicit list. In the host the mask removes the connector tools, but the connector instructions stay in the prompt (69).
  - The mask hits any tool with four hyphens in its full name: in the probe an unrelated `probe-env-mcp` disappeared (69). So Curator checks the profile server and tool names before applying the mask (CIP-0035, section 6).
- **Built-in host MCP servers** are closed with `permissions.deny` by real names (22). `allowedMcpServers` does not apply to them, to `ccd_*` or to connectors (68). Whether `deniedMcpServers` applies to host servers has not been checked.

### 6.10 Expected account

- It is set in the profile machine configuration, not in the package: an email address or a domain.
- The launcher reads only the `oauthAccount` metadata (address, organization) from `.claude.json`, never tokens.
- A mismatch warns. Under `hardened` it refuses at the operator's choice.

### 6.11 Foreign policy

Curator only detects foreign policy and reports it in preflight and `env status`. It neither disables nor replaces it.

This CIP has no policy packages. For Desktop the `CLAUDE_CODE_MANAGED_SETTINGS_PATH` path does not work (38), and the work/personal split is done by account and surface.

### 6.12 Launch contract (launcher)

1. **Host.** The bundle is taken by explicit path from the host record, not through `open -a Claude` by name: LaunchServices may pick another copy. `CFBundleIdentifier` and Team ID are checked (66). A mismatch gives `host_bundle_untrusted`.
2. **Qualification.** Tier-0 is checked on every launch (section 7). On an unqualified version `strict` and `curated` refuse with `surface_unqualified`; `full` warns.
3. **Preflight:**
   - the host `CLAUDE_CONFIG_DIR` setting is empty, otherwise `host_config_override_present`;
   - every `${NAME}` reference resolves: in v1 from the calling process environment, with CIP-0037 through the broker (6.5);
   - project check (6.9);
   - account check (6.10);
   - foreign policy detection (6.11).
4. **The instance already runs** (the data directory is held): bring its window forward and exit.
5. **Preparation:** `env resolve --repair`, the lease with a `gui-host` holder, toggles (6.6, 6.8).
6. **Launch** with `NSWorkspace.openApplication`, the environment `{CLAUDE_CONFIG_DIR: <home>, allowed variables}` and the argument `--user-data-dir=<data>`. The PID comes from the result (`NSRunningApplication`), not from a `ps` search. This is the macOS implementation of `PlatformDriver.SpawnInstance` (6.1).
7. **Post-launch check:**
   - the process environment is read independently (`KERN_PROCARGS2`, like `ps -E`);
   - the lease is bound (`bind`). Curator's observer checks the tuple, the bundle and `SingletonLock` itself (6.6).

   Otherwise the result is `host_launch_unverified`.
8. **Follow-up.** When the instance exits, `curator-app` requests `release`. Curator releases the lease, and only on its own evidence of termination (6.6). The launcher then reconciles the toggles.

### 6.13 Wrappers and `Curator.app` (launcher)

**Thin per-profile wrappers** (`~/Applications/Claude - <P>.app`):
- **Build.** A copy of the template, an `Info.plist` with the name and a unique bundle id, a `launcher.json` without secrets, the host icon with a profile ribbon. Ad-hoc signature (30, 31).
- **What they do.** They only launch the instance through `NSWorkspace`. They need no Apple Events and no Automation permission.
- **Rebuild.** `app repair` changes the CDHash, but the wrapper has nothing to lose: it holds no permissions.

**One signed application, `Curator.app`.** Earlier drafts called it `CuratorAppRouter.app`. From the start it is a single Curator application, not a narrow router:
- here it routes links;
- later it also hosts a thin GUI for sign-in and SealLink grant confirmation (CIP-0037).

Properties:
- **Signature.** Developer ID Relux Works, notarized.
- **Links.** Registers `curator-claude://` and sends `kAEGetURL` to the instance by the PID of the `bound` lease record.
- **TCC.** The Automation permission is granted once and survives updates: the designated requirement is stable because it is bound to the Team ID. An ad-hoc signature does not fit here: TCC binds the permission to the CDHash, and the system would ask again after every rebuild.

**Release pipeline.** Signing and notarization of `Curator.app` and the wrapper template run in the release pipeline, together with key custody (owned by the project owner).

**Link forwarding phases:**
1. A wrapper menu item "Open the link from the clipboard in this profile".
2. `curator-claude://<profile>/...` through `Curator.app`.
3. Taking over the system `claude://` scheme is deferred: the host registers itself as its handler and may take the scheme back.

### 6.14 Appearance

- **The main distinction** is the wrapper icon with the profile ribbon and name. A running instance keeps the host icon in the Dock.
- **Theme and zoom** are per instance and stored in the data directory (11).
- **Not used:** Chromium theme switches and CSS injection.

### 6.15 Other platforms and hosts

The 6.1 framework is laid down from the start: a platform is a new `PlatformDriver`, a host is a new `HostAdapter`. Each stage has its own full verification run. Only stage 1 is normative in v1; stages 2 and 3 are placeholders.

| `PlatformDriver` | Stage 1: macOS (normative in v1) | Stage 2: Linux (placeholder) | Stage 3: Windows (placeholder) |
|---|---|---|---|
| Launch | `NSWorkspace`, thin Swift wrappers, signed `Curator.app` | a per-profile `.desktop` file with `StartupWMClass` | `.lnk` or a thin `.exe` with a unique `AppUserModelID` and its own `.ico` |
| Links | `Curator.app` and Apple Events (6.13) | `x-scheme-handler` with the link passed in argv | `HKCU\Software\Classes` and the Electron `second-instance` event |
| Process | `proc_pidinfo` | `/proc/<pid>/stat` | `CreateProcess`. The stub process PID (Squirrel `Update.exe`, MSIX install) must be told apart from the main process |
| Data directory | `SingletonLock`, `tmutil` | `SingletonLock`; detect Flatpak or Snap installs, which have their own paths and sandbox | Chromium locks the data directory differently on Windows; the method is defined in that stage |
| `read-only` analog | `0400` | `0400` | NTFS ACL |

Home leases have no Windows `start_time` variant or `boot_id` source yet. Until stage 3, `bind` refuses there with `authority_unavailable`.

**Other hosts** are separate `HostAdapter`s:
- **OpenCode Desktop** -- `opencode_desktop`;
- **Codex app** -- `codex_app` (`CODEX_HOME`);
- **Antigravity IDE** -- a separate CIP, `antigravity_ide`, once the `~/.gemini` question is settled: no variable exists for that directory.

## 7. Host qualification (CIP-0034 rev 2)

| Capability | Confirms | Facts |
|---|---|---|
| `host.config-dir-env/1` | The instance takes the home from the process environment | 2-4 |
| `host.data-dir-arg/1` | Parallel instances, each with its own login and session list | 5-7, 9 |
| `mcp.native-user-config/1` | `.claude.json` `mcpServers` start in sessions | 17 |
| `mcp.always-load/1` | `alwaysLoad` loads tools without `ToolSearch` | 18 |
| `mcp.env-expansion/1` | `${NAME}` is substituted from the instance environment; the launch value wins over `.zshrc` | 58, 71 |
| `host.instance-toggles/1` | `preferences` keys remove servers and prompt sections | 26.1-26.5 |
| `host.account-plugin-id/1` | The account skills plugin identifier | 21, 39 |
| `host.connector-ids/1` | Built-in connector UUIDs in the CLI binary | 56 |
| `host.tool-inventory/1` | Tools and servers the host adds (including the name `Agent`) | 49, 68-70, Appendix B of the evidence note |

A host property, not a capability, is recorded separately: the host merges the login-shell environment (3, 71, section 6.5).

**Self-update** (65). Keeping a sealed binary per CIP-0034 does not fit a signed application in `/Applications` that updates itself. A GUI sign-in on headless CI is not possible either. So host qualification has three parts:
- **Tier-0 on every launch:**
  - bundle version (`Info.plist`) and Team ID;
  - version and SHA-256 of the CLI in the data directory (63);
  - presence of the known keys in `claude_desktop_config.json`;
  - the login-free init of this CLI (48) for the CLI inventory.
- **Local host smoke** on the operator machine after every host update (section 13). It leaves a machine receipt (below). The session composition comes from the `api-request-shape` transcript record (72), not from the model's answers.
- **`surface_unqualified`** holds until a receipt with `result: "pass"` exists for the current triple.

**Local smoke receipt.** The key is the triple `(app_bundle_version, app_team_id, embedded_cli_sha256)`. The receipt lives in manager state, for example `state/host-smoke/v1/<host_id>/<SHA-256 of the triple>.json`:

```json
{
  "receipt": "host-smoke-receipt-v1",
  "host_id": "claude_desktop",
  "key": { "app_bundle_version": "7.37095.0", "app_team_id": "Q6L2SF6YDW",
           "embedded_cli_sha256": "b76a8345f6c00c40..." },
  "embedded_cli_version": "2.1.331",
  "platform": "darwin-arm64",
  "suite_sha256": "<digest of the smoke suite>",
  "result": "pass | fail",
  "capabilities": {
    "host.instance-toggles/1": { "result": "pass" },
    "mcp.always-load/1": { "result": "pass" },
    "host.tool-inventory/1": { "result": "pass",
      "details": { "source": "host-smoke", "...": "shape per CIP-0035, section 8" } }
  },
  "observed_at": "2026-11-25T06:40:00Z"
}
```

- Details live inside the capability, keyed by its ID, as in CIP-0034 `capabilities["<cap_id>"].details`. The host inventory is under `host.tool-inventory/1`.
- The receipt is unsigned and valid only on this machine. It does not replace the signed CIP-0034 `harness-qualification-v1` record.
- If the host version is qualified centrally, the same inventory is in the signed record under `capabilities["host.tool-inventory/1"].details`. It reaches the fragment as `qualification.capability_details["host.tool-inventory/1"]`.
- A change in any element of the triple makes the receipt inapplicable: for example the host updated itself (65) or the data directory has another CLI copy (63).

**Reasons inside `surface_unqualified`.** The typed CIP-0034 rev 2 code is kept in the reason field, not replaced by the generic verdict. The order is the CIP-0034 priority: if several reasons apply, the first is reported.

| # | Reason | When |
|---|---|---|
| 1 | `qualification_artifact_revoked` | The whole artifact is revoked: the CLI or host version |
| 2 | `qualification_capability_revoked` | A capability the preset requires is revoked |
| 3 | `qualification_capability_regressed` | A capability confirmed on an earlier version fails on the current one |
| 4 | `qualification_capability_unqualified` | A record for the version exists, but the required capability has the verdict `unqualified`, `not_run` or `not_applicable` |
| 5 | `qualification_record_missing` | No signed record for the CLI version, or no receipt for the host triple |
| 6 | `qualification_host_smoke_failed` | A receipt for the triple exists with `result: "fail"` |

## 8. Diagnostics

| Code | When |
|---|---|
| `host_bundle_untrusted` | The bundle path, `CFBundleIdentifier` or Team ID did not match |
| `host_config_override_present` | The host settings set their own config directory |
| `host_instance_running` | A writer found a live instance without a lease on this home |
| `host_launch_unverified` | The environment or the data directory lock was not confirmed after launch |
| `host_env_unbounded` | `hardened`, and the host merges the login-shell environment |
| `mcp_env_reference_unset` | A `${NAME}` reference has no value. In v1 a Dock launch of a profile with `env_names` refuses the same way until CIP-0037 (6.5) |
| `surface_project_widening` | The project widens the surface (6.9) |
| `surface_unqualified` | The CIP-0034 verdict for the host or CLI version. The typed CIP-0034 reason is kept (section 7) |
| `environment_home_leased` | Existing lease code (HL19) |
| `environment_lease_holder_mismatch` / `environment_lease_authority_refused` | Existing lease codes: Curator's observer did not confirm the `bind` of a `gui-host` holder (6.6) |
| `environment_lease_release_unconfirmed` | Existing lease code: Curator did not prove the termination of the instance and its descendants (6.6) |

## 9. Security considerations

- **The data directory** holds the login: cookies and tokens. Mode `0700`, plus the exclusions in 6.3. Curator does not read tokens.
- **`HOME` is not replaced** (32-36).
- **Foreign policy** is neither disabled nor replaced (6.11).
- **The lease is not cooperative.** Neither `bind` nor `release` accepts a launcher assertion as evidence. Curator reads the kernel, the bundle, `SingletonLock` and process environments itself (6.6). A crashed launcher or a wrapper that exited at once does not lift protection.
- **MCP secrets** are stored on disk only as references (6.5). In v1 the values come from the terminal environment. With CIP-0037 they go through `curator-credential-broker` and disappear from disk, `.claude.json`, argv and the model context.
  - On Tier 1 (same-UID) a process of the same user, including `Bash` in the session, can still read the environment of `curator-mcp-exec` or `CURATOR_AUTH_SESSION` (`KERN_PROCARGS2`, `/proc/<pid>/environ`).
  - Only Tier 2 (CIP-0011, CIP-0025) isolates secrets from a hostile agent.
  - The login-shell environment merge is a recorded limitation.
- **Apple Events** are sent only by the signed `Curator.app`, and only to instances from lease records. Wrappers hold no permissions.
- **Host authenticity** is checked by Team ID before launch (6.12).
- **Remote tools.** Instances compete for the remote-tools "device" (10). The documentation must state that using the machine from other devices probably works only in the first instance.

## 10. Compatibility and migration

- `curator run` and existing managed homes do not change.
- The native host instance works as before: a normal Dock launch opens the app with `~/.claude`.
- Data directories, host records, wrappers, `Curator.app` and the `gui-host` lease variant are new entities. `curator-run` lease records do not change. Curator does not touch the existing application data directory.
- A host update may change internal identifiers. Until the smoke passes, `surface_unqualified` applies (section 7).

## 11. Specification changes

1. **Environments, a new "GUI hosts" section:** host registry and record (6.2), data directory (6.3), launcher contract (6.12) and diagnostics (section 8).
2. **Environments section 7.8:** the `native-user-config` channel for `claude_code` (6.4).
3. **Environments section 10.3:** `${NAME}` references and the login-shell environment limitation (6.5).
4. **Environments section 10.5:** the O11 (a) record for GUI hosts (6.7).
5. **Home leases:** a new holder variant `gui-host` (`launcher: curator-app`), section 6.6.
   - Curator itself is the authoritative observer for both `bind` and `release`. It checks the kernel tuple `{pid, uid, boot_id, start_time}`, the bundle path, the data directory `SingletonLock` and the absence of live descendants on this home.
   - HL05, HL07, HL09 and HL23 gain rows for this variant. The `curator-run` rows do not change.
   - The process is the host main process, not the wrapper.
6. **CIP-0034 catalog:** host capabilities, the host inventory in `capabilities["host.tool-inventory/1"].details`, and the local smoke receipt (section 7).
7. **Machine configuration (`manager-config-v10`):** the `mcp_delivery` profile setting (6.4).
8. **Connection to CIP-0037 r3:** MCP secrets for Dock launches through `curator-credential-broker`; the session per `(profile, host_instance)`; the Tier 1 threat model (6.5, stage A4).

## 12. Implementation plan

| # | Repository | What | Depends on |
|---|---|---|---|
| S2 | curator-spec | This CIP, environments text, home leases with the `gui-host` variant (schema, vectors) | S1 (CIP-0035) |
| Q-H | curator-spec / suites | Host capabilities in the CIP-0034 catalog, the host smoke, the receipt format | CIP-0034 Q1 |
| I2 | curator | `mcp_delivery` and the `native-user-config` channel: ownership, `--repair`, `status` | S2 |
| I3 | curator | `HostAdapter` and host registry, data directory, the `gui-host` lease observer (`bind`/`release`), expected account, status rows, the `SingletonLock` check in writers | S2, curator #208 |
| I4 | curator-agent-launcher | `curator-app launch`, the macOS `PlatformDriver`, preflight, Tier-0, the `gui-host` lease for the instance lifetime, post-launch check | I3 |
| I5 | curator-agent-launcher | Wrapper template, `curator app install/repair/remove/list`, ribboned icon, ad-hoc copies | I4 |
| I6 | curator-agent-launcher | `Curator.app` (Developer ID, notarization): link routing, phases 1-2 | I5 |
| A4 | curator-agent-launcher, curator-credential-broker | Broker session per `(profile, host_instance)` with `max_ttl` and early revocation on `release`. `curator-mcp-bridge` (mode A) and `curator-mcp-exec` (mode C). Dock launch with secrets | I4, CIP-0037 r3 |
| D | docs | User and operator documentation | I5 |

Critical path to "Claude - P" in the Dock with `strict`: P0 -> S1 -> S2 -> I3 -> I4 -> I5. I1 and I2 run in parallel with I3 and I4. A4 is not on the critical path: without it only profiles without `env_names` launch from the Dock (6.5).

## 13. Test plan

A host smoke per host version and platform. It also runs after every host update.

1. **Instance.** `CLAUDE_CONFIG_DIR` in the process environment. A second instance starts alongside. The data directory is held by its own process. Curator's observer binds the `gui-host` lease to the host main process.
2. **Lease.**
   - `bind` with a wrapper PID, with a foreign bundle or with a `SingletonLock` of another process refuses;
   - `release` while the instance is alive refuses with `termination_unconfirmed`;
   - `release` after the main process exits, while a CLI or MCP process with this `CLAUDE_CONFIG_DIR` is alive, refuses too;
   - after a full exit `release` succeeds even if a process other than the launching one requested it;
   - Dock launch: the next `curator app launch` or the operator releases the lease.
3. **Context.** The base and overlay codewords are present. Native markers are absent. In a control launch without exclusions the markers are present.
4. **Skills and MCP.**
   - The skill secrets and the MCP codeword are received. `alwaysLoad` works.
   - The server log holds the hash of the `${NAME}` value, not the literal reference. The launch value wins over a `.zshrc` variable of the same name (71).
   - A Dock launch of a profile with `env_names` refuses with `mcp_env_reference_unset` until CIP-0037.
5. **Surface.** The CIP-0035 presets, plus the allowlist against host servers (68), the connector mask from the first session (69) and `ENABLE_TOOL_SEARCH` in a host session (70). The smoke takes the session composition from the `api-request-shape` transcript record (72), not from the model's answers.
6. **Writers.** `env resolve --repair` with a live instance refuses (`environment_home_leased`). For an instance started outside the launcher, `host_instance_running`.
7. **Sessions.** The instance session list holds only the profile sessions.
8. **Links.** A controlled link reaches the profile instance through `Curator.app`.
9. **Negative checks:**
   - foreign bundle;
   - the host sets its own config directory;
   - the project widens the surface;
   - no value for `${NAME}`;
   - signed in to the wrong account;
   - unverified host version.
10. **Platforms:** macOS arm64 (verified manually), macOS x86_64. Linux and Windows are separate stages (6.15).

## 14. Open questions for the operator

1. **Data directory.** Recommendation: `~/.curator/hosts/<host_id>/<profile>/`.
2. **Wrappers and `Curator.app`.** Decided: thin ad-hoc wrappers for launch only, and one signed `Curator.app` for links and later for the CIP-0037 confirmation GUI (6.13).
3. **Default preset.** Recommendation: `full`; `curated` and `strict` only explicitly.
4. **Login-shell environment.** Can the host be kept from merging it? If not, `hardened` keeps the refusal or an explicit acknowledgment.
5. **Snapshots for a GUI.** A persistent transcript directory, or a stable snapshot path per generation?
6. **Expected account.** Recommendation: machine configuration, warning only, refusal under `hardened` at the operator's choice.
7. **Command name.** Decided: `curator app launch|install|repair|remove|list`, the `curator-app` executable from curator-agent-launcher through environments section 11 (6.1).
8. **Order.** Recommendation: P0 -> CIP-0035 -> this CIP (macOS) -> wrappers and `Curator.app` -> Linux -> Windows. Other hosts (`opencode_desktop`, `codex_app`) are separate adapters; `antigravity_ide` is a separate CIP.
9. **Lease holder variant name.** `gui-host` or `app-instance`. Recommendation: `gui-host`, paired with `launcher: curator-app` (6.6).
10. **Leases on Windows.** Which `start_time` variant and which `boot_id` source home leases add for stage 3 (6.15).

## Appendices

### A. Instance toggles (`claude_desktop_config.json` in the data directory, instance stopped)

```json
{ "preferences": { "chicagoEnabled": false, "chromeExtensionEnabled": false,
  "claudeIosSimulatorAccessEnabled": false, "claudeAndroidEmulatorAccessEnabled": false,
  "ccdScheduledTasksEnabled": false } }
```

### B. Profile MCP in the managed home `.claude.json` (secret by reference)

```json
{ "mcpServers": { "acme-tracker": {
  "type": "stdio", "command": "acme-tracker-mcp", "args": [],
  "env": { "ACME_TOKEN": "${ACME_TOKEN}" }, "alwaysLoad": true } } }
```

In v1 `curator app launch` takes the `ACME_TOKEN` value from the terminal environment and passes it into the instance environment only if the name is in `passable_env_names`. A Dock launch of such a profile refuses with `mcp_env_reference_unset` until CIP-0037 (6.5).

### C. Commands used for verification

```
open -n -a /Applications/Claude.app --env CLAUDE_CONFIG_DIR=<home P> --args --user-data-dir=<data P>
curator env resolve claude_code --profile <P> --repair --format json
ps -E -ww -p <pid> -o command= | tr ' ' '\n' | grep '^CLAUDE_CONFIG_DIR='
codesign -dv /Applications/Claude.app      # Identifier and TeamIdentifier
```
