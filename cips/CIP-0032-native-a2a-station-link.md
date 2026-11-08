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
claims no adoption or runtime support. Supplied a2a owner and curator-run answers
settle per-environment enrollment outside launch and the a2a-owned key length.

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
The a2a owner design note v0 supplies the station-link custody shape, not
a runtime receipt. Subsequent supplied owner/launcher answers settle the enrollment
shape and current key length below; no implementation source or runtime was
inspected to refresh those answers.

## Design

### Options considered

1. Keep a caller-selected credential directory. This leaves credentials within
   station reach and does not meet the requested custody boundary; reject it for
   this native route.
2. Derive a closed station link at `M/.a2a`, where M is the environment managed
   home. Courier retains all credentials/state/mailbox/locks, and its operator
   mints the station secret. This matches the supplied handover shape and keeps
   secrets out of launcher argv, environment, logs and plans.
3. Make the launcher mint or register stations automatically. This conflicts with
   the supplied per-environment enrollment contract; do not select it.

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

The station is the managed environment. Enrollment is per environment, outside
launch: as Courier user, `register-station ... --emit -` emits one closed JSON
line; as station user, `a2a courier enroll --dir <home>/.a2a --from -` consumes it,
creates the 0700 directory and caller-owned entries, refusing existing entries
without `--rotate`. Keys last for the environment and rotate on recreation or
explicit rotate. Launcher never registers/enrolls, mints secrets or writes the
link. A later a2a admin socket may let the Curator manager drive the same pipe;
this future seam is not implemented or claimed here.

The versioned a2a enroll contract owns the key length, currently 32 bytes per
the a2a owner's enrollment answer. Admission checks regular file, no symlink,
station ownership, 0600 mode and metadata size against that supplied contract
value; it never reads key contents and still refuses an unavailable contract.
`identity` is exactly one ASCII line matching `^[a-z0-9._=-]{1,64}\n`, whose
name equals the selected identity; spaces, BOM and extra/missing lines refuse.
The only socket-path source is the absolute value in `courier.sock`, with no
per-OS default here. Missing/bad link facts use operator-facing code
`native-environment-not-registered` (environment not registered with Courier),
with the packet's finer codes as content-free sub-reasons. Courier and grants
review one handover shape, not separate invented authentication designs.

## Security considerations

Courier's separate OS user keeps credentials and state outside station reach.
Under a shared station UID, stations can read each other's 0600 `station.key`
and impersonate each other to Courier. Real isolation requires one OS user per
station; private modes alone do not provide it. The station secret authenticates
a station but is not an a2a credential store. This proposal neither provisions OS
users nor qualifies Courier authentication.

Validate directory/entry metadata without following symlinks and bind observations
to the same directory before planning. Read only the two public values; inspect
`station.key` owner, mode and size without reading its bytes. Refusal codes do not echo
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

1. Carry the supplied per-environment enrollment and a2a-owned length answers
   into implementation review; the two former questions are closed.
2. Review one Courier/grants handover shape and operator-side publication contract.
3. Separately implement launcher no-follow checks and typed carrier integration
   behind the existing gates; preserve hosted routing and scrubs.
4. Obtain native non-root Linux tool-shell/Courier receipts, including refusals,
   unchanged state and UID boundaries, before root emission or runtime adoption.

These are implementation dependencies, not runtime receipts or adoption of the
future admin-socket seam.

## Test plan

The bounded model takes no-follow metadata plus only the identity/socket public
values. Each directory/entry/key/identity/socket negative has an unchanged-input
assertion, a valid positive neighbour and a guard-removal plant exposing that
specific forbidden case at its validation stage. Closed-entry-set plants exercise
the namespace helper before later value checks; they do not claim a complete
mutated launch succeeds. A credential-looking extra is explicit. Additional
controls cover derived-home delivery, the removed flag, inherited credential
conflicts, unresolved size and an attempted secret-content read. Existing
session-selector and four-key scrub plants remain. Identity-line vectors cover
space, BOM, uppercase, 65 characters, missing LF and two lines with valid length
1/64 neighbours and named format-guard plants. Key sizes 31/33 refuse against the
supplied a2a contract value 32; ownership and unavailable-contract controls remain.
Run the named Python tests and repository validator; outputs
are model checks, not filesystem, SAM, Courier or Linux runtime qualification.

## Resolved questions and remaining dependencies

Both questions from the first round are closed by supplied a2a owner and
curator-run answers: registration is per environment through the external
Courier-user/station-user pipe, with no launch caller; the a2a enroll contract
owns the current 32-byte key length. No new product question is introduced.
The concrete published versioned contract and its launcher consumption, real
enrollment qualification and the later admin-socket seam still need separate
implementation work. An unavailable contract value refuses; no launcher-owned
fallback or implicit admin integration is permitted. Review status, draft
Decision and CLOSED gates are unchanged.
