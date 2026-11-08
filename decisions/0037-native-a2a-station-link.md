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
value, matching identity and a 0600 key of the Courier-contract size. The launcher
checks key metadata only and never reads its contents. Courier operator-side
`register-station ... --secret-out` mints the key; launcher and agent do not.

Use the [packet's stable refusals](../protocol/profile-command-root-admission.md#native-station-link-handover-review)
before planning, without content reflection. Retain existing Codex/Claude carriers,
the two-key inherited comparison, four-key transport/store/token rule and
session-selector scrub. Deliver only the selected identity and derived directory.

## Alternatives

Reject keeping a credential-directory pair on this native route. Do not assign
automatic registration or secret minting to the launcher. Registration lifetime,
caller and exact secret format remain owner questions, not implicit decisions.

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

## Open decisions

The [registration questions](../protocol/profile-command-root-admission.md#station-registration-questions-open)
are addressed jointly to the a2a owner and curator-run. Neither a registration
caller nor a production secret-size/encoding contract is assigned here.
