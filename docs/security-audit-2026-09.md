# Architectural Security Audit — Curator Protocol Specification, 2026-09-10

**Scope.** This audit covers the Curator Protocol specification documents as
they constrain conforming implementations: `protocol/core.md` (`1.0.0-rc.9`
band), `protocol/registry.md`, `protocol/assurance.md`,
`protocol/environments.md` (revision 1), `profiles/registry-service.md`, and
`SECURITY.md`. It is an **architectural** audit of the specification as a
security design: what its defaults, trust boundaries, and composition rules
guarantee, and where they leave exploitable gaps that no conforming
implementation can close on its own.

**Method.** All normative documents were read in full. Findings were checked
against two conforming implementations — the Go manager
(`relux-works/curator`) and the Python registry service
(`relux-works/curator-skill-registry`) — to confirm which gaps are
specification-level rather than implementation defects.

**Companion documents.** The manager-side and service-side documents live in
`relux-works/curator/docs/security-audit-2026-09.md` and
`relux-works/curator-skill-registry/docs/security-audit-2026-09.md`. Finding
IDs are shared.

**Remediation tracking.** See [Appendix A](#appendix-a-remediation-decomposition)
for the board decomposition. Epics: `EPIC-260910-2hw1xb` (manager + spec)
and `EPIC-260910-16qce1` (registry service), tracked on the shared Curator
board.

## 1. Executive summary

The specification is unusually honest and disciplined: it separates
manager-enforced mechanisms from kernel-enforced guarantees, keeps identifier
and policy sets closed, and specifies fail-closed behavior for nearly every
unprovable state. The audit confirms the core architecture is sound. The
gaps are concentrated in five places:

1. **Default posture is permissive** (S1): every strong gate — strict
   registry policy, strict audit mode, non-empty allowlists — is opt-in.
2. **The registry transparency promise is not closed by the client
   verification path the protocol defines** (R1/P1): record pages carry no
   boundary, so transparency is only real for clients that replay the log,
   and the shipped client does not.
3. **Availability semantics make revocation hiding practical under the
   default policy** (S3): unreachable registries warn rather than exclude.
4. **The environments capability admits package-controlled launch-time code
   execution with unbounded secret passthrough by default** (S4).
5. **First-use trust is TOFU with no authenticated bootstrap** (S2), and
   equivocation across clients has no protocol-level detection.

## 2. Confirmed strengths

- **Closed sets everywhere**: drivers, execution policies, native-control
  inventories, interpreter identifiers, diagnostics — all closed with
  explicit admission rules (§12.3), preventing silent capability creep.
- **Honest mechanism/guarantee separation** (core §4.1.1, §4.2.1,
  assurance.md, SECURITY.md): deferred guarantees are named and forbidden on
  evidence surfaces.
- **Fail-closed rollback state** for registry snapshots (registry §5),
  including deletion detection and rebootstrap discipline.
- **Deny-wins federation** (registry §4) with deterministic latest-record
  projection and exact artifact keys preserving equivocation evidence.
- **Compile-only build boundary** (SECURITY.md, core §4.2): zero package
  hooks, fixed argv/environment, no artifact execution.
- **Credential ownership** (core §12.2): the unbound-HTTPS-credential
  exposure is explicitly specified with host binding required.
- **Portable path discipline** (core §2): case-folding, Windows reserved
  names, collision detection before writes.

## 3. Findings

### S1. Default-open posture of every strong gate (Medium, systemic)

Registry §4: unknown artifacts block only under strict policy. Core §6.1: an
empty allowlist permits all network identities. Environments §2.2/§12.1: an
empty MCP package allowlist permits all declaration sources and
`passable_env_names: null` is unbounded. Nothing in the protocol recommends
or defaults to the stricter end, and both surveyed implementations ship the
permissive defaults.

A hostile project repository plus `curator install` therefore passes with
zero blocking gates under defaults. The strong machinery (deny-wins
revocation, allowlists, strict modes) exists but is opt-in at every level.

*Recommendation:* specify a **hardened defaults** profile (strict registry
policy, recommended non-empty allowlist shape, MCP allowlist required for
managed deployments) and require managers to report which posture they run in.
Reference: `STORY-260910-2qmrb8`.

### R1 / P1. Records pages carry no snapshot boundary; transparency rests on log replay the protocol never requires (High)

Registry §2/§9: the first page of a paginated endpoint "captures one
committed signed snapshot boundary" — but this is **server-side**
consistency. The records response schema has no boundary field, no signature
over the page, and §10 says verification is per-record signatures. §6
provides the log, and the registry-service profile §10 states transparency is
verified "by replaying the append-only log or an authenticated bundle" — yet
nothing **requires** clients to do either, and the shipped Go client does
neither.

Consequently a key-holding registry can serve an honest, advancing
`/v1/snapshot` while evaluating `/v1/records` at an older boundary, hiding
an appended `revoked` record and re-serving a stale `audited` one. Client
rollback state (§5) does not detect this: it binds snapshot versions, not
record-page boundaries.

*Recommendation:* extend the records/log response schemas with the committed
boundary they were evaluated at (or compact inclusion proofs), and require
conforming clients to reject pages below their persisted high-water.
References: `STORY-260910-25yc0h` (this repo + client),
`STORY-260910-3rvvxh` (service).

### S3. Revocation hiding via network DoS under advisory policy (Medium)

Registry §4: "Unreachable registries warn and contribute no record." Under
advisory policy (the default, see S1) an attacker on the network can suppress
delivery of a revoked record — the artifact resolves unknown, and advisory
installs proceed. Deny-wins requires seeing the revocation; hiding it is
sufficient. The 7-day offline grace extends the window (a cached response
from before the revocation remains stale-valid).

Each choice is individually defensible (availability vs strictness), but the
spec never states the composed residual.

*Recommendation:* name the residual explicitly in registry.md/SECURITY.md
("revocation is network-dependent under advisory policy"); require managers to
surface unreachable trusted registries prominently during install.
Reference: `STORY-260910-2qmrb8`.

### S4. Environments: MCP declarations are launch-time package execution with unbounded secret passthrough (High)

Environments §2.2: `stdio` MCP servers declare `command`+`args` executed by
the agent tool at launch. The profile itself admits "a binary allowlist
bounds nothing: `npx`, `uvx`, `node`, or `sh` admit any program through
`args`", and bounds declaration packages only by source identity — with an
**empty default allowlist**. `env_names` names operator variables passed into
the launch environment; the reserved-set exclusion covers manager variables,
not operator secrets, and `passable_env_names` defaults to unbounded.

A hostile declaration package can therefore execute arbitrary programs in the
agent's environment and receive named operator secret values. Root-context
modules (also package data) can prompt the agent to invoke the server.

*Recommendation:* (1) default `passable_env_names` to empty (opt-in per
name); (2) require a loud warning when the MCP allowlist is empty; (3)
require managers to surface resolved stdio `command`+`args` at profile
install/update; (4) longer term, a closed interpreter contract for MCP
launch analogous to `script-worker-v1`. Reference: `STORY-260910-1lf0m5`.

### S6. Shell integration auto-sources project-controlled `.agents/env.sh` (High)

The manager profile's shell integration caches a hook that sources
`.agents/env.sh` walking up from `$PWD` on every directory change. A
project-controlled file is therefore executed in the operator's interactive
shell on `cd`, with no approval or digest gate specified anywhere in the
protocol. The implementation confirms this is live behavior.

*Recommendation:* specify a trust rule: the hook sources only env files whose
digest the manager recorded (or the operator approved); unknown files warn
and are not sourced. Reference: `STORY-260910-2awkzu`.

### S2. TOFU bootstrap and equivocation (Medium)

Registry §5: rollback protection keys persisted high-water state per registry
URL — but the **first** fixation is trust-on-first-use with no authenticated
checkpoint; recovery after loss requires out-of-band rebootstrap, while
initial pinning has only the pinned keys plus whatever the network serves.
Equivocation (divergent, each-monotonic views for different clients) has no
protocol-level detection; §10/registry-service §10 acknowledge it.

*Recommendation:* specify a signed bootstrap checkpoint interchange (the
registry-service profile already defines signed `registry-snapshot-v1`
objects usable for it) and an optional cross-registry Merkle-root
comparison. Reference: `STORY-260910-6bo7ej`.

### S5. Environments store lacks a protected-boundary contract (Medium)

Core §9.3 gives the build cache a normative ownership/permission/containment
contract revalidated on every lookup. Environments §4/§8.2/§10.1 give the
profile store, locks, and markers none: they are records, not signatures,
and "link-target identity is sufficient currency" — so a same-user swap of
store bytes is undetected at resolve. The agent-facing prompt material
(system prompt, root context) is the sharpest surface a profile carries and
is the least protected store under the manager home.

*Recommendation:* extend the environments document with an ownership/
permission/containment validation contract for the environments root and
store, mirroring core §9.3. Reference: `STORY-260910-148pj1`.

### P2. Restore-checkpoint enforcement point is ambiguous (Low)

Registry-service profile §6: "A restored state below or inconsistent with
the checkpoint MUST NOT serve the same canonical URL... before the service
becomes ready" reads as a service behavior, but the only conforming
mechanism implementations can build today (`verify-backup`) is a CLI check;
nothing at serve time compares against the external checkpoint. The profile
should state exactly where enforcement lives (e.g. `serve --checkpoint`).

### P3. No performance envelope for verification work (Info)

The profile mandates finite deadlines but is silent about the O(n) boundary
recomputation its §2/§5 rules imply (every page, every cursor, every
health probe). A conforming registry self-degrades as the log grows. Add a
documented requirement or allowance for boundary memoization and cached
health verdicts.

### P4. Bundle import does not compare upstream high-water (Low)

Registry §7 specifies bundle authenticity as signature + chain + Merkle
verification but never compares the upstream snapshot against a persisted
high-water for that upstream, so an old-but-valid bundle imports as new.
Require (or recommend) an upstream high-water check at import.

### Environments and launch plane supplement (E1–E6, 2026-09-16)

The findings below were added after the initial audit, cross-checked
against `protocol/environments.md` at `main` (revision 1.1, 2336 lines),
Decision 0012 §8, and the launcher SPEC 0.2.1-draft. They carry their own
`E` prefix because the manager-side document already uses `S7`/`S8`.
They were established against the specification text and one known
implementation defect (E5); their status in the shipped code is the
subject of `STORY-260916-1nc5dc`.

### E1. Range resolution trusts every future tag of a source; no signature or provenance rule exists (High)

Decision 0012 makes root-context, skill and MCP requirements semver
**ranges** (`^1.0`, `latest`) resolved to the highest satisfying `v`-tag;
`profile update` / `--all` re-resolves them (0012 §8) and in-place
surfaces (`~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`, skills)
re-materialize on the spot. The lock pins commits only *after*
resolution, and environments §4/§8.2 are explicit that "the lock is a
record, not a signature". Nothing in core, 0012 or environments requires
or allows verifying tag or commit signatures against an operator-pinned
signer set. Whoever can push an in-range tag to a source — a compromised
maintainer account, a hijacked fork used as a mirror — therefore ships new
**system-prompt** and root-context bytes and new MCP `command`+`args` into
every managed home and the operator's live global context on the next
`profile update`, with only strict audit (secret detection) in the way.
The strict-tag policy of 0012 §8 covers a *moved* tag, not a *new* one.

*Recommendation:* (1) an optional-but-lockable **signer allowlist per
source** (SSH/GPG tag or commit signatures verified before a candidate
enters the lock), reported as posture like the other gates; (2) `profile
update` MUST present the resolved-version delta and, when the delta
introduces or changes a `class: system` module or an MCP declaration,
refuse without an explicit per-run confirmation; (3) name the residual
for `latest`. Reference: `STORY-260916-ioemse`.

### E2. `class: system` modules are admitted transitively; the only control is an always-warn finding (High)

A `class: system` module replaces or appends the tool's system prompt (pi
`SYSTEM.md` replaces it wholesale). Environments §12/§13 give it exactly
one control: `context-system-module-present`, "an always-warn,
never-blocking" finding. Any package anywhere in the closure — a
dependency three edges below the umbrella, selected by a range — may
carry one; weights order chapters, they do not gate admission. Composed
with E1, a transitive dependency update rewrites the operator's system
prompt behind a warning.

