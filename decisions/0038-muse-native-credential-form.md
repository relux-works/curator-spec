# Draft Decision 0038: Muse native credential form

## Status

PROPOSAL, 2026-11-10; not accepted or adopted. [CIP-0033](../cips/CIP-0033-muse-native-credential-form.md)
is Draft.

**Origin:** Requested by Ivan on 2026-11-09: shared homes reuse the ordinary Keychain login; Linux support is required.

Existing file-only contracts remain in force until acceptance; this candidate enables no emission.

## Context

The original v4 grammar forces file storage for Muse. A shared macOS home
could instead reuse Muse's default native lookup, while global Keychain scope
still makes that form unsuitable for isolated homes.

## Proposed decision

Publish a separate complete v4 successor schema admitting exactly file with
the backend literal, or native without it. Scope native emission to shared
macOS homes with native/unset machine selection. Effective selection `native`
means Muse's global Keychain-first default with existing file fallback, not
forced Keychain success. Linux native/unset resolves to the existing effective
file store and file fragment; lack of Keychain does not cause refusal. Explicit file stays valid on
both platforms, and other non-macOS/isolated native mappings retain file.
Unsupported native delivery refuses without fallback; mixed forms and
admitted backend overrides refuse before execution. Keep credential-source,
readable-target and preservation checks, root-context and XDG/HOME boundaries.

## Alternatives

Retaining file-only does not support the proposed native login reuse.
Changing frozen schema bytes or silently widening existing readers breaks
hash-bound compatibility. A future full wire revision remains an alternative
if joint same-discriminator capability selection cannot be agreed.

## Compatibility impact

The frozen v4 schema and its pin stay byte-identical. V5 and later carriers,
released corpora, manifest digests and release metadata remain unchanged.
Only explicitly qualified producer/consumer pairs may select the separate
successor after acceptance; the v4 token alone does not establish support.
Old readers reject native, and file remains valid. No installed migration,
readiness-carrier extension or release is performed.

## Security impact

Native exposes the existing operator-global store, not home isolation or
Keychain availability. No secret read/export, automatic migration or silent
file downgrade is authorized. Existing file-link safety and refresh limits
remain; wire validity cannot prove platform/mode or effective credential use.
