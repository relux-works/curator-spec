# Login readiness revision 1 conformance

This separate accepted corpus follows [login readiness](../../protocol/login-readiness.md)
and [its schemas](../../schemas/login-readiness-v1/README.md). It does not
modify the released core suite or claim that a pinned implementation consumes
this amendment. `index.json` enumerates structural positive/negative instances;
`schema-cases/` is an exhaustive file inventory for that index.

## Specification checks

From the repository root, with `requirements-dev.txt` installed:

```sh
python3 tools/validate.py
python3 -B -m unittest discover -s tools -p 'test_login_readiness.py'
make validate
make regenerate-check
```

The production validator calls `tools/login_readiness.py` and reports measured
schema-case and negative counts. Unit tests narrow secret-field closure,
caller-session scope, one adapter's mapping refusal and one Codex mapping;
they also prove dispatch failure, missing-witness detection and old-reader
rejection. These are **structural specification** checks. A metadata-failure
reason cannot structurally attest absence, but only a real implementation
probe can establish which observation occurred. Schema tests do not execute
status, login, resolve, prepare or a launcher and cannot establish those effects.

## Required implementation vectors

The following rows are normative semantic vectors, **unrun** here. A consumer
harness MUST drive the named production entrypoint with synthetic stores,
tripwire executables and instrumented effects, including nearby valid controls.
The proposed test names come from CIP-0015; implementations may organize tests
differently but MUST report every row's actual coverage and effects. No runtime
oracle is implemented in this specification tooling.

| Row | Entry / proposed test | Input and required outcome |
|---|---|---|
| metadata-only | status / `TestEnvStatusLoginMetadataOnly` | Accessible nonempty private file → present. Tripwire agent, secret-content reads, secret API returns, network, prompts and helper invocation → zero such effects. |
| read-failure | status / `TestEnvStatusLoginReadFailureUnknown` | Successful no-entry lookup → absent. Permission failure, denied/locked Keychain, timeout, wrong type, unexpected link or incomplete metadata → unknown; check 1; no login/fallback/write. |
| session | status / `TestEnvStatusClaudeCallerSession` | Qualified capability selects exactly that session's store and exact exported-path service/account. Failed capability or ambiguous derivation → unknown, never another store's present or false absent. |
| presence-bound | status / `TestEnvStatusPresenceIsNotValidity` | Nonempty metadata candidate → present without parsing; zero-length candidate → unknown. Do not assert JSON validity, expiry or inference. |
| aggregate | status / `TestEnvStatusCheckIncludesLogin` | Current + all present → check 0. Current + any absent/unknown, including ambient OpenCode → check 1. Non-current + present → check 1. Plain rendered status → 0. Emit all available rows. |
| shared-refusal | login / `TestEnvLoginSharedRefusesBeforeExec` | Current isolated supported home + interactive session may exec. Shared mode → refusal before exec; no native changes or writes through link. |
| login-input | login / `TestEnvLoginRequiresInteractiveTrustedChild` | Trusted executable, current home, interactive stdin/stdout and no headless marker permit ceremony. Missing either terminal, CI, profile-owned binary, stale home, unsupported mapping or conflicting source → no exec; no transcript. |
| login-result | login / `TestEnvLoginChildResultAndPostRead` | Child 0 + present → 0. Child 0 + absent/unknown → 1. Nonzero child → unchanged exit; signal → platform convention. No destructive cleanup. |
| participants | prepare / `TestPrepareAllParticipantsNoActivation` | Installed name retains lock; explicit missing source uses install then resolve. Every participant appears; no machine/scoped-current change; ambiguous name never becomes guessed URL. |
| headless | prepare / `TestPrepareHeadlessReportOnly` | Noninteractive stale home → report only; missing profile → install required/participation unknown, exit 1. Zero fetch, install, repair, browser, login or activation. |
| unknown-no-login | prepare / `TestPrepareUnknownNeverLogsIn` | Isolated supported absent home may login; unknown/conflicting metadata never does. Shared/native absence and external sources give guidance, never home-login exec. |
| idempotent-partial | prepare / `TestPrepareIdempotentAndPartial` | Installed/current/present repeat → zero mutation. Independent failure retains successful transactions and reports every row; aggregate 1. Cancel → no further ceremonies. |
| applied-policy | login + direct/hosted launch / `TestStorePolicyAppliedAtLoginAndLaunch` | Matching Codex override or Muse literal applied identically at all paths; native config unchanged. No home inspection by consumers. Missing hosted override must fail. |
| policy-refusal | resolve + launch / `TestStorePolicyRejectsUnsupportedAndConflicts` | Supported file policy passes. Claude forced backend, Muse forced keychain, unqualified Codex keychain, isolated keyring/auto, incompatible shared native source, unknown key, missing/mismatched override or conflicting argv/env → refusal, no fallback or launch. |
| source-refusal | login + resolve / `TestStorePolicyRejectsUnsupportedAndConflicts` | Explicit external source + native preserves source policy; non-native home override refuses. Home login never replaces external selection or counts an inherited environment token as post-login home readiness. |
| policy-race | prepare + login / `TestPrepareIdempotentAndPartial` | Revalidated stable inputs can exec; concurrent home/source/selector change stops affected operation, never redirects login. Mutation locks released before browser wait. |
| broker | status + login / `TestBrokerReadinessDoesNotEnrolOrLease` | Metadata observation only; unavailable observation → unknown. Unauthorized enrolment refuses; no lease, credential bytes or local vendor login. Broker adoption remains separately gated. |
| old-reader | fragment parsing / `test_old_fragment_readers_reject_policy_and_unknown_revision` | Valid v1–v3 control accepted; extra policy member, Muse backend literal or unknown revision rejected. Runtime consumer execution remains required despite schema evidence here. |

A consumer handoff MUST report passed/declared rows and killed narrowing
mutants, with surviving bounds explicit. Platform reader qualification,
real authentication, native keyring scope, token expiry, Muse refresh writes,
source/broker adoption and destination authentication are not established by
this corpus's structural check. These are explicit later-leaf limits, not
permission to fabricate presence.
