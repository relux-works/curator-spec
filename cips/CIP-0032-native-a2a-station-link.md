# CIP-0032: Native a2a station-link handover

- **Status:** Review
- **Owner:** Curator protocol proposal; decision: operator
- **Created:** 2026-11-09
- **Related:** [Draft Decision 0037](../decisions/0037-native-a2a-station-link.md); [CIP-0024](CIP-0024-agent-stations.md); a2a owner design note v0
- **Affects:** [native command-root admission](../protocol/profile-command-root-admission.md#native-station-link-handover-review); curator-run launcher; SAM typed environment carriers; a2a Courier; grants station-link coordination

## Summary

Replace native identity selection's proposed credential-directory flag with a
Courier station link derived from the canonical environment managed home. The native route
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
a runtime receipt. The subsequent **a2a owner statements, Courier protocol
version 1** bind the file grammars, wire shape, rotation and published constants below. These replace
the earlier socket regex proposal. No implementation source or runtime was
inspected to qualify those statements.

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
All three entries have link count exactly 1 and mode exactly 0600, as required
by the public [a2a enroll PR #366](https://github.com/relux-works/a2a-swarm/pull/366)
and [C1 PR #367](https://github.com/relux-works/a2a-swarm/pull/367). Any entry with
another link count refuses `native-station-entry-links`; socket/identity modes
other than 0600 refuse `native-station-entry-mode`, retaining the key-mode code.
These are content-free sub-reasons under `native-environment-not-registered`.
`courier.sock` is a regular path file, not the socket itself. The removed directory
flag and legacy credential-directory handover are refused.

The canonical-path rule is an **a2a owner statement, Courier protocol version 1**.
Enrollment resolves D's parent once with `EvalSymlinks` and works on the canonical
path. Launcher uses the canonical `EvalSymlinks` managed home M, then `M/.a2a`,
for both delivery and comparison. Input-home ancestor aliases are allowed;
symlinks at `.a2a` or any entry remain refused. Each canonical ancestor through M
must be caller/root-owned and not group/world-writable, except root-owned sticky
directories; M itself must belong to the launching effective UID.

An **a2a owner statement, Courier protocol version 1** closes the former
record question: no enroll-time station path is stored. Every reader (enroll's
rotate path, station-side client, launcher admission) requires the supplied D
to be absolute and `EvalSymlinks(D) == D`; the caller passes canonical form.
Launcher checks its derived `M/.a2a` before planning. Relative, unavailable
resolution and noncanonical paths refuse as environment not registered with
Courier, with stable content-free sub-reasons. No location is fixed or recorded
across launches; the reader never rewrites its supplied D or enrolls on launch.
A re-pointed input-home alias can yield a new canonical path that passes this
path check. That location has no enrolled entries unless enrollment ran there;
entry admission still applies. Canonical ancestor checks do not cover alias
components outside the resolved chain. Courier hello still authenticates by
secret and UID, not path.
No record storage or read API is needed. Ancestor and link/entry symlink guards
remain binding.

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
explicit rotate with `--rotate` on both sides, never per launch. The emitted
JSON object has exactly `socket`, `identity`, `station`, `secret_b64`, followed
by LF; enroll refuses unknown keys. Wire shape and rotation are **a2a owner
statements, Courier protocol version 1**. Launcher never registers/enrolls,
mints secrets or writes the link. A later a2a admin socket may let the Curator manager drive the same pipe;
this future seam is not implemented or claimed here.

Per **a2a owner statements, Courier protocol version 1**, the a2a Go module
package `courier` publishes `StationKeyLen = 32` and `ProtocolVersion = 1`.
The key is 32 raw bytes with no encoding or appended newline. Admission checks
regular file, no symlink, station ownership, exactly 0600 and metadata size
against `courier.StationKeyLen` at that pinned protocol version because a2a
publishes it; this is not a launcher-owned size. Curator-run accepted either
form and preferred no size stat; the mandatory size check is not attributed to
that preference. Which a2a module version is pinned and the pin/lookup mechanism
are curator-run implementation work, not claimed here. The model consumes
supplied pinned constants, never key contents, and refuses an unavailable pin.
`identity` is exactly one ASCII line matching `^[a-z0-9._=-]{1,64}\n`, whose
name equals the selected identity; spaces, BOM and extra/missing lines refuse.
Courier v1 states `courier.sock` is a regular nonsymlink file containing UTF-8 P
plus exactly one LF. P starts with `/`, has no NUL, CR, LF or BOM, and has byte
length 1..103 including `/`, excluding LF. Check bytes explicitly; non-ASCII
paths are allowed. This replaces the earlier socket regex statement. The file
is the only socket-path source; no per-OS default is assigned here. Missing/bad
link facts use operator-facing code
`native-environment-not-registered` (environment not registered with Courier),
with the packet's finer codes as content-free sub-reasons. Courier and grants
review one handover shape, not separate invented authentication designs.

## Security considerations

Courier's separate OS user keeps credentials and state outside station reach.
Station UID is the launching process's effective UID for this milestone.
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
assertion and a valid positive neighbour. Named guard-removal plants expose
forbidden cases at their validation stages. Closed-entry-set plants exercise
the namespace helper before later value checks; they do not claim a complete
mutated launch succeeds. A credential-looking extra is explicit. Additional
controls cover derived-home delivery, the removed flag, inherited credential
conflicts, unresolved size and an attempted secret-content read. Existing
session-selector and four-key scrub plants remain. Identity-line vectors cover
space, BOM, uppercase, 65 characters, missing LF and two lines with valid length
1/64 neighbours and named format-guard plants. Key sizes 31/33 refuse against the
supplied a2a contract value 32; ownership and unavailable-pinned-contract controls
remain. Exact-mode vectors include directory 0500/0300/0711 and key 0400/0640.
Link-count vectors reject 2 for each entry; socket/identity mode vectors reject
0644 and 0640, each beside a valid complete station. Removing the link-count
guard must lose those named refusals. The key observation exposes only five
metadata attributes (including link count); attribute, get, items,
values and iteration secret-read plants fail by name. Socket vectors cover
ASCII 103/104-byte and Unicode 103/105-byte boundaries, LF, CRLF, embedded LF,
NUL, BOM, missing LF, empty/relative/invalid UTF-8 and symlink refusal. P9's valid
LF-file probe is admitted; planting the old whole-file absolute check kills
that positive control.
Canonical-path vectors pair canonical and canonicalized-aliased-home admission
with relative/uncanonicalized/later-noncanonical reader-path refusals and
unavailable resolution. Mismatched requested-home binding and relative
canonical-home results refuse by the home-resolution reason; removing only the
binding conjunct is killed by `requested-home-mismatch`. Unsafe ancestor,
home-owner and link/entry-symlink refusals retain root-sticky positive controls. Each has a valid neighbour and
unchanged-input assertion. Dropping path equality is killed by
`path-later-noncanonical`; dropping the write-permission guard is killed by
`group-writable-parent`. All facts are
supplied: no live resolution or Courier authentication is qualified.
Run the named Python tests and repository validator; outputs
are model checks, not filesystem, SAM, Courier or Linux runtime qualification.

## Resolved questions and remaining dependencies

Both questions from the first round are closed by supplied a2a owner and
curator-run answers: registration is per environment through the external
Courier-user/station-user pipe, with no launch caller; the a2a enroll contract
owns the current 32-byte key length. The canonical enrollment-record question
is also closed: readers check absolute canonical paths; Courier stores none.
The a2a owner now states the published constants; the launcher module-version
pin and contract consumption remain curator-run implementation work. Real
enrollment qualification and the later admin-socket seam also remain future work.
An unavailable contract value refuses; no launcher-owned
fallback or implicit admin integration is permitted. Review status, draft
Decision and CLOSED gates are unchanged.

## Open questions

No new owner question is introduced by this revision.
