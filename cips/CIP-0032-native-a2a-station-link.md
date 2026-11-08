# CIP-0032: Native a2a station-link handover

- **Status:** Review
- **Owner:** Curator protocol proposal; decision: operator
- **Created:** 2026-11-09
- **Related:** [Draft Decision 0037](../decisions/0037-native-a2a-station-link.md); [CIP-0024](CIP-0024-agent-stations.md); a2a owner design note v0
- **Affects:** [native command-root admission](../protocol/profile-command-root-admission.md#native-station-link-handover-review); curator-run launcher; SAM typed environment carriers; a2a Courier; grants station-link coordination

## Summary

Replace native identity selection's proposed credential-directory flag with a
Courier station link derived from the environment managed home. The native route
takes `--native --a2a <identity>` and delivers the two existing non-secret a2a
variables after validating the link. Courier holds credentials and operational
state under a separate OS user. This Review proposal opens no root-emission gate,
claims no acceptance or runtime support, and assigns no registration caller.

## Motivation and user stories

A station should use its own a2a identity without holding that identity's keys.
An operator should be able to provision several native stations with one handover
shape shared with the grants lane. The launcher must refuse a misplaced, malformed
or legacy credential directory before provider planning, without handling secrets.
A functional shared-UID launch is distinct from isolation between stations.

## Current state

At curator-spec main `aaa843965c4caaf4ededf45a0c269dddc50e0472`,
`protocol/profile-command-root-admission.md:145-150,326-330,416-470` proposes
an explicit native identity plus credential-directory pair; its bounded
`tools/native_root_admission.py:205-222` only compares and forwards that pair.
The packet is unreleased and all seven root-emission gates are CLOSED. Released
rc.14 conformance and existing hosted routing are unchanged by this proposal.
The a2a owner design note v0 supplies the station-link custody shape, not a
published byte-size contract, registration lifecycle decision or runtime receipt.
No implementation source or measured native launch is claimed inspected here.

## Design

### Options considered

1. Keep a caller-selected credential directory. This leaves credentials within
   station reach and does not meet the requested custody boundary; reject it for
   this native route.
2. Derive a closed station link at `M/.a2a`, where M is the environment managed
   home. Courier retains all credentials/state/mailbox/locks, and its operator
   mints the station secret. This matches the supplied handover shape and keeps
   secrets out of launcher argv, environment, logs and plans.
3. Make the launcher mint or register stations automatically. This would assign
   an unagreed lifecycle and operator authority; do not select it.

### Recommendation

Use option 2 for handover shape. The [packet's refusal table](../protocol/profile-command-root-admission.md#native-station-link-handover-review)
requires the private station-owned directory, exactly three regular nonsymlink
entries, key metadata, matching identity and an absolute socket-path value.
`courier.sock` is a regular path file, not the socket itself. The removed directory
flag and legacy credential-directory handover are refused.

Retain exactly the existing two-key inherited comparison, named four-key
transport/store/token removal choice and every-native session-selector scrub.
Deliver `A2A_AGENT` and derived `A2A_CONFIG_DIR` using the existing typed SAM
Codex `-c` carrier and Claude carrier, with their existing settings-precedence
and tool-shell witness requirements. No secret enters either carrier.

Courier operator-side `register-station ... --secret-out` mints the secret;
neither launcher nor agent does. Defer the registration lifecycle/caller and
secret format to the named questions below, without recommending an ungrounded
answer. The grants lane and Courier should review one handover shape rather
than receive two independently invented authentication designs.

## Security considerations

Courier's separate OS user keeps credentials and state outside station reach.
Under a shared station UID, stations can read each other's 0600 `station.key`
and impersonate each other to Courier. Real isolation requires one OS user per
station; private modes alone do not provide it. The station secret authenticates
a station but is not an a2a credential store. This proposal neither provisions OS
users nor qualifies Courier authentication.

Validate directory/entry metadata without following symlinks and bind observations
to the same directory before planning. Read only the two public values; inspect
`station.key` mode and size without reading its bytes. Refusal codes do not echo
file contents or extra-entry names. Registration, secret rotation/revocation,
atomic operator publication and real TOCTOU/peer-credential handling require
owner integration and runtime evidence; the bounded model proves none of those.

## Compatibility and migration

The environment variable names stay unchanged, but native `A2A_CONFIG_DIR` now
names a closed link, never a legacy credential store. There is no automatic
credential copy, migration, registration or fallback. An inherited credential
locator conflicts with the derived locator; credentials under the derived path
are an extra-entry refusal. Existing hosted `--a2a`, doorbell wiring and route
selection stay unchanged. No released schema, signed bytes or rc.14 vectors change.

## Specification changes

Update the native packet and its pure model/tests. Record this trust-boundary
proposal in draft Decision 0037, pending adoption. Keep every gate CLOSED and
runtime witnesses owed. README and the unresolved-question index identify the
new Review proposal; no status becomes Accepted.

## Implementation plan

1. Obtain joint answers to the registration and secret-contract questions.
2. Review one Courier/grants handover shape and operator-side publication contract.
3. Separately implement launcher no-follow checks and typed carrier integration
   behind the existing gates; preserve hosted routing and scrubs.
4. Obtain native non-root Linux tool-shell/Courier receipts, including refusals,
   unchanged state and UID boundaries, before root emission or runtime adoption.

These are dependencies, not an assignment of a registration component or an
implementation claim.

## Test plan

The bounded model takes no-follow metadata plus only the identity/socket public
values. Each directory/entry/key/identity/socket negative has an unchanged-input
assertion, a valid positive neighbour and a guard-removal plant exposing that
specific forbidden case at its validation stage. Closed-entry-set plants exercise
the namespace helper before later value checks; they do not claim a complete
mutated launch succeeds. A credential-looking extra is explicit. Additional
controls cover derived-home delivery, the removed flag, inherited credential
conflicts, unresolved size and an attempted secret-content read. Existing
session-selector and four-key scrub plants remain. Fixture sizes do not allocate
a production format. Run the named Python tests and repository validator; outputs
are model checks, not filesystem, SAM, Courier or Linux runtime qualification.

## Open questions for the operator

1. **To the a2a owner and curator-run:** Is station registration per launch or per environment, and which component calls Courier operator-side `register-station ... --secret-out` at launch? No caller or lifecycle is assigned here, and the available note does not ground a recommendation.
2. **To the a2a owner and curator-run:** What exact `station.key` byte size/encoding does the shared Courier/grants station-link handover require, and how is that contract supplied to launcher admission? The note does not allocate it. The model takes an explicit expected size, refuses when it is unresolved, and uses fixture-only sizes without choosing a production format.
