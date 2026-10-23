# Protected local Claude setup-token source, revision 1

This normative amendment adopts the local slice of CIP-0010 C1–C4/C6 by
owner decision 2026-10-16 (support is required), with the narrow C7 sequencing
exception below. It builds on the accepted rc.7 implementation-wave baseline,
including CIP-0014/0015/0017/0018 and the joint L15-0/C0
[carrier allocation](rc7-carriers.md). It is publication only: no store,
metadata reader, vendor execution or route qualification is claimed.

## 1. Scope and source (L1)

An implementation MAY adopt this source for Claude Code launches executing
under the enrolling OS UID on the same host. This adoption MAY precede the
cross-user broker sequence in CIP-0010 C7. It grants no broker, remote,
cross-user, lease or peer authority. Helpers, other harness node kinds and
refresh-token provisioning are outside this slice. Native per-home login
remains the default and retains its existing behavior. Remote Control and
fetched claude.ai connectors are outside this source's capability.

The only selector is user-owned, non-lockable machine configuration:
`environments.credential_source.<profile>.claude_code = per-home | node:<label>`.
The CLI is `curator env config set credential_source.<profile>.claude_code
per-home|node:<label>`. Labels and profiles use the existing portable identifier
grammar. Absence preserves source-policy v1's `per-home`; it does not adopt
source-policy v2's explicit-entry requirement. Packages, repositories,
overlays and system locks MUST NOT select a source, node, account or material.
The source selector is not an executable path, environment name or secret.

## 2. Custody, input and atomicity (L2, L8)

The initial backend is the per-user file `~/.curator/auth/<label>/secret`:
0700 protected directory and 0600 regular file, on macOS and Linux. No node
Keychain backend is admitted. Node [registration](../schemas/local-setup-token-v1/registration-v1.schema.json)
is separate metadata: harness, kind, user label, fresh opaque reference,
source/policy generations, lifecycle state and timestamps. Labels are not
verified identities. No credential value, digest, prefix, account email or
inferred organization MAY enter registration or public metadata.

```text
curator env credential enrol claude_code --node <label> --token-stdin [--issued-at <date>]
curator env credential status --node <label>
curator env credential revoke --node <label>
```

The human obtains a token privately with `claude setup-token` and supplies
only the deliberately selected token. The vendor transcript is not a stdin
protocol; the login wrapper MUST NOT capture it. No token argv, environment
variable enrollment or arbitrary file-path interface is admitted. Before any
stdin read, validate user authority, label, trusted ancestry and operation
preconditions. Input MUST be a non-terminal stream containing 1–16384 token
bytes, optionally followed by one LF or CRLF. Read at most 16387 bytes to detect
overflow. After removing that one terminator, accept only opaque bytes 0x21–0x7e;
reject all whitespace/control bytes, empty input, multiline transcripts and
oversize input with `credential_enrollment_input_invalid`, without echo or
original-size reporting. Structural acceptance is not vendor authentication.
No shell evaluation or token-prefix check establishes authenticity.

`--issued-at` is an actual UTC calendar date `YYYY-MM-DD`, not later than the
enrollment date. Invalid dates refuse before stdin read. Record its UTC midnight
as stated issuance, separately from enrollment time. Stated expiry is the UTC
anniversary one calendar year later (February 29 clamps to February 28).
Without issuance both issuance and computed expiry MUST remain unknown:
`issued_at` is absent and `expires_at` is `unknown`. Status MUST label issuance
as stated; it MUST NOT infer it from enrollment time or decoded token bytes.

Reads and writes MUST walk protected ancestry without following symlinks;
validate owner, private mode, effective ACL protection, regular-file type,
link count one and opened-object identity. A validated pathname MUST NOT be
reopened after a substitution window. Unsafe existing objects refuse
`credential_store_unreadable`; never follow, chmod, replace or repair them.
Credential material MUST NOT enter generic journals, backups or temp directories.
Private atomic staging, if used, belongs inside the same protected store,
with identical protection, cleanup and crash-recovery rules.

