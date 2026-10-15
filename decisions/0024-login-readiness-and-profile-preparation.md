# Decision 0024: Login readiness and profile preparation

## Status

Accepted by owner decision 2026-10-15 (D1, D7–D9, D11, D13), adopting
[CIP-0015](../cips/CIP-0015-login-readiness-and-profile-preparation.md) leaf 1.
The [normative amendment](../protocol/login-readiness.md) is the contract;
acceptance is not implementation shipment or platform qualification.

## Context and decision

Home currency does not establish login readiness. Curator owns metadata-only
presence and preparation; consumers apply its policy rather than inspecting
homes. Freeze a closed three-value caller-session row, user-owned native/file/
keychain selector and typed store projection. Preparation does not activate;
headless preparation is report-only; login refuses shared writes.

Retain the strict all-participants aggregate, explicitly accepting that an
ambient OpenCode participant cannot currently return green. This preserves the
CIP's refusal to assert unobserved readiness. Allocate the distinct
`environment_credential_store_unsupported` code for Curator selector/mapping
refusals; retain `environment_credential_unsupported` for native selectors.

## Alternatives

Agent status execution or inference probes violate metadata-only status.
Cached machine-wide readiness crosses session boundaries. Silently excluding
unknown ambient rows weakens the accepted aggregate. Activation during prepare
changes unrelated future launches. Reusing the native-selector code obscures
the failed policy layer. Silent fragment extension lets old readers lose policy.

## Compatibility impact

Existing profiles retain native storage and current selections. Check becomes
stricter, including ambient OpenCode; ordinary status and explicit install/
resolve remain usable. Released schemas and fragment revisions remain unchanged.
Standalone schemas occupy a separate namespace. Full manager-config/status/
fragment containing revisions remain coordinated publication work; no token is
invented here. Old readers reject unsupported members/revisions. Muse admission
and other-repository implementation remain separately owned.

## Security impact

Presence is neither authentication nor remote-launch authority. No credential
payload, account identity or token digest enters status. Failed metadata is
unknown; no store fallback, helper invocation, lease acquisition or automatic
login follows. Trusted interactive children own credential I/O; no transcript
capture is permitted. Existing source, isolation and migration gates remain.
