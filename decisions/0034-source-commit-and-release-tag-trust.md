# Decision 0034: Separate source commits from release-tag authority

## Context

Reviewed human-signed source commits can land without rewriting their signed
objects. The earlier squash-only checklist rejected such a commit when its
authorized source key was absent from the release trust root. Adding that key
to release trust would improperly expand release-tag authority. The verifier
also accepted locally trusted signatures before checking branch containment.

## Decision

Amend source provenance policy to accept the explicitly authorized source key
in `source.allowed_signers`, plus existing release signers through the separate
fixed `maintainers.allowed_signers` input. Every target must be contained in
fetched `origin/main`. Source integration may use reviewed exact-head
fast-forward; preserve the GitHub-created, API-verified squash alternative.
Fix repository, branch and API roots in source-owned code and reject overrides
and uncertainty. Require local signed material before delegated API acceptance.

The source role's public-key fingerprint is
`SHA256:rE/sRlfdFt/vT5y5yukDCsq4aFtC48pbWsq9z4hm8MA`.
This is a source-only authorization under the existing signed-source mandate.
It grants no tag authority. Keep the release trust file byte-identical;
release CI must verify the tag with that file alone, bind the exact endorsed
target, and retain all containment, review, version and platform gates.
Both distinctly scoped trust files accompany release archives for audit.

This is an explicit trust-policy amendment requiring independent security
review before landing, not producer-only trust adoption or a claim that the
previous release checklist already allowed this source route.

## Alternatives

Adding the key to the shared release trust root would expand tag custody.
Rewriting every reviewed head via squash loses its reviewed signed identity.
Accepting arbitrary GitHub-verified authors, ambient user trust or configurable
API/ref roots would admit unapproved identities or unknown ancestry. Skipping
provenance or reporting the historical failed run as repaired would conceal a
real policy failure. These alternatives are rejected.

## Compatibility impact

Existing release signers remain valid source signers and the GitHub-created
squash route remains available. Existing release-tag trust and immutable tags
are unchanged; no key is removed, rotated or declared revoked. The historical
main check name is retained. Arbitrary API/repository/branch CLI overrides are
removed; this repository's policy roots are fixed. Trusted signatures outside
the default branch now refuse, closing the previous containment bypass.
There is no protocol wire/schema change or release performed by this decision.

## Security impact

SSH signatures are checked with explicitly selected repository trust inputs,
format and verifier, independent of ambient Git config selectors. The
commit-only file is not a second tag trust root: OpenSSH uses the same `git`
namespace for both, so consumer separation is essential. Source policy files
and verifier changes are themselves reviewed trust changes. A passing source
check supplies neither independent review nor release endorsement. Native,
platform-key, protected-branch and infra-exit boundaries remain unchanged.
