# Decision 0029: Persist managed-home provisioning origin

## Context

A managed caller can hide the selector originally used to provision a home.
Recomputing credential authority from today's HOME or selector can reject an
unchanged custom link, accept a retargeted link or repair it to another origin.
Published closed markers contain no native-origin carrier.

## Decision

Adopt [provisioning-origin revision 1](../protocol/provisioning-origin.md): a
separate private `provisioning-origin/1` file beside the managed-home marker,
with original selector state/value, actual operator-home anchor, resolved
native root, capture provenance and exact adapter/profile/lock/target binding.
Capture precedes mutation; the record and home share atomic lifecycle and
rollback. Credential authority and caches use the record exclusively. Legacy
homes refuse until explicit trusted-input adoption. The Curator source owner
selected this contract on 2026-10-26; implementation and review are separate.

## Alternatives

Extending marker 7 changes a frozen closed carrier. Deriving authority from
current HOME or a link lets the observation redefine the expected origin.
An unversioned implementation-private field has no interoperable contract.
Record-only publication leaves home mutations outside the transaction. These
alternatives are rejected.

## Compatibility impact

A new standalone schema namespace and corpus preserve all released markers,
locks, fragments, source corpus pins and release records. Legacy homes acquire
no inferred authority. Adoption requires explicit trusted input. This additive
specification establishes no implementation delivery, live adoption or binary
rollback qualification.

## Security impact

No credential bytes are persisted. Read failures and ambiguous physical path
identity refuse; changed caller selectors cannot authorize another origin.
The manager validates exact bindings before writes, preserves native state and
uses recoverable transactions. The sidecar is manager-owned local state, not
isolation from hostile processes with the same operating-system authority.
