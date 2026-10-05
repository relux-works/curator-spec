# CIP-0006: Legacy provider settings and MCP opt-outs

- **Status:** Draft
- **Owner:** ivan-curator (orchestrator); decision: operator
- **Created:** 2026-10-04
- **Related:** [curator#105 — preserve legacy provider settings and explicit MCP opt-outs](https://github.com/relux-works/curator/issues/105); Decision 0014 — tool-configuration surfaces (**proposed, not adopted**); Decision 0018 — curator run permission interface (**adopted**); TASK-261004-2iewnz — research-105-design-and-implementation-plan; STORY-261004-3v2zm2 — legacy-provider-settings-and-mcp-optouts-105; TASK-260927-367jb7 — infra-exit (external dependency named by the brief); TASK-260929-3hrwzn — transactional-legacy-config-import (PM-owned importer).
- **Affects:** environments §§5.8, 7.4, 7.8, 8, 9.2, 10, 12–13; manager configuration and profile cleanup; CLI `env config`, `env resolve`, `env status`; implementations: curator, curator-run/launcher and its agents-management integration; PM importer as a consumer.

## Summary

Add one closed, machine-owned `environments.profile_settings.<profile>` record to the existing profile configuration surface, covering exactly the nine provider paths and per-server MCP choices in issue #105. Keep global and project declarations separate, apply them through the existing managed-home resolver, and expose explicit negative MCP intent through the existing launch fragment. Curator owns only the selected configuration keys, preserving unrelated managed values and leaving native provider files and authentication stores untouched. This is a narrow adoption of the machine-configuration approach discussed in Decision 0014, not adoption of that decision or its package-distribution, rules, model, or plugin-installation proposals. Every new name and behavior below is proposed; none is claimed to exist on current main.

## Motivation and user stories

1. The legacy importer must carry Claude `allow`, `deny`, `ask`, and `acceptEdits` without pretending they are equivalent to Curator's `native|yolo` launch mode.
2. A plugin explicitly set to `false`, a Codex color preference set to `false`, or an empty status-line array must survive import and round-trip. Absence must remain inheritance, not a default-filled value.
3. A project's explicit MCP opt-out must survive composition, an older Codex managed home containing inherited servers, and an empty resulting server set. Merely removing a dependency or omitting the launch channel is insufficient.
4. PM writes Curator configuration through a public API. It neither edits native provider configuration nor assumes ownership of sessions, credentials, model routing, or another launch builder.

The decision to unblock is **where the narrow import authority lives and how its values reach an existing managed launch without expanding repository package authority**. Research is bounded to this decision: one CIP plus one evidence file, at most 80 KiB combined; a 60-minute initial research budget; no additional serial research prerequisite. The next runtime slice is L3 below. The grammar in this draft is not adopted or frozen: L1 must publish the reviewed schema and machine-checkable vectors before that slice consumes them.

## Current state

Source baseline: curator main `ca1b776fb580ec0cee0173bf150daf063023aeaa`, equal to the worktree HEAD and advertised remote main when inspected. Specification baseline: `v1.0.0-rc.14`, peeled commit `43bf0a2506d5c354a73bbc3ea4623d4653db10c7`. This CIP is filed from the research draft in [.research/261004_CIP-0006-legacy-provider-settings-and-mcp-optouts.md](https://github.com/relux-works/curator/blob/fae2ff9cab17a031c26a2b4c776afd8dc5e8b4f6/.research/261004_CIP-0006-legacy-provider-settings-and-mcp-optouts.md) on `relux-works/curator` `main` @ `fae2ff9c`. Detailed citations, commands, exit codes, and bounds remain in the companion [.research/261004_CIP-0006-legacy-provider-settings-and-mcp-optouts_evidence.md](https://github.com/relux-works/curator/blob/fae2ff9cab17a031c26a2b4c776afd8dc5e8b4f6/.research/261004_CIP-0006-legacy-provider-settings-and-mcp-optouts_evidence.md) at the same commit; they are cited, not copied. The operator has made no acceptance decision on this proposal.

| Surface | What exists | Consequence for #105 |
|---|---|---|
| Package | `internal/contextpkg/contextpkg.go:168–255` strictly accepts schema 1 and the closed context/requirements fields. Environments §1:35–46 explicitly excludes settings. | The issue's `settings` example is rejected, correctly for rc.14. Adding fields to schema 1 is not a compatible shortcut. |
| Profile configuration | `internal/config/environments.go:20–35,270–275,395–403`; `cmd/curator/envconfig.go:58–102`. Typed per-profile knobs already exist, including `permissions`. | The existing `env config set/show/unset` API is a smaller extension point than a new package content class. |
| Overlays | `internal/envprofile/overlays.go:15–43`; `cmd/curator/compose.go:95–130`; environments §6:1143–1237. | Machine declarations join a named profile's closure. `compose add` edits configuration; `profile update` moves the lock. Weights currently order context chapters, not settings. |
| Scope selection | `internal/envprofile/managed.go:2389–2437`; environments §§9.3, 10.1. | Explicit profile, environment-scoped current, then machine current. A project directory is not a profile selector; `--env` is not project scope. |
| Provider homes | `internal/envregistry/envregistry.go:242–288`; `internal/envprofile/managed.go:823–895`. | Claude has no `settings.json` seed. Codex copies `config.toml` once, not on repair. Current main ships Codex seed **A**, not B (`envregistry.go:28–37`); existing inherited servers therefore matter. |
| MCP | `internal/contextmaterialize/mcp.go:95–127,214–238`; `internal/envprofile/managed.go:204–223,2884–2905`. | The set is positive, selector-filtered declarations. Empty sets produce no file or channel. Names are MCP package names, not arbitrary aliases. |
| Ownership / launch | `internal/envmarker/envmarker.go:307–315`; `internal/envprofile/managed.go:2258–2317`; environments §§8.2–8.4, 10.2. | Marker surfaces and fragments are closed. Existing whole-file hashes do not express ownership of a few keys inside a tool-owned file. |
| Native import | `internal/envprofile/import.go:101–180`; environments §9.6. | The native-context importer covers context/skills, not these provider settings. It is not PM's transactional legacy importer. |

Decision 0014:3–10 explicitly leaves all its options unadopted. Decision 0018:175–240 and environments §10.1:3093–3134 establish separate launch-mode authority: `native` means no launcher bypass override, not a guarantee of prompting. Transporting `acceptEdits` as `native` or `yolo` would lose information.

Measured on the baseline: the scratch package with the issue's Claude permission object failed with exit **1**, `profile_source_invalid: context_manifest_invalid: unknown field settings`. A synthetic `mcp_policy` member failed with exit **1** for the same closed-schema reason. The otherwise identical plain package installed with exit **0**; its real `env resolve claude_code --repair --format json` exited **0** with no `mcp` member. Five selected existing tests passed, exit **0**. These establish current behavior, not implementation of this proposal.

## Design

### Options considered

| Option | Mechanism | Benefits | Costs and security tradeoffs |
|---|---|---|---|
| **A — typed machine record on each profile (recommended)** | One new §12.1 knob; existing config API, resolver, homes, markers, and launcher. Project intent is a separate block on an explicitly selected profile. | Smallest authority expansion; no new package grammar or remote update permission authority; PM has a public destination. | Not portable package distribution. Requires key-level ownership, explicit project binding, and versioned fragment semantics for opt-outs. |
| B — schema-2 context packages | Add typed `settings` and MCP policy to roots/direct overlays; resolve through the profile lock. | Portable declarations, snapshot audit and existing source update machinery. | New package trust boundary, confirmation/admission policy, transitive rules and update-delta coverage. Larger than the concrete importer need; risks silently adopting much of 0014. |
| C — native per-invocation layers | Store typed profile settings, render dedicated Claude/Codex layers, apply through the same launcher. | Avoid editing mutable base configuration; easy removal of owned layers. | Claude list merge and path anchors need proof; Codex already reserves its single `-p` layer for MCP. New settings-channel semantics and native-argument conflicts are broader than A. |
| D — provisioning-only copies | Copy sanitized legacy configuration once. | Small initial implementation. | Cannot preserve changes/removal/opt-outs on existing homes or provide reproducible ownership. Does not meet #105; arbitrary copying risks importing unrelated state. |

### Recommendation

**Choose A.** Adopt CIP-0006's narrow contract separately and leave Decision 0014 proposed. Packages and overlay sources continue to provide their current content/skills/MCP declarations; they cannot write the new machine record. No network profiles, rules files, model routing, credential settings, hooks, arbitrary files, plugin installation, or new process-construction API are admitted.

#### Public input and scope

Proposed `manager-config-v4` adds `environments.profile_settings`, a map from existing portable profile name to this closed record:

```json
{
  "global": {
    "providers": {
      "claude_code": {
        "permissions": {
          "allow": ["Read"],
          "deny": ["Bash"],
          "ask": [],
          "defaultMode": "acceptEdits"
        },
        "enabledPlugins": {"example@example-market": false}
      },
      "codex_cli": {
        "project_doc_max_bytes": 32768,
        "tui": {"status_line": [], "status_line_use_colors": false},
        "service_tier": "fast"
      }
    }
  },
  "project": {
    "root": "<absolute operator-selected project root>",
    "mcp": {
      "claude_code": {"example-server": "denied"},
      "codex_cli": {"example-server": "disabled"}
    }
  }
}
```

The root placeholder illustrates private machine data, not a valid literal path. `global` and `project` are optional; both may contain `providers` and `mcp`; only `project` contains a required `root`. Empty objects are valid no-ops. `null` is not an inheritance spelling. The profile record and every nested object reject unknown members, duplicate keys, invalid UTF-8, incorrect types, and unsupported provider values before a configuration write.

The public operation is the existing `curator env config set profile_settings.<profile> '<JSON record>'`; replace a whole profile record atomically, or replace the entire `profile_settings` map for a multi-profile import. `show` reports the declarative record, preserving presence; `unset` removes ownership on subsequent repair. Plugin identifiers containing dots are map keys inside the JSON record, never dotted CLI path segments. Strict decoding must replace the current `json.Unmarshal`-then-string fallback for this knob; malformed JSON and duplicate members cannot be accepted through the convenience parser (`cmd/curator/envconfig.go:78–81`).

“Global” means the imported global contribution **to this named profile**, not a write to all native homes or all installed profiles. PM places it on each profile included in its migration plan. A project contribution goes only on that project's selected profile; use an existing project profile where available, otherwise install the existing root under another `--as` name and retain the same audited overlays/closure. PM's existing project launch selection must pass that name through `--profile`; this CIP adds no automatic cwd discovery or profile inheritance graph. Global updates affecting several migrated profiles replace their records in one map write, not a hidden cascade.

A profile with a project block is bound to one project. `env resolve` checks that the launch directory is the declared root or a descendant, after filesystem identity/canonicalization checks; aliases, inaccessible roots and ambiguous boundaries fail closed. An unrelated project never receives that block, and an explicit wrong `--profile` is `profile_settings_scope_mismatch`, not a fallback to global settings. Different project roots use different profiles/homes so concurrent projects do not rewrite one shared global home. The new machine path never enters package data or retargets a fragment variable outside the environments root.

#### Exact field mapping

Let `P` be `environments.profile_settings.<profile>`, and `S` be the preserved source scope, `global` or `project`. The nine paths below are the complete initial provider inventory, derived from issue #105 rather than an implementation table.

| Legacy path | Proposed destination under `P` | Type / meaning | Managed output |
|---|---|---|---|
| Claude `permissions.allow` | `S.providers.claude_code.permissions.allow` | Ordered rule-string array, including `[]` | `settings.json` → `permissions.allow` |
| Claude `permissions.deny` | `S.providers.claude_code.permissions.deny` | Ordered rule-string array, including `[]` | Same key in `settings.json` |
| Claude `permissions.ask` | `S.providers.claude_code.permissions.ask` | Ordered rule-string array, including `[]` | Same key in `settings.json` |
| Claude `permissions.defaultMode` | `S.providers.claude_code.permissions.defaultMode` | Release-validated native mode string; `acceptEdits` required | Same key in `settings.json`, **not** Curator `permissions.<profile>` |
| Claude `enabledPlugins.<plugin>` | `S.providers.claude_code.enabledPlugins.<plugin>` | Boolean per native plugin identifier, preserving false | Same leaf in `settings.json`; no download or installation |
| Codex `project_doc_max_bytes` | `S.providers.codex_cli.project_doc_max_bytes` | Non-negative integer; proposed portable upper bound `2147483647`; retain explicit zero | Same root key in managed `config.toml` |
| Codex `tui.status_line` | `S.providers.codex_cli.tui.status_line` | Ordered string array, including `[]`; never sort | Same leaf in managed `config.toml` |
| Codex `tui.status_line_use_colors` | `S.providers.codex_cli.tui.status_line_use_colors` | Boolean; false is a value | Same leaf, subject to the pinned adapter evidence below |
| Codex `service_tier` | `S.providers.codex_cli.service_tier` | Non-empty native tier string accepted by the pinned adapter; no model translation | Same root key in managed `config.toml` |
| Per-server project MCP enabled / disabled / denied | `project.mcp.<env-id>.<server>` | Enum `enabled`, `disabled`, `denied`; missing key means inherit | Filtered declaration output plus explicit native suppression, described below |

The same MCP map is allowed in `global` so project inheritance has an explicit lower scope. The initial environment set for these settings is exactly `claude_code` and `codex_cli`; another environment is a typed unsupported-input error, not a skipped row. A source boolean true/false maps to `enabled`/`disabled`; a source deny maps to `denied`. Server identifiers must map unambiguously to the current declaration name or to an existing inherited native server. Do not lowercase, sanitize, or silently merge names that cannot be represented; report `mcp_policy_target_unsupported` with the source field.

Current official [Codex configuration documentation](https://learn.chatgpt.com/docs/config-file/config-reference) supports the documented types for the cap, status-line list and service tier, but does **not** establish `status_line_use_colors` on the pinned 0.153.2 adapter. The cap bound is a proposed protocol bound, not a measured native limit. The docs' nullable status-line form does not make null a valid legacy TOML value. L2 must freeze actual supported values against pinned releases; an unverified key is `provider_setting_unsupported`, never silently renamed, omitted, or represented as successfully applied. Importer retirement waits for every actual source value to be supported or explicitly resolved by the operator.

#### Resolution and authority

Resolve settings in this order: system configuration replacement of the whole knob, profile global contribution, then that profile's project contribution. Environments context weights and `precedence.placement` do not order these values. Scalar settings and individual plugin booleans use the highest present scope; Codex status-line arrays replace as a whole. Removing a project leaf exposes the global value, and removing the last declaration releases the owned key to its saved pre-management value or absence.

Claude permission lists retain separate source records and compose using a versioned adapter rule, not generic array replacement. The initial rule concatenates global then project contributions, retaining order and empty-array presence in provenance. Empty project `deny: []` does not erase a global deny. No permission evaluator is reimplemented; native deny/ask/allow evaluation remains with Claude. The [Claude settings rules](https://code.claude.com/docs/en/settings) document cross-scope list combination. Source-dependent negations and path anchors mean this simple combination has a bounded admitted grammar, specified next.

For the first adapter contract, admit `Tool` and `Tool(specifier)` forms validated by the pinned Claude implementation; support the concrete `Read`/`Bash` witness, ordinary Bash patterns and Read/Edit patterns without leading negation. Preserve cwd-relative, home-relative and absolute patterns. A single-slash Read/Edit pattern must be rebased from its original scope: native settings directory for a global rule, the verified primary launch directory for a project rule. Retain the source rule unchanged in the machine record, render the equivalent absolute pattern in the managed file, and include the resolved anchor in the effective-settings digest. Do not concatenate source-local negation rules or copy a single-slash pattern into another settings directory unchanged. Refuse shapes whose equivalence is unproved with `provider_setting_unsupported`; extending that subset is an adapter revision with vectors, not a new research chain. The [native path rules](https://code.claude.com/docs/en/permissions) explain why relocation otherwise changes meaning.

Source scope also constrains native modes: a project-only mode that the pinned provider would ignore or forbid must be refused, not promoted into an effective user-level setting by writing it in the managed home. This includes checking current restrictions on project `auto` and `bypassPermissions`. The issue's `acceptEdits` is mandatory in the supported subset. Curator's `permissions.<profile>`, its force-native lock, launcher defaults and flags retain Decision 0018 semantics. The importer must not derive a launch mode from a native setting. Operator choice of a separate yolo launch can change native behavior; it is never described as evidence that imported rules are enforced.

#### Owned keys, output and launch

Apply provider settings to the existing **managed** `settings.json` / `config.toml`. Never write native defaults or project `.claude` / `.codex` files. Do not create a wholesale Claude seed; absent unrelated managed values stay absent, while existing unrelated native files remain byte-identical and existing unrelated managed values retain their parsed values. Codex's existing one-time seed behavior remains unchanged.

The manager reads and validates all necessary non-credential configuration before mutation, computes the full candidate, then updates only its exact key projection under the existing mutation lock/journal. Parsing an existing file unsuccessfully is a failure, not an empty base. First acquisition of a conflicting existing key requires the existing `--takeover` flow, with a private record of its prior value; an identical existing value may be adopted with recorded ownership. No takeover is required merely because an unrelated key shares the file. A change in an owned key is drift; bare resolve fails, explicit repair restores the declared value. An unrelated-key edit is preserved and is not owned-key drift.

Marker v4 records a distinct `provider-settings` projection: adapter contract version, source-scope/effective digest, sorted JSON-pointer-like owned paths, and a canonical hash of their **presence plus typed values**. Store rollback data for only these keys in private manager state; never put entire user configuration in the profile store. The normal full-file surface hash is not repurposed to mean a projection hash. On ownership removal, restore the saved value/absence only if the current key still equals the last managed value; otherwise refuse with `provider_settings_release_conflict`. This makes uninstall/unset conservative in the presence of provider writes. Retained homes remain subject to the existing profile-remove retention policy; settings migration never purges a home.

A settings-only config change does not alter the profile lock hash. Verification therefore recomputes the effective-settings digest independently on every resolve, including `--repair`'s fast path, and compares it with the marker. Proposed fragment v4 carries optional `settings: {digest: "<64 lowercase hex>", adapter_revision: "<frozen identifier>"}` when this record influences the launch. No raw setting, source path, or arbitrary argv enters the fragment. Existing home variables deliver the native configuration; the launcher's existing builder remains the sole process constructor. The fragment digest then changes when effective settings or scope changes.

#### MCP negative policy

Keep `requires.mcp` as dependency declarations; never give it false values. Compute a separate effective policy by server and environment. Absence inherits; `disabled` suppresses until a higher explicit operator scope enables it; `denied` in either effective scope wins over any `enabled` in the other. Removing a deny requires editing the scope that owns it. A system-locked knob is resolved first and cannot be overridden by an operator record.

An `enabled` choice cannot manufacture a server or bypass the MCP package/source allowlists: it requires an admitted declaration. A negative choice may name an undeclared server, because old native seeds and project sources can supply it; retain this choice even when the server is currently absent. Do not fetch or launch anything to check a negative target. Do not skip audit or allowlist checks for a disabled declaration already in the closure. Compute `env_names` from enabled servers only.

For **Claude**, filter the managed declaration set and keep the existing strict MCP channel whenever there is any explicit negative choice, including a negative-only or all-disabled profile. In that case write the canonical empty `{ "mcpServers": {} }` file when needed and pass the existing `--strict-mcp-config` companion flag. Omitting that channel would re-enable other sources.

For **Codex**, filtering declarations alone cannot suppress an A-seeded base. Emit explicit `enabled = false` overrides for negatively selected names through the existing reserved `curator-mcp.config.toml` channel. The pinned adapter must establish whether a negative-only table can inherit its transport from the base; if not, a manager-owned per-key suppression in the existing managed base is the bounded fallback, retaining all unrelated server fields. No commandless table may be emitted merely on the assumption that Codex accepts it. An absent negative target remains in policy provenance and is checked on subsequent resolves so a newly added base server cannot evade it. The initial implementation must cover A, B, and pre-record homes without forcing re-provisioning, copying auth, changing the historical seed record, or deleting unrelated native servers.

Fragment v4 retains the current `mcp` path/channels/env-names shape and adds a closed per-name `policy` map when explicit choices exist. Its presence rule includes explicit negatives even if there are no positive declarations. The launcher/agents-management path must preserve the channel, recheck file availability before exec, and refuse conflicting native arguments or unverified higher-precedence provider configuration that would re-enable a denied/disabled target. This is a bounded extension of the existing launch contract, not another transport. If the pinned release cannot establish suppression for a source class, return `mcp_policy_unenforceable` and no fragment/launch; neither missing evidence nor a provider silently ignoring a key proves suppression. Open question 4 identifies the exact decision if the Codex layer assumption fails.

## Security considerations

The threat model includes hostile repository content, malformed legacy input, a changed local config between inspection and publication, and pre-existing provider configuration that defeats an apparent opt-out. The new authority lives in operator/system configuration, never in package content or project-discovered files. Package schema 1 remains closed, overlays retain their current admission gates, and profile selection alone does not authorize a repository to alter the machine setting. A new optional system lock for the entire `environments.profile_settings` knob prevents operator replacement when fleet configuration owns it; it does not create per-tool semantic policy inference.

Use strict JSON for the new record and a real TOML parser/editor for existing Codex files. Bound bytes, array lengths, integer values and strings in the adopted schema; freeze these bounds in L1 rather than relying on provider defaults. Never execute permission patterns, plugin identifiers, or MCP source data while parsing. Error messages name the field and reason without echoing a whole input or native file. Reject credential/auth selectors and all non-allowlisted fields. Preserve unknown existing values locally without exporting them into markers, outcomes, logs, packages, or public board resources.

All mutation paths retain no-follow directory-entry replacement, protected-root checks, preflight, and journal recovery. Revalidate file identity/content before publication; a concurrent edit yields a typed conflict, not loss of unrelated data. The existing same-user resolve-to-exec race remains a stated bound (rc.14 §10.1:3045–3053); this proposal does not promise a sandbox or protection against an actor controlling operator configuration and the manager lock. Launch-time checks improve detection but are not a claim of race freedom. Claude may reload changed settings in a running session; migration and updates must state that consequence and recommend quiescing sessions when rule anchors or permissions change.

No real credentials, auth files or Keychain contents were read in this research. No native provider was launched, logged in, or logged out. All runtime probes used a synthetic HOME and an empty inherited environment.

## Compatibility and migration

1. **No automatic migration on upgrade.** An absent `profile_settings` record keeps existing behavior. Existing package manifests, profile locks, overlay sources, v1–v3 markers and v1–v3 fragments retain their old meaning. Decision 0014 stays proposed.
2. **Inventory on the PM side.** Read only installer-owned source fields, preserve global/project provenance and explicit false/empty values, and classify every field as mapped, owned elsewhere, or unsupported. Engine/model configuration stays with curator-inference-manager; sessions, project trust/notice tables, credentials and attachments are excluded. Do not use Curator's native-context import as a proxy for this inventory.
3. **Install/select profiles using current APIs.** Reuse existing names/homes when possible. A new project profile uses ordinary install/overlay composition and explicit launch selection. Existing credential mode and home identity never change as a side effect of adding settings. A genuinely new profile may have the existing first-use authentication requirements; this feature cannot silently copy credentials to avoid them.
4. **Publish configuration atomically.** PM submits the full candidate record/map through `env config set`. Curator validates it before its atomic configuration write. A malformed or unsupported record changes no config, profile lock, native file, or managed surface. Successful configuration publication may intentionally leave a home stale; that is an unapplied declaration, not proof of a migrated launch. PM records that state and retains its old installer inputs until verification succeeds.
5. **Apply per managed home.** `env resolve --repair` plans all owned-key edits and MCP effects before changing that home, with consented takeover for colliding keys and journal recovery. Bare resolve emits no fragment while stale. `profile sync`, update, reinstall, use, removal and config unset must share the ownership rules; no path may restore a whole old config over unrelated tool edits. An outer importer transaction compensates a failed multi-profile rollout; no claim of all-homes atomicity is made by a sequence of separate CLI invocations.
6. **Keep old Codex homes.** Seed A and pre-record homes retain their seed bytes except for specifically acquired owned keys. Negative policy suppresses named servers without deleting the base or touching auth. Release of that policy restores the prior owned value/absence conservatively. The old seed record remains truthful.
7. **Downgrade.** New schema/version tokens fail closed in old readers. To downgrade, first release the new records through the new binary and repair each affected home; verify restored owned keys and absence of v4-only launch requirements. Never strip fields or relabel a marker/fragment version in place.

## Specification changes

Adopt **CIP-0006 only**, with a short link from Decision 0014 recording that the narrow machine-owned subset was decided elsewhere. Do not change 0014's overall status. Add a clarifying cross-reference to Decision 0018: stored provider defaults are not the launch-mode knob and do not imply an effective-policy attestation.

The normative amendment should say:

> A manager MAY accept the closed `profile_settings` machine knob. It MUST preserve presence and scope, reject unsupported or malformed contributions before publication, and apply only its declared owned keys in managed homes. An unreadable base is never an empty base. A negative MCP choice MUST be represented at launch even when the positive declaration set is empty. A manager or launcher unable to establish the supported adapter's suppression MUST refuse rather than emit or consume a permissive substitute.

| Spec / schema | Required change |
|---|---|
| Environments §1 and §2 | Clarify that machine-owned settings do not broaden package content. Keep `agent-context-v1` byte-frozen; package `settings` remains invalid. |
| §§5.8, 7.8, 10.2 | Explicit MCP negative policy, empty authoritative output, pinned Codex suppression encoding; fragment v4 and existing-channel application. |
| §§7.4, 8.2–8.4, 10.1 | A/B/pre-record coexistence, key-projection ownership, stale checks, takeover/release/rollback, scope and adapter digests; no credential-mode migration. |
| §§9.2, 12.1–12.2; manager config/cleanup | `profile_settings` grammar, project scope guard, whole-knob system lock, config changes/removal and retained-home handling. |
| `manager-config-v4`, `system-config-v3` | New knob; retain all earlier accepted shapes. These are next versions after main's manager v3/system v2, not rewrites of v2. |
| `agent-environment-marker-v4` | Separate typed key-projection record, effective-settings digest and adapter version; preserve existing hash framing version 2 and credential records. |
| `launch-env-fragment-v4` | Optional settings digest/adapter revision; MCP policy extension and presence semantics; existing permission object and home boundary unchanged. |
| CLI reference, §13, conformance catalog | Exact typed reasons, entry-point vectors, schema rejection/compatibility cases, projection and launch goldens. |

Proposed new reasons: `profile_settings_invalid`, `profile_settings_scope_mismatch`, `provider_setting_unsupported`, `provider_settings_release_conflict`, `provider_settings_write_conflict`, `mcp_policy_target_unsupported`, `mcp_policy_unenforceable`. Reuse existing unmanaged-conflict, stale-home, unreadable, store-trust and write-would-follow-link reasons where their definitions already fit. CLI syntax errors remain exit 2; configuration/resolution refusals exit 1; no refusal emits a fragment. Do not hardcode version numbers into a landing without checking that they remain unallocated.

## Implementation plan

Sizes are engineering estimates, not measured durations: **S** ≤1 focused day, **M** 1–3 days. No leaf requires another research handoff; bounded adapter probes are evidence within their consuming implementation leaf. Spec changes land first or with their consumers, never after an implementation silently broadens rc.14.

| Leaf | Size | Ordered deliverable and boundary | Dependencies |
|---|---|---|---|
| **L1 — narrow normative contract and input vectors** | M | Decide the questions below; publish CIP in curator-spec; freeze config grammar, bounds, scope and presence algebra, typed errors, ownership and rollback, and synthetic mapping vectors for all ten inventory rows. Update manager/system schemas and keep legacy schemas frozen. | Operator decision / review |
| **L2 — pinned adapter contracts** | M | Version the nine-field validators and MCP suppression encodings against Claude 2.1.261 and Codex 0.153.2, or an explicitly adopted replacement pin. Accept the bounded Claude rule subset above; no home/auth probes. TOML is 1.0 parsed by the repo's existing `go-toml/v2`, never line matching. Probe false, empty, anchored rules, source scopes and older seeded MCP bases with disposable homes. Freeze provider and fragment/marker vectors. Any failed native assumption routes only the exact open decision. | L1; feeds L3/L5/L6 |
| **L3 — first vertical settings slice: Codex cap** | M | Drive `env config set` → strict parser/config persistence → `machineFromConfig` → `Resolve`/`assembleHome` → owned `project_doc_max_bytes` → marker/digest → real `env resolve`. Implement the reusable projection transaction for one scalar, including unset/release and unrelated TOML value preservation. A malformed real CLI call must preserve previous state. | L1–L2 |
| **L4 — remaining Codex settings** | S | Add ordered status-line array, false color flag and service tier to that path; unknown values refuse. Do not build a model capability router. | L3 |
| **L5 — Claude settings and scope preservation** | M | Closed JSON projection, permissions/list provenance and anchor conversion, mode-scope validation, plugin booleans, project-root guard. No plugin installer or arbitrary settings import. Exercise config publication and managed-home resolve, not helpers alone. | L2–L3 |
| **L6 — MCP policy through manager output** | M | Centralize effective server policy used by rendering, status and fragment env-name union. Implement negative-only/all-disabled output, allowlist precedence, name validation and A/B/pre-record suppression. Ensure policy edits stale the home without requiring a lock change. | L2–L3 |
| **L7 — launcher/agents-management consumption** | M | Consume fragment v4 through the existing builder, preserve strict/negative channels, reject unsupported revisions and contradictory native overrides using the provider-owned argv grammar. Real `curator run` with a capture tool exercises both direct and tracked plan paths where supported. No alternate transport or duplicate permission mapper. | L5–L6; launcher spec in lockstep |
| **L8 — existing-home lifecycle and PM handoff** | M | Cover sync/use/update/reinstall/unset/remove/retry and crash recovery; test old marker/seed combinations; provide a sanitized PM input/output example and mapping receipt with unsupported-field reporting. PM's importer leaf consumes this API and owns project selection, global-record replication and multi-profile compensation. | L4–L7 |

The first useful production slice is L3; L4/L5 are bounded adapter extensions, not prerequisites to yet another generalized settings framework. #105 is not ready for importer retirement until all ten inventory rows and the managed launch path are verified.

## Test plan

Use the repository's Go tests, CLI harnesses and curator-spec conformance vectors; no new test framework. Every gate test names the real call chain it reaches. Proposed feature coverage today is **0/10 mapping rows**; the research's **5/5 selected existing tests** only verify the baseline. Do not conflate them.

| Vector family | Required production-entry evidence | Negative / narrowing mutant |
|---|---|---|
| Mapping / presence | All nine provider paths plus MCP; absent, empty, false/zero and nonempty values through `env config set/show`, resolve, and captured native config. Derive expected paths from the frozen #105 vector inventory. | Drop false in serialization; default-fill an absent value; omit one row from materialization. Report exact covered/required ratio. |
| Strict input | Unknown object key at every depth, duplicate JSON keys, wrong/null types, invalid UTF-8, invalid ranges/modes/rules/server identity and unsupported tool release. | Bypass strict decoding only in `cmdEnvConfigSet`; accept a bad nested member while rejecting top-level extras. Prove nonzero exit and unchanged state. |
| Scope | Global and project values differ; current versus named profile; two projects concurrently; same-prefix sibling directory; symlink alias; inaccessible root; root versus nested cwd for permission anchors. | Apply project block outside root; treat a failed canonicalization as absence; drop global deny when project list is empty. |
| Ownership | Existing unrelated JSON/TOML values and types survive acquisition/update/unset. Owned drift refuses bare resolve; repair restores only owned projection. Source anchor/digest changes stale the right home. | Hash whole file; trust marker digest without recomputing config; restore whole backup; release a provider-modified key. |
| Transaction | Bad config leaves config bytes unchanged. Unreadable/malformed native-format base, no-follow target/component attacks, injected journal failure, failure before marker rename and retry. | Validate after first write; use empty base on read failure; follow a target link; omit recovery of one affected file. Verify no emitted fragment on failure. |
| MCP | Absent/enable/disable/deny; negative-only and all-disabled; transitive declaration, unknown positive, negative absent target, name collisions, global deny versus project enable; disabled env names excluded. | Restrict filter to direct dependencies; only preserve empty channel when a positive server once existed; keep disabled env names; skip package allowlist for disabled dependency. |
| Native suppression | Claude strict-empty plus native/project servers; Codex A/B/no-record base, newly added base server, inline/dotted/quoted TOML keys, higher-precedence project config, conflicting CLI args. Capture zero contact with a synthetic disabled server. | Remove strict companion flag; filter declaration but keep base active; accept second/overriding provider profile/config argument. Report unknown, not zero, if the provider's effective set cannot be observed. |
| Versions / lifecycle | Old files with no new knob stay unchanged; old version carrying new member refused; new version rejected by old consumer; setting changes without lock change; sync/use/update/reinstall/config unset/profile removal and restart. | Check only explicit repair, bypassing the current-home fast path; relabel old schema; silently ignore v4 policy. |

Run platform CI on Linux, macOS and Windows for parsing, path identity, case collisions, no-follow operations and journal recovery. Native adapter qualification is separate: publish the measured tool/OS pairs and refuse an unverified enforcement path, rather than calling a Go cross-platform green a native-provider result. Auth-preservation tests use sentinel paths/files and assert no read/open/copy or Keychain invocation; no live login is needed. Contract probes use an empty inherited environment and isolated HOME/config paths.

## Open questions for the operator

1. **Approve the narrow authority location?** Recommended: option A, the machine-owned `profile_settings` knob on existing profiles. Keep package distribution and Decision 0014 adoption deferred. If portable settings packages are required now, choose B explicitly and add its trust/admission leaf.
2. **Approve project selection and the meaning of global?** Recommended: explicit named project profiles with guarded roots; PM copies the preserved global contribution into each migrated profile record and selects that profile through existing launch configuration. No automatic cwd profile selector or implicit all-profile inheritance. Confirm the PM consumer can supply that existing selection before its importer switches over.
3. **Approve the bounded native-rule contract and semantic preservation?** Recommended: refuse unproved rule forms and values, preserve supported values and source intent, and permit managed JSON/TOML formatting changes while preserving unrelated parsed values. Source-relative permission anchors must be translated and tested; no raw relocation. `status_line_use_colors` must be verified at L2, or reported as an unresolved source value that still blocks retirement.
4. **Approve old-Codex-home suppression if the reserved layer cannot express it?** Recommended: first prove explicit `enabled=false` in the existing layer. If the pinned tool rejects negative-only layering, authorize key-level suppression only in the managed base, with projection ownership and conservative restoration. If neither suppresses a higher-precedence source reliably, refuse that launch and request a pinned-provider/spec decision; do not purge/re-provision auth homes or silently drop the opt-out.
5. **Approve deny and release semantics?** Recommended: deny wins across the preserved global/project scopes, disable is overridable by a higher explicit enabled choice, and removal restores prior values only when the manager's last value is still present. System configuration can lock the whole new knob. Keep Decision 0018's launch permission mode independent.

With those decisions, A provides the smallest supported migration surface; its main cost is explicit per-key ownership rather than portable package distribution. The implied work is L1's reviewed spec/schema contract, L2's bounded adapter qualification, then L3–L8's settings, MCP, launcher and migration slices. This draft and its evidence are ready for review; they do not authorize implementation or claim that #105's runtime acceptance already passes.
