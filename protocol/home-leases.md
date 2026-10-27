# Managed-home leases (v1)

This is the Curator contract for CIP-0016's **refuse** condition, confirmed by
owner decision **2026-10-27**. It is specification-first work, not evidence of
an implemented CLI, enabled capability or qualified runtime. The
[schemas](../schemas/home-leases-v1/README.md) and
[paired vectors](../conformance/home-leases-v1/README.md) are normative.
Existing frozen release carriers and `project-lease/1` are unchanged.

## 1. Authority, storage and identity

**HL01.** Curator MUST own the profile-home lease store in manager state at
`state/home-leases/v1/`, outside all provider homes, reusing the existing
`managerlock`, transaction journal and `projectlease` lifecycle/persistence
primitives. This is a typed storage namespace, not a second lock, journal,
TTL collector or launcher-owned file protocol. Project state remains under
`state/project-leases/v1/` with its closed bindings and authority intact.

The home namespace contains `ledger.json`, immutable acquisition bindings in
`bindings/<lease-id>.json`, and immutable terminal audit events in
`events/<event-id>.json`. The ledger indexes request identities, current record
revisions and terminal tombstones; the journal publishes related targets in
one transaction. Initial allocation and missing ledger in an existing namespace
are distinct. The closed [record schema](../schemas/home-leases-v1/record.schema.json)
is the public record/diagnostic projection, not permission for a caller to edit
these files. A mutable ledger implementation cannot rewrite immutable bindings.

**HL02.** All mutations MUST use the existing manager-wide canonical manager-home
lock, validate its borrowed held witness, and retain it through the last write.
The OS lock is held for an operation, never for the session lifetime. Existing
project/global-operation lock ordering precedes manager-home; callbacks borrow
the held operation rather than recursively acquiring it. A bounded OS-lock wait
is allowed; unavailable lock returns `environment_lock_unavailable`. No operation
waits for a hosted holder to end as an alternative to refusal.

**HL03.** Under that lock, acquisition MUST resolve canonical environment aliases,
profile, manager-root and actual home identity from Curator authority, revalidate
the admitted `lock_sha256`, current marker/materialization and shared dependencies,
and reject drift before publishing a reservation. Selectors are not caller paths.
A different current digest is `environment_lease_lock_mismatch`; no silent
substitution, lease allocation or manager start follows. Environment selector
aliases use existing `NormalizeEnvID`; stored IDs and holder discriminators are
canonical and case-sensitive. Home identity uses the existing symlink-aware,
platform-aware manager identity rules, not lexical path cleanup or lowercase.

**HL04.** Readers and mutation admission MUST retain uncertainty from unreadable,
corrupt, symlinked, partly initialized or pending state in either affected lease
namespace. An absent namespace is empty; an existing namespace with missing
ledger is `environment_lease_unreadable/ledger_missing`. No failure becomes
an empty list or a successful absent-ID release.

## 2. Holder and lifecycle

**HL05.** Inputs and records MUST follow the closed prepared/bound holder union:
`kind`, `launcher`, `manager_id`, `manager_registered_at`, `request_id`,
`werkstatt`, `session`, `generation`, `process`. Prepared has the last three
explicitly null; bound has an exact session, positive safe-integer generation and
process incarnation (`pid`, `started_at`). The start time is the manager
observer's exact OS process-start identity, not the launcher's current clock or a
PID-existence probe; inability to validate it retains uncertainty. `werkstatt` is an ID or null.
`launcher` is exactly `curator-run`; `kind` is exactly `prepared` or `bound`.
Curator authors `acquired_at`, opaque canonical `manager_root_id`, `home_id`,
`lease_id`, environment/profile, digest, phase, revision and observation evidence.
Home lease IDs are manager-allocated and cannot collide with existing project IDs;
request identity is scoped to this typed profile-home API, not project authority.
No arbitrary maps, argv, secrets or caller filesystem paths are accepted.
Strict UTF-8 decoding rejects duplicate, missing and unknown members, unsafe
integers, case aliases, overlength fields and control characters before use.
Schema-valid shape alone supplies no lifecycle or observation authority.

