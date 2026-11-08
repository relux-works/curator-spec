# Draft Decision 0035: Closed machine Claude output-limit selection

## Status and context

Proposed 2026-11-05; not adopted or implemented. See
[CIP-0029](../cips/CIP-0029-machine-claude-output-limit.md).
The operator needs one machine launch setting rather than profile or native-home
edits. Existing machine extensions are closed, and schema 8 is already pending
for notification metadata.

## Proposed decision

Add only `extensions.claude_env.BASH_MAX_OUTPUT_LENGTH`, as a canonical decimal
string in 1..65536, to the next per-account machine carrier. Absence or `{}` is
inert. Validate before any side effect; deliver only to Claude child launches
or resumes, without mutating profiles, locks, parents, native homes or running
sessions. Other runtimes receive no contribution and remain usable. Reject
unknown names, malformed/duplicate input and invalid values without reflecting
input in diagnostics.

The [contract](../protocol/machine-claude-env-proposal.md) is the complete
proposal. Configuration **9** and projection **`curator.launcher-config/3`** are
allocated to `extensions.claude_env`, conditional on schema **8** and
**`curator.launcher-config/2`** in
[Core #216](https://github.com/relux-works/curator/pull/216) staying as is.
This allocation leaves this decision **Proposed** and CIP-0029 **Review**;
adoption is the operator's decision. Version or admitted-shape changes in #216
require re-review and coordinated schema/vector updates. The
[closed containing-schema drafts](../schemas/machine-claude-env-v1/README.md)
await #216's accepted final shape. The complete containing schemas must preserve
every admitted predecessor form before any producer emits the successor;
draft publication does not satisfy or defer that gate.

## Alternatives and effects

Reject a free-form environment map and native-home hotfixes. The allowlist
limits credential/proxy/permission injection, and the finite integer range
bounds configuration without claiming native output or storage behavior.
Existing admitted extensions and environment policy are preserved; old readers
fail closed on the unsupported version. No released schema, trust root,
profile identity or lock bytes change. Production entrypoint and real-runtime
witnesses remain required after implementation; this decision grants no
launch, credential, installation or cross-account authority.
