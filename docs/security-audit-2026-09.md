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

### Epic `EPIC-260910-16qce1` — security-audit-remediation-registry-service

| Story | Findings | Spec-side tasks |
|---|---|---|
| `STORY-260910-3rvvxh` records-boundary-in-response | R1 | (paired with `TASK-260910-1b1ens`) |
| `STORY-260910-35tbgb` serve-time-checkpoint-gate | R3+P2 | `TASK-260910-33j1hu` spec-restore-enforcement-point |
| other stories | service-side | see the registry audit document |
