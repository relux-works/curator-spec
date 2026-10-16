# Profile Codex settings member schemas, revision 1

These unreleased Draft 2020-12 schemas freeze the added members of
[the normative amendment](../../protocol/profile-codex-settings.md), separately
from the byte-frozen `schemas/v1` corpus. They reuse its portable identifier
and precedence definitions by relative reference.

| Schema | Validated projection |
|---|---|
| `codex-settings-v1` | The package settings object, empty only under D14 |
| `manifest-members-v1` | Only the optional added `codex_settings` manifest member |
| `lock-members-v1` | Effective settings, contribution records and precedence |
| `marker-members-v1` | Required recorded effective settings |
| `fragment-members-v1` | Environment discriminator and optional machine-selected `file`/`keyring` launch override |

These are closed **member projections**, not full wire envelopes. They MUST
NOT be substituted for complete manifest, lock, marker or fragment validation.
Existing wire revisions still reject the additions. The module revision does not allocate enclosing version numbers.
[Containing carriers](../rc7-carriers-v1/README.md) separately publishes full
successors and cases. Runtime qualification, strict consumers and covered
delivery remain required before producer enablement.

Schema checks cannot prove duplicate-key/encoding rejection, package closure
membership, declaration/pin equality, weight selection, identity currency,
credential backend effects, host isolation or runtime delivery. See the
[corpus and exact test command](../../conformance/profile-codex-settings-v1/README.md)
for structural coverage and the explicit semantic qualification boundary.