**HL06.** Acquire MUST use a launcher-persisted `request_id` and canonical payload
binding, durable before its first attempt. Replaying an identical request returns
the same lease at its current disposition, including after a lost reply; changing
its payload returns `environment_lease_holder_mismatch/request_conflict`. While
the lease remains blocking, replay returns `acquired` with `changed:false`.
Current terminal disposition MUST take precedence over historical acquire
success: a released/broken replay returns `already_released`/`already_broken`,
respectively, with the current terminal record and `changed:false` (exit 0,
`ok:true`, `code:null`). This is a **non-admitting terminal replay**: successful
outcome retrieval is not current launch authority. The consumer MUST follow
HL21's no-start rule. The request index is manager-wide and retained with
tombstones; replay MUST NOT allocate, revive or alter the lease, binding,
tombstone or audit. Only fresh admission under a new `request_id` can lease
again. First acquire requires a prepared holder matching `--request-id`.
Its prepared record is blocking before success is acknowledged.

**HL07.** Bind MUST compare `--if-revision` and the exact request, manager ID and
registration incarnation, Werkstatt and session/generation/process tuple from
authoritative manager evidence. It changes prepared to active, advances the
revision by one and makes the bound tuple immutable. An identical committed
retry with the original revision/payload returns that bind outcome without a
write only while the lease is nonterminal; terminal refusal takes precedence
over this idempotent retry. Other stale revisions conflict. A different tuple,
wrong incarnation,
unknown ID or terminal lease refuses. Binding is not a liveness assertion.

**HL08.** Prepared, active and unknown records MUST all block overlapping writers.
Timeout, age, detach, dead launcher, missing/unreachable/re-registered manager,
PID reuse, `draining` or uncertain descendants retain protection. Observation
uncertainty may set phase `unknown` without discarding a prepared/bound holder.
No lease expires on a timer; `acquired_at` is diagnostic metadata only.

**HL09.** Release MUST perform authoritative reconciliation for the stored exact
manager/session/generation/process incarnation, proving terminal session and
all descendants plus reconciled ownership, or proving no manager call/no start.
A caller holder assertion, forwarded unsigned terminal record, launcher death
or abandoned operation alone is insufficient. Curator consumes an authoritative
manager observer (including incarnation validation and no-start operation
observation); unavailable integration refuses
`environment_lease_release_unconfirmed/session_state_unknown`. Curator-run must
publish its registry/status read contract before this integration can qualify.
This specification does not accept the weaker cooperative-record alternative
left open in L3. Normal project release remains its existing `Reconcile` path.

**HL10.** Release of a syntactically valid unknown ID MUST return exit 0,
`unknown_lease`, `changed:false`, only after a successful complete state read,
without creating a record/event. A known project lease ID is not an absent
profile lease: bind/release/break refuse
`environment_lease_authority_refused/unsupported_lease_kind`. Terminal retries return `already_released` or
`already_broken`, unchanged. A known lease releases only with HL09 evidence;
no proof returns exit 1 and preserves the blocking record. Release advances
revision once and retains an immutable reconciliation event and tombstone.

**HL11.** Multiple holders of one admitted profile-home generation MUST retain it
independently. Releasing/breaking one never clears another. A different digest or
materialization cannot join it. Same-generation sharing within one lane does not
authorize cross-lane use or override project adapter concurrency qualification.

**HL12.** Operator break MUST target one profile lease with per-invocation
`--operator`, nonempty bounded `--reason` and exact `--if-revision`. No default,
wildcard, environment variable, implicit repair or timeout grants this intent.
This is explicit intent under same-OS-user trust, not OS authentication. The
reason acknowledges descendant fencing or deliberate abandonment of protection;
break does not claim it stopped any process. Missing intent/reason/revision is
usage failure; unavailable ownership authority or a project lease kind refuses.

