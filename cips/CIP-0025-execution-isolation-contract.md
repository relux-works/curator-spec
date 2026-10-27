# CIP-0025: Execution Isolation Contract

- **Status:** Review
- **Owner:** orchestrator; decisions: operator
- **Created:** 2026-10-24
- **Related:**
  [CIP-0024](CIP-0024-agent-stations.md);
  CIP-0026 — Foreign-code execution (in preparation);
  external-pool threat catalogue (companion reference)
- **Affects:** user-manager launcher, dispatcher, credential broker, session host,
  station composition/start gates, platform parity and qualification

## Summary

Define the common execution norm for trusted agent stations and separately admitted
external execution classes. EIC specifies objects, guarantees, ordering and evidence;
modules retain their operations, journals and wire formats. No first station may run
before every requirement of its narrow class is qualified. Boundary receipts and
credential issue/renewal checks activate together on any path claiming conformance.
A weaker guarantee remains weaker in placement decisions, receipts and replies.

## Motivation and user stories

- A scheduler compares a task's declared guarantees against actual qualified
  capabilities, rather than assuming that a UID, OS name or backend supplies them.
- A station starts only after its read, write, IPC, network and process boundaries
  cover its complete invocation, including hooks, plugins and descendant services.
- A credential consumer obtains or renews authority only for its current execution
  and independently checked applied boundary, including after asynchronous refresh.
- An operator sees which Linux and macOS properties are equal, compensated, absent
  or unverified, and can explicitly accept a qualified reduction for one task.
- Recovery keeps unknown work fenced while preserving authorised status and stop
  operations, bounded resources, input integrity and complete output custody.

## Current state

This is a requirements proposal, not deployment or privileged qualification evidence.
[Station scope][stations], [dispatcher][dispatcher], [broker][broker] and
[session-host][session-host] already assign their module responsibilities. The
[user-manager host model][linux-host] and [station account contract][accounts]
are inspected at a refreshed public main commit; their own activation gates remain.
Fixture passes in those modules do not qualify a complete EIC station.

The shared guarantee vocabulary and four admission statuses are published in
[station platform parity][parity] at
`71dd888e23350d736ea74589ea1f5b4692258a2d`. Sections §2 and §7 adopt its normative
definitions, station declaration and reviewed mapping; EIC-local requirements
remain explicitly separate and allocate no station identifiers. CIP-0026 (reserved)
remains a separate draft;
its provisional EIC objects are replaced by references only after joint review.

[Waggle record][waggle-record] and [verifier][waggle-verifier] are inspected at
public main `98c9cfd26cfc57a7ee82176cd599e92af03e69bb`. They supply signed-record
bytes and verification, not deployment, online state, effect serialization or a
new EIC receipt schema. No tests from those repositories are executed here.
The repository was renamed to `relux-works/swarma-envelope` on 2026-10-26;
the historical commit-pinned URLs below retain their original spelling.

## Design

### Options considered

1. UID separation as the complete station boundary: insufficient read, inherited
   descriptor, IPC, network, process-fate and resource evidence. Transitional only.
2. One mandatory container/orchestrator: unnecessary coupling and no proof of the
   actual composed boundary. Not selected.
3. A common norm with module-owned adapters and exact capability evidence: selected.
   This permits native platforms and separately qualified optional backends while
   preserving a common refusal, receipt, stop and qualification standard.

### Recommendation

Use a narrow measured native class first. Keep admission closed until its complete
production-entry checks are green. Publish shared objects and module carriers
before activating receipt-dependent credential release. Unsupported alternatives
remain explicit, rather than inheriting a stronger class's designation.

### §1 Scope, trust and guarantees

The common objects are an isolation profile, capability vector, identity/placement/
execution bindings, boundary receipt and qualification tuple. A guarantee describes
an enforced property within its stated TCB and exclusions; it is not a product name,
message-assurance rank or claim that unknown exploits cannot exist.

EIC owns the norm. Module-owned duties remain:

| Owner | Responsibility retained |
|---|---|
| User-manager privileged launcher | Apply the admitted boundary, write protected applied-state evidence and perform the qualified account stop |
| Dispatcher | Authenticate admission, compare capability coverage, bind execution/profile/node and coordinate effects/recovery |
| Credential broker | Independently check current boundary/generation/authority at issue and renewal under final release serialization |
| Session host | Input admission, single-writer/lifecycle fences, authenticated runner binding and retained input/output accounting |
| CIP-0024 station contract | Station account/generation, keys, mapping, protected controls/releases, start gate, station caches and host heavy-run budget |
| Keymaker and registrar | Custody, registration and native peer-UID duties remain module-owned; station caller paths depend on the separately published and qualified signing purpose (§8), without guest identity translation |
| Qualification authority | Independently review exact tuple evidence, restrictions, revocation and change invalidation |

The local TCB includes hardware/firmware, host kernel, enforcement backend, trusted
launcher, privileged interpreter/collector paths and their protected configuration.
Platform integrity also depends on external authority, time/revocation, protected
journals, credential custody and network enforcement outside the payload's control.
A guest kernel may be hostile where an outer boundary is explicitly qualified.

Signed receipts are host claims, not hardware attestation or proof of honest
execution, truthful computation or completed cleanup. Local root/firmware compromise
can defeat host claims. A pool's external containment and platform-secret absence
remain necessary even when receipt signatures verify.

Physical attacks, malicious manufacture and advanced hardware side-channel
elimination are excluded from the initial guarantee. Unknown exploits, deceptive
outputs, operator access and outages remain residual risks. Explicit placement
policies may reduce exposure; no weaker policy is presented as equal.

A UID-only transition MUST be labelled non-station and MUST NOT issue station
conformance evidence. A first station MUST require every check of its selected
narrow class, including shared service/carrier integration; partial green evidence
MUST NOT create a transitional station class. Qualification: EQ-01.

### §2 Isolation profiles and capability coverage

An isolation profile is immutable protected policy, not an agent-edited manifest.
A capability vector describes the exact applied/qualified scope of each property;
it is not a boolean claim that a machine is generally safe.

| Object member group | Required meaning; exact carrier belongs to its module |
|---|---|
| Profile identity | Version, class and immutable resolved-body digest, with protected selection provenance |
| Read/write roots | Positive read boundary, private writable roots, immutable input/control roots and link/mount semantics |
| Invocation | Exact executable/entrypoint/arguments, environment, descriptors and transitive interpreted configuration |
| IPC/process | Allowed service/socket/namespace interfaces, process containment and complete stop scope |
| Network/resource | Enforced route/source binding, DNS/destination policy, limits, measurement and reserved recovery capacity |
| Capability entry | Guarantee ID/version, enforcement mode, scope, restrictions, evidence/tuple reference and current status |
| Compensation | Missing property, actual substitute, response bound, residual risk and exact acceptance reference |

**EIC-2-01.** The dispatcher MUST select the profile through protected machine
policy intersected with class minimums and caller authority, and MUST pin its
immutable resolved digest. The launcher MUST refuse absent, changed or substituted
policy rather than accept a reference to a mutable body. Qualification: EQ-10.

