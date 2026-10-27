# Local hosted launches

This document is normative for the curator-spec part of
[CIP-0016](../cips/CIP-0016-local-hosted-launches.md), adopted by owner decision
2026-10-15. It freezes ownership, selection and the receiver contract summary,
not a deployable wire format. The
[Decision 0021 amendment](../decisions/0021-sessions-enter-through-curator-run.md#amendment-v2--local-hosted-launches-2026-10-15)
records compatibility with earlier entry-point decisions.

The numbered sections below describe the snapshot-based exact-plan route.
The owner accepted a transitional delegated route on 2026-10-21 in
[CIP-0016's dated revision](../cips/CIP-0016-local-hosted-launches.md#revision-delegated-local-launches-2026-10-21).
That revision separately records its caller-side composition, live-home and
provenance limits, registry selection, per-runtime activation and retirement.
Its home-lease **refuse** and exclusive-profile conditions were confirmed by
owner decision 2026-10-27; the [Curator contract](home-leases.md) and consumer
requirements are specification gates, not runtime qualification.
Delegated request and record schemas belong to curator-run; this pointer
publishes no wire schema and does not qualify either route.

## 1. Scope and activation

`curator-run <env> --hosted` selects local primary-session hosting through the
selected board's `tb-sessiond`, before the dispatcher is available. The scope
is the same machine and OS user. It MUST NOT authorize remote-board services
to submit executable plans or claim cross-account isolation.

Curator owns home content, verification, repair, login readiness and snapshots.
agents-management owns runtime argv and channel spelling. The caller consumes
the Curator fragment, requests composition and seals the complete process;
the launcher owns full environment composition. The session host owns private
session state, terminal/private app-server lifetime, tool policy, trust,
typed resume, goals and input. It MUST NOT become another profile composer.

The first supported local release MUST qualify Claude Code, Codex and Muse
together. A registered factory, matching digest, login status or partial
internal capability list MUST NOT be advertised as that release. Adoption
alone activates no receiver. The successor schemas, capability vocabulary,
preparation framing and launcher configuration MUST be jointly published by
launcher and receiver before activation; unresolved items are in section 8.
Frozen plan `1.0.0` and control protocol 9 MUST retain their meaning. The
recommended `2.0.0` / protocol 10 identifiers remain publication proposals.

The required operation matrix is semantic; it assigns no capability tokens:

| Runtime | Prepare / launch | Attach / resume | Goal application |
|---|---|---|---|
| Claude Code | Exact-plan PTY | PTY attach; typed session restart | Acknowledged revision adapter |
| Codex | Exact-plan private app-server | Private managed client; typed thread resume | Text directives; native goals disabled |
| Muse | Exact-plan musepty | PTY attach; typed Muse resume | Qualified musepty goal adapter |

Advertisement MUST match the real adapter and supported provider build.
Unknown capability tokens confer no operation; generic factory registration
is insufficient. The first public release requires every cell above.

`task-board spawn` is outside this terminal primary-session mode. Its fragment
requirement does not prove a per-run snapshot; its adoption of CIP-0014 remains
separate. The dispatcher and agent-account executor activation gates remain
unchanged. Their future snapshot archive MUST be plan-covered, relayed without
managed-home discovery, and verified/unpacked read-only by `curator-run exec`;
local home paths and the local bearer MUST NOT become remote authority.

## 2. Selection and refusals

The launcher MUST preserve existing host precedence, named-environment locks,
repeated-selector errors, legacy `ax` conflict and native routing semantics.
Native selection MUST perform zero receiver lookup or daemon probing. A hosted
refusal MUST NOT fall back to native, another runtime or another backend.

An explicit `--hosted` with no backend selection selects `local-task-board`.
That absence meaning MUST stay stable on later upgrades. Backend selection
does not itself turn native execution into hosting. An explicitly selected
`dispatcher` before its implementation MUST refuse, never become local.
The exact configuration member/location is not yet frozen.

Existing operator hosted defaults MUST require explicit local-backend
migration. Machine hosted defaults MUST continue to refuse
`session_host_default_not_ready` (exit 16) until upgrade-without-hangup is
qualified. Explicit `--hosted` does not require enabling a hosted default.
Enabled legacy `ax` plus hosted selection MUST refuse
`host_configuration_conflict` (exit 2) before the defaults gate.

The launcher MUST reject hosted source-side `--network` with
`network_scope_unsupported` (exit 16), missing terminal with
`session_host_terminal_required` (exit 6), and piped/attached payload stdin
with `session_host_stdin_unsupported` (exit 6). Knowable terminal, piped-stdin
and network failures MUST precede preparation or receiver contact; attached
plan stdin is rejected after composition and before handoff. The admitted
local stdin mode is terminal only. Native network rules remain unchanged.

The private receiver client MUST resolve the authoritative board using normal
session-management rules and use its existing authenticated control transport.
It MUST NOT use a repository-supplied socket or execute a board-supplied binary
to discover an endpoint. The daemon executes the plan; the private client
transports it, mediates attach/status and MUST NOT compose again.
Missing receiver refuses `session_host_missing` (exit 1); unreachable receiver
refuses `session_host_unavailable` (exit 1). Neither permits fallback.

## 3. Preparation and admission

Before composition, a bounded authenticated preparation operation MUST reserve
board/owner/runtime-bound session identity, generation and private writable
locations, with opaque reservation and expiry. For Codex it MUST also supply
the endpoint and transport/policy values needed to compose the final
app-server invocation. Preparation MUST NOT run a provider, resolve a profile
or execute caller-supplied preparation commands. Resource allocation is not
launch authorization.

The caller MUST ask Curator to materialize into the reserved private home,
then request the runtime's hosted form from agents-management, compose the
complete environment and seal the plan. A running session MUST NOT point
into a live Curator managed home. Receiver and launcher MUST NOT maintain
a parallel list of home files or select files to copy. Curator MUST define
materialization verification, relocation, protected inputs and any native
credential exception through the companion
[CIP-0014](../cips/CIP-0014-managed-home-snapshots.md) contract.

Admission MUST authenticate and strictly decode, check negotiated control and
capability versions, supported plan and producer/restart data, build
compatibility, local scope and the runtime's required operations. It MUST
recompute SHA-256 over CCJ-1 of the received plan excluding only
`content_digest`. The digest MUST cover the entire process, runtime,
preparation binding, snapshot reference and closed policy overlay. The existing §4.9 bounds remain requirements, including absolute
binary/cwd/home, source paths at most 4096 bytes, at most 64 sorted unique
lookup names, the 1 MiB object/depth-16 limits, and the existing argv, env,
literal and versioned-data bounds. A digest
match is byte consistency, not trusted authorship or policy authorization.

The receiver MUST independently verify board/owner/generation, reservation,
expiry, materialization receipt/binding, path ownership/confinement, policy
and the imported exec guard at the actual start boundary. It MUST NOT
silently repair, normalize or recompose a rejected plan. Curator defines
content verification; the receiver verifies its receipt/binding rather than
inventing a home-content checklist. A missing suitable Curator verification
API prevents activation of this property.

Before process start, provenance and the admitted generation MUST be durable
and the reservation MUST be consumed once. Failure/cancellation before
admission MUST release resources without launching a provider. Expiry MUST
NOT permit reuse. Recovery MUST distinguish prepared, admitted, started and
unknown outcomes. An admitted retry MAY return its recorded result but MUST
NOT launch twice; unknown liveness MUST NOT be interpreted as absence.

Endpoint reservation does not guarantee bind success. If allocation releases
a socket before provider bind, the handover race remains a stated residual.
Bind/readiness failure MUST record/refuse the outcome without endpoint or
argv substitution; retry requires fresh preparation and a new plan.

## 4. Exact process and runtime writers

Profile command delivery follows the native-first
[environments §§9.4/10.2 companion](environments.md#94-profile-scoped-skills-and-migration)
and its [detailed availability/receipt contract](profile-command-path.md).
A no-export profile has no prepend and no refusal from this companion. Hosted
command delivery is a named joint dependency owned by curator-run and the
session host, with Curator for binding. It needs a new required-understanding
carrier (for example `launch-delegated/2`), schema/module pins and receiver
support. Closed `launch-delegated/1` has no PATH member; reserved `child_env`
cannot carry it. No old carrier is widened here.

Until that carrier exists, a command-exporting hosted launch proceeds with an
explicit caller-local empty root decision and a commands-unavailable diagnostic,
without refusing for missing command delivery. Empty is null root/receipt and
zero profile command paths, not an empty PATH entry. The caller records this
outcome without claiming it changed the old receiver's final PATH. This is
not successful hosted command delivery and does not clear
`profile_skill_companion_required`.

After joint publication, supported hosted delivery MUST preserve protected
tools → verified profile root → admitted base PATH into the actual agent child,
with existing dispatcher rules. Curator publishes the root/fragment; curator-run
independently verifies and applies `path_prepend`; the manager carries effective
PATH, fragment digest, complete lock/plan and generation binding in the
session-launch request and manager session record. Exact-plan delivery covers
them with its complete process digest; delegated delivery uses the jointly
published binding contract. Start verification refuses a dropped active root
or stale/substituted binding, without route fallback. The
[paired vectors](../conformance/profile-command-path/README.md) distinguish
future active delivery from today's unavailable-but-launching case. Native
success does not qualify hosted transport. No implementation is supplied here.

The daemon MUST execute the planned absolute binary, ordered argv, full env,
cwd, stdin and selected home. It MUST NOT concatenate a shell command,
re-resolve PATH, merge daemon env, resolve/repair a profile, choose defaults,
append session-delivery variables or convert argv during admission/retry.
Delivery values MUST be prepared and digest-covered. Host geometry,
descriptors, process groups and bookkeeping do not authorize runtime flags.

| Runtime | Planned process | Curator writes | Receiver writes |
|---|---|---|---|
| Claude Code | Exact argv/env under daemon-owned PTY | Snapshot, manifest, relocated `CLAUDE_CONFIG_DIR`, credential strategy | Private session, trust, input, goal and declared policy state |
| Codex | Final private app-server invocation with prepared endpoint | Entire initial private `CODEX_HOME`, manifest and credential strategy | Separate policy/trust record beside the home and session/control records |
| Muse | Exact argv/env through the existing registered `musepty` factory | Snapshot/XDG layout, manifest, credential strategy, explicit `root_context` | PTY/session, input, goal and declared policy state |

Claude MUST consume the plan environment rather than ambient daemon env and
MUST NOT receive host-added plugin, context or Remote Control tokens. This
mode imposes no Remote Control requirement. Muse MUST use the real registered
`musepty` path; MSP-only or test-only substitutes do not qualify it. Its
composer MUST consume explicit fragment `root_context`, never infer it from
Curator's layout. The launcher's environment/system mapping MUST admit Muse.

Codex MUST arrive as an app-server plan, with native goals disabled and the
prepared endpoint and profile-level `-c key=value` settings already in argv.
The host retains private managed-client transport; it MUST NOT expose the
endpoint as a public service or wrap the app-server in a PTY. It MUST NOT
select/copy config keys or link native `auth.json` through a legacy home
preparer. Curator owns the complete initial private home.

The only receiver overlay is declared session tool policy and trust. For
Codex this includes `sandbox_mode`, `approval_policy` and selected workspace
trust entries; its closed keys and precedence await successor publication.
It MUST NOT change models, profile settings, instruction paths, MCP or login.
Preparation supplies the projection and agents-management composes its startup
overrides before sealing. The receiver MAY apply the same declared policy
through supported thread APIs, never append launch overrides. Context-builder
confinement is a separate contract; arbitrary `-c` tables are not assumed to
replace native MCP tables.

The policy record MUST be beside the home. Launcher and receiver MUST NOT
rewrite runtime-owned `config.toml`, including in a private snapshot. Curator
materializes its initial bytes; later native runtime writes are runtime-owned.
Qualification MUST prove the policy survives conflicting native config,
repeated attach and cold resume on the actual supported app-server release.
A thread/start-only proof is insufficient. If startup/API layering cannot
enforce this, activation MUST stop for a supported mechanism decision;
config rewriting or weakened policy is not a fallback.

Curator decides the profile × environment credential strategy, including
Codex `cli_auth_credentials_store="file"` and Muse
`TBH_CREDENTIAL_BACKEND=file`; agents-management applies it in argv/env.
The receiver MUST NOT log in, copy/reconnect credentials or invent exceptions
to regular-file snapshots. Native credential refresh is not receiver snapshot
maintenance. Muse's optimistic file-backend admission does not qualify its
unmeasured refresh writes.

## 5. Provenance, resume and goals

Private records MUST retain plan digest, producer version/commit, runtime,
profile name/pin, original fragment digest/system-module fact, snapshot
relocation, materialization manifest identity, prepared resources, policy
overlay identity and session generation. The initial manifest covers Curator
output before runtime writes; a separate receipt identifies the bounded host
overlay. Neither may be rewritten to bless later provider writes as initial
bytes. Profile repair/use/sync MUST NOT mutate an active snapshot.

Fresh launch MUST verify initial materialization. Restart MUST verify the
persisted receipt and Curator-defined protected inputs; native writable state
is validated by the runtime, not compared with its initial digest. Resume MUST
use the persisted session home/provenance and the module's closed restart
template with typed identity substitution, never a fresh live profile or a
reparsed native tail. Board, owner, location, runtime and generation MUST
match. Missing, ambiguous, unreadable, mismatched and liveness-unknown records
MUST refuse distinctly; resume MUST NOT become a new session.

The host retains goal binding, revision ordering and runtime reflection.
A requested goal MUST bind before ordinary work and MUST NOT be represented
as applied without acknowledgment. A no-goal session is allowed. Reflection
failures use the existing goal vocabulary. Codex keeps text-directive goals
with native goals disabled in its sealed plan.

## 6. Transport, diagnostics and security

The successor MUST preserve private plan stdin, terminal fd3, status fd4,
descriptor validation and receiver-side close-on-exec before descendants,
length-prefixed JSON status with a 64 KiB bound, closed registry messages and
redaction. Malformed complete status is `session_host_protocol_error` (exit 6);
truncation on a clean stream is `session_host_unavailable` (exit 1). Malformed
status remains poisoned despite later truncation. Without a typed status,
receiver/child exit alone MUST NOT be reclassified as a typed refusal.

| Condition | Existing refusal | Exit |
|---|---|---:|
| Invalid plan, digest mismatch, invalid preparation binding | `launch_plan_invalid` | 2 |
| Unsupported negotiated version | `session_host_protocol_unsupported` | 6 |
| Missing required runtime operation | `session_host_capability_missing` | 6 |
| Unsupported runtime | `session_host_provider_unsupported` | 6 |
| Wrong account or execution scope | `session_host_scope_unsupported` | 6 |
| Enforced policy or snapshot drift | `policy_refused` | 16 |
| Forbidden secret-bearing metadata | `secret_policy_violation` | 16 |
| Missing / ambiguous / unreadable resume | `session_resume_not_found` / `session_resume_ambiguous` / `session_resume_unreadable` | 1 |
| Location / identity mismatch | `session_resume_location_mismatch` / `session_resume_identity_mismatch` | 1 |
| Unknown liveness | `session_liveness_unknown` | 1 |

Only registry-permitted details/reasons may be emitted. No new diagnostic
reason or wire envelope is created here; new reasons require joint registry
publication. Build skew MUST refuse without automatically replacing a live
daemon, which can destroy its PTYs.

Frozen `1.0.0` policy `permission_mode: native` is a wire constant, not a
request to recompute permissions; `execution_profile` distinguishes standard
and yolo. This adoption changes no permission-resolution rule or native flag
mapping. The receiver MUST enforce or refuse the admitted policy, never
derive a broader policy from terminal presence or a daemon default.

Token, endpoint metadata, reservation, plan, manifest and logs MUST remain
private; control transport MUST NOT be network-exposed. The bearer is usable
by another same-user process and is neither per-process identity nor producer
signing. Digests and absolute paths are integrity checks, not executable trust.
Recheck exec/snapshot bindings before start; unreadable evidence refuses.
Same-user mutation between validation and use remains a residual unless
immutable handles or equivalent enforcement close it. Project data MUST NOT
select the endpoint, relocate the home, promote trust or inject daemon env.

Secret policy MUST govern persistence of env/argv. Diagnostics and public
outcomes MUST NOT expose their secret values. If restart needs fresh secrets,
the caller resolves them and seals a new restart plan bound to the same
snapshot; the daemon MUST NOT resolve them or mutate the old admitted process.
Cleanup MUST NOT follow links into native or managed homes. Adoption permits
no extra credential copying, login probes or secret persistence.

## 7. Compatibility and conformance

Legacy `task-board claude|codex` commands remain supported. Converting them
to thin wrappers is recommended, not required. Legacy conversion paths MUST
stay separate from exact-plan execution. Old routes retain their refusal
semantics; no fields may be added to frozen plan `1.0.0`. Curator
materialization precedes joint hosted-planner/receiver rollout, then production
lookup activation. Status reads MUST NOT rewrite homes or launch sessions.

The [semantic corpus](../conformance/local-hosted-launches/README.md) fixes
selection outcomes and forbidden observations. It is not a payload schema or
provider qualification. The required implementation properties and narrowing
mutants remain in CIP-0016's Test plan; they MUST run through real entry points
before capability advertisement, for each applicable runtime and supported
platform. macOS/Linux qualification MUST report versions, environment identity,
measured rows/required rows and unknown/skipped rows. Unsupported combinations
refuse capability. No provider probes or runtime mutants are claimed here.

## 8. Publication questions retained

1. **Successor wire:** choose a `2.0.0` / protocol 10 successor (recommended)
   or separate family; jointly freeze exact capability tokens/matrix,
   preparation schemas/framing, limits, bindings and old/new vectors.
2. **Backend configuration:** choose per-environment selection following
   host precedence/locks (recommended) or a global member; publish schema,
   spelling and explicit default migration. Absence semantics in section 2
   and repository inability to select the endpoint are already fixed.
3. **Codex policy:** qualify startup overrides plus supported thread APIs
   (recommended) or an actually supported native policy-file API, including
   cold resume. If neither works, seek a supported-mechanism decision;
   receiver config rewriting is excluded.
4. **Credential exception:** CIP-0014 must define a Curator-owned shared-login
   strategy (recommended) or restrict first support to self-contained snapshots
   with separately prepared login. Neither permits receiver-created links or
   asserts measured Muse refresh semantics.

These questions do not permit deferring Codex, waiting for the dispatcher or
using a live managed home. They prevent premature wire publication and
activation; this document does not choose their unapproved answers.