**HL13.** Break MUST atomically publish a terminal tombstone and immutable audit
event with prior record, old/new revision, reason and Curator timestamp in the
same existing transaction. Audit failure cannot acknowledge an unblock; retain
blocking or recoverably pending state. Recovery/retry yields one logical event.
Completed journals are not permanent audit. Late bind/release cannot revive a
broken lease; terminal retry is unchanged, with the original outcome discoverable.

## 3. Guarded writes, recovery and reads

**HL14.** Before any affected write or recovery entry, a writer MUST enumerate the
complete command-wide set of actual homes, profile locks and shared mutable
references under the held manager lock, inspect all blocking holders, and either
refuse without affected changes or retain the lock through publication. This
includes bytes, links, modes, directories, seeds, backups, markers, ownership
records, current/scoped pointers and current/previous profile locks. A lease on
a disjoint home/dependency does not freeze the manager. Lease-refusal atomicity
is a no-write guarantee; unrelated I/O failures do not gain a universal rollback
guarantee. Batch preflight precedes the first target's write.

The following writer rows are normative HL14 targets; library/borrowed-operation
entry points have the same guard as their CLI callers. Native in-place targets
that alias a leased managed home are included by identity, not command label.

| ID | Writer and required boundary |
| --- | --- |
| W01 | `env resolve --repair`, with/without `--preserve-lock`, takeover, first provisioning: before recovery, directory protection, backup or apply; publisher assertion before apply. |
| W02 | Store-entry reconstruction: all leased consumers before staging/replacing a linked entry. |
| W03 | Hash/identity migration during resolve/use/migrate: before preparing projections and publishing locks, markers or links; full migration target set. |
| W04 | `profile update`, including unchanged-lock native-skill repair and `--all`: before current/previous lock publication or resync; command-wide target preflight. |
| W05 | `profile use`, scoped use and `--clear`: old/new overlapping targets before migration, native materialization and pointer changes; held-operation current/scoped setters. |
| W06 | `profile install`, reinstall, first activation, `--use`, `profile import`: before profile record/lock or activation writes, not only the later use call. |
| W07 | `profile sync`: one continuous borrowed operation across managed and native phases and all environments. |
| W08 | `global add/install`, legacy install continuation and standalone library calls: before profile locks or any materialization; hold the operation through managed sync. Declaration-only global remove is not materialization. |
| W09 | Shared skill projection, copy fallback and skill sync: before replacement for any leased consumer; identical no-write verification and new unreferenced immutable entries remain possible. |
| W10 | Managed MCP render and native in-place documents: before publishing documents/links/copies. |
| W11 | `profile mcp install/repair`, multi-environment included: preflight before recovery/ownership/lock writes. Already-refused ownership actions remain refused. |
| W12 | Seed/credential projection and merge: before directories, backups, seed/link/marker writes. Lease diagnosis reads no credential content. |
| W13 | `env migrate --apply`: both pending migration-journal effects and new link/marker/identity plan before recovery or mutation; `--plan` stays read-only. |
| W14 | `env unmanage [--restore-backups]`: before native removals/restoration, markers and selection changes. |
| W15 | `profile remove`, with/without `--purge`: retain leased authority even for non-current profiles; before native cleanup or deleting any descendant home/session data. |
| W16 | Project-home allocation/publication/update and adapters: common held admission boundary; retain `project_view_busy`, prepared publication and qualified concurrency. No profile-to-project authority conversion. |
| W17 | Transaction/migration recovery from envprofile, install, GC and borrowed global engines: preflight both forward and rollback effects before replay. |
| W18 | Legacy/global install and collection: guard mutable overlaps and retain referenced runtime/build/store/projection roots. Historical unlocked collection cannot treat profile leases as absent project state. |

**HL15.** Recovery policy MUST guard forward and rollback effects independently
before entering replay, including rollback caused by a forward commit-check
failure. A leased-home refusal cannot itself replay/rollback an affected write.
Unknown journal targets retain pending evidence. Acquire refuses unresolved
overlapping recovery intent with `environment_lease_recovery_required`; recovery
can complete without a lease before a fresh acquisition. Every recovery owner,
including install, GC and migration journals, shares this policy.

