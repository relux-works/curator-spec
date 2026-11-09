# Draft Decision 0037: Native a2a station-link handover

## Status

Proposed 2026-11-09; not Accepted or adopted. [CIP-0032](../cips/CIP-0032-native-a2a-station-link.md)
is in Review. All root-emission gates remain CLOSED.

## Context

Native identity delivery previously proposed a caller-selected credential
location. The a2a owner design note v0 instead puts credentials and operational
state under a separate Courier OS user and supplies a station link. The grants
lane proposes the same handover shape, intended as one design.

## Proposed decision

Use `--native --a2a <identity>` and derive the link at the environment managed
home's canonical `EvalSymlinks` result, then its `.a2a` directory. Refuse the removed directory flag. Require a station-UID
owned nonsymlink 0700 directory with exactly `courier.sock`, `identity` and
`station.key`, all regular nonsymlink files. Require an absolute socket-path
value from that file alone (no per-OS default), an exact one-line identity
`^[a-z0-9._=-]{1,64}\n` matching the selected name, and a station-owned 0600 key
whose metadata size equals a2a Go package `courier.StationKeyLen = 32` at pinned
`courier.ProtocolVersion = 1`, attributed to **a2a owner statements, Courier
protocol version 1**. It is raw bytes, no encoding or appended newline.
Unavailable pinned contract refuses. Curator-run accepted either form, preferring
no size stat; this proposal checks size because a2a publishes the constants.
The a2a module-version pin/lookup is curator-run implementation work, not claimed.
The launcher never reads key contents. Station UID is the launching process's
effective UID on this shared-UID milestone.

The canonical-path rule is an **a2a owner statement, Courier protocol version 1**:
`enroll --dir D` resolves D's parent once using `EvalSymlinks` and uses only that
canonical path. Launcher delivers and compares `A2A_CONFIG_DIR` from canonical
managed home plus `/.a2a`. Canonical ancestors must be caller/root-owned without
group/world writes, except root-owned sticky directories. The canonical home
belongs to launching effective UID. Link/entry symlinks still refuse. The same
canonicalization applies to the Codex gateway managed-home follow-up.

An **a2a owner statement, Courier protocol version 1** closes the former
record question: no enroll-time station path is stored. Every reader (enroll's
rotate path, station-side client, launcher admission) requires the supplied D
to be absolute and `EvalSymlinks(D) == D`; the caller passes canonical form.
Launcher checks its derived `M/.a2a` before planning. Relative, unavailable
resolution and noncanonical paths refuse as environment not registered with
Courier, with stable content-free sub-reasons. A path that later becomes
noncanonical fails this check; no silent rewrite, fallback or launch enrollment.
Courier stores no station path: hello authenticates by secret and UID, not path.
No record storage or read API is needed. Ancestor and link/entry symlink guards
remain binding.

The same Courier v1 owner statements bind the socket file: UTF-8 P plus exactly
one LF, where P starts with `/`, has no NUL, CR, LF or BOM, and is 1..103 bytes
including `/` but excluding the final LF. This is a byte bound, not a character
quantifier; non-ASCII paths are allowed. It replaces the earlier socket regex.

Enrollment is per environment, outside launch. As Courier user,
`register-station ... --emit -` mints the key and emits one closed JSON line;
as station user, `a2a courier enroll --dir <home>/.a2a --from -` creates the 0700
link and caller-owned entries, refusing existing entries without `--rotate`.
The key lasts for the environment and rotates on recreation or explicit rotate
with `--rotate` on both sides, never per launch. These rotation and closed-JSON
claims are **a2a owner statements, Courier protocol version 1**: the emitted
object has exactly `socket`, `identity`, `station`, `secret_b64`, then LF;
enroll refuses unknown keys.
Launcher never registers/enrolls, mints the key or writes the link. A later a2a
admin socket may let Curator manager drive the same pipe; this is a future seam,
not a claimed feature.

Use the [packet's stable refusals](../protocol/profile-command-root-admission.md#native-station-link-handover-review)
before planning, without content reflection. Missing or bad link entries mean
`native-environment-not-registered`, with fine validation sub-reasons. Retain existing Codex/Claude
carriers,
the two-key inherited comparison, four-key transport/store/token rule and
session-selector scrub. Deliver only the selected identity and derived directory.

## Alternatives

Reject keeping a credential-directory pair on this native route. Do not assign
automatic registration or secret minting to the launcher. Use the supplied owner
and launcher answers for per-environment enrollment and a2a-owned key length;
never substitute a launcher-owned length or launch-time registration.

## Compatibility impact

No released schema or signed bytes change. The unreleased native proposal changes;
legacy native credential handover is not admitted. Hosted `--a2a`, doorbells and
route selection are unchanged. No automatic migration or fallback is authorized.

## Security impact

Credentials/state/mailbox/locks leave station reach. Shared-UID stations can
still read each other's station secrets; real station isolation needs one OS
user per station. The bounded model provides no OS, authentication, live
filesystem, provider-carrier or runtime receipt. Separate adoption and native
witnesses remain required.

## Resolved questions and pending work

The [enrollment contract](../protocol/profile-command-root-admission.md#station-enrollment-contract-owner-answers-folded-into-review)
closes both former questions using supplied a2a owner and curator-run answers.
The canonical enrollment-record question is also closed by the Courier v1
owner statement: absolute canonical reader paths, no stored path. Curator-run
module-version pinning and
contract consumption, real enrollment qualification and later admin-socket integration
remain implementation work; this draft accepts or qualifies none of them.

## Open questions

No new owner question is introduced by this revision.
