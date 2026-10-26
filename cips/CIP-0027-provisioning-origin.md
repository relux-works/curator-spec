# CIP-0027: Persist managed-home provisioning origin

- **Status:** Accepted
- **Accepted:** 2026-10-26, Curator source-owner decision; canonical schema and implementation review remain separate.
- **Owner:** Curator maintainers
- **Created:** 2026-10-26
- **Related:** BUG-261018-2h258j — native-home-from-managed-caller; Curator PR179; [Decision 0029](../decisions/0029-provisioning-origin.md)
- **Affects:** Environments sections 7.4, 8 and 10.1; Curator provisioning, verification, repair and adoption

## Summary

Persist a separate private `provisioning-origin/1` record beside each managed
home marker. Capture original selector state/value, actual operator anchor,
native root and exact profile/lock/target binding before mutation. Use the
record as credential authority and require an atomic home lifecycle. Legacy
homes refuse until explicit trusted-input adoption.

## Motivation and user stories

An unchanged custom-origin credential must remain usable when Curator runs
from a managed caller. Retargeting that link to today's default must conflict;
repairing an absent link must restore the original origin only.

## Current state

At Curator main c7b39b5474f68db1064256a91e59a9cdfb66b49b,
`internal/envprofile/managed.go:186` resolves native homes through current
process state, and `internal/envprofile/credential_policy.go:87` derives policy
from that observation. Environments rc.14 sections 7.4 and 8 define passthrough
and closed marker ownership but contain no persisted native root. Independent
review probes at PR179 successor d04af717ea4166b874c8d830d87326348c8f466e
fail all four A/B authority scenarios; absent-root and link-variant controls
pass on the tested Darwin filesystem. That is bounded implementation evidence,
not cross-platform qualification or proof of this new contract.

## Design

### Options considered

Recomputing today's selector loses original authority. Extending marker 7
changes a frozen carrier. An unversioned private field lacks a shared contract.
A separate versioned record preserves old carriers and supplies explicit
capture, authority and lifecycle semantics.

### Recommendation

Adopt [revision 1](../protocol/provisioning-origin.md) and its standalone schema.
Source-owner selection is recorded in Decision 0029. Command details belong to
the implementation; trusted-input `adopt` and fail-closed legacy behavior are
mandatory. No credential bytes are included.

## Security considerations

Validate full bindings and existing-ancestor physical identity before mutation.
Refuse unreadable, stale or missing authority; never infer it from symlinks or
current HOME. Journal home changes and origin together, with rollback and
recovery. This is local provenance, not isolation from a hostile shared UID.

## Compatibility and migration

Frozen markers, locks, fragments and release metadata remain unchanged. Old
homes refuse until explicit trusted-input adoption. Old binaries are not
qualified to maintain homes under this amendment. Source acceptance authorizes
no live adoption or installation.

## Specification changes

Decision 0029, normative provisioning-origin revision 1, a separate closed
schema, schema/authority vectors and publication-entry controls form the
additive specification change. No release version or signed release is changed.

## Implementation plan

1. Publish canonical grammar and lifecycle requirements for source review.
2. Implement record capture, authority/cache binding and atomic home lifecycle
   in existing Curator PR179, including explicit adoption and removal.
3. Run original independent probes plus transaction, cache and lifecycle
   controls; obtain exact-head source review and required green checks.

## Test plan

The specification checks positive/negative schema and authority vectors with
planted publication failures. Curator must exercise real provisioning, repair,
adoption, removal, read-only refusals, cache revalidation and crash recovery.
Original upstream witness bytes remain independent qualification input. Relevant
Darwin, Linux and Windows lanes must report separately; no skipped or failed
lane is inferred green.

## Open questions for the operator

None pending for the selected source contract. Implementation issues and review
findings remain owned by the existing source unit and do not imply a new live
maintenance grant.
