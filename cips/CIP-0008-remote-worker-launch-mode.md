# CIP-0008: Remote-worker launch mode (tool lockdown on a donor machine)

- **Status:** Draft
- **Owner:** ivan-curator (orchestrator); decision: operator
- **Created:** 2026-10-08
- **Related:** owner brief 2026-10-08 (remote worker on a donor machine); [Decision 0018](../decisions/0018-curator-run-permission-interface.md) (`native|yolo`); [Decision 0013](../decisions/0013-execution-ownership-and-launch-plans.md) (launch plans); [Decision 0014](../decisions/0014-tool-configuration-surfaces.md) (proposed); [CIP-0002](CIP-0002-project-context-in-managed-launches.md) (strict MCP set); [CIP-0006](CIP-0006-legacy-provider-settings-and-mcp-opt-outs.md); [CIP-0009](CIP-0009-donor-side-deployment-and-bridge.md) (the donor machine and the bridge); [CIP-0010](CIP-0010-credentials-setup-token-and-inherited-auth.md) (credentials); environments [§2.2](../protocol/environments.md#22-mcp-declaration-packages), [§10.3](../protocol/environments.md#103-the-profile-influence-boundary), [§12.1](../protocol/environments.md#121-machine-configuration-knobs)
- **Affects:** environments §12.1 (new knobs), §10.1 (fragment metadata), launcher SPEC (mode, refusals, receipts), agents-management (per-harness mapping, session-start parameters); implementations: curator, curator-run/launcher, agents-management, the remote executor

## Summary

A **remote worker** is a harness whose model runs on a machine we do not own (the *donor*'s machine) while every tool call executes inside a remote workplace on our host. This CIP adds a launch mode in which the harness starts with **every locally acting tool switched off**: the only capabilities are the remote-tools MCP server and the mailbox. The lockdown is a machine-level **tool posture** bound to a profile, mapped per harness by agents-management, enforced by the launcher (refusing arguments that re-enable anything), recorded in the plan, the receipt and `env status`, and visible and stoppable by the donor. Permission prompts are answered automatically in a form that is explicitly marked "nothing can act on this machine; the remote side is sandboxed". The design reuses what `rwh` already proved live for Claude, Codex and Muse and moves it from a hand-written harness into Curator's declared surfaces.

## Motivation and user stories

- **Owner (2026-10-08):** "the native tools of the remote harness are switched off or overridden at launch, so a compromised or prompt-injected environment cannot act on its own machine; the donor must be able to see it and control it."
- **The donor** lends a subscription and a machine. They want one command that provisions the thing, a visible posture ("this harness can only talk to our project's workplace"), an audit of what left their machine, and a kill switch.
- **The project orchestrator** wants the same pin and plan discipline as for local workers: the remote executor accepts only a plan whose profile pin and posture match, and a harness that could act locally is never admitted (VISION v1.3 LCH §8; the earlier curator-side review CUR-R4).
- **The platform** wants this to be a Curator mode, not a bespoke launcher: one composer, one plan schema, one refusal table.

## Current state

- **No deny field in a profile.** A profile carries skills, instructions, the MCP set and context (environments §2, §3, §9, §10). Native settings files (Claude `settings.json` `permissions.deny`, hooks) are outside the managed surface: Decision 0014 is still *proposed*; CIP-0006 (Draft) covers preserving legacy provider settings and MCP opt-outs, not tool denial.
- **The only permission knob is `permissions.<profile>` with values `native|yolo`** (Decision 0018; environments §12.1). `yolo` maps to Claude `--dangerously-skip-permissions` and Codex `--dangerously-bypass-approvals-and-sandbox`; `pi` refuses it. There is no restricted or lockdown value. In `native` mode argv after `--` is forwarded verbatim (0018 item 4), so a caller *can* pass `-- --disallowedTools Bash,Edit,Write`, but 0018 says plainly that this interface is UX, not a security perimeter, and it is not a profile property.
- **MCP injection is partial** (CIP-0002 §Current state): Claude's `--strict-mcp-config` is applied only when the profile's MCP set is non-empty; Codex seed revision A inherits native MCP servers (fixed by seed revision B, landing for v0.15.0-rc.5); an `http` MCP declaration carries no per-profile authentication (environments §2.2).
- **`rwh` already runs locked-down remote harnesses on the dedicated Mac mini** (relux-works/remote-worker-harness, modes 2b Claude, 2c Muse, Codex session; live-accepted 2026-09-29 and 2026-10-06). Its measured per-harness recipes are the evidence base of the mapping table below. What it lacks is exactly what this CIP adds: a declared posture, a pin that covers it, a launcher refusal table and a donor-facing control surface.
- **Harness surfaces, measured on the mini 2026-10-08** (`claude` 2.1.293, `codex` 0.159.0, `muse` 1.4.3, `--help` output under a scratch `HOME`):
  - Claude Code: `--tools <tools...>` ("use `\"\"` to disable all tools"), `--restricted` (removes the built-in tools that run commands or code and WebFetch unless `--tools` names them; ignores user, project and local settings files, managed settings and `--settings` still apply; `--strict-mcp-config` skips other MCP servers; confines file tools to the working directories; **refuses `bypassPermissions`**; writes to settings, git and tool-configuration files need a person or the configured permission handler), `--permission-prompts none` (with `--print`: anything that would prompt is denied), `--permission-mode dontAsk`, `--allowedTools`, `--disallowedTools`, `--setting-sources`, `--settings`, `--disable-slash-commands`, `--bare`, `--add-dir`, `--plugin-dir`, `--plugin-url`.
  - Codex CLI: `-s/--sandbox <read-only|workspace-write|danger-full-access>`, `-a/--ask-for-approval` (`untrusted` is rejected since 0.155.1 per `rwh`), `--ephemeral`, `--ignore-user-config`, `--ignore-rules`, `--strict-config`, `-c key=value`, `--enable/--disable <FEATURE>`, `--add-dir`, `--search`, `--dangerously-bypass-approvals-and-sandbox`, `--dangerously-bypass-hook-trust`, `--remote <ADDR>`. There is no flag that removes the built-in tools; `rwh` removes them through a sanitized `model_catalog_json` (implementation-private, re-verified per release) plus `sandbox_mode = read-only`, an empty cwd and approval denial.
  - Muse: `--disable-shell`, `--disable-write`, `--disable-web-tools`, `--enable-shell-tool`, `--no-foreign-personal-context`, `--approval-mode <MODE>`, `--approval-judge off`, `--permission-profile <ID>`, `--disable-sandbox`, `--sandbox-network <MODE>`, `--max-model-steps`, `--max-tool-output-bytes`, `--no-session-log`, `--yolo`, `--trust-workspace`, `--disable-approval`. Muse cannot drop its built-in *read* tools and `--workspace` is not a read boundary (`rwh` measured a canary read), so an OS sandbox is mandatory for Muse.

## Design

### Options considered

1. **Profile bytes carry a tool deny list.** Simple to author. Violates environments §10.3 ("a profile chooses what the context says, never how a process is launched") and makes a security property depend on package bytes that any overlay could change. Rejected.
2. **Per-launch native arguments only (today's passthrough).** Works, as `rwh` shows, but nothing records the posture, the pin does not cover it, nothing refuses the opposite arguments, and a donor cannot lock it. Rejected as the end state; kept as the mechanism the mapping table compiles to.
3. **A machine-level tool posture bound to a profile, compiled per harness by agents-management, enforced and refused by the launcher, recorded in plan and receipt.** The same shape as Decision 0018's `permissions.<profile>`; lockable by the donor's system configuration; the profile contributes only what it may (the remote-tools MCP declaration and the instructions). **Recommended.**
4. **Ship a separate "remote worker" harness wrapper.** This is `rwh` today. It duplicates the composer and spells flags outside Curator; the owner asked for a Curator mode.

### Recommendation

**R1. Posture knob.** A new environments §12.1 knob `tool_posture.<profile>` with the closed values `open` (default, absent) and `lockdown`. It is a *machine* knob: lockable by system configuration (manager §12), never profile content, never a launcher-file entry. The donor's installation locks `tool_posture.remote-worker: lockdown` (CIP-0009), so no launch of that profile on that machine can be `open`.

**R2. Permissions value for the mode.** Decision 0018's `permissions` gains a third value `remote-auto`, admitted **only** when the effective `tool_posture` is `lockdown`; `remote-auto` with `open`, or `yolo` with `lockdown`, is a `usage` refusal naming both. `remote-auto` means: the remote-tools MCP tools are pre-approved, everything else that would prompt is denied without prompting, and no native bypass is requested. This is the "marked yolo" of the owner brief.

**R3. Compile per harness in agents-management** (the Decision 0018 owner of provider mappings; goldens per tool release), as a `LaunchRequest` member `tool_posture` and a reviewed capability table. The table below is the first revision; every row cites what `rwh` measured or the vendor's help text, and each row is a conformance vector (R7).

| Harness (pinned) | Lockdown arguments the composer spells | `remote-auto` spelling | What still acts locally, and the answer |
|---|---|---|---|
| `claude_code` ≥ 2.1.293 | `--restricted --tools "" --strict-mcp-config --mcp-config <managed remote-tools file> --setting-sources ""` (`--restricted` already ignores user/project/local settings; the managed settings file of the donor's OS user still applies and carries `permissions.deny` for every built-in as belt and braces); cwd = an empty scratch directory; `--disable-slash-commands` unless the profile lock carries skills (skills are prompts, not tools; with no built-ins a skill script cannot run); the Curator-written `settings.json` of the managed home also disables hooks and plugin sync | `--allowedTools "mcp__<server>__*" --permission-mode dontAsk`, plus `--permission-prompts none` in `--print` mode. `--dangerously-skip-permissions` is never spelled: `--restricted` refuses `bypassPermissions` anyway | CLAUDE.md auto-discovery reads the cwd (empty scratch dir: nothing to read); transcripts and session state are written under `CLAUDE_CONFIG_DIR` (inside the managed home, owned by the donor's harness user); the auto-updater, telemetry and prefetches: set `DISABLE_AUTOUPDATER=1`, `DISABLE_TELEMETRY=1`, `DISABLE_ERROR_REPORTING=1`, `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` in the composed environment (names to be re-verified per release in the goldens); the Keychain is not read when `CLAUDE_CODE_OAUTH_TOKEN` is present (CIP-0010). `--bare` is **not** used: it never reads OAuth, which removes the setup-token path |
| `codex_cli` 0.159 | `-s read-only -a on-request --ephemeral --ignore-user-config --ignore-rules --strict-config -c features.web_search=false`; a sanitized `model_catalog_json` with `shell_type = "disabled"`, no `apply_patch_tool_type` and no `tool_mode` (the `rwh` layer a; implementation-private key, re-verified per release); cwd = an empty scratch directory; MCP through the Curator profile table only (`-p curator-mcp`, seed revision B) | approvals are routed to the Curator remote-worker supervisor, which **denies every one**; `approvals_reviewer = "user"`; no `--dangerously-bypass-*`, no `danger-full-access` | Codex writes sessions under `CODEX_HOME` (the managed home); `web_search` is a feature flag, kept off; the app-server listens on loopback only (`rwh` uses `--listen ws://127.0.0.1:0`); the tripwire and audit of `rwh` (trace output of every tool dispatch; any non-remote tool name ends the turn) are kept as the executor's second layer because Codex has no "no built-ins" flag |
| `muse` 1.4.3 | `--disable-shell --disable-write --disable-web-tools --no-foreign-personal-context --no-session-log --max-model-steps <N> --max-tool-output-bytes <N>`; MCP through the managed `settings.json` `mcp_servers.<server>` | `--approval-mode never --approval-judge off` (`never` does not re-enable the shell: measured by `rwh`) | Muse keeps its built-in read and search tools and `--workspace` is not a read boundary, so the **OS sandbox of CIP-0009 is mandatory** (deny reads outside the managed home and the scratch dir); Muse auto-updates: the donor's sandbox denies writes to the binary's location and the composer pins the release it verified |
| `pi`, `opencode`, others | `tool_posture_unsupported` (usage refusal) until a reviewed row exists | — | — |

**R4. Launcher refusals (the T3 of the earlier answer).** Under `lockdown`, any native argument after `--` that could re-enable a local effect is refused before any process exists, with `tool_posture_conflict` (usage, exit 2), in `=` and separate forms, aliases included:
- Claude: `--tools`, `--allowedTools`/`--allowed-tools`, `--disallowedTools` (it could narrow the MCP allow), `--permission-mode`, `--dangerously-skip-permissions`, `--allow-dangerously-skip-permissions`, `--add-dir`, `--mcp-config`, `--strict-mcp-config` (already spelled), `--settings`, `--setting-sources`, `--plugin-dir`, `--plugin-url`, `--bare`, `--remote-control`, `--agents`, `--agent`;
- Codex: `-s/--sandbox`, `-a/--ask-for-approval`, `--approve-for-me`, any `--dangerously-bypass-*`, `--add-dir`, `--enable`, `--disable`, `--search`, `--remote`, `-c`/`--config` keys `sandbox_mode`, `approval_policy`, `sandbox_permissions`, `model_catalog_json`, `mcp_servers*`, `features.*`, `shell_environment_policy*`;
- Muse: `--enable-shell-tool`, `--disable-sandbox`, `--sandbox-network`, `--yolo`, `--disable-approval`, `--trust-workspace`, `--approval-mode`, `--permission-profile`, `--allow-workspace-switch`, `--agents`.
An unknown env or an unknown release of a known env fails closed (`tool_posture_unsupported`): a failed probe is not known support, as in 0018 item 4.

**R5. What the pin and the plan cover.** The profile pin keeps covering the lock: the remote-tools MCP declaration package (environments §2.2, `http` with `https` only, or `stdio` to the Curator-managed local server of CIP-0009) and the instructions. The posture is a machine knob, so it enters the **plan**, not the pin: the fragment metadata of Decision 0013 §6.4 gains `works.relux.curator.tool-posture` (`open|lockdown`) and `works.relux.curator.permissions` (`native|yolo|remote-auto`); the launch plan carries both; the receipt and `env status` print them; the remote executor compares `expect_pin` **and** `tool_posture = lockdown` before intake and refuses otherwise (VISION LCH §8; `remote-worker-start`). A plan with `lockdown` whose argv contains any R4 argument is `launch_plan_invalid` on intake, independent of the launcher's own refusal.

**R6. Donor visibility and control.**
- *See:* `curator env status` on the donor machine shows, per managed home, `tool posture: lockdown`, `permissions: remote-auto (nothing can act on this machine; tool calls execute in the remote workplace sandbox)`, the remote-tools server identity and the project it is bound to; the harness's own banner line says the same at session start (the `remote-auto` spelling includes a system-prompt sentence stating it to the model, so the model does not try local tools and explains itself to humans).
- *Audit on the donor side:* the Curator-managed local MCP server (CIP-0009) writes one record per tool call it forwards: tool name, argument hash and size, timestamps, result size and exit, never arguments or environment; the records live in the harness user's state directory, readable by the donor (the machine's owner).
- *Stop:* `curator remote-worker stop <profile>` ends the harness user's processes and marks the home stopped; `curator remote-worker revoke <profile>` additionally deletes the carrier identity and the enrolled credentials from the donor machine (CIP-0009 §retire). Both are local commands under the donor (the machine's owner); nothing on our side can prevent them.
- *Locked posture:* the donor's system configuration (manager §12) locks `tool_posture.remote-worker` and `permissions.remote-worker`; a flag that conflicts with a locked member is a `usage` error (0018 item 2).

**R7. Conformance (the T4 of the earlier answer).** One vector per row of R3 and per refusal of R4, plus the production-entry negatives of the test plan. Rows are executed on the hosted lab runners (tb-R194: suites that spawn harness binaries do not run on the mini).

**R8. What this CIP does not claim.** On someone else's machine, no argument a launcher writes is a security boundary against that machine's owner, and a harness binary that auto-updates can change its flags. The lockdown is the *declared and checked* posture; the enforced boundary is the OS sandbox of CIP-0009 on the donor side plus the fact that the only capability with effect is the remote-tools MCP, whose calls execute in our sandboxed workplace. The remote harness stays untrusted in every case (architecture §7.9).

## Security considerations

- **Threat model.** The remote harness is compromised or prompt-injected. Goals: it must not read, write or execute on the donor's machine beyond its own managed home and scratch dir; it must not reach the network beyond the provider API, the join point and the carrier (CIP-0009 firewall); it must not carry a credential it can exfiltrate in bulk (CIP-0010: per-launch injection, no store copy); and whatever it does must be visible to the donor.
- **Layers, in order of strength:** (1) OS user + kernel sandbox + per-UID firewall on the donor (CIP-0009); (2) no local tools (this CIP, R3); (3) launcher refusal of re-enabling arguments (R4) and intake refusal of a contradicting plan (R5); (4) the executor's tripwire and audit of every tool name the model requests (kept from `rwh`); (5) the remote workplace's own policy and container on our host (relux-works/remote-workplace protocol v2.1). Layers 2–4 are UX and evidence; 1 and 5 are the boundaries.
- **TOCTOU.** The posture is read once at compose time under the machine-config lock and copied into the plan; the executor rechecks the plan, not the file, at intake; a changed machine config after compose yields a new plan digest and a refusal at resume (RST §3).
- **Hostile repository.** Nothing in this CIP reads repository bytes to decide the posture; CIP-0002 strict project context keeps project files out of the managed launch, and the cwd is an empty scratch directory.
- **Secrets.** No secret enters argv or the plan; the MCP server's authentication to our host is the pinned key pair of CIP-0009, held by the local MCP server process, not by the harness.

## Compatibility and migration

- Absent knob = `open`: every existing install and plan keeps its meaning. `permissions: remote-auto` is only valid with `lockdown`, so no existing configuration becomes invalid.
- The fragment metadata keys are additive within Decision 0013's closed metadata object: a new fragment revision (v4, together with CIP-0002's `command_environment`) with v3 readers rejecting it precisely, as 0018 did for `curator-run-defaults-v2`.
- `rwh` migrates by replacing its hand-written flag recipes with `curator run --mode remote-worker` (VISION D-R3: `curator run` is the canonical entry) and keeping its tripwire and audit as the executor's second layer.