Enrollment, replacement, revoke and material release MUST serialize per node.
Secret and registration generations MUST match. Crash before/after either
publication MUST NOT combine old authorization and new material. Failed first
enrollment publishes no usable source; failed replacement preserves the old
coherent generation or makes the source unavailable with explicit recovery.
Ambiguous/incomplete recovery refuses `credential_store_unreadable`. No failed
operation publishes a usable partial registration or exposes input. Publication
of a coherent generation and material release have a single ordered node-lock
boundary. Re-enrollment, including replacement, MUST create a fresh opaque
reference and increment source and policy generations; references MUST NOT be
recycled under a reused label. Generation counters MUST NOT wrap.

Local revoke atomically makes registration unusable and invalidates bindings
before acknowledging success; it safely removes stored material under the same
lock. Interrupted deletion remains delivery-disabled and recovery-required.
Success says **local delivery disabled** and gives separate vendor revocation
guidance. It does not revoke the vendor token, stop arbitrary processes, erase
already delivered values or recall running sessions. Known expiry refuses exec;
unknown expiry stays unknown. Typed authentication failure permits bounded
re-enrollment/restart guidance, never endless retry or native fallback. Quota,
permission, transport and ambiguous errors remain distinct; an arbitrary
401/403 does not establish revocation. Transcript resume under a new token
requires separate qualification.

The store protects against other OS users and accidental artifact copying.
Same-UID trusted processes and the harness can access material. `isolated` is
not OS/account isolation. No root, compromised same-user process, backup,
process-memory or perfect garbage-collected-memory-erasure protection is claimed.

## 3. Policy and home adoption (L3)

Resolve source → home-store selector → isolation admission → link strategy.
Node mode requires `credential_store=native` (including its default): this
means no override of Claude's home store, not node custody in Keychain.
Explicit `file` or `keychain` refuses
`environment_credential_store_unsupported`. A node home MUST have no native
credential-store link. An implicit shared default may yield to linkless
isolated mode; an explicit shared setting refuses `credential_source_conflict`,
and an applicable shared lock refuses `environment_isolation_lock_conflict`.
An isolated lock does not promise separate vendor accounts or prohibit reuse
of a deliberately selected external token. macOS native shared stays unsupported.

Existing homes MUST use inspect → plan → apply with a new marker/source
identity. Repair MUST NOT migrate a source. Old per-home marker plus selected
node refuses `credential_source_migration_required`. Native login presence,
native links or competing effective auth settings refuse
`credential_source_conflict`; native credentials MUST NOT be deleted, extracted,
exported or copied. Unreadable evidence MUST NOT count as empty: refuse
`credential_store_unreadable`, preserve the home, and require an independently
prepared node-source home if safe absence/adoption cannot be established.

## 4. Readiness and lifecycle (L4)

The closed `login-row-v1` is unchanged; command diagnostics below MUST NOT be
added to its reason enum. Node observations use `source=node`, `store=native`,
`session=caller`, backend `file` when established, otherwise `unknown`.

| Protected metadata observation | login | reason |
|---|---|---|
| Active registration and accessible nonempty regular candidate, no conflict | present | candidate-present |
| Successful lookup establishes no candidate, including completed revoke | absent | candidate-absent |
| Denied/unsafe/inconsistent registration or incomplete recovery | unknown | metadata-unavailable |
| Untrusted home boundary | unknown | untrusted-home |
| Empty candidate | unknown | empty-file |
| Native home login or competing effective source | unknown | source-conflict |
| Source reader/policy unadopted or unqualified | unknown | unqualified-backend |

Readiness MUST NOT open credential content, execute an agent (including version
or auth-status probes), call a helper/network, prompt or retrieve material.
No node label, source reference, expiry or refusal code belongs in the row.
Registration lifecycle and executor capability are separate reports. A known
expired token may still be a physically present candidate; the lifecycle report
requires re-enrollment and exec refuses. Presence does not prove token validity,
inference, expiry, injection, Remote Control or source authority.

