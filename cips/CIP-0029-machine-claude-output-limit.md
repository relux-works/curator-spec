# CIP-0029: Machine-scoped Claude output limit

- **Status:** Draft
- **Created:** 2026-11-05
- **Affects:** machine configuration and Claude child-environment delivery
- **Related:** [proposed contract](../protocol/machine-claude-env-proposal.md),
  [draft Decision 0035](../decisions/0035-machine-claude-output-limit.md),
  [notification carrier](https://github.com/relux-works/curator/pull/216)

## Summary and motivation

An operator needs a common bounded Claude output limit without editing every
profile or a running session's native settings. Add a closed
`extensions.claude_env` object to per-account machine configuration, initially
admitting only `BASH_MAX_OUTPUT_LENGTH`. An optional canonical decimal string
from 1 through 65536 is projected only to Claude children at normal launch or
resume. A shared declaration must leave other runtimes usable and uninjected.

Owner direction, 2026-11-05: «т.е это явно конфигурация ланча котороая общая для
всех на тачке». The carrier is per OS account; cross-account system authority is
outside this proposal. The requested initial value is `"8000"`.

## Current state

Core at `330556ab88278fe7a40f12ff7ae136db8b006798` has a closed schema-7
machine `extensions` object for `proxy` and `claude_auth`
(`internal/config/launcher_extensions.go`). Its `passable_env_names` bounds
names without assigning values. There is no established general Claude
settings-env composition route in that inspected contract. Draft Core #216
adds notification metadata in schema 8. This addition must not reuse that
version or reinterpret the separate schema-6 node-source family.

## Options and recommendation

| Option | Benefit | Limit / risk |
| --- | --- | --- |
| Native-home or per-profile edits | Existing files can express native settings | Repeated writes, unrelated custody and drift; rejected for this change |
| Free-form machine environment | Broad configuration flexibility | Credential/proxy/permission injection surface; rejected |
| Closed machine selection and Claude-only child contribution | One operator selection, no profile/lock/home mutation | Needs a typed carrier successor and real-runtime qualification; recommended |

Use the string wire type already proposed for environment transport. The
65536 cap is a finite manager-policy budget, not a claimed native maximum.
Absence and an empty map are inert. Explicit malformed input refuses without
values in diagnostics. The manager must preserve all other existing fields.

## Security, compatibility and migration

The [contract](../protocol/machine-claude-env-proposal.md) defines the positive
allowlist, exact integer spelling, duplicate handling, redaction, child-only
delivery and valid/forbidden target table. Profiles and locks stay unchanged.
There is no active-session update or new credential/config read authority.
Older readers must reject the new whole-carrier version, not ignore the member.
Propose configuration 9 and projection `/3`, after #216; maintainer allocation
and dependency acceptance are required before accepted publication. The member
schemas here are deliberately not complete containing carriers.

## Specification and test plan

The proposed contract, standalone member schemas and separately named corpus
are outside frozen release artifacts. The Go validator and tests check actual
JSON Schema admission, semantic refusal reasons, six individually defective
inputs, adjacent positives, range boundaries, duplicate decoding and diagnostic
redaction. Existing full specification checks still apply. Implementation and
real-runtime witness obligations are listed separately in contract section 5;
no runtime result is inferred from these tests.

## Remaining decisions and implementation order

1. Maintainer review allocates the next configuration/projection numbers after
   the final schema-8 carrier; this PR proposes 9 and `/3`.
2. Independent exact-candidate review and checks precede source acceptance and
   landing. This proposal cannot land as accepted protocol ahead of #216.
3. Only then is implementation assigned. Its actual-entrypoint and runtime
   witnesses precede usable-support claims. The generic shell slot remains a
   separate change and is not a dependency of this bounded env selection.
