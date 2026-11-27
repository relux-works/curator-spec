# CIP-0035: Claude Code session surface projection

- **Status:** Draft
- **Owner:** Ivan Oparin (decision)
- **Created:** 2026-11-25
- **Numbering:** reserved by the coordinating S0 change (relux-works/curator-spec#233), which also reserves the shared `launch-env-fragment-v8` and `manager-config-v10`.
- **Depends on:** CIP-0006. It is accepted but not implemented yet; its implementation (P0) comes first.
- **Related:**
  - CIP-0034 -- qualification registry: capabilities and the `surface_unqualified` verdict;
  - CIP-0036 -- GUI hosts, the consumer of this projection;
  - Decision 0013 and Decision 0019 (one construction site for argv), CIP-0018 D1;
  - curator: `docs/qualification/project-source-exclusion-claude.md`.
- **Affects:**
  - machine configuration: the `surface` member of `environments.profile_settings` in `manager-config-v10`;
  - environments: the `profile_settings` section;
  - `claude_code` adapter: publication of keys into `settings.json`;
  - `launch-env-fragment-v8`: the closed member `surface.setting_sources: "user"`. It is one shared revision with the CIP-0034 `qualification` member. It carries no raw argv (environments section 10.3).

  Implementations, one per repository:
  - curator -- the projection and the fragment member;
  - `relux-works/skill-agents-management` (`pkg/agentic/systems/claude/`) -- renders `--setting-sources user` and refuses a conflicting `--setting-sources` in `NativeArgs`;
  - curator-agent-launcher -- accepts the new fragment revision and passes the member into `LaunchRequest`. It does not spell the flag and does not read `profile_settings`.
- **Evidence:** [Claude Desktop evidence note](../.research/261126_claude-desktop-managed-sessions-evidence.md). Below, "fact N" refers to that note.

## 1. Summary

The operator describes, per profile, what the model sees: tools, skills, plugins, MCP servers and connectors, and which of them load up front. Curator expands this into native Claude Code keys in the managed home `settings.json`.

**Record owner.** The record is machine configuration owned by the operator. It is a new `surface` member of the closed CIP-0006 `profile_settings` record. Profile packages do not set the surface.

**Presets.** `full`, `curated`, `strict` and `custom` expand from the qualification data of the exact CLI version (CIP-0034). If the version is not qualified, Curator reports `surface_unqualified` and guesses nothing.

**Consumers.** Both `curator run` (for example `strict` for autonomous agents) and GUI hosts (CIP-0036) need the projection.

**Guarantees depend on the layer:**
- **deny rules** hold whatever the project settings say;
- **setting keys** can be overridden by the project. In `curator run` the `--setting-sources user` flag closes that gap. Curator sends it as a closed fragment member, and skill-agents-management spells the argv. In a GUI host only the pre-launch project check remains (CIP-0036).

## 2. Motivation

- **Fully managed agent.** For example, "our two skills and our one MCP server", without bundled skills, plugins, connectors or built-in tools. Verified live up to the strict level (facts 19-26 and the strict run).
- **One account, different surfaces.** One profile shows the account skills and another does not, while the account stays the same (21).
- **Loading.** What loads up front and what loads on demand (18, 57, 67).
- **Autonomous agents under `curator run`.** The same `strict`, without a GUI.

## 3. Scope

**In scope:**
- the `surface` member in `environments.profile_settings.<P>.<scope>.providers.claude_code`;
- presets and their expansion from qualification data;
- publication of keys into `settings.json` and of the MCP loading mode into the MCP channel;
- the closed fragment member `surface.setting_sources` and its rendering in skill-agents-management;
- merge rules with the nine CIP-0006 paths, and publication of its hard MCP deny into `deniedMcpServers`;
- the `surface_unqualified` verdict through CIP-0034.

**Out of scope:**
- a surface section in the profile package (section 13);
- `codex_cli` and other environments: same framework, projection tables later;
- instance toggles and prompt sections of a GUI host. CIP-0036 projects the `host_mcp` keys into instance settings;
- account settings.

## 4. Current state

- **CIP-0006.** Accepted: a closed machine record `profile_settings` with exactly nine provider paths and per-server MCP choices. Not implemented in rc.10 (47).
- **`settings.json` is runtime-owned.** Curator owns only the exclusions it recorded (`internal/envprofile/claude_settings.go`).
- **A key writer already exists.** It is a transactional write with preimage checks (`claude_ancestor_settings.go`, state `state/claude-memory/v1/`). There is also `claude_settings_mode=read-only` (`0400` on `settings.json`, `cowork_settings.json`, `.config.json`).
- **Project source exclusion.** The `--setting-sources user` flag is described in the curator qualification record `project-source-exclusion-claude.md` (2.1.305). It records native behavior and is not a product integration. Fact 59 confirms the behavior on 2.1.331.
- **Who builds the launch:**
  - The launcher (`curator-run`) reads neither `~/.curator/config.json` nor `profile_settings`. It receives only the closed `launch-env-fragment-vN` from Curator, currently v7 from CIP-0033 (Decision 0013, CIP-0018 D1).
  - Every argv element and context channel of Claude Code is spelled in one place, skill-agents-management `pkg/agentic/systems/claude/` (Decision 0019). Conflicting `NativeArgs` are checked there too.
  - So the flag of this CIP reaches the CLI as "fragment member -> `LaunchRequest` -> argv in skill-agents-management". The precedent is CIP-0033 `home.transport: "flag"`: SAM renders `--gemini_dir` and rejects conflicting flags in `NativeArgs`.
- **Native mechanisms and their behavior** are described in facts 19-26, 50-62 and 67-70.

## 5. Model

### 5.1 Location

`environments.profile_settings.<profile>.global.providers.claude_code.surface`. A `project` variant follows the CIP-0006 scope rules.

The record belongs to the operator. It never enters packages or files found in a project: by the CIP-0006 principle, new authority lives only in machine configuration.

### 5.2 Schema (v1)

```json
{
  "preset": "full | curated | strict | custom",
  "tools":      { "allow_only": ["Skill", "Read"] },
  "skills":     { "bundled": "on | off", "account": "on | off",
                  "overrides": { "<skill>": "on | name-only | user-invocable-only | off" } },
  "plugins":    { "<plugin-id>": true },
  "mcp":        { "allow_only": ["<server>"], "deny": ["<server>"] },
  "host_mcp":   { "<logical-name>": "on | off" },
  "connectors": { "mode": "on | off", "allow": ["<connector-name>"] },
  "load":       { "tool_search": "auto | on | off", "mcp": { "<server>": "always | deferred" } }
}
```

- **`preset`** sets the starting set; the other members refine it.
- **`tools`** takes `allow_only` or `deny`, never both.
- **How a member combines with the preset.** Each preset sets a default for every member (5.3). An explicitly set member replaces the preset value as a whole; values inside a member are not merged. The only exception is `tools.deny`:
  - **`tools.allow_only`** replaces the preset tool set. Exactly the listed tools are allowed, and the rest of the version inventory is denied (section 6). Example: `strict` with `allow_only: ["Skill", "Read", "Grep"]` allows these three tools, not only `Skill` (Appendix A).
  - **`tools.deny`** is subtracted from the preset set: whatever the preset allows, minus the listed tools. For `full` it is just a deny list.
  - **Without `tools`** the preset set applies.
  - **`custom` has no defaults:** an unset member projects nothing.
- **`load`** is separate from permissions. It changes only when tool schemas load, not which tools are available.
- **`host_mcp` and `connectors`** describe what the host or the account provides. Where there is nothing of the kind, they have no effect.
- **Logical `host_mcp` names:** `browser`, `chrome`, `computer_use`, `ios_simulator`, `android_emulator`, `terminal`, `scheduled_tasks`, `mcp_registry`, `visualize`, `app_control`. Real names come from qualification data. `app_control` means the service servers `ccd_*`.
- **`connectors.allow`** is set by name. The UUIDs of built-in connectors come from qualification data: they are constants of the CLI version (56).

### 5.3 Presets

| Preset | What the model sees | Default |
|---|---|---|
| `full` | Everything the CLI, the host and the account provide, plus the profile content. Curator projects nothing. | yes |
| `curated` | Profile content, the core CLI tools and the host `app_control`. No account skills, bundled skills, built-in host MCP servers or connectors. | |
| `strict` | Only the profile content and `Skill`. Everything else is denied. Profile MCP servers load up front. | |
| `custom` | Only the explicitly set members. | |

Qualification data (CIP-0034), not Curator code, defines what `curated` and `strict` contain for a given version. Even tool names depend on the host: the subagent tool is `Task` in a host-less CLI and `Agent` in a Desktop session (49).

### 5.4 Merge with CIP-0006

- **`permissions.deny`** is assembled deterministically: CIP-0006 rules first, in their order, then the expanded `surface` denies, without duplicates.
- **Both set the same leaf** (for example `enabledPlugins["anthropic-skills@inline"]`):
  - equal values are allowed;
  - different values refuse with `profile_settings_conflict` before publication. There is no "last one wins" rule.
- **CIP-0006 per-server MCP choices** (`enabled`, `disabled`, `denied`) combine with `surface.mcp` as follows:
  - negative choices are united;
  - `enabled` against a `surface` deny gives `profile_settings_conflict`.
- **The CIP-0006 hard deny is also published into `settings.json`.** For Claude, CIP-0006 relies on the strict MCP channel (`--strict-mcp-config`), and a GUI host passes no such flags (CIP-0036, fact 16). So an effective `denied` for `claude_code` is additionally projected as:
  - `deniedMcpServers: [{"serverName": "<s>"}]`: the server does not start (51);
  - `permissions.deny: ["mcp__<s>"]`: the tools are removed even if the server still starts (54).

  **Only `denied`** goes into `deniedMcpServers`. `disabled` is a soft default-off that an `enabled` in a higher scope overrides. For it Curator only stops delivering the server: it is absent from both `.claude.json` and the `--mcp-config` file. `disabled` produces no native deny.

  A user deny beats a project allow, including servers from the project `.mcp.json` with `enableAllProjectMcpServers` (51). So a deny of a specific server also works in a GUI, without `--strict-mcp-config`. As in CIP-0006, a negative choice may name a server the profile does not have; the deny is published for it as well.
- **`global` and `project` scopes** follow the CIP-0006 rules.

### 5.5 Packages

A profile package neither sets nor changes the surface (section 13). As today, a package only brings skills and MCP servers through `requires`.

## 6. Projection into native Claude Code keys

| Surface key | Native key | File | Layer (7.1) | Capability (CIP-0034) | Facts |
|---|---|---|---|---|---|
| `tools.allow_only` | `permissions.deny: ["<Tool>"]` for every inventory tool except the allowed ones | `settings.json` | deny | `surface.deny-tools/1` | 23, 60 |
| `tools.deny` | `permissions.deny: ["<Tool>"]` | `settings.json` | deny | `surface.deny-tools/1` | 23, 60 |
| `skills.bundled: off` | `disableBundledSkills: true` | `settings.json` | setting | `surface.bundled-skills-off/1` | 19, 59 |
| `skills.overrides` | `skillOverrides` | `settings.json` | setting | `surface.skill-overrides/1` | 20, 59 |
| `skills.account: off` | `enabledPlugins["anthropic-skills@inline"]: false` | `settings.json` | setting | `surface.account-plugin-off/1` | 21, 59, 62 |
| `plugins` | `enabledPlugins` | `settings.json` | setting | CIP-0006 path | 21, 59 |
| `mcp.allow_only` | `allowedMcpServers`, plus `permissions.deny` for known servers outside the list | `settings.json` | setting and deny | `surface.mcp-allowlist/1`, `surface.deny-mcp/1` | 50, 52, 54, 68 |
| `mcp.deny` | `deniedMcpServers` (the server does not start) and `permissions.deny: ["mcp__<s>"]` | `settings.json` | deny | `surface.mcp-denylist/1`, `surface.deny-mcp/1` | 51, 54 |
| CIP-0006 effective `denied` (5.4); `disabled` is only not delivered | `deniedMcpServers` and `permissions.deny: ["mcp__<s>"]` | `settings.json` | deny | `surface.mcp-denylist/1`, `surface.deny-mcp/1` | 51, 54 |
| `host_mcp.<x>: off` | `permissions.deny: ["mcp__<real name>"]`, plus an instance toggle (CIP-0036) | `settings.json` | deny | `surface.deny-mcp/1` | 22, 26.1-26.8 |
| `connectors.mode: off` | `permissions.deny` by UUID from qualification data. For connectors not listed there, the mask, if qualified | `settings.json` | deny | `surface.deny-connectors/1` | 22, 54-56, 69 |
| `load.mcp.<s>` | `mcpServers.<s>.alwaysLoad` | MCP channel (`.claude.json` in a GUI, the `--mcp-config` file in `curator run`) | loading | `mcp.always-load/1` | 18 (`.claude.json`), 67 (`--mcp-config`) |
| `load.tool_search` | `env.ENABLE_TOOL_SEARCH`: `off` -> `"false"`, `on` -> `"true"`; with `auto` the key is not written | `settings.json` | setting | `surface.tool-search-env/1` | 57, 70 |

Notes:
- **`allow_only`** expands into denies over the inventory of the qualified version: the CLI inventory (48, 49) plus the host inventory (CIP-0036). Tools that appear later are not covered by these denies, so a version change yields `surface_unqualified` (section 8).
- **`mcp.deny` uses both mechanisms.** `deniedMcpServers` keeps the server from starting (51). `permissions.deny` removes the tools even if the server still starts (54).
- **`mcp.allow_only` does not restrict host servers or connectors.** `allowedMcpServers` applies only to servers from configuration. Built-in host MCP servers, `ccd_*` and account connectors pass through it (68). So `strict` and `curated` close them with denies, not with the allowlist.
- **Connectors.** The UUIDs of built-in connectors are known in advance (56). For the account's own connectors there is the mask `mcp__*-*-*-*-*` (55, 69). It removes the connector tools in a Desktop session, but it also hits any tool whose full name has four hyphens. It is allowed only after Curator has checked that the mask does not hit the names of profile servers and tools. Otherwise the result is `surface_unenforceable`.
- **`load.tool_search` on 2.1.331 is verified in the CLI (57) and in a Desktop session (70).** For a GUI host the key, like everything else, applies only to a host version with a passed smoke (CIP-0036, section 7).

## 7. Layers and guarantees

### 7.1 Two layers

- **Deny layer:** `permissions.deny` (tools, MCP by name and by mask) and `deniedMcpServers`. Rules are united across all settings levels, and a deny wins. Project settings cannot lift this layer (51, 60).
- **Setting layer:** `disableBundledSkills`, `skillOverrides`, `enabledPlugins`, `allowedMcpServers`, `env`. Here the project overrides the user (52, 57, 59).

### 7.2 What this means for presets

- **`curator run`.** For profiles with `curated` or `strict`, `--setting-sources user` reaches the CLI (59), and the setting layer holds as well. The chain:
  - Curator writes `surface: {"setting_sources": "user"}` into the fragment;
  - the launcher passes the member into `LaunchRequest`;
  - skill-agents-management renders the flag. If `NativeArgs` already carries its own `--setting-sources` (in any spelling), it refuses before launch.

  The cost: the project also loses useful settings (`permissions.allow`, hooks). For `strict` that is the point. For `curated` it is the operator's choice (question 3).
- **GUI host.** The launcher does not set session arguments. The setting layer holds only for projects that Curator checked before launch: CIP-0036 checks `.claude/settings.json` and `.claude/settings.local.json` for keys that widen the surface. For folders opened from the host UI only the deny layer is guaranteed.
- **`strict` relies on denies wherever possible:**
  - tools are closed with `permissions.deny`;
  - MCP servers with `deniedMcpServers` and `permissions.deny`;
  - connectors with `permissions.deny` by UUID.

  Account skills and bundled skills have no such deny yet. The rule `Skill(<plugin>:*)` does not remove them from the list, and whether it blocks the call is not verified (61, question 2).

### 7.3 Wording of the guarantee

`strict` means **call restriction**:
- the model cannot call a denied tool or a tool of a denied server;
- mentions may remain in the prompt: skill lists, host sections and instructions (26, 26.6-26.8, 61, 69);
- an MCP server declared elsewhere (for example by the project) may start unless its name is closed by `deniedMcpServers` (54);
- the guarantee applies only to a qualified version (section 8).

## 8. Qualification (CIP-0034)

**Capabilities for the catalog:**

| Capability | Smoke |
|---|---|
| `surface.deny-tools/1` | The denied built-in tool is absent from init; a project `permissions.allow` does not bring it back |
| `surface.bundled-skills-off/1` | No bundled skills in init |
| `surface.skill-overrides/1` | A home skill set to `off` disappears |
| `surface.account-plugin-off/1` | The `<name>@inline` plugin is off through `enabledPlugins` |
| `surface.mcp-allowlist/1` | A server outside the list does not start |
| `surface.mcp-denylist/1` | A denied server does not start; a project allow does not help |
| `surface.deny-mcp/1` | The server tools are absent; masks match the full name |
| `surface.deny-connectors/1` | The built-in connector UUIDs are present in the version binary. The mask does not hit profile names |
| `surface.tool-search-env/1` | `ENABLE_TOOL_SEARCH=false` in `env` removes `ToolSearch` |
| `surface.project-sources-excluded/1` | With `--setting-sources user` the project does not bring setting keys back |
| `mcp.always-load/1` | `alwaysLoad: true` loads tools without `ToolSearch`: in `.claude.json` by the host smoke, in the `--mcp-config` file by probe D5 (fact 67) |
| `surface.inventory/1` | The inventory from the login-free init of the exact binary (48) matches the reference in the record, with no new names |

- **The `surface_unqualified` verdict** is the CIP-0034 verdict for the pair "CLI or host version x capabilities the preset requires".
- **Reason inside the verdict.** The typed CIP-0034 rev 2 code is not replaced by the generic `surface_unqualified`; it is kept in the reason field. Codes follow the CIP-0034 priority order; if several apply, the first is reported.
  1. `qualification_artifact_revoked` -- the whole artifact is revoked;
  2. `qualification_capability_revoked` -- a capability the preset requires is revoked;
  3. `qualification_capability_regressed` -- the capability passed on an earlier version and fails on the current one;
  4. `qualification_capability_unqualified` -- a record for the version exists, but the required capability has the verdict `unqualified`, `not_run` or `not_applicable`;
  5. `qualification_record_missing` -- no record for the version;
  6. `qualification_host_smoke_failed` -- the local host smoke failed (CIP-0036, section 7).
- **Login-free Tier-0 inventory.** The init message of the exact binary (48) lists built-in tools, skills, plugins and agents. Qualification compares this list with the registry record. If a new name appears, presets with `allow_only` get `surface_unqualified` before launch. This closes the "future tool is not covered by a deny" gap.
- **Where the reference inventory lives.** In the CIP-0034 schema, details live inside the specific capability, keyed by its ID:
  - in the signed `harness-qualification-v1` record -- `capabilities["surface.inventory/1"].details`;
  - in `launch-env-fragment-v8` -- `qualification.capability_details["surface.inventory/1"]`.

  ```json
  "capabilities": { "surface.inventory/1": {
    "...": "other capability fields per CIP-0034",
    "details": {
      "source": "cli-init",
      "binary_sha256": "b76a8345f6c00c40...", "binary_version": "2.1.331",
      "tools": ["Bash", "Edit", "Read", "Skill", "Task", "ToolSearch", "..."],
      "mcp_servers": [{ "name": "<name>", "origin": "builtin | host | connector" }],
      "skills": ["init", "security-review", "..."], "plugins": ["cc-plugin-...@builtin"],
      "agents": ["general-purpose", "..."], "connector_ids": ["1a59c906-..."]
    } } }
  ```

  - Lists are sorted; names are exact and case-sensitive.
  - The host inventory has the same shape in `capabilities["host.tool-inventory/1"].details` (CIP-0036, section 7). It holds the tools and servers the host adds (`ccd_*`, built-in MCP servers, `Agent`).
- **Host tools** (`ccd_*`, built-in MCP servers, `Artifact` and so on) do not appear in a host-less init (49). The local host smoke checks them (CIP-0036).
- **The smokes in the table** are probes 50-62 and 67, packaged as a per-version suite (scripts in [probes](../.research/261126_claude-desktop-managed-sessions-probes/)).

## 9. Writing and ownership

- **One writer.** `claudeMdExcludes`, the CIP-0006 paths and `surface` are published in one transaction on `settings.json`. The mechanism is the one that writes `claudeMdExcludes` today (`claude_ancestor_settings.go`): recorded ownership keys, preimages, up to three attempts.
- **Ownership.** Curator owns only the leaves it wrote. The rest of `settings.json` belongs to the runtime and the user.
- **Removing a key** from the operator record restores the previous leaf value from the ownership record. If the leaf did not exist before, it is deleted.
- **`claude_settings_mode=read-only` is compatible.**
  - `settings.json` is published in one transaction directly with the target mode `0400`: the new file is created with that mode and atomically replaces the old one. There is no window in which the file is writable.
  - On Windows the mode refuses with `environment_settings_mode_unsupported`, as `internal/envprofile/claude_readonly_settings.go` does today.
  - This mode is recommended for `strict`: the host and the user cannot change the file from the UI, for example to re-enable a plugin.
- **Machine configuration schema version** -- `manager-config-v10`, shared by CIP-0006, CIP-0035, CIP-0036 and CIP-0037 and reserved by S0 (relux-works/curator-spec#233). Main publishes v9 (`machine-claude-env-v1`); v4 stays with deferred work.

## 10. Diagnostics

| Code | When |
|---|---|
| `surface_unqualified` | The CLI or host version is not qualified for the preset capabilities, or an unknown name appeared in the inventory. The typed CIP-0034 rev 2 reason is kept (section 8) |
| `environment_settings_mode_unsupported` | Existing code: `read-only` on a platform without Unix permission bits (Windows), section 9 |
| `NativeArgs` conflict | skill-agents-management refuses when `NativeArgs` carries its own `--setting-sources`. The error is typed, following `ErrContextDescriptorConflict` |
| `profile_settings_conflict` | CIP-0006 and `surface` set the same leaf differently |
| `surface_unenforceable` | No native mechanism exists for the key, or it does not hold for this launch mode (for example `connectors.allow` without known UUIDs, or a mask that hits profile names) |
| `surface_project_widening` | The pre-launch check found keys in the project that widen the surface (CIP-0036). It does not occur in `curator run` with `--setting-sources user` |

## 11. Security considerations

- **Authority belongs to the operator only.** A hostile repository cannot lift the deny layer (51, 60) but can override the setting layer (59). `--setting-sources user` closes that in the CLI and the project check closes it in a GUI.
- **A tool deny does not stop MCP server processes** (54, 69). To keep a server from starting, use `deniedMcpServers` with the exact name.
- **`surface` holds no secrets.**
- **`strict` and `curated` do not launch on an unqualified version.** `full` is never blocked.

## 12. Compatibility and migration

- `full` is the current behavior. A record without `surface` changes nothing.
- Older readers refuse the new schema version, as in CIP-0006 (Downgrade).
- Removing `surface` restores the leaves from the ownership record.

## 13. Deferred: surface in the profile package

An earlier draft proposed that a profile package could only narrow the surface. v1 does not include this:
- **CIP-0006 threat model.** Authority over provider settings lives in machine configuration, not in the package. The `agent-context` schema is closed for this.
- **Overlay composition.** Package rules would need their own algebra, in the manner of CIP-0018.
- **`load: always` does not narrow the surface.** It increases what loads on every turn.

A possible follow-up is a separate CIP on "package recommendations": `profile show` displays them, and the operator accepts them explicitly.

## 14. Specification changes

1. **Environments, `profile_settings` section:** the `surface` member, the projection table (section 6), layers (section 7), diagnostics (section 10).
2. **Machine configuration schema:** `manager-config-v10`, reserved by S0 (relux-works/curator-spec#233).
3. **CIP-0034 catalog:** the capabilities from section 8 and the login-free init smoke.
4. **`launch-env-fragment-v8`.** One shared revision with the CIP-0034 `qualification` member, reserved by S0 (relux-works/curator-spec#233). Frozen v1-v7 do not change.
   - The new `surface` member is valid only with `environment: "claude_code"`. Its closed form is `{"setting_sources": "user"}`, with no other members or values.
   - The member is always present for `strict`, present for `curated` at the operator's choice (question 3), and absent for `full` and `custom`.
   - A reader of an earlier revision refuses the unknown revision, as for v2-v7.
   - The member carries no raw argv, variable names or paths (environments section 10.3).
5. **skill-agents-management, `pkg/agentic/systems/claude/`:**
   - `surface.setting_sources: "user"` from `LaunchRequest` renders as `--setting-sources user`;
   - a conflicting `--setting-sources` in `NativeArgs`, in the separate and in the `=` form, refuses with a typed error before launch;
   - this is the only place that spells the flag (Decision 0019).
6. **Launcher contract:** accept the new fragment revision and pass `surface` into `LaunchRequest` unchanged. The launcher does not read `profile_settings` and does not spell the flag.
7. **CIP-0006 projection for `claude_code`:** an effective `denied` is additionally published into `settings.json` as `deniedMcpServers` and `permissions.deny`. `disabled` is only not delivered (5.4).

## 15. Implementation plan

| # | Repository | What | Depends on |
|---|---|---|---|
| P0 | curator | CIP-0006 as accepted (nine paths) | -- |
| S1 | curator-spec | This CIP, environments text, the `launch-env-fragment-v8` `surface` member schema, vectors | P0 (acceptance can run in parallel) |
| Q-S | curator-spec / suites | Surface capabilities in the CIP-0034 catalog, init smoke | CIP-0034 Q1 |
| I1 | curator | Writing `surface` into `settings.json`, presets, conflict rules, projection of CIP-0006 `denied`, `surface_unqualified`, the `surface` fragment member | P0, S1 |
| I1-SAM | skill-agents-management | `pkg/agentic/systems/claude/`: render `--setting-sources user` from `LaunchRequest`, refuse a conflicting `--setting-sources` in `NativeArgs` | S1 |
| I1b | curator-agent-launcher | Accept the new fragment revision and pass `surface` into `LaunchRequest`. Bump the skill-agents-management dependency to the version with I1-SAM | S1, I1-SAM |

## 16. Test plan

- **Vectors.** Every schema member in the states "absent", "empty", `false` and "value" yields the expected `settings.json` leaves and ownership records.
- **Per-CLI-version suite.** Probes 50-62 and 67: allowlist, denylist, masks, project widening, `ENABLE_TOOL_SEARCH`, `--setting-sources user`, `alwaysLoad` in `--mcp-config`.
- **Fragment and argv construction:**
  - `strict` always carries the `surface` member, `curated` only at the operator's choice, `full` and `custom` never;
  - a v7 reader refuses the new revision;
  - the `surface` member with another `environment` is invalid by schema;
  - skill-agents-management renders `--setting-sources user`;
  - `NativeArgs` with `--setting-sources project` or `--setting-sources=project` refuse without launch.
- **CIP-0006 negative choices:** `denied` yields `deniedMcpServers` and `permissions.deny`. `disabled` removes the server from delivery but yields no native deny.
- **Negative cases:**
  - conflict with CIP-0006;
  - unqualified version: each typed CIP-0034 reason is visible inside `surface_unqualified`;
  - `read-only` mode: the file appears with `0400` directly, with no writable window; on Windows `environment_settings_mode_unsupported`;
  - repeated resolve without changes;
  - removing `surface` restores the leaves.
- **The GUI smoke** is described in CIP-0036.

## 17. Open questions for the operator

1. **Contents of `curated`.** Recommendation: `Bash`, `Read`, `Edit`, `Write`, `Grep`, `Glob`, the subagent tool, `TodoWrite`, `WebFetch`, `WebSearch`, `Skill` and the host `app_control`. No built-in host MCP servers, connectors, account skills or bundled skills.
2. **`Skill(<plugin>:*)` as a safety net.** Needs a check with a model: does the rule block the call? If yes, `strict` adds it for account skills and bundled skills.
3. **`--setting-sources user` for `curated`.** Recommendation: always for `strict`, at the operator's choice for `curated`. If a separate key is introduced, it is `surface.project_settings: "ignore" | "allow"`.
4. **Connectors that qualification data does not list.** Qualify the mask (55, 69) or require an explicit list in `connectors.allow`? Recommendation: the mask only as a safety net; the main path is the explicit list.

## Appendix A. Example: operator record and the result for `curator run`

Operator record:

```json
{
  "environments": { "profile_settings": { "acme-reviewer": { "global": { "providers": { "claude_code": {
    "surface": {
      "preset": "strict",
      "tools": { "allow_only": ["Skill", "Read", "Grep"] },
      "load":  { "tool_search": "off", "mcp": { "acme-tracker": "always" } }
    }
  } } } } } }
}
```

What Curator publishes into the managed home `settings.json` (its own leaves only):

```json
{
  "disableBundledSkills": true,
  "enabledPlugins": { "anthropic-skills@inline": false },
  "allowedMcpServers": [{ "serverName": "acme-tracker" }],
  "env": { "ENABLE_TOOL_SEARCH": "false" },
  "permissions": { "deny": ["Bash", "Edit", "Write", "WebFetch", "WebSearch", "Task", "...every other inventory tool of the version except Skill, Read, Grep"] }
}
```

In addition:
- the `--mcp-config` file sets `alwaysLoad: true` for `acme-tracker`. In this file the key works as in `.claude.json` (fact 67);
- the fragment carries `surface: {"setting_sources": "user"}`, and skill-agents-management adds `--setting-sources user`;
- for a GUI host, CIP-0036 adds denies for host MCP servers and connectors and the instance toggles.

The 5.2 rule on this example: `tools.allow_only` replaces the `strict` tool set (`Skill`) with `Skill`, `Read`, `Grep`. The other members come from `strict`: bundled skills off, the account skills plugin off, profile MCP servers allowed.
