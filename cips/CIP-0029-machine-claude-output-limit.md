# CIP-0029: Machine-scoped Claude output limit

- **Status:** Review
- **Owner:** Curator maintainers; decision: operator
- **Created:** 2026-11-05
- **Related:** [proposed contract](../protocol/machine-claude-env-proposal.md), [draft Decision 0035](../decisions/0035-machine-claude-output-limit.md), [Core notification carrier](https://github.com/relux-works/curator/pull/216)
- **Affects:** machine configuration, its typed launcher projection, and Claude child-environment delivery

## Summary

Add a closed `extensions.claude_env` object to per-account machine configuration,
initially admitting only `BASH_MAX_OUTPUT_LENGTH`. An optional canonical decimal
string from 1 through 65536 is contributed only to Claude children at normal
launch or resume. A valid shared declaration leaves other runtimes usable
without that contribution. This is an unreleased proposal: schemas and fixture
results do not establish implementation or native runtime effect.

## Motivation and user stories

An operator needs a common bounded Claude output limit without editing every
profile or a running session's native settings. Owner direction, 2026-11-05:
«т.е это явно конфигурация ланча котороая общая для всех на тачке».
The requested initial value is `"8000"`.

- Configure one limit for the account, then receive it at the next normal
  Claude launch or resume without changing profile or lock bytes.
- Keep using other admitted runtimes with the same machine configuration;
  they receive no contribution from this extension.
- Reject malformed or unauthorized selections before publishing a usable
  plan, starting a child or writing state, without reflecting supplied input.

The carrier is per OS account. Cross-account system authority, the generic
shell extension and active-session updates are outside this proposal.

## Current state

The following are bounded source observations, not native probes:

| Evidence | Observation and limit |
| --- | --- |
| Core main revision `330556ab88278fe7a40f12ff7ae136db8b006798`, [`internal/config/launcher_extensions.go:11`](https://github.com/relux-works/curator/blob/330556ab88278fe7a40f12ff7ae136db8b006798/internal/config/launcher_extensions.go#L11), [`:17`](https://github.com/relux-works/curator/blob/330556ab88278fe7a40f12ff7ae136db8b006798/internal/config/launcher_extensions.go#L17), [`:84`](https://github.com/relux-works/curator/blob/330556ab88278fe7a40f12ff7ae136db8b006798/internal/config/launcher_extensions.go#L84) | Schema 7 defines a closed `extensions` object containing `proxy` and `claude_auth`; the inspected carrier does not declare `claude_env`. This is not an exhaustive search for another launch route. |
| Same revision, [`internal/config/config.go:583`](https://github.com/relux-works/curator/blob/330556ab88278fe7a40f12ff7ae136db8b006798/internal/config/config.go#L583) and [`launcher_extensions.go:51`](https://github.com/relux-works/curator/blob/330556ab88278fe7a40f12ff7ae136db8b006798/internal/config/launcher_extensions.go#L51) | Configuration schema admission is explicit; the existing typed projection is `curator.launcher-config/1`. No delivery behavior is inferred. |
| Draft Core [PR #216](https://github.com/relux-works/curator/pull/216), inspected head `f5d7cd472db973b9864f87e5ca4526f20e4a893c`, [`internal/config/launcher_extensions.go:15`](https://github.com/relux-works/curator/blob/f5d7cd472db973b9864f87e5ca4526f20e4a893c/internal/config/launcher_extensions.go#L15) and [`:66`](https://github.com/relux-works/curator/blob/f5d7cd472db973b9864f87e5ca4526f20e4a893c/internal/config/launcher_extensions.go#L66) | The draft uses schema 8 and projection `/2` for notification metadata. It is a landing dependency, not accepted or shipped behavior. The conditional allocation below still requires final-shape reconciliation before emission. |
| [Protocol core §1](../protocol/core.md#1-data-model-and-versioning) and [environments §12.1](../protocol/environments.md#121-machine-configuration-knobs), at specification base `a9c5e03b2857a10a66433e1a60bb255a89b9d741` (`1.0.0-rc.14`) | JSON readers reject duplicates, invalid UTF-8 and unsupported versions. `passable_env_names` lists names; it does not assign this setting's value. Existing released surfaces remain closed. |
| Draft spec [PR #205](https://github.com/relux-works/curator-spec/pull/205), inspected head `ee33b1d601e8a16116b7e91d0aa9b821dd016e25`, [`cips/CIP-0028-claude-read-scope.md:1`](https://github.com/relux-works/curator-spec/blob/ee33b1d601e8a16116b7e91d0aa9b821dd016e25/cips/CIP-0028-claude-read-scope.md#L1) | CIP-0028 is already in use by that proposal; this CIP does not reuse it. |

No production parser/editor/status/launcher or real Claude runtime was exercised.
The separately named corpus checks only the proposed member schemas and bounded
semantic refusals. Decision 0035 is a draft locator for this proposal, not a
claim that any preceding decision number is free or available for reuse.

## Design

### Options considered

| Option | Mechanism and benefit | Cost and security limit |
| --- | --- | --- |
| Native-home or per-profile edits | Existing files can express native settings | Repeated writes, unrelated custody and drift; rejected for this change |
| Free-form machine environment | One map can assign arbitrary child values | Credential, proxy and permission injection surface; rejected |
| Closed machine selection | One operator declaration, typed Claude-only contribution | Needs a versioned carrier successor and real-runtime qualification; recommended |

### Recommendation

Use optional `extensions.claude_env.BASH_MAX_OUTPUT_LENGTH` as a canonical
ASCII decimal string in 1..65536. Absence and an empty map are inert. A selected
value overrides an inherited value only for the Claude child; other runtimes
receive no contribution. Status distinguishes absent, configured and
runtime-ineligible selection without claiming effect.

The string wire type follows environment transport. The 65536 cap is a finite
2^16-unit manager policy budget that admits 8000; it is not a vendor maximum,
measured output size, disk quota or token-use guarantee. The real-runtime
witness must establish native units, precedence and full-output disposition.

## Security considerations

The machine configuration is the sole authority. Repository/profile/context
content cannot supply this member. A positive allowlist admits one exact name
and bounded canonical value; unknown names, malformed/duplicate JSON, invalid
UTF-8 and unauthorized contribution targets refuse without raw input in errors.
All names and values are validated before side effects. The checker also
rejects ambiguous, missing or unknown corpus metadata rather than last-wins
expectations.

This proposal grants no credential read, full-environment export, native-home
write, hook or permission change, cross-account authority or session restart.
The future implementation must bind validation and projection to the selected
source at each launch/resume; an already running process remains unaffected.
Refusal leaves accepted state intact and performs no child start or write.
Fixture success does not prove these production invariants.

## Compatibility and migration

Profiles and locks stay unchanged. Existing proxy, auth, notification and
nonselected environment semantics are preserved. Valid shared configuration
must remain usable for non-Claude targets with an empty contribution; invalid
explicit declarations refuse for every target rather than becoming absence.

Configuration **9** and projection **`curator.launcher-config/3`** are allocated
for `extensions.claude_env`, conditional on Core #216's schema **8** and
**`curator.launcher-config/2`** staying as is. This allocation does not adopt the
proposal: this CIP remains **Review** and Decision 0035 remains **Proposed**;
acceptance is the operator's decision. A change to #216's versions or admitted
shape requires re-review of the allocation and coordinated schema/vector changes
before acceptance or emission. The separate schema-6 node-source
family is not reused. Old readers reject unsupported containing versions;
ordinary edits cannot downgrade or discard the selection. No frozen release
artifact is amended and no existing-session update is provided.

## Specification changes

- [Proposed contract](../protocol/machine-claude-env-proposal.md): declaration,
  authority, contribution compatibility, refusal precedence and runtime evidence.
- [Schemas](../schemas/machine-claude-env-v1/README.md): standalone declaration
  and synthetic contribution schemas, plus closed containing-schema drafts for
  configuration 9 and projection `/3`, awaiting final #216 reconciliation.
- [Conformance corpus](../conformance/machine-claude-env-v1/README.md): valid
  controls, semantic reasons, six single-defect plants and checker controls.
- [Draft Decision 0035](../decisions/0035-machine-claude-output-limit.md): proposed
  choice and compatibility/security effects, pending maintainer adoption.

The complete containing schemas must preserve every admitted predecessor form
before any producer emits the successor. Acceptance and release remain subject
to [governance](../GOVERNANCE.md#changes); this proposal cannot land as accepted
protocol ahead of its final schema-8 dependency.

## Implementation plan

These are relative work sizes, not delivery dates or an implementation assignment.

1. **Small — specification first:** retain the conditional 9 and `/3` allocation;
   reconcile the containing-schema drafts against final accepted schema 8 and
   `/2`, including every predecessor form and refusal. Settle cap and wire type;
   land accepted prose, complete schemas, vectors and operator decision through
   normal review. Draft publication alone does not satisfy the pre-emission gate.
2. **Medium — machine carrier:** add the typed parser/editor/status path and
   predecessor compatibility checks; preserve unrelated settings and old-reader
   refusal. No profile/lock migration.
3. **Medium — projection and child boundary:** implement the versioned transport
   and Claude-only launch/resume contribution with inherited-value override,
   no-write rejection and no non-Claude injection.
4. **Medium — qualification:** run the actual entrypoint and runtime controls in
   contract §5 on each claimed supported platform; keep unsupported targets or
   unperformed witnesses explicitly unqualified.
5. **Small — adoption:** select the accepted machine setting through its normal
   configuration route and check the next admitted launch/resume; preserve
   rollback, credentials and live-session custody.

The generic shell slot is separate and is not a dependency of this selection.

## Test plan

The Go checker validates the actual member JSON Schemas and independently stated
semantic reasons. Tests enumerate 1..65536, reject adjacent values and forbidden
spellings, detect duplicates and malformed/invalid-UTF-8 input, and exercise case
variants, escaped duplicates, trailing commas and refusal precedence. Each of
the six required plants changes one leaf from a valid control. Wrong expected
acceptance and rejection must fail the aggregate while later cases still run;
strict corpus-admission controls pair each refusal with valid/restored loading.

Run repository validation, source-independence, the Python suite, the Go tools
suite and deterministic regeneration; hosted CI covers Linux, macOS and Windows
specification checks. These are not native runtime tests. Contract §5 separately
requires actual selected parser/editor/status, old-reader and predecessor checks,
child-bound launch/resume observations, inherited/native-settings precedence,
finite above/below-budget command output and no-write/no-leak preservation on
each platform for which usable support is claimed. No such effect is claimed here.

## Open questions for the operator

1. **Adopt the proposed 65536 cap, admitting the requested 8000?** Recommended:
   yes, as an explicit finite manager-policy budget. Revisit only with schema,
   prose and vectors together; do not describe it as a native maximum.
2. **Confirm adoption and the Decision 0035 locator after final Core #216?**
   Configuration 9 and `/3` are conditionally allocated above. The operator
   still decides adoption. Keep the allocation only if schema 8 and `/2` stay
   as is; reconcile all admitted forms before any producer emits the successor.
3. **Use canonical decimal strings rather than JSON numbers?** Recommended: yes,
   to match environment transport and keep a single exact wire type without
   coercion, signs, leading zeros or exponent spellings.
4. **Keep other runtimes usable under the shared declaration?** Recommended: yes,
   with no extension contribution; reject attempted injection and invalid
   explicit declarations using the documented refusal precedence.
