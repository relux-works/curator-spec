# Decision 0025: Profile-level Codex settings

## Status

Accepted under owner decision 2026-10-15 (D9, D13), corrected by owner
decision 2026-10-16 (D14), adopting
[CIP-0018](../cips/CIP-0018-profile-level-codex-settings.md) implementation-plan
leaf 1. The [normative amendment](../protocol/profile-codex-settings.md)
defines the contract; acceptance is not implementation qualification.

## Decision

Context packages retain the closed `codex_settings` member and inheritance
machinery, but no package key is admitted in this revision. New keys need a
reviewed typed vocabulary extension; credential-store, credential-source and
account keys, including `cli_auth_credentials_store`, are never admissible.
Curator rejects nonempty declarations before resolution with
`context_manifest_invalid`, no replacement lock, fragment or launch data.
The inheritance machinery retains ordinary closure weights, winning-tie
refusal and provenance for future admitted keys, never for credential stores.

CIP-0015 section 2's user-owned machine selector
`credential_store.<profile>.<env-id>` (default `native`) is the only store
source. Curator fills the typed launch override from it: `file` maps to `file`,
qualified `keychain` to `keyring`, and `native` emits no override. Packages,
overlays, locks and repositories cannot select or refine this choice.
The launcher consumes effective settings and emits stable TOML scalar `-c`
pairs on all managed paths. Nobody applies settings by rewriting Codex-owned
configuration. Host tool policy remains disjoint and authoritative.

This deliberately narrows environments section 10.3's no-launch-influence
statement only for reviewed package keys, admitting none under D14, without
changing its registry-only variable boundary. Credential-store launch influence
is machine-owned. Differing third-party contributions can deny resolution, failing
closed rather than bypassing policy. Native credential storage still defines
sharing; explicit isolated/file admits only a separately prepared private
credential. Absent settings preserve existing eligibility and behavior.

## Compatibility and remaining gates

Released schemas and corpus pins remain unchanged. New member schemas and
structural/semantic cases live in a separate unreleased namespace. Coordinated
successor carrier allocation remains open with the parallel amendments; the
member schemas are not full envelope validators and allocate no wire token.
Strict successor schemas/cases and consumer support precede producer activation.

Scalar CLI precedence over a conflicting seed, login, app-server and refresh
effects remain unverified on the recorded Codex release. Each supported release
must be qualified before activation, together with CIP-0015 eligibility adoption.
No new behavior is inferred from a native config key or a source comment.
Later repository implementation leaves and the joint qualification leaf remain
separate work; snapshots and remote dispatch retain their own contracts.
