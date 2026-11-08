# Draft Decision 0036: Machine Host notification carrier

## Status

Proposed 2026-11-08; not Accepted or adopted. See
[CIP-0031](../cips/CIP-0031-machine-host-notification.md).

## Proposed decision

Allocate machine configuration **8**, projection **`curator.launcher-config/2`**
and selection contract name **`curator-host-notification/1`** as specified by the
[Review contract](../protocol/host-notification-proposal.md). Preserve old `/1`
bytes and the separate schema-6 node-source family. Admit only absent, exact off
or exact Host workflow reference/digest; system policy cannot supply or lock it.

The complete containing schemas must preserve every admitted predecessor form
before any producer emits the successor. Draft publication does not satisfy or
defer that gate. CIP-0029's 9 and `/3` stack on the accepted final shape.

## Recorded owner decision and effects

Review F3 is resolved by the owner's choice: **the claude-auth editor admits
schema 8 and preserves it**, including plan/apply/restore and notification-aware
guarded equivalence. Apply that rule later to admitted schema 9. This records
the required behavior without claiming an implementation fix or qualification.
Unrelated env/auth/project edits retain selections, and no notification file
is downgraded to 7. Reject silently dropping the field or refusing all schema-8
auth edits as the chosen compatibility behavior.

This carrier is metadata only. Runtime capability, workflow/member admission,
continuing attachment, old-reader compatibility and editor effects remain
separately qualified. No credential, launch or deployment authority is added.

## Open ownership boundary

CIP-0023 has a manager-owned binding and jointly published launcher/manager
notification/event contract. No current spec assigns the named
`curator-host-notification/1` publisher or its relation to the doorbell lifecycle.
The owner must answer that question; this decision invents neither ownership
nor equivalence between workflow and binding digests.
