# Decision 0030: Policy-derived workspace trust events

## Context

The operator's Q1 decision of 2026-10-27 places dangerous runtime settings
under the operator role. The keeper exercises that authority on the owner's
approval through Curator commands. Packages never own it. Pre-approved
unattended checkout trust needs provenance distinct from a direct trust-add
action; existing CIP-0020 A1 events do not express that distinction.

## Decision

Publish [CIP-0020 §2.1](../cips/CIP-0020-workspace-trust-ledger.md#21-policy-derived-grants-q1-first-slice)
and its separate private `workspace-trust-policy-grant-v1` event. Bind the
complete approved policy entry digest, registered exact checkout and canonical
destination, environment/lane identity, limited trust/hook surfaces, approving
operator, actual actor and revocation history. Never mint `explicit-grant` on
the operator's behalf. Packages cannot supply or widen authority.

Unknown unattended checkouts refuse with `workspace_untrusted` before provider
start. Editing/removing an entry revokes all derived events before conservative
per-key cleanup; expiry or identity drift lapses them. Resolve/repair never
renew consent. Require qualified destination and hook admission at each start.

## Alternatives

Reusing `explicit-grant` falsely attributes a direct operator act. Package
declarations or native trust seeds bypass operator authority. Prefix matching,
normalizing aliases into consent and falling back to implicit-launch let an
unapproved checkout inherit trust. These alternatives are rejected.

## Compatibility impact

The original A1 event schema/corpus and released portable carriers remain
unchanged. The new carrier is private state only. Environments integration is
separately owned; this decision publishes the amendment, not a new environment
fragment or active adapter. It changes no permission interface. Unattended
lanes' owner-selected default without the vendor sandbox requires separate
runtime mapping and is never inferred from a trust grant.

## Security impact

Issuer strings require independent authenticated operator approval. The
repository tuple records consent provenance, not content authenticity. A
same-UID process may tamper with private policy until CIP-0024 protection is
deployed. Native key ownership conflicts retain bytes and pending cleanup
while authorization remains revoked; active sessions are not terminated.
Unqualified/unreadable hook state refuses even apparently hook-free launches.

## Validation boundary

The [paired corpus](../conformance/workspace-trust-policy-grant-v1/README.md)
and publication-entry control check specification consistency. Authentication,
protected storage, crash recovery, retained filesystem identity, command-free
SSH configuration evaluation and actual vendor hook behavior remain production
qualification obligations. No runtime implementation is delivered here.