## Specification changes

- environments §12.1: add `tool_posture.<profile>` (`open|lockdown`, default absent = `open`); extend `permissions.<profile>` with `remote-auto` and the two admissibility rules of R2.
- Decision 0018 amendment: the three-valued `permissions`; the refusal table of R4; the mapping table of R3 owned by agents-management as a `LaunchRequest` member `tool_posture` with goldens per release.
- Decision 0013 §6.4: fragment metadata `works.relux.curator.tool-posture` and `works.relux.curator.permissions`; intake refusal `launch_plan_invalid` for a `lockdown` plan whose argv matches R4.
- Launcher SPEC: `--tool-posture <open|lockdown>` before `--` as the per-launch level (CLI > per-profile knob > defaults file > built-in `open`), `--permissions remote-auto`, the refusal codes `tool_posture_conflict` and `tool_posture_unsupported`, and the receipt lines.
- Conformance: a `remote-worker/` case family with one vector per R3 row and per R4 refusal.

## Implementation plan

1. Spec: §12.1 knobs, 0018 and 0013 amendments, launcher SPEC text, conformance vectors (lockstep with 2). Size M.
2. agents-management: the mapping table and goldens for the three harnesses at their pinned releases; the `remote-auto` spelling; the session-start sentence. Size M.
3. curator: knob parsing and locking, fragment v4 metadata, `env status` lines, `remote-worker status|stop|revoke` (the donor commands of CIP-0009). Size M.
4. curator-run/launcher: `--tool-posture`, `--permissions remote-auto`, the refusal table, receipts. Size S–M.
5. Remote executor: intake check of pin + posture; the tripwire and audit layer moved from `rwh` into the executor. Size M.
6. Lab qualification on hosted runners (macOS, Linux): each R3 row against a fake model that requests a built-in tool (the control plant of `rwh`), each R4 refusal, the `remote-auto` denial of a non-remote prompt. Size M.

