# CIP-0002: Project context in managed launches

- **Status:** Draft
- **Owner:** ivan-curator (orchestrator); decision: operator
- **Created:** 2026-10-04
- **Related:** TASK-261004-2asduq — launch-command-environment-fragment-design; STORY-261004-1ffwh8 — design-launch-project-views; TASK-261004-34brhn — research-claude-login-transfer-modes; Decisions 0013, 0017, 0018 and 0019
- **Affects:** curator-spec environments §§1–5, 7–12; manager §§3, 5, 6, 10, 12; fragment and manager schemas; Curator, curator-run, agents-management and the tracked-session launch-plan consumer

## Operator input (2026-10-10)

The operator confirmed the model: a project layer composed over a profile, outside the repository, while the Skillfile stays in the project as the declaration of skills. To be integrated before acceptance:
- **Names.** `register` takes `--name`; by default the name comes from the repository or directory name.
- **Operator and agent mode.** `inspect`, `preview` and `approve` work for both. An agent may inspect and propose, and may approve only within a granted ceiling (for example no new permissions and no network MCP servers); everything above the ceiling needs the operator. Every approval records who approved it.
- **Launch by project.** `curator run <project>` or `curator run <profile> --project <project>` works from any directory.
- **Saved composites.** A project can keep a default composite: `curator project set acme --profile dev` records `dev` plus the admitted layer of `acme` (the profile, its lock and the layer, with their digests) as a manager record, never as a new profile. `curator run acme` uses it; `curator run review --project acme` overrides it once. Without one, `curator run <project>` uses the profile extracted from the repository's own admitted layer. A name that is both a profile and a project refuses until `--profile` or `--project` disambiguates it.
- **Several profiles per project.** A project may list alternative profiles with one default (`curator project set acme --profiles dev,review,release --default dev`; `curator run acme --as review`), or a stack composed like overlays (`curator project set acme --stack dev,security`, weights in stack order). Version requirements of the stacked profiles resolve jointly under semver: a common satisfying version is chosen, and only ranges with no common version refuse (`context_range_conflict`), never as two copies.
- **Trust boundary.** Everything in a repository that configures an agent (instructions, rules, MCP servers, hooks, plugins, permissions, skills) reaches the harness only as approved protected copies, and native discovery of it is suppressed. The project's code stays the agent's work data: it is read and edited, but nothing in it becomes an instruction, a tool or a permission without approval.
- **Composition today.** Machine overlays (`curator profile compose <profile> add`) already join packages to a profile's closure for every launch of that profile on the machine; a profile-plus-project composite that leaves the profile untouched is new in this CIP. Per-launch PATH entries are also new: the fragment's `path_prepend` is reserved and not emitted today, and profile commands are unavailable in managed-home launches.
- **Follow-ups:** the surfaces the Skillfile does not cover yet (curator issue #113), and modular instruction files assembled from chapters at launch (curator issue #114).

## Summary

Allow a registered project X to contribute individually approved context, rules, knowledge, MCP servers, permissions, skills and commands when launched with profile Y. Recommend a persistent manager-owned home for each checkout × profile × environment, backed by a digest-bound composition record and leased for the session lifetime. Repository files are candidate inputs to admission; native tools receive generated, protected copies and must not discover unapproved project configuration implicitly. A proposed fragment v4 carries the context identity and a single manager dispatcher directory through a typed channel, with PATH append performed after child-environment admission. This proposal asks for design decisions; it neither authorizes implementation nor claims that every native adapter can enforce the proposed boundary today.

## Motivation and user stories

- An operator launches project X with profile Y and gets X's approved instructions, knowledge, skills and commands together with Y's base environment. Another project using Y must not inherit X's context, approvals or session state.
- A project can request its own MCP servers, AGENTS.md/CLAUDE.md equivalents, environment-specific rules and permission changes. The operator can enable a category, select individual items, inspect the effective result, and revoke them without editing Y.
- An unfamiliar or hostile checkout remains ordinary work data. Opening it must not implicitly execute hooks/extensions, grant permissions, start MCP servers, import secrets or make its `.agents/bin` authoritative.
- A tracked run must resolve the same admitted context and command owners as a direct launch. Detach, resume, native subagents and garbage collection must preserve that identity.
- A macOS user should see the first-login cost before choosing isolated project homes. The design must not depend on credential copying or an unverified shared Keychain strategy.

## Current state

Evidence below is pinned to Curator main `ca1b776`, curator-spec `43bf0a2` (the exact `v1.0.0-rc.14` commit), and launcher main `d092035`. The attached sketch's older Curator/launcher pins are historical inputs, not the baseline used here. This CIP is filed from the research draft in [.research/261004_CIP-0002-project-context-in-managed-launches.md](https://github.com/relux-works/curator/blob/fae2ff9cab17a031c26a2b4c776afd8dc5e8b4f6/.research/261004_CIP-0002-project-context-in-managed-launches.md) on `relux-works/curator` `main` @ `fae2ff9c`. Reproduction details, source locators, versions and bounds remain in the companion [.research/261004_CIP-0002-project-context-in-managed-launches_evidence.md](https://github.com/relux-works/curator/blob/fae2ff9cab17a031c26a2b4c776afd8dc5e8b4f6/.research/261004_CIP-0002-project-context-in-managed-launches_evidence.md) at the same commit; they are cited, not copied. The operator has made no acceptance decision on this proposal.

- Homes are keyed by profile × environment, without a checkout dimension: Curator `internal/envprofile/managed.go:63–76`. `LaunchDir` exists, but is not part of that home key. E1.
- The fragment emitter uses v2 for existing adapters and v3 for Muse. It has no project/context identity, command dispatcher or append operation; `path_prepend` is reserved, never emitted, and restricted to one path beneath the environments root. Curator `internal/envfragment/envfragment.go:23–70`; rc.14 environments §§9.4, 10.2–10.3. E2.
- Current command shims represent the machine-current profile. The spec explicitly declares profile commands unavailable in managed-home launches; project/hybrid skill resolution is a separate lane. Merely appending a new directory would leave older singleton shims ahead of it. rc.14 environments §9.4, lines 2583–2606. E3.
- Claude's strict MCP flag is conditional: Curator creates the MCP member only for a recorded, resolved MCP surface; the launcher appends `--strict-mcp-config` only inside its non-nil MCP branch. An empty profile MCP set does **not** establish an exclusive empty set. Curator `internal/envprofile/managed.go:2290–2312`; launcher `internal/composition/composition.go:93–122`. E4.
- The launcher passes the real launch CWD to the admitted plan. It launches Claude, Codex and Pi; OpenCode has no provider mapping, and its parser accepts only fragment v1/v2, so Muse's v3 is not consumable at this pin. A five-adapter manager registry is not a five-adapter launcher. E5.
- Tracked composition transports owned environment literals and environment-name lookups, not an operation on the destination's PATH. Existing fragment hashing cannot identify a project composition absent from the fragment. Decision 0013 §§3.2, 6.4; launcher `internal/composition/composition.go:33–46,74–90`. E6.
- Managed credential isolation is not a sandbox. Decision 0017 keeps Claude/macOS shared mode unsupported and records evidence inconsistent with the older Keychain-suffix explanation. First login per distinct home is the supported planning assumption; the mechanism and transfer options remain under TASK-261004-34brhn — research-claude-login-transfer-modes, whose outcome was not yet available when checked. E7.

### Native project inventory

“Documented” means vendor documentation or installed-package documentation, not a launch-enforcement result. P1–P6 in the evidence identify the smaller measured surface. Native slash commands and shell executables are different command mechanisms.

| Environment | Instructions, rules and knowledge | Settings, executable discovery, skills and commands | MCP and permissions |
|---|---|---|---|
| `claude_code` | Ancestor/current `CLAUDE.md`, `.claude/CLAUDE.md`, `CLAUDE.local.md`, imports, nested instructions and `.claude/rules/`; path-scoped rules and auto-memory. Current docs add AGENTS.md fallback from 2.1.277, newer than Curator's 2.1.261 pin. Knowledge may be imported or read on demand. | `.claude/settings.json` and `.claude/settings.local.json`; project skills, commands, agents, hooks and plugins. Settings source selection alone does not suppress instruction or skill discovery. | `.mcp.json` is a native project source. Settings contain permission rules and environment assignments. Strict MCP excludes other MCP configuration when applied; it does not exclude project instructions, hooks or settings. D1–D3. |
| `codex_cli` | Root-to-CWD AGENTS chain: `AGENTS.override.md`, then `AGENTS.md`, then configured fallbacks; home instructions load separately. Project `.codex/rules` execution rules are permission policy, not prose. | Trusted `.codex/config.toml` layers; project hooks and enabled plugins; `.agents/skills` from CWD to repository root. Current docs describe project plugins/marketplaces too. A home override does not disable these reads. | Project config can declare MCP/settings; selecting `-p curator-mcp` is a config layer, not an exclusive configuration source. No reviewed evidence establishes native `.mcp.json` discovery. CLI policy overrides and enforced requirements are separate from instructions. D4–D7; P2–P4. |
| `opencode` | Legacy docs describe project AGENTS.md with CLAUDE.md fallback, plus `instructions` paths/globs/URLs, including Cursor rules. V2 docs instead describe AGENTS-only discovery, dynamic nested reads and an inactive `instructions` array. These are distinct version contracts. | `opencode.json(c)`, `.opencode` configuration/resources, commands, agents, skills, tools and plugins; configuration merges with global/custom sources. Project resources may execute code. | MCP and permissions are config members. `OPENCODE_CONFIG` is below project config in the legacy merge order. No reviewed evidence establishes native `.mcp.json` discovery. V2 documents `OPENCODE_DISABLE_PROJECT_CONFIG`; its entire security coverage is unmeasured here. D8–D11. |
| `pi` | AGENTS/CLAUDE chain with `AGENTS.override.md`; `.pi/SYSTEM.md` replaces and `.pi/APPEND_SYSTEM.md` appends. Instructions can load before project trust. Knowledge is ordinary context/skill data. | `.pi/settings.json`, `.pi` extensions, packages, skills, prompts/themes; project `.agents/skills`. Trusted project resources can install packages and execute extensions. `--no-approve` excludes project resources but is not an instruction-file switch. | No built-in MCP channel or permission-popup system; extension-based MCP/permissions are executable integrations needing separate admission. Native project trust is not a filesystem sandbox. Installed 0.84.2 docs and a real RPC startup probe establish the trust split. D12; P5. |
| `muse` | Vendor docs describe AGENTS.md, CLAUDE.md, `.agents/AGENTS.md`, `.claude/CLAUDE.md`, choosing the first at each level; project rules require trust. `.agents/memory` supplies an index and knowledge files. | Project `.agents/skills`, `.codex/skills`, `.claude/skills`, plugin skills and `.muse/hooks.json`; foreign personal skill roots can remain ambient. Project trust enables several surfaces together. | Documented MCP and permission profiles live in user settings; project hooks are separate. Native project `settings.json` or `.mcp.json` loading is **not established**. rc.14 admits no Muse root-context, prompt or MCP channel; its measured skill location differs from current vendor docs. D13–D15; E8. |

### What managed launches keep, suppress or must re-admit

| Adapter | Current managed behavior | Required behavior for the proposed strict modes |
|---|---|---|
| Claude | Keeps the managed home and real CWD; suppresses other MCP sources only when its MCP channel exists. No general project-source suppression in the composition site. | Explicit generated MCP file, including an empty set, plus strict mode; suppress project/local settings and all automatic instruction, skill, hook/plugin discovery, then enable only admitted outputs. Test lazy nested reads as well as startup. `--bare` is not a general solution: its measured help excludes OAuth/Keychain; `--safe-mode` disables desired customizations. No complete selective recipe is proven here. |
| Codex | Managed home/context and MCP layer; project instructions still load. P2 reproduces that; P3 reproduces trusted project configuration despite the zero document cap. | `project_doc_max_bytes=0` is a measured candidate for suppressing project instruction injection while retaining home context. Separately exclude project config, hooks/rules, repository skills and plugins; re-render admitted atoms into the managed layer. Untrusted-project configuration alone does not prove all discovery is disabled. Unknown coverage refuses strict launch. |
| OpenCode | `env resolve` supplies XDG home and optional custom config; current curator-run refuses this adapter. Ambient native skill sources and project overrides are documented residuals. | Add a real launcher mapping only with a version-specific exclusion/re-admission contract. Qualify V1/V2 separately, including remote configs, compatibility roots and dynamic instruction reloads. No claim that changing XDG or setting one disable variable isolates everything. |
| Pi | Managed home and prompt channels; launch arguments do not establish a project-source exclusion policy. Current Curator notice says “No trust wall”, contrary to P5 and installed 0.84.2 docs. | Candidate recipe: `--no-approve`, `--no-context-files`, resource-discovery disable flags, then explicit manager-owned skill/prompt/extension paths. Also neutralize project SYSTEM/APPEND_SYSTEM discovery. Verify these combinations at the entry point before certification. Required MCP or enforced permission semantics without an admitted implementation refuse. |
| Muse | Four XDG roots can be resolved, but current launcher cannot consume v3. Foreign personal context remains ambient by the current manager's own notice. | First establish the native target paths and source controls on the selected release. Neither trusting the whole checkout nor `--workspace` establishes per-item admission. A complete exclusion/re-admission channel is unknown; strict project capability remains unavailable until qualified. |

## Design

### Options considered

| Option | Mechanism | Advantages | Costs and security tradeoffs |
|---|---|---|---|
| **A. Persistent checkout × profile homes** | `environments/project-views/<checkout-id>/<profile>/<env>/`, with an immutable composition record and a stable native state/auth root. | Separates projects, approvals and memory; reuses a home's login; fits existing materialization/marker concepts; easy to explain. | More homes and storage; first login may recur per new home; generated surfaces cannot change while leased. Still needs native project-source suppression and OS protection of authority. **Recommended.** |
| **B. Composed view inside profile Y's existing home** | Select or rewrite a project composition at Y's native fixed paths; store records alongside Y. | Reuses existing login and configuration/state roots; smaller migration. | A config switch is visible to late reads by every session using Y. Safe only by serializing all differing project views on that home, or proving complete per-session native indirection. Shared trust/memory remain cross-project. A symlink swap does not solve this. |
| **C. Launch-time overlay** | Generate temporary files and pass explicit native flags/config roots for each launch; retain Y only for authentication where supported. | Immutable session inputs, simple cleanup ownership, natural plan identity. | Uneven native channels; root/rule/skill discovery often follows CWD independently. A new native home per run multiplies login cost; reusing Y can leak mutable state. Acceptable later for adapters with independently proven config/state/auth separation. |

None of these home layouts alone provides the hostile-repository boundary. This proposal does not hide that missing boundary behind a copied workspace, an empty fake repository, broad native trust, or credential transfer.

### Recommendation

Adopt option A as an **optional, separately versioned project-context capability**. Keep rc.14's existing environment capability intact. Release a strict adapter only when it can both exclude unadmitted native sources and expose the declared admitted surfaces; otherwise return a typed refusal for the requested capability.

#### Operator control surface

The following names are proposed, not implemented CLI/config promises:

| Control | Semantics and default |
|---|---|
| `projects.<checkout-id>.context.mode` | Closed enum `off \| admitted`. New registrations default `off`: a certified launch admits profile context only and suppresses project-native discovery. `admitted` adds the selected project generation. |
| `context.environments.<env-id>` | Per-environment enablement. Enabling an environment does not enable all items. Unknown adapter or unsupported required item refuses. |
| `context.categories.<kind>` | Category ceiling for `context`, `rules`, `knowledge`, `mcp`, `permissions`, `skills`, `commands`, `native-settings`; default disabled until the operator selects it. |
| `context.items.<id>` | `enabled \| disabled`, pinned digest and optionality. Newly discovered items remain unapproved. Exact item/closure approval is required, even inside an enabled category. |
| `context.project_grants` | `deny \| review`, default `deny`; `review` permits presenting permission-expansion requests, never automatically grants them. Fleet ceilings cannot be overridden. |
| `context.memory` | `off \| private`, default `off`; private mutable memory stays in the view's state, separate from approved repository knowledge and admission records. |
| Proposed `context inspect / preview / approve / revoke` | Discovery report, effective diff, explicit approval of its digest, and revocation. No preview executes or sources a file. A launch-time `--project-context=off` can narrow an admitted launch. |

Existing launches remain in an explicitly reported **legacy compatibility state** until enrolled; legacy means today's native discovery behavior, not `off` and not strict isolation. Fleet policy may require enrollment and refuse legacy launches. Unregistered checkouts never gain project context implicitly. This distinction prevents an “opt out” switch from silently re-enabling raw native repository settings.

#### Admission and composition

1. The manager binds an opaque checkout ID to a canonical root through its own registration operation, then proves launch CWD belongs to that registration. Nested registrations use the most specific **registered** containing root; ambiguity, a replaced root, unreadability or a moved checkout requires an explicit repair/rebind. Repository names, `.git` content and profile bytes cannot choose the registration or dispatcher path.
2. Discovery reads a bounded inventory as **untrusted data**, with no-follow/path-kind checks. It may offer imports of AGENTS/CLAUDE files, `.mcp.json`, native config, rules and knowledge; it never executes a parser hook, sources a shell file, fetches a referenced URL implicitly, installs a package or connects an MCP server.
3. Normalize into a closed, versioned declaration: stable item ID, kind, environment selector, scope/path applicability, immutable content or dependency digest, requested capability, dependencies, optionality and source provenance. Native config import accepts a named dialect and allowlisted fields; unknown/executable fields are rejected or shown as separate executable items. It is not a general JSON/TOML pass-through.
4. Snapshot candidate bytes and their transitive file references into the protected store. Resolve imports and finite glob matches at admission; reject escaping paths, cycles, symlinks/reparse points crossing the boundary, malformed reads and unbounded expansion. Pin every referenced knowledge file. Native auto-imports must resolve to those snapshots, never back into the checkout. Each approved executable uses the existing audit/build/activation contract.
5. Present an itemized semantic diff and a digest of the entire review package, including dependency changes, command owners, MCP endpoints/transports and permission effects. Record operator approval against manager identity, checkout ID, digest, allowed environments and policy ceiling. A hash is an identity, not proof of approval; a repository-supplied approval file is never authority.
6. Compose admitted project generation P over **selected profile Y's lock**. Identical skill pins deduplicate. A project replacement substitutes the entire same-identity skill, including its context, commands and providers; recheck every requirement against that replacement. Incompatible required providers and multiple skill identities exporting one command refuse. Hybrid inputs, if needed, must first become explicit admitted P members; do not inherit machine-current/hybrid state implicitly.
7. Build a **derived composition record**, never a replacement profile lock. Include Y lock hash, P/admission digest, environment/release contract, effective policies, ordered context modules, command-owner map, artifact digests and materialization hashes. Profile Y is not mutated. Edits in the repository create candidates for another review; they never update the active generation automatically. Launch reports the admitted generation and candidate drift; unreadable candidate state is “unknown”, not “unchanged”.
8. Before publication/launch, revalidate protected boundaries, approval status, materialized bytes and the CWD binding under the same transaction/lease discipline. Failure yields no fragment/child. A pure preview acquires no durable launch lease and starts nothing; a separate manager preparation operation binds a leased launch context.

#### Layer precedence, by surface

| Surface | Proposed composition rule |
|---|---|
| Root context | Retain Y's base context and system prompt. Add approved project-general context, then environment-specific project context in recorded order; deeper approved scope follows shallower scope. Replacement of Y's root/system prompt is a separately approved item and can be prohibited by policy. Record precedence as intent, not a claim that an LLM enforces it. |
| Rules | Preserve kind and applicability. Support a bounded prose-rule subset: UTF-8 Markdown and explicitly parsed metadata for description, relative path globs and `alwaysApply`; environment-specific formats have separate dialect revisions. Cursor-style `.mdc` is an import format, not a new Cursor launcher adapter. Do not convert conditional rules into unconditional prose or turn execution-policy rules into advice. Unsupported semantics refuse or omit only explicitly optional items. |
| Knowledge | Approved immutable files, indexed under the managed view and loaded eagerly or by explicit reference as chosen per item. An instruction cannot escape the approved reference graph via a native import. Ordinary source reads remain untrusted task data, not newly admitted knowledge. |
| MCP | Union of approved profile/project servers. Same stable ID and digest deduplicates; a differing same-ID server requires explicit replacement approval, otherwise refuses. Pin executable/args or endpoint/transport and declared environment **names**. Manager policy bounds tool capabilities, network access and secret references. Empty means an explicitly enforced empty set. |
| Permissions | Fleet/manager ceilings and immutable denies apply first. Project restrictions may narrow. New grants require `review`, exact approval and compatibility with the ceiling. Use versioned adapter-native rule atoms and evaluate their effective meaning; there is no universal scalar ordering of permission modes. Keep legacy `native/yolo` transport and its lock intact; project settings cannot select bypass or weaken that lock. |
| Skills and shell commands | Whole-skill overlay and unique command ownership as above. Project P falls back to Y, never machine-current. Disabling a required skill/command/provider refuses composition rather than silently breaking a dependency. |
| Native settings and mutable memory | Allow only reviewed fields with known semantics. Deny auth stores, provider redirection, updater/download controls, PATH/home overrides, arbitrary hooks/plugins and shell initialization by default. Separate executable integrations need their own pinned admission. Runtime memory/approval writes cannot mint project admission or alter generated policy. |

Native trust flags approve a whole folder and may activate more than one of these surfaces. They cannot stand in for per-item manager approval.

#### Stable homes, leases and login

Use a stable native home at `environments/project-views/<checkout-id>/<profile>/<env>/`, with generated surfaces recorded separately from native writable state. Immutable composition records live in a manager-owned records area; the fragment binds their content digest, not a mutable `current` alias. The exact native layout remains adapter-owned, including Muse's four XDG parents and OpenCode's parent/child shape.

One home has at most one materialized composition while any session leases it. Concurrent launches may share the same composition only where the native adapter supports concurrent state access. A changed composition waits for all old leases to end or refuses with `project_view_busy`; it never swaps generated files beneath running sessions. Reuse the same home after an idle, transactional update to avoid a new login for each digest. Creating an additional separately named home is an explicit operator choice with its own login/state cost, not an automatic fallback.

Acquire the lease before the view can be collected and bind it to the launch context; transfer ownership to the actual tracked session/runner before the launching process exits. Detach and descendants retain it. Resume uses the recorded composition, not today's active generation. PID alone and elapsed TTL alone are insufficient proof of termination: recovery establishes process/session identity, and unknown liveness retains the lease. GC cannot remove leased homes, compositions or runtime artifacts. Revocation prevents new launches and new dispatcher admissions; already running native processes need an explicit stop/restart or an enforcing runtime channel. File replacement is not revocation of already loaded context.

Default to existing adapter credential strategies. Do not copy/export secrets, re-point credentials on a launch, or preserve login by sharing a mutable profile home behind the operator's back. Claude/macOS may require one login for each new checkout × profile home. Auth sharing experiments and future mechanisms belong to TASK-261004-34brhn — research-claude-login-transfer-modes; this recommendation does not depend on a positive result there.

#### Fragment v4 and the command dispatcher

Reserve the next unused outer fragment revision, currently **`launch-env-fragment-v4`**; v3 already names Muse. V4 retains applicable v2 permissions/v3 home semantics and adds a closed project-context descriptor even for views without commands. Separate context admission from command transport so a context-only opt-in does not require PATH modification.

Candidate shapes, with symbolic values rather than executable configuration:

```json
{
  "project_context": {
    "version": 1,
    "mode": "admitted",
    "context_ref": "<manager-owned immutable record reference>",
    "context_sha256": "<64 lowercase hex>",
    "project_root": "<canonical registered absolute root>",
    "lease_ref": "<manager-issued launch lease reference>"
  },
  "command_environment": {
    "version": 1,
    "operation": "append",
    "dispatcher_dir": "<canonical protected manager dispatcher directory>",
    "context_ref": "<same context reference>",
    "context_sha256": "<same digest>",
    "project_root": "<same root or null for a profile-only context>"
  }
}
```

These are draft members, not an accepted schema. The normative revision must fix reference grammar, null/absence rules, bounds and diagnostics. Proposed invariants: object fields and enums are closed; one dispatcher directory; no append-list grammar, executable fragments, arbitrary environment maps or repository command root. Duplicate keys, unknown versions, mismatched context references/digests/roots and conflicting `path_prepend` are invalid. The project root is the sole typed external path exception; home, record and dispatcher paths remain manager-owned. Validators must stop deriving the environments root by stripping two path segments from a home: the project-view layout is deeper. E9.

The original sketch's at-most-two project/global roots is rejected in favor of **one manager dispatcher directory**. The effective project-then-profile precedence lives in the protected owner map; it does not require two search roots. Forwarders execute a manager-owned dispatcher by absolute identity, which resolves the captured context/lease, revalidates protected activation and invokes the admitted runtime/artifact. Never execute `.agents/bin` or source `.agents/env.sh`, `.envrc`, profile shell bytes or repository hooks. Context references are lookups, not bearer authority; the dispatcher authenticates its managed session binding independently.

Migrate existing manager-owned singleton forwarders to dispatch through the same context binding, or refuse when an older forwarder would shadow the new view. Appending cannot outrank such a shim. For unmanaged earlier executables with an admitted command's name, report/refuse ambiguous ordinary-command availability and offer an explicit manager command invocation; never silently invoke the wrong skill. Reserve all `curator-*` names and add the dispatcher directory and aliases to umbrella provider-discovery refusals, even if placed in a configured provider trust root. E3, E10, P6.

For a nonempty admitted base PATH, append the dispatcher once using the platform separator, retaining earlier entries and order. Normalize/deduplicate the manager-added directory by canonical identity; retain its existing position if already present. Reject malformed/unreadable manager roots and ambiguous PATH entries required for command selection. If PATH is absent or excluded by the environment policy, refuse command capability rather than recreate an environment variable that admission removed. Empty/relative/CWD-sensitive components and repository-writable search roots require explicit treatment in the upstream PATH-admission contract; strict mode must not accept them by accident. Native settings may not subsequently replace PATH or shell initialization defeat the recipe. Claude `settings.env` and Codex `shell_environment_policy.set` are assignment surfaces, not append operators. D2, D5.

Apply the operation on the **admitted child PATH**, not the parent shell's PATH. In tracked mode the destination performs the same typed transformation after its own environment admission and records both the operation/context digest and resolved PATH in the immutable effective plan identity. Do not transport the caller's inherited PATH as an owned literal. The launcher remains the only semantic composer; the destination evaluates its admitted transform and the provider translates the resulting plan without recomposition. Until the tracked schema, consumer and provider reproduce this contract, refuse tracked requests for command capability. A resume must reproduce the pinned effective plan or refuse a changed destination context.

## Security considerations

The attacker controls the checkout, including instruction prose, filenames, symlinks, native config, hooks, plugins, skill commands, build inputs and files changed after review. They may attempt to select another checkout's context, exploit a nested CWD, inherit a global shim, replace a dispatcher, smuggle PATH through native settings, obtain broad MCP credentials or revive a revoked generation.

The trust boundary is operator approval → protected manager records/store → validated native adapter/launch plan → child process. Canonical paths and digests alone do not establish that boundary. Apply the existing protected activation rules, anchored no-follow reads, atomic publication and revalidation at execution. Do not use a fallback on unreadable, malformed or partially read state. Bind a context to manager, checkout identity, profile lock, environment, policy, snapshot and session; reject self-minted records and cross-project replay.

Appending preserves precedence but provides **no integrity guarantee** for earlier PATH entries or a writable appended directory. Protect the dispatcher and its artifacts from repository writes, and admit the base PATH separately. Also audit the command's own runtime launch behavior: the older portable command lane can prepend project/global directories (manager §3), and enforced script commands have a different boundary. The dispatcher must enter a context-bound protected activation lane, not just wrap an old shim that reintroduces the checkout's bin directory.

A manager-owned directory writable by the same unrestricted UID is not protection from an already executing hostile process. Strict-mode qualification must prove that the child, its native configuration loader and executable integrations cannot modify manager admission/store/dispatcher state; use an actual sandbox/process boundary where required. If only initial file discovery is controlled, describe that narrower property and do not claim hostile-code containment. Native `yolo`, unrestricted extensions or an unisolated same-user process cannot be made safe by chmod or hashing alone.

Instructions and knowledge can still contain prompt injection. Snapshotting makes their provenance stable; it does not make their advice safe. Tool permissions, process confinement and secret-scoped MCP access enforce capabilities independently of prose. Ordinary source reads may expose malicious text without converting it into trusted instructions. An adapter that cannot keep unadmitted control files from its automatic loading path cannot claim strict admission, even if those files appear absent at launch.

Credential values never enter declarations, composition records, digests of public outcomes or logs. Only opaque secret references and admitted environment names are recorded, resolved at the authorized destination with purpose-specific scope. Auth, session history, private knowledge and mutable memory are never published to a public board or packaged as research evidence. No credentials were inspected for this proposal.

## Compatibility and migration

Existing installations and profile locks remain valid. V1–v3 schemas remain byte-identical; older readers reject v4 and do not fall back. Command capability requires the new transport end to end. The old single-root `path_prepend` is not reinterpreted as append, and arbitrary `PATH`/project-root values do not enter the existing fragment `env` map.

Introduce a new closed manager configuration revision for registrations, item policy and legacy/enrolled state. Introduce separate schemas for project declarations, protected admissions, composition records, leases and v4 context/command members. Keep immutable content identity separate from lease identity: repeated launches can share a composition digest while each launch has its own lease, and the canonical fragment/plan hash includes whichever launch binding it transports.

Enroll projects by explicit preview/approval; import nothing automatically. Existing profile homes can continue to serve legacy launches. Project homes are provisioned lazily on an accepted strict launch preparation, with first-login and state-retention implications shown. Required unsupported surfaces fail with an actionable diagnostic; an optional item can be omitted only when that omission is in the approved record and effective preview. No silent conversion of a context-only adapter into full project support.

## Specification changes

Proposed normative text, subject to operator acceptance:

1. **Admission:** A manager MUST NOT treat repository-native configuration, instruction discovery, executable discovery or an on-repository approval record as launch authority. It MUST materialize only selected approved snapshot items, prove their effective policy and refuse unknown required semantics.
2. **Identity:** The manager MUST bind each composition to a registered checkout, selected profile lock, approved project generation and adapter contract. It MUST NOT mutate the selected profile or substitute machine-current as fallback.
3. **Native isolation:** Strict `off` and `admitted` modes MUST exclude unadmitted sources at startup, reload, nested file discovery, resume and child-agent entry points. A tool version whose boundary is unproven MUST refuse that strict capability.
4. **Concurrency:** Leased generated surfaces MUST remain unchanged. Updating a busy stable home MUST wait or refuse; collection MUST retain live or indeterminate leases and all referenced artifacts.
5. **Commands:** A v4 command environment MUST name one protected dispatcher and fixed append semantics. Launcher/provider discovery MUST exclude skill-published command locations and the dispatcher from `curator-*` provider selection. The selected owner map MUST govern every managed forwarder in the child PATH.
6. **Tracking:** The tracked launch plan MUST represent destination-side PATH append, bind the composition/lease, and hash the resolved effective plan. A consumer lacking this capability MUST refuse before creating a session or child.
7. **Secrets:** Imports, approvals and generated evidence MUST NOT copy credential bytes. Existing credential-mode prohibitions continue to apply.

Adopt decision records covering (a) project-context authority and stable-home/lease semantics, (b) typed command-environment v4 and tracked PATH evaluation, and (c) per-adapter certified source controls. Amend environments §§1–5 for declaration/admission/composition, §§7–8 for materialization and source suppression, §9.4 for command scope, §10 for fragments, §11 for provider refusal, §12 for control/status/GC; amend manager §§3/12 and Decision 0013's owned-literal transport. Correct the Pi trust notice and reconcile credential/Muse evidence through the existing erratum process rather than treating this draft as an erratum itself.

## Implementation plan

These are proposed leaves **after** operator acceptance and prioritization; no tasks or producers are scheduled by this research. Sizes are relative: S = one narrow contract/change; M = one subsystem; L = a cross-component slice that must be split before execution. No second general research prerequisite is proposed.

| Order | Leaf | Size | Reviewable exit |
|---|---|---|---|
| 1 | Spec decisions, closed declaration/admission/composition subset and fragment-v4 vectors | M | Freeze the smallest executable slice and refusal vocabulary; retain released schemas. |
| 2 | First vertical slice: registered project + approved context/skill command + Pi 0.84.2 source exclusions + manager resolve + direct curator-run | L | One real launch reads the approved snapshot and invokes its protected command; changed/untrusted repository sources do not activate. Unsupported MCP/permission items refuse. Split into bounded producer leaves at acceptance. |
| 3 | Stable home publication, session lease transfer, busy-update refusal, resume and GC | M | Concurrent projects cannot switch one another's surfaces; crash/detach cases retain correct state. Required before advertising concurrent use. |
| 4 | Dispatcher/activation lane, legacy forwarder migration and umbrella provider exclusion | M | Real command entry proves selected P→Y ownership and prevents repository-bin reintroduction. Required parts land with leaf 2, not afterward. |
| 5 | Tracked schema, destination environment evaluation and effective-plan identity | M | Direct/tracked equivalence for identical admitted destination input; unsupported consumer refuses. |
| 6 | Claude and Codex adapters, separately: full source exclusion and per-item re-admission | M each | Pinned native entry probes cover config, lazy context, skills, hooks/plugins, empty/nonempty MCP and permission atoms. Preserve approved authentication strategy. |
| 7 | OpenCode launcher/version contract; Muse launcher/version/target contract | M each | Establish actual native support first; required unknown surfaces remain refused. No adapter-name-only support claim. |
| 8 | Remaining rule dialects, MCP/permission atoms, knowledge and private memory; enrollment/status UX | M per dialect/surface | Per-item preview, approval, disable/revoke and negative vectors; no raw-config pass-through. |

Spec and implementation changes land in lockstep for each certified surface. The initial slice consumes this proposal directly once its decisions are accepted; platform probes belong to the implementing adapter leaves. The output of this research is a recommendation, not authorization to begin those leaves.

## Test plan

Use the repositories' existing Go tests and conformance-vector machinery. Drive the production paths: Curator resolve/materialization, `curator-run`'s `run`/`launch` composition, protected command dispatch, and tracked consumer start/resume. Native probes run in synthetic homes/checkouts without operator credentials; qualification requiring real login needs separately authorized disposable-account evidence.

| Family | Required positive and negative evidence | Narrowing mutant |
|---|---|---|
| Admission | Approved digest launches; changed bytes/dependencies, self-minted approval, optional-vs-required omission, malformed/unreadable manifest refuse correctly. | Bind only root file instead of transitive closure; trust same hash from another checkout. |
| Native discovery | Approved context/skill loads; unapproved ancestor/nested instructions, dynamic rules, settings, MCP, hooks, plugin resources and late-created files do not activate. Observe loader/tool behavior, not an LLM claim that it ignored a file. | Suppress only startup files; suppress config but leave rules/skills. |
| Composition | Same pin deduplicates; whole-skill replacement works; incompatible required provider, command collision and MCP same-ID conflict refuse. | Compare command names only in project, omitting profile or transitive providers. |
| PATH/dispatch | Base precedence, one append, duplicates and profile-only/null root; project P then selected Y; old singleton shims, symlinked dispatcher, missing PATH, hostile earlier entry, empty/relative segment and runtime re-prepend negatives. | Reject only direct `.agents/bin`, admitting a canonical alias or nested writable root. |
| Permissions/secrets | Approved grants within ceiling and added denies work; project bypass, secret-name widening, native PATH assignment, forbidden hooks and dialect ambiguity refuse. | Enforce global lock only on CLI flags, leaving imported native settings. |
| Leases/TOCTOU | Two projects on Y, two identical view sessions, busy update, revocation, detach, descendant, resume, crash and unknown liveness. No GC of referenced artifacts. | Key lease only by PID; release at launcher exit; collect on TTL alone. |
| Tracking | Same effective child environment at the destination, digest changes with composition/PATH/policy, replay and context substitution refuse before child creation. | Hash declared transform but omit resolved PATH or composition identity. |

Platform matrix: macOS and Linux for each qualified native version; Windows only after path separator, executable suffix, canonical path/reparse-point, case-folding, permissions and lease tests pass. OpenCode V1/V2 are separate rows. Claude login behavior is version/OS-specific. Record the number passed over the enumerated cases and the uncovered surfaces; an absent binary, skipped native test or failed read is not green coverage.

Research validation is limited to the file/source audit and P1–P6 in the companion. No product test suite was rerun and no implementation conformance is claimed.

## Open questions for the operator

1. **Home architecture and macOS login cost:** Accept A's persistent checkout × profile × environment home and potentially one initial login per home? **Recommend yes**, provision lazily and retain native state. If login reuse is mandatory, choose B with serialized differing project views; do not invent credential sharing. Revisit only against the outcome of TASK-261004-34brhn — research-claude-login-transfer-modes.
2. **Strict boundary versus existing behavior:** Require certified exclusion of unadmitted native sources for `off` and `admitted`, with typed refusal where unsupported? **Recommend yes**, while exposing existing unenrolled launches as legacy compatibility. Do not market a home change as repository isolation.
3. **Permission expansion:** Allow project permission requests at all? **Recommend default deny, explicit per-project `review` opt-in**, exact per-item approval within fleet/manager ceilings; preserve all hard denies and the existing permission-mode lock.
4. **Context replacement and memory:** May projects replace Y's root/system prompt or carry mutable memory? **Recommend additive context and memory off by default**, separately approved replacement, private per-view memory opt-in, and no auto-promotion of generated memory into admission.
5. **Busy view updates:** Wait for active leases or allocate a fresh home automatically? **Recommend wait/refuse**, reusing the stable home after it becomes idle. An explicit additional view may incur another login; never silently switch active sessions.
6. **Command conflicts and tracked transport:** Use one protected dispatcher, fail on stale/ambiguous earlier command owners, and refuse tracked capability until destination append exists? **Recommend yes**. Two raw append roots and caller-PATH literals do not meet the admission or identity boundary.
7. **Adapter delivery contract:** Accept a separately versioned optional capability whose certified environments/surfaces are advertised explicitly, with Pi as the first proposed direct slice? **Recommend yes**, with Claude/Codex next and OpenCode/Muse after their native contracts are established. All five remain in the design; an unsupported required feature refuses rather than being omitted.
