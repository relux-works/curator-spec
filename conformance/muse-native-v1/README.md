# Proposed Muse native credential cases

**PROPOSAL; not adopted.**

**Origin:** Requested by Ivan on 2026-11-09: shared homes reuse the ordinary Keychain login; Linux support is required.

See [CIP-0033](../../cips/CIP-0033-muse-native-credential-form.md) and the
[separate successor schema](../../schemas/muse-native-v1/README.md).
The corpus is outside frozen release manifests; all paths and pins are
synthetic. It does not launch a provider or inspect credentials.

The [case index](schema-cases/index.json) is consumed by `tools/validate.py`,
including the existing XDG one-parent semantic check. Run `make validate`;
focused Go controls run with `go test ./tools/muse-native -v`.
Valid neighbours cover both Muse forms, optional root absence and all four
non-Muse native policies. Invalid neighbours cover unknown/keychain selection,
backend presence/absence mismatch, overrides, foreign parents, HOME, missing
required members, root weakening and wrong revisions.

Native is already valid for every other adapter under its original rules;
there is no other adapter whose plain native selection should be forbidden.
Their native-with-overrides cases remain invalid. Go controls also replay the
entire predecessor corpus, pin frozen bytes and exercise guard mutations.
These structural/semantic checks prove no runtime login, Keychain availability,
platform/mode eligibility, refresh behavior or installed consumer support.

[Platform policy cases](policy-cases.json) pair macOS shared native with Linux
native/unset resolving to the existing file store, and explicit file on both.
They also retain isolated file mapping, explicit-keychain refusal and
unsupported native-route refusal. These are contract mapping examples, not
probes of either operating system or credential availability.
