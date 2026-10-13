# Decision 0023: Machine base context

**Revision 2026-10-14 — Proposal revision 3.** Records the requested design;
clarifies per-lock framing, migration, lockable keys and approval rollout;
no released contract, implementation or activation changes here.

## Status

Status: Proposed — not adopted.

The operator requested the opt-in package-based machine overlay on 2026-10-13.
This record proposes the precise contract in
[CIP-0013](../cips/CIP-0013-machine-base-context.md); the request to draft it
is not acceptance of this record or qualification of an implementation.

## Context

[Environments](../protocol/environments.md) §6 already provides machine-only
per-profile overlays with joint resolution and lock membership. Weights order
chapters, so they alone cannot guarantee that profile/project instructions do
not override a machine base. Sections 2, 5.4 and 9.4 write no root-context
output for a root lacking `context`, including pure umbrellas with
module-bearing dependencies and `default`. A binary-embedded rule set would let a manager upgrade change instructions without package
update approval, contrary to the operator's requirement.

## Proposed decision

1. Add OPTIONAL `environments.base_context`, absent by default: exactly one
   `{ name, git, range | tag | revision, directory? }` declaration. Its
   package is an ordinary §6 overlay in every current and future profile,
   including `default`. Package data never declares or changes composition.
   Do not create the illustrative `curator-root-context` package here.
2. Require explicit consent for setup adoption: confirmation of the exact
   declaration interactively or an explicitly supplied configuration value
   headlessly. Suggestions provide neither consent nor trust. Apply existing
   source allowlist, signer, strict-audit and protected-store rules unchanged.
3. Permit whole-object system locking as `environments.base_context`. Keep
   `overlays_allowed` applicable to every overlay; false plus a configured
   base fails closed as invalid effective configuration. Hardened posture
   does not enable or exempt the base.
4. Make the designated base the highest instruction authority; profile and
   project instructions cannot replace, weaken, exempt or override it. Use
   the existing weight domain's greatest endpoint for higher-weight and
   least endpoint for lower-weight, with the base winning endpoint ties.
   Placement puts it at the winning end, first or last. Conceptual layering
   remains base, profile closure including per-profile overlays, project.
   This declares authority; it does not prove model obedience or containment.
5. Record the base role by its member name in successor lock and marker
   `base_context` members and by the successor header's `base: <name>` line.
   For a profile whose lock is context-lock-v3, emit the root-context file
   even when the root has no `context`: applicable
   chapters or, with zero applicable modules, the header alone. Independently
   of base opt-in, revision 2 also writes output for pure-umbrella roots
   whose locked context dependencies declare context.
6. Unify a profile requirement for the base name through ordinary joint
   resolution, producing one member/chapter. Incompatible ranges fail
   `context_range_conflict`, never substitution by weight. Keep existing
   project/hybrid/profile skill scope precedence and launch boundaries;
   allocate no project context format or launch-fragment field.
7. Resolve the explicitly configured base on initial install. Subsequent
   addition, removal, replacement, pin movement or policy-derived weight
   change requires `profile update`, including `--all`, and the existing
   per-invocation `--confirm-system-delta` approval. Surface version/pin and
   context text deltas even for root-only modules; enable the feature only
   with the enforcing gate. Revision A rejects base_context as unsupported
   configuration; its existing system/MCP warning path is unchanged. Preserve
   the old lock/surfaces on refusal.
   Manager upgrades, use/sync/resolve/repair, status and global skill edits
   cannot move the base or its pinned contribution. Global update/upgrade
   remains fetch-only. Status reports per-profile pins/digests and makes
   configuration/role mismatch or drift non-current, read failure unknown.
8. Propose agent-environments revision 2 and new manager-config-v4,
   system-config-v3, context-lock-v3, agent-environment-marker-v4 and
   curator-root-context-v3 framing. Preserve older schemas and core names.
   Adoption requires the schemas, vectors, release notes and review under
   [GOVERNANCE.md](../GOVERNANCE.md); this record creates none of them.

## Alternatives

Repeated per-profile declarations cannot cover future profiles reliably.
Manager-embedded instructions violate package control and update consent.
Weights without an authority rule only relocate text and do not satisfy the
requested non-overridable layer. The package-overlay design is requested;
its unresolved consumer guarantees remain questions, not silent redesigns.

## Compatibility impact

Revision 1 remains frozen. Absent configuration adds nothing, even under
hardened posture or after a manager upgrade. Fresh revision-2 installs and
explicitly migrated profiles use lock-v3, marker-v4 and eligible header-v3
even without a base, omitting base role members/lines. Unmigrated profiles
retain revision-1 framing and eligibility on profile use/sync/update until
explicit migration under CIP-0013 §1.3. Unchanged inputs retain their prior
bytes. Configuring a base and ordinary profile update are not migration;
the explicit entry point is registered as an adoption question. Absent-base
composition is unchanged,
but framing bytes change on migration and pure-umbrella output is corrected.
New framing rejects unsupported versions explicitly and is adopted through
explicit migration, never by
reinterpreting old locks or markers. No core object, shared filename,
`workspace-result/1` field, project skill scope precedence or launch variable
changes. Existing sessions retain their prior context in memory.

## Security impact

A machine-wide prompt has broad influence but no extra trust, executable,
credential or configuration authority. System locking selects provenance,
not intent. Joint resolution and existing audit/signature gates remain hard;
approval precedes publication. Byte checks and declared authority are not
proof of model obedience, execution containment or protection against native
instruction truncation.

## Consequences and open questions

Before adoption, resolve CIP-0013's numbered questions: consumer authority
qualification, the first project-context consumer, the fleet overlay conflict,
approval rollout/migration, fleet-stale use, text-delta grammar, invalid
configuration refusal scope, base/root identity and mismatch handling, and
the explicit framing-migration entry point.
Conformance must cover absence, consent, default-base and pure-umbrella
output, all precedence pairs, unification, range conflict,
system locks, update approval and drift before adoption. No implementation,
qualification or activation is claimed.
