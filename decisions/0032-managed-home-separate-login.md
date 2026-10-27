# Draft Decision 0032: Opt-in separate login for a managed home

## Status

Proposed design, 2026-10-27. Owner decision **Q6** settles the direction:
credentials default to one owner, either the credential broker or the
CIP-0010 authentication node; managed homes consume without token copies.
A machine operator may explicitly opt a managed home into its own separate
login. Details below are proposed for review, not adopted schema or
implemented behavior.

## Context

[CIP-0003](../cips/CIP-0003-claude-managed-home-credential-modes.md), as narrowed
by [CIP-0010 C2/C3/C6](../cips/CIP-0010-credentials-setup-token-and-inherited-auth.md#recommendation),
already distinguishes `per-home`, node-sourced authentication and API-key
helpers. [CIP-0015](../cips/CIP-0015-login-readiness-and-profile-preparation.md)
adds a machine-owned store selector and interactive login ceremony. A separate
file or `isolation=isolated` establishes neither separate login ownership nor
account/process isolation.

This note follows the authority and publication boundaries of
[#183](https://github.com/relux-works/curator-spec/pull/183),
[#193](https://github.com/relux-works/curator-spec/pull/193) and
[#195](https://github.com/relux-works/curator-spec/pull/195): explicit authority,
compatibility limits and admit/refuse obligations precede implementation.

## Proposed decision

### 1. Machine-owned selection

Like Q1's [operator-approved policy grants](0031-policy-derived-workspace-trust.md),
the operator role approves the exception through authenticated Curator commands;
a keeper acts only within that approved role. Packages, profiles, overlays,
repositories, provider arguments and system locks cannot create, widen or
renew it. A package's statement of credential need grants no selection authority.

Keep selection in operator-owned machine configuration. The existing logical
source key is `environments.credential_source.<profile>.<env-id>`; CIP-0015's
store key remains `environments.credential_store.<profile>.<env-id>`, selecting
`native | file | keychain`. Extend the **machine source selector** with an
exact lane/home binding in a future closed containing revision. Store choice
stays orthogonal and must agree at bootstrap and launch; choosing `file`
alone never opts in. Today's profile/environment-only keys cannot encode
lane/home exceptions; accept no invented nested member or profile-name convention.

The proposed entry binds canonical environment, profile/lock identity, lane
and Werkstatt allocation, retained home identity/generation, source `per-home`,
approving operator and actual approval actor, approval revision, validity and
revocation history. Protected manager state identifies the home, not a supplied
path. Scope is **per environment, per lane, per home**, without wildcard or
cross-lane inheritance. Replacing/relocating the home or changing its admitted
lock/allocation requires explicit re-admission, never retargeting old consent.

Unattended policy defaults to the independently configured broker or node owner;
it never chooses by availability. Missing owner configuration refuses. The
separate-login entry is an explicit exception. CIP-0010 source-policy v1's
absent-entry `per-home` default remains compatibility behavior for existing
routes, not unattended approval. Migration inspects existing homes and obtains
explicit approval while preserving login bytes; no upgrade silently enrolls,
logs out, opts in or switches a working source to the shared owner.

### 2. Mapping and passthrough

| Existing axis/mode | Proposed relationship |
| --- | --- |
| CIP-0003 `per-home` | Reuse this source mode with explicit lane/home approval. Separate-login is a policy restriction on it, not a fifth credential mode. The home owns a fresh vendor login, never a clone of the shared login. |
| CIP-0003 `token`, now CIP-0010 `node:<label>` | Shared-owner path; cannot supply credentials, refresh state or fallback to this home. |
| CIP-0003 `helper` | Retains API-key scope; it cannot stand in for a separate login. An effective competing helper is a source conflict. |
| Historical `shared-file` / credential passthrough | Not separate login. CIP-0010 replaces shared-file with node; legacy symlinks do not become separate logins. No shared/native credential symlink, hard link or copied auth file is admitted here. |
| Decision 0017 `shared | isolated` | Require `isolated` native-store handling. Existing shared locks retain their veto. This is bounded store separation, not account/process isolation. |
| CIP-0015 `native | file | keychain` | Selects a qualified store for the home-owned login, not its source. Unsupported mappings refuse without store search/fallback. |

Non-credential provisioning seeds retain their rules; auth/refresh state never
becomes a seed. Source/store transitions require explicit inspect → plan → apply;
repair cannot migrate, copy secrets or delete conflicting credentials to pass.

The node/broker keeps serving other approved homes but receives no enrollment,
binding, lease, lookup or refresh request for this home's login, and must never
read or serve it. The executor checks the exception before requesting any shared
secret. Conversely the home must not reach the node store, broker socket or
native shared login through inherited environment, helpers, settings, mounts
or other effective provider inputs. Competing sources refuse; they are neither
silently stripped nor allowed to win through provider precedence.

This two-way boundary needs qualified executor/service protection. A selector
cannot stop unrestricted same-UID processes reading each other's secrets.
Where actual exclusion requires [CIP-0024 station protection](../cips/CIP-0024-agent-stations.md)
or another protected boundary, keep the exception unavailable until qualified;
do not describe ordinary same-UID configuration as secret isolation.

### 3. Lifecycle

**First login.** The operator approves the exact selection/allocation, then
arranges an attended bootstrap outside the unattended job. Use
[CIP-0015's `env login` ceremony](../protocol/login-readiness.md#3-env-login),
a trusted machine executable and the same home/store/OS identity and qualified
session class that later launch will use. The operator or an explicitly approved
human delegate answers the vendor terminal/browser prompts. Agents never answer
TUI prompts, synthesize keystrokes or collect a token for the human.

The existing command is `curator env login <env-id> --profile <name>`.
It can bootstrap a lane only when protected lane-aware resolution proves it
targets that exact home. Lane/home grammar and routing must be published first;
no undocumented flag or manual home-variable retargeting is authorized here.
A remote lane needs an approved interactive session under its own identity,
not credentials copied from a laptop. Without that channel it waits for bootstrap.

Require a current isolated home, stable source/store/allocation and #193 writer
admission with no holders. Release short mutation locks before browser I/O,
retain exclusion of competing starts/writers for the ceremony, and revalidate
identity/approval before exec and completion. The mechanism carrying that
exclusion across browser I/O is a publication dependency, not a long-held
manager mutex or an invented lease kind. Disable transcript capture; persist
no callback, token, stdin or environment value. Partial vendor writes/cancellation
stay local and non-admitting until verified recovery; never erase a prior login
or retry silently. A headless start cannot open login or borrow shared auth.

**Expiry and refresh.** The vendor owns refresh and writes only this home's
selected store. Curator status retains metadata-only `present | absent | unknown`
in the calling session: presence proves neither authentication nor ownership.
No secret parsing, token digest or helper probe establishes separation. Exact
provider/store/session tuples require effective-source and refresh qualification.
Unknown expiry stays unknown. Known login expiry without qualified refresh
recovery refuses; ordinary refreshable access-token rollover is not a revoked
login. Typed runtime auth failure parks the job and reports `reauth_required`,
without unattended login, shared fallback or indefinite retries.
Refresh/re-login cannot renew operator approval.

One home per lane does not mean one refresher: #193 permits multiple hosted
holders in the admitted lane. Concurrent starts need qualified single refresh
ownership for this login; otherwise refuse the extra start. CIP-0010's Codex
single-auth-owner-per-account obligation is unchanged. A fresh file/browser
login does not establish an independent refresh family or authorize a second
owner for that account. Known account-owner collision refuses; unavailable
ownership evidence leaves the tuple unqualified. Separate-login does not itself
promise a distinct account or same-account multi-owner support.

**Revocation.** Record a durable approval tombstone and advance its generation
before cleanup, denying new starts even when the store is unreadable. Serialize
revocation with final start admission: a completed revoke before that boundary
must refuse the start; an already admitted process follows the running-session
rule below. Never
switch to shared auth or enroll the revoked login in the node. Policy revocation
and vendor revocation are distinct: a human performs vendor logout/revocation
through the approved ceremony. Remove only proven owned state under writer
gates; conflicts remain cleanup pending. Admission failure never authorizes
credential deletion. Deleting a policy cannot recall credentials in a process.

Running sessions are not implicitly terminated; drain/stop and lease release
follow launcher contracts, retaining the lease when termination is unconfirmed.
Resume/restart needs fresh admission. Re-enabling requires new approval and
login evidence; an old selector or residual file cannot override the tombstone.
Returning to shared auth requires a separate explicit migration.

**Home lease.** Keep [#193's HL24 allocation and refuse policy](../protocol/home-leases.md#5-consumer-requirements-and-isolation-policy):
one managed home per unattended lane, one profile per Werkstatt, no cross-lane
or ad-hoc sharing. Holders block login, source/store adoption, replacement and
cleanup writers. No implicit break, alternate-home workaround or token copy.
Hosted starts retain acquire/bind/release and terminal-replay refusal. Native
unhosted starts still take no #193 lease and need separate launcher allocation/
concurrency admission. Home leases are not broker leases, refresh locks or grants.

### 4. What the launcher sees at every start

[#197's effective-posture contract](../protocol/effective-posture.md) requires
current protected authority and an exact immutable plan binding. Its closed
`effective-posture/1` has **no credential-selection field**. Do not insert an
optional member, repurpose `native_policy` or infer opt-in from `yolo`, a lock
digest, store selection or lease.

Propose a required-understanding **successor posture carrier**, whose closed
credential-selection record contains only non-secret metadata:

- Effective `per-home` source and actual selection provenance; protected operator
  approval reference, policy digest/revision, validity and revocation generation.
- Exact environment/lane/home binding; configured/effective store and qualified
  provider/backend/session identity.
- Bootstrap/refresh-ownership evidence references and caller-session readiness,
  explicitly separate from authentication and approval.
- Fresh protected source-exclusion verdict, explicit no-shared-fallback policy
  and the existing prepared home-lease relation where hosted.

These are proposed logical fields, not allocated wire names or a schema version.
No account identity, token, refresh state, token-derived hash, helper body,
auth-store contents or credential-bearing argv enters the carrier. References
identify protected evidence, not readable secret-store paths. Keep readiness's
three values; approval/lifecycle are separate.

Every start, resume and restart obtains fresh protected manager/operator evidence,
checks allocation, source exclusion, refresh ownership, readiness and revocation,
and binds complete successor bytes/digest into the immutable launch plan.
Immediately before provider start recheck approval generation, provider/store/
session, home/plan binding and the hosted prepared lease. Consume Curator's
projection without opening home credentials. Copied records or rehashed stale
decisions cannot grant authority. Changed inputs need a fresh admitted plan,
never an in-place baseline update or shared fallback.

Curator owns selection, protected home/readiness projection and typed fields;
curator-run owns allocation, immutable consumer plan, start admission and public
refusal mapping. The node/broker owns exclusion at its service boundary.
Joint publication must cover machine config, marker/status/source projection,
successor posture, direct/hosted plans and receivers, bootstrap exclusion and
revocation reads. Old consumers reject the negotiated successor. Until that
publication and exact release qualification, this unattended exception is
unavailable. Existing carriers/defaults remain unchanged.

### 5. Diagnostics

This is proposed semantic reuse, not an extension of frozen
[local-node refusal-v1](../protocol/local-setup-token-source.md#9-exact-command-refusals-and-conformance).
The successor and curator-run must publish exact wire codes, typed reasons
and exits before implementation. Node absence must not mean missing home login.

| Condition | Proposed diagnostic/action |
| --- | --- |
| Package/profile requests opt-in or supplies selector authority | Existing `usage` at declaration/config validation; no selector/grant write. |
| Opted-in home has no completed login | **New proposed** `credential_home_login_required`; attended-bootstrap guidance, never `credential_node_missing`. |
| Shared credential/competing effective source; wrong login ownership | Existing `credential_source_conflict`; `environment_credential_conflict` for conflicting/forked native-store objects. Preserve bytes. |
| Unsupported machine store mapping / native selector | Existing `environment_credential_store_unsupported` / `environment_credential_unsupported`; no fallback. |
| Shared isolation lock / unsupported isolated backend | Existing `environment_isolation_lock_conflict` / `environment_isolated_unsupported`. |
| Source/store change without adoption | Existing `credential_source_migration_required`. |
| Wrong lane/home/approval binding | Reuse `credential_binding_mismatch` with a home-specific successor reason. |
| Revoked approval / stale selection or plan / known expired login or approval | Reuse `credential_source_revoked` / `credential_source_stale` / `credential_source_expired`, naming the failed subject; no implicit renewal. |
| Unreadable/unsafe login metadata | Existing `credential_store_unreadable`; unknown never becomes absent/present. |
| Unknown ownership, missing carrier/consumer or unqualified exclusion/refresh | Reuse `credential_injection_unavailable` with the exact missing-obligation reason in the successor mapping; no child/shared fallback. |
| Writer blocked by holders / hosted lease admission fails | Existing `environment_home_leased` / launcher `session_home_lease_unavailable`, retaining Curator code/reason. |

CIP-0015 non-interactive login remains usage exit 2. Readiness labels are not
new command codes; preserve child failures separately. Reuse CIP-0010 events
`credential_expiring`, `credential_expired`, `credential_error`, `reauth_required`
only when evidence supports them; 401/403 alone proves neither expiry nor
revocation. Output neutral home/lane references, source/store, approval revision,
failed obligation and operator action, never secrets, accounts or raw vendor output.

### 6. Adjacent admit/refuse cases

Each pair assumes unrelated gates pass and changes only the stated fact.
These are **design counterexamples**, not executed tests or certification.
Every refused admission leaves provider-start count zero and preserves existing
credentials, config, approval and lease state; an explicit revoke's tombstone
and permitted sanitized refusal telemetry are separate authorized effects.
In the expiry rows, expiry means no qualified refresh recovery remains.

| Case | Admit control | Refuse witness and postcondition |
| --- | --- | --- |
| Package requests opt-in | Protected operator approval selects exact lane/home `per-home`; package supplies context only. | Package/profile selects separate-login or impersonates approval: `usage`; no machine selection, grant, login or provider start. |
| Opt-in home handed shared credential | Executor selects home login and never requests shared delivery. | Shared broker/node credential supplied through launch input: `credential_source_conflict` before provider start; no persistence/forwarding to children. |
| Shared owner leaks into home | Inspection proves no inherited credential/helper/settings injection/shared store; node cannot inspect the private login. | Shared owner becomes reachable or wins precedence, or node can read/serve home login: `credential_source_conflict`; unestablished exclusion: `credential_injection_unavailable`. No weaker-source retry. |
| Copied token | Vendor performs an approved fresh login in place under qualified ownership rules; record non-secret evidence only. | Shared/native token or refresh state copied/imported, even into a private 0600 file: `environment_credential_conflict` for known copied/forked objects; unknown provenance cannot qualify. No extraction, copy-back, merge or secret hash; preserve conflicting bytes. |
| Stale opt-in after revocation | New approval/bootstrap evidence matches current non-revoked generation/home. | Old entry/plan/file survives tombstone: `credential_source_revoked` (stale binding also fails); zero starts, approval renewal, credential deletion or shared fallback. |
| Missing login / expiry | Current approval, qualified login ownership/source and current-session presence, no known expiry. | Missing: `credential_home_login_required`; expired: `credential_source_expired`; unreadable: `credential_store_unreadable`. No TUI/helper probe/borrowing. |
| Lane and lease | Exact lane/home, still-prepared hosted lease; login writer has no holders. | Cross-lane alias, terminal replay or leased login writer refuses under allocation/#193 gates; no auto-break or replacement home. |
| Refresh and posture | Qualified single refresh ownership and successor bound to protected current evidence. | Unqualified concurrent refreshers, account-owner collision, old carrier or changed approval/store/home refuses; no cloning, field dropping or caller-only authorization. |

## Alternatives

A new mode duplicates `per-home`. Isolation/file-store flags confuse storage
with authority. Package opt-in grants authority to untrusted content. Shared-file
passthrough, cloned tokens and silent shared fallback violate Q6's boundary.
Automated TUI answers contradict human-only bootstrap. Reject these alternatives.

## Compatibility impact

This draft changes no normative prose, schema, generated vector, source-policy
default, fragment or carrier. Adoption needs coordinated publication, explicit
migration and required-understanding negotiation. Legacy defaults do not enroll
homes into new unattended policy; legacy links do not qualify as separate login.
Machine store and isolation constraints keep their existing meaning.

## Security impact and validation boundary

Separate login adds a credential/revocation domain, not sandbox permissions,
project trust or hook consent. Lane separation needs protected allocation;
same-UID disclosure, runtime exfiltration and refresh need actual qualified
boundaries. Metadata/synthetic fixtures cannot prove them.

Before activation, consumers need paired production-entry tests for the cases
above, synthetic secret-absence checks over artifacts, bounded known-violation
controls for admission/exclusion checkers, interrupted bootstrap and revoke/retry
witnesses, and authorized disposable-account qualification of exact provider/
store/session/concurrency tuples. Preserve operator homes and sessions.
This note performs no login, secret read, live experiment or implementation.

## Open questions for the owner

1. Who may bootstrap a remote lane account: only its owner, or a named human
   delegate under recorded operator approval?
2. Keep same-account Codex shared-owner/separate-home combinations unavailable
   under C2, or commission a separate single-owner-compatible design? Recommend
   keeping them unavailable; a fresh file/login is insufficient evidence.