`profile prepare` retains current+present as its strict exit-0 condition,
not execution qualification. Unknown never triggers login. For node absence or
unknown it MUST NOT mint/enroll a token, invoke native login or prompt.
`env login` refuses `credential_source_enrollment_required` with enrollment
guidance. Home-owned isolated absent login retains the existing admitted ceremony.

## 5. Closed carriers (L5)

The [schema index](../schemas/local-setup-token-v1/README.md) publishes complete
closed successors under the same allocation lineage as L15-0/C0:

| Carrier | Discriminator | Change from joint baseline |
|---|---|---|
| Manager | schema_version 6 | Config 5 plus optional machine `credential_source` subtree |
| Status | status env-status-v2 | Complete status 1, frozen rows with node/native/file-or-unknown/caller relation |
| Marker | version 6, hash_version 2 | Marker 5 plus required per-home or node source identity |
| Fragment | fragment launch-env-fragment-v6 | Fragment 5 plus optional node projection; absent retains per-home |
| Local final-exec plan | plan local-final-exec-v1 | Complete dedicated headless entry document, not a hosted/ax envelope |

All retained required fields and semantic path/channel/permission rules remain.
Manifest 2 and lock 4 remain closed and contain no machine source policy;
marker source identity is machine provenance, never package content or authority.
Node marker is managed-home, with empty passthrough, seeds and seed links.
Other-adapter marker source is per-home. Source changes require normal explicit
migration; source metadata MUST NOT change package lock identity.

`source-projection-v1` is exactly `{source, source_generation, policy_generation}`.
`source` and the required-understanding extension
`works.relux.curator.credential/1` are exactly
`{mode: "node", source_ref, harness_channel: "CLAUDE_CODE_OAUTH_TOKEN"}`.
References are opaque, newly random 128-bit lowercase values with `local:`
prefix, never token-derived. Generations are positive JSON safe integers.
A plan MUST carry the exact source branch and generations of its full fragment.
No broker branch is reinterpreted or adopted. No secret path, token/digest,
ambient-name fallback or arbitrary branch is admitted. Every selected hop
MUST understand the entire document and required extension. Source metadata
MUST be covered by the enclosing plan's canonical digest when transported
inside another jointly published plan. That embedding is not allocated by a
standalone source schema.

Config 1–5, marker 1–5, fragment 1–5 (especially v4), status 1, manifest and
lock schemas retain their exact previous bytes and semantics. Old readers
MUST reject successors and additions under old discriminators. No relabeling,
policy removal, silent downgrade or env/shell projection of node mode is
permitted. Unknown source/carrier semantics or incapable consumers refuse
`credential_injection_unavailable`, before material access, output or mutation.
Malformed supported metadata refuses `usage`. Decoders MUST reject duplicate
keys, invalid UTF-8, nesting deeper than 16 or documents over 1 MiB.

Snapshot descriptors, manifests and archives MUST contain neither material,
material digest nor credential-source metadata (including registration,
projection, binding or node marker). Machine source state stays outside the
snapshot. A relocated snapshot or source caller's present row supplies no
credential authority; destination Curator runtime preparation and a fresh local
binding remain mandatory. No credentials are copied across UID/host to make
an unavailable source work.

## 6. Local binding and final boundary (L6)

The closed protected `credential_binding/1` local shape has `scope=local`,
executing UID, opaque local host reference, profile, harness `claude_code`,
node label, source reference and generation, fixed channel, approved HTTPS
endpoint, approved executable SHA-256 and current policy generation.
It has no broker peer, broker generation or lease fields. Host reference is
local protected host identity, not a hostname or portable authority. A plan
MUST NOT install or supply this protected binding. A digest, source reference,
matching caller values or self-declared capability alone grants no authority.

At the actual process-start boundary the executor MUST:

1. Validate full carrier, required-understanding semantics, route and independently
   qualified `credential-injection/1` tuple; reject another UID/host,
   unsupported interactive mode, `--bare` or unknown semantics before material.
2. Ask Curator for source/home admission, without reconstructing a home inventory.
   Re-resolve local protected binding and effective policy/settings, executable
   identity and endpoint; changed or unreadable evidence refuses.
