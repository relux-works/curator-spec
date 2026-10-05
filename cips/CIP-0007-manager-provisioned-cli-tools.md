# CIP-0007: Manager-provisioned CLI tools

- **Status:** Draft
- **Owner:** orchestrator; decision: operator
- **Created:** 2026-10-05
- **Related:** Issue #108 (manager-provisioned CLI tools proposal); issues #100
  (provider installs), #101 (newer Go families), #106 (manager-provisioned Go
  toolchain), #107 (shim resolution); TASK-261005-39d5lx (this design);
  triage recommendation B (registry-only lane); CIP-0005 (audit backends)
- **Affects:** `protocol/core.md` §4 (skill manifest); `protocol/registry.md`
  (signed snapshots, offline behavior); `protocol/skillfile-sources.md` §3
  (lock identity); manager profile §§2–4, 10 (install lifecycle, scopes,
  status); skillfile and lock schemas; conformance vectors. No normative
  change is made by this document.

## Summary

Skills that need an ordinary infrastructure CLI (for example a
forge-hosted issue-tracker CLI or a dashboard-query CLI) can today only name
a bare system command; a missing command
fails installation and versions drift between machines. This proposal designs
three options: keep system commands with better hints, add a registry-only
lane where a skill declares a tool by logical identity plus version
constraint and the manager provisions it only from operator-trusted signed
registries, or build full provisioning with layered registries, a
Gatekeeper-style trust policy, and a mirrored upstream catalogue. It
recommends the registry-only lane, records the trust model and threat
analysis, and lists the owner and service decisions the operator must make
before any implementation.

## Motivation and user stories

- A field report behind issue #108: two of eleven maintained skills failed to
  install on fresh machines because their CLIs were absent. The user story is
  seamless installs with no per-machine prose setup step.
- A skill author needs "this CLI at version ≥ X", not "some binary of this
  name on PATH". Teammates and CI need the same resolved bytes, recorded in
  the lock.
- The operator needs the default to stay strict: a skill author must never be
  able to make the manager download arbitrary binaries. Every provisioning
  decision goes through operator-trusted registries and policy.
- The design should reuse a maintained upstream catalogue rather than
  hand-writing per-OS artefact tables, and should share download, verify,
  store, and mirror machinery with the Go-toolchain proposal (#106).

Non-goals (from #108): prebuilt skill CLIs (the source-built `go-v1` /
`go-repository-v1` model stays unchanged; prebuilt artefacts need their own
security design); a general package-manager replacement (OS tools such as
`git`, `curl`, `ssh` stay presence-checked system commands).

## Current state

This is docs-only design research against specification rc.14. No Curator
main revision was inspected and no behavioral probe was run; all citations
are to this repository.

| Finding | Evidence |
| --- | --- |
| System commands are a bare name plus hint | `protocol/core.md:210-213`: "A system command declares a non-empty bare executable name and MAY include a hint. A missing system command fails installation with the hint." Schema: `schemas/v1/common.schema.json` `systemCommand` (`type`, `command`, `hint`; closed object). |
| Readiness is verified in planning, never provisioned | Manager profile §2.1 step 7 verifies "system, legacy command, and MCP requirements" (`profiles/manager.md:163-166`); no step downloads or installs a tool. |
| No version constraint or recorded tool identity exists | The manifest carries no tool-version field; the lock (`protocol/skillfile-sources.md` §3, `skillfile-lock-v1.schema.json`) records skill members and package identity only. |
| Install is a read-only plan plus one serialized transaction | Manager profile §§2.1–2.5: read-only planning and source gates, private builds in staging, then a single journaled manager-home transaction with rollback (`profiles/manager.md:134-599`). |
| A signed-registry machine already exists for audit records | `protocol/registry.md`: CCJ-1 canonical bytes (§1), Ed25519 envelope (§2), key rotation (§2.1), canonical registry URLs (§2.2), snapshot rollback protection (§5), cache and offline grace (§8), HTTP wire contract (§9). |
| The Go toolchain is closed and manager-owned | Manager profile §2.2 pins an operator-trusted Go family, fixed probe vectors, and a fingerprinted tree; package-selected toolchains are rejected. Any tool provisioning must meet at least this bar. |
| Package code never executes during install | `protocol/core.md:85-91`. A provisioned tool is a manager-fetched artefact, not package code, but its bytes still enter the trust boundary only through verification. |
| Triage recommended option B | Triage (2026-10-04) recommended a registry-only lane, noting it needs an owner and service decision. |

## Design

### Options considered

**Option A — Status quo system commands with better hints.**

Mechanism: no manifest or lock change. Document hint conventions (install
commands per OS, minimum versions in prose), improve the missing-command
diagnostic to name the requiring skill and the hint verbatim, and add a
`check`-style readiness report. Versions stay unenforceable.

- Pros: zero protocol surface; no new trust boundary; shippable as docs plus
  diagnostics.
- Cons: does not solve drift or fresh-machine installs; hints go stale; no
  recorded identity; CI images still need skill-specific setup.
- Security: no new risk beyond today's (a hint is prose, never executed by
  the manager: `core.md:210-213` fails installation with the hint, manager
  §2.1 step 7 only verifies requirements, and package code never executes
  during install per `core.md:85-91`). Residual: users copy-paste hinted
  install commands, which is unaudited trust in whatever the hint names.

