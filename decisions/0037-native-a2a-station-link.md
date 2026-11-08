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
home's `.a2a` directory. Refuse the removed directory flag. Require a station-UID
owned nonsymlink 0700 directory with exactly `courier.sock`, `identity` and
`station.key`, all regular nonsymlink files. Require an absolute socket-path
value from that file alone (no per-OS default), an exact one-line identity
`^[a-z0-9._=-]{1,64}\n` matching the selected name, and a station-owned 0600 key
whose metadata size equals the versioned a2a enroll contract value (currently
32 bytes, owned by a2a). Unavailable contract value refuses. The launcher never
reads key contents.

Enrollment is per environment, outside launch. As Courier user,
`register-station ... --emit -` mints the key and emits one closed JSON line;
as station user, `a2a courier enroll --dir <home>/.a2a --from -` creates the 0700
link and caller-owned entries, refusing existing entries without `--rotate`.
The key lasts for the environment and rotates on recreation or explicit rotate.
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
No new product question is introduced. Publishing/consuming the versioned a2a
contract, real enrollment qualification and the later admin-socket integration
remain implementation work; this draft accepts or qualifies none of them.