**HL16.** GC MUST union retained roots from profile and project leases, including
prepared/unknown holders, pending acquisition, profile-lock provenance and
shared projections/runtime/build entries that a session may load later.
Unreferenced neighboring artifacts remain collectible.

**HL17.** `lease list`, status and no-repair resolve MUST be read-only: no implicit
recovery, reconciliation, default-profile creation, bind, release or mutation-lock
file creation. Use existing-lock/pending-intent read certainty. List orders all
records by `(environment, profile, home_id, lease_id)` and distinguishes terminal
rows. A genuinely absent namespace lists empty without creating it; unresolved
relevant pending state returns a typed uncertainty. A stale resolve emits no
fragment. Read-only config edits may report candidate drift but never repair.
Provider-owned auth/session/history writes are outside this cooperative guard.

## 4. CLI, diagnostics and exit codes

The following family is new; default and only accepted format is JSON:

```text
curator env lease acquire --env <id> --profile <P> --lock-sha256 <digest> --request-id <id> --holder <json> [--format json]
curator env lease bind --lease <id> --if-revision <n> --holder <json> [--format json]
curator env lease release --lease <id> [--format json]
curator env lease list [--env <id>] [--profile <P>] [--format json]
curator env lease break --lease <id> --if-revision <n> --operator --reason <text> [--format json]
```

**HL18.** The family MUST emit exactly one closed v1 result object on stdout for
success, semantic refusal and recognized-command usage failure; no progress
text. Unknown command routing retains existing usage behavior. Human explanation
goes to stderr with `curator:`. Result shape is operation-specific; details are
closed, never an arbitrary map. Malformed holder bytes are not echoed. Unknown
code/reason tokens and wrong success/exit combinations are invalid.

**HL19.** `environment_home_leased/blocking_holders` MUST identify every blocking
holder across the affected set: lease/request IDs, phase, revision, environment,
profile, home identity, digest, manager incarnation, nullable session/generation,
acquisition time and available observation evidence. Prepared and unknown rows
count even without a session. The count equals rows, deterministically ordered.
Human refusal names each holder and directs users to `env lease list`, stop/down
and reconcile, or explicit audited break. Unreadable state is a storage refusal,
never fabricated holder identities. No secrets/argv or paths beyond the home.

**HL20.** Existing resolve MUST retain no stdout fragment on failure and typed
internal errors for profile writers. Existing earlier boundary/credential refusal
ordering and `project_view_busy` remain intact; substring error matching is not
the machine contract. The following closed mapping applies to the new family:

| Exit | Code | Reasons |
| ---: | --- | --- |
| 0 | null | `acquired`, `bound`, `released`, `broken`, `listed`, `unknown_lease`, `already_released`, `already_broken` |
| 1 | `environment_home_leased` | `blocking_holders` |
| 1 | `environment_lease_lock_mismatch` | `profile_lock_changed` |
| 1 | `environment_lock_unavailable` | `mutation_lock_busy` |
| 1 | `environment_lease_unreadable` | `state_unreadable`, `invalid_record`, `ledger_missing` |
| 1 | `environment_lease_recovery_required` | `pending_mutation` |
| 1 | `environment_lease_release_unconfirmed` | `session_state_unknown`, `termination_unconfirmed` |
| 1 | `environment_lease_holder_mismatch` | `manager_incarnation_changed`, `session_generation_changed`, `request_conflict` |
| 1 | `environment_lease_revision_conflict` | `revision_changed` |
| 1 | `environment_lease_unknown` | `unknown_lease` (bind/break only) |
| 1 | `environment_lease_authority_refused` | `unsupported_lease_kind`, `authority_unavailable` |
| 1 | `environment_lease_write_failed` | `publication_failed` |
| 1 | `environment_home_stale` | `home_not_current` |
| 1 | `profile_unknown` | `profile_absent` |
| 1 | `environment_unknown` | `environment_absent` |
| 2 | `usage` | `operator_confirmation_required`, `reason_required`, `revision_required`, `invalid_holder`, `invalid_selector`, `invalid_format`, `invalid_flags` |

