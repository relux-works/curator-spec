# CIP-0033: Muse native credential form

- **Status:** Draft — PROPOSAL, not adopted
- **Owner:** Protocol maintainers; decision pending
- **Created:** 2026-11-10
- **Related:** [CIP-0017](CIP-0017-muse-root-context-and-credential-store.md); [launcher #98](https://github.com/relux-works/curator-agent-launcher/pull/98)
- **Affects:** Environments §§7.4 and 10.2; rc7-carriers §4; v4 schema successor; Curator and launcher implementations
- **Origin:** Requested by Ivan on 2026-11-09: shared homes reuse the ordinary Keychain login; Linux support is required.

## Summary

Propose a second Muse credential form for shared macOS homes: selection
`native`, four managed XDG parents and no `TBH_CREDENTIAL_BACKEND`.
Retain the file form and publish a separate successor schema without changing
frozen v4 bytes. This proposal grants no producer activation or qualification.

## Motivation and user stories

A shared home may need the operator's existing native login. Forcing the file
backend bypasses Muse's default Keychain-first lookup on macOS. An isolated
home still needs the file store; a global native login cannot isolate homes.

## Current state

At specification main `1c69e3125f40696584e3f3c26bb4c4dda757d5a4`, environments
§§7.4 and 10.2 and rc7-carriers §4 require effective file for managed Muse.
CIP-0017 records why: global Keychain scope, non-desktop access failures,
measured file login and unmeasured refresh. Those evidence bounds remain.
Launcher #98 at `0e09b4810ff470c381350bc91ac5f602925f426a` proposes native
with no backend variable and refuses mixed forms; implementation is evidence
of a requested contract change, not authority for it. No new vendor probe is
claimed here.

## Design

### Options considered

1. Keep file-only: preserves the current contract but cannot reuse a
   Keychain-first native login through the proposed form.
2. Rewrite frozen v4: rejected because hash-pinned readers and negative cases
   would change meaning silently.
3. Publish a separate complete v4 successor schema and require explicit joint
   producer/consumer support before emission. Retains old readers and file
   behavior, with a required-understanding rollout obligation.

### Recommendation

Propose option 3, with the exact eligibility, merge and refusal rules in
[environments §7.4](../protocol/environments.md#74-credential-passthrough-provisioning-seeds-and-isolation).
The effective selection is `native`: Muse's default global Keychain-first
store, with its existing file fallback, not a guarantee of Keychain success.
Do not silently force file when this eligible native form is selected.
On Linux, native/unset MUST resolve to the existing effective file store,
with the file-form fragment and existing native-file sharing checks. It does
not refuse for lack of Keychain. Explicit file remains valid on both platforms;
isolated homes and other non-macOS native/unset mappings also retain file.

## Security considerations

A schema cannot prove platform, isolation mode, credential availability or
provenance. Producers must establish eligibility; consumers must preserve the
closed form and reject admitted backend overrides. Native selection grants no
account/process isolation and may require desktop Keychain access. Preserve
existing readable-target checks, conflict-preserving migration, private modes,
no secret inspection and unmeasured refresh bounds. No credential is copied,
exported, stripped or silently migrated to make the form work.

## Compatibility and migration

Old v4 and every later allocated carrier retain their bytes and meanings.
The successor retains the v4 wire discriminator; it is selected by explicit
producer/consumer capability qualification, never inferred from that token.
Old file-only readers reject native. Unsupported native delivery refuses;
no downgrade, relabeling or retry is permitted. Existing file fragments
remain valid. The published file-only readiness carriers do not acquire a
native backend: native readiness remains unknown pending its own qualification.

## Specification changes

Candidate edits to environments §§7.4 and 10.2 and rc7-carriers §4 are marked
PROPOSAL and apply only after acceptance. Add the complete successor schema,
paired corpus, existing-validator dispatch and Go controls. [Draft Decision
0038](../decisions/0038-muse-native-credential-form.md) records compatibility
and security impact. CIP-0017's original acceptance is not acceptance of this
amendment; its historical text is preserved.

## Implementation plan

1. Obtain contract review, then decide this proposal.
2. Publish the accepted contract/schema before producer and consumer adoption.
3. Qualify joint source selection, all renderers, merge refusals and supported
   platform/mode mapping before any native emission. No release is claimed.

## Test plan

Run repository validation and CI commands. Paired schema cases admit native
and file, reject mixed/unknown policies and preserve every non-Muse adapter.
Go controls pin frozen bytes, compare predecessor verdicts, mutate the Muse
branch to witness widening/narrowing, and check one-parent semantics through
the existing validator. Runtime acceptance must exercise resolve → plan →
composition with actual platform/mode eligibility, four XDG paths, unchanged
HOME, absent native backend and refusal before child start. Repeat native
lookup and file controls on qualified platforms without inspecting secrets;
refresh and concurrent writes remain separate. Corpus tests prove no login,
Keychain access or live execution.

## Open questions for the operator

1. Adopt the native shared-macOS exception while retaining Linux native-to-file?
   Recommended: review this bounded proposal; the request does not select a
   fragment revision or waive frozen-schema and conformance requirements.
2. Accept the same-discriminator successor with explicit joint qualification?
   Recommended: require exact supported schema selection; absent that
   agreement, retain file-only and refuse native emission.
