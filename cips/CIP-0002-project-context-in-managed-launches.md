# CIP-0002: Project context in managed launches

- **Status:** Draft
- **Owner:** orchestrator; decision: operator
- **Created:** 2026-10-04
- **Related:** TASK-261004-2asduq: launch-command-environment-fragment-design; STORY-261004-1ffwh8: design-launch-project-views; TASK-261004-34brhn: research-claude-login-transfer-modes; Decisions 0013, 0017, 0018 and 0019
- **Affects:** curator-spec environments §§1–5, 7–12; manager §§3, 5, 6, 10, 12; fragment and manager schemas; Curator, curator-run, agents-management and the tracked-session launch-plan consumer

## Operative summary

| Field | Contract |
|---|---|
| Purpose | Registered project context composed over a selected profile. |
| Boundary | Repository inputs are candidates; only protected, individually approved snapshots enter strict launches. Unaccepted candidate files remain untrusted review data; exact-candidate acceptance confers no control-context admission. |
| Authority owner | Operator approves within fleet/manager ceilings; manager owns registrations, admissions, compositions and leases; launcher owns composition. |
| Inputs → outputs | Registered checkout, selected profile lock, approved generation and adapter contract → protected view, metadata fragment and context-bound launch plan. |
| Phase | Draft; proposed for acceptance. Werkstatt home, trusted first wave and the leaf-1 candidate grammar are specified below; publication and qualification remain gates. |
| Normative links and proposed landing | [Environments §§1–5](../protocol/environments.md#1-environment-profiles-and-sources), [§10](../protocol/environments.md#10-resolution-and-the-launch-fragment), [Manager §12](../profiles/manager.md#12-agent-environments-manager-profile); amendments: [Specification changes](#specification-changes). |

R-TRANSFER review at stage T is the first required consumer of the strict-context boundary. The board first supplies exact-C diffs and blobs as inert, read-only resources bound by digest and placed outside every consuming harness's discovery roots, using the R-NET-TOOL task-resource path. This applies to reviewers, orchestrators reading C for rework and testers reading candidate data. No harness may automatically adopt candidate instructions, hooks, MCP servers, permissions, skills or executable discovery at startup, reload, nested discovery, resume or child-agent entry, before or after flagged-hunk acknowledgement. Acceptance of C is not admission of its control surfaces; activation remains a separate CIP-0002 control-context decision.

Materializing or entering an unaccepted candidate tree in a discovery-capable harness requires a qualified strict-context adapter, or equivalent exclusion of ambient candidate discovery, as that launch's admission gate. A tuple without that qualification cannot host such tree entry. Root-supplied surfaces alone do not establish exclusion. The flagged-hunk acknowledgement record must show that no automatic load preceded it; the inert-resource path satisfies this by construction. Data-only consumption still leaves semantic prompt injection as a review residual.

## Revision: accepted architecture-review findings (2026-10-13)

R-TRANSFER's inert exact-C resources are the first review consumer; discovery-capable candidate-tree entry waits for a qualified strict adapter. Verdict acceptance never admits control surfaces. The wider project-context direction remains open; no implementation or qualification is claimed.

## Operative disposition: Proposed for acceptance (2026-10-21)

**Status remains Draft.** This is the candidate text for owner acceptance,
not an Accepted CIP, published schema or implementation claim. The dated
owner decisions below supersede older recommendations where they conflict.

- **Decided:** The 2026-10-10 operator model remains in force. On 2026-10-18
  the owner selected option A, the persistent checkout × profile × environment
  home now called a Werkstatt, a repository overlay and sparse worktree,
  trusted mode first, manager-controlled permissions with default deny,
  explicit grants for agent changes, native memory off by default, busy-home
  wait/refusal, the checked D-PATH transform and inert foreign-candidate diffs.
- **First wave, updated 2026-10-21:** Claude Code, Codex and Muse together in
  the delivery plan. OpenCode and Pi remain in the design for later delivery.
  This replaces the old Pi-first ordering, not the qualification gates.
- **Certified delivery:** A separately versioned optional capability per
  environment advertises its certified surfaces. An unsupported required
  item refuses with a typed diagnostic. A home path or native trust flag is
  not certification. The [leaf-1 grammar](#leaf-1-candidate-grammar) fixes
  the proposed smallest slice; larger surfaces are explicitly deferred there.
- **Accepted companion directions, 2026-10-21:** Inline project Skillfile MCP
  declarations enter as individually approved, normalized-server-digest-bound
  items. The interim `launch-delegated/1` route composes the same approved
  Werkstatt context through the shared construction site; the later exact-plan
  route binds its snapshot and complete process instead.
- **Deferred, not unresolved architecture:** Multi-profile/stack execution,
  replacement root/system context, rule dialects, native settings, hooks,
  plugins, private-memory delivery, advanced commands and other platforms
  follow the first slice. Their accepted operator model is retained below.
  The remaining owner questions concern replacement and memory retention,
  not the chosen home, permission, PATH, adapter or review model.

[Cross-CIP contract, schema owners and versions](platform-contract-disposition.md)
remains the publication coordination register. This candidate does not widen
published fragments v4/v5 or any frozen carrier. Design disposition, schema
publication and native qualification are separate. Historical evidence below
has not been rerun.

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

## Operator decisions (2026-10-18 and 2026-10-21)

The owner answered the eight former questions on 2026-10-18, with the
first-wave correction and companion decisions on 2026-10-21:

1. **Home:** option A, persistent per checkout × profile × environment,
   named Werkstatt. Claude login uses setup-token through the separately
   admitted credential channel, not copied native login state.
2. **Workspace:** repository as an approved overlay in the Werkstatt home,
   with a sparse Werkstatt worktree outside the repository tree; trusted mode
   first. The worktree does not itself establish source exclusion or hostile
   code containment.
3. **Permissions:** default deny, managed programmatically for every harness.
   Agents change permissions only through protected grants within their
   ceiling. Project-shipped permission settings never apply.
4. **Memory:** native harness memory is off by default and requires an explicit
   opt-in parameter. Repository knowledge approval is not memory opt-in.
5. **Busy home:** update waits or refuses; it never changes leased surfaces.
6. **PATH:** D-PATH with its checked destination transform is accepted; skills
   and CLIs are scoped to the Werkstatt, not machine-current state.
7. **Adapters:** the owner updated the first wave on 2026-10-21 to Claude,
   Codex and Muse. OpenCode and Pi follow; all five remain in the design.
8. **Review:** R-TRANSFER shows a foreign candidate as an inert diff; accepting
   code never admits candidate control surfaces.

On 2026-10-21 the owner also accepted inline MCP in the project Skillfile as
an individually approved project contribution, bound to the normalized
`server` object digest. The companion draft, **MCP server declarations in the
project Skillfile**, is on branch `cip-mcp-in-project-skillfile`; this base has
no numbered main-branch entry for it, so this proposal refers to it by title.
It owns Skillfile parsing and server normalization, not launch authority.

The same date's accepted CIP-0016 amendment admits `launch-delegated/1` as an
interim local hosted route. [Launch route binding](#launch-route-binding)
states its different provenance and home guarantees without claiming that
its wire or the exact-plan successor is implemented.

## Summary

Compose individually approved project context, rules, knowledge, MCP servers,
skills and commands over selected profile Y in a persistent manager-owned
Werkstatt per checkout × profile × environment. Repository control files are
candidate inputs, never authority; native tools consume approved protected
copies while certified adapters exclude unapproved discovery. Permissions
come only from manager policy and grants, with default deny; project-shipped
permissions never apply. Native memory defaults off. The typed context,
lease and D-PATH transform bind one launch to that composition. Claude,
Codex and Muse are the first wave. The first slice is specified below for
acceptance review, with publication and runtime qualification still pending.

## Motivation and user stories

- An operator launches project X with profile Y and gets X's approved instructions, knowledge, skills and commands together with Y's base environment. Another project using Y must not inherit X's context, approvals or session state.
- A project can request its own MCP servers, AGENTS.md/CLAUDE.md equivalents and environment-specific rules; permission needs are proposals to the manager grant flow, never imported permission settings. The operator can enable a category, select individual items, inspect the effective result, and revoke them without editing Y.
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
- Managed credential isolation is not a sandbox. Decision 0017 keeps Claude/macOS shared mode unsupported and records evidence inconsistent with the older Keychain-suffix explanation. First login per distinct home is the supported planning assumption; the mechanism and transfer options remain under TASK-261004-34brhn: research-claude-login-transfer-modes, whose outcome was not yet available when checked. E7.

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
| **A. Persistent checkout × profile homes** | `environments/project-views/<checkout-id>/<profile>/<env>/`, with an immutable composition record and a stable native state/auth root. | Separates projects, approvals and memory; reuses a home's login; fits existing materialization/marker concepts; easy to explain. | More homes and storage; first login may recur per new home; generated surfaces cannot change while leased. Still needs native project-source suppression and OS protection of authority. **Selected 2026-10-18; called Werkstatt.** |
| **B. Composed view inside profile Y's existing home** | Select or rewrite a project composition at Y's native fixed paths; store records alongside Y. | Reuses existing login and configuration/state roots; smaller migration. | A config switch is visible to late reads by every session using Y. Safe only by serializing all differing project views on that home, or proving complete per-session native indirection. Shared trust/memory remain cross-project. A symlink swap does not solve this. |
| **C. Launch-time overlay** | Generate temporary files and pass explicit native flags/config roots for each launch; retain Y only for authentication where supported. | Immutable session inputs, simple cleanup ownership, natural plan identity. | Uneven native channels; root/rule/skill discovery often follows CWD independently. A new native home per run multiplies login cost; reusing Y can leak mutable state. Acceptable later for adapters with independently proven config/state/auth separation. |

None of these home layouts alone provides the hostile-repository boundary. The selected sparse worktree supports trusted-mode delivery; it is not evidence of a hostile-repository boundary. Native trust cannot replace individual admission or source-exclusion qualification.

### Recommendation

The [configuration publication figure](diagrams/configuration-publication.puml) shows the proposed admission, composition, lease and destination PATH boundaries, with the independent shell/settings lanes.

Option A was selected on 2026-10-18. Deliver it as an **optional, separately versioned project-context capability** per environment. Keep rc.14's existing environment capability intact. Release a strict adapter only when it can both exclude unadmitted native sources and expose the declared admitted surfaces; otherwise return a typed refusal for the requested capability.

#### Operator control surface

The following wider operator model includes deferred surfaces; only the
closed leaf-1 subset below is proposed for initial publication. These names
are not implemented CLI/config promises:

| Control | Semantics and default |
|---|---|
| `projects.<checkout-id>.context.mode` | Closed enum `off \| admitted`. New registrations default `off`: a certified launch admits profile context only and suppresses project-native discovery. `admitted` adds the selected project generation. |
| `context.environments.<env-id>` | Per-environment enablement. Enabling an environment does not enable all items. Unknown adapter or unsupported required item refuses. |
| `context.categories.<kind>` | Category ceiling for `context`, `rules`, `knowledge`, `mcp`, `skills`, `commands`, `native-settings`; default disabled until the operator selects it. Permission requests go to the separate manager grant flow, never an imported permission category. |
| `context.items.<id>` | `enabled \| disabled`, pinned digest and optionality. Newly discovered items remain unapproved. Exact item/closure approval is required, even inside an enabled category. |
| `context.project_grants` | `deny \| review`, default `deny`; `review` presents requests to the protected manager grant flow. Only manager-programmed grants change harness permissions; project permission bytes never apply and fleet denies remain binding. |
| `context.memory` | `off \| private`, default `off`; `private` requires an explicit opt-in parameter and a certified environment. Private mutable memory stays in Werkstatt state, separate from repository knowledge and admission; delivery is deferred beyond leaf 1. |
| Proposed `context inspect / preview / approve / revoke` | Discovery report, effective diff, explicit approval of its digest, and revocation. No preview executes or sources a file. A launch-time `--project-context=off` can narrow an admitted launch. |

Existing launches remain in an explicitly reported **legacy compatibility state** until enrolled; legacy means today's native discovery behavior, not `off` and not strict isolation. Fleet policy may require enrollment and refuse legacy launches. Unregistered checkouts never gain project context implicitly. This distinction prevents an “opt out” switch from silently re-enabling raw native repository settings.

#### Admission and composition

1. The manager binds an opaque checkout ID to a canonical root through its own registration operation, then proves launch CWD belongs to that registration. Nested registrations use the most specific **registered** containing root; ambiguity, a replaced root, unreadability or a moved checkout requires an explicit repair/rebind. Repository names, `.git` content and profile bytes cannot choose the registration or dispatcher path.
2. Discovery reads a bounded inventory as **untrusted data**, with no-follow/path-kind checks. It may offer imports of AGENTS/CLAUDE files, `.mcp.json`, native config, rules and knowledge; it never executes a parser hook, sources a shell file, fetches a referenced URL implicitly, installs a package or connects an MCP server.
3. Normalize into a closed, versioned declaration: stable item ID, kind, environment selector, scope/path applicability, immutable content or dependency digest, requested capability, dependencies, optionality and source provenance. Project permission settings are never imported. Other native config import accepts a named dialect and allowlisted fields; unknown/executable fields are rejected or shown as separate executable items. It is not a general JSON/TOML pass-through.
4. Snapshot candidate bytes and their transitive file references into the protected store. Resolve imports and finite glob matches at admission; reject escaping paths, cycles, symlinks/reparse points crossing the boundary, malformed reads and unbounded expansion. Pin every referenced knowledge file. Native auto-imports must resolve to those snapshots, never back into the checkout. Each approved executable uses the existing audit/build/activation contract.
5. Present an itemized semantic diff and a digest of the entire review package, including dependency changes, command owners, MCP endpoints/transports and permission effects. Record operator approval against manager identity, checkout ID, digest, allowed environments and policy ceiling. A hash is an identity, not proof of approval; a repository-supplied approval file is never authority.
6. Compose admitted project generation P over **selected profile Y's lock**. Identical skill pins deduplicate. A project replacement substitutes the entire same-identity skill, including its context, commands and providers; recheck every requirement against that replacement. Incompatible required providers and multiple skill identities exporting one command refuse. Hybrid inputs, if needed, must first become explicit admitted P members; do not inherit machine-current/hybrid state implicitly.
7. Build a **derived composition record**, never a replacement profile lock. Include Y lock hash, P/admission digest, environment/release contract, effective policies, ordered context modules, command-owner map, artifact digests and materialization hashes. Profile Y is not mutated. Edits in the repository create candidates for another review; they never update the active generation automatically. Launch reports the admitted generation and candidate drift; unreadable candidate state is “unknown”, not “unchanged”.
8. Before publication/launch, revalidate protected boundaries, approval status, materialized bytes and the CWD binding under the same transaction/lease discipline. Failure yields no fragment/child. A pure preview acquires no durable launch lease and starts nothing; a separate manager preparation operation binds a leased launch context.

#### Layer precedence, by surface

| Surface | Proposed composition rule |
|---|---|
| Root context | Retain Y's base context and system prompt. Add approved project-general context, then environment-specific project context in recorded order; deeper approved scope follows shallower scope. Leaf 1 is additive only; replacement of Y's root/system prompt is deferred pending the owner question below. Record precedence as intent, not a claim that an LLM enforces it. |
| Rules | Preserve kind and applicability. Support a bounded prose-rule subset: UTF-8 Markdown and explicitly parsed metadata for description, relative path globs and `alwaysApply`; environment-specific formats have separate dialect revisions. Cursor-style `.mdc` is an import format, not a new Cursor launcher adapter. Do not convert conditional rules into unconditional prose or turn execution-policy rules into advice. Unsupported semantics refuse or omit only explicitly optional items. |
| Knowledge | Approved immutable files, indexed under the managed view and loaded eagerly or by explicit reference as chosen per item. An instruction cannot escape the approved reference graph via a native import. Ordinary source reads remain untrusted task data, not newly admitted knowledge. |
| MCP | Union of approved profile/project servers. Same stable ID and digest deduplicates; a differing same-ID server requires explicit replacement approval, otherwise refuses. Pin executable/args or endpoint/transport and declared environment **names**. Manager policy bounds tool capabilities, network access and secret references. Empty means an explicitly enforced empty set. |
| Permissions | Default deny under fleet/manager ceilings and immutable denies. The manager programs each harness policy; agents can change it only through protected grants within their ceiling. Project-shipped permission rules, including restrictions, never apply. They may be displayed as inert requests for an independent manager grant. A legacy `native/yolo` transport constant is not authority to bypass this policy; an adapter unable to enforce it refuses. |
| Skills and shell commands | Whole-skill overlay and unique command ownership as above. Project P falls back to Y, never machine-current. Disabling a required skill/command/provider refuses composition rather than silently breaking a dependency. |
| Native settings and mutable memory | Allow only reviewed fields with known semantics. Deny auth stores, provider redirection, updater/download controls, PATH/home overrides, arbitrary hooks/plugins and shell initialization by default. Separate executable integrations need their own pinned admission. Runtime memory/approval writes cannot mint project admission or alter generated policy. |

Native trust flags approve a whole folder and may activate more than one of these surfaces. They cannot stand in for per-item manager approval.

#### Stable homes, leases and login

The selected Werkstatt uses a stable native home at `environments/project-views/<checkout-id>/<profile>/<env>/`, with generated surfaces recorded separately from native writable state. Immutable composition records live in a manager-owned records area; the fragment binds their content digest, not a mutable `current` alias. The exact native layout remains adapter-owned, including Muse's four XDG parents and OpenCode's parent/child shape.

The repository overlay contains only approved control items, projected into
this home. Its sparse Werkstatt worktree is outside the source repository
and manager authority/store roots. Bind the source checkout identity, sparse
selection and worktree identity to the composition; changes require explicit
preparation, not an automatic sync. Skills, their protected command artifacts
and CLIs belong to this Werkstatt. A native trust decision applies only to
this prepared worktree and never approves other items or grants permissions.
Exclude unapproved native control paths, including lazy nested discovery;
copying only some files is not a qualification result.

One home has at most one materialized composition while any session leases it. Concurrent launches may share the same composition only where the native adapter supports concurrent state access. Repair, profile switching, skill/CLI sync and any changed composition targeting this home wait for all old leases to end or refuse with proposed `project_view_busy` plus remediation to wait or end the owning session; it never swaps generated files beneath running sessions. Reuse the same home after an idle, transactional update to avoid a new login for each digest. Creating an additional separately named home is an explicit operator choice with its own login/state cost, not an automatic fallback.

Acquire the lease before the view can be collected and bind it to the launch context; transfer ownership to the actual tracked session/runner before the launching process exits. Detach and descendants retain it. Resume uses the recorded composition, not today's active generation. PID alone and elapsed TTL alone are insufficient proof of termination: recovery establishes process/session identity, and unknown liveness retains the lease. GC cannot remove leased homes, compositions or runtime artifacts. Revocation prevents new launches and new dispatcher admissions; already running native processes need an explicit stop/restart or an enforcing runtime channel. File replacement is not revocation of already loaded context.

Claude Werkstatt login uses setup-token through the admitted credential
source/channel, as decided on 2026-10-18. Follow the
[local setup-token source publication](../protocol/local-setup-token-source.md)
and the launcher's credential capability gates; token unavailability or expiry
refuses with its owning diagnostic, never copied native login or a silent
fallback. Other adapters retain their separately selected credential strategy.
No credential bytes enter project declarations, snapshots, leases or public
outcomes. This design performs no login or credential probe.

#### Project fragment and the command dispatcher

The original project proposal used the label `launch-env-fragment-v4`.
That label is historical: Muse now owns published v4 and the login/store and
Codex publication owns v5. Neither accepts new project members. The
[leaf-1 candidate grammar](#leaf-1-candidate-grammar) freezes separate project
members and their required vectors, historically called the fragment-v4
vectors. Coordinated publication must allocate an unused outer successor
and its required-understanding capability; this Draft does not reserve v6
or reinterpret any released carrier. Unsupported consumers refuse before
session creation. A context-only launch requires no command-dispatcher append; its CLI still
comes from the protected Werkstatt tool allocation, with the admitted tool
prefix applied by the shared launch construction site.

The original sketch's at-most-two project/global roots is rejected in favor of **one manager dispatcher directory**. The effective project-then-profile precedence lives in the protected owner map; it does not require two search roots. Forwarders execute a manager-owned dispatcher by absolute identity, which resolves the captured context/lease, revalidates protected activation and invokes the admitted runtime/artifact. Never execute `.agents/bin` or source `.agents/env.sh`, `.envrc`, profile shell bytes or repository hooks. Context references are lookups, not bearer authority; the dispatcher authenticates its managed session binding independently.

Migrate existing manager-owned singleton forwarders to dispatch through the same context binding, or refuse when an older forwarder would shadow the new view. Appending cannot outrank such a shim. For unmanaged earlier executables with an admitted command's name, report/refuse ambiguous ordinary-command availability and offer an explicit manager command invocation; never silently invoke the wrong skill. Reserve all `curator-*` names and add the dispatcher directory and aliases to umbrella provider-discovery refusals, even if placed in a configured provider trust root. E3, E10, P6.

D-PATH (accepted 2026-10-11) defines one managed-launch order: protected tool directory of this launch (CIP-0007), admitted base PATH of this user in its existing order, then one protected manager dispatcher directory. Project commands run through that dispatcher only after admission and execution checks; repository `.agents/bin` is never executed in a managed launch. Use the platform separator; deduplicate by identity and preserve the existing position of the manager dispatcher directory when it is already in the admitted base PATH, otherwise append it. Do not move an existing dispatcher entry to the tail. The protected launch tool directory remains first; the admitted base entries retain their order. The leaf-1 closed transform below preserves this accepted order; its publication remains separate from this Draft. Reject malformed/unreadable manager roots and ambiguous PATH entries required for command selection. If PATH is absent or excluded by the environment policy, refuse command capability rather than recreate an environment variable that admission removed. Leaf 1 refuses empty, relative, CWD-sensitive or repository-writable base components rather than guessing their intended authority. Absolute components still require protected destination admission and identity checks. Native settings may not subsequently replace PATH or shell initialization defeat the recipe. Claude `settings.env` and Codex `shell_environment_policy.set` are assignment surfaces, not append operators. D2, D5.

Apply the operation on the **admitted child PATH**, not the parent shell's PATH. In tracked mode the destination performs the same typed transformation after its own environment admission and records both the operation/context digest and resolved PATH in the immutable effective plan identity. Do not transport the caller's inherited PATH as an owned literal. The launcher remains the only semantic composer; the destination evaluates its admitted transform and the provider translates the resulting plan without recomposition. Until the tracked schema, consumer and provider reproduce this contract, refuse tracked requests for command capability. A resume must reproduce the pinned effective plan or refuse a changed destination context.

#### Leaf-1 candidate grammar

This is the closed design slice **proposed for acceptance**, not a published
JSON Schema. Leaf 1 must publish these definitions and positive/negative
vectors together before a producer emits them. It covers one registered
checkout, one selected profile, one environment, one approved generation and
one launch. Context, whole skills and inline MCP items are included. Source
exclusion, manager permissions, memory-off and leases are mandatory. The
optional command arm covers one protected skill command, not arbitrary scripts.

**Common encoding and bounds.** JSON objects reject duplicate/unknown members,
invalid UTF-8, trailing input and unknown versions. All listed members are
required unless marked optional; null never means absent. ID is
`[a-z][a-z0-9_-]{0,63}`. REF is `TAG:ID`, at most 96 ASCII bytes, where TAG is
one of `registration`, `snapshot`, `approval`, `composition`, `lease`, `home`,
`worktree`, `policy`, `adapter`, `session`, `principal`, `grant`, `tool`,
`dispatcher`, `command` or `lock`. A REF resolves only in protected manager state,
never as a path, URL or bearer credential; its tag must match the field.
HEX is exactly 64 lowercase hexadecimal characters. All manager refs are
scoped to the issuing manager and immutable allocation identity; the same
text from another manager conveys no authority. Record identities use SHA-256
of CCJ-1 bytes without a trailing LF, excluding no member. A record does not
contain its own digest. Arrays preserve order unless explicitly
sets; sets are unique and sorted by UTF-8 bytes. Bound each record to 1 MiB
and depth 16, with at most 256 items per generation and 256 bytes per
ordinary string unless a referenced owning schema provides its own bound.
Absolute root paths are bounded to 4096 UTF-8 bytes and validated through
retained filesystem identity, not a lexical prefix alone.

| Object | Closed members and meaning |
|---|---|
| Registration | `kind: "project-registration/1"`, `checkout_id: ID`, `project_root: absolute path`, `root_identity: HEX`, `profile: {name, lock_sha256}`, `environment: ENV`, `home_ref: REF`, `worktree_ref: REF`. ENV is `claude_code`, `codex_cli` or `muse` in this slice. Profile name uses the existing profile grammar; lock digest is HEX. `root_identity` hashes the closed binding defined below, retained privately; re-registration/replacement cannot retain old authority merely by reusing a path. Home and sparse worktree are protected manager allocations outside the source tree. |
| Item | `kind: "project-item/1"`, `id: ID`, `type: "context" \| "skill" \| "mcp"`, `environment: ENV`, `required: boolean`, `payload: PAYLOAD`. A context payload is exactly `{snapshot_ref, snapshot_sha256, lock_ref, lock_sha256}`; a skill payload remains exactly `{snapshot_ref, snapshot_sha256}`. Context lock references have tag `lock`, and their digest is HEX. MCP payload is exactly `{name, server, server_sha256}` as described below. No raw native-settings, permission, hook, plugin or shell arm exists. |
| Approval | `kind: "project-approval/1"`, `checkout_id`, `item_id`, `item_sha256`, `environment`, `approver_ref`, `ceiling_sha256`, optional `grant_ref`. IDs, HEX and tagged refs follow the common types. An agent approver requires a live manager-issued grant covering this exact act and ceiling; a human approval cannot exceed hard denies either. The protected revocation ledger is checked at preparation/start and dispatch; the repository cannot mint approval. |
| Generation | `kind: "project-generation/1"`, `registration_ref`, `registration_sha256`, `items: [{item_id, item_sha256, approval_ref}]`. References have the matching tags. Item IDs are unique; this ordered list is the admitted rendering order. Every item must match checkout, profile policy and environment, and have current approval. No implicit filesystem discovery contributes extra members. |
| Composition | `kind: "project-composition/1"`, `registration_ref`, `registration_sha256`, `generation_sha256`, `profile: {name, lock_sha256}`, `environment`, `adapter_ref`, `adapter_sha256`, `policy_ref`, `policy_sha256`, `memory: "off"`, `home_ref`, `worktree_ref`, `materialization_sha256`, `command_owners: [{name, item_id, artifact_sha256}]`, `omitted: [{item_id, reason}]`. Generation bytes are retained under their digest in protected state. Owner names use the existing command grammar, are unique, and bind full audited artifacts, never checkout executables. `item_id` names the selected effective skill from the approved generation or selected profile lock; at most one exported command is enabled in this slice. Omission reason is `disabled` or `unsupported` and requires approved optionality/effective preview; required items cannot be omitted. The policy reference names protected manager-programmed harness policy with default deny and only effective granted permissions, never a repository permission payload. |
| Lease binding | `kind: "project-lease/1"`, `lease_id`, `context_ref`, `context_sha256`, `checkout_id`, `environment`, `home_ref`, `owner_ref`, `session_ref`, `generation`. Generation is a positive integer at most 2^53-1. Owner is a principal reference; session is reserved before composition. The immutable tuple binds a specific composition and session generation. State and liveness are stored separately, not rewritten into this digest. |
| Fragment members | Required `project_context: {version: 1, mode: "off" \| "admitted", context_ref, context_sha256, project_root, lease_ref}`; optional `command_environment: {version: 1, operation: "checked-d-path/1", tool_ref, dispatcher_ref, context_ref, context_sha256}`. Context refs name the same protected composition. Project root must equal its registration. `off` has no project items but still requires certified source exclusion. No arbitrary environment map, append list or executable command text is accepted. Command members require a command-certified adapter and cannot coexist with `path_prepend`. |

The root binding is exactly `{repository, filesystem}`. `repository` is the
closed workspace-trust repository object (`root`, `primary_remote`,
`root_commit`), including its specified null-remote case. `filesystem` is
exactly `{device, inode}`, each a canonical unsigned decimal string, no
leading zeros except `0`, at most 20 digits and at most 2^64-1. Both native
identities and repository binding must still match at use; replacing a root
with equal Git metadata cannot reuse the old registration. This slice's
macOS/Linux filesystem binding does not allocate a Windows identity grammar.

The referenced context/skill snapshot manifest is closed:
`{version: 1, files: [{path, size, sha256, mode}]}`. Paths are unique sorted
portable relative paths, with no absolute/dot/parent/empty segments, links,
case/normalization aliases or file/ancestor collisions. Modes are `0600` or
`0700`; size is the exact nonnegative integer byte count. Caps are 10,000
files, depth 32, 240 UTF-8 bytes per path, 16 MiB per file and 64 MiB total.
The manifest digest covers its canonical bytes; verify the complete entry
set, bytes, sizes and modes, not only an asserted manifest hash. References
and imports must close over this inventory. A skill snapshot also passes
the existing whole-package manifest, pin, audit and activation contracts;
this slice does not admit an arbitrary directory as an executable skill.

**Context package inheritance.** A context item is the snapshot of one selected
context-package root, not an arbitrary Markdown directory. Its root contains
`agent-context.json` conforming to the existing
[context manifest schema 2](../schemas/rc7-carriers-v1/agent-context-v2.schema.json),
including the selected-root rules of
[environments §2](../protocol/environments.md#2-context-package-shape) and
[CIP-0021](CIP-0021-profile-skill-directories.md). Only the manifest's explicit `context.modules` list selects package-local
modules; each path names a regular file below that package's `context/`
directory. Leaf 1 requires `context` at this selected root; an umbrella with
no local modules declares `context: {modules: []}` explicitly. No filename, directory scan or adapter preference chooses
an entry. Files not selected as applicable modules remain inert snapshot/audit
content; the same file cannot be declared twice, including once in each role
`root` and `system`. Duplicate JSON keys, including duplicate `class`, refuse.

The item inherits context-package validation, root and module selection,
environment selectors, default/root/system classes, module order, effective
weights, topological tie order, system-module admission and exact byte/rendering
rules from [environments §§3–6](../protocol/environments.md#3-context-modules).
Modules are opaque UTF-8 Markdown with LF endings and exactly one trailing LF;
no normalization, templating or inclusion is performed. Every selected module
must exist inside the complete immutable snapshot at its manifest path, without
symlink traversal or path aliasing. A bare `AGENTS.md` or other instruction
file without the manifest is not admitted in leaf 1. An operator may explicitly
package such bytes with a manifest before preview and approval; the manager
never synthesizes an unapproved entry selection.

`lock_ref` names the manager-resolved, retained
[context lock schema 4](../schemas/rc7-carriers-v1/context-lock-v4.schema.json),
with the existing [lock identity rules](../protocol/environments.md#13-the-lock-is-the-identity).
The lock's `root` names this selected package; its root pin must match the
verified snapshot bytes. The lock lists the complete resolved context closure,
including exact source, selected directory, pin, version, effective weight,
requirer and overlay records. Each member resolves to its verified protected
store snapshot under environments §4, never today's checkout or an unpinned
fetch. Apply the owning content-hash framing to pins; the inventory's CCJ-1
`snapshot_sha256` is a separate digest and cannot substitute for a content pin.
`lock_sha256` is the unprefixed HEX of SHA-256(CCJ-1(lock)), without LF; the
owning lock spelling adds `sha256:` when required. The recorded precedence
must equal the selected profile's protected precedence. Retain the manifest,
lock and complete pinned closure before approval; preparation never implicitly
re-resolves it. Unknown, missing, stale or inconsistent lock/member evidence
refuses before materialization.

For this slice the context item's lock contains context members only.
In every closure member, non-empty `requires.skills` or `requires.mcp` and
non-empty `codex_settings` are refused: context approval cannot activate a skill, MCP server or native
setting. Whole skill and inline MCP items keep their separate approvals.
The inherited lock carries empty `codex_settings` and
`codex_settings_contributions`; context requirements, weights and their owning
conflict checks remain supported. At least one applicable root module must
exist in the pinned context closure for this item's environment; an umbrella
with an explicit empty module list may select it through its declared
requirements, never discovery. A root with no `context` contributes no root
surface under the inherited contract and is refused as a leaf-1 context item.

Within each item, render the pinned closure in `monolithic` form using
environments §5's exact header, chapter, module and LF-joining rules, with the
lock's root/pins/precedence and the selected environment. Applicable root
modules follow manifest order within each package; package weights and
topological ties follow the inherited emitted order. System modules use only
the separately admitted environments §5.5/§7.3 channel and its exact bytes;
they are never promoted into root context. The generation's ordered item list
still orders project items: append each rendered root-context document after
the base profile's document, with exactly one additional LF between non-empty
documents. Append admitted system parts in the same item order using the owning
part-joining rule. An adapter that cannot reproduce these additive outputs
refuses rather than selecting a different entry or replacing base context.

Native import directives are not an entry-selection or support-file mechanism
in leaf 1. A construct the qualified adapter would follow as a control-file
import refuses, even if its target is inventoried; in particular an import
outside the pinned closure cannot cause a native read. Ordinary prose references
remain opaque data, not a discovery grant. Future import dialects need a separate
closed contract and qualification; no adapter may infer one here.

The approved item digest covers `snapshot_sha256` and `lock_sha256` through its
closed payload. The inventory includes the exact `agent-context.json` bytes;
the lock binds every transitive manifest and module through its content pins.
Changing selected root, `context.modules` paths/order/classes/selectors,
weights, a closure member, or any supporting bytes changes the snapshot and/or
lock digest, hence the item digest and required approval. A later output hash
cannot retroactively approve an entry choice. For example, with distinct files
`context/entry.md` and `context/reference.md`, a manifest selecting only the
first and a manifest selecting only the second are two items with different
snapshot/item/approval bindings and different rendered module bytes. Keeping
one approval while changing that manifest is `project_item_unapproved`; missing
or changed stored bytes under an already approved digest is
`project_context_drift`, never a new baseline.

The composition's `materialization_sha256` covers a closed control receipt:
`{version: 1, files, adapter_sha256, policy_sha256, worktree_ref}`. `files`
uses the same complete sorted file-entry grammar above, for generated
agent-visible control outputs only, relative to the Werkstatt home. Mutable
native state, credentials and the ordinary source worktree are not control
files. Verify outputs against the receipt and qualified source-exclusion
contract before start; the receiver cannot bless changed files by replacing
this baseline. The receipt and its hash contain metadata, not credential bytes.

**Inline MCP.** NAME and SERVER reuse the companion **MCP server declarations
in the project Skillfile** grammar and environments §2.2: SERVER has exactly
`transport`, either `command`/`args` for `stdio` or `url` for `http`, and
optional `env_names`/`environments`. All owning bounds and secret-name rules
apply. Expand URL shorthand; set absent `env_names` to `[]`; sort unique
names and explicit environments; preserve argument order and scalar bytes;
leave absent `environments` absent. `server_sha256` is `sha256:` followed by
SHA-256 of CCJ-1 of that normalized SERVER, without LF. Approval binds
(checkout identity, NAME, normalized server digest); the item approval also
binds its environment, required flag and effective policy. Changing an
endpoint, argument, environment name or selected environments needs new
approval. Renaming or moving the item cannot replay it. Raw manifest and
normalized declaration digests remain separate. Writer-local `install`
options have no authority in this slice; an option affecting control
configuration must be separately specified/approved or refuse.

**Lease state machine.** Preparation creates `prepared` before publishing a
fragment. Durable transfer to the reserved session/runner creates `active`
before provider start; detached sessions and descendants retain that owner.
A failed pre-start preparation releases only after absence of a started child
is established. `active` becomes `released` only on authoritative confirmed
termination. Interrupted recovery enters `unknown`, which retains the home
and artifacts; it can become `active` or `released` only through session and
process-generation reconciliation. Neither PID reuse nor TTL alone releases
a lease. Resume checks the original binding and current authority; failure
cannot become a new launch. An idle update is transactional and rechecks
lease state before publication; a concurrent acquisition cannot race a write.

**Checked destination transform.** Resolve tool/dispatcher refs to protected
Werkstatt directories at the destination, after child-environment admission.
Reject missing/excluded PATH, unreadable roots, identity aliases between the
two roots, unsafe base components and stale command owners. Prepend the
protected tool directory exactly once. Deduplicate base entries by filesystem
identity while retaining their first admitted order; retain a dispatcher
already among them at that position, otherwise append it once. Never import
the caller's PATH literal or a repository command root. Record the context,
lease, transform and actual resolved PATH in the effective launch identity;
exact-plan mode covers them with the complete process digest. Native settings
or shell initialization cannot replace the result. Profile-only/null-root
transforms and general remote/tracked transport are deferred, not guessed.

**Certified adapter delivery.** A protected capability record is exactly
`{kind: "project-adapter/1", environment, provider_version, platform, surfaces}`.
Platform is `macos` or `linux` for the first slice; provider version is an
exact bounded release string, not a range. Surfaces are a set drawn from
`context`, `skills`, `mcp`, `commands`, `permissions`, `memory-off`,
`native-source-exclusion`. Capability advertisement is optional per environment
and bound to real qualification on that release/platform. Every first-slice
launch requires `permissions`, `memory-off` and `native-source-exclusion`,
plus every required selected surface. No environment borrows another's result.

For Claude, Codex and Muse independently, exclusion qualification covers
ancestor/current/nested instructions, config and permission files, native and
compatibility skill roots, MCP, hooks/plugins, auto-memory and late discovery,
including reload, resume and child entry. Re-admit only protected selected
context/skills/MCP; enforce an explicit empty MCP set where none is approved.
An unsupported required surface refuses even if an install report says
`skipped: unsupported`. Trusted mode is the first delivery target; this loader
boundary does not claim containment of hostile same-user executable code.

| Proposed refusal | Exact trigger and preserved effect |
|---|---|
| `project_context_invalid` | Malformed/duplicate/unknown fields, invalid refs, closed enums or bounds, inconsistent context/lease/roots or forbidden PATH arm. No fragment, child or partial publication. |
| `project_registration_mismatch` | Missing/replaced/moved checkout or CWD/worktree outside its registered binding. No substitution of another project/profile. |
| `project_item_unapproved` | Missing, revoked, wrong-project/item/environment approval or insufficient approver grant/ceiling. No native write, MCP connection or provider start. |
| `project_context_drift` | Changed/missing snapshot entry, policy, adapter contract, protected composition or digest. No repair or baseline update during launch. |
| `project_context_unreadable` | Failed read of required authority, inventory, PATH or liveness evidence. Never treat this as absence/optional omission. |
| `project_context_unsupported` | Missing certified environment/surface, non-enforcing permission or memory adapter, or unsupported required route/consumer. No omission of required items or downgrade to legacy/native. |
| `project_view_busy` | Repair, profile switch, sync or update while a home has a live/unknown lease. Wait or refuse before writes; remediation identifies the owning session and advises waiting/ending it. |
| `project_lease_mismatch` | Wrong owner/session/generation, stale lease, release replay or invalid transition. No new session or lease takeover. |
| `project_path_refused` | Missing/excluded/unsafe PATH, invalid protected roots, command shadowing or stale/ambiguous owner. No PATH reconstruction or wrong executable. |

These names are proposed for joint diagnostic-registry publication with leaf
1; no exit numbers or new members are smuggled into an existing registry.
Before any authority lookup, old/unsupported outer carriers retain their own
published version refusal. The new code applies only after project-capability
negotiation. Every failure preserves existing home/approval state and emits
no success fragment; permitted refusal telemetry is redacted.

**Required fragment-v4 design vectors.** These names retain the historical
project design label, not permission to modify published fragment v4. Each
positive has a nearby negative and a narrowing control for the future checker:

| Vector family | Positive control and negative witness | Narrowing control that must fail |
|---|---|---|
| `ProjectRegistrationBinding` | Valid registered checkout/profile/ENV prepares; replaced root, nested foreign registration and worktree substitution refuse. | Compare root strings only, ignore retained identity. |
| `ProjectItemApproval` | Approved context and complete skill snapshot load; wrong-project replay, changed transitive asset and revoked/absent approval refuse. | Check only root content or item name. |
| `ProjectContextSelectionBinding` | Two valid schema-2 packages inventory the same two distinct Markdown bodies but select different root modules in their manifest; snapshot/item digests and approval bindings differ, and each materializes only its selected bytes. A changed selection under the old approval refuses. | Omit manifest bytes from inventory identity or check only Markdown bodies; permit one approval for both selections. |
| `ProjectContextPackageValidation` | Valid manifest/lock and complete context closure load in inherited order; missing manifest/module, outside-snapshot entry, native import escaping the closure, invalid UTF-8/LF, duplicate path/role or duplicate class key refuse before output/native reads. An inside-closure native import also refuses; a declared second module is the positive alternative. | Infer entries by filename, deduplicate conflicting roles, normalize bytes or let native includes discover support files. |
| `ProjectContextClosureRendering` | Pinned context requirements, weights and topological ties reproduce environments rendering; changed root/directory/module order/weight/member pin needs re-approval. A mismatched or unavailable lock and nested skill/MCP/settings activation refuse without re-resolution. | Hash only the selected package, ignore the lock/ordering, or inherit unapproved side effects through context requirements. |
| `ProjectInlineMCP` | URL/expanded SERVER normalize identically and approved server loads; endpoint/arg/env/NAME changes, unapproved server and raw install authority refuse. | Hash URL only or trust raw Skillfile approval. |
| `ProjectSourcesClaudeCodexMuse` | Each runtime loads approved home context/skill and explicit MCP set; planted ancestor/nested/late instructions, skills, hooks, permissions, plugins and memory do not activate. | Suppress startup only or only one runtime. |
| `ProjectPermissionsAndMemory` | Manager grant within ceiling is enforced; project allow/deny settings and implicit memory opt-in never apply. | Let native project permissions or memory override the manager. |
| `ProjectLeaseLifecycle` | One prepared/active launch retains its home across detach/resume; busy repair/switch/sync, PID reuse, stale generation, unknown liveness and TTL-only collection refuse without writes. | Release at caller exit or key by PID alone. |
| `ProjectDestinationPATH` | Tool/base/dispatcher order, existing dispatcher position and identity dedup match D-PATH; absent/relative/writable PATH and command shadowing refuse. | Use caller PATH or always move dispatcher to the tail. |
| `ProjectLaunchRoutes` | Same admitted Werkstatt tuple composes through delegated and exact-plan routes under their own capabilities; changed fragment, missing route understanding and failed resume refuse. | Drop the project binding or claim a delegated pin proves snapshot isolation. |
| `ProjectClosedGrammar` | Minimal valid records and context-only launch pass; unknown fields, duplicate keys, nulls, excessive bounds and project fields in frozen v4/v5 refuse. | Accept unknown fields or parse before version negotiation. |

**Explicitly deferred.** Multi-profile alternatives/stacks and profile-only
launches; cross-account/remote/tracked transform carriers; simultaneous
same-home writers; replacement root/system context; conditional rule dialects,
mutable knowledge/private-memory delivery; native settings/hooks/plugins;
permission-file import (forbidden, not a future authority source); multi-command
and generic executable integrations; OpenCode and Pi adapters; Windows and
bare instruction-file items without a context manifest, native context-import
dialects, and new provider/platform qualification. The 2026-10-10 broader model remains the
design target, with no implicit activation of these deferred arms.

#### Launch route binding

The approved Werkstatt composition is selected before either route. Resolve
the selected profile plus approved project generation, acquire its home lease,
and use the same agents-management construction site. The project-capable
fragment names the leased Werkstatt home, not a shared machine-current profile
home. Unsupported home indirection or source exclusion refuses; it does not
silently launch against the base profile alone.

On the **delegated route**, curator-run resolves the profile/fragment,
model/effort, permissions, system-prompt opt-in, typed resume and credential
intent, then sends the closed request. The manager's caller-side component
composes using the leased Werkstatt home and certified adapter; it checks
its fragment digest against the request and changes no resolved value,
adds no unapproved profile content and enables no Remote Control. The
project tuple must be conveyed or securely bound by curator-run's own
required-understanding contract before this route advertises project support;
this CIP does not add private fields to `launch-delegated/1` requests/records.
A shared-profile-home-only consumer is unsupported for a Werkstatt launch.
The route retains live-home/profile-pin/fragment-digest provenance, not
CIP-0014 snapshot isolation. This CIP's selected busy-Werkstatt lease rule
protects cooperating updates; it does not relabel CIP-0016's proposed general
home-lease/exclusive-profile conditions as accepted or protect arbitrary
same-user mutations.

On the **exact-plan route**, the caller materializes the approved content
through the [CIP-0014](CIP-0014-managed-home-snapshots.md) contract into the
reserved session home and composes the full process before sealing it.
Bind the Werkstatt tuple, lease, snapshot/manifest, policy overlay and resolved
PATH in that process identity. The host executes the admitted process and
never composes or repairs it. Snapshot support for the approved project
inventory, native-state placement and source exclusion must be qualified;
there is no raw home-copy fallback. The original Werkstatt remains leased
until the session's authority/state ownership is reconciled on termination.

[CIP-0016](CIP-0016-local-hosted-launches.md) owns the hosted direction.
Its amendment accepted 2026-10-21 activates delegated support per runtime,
Claude/Codex first and Muse after the manager's v4 consumer is qualified.
This is distinct from published fragment-v4 and the project design vector
label. The project first-wave plan covers Claude/Codex/Muse, but each row
still requires its project capability and route qualification; no test-only
or unsupported row is advertised. The joint three-runtime exact-plan release
gate remains. Retirement is per manager/runtime when exact-plan with detach
is advertised; detached launches retain delegated until exact detach exists.
Typed resume never creates a session; any hosted refusal has no native fallback.

## Security considerations

The attacker controls the checkout, including instruction prose, filenames, symlinks, native config, hooks, plugins, skill commands, build inputs and files changed after review. They may attempt to select another checkout's context, exploit a nested CWD, inherit a global shim, replace a dispatcher, smuggle PATH through native settings, obtain broad MCP credentials or revive a revoked generation.

The trust boundary is operator approval → protected manager records/store → validated native adapter/launch plan → child process. Canonical paths and digests alone do not establish that boundary. Apply the existing protected activation rules, anchored no-follow reads, atomic publication and revalidation at execution. Do not use a fallback on unreadable, malformed or partially read state. Bind a context to manager, checkout identity, profile lock, environment, policy, snapshot and session; reject self-minted records and cross-project replay.

Appending preserves precedence but provides **no integrity guarantee** for earlier PATH entries or a writable appended directory. Protect the dispatcher and its artifacts from repository writes, and admit the base PATH separately. Also audit the command's own runtime launch behavior: the older portable command lane can prepend project/global directories (manager §3), and enforced script commands have a different boundary. The dispatcher must enter a context-bound protected activation lane, not just wrap an old shim that reintroduces the checkout's bin directory.

The first slice is trusted-code delivery: the operator authorizes worktree
code under manager-programmed grants, while strict control-source admission
still excludes unapproved automatic loading. It does not claim hostile-code
containment. A manager-owned directory writable by the same unrestricted UID
cannot protect against an already executing hostile process. A later mode
claiming that protection must prove that the child, its native loader and
executable integrations cannot modify manager admission/store/dispatcher
state, using an actual sandbox/process boundary. Startup-only discovery
suppression, native `yolo` or chmod/hashing alone cannot establish it.

Instructions and knowledge can still contain prompt injection. Snapshotting makes their provenance stable; it does not make their advice safe. Tool permissions, process confinement and secret-scoped MCP access enforce capabilities independently of prose. Ordinary source reads may expose malicious text without converting it into trusted instructions. An adapter that cannot keep unadmitted control files from its automatic loading path cannot claim strict admission, even if those files appear absent at launch.

Credential values never enter declarations, composition records, digests of public outcomes or logs. Only opaque secret references and admitted environment names are recorded, resolved at the authorized destination with purpose-specific scope. Auth, session history, private knowledge and mutable memory are never published to a public board or packaged as research evidence. No credentials were inspected for this proposal.

## Compatibility and migration

Existing installations and profile locks remain valid. All published fragment versions, including v4/v5, remain byte-identical; older readers reject a project-capable successor and do not fall back. Command capability requires the new transport end to end. The old single-root `path_prepend` is not reinterpreted as append, and arbitrary `PATH`/project-root values do not enter the existing fragment `env` map.

Introduce a new closed manager configuration revision for registrations, item policy and legacy/enrolled state. Introduce separate schemas for project declarations, protected admissions, composition records, leases and the separately published project context/command members. Keep immutable content identity separate from lease identity: repeated launches can share a composition digest while each launch has its own lease, and the canonical fragment/plan hash includes whichever launch binding it transports.

Enroll projects by explicit preview/approval; import nothing automatically. Existing profile homes can continue to serve legacy launches. Project homes are provisioned lazily on an accepted strict launch preparation, with first-login and state-retention implications shown. Required unsupported surfaces fail with an actionable diagnostic; an optional item can be omitted only when that omission is in the approved record and effective preview. No silent conversion of a context-only adapter into full project support.

## Specification changes

Proposed normative text, subject to operator acceptance:

1. **Admission:** A manager MUST NOT treat repository-native configuration, instruction discovery, executable discovery or an on-repository approval record as launch authority. It MUST materialize only selected approved snapshot items, prove their effective policy and refuse unknown required semantics.
2. **Identity:** The manager MUST bind each composition to a registered checkout, selected profile lock, approved project generation and adapter contract. It MUST NOT mutate the selected profile or substitute machine-current as fallback.
3. **Native isolation:** Strict `off` and `admitted` modes MUST exclude unadmitted sources at startup, reload, nested file discovery, resume and child-agent entry points. A tool version whose boundary is unproven MUST refuse that strict capability.
4. **Concurrency:** Leased generated surfaces MUST remain unchanged. Updating a busy stable home MUST wait or refuse; collection MUST retain live or indeterminate leases and all referenced artifacts.
5. **Commands:** A project-capable command environment MUST name one protected dispatcher and fixed append semantics. Launcher/provider discovery MUST exclude skill-published command locations and the dispatcher from `curator-*` provider selection. The selected owner map MUST govern every managed forwarder in the child PATH.
6. **Tracking (deferred after the first slice):** The tracked launch plan MUST represent destination-side PATH append, bind the composition/lease, and hash the resolved effective plan. A consumer lacking this capability MUST refuse before creating a session or child.
7. **Secrets:** Imports, approvals and generated evidence MUST NOT copy credential bytes. Existing credential-mode prohibitions continue to apply.
8. **Permissions and memory:** Harness permissions MUST be programmed by the manager with default deny; agent changes MUST require protected grants within ceilings. Project-shipped permissions MUST NOT apply. Native harness memory MUST remain off absent explicit opt-in; the first-slice grammar supports off only.
9. **Routes:** A delegated caller-side composer MUST preserve the approved Werkstatt binding without claiming snapshot provenance. An exact-plan host MUST consume the covered snapshot/process without recomposition. Missing required route understanding MUST refuse before launch.

Adopt decision records covering (a) project-context authority and stable-home/lease semantics, (b) typed command environment and tracked PATH evaluation, and (c) per-adapter certified source controls. Amend environments §§1–5 for declaration/admission/composition, §§7–8 for materialization and source suppression, §9.4 for command scope, §10 for fragments, §11 for provider refusal, §12 for control/status/GC; amend manager §§3/12 and Decision 0013's owned-literal transport. Correct the Pi trust notice and reconcile credential/Muse evidence through the existing erratum process rather than treating this draft as an erratum itself.

## Implementation plan

These leaves follow owner acceptance and prioritization, not this Draft's
filing. Sizes are relative; cross-component slices are split before execution.
The first delivery wave is Claude, Codex and Muse, with no implementation or
native qualification claimed by this table.

| Order | Leaf | Size | Reviewable exit |
|---|---|---|---|
| 1 | Publish the leaf-1 closed grammar, diagnostic registry and project fragment vectors | M | Exact member schemas, canonical positive/negative bytes and narrowing controls match this candidate; coordinate a new outer carrier without changing published v4/v5. |
| 2 | Werkstatt registration, protected item admission and persistent home/sparse worktree preparation | M | One checkout/profile/environment generation and approved context/skill/MCP inventory; no raw project permissions, credential copying or implicit item approval. |
| 3 | Werkstatt lease transfer, busy-update refusal, resume and recovery | M | Acquire before publication/start; repair/switch/sync wait/refuse; detach and unknown liveness retain state. This precedes the first hosted launch. |
| 4 | Claude, Codex and Muse source-exclusion and re-admission adapters, in the first wave | M each | Each real entry point qualifies instructions/config, skills, hooks/plugins, MCP, manager-programmed permissions and memory-off for its exact release/platform; required unsupported surfaces refuse. Claude setup-token uses its owning admitted channel. |
| 5 | Protected Werkstatt tools/skills, checked D-PATH and command dispatch | M | One admitted skill command binds full artifact/owner identity; legacy shadowing, repository bins, unsafe PATH and provider discovery refuse. Required parts precede any command-capable launch. |
| 6 | One direct/hosted launch with the approved Werkstatt tuple | M per runtime/route | First wave has Claude/Codex/Muse rows. Delegated caller composition and later exact-plan snapshot execution obey the route binding above; version/capability mismatch and resume failure never downgrade. |
| 7 | Tracked destination transform and complete effective-plan transport | M | Later closed carrier and consumer qualify identical admitted destination behavior; absence refuses tracked command capability. |
| 8 | OpenCode and Pi delivery | M each | Later native/version contracts and source exclusions qualify independently; neither disappears from the design or substitutes for first-wave rows. |
| 9 | Deferred stacks, rule dialects, replacement/memory decisions and advanced surfaces | M per surface | Separate owner disposition where required, per-item grammar, preview/revocation and negative qualification; no general native-config pass-through. |

Schema, consumer and real adapter checks gate each advertised surface. The
minimal context-only launch need not wait for command or tracked delivery;
command requests must wait for the corresponding protected transform lane.

## Test plan

Use the repositories' existing Go tests and conformance-vector machinery. Drive the production paths: Curator resolve/materialization, `curator-run`'s `run`/`launch` composition, protected command dispatch, and tracked consumer start/resume. Native probes run in synthetic homes/checkouts without operator credentials; qualification requiring real login needs separately authorized disposable-account evidence.

| Family | Required positive and negative evidence | Narrowing mutant |
|---|---|---|
| Admission | Approved digest launches; changed bytes/dependencies, self-minted approval, optional-vs-required omission, malformed/unreadable manifest refuse correctly. | Bind only root file instead of transitive closure; trust same hash from another checkout. |
| Native discovery | Approved context/skill loads; unapproved ancestor/nested instructions, dynamic rules, settings, MCP, hooks, plugin resources and late-created files do not activate. Observe loader/tool behavior, not an LLM claim that it ignored a file. | Suppress only startup files; suppress config but leave rules/skills. |
| Composition | Same pin deduplicates; whole-skill replacement works; incompatible required provider, command collision and MCP same-ID conflict refuse. | Compare command names only in project, omitting profile or transitive providers. |
| PATH/dispatch | D-PATH tool-prefix/base/dispatcher order, one dispatcher, duplicates and profile-only/null root; project P then selected Y; old singleton shims, symlinked dispatcher, missing PATH, hostile earlier entry, empty/relative segment and runtime re-prepend negatives. | Reject only direct `.agents/bin`, admitting a canonical alias or nested writable root. |
| Permissions/secrets | Manager-programmed grants within ceiling work; raw project grants and denies never apply. Project bypass, secret-name widening, native PATH assignment, forbidden hooks and dialect ambiguity refuse. Native memory stays disabled without explicit opt-in. | Enforce global lock only on CLI flags, leaving imported native settings. |
| Leases/TOCTOU | Two projects on Y, two identical view sessions, busy update, revocation, detach, descendant, resume, crash and unknown liveness. No GC of referenced artifacts. | Key lease only by PID; release at launcher exit; collect on TTL alone. |
| Tracking | Same effective child environment at the destination, digest changes with composition/PATH/policy, replay and context substitution refuse before child creation. | Hash declared transform but omit resolved PATH or composition identity. |

Platform matrix: macOS and Linux for each qualified native version; Windows only after path separator, executable suffix, canonical path/reparse-point, case-folding, permissions and lease tests pass. OpenCode V1/V2 are separate rows. Claude login behavior is version/OS-specific. Record the number passed over the enumerated cases and the uncovered surfaces; an absent binary, skipped native test or failed read is not green coverage.

The historical research evidence remains limited to the file/source audit
and P1–P6 in the companion. This acceptance candidate adds no native probes
or implementation conformance claim. Documentation validation and published
carrier controls are recorded separately in the task outcome.

## Open questions for the operator

The former eight questions are resolved by the dated owner decisions above.
Publication of the candidate grammar/diagnostics and qualification of actual
adapters remain engineering gates, not reopened home, PATH or adapter choices.
Only these later-surface owner decisions remain:

1. **Replacement of profile root/system context:** permit a separately
   approved replacement in a later slice, or retain additive-only context?
   **Recommend additive-only for the first release**, with a separately
   specified replacement item and immutable policy ceiling before any later
   opt-in. The selected repository overlay does not itself authorize replacement.
2. **Private memory retention after explicit opt-in:** retain memory in the
   Werkstatt until explicit deletion, or expire it at an operator-selected
   retention limit? **Recommend private per-Werkstatt retention with explicit
   deletion**, never publication, cross-Werkstatt reuse or automatic promotion
   to approved knowledge. Memory remains off by default; the first slice
   accepts only `memory: "off"` and defers the opt-in delivery grammar.
