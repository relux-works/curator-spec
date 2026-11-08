# CIP-0031: Machine Host notification carrier

- Status: Review
- Authors: Ivan Oparin
- Created: 2026-11-08
- Target: machine configuration and launcher metadata
- Decision: [Draft Decision 0036](../decisions/0036-machine-host-notification.md)

## Motivation and evidence

Core #216 at `f5d7cd472db973b9864f87e5ca4526f20e4a893c` and
launcher #92 at `802895a2fbbc3e49a7bb01ac59674343ec1f720d` agree on a closed
Host selection, but implementation agreement does not allocate a protocol
carrier. The [contract](../protocol/host-notification-proposal.md) records the
source evidence and the publication/qualification boundaries. CIP-0029 needs
this predecessor before it can publish configuration 9 and projection `/3`.

## Recommendation and alternatives

Allocate configuration **8**, **`curator.launcher-config/2`** and the identifier
**`curator-host-notification/1`**, with machine-only closed metadata. Keep older
projection bytes unchanged and schema 6 in the node-source family. Reject
adding fields to `/1`, general executable/endpoint selection and implicit
workflow authorization. Absence and explicit off both disable notification;
only explicit off survives as a selected value.

The complete containing schemas must preserve every admitted predecessor form
before any producer emits the successor. Draft publication does not satisfy or
defer that gate. The [containing schemas](../schemas/host-notification-v1/README.md)
and [conformance corpus](../conformance/host-notification-v1/README.md) cover
published predecessor fields and the selection. No Accepted status or emission
permission follows from this Review publication.

## Compatibility and security

Retain proxy/auth, credential-store, environment, waiver, build, script and
execution forms. Refuse unsupported versions, system selections/locks,
unknown/mixed fields and malformed JSON without input reflection. Core only
exports metadata; it neither reads secrets nor enrolls or starts a runtime.

Owner decision on review F3: **the claude-auth editor admits schema 8 and
preserves it** through plan/apply/restore. Notification participates in guarded
equivalence, proxy survives auth edits, and no edit writes notification under
schema 7. The same rule later applies to admitted schema 9. This decision is
recorded now; the inspected implementation still needs that fix and validation.

## Plan and tests

1. Review the allocation, complete shapes, fixed diagnostic mapping and owner
   question; publish accepted prose/schemas/vectors only after owner adoption.
2. Reconcile Core with the accepted spec, repair its current-main build conflict
   and F3 editor path, then re-review the exact rebased implementation head.
3. Qualify old projection byte identity and real env/auth/project editor
   roundtrips with no-write/stale-plan/no-downgrade controls.
4. Publish the separately owned Host contract, verify actual receiver capability
   and admitted workflow/member lifecycle, then qualify runtime behavior.

The checker includes positive controls and intended-reason negative vectors.
Five instrument plants weaken schema-7 admission, host closure, off closure,
lowercase digest and `/2` identity independently; each must fail its named
witness, with the restored corpus passing. Specification validation is not an
editor, consumer, receiver or runtime witness.

## Open owner question

CIP-0023 assigns concrete protected doorbell binding publication to the manager
owner and joint notification/event publication to launcher and manager owners.
It does not assign `curator-host-notification/1`. Name that contract's publisher
and its relation to `session-doorbell-v1`/`binding_sha256` before activation;
see contract §6. Do not infer an owner from the implementation author.