**Option B — Registry-only lane (recommended).**

Mechanism: a new manifest dependency kind (for example
`dependencies.tools[]`) carries logical identity plus version constraint
only — no URL, checksum, or signature:

```json
{ "id": "example.com/org/cli", "alias": "cli", "version": ">= 1.90.0, < 2" }
```

The manager resolves `id@constraint@os/arch` exclusively from
operator-configured signed registries (a built-in snapshot shipped with or
pinned by the manager release, plus organization registries configured with
URL and public keys, following the `registry.md` §§1–2, 5 envelope and
rollback rules). Records are resolved and flat: exact version, per-platform
URL, format, file map, SHA-256, and a `trust` marker (`signed` /
`checksummed` / `pinned`) describing the evidence behind the record. No
author-supplied URL is ever fetched; unknown or unsigned identities fail
with a structured refusal naming the tool, the constraint, the policy, and
the remediation. The resolved version, per-platform hashes, source registry,
and system-or-provisioned choice are recorded in the lock; replay provisions
exactly those bytes subject to the replay authorization checks in Security
considerations (proposal — hash presence alone is not sufficient).

Resolution is two-phase (proposal, adapting `registry.md` §4 to tool
records). Phase 1 is a federation-wide revocation scan: the manager queries
every enabled tool registry with at least one pinned key, in configured
order, and any verified revocation whose match key covers the candidate
artefact blocks resolution before any positive record is accepted. The
proposed record match key is `(id, version, os, arch, sha256)`; the proposed
revocation match key is `(id, version, os, arch, sha256)` for an exact
artefact revocation plus `(id, record-digest)` for a record withdrawal,
either of which blocks. Phase 2 is ordered positive selection: the first
layer holding a verified non-revoked record satisfying the constraint wins.
Malformed, unmatched, or unverifiable records are ignored with a warning,
as in `registry.md` §4. An unreachable trusted tool registry in the B lane
is a refusal: the operation fails with a gate notice naming the registry
and every tool resolved without complete revocation evidence (proposal —
`tool_registry_unreachable_during_install`-class; no
availability-preferring mode exists in B).