3. Before lookup reject competing inputs by name/presence, even equal or empty:
   OAuth/API/bearer/refresh variables, host/FD token channels, `apiKeyHelper`,
   settings `env`, provider/gateway/profile/federation switches, secure-storage
   overrides, endpoint/header overrides and native argv that replaces policy.
   Reserve the injected name in generic literals, inherited-name requests,
   MCP interpolation/headers/argv and configuration. Carry the retained
   CIP-0003 conflict inventory through every input layer. Reject unqualified
   loader/runtime startup or code-loading inputs, including `LD_*`, `DYLD_*`,
   `NODE_*` and `PYTHON*`; an unchanged binary digest cannot authorize supplied
   code. Preserve required benign environment through explicit qualified policy.
   Construct the final environment from admitted non-secret inputs, never by
   blindly inheriting the caller's full environment.
4. Under the node lock recheck reference, generation, current policy/binding
   and known expiry, then validate/open exactly the protected object. This is
   the revoke/material-release linearization point. No missing, revoked,
   unreadable, changed or expired source permits fallback.
5. Add `CLAUDE_CODE_OAUTH_TOKEN` only to the actual approved Claude child's
   private environment immediately before start. Never modify global process
   environment, `EnvLiterals`, `env_names`, argv, plan requests, shell strings,
   env files, ax environment, receiver payloads, receipts or logs. Close
   credential FDs before child exec and discard buffers when no longer needed.

## 7. Entry point and qualification (L7)

The proposed same-user headless chain is:
`task-board spawn → approved curator-run local-final-exec → Claude noninteractive process`.
Its explicit entry grammar is:

```text
curator-run local-final-exec --plan <file|->
```

The plan MUST validate the complete `local-final-exec-v1` schema: route
`task-board-headless-local`, full v6 fragment, required credential extension,
source/policy generations and non-secret invocation (absolute binary/cwd,
approved digest and endpoint, ordered argv, admitted baseline environment,
null or bounded payload stdin). The document is metadata only and at most
1 MiB/depth 16. Payload stdin is supplied separately through typed process IO,
not token enrollment or plan JSON. Invocation fields are requested intent,
not authorization. The launcher companion SPEC MUST publish/import this exact
entry/carrier and API at an explicit Curator module pin before producer emission;
T3a/T3b/T4 implementation and qualification are separate, currently unverified.

| Qualification row | Admission boundary |
|---|---|
| Direct local noninteractive | Separately qualified direct final executor; proves no spawned/tracked support |
| task-board same-user headless local | Approved local-final-exec plus T4 real spawn uptake; independent qualification |
| Tracked ax | Refused until actual final receiver supports this protected lookup and carrier |
| Interactive hosted PTY | Separate mode qualification; cannot inherit headless admission |
| tb-sessiond lookup/restart | Refused under local-hosted-launches §§4/6 |
| Another UID/host or remote/archive-only | Refused in this slice |

This route is independent of the full CIP-0016 primary hosted matrix. That
matrix still seals the exact provider process (§4), with fresh restart secrets
resolved by the caller and daemon lookup prohibited (§6). Node mode MUST NOT
be enabled there through an internal injection callback, hidden wrapper,
caller-side token sealing or daemon lookup. A later hosted token route needs
an explicit separately reviewed amendment and qualification.

`credential-injection/1` MUST be advertised only per published, behaviorally
qualified route/platform/harness release and configuration tuple. Qualification
MUST establish selected-source use without native secret reads, rejection of
competing sources and no token exposure to uncontrolled MCP, hooks, tool/shell
children, plugin helpers, telemetry, debug dumps or transcripts. Include MCP
interpolation and settings reload/source/endpoint replacement; removing only
the original env name is insufficient. Use a pinned real harness, disposable
sentinels, child probes and a known-leaking detector control. Mocked exec,
metadata/schema passes, clean initial env and guessed scrub flags cannot
qualify it. If a clean mechanism is unavailable, capability stays unavailable.
The trusted harness itself intentionally sees the token; no non-extraction
claim is made. Unsupported `--bare`, recipients and interactive routes refuse.

