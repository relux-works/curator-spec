# Decision 0033: Compatible lock refresh on ordinary profile launch

## Status

**Draft, 2026-10-27. Owner confirmation pending. Design only.**
The requested behavior reached the source owner through a keeper relay. That
relay is evidence of a requirement, not operator approval. Approval of the
profile lock field on 2026-10-26 does not approve automatic lock changes.
This draft proposes that change separately. It authorizes no implementation,
schema change, release, installation, profile mutation or session restart.

The profile lock remains the identity defined by
[environments §1.3](../protocol/environments.md#13-the-lock-is-the-identity)
and [Decision 0012](0012-context-packages-and-semver-locks.md). A lock is a
retained resolution record, not permission, a signature or a policy grant.

## Context and dependencies

Ordinary launch currently invokes only
`curator env resolve <env> [--profile <P>] --repair --format json`.
It repairs or consumes the stored lock; it does not call `profile update` or
refresh dependency ranges. The launcher source owner additionally distinguishes
native provider-thread relaunch from hosted identity-preserving resume: native
launch has no stored launcher admission identity, while hosted resume does.
These are reported source facts, not runtime tests performed for this draft.
The proposed refresh belongs
inside that resolve operation, not in a launcher wrapper or a second update
prelude. Manual per-keeper updates would cease for eligible new launches.

The design preserves these contracts:

- [Source signers and resolution, environments §1.4](../protocol/environments.md#14-versions-ranges-and-resolution),
  [registry signatures and attestations](../protocol/registry.md), strict audit,
  content identity, source admission and immutable-tag checks.
- [Update confirmation, environments §9.2](../protocol/environments.md#92-current-profile-switching-update-and-removal):
  B-flip refuses a triggered system/MCP delta without the invocation's
  `--confirm-system-delta`. Policy cannot pre-confirm it.
- [Home leases, spec #193](https://github.com/relux-works/curator-spec/blob/e8f0f6e7dd371e36e63b2859d6ce4f941cf58913/protocol/home-leases.md):
  guarded writes, command-wide preflight, retained uncertainty and no implicit
  release or break. The referenced revision must be checked before adoption.
- [Effective posture, spec #197](https://github.com/relux-works/curator-spec/blob/633c3ae8b1be4c227c12b5173cb75c1d6e51be26/protocol/effective-posture.md),
  [per-launch PATH, spec #194](https://github.com/relux-works/curator-spec/blob/bd44903fa5a64b4bba66666da071a5e58461ad44/protocol/profile-command-path.md)
  and [Decision 0031, policy-derived trust](https://github.com/relux-works/curator-spec/blob/bd44903fa5a64b4bba66666da071a5e58461ad44/decisions/0031-policy-derived-workspace-trust.md):
  exact lock/plan/generation bindings and independently approved authority.
- [Decision 0028](0028-project-context-and-werkstatt-leases.md): frozen
  Werkstatt identity and faithful session resume.

Companion references describe specification dependencies, not implemented or
qualified behavior. This draft does not extend an existing closed carrier.

## Proposed decision

### 1. Operator-owned policy and default

Add a per-profile **machine configuration** member
`environments.lock_policy.<profile>`, with exactly two values:
`refresh-compatible` and `frozen`. It is not part of a package manifest, root,
overlay, skill, project file or portable lock. A profile selects the applicable
machine entry by its installed name; downloaded content cannot set the entry.
The proposed default, once this design is approved and activated, is
**`refresh-compatible`**. An absent entry then has that meaning.

Only authenticated operator authority may set or change this policy through
Curator. A keeper may exercise that authority only under the owner's approval;
being a package author, a keeper process or a launcher caller is insufficient.
Follow Decision 0031's authority/provenance distinction without reusing a
workspace trust grant as update consent. Record policy changes and their actual
actor/approver in protected manager state. Fleet/system policy may lock the
per-profile value to `frozen`; lower layers cannot override it to refresh.
Locking it to `refresh-compatible` cannot override a launch pin or no-refresh.

This default addresses the reported requirement for ordinary existing-profile
launches without a per-release manual update. Signer checks, system-delta
confirmation and lease admission still bound each update. `frozen` supports
reproducible/manual maintenance and disables automatic refresh, not explicit
operator `profile update`. A new release alone cannot opt existing machines
into this draft: adoption needs owner approval and a documented activation
transition that explains the changed absent-field default. Until then existing
read/repair behavior remains authoritative.

### 2. Resolve inputs and consumer boundary

Propose these resolve inputs, negotiated before use:

```text
curator env resolve <env> [--profile <P>] --repair --format json
    [--expect-lock sha256:<64 lowercase hex>] [--no-refresh]
    [--confirm-system-delta] [--readmit-profile <protected-readmission-ref>]
```

`--expect-lock` supplies an independently admitted **complete profile lock**
pin. The launcher passes a Werkstatt record's `profile_lock_sha256` here,
normalizing bare lowercase hex to this spelling without changing its value.
Compare against the current lock before recovery, migration or any write.
Matching pins freeze this launch; mismatch refuses before writes. Never update
the record to match a candidate or refresh first and discover the mismatch
later. All Werkstatt runs keep their admitted pin, including up/recycle of an
existing record. Refresh is a separate stopped-task operator action, outside
this decision's automatic path.

The launcher sends `--no-refresh` by default on **hosted resume and continue**,
and passes the session's admitted lock via `--expect-lock`.
No-refresh prohibits resolution or lock identity migration, including an
otherwise automatic v1-to-v2 migration. Apply the existing preserve-lock
discipline: repair to exactly that lock or refuse before mutation. It cannot
resurrect an old session by silently adopting the profile's newer lock.
`--preserve-lock`, when supplied, likewise suppresses refresh and preserves
its existing migration refusal. An explicit no-refresh is always permitted;
it does not authorize any other operation. Without `--repair`, resolve remains
read-only and never fetches, refreshes or recovers a journal.

**Never refresh under a RUNNING session or a running Werkstatt task.** A
stopped native thread's deliberate relaunch and an explicitly re-admitted down
hosted session may refresh and continue the same thread, under the route rules
below. Same-thread upgrade/restart is part of this decision, not a separate
design decision. Frozen hosted resume remains the default.

Propose one required, closed JSON member in a **negotiated successor resolve
fragment**, named `lock_refresh`, with exactly these fields:

| Field | Closed meaning |
| --- | --- |
| `status` | `refreshed`, `unchanged`, `frozen`, `deferred-lease`, `deferred-offline`, or `read-only` |
| `previous_lock_sha256` | Complete pre-resolve lock digest, `sha256:<64 lowercase hex>` |
| `lock_sha256` | Complete admitted post-resolve lock digest in the same spelling |

`refreshed` requires unequal hashes; every other status requires equality.
The post-resolve hash must equal `fragment.profile.lock_sha256`. This member
reports the outcome of **this resolve**, never an earlier pending transaction.
Refusal produces no fragment; typed refusal details and human delta go to
stderr. Diagnostics never contaminate JSON stdout. A later schema allocation
must define closed validation, capability negotiation and failure transport;
old fragment revisions remain closed and cannot carry this member.

curator-run only conveys intent/pins and consumes the result. It surfaces a
refresh on stderr and binds the member into native per-launch provenance or
the jointly negotiated hosted request. It does not resolve versions, choose
policy or mutate a lock. Missing successor support cannot silently drop the
resume/pin inputs or label the old behavior as refresh-capable.

### 2.1 Native stopped-thread upgrade and restart

Native keepers launch through
`curator run <env> --profile P --native -- <provider resume arguments>`.
There is no launcher admission record to replace. Each launch resolves P
through `env resolve --repair`; native resume arguments are the provider's own
continuation request, not hosted `resume SES-…`. They do not imply no-refresh
or an old `--expect-lock` pin. The operator stops the keeper at a safe checkpoint,
waits for termination and reconciles any outstanding work, then deliberately
relaunches the same thread with P's refresh-compatible policy. That relaunch's
resolve may adopt the newest compatible lock and render it before provider
resume. Explicit frozen policy/no-refresh still keeps the old lock.

The thread identifier, history, goals and continuation data remain in the same
managed home; refreshing managed context/commands must not replace the home,
clear native state or create a fresh thread/keeper identity. Record old/new
locks through `lock_refresh` and the new per-launch provenance. Recheck the
normal operator, signer, confirmation and launch gates. Native launches acquire
no hosted home lease; manager mutation serialization and the checks against any
overlapping hosted lease still apply. A running native consumer of the affected
home, or unconfirmed termination at this restart checkpoint, refuses before
refresh writes. A lack of native lifetime leases is not evidence of idleness:
native stop/ownership observation is a qualification obligation of the refresh
route, not a claim that #193 already tracks native sessions.

### 2.2 Hosted stopped-session operator re-admission

Ordinary FRONT-DOOR §5.3 resume keeps its stored admitted Curator identity.
If the current identity differs, refuse `session_curator_identity_stale` before
provider start, without updating the stored record. No-refresh is not permission
to ignore this comparison. The explicit operator alternative is
`resume SES-… --readmit-profile`, owned by curator-run's FRONT-DOOR amendment.
It is prohibited for Werkstatt records with `profile_lock_sha256`.

The launcher calls the proposed Curator resolve form above with
`--readmit-profile <protected-readmission-ref>`, without `--expect-lock`,
`--no-refresh` or `--preserve-lock`. Combining those inputs is `usage`, not a
silent override of a frozen pin. The protected reference is issued through
independently authenticated operator/manager authority; a caller-supplied
`down` boolean, session ID or pair of matching digests is not admission.
The resolve contract is:

1. Validate a closed, single-operation readmission record binding the operator
   approval, operation ID, registered manager incarnation, exact session and
   generation, profile/environment/home, stored admitted identity, current
   complete profile lock and authoritative stop/checkpoint observation. The
   manager must report that exact generation **`down`**, with provider and
   descendants terminated and ownership reconciled. Running, draining, unknown,
   unreachable, stale or different-generation observations refuse before writes.
   Stored session lock and current profile lock are separate preimages: a stale
   session may be deliberately re-admitted, but neither preimage may be replaced
   by an unchecked caller value. Frozen machine policy still vetoes automatic
   range refresh; readmission grants no override of policy or system consent.
2. Hold an exclusive readmission reservation under Curator's home-lease authority
   for that exact down session/home while resolving, verifying and adopting the
   candidate. Validate the reservation's operation, incarnation and revision
   under the manager-home lock at every publication boundary. No other prepared,
   active or unknown holder may overlap. The lease remains held through identity
   recording and transfer to start admission; no release/reacquire gap is allowed.
   This proposes a scoped successor to #193's guarded-write contract: only this
   authenticated reservation authorizes its own listed lock/render writes.
   An ordinary prepared lease never grants such an exception. Existing closed
   holders and immutable acquisition bindings are not silently reinterpreted.
3. Run the same compatible resolution, verification, system-delta confirmation,
   journal and render algorithm. Journal the old/current lock preimages, the
   new lock/generation and an immutable readmission receipt. Retain old lock,
   managed history and prior continuation record. The receipt binds both complete
   old stored-session identity and new admitted identity (profile, lock, plan,
   protected generation), the current-lock preimage, exact session/generation,
   operation/manager/operator and held reservation reference. Record the actual
   actor and approver; neither a package nor a keeper relay can approve it.
4. Return the new fragment plus a protected receipt reference/digest in a
   negotiated closed readmission result. `lock_refresh` continues to report the
   current-profile-lock transition; the receipt separately records the stored
   session identity transition, even if the profile was already at the target
   lock and `lock_refresh.status` is `unchanged`. The session host must CAS its
   still-down exact generation/old identity to the new identity and append the
   receipt before provider resume, preserving the same native thread/history.
   curator-run owns the orchestration; **swarma-session-host owns the stored
   identity and resume/1 change**, not tb-sessiond. Curator does not edit the
   session host's ledger directly or claim a cross-process atomic rename.
5. A lost reply/retry uses the operation's retained receipt and journal; it does
   not refresh again or append a second identity transition. If manager CAS or
   acknowledgement fails after Curator publication, keep the session down, keep
   the reservation and pending receipt, and refuse start until reconciliation.
   Never report old identity with a usable new start. A race to running or
   generation drift cannot be fixed by overwriting the manager record. On
   successful CAS, consume the reservation into a fresh prepared start lease
   bound to the new identity, then recheck and bind before provider start.
   Retain the old reservation/binding as terminal audit, never retarget its
   immutable lock binding or accept terminal replay as start authority.

A deferred refresh is not successful hosted readmission: report the lease or
offline condition, keep the old identity and session down, and do not issue a
new start from that outcome. Any already acquired reservation is reconciled
through its recorded no-start/ownership evidence; uncertainty keeps it held.

The closed input/result/receipt and lease-reservation successor must be
jointly published and qualified with curator-run and swarma-session-host before
use. This decision defines their required authority and transitions; it does
not add fields to today's #193 or resume/1 schemas. Unsupported readmission
refuses without falling back to ordinary frozen resume or a new thread.

### 3. Launch-time algorithm

1. **Read authority and classify.** Validate effective machine policy, stored
   lock, declared sources/ranges, operator restrictions and launch intent.
   Unknown policy/invalid flags refuse. A missing/unreadable lock is not an
   outage fallback baseline. First installation retains its own explicit
   install contract. Read-only, frozen, pinned, preserve-lock and ordinary hosted
   resume resolves take the existing pinned repair/read path, with no remote
   refresh. Stopped native relaunch and explicit hosted readmission follow §2.1
   and §2.2; running-session refresh always refuses.

2. **Obtain exclusive home-lease write admission.** A refresh needs the
   lease-protected mutation boundary from #193: acquire the existing canonical
   manager-home operation lock and preflight every affected home, current/old
   lock and shared dependency, retaining that held witness through publication.
   No unrelated prepared, active or unknown hosted holder may overlap. The
   explicit down-session readmission of §2.2 holds its own scoped reservation
   through its authorized writes; a generic lease is never a write permit.
   This is exclusive
   mutation admission under the home-lease contract, not a new lease store or
   a session-lifetime OS lock. Do not borrow or break another session's lease.
   Native launch posture still has a null session lease under #197. If a
   holder blocks, defer the refresh, leave the lock and all affected bytes
   unchanged and report `environment_home_leased/blocking_holders`. An unchanged
   current fragment may be read for the old lock; a required home repair still
   refuses under #193. Deferral never overrides session start/lease admission.

3. **Resolve a candidate in staging.** Fetch the release inventory and use
   environments §1.4's deterministic newest-first closure algorithm, including
   its downward re-selection, conflicts, prerelease rules and no backtracking.
   For each existing ranged member, intersect all declared ranges with
   `>=<locked version> <(locked major + 1).0.0-0`. A new member must have a
   declared effective range bounded to one major; otherwise require an explicit
   operator update (`profile_lock_refresh_range_unbounded`). Do not guess a
   major from an unbounded new dependency. No automatic downgrade, next-major
   prerelease or widening of declared constraints is allowed. A graph with no
   admissible candidate refuses `context_range_conflict`; it does not edit
   declarations. "Newest" is under that resolver, not a global SAT optimum.

   The owner's intended 0.x range remains question 5: an explicitly declared
   `>=0.1.5 <1.0.0` permits stable 0.2, while `^0.1.5` excludes it. This draft
   presents both choices and does not choose or rewrite the declared range.
   Existing prerelease admission rules still apply; the automatic next-major
   bound above excludes next-major prereleases. Existing `*`/`latest` is bounded
   by the installed member's major. Exact tags, revisions, direct fixed skill
   declarations and manifest exact dependencies retain their commits and
   directories. Moved-tag checks never turn a fixed tag into a movable pin.
   Path sources have no release range: preserve their recorded state pin;
   local edits require their existing explicit update/admission path. Resolve
   versions from the declared source and directory under existing tag rules;
   do not mistake a monorepo collection version for a package release.

4. **Verify before admission.** Automatic refresh requires configured effective
   signer allowlists for every Git source in the candidate closure, even where
   ordinary explicit resolution permits unconfigured signers. Missing lists
   refuse `context_source_signers_missing`. This is a proposed stricter gate
   for automatic refresh, not a change to the global default of
   `require_source_signers`. Verify the selected annotated tag OR peeled commit
   against that source's allowed signers; exact revision selections require
   their commit signature. Reuse `context_source_unsigned` and
   `context_source_signer_rejected`. Never try an older candidate to hide a bad
   signature. Verify snapshot/content hashes, source admission, protected path
   boundaries, strict audits and required assurance/build receipts. Verify
   registry signatures against pinned keys and exact artifact identity; apply
   deny-wins revocation, required attestations and current assurance policy.
   A source signature is not an audit attestation. Automatic refresh cannot
   exploit advisory unknown/unreachable evidence to adopt an unaudited release.

5. **Compute and gate the delta.** Compare the complete candidate with the
   stored lock and print environments §9.2's ordered `lock-delta` lines before
   publication. Apply B-flip's complete system-module inventory and MCP
   declaration comparisons, not version strings or only selected modules.
   Any triggered delta without this invocation's `--confirm-system-delta`
   refuses `profile_update_confirmation_required`. Conservatively include
   removal of a system-bearing member/module or MCP declaration as touching
   that surface; this is an explicit proposed tightening beyond §9.2's current
   added/moved trigger. No policy, saved consent, keeper identity, unattended
   default or workspace grant supplies the flag. Never retry with confirmation
   added automatically. A routine unconfirmed launch refuses rather than
   quietly launching the old profile after this security refusal.

6. **Journal, publish and render.** Stage and validate the complete candidate
   closure, builds and generation before advancing the lock. Recheck old lock
   digest, policy revision and all lease admission under the held boundary;
   drift refuses, not last-writer-wins. Reuse the manager transaction journal
   for the candidate, previous lock and affected generation/pointer writes.
   Retain the complete previous lock, immutable store/build inputs and generation
   as rollback/GC roots. Publish the new lock atomically (durable staged bytes,
   atomic replacement and durable journal ordering); never truncate in place.
   Re-render and publish the matching home, marker and command receipts under
   the same recoverable transaction before returning any usable fragment.
   Readers cannot consume a new-lock/old-home mixture. Empty deltas do not
   rotate the previous lock or create a fictitious refresh.

   A pre-publication failure leaves the old baseline usable. An interruption
   after publication leaves a journaled complete-old/complete-new recovery
   choice and no fragment/provider start until recovery finishes. Recovery
   must obey #193 before its first write; a leased target cannot be rolled
   back as a side effect of refusal. If automatic recovery cannot establish
   consistency, refuse and retain evidence. An operator rollback uses retained
   bytes under the same authority/lease/transaction gates, never re-resolves
   the old ranges or rolls back underneath an active holder. Retention does
   not authorize reactivating revoked or now-disallowed bytes; rollback must
   pass current signer, audit and policy admission as well.

7. **Bind and launch.** Only after successful render does resolve return a
   fragment. Generate a fresh plan, command root/receipt, PATH state and
   effective posture for the final lock and generation. Recheck bindings at
   actual start; never patch hashes on an already admitted old plan. Hosted
   consumers acquire their prepared session lease against this final lock;
   explicit readmission instead transfers its held reservation under §2.2,
   after the down-session identity CAS and before provider resume.
   A race with another mutation refuses under existing lease/start admission.
   Only then may the launcher start the provider. No running session is
   patched, restarted or relabeled by refresh.

### 4. Offline behavior and authority interactions

An offline source, failed fetch or unreachable enabled trusted registry
**defers the entire refresh**, even if caches could supply a newer candidate.
Keep the current lock, previous-lock history and generation; emit a diagnostic
identifying the unavailable source/registry and old lock. The old lock must
still pass existing local integrity, revocation, policy and currency admission.
Offline reuse grants no exemption to strict assurance requirements. Known bad
signatures, revoked artifacts, malformed evidence or a system-delta refusal
are security failures, not outages. Never convert them into a success fallback.

Frozen/current-lock use does not mint or renew grants. A refreshed signed
package cannot change operator policy, signers, permissions, hook consent,
native settings ownership, sandbox posture or project registration. If existing
approval is bound to the old lock/plan/generation, require fresh independent
admission; do not copy it to the new digest. Decision 0031's revocation and
expiry rules survive. #194's command availability fallbacks do not waive PATH
integrity, and #197's missing qualification/downgrade refusals survive refresh.

### 5. Diagnostics and refusal outcomes

Existing codes keep their owning contract's details/exits. Deferral describes
the **refresh attempt**, not permission to bypass a launch refusal. A successful
old-lock fragment may carry `deferred-*`; if pinned read/repair/start admission
fails, return that refusal without a fragment.

| Condition | Proposed outcome/code |
| --- | --- |
| Matching pin, frozen policy, ordinary hosted resume/no-refresh/preserve-lock | `lock_refresh.status=frozen`, identical hashes; no release lookup |
| Successful adoption / no eligible change | `refreshed` / `unchanged` |
| Held home lease | Reuse `environment_home_leased/blocking_holders`; `deferred-lease` only when old-lock read is admissible |
| Manager lock busy; unreadable lease; pending mutation | Reuse `environment_lock_unavailable`, `environment_lease_unreadable`, `environment_lease_recovery_required`; refuse, not an invented holder |
| Missing signer list / unsigned / rejected signer | Reuse `context_source_signers_missing`, `context_source_unsigned`, `context_source_signer_rejected`; refuse, old lock stands |
| Triggered unconfirmed delta | Reuse `profile_update_confirmation_required`; refuse, old lock and homes stand |
| No satisfying closure / invalid declaration | Reuse `context_range_conflict` / `profile_source_invalid` |
| Offline source or registry | New diagnostic `profile_lock_refresh_deferred_offline`; reuse `registry_unreachable_during_install` for the registry gate notice; `deferred-offline` only with admissible old lock |
| Expected lock differs | New `profile_lock_expectation_mismatch` (exit 1), expected/actual digests; no writes. Launcher retains `werkstatt_profile_lock_mismatch` or `session_curator_identity_stale` mapping in its amendment |
| New member's major is ambiguous | New `profile_lock_refresh_range_unbounded` (exit 1); explicit update needed |
| Hosted frozen resume's current identity differs from stored identity | Existing launcher `session_curator_identity_stale`; no record update or provider start |
| Readmission or native restart checkpoint is running/unknown, or readmission authority/receipt is invalid | New `profile_readmission_refused` (exit 1), with closed reasons `session_not_down`, `stop_unconfirmed`, `authority_invalid`, `generation_changed`, `werkstatt_pinned`, `identity_record_pending`, `unsupported`; no start or unauthorized writes |
| Unknown policy, malformed digest or conflicting flags | Existing `usage` (exit 2); unknown configuration refused, never treated as absent |
| Journal publication/recovery or render failure | Existing transaction/materialization refusal, no fragment or start; implementation slice must enumerate exact existing mappings before code |

Attestation/audit failures retain their registry/assurance owning codes, without
collapsing them into a signer error. New tokens above are proposed names, not
entries added to a released diagnostic registry by this document.

## Proposed admit/refuse vectors

These are design vectors for a future executable corpus, **not executed runtime
evidence**. Unless varied, use operator refresh-compatible, an installed 1.2.0
lock, `>=1.2.0 <2.0.0-0`, signed/audited inputs, unchanged non-system payload,
free lease admission and a new unpinned session. `L0` is the complete old lock;
`L1` is independently computed from the specified candidate. Successful refresh
must prove exact emitted bytes, marker, command receipt and launch binding to
L1. Pre-publication refusals prove no provider start and unchanged
lock/home/policy/pins; post-publication interruptions in V15/V28 prove the
specified journaled state and no start until reconciliation. Deferred success
proves binding to L0 and an explicit diagnostic. History preservation is checked
against retained pre-restart bytes, not inferred from a reused thread label.

| ID | Input/control | Required verdict and effects |
| --- | --- | --- |
| V01 | Add valid 1.3.0 | Admit L1 at 1.3.0; `refreshed`, L0 retained for rollback |
| V02 | Add 2.0.0 and 2.0.0-rc.1 alongside 1.3.0 | Admit 1.3.0 only; neither next-major candidate enters L1 |
| V03 | Only a next major is new | Admit L0; `unchanged`, no lock rotation |
| V04 | Highest in-range 1.3.0 unsigned; signed 1.2.1 also available | Refuse `context_source_unsigned`, not downgrade to 1.2.1; signed 1.3.0 is positive control |
| V05 | 1.3.0 signed by an unlisted key / source list absent | Refuse `context_source_signer_rejected` / `context_source_signers_missing`; approved signer control admits |
| V06 | Change system module bytes or MCP URL; no confirm flag | Refuse `profile_update_confirmation_required`; same delta with per-run flag admits; saved config consent alone still refuses |
| V07 | Skill revision S is fixed; newer skill tag exists | Context may advance to L1, but skill source/commit/directory remain S; a candidate requiring a different exact skill pin refuses conflict |
| V08 | Prepared/active/unknown lease held elsewhere | No refresh writes; diagnostic names holders. If old home current, read L0 as `deferred-lease`; if repair needed, refuse `environment_home_leased`. Idle control admits V01 |
| V09 | Hosted frozen resume/continue with `--no-refresh --expect-lock L0` | Keep L0 and same session identity when still current, even when 1.3.0 exists; no lookup/migration. If current profile is already L1, refuse stale identity before writes/start |
| V10 | Registry outage / offline source | Keep L0; `deferred-offline`, explicit diagnostic. Unreadable/invalid L0 refuses; restored registry control admits V01 |
| V11 | Werkstatt up/recycle with `--expect-lock L0` | Freeze L0, no mid-task/new-launch refresh; mismatch against current L1 refuses before journal recovery or writes |
| V12 | Plain `env resolve` without repair; explicit frozen policy | Read-only / frozen; no network or lock writes despite available 1.3.0 |
| V13 | 0.1.5 lock, candidates 0.2.0 and 1.0.0, two explicitly declared ranges | Conditional range controls: `>=0.1.5 <1.0.0` admits 0.2.0 only; `^0.1.5` keeps 0.1.x. Owner question 5 selects intended profile range; no semantic reinterpretation |
| V14 | Revoked attestation / mismatched content / tampered registry signature | Refuse under owning integrity/registry gate, not outage fallback; verified exact-artifact control admits |
| V15 | Kill before publication, after lock replacement, during render | Respectively old baseline or journaled recovery; no mixed fragment/start; hold acquired after crash prevents recovery writes |
| V16 | L0 or policy/lease revision moves between staging and publication | Refuse before publication, retain intervening state; no overwrite or implicit retry with weaker constraints |
| V17 | Changed lock with old PATH receipt, plan, grant or effective posture | Refuse start; fresh independently admitted bindings are positive control, recomputed caller hashes alone are not |
| V18 | Frozen/ordinary hosted resume resolve encounters legacy lock needing hash migration | Preserve identical identity or refuse before any migration write; ordinary repair's migration is not a refresh exemption |
| V19 | New dependency has unbounded range / exact existing tag moves | Refuse ambiguous-major / existing strict-tag failure respectively; single-major new dependency / unchanged exact tag are controls |
| V20 | Remove system module or MCP declaration | Require per-run confirmation just as V06; this tests the proposed trigger tightening explicitly |
| V21 | `lock_refresh` unknown field/status, unequal frozen hashes, or fragment hash mismatch | Reject successor JSON; valid refreshed and frozen objects are controls; no progress text on stdout |
| V22 | Source fetch/registry times out, but newer bytes are cached | Keep L0 and report deferral, never silently adopt cached L1; no older lock or bootstrap fabrication if L0 absent |
| V23 | Native keeper stopped at a confirmed safe checkpoint; deliberate relaunch with provider resume of thread T | Resolve adopts L1 then resumes T in the same managed home. Existing history/continuation bytes and goals survive; emitted context/commands and provenance bind L1; no new thread/identity |
| V24 | Hosted frozen resume stores identity I0, current profile has I1 | Refuse `session_curator_identity_stale`, even with no-refresh; stored I0/history unchanged and zero starts. Matching-I0 current-profile control resumes frozen |
| V25 | Operator `resume SES --readmit-profile`, exact generation down, authentic reservation, stored I0 | Adopt compatible L1 under held reservation, retain L0 and I0/continuation, record I0→I1 with receipt and CAS, transfer lease and resume the same thread; history survives. Include profile-already-L1 control: unchanged lock still records I0→I1 |
| V26 | Same native restart/readmission attempt while session running, draining or unknown, or generation changed | Refuse before refresh writes and provider resume; preserve lock/home/identity/history. Confirmed stopped/down controls V23/V25 admit |
| V27 | Readmission with pinned Werkstatt, forged/down-only assertion, unrelated lease, or conflicting no-refresh/expect-lock | Refuse intended pin/authority/lease/usage gate before writes; no implicit pin edit, lease break or policy override |
| V28 | Curator publishes readmission; manager CAS fails or reply is lost | Hold reservation and pending receipt, session stays down and no start; retry reconciles same operation once, records one transition and preserves history. Running-generation race never overwrites identity |

Future validation must drive real resolve/launcher entries in isolated homes,
not a wrapper that calls explicit update. Each gate must demonstrate an intended
known-violation control alongside its valid control. Crash/lease tests must
observe post-failure bytes and start counts. No live keeper, user home or active
Werkstatt may be used as a fault-injection fixture.

## Alternatives, compatibility and security impact

Keeping `frozen` as the eventual default preserves current behavior but leaves
ordinary keeper launches needing an extra update policy setting. A launcher
`profile update` prelude duplicates authority, races pins/leases and misses the
single resolve boundary. A timer or mid-session refresh violates admitted
session identity. Trusting all SemVer-compatible releases without signer,
attestation and system gates mistakes version compatibility for authorization.

Adoption changes absent-policy behavior and adds network work/latency to eligible
launches. It needs negotiated successor fragments, machine-config schema,
status/provenance fields and exact diagnostics, plus amendments to environments
§§1.3, 9.2, 10.1 and 12 and curator-run's FRONT-DOOR/resolve contract. Existing
lock schema bytes and explicit pins need not change. Publication, implementation,
release and runtime qualification are separate gates; this prose adds no such
artifacts and makes no conformance claim.

Automatic consumption increases exposure to future allowed-signer releases.
Major bounds do not prevent malicious or breaking minor releases. Protected
operator policy, strict candidate verification, explicit system consent, lease
serialization and retained rollback bound that exposure without granting
packages runtime authority. Availability fallback preserves admitted old bytes;
it does not promise fresh revocation knowledge while offline.

## Owner questions

1. Confirm the relayed requirement and `refresh-compatible` as the activated
   absent-field default, including the transition for existing profiles?
   Recommendation: yes, with visible activation and explicit frozen overrides.
2. Confirm the same-thread routes in §2.1 and §2.2: deliberate stopped native
   relaunch may refresh, ordinary hosted resume stays frozen, and explicit
   operator readmission of an exact down hosted generation holds the lease and
   records old/new identity before resuming? Recommendation: yes, preserving
   history and continuation records; running/unknown sessions always refuse.
3. Confirm operator-owned per-profile machine policy, fleet frozen veto and no
   package authority? Recommendation: yes, following Decision 0031's provenance.
4. Confirm required signer configuration and attestation evidence for automatic
   refresh even on permissive machines? Recommendation: yes; use explicit update
   for deliberate exceptions under its existing contract.
5. For 0.x, should the profile declare `>=0.1.5 <1.0.0` (permits 0.2 and later
   0.x minors) or `^0.1.5` (permits 0.1 patches, excludes 0.2)? Recommendation:
   choose explicitly; the first matches a literal below-next-major requirement,
   while caret gives the tighter 0.x compatibility boundary. Neither is selected
   by this draft, and the resolver never rewrites a declared caret. Also confirm
   no automatic downgrade and explicit update for an unbounded new member.
6. Confirm refusal on unconfirmed system/MCP changes and the proposed removal
   trigger tightening? Recommendation: yes; no automatic old-lock fallback for
   this refusal and no stored confirmation.
7. Confirm offline/held-lease refresh deferral with old-lock launch only when
   independently admissible, and indefinite retention of the immediately
   previous usable lock/generation until replaced or explicitly pruned when
   unreferenced? Recommendation: yes; active/resume/rollback roots remain live.
