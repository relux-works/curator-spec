# Managed Muse v4 conformance amendment

This later amendment freezes the [environments §10.2](../../protocol/environments.md#102-the-launch-environment-fragment)
transport adopted by [CIP-0017](../../cips/CIP-0017-muse-root-context-and-credential-store.md).
It is separate from the released rc.14 corpus; no released manifest, candidate
metadata, v1–v3 schema or historical vector bytes are changed.

## Schema cases

[`schema-cases/index.json`](schema-cases/index.json) uses the existing
`schema`, `instance`, `valid` convention. Run `python3 tools/validate.py` from
the repository root: its schema gate consumes both the historical index and
this index. `python3 -B -m unittest discover -s tools -p 'test_muse_v4.py'`
checks the corpus, strict duplicate-key parsing, negative controls and gate
wiring. These are specification-data checks, not runtime qualification.

The v4 schema supports all existing adapters. Muse requires the five-key
environment and effective file policy; the optional root fact is closed and
Muse-only. Codex's optional typed override must agree with store selection.
Other adapters retain native policy and their existing channels/home variable.
Missing or contradictory policy is invalid. Old schemas reject v4 and the
new fields under old tokens. Semantic validation additionally requires all
Muse XDG values to share one home with the four declared suffixes.

## Runtime vector notes for subsequent implementation leaves

These are normative required outcomes, not executed runtime results. Drive
resolve, login, plan, seal and exec rather than an uncalled helper. The
historical [argv vectors](../environments-muse-launch-argv/vectors.json) retain
the materialized-target contrast; in v4 the launcher receives only Curator's
typed fact. It must not discover that contrast by reading files.

| Scenario | Required outcome | Narrowing counterexample that must fail |
|---|---|---|
| Verified linked, copied, current or repaired root surface | Emit `root_context: {"exclusive":true}` | Recognize only regular files, omitting linked roots |
| No declared root surface | Omit fact and both exclusions; retain residual | Infer a requirement from an unrelated file |
| Stale, unreadable or failed required-root repair | No fragment | Treat only unreadability as no declared surface |
| Fact on qualified exec / interactive | Exact `--no-foreign-personal-context` / `-c context.foreign_personal_skills=false`, including dry-run | Apply exclusion only to exec or only to one permission mode |
| Fact on serve or unqualified selected build | Refuse before execution | Warn and continue only on serve |
| Native argument re-enables foreign skills | Refuse, including alternate accepted config spellings | Protect only one spelling |
| Network relocation | Preserve established root through admitted materialization or refuse | Remove the fact only for network launches |
| Native/unset and explicit file managed Muse | Effective file policy at login and launch, unchanged stored selector | Force file only for isolated, or only during login |
| Explicit Muse Keychain | `environment_credential_unsupported`, no fragment or migration | Silently convert explicit Keychain to file |
| Ambient backend / explicit conflicting plan backend | Fragment file wins over ambient; explicit conflict refuses | Allow a later environment merge to undo file |
| JSON / env / shell projection | Same five values; declared XDG order then backend | Omit backend only in shell |
| Isolated login | Managed file login, no native link/copy | Count a native Keychain login as managed readiness |
| Shared native-file login | Capture pre-override native path and verify regular readable target | Link to the post-override managed path |
| Missing shared source / metadata read failure | Native file-login guidance / unreadability refusal, no fragment | Treat read denial as absence and relink |
| Shared fork, unexpected link, dangling source, nonempty directory | Status non-current; bare resolve stale; repair conflict preserving bytes | Refuse forked files but overwrite unexpected links |
| Absent shared link with readable native file / empty directory | Only existing §7.4 nondestructive repair admitted | Skip target liveness only during repair |
| Legacy v3 managed Muse request | Upgrade refusal; no retry or file inspection | Accept v3 only when no fact is carried |
| Broker child key delivery | Key via admitted stdin/env channel, file backend, no linked/copied owner OAuth | Link OAuth only for broker children |

Credential admission does not await refresh probes. Before consumer release,
replay P1–P4 on the exact 1.4.8 build, links and regular-file snapshots, both
forms and the workspace residual, as environments §7.9 requires. Do not
promote the 1.4.8 credential observations to exclusion qualification.

Refresh/concurrent writes, live vendor authentication, model-visible foreign
removal, managed skills/system-prompt discovery, broker lifetime/rotation,
and unqualified native platforms are outside the schema/data-check claim.
The schema cannot attest Curator provenance, actual materialization or plan
binding; runtime consumers must enforce the existing authority checks.