*Recommendation:* admit `class: system` modules only from packages the
root (or a machine-config allowlist) names **directly**; make a
transitive system module a resolution error
(`context_system_module_transitive`) with an explicit scoped waiver; keep
the fragment's `works.relux.curator.system-modules` flag so `ax` resume
refuses on drift. Reference: `STORY-260916-2d9coh`.

### E3. The codex provisioning seed imports the native `mcp_servers` tables, so the MCP allowlist is enforced asymmetrically per adapter (Medium)

§7.4 seeds `codex_cli` with the native `config.toml` "copied whole
(project trust, model, and MCP tables included)"; §7.8 then *layers* the
profile's set over it with `-p curator-mcp`. A managed codex home
therefore runs every native MCP server the operator ever configured,
outside the profile's lock and outside the §2.2 allowlist, while
`claude_code` gets `--strict-mcp-config` and runs only the profile's set.
The document records the layering but not that the allowlist does not
govern the seeded base.

*Recommendation:* strip `mcp_servers` from the codex seed (seed only
trust, model and TUI members) or state the residual in §7.4 and §7.8 and
report the ungoverned entries in `env status`, as §7.6 already does for
Xcode targets. Reference: `STORY-260916-1i1gfo`, pairs with
`STORY-260910-1lf0m5`.