Runtime exposure in B is provisioned-only with a minimal binding
(proposal). Provisioned executables are manager-owned files in the sealed
store; the launcher exposes a tool's `alias` only to the declared commands
of skills that depend on that exact tool identity. Alias collisions fail
closed: two tools claiming one `alias` in the same scope, or two scopes
sharing a bin path with conflicting versions, refuse with a structured
error (no silent shadowing, no last-writer-wins). Declared-only script
commands (core §4.1) may resolve the alias through the manager-built
launcher PATH prefix. Enforced `script-worker-v1` commands are unchanged:
their PATH is built from exactly the resolved interpreter plus the
resolved declared `exec` names (core §4.1.1), the inherited PATH is
discarded, and adding a tool dependency MUST NOT widen that PATH — a tool
is callable from an enforced command only when its alias is also a
declared `exec` name resolved by the manager to the provisioned path. B
performs no PATH version probes; "system tool satisfies the constraint"
reuse is a C-only addition (see issue #108 §6).

- Pros: closes the version-drift and fresh-machine gaps with the smallest new
  trust surface; every byte is traceable to a signed registry entry the
  operator chose; reuses the `registry.md` signature, rotation, and rollback
  machinery instead of inventing a second one.
- Cons: needs a registry owner and service decision (who publishes and signs
  snapshots, who reviews new records); coverage is bounded by what registries
  carry, so uncommon tools still fail closed until added; per-OS/arch record
  curation is ongoing work.
- Security: the registry operator becomes a supply-chain principal (see
  Security considerations). Author-controlled downloads are structurally
  impossible: the manifest cannot name a fetch location.

**Option C — Full provisioning with layered registries, trust policy, and an
upstream mirror.**

Mechanism: option B plus (1) a third layer of machine-local operator
approvals (explicit per-artefact hash approvals in a machine trust store);
(2) a Gatekeeper-style operator policy, strict by default — `registry-only`,
then `verified` (on-demand resolution from a metadata mirror only when the
upstream checksum verifies AND a signature/attestation verifies against the
operator-pinned expected publisher and subject for that tool identity —
proposal, see Security considerations; a valid signature from an unexpected
signer is a refusal, never an acceptance), then `prompt` (interactive
approval of weaker evidence, never in non-interactive or CI mode) — with
per-tool allow/deny overrides and a revocation list; (3) a whole-catalogue
metadata mirror of the upstream aqua-registry catalogue treated as
untrusted input, with lazy resolution through a privileged resolver job
(proposal — its output enters organization snapshots only via reviewed,
signed changes), upstream verification against the per-tool expected-signer
policy, reviewed snapshotting, and signing into organization registries;
(4) refined per-scope PATH composition on top of B's minimal binding
(project-scoped tools visible only to that skill's commands via the
launcher PATH prefix; global skills on the manager global bin path;
profile skills on the profile bin path) and a "system tool on PATH wins
when it satisfies the constraint" rule (issue #108 §6) with explicit
registry-declared version probes and never-silent shadowing.

- Pros: broadest coverage without per-tool curation lag; deliberate,
  auditable loosening path for the operator; mirrors are untrusted transport
  because verification is by hash.
- Cons: largest design and implementation surface (policy engine, approval
  store, mirror resolver service, version-probe contract, per-scope PATH
  composition); on-demand resolution moves verification work to every client
  unless a registry service pre-signs records; `prompt` mode is an
  interactive-only escape hatch that CI must never see.
- Security: each added layer is a new principal or bypass path — the mirror,
  the resolver job, the approval store, and the version probe must each be
  threat-modelled (see below). Misconfiguration risk rises with policy
  expressiveness.

Rejected within every option: manifest-carried URLs, checksums, or
signatures; template evaluation by the client; silent shadowing of a
user-installed tool; automatic fallback from a refused tool to an unrelated
source.

### Recommendation

Adopt **option B**, per the triage recommendation, with option C held as the
explicit target architecture gated on the decisions in Open questions. The
operator control surface for B:

- `tools.policy`: fixed `registry-only` in this slice (no `verified` /
  `prompt` modes yet); unknown tools fail closed.
- `tools.registries[]`: ordered operator configuration of registry name,
  canonical URL (per `registry.md` §2.2), pinned Ed25519 key set, freshness
  bounds, and an optional bootstrap checkpoint (per §5). Selection is
  two-phase (proposal): a federation-wide revocation scan across every
  enabled tool registry first (any verified revocation covering the
  candidate artefact blocks), then first-layer positive selection among
  verified non-revoked records.
- `tools.overrides`: per-`id` allow/deny, evaluated before resolution; deny
  always wins (proposal). A verified registry revocation blocks even when
  an allow override names the same `id`: overrides select policy
  participation, never revocation immunity.
- `tools.refresh` (proposal): initial resolve picks the highest
  constraint-satisfying verified version; `upgrade`/refresh re-resolves
  within the constraint but never moves to a lower tool version without an
  explicit operator downgrade approval; lock replay provisions exactly the
  locked bytes after re-running current revocation, key-validity, and
  freshness authorization checks.
- Defaults: built-in registry only; no organization registry configured;
  overrides empty. A skill needing an unlisted tool fails with a refusal that
  names the tool, constraint, policy, and the exact remediation (add a
  registry, or install the tool on PATH where policy permits).

Option C's `verified` mode, approval store, mirror resolver, refined
per-scope PATH composition, and system-probe reuse ship only after the
operator answers the owner, service, key, and policy questions below. B
ships with its minimal provisioned-only binding only.

## Security considerations

Threat model and trust boundaries (all options; B/C deltas noted):

- **Hostile skill author.** The author controls the manifest, hence `id`,
  `alias`, and the version constraint — but never the fetch location,
  bytes, or trust verdict (proposal). Under B the worst case is a
  dependency on a tool the operator's registries do not carry (fail closed)
  or a constraint that resolves to an older signed record (still
  operator-reviewed bytes, but see the downgrade paragraph below).
  Alias-squat risks (two skills, one `alias`) are handled by B's minimal
  binding: same-scope alias collisions and shared-bin-path version
  conflicts refuse with a structured error, following the one-owner rule
  analogous to `core.md:213` (proposal). Enforced `script-worker-v1`
  commands keep the core §4.1.1 rule: PATH is built from exactly the
  resolved interpreter plus resolved declared `exec` names, the inherited
  PATH is discarded (`core.md:335-343`), and a tool dependency never widens
  it (proposal).
- **Downgrade policy (proposal; distinct from snapshot rollback).**
  `registry.md` §5 protects snapshot high-water (`version`/`log_size`/
  `head`/`merkle_root`), not semantic tool versions: a current snapshot can
  still carry an older tool release. Initial resolve therefore picks the
  highest constraint-satisfying verified version; refresh/`upgrade`
  re-resolves within the constraint but never moves to a lower tool version
  without explicit operator downgrade approval; replay provisions the locked
  version after current authorization checks (below) and never silently
  upgrades or downgrades. A lower tool version inside a newer snapshot is
  not a rollback violation — it is a downgrade event governed by this
  policy.
- **Author-controlled downloads.** Structurally excluded from B declarations
  (proposal): clients never fetch a manifest-supplied URL. Under C's
  `verified` mode the client may resolve from the metadata mirror, but the
  mirror is untrusted input — only artefacts whose upstream checksum
  verifies AND whose signature/attestation verifies against the
  operator-pinned expected publisher and subject for that tool identity
  become records (proposal), and policy decides whether clients resolve at
  all.
- **Registry compromise.** A compromised organization registry can serve
  malicious bytes for identities it signs. Mitigations, all reused from
  `registry.md`: Ed25519 signatures over CCJ-1 bytes (§§1–2), rollback
  protection via persisted high-water (§5), freshness bounds, out-of-band
  trust-anchor updates (§2.1), and deny-wins federation adapted to tool
  records (proposal): every enabled tool registry is queried in configured
  order, malformed/unmatched/unverifiable records are ignored with a
  warning as in §4, any verified revocation covering the candidate artefact
  — proposed match keys `(id, version, os, arch, sha256)` or
  `(id, record-digest)` — blocks before positive selection, and only then
  does the first verified non-revoked record win. Example: a built-in-layer
  permit plus a later-layer revocation of the same artefact resolves to
  blocked. Per-tool overrides and a revocation list give the operator a
  kill switch (proposal); deny always wins and a verified revocation
  overrides an allow entry. There is no availability-preferring mode in B:
  an unreachable trusted tool registry fails the operation with a
  `tool_registry_unreachable_during_install`-class gate notice naming the
  registry and every tool resolved without complete revocation evidence
  (proposal, mirroring the `registry_unreachable_during_install` gate in
  §4 and the manager §7.1 hardened posture). The stated residual is
  availability: B fails closed where audit `advisory` policy would proceed
  (see §4's stated revocation-hiding residual).
- **Signature and key rotation.** Follow `registry.md` §2.1 exactly: overlap
  pin sets, sign with the new key only after overlap deployment, persist
  rollback state keyed by canonical URL across rotation, remove a
  compromised key immediately. Tool registries add no new key semantics.
  Adapted consequence (proposal): tool records and snapshots verified
  solely by a removed key no longer verify, and replay of bytes whose
  record key was removed fails authorization rather than proceeding from
  the store.
- **Mirror and resolver compromise (C; proposal).** A checksum plus "a valid
  signature" alone does not establish the intended tool: without an
  independent binding, a mirror can substitute a different legitimately
  signed artefact or supply its own verification key. The proposed binding
  is per-tool expected upstream identity: each tool `id` maps to allowed
  upstream publishers and subjects (for example pinned cosign identities,
  SLSA provenance builders, or minisign keys) plus the expected artefact
  digest for the resolved version/platform; verification succeeds only when
  the checksum matches AND the signature/attestation verifies against an
  allowed identity for that `id`. Upstream identity revocation is part of
  the policy: a removed publisher key or builder identity fails
  verification. This mirrors `registry.md` §2 (verification against
  currently pinned keys, not arbitrary keys) and §7 (an embedded
  `public_key` MUST NOT bootstrap trust). The metadata mirror is therefore
  untrusted input that can cause denial, or propose bytes that MUST fail
  the binding check when the signer or subject is unexpected — it cannot
  mint trust by itself. The resolver job is the privileged verifier
  boundary: a compromised resolver can mint records, so its output enters
  organization snapshots only through reviewed, signed changes, and nothing
  the resolver emits is trusted by clients until it appears in a
  registry-signed snapshot. Mirror transport integrity is by hash
  throughout; trust is by the registry signature plus the upstream binding.
- **TOCTOU and staging.** Downloads land in operation-private staging,
  verify (hash, then signature/attestation against the expected publisher
  and subject where the record claims it — proposal) before publication,
  and publish into a content-addressed, read-only-sealed store under the
  manager-home mutation lock (manager §2.5 pattern; proposal). Lock replay
  re-verifies hashes AND re-runs current authorization (revocation,
  key-validity, freshness — proposal); a changed upstream artefact is a
  `tool_snapshot_changed`-class failure, never a silent update.
- **Version probes (issue #108 §6; C only).** Probing a PATH tool's version
  executes an operator-selected probe from a registry entry, never author
  bytes — but it still executes a host binary during planning (proposal).
  B performs no probes and trusts only provisioned copies for constrained
  tools. If probes prove unmodellable, C likewise falls back to
  provisioned-only (open question 8).
- **Offline, replay, and air-gapped behavior (proposal with cited
  mechanics).** Three operations with different authorization:
  (1) initial resolve requires current registry evidence (verified
  snapshot within freshness bounds per §5, verified non-revoked record);
  (2) refresh/`upgrade` re-resolves and applies the downgrade rule above;
  (3) replay provisions the locked bytes only after current authorization:
  the locked record must still be non-revoked, its signing key still
  pinned (per §2.1, objects signed solely by a removed key lose trust),
  and its snapshot/freshness evidence still valid within §5 bounds and §8
  offline grace. Local store hash presence alone never authorizes replay —
  this follows manager §2.1 (a cache hit MUST NOT bypass attestation or
  revocation gates) and `registry.md` §8 (stale grace keeps a cached
  pre-revocation response valid only up to the grace, with the stated
  revocation residual). Registry and artefact mirrors are configurable
  (for example an internal mirror); verification is by hash so mirrors
  stay untrusted transport. A fully air-gapped host needs a pre-seeded
  store plus pinned registry snapshots, and the pre-seeded snapshots
  expire per §5 maximum age (default seven days) and §8 grace unless the
  operator re-seeds or explicitly re-authorizes them: there is no
  network-dependent fallback and no promise of indefinite air-gapped
  success from hash presence alone. The intentional availability residual
  is documented: expired air-gapped evidence fails closed until the
  operator acts.
- **Audit interaction (proposal).** Provisioned-tool resolution must be
  visible to source audit (CIP-0005): the resolved tool identity, record
  digest, and registry/key identity belong in the audit evidence, and
  provisioned tool directories must not leak ambient credentials into
  analyzer child environments under the CIP-0005 Design §3 single child
  environment policy (CIP-0005 lines 99–112: allowlist plus unconditional
  secret exclusions; PATH/HOME remain operator trust inputs and the filter
  is not a filesystem sandbox).

## Compatibility and migration

- Existing `system` commands keep their exact meaning (`core.md:210-213`,
  frozen schema behavior in core §1). OS tools stay presence-checked; no
  existing manifest is reinterpreted.
- The new dependency kind arrives as a new skill-manifest schema version
  (proposed schema 9) with the usual downward version gates (core §4
  table): older readers reject it with the upgrade error rather than
  ignoring it. Tool declarations live in the member skill manifest
  (`agent-skill.json` / legacy `csk-skill.json`, core §4), whose versions
  are independent of Skillfile versions (`skillfile-sources.md` §1).
- Locks extend as a new versioned schema without relabeling history
  (proposal): the current `skillfile-lock-v1` schema is closed at both the
  root and member objects (`additionalProperties: false`), so tool entries
  require a proposed `skillfile-lock-v2` that adds a per-member resolved
  `tools[]` list (identity, resolved version, per-platform hashes, source
  registry, system-or-provisioned choice, record digest). Existing
  `Skillfile.lock.json` v1 files stay valid and tool-less and MUST NOT
  attest tool currency.
- Staleness follows collection-versus-member identity correctly:
  `manifest_sha256` is the CCJ-1 SHA-256 of the entire parsed *declaring
  Skillfile* (`skillfile-sources.md` §3, lines 161–170), not of member
  skill manifests — so changing a member's tool declaration while leaving
  `Skillfile.json` unchanged does NOT change that hash and does NOT
  produce `source_lock_stale`. Member byte changes are governed by locked
  package identity and `content_sha256` with explicit refresh
  (`skillfile-sources.md` §3): replaying a lock against a member whose
  tool declaration changed fails with `source_snapshot_changed` unless an
  explicit update/refresh adopts the new member bytes and re-resolves its
  tools. Only a change to the declaring Skillfile itself stales via
  `source_lock_stale`.
- Install markers gain tool bindings in a new marker version (proposal);
  old markers remain readable on their lanes and must not attest tool
  currency.
- Rollout: option A diagnostics first (no protocol change), then the B lane
  behind operator-configured registries (default: built-in only, so default
  behavior is unchanged until the operator opts in), then C's policy modes
  only after the service decisions land.

## Specification changes

Normative sketch for a future accepted revision (proposed sentences, not
current requirements):

1. **Declaration:** "A skill MAY declare tool dependencies by registry
   identity, executable alias, and version constraint. The manifest MUST
   NOT carry a fetch URL, checksum, or signature for a tool. A manager
   MUST resolve tools only from operator-configured registries."
2. **Resolution:** "Resolution queries every enabled tool registry in
   configured order; any verified revocation covering the candidate
   artefact blocks before positive selection, and only then does the
   first ordered layer holding a verified non-revoked record for
   `id@version@os/arch` satisfying the constraint win. An unknown
   identity, an unsatisfiable constraint, a verified revocation, an
   unreachable trusted tool registry, or a failed verification MUST fail
   the operation with a refusal naming the tool, the constraint, the
   policy, and the remediation."
3. **Records:** "Tool registry records MUST be resolved and flat: exact
   version, per-platform URL, format, file map, SHA-256, and a `trust`
   marker of `signed`, `checksummed`, or `pinned`. Clients MUST NOT
   evaluate templates."
4. **Trust:** "Tool registries MUST use the `registry.md` §§1–2 signature
   envelope, §2.1 rotation, and §5 rollback rules. Deny-wins revocation
   applies federation-wide before positive selection; an unreachable
   trusted tool registry fails the operation with a gate notice naming
   the registry and every tool resolved without complete revocation
   evidence."
5. **Upstream binding (C `verified` mode):** "On-demand resolution MUST
   verify the upstream checksum AND a signature/attestation against the
   operator-pinned expected publisher and subject for that tool identity.
   A valid signature from an unexpected signer MUST be refused."
6. **Lock and replay:** "The lock MUST record each tool's identity,
   resolved version, per-platform hashes, source registry, record digest,
   and system-or-provisioned choice. Replay MUST provision exactly those
   bytes after re-running current revocation, key-validity, and freshness
   authorization; revoked bytes, bytes whose record key was removed, or
   expired evidence MUST fail, never provision from the store. Changed
   bytes MUST fail, never update."
7. **Downgrade:** "Refresh MUST NOT move to a lower tool version without
   explicit operator downgrade approval. A lower tool version inside a
   newer snapshot is a downgrade event, not a rollback violation."
8. **Transaction:** "Tool download and verification happen in
   operation-private staging before the manager-home transaction; store
   publication and marker writes are journaled targets with the §2.5
   rollback rules, retaining protected-boundary and preimage revalidation
   and distinguishing immutable-store retention from mutable-target
   rollback."
9. **Offline:** "A manager MUST satisfy offline installs from the local
   store only when current authorization (revocation, key-validity,
   freshness within §5/§8 bounds) still holds, else fail with a
   structured error; it MUST NOT fetch from a new source to satisfy an
   offline install."
10. **Exposure:** "A provisioned tool MUST be exposed only to the declared
    commands of dependent skills; same-scope alias collisions and
    shared-bin-path version conflicts MUST fail. Adding a tool dependency
    MUST NOT widen an enforced `script-worker-v1` PATH."

Schemas: a new tool-dependency object in the proposed skill-manifest
schema 9; a tool-record schema for registry snapshots; a proposed
`skillfile-lock-v2` (per-member resolved `tools[]`; v1 stays closed and
tool-less) and a new marker version; a registry-service profile section
if the operator charters a tool registry service. Conformance:
resolution vectors (constraint satisfaction, two-phase order, override
precedence, revocation-in-later-layer, unreachable-later-layer,
allow-vs-revocation), refusal vectors (unknown, unsigned, revoked,
stale, hash-mismatch, signer-substitution, valid-signature/wrong-subject,
undeclared alias, duplicate alias, shared-scope version conflict),
replay vectors (exact-byte provisioning, snapshot-changed, revoked
locked bytes, removed signing key, expired freshness/grace, lower
version in newer snapshot), and offline vectors (authorized store-hit
success, store-miss structured failure, no new-source fetch).

Adoption produces Decision record(s) for the tool-declaration schema and
the tool-registry trust profile, cross-linking this CIP. The orchestrator
assigns free Decision numbers. Adoption and prioritization remain operator
actions.

## Implementation plan

Proposed sequence, **not scheduled tasks**. Sizes are relative review units:
S = one narrow surface; M = one production path plus its vectors.

| Order | Leaf / size | Consumes and produces |
| --- | --- | --- |
| 1 | Spec and Decision adoption, M | Approve the decisions above; freeze the declaration, record, lock, refusal, and offline vectors. No runtime work before operator acceptance. |
| 2 | Hint/diagnostic improvements (option A), S | Better missing-command diagnostics and readiness reporting. Independently useful; no protocol change. |
| 3 | Registry-only resolution and store, M | Ordered registry configuration, two-phase revocation-then-selection verification, staging download, content-addressed sealed store, B minimal provisioned-only binding with collision refusal (no probes). |
| 4 | Lock, marker, and transaction integration, M | Proposed lock-v2 per-member tool entries, replay/refresh with current authorization and downgrade approval, marker bindings, journaled publication and rollback, `tool_snapshot_changed`-class diagnostics. |
| 5 | Audit-evidence integration, M | Resolved tool identity in audit evidence per CIP-0005; no credential leakage into analyzer environments. |
| 6 | Policy modes and approvals (option C), M | `verified`/`prompt` modes, approval store, per-tool overrides, revocation list — only after the service decisions. |
| 7 | Mirror resolver service (option C), M | Metadata mirror, lazy resolve-verify-sign pipeline, reviewed snapshotting. Service-owned, not client-owned. |

Leaves 6–7 wait for the owner/service/key/policy decisions. Leaf 3 must not
advertise coverage for tools no configured registry carries.

## Test plan

Proposed implementation gates; **none is claimed to have passed here**.

Drive the built manager executable with a scratch home, a fixture signed
registry, and synthetic tool artefacts. Required vectors per surface, each
with positive and negative cases: declaration validation (constraint
grammar, alias rules, rejected URL/checksum/signature fields); resolution
(two-phase order, override precedence, deny-wins revocation, revocation in
a later layer blocks a built-in permit, unreachable later layer refuses,
allow override versus verified revocation blocks); refusal rows (unknown
identity, unsatisfiable constraint, unsigned record, revoked record, stale
snapshot, hash mismatch, signer substitution, valid-signature/wrong-subject
— each naming tool, constraint, policy, remediation); replay (exact bytes,
snapshot-changed failure, revoked locked bytes fail, removed signing key
fails, replay after freshness/grace expiry fails, lower tool version in a
newer snapshot treated as downgrade event); offline (authorized store-hit
success, store-miss structured failure, no new-source fetch); transaction
(failed verification preserves prior state byte-for-byte; rollback
restores journaled targets); exposure (declared-only launcher visibility,
enforced PATH unwidened, undeclared provisioned alias refused, duplicate
aliases refused, conflicting shared-scope versions refused, no silent
shadowing, explicit system-vs-provisioned reporting for C probes).

Narrowing mutants that must fail: resolve from manifest URL when present;
skip signature check for one layer; accept a stale snapshot for one
registry; skip the federation-wide revocation scan and accept the first
layer; accept a valid signature from an unexpected publisher; treat hash
mismatch as update; satisfy offline install from network; provision
locked bytes without current authorization; downgrade without explicit
approval; expose a provisioned alias to an undeclared command; shadow a
PATH tool silently. Publish observed/expected ratios per platform. No
claim from simulation alone; run real child launches on each supported
platform.

## Open questions for the operator

### Decisions needed

1. **Registry owner and service.** Who publishes, reviews, and signs tool
   registry snapshots, and is there a registry service or only
   file-distributed snapshots? Recommend: charter one operator-owned
   snapshot pipeline before leaf 3, even if it starts as reviewed files;
   no client resolves from a registry with no owner.
2. **Signing keys.** Which keys sign the built-in and organization
   snapshots, and where do operators obtain pins out of band?
   Recommend: Ed25519 pins distributed with the manager release for the
   built-in snapshot, operator-configured pins for organization
   registries, rotation per `registry.md` §2.1.
3. **Default policy.** Ship option B's fixed `registry-only`, or also
   charter option C's `verified`/`prompt` modes now? Recommend:
   `registry-only` only, until the mirror and approval-store designs are
   accepted.
4. **Client vs service resolution for `verified` mode.** If C is chartered,
   do clients resolve on demand or only consume pre-signed records?
   Recommend: service-only resolution; clients consume pre-signed records,
   keeping verification work and mirror trust in one place.

### Design questions

5. **Manifest shape.** New `dependencies.tools` block, or an extension of
   `system` commands with an optional registry identity? Recommend: a new
   block — extending `system` risks reinterpreting frozen schema behavior
   (core §1).
6. **Identity scheme.** Canonical own namespace with the upstream catalogue
   as one resolver, or the upstream `owner/repo` identities directly?
   Recommend: own namespace with documented resolver mapping, so identity
   survives upstream renames.
7. **Built-in registry distribution.** Ship in the manager release or fetch
   as a signed snapshot on first use? Recommend: ship a pinned snapshot
   with the release (zero-config, no first-use network trust decision).
8. **Version probes vs provisioned-only.** Registry-declared PATH probes,
   or trust only provisioned copies for constrained tools? Recommend:
   provisioned-only first; add probes only with an execution model the
   operator accepts.
9. **Upstream expected-signer policy (C `verified` mode).** Who owns the
   per-tool allowed publisher/subject pins and their revocation, and where
   are they distributed? Recommend: the registry owner publishes the
   expected-signer map inside organization snapshots (same signature and
   rotation as records); clients pin it like registry keys and refuse
   unknown publishers.
10. **Downgrade and air-gap re-authorization posture.** How does the
   operator approve a downgrade, and how do pre-seeded air-gapped
   snapshots get re-authorized after expiry? Recommend: explicit
   per-operation downgrade approval (never a persistent "allow older"
   flag), and air-gapped re-seeding via a signed checkpoint file verified
   against pinned keys per `registry.md` §5 (never an automatic grace
   extension).

Accepting the recommendation implies the spec/Decision leaf and the
bounded B-lane leaves above. Until acceptance, this packet is ready for
review as research only.