**EIC-2-02.** Each capability MUST name enforcement mode, scope and exact
qualification evidence. The vector MUST distinguish applied enforcement from
observation and hard limits from soft compensation. The complete status vocabulary
is `present`, `weaker-with-compensation`, `absent` and `PENDING-VERIFY`, with the
meanings in [station parity §2](https://github.com/relux-works/swarma-user-manager/blob/71dd888e23350d736ea74589ea1f5b4692258a2d/spec/platform-parity.md#2-status-vocabulary-and-evidence).
Missing required proof MUST remain `PENDING-VERIFY` and unavailable; status cannot
be inferred from a platform label. The separate annotation **implemented, deployment
qualification pending** has no admission effect and creates no fifth status. Qualification: EQ-10, EQ-17.

**EIC-2-03.** Positive read boundary, inherited-descriptor control and IPC/service
access MUST be required capabilities, independently of UID separation. Qualification
MUST cover global paths, already-open handles, links/mounts and indirect service
access, not merely successful writes to the private home. Qualification: EQ-10, EQ-16, EQ-20.

**EIC-2-04.** A station task MUST use `station-required-guarantees/1` under
[station parity §3](https://github.com/relux-works/swarma-user-manager/blob/71dd888e23350d736ea74589ea1f5b4692258a2d/spec/platform-parity.md#3-task-declaration-and-scheduler-interface),
including its authenticated immutable envelope binding, validation, quantitative
scope and scheduler disclosure rules. That interface is incorporated by reference,
not redefined here. External classes MUST publish their own reviewed versioned
declarations for class-local requirements; they MUST NOT insert local identifiers
into the closed station declaration. Admission MUST compare every required
property and resource bound against the exact capability scope. Missing,
unsupported or unverified coverage MUST refuse with a typed reason and MUST NOT
select a weaker backend, broaden a root or drop a requirement silently.
Qualification: EQ-02, EQ-10.

**EIC-2-05.** A qualified `weaker-with-compensation` guarantee MUST require an
explicit independently authenticated operator act under [station parity §3][parity].
Acceptance MUST bind the immutable task/declaration revision, exact station and
generation, placement tuple, profile revision, **exact matrix revision**,
quantitative scope/bounds, missing property, compensation, residual risk and the
**validity interval of the operator act**. A task-supplied boolean or blanket
waiver MUST NOT supply this act. At **start, resume and restart**, a missing,
not-yet-valid or expired validity interval, changed matrix revision or any other changed/missing
binding MUST refuse the weaker placement until a fresh exactly bound, currently
valid act and complete qualification pass reevaluation. The interval check MUST
use current authority time; a receipt's lifetime MUST NOT stand in for the act's
validity interval. The boundary receipt is a separate object, not acceptance.

The scheduler MUST disclose the reduction to the requester and retain it in its
answer and boundary receipt. Changing any binding MUST invalidate acceptance;
acceptance MUST NOT relabel weaker as `present`, make unverified evidence
qualified, or admit an `absent` or `PENDING-VERIFY` requirement. Qualification:
EQ-11 (AcceptanceMatrixRevisionDenied, AcceptanceValidityDenied and paired valid
controls), EQ-17.

**EIC-2-06.** An `absent` guarantee MUST refuse the requirement; operator acceptance
cannot create an implementation. A separately authorized revised declaration that
omits a waivable requirement MUST be reevaluated as a new admission, never counted
as satisfying the original. `PENDING-VERIFY` cannot be waived. Owner policy MUST
only narrow platform/class authority and MUST NOT waive currentness, credential
class refusal, input fences or the minimum station boundary. Qualification: EQ-02, EQ-11.

**EIC-2-07.** Shared guarantee identifiers and their normative definitions MUST
come from [station parity §1](https://github.com/relux-works/swarma-user-manager/blob/71dd888e23350d736ea74589ea1f5b4692258a2d/spec/platform-parity.md#1-guarantee-identifiers),
pinned to `71dd888e23350d736ea74589ea1f5b4692258a2d`. Consumers MUST pin this
vocabulary and the reviewed §7 mapping, refuse unknown IDs or incompatible revisions,
and never reassign or broaden an identifier. EIC-local requirements noted in §7
remain additional mandatory clauses; they allocate no station identifier. A
class-local namespace requires its own reviewed declaration and cannot extend
`station-required-guarantees/1` implicitly. Qualification: EQ-10, EQ-17.

**EIC-2-08.** Invocation qualification MUST include fixed CLI, environment, startup
files, plugins, imports and descendant configuration. A readable script, inline
interpreter or wrapper bypass MUST NOT introduce candidate behavior into a
station's inert light-check path. Qualification: EQ-04, EQ-16, EQ-19.

### §3 Identity, placement and execution bindings

These are separate objects. An identity names a principal; a placement records
where a principal may run; an execution records one physical attempt. Account
names, UIDs, node names and guest labels are not interchangeable identifiers.

| Binding | Protected content |
|---|---|
| Identity | Stable principal, authority/class and authenticated declaration revision |
| Placement | Identity binding version, node/host incarnation, account and account generation |
| Execution | Placement binding version, unique attempt ID, profile digest and admission evidence |
| Lifecycle | Durable execution epoch, pending effects, ingress fences, reservations and absence evidence |

**EIC-3-01.** Each binding MUST be independently versioned and protected against
substitution and replay. Admission and every subsequent effect MUST resolve the
same identity, placement and execution versions; a reused account name or numeric
UID MUST NOT resurrect authority from an earlier generation. Qualification: EQ-12.

**EIC-3-02.** At most one live physical execution MUST exist per account generation.
An attempt with unknown liveness MUST continue occupying that slot. Replacement
MUST wait for qualified whole-account absence and fenced prior ingress; changing
an execution ID MUST NOT create permission for a second process tree.
Qualification: EQ-07, EQ-09, EQ-12.

**EIC-3-03.** A station placement MUST preserve [CIP-0024's station mapping and
station-only requirements][stations], including its account/generation, controls,
release/start gate, key custody, service enforcement, caches and host budget.
An EIC binding MUST NOT replace those checks or grant a station label before
both station and selected EIC class gates pass. Qualification: EQ-01, EQ-12.

**EIC-3-04.** A public-pool placement MUST use the separate mapping and authority
class specified by CIP-0026 (reserved), on separately
qualified dedicated secret-free machines. Pool identity MUST NOT become a station,
credential principal or host peer UID through a shared string or numeric value.
CIP-0026 remains a separate draft until its normative reference lands.
Qualification: EQ-12, EQ-19, EQ-20, EQ-23.

**EIC-3-05.** A guest UID MUST NOT authenticate as the host's peer UID. Host services
MUST derive peer authority only from their qualified host-side transport and
protected bindings. Keymaker custody, registrar registration and signer APIs remain
module-owned, including §8's station-caller purpose dependency; EIC MUST NOT
introduce an implicit guest registration or key-release route.
Qualification: EQ-12, EQ-20, EQ-23.

**EIC-3-06.** Restart, migration and restored state MUST retain or safely supersede
execution fences and accounting provenance before admitting effects. New identity,
placement or execution labels MUST NOT reset resource debt, make unknown absence
known or discard an unresolved effect. Qualification: EQ-09, EQ-12, EQ-26.

### §4 Admission and adapter operations

**EIC-4-01.** The dispatcher MUST admit only the intersection of authenticated
request authority, recorded class, platform minimums, owner policy, task guarantees
and current qualified capabilities. Owner policy MUST only narrow rights; no caller
label, model acknowledgement or backend name supplies authority. Qualification: EQ-02.

**EIC-4-02.** Services MUST use closed typed versioned plans binding canonical
arguments, profile/body digests, inputs and effects; they MUST NOT accept caller-
composed privileged host commands, arbitrary executors or an alternate root entry.
The adapter adds no general root daemon or mandatory orchestrator. Qualification: EQ-03.

| Operation | Required semantics; module owns exact grammar |
|---|---|
| probe | Inventory capabilities and restrictions; no qualification inferred |
| qualify | Exercise exact production entry with reviewed paired evidence |
| prepare | Pin plan/profile/inputs, reserve capacity and idempotently establish constrained preparation without controlled/workload code; return the original effect-bound durable handle and effective policy digest; reconcile lost replies without duplicate boundaries (EIC-4-09) |
| start | Recheck authority and tuple; apply full boundary before controlled code |
| observe | Bounded current evidence for the same execution; never create/resume |
| stop | Fence new ingress/start, stop the complete account scope and confirm absence |
| destroy | After absence and output custody, remove residue and confirm cleanup |
| reconcile | Resolve original effects/unknown observations without duplicate work |

**EIC-4-03.** The launcher MUST apply restrictions before the first agent-controlled
instruction, including initialization, hooks, plugins, imports and descendant
configuration. Startup/restart/backend exec MUST NOT bypass dispatcher authority or
session-host input fences. Qualification: EQ-04.

**EIC-4-04.** Narrowing MUST be applied and confirmed within its published bound;
if it cannot be confirmed, the execution MUST be stopped under the same bound.
Widening MUST require new admission and evidence; a live receipt cannot be edited
to represent policy that was never applied. A change that cannot be applied to the
running execution because an enforced restriction is immutable MUST require a new
physical execution after confirmed prior absence and fresh admission. Policy
changes MUST be recorded as linked effects; the original admitted input and its
receipt history MUST NOT be rewritten. Qualification: EQ-05.

**EIC-4-05.** The session host MUST own input admission and its ingress/single-writer
fences. It MUST close affected ingress before stop, round export or replacement;
unknown delivery/application MUST stay unknown until intact durable evidence
resolves it. Historical approvals MUST NOT replay after restart. Qualification: EQ-06.

**EIC-4-06.** Agent stopped MUST mean zero processes of the whole agent account over
the published quiet period. Cgroup-based containment MUST be used on the Linux
native path; until completeness is qualified, account-wide process enumeration
remains decisive. Leader exit, backend status or timeout MUST NOT prove absence.
A qualified empty containment observation is sufficient only if proven equivalent
to whole-account zero, including OS-spawned processes. Qualification: EQ-07.

**EIC-4-07.** Messaging MUST run outside every agent account, under one shared
protected messaging service account, with one separately bound daemon instance and
client per station identity. Per-identity service accounts are optional and require
a separately approved placement; they are not an EIC conformance prerequisite.
Each instance MUST preserve its own authenticated identity and ingress fences and
MUST NOT create an unfenced agent-process ingress path. Messaging-process survival
is neither agent liveness nor a failed agent-account stop predicate. Exact placement
is part of qualification. Qualification: EQ-08.

**EIC-4-08.** A stale stop MUST NOT signal a successor generation or later execution.
Partial scans, unkillable tasks and failed state reads MUST retain the original
pending effect, reservations and fences. Replay after recorded absence MUST return
evidence without signalling. Qualification: EQ-07, EQ-09.

**EIC-4-09.** `prepare` MUST idempotently establish the admitted filesystem,
process, resource and network preparation without executing agent-controlled or
workload code. It MUST return a durable handle bound to the original preparation
effect and the effective policy digest. A lost or partial reply MUST reconcile
that same effect and MUST NOT create a second prepared boundary. Agent-controlled
hooks and plugins are start-phase work and remain subject to full admission,
receipt and first-instruction ordering. Qualification: EQ-37.

### §5 Boundary receipts and recovery

A boundary receipt is the privileged launcher's claim about an applied boundary.
Its signature authenticates its writer, not the truth of a compromised host.
Qualification records authorize a tuple; receipts describe a particular execution;
observation and stop evidence describe later effects. None substitutes for another.

| Receipt binding | Required semantic content; owning modules define wire fields |
|---|---|
| Carrier | Version/type, authorized writer and integrity/signature verification context |
| Subject | Separate identity, placement/account generation and execution versions from §3 |
| Admission | Class, task/declaration revision, plan and immutable resolved profile digest |
| Platform | Node incarnation, boot identity, backend and complete qualification tuple/evidence |
| Applied state | Boundary application evidence, actual capabilities and accepted weaker properties |
| Validity | Publication epoch, bounded validity/currentness and policy/qualification/revocation epochs |
| Recovery | Durable operation reference, pending/unknown state and applicable fencing epoch |

**EIC-5-01.** The privileged launcher MUST write the receipt from confirmed applied
state in protected storage. A caller-supplied receipt or a launcher executable
digest alone MUST NOT establish that a boundary exists. The writer MUST be
outside the agent's write authority. Qualification: EQ-13.

**EIC-5-02.** The launcher MUST publish a complete validated receipt after applying
the boundary and before permitting agent-controlled instructions; the dispatcher
MUST bind that receipt to its exact admission and placement. Partial publication,
application failure or mismatched bindings MUST leave start and credential gates
closed, retaining durable pending effects for reconciliation. Qualification: EQ-04, EQ-14.

**EIC-5-03.** The credential broker MUST independently read and verify protected
current receipt state for issue and renewal, including after asynchronous refresh,
under its final release serialization. The final check MUST include the current
admission, execution, profile, qualification and revocation bindings. A caller's
cached validity assertion MUST NOT substitute for that check. Qualification: EQ-21, EQ-24.

**EIC-5-04.** Every authority-consuming reader MUST reject unknown versions,
unauthorized writers, expired validity, stale epochs, substituted subjects or
revoked tuples. A verified historical signature MUST NOT establish currentness.
Boot, profile, policy, qualification and placement changes MUST invalidate affected
receipts until the corresponding boundary is re-established and newly admitted.
Qualification: EQ-13, EQ-14, EQ-30, EQ-33.

**EIC-5-05.** Receipt publication, dispatcher admission binding and broker issue/
renewal gating MUST activate together on the first claiming path. A receipt-only
migration MUST NOT claim station conformance. The standalone credential refresher
MUST retain a separate nonconformant profile until this joint path is qualified.
Qualification: EQ-22.

**EIC-5-06.** Publication and invalidation MUST have a durable ordering against
start, ingress and credential release. Stop, revocation and loss of currentness
MUST close affected authority before further effects; an in-flight release MUST
recheck at its final serialization point. A stale snapshot MUST NOT reopen the
gate or overwrite a later invalidation. Qualification: EQ-06, EQ-14, EQ-21, EQ-24.

**EIC-5-07.** Recovery MUST distinguish absent, stopped, running and unknown state.
A missing receipt MUST NOT prove process absence, and a current receipt MUST NOT
prove start success. Unknown effects MUST preserve reservations and fences until
reconciliation obtains intact durable evidence for the original operation;
retries MUST NOT create a duplicate execution. Qualification: EQ-07, EQ-09.

**EIC-5-08.** Restoring state MUST NOT restore obsolete authority: freshness anchors
and fencing MUST survive or be re-established outside the restored failure domain
before effects resume. Broken shared state MUST refuse authority-consuming work;
observe, list, reconcile and authorized stop require their own intact prerequisites.
A pool report MUST NOT require exposing platform secrets to its execution account.
Qualification: EQ-09, EQ-23, EQ-34.

Signed boundary, qualification and revocation carriers SHOULD use a [waggle signed
record type][waggle-record] and its [verifier][waggle-verifier]. Exact types and
verification policy remain Q-EIC-02; EIC invents no envelope. Signature validation
alone does not supply the independent current-state reads required above.

### §6 Linux native

This section incorporates the existing native host model by reference, at the
pinned revision linked here. It does not restate its algorithms or create an
alternative qualification procedure.

| Normative native source | Incorporated scope |
|---|---|
| [Linux backend, Production qualification][linux-host] | Host qualification `initial → pin → boot`, issuer/unit identity, publication and deployment schema; loader/NSS closure and kernel boundary checks |
| [Managed accounts, §7][accounts] | Protected homes, approved controls/release and installation/start interlock |
| [Managed accounts, §11][accounts] | Activation/handoff gates and unresolved implementation prerequisites |
| [Helper, §4.7 and §7][helper] | Account stop semantics, execution fences and privileged launcher contract |

**EIC-6-01.** Linux native admission MUST satisfy the incorporated host model at
its pinned approved revision and the selected EIC profile. EIC receipts MUST NOT
replace native qualification, convert an initial record into boot authority or
weaken the native loader closure, protected-home or current-unit requirements.
Qualification: EQ-15, EQ-32.

**EIC-6-02.** Existing native activation gates MUST remain closed until their own
implementation and production qualification requirements pass. A fixture result,
installed helper or draft EIC document MUST NOT be treated as station activation.
The referenced revision explicitly leaves automatic update requalification and
running-work containment qualification pending. Qualification: EQ-01, EQ-15, EQ-33.

**EIC-6-03.** Any native revision or relevant deployment change MUST undergo §10
invalidation and requalification, including the native source's upgrade gates.
An EIC implementation MUST NOT silently reinterpret a native record as its own
carrier or turn an unreviewed package update into a qualified pin.
Qualification: EQ-15, EQ-30, EQ-33.

**EIC-6-04.** Linux execution/stop adapters MUST preserve the incorporated helper's
account-generation and execution fences while satisfying §4's whole-account zero
predicate. Native containment evidence MUST NOT suppress an unknown or incomplete
account inventory. Qualification: EQ-07, EQ-09, EQ-15.

No privileged qualification commands are part of producing this draft. Real host
qualification is a separately authorized deployment operation; all normative
references describe obligations, not evidence that this draft exercised them.

### §7 macOS native and parity

macOS is a full station platform with the same guarantee vocabulary and admission
rules as Linux. It is not an exception class. The [native macOS account draft][mac-accounts]
is a candidate mechanism source, not evidence that an EIC boundary is implemented
or qualified. The native draft is pinned to the same `71dd888` revision as
station parity; admission is guarantee-based, without a named-task allowlist.
Equal platform standing does not imply equal enforcement mechanisms.

**EIC-7-01.** A macOS profile MUST define a positive read boundary covering global
paths, user homes, temporary directories, link/mount resolution and already-open
handles. UID separation and write denial alone MUST NOT qualify read isolation.
Inherited descriptors MUST be reduced to the exact allowed set before controlled
code, including every descendant. Qualification: EQ-10, EQ-16, EQ-20.

**EIC-7-02.** Qualification MUST bind the exact CLI/build, executable, arguments,
environment and transitive startup/plugin/descendant configuration. Interpreter,
resolver, IPC and service-spawn paths MUST stay within the declared boundary;
launchd or another service MUST NOT provide an escape through a different process
identity or unsandboxed descendant. Qualification: EQ-04, EQ-16, EQ-20, EQ-32.

**EIC-7-03.** Xcode, simulators, Keychain, launchd, TCC and APFS quota access MUST be explicit
capabilities with bounded authority, resource costs and per-path tests. An OS grant,
interactive approval or successful tool invocation MUST NOT waive another required
guarantee or import an unrelated user's secrets. `platform.keychain` is an optional
native capability, not a key-service port. On macOS, `keys.station` and `matrix.login`
remain `absent`: only a separately qualified native key-service port and its login
dependency can change that. Keychain availability supplies neither. Likewise,
`platform.apfs-quota` alone MUST NOT establish the full `limit.disk` guarantee.
Qualification: EQ-16, EQ-17, EQ-23.

**EIC-7-04.** Every station guarantee MUST have a per-platform matrix cell naming
status, mechanism, scope, compensation where applicable and qualification tests.
Only `present`, `weaker-with-compensation`, `absent` and `PENDING-VERIFY`
are admission statuses, with the normative meanings in [station parity §2][parity].
Missing full-scope proof MUST remain `PENDING-VERIFY`, never positive coverage.
A matrix/receipt/scheduler answer MUST expose accepted reductions.
Qualification: EQ-10, EQ-11, EQ-17.

**EIC-7-05.** A task requiring a hard property MUST refuse a soft or `absent` cell.
Only a separately authorized revised, waivable requirement under §2 may be
reevaluated; acceptance cannot satisfy the original non-waivable hard bound.
The exact matrix revision, quantitative scope and current operator-act interval
required by EIC-2-05 MUST be rechecked at start, resume and restart; missing/expired
intervals or changed revisions MUST refuse weaker placement. Soft resource limits
MUST remain weaker compensation; unverified guarantees MUST remain unavailable.
An acceptance MUST NOT turn a missing minimum station boundary into conformance.
Qualification: EQ-02, EQ-11, EQ-17, EQ-25.

**EIC-7-06.** OS-spawned and detached work MUST be included in whole-account stop
qualification, even when outside a launcher process tree. The separate messaging
account MUST preserve ingress fences without being counted as an agent process.
Unknown coverage MUST prevent absence, reuse and successor execution.
Qualification: EQ-07, EQ-08, EQ-09, EQ-16.

The mapping below retires all sixteen `G-*` labels; they are migration labels,
not identifiers accepted by admission. The shared identifiers and definitions are
those of [station parity §§1–4][parity] at
`71dd888e23350d736ea74589ea1f5b4692258a2d`. Each listed identifier is a separate
obligation with its complete published definition; grouping does not merge or
narrow it. EIC-local remainders have **no shared identifier** and remain mandatory
under their cited clauses, outside the closed station declaration. Every old row
has at least one published identifier; this mapping does not claim that shared
identifiers cover its local remainder. The four partial mappings are G-read,
G-write-input, G-hard-resources and G-cache-data: their stronger EIC obligations
are explicit in the local-remainder column and MUST be qualified separately.

This EIC review inventory is not the normative platform parity matrix or an active
capability vector. Before activation, each independently requested guarantee MUST
map to its own cell in the separately maintained, versioned normative matrix.
CPU, memory, disk, process-count and I/O enforcement MUST have independent status
and evidence; Xcode, simulators, Keychain, launchd, TCC and APFS quota MUST have
separate capability rows under their published identifiers. Aggregate inventory
labels MUST NOT be used as admission guarantees. This preserves EIC-7-04's
per-guarantee rule and the existing published mapping; qualification: EQ-17.
No complete EIC tuple is qualified here. Each review-inventory cell applies its
status to every listed identifier unless it explicitly names an exception. Candidate
mechanisms/tests are unqualified requirements, including on Linux. Core fixture evidence in the station matrix
retains only its original scope. The known missing macOS key-service port is
`absent`; Linux's native Apple capabilities are `absent`, as in station parity.
An implementation annotation under §2 cannot promote any cell.

| Retired label (migration only) | Published identifiers | EIC-local remainder (no shared ID) | Linux: status; candidate mechanism; test | macOS: status; candidate mechanism; test |
|---|---|---|---|---|
| G-identity | `identity.generation`, `account.lifecycle` | Execution/placement bindings remain EIC-local (§3). | PENDING-VERIFY; receipt-owned native account lifecycle/generation plus EIC bindings; EQ-01, EQ-12 | PENDING-VERIFY; receipt-owned native account lifecycle/generation plus EIC bindings; EQ-01, EQ-12 |
| G-read | `isolation.read` | Positive read-root boundary, including otherwise OS-readable unrelated paths (§2, §7; EQ-10, EQ-16, ReadBoundary). | PENDING-VERIFY; exact qualified filesystem/read boundary; EQ-10 | PENDING-VERIFY; positive sandbox read rules including global paths; EQ-16 |
| G-write-input | `isolation.controls`, `isolation.shared-state` | Private writable-root restriction plus immutable admitted inputs and plan-bound authorization/provenance (§2, §9; EQ-15, EQ-28). | PENDING-VERIFY; protected homes/controls and immutable inputs; EQ-15, EQ-28 | PENDING-VERIFY; protected controls and exact sandbox write rules; EQ-16, EQ-28 |
| G-invocation | `execution.profile`, `loader.closure` | None. | PENDING-VERIFY; pinned CLI/configuration and loader closure; EQ-04, EQ-15 | PENDING-VERIFY; exact CLI/configuration and descendant policy; EQ-04, EQ-16 |
| G-descriptors | `execution.descriptors` | None. | PENDING-VERIFY; launcher descriptor closure/allowlist; EQ-20 | PENDING-VERIFY; launcher descriptor closure/allowlist; EQ-16, EQ-20 |
| G-ipc-services | `ipc.isolation` | None. | PENDING-VERIFY; namespace/socket and peer authority restrictions; EQ-20 | PENDING-VERIFY; sandbox IPC/service-spawn and peer restrictions; EQ-16, EQ-20 |
| G-stop | `process.stop`, `process.identity`, `inventory.uid` | None. | PENDING-VERIFY; stable native process identity, complete reuse/holder inventory and cgroup/whole-account stop; EQ-07, EQ-09 | PENDING-VERIFY; stable native process identity, complete reuse/holder inventory and whole-account stop including service-spawned work; EQ-07, EQ-09, EQ-16 |
| G-messaging | `messaging.placement` | One separately bound daemon and client per identity under a shared protected service account (§4); per-identity accounts optional. | PENDING-VERIFY; shared protected service account, per-identity daemon/client and input fences; EQ-06, EQ-08 | PENDING-VERIFY; shared protected service account, per-identity daemon/client and input fences; EQ-06, EQ-08 |
| G-network | `network.egress`, `network.range-deny` | Protected execution-source binding (§8). | PENDING-VERIFY; source-bound external enforcement and resolver policy; EQ-18 | PENDING-VERIFY; source-bound external enforcement and resolver policy; EQ-16, EQ-18 |
| G-credential | `credential.issuance` | Joint activation and module-owned receipt carriers (§5, §8). | PENDING-VERIFY; protected receipt plus final broker gate; EQ-21, EQ-22 | PENDING-VERIFY; protected receipt plus final broker gate; EQ-21, EQ-22 |
| G-keys-controls | `keys.station`, `isolation.controls`, `execution.profile`, `qualification.boot` | CIP-0024 composition/start gates retain their own contract. | PENDING-VERIFY; CIP-0024 custody/start gate, qualified invocation and protected release; EQ-01, EQ-04, EQ-15, EQ-23 | `keys.station`: absent; other listed identifiers: PENDING-VERIFY; CIP-0024 custody/start gate, qualified invocation and protected release; optional Keychain is separate; EQ-01, EQ-04, EQ-16, EQ-23 |
| G-hard-resources | `limit.processes`, `limit.memory`, `limit.cpu`, `limit.disk`, `limit.io` | Actually available protected recovery reserve under admitted load, output bounds and retained debt (§9; EQ-25). | PENDING-VERIFY; exact kernel-backed limits and recovery reserve; EQ-25 | PENDING-VERIFY; measured limits; soft limits only candidate compensation, no hard equality; EQ-17, EQ-25 |
| G-finite-budget | `budget.principal` | Standing stations have no imposed lifetime deadline (§9). | PENDING-VERIFY; principal-bound quotas and host budget gate; EQ-25, EQ-26 | PENDING-VERIFY; principal-bound quotas and host budget gate; EQ-25, EQ-26 |
| G-cache-data | `isolation.shared-state`, `isolation.read`, `isolation.temporary` | Safe materialization (EQ-28), authorized import and complete-content retention until authorized deletion (EQ-29; §9). | PENDING-VERIFY; private caches, immutable objects and safe import; EQ-27, EQ-28, EQ-29 | PENDING-VERIFY; private caches, immutable objects and safe import; EQ-27, EQ-28, EQ-29 |
| G-recovery-revocation | `effects.provenance`, `journal.durable`, `journal.restore`, `process.fate`, `qualification.boot`, `qualification.drift`, `qualification.revocation`, `update.authentic`, `update.requalified` | Cross-module execution/effect recovery and current receipt fences (§3–§5, §8, §10). | PENDING-VERIFY; original-effect provenance, authenticated updates, current-boot proof, durable fences/epochs and bounded disposition; EQ-09, EQ-14, EQ-15, EQ-33, EQ-34 | PENDING-VERIFY; original-effect provenance, authenticated updates, current-boot proof, durable fences/epochs and bounded disposition; EQ-09, EQ-14, EQ-16, EQ-33, EQ-34 |
| G-platform-tools | `platform.xcode`, `platform.simulator`, `platform.keychain`, `platform.launchd`, `platform.tcc`, `platform.apfs-quota` | Other native tools require their own reviewed capability, not an invented station ID. | absent; native Apple capabilities unsupported by Linux; EQ-10, EQ-32 | PENDING-VERIFY; scoped Xcode/simulator/Keychain/launchd/TCC and dedicated APFS quota paths; EQ-16, EQ-17, EQ-32 |

A future accepted cell records concrete mechanism/configuration, scope and exact
evidence. For `weaker-with-compensation`, it additionally records the lost hard
property, measured substitute, response bound and residual risk; a generic promise
to monitor is insufficient. Q-EIC-05 selects the first actual macOS tool/task cells.
No numeric limits, sandbox APIs or platform version support are invented here.
Qualification expands this inventory whenever a station/task adds a guarantee;
absence from the table supplies no implied capability.

### §8 Network and credentials

**EIC-8-01.** The network enforcer MUST derive source identity from protected
placement/generation/execution bindings, not caller text or request headers.
Every DNS answer, resolved address, redirect and protocol MUST remain within the
admitted policy across address families; resolver bypass and policy/proxy failure
MUST fail closed. Qualification: EQ-18.

**EIC-8-02.** Existing network classes MUST retain their limits: workplaces have
zero egress and trusted local agents only their approved provider path. The pool
MUST remain a distinct class with independently enforced containment; its network
needs MUST NOT widen a station or workplace. Qualification: EQ-18, EQ-19.

**EIC-8-03.** Private, metadata, loopback and platform destinations MUST remain denied
unless a separately published minimal service binding expressly permits the exact
service for the class. A general network declaration MUST NOT create such a
binding, platform-service route or inherited socket. Qualification: EQ-18, EQ-20.

**EIC-8-04.** The broker MUST independently obtain and verify current protected
boundary evidence at credential issue AND renewal. Under its final release lock it
MUST recheck execution, active generation, receipt/profile/tuple currentness,
revocation, authority and release fences, including after asynchronous refresh.
A caller-supplied receipt or launcher digest alone MUST NOT satisfy this gate.
Qualification: EQ-21.

**EIC-8-05.** Boundary receipt publication and the broker issue/renewal gate MUST
activate together on the first path claiming the guarantee. A standalone Codex
refresher MUST remain a separate profile and MUST NOT claim station conformance.
Missing current evidence MUST refuse release, not fall back to native credentials.
Qualification: EQ-21, EQ-22.

**EIC-8-06.** Verification payloads MUST NOT receive model-provider credentials.
Untrusted allocations MUST receive no subscription binding or lease; neither EIC
nor a valid receipt overrides that class refusal. Pool hosts MUST contain no
platform secrets or authority. Qualification: EQ-19, EQ-23.

**EIC-8-07.** Receipt/currentness checks MUST NOT introduce cross-service waits under
conflicting generation/state locks. Consumers MUST use immutable evidence and a
published serialization/recheck protocol; stale asynchronous completion MUST NOT
reopen a revoked release fence. Qualification: EQ-21, EQ-24.

**EIC-8-08.** EIC does not redefine Keymaker custody, registrar registration or
native peer identity. Station caller authority depends on a separately reviewed,
published and qualified Keymaker station-caller signing purpose and its versioned
dispatcher/broker adapters. Until that integration is qualified, every station
caller path that depends on this purpose MUST remain disabled, including
operator-enrolled bootstrap and recursive delegation. A station-readable caller
private key, the interim Git signing purpose or an arbitrary-bytes signing
interface MUST NOT substitute for it. This dependency does not transfer key
custody or signer API ownership to EIC and does not disable the separately protected
operator service root. Qualification: EQ-35.

**EIC-8-09.** Admission, adapters, receipt readers and network or credential
mediators MUST emit bounded structured diagnostics that exclude credential values,
authorization headers and private request bodies. Qualification and recovery
evidence MUST obey the same rule and use synthetic sensitive fixtures. The owning
module retains its journal format and access policy; evidence completeness MUST
NOT require copying secret-bearing payloads. A rejection diagnostic MUST NOT
become an alternate content or credential delivery channel. Qualification: EQ-36.

### §9 Resources and data

**EIC-9-01.** Each resource capability MUST state hard, soft or absent enforcement,
measurement scope and response bounds. Soft watcher/stop behavior MUST NOT be
reported as a hard ceiling; absent guarantees MUST refuse required workloads or
use the explicit qualified weaker-acceptance path. Qualification: EQ-17, EQ-25.

**EIC-9-02.** The first pilot MUST use a conservative measured envelope with small
concurrency and protected recovery reserve. Without production-entry measurements,
heavy-class admission MUST remain closed. The same host budget MUST cover station-
orchestrated off-host verification requests without authorizing local builds/tests.
Qualification: EQ-25, EQ-26.

**EIC-9-03.** CPU/memory/process/storage/I/O/output and service-retained debts MUST
have finite published budgets. New identities, runs or account generations MUST
NOT reset principal/aggregate accounting or discard retained obligations. Standing
stations MUST have finite quotas but no imposed lifetime deadline. Freezing or
parking an execution MUST NOT be accounted as memory release. Frozen processes and
retained state MUST remain charged to the same principal and aggregate budgets
until actual release is observed through a qualified termination or state-preservation
protocol. Qualification: EQ-26.

**EIC-9-04.** Mutually untrusted executions MUST NOT share writable caches, workspaces
or Git administration. Shared objects MUST be immutable, authorized, provenance-
checked and read-only; private writable state MUST follow the class cleanup policy.
Station cache policy remains owned by CIP-0024. Qualification: EQ-27.

**EIC-9-05.** Inputs MUST bind immutable base/manifests/resources to the admitted
plan and remain data outside platform-control discovery. Every outside interpreter
MUST have constrained roots, safe types/paths and streaming expansion/count/byte
limits; refusal MUST leave no partial publication or outside-root write.
Qualification: EQ-28.

**EIC-9-06.** Output intake MUST validate whole bounded objects without following
worker-controlled links, activating configuration or executing returned behavior.
Complete-content custody MUST precede deletion/retirement unless separately
waived by an authenticated per-act disposition. Missing blobs MUST retain the
obligation; a digest receipt alone is insufficient. Qualification: EQ-28, EQ-29.

**EIC-9-07.** Compilation, builds, tests and any worker-produced code execution MUST
remain in the existing isolated off-host verification class, never the station's
light-check or heavy-budget path. Pool runtime dependencies MUST be included in
result provenance under CIP-0026 (reserved). Qualification: EQ-19, EQ-29.

### §10 Qualification, updates and revocation

**EIC-10-01.** Qualification MUST bind exact OS/kernel, architecture, hardware/firmware
class, backend/version/composed layers, profile and image digests, harness/launcher/
collector, UID scheme, node configuration and network/service policies. An unrelated
feature test or host observation MUST NOT qualify the execution boundary.
Qualification: EQ-30.

**EIC-10-02.** Every independently enforced gate MUST have a named negative case and
nearby valid positive control. A bounded independently weakened-gate control MUST
fail the intended case, not crash or fail setup. Tests MUST check rejection effects,
not merely an error string. Qualification: EQ-31.

**EIC-10-03.** Qualification MUST use the exact production service entry, identity,
groups, descriptors, sandbox, mounts, environment, CLI, descendants and resource
properties. An interactive-shell pass MUST NOT substitute for hardened-unit evidence.
Unavailable target or truncated logs MUST remain unverified. Qualification: EQ-32.

**EIC-10-04.** Material tuple changes MUST invalidate affected evidence and close new
admission until reviewed requalification. Updates MUST be approved/pinned and MUST
NOT roll back to a revoked tuple; package maintenance MUST preserve the native
host model's own gates rather than repin arbitrary drift. Qualification: EQ-30, EQ-33.

**EIC-10-05.** On detection of a security revocation affecting an execution tuple,
new starts and credential release for that tuple MUST be fenced immediately.
For the Linux and macOS station baseline, confirmed whole-account stop, including
the required quiet period, or confirmed qualified narrowing to a non-revoked class
MUST complete no later than 300 seconds after detection. Profiles MAY specify a
shorter bound, never a longer one or a later trigger. Retries, observer restarts,
delayed publication and recovery MUST NOT reset that deadline. Unconfirmed
narrowing MUST fall back to stop within the same deadline; a missed deadline fails
qualification even when fences remain intact. Unknown evidence MUST retain fences.
Other execution classes publish their own approved bounds without weakening this
baseline. Qualification: EQ-05, EQ-34.

**EIC-10-06.** Status, list, observe, reconcile and authorised stop MUST remain
available under their state-integrity prerequisites during holds/revocation.
Broken shared state MUST NOT open an alternate authority, launch, release or
recovery bypass. Receipt and broker recovery MUST agree on the current execution
before release resumes. Qualification: EQ-09, EQ-24, EQ-34.

### §11 Optional backends and rollout

**EIC-11-01.** The maintained support matrix MUST separately record `supported`,
`restricted` or `unsupported` for each exact OS/backend/profile tuple, with reasons,
tested scope and evidence references. Capability coverage, enforcement mode, and
implementation, qualification and activation state MUST remain distinct axes.
Restricted support MUST NOT satisfy an unmet mandatory guarantee. This tuple-level
record complements, and MUST NOT replace, the per-guarantee platform parity matrix.
A `supported` record alone supplies no qualification or activation authority;
`restricted` permits only its explicitly qualified scope, and `unsupported` tuples
MUST refuse admission. Qualification: EQ-38.

Optional gVisor, microVMs, VM pools and other backend compositions MUST qualify as
distinct tuples. A VM guest is never a host kernel peer UID; a forwarding bridge
cannot borrow its host identity. No product is mandatory or selected as winner.
External-code pool admission is a separate step on dedicated secret-free machines,
not an extra permission on a station host.

The rollout order is station rules → EIC and versioned carriers → qualify one
narrow native tuple → activate only that tuple → separately qualify/activate the
pool and other backends. Unresolved required policy choices MUST refuse activation.
No optional backend, receipt type or compensation becomes supported by appearing
in this document. No UID-only path is advertised as a station.

Signed boundary, qualification and revocation carriers SHOULD be expressed as
reviewed waggle signed record types using its record/verifier architecture. Their
exact types, domains, schemas and consumers remain a joint publication question;
EIC invents no new envelope or crypto. Existing types MUST NOT be overloaded to
claim an undefined EIC receipt. Signature validity does not establish currentness.

## Security considerations

Services enforce trust decisions; editable instructions do not. Local privilege,
IPC, descriptors, network and data interpretation are separate surfaces, each with
capability/evidence requirements. Account identity does not establish a positive
read boundary or provenance of interpreted configuration.

The external-pool threat catalogue is a companion reference and does not define
station conformance. Any normative use of its identifiers MUST cite a published
immutable revision and a reviewed mapping; no normative catalogue-ID dependency
is established by this draft. Station-only keys, context and platform-host exposure
remain governed by CIP-0024 and the module contracts. Shared requirements cover
containment, credential release, replay/restore, bounded resources, stale identity,
output injection and dishonest host evidence. Negative qualification is not proof of the
absence of every hardware or kernel defect.

An operator's qualified weaker acceptance is a deliberate reduction with visible
residual risk, never exemption from authority, currentness, input fences or minimum
class boundaries. Physical isolation and external containment remain necessary
when the adversary can compromise a pool host.

## Compatibility and migration

Key custody, registrar registration, signer APIs and native peer identity remain
owned by their modules. Station caller activation additionally depends on the
separately reviewed, published and qualified Keymaker station-caller signing
purpose and versioned dispatcher/broker adapters required by EIC-8-08. Until that
integration is qualified, every dependent station caller path MUST stay disabled,
including bootstrap and recursive delegation; migration MUST NOT retain a readable
caller key, interim Git signing purpose or arbitrary-bytes signing fallback.
The separately protected operator service root retains its own authority.
Station-only account/key/composition/release rules remain in CIP-0024. Existing
workplace/agent-host restrictions and the standalone refresher profile retain
their distinct activation and credential scope.

Modules retain their closed wire formats, service operations and journals. New
receipts and bindings require reviewed versions and normative EIC references;
no extra members, protocol fallback or synthetic authority is inferred here.
A partial migration keeps the claiming path disabled. Retained unknown executions
and output obligations survive migration; old evidence cannot be silently upgraded.

## Specification changes

1. Publish this CIP before CIP-0026 (reserved); replace
   that class's provisional objects only through a reviewed reference mapping.
2. Add normative references from CIP-0024 and user-manager, dispatcher, broker
   and session-host contracts, preserving the ownership table.
3. Publish versioned applied-boundary receipts, readers, invalidation and the
   combined issue/renewal activation gate; prefer waggle record types. Separately
   review, publish and qualify the Keymaker station-caller signing purpose and its
   dispatcher/broker adapters before enabling any dependent station caller path.
4. Maintain the §7 mapping to the pinned [station parity vocabulary][parity],
   including mechanism, evidence, restriction and compensation semantics per
   platform cell; local remainders retain their cited EIC clauses.
5. Qualify production entry and recovery, then activate exactly the accepted class.

## Implementation plan

| Order | Leaf | Exit evidence |
|---|---|---|
| 1 | Station ownership, composition, process/messaging placement | Reviewed CIP-0024 mappings and full class preconditions |
| 2 | EIC objects, module-owned carriers and station-caller signing purpose | Reviewed schemas/ordering/currentness and vocabulary mapping; separately reviewed, published and qualified Keymaker purpose and versioned dispatcher/broker adapters; dependent caller paths disabled until qualified |
| 3 | Launcher/dispatcher/broker/session-host integration | Applied-state publication, issue/renewal serialization, bounded secret-free diagnostics and recovery tests; EQ-35 rejects missing purpose and readable-key fallback, then permits the published purpose for the active generation |
| 4 | Native narrow tuple and measured budgets | Production-entry negative/positive evidence and mandatory reserve |
| 5 | Explicit one-class activation | Independent acceptance of exact head, configuration and tuple |
| 6 | macOS parity and separately scoped optional/external classes | Per-cell evidence and class-specific qualification; no inferred equivalence |

These are specification/implementation dependencies, not deployment authorization.
No qualification workload, service modification or host installation runs here.

## Test plan

EQ cases are future executable qualification requirements, not executed evidence.
For §§2–11 each numbered normative clause names applicable EQ cases; those links
are coverage obligations, not claims that a keyword checker proves semantics.
No hardware/host-honesty theorem is claimed testable: physical attacks and arbitrary
future exploit absence are excluded, not passed by a finite suite.

Every case uses isolated fixtures and synthetic data under the production service
properties. It checks the negative first and the adjacent positive under the same
relevant policy. Independent gate weakening requires a named intended witness;
unapplied plants, setup failures, crashes and timeouts are not killed controls.

| Case | Negative case and required post-failure state | Positive control |
|---|---|---|
| EQ-01 | Incomplete class or UID-only path cannot start/claim a station | Fully green exact narrow class admits only its recorded scope |
| EQ-02 | Caller class/owner policy cannot widen authority or select unavailable guarantees | Recorded task/policy/capability intersection admits compatible work |
| EQ-03 | Unknown plan fields, version or caller host command refuses before effect | Canonical closed admitted plan reaches its fixed executor |
| EQ-04 | Hooks, plugins, readable scripts or backend exec cannot run before boundary/fences | Approved entrypoint and qualified inert light check run after application |
| EQ-05 | DW-06/DW-28: missing confirmed narrowing/whole-account stop by the original bound fails even if fenced/unknown; widening without new admission refuses; ImmutableRestrictionRestartDenied rejects in-place immutable change or replacement before prior absence/fresh admission; PolicyHistoryRewriteDenied rejects rewritten input/receipts | Mutable narrowing confirms by the bound or whole-account stop including quiet period completes in time; immutable change creates a new physical execution only after confirmed absence and fresh admission, with linked effects and intact original input/receipts |
| EQ-06 | Restart/retry cannot replay unknown input or historical approval or bypass a closed fence | Intact exact delivery evidence permits only authorised continuation |
| EQ-07 | Escaped/double-fork/OS-spawned children, stale stop or incomplete scan cannot produce absence/reuse | Account-wide quiet-period zero records absence; replay does not signal |
| EQ-08 | MessagingAgentUidDenied and MessagingIdentityFenceDenied reject a daemon under any agent UID, reopened ingress or borrowed identity; no forbidden delivery or spawned agent work | MessagingSharedAccountAllowed: two separately bound daemon/client pairs under one protected shared service account retain their identities and fences; one agent account stops while its ingress stays closed, the other pair delivers only its own authorized traffic |
| EQ-09 | Unknown start/stop/restore cannot release claims, duplicate execution or bypass state integrity | Original effect reconciles from intact evidence without signalling a successor |
| EQ-10 | Caller-modified profile or unsupported capability refuses without fallback; on an admitted Linux or macOS tuple, forbidden global, other-account and link/alias reads deny access and disclose no unauthorized bytes (ReadBoundary) | Exact protected profile admits; actual reads return the exact allowed bytes, including through allowed aliases |
| EQ-11 | AcceptanceMatrixRevisionDenied and AcceptanceValidityDenied refuse missing/changed matrix binding or missing/not-current operator interval at start, resume and restart; stale/wrong acceptance, lower compensation or changed task cannot admit work or report equality | AcceptanceMatrixRevisionCurrent and AcceptanceValidityCurrent actually permit the same qualified reduced task/bounds at each transition with exact current matrix/interval bindings and visible weaker status |
| EQ-12 | Identity/placement/execution substitution or second live generation execution refuses | Correct separate bindings permit sequential work after confirmed absence |
| EQ-13 | Job/caller receipt or executable digest without applied state cannot authorize release | Protected launcher applied-state receipt verifies for the exact admission |
| EQ-14 | Stale boot/profile/qualification/revocation evidence or partial publication cannot become current | Complete current receipt published before controlled code supports its scoped claim |
| EQ-15 | Native Linux host-model gate/closure/home violation refuses through production reader | Exact pinned native model and EIC additions pass without relaxing native prerequisites |
| EQ-16 | macOS ReadBoundary and descendant config, resolver/IPC/service-spawn probes deny actual out-of-boundary access, disclosure and effects | Approved exact CLI and its qualified descendants actually read allowed bytes and perform only declared operations |
| EQ-17 | Hard-limit task cannot land on a soft/absent cell; unqualified platform specifics cannot widen scope; AggregateInventoryDenied rejects a grouped label or one sibling cell as evidence for a missing independently required cell | Explicit qualified soft compensation or a `present` property appears honestly; each requested resource/tool guarantee has its own exact normative cell and independent evidence |
| EQ-18 | DNS/redirect/address-family bypass, forged source or proxy failure cannot leave policy | Bound placement reaches only admitted provider/dependency destinations |
| EQ-19 | Verification code/model credentials or pool permission cannot activate on station/workplace hosts | Secret-free off-host verification runs through its own admitted class |
| EQ-20 | Actual inherited descriptor set is restricted; host socket/guest peer cannot impersonate native peer; same-peer/same-endpoint forbidden service purpose returns no unauthorized bytes and causes no unauthorized effect (ServicePurpose) | Exact allowed descriptor set is usable; the same authenticated peer and endpoint actually return allowed bytes or perform the permitted service effect |
| EQ-21 | Issue/renewal and async-refresh races with stale receipt/generation/revocation release no credential | Independent current check under final release serialization releases exact permitted lease |
| EQ-22 | Receipt-only migration or standalone refresher cannot claim station conformance | Jointly activated launcher/dispatcher/broker path verifies both issue and renewal |
| EQ-23 | Untrusted bind/lease/injected platform secret refuses with no release | Trusted eligible class obtains only its admitted scoped credential; pool stays secret-free |
| EQ-24 | Lock-cycle/stale completion or broken shared state cannot reopen authority/release | Immutable evidence plus serialized final recheck preserves recovery without cross-service lock waits |
| EQ-25 | Soft/absent or unmeasured heavy envelope cannot masquerade as enforced hard capacity | Measured bounded work retains reserve and reports exact enforcement mode |
| EQ-26 | Identity churn/standing lifetime cannot reset quota or consume reserve; FrozenChargeDenied observes no memory-credit release from freezing/parking or unconfirmed release | Sequential identities share principal debt; standing work continues within quota; frozen retained state stays charged and credit returns only after observed qualified actual release |
| EQ-27 | Cross-execution writable cache/Git metadata access and poisoned shared object refuses | Private writable cache and authorized immutable digest object work |
| EQ-28 | Authorized digest-matching unsafe paths/types/expansion cannot publish or trigger discovery | Benign bounded input/output materializes wholly; opaque transfer avoids host interpretation |
| EQ-29 | Missing blob/dependency provenance, premature deletion or local candidate execution refuses | Complete-content custody and inert import succeed; code runs only off-host |
| EQ-30 | Change any independently enforced tuple component or borrow feature evidence: admission closes | Current unchanged exact tuple retains only its tested capability scope |
| EQ-31 | Independently weaken each gate: named negative witness must fail for that property | Restored gate rejects known violation and admits neighbouring valid case |
| EQ-32 | Shell-only, wrong unit/groups/CLI/sandbox or truncated evidence cannot qualify | Exact production service evidence and complete logs qualify only their matched tuple |
| EQ-33 | Unapproved update/arbitrary drift or rollback to revoked tuple refuses activation | Reviewed requalification follows native update gates and new exact evidence |
| EQ-34 | DW-27/DW-28: start/release after detection or missing confirmed whole-account stop (including quiet period)/qualified non-revoked narrowing by detection + B fails; on both station platforms B <= 300 seconds; longer/later-trigger profiles and clock resets refuse; intact fences cannot mask failure | Immediate fencing at detection plus actual confirmed disposition by detection + B, including failed narrowing followed by stop; both Linux and macOS exercise the exact 300-second boundary and a shorter profile; authorized recovery calls complete (DW-29) |
| EQ-35 | StationCallerPurposeDenied disables every dependent path (including bootstrap/delegation) without a published qualified purpose/adapters; StationCallerFallbackDenied rejects readable keys, Git-signing or arbitrary-bytes substitutes; stale-generation authority produces no caller signing or onward effect | StationCallerPurposeAllowed actually obtains only the published purpose's permitted caller signature through qualified versioned adapters for the active station generation; protected operator service root remains independently usable |
| EQ-36 | SensitiveDiagnosticDenied: synthetic credential values, authorization headers and private bodies never appear in diagnostics, qualification/recovery evidence or refusal output; oversized inputs cannot exceed published diagnostic bounds or become a content channel | BoundedDiagnosticAllowed actually emits structured bounded refusal/resource evidence with permitted non-sensitive fields and no sensitive values, retaining sufficient journal/effect references for recovery |
| EQ-37 | PrepareCodeDenied observes zero agent/workload instructions during prepare; PrepareDuplicateDenied rejects substituted handles/digests and observes no second boundary/effect after duplicate calls or lost/partial replies | PrepareReplayAllowed returns/reconciles the same durable original-effect handle and effective policy digest after retry/restart; one prepared boundary exists and controlled code starts only after full admission/receipt ordering |
| EQ-38 | TupleSupportDenied rejects unsupported tuples or restricted scope missing a mandatory guarantee; a supported label cannot bypass pending qualification, absent parity or closed activation | TupleSupportAllowed exercises a supported exact qualified tuple and a restricted tuple wholly within its qualified scope; support records remain separate from per-guarantee status and activation evidence |

### Qualification properties and observables

Each PO row audits its corresponding EQ case by the property being guaranteed,
its direct observation, a real permitted outcome and an independent narrowing
control. All listed facets are required subcases, not alternatives to select from.
A negative verdict requires the specified denial and absence of forbidden effects;
an error alone cannot pass. A positive actually exercises its permitted operation.
Admission is the direct observable of an admission rule, but cannot establish a
runtime read, service, network, process, credential or data property. Profile shape,
peer identity, an unchanged write canary and a success/status label cannot replace
those observations. The TO inventory below independently supplies completion and
ordering oracles; neither inventory substitutes for the other.

ReadBoundary expands to named ReadGlobalDenied, ReadOtherAccountDenied and
ReadAliasDenied subcases on **each** Linux and macOS tuple claiming `isolation.read`,
including macOS's exact CLI and qualified descendants in EQ-16. Fixtures contain
synthetic distinct content in unrelated global paths, other accounts' OS-readable
files outside the approved roots, temporary paths and link, alias and mount routes
to forbidden targets. Each attempt observes actual access denial and zero
unauthorized content in responses, logs, artifacts and other execution-visible
channels, even when all host files remain unchanged. Qualified already-open handle
paths are exercised with EQ-20's descriptor controls. ReadAllowed actually obtains
the exact permitted fixture bytes through declared direct and alias paths; file
existence, readable mode or successful admission alone is insufficient.
ReadEnforcementOnlyRemoved preserves admission, protected profiles, capability
checks, write restrictions and all allowed-read positives, while removing only the
read restriction. It must fail the named forbidden-read subcases on each platform.
No `present` read cell can inherit another platform's result or a home-only test.

ServicePurpose expands to ServicePurposeDeniedSamePeer on every claimed service
binding and qualified platform path: retain the same valid authenticated peer,
placement and declared endpoint, and request a purpose/operation outside that
binding. Require explicit denial, zero unauthorized returned content and zero
unauthorized state change, spawned work or onward request. Observe the actual
service effect and returned bytes, not merely the socket set or peer check.
ServicePurposeAllowed uses that same peer and endpoint and actually obtains the
allowed content or effect. ServiceScopeOnlyRemoved removes only purpose scope,
retaining peer authentication, endpoint, descriptor and transport restrictions;
ServicePurposeDeniedSamePeer must fail while ServicePurposeAllowed remains green.
These controls use isolated synthetic fixtures, never live users' data/services.

| Audit / case | Guaranteed property | Direct negative observation | Actual positive observation | Independent narrowing / intended witness |
|---|---|---|---|---|
| PO-01 / EQ-01 | Qualified class and station claim | Incomplete/UID-only class produces no start or station claim | Fully qualified exact class starts only its recorded scope | Skip one class gate; unqualified start/claim fails ClassStartDenied |
| PO-02 / EQ-02 | Authority intersection | Widened request has no admission or downstream effect | Compatible intersection is admitted and executes within its scope | Ignore owner/task restriction; widened admission fails IntersectionDenied |
| PO-03 / EQ-03 | Closed plan and fixed executor | Unknown field/version/host command produces no executor effect | Canonical admitted plan invokes the fixed executor | Accept extra command authority; executor trace fails ClosedPlanDenied |
| PO-04 / EQ-04 | Boundary before controlled instructions | Instruction/effect trace is empty until all restrictions and fences apply | Approved entrypoint and inert check actually run after application | Permit early hook only; first-instruction trace fails EarlyInstructionDenied |
| PO-05 / EQ-05 | Confirmed disposition; immutable changes create a fresh execution with linked history | Missing completion by original bound fails; immutable in-place change/early replacement or rewritten input/receipts is denied without forbidden effects; widening without admission refuses | Mutable narrowing or stop completes in time; immutable change runs a new physical attempt only after absence and fresh admission with preserved linked history | Drop completion: DW-06/DW-28 fail; omit immutable replacement/admission gate: ImmutableRestrictionRestartDenied fails; overwrite original history: PolicyHistoryRewriteDenied fails |
| PO-06 / EQ-06 | Input fences and no historical replay | Restart/retry applies no unknown/historical input and no fenced effect | Exact authorized continuation actually applies once | Replay historical approval; application trace fails InputReplayDenied |
| PO-07 / EQ-07 | Whole-account absence and stale-stop safety | Surviving escaped/OS-spawned process prevents absence/reuse; stale stop sends no successor signal | Whole-account zero persists for quiet period; replay returns evidence without signal | Count leader only or signal successor; AccountAbsenceDenied fails |
| PO-08 / EQ-08 | Shared protected messaging placement and per-identity fences | MessagingAgentUidDenied observes rejection under an agent UID; MessagingIdentityFenceDenied observes no borrowed identity, fenced delivery or spawned work | MessagingSharedAccountAllowed actually runs two daemon/client pairs under one protected shared account; one stopped agent stays fenced while the other receives only its own authorized traffic | Place daemon under agent UID: MessagingAgentUidDenied fails; remove one identity or ingress binding: MessagingIdentityFenceDenied fails, including DaemonIngressDenied |
| PO-09 / EQ-09 | Unknown-effect recovery without duplicate work | Pending claim/reservation/fence retained; no duplicate execution or successor signal | Original effect actually reconciles under intact evidence, per TO-15/16/29 | Forget pending unknown effect; live-attempt/effect count fails UnknownReplayDenied |
| PO-10 / EQ-10 | Protected capabilities and runtime read boundary | Modified/unsupported profile refuses; ReadBoundary denies actual reads with zero unauthorized content on Linux and macOS | Protected admission plus ReadAllowed returning exact permitted bytes | ReadEnforcementOnlyRemoved fails ReadGlobalDenied, ReadOtherAccountDenied and ReadAliasDenied per platform |
| PO-11 / EQ-11 | Exact current matrix/interval acceptance and honest disclosure | Stale/wrong matrix or missing/not-current act interval produces typed refusal and no start/resume/restart effect or equality claim; EQ-11 subcases below are mandatory | Exact current matrix and valid operator interval permit each transition; accepted reduction is visible in matrix, receipt and scheduler answer | Substitute older acceptance or equality label: WeakerDisclosureDenied fails; WeakerMatrixBindingOnlyRemoved and WeakerActExpiryOnlyRemoved fail their EQ-11 witnesses below |
| PO-12 / EQ-12 | Separate binding versions and one live attempt | Substituted/stale generation has no authorized effect; actual live-attempt count never exceeds one | Correct bindings execute sequentially after confirmed absence | Ignore one binding version or unknown liveness; BindingSubstitutionDenied fails |
| PO-13 / EQ-13 | Protected receipt from applied state | Caller/digest-only/unapplied receipt authorizes no start/release; agent cannot alter writer state | Launcher confirms boundary, publishes protected receipt and exact reader accepts | Treat executable digest as application; AppliedReceiptDenied fails |
| PO-14 / EQ-14 | Complete current receipt and publication order | Stale/partial receipt never becomes current or enables controlled code/release | Complete validated receipt is durably current before actual dependent effect | Publish partial/stale receipt as current; ReceiptPublicationDenied fails |
| PO-15 / EQ-15 | Incorporated native host model plus EIC | Native production reader rejects each violated native gate, closure/home or containment predicate | Exact pinned native qualification and EIC controls pass without relaxed prerequisites | Independently remove incorporated gate; its native named witness fails; EQ-10 separately tests global reads |
| PO-16 / EQ-16 | macOS boundary through CLI and descendants | ReadBoundary discloses no unauthorized bytes; config/resolver/IPC/service-spawn routes cause no forbidden access/effect | Exact CLI and qualified descendants actually read allowed bytes and perform permitted operations | ReadEnforcementOnlyRemoved fails macOS ReadGlobalDenied/ReadOtherAccountDenied/ReadAliasDenied; remove each other path restriction and its escape witness fails |
| PO-17 / EQ-17 | Truthful independent per-guarantee cells and enforcement mode | Required hard/unqualified property yields no admission; grouped inventory labels or qualified siblings cannot fill a missing cell | Each exact required resource/tool cell independently qualifies; permitted scoped compensation is exercised and disclosed | Relabel soft/absent as hard: HardCapabilityDenied fails on actual enforcement; collapse sibling cells: AggregateInventoryDenied fails with one required sibling pending and the others valid |
| PO-18 / EQ-18 | Enforced destination policy and trusted source | Synthetic denied destinations receive no connection/request across DNS, redirects, families, forged source and proxy failure | Bound execution actually reaches only permitted synthetic destinations | Remove one route/source check; observed denied-destination traffic fails NetworkPolicyDenied |
| PO-19 / EQ-19 | Off-host verification and credential separation | Candidate code never executes on station/workplace; no model credential reaches payload | Secret-free payload actually runs only through admitted off-host class | Allow local activation or model secret; execution/credential observation fails VerificationPlacementDenied |
| PO-20 / EQ-20 | Exact descriptors, peer authority and minimal service purpose | Inspect actual descriptor set and usability; reject impersonation; ServicePurposeDeniedSamePeer observes no unauthorized content/effect | Allowed descriptors work; ServicePurposeAllowed returns allowed content or performs permitted effect | Remove descriptor closure/peer check: native descriptor/peer witness fails; ServiceScopeOnlyRemoved fails ServicePurposeDeniedSamePeer |
| PO-21 / EQ-21 | Current credential issue and renewal | Stale/racing issue, renewal and async refresh produce zero credential releases | Final serialized independent current check actually releases exact permitted lease | Skip final currentness recheck on refresh; release trace fails CredentialReleaseDenied |
| PO-22 / EQ-22 | Joint receipt/dispatcher/broker activation | Partial activation or standalone refresher gets no conformance claim and no claiming-path release | Joint path actually binds applied receipt and checks issue plus renewal | Activate receipt-only path; conformance/release observation fails JointActivationDenied |
| PO-23 / EQ-23 | Class credential refusal and secret-free pool | Untrusted class gets no binding, lease or platform secret; pool inventory/execution observations expose no platform secret | Eligible trusted class actually receives only its scoped credential | Treat valid receipt as class override; actual release/read fails ClassCredentialDenied |
| PO-24 / EQ-24 | Serialized recovery and no stale authority | Stale async completion/broken state causes no release or reopened fence; no cross-service lock wait cycle | Healthy authorized recovery and final recheck actually complete, per TO-18/29 | Let stale completion reopen release or add conflicting wait; ReleaseRecoveryDenied/DW-18 fail |
| PO-25 / EQ-25 | Measured capacity, honest limit and usable reserve | Unmeasured heavy class refuses; overstated hard limit or unavailable recovery capacity fails | Actual bounded workload and recovery execute within measured envelope/reserve | Count nominal unavailable reserve or soft as hard; RecoveryReserveDenied/DW-20 fail |
| PO-26 / EQ-26 | Persistent finite quotas and frozen charges without lifetime deadline | Churn/freeze/parking cannot lower principal/aggregate debt or admit work beyond budget; unconfirmed release returns no credit | Standing work continues within quota; freeze retains measured memory/state charge, then qualified actual release returns only observed released credit | Reset debt on identity: DebtResetDenied fails; credit memory solely on freeze/parking: FrozenChargeDenied fails |
| PO-27 / EQ-27 | Private mutable state and immutable authorized sharing | Cross-execution cache/Git read or write and poisoned object access deny; zero unauthorized content/change | Private writable cache operates; authorized digest object actually reads, remains immutable | Remove read isolation only or provenance check; observed access fails CacheAccessDenied |
| PO-28 / EQ-28 | Safe bounded whole-object interpretation | Even authorized digest-matching unsafe paths/types/expansion cause no partial publication, outside-root write or control discovery | Whole benign bounded object materializes; opaque transfer causes no interpretation | Skip one path/type/streaming bound; materialization trace fails UnsafeObjectDenied |
| PO-29 / EQ-29 | Complete custody, provenance and inert import | Missing blob/dependency retains obligation; no premature deletion or local candidate execution | Actual complete bytes are retrievable before retirement; inert import succeeds and execution occurs off-host | Accept digest without bytes or activate import; custody/execution trace fails ContentCustodyDenied |
| PO-30 / EQ-30 | Exact tuple qualification and invalidation | Each independent tuple change/borrowed feature record closes affected admission | Unchanged exact tuple actually admits only tested scope | Ignore one tuple component; affected admission fails TupleChangeDenied |
| PO-31 / EQ-31 | Effective negative controls and real positive operations | Each independently applied narrowing causes its named intended property assertion to fail, not setup/crash/timeout | Restored gate rejects known violation and actually permits neighboring valid operation | Replace direct oracle with admission/canary/peer proxy; known violation passes and ProxyOracleDenied fails |
| PO-32 / EQ-32 | Exact production-entry evidence identity | Wrong service properties, shell-only or incomplete logs produce no qualification | Full evidence records actual exact production service invocation and all required observations | Accept wrong-unit or truncated evidence; qualification verdict fails ProductionEvidenceDenied |
| PO-33 / EQ-33 | Approved update, invalidation and no revoked rollback | Unapproved drift/revoked tuple causes no activation or renewed authority | Approved requalification actually completes native update gates and new exact evidence | Skip revoked rollback check; activation trace fails UpdateActivationDenied |
| PO-34 / EQ-34 | Immediate detection fence and station disposition within at most 300 seconds | Zero new starts/releases after detection; missing confirmed disposition, later trigger, longer bound or reset fails independently on Linux and macOS | Whole-account stop with quiet period or qualified narrowing confirmed by detection + B (B <= 300 seconds); failed narrowing falls back to confirmed stop within that same deadline; recovery completes | Drop one fence or deadline: DW-27/DW-28 fail; reset clock on retry/restart/publication/recovery: RevocationClockResetDenied fails; actual recovery checked by DW-29 |
| PO-35 / EQ-35 | Published qualified station-caller purpose for the active generation | Missing integration disables all dependent paths; readable-key/Git/arbitrary-byte fallbacks and stale generation cause zero caller signatures or onward effects | Published purpose/adapters actually sign the permitted caller assertion for the active generation; independent protected service root works | Bypass purpose readiness: StationCallerPurposeDenied fails; enable one fallback: StationCallerFallbackDenied fails; ignore generation: StationCallerGenerationDenied fails |
| PO-36 / EQ-36 | Bounded structured diagnostics without sensitive payloads | Inspect every diagnostic/refusal and qualification/recovery evidence channel: zero synthetic sensitive values/headers/bodies and bounded emitted size | Actual bounded structured permitted fields and resource/effect references support refusal and recovery | Copy synthetic payload or remove output bound independently: SensitiveDiagnosticDenied fails for the leaking/oversized channel |
| PO-37 / EQ-37 | Code-free idempotent preparation and durable exact-effect handles | Actual instruction trace contains no controlled code; durable effect/boundary count stays one through duplicate/lost/partial replies; wrong handle/digest has no effect | Reconciled original handle/digest survives restart and authorizes only the same preparation; controlled code runs later after full start gates | Run one prepare hook: PrepareCodeDenied fails; allocate a second effect on reply loss or accept wrong digest: PrepareDuplicateDenied fails |
| PO-38 / EQ-38 | Separate tuple support, capability, qualification and activation axes | Unsupported or out-of-scope restricted tuple produces no admission; supported label alone cannot admit missing mandatory proof | Exact supported and in-scope restricted tuples actually operate only after independent parity, qualification and activation checks | Treat support label as parity/qualification or ignore restricted scope: TupleSupportDenied fails |

### Additional qualification subcases

EQ-35 exercises bootstrap and recursive delegation as separate dependent paths.
StationCallerGenerationDenied uses a real published, qualified purpose and adapters
with a retired generation; it observes no caller signature or onward request. Its
paired StationCallerPurposeAllowed control uses the active generation with all
other bindings unchanged. Missing-purpose and each forbidden-fallback variant
likewise have adjacent active-generation controls through the published purpose.

EQ-36 plants distinct synthetic sensitive markers in credential values,
authorization headers and private request bodies. Exercise admission, each adapter,
receipt readers, network/credential mediators, qualification collection and recovery
independently, on accepted and refused paths. Observe every emitted channel and
published size bound; test oversized and repeated requests as well as ordinary
ones. Removing only one channel's exclusion or bound must fail its own
SensitiveDiagnosticDenied variant; valid controls retain bounded non-sensitive
reason, accounting and evidence references without copying the planted payload.
No real credential or private body is used to establish these future observations.

### EQ-11 operator acceptance bindings

These are additional **unrun qualification subcases**, not document-check evidence.
Run each negative and its adjacent valid control independently through the actual
start, resume and restart entry points. Keep the task/declaration, station/generation,
placement, qualified weaker profile, quantitative bounds, compensation and every
unrelated gate valid and identical except for the stated acceptance binding. Use
independently authenticated synthetic operator acts and controlled authority time.
A fresh valid boundary receipt remains present in the negative fixtures: its own
validity MUST NOT substitute for the operator act. Conversely, a valid act never
waives the independent receipt/currentness checks in EQ-13/14/21. Do not use
`absent` or `PENDING-VERIFY` as the weaker profile in the valid controls.

| Named negative subcase | Input variation | Required direct observation | Paired valid control | Independent narrowing / intended witness |
|---|---|---|---|---|
| AcceptanceMatrixRevisionDenied | Omit the act's exact matrix binding, or retain an otherwise valid unexpired act for the previous matrix revision while current qualified matrix evidence is valid | Explicit matrix-binding refusal; zero new start/resume/restart authorization or work; existing fences/obligations retained; no equality label | AcceptanceMatrixRevisionCurrent: a current act bound to the exact current matrix and identical quantitative scope actually permits each transition; all three outputs show weaker status and exact acceptance | WeakerMatrixBindingOnlyRemoved removes only matrix-revision comparison, retaining interval checks, scope and disclosure; the previous-revision variant of AcceptanceMatrixRevisionDenied must fail |
| AcceptanceValidityDenied | Omit the operator interval, or use a validly authenticated act whose interval is strictly before or after current authority time (Expired and NotYetValid variants) | Explicit operator-act validity refusal; zero new start/resume/restart authorization or work despite the fresh receipt; no silently renewed interval, lost obligation or equality label | AcceptanceValidityCurrent: an exactly bound act with authority time strictly inside its interval actually permits each transition within the same task/bounds; matrix, receipt and scheduler output retain visible weaker status and the current act | WeakerActExpiryOnlyRemoved removes only operator-act expiry enforcement, retaining missing-interval rejection, matrix/scope checks and disclosure; AcceptanceValidityDenied.Expired must fail |

Every invalid variant requires its own corresponding valid control at each entry
point, so rejecting every act cannot pass. Observe the acceptance decision's named
reason and the actual transition/work trace, not an unrelated parse/setup failure
or an error alone. The matrix-change fixture MUST keep current profile/qualification
proof valid so stale qualification cannot mask the act-binding check. Fresh valid
acceptance MUST NOT restart execution budgets or the original drift/revocation
response clock; these controls leave the existing deadline oracles in force.

### EQ-34 station security-revocation deadline

These are unrun production-entry qualification subcases on both Linux and macOS.
Use controlled monotonic observations of detection, immediate fencing, actual
process absence over the required quiet period, and actual narrowing confirmation.
RevocationDeadlineExceeded fails if neither permitted outcome is confirmed by
`detection + B`, even with intact fences and unknown status. RevocationBoundDenied
refuses a profile with a bound above 300 seconds or a trigger later than detection;
a profile with a shorter bound must satisfy that shorter bound. Paired valid
controls complete each permitted outcome exactly at 300 seconds and before it,
and complete within the shorter profile bound. A completion after the applicable
boundary is a failure, never a successful safe hold.

RevocationClockResetDenied separately exercises retry, observer restart, delayed
publication and recovery near the original deadline; none may obtain another
interval. Keep current authority, all fences and other prerequisites intact so a
stale-credential refusal cannot mask the deadline observation. The paired positive
actually completes before the unchanged deadline after each transition. Failed or
unconfirmed narrowing has a separate positive with confirmed whole-account stop,
including quiet period, within that same deadline. Removing only clock persistence
must fail RevocationClockResetDenied; removing only completion enforcement must
fail DW-28. These are required future controls, not executed evidence.

### Completion and deadline oracles

Failure safety and completion are independent verdicts. Fenced, unknown, refused,
contained, or reserved state cannot satisfy an outstanding completion obligation.
For a published time bound, qualification requires observed completion no later
than that bound, including confirmation and any required quiet period. A missed
bound fails the property even when every failure-safety check passes. Those checks
remain mandatory after failure; no timeout authorizes unsafe cleanup or reuse.

For an event-order obligation, completion is observed before the named dependent
effect. No dependent effect is allowed to win a race with incomplete prerequisites.
A valid positive fixture actually reaches that effect after completion: permanent
refusal cannot pass. An invariant maintained over an interval is checked throughout
that interval, not just when a request returns. Each case records the trigger,
clock/event boundary, actual observations and separate safety/completion verdicts.

The inventory groups all completion, ordering and response obligations, including
those inherited through the operation table. References identify whole clauses;
only their completion/ordering part is inventoried here. Each `DW` is a named
qualification witness under its listed EQ cases; each `DM` is its paired narrowing
control. A DM drops only the listed enforcement on the stuck/unknown branch,
retaining normal success and all fences. Its DW has to fail the completion property
for that exact omission. Each positive includes ordinary success and a transient
unknown/stall resolved before the same applicable boundary. These are required
future production-entry tests, not claims of runtime tests executed for this draft.

`B` means the applicable response/stop bound measured from its original triggering
event. For security revocation of a Linux or macOS station, that event is detection
and `B` is 300 seconds or the profile's shorter bound. No profile may lengthen it
or move the trigger; retries, observer restarts, delayed publication and recovery
never reset it. Other classes publish their approved bounds without weakening the
station baseline. `E` means before the named dependent event; `I` means throughout
the stated interval.
Missing required bounds/evidence cannot qualify a class. Event ordering adds no
arbitrary wall-clock deadline: reconciliation may remain unknown with intact
fences; it cannot report completion, release reservations or authorize a successor.
Standing stations still have no lifetime deadline. No row relaxes safe failure.

| ID; source clauses and qualification cases | Required observable completion/boundary | Named deadline/completion witness | Narrowing control on stuck/unknown path | Positive controls within the same boundary |
|---|---|---|---|---|
| TO-01; §1, EIC-2-01/03/04/06/07, EIC-3-03/04, EIC-4-01/02, EIC-6-01/02, EIC-7-02/03/05, EIC-10-01/03; EQ-01/02/03/10/15/17/30/32 | E: protected profile, complete exact qualification, task comparison and fixed plan precede admission/start | DW-01-admission-incomplete: qualification pending at attempted start | DM-01: omit pending-path admission prerequisite | Exact qualified plan starts only after all gates; pending evidence completed before start |
| TO-02; EIC-2-05, EIC-7-04; EQ-11/17 | E: authenticated weaker acceptance and actual disclosure retained in receipt and scheduler answer before dependent effect | DW-02-disclosure-pending: accepted reduction omitted while reply/receipt is pending | DM-02: skip pending-path disclosure completion | Complete acceptance/disclosure then admitted effect, including delayed disclosure |
| TO-03; EIC-3-01/06; EQ-09/12/26 | E: exact binding resolution and retained fences/accounting before each resumed effect | DW-03-binding-unknown: restart effects precede durable binding/accounting recovery | DM-03: skip unknown-path binding recovery | Exact recovered versions/debt before effects, including interrupted recovery |
| TO-04; EIC-3-02, EIC-4-04/08, EIC-7-06; EQ-05/07/09/12/16 | E: confirmed whole-account absence and prior ingress fence before replacement | DW-04-successor-unknown: predecessor still alive/unknown at replacement | DM-04: skip unknown-path absence prerequisite | Sequential replacement after quiet-period zero; stalled inventory resolved first |
| TO-05; EIC-2-08, EIC-4-03, EIC-7-01/02; EQ-04/16/20 | E: all restrictions and descriptor reduction applied before first controlled instruction/descendant | DW-05-hook-pending: hook executes while a boundary application is stuck | DM-05: omit stuck-path application-before-code gate | Full boundary then hook/descendant; delayed application completes before code |
| TO-06; EIC-4-04, EIC-10-05; EQ-05/34 | B: actual confirmed qualified narrowing or whole-account stop including quiet period by the original deadline; station security revocation uses detection + B with B <= 300 seconds | DW-06-narrowing-unknown: neither outcome by B although fenced/unknown | DM-06: drop deadline enforcement only while narrowing is stuck | Confirmed narrowing by B; failed/unconfirmed narrowing followed by confirmed stop by B |
| TO-07; EIC-4-05/07, EIC-7-06; EQ-06/08/16 | E: affected ingress actually closed before stop/export/replacement; separate messaging cannot reopen it | DW-07-ingress-pending: dependent operation overtakes a stalled fence | DM-07: skip stuck-path ingress closure | Closed ingress then operation; delayed closure completes first, daemon stays separate |
| TO-08; EIC-4-06, EIC-6-04, EIC-7-06; EQ-07/15/16 | B where stop is bounded; E before absence/reuse: complete account zero over quiet period, including OS-spawned work | DW-08-stop-unknown: hidden child lives past B or claimed absence | DM-08: omit unknown-path full-account completion | Whole-account zero/quiet period within B; escaped child actually stopped before confirmation |
| TO-09; EIC-4-08; EQ-07/09 | E: replay of recorded absence actually returns original evidence without signalling | DW-09-replay-pending: replay remains unknown despite intact recorded evidence | DM-09: drop pending-path replay completion | Evidence returned without signal, including delayed but intact evidence read |
| TO-10; EIC-5-01; EQ-13 | E: launcher writes protected evidence of confirmed applied state before receipt consumption | DW-10-receipt-write-stuck: caller consumes an unwritten/partial applied-state claim | DM-10: skip stuck-path protected-write completion | Protected applied-state receipt consumed only after write, including delayed write |
| TO-11; EIC-5-02; EQ-04/14 | E: apply boundary, publish complete validated receipt, bind admission, then controlled code | DW-11-publication-unknown: code starts while publication/binding is pending | DM-11: drop pending-path publication ordering | Complete durable receipt/admission binding before code; interrupted publication reconciled first |
| TO-12; EIC-5-03, EIC-8-04; EQ-21/24 | E: independent current-state read/recheck at final release serialization for issue and renewal, after refresh | DW-12-refresh-unknown: refreshed credential released before final current check | DM-12: omit pending-refresh final recheck | Current issue and renewal complete final check before release, including delayed refresh |
| TO-13; EIC-2-05, EIC-5-04/06; EQ-11/14/21/24/30/33 | E: invalidation durable and affected authority closed before next start/ingress/release; no stale completion reopens it | DW-13-invalidation-stuck: affected effect wins against a pending invalidation | DM-13: drop stuck-path invalidation-before-effect | Invalidation wins first; eligible new evidence later permits only new authorized effects |
| TO-14; EIC-5-05, EIC-8-05; EQ-22 | E: receipt publication, dispatcher binding and issue/renewal gates all active before conformance claim | DW-14-activation-pending: partial migration claims conformance | DM-14: skip pending-path joint activation | All participants active before claim, including delayed last participant; refresher stays separate |
| TO-15; EIC-4-08, EIC-5-07; EQ-07/09 | E: reconciliation obtains original durable effect evidence before claiming completion or releasing reservations | DW-15-reconcile-unknown: fenced unknown is reported as completed/released | DM-15: omit unknown-path reconciliation evidence | Original effect resolved without duplicate/successor signal; delayed evidence completes first |
| TO-16; EIC-5-08; EQ-09/23/34 | E: freshness anchors/fences survive or are re-established outside restored domain before resumed effects | DW-16-restore-pending: effects resume while freshness recovery is incomplete | DM-16: skip pending-restore freshness completion | Re-established external anchors precede effects, including interrupted restore |
| TO-17; EIC-8-01; EQ-18 | E: enforced source/DNS/redirect policy or closed route before any network effect after enforcer failure | DW-17-proxy-unknown: request escapes while enforcer outcome is unknown | DM-17: omit unknown-path route closure | Allowed bounded destination works; enforcer failure closes route before packet, restored policy permits valid request |
| TO-18; EIC-8-07, EIC-10-06; EQ-21/24/34 | E: current evidence/final recheck complete without conflicting cross-service lock waits before release resumes | DW-18-lock-stuck: healthy continuation deadlocks or releases using stale completion | DM-18: skip stuck-path lock ordering/current-state completion | No lock cycle, exact current release after delayed immutable evidence; broken state never releases |
| TO-19; EIC-9-01, EIC-7-05; EQ-17/25 | B for declared soft response: actual advertised action by B; hard limits checked continuously | DW-19-soft-response-unknown: monitor reports fenced/unknown but advertised action misses B | DM-19: omit stuck-path response deadline | Advertised soft action completes by B; hard control remains hard, absent property refuses requirement |
| TO-20; prepare operation, EIC-9-02; EQ-25/26 | I/B: measured pilot retains accessible recovery reserve at saturation, recovery action completes within its declared bound | DW-20-reserve-starved: nominal reserved capacity exists but recovery misses B under load | DM-20: omit stuck-work reserve enforcement | Small measured concurrency and actual recovery within B, including stalled workload at envelope |
| TO-21; EIC-9-02/03; EQ-25/26 | E/I: quotas/debt and shared host budget accounted before further work and throughout standing/frozen execution; actual qualified release precedes returned memory/state credit | DW-21-accounting-pending: identity churn starts work before retained debt is charged | DM-21: skip pending-path debt/reserve accounting | Finite aggregate quotas preserved across identities and delays; standing work continues within quota |
| TO-22; destroy operation, EIC-9-04; EQ-07/27/29 | E after absence/custody, B only if cleanup policy publishes one: actual residue removal and confirmed cleanup before destroy success/reuse | DW-22-destroy-stuck: residue survives but fenced/unknown counts as destroyed | DM-22: omit stuck-path residue completion | Residue actually removed and confirmation recorded after prerequisites, within applicable cleanup bound |
| TO-23; EIC-9-05/06; EQ-28 | E: full bounded validation before whole publication, or refusal with no partial/outside-root write | DW-23-import-pending: incomplete validation reported as successful publication | DM-23: skip pending-path validation/atomic publication | Valid object fully materializes after validation; delayed validation completes before publication |
| TO-24; EIC-9-06/07; EQ-29 | E: complete-content custody and dependency provenance before success/deletion, unless exact authorized disposition waives custody | DW-24-custody-unknown: missing blob marked retained/unknown then source deleted | DM-24: omit unknown-path custody prerequisite | Complete retrievable bytes/provenance then deletion, or authenticated exact waiver; delayed transfer completes first |
| TO-25; EIC-10-01/02/03; EQ-30/31/32 | E: exact production evidence, intended negative/control failures and positives complete before qualification | DW-25-evidence-pending: truncated/skipped/deadlocked run marked qualified | DM-25: skip pending-path evidence completion | Exact complete logs with named intended failures and actual valid successes, delayed collection completes first |
| TO-26; EIC-6-02/03, EIC-10-04; EQ-01/15/30/33 | E: changed tuple invalidated before new admission; reviewed native requalification before reopening, never revoked rollback | DW-26-update-unknown: drift resumes work while requalification is pending | DM-26: omit unknown-update invalidation/requalification gate | Changed tuple closes then reopens only after complete reviewed checks; delayed checks never bypass |
| TO-27; EIC-5-06, EIC-10-05; EQ-14/21/34 | E immediately at detection of revocation: new starts and final credential releases fenced, including already in-flight refresh | DW-27-revocation-pending: start/release crosses revocation serialization while fence update stalls | DM-27: omit stuck-path immediate start/release fence | Fence precedes next start/release even with delayed refresh; later non-revoked admission works |
| TO-28; EIC-10-05; EQ-05/34 | B from security-revocation detection: whole-account stop including quiet period or confirmed qualified non-revoked narrowing actually complete; Linux/macOS station B <= 300 seconds, never reset | DW-28-revoked-unknown: neither confirmed outcome by original detection + B despite intact fences; RevocationClockResetDenied retains the same deadline across retry/restart/publication/recovery | DM-28: omit deadline enforcement only for stuck/unknown execution; separately reset the clock only on a recovery transition | Confirmed whole-account stop by detection + B; separately qualified non-revoked narrowing by the same deadline; failed narrowing stops within the original deadline, including transient unknown |
| TO-29; EIC-10-06, EIC-5-08; EQ-09/24/34 | E on each authorized recovery call with intact prerequisites: operation actually returns its permitted evidence/effect | DW-29-recovery-stuck: blanket hold/refusal replaces intact status/list/observe/reconcile/stop | DM-29: omit pending-path authorized recovery service | Each permitted call progresses under intact state, delayed original evidence resolves; broken state still refuses |
| TO-30; §11, EIC-8-08, EIC-11-01; EQ-01/22/30/33/35/38 | E: station rules, carriers, support record and complete exact-tuple qualification precede activation; dependent station caller paths also await the published qualified signing purpose/adapters | DW-30-rollout-pending: incomplete native/optional tuple activated while prerequisites remain pending | DM-30: skip pending-path rollout completion | Only complete reviewed tuple activates after delayed prerequisites; pool/optional tuples qualify separately |
| TO-31; prepare operation, EIC-4-09; EQ-37 | E: original preparation effect and policy digest durably bound before returning a handle or consuming it at start; lost/partial replies reconcile that same effect | DW-31-prepare-reply-unknown: reply loss creates a second boundary or a non-durable/unbound handle is consumed | DM-31: allocate a new effect only on the lost-reply path or skip durable binding | Retry/restart reconciles the same effect/handle/digest and one boundary; delayed original publication completes before handle consumption and controlled code |

Pure classification/containment invariants (for example EIC-2-02, EIC-3-05,
EIC-8-02/03/06 and the non-ordering parts of other clauses) retain their existing
paired EQ cases. They promise neither eventual recovery nor a station lifetime
limit. This inventory does not convert refusal of invalid work into an obligation
to finish that work. Its positives require completion only with valid authority,
intact prerequisites and the resources promised by the selected qualified class.

Production qualification reports retain command, source/test/configuration identity,
platform/tuple, exit codes, positive/negative outcomes and any unverified limits.
Structural vocabulary/format checks supply no evidence that qualification tests
detect weakened behavior; runtime sensitivity requires the actual paired gate cases.

## Open questions for the operator

1. **Q-EIC-01 — Shared ownership and vocabulary.** Who owns EIC coordination and
   the parity mapping? Recommended: one cross-module specification owner with
   station/module acceptors; review the §7 mapping and local remainders against
   pinned station parity before activation.
2. **Q-EIC-02 — Signed carriers.** Which waggle types/domains represent boundary,
   qualification and revocation records? Recommended: reviewed signed record types
   with module-owned readers and no new envelope; do not overload existing types.
3. **Q-EIC-03 — Joint activation.** Which exact native path first enables receipt
   publication and issue/renewal checks together? Recommended: one narrow station
   class; keep standalone refresh and every incomplete integration non-conformant.
4. **Q-EIC-04 — First measured envelope.** Which finite quotas, concurrency,
   recovery reserve, quiet-period duration and shorter profile response bounds are
   accepted? The Linux/macOS station security-revocation ceiling is fixed at 300
   seconds from detection, including confirmation and quiet period. Other classes'
   bounds and non-revocation response parameters remain to be approved.
   Recommended: conservative measured limits and no unmeasured heavy admission.
5. **Q-EIC-05 — macOS parity and capabilities.** Which exact CLI/build/task and
   compensation cells activate first? Recommended: review each required cell;
   refuse hard requirements until `present`, and qualify platform tooling separately.
6. **Q-EIC-06 — Recovery and compromise.** Who authorizes revocation disposition,
   narrowed-class acceptance, journal restore and host reuse? Recommended: external
   security authority, durable fences and independently reviewed bounded recovery.
7. **Q-EIC-07 — Messaging placement.** Which shared protected messaging-account
   lifecycle and per-identity daemon/client/input-fence adapter is qualified?
   Recommended: one shared service account outside all agent accounts, separately
   bound daemon and client per identity, no identity borrowing or ingress bypass;
   per-identity service accounts require separately approved optional placement.

[parity]: https://github.com/relux-works/swarma-user-manager/blob/71dd888e23350d736ea74589ea1f5b4692258a2d/spec/platform-parity.md
[stations]: CIP-0024-agent-stations.md
[dispatcher]: https://github.com/relux-works/swarma-dispatcher/blob/b719e2307f5f4d6284abbd1ba60c42330f2d6ae8/spec/dispatcher.md
[broker]: https://github.com/relux-works/swarma-credential-broker/blob/f2c01f52477b5885aefd5b6bd04d09a6a22813b2/spec/broker.md
[session-host]: https://github.com/relux-works/swarma-session-host/blob/e78aa20777c3ac4516268143859d6b3114ad68c1/spec/session-host.md
[linux-host]: https://github.com/relux-works/swarma-user-manager/blob/a5e99c4f9d4cde0d542588806dbd535e0af26ac4/docs/linux-backend.md
[accounts]: https://github.com/relux-works/swarma-user-manager/blob/a5e99c4f9d4cde0d542588806dbd535e0af26ac4/spec/stations-v0.md
[helper]: https://github.com/relux-works/swarma-user-manager/blob/a5e99c4f9d4cde0d542588806dbd535e0af26ac4/spec/helper.md
[mac-accounts]: https://github.com/relux-works/swarma-user-manager/blob/71dd888e23350d736ea74589ea1f5b4692258a2d/spec/stations-macos-v0.md
[waggle-record]: https://github.com/relux-works/waggle/blob/98c9cfd26cfc57a7ee82176cd599e92af03e69bb/record/README.md
[waggle-verifier]: https://github.com/relux-works/waggle/blob/98c9cfd26cfc57a7ee82176cd599e92af03e69bb/verifier/README.md