## 8. Public in-process API

Curator owns `github.com/relux-works/curator/pkg/localcredential`, backed by
private `internal/envcredential`. Launcher MUST pin/import the public facade;
it cannot import another module's `internal` package. T0 freezes these names
and semantics; T1/T2 do not have to implement the final-launch API prematurely.
T3a publishes a version pin; no usable pin or runtime implementation is claimed here.
The Go API is in-process and MUST NOT become a serializable command/getter:

```go
type Source struct {
    Reference string
    Generation uint64
    PolicyGeneration uint64
    Channel string
}
type DescribeRequest struct { Profile string; Node string }
type Description struct {
    Source *Source // nil when registration identity is unavailable
    Registration string // active, revoked, recovery-required, absent, unknown
    IssuedAt *time.Time // stated; nil means unknown
    ExpiresAt *time.Time // nil means unknown
    Readiness *LoginRow // exact frozen row; nil without a requested profile
}
type Invocation struct {
    Binary string
    ExecutableSHA256 string
    Cwd string
    Argv []string
    Environment map[string]string // admitted non-secret baseline only
    Endpoint string
}
type StartRequest struct {
    Profile string
    Source Source
    Route string
    Invocation Invocation
}
type ProcessIO struct {
    Stdin io.Reader
    Stdout io.Writer
    Stderr io.Writer
    Terminal *os.File // non-nil refused until this mode is qualified
}
type Exit struct { Code int; Signal os.Signal }
type Process interface {
    Wait() (Exit, error)
    Signal(os.Signal) error
    Resize(rows, columns uint16) error
    Cancel() error
}
func Describe(context.Context, DescribeRequest) (Description, error)
func AuthorizeAndStart(context.Context, StartRequest, ProcessIO) (Process, error)
type RefusalCode string // closed refusal-v1 code enum
type Refusal struct { Code RefusalCode } // exact section 9 codes; no raw causes/input
```

`LoginRow` names the exact imported frozen row type, with no extra members.
Describe addresses the user-selected node label without requiring a reference
that does not yet exist. Profile is optional; without it no readiness row is
invented. Describe uses metadata only, including for inaccessible/absent registrations;
it never retrieves a token or executes an agent. AuthorizeAndStart independently
resolves user-owned source/home policy, executing UID/host, protected binding,
qualification and effective inputs. Caller `authorized=true`, a binding object,
a token getter, environment-map return, secret stdout/IPC, generic CLI bridge
or duplicated launcher store traversal MUST NOT exist. Start either returns
a secret-free lifecycle handle after one approved process start or a typed
refusal with no child, no fallback and no source/home mutation. Lifecycle
cancellation/signal races MUST NOT start a second child. Preserve existing
launcher signal, terminal, process-group, cancellation and wait semantics;
unsupported modes refuse rather than silently discard IO. This requires no
module cycle or import of launcher internals. Go visibility is an accidental
transport guard, not protection against malicious same-UID callers.

## 9. Exact command refusals and conformance

The closed [refusal-v1](../schemas/local-setup-token-v1/refusal-v1.schema.json)
object contains only a typed `code`; it carries no raw cause, input or authority.

All refusals precede secret access/child start unless the failing protected
object itself must be opened to establish the error. No refusal logs input,
values, token digests or original input sizes, mutates policy/home/source, or
emits usable partial output. Enrollment/revoke have only section 2's explicit
atomic state transitions. First failing admission stage wins; no catch-all
native fallback. Command diagnostics are separate from frozen readiness reasons.

