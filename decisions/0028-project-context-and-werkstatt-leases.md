# Decision 0028: Project-context authority and Werkstatt leases

## Status

Accepted; decision: operator, 2026-10-22.
Adopts the closed leaf-1 subset of
[CIP-0002](../cips/CIP-0002-project-context-in-managed-launches.md#leaf-1-candidate-grammar),
including the [amended root/system ruling](../cips/CIP-0002-project-context-in-managed-launches.md#owner-decisions-2026-10-22).
Schema/vector publication and normative amendments are coordinated halves of
leaf 1. This decision claims no implementation or native qualification.

## Context

A registered checkout's approved context needs its own authority and persistent
home identity. Repository-native discovery, native trust and a profile lock alone
do not prove approval, exclusion of other control sources or safe concurrent
updates. A content digest is not a grant, and a finished snapshot does not prove
that the original native home is idle.

## Decision

Adopt [project context leaf 1](../protocol/project-context.md): protected
registration, individually approved immutable context/whole-skill/inline-MCP
items, an ordered generation, derived composition, separate lease binding,
verified control receipt, exact-release adapter evidence and closed fragment
members. Keep the selected profile unchanged. Permission authority stays with
manager-programmed default-deny policy and grants; memory is off in leaf 1.
Inline MCP additionally waits for its companion normative grammar and admission.

Apply the operator's amended Q1 permanently: preserve the profile's root and
system context. Approved project context is additive only, below the profile
root in the managed home's composed AGENTS.md/CLAUDE.md. Render the base profile
document, then project-general and environment-specific documents in approved
item order, deeper scope after shallower, with exactly one additional LF between
non-empty documents. System parts retain their separate channel and joining
rule. The separate replacement item is withdrawn, not deferred to a later slice.
Whole-skill overlay does not override that profile context invariant.

Use a persistent protected checkout × profile × environment Werkstatt and sparse
worktree, with immutable control records separate from native mutable state.
Acquire `prepared` before fragment publication, transfer durable ownership to
the actual reserved session as `active` before provider start, and retain the
original-home lease through detach and snapshot completion until authoritative
termination and ownership/state reconciliation. Unknown liveness retains roots;
PID/TTL alone cannot release them. Busy repair, switching and skill/CLI sync
wait or refuse before writes; idle updates recheck leases transactionally.
Resume retains the original composition and current authority without a new
session fallback. GC retains leases, compositions and referenced artifacts.

The exact refusal names and effects are registered in
[environments §10.6](../protocol/environments.md#106-project-context-diagnostics).
The [owned-literal note](0013-execution-ownership-and-launch-plans.md#project-context-owned-literal-boundary-2026-10-22)
keeps general tracked PATH transport deferred rather than encoding it as caller
literals or widening existing closed plans.

## Alternatives

Raw repository/native discovery makes code review or folder trust confer control
authority. Rewriting the profile home swaps controls under other sessions.
Per-digest new native homes impose fresh login/state cost and do not themselves
exclude discovery. PID/TTL leases lose detached or indeterminate owners.
Replacing profile root/system context contradicts the operator's permanent
additive ruling. These alternatives are rejected.

## Compatibility impact

This is a separately versioned optional capability; legacy launches remain
explicit legacy compatibility, not strict off. Existing profile locks, markers,
manager configuration, fragments v1–v6, hosted/tracked records and frozen corpus
bytes are unchanged. Leaf-1 members do not allocate an outer revision token.
Emission waits for a complete project-capable outer carrier and its supported
required-understanding consumer; old-version refusal precedes authority lookup.
Rule dialects, stacks, memory opt-in delivery, Windows, other adapters and general
remote/tracked transforms remain deferred, not inferred from these records.

## Security impact

Approval binds the exact checkout, item/closure, environment and ceiling;
repository bytes cannot grant it. Complete snapshot/lock/receipt verification
prevents entry substitution and changed native controls from becoming a baseline.
Qualified exclusion covers startup, late discovery, resume and child entry,
with manager-controlled permissions, memory-off and explicit empty MCP sets.
Refusal preserves prior home/approval state. Credential delivery retains its
separate channel; no secret enters project metadata. The first trusted-mode
loader boundary is not containment of hostile same-user executable code.

## Adoption evidence and limits

The [normative amendment](../protocol/project-context.md), environments
§§1–8/10–12 and manager §§3/12 define the prose half of leaf 1. The separate
schema/conformance leaf owns member schemas, paired positive/negative vectors
and narrowing controls; neither that publication nor metadata-only checks
qualify a filesystem implementation, lease race, native loader or launcher.
No route or adapter support follows from this decision alone.
