# Proposed Muse native v4 successor schema

**PROPOSAL; not adopted.**

**Origin:** Requested by Ivan on 2026-11-09: shared homes reuse the ordinary Keychain login; Linux support is required.

[CIP-0033](../../cips/CIP-0033-muse-native-credential-form.md) and
[Draft Decision 0038](../../decisions/0038-muse-native-credential-form.md)
propose the complete [successor schema](launch-env-fragment-v4-muse-native.schema.json).
It retains `fragment: "launch-env-fragment-v4"`, with a distinct schema `$id`.
Only explicit joint producer/consumer qualification may select this successor
after acceptance; the wire token alone cannot establish native support.

The frozen [v4 schema](../v1/launch-env-fragment-v4.schema.json) remains
byte-identical at SHA-256
`afc824151de968d1bd2c3c9a15d6bf4024ad6920f0f0a56351ee755b56aa9847`.
Its file-only Muse interpretation and all later allocated carriers remain.
The successor changes only Muse's store/environment pairing: file plus the
literal, or native with exactly four XDG parents and no backend variable.
Non-Muse policy, required members, closed objects and root-context rules stay.

[Cases](../../conformance/muse-native-v1/README.md) enter the existing schema
gate. Platform/shared eligibility, one-parent paths, provenance, no backend in
the composed child and actual store behavior require semantic/runtime checks.
Schema acceptance grants no activation or native authentication qualification.