| Condition / command boundary | Diagnostic |
|---|---|
| Package/overlay/repository or system-lock source authority; invalid selector/label; malformed supported JSON | usage |
| Unknown carrier/source branch/required extension; missing or unqualified route capability; unsupported mode/recipient/`--bare`; node env/shell rendering | credential_injection_unavailable |
| Node with file/keychain home selector at resolve/login/start | environment_credential_store_unsupported |
| Shared isolation lock at resolve/adoption | environment_isolation_lock_conflict |
| Explicit shared isolation, native credential/link or competing auth/settings/endpoint/startup input | credential_source_conflict |
| Old marker/source change attempted by resolve repair/start without explicit adoption | credential_source_migration_required |
| Invalid/terminal/bounded-input/date enrollment | credential_enrollment_input_invalid |
| No registered reference/candidate at final start | credential_node_missing |
| Unsafe, denied, malformed, inconsistent or unrecoverable protected store/binding lookup | credential_store_unreadable |
| Wrong UID/host/profile/harness/channel/endpoint/executable or missing protected binding | credential_binding_mismatch |
| Reused reference, stale source or policy generation, replaced/re-enrolled source | credential_source_stale |
| Completed revoke before release | credential_source_revoked |
| Known expiry before release | credential_source_expired |
| env login for node source | credential_source_enrollment_required |

No local operation uses broker `lease_*` diagnostics. A revoked record wins
over its removed candidate; absent record is missing, denied lookup is unreadable,
and an active replacement with different reference/generation is stale.
See the [publication corpus](../conformance/local-setup-token-v1/README.md) for
ST-01/06/07/09/13 paired metadata/refusal fixtures and checker controls.
ST-02–05/08/10–12/14–15 runtime obligations in the design remain mandatory for
the respective implementation leaves; semantic vectors do not qualify vendor
execution, crash recovery, filesystem protection or absence of child leakage.

## 10. Proposed hosted-station qualification amendment

**Status: proposed contract, not activation.** Sections 1–9 remain the admitted
local-source revision 1. This section proposes the additional qualification
requirements for a long-lived Claude station on the same host and UID as its
enrolled source. It does not publish a hosted carrier, implement the source
store/API, qualify a provider, or lift section 7's hosted/Terminal refusals.
The requirements below apply to a future jointly adopted hosted route; until
its publication and behavioral qualification, node-source hosting MUST remain
unavailable, with no manager contact or native/per-home fallback.

### 10.1 Dependency and ownership boundary

The proposal relies on the following source snapshots, not on inferred runtime
support. Re-pin the owning contracts when admitting an implementation or
qualification tuple; do not treat a branch name or a newer draft as authority.