Existing environment-registry and project diagnostics at their earlier
boundaries are not redefined by this table. A break retry may report
`already_broken` only for the same original break identity/revision/reason;
conflicting retries refuse. Release takes no caller-evidence flag: observation
is Curator's reconciliation dependency, not JSON supplied as authority.
For acquire, exit 0 with `already_released` or `already_broken` reports only
terminal replay retrieval; it MUST NOT admit a launch (HL06/HL21). `acquired`
MUST carry a currently blocking record, never a terminal record or a historical
prepared snapshot in place of the current terminal disposition.

## 5. Consumer requirements and isolation policy

**HL21 (L1).** curator-run MUST durably write recoverable `op.json` phase
`lease_requested` with request ID, env, profile, admitted digest and identical
holder payload **before** first acquire for every hosted launch/resume and
`werkstatt up`. When reconciling a `lease_requested` op.json, curator-run MUST
replay the identical acquire. If the replay reports a released or broken lease,
the result is non-admitting: the launcher MUST make **zero manager calls**,
settle op.json as **not started**, and refuse with
`session_home_lease_unavailable` (exit 1), carrying Curator's terminal reason
(`already_released` or `already_broken`). It MUST NOT treat exit 0/`ok:true`
alone as launch authority. Only fresh admission with a new `request_id` can
lease again. Paired lost-reply control: replay of a still-prepared blocking
lease returns `acquired` for the same lease with `changed:false`, then proceeds
to the manager call **exactly once**. Lock mismatch requires fresh admission,
never silent digest replacement.

**HL22 (L2).** After manager `started`, curator-run MUST bind immediately with exact
manager registration, session, generation, process incarnation and Werkstatt,
using the acquired revision. Crash before bind leaves a discoverable blocking
prepared lease; reconciliation binds from the manager's authoritative record.
A future reserve/start split binds durably before provider start.

**HL23 (L3).** curator-run MUST request release only after exact `down`/termination
or proven no-start from settled operation/manager evidence. Unknown, unreachable,
`draining`, absent or re-registered managers retain the lease. It must expose the
read-only command `curator-run session-manager observe <id> --session <handle> --json`
as the closed registry/status observation contract needed by HL09.
curator-run owns this command; Curator MUST NOT speak the manager plugin
protocol directly. The observation must satisfy HL09's exact-incarnation and
no-start evidence requirements; forwarding its own assertion is insufficient.
`recover --abandon-operation` never releases/breaks
by itself: report the exact lease/revision and explicit operator break command.
This also carries L4. Acquire failures become launcher
`session_home_lease_unavailable` (exit 1), preserving Curator code/reason; lock
unavailability remains distinct (L5). Native unhosted launches take no lease,
and no `--no-home-lease` hosted bypass is admitted (L6).

**HL24.** Owner decision 2026-10-27 requires one managed home per unattended lane
and one profile per Werkstatt. Launcher admission MUST refuse cross-lane or
cross-Werkstatt/ad-hoc sharing of that selected profile home; multiple hosted
holders within the same admitted lane/Werkstatt remain independent. Curator
protects the actual identity and digest, not just a profile label. No host/cross-user
isolation is claimed, nor does this mutate project composition authority.
The launcher owns lane/Werkstatt allocation enforcement; no invented lane field
is added to the holder. Its accepted allocation/read contract is a qualification
dependency, alongside the observer contract. Lease schema acceptance alone
cannot advertise either integration as implemented.

## 6. Qualification

Every HL requirement and W writer has paired negative/positive vectors. Schema
cases validate bytes/shape; semantic cases specify actual entry-point observations
required of the later Curator and consumer implementations. Specification checks
alone prove no locking, process lifetime, recovery or runtime no-write property.
The implementation qualification uses isolated homes, real manager locks and
process barriers, exact code/reason plus byte/link/mode/record preimages, and
fault points before/after publication. Guard-bypass, ignore-unknown and
omit-expected-digest control plants must fail their intended assertions while
positive controls run. Frozen project lifecycle/regression suites remain gates.