### E4. S6 composes with umbrella discovery: a project `.agents/env.sh` can plant `curator-run` (High, composition)

§11 refuses a `curator-<name>` provider that resolves inside a
manager-published or managed directory (`subcommand_provider_untrusted`).
It does not refuse a provider found in a directory that a
project-controlled shell hook (S6) prepended to `PATH`. `cd project &&
curator run claude_code` then executes the project's binary as the
launcher with the operator's environment. The launcher SPEC inherits the
same trust (§2: "the umbrella discovery of section 11 trusts `PATH`").

*Recommendation:* resolve providers only from the manager's own install
directory plus an explicit machine-config provider directory list, never
from the ambient `PATH`; or, at minimum, refuse providers in directories
writable by anyone other than the operator, and print the resolved
provider path in the launch stderr line-group. Reference:
`STORY-260916-2otjbn`, pairs with `STORY-260910-2awkzu`.

### E5. Takeover replaces files but never says "do not write through a symlink" (Medium)

§9.5 detects a foreign-manager symlink
(`environment_foreign_manager_detected`) and lets the operator take over
with backup, but no sentence forbids writing *through* an existing link.
The reference implementation had exactly this defect during the
environments epic (takeover wrote through a dotfile-manager symlink into
the foreign manager's source of truth; `os.WriteFile` follows links) and
fixed it locally. A conforming implementation written from the text alone
reproduces it.

*Recommendation:* one normative sentence in §8.3/§9.5: a takeover or
repair write replaces the directory entry (unlink, then create) and MUST
NOT follow a symlink at the target path — `O_NOFOLLOW`-class semantics on
every managed-surface write — with a conformance vector whose target is a
symlink. Reference: `STORY-260916-73a5zg`.

### E6. `path`-kind sources sit outside the source-identity allowlists and the store boundary (Medium)

Overlays and onboarding imports use the `path` kind (0012 §5, environments
§6/§9.6): pinned by state hash, no git identity. The MCP package allowlist
and any future signer allowlist (E1) are over canonical source identities,
which a `path` source does not have; S5's missing store boundary applies to
the directory itself. If a `path`-kind MCP declaration package is
admissible, the allowlist cannot name it and it is unbounded by
construction; if it is not, the text should say so.

*Recommendation:* state explicitly which kinds may carry MCP declarations
and `class: system` modules (git only is the safe answer); for `path`
overlays, require the directory to pass the ownership/permission/
containment validation S5 proposes for the store. Reference:
`STORY-260916-wgt8vz`.

### E7. Minor launch-plane residuals (Low)

- **Launcher configuration family** (`defaults.json`, `ax.json` under
  `/etc/curator-run/` and `$XDG_CONFIG_HOME/curator-run/`): the SPEC
  validates schema but not ownership; a user-writable machine file or a
  symlinked operator file flips tracking policy or locks. The same
  S5-style contract, one paragraph.
- **`env resolve --repair` on every launch** re-materializes from the
  store under the launcher's authority (launcher §4.1). Under S5 a
  tampered store is re-applied on every launch — repair doubles as
  persistence. Worth a sentence in S5's remediation.
- **`--strict-mcp-config` asymmetry**: for `claude_code` the channel
  intentionally disables the managed home's own `.claude.json` servers
  (0012 D6 records this); for `codex_cli` the inverse holds (E3). One
  table row in §7.8. Reference: `STORY-260916-33vuzm`.

## 4. Priority summary

| # | Finding | Severity | Where |
|---|---|---|---|
| R1/P1 | Records pages not bound to snapshot | High | registry.md §2/§9 + clients |
| S4 | MCP launch execution + env passthrough | High | environments §2.2/§12.1 |
| S6 | Shell hook auto-source | High | manager profile (shell integration) |
| S1 | Permissive defaults | Medium | registry.md §4, core §6.1, environments |
| S3 | Revocation hiding under advisory | Medium | registry.md §4 |
| S2 | TOFU / equivocation | Medium | registry.md §5 |
| S5 | Environment store boundary | Medium | environments §4/§8/§10 |
| E1 | Range resolution trusts future tags; no signer rule | High | decisions/0012 §8, environments §4/§8/§12 |
| E2 | Transitive `class: system` modules, warn-only | High | environments §2/§12/§13 |
| E4 | S6 × umbrella discovery on ambient `PATH` | High | environments §11, launcher SPEC §2 |
| E3 | Codex seed imports native `mcp_servers`; allowlist asymmetric | Medium | environments §7.4/§7.8 |
| E5 | No nofollow rule for takeover/repair writes | Medium | environments §8.3/§9.5 |
| E6 | `path`-kind sources outside allowlists and store boundary | Medium | decisions/0012 §5, environments §2.2/§6/§9.6 |
| E7 | Launcher config ownership; repair-as-persistence; strict-MCP asymmetry | Low | launcher SPEC §4.3/§4.6/§4.7, environments §7.8/§10.1 |
| P2 | Restore enforcement point | Low | registry-service §6 |
| P4 | Import high-water | Low | registry.md §7 |
| P3 | Verification cost envelope | Info | registry-service §2/§5 |

## 5. Positive notes for the revision process

The closed-set discipline (§12.3) means every fix above can be introduced as
an explicit, versioned revision with its own conformance vectors — the
specification is well prepared for exactly this kind of change.

---

## Appendix A. Remediation decomposition

Tracked on the shared Curator board (the specification repository shares the
manager board). The audit documents are attached to both epics as resources.

### Epic `EPIC-260910-2hw1xb` — security-audit-remediation-manager-and-spec

| Story | Findings | Spec-side tasks |
|---|---|---|
| `STORY-260910-2awkzu` shell-hook-project-env-approval-gate | S6 | `TASK-260910-1wjst3` spec-hook-trust-rule |
| `STORY-260910-1lf0m5` bound-mcp-declaration-exposure | S4 | `TASK-260910-2ohnjo` spec-bound-env-passthrough |
| `STORY-260910-25yc0h` records-boundary-binding | R1/P1 | `TASK-260910-1b1ens` spec-records-boundary-envelope |
| `STORY-260910-2qmrb8` secure-defaults-for-audit-gates | S1+S3 | `TASK-260910-2qtiho` spec-hardened-defaults-profile |
| `STORY-260910-148pj1` profile-store-protected-boundary | S5 | `TASK-260910-39fzpq` spec-environment-store-boundary |
| `STORY-260910-6bo7ej` tofu-and-equivocation-mitigations | S2 | `TASK-260910-1tvf2t` spec-bootstrap-checkpoint |
| `STORY-260910-234vmx` supply-chain-and-credential-hardening | I2, I3, S7 | (manager-side only) |
| `STORY-260916-ioemse` source-signer-allowlist-and-update-delta | E1 | `TASK-260916-y4sa6s` spec-signer-allowlist-and-update-confirmation; manager: `TASK-260916-1zgucp` |
| `STORY-260916-2d9coh` direct-only-system-modules | E2 | `TASK-260916-1hrx51` spec-system-module-admission-rule; manager: `TASK-260916-55g9dg` |
| `STORY-260916-1i1gfo` codex-seed-mcp-tables-residual | E3 | `TASK-260916-2rnkei` spec-codex-seed-mcp-residual; manager: `TASK-260916-33abdk` |
| `STORY-260916-2otjbn` umbrella-provider-trust-roots | E4 (with S6) | `TASK-260916-1x0ogh` spec-provider-resolution-trust-roots; manager: `TASK-260916-3oh0u8`; launcher: `TASK-260916-16ys92` |
| `STORY-260916-73a5zg` managed-write-nofollow-rule | E5 | `TASK-260916-1qfpu4` spec-nofollow-write-rule; manager: `TASK-260916-19shmj` |
| `STORY-260916-wgt8vz` path-kind-admission-and-boundary | E6 | `TASK-260916-3l60rn` spec-path-kind-admission-rule; manager: `TASK-260916-yvxbs1` |
| `STORY-260916-33vuzm` launch-plane-minor-residuals | E7 | `TASK-260916-2x2f7h` spec-repair-persistence-and-strict-mcp-asymmetry-notes; launcher: `TASK-260916-1ihonr` |
| `STORY-260916-1nc5dc` verify-e-findings-against-implementations | E1–E7 | `TASK-260916-dv7xv5` verify-e1-e6-against-curator-and-launcher-main (research, read-only) |

The E-series supplement text is attached to `EPIC-260910-2hw1xb` as
`security-audit-2026-09-spec-supplement.md`.

### Epic `EPIC-260910-16qce1` — security-audit-remediation-registry-service

| Story | Findings | Spec-side tasks |
|---|---|---|
| `STORY-260910-3rvvxh` records-boundary-in-response | R1 | (paired with `TASK-260910-1b1ens`) |
| `STORY-260910-35tbgb` serve-time-checkpoint-gate | R3+P2 | `TASK-260910-33j1hu` spec-restore-enforcement-point |
| other stories | service-side | see the registry audit document |

## Appendix B. Implementation verification of E1–E7 (2026-09-16)

Static, read-only review of `relux-works/curator` `main` @ `80483355` and
`relux-works/curator-agent-launcher` `main` @ `b34e1e27` (no tests run, no
dynamic reproduction). The full evidence table is the outcome resource
`verify-e-findings.md` on `TASK-260916-dv7xv5`.

| Finding | Verdict | Where in the code |
|---|---|---|
| E1 | **confirmed** | no signer verification anywhere; `profile update` prints only `updated profile <name> (lock <hash>)` (`cmd/curator/profile.go:81`); `latest` is `*` (`internal/pkgversion/pkgversion.go:286`) |
| E2 | **confirmed** as specified | every closure package's system modules are applied (`internal/contextmaterialize/contextmaterialize.go:259`); only the always-warn `context-system-module-present` exists (`internal/contextaudit/contextaudit.go:22`) |
| E3 | **confirmed** | codex seeds `config.toml` whole (`internal/envregistry/envregistry.go:219`; `gatherSeeds`, `internal/envprofile/managed.go:565`), nothing strips `mcp_servers` |
| E4 | **confirmed** | `exec.LookPath("curator-"+name)` on the ambient `PATH`; only manager-published directories are refused (`cmd/curator/umbrella.go:30-63`) |
| E5 | **mitigated in code**, rule absent from the text | remove-then-create on every managed-surface write (`internal/envprofile/switch.go:520-545`, `replaceLink` `:694`); not atomic, not `O_NOFOLLOW` |
| E6 | **partially confirmed** | dependencies are git-only (`internal/contextpkg/contextpkg.go:289-302`), so a `path`-kind MCP package cannot enter a closure — not applicable; a `path`-kind root or overlay still carries `class: system` modules with no directory boundary — confirmed |
| E7 | **confirmed** | both launcher loaders follow a symlinked configuration file instead of refusing it (`internal/axconfig/config.go:58-75`, `internal/defaults/defaults.go:100-118`); no ownership or permission check; provider path absent from the stderr line-group |