## Test plan

- Production-entry: `curator run --mode remote-worker <profile>` composes the plan of R3 for each harness (golden argv and environment); the receipt prints posture and permissions.
- Negatives: each R4 argument after `--` refuses `tool_posture_conflict`; `remote-auto` with `open` and `yolo` with `lockdown` refuse `usage`; a locked knob with a conflicting flag refuses `usage`; an unknown harness release refuses `tool_posture_unsupported`; a plan edited to carry a built-in tool enabler is refused at intake with `launch_plan_invalid`.
- Behavioural (lab runners only): a fake model requesting `Bash`, `Edit`, `Write`, `WebFetch` gets an error tool result from Claude (`rwh` `TestTripwireOnExecutedBuiltin`), the same for Codex (`unsupported call`) and Muse (refused at call time); a positive control with the posture off shows the marker files appear, so the test is not vacuous.
- Mutants: remove `--restricted`; keep `--tools ""` but add `--allowedTools Bash`; set `sandbox_mode = workspace-write`; drop `--disable-shell`; drop the intake argv check. Each must be killed by a named vector.
- Platform matrix: macOS and Linux for the donor side (Windows later, per the owners' call C18).

## Open questions for the operator

1. **Name of the mode and the profile.** Recommended: launch mode `remote-worker`, default profile name `remote-worker`, knob values `open|lockdown`.
2. **Should `remote-auto` also require the donor's one-time consent at first deployment** (a `consented` knob like `targets.<id>.consented`)? Recommended: yes, recorded by `curator remote-worker init` (CIP-0009).
3. **Codex catalog sanitization** relies on an implementation-private config key. Recommended: keep it as a per-release golden with the tripwire as the guard, and ask the vendor for a documented "no built-in tools" switch.
4. **Muse** cannot drop read tools; accept Muse only where the donor's OS sandbox (CIP-0009) is verified, or exclude Muse from the first release. Recommended: include, with the sandbox as a hard precondition.
5. **Pi and opencode**: refuse until rows exist. Recommended: refuse.