| Dependency | Inspected revision and boundary |
|---|---|
| CIP-0010 and local source | [Spec a77686c8](https://github.com/relux-works/curator-spec/tree/a77686c8112d60841236f2107d7e085e48361f6e): CIP-0010 Draft revision 4 and local-source revision 1. Sections 2, 6 and 8 retain custody, protected binding and the in-process final boundary. |
| Station account, keys, paths and lifecycle | [CIP-0024 Draft fb4e16ab](https://github.com/relux-works/curator-spec/blob/fb4e16abe1cf4aa2c87e01a87203134b4f06b6b9/cips/CIP-0024-agent-stations.md): one OS account per station; separate account/key and home/composition owners; protected assignment, fenced lifecycle and unknown-state retention. This draft publishes no station wire or live capability. |
| Hosted lifecycle and exact process | [Local hosting](local-hosted-launches.md) and [CIP-0023](../cips/CIP-0023-exact-plan-hosted-launches.md) at a77686c8: preserve their selection, preparation, exact-process, original-home/session-lease, resume and recovery gates. |
| Launcher companion | [FRONT-DOOR section 9 and Appendix B at 60143fec](https://github.com/relux-works/curator-agent-launcher/blob/60143fec205e21a7b7ec98674f6e48cd646db22a/FRONT-DOOR.md): hosted node source is refused; the per-session final-owner amendment is proposed, not qualified. |

The station owner must publish the relied-on account/UID, platform-owned versus
station-writable path, protected trust/key and lifecycle bindings before their
use in a live tuple. CIP-0024's inspected key-custody interim is not a grant to
choose a successor signer, key backend or writable trust path here. This
amendment allocates none of those interfaces, nor station-record, role,
raise-by-card, a2a/profile-link or product-card fields. An unresolved normative
choice stays an explicit owning dependency; it cannot become a local workaround.

Before implementation, identify the writers and published pins for T1/T2
custody/policy, T3a `pkg/localcredential`, and launcher/manager consumption.
The specification of `AuthorizeAndStart` is not an available module pin.
Acceptance of this text does not assign those implementations or silently
include them in an injection-only change.

### 10.2 Account-local source and profile continuity

A station has a distinct OS account from the outset. The source and final
executor MUST use that station's admitted UID and local host binding. The
human's separately authorized enrollment occurs in the destination account;
neither a raising orchestrator nor a manager copies an operator's source,
`source_ref`, HOME, native login, token, private key or trust state into it.
No cross-UID broker, account allocator, privilege-escalation helper or token
transport is admitted by this local-source amendment.

Preserve the admitted role-profile source, dependency closure and lock unless
a separately reviewed pin/closure change is intentional. Matching profile or
lock bytes are configuration identity, never credential or OS-account
authority. Reject unexpected profile drift without silent repair, repinning,
old-HOME reuse or account creation. Source selection remains user-owned machine
configuration; a profile, product card or package cannot select credentials.

Before a later native migration admission, its owning private task records
old and target host/account, profile source/revision/closure/lock, managed
HOME, lifecycle owner and current execution generation. It also records the
destination's supported cache/root layout, protected source/binding metadata
and approved enrollment route, without material or material digests. Explain
legitimate account-dependent rendered-path/context differences: neither copied
root hashes nor unexplained new hashes prove the destination boundary.
Do not populate real continuity rows in this shared specification or corpus.

Cache access and private Git administration require their owning supported
cross-account contracts. A writable shared cache or operator Git back-link is
not assumed. Unsupported destination cache/HOME/root layout refuses before
start without changing either account's existing state. Same-UID workers and
copied roots MUST NOT be reported as account-isolated stations.

### 10.3 Proposed hosted final boundary

Only the per-session final-process owner executing as the enrolled station UID
may call the Curator in-process `AuthorizeAndStart` boundary. The shared daemon
does not retrieve, retain or distribute material; no callback into a daemon,
token getter, caller-sealed secret, wrapper or per-home fallback substitutes
for that boundary. The trusted Claude process intentionally sees its token;
this does not claim secrecy from the harness or a compromised same-UID process.

Launcher and receiver owners must jointly publish the full hosted carrier and
its canonical digest coverage before emission. It binds the requested source
projection, admitted profile/lock, station/execution identity and generation,
non-secret invocation, route/mode and IO to the owning preparation/lifecycle
contract. These are required semantic bindings, not new JSON field names or
permission to extend `local-final-exec-v1` or another closed carrier. A plan's
source or capability declaration remains requested intent, not authority.

The final owner compares the requested source projection with its own Curator
resolve; source/reference/generation drift refuses `credential_source_stale`.
It then uses section 6's independent protected binding, policy, executable,
endpoint, competing-input and node-lock checks. Qualification must cover both
the lifecycle's one-start boundary and the node's revoke/material-release
boundary; neither lock is assumed to replace the other's ordering.

The only proposed exception to hosted exact-process execution is the final
Curator-controlled addition of `CLAUDE_CODE_OAUTH_TOKEN` to that one approved
child's private environment. All other admitted argv, environment, cwd, binary,
policy and IO stay exact. No secret enters a plan, generic environment map,
daemon environment, snapshot, journal, restart recipe, temporary file outside
the protected source store, log, diagnostic or child-environment dump.
Section 6's conflicting names are rejected by presence, including empty/equal
values. A pre-start refusal starts no child and leaves source, home, environment
and preparation state without forbidden partial writes; permitted durable
refusal/recovery telemetry follows the owning lifecycle contract.

PTY and noninteractive hosting are separate qualification tuples. A non-nil
`Terminal` remains refused until its actual mode is qualified; a headless test
cannot qualify PTY, attach or resume. Unsupported modes preserve their typed
refusal rather than dropping IO. Current local-final-exec schemas retain only
their published headless route and acquire no hosted authority from this text.

### 10.4 Long-lived execution, cutover and recovery

Preserve existing legacy sessions, homes, profile locks and live bindings while
specifying or testing this contract. A later identity cutover needs a separate
authorized operation: its lifecycle owner establishes authoritative quiescence
and release of the old execution generation before starting one target.
An unacknowledged start, missing PID, quiet inbox, expired TTL or disconnected
client does not establish absence. Unknown execution retains its claims and
must be reconciled against the same operation/manager/generation, never retried
as a second provider or resolved by stealing a lease.

Every newly started process, including a typed restart/resume, re-enters the
qualified final boundary and re-resolves current source and policy. Do not
persist material for restart or imply that a token delivered to an existing
Claude process can be recalled. Local revoke disables future delivery; it is
not vendor revocation or proof of process termination. Source replacement or
post-revoke recovery cannot reuse stale authorization. Unknown expiry remains
unknown, and transcript resume under changed authentication needs its separate
qualification under section 2.

Recovery distinguishes a provably unstarted target, uncertain start, completed
authority transition and revoked source. A filesystem rollback restores neither
revoked authority nor a released execution generation. Preserve recovery records,
leases and source-state distinctions instead of recreating old credentials or
deleting an account/home to obtain a clean retry.

### 10.5 Qualification evidence and counterexamples

The [hosted qualification witnesses](../conformance/local-setup-token-v1/hosted-qualification-cases.json)
define neutral positive controls and forbidden neighboring outcomes. They are
contract/test-plan data, not a hosted wire, executable runtime harness or test
results. The existing metadata corpus separately exercises current binding,
source and unsupported-route diagnostics; it cannot establish no-read/no-write,
one-start, isolation, real OAuth or leak containment.

Keep the following evidence claims distinct:

| Claim | Evidence required before that claim is made |
|---|---|
| Specification/fixture consistency | Schema, metadata/refusal, link and paired contract-counterexample checks. Every hosted runtime remains unqualified. |
| Synthetic final-executor behavior | Isolated disposable fixtures show one final injection, exact refusals, no fallback, residue or duplicate child, including interrupted start/cutover/revoke and valid neighboring controls. |
| Real-harness containment | Separately authorized pinned real Claude release, disposable sentinels and child probes, including MCP interpolation/settings reload, hooks, tools, plugin helpers, telemetry and debug/transcript sinks; a known-leaking detector control fails for the intended leak. A guessed scrub flag or mock exec is insufficient. |
| Actual OAuth authentication | Separate owner-run destination-account enrollment and authorized provider check; structural token acceptance and a present readiness row do not prove it. |
| Live station/pilot | Qualified account/key/path, source/API, carrier/final-owner, IO/lifecycle and real-harness tuple; owning Curator-lane pilot first, later-host activation separately admitted after its evidence. |

Record exact reviewed source/API/carrier pins, host platform, harness release,
mode, configuration, commands, exits and intended control failures for each
claimed tuple. macOS/Linux results cannot admit another OS, account, host,
harness release or mode implicitly. Unknown or failed prerequisites leave
`credential-injection/1` unavailable for that tuple. All destructive fault and
revoke cases use isolated fixtures or explicitly authorized test accounts;
qualification requirements never authorize damage to a live operator session.

### 10.6 Compatibility and security impact

This proposed section changes no released or closed schema, frozen readiness
row, default `per-home` behavior, source-policy selector, custody backend,
snapshot exclusion, diagnostic or execution capability. It adds no Keychain,
broker, refresh-token, Remote Control, archive relocation or cross-UID route.
Joint adoption and later route-specific qualification remain separate gates.

The intended security change is to qualify hosted final-owner delivery without
turning metadata/profile equality into authority or teaching a shared daemon to
read credentials. Reuse sections 2–9's exact protections and typed refusals;
do not claim account isolation from ordinary same-UID precautions. If the real
harness cannot contain delivery to the required sinks or an owning interface
cannot express these bindings, keep the tuple unavailable and return the exact
constraint to its owner instead of weakening the contract or hiding it in mocks.
