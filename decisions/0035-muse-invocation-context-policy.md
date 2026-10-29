# Draft Decision 0035: Separate Muse invocation context policy

## Status

Candidate for review. Canonical signing, independent review, required checks and
publication remain pending; this record does not claim acceptance or adoption.

## Context

[CIP-0017](../cips/CIP-0017-muse-root-context-and-credential-store.md)
and [environments §10.2](../protocol/environments.md#102-the-launch-environment-fragment)
bind a materialized Muse root context to strict form-specific exclusion.
A deliberate native interactive invocation needs a separate effective choice
without falsifying the manager's materialization fact or weakening defaults.

## Proposed decision

Keep the raw v4 fact exactly `{"exclusive":true}`, complete fragment
identity/digest, profile/lock, provenance, home, resolve/repair rules and default
strict mappings. Only an explicitly selected native interactive managed Muse
invocation with that valid fact may waive effective foreign-personal exclusion
and its exclusion qualification, reporting MIXED. Omit the consumer exclusion
override; add no enabling flag or forced cached `true`. MIXED guarantees neither
foreign loading nor qualified exclusivity. No inherited environment/config/profile
or permission default may select it. Hosted, exec, serve, dry-run and headless
workers gain no exception.

Require a separate finite versioned typed consumer request, one SAM-owned
immutable bound decision, matching capability and seal successor, and fidelity
through both vendor and system-only paths. Mode-less `ChildEnv` consumes the
same bound mode. Missing, unknown, dropped, replaced or unsupported choice,
identity, capability or fidelity refuses; replacing allowance with strict cannot
be successful fulfillment. No fragment member, schema revision, installed API,
version or runtime refusal-code spelling is allocated here.

Protect both `context.foreign_personal_rules` and
`context.foreign_personal_skills`, including combined switches and equivalent
spellings/alternate option positions, even if redundant. Preserve opaque data
after the provider separator; unknown policy grammar refuses. No command-position
form switch may convert an allowed interactive invocation into exec or serve.
SAM alone owns native argv and final verification of the exact composed process
immediately before execution; a consumer-only check cannot bridge composition
to native execution.

## Alternatives

Rewriting or removing the raw fact loses provenance and corrupts the producer
contract. A persistent or inherited allowance weakens strict defaults and
unattended boundaries. Native-option overrides create a second policy authority.
A launcher-only receipt check leaves final composition unverified. These
alternatives are rejected by the proposed contract; retaining strict-only behavior
remains the compatibility path for consumers without the new capability.

## Compatibility impact

All released schemas, vectors and existing default-strict argv fixtures remain
unchanged. The [separate semantic corpus](../conformance/environments-muse-invocation-policy/README.md)
adds specification-data declarations without a public wire format. Unsupported
explicit policy fails closed with no old-API retry. Independent review of the
canonical signed candidate and required checks precede normative publication.
That publication precedes one accounted SAM writer, independent review,
required checks, signed integration and a signed compatible release under an
unused version. Exact launcher pin/typed implementation and separate native
qualification and adoption remain gates; this record grants none of them.

## Security impact

The allowance changes effective exclusion authority for one explicit native
interactive invocation only.
Every unrelated binary/build, model/effort, help, permission, network, credential
and integrity gate remains. Credential Recommendation 2 and recorded workspace,
skills-discovery and model-visible residuals are unchanged. Historical evidence,
general skills guidance, strings or help alone cannot qualify a new build/form,
including exact 1.4.14 precedence or interactive semantics.

## Validation boundary

The corpus and `tools/test_muse_invocation_policy.py` check closed declarations,
required positive/negative coverage and preservation metadata. They do not parse
native argv, implement a launch policy, validate actual provenance, observe
loading/precedence, authenticate, seal or execute a process. Real implementation,
native qualification and hosted repository CI remain separate delivery gates.
