# CIP-0026: Foreign-code execution

- **Status:** Review
- **Owner:** orchestrator; decisions: operator
- **Created:** 2026-10-24
- **Related:**
  [CIP-0025](CIP-0025-execution-isolation-contract.md) — Execution Isolation Contract;
  [CIP-0024](CIP-0024-agent-stations.md) — Agent stations;
  [Threat catalogue](#threat-catalogue)
- **Affects:** admission/scheduler, dispatcher adapters, launcher, runner hosts,
  qualification, input/artifact store, result consumers and network enforcement

## Summary

Define the public pool as the first external execution class of a general
Execution Isolation Contract (EIC). The pool MUST run third-party code only in
ephemeral isolated executions on dedicated machines without platform secrets or
authority. Services MUST refuse unsupported guarantees, stale qualification and
unsafe data handling; an explicitly accepted weaker guarantee MUST remain visible.
This proposal defines requirements, not a shipped API, chosen backend or qualified
placement. Shared EIC objects are incorporated from CIP-0025 below; shared guarantee
vocabulary is pinned to published station parity and pool-local identifiers are
explicitly separate.

## Motivation and user stories

- A requester submits an exact candidate for a build or test without executing
  candidate code on an agent station or giving it provider credentials.
- A scheduler explains whether the exact requested isolation and resource bounds
  are available before any third-party startup script runs.
- An operator can accept an explicitly described reduction for one execution,
  while services continue enforcing every non-waivable platform boundary.
- A requester receives bounded artifacts, exact input provenance and an honest
  description of host-reported evidence, including interrupted or unknown work.
- A pool operator can fence a compromised host without relying on that host's
  claim that it stopped, cleaned itself or passed qualification.

## Current state

The [Threat catalogue](#threat-catalogue) defines the 28 threat identifiers used
here, controls TC-01 through TC-25, adversaries and the interpretation inventory.
It is this proposal's security reference, not runtime qualification evidence.
The full threat model is maintained separately.
No pool implementation or measured pool-host conformance is supplied here.

The inspected public specification baselines are:

- [Dispatcher](https://github.com/relux-works/swarma-dispatcher/blob/b719e2307f5f4d6284abbd1ba60c42330f2d6ae8/spec/dispatcher.md),
  §3.6 R-UNTRUSTED: slice 0 refuses untrusted allocations; untrusted allocations
  receive no subscription binding or lease. §5.3 R-VERIFY sends builds/tests to
  secret-free ephemeral runners on another machine. R-EXEC and R-SHARED remain
  restrictions on platform hosts, not permissions granted by pool admission.
- [Broker](https://github.com/relux-works/swarma-credential-broker/blob/f2c01f52477b5885aefd5b6bd04d09a6a22813b2/spec/broker.md),
  R-UNTRUSTED: no untrusted binding, issue or renewal, including API credentials;
  absent or conflicting class evidence refuses rather than becoming trusted.
- [Stations, CIP-0024](CIP-0024-agent-stations.md):
  protected agent identity, signing and persistent station lifecycle are separate
  from a pool runner. This CIP gives the pool none of those station rights.
- [Key custody](https://github.com/relux-works/swarma-keymaker/blob/46825e7c12cc0d5733ba057bb1f9609caf2925a4/spec/keymaker.md),
  §3.1, and [registrar](https://github.com/relux-works/swarma-registrar/blob/2219f70358fb7b5c7d66f229c80a8ba4a1fe0230/spec/registrar.md):
  host identity depends on kernel peer UID and admitted generation. A guest UID,
  forwarded connection or matching integer MUST NOT stand in for that evidence.
- [Platform envelopes and grants](https://github.com/relux-works/waggle/blob/67df75bec015ea463f685e4daf4975ecda18816a/spec/swarm-envelope-2.md),
  §§2–3: protected protocol selection, concrete action/target authority,
  attenuation, current time and revocation are consumer obligations. Transport
  delivery and valid signatures alone do not authorize a pool action.
  The repository was renamed to `relux-works/swarma-envelope` on 2026-10-26;
  this historical commit-pinned URL retains its original spelling.

Shared EIC objects are defined in [CIP-0025](CIP-0025-execution-isolation-contract.md);
cross-module coordination remains an operator question there. Shared guarantee
naming is published in [station platform parity][station-parity] at
`71dd888e23350d736ea74589ea1f5b4692258a2d`; the mapping below preserves local semantics.
This proposal MUST NOT silently add fields to any existing closed carrier.

## Design

### Options considered

1. Execute foreign code under a station account. This reuses existing capacity
   but violates R-VERIFY and exposes a platform trust domain. Rejected.
2. Pool persistent accounts on a machine that also hosts platform services.
   This reduces provisioning but combines residue, authority and service exposure.
   Rejected; an ephemeral process is not an ephemeral isolated execution.
3. Use dedicated pool hosts, qualified execution adapters and a mediated data
   return path. This adds lifecycle and qualification work but separates platform
   authority from hostile computation. Recommended without selecting a backend.

### Recommendation

Admission MUST remain disabled until the published service interfaces, limits,
qualification and operator decisions required here exist. The initial recommended
policy is secret-free jobs, exclusive host allocation, no device passthrough and
no egress; declared dependency access requires a separately admitted policy.
These are proposed defaults for decision, not claims of current deployment.

The scheduler, launcher, transfer gateway and result consumer MUST enforce their
own decisions. Text in instructions, declarations, reports or job output MUST
NOT be an enforcement boundary. An operator acceptance is an authenticated,
current service act, never a sentence in a job or a model's acknowledgement.

### Definitions incorporated from CIP-0025

The following references are normative for this proposal. CIP-0025 supplies the
shared objects and ordering; this CIP adds the external pool's requirements and
retains every stronger pool restriction. Filing either proposal does not qualify
an implementation or publish a module wire format. Pool declarations and reporting
identities remain separate from station declarations and service authority.

| Object | Normative CIP-0025 reference | Pool requirements retained or made explicit |
|---|---|---|
| Isolation profile | [§2, EIC-2-01/03/08](CIP-0025-execution-isolation-contract.md#2-isolation-profiles-and-capability-coverage) | Protected resolved immutable policy; caller text cannot choose or weaken it. Pool interfaces, data roots, network and hard-limit requirements remain mandatory. |
| Capability vector | [§2, EIC-2-02/04/06/07](CIP-0025-execution-isolation-contract.md#2-isolation-profiles-and-capability-coverage) and [§7, EIC-7-04/05](CIP-0025-execution-isolation-contract.md#7-macos-native-and-parity) | Exact per-guarantee scope, evidence, enforcement and four statuses; pool-local IDs and stronger pool minimums stay separate. No OS/backend inference or missing-member substitution. |
| Adapter operations | [§4, operation table and EIC-4-02/03/04/08/09](CIP-0025-execution-isolation-contract.md#4-admission-and-adapter-operations), [§3 bindings](CIP-0025-execution-isolation-contract.md#3-identity-placement-and-execution-bindings) and [§5 recovery](CIP-0025-execution-isolation-contract.md#5-boundary-receipts-and-recovery) | All operations remain generation/execution-bound and idempotent for identical effect identities. These semantic names define no CLI/RPC grammar. Complete qualified runner-scope absence, residue destruction and original-effect reconciliation remain required. |
| Boundary receipt | [§5, receipt bindings and EIC-5-01/02/04/06/07/08](CIP-0025-execution-isolation-contract.md#5-boundary-receipts-and-recovery) | Incorporate the complete binding, currentness, invalidation and ordering contract. Keep the pool-only writer/reporting authority and distinct physical-start evidence below; no broker lease or station-conformance claim follows. |
| Qualification tuple | [§10, EIC-10-01/03/04](CIP-0025-execution-isolation-contract.md#10-qualification-updates-and-revocation) | Include every enforcing layer and exact harness, service-entry and deployment configuration. Pool image/profile/launcher/collector digest bindings, independent reviewed evidence and expiry/revocation state remain additional requirements. |
| Weaker-guarantee acceptance | [§2, EIC-2-05/06](CIP-0025-execution-isolation-contract.md#2-isolation-profiles-and-capability-coverage) and [§3 identity/placement/execution](CIP-0025-execution-isolation-contract.md#3-identity-placement-and-execution-bindings) | Use the exact matrix revision, quantitative scope and current operator-act interval at start/resume/restart. Bind the pool requester, declaration, protected pool identity, placement generation and execution versions; this mapping creates no station identity. Requester acknowledgement and non-waivable pool minimums remain additional requirements. |

`probe` inventories capabilities and MUST NOT make a placement qualified.
`qualify` requires independently reviewed paired evidence from the intended
production service entry. The scheduler MUST read qualification from protected
external records rather than accept a host-supplied boolean.

Under EIC-4-09, `prepare` MUST run no agent-controlled or workload code, even
inside an isolated runner. Preparation MUST be idempotent and return a durable
handle tied to its original effect and effective policy digest; a lost or partial
reply MUST reconcile that effect without preparing another boundary. The pool
additionally requires constrained staging, reserved capacity and immutable pinned
inputs. Candidate hooks and package tooling belong to admitted `start` work, after
the full boundary, receipt and input fences. Qualification MUST include CIP-0025's
EQ-37 preparation cases in addition to FX-06/22 here. Policy changes follow
EIC-4-04: an immutable running restriction requires a new physical execution only
after confirmed prior absence and fresh admission; linked policy effects preserve
the original admitted input and receipt history. Its EQ-05 cases also apply.

`start`, `observe`, `stop`, `destroy` and `reconcile` follow the referenced §4
operations and §5 ordering/recovery contract, plus the pool lifecycle below.
No operation may substitute boundary evidence for actual start, absence or cleanup.

### Job declaration

The following twelve fields define the semantic declaration. Their wire encoding,
units, identifier syntax and numerical caps require reviewed versioned schemas
before activation. Objects MUST be closed; unsupported fields/versions refuse.
Authentication and requester identity come from protected delivery context.

| Field | Admissible value and constraint |
|---|---|
| `version` | Published pool declaration version; no negotiation fallback into a different protocol. |
| `request_id` | Requester-scoped idempotency identity; same identity with different canonical arguments refuses. |
| `inputs` | Bounded list of authorized object digests, lengths, kinds and logical runner destinations; immutable bytes, no host paths. |
| `runner_image` | Exact content digest of an approved image and its provenance; mutable tags alone are insufficient. |
| `entrypoint` | Bounded executable/arguments within the runner image or admitted inputs; interpreted only after the boundary applies. |
| `required_guarantees` | Guarantee IDs and minimum requirements from the reviewed vocabulary; no caller-selected enforcement class. |
| `resource_request` | CPU, memory, process, storage, I/O, output and optional published-device demands; published units, principal/global bounds and enforced limits apply. |
| `network_need` | `none` or bounded declared dependency destinations/protocols under published policy; a request does not grant egress. |
| `time_limit` | Bounded elapsed execution limit plus admitted deadline; no guest-controlled extension or implicit renewal. |
| `outputs_expected` | Bounded logical output names, supported inert types and size/count limits; no links into host paths or executable return channel. |
| `dependency_plan` | Pinned known dependency identities and permitted resolution needs; runtime resolutions must enter complete result provenance. |
| `result_policy` | Published evidence/retention requirement; cannot demand attestation or semantic truth that a host report does not provide. |

The declaration MUST NOT select trust class, host UID, host paths, platform
identity, broker credentials, signing keys, service sockets or privileged devices.
Device requests MAY name only entries in a published qualified device list;
unpublished devices and all requests to pass raw host handles MUST refuse.
No field can activate a station agent loop or acquire platform-service authority.

Secret-bearing jobs, credential injection and job-supplied credentials MUST refuse
under the initial secret-free verification class. Undeclared sensitive bytes cannot
reliably be detected; submission terms MUST state that authors must not send them.
The platform and host operators can inspect job plaintext; no confidentiality
against those operators is claimed.

Admission MUST intersect recorded class, requester authority, platform minimums,
operator policy, qualification and the declaration. Effective rights can only
narrow. Artifact digests authenticate bytes, not entitlement to retrieve them or
safe materialization. The store MUST independently authorize each object access.

The network enforcer MUST derive identity from protected placement/execution
bindings, not caller headers. `none` permits no external or host-service route.
For admitted dependency egress, every DNS answer, destination and redirect MUST
remain within policy across address families; private, loopback, link-local,
metadata and platform destinations MUST remain denied. Resolver bypass, unsolicited
ingress and policy/proxy failure MUST fail closed during running jobs as well as
at admission. Independent upstream containment MUST also bound a compromised host.

### Placement classes and guarantee vocabulary

Shared identifiers use the complete normative definitions in [station parity §1][station-parity]
at `71dd888e23350d736ea74589ea1f5b4692258a2d`. IDs describe properties, not products
or message-assurance levels. The required-property column retains the pool's
additional class obligations; these do not alter any shared definition. Each ID
in a grouped row is independently required and independently evidenced.

Pool-only identifiers use the explicitly local **`pool.`** namespace defined below.
They are not station identifiers and add no station matrix rows. The scheduler
MUST reject unknown IDs and incompatible vocabulary revisions. This pool's job
declaration remains a separate interface: it MUST NOT insert local IDs into
`station-required-guarantees/1` or imply station authority/qualification.

- **Exclusive:** one live job on a dedicated pool machine and no foreign co-tenant.
- **Shared:** concurrent mutually untrusted jobs on a dedicated pool machine;
  admission requires an approved sharing/leakage policy and compatible jobs.
- **Composed:** multiple virtualization/sandbox layers on a dedicated pool machine;
  the tuple includes every enforcing outer and inner layer and its co-tenancy.
  An operator workstation or machine hosting platform services is not this class.

A virtualized pool host MUST disclose its physical parent and other tenants to
the qualification authority. Unverifiable parent topology MUST refuse admission.
The composed class MUST NOT borrow exclusive-placement evidence; exclusive
requirements additionally need qualified exclusive allocation at every layer.

Statuses are exactly `present`, `weaker-with-compensation`, `absent` and
`PENDING-VERIFY`, with the normative meanings in [station parity §2][station-parity].
`present` requires matching full-scope evidence, not immunity to unknown exploits.
`absent` means unsupported; `PENDING-VERIFY` means unverified and unavailable for
admission, never an acceptable weaker level. No implementation is qualified here.
The separate **implemented, deployment qualification pending** annotation creates
no fifth status and has no admission effect; missing required proof stays pending.

#### Identifier mapping

Former labels below are migration references only, not additional accepted IDs.
A grouped replacement does not let one guarantee's evidence substitute for another.

| Former pool label (migration only) | Current required identifiers | Mapping scope |
|---|---|---|
| `isolation.read` | `isolation.read` | Shared read boundary; pool host/job scope remains required. |
| `isolation.write` | `pool.isolation.write` | All host/other-job state, beyond approved station controls. |
| `isolation.ipc` | `ipc.isolation`, `execution.descriptors` | Separate IPC and first-instruction descriptor obligations. |
| `isolation.residue` | `pool.isolation.residue` | Cross-job teardown, not generation-private temporary state alone. |
| `isolation.exclusive` | `pool.isolation.exclusive` | Physical/layer co-tenancy is pool policy. |
| `isolation.side-channel` | `pool.isolation.side-channel` | Unsupported elimination claim remains absent. |
| `network.egress` | `network.egress` | Shared policy; independent upstream containment remains required. |
| `network.ingress` | `pool.network.ingress` | Unsolicited pool traffic and transfer authorization. |
| `credential.absent` | `pool.credential.absent` | Credential absence is different from credential.issuance. |
| `identity.separated` | `pool.identity.separated` | Guest/native authority separation is not identity.generation. |
| `process.stop` | `process.stop` | Complete fenced scope and quiet interval; no leader-only substitution. |
| `limit.cpu` | `limit.cpu`, `pool.limit.elapsed-work` | Aggregate CPU rate/time plus separate elapsed-work ceiling. |
| `limit.memory` | `limit.memory` | Aggregate hard ceiling; protected recovery is an additional pool minimum. |
| `limit.storage` | `limit.disk`, `limit.io`, `pool.limit.storage` | Shared allocation/IO bounds plus pool inode/debt obligations. |
| `limit.output` | `pool.limit.output` | Output, expansion and consumer work are pool-owned. |
| `time.authority` | `pool.time.authority` | External time/freshness and rollback-safe budgets. |
| `input.integrity` | `pool.input.integrity` | Authorized objects and image provenance exceed shared-state isolation. |
| `input.interpretation` | `pool.input.interpretation` | External interpretation inventory is pool-owned. |
| `result.provenance` | `pool.result.provenance` | Result binding is not OS-effect provenance. |
| `result.inert` | `pool.result.inert` | Pool intake and review non-execution. |
| `journal.durable` | `pool.journal.durable` | Execution effects/blob custody, not the station generation-journal contract. |
| `control.bounded` | `pool.control.bounded` | Pool submission/transfer/recovery scope is separately bounded. |
| `update.requalified` | `update.requalified`, `qualification.revocation` | Fresh qualification and completed running-work revocation remain separate obligations. |

#### Pool-local normative definitions

These seventeen definitions belong only to the pool contract. They preserve the
original requirements where no station identifier has the same complete meaning.

| Local identifier | Normative guarantee |
|---|---|
| `pool.isolation.write` | Runner work cannot modify host or other-job bytes, metadata or effective state; writes stay inside its own admitted writable scope. |
| `pool.isolation.residue` | After qualified teardown, a new job cannot observe prior-job disk, memory, cache or snapshot state; actual cleanup/reset is required. |
| `pool.isolation.exclusive` | No concurrent foreign execution exists anywhere in the admitted physical and composed-layer sharing scope. |
| `pool.isolation.side-channel` | Advanced hardware side channels are eliminated; this unsupported property is absent in every class here. |
| `pool.network.ingress` | Unsolicited or unauthorized traffic cannot establish job ingress or an accepted transfer/control effect. |
| `pool.credential.absent` | No platform or injected job credentials enter a job; no pool subscription binding, broker issue or renewal occurs. |
| `pool.identity.separated` | Guest, forwarded or numerically matching identities cannot authenticate as a native station peer or obtain station service authority. |
| `pool.limit.elapsed-work` | Elapsed execution work stays within its admitted original time ceiling across retries and clock changes; limit-triggered stop completes within its published response bound. |
| `pool.limit.storage` | Writable inode and retained-storage/debt caps remain enforced across retries and identity changes, in addition to the separate shared allocation and IO bounds. |
| `pool.limit.output` | Logs/artifacts, expansion and parsing work obey admitted byte/count/work caps; partial content cannot be accepted as a whole result. |
| `pool.time.authority` | Accepted authority uses current external time and cannot gain validity or budget through rollback, reboot, retry or guest clock changes. |
| `pool.input.integrity` | Only authorized exact approved input/image bytes materialize, with immutable digest bindings and approved image provenance. |
| `pool.input.interpretation` | Every external interpreter is inventoried and confined to safe roots/types and bounded work; invalid input causes no outside-root write, partial publication, hook execution or discovery. |
| `pool.result.provenance` | Accepted host-reported results bind the exact request, attempt, inputs, dependencies and output bytes without asserting computation truth or stronger attestation. |
| `pool.result.inert` | Returned artifacts remain inert data throughout transfer, import, review, rendering and telemetry without activating code or configuration. |
| `pool.journal.durable` | Crash/restore recovery retains original execution-effect identity, at most one physical start, all blob obligations and fences; unknown completion is never invented. |
| `pool.control.bounded` | Submission, transfer, queue/work/debt caps preserve independent valid admission, stop and revocation completion under load by their original published bounds. |

#### Placement availability

All three cells of a grouped row apply to every listed identifier. A future
capability vector MUST record each identifier separately, including mixed statuses;
no conjunction may conceal a missing or weaker member.

| Guarantee ID | Required property | Controls | Threats | Exclusive | Shared | Composed |
|---|---|---|---|---|---|---|
| `isolation.read` | Runner cannot read unrelated host/job data | TC-02, TC-03, TC-21 | TM-ISO-01, TM-ISO-02, TM-DATA-04 | PENDING-VERIFY | PENDING-VERIFY | PENDING-VERIFY |
| `pool.isolation.write` | Runner cannot modify host/other-job state | TC-02, TC-25 | TM-ISO-01, TM-DATA-05 | PENDING-VERIFY | PENDING-VERIFY | PENDING-VERIFY |
| `ipc.isolation`, `execution.descriptors` | No undeclared host sockets, namespaces or inherited handles | TC-03, TC-09 | TM-ISO-02, TM-CRED-03 | PENDING-VERIFY | PENDING-VERIFY | PENDING-VERIFY |
| `pool.isolation.residue` | No previous-job state exposed after qualified teardown | TC-04, TC-06, TC-14 | TM-DATA-01, TM-DATA-03, TM-SUP-02 | PENDING-VERIFY | PENDING-VERIFY | PENDING-VERIFY |
| `pool.isolation.exclusive` | No concurrent foreign execution in the admitted sharing scope | TC-07, TC-21 | TM-SIDE-01 | PENDING-VERIFY | absent | PENDING-VERIFY |
| `pool.isolation.side-channel` | Elimination of advanced hardware side channels | TC-07 | TM-SIDE-01 | absent | absent | absent |
| `network.egress` | Enforced destinations/DNS/traffic policy, including upstream containment | TC-10, TC-11 | TM-NET-01, TM-NET-02 | PENDING-VERIFY | PENDING-VERIFY | PENDING-VERIFY |
| `pool.network.ingress` | No unsolicited job ingress or unauthenticated transfer | TC-10, TC-12 | TM-NET-03 | PENDING-VERIFY | PENDING-VERIFY | PENDING-VERIFY |
| `pool.credential.absent` | No platform or injected job credentials | TC-01, TC-08 | TM-CRED-01, TM-CRED-02 | PENDING-VERIFY | PENDING-VERIFY | PENDING-VERIFY |
| `pool.identity.separated` | Guest/host identities cannot acquire station authority | TC-09, TC-21 | TM-CRED-03, TM-AUTH-02 | PENDING-VERIFY | PENDING-VERIFY | PENDING-VERIFY |
| `process.stop` | Fenced account/runner-wide absence, not just leader exit | TC-19, TC-22 | TM-DOS-01, TM-LIFE-01 | PENDING-VERIFY | PENDING-VERIFY | PENDING-VERIFY |
| `limit.cpu`, `pool.limit.elapsed-work` | Enforced aggregate CPU rate/time and elapsed-work ceilings | TC-19 | TM-DOS-01 | PENDING-VERIFY | PENDING-VERIFY | PENDING-VERIFY |
| `limit.memory` | Enforced memory ceiling without starving recovery | TC-19 | TM-DOS-01 | PENDING-VERIFY | PENDING-VERIFY | PENDING-VERIFY |
| `limit.disk`, `limit.io`, `pool.limit.storage` | Enforced disk/inode/I/O bounds with retained debt accounting | TC-19, TC-20 | TM-DOS-01, TM-DOS-02 | PENDING-VERIFY | PENDING-VERIFY | PENDING-VERIFY |
| `pool.limit.output` | Bounded logs/artifacts and parsing/expansion work | TC-16, TC-20 | TM-RES-02, TM-DOS-02 | PENDING-VERIFY | PENDING-VERIFY | PENDING-VERIFY |
| `pool.time.authority` | Fresh external authority time and rollback-safe budgets | TC-18 | TM-TIME-01 | PENDING-VERIFY | PENDING-VERIFY | PENDING-VERIFY |
| `pool.input.integrity` | Authorized exact immutable inputs and approved image provenance | TC-05, TC-13, TC-15 | TM-DATA-02, TM-DATA-04, TM-SUP-01 | PENDING-VERIFY | PENDING-VERIFY | PENDING-VERIFY |
| `pool.input.interpretation` | Every external interpreter is constrained and mapped | TC-25 | TM-DATA-05 | PENDING-VERIFY | PENDING-VERIFY | PENDING-VERIFY |
| `pool.result.provenance` | Exact attempt/input/dependency/output bindings; evidence level disclosed | TC-15, TC-17 | TM-RES-01, TM-RES-03 | PENDING-VERIFY | PENDING-VERIFY | PENDING-VERIFY |
| `pool.result.inert` | Validated artifacts remain data through import and review | TC-16 | TM-RES-02 | PENDING-VERIFY | PENDING-VERIFY | PENDING-VERIFY |
| `pool.journal.durable` | Effect identity and recovery survive crash/restore fencing | TC-22 | TM-LIFE-01 | PENDING-VERIFY | PENDING-VERIFY | PENDING-VERIFY |
| `pool.control.bounded` | Submission/transfer budgets preserve independent recovery capacity | TC-20 | TM-DOS-02 | PENDING-VERIFY | PENDING-VERIFY | PENDING-VERIFY |
| `update.requalified`, `qualification.revocation` | Changed or revoked tuples cannot reuse old qualification | TC-13, TC-23 | TM-QUAL-01, TM-QUAL-02 | PENDING-VERIFY | PENDING-VERIFY | PENDING-VERIFY |

A capability vector MUST identify the exact evidence behind each row and its
scope. A host's assertion MUST NOT change its external qualification status.
A required `absent`, missing or `PENDING-VERIFY` property MUST refuse.
No hardware-side-channel elimination is promised even on an exclusive machine.

A `weaker-with-compensation` entry MUST state the missing part, actual enforced
substitute, residual risk, qualification evidence and permitted workloads. The
scheduler MUST require an explicit operator act plus requester acknowledgement
bound to the exact declaration, tuple, profile, guarantee and compensation before
admission. EIC-2-05 additionally requires the exact matrix revision, quantitative
scope/bounds and the operator act's own validity interval, independently of receipt
lifetime. Start, resume and restart MUST each reject a missing, not-yet-valid or
expired interval, changed matrix or any changed/missing binding; fresh currently
valid exact acceptance and qualification reevaluation are required. These bindings
use the protected pool subjects specified above, never borrowed station identity.
A changed input, tuple or compensation invalidates that acceptance.
The scheduler answer and boundary receipt MUST retain both requested and actual
status. They MUST NOT relabel the weaker entry `present`.

For `absent`, the operator may authorize a revised, explicitly reduced
requirement with requester acknowledgement; the scheduler MUST reevaluate that
new declaration. It MUST NOT pretend the original requirement was satisfied.
Unknown/unverified evidence cannot be converted into qualification by acceptance.
No acceptance may waive dedicated hosts, secret-free execution, service authority,
external enforcement, lifecycle fencing or current qualification minimums.

### Closed refusal vocabulary

The following twenty reason names are closed for this proposal's semantic result.
They do not rename existing module refusal codes. A reviewed versioned adapter
MUST map module outcomes before activation; clients MUST reject unknown reasons.
Stages below are adapter/admission stages, not a claim of published wire methods.

| Reason | Stage(s) | Refusing service and no-partial-effect rule |
|---|---|---|
| `declaration_invalid` | admission | Admission verifier rejects malformed/unknown fields, conflicting request arguments or unsupported logical paths; no allocation/start. |
| `authority_denied` | admission, prepare, start, intake | Consumer refuses wrong principal/action/target, expired/revoked/unavailable authority; no protected action or content release. |
| `class_forbidden` | admission | Scheduler refuses caller-selected class, station authority, secret/device escalation or non-pool host; no placement. |
| `guarantee_unavailable` | admission, prepare, start | Scheduler/launcher refuses missing or unsatisfied property; no payload start or substitute backend. |
| `weaker_acceptance_required` | admission, start | Scheduler/launcher refuses absent/stale exact acceptance; no silent reduced placement. |
| `quota_exceeded` | admission, prepare, start, intake | Budget owner refuses excess work/storage/output; no unbounded intake or partial publication; already-running work stays fenced/accounted. |
| `qualification_unavailable` | probe, qualify, admission, start | Qualification gate refuses missing/unverifiable tuple evidence; no placement/start. |
| `qualification_stale` | admission, prepare, start | Gate refuses expired evidence or tuple drift; no new launch; recovery remains available. |
| `qualification_revoked` | admission, prepare, start | Gate refuses revoked evidence; immediately fences new starts/releases and requires actual bounded active-work disposition under Lifecycle; unknown is not completion. |
| `input_provenance_missing` | prepare, intake | Materializer/consumer refuses absent immutable input or runtime dependency identity; no verified-result success or partial input publication. |
| `input_rejected` | prepare | Preparation worker refuses unsafe shapes, unsupported types or bounded-expansion failure; no outside-root write, published partial input or payload start. |
| `image_policy_denied` | prepare, start | Image loader refuses unapproved/revoked/mismatched image/backend/profile; no hook execution or replacement image. |
| `network_policy_unavailable` | admission, prepare, start | Scheduler/launcher refuses unapplied or unverifiable enforced policy; no fallback route or payload start. |
| `receipt_invalid` | start, intake | Receipt verifier refuses incomplete, mismatched, replayed or untrusted-source evidence; no acceptance of launch/result claim. |
| `generation_mismatch` | prepare, start, observe, stop, destroy, reconcile | Effect receiver refuses foreign/stale identity without signalling, deleting or reviving the current execution. |
| `time_authority_unavailable` | admission, prepare, start, intake | Authority verifier refuses stale/held/untrusted time; no new authority-dependent effect or result success. |
| `result_rejected` | intake | Result validator refuses unsafe, incomplete, corrupt or over-limit artifacts; no partial import, active rendering or discovery. |
| `execution_conflict` | prepare, start | Lifecycle owner refuses overlapping or unresolved execution; no second physical launch or reusable capacity claim. |
| `host_quarantined` | admission, prepare, start | Scheduler refuses externally fenced host/generation; host health text cannot clear the fence. |
| `unsupported_version` | admission, prepare, start, intake | Receiving parser refuses unknown declaration/profile/receipt/result version; no alternate-protocol retry or partial effect. |

A refusal before launch MUST leave no payload process. A refusal during result
intake MUST leave the complete result unaccepted, preserve bounded diagnostics
and retain accounted recovery obligations. Refusal does not undo permitted audit
or bounded fetch traffic; it forbids unauthorized writes, secret release and
partial published objects. A collector refusal MUST NOT authorize host reuse.

Infrastructure interruption, lost communication and uncertain process absence
are **unknown observations**, not a manufactured policy refusal or success.
They retain the original effect identity, reservations, fences and evidence.
A resource limit reached during execution is an observed bounded termination;
its result may contain diagnostics, but is not a passing build/test by default.

### Lifecycle and requester-visible outcomes

The controller MUST durably bind requester, declaration digest, execution attempt,
host/boot generation, tuple, profile, budgets and effect identities before effects.
At most one live or unresolved physical execution is allowed per admitted runner
placement generation. Different concurrent jobs require distinct qualified scopes;
a new request ID MUST NOT bypass an unknown predecessor on the same scope.

| Stage | Required action | Requester receives |
|---|---|---|
| admission | Authenticate concrete action, intersect authority/policy, reserve bounded capacity and select an exact qualified tuple | Refusal or admitted identity, immutable declaration digest and requested/available/accepted guarantee comparison |
| probe/qualify | Resolve protected current capability evidence and restrictions; no payload probing on platform hosts | Evidence references and actual support status, never an inferred qualification |
| prepare | Constrained input/image staging, digest/authority checks, full limits and pinned policies; no agent-controlled or workload code anywhere | Durable original-effect/policy-bound preparation handle or refusal/unknown; no claim that code started |
| start | Recheck authority/current tuple, apply full boundary, write protected boundary evidence and issue one physical start | Distinct boundary and start evidence, or explicit unknown/refusal |
| observe | Bounded state and budget accounting for the same attempt; no side-effectful status/resume | Running, exited, stopping or unknown with evidence freshness |
| stop | Fence all new ingress/launch/resume, stop complete scope and verify absence | Confirmed absence evidence or unknown; leader exit alone is insufficient |
| destroy | After absence, complete bounded output custody, remove residue and verify cleanup/reset | Teardown evidence; no reusable-capacity claim while unknown |
| reconcile | Resolve original journaled effects/retained objects under current fences | Updated disposition for the same execution, never a fabricated fresh success |

The approved launcher MUST enforce the start gate before entrypoint, init scripts,
image hooks, dependency tooling, plugins and any transitive interpreted input.
A restarted backend, interactive exec API or status endpoint MUST NOT create
another route to start code, bypass input fencing or supply an agent loop.

The boundary receipt MUST be durable, verified by the scheduler consumer and bound
to admission before payload release. A separate start record MUST identify whether
a physical launch actually occurred. If the release
or record is interrupted, the controller MUST observe/reconcile that same effect;
a boundary receipt alone MUST NOT imply a launched, exited or absent process.

Cancellation MUST first fence new ingress and starts, then resolve any in-flight
start and stop its complete scope within the original published stop bound.
A stale stop MUST NOT signal a newer generation.
Identical retries MUST return the original recorded outcome or remain pending;
they MUST NOT allocate another execution to make uncertainty disappear.

Under [CIP-0025 §10, EIC-10-05](CIP-0025-execution-isolation-contract.md#10-qualification-updates-and-revocation),
security-revocation detection MUST immediately fence new starts
and credential release for the affected tuple. Existing untrusted-class credential
refusal remains unconditional. The pool MUST use `B-revoke <= 300 seconds` from
security-revocation detection, including confirmation and the required quiet
period; a profile MAY require a shorter bound. A longer bound or later trigger
MUST refuse admission unless the explicit owner exception below authorizes that
exact departure. Ordinary qualification or publication of a bound is insufficient.
Retries, observer restarts, delayed publication and recovery MUST NOT reset the
original admitted deadline, including when an owner exception applies.
Affected executions MUST actually stop or, only where separately qualified,
be confirmed narrowed to a non-revoked class within
the original published revocation bound. Unconfirmed narrowing MUST lead to stop
within that same bound. Fencing or unknown state MUST NOT count as completion.
Status/list/observe/reconcile/authorized stop retain their intact-state prerequisites;
broken shared state MUST NOT create a launch, release or recovery bypass.

#### Timing baselines and explicit owner exceptions

Every pool bound or window with a corresponding CIP-0025 station baseline MUST
be equal or stricter: response/cleanup deadlines no later, quiet periods no
shorter, and validity/freshness windows no longer. Compare the exact qualified
scope and its published parameters, not merely a platform label. Where CIP-0025
sets no universal numerical value, admission MUST bind the applicable qualified
baseline and pool value; a missing required comparison MUST refuse admission,
not imply an unlimited window. Pool-only bounds still require qualification.

A looser value or later trigger MUST require an explicit, independently
authenticated owner decision naming the baseline, the exact exception (value,
units and trigger), reason/residual risk, declaration/profile/tuple and execution
scope, and its own validity interval. The decision MUST be stored in protected
policy records actually read by admission. Ordinary bound approval, qualification,
a requester acknowledgement or a blanket waiver MUST NOT substitute for it.
For a looser value or later trigger, admission MUST reject a missing, unverified,
not-yet-valid, expired or out-of-scope decision with `guarantee_unavailable`,
without allocation or payload start. Start, resume and restart MUST recheck that
decision and its bindings using current authority time; a receipt lifetime MUST
NOT extend the decision. The scheduler answer and boundary receipt MUST expose
the baseline, actual bound/window and
trigger, exception identity, scope and validity, and accepted weaker status.
They MUST NOT claim equality with the baseline. Changed bindings require new
admission, qualification and any necessary new decision; no decision may
retroactively extend an admitted deadline or reset its clock.

Such decisions change only explicitly waivable timing parameters. They MUST NOT
waive immediate detection fences, currentness/expiry or revocation checks,
non-waivable pool minimums, actual confirmation/absence/custody prerequisites,
original-effect recovery, accounting or the same-deadline fallback on failed
narrowing. They grant no station exception or station-conformance claim.

The following comparison applies at admission and qualification:

| Pool timing surface | CIP-0025 baseline | Pool result and exception limit |
|---|---|---|
| Security revocation and revocation narrowing | EIC-10-05: detection + at most 300 seconds, including quiet-period confirmation; failed narrowing stops by the same deadline | `B-revoke <= 300 seconds` from detection by default; a longer bound/later trigger needs the explicit owner decision above. Immediate fences and the original admitted deadline always hold. |
| Cancellation, limit-triggered and other bounded stop | EIC-4-04/06, TO-06/08: published original bound, full-scope absence before reuse; no universal non-revocation number | `B-stop` no longer and trigger no later than the applicable qualified baseline; looser timing needs an explicit owner decision, never an extended work ceiling. |
| Non-revocation narrowing and stop fallback | EIC-4-04: confirmed narrowing or complete stop within the same published bound | No longer/later response without an explicit owner decision; failed narrowing cannot acquire a second stop interval. |
| Stop quiet period | EIC-4-06: whole-account zero throughout the published quiet period | Pool period no shorter than the applicable qualified baseline without an explicit owner decision; no leader-only absence or confirmation after the stop/revocation deadline. |
| Receipt validity and publication | EIC-5 receipt bindings and EIC-5-02/04/06: bounded validity, current epochs, complete publication before code | Pool window no longer without an explicit owner decision; no numerical TTL is imposed by CIP-0025. Expired/stale/partial evidence still refuses; an exception cannot defer publication past code. |
| Qualification freshness and update windows | EIC-10-01/03/04/05: exact production tuple, change invalidation and immediate revocation fences | Any qualified evidence-age window no longer without an explicit owner decision; CIP-0025 gives no universal age. No grace for drift/revocation or reuse of expired evidence. |
| Operator/owner decision validity and authority time | EIC-2-05/06, EIC-5-08: current act at start/resume/restart; restore cannot revive obsolete authority | Any baseline policy window no longer without a separate explicit owner decision; neither receipt validity nor the act itself can extend its interval. Missing/currentness checks are non-waivable. |
| Recovery, retry and restore | EIC-5-07/08, EIC-10-06, TO-20/29: original effects/fences, usable authorized recovery and original applicable bounds | Clock resets remain forbidden; a later completion bound requires a prior explicit owner exception; event-only reconciliation has no invented wall-clock limit and cannot claim completion/reuse while unknown. |
| Resource/soft-response and recovery-reserve intervals | EIC-9-01/02/03, TO-19/20: published response, continuous hard caps and usable reserve under load | Applicable response bounds no longer without an explicit owner decision; no universal number. Continuous hard caps, charged debt and non-waivable pool hard limits remain in force. |
| Destroy/cache cleanup, intake and retention | EIC-9-04/05/06, TO-22/23/24: class cleanup policy, whole validation/publication and custody before deletion/reuse; cleanup bound if published | `B-destroy`, `B-intake`, retention window and `B-delete` cannot loosen an applicable qualified baseline without an explicit owner decision. No universal numerical values; pool custody/order and deletion duties remain. |
| Elapsed job lifetime | EIC-9-03: standing stations have no imposed lifetime deadline | Separate finite pool job ceiling, not a station lifetime restriction; no station numerical comparator. No retry/response allowance extends the admitted pool ceiling. |

Before activation, the lifecycle owner MUST publish and durably bind each trigger
and bound to the admitted execution: accepted cancellation or limit-triggered stop
plus `B-stop`; detection of security revocation plus `B-revoke` (or its explicit
owner-authorized trigger exception); confirmed absence and complete
custody/authorized discard plus `B-destroy`; complete bounded upload accepted for
intake plus `B-intake`; published retention expiry plus `B-delete`, with custody
or explicit disposition prerequisites preserved. Runtime/resource ceilings still
apply: a stop-response budget MUST NOT extend permitted work. Retries, restarts,
new observers or identity changes MUST NOT restart these original clocks. Actual
completion includes whole-agent-account zero over the published quiet period for
stop, verified residue removal/reset for destroy, whole publication or intended
terminal refusal for intake, and covered-copy deletion for retention. A runner
leader exit or an empty backend status MUST NOT substitute for account absence.
Unknown outcomes MUST retain fences, debt and reservations; missing a bound fails
qualification regardless of those separate safety measures. Safe custody or
reconciliation with unavailable evidence has no invented wall-clock deadline.

Output collection MUST run only at the qualified fenced/quiescent point. Before
removing execution state, the controller MUST have durable custody of the complete
bounded output and all referenced blobs outside that deletion scope, or a separately
authorized explicit discard. A digest-only receipt is not complete-content custody.
Retained debt and pending obligations MUST remain capacity-accounted and bounded.
Unreachable requesters require explicit disposition, not silent successful delivery.

Destroy MUST actually remove residue and confirm qualified cleanup/reset within
`B-destroy`; retained fences or unknown reset MUST NOT satisfy that obligation.
Host reuse requires confirmed absence, residue destruction and current qualification.
Memory, disk, swap, private caches, snapshots and admitted devices are in the
cleanup scope. Unknown reset or firmware compromise MUST quarantine the host;
fresh guest creation alone cannot clear the fence. Stop/reconcile/abuse containment
MUST remain possible while new admission is held or qualification is revoked.

Confirmed local observations rely on the qualified host TCB. A dishonest host can
lie about absence or reset. Suspected host compromise MUST trigger an externally
held fence and independently authorized rebuild/re-enrollment or retirement;
operator risk decisions MUST NOT be described as cryptographic proof of cleanup.

### Pool boundary receipt

The [CIP-0025 §5 receipt contract](CIP-0025-execution-isolation-contract.md#5-boundary-receipts-and-recovery)
is normative in addition to the pool bindings below: complete version/writer,
subject/admission/tuple, bounded validity, publication and policy/qualification/
revocation epochs, durable operation identity and fencing state MUST be bound and
checked. Expired validity or stale epochs MUST refuse even if the signature verifies.

The trusted launcher on the pool host MUST write the boundary receipt from protected
applied state, never from job assertions. The job MUST NOT write, select, replace or
access a signer for the receipt. The following are binding groups, not a wire schema:

| Binding group | Required contents |
|---|---|
| Request and authority | Authenticated requester, declaration/plan digest, execution attempt and effect identity; exact weaker-acceptance reference if present |
| Placement | Host enrollment identity, boot and placement generation, complete qualification tuple and evidence reference |
| Applied boundary | Backend/composed layers and versions, image digest, selected profile digest and actual applied policy digest |
| Capabilities | Requested IDs, actual statuses, enforced restrictions/compensations, evidence references and unsupported entries |
| Enforcement | Actual resource/time bounds and triggers; applicable timing baselines and any explicit owner exception identity, scope and validity with accepted weaker status; network/DNS policy and independent containment references, identity/device mapping and input-root policy |
| Freshness and provenance | Protected operation ordering, authority-time evidence and receipt version/integrity identity bound to this attempt |

The scheduler's receipt consumer MUST obtain it through the protected host-control
path, verify reporting identity/integrity, exact bindings, current qualification,
revocation, time, replay state and comparison with its admitted plan. The result
consumer MUST independently check the same execution binding before publishing.
Neither consumer may trust a job-provided receipt file or URL as the source.

The reporting mechanism MUST be pool-specific and incapable of authorizing platform
services, broker leases, registrar enrollment or station signatures. Public trust
roots may be installed on hosts; platform private keys or tokens MUST NOT be there.
The enrollment/reporting-key/gateway design is an activation question, not permission
to copy an existing platform credential to make delivery work.

A receipt is a **host claim, not attestation**. Integrity verification proves who
reported which bytes, not that a compromised host applied the claimed policy,
ran honest code or destroyed residue. Consumers MUST preserve the host-reported
evidence level. Hardware attestation would need a separate approved protocol and
measurement argument; this CIP supplies neither that capability nor an equivalent.

### Input, image and dependency interpretation

The [interpretation inventory](#interpretation-inventory) below is normative for
coverage. Prefer passing bounded opaque bytes to a runner and parsing them after the boundary is applied.
Every unavoidable outside interpreter MUST have a named enforcing service, closed
format/schema, caps and qualification evidence; no undeclared host helper is allowed.

Materializers MUST validate paths/types without following hostile links, refuse
root escapes, ambiguous/colliding names, unsupported links/devices and expansion
excesses, and stage under a private constrained root. Complete validation precedes
atomic publication; refusal/interruption MUST NOT publish partial input, modify
unrelated paths, start payload code or activate ambient hooks/discovery.
Image/layer assembly, dependency transfer metadata, logs/telemetry, recovery paths
and result unpacking are covered, not only the final result importer.

Job-controlled package resolution/install hooks MUST run inside the runner.
Proxies MAY interpret only admitted destination/protocol metadata and opaque blob
identities under TC-10/TC-11/TC-25; they MUST NOT run a host package manager for
the job. Shared caches MUST be immutable, authorized and digest-verified; writable
caches MUST be private and destroyed between executions.

Every runtime-resolved/fetched dependency, including transitive acquisitions,
MUST enter the result's complete input manifest with resolved identity, exact byte
digest and resolution metadata bound to the attempt. An allowed name/endpoint
alone is not provenance. Missing provenance forbids a successful verified-result
claim; the consumer MAY retain explicitly incomplete bounded diagnostics.
The manifest remains host-reported unless independently verified; it does not
prove dependency safety or that a dishonest host consumed the recorded bytes.

### Results and intake path

All logs, exit statuses, telemetry, artifacts, file names and reports are untrusted
data. The approved collector MUST emit a bounded result tied to the exact requester,
declaration/input/dependency/image/profile/tuple/attempt identities, output digests,
execution observations, receipt references and evidence level. Success of transport,
validation or process exit MUST NOT be presented as semantic test correctness.

The return path MUST be: authenticated scoped upload → bounded quarantine → whole
object/digest/type/path/provenance validation → atomic publication → authorized
requester retrieval. Each consumer MUST retain its own current authorization and
size/work budgets. Content addressing MUST NOT grant read access or enumeration.

The contract MUST publish per-object/count/total/expanded-size and parsing-depth
limits, accepted file types and retention units before activation. Collectors MUST
bound work while reading, refuse unsafe paths and unsupported devices/links, and
never follow job-controlled links or materialize job-controlled Git administration.
No partial import or truncation may masquerade as a complete accepted result.
Accepted complete bounded uploads MUST reach whole publication or an intended
terminal refusal within the original `B-intake`; valid positives MUST publish.

A trusted consumer MUST NOT execute returned binaries, evaluate repository config,
load instructions/plugins/hooks, source shell text or render active markup. Review
uses inert resources outside discovery roots; entering a candidate tree needs the
separately qualified strict-context adapter required by dispatcher review rules.
Any execution of returned code requires another independently admitted pool job.

Retention services MUST actually remove all covered artifact/log/backup copies
within the published B-delete after eligible retention expiry and retain deletion
evidence. Denied retrieval alone MUST NOT prove deletion. Pending custody requires
its published accounted disposition; expiry MUST NOT silently waive that obligation.

Requester delivery MUST include actual guarantees/compensations, host-reported
limits, input/dependency provenance, complete artifacts or explicit incomplete/
refused/unknown disposition, and separate process/teardown states. A signed pass
MUST NOT trigger automatic integration or satisfy an independent-verification
requirement. Transport delivery is not authenticated import acknowledgement.

## Security considerations

The [Threat catalogue](#threat-catalogue) is the security baseline for this CIP. Controls
MUST be enforced by the services identified below and qualified for their exact
production configuration. No operator acceptance can relax immutable boundaries.

| Threat group | Required enforcement and limitation |
|---|---|
| TM-ISO-01, TM-ISO-02 | TC-01, TC-02, TC-03, TC-09: dedicated machines, minimal backend interfaces, no host sockets or platform authority; unknown escape vulnerabilities remain. |
| TM-DATA-01, TM-DATA-02, TM-DATA-03 | TC-04, TC-05, TC-06, TC-22: verified teardown, private writable caches, immutable shared objects and qualified device reset; no device admission on unverified reset. |
| TM-DATA-04, TM-DATA-05 | TC-12, TC-21, TC-25: store authorization plus safe bounded outside interpretation; an authorized digest does not establish safe paths or code. |
| TM-SIDE-01 | TC-07, TC-21: approved co-tenancy and disclosed leakage; advanced side-channel elimination is absent. |
| TM-CRED-01, TM-CRED-02, TM-CRED-03 | TC-01, TC-08, TC-09: no platform secrets, injected credentials or borrowed station identity; undeclared sensitive input cannot be reliably discovered. |
| TM-NET-01, TM-NET-02, TM-NET-03 | TC-10, TC-11, TC-12: independent upstream containment, controlled DNS/destinations, authenticated transfer and no unsolicited ingress; allowed channels still carry data. |
| TM-SUP-01, TM-SUP-02 | TC-13, TC-14, TC-23: approved pins, externally held compromise fence and independent re-enrollment; runner recreation does not remove firmware compromise. |
| TM-RES-01, TM-RES-02, TM-RES-03 | TC-15, TC-16, TC-17: exact provenance, inert bounded intake and honest evidence levels; a dishonest host can forge computation and host-signed reports. |
| TM-TIME-01 | TC-18: external authority time, rollback protection and elapsed budgets; guest clocks cannot renew authority. |
| TM-DOS-01, TM-DOS-02 | TC-19, TC-20: hard bounds and protected recovery capacity; global abuse/Sybil campaigns still need admission and operator response. |
| TM-AUTH-01, TM-AUTH-02 | TC-21 and existing consumers: recorded class, concrete action/target, current attenuated authority; documents and transport are never authority. |
| TM-LIFE-01 | TC-22: one unresolved effect, durable fencing and complete-content custody; unknown is never absence. |
| TM-QUAL-01, TM-QUAL-02 | TC-23: independent scoped evidence, freshness/revocation and change invalidation; self-reported health is not qualification. |
| TM-OPS-01 | TC-24: disclosed administrative access, retrieval authorization, retention/deletion; no secrecy against host/platform operators. |

Hardware/firmware, host kernel, backend/VMM, launcher, image verification, constrained
interpreters and cleanup remain the local TCB. External gateways, store authorization,
qualification, signing verification, time and upstream enforcement protect the
platform against a dishonest host. A weakened host cannot certify those external
properties by signing more reports.

Physical attacks, malicious manufacture and advanced hardware side channels are
outside the initial guarantee. Unknown exploits, semantic dependency malice,
deceptive results and outages remain residual risks. Independent checks improve
only their documented scope; identically compromised replicas are not independent.
A weaker policy MUST NOT be marketed or returned as equal to a stronger one.

## Compatibility and migration

The new pool class MUST NOT widen station/workplace execution, network or broker
rights. Platform-host builds/tests remain forbidden by R-VERIFY; the initial
untrusted-class refusal and existing R-EXEC/R-SHARED gates remain effective.
Trusted-circle membership, a pool submission grant or available CPU is not a
station reviewer role, local agent-loop right or broker credential authority.

Existing module carriers remain closed. The proposal MUST use reviewed versioned
adapters rather than append members, reinterpret guest UID as host identity or
fall back between signature protocols. Old clients MUST refuse unsupported new
versions, not silently select a less restrictive policy.

Rollout MUST start with service/admission defaults disabled. Enabling one exact
qualified tuple MUST NOT enable an OS, backend family, composed topology or sharing
class generally. Changes to enforced properties invalidate affected qualification;
stop/observe/reconcile remain supported during admission holds and rollback.
No migration may transfer platform secrets or identities onto pool machines.

## Specification changes

The following are proposed normative changes, not live API amendments:

1. Add this numbered CIP to the public specification index at review time.
   Use the normative CIP-0025 references and reviewed pool additions above.
2. Maintain this mapping to the pinned station parity vocabulary and the separate
   pool-local definitions. Preserve semantic differences and per-property evidence;
   do not derive status from one overall OS/backend label or message-assurance rank.
3. Publish versioned job/admission/receipt/result and effect/reconciliation carriers,
   refusal mappings and guarantee-acceptance acts. Pin authority protocol and
   operator/requester identity bindings before enabling any action.
4. Bind dispatcher off-host verification to the pool service without altering
   platform-host job classes, broker R-UNTRUSTED or native peer-UID semantics.
5. Publish runner-host and admission/qualification rules implementing every
   referenced control, numerical cap, data retention and compromise fence.
6. Register every external interpreter and its tests in this CIP's interpretation
   inventory; update this catalogue/inventory and the separately maintained full
   model before admitting a new host-side interpretation surface.

No backend product is selected here. Backend evaluation MUST explain its TCB,
restrictions and exact tuple evidence, including any composed virtualization.
The CIP MUST NOT infer backend properties from packaging, names or benchmarks.

## Implementation plan

Each leaf MUST produce specification and narrowly scoped conformance evidence;
no deployment is authorized by this plan. Sizes indicate dependency scope, not
commitments of elapsed time.

| Order | Leaf and relative size | Deliverable and gate |
|---|---|---|
| 1 | Shared definitions and vocabulary, small | EIC owner decision, reviewed shared/local mapping and approved guarantee IDs |
| 2 | Authority and data carriers, medium | Closed schemas, refusal semantics, signing/reporting separation and deterministic vectors |
| 3 | Admission and qualification, medium | Current tuple/evidence registry, per-guarantee comparison, explicit weaker acceptance and revocation fences |
| 4 | Host adapter and preparation, large | Production entry with apply-before-code, constrained interpreters, lifecycle journal, hard caps and host isolation |
| 5 | Transfer and result consumer, medium | Scoped opaque input transfer, complete provenance, bounded inert intake, durable custody and authorized retrieval |
| 6 | Exact-tuple qualification, large | Paired negative/positive cases, independent review, production-entry evidence and compromise/recovery procedures |
| 7 | Restricted pilot, medium | Explicit operator decisions, disabled unsupported classes, narrow activation and rollback/stop evidence |

An upstream dependency remaining unpublished MUST remain an activation gate.
Implementation MUST NOT invent stubs, mock-only authority or compensating flags
that present an unsupported platform contract as implemented.

## Test plan

The cases below are requirements for qualification on **pool test machines**.
Nothing in this plan runs hostile code or qualification workloads on a platform
agent host. Structural checks of this proposal are separate documentary evidence.

Each case MUST run through the exact production service and sandbox properties:
service account, groups, unit hardening, namespaces, mounts, descriptors, working
directory, environment, policy digests and resource controls. An interactive-shell
pass MUST NOT substitute for production-entry evidence. Qualified platform and
architecture must match the tuple; a simulation MUST state its unverified limits.

Negative cases come first; each nearby positive control MUST pass under the same
relevant policy. Tests MUST assert intended refusal/invariants and post-failure
state, not accept any exception, crash or timeout. Destructive cases MUST use
isolated fixtures and synthetic data, never live secrets or uncontrolled targets.
Every enforced gate MUST be checked with a bounded known-violation control where
applicable; weakening a gate must fail the named case, not a setup accident.

### Completion obligations

Completion and failure safety have separate verdicts. Fenced, unknown, contained,
refused or capacity-reserved state cannot satisfy actual completion. Missing an
applicable original bound fails qualification even if all safety checks pass;
fences, custody and accounting remain required after that failure. A bounded
positive actually completes, including any required quiet period, not merely
reports that stopping or cleanup is possible. Permanent refusal cannot pass it.

The following inventory groups every completion/order obligation in the normative
text and operation tables. Source names refer to the corresponding Design
subsections; FX cases also include their listed `CW` subcases. Each `CM` drops
only the named enforcement on the stuck/unknown branch while preserving normal
success and fences; the named witness has to fail for that precise omission.
Each positive includes normal completion and a transient-unknown/stalled variant
resolved within the same original bound. All remain future pool-machine tests.

`B-stop`, `B-revoke`, `B-destroy`, `B-intake` and `B-delete` are the published
class bounds defined under Lifecycle. Their trigger is never a later retry or
observer restart. `E` is the named dependent event, not an invented time deadline;
`I` is the entire stated interval. Event-only custody/reconciliation may stay
unknown and accounted until intact evidence or authorized disposition exists;
it cannot claim completion or release capacity. Timed operations still fail when
their deadlines pass in that state. Missing required bounds keep activation closed.

| ID; source and cases | Trigger and original bound; actual observable | Named stuck/unknown witness | Narrowing control | Positive completion control |
|---|---|---|---|---|
| CO-01; declaration, placement, refusals; FX-09/21/23 | Before E=allocation/start: authority, exact tuple/profile, immutable declaration, limits and qualification fully checked | CW-01-admission-pending: incomplete checks yet allocated | CM-01: skip pending-path admission completion | Valid admitted exact tuple after all checks; delayed evidence resolves before E |
| CO-02; placement; FX-25 | Before E=weaker admission/reply: exact acceptance and requested/actual comparison retained in receipt/answer | CW-02-disclosure-unknown: acceptance or disclosure still missing at E | CM-02: omit unknown-path acceptance/disclosure | Actual reduction visibly recorded before E, including delayed acceptance |
| CO-03; preparation/interpretation; FX-06/13 | Before E=input publication/code: complete bounded validation and immutable approved image/input pin; no external hooks | CW-03-validation-stuck: partial input published | CM-03: skip stuck-path validation/publication ordering | Benign input fully publishes after validation; transient interruption resolves first |
| CO-04; start/receipt; FX-26 | Before E=first payload instruction: complete boundary applied, receipt durable/verified and bound to admission | CW-04-publication-pending: code runs with incomplete receipt/application | CM-04: omit pending-path apply/publish/verify gate | Actual durable receipt and applied boundary precede code, including delayed publication |
| CO-05; lifecycle; FX-22/26 | Before E=physical-start claim/replacement: separate original start evidence resolves effect identity | CW-05-start-unknown: receipt alone counted as physical start | CM-05: skip unknown-path original-effect resolution | Correct original start observation before claim; interrupted record reconciles without second start |
| CO-06; cancellation; FX-19/22 | Accepted cancellation + B-stop: resolve in-flight start, whole-account stop and quiet-period confirmation | CW-06-cancel-stuck: fenced cancelled job remains live past bound | CM-06: drop stuck-path cancellation deadline | Actual complete stop by original bound; transient unknown resolves in time |
| CO-07; runtime/resources; FX-18/19 | Runtime/resource-limit trigger + B-stop, without extending execution ceiling: actual bounded termination/absence | CW-07-expiry-unknown: expired job remains live while fenced | CM-07: omit unknown-path elapsed/stop enforcement | Enforced ceiling and confirmed stop in time, including delayed observation within bound |
| CO-08; revocation; FX-14/23 | At detection: immediate start/release fence; default detection + B-revoke with B-revoke <= 300 seconds: actual stop or confirmed qualified non-revoked narrowing, including quiet period; longer/later requires the explicit owner exception at admission; no clock reset | CW-08-revoked-unknown: original revoked execution survives admitted deadline; RevocationExceptionRequired rejects a longer/later profile without the decision | CM-08: drop stuck-path deadline enforcement; separately OwnerExceptionOnlyRemoved skips only the explicit-exception gate | Actual stop/narrowing by original deadline, including transient unknown; RevocationBaselineAllowed and RevocationExceptionAllowed admit the baseline and valid explicitly excepted profiles |
| CO-09; stop; FX-19/22 | Every bounded stop trigger + B-stop: whole-account zero throughout quiet period, including detached/OS-spawned work | CW-09-child-unknown: leader exits but descendant survives deadline | CM-09: omit unknown-path full-scope completion | All processes absent and quiet confirmation by bound; escaped child actually stops first |
| CO-10; network; FX-10/11/12 | Before E=next network effect after policy/proxy/authority failure: actual route closure or valid enforced policy | CW-10-proxy-pending: packet escapes while closure is pending | CM-10: skip pending-path fail-closed enforcement | Allowed transfer completes; failure closes route before E and restored policy admits valid traffic |
| CO-11; destroy/reuse; FX-03/05/22 | Confirmed absence plus custody/discard prerequisites + B-destroy; before E=reuse: actual residue removal and verified reset | CW-11-destroy-stuck: residue persists but destroy reports success | CM-11: drop stuck-path cleanup/reset completion | Actual disk/memory/snapshot/device cleanup completes by bound before fresh work, including transient reset delay |
| CO-12; private caches; FX-03/04 | Same B-destroy; before E=next execution: private writable cache actually destroyed; shared objects stay immutable | CW-12-cache-unknown: prior private cache survives into successor | CM-12: omit unknown-path cache destruction | Cache removed in time; authorized immutable shared object and new private cache still work |
| CO-13; custody; FX-15/22 | Before E=execution/source deletion: complete retrievable bytes outside deletion scope or exact authorized discard | CW-13-custody-pending: missing blob marked unknown then source removed | CM-13: skip pending-path complete-content prerequisite | Every blob durably retrievable before E or exact discard recorded; delayed transfer resolves first |
| CO-14; result intake; FX-15/16/20 | Complete bounded upload accepted for intake + B-intake: actual whole valid publication or intended terminal refusal without partial import | CW-14-intake-stuck: valid complete object remains fenced/unknown past bound | CM-14: omit stuck-path intake completion | Valid result wholly publishes by bound; transient validation delay resolves in time; invalid sibling refuses safely |
| CO-15; provenance/delivery; FX-15/17/26 | Before E=success/retrieval: exact request/input/dependency/attempt/receipt binding, full artifacts or explicit incomplete disposition and honest evidence level | CW-15-manifest-pending: success before dependency or blob provenance complete | CM-15: skip pending-path manifest/evidence completion | Whole current result retrieved once after checks; delayed provenance resolves before E |
| CO-16; recovery reserve; FX-19/20 | I=saturation interval; applicable original stop/revoke bound: reserve actually usable and recovery action completes | CW-16-reserve-starved: nominal reserve but actual stop misses deadline under load | CM-16: omit stuck-work recovery reserve enforcement | Measured recovery completes within original bound under saturation and transient unknown |
| CO-17; quotas/accounting; FX-18/19/20/22 | Before E=further allocation and throughout I=retained lifecycle: charge principal/global debt without identity/reboot reset | CW-17-accounting-pending: new ID starts before old debt charged | CM-17: skip pending-path retained-debt accounting | Valid work within aggregate budgets continues after delayed accounting; reserve remains accessible |
| CO-18; authority/time; FX-09/18/26 | Before E=authority-dependent effect: current external time/revocation/bindings checked; original deadlines retained across restart | CW-18-time-unknown: stale sample or retry resets deadline | CM-18: omit unknown-path currentness/original-clock check | Fresh authorized effect completes before original expiry; delayed current evidence does not extend it |
| CO-19; update/quarantine; FX-13/14/23 | Before E=next start: changed/revoked tuple invalidated; reviewed exact requalification/re-enrollment before reopening | CW-19-requalify-pending: old evidence authorizes changed tuple | CM-19: skip pending-path invalidation/requalification | New tuple runs only after complete independent checks; delayed rebuild never self-clears fence |
| CO-20; retention; FX-24 | Published retention expiry + B-delete after custody/disposition prerequisites: actual covered artifact/log/backup deletion and evidence | CW-20-delete-unknown: access refused but covered bytes remain after deadline | CM-20: omit unknown-path retention deletion enforcement | Actual covered copies removed by bound; authorized pre-expiry retrieval works; transient deletion delay resolves in time |
| CO-21; retries/recovery; FX-22/23 | Before E=completed disposition/resume/replacement: original intact journal/effect evidence; authorized recovery works under intact prerequisites | CW-21-reconcile-unknown: blanket refusal or fabricated completion replaces original evidence | CM-21: omit unknown-path original-effect reconciliation | Actual original effect resolves before E without duplicates; delayed intact evidence permits authorized continuation |
| CO-22; activation/qualification; FX-21/23/25 | Before E=pilot or broadened admission: complete carriers, limits, current production-entry paired evidence and required operator decisions | CW-22-qualification-pending: incomplete evidence or unresolved mandatory choice counted as qualified | CM-22: skip pending-path evidence/activation completion | Only exact reviewed tuple activates after complete checks, including delayed evidence; no backend-family inference |

### Guarantee properties and observables

Each row below defines a mandatory direct-observable subcase of the listed FX
cases. It checks the property itself, independently of side effects used for
other guarantees. An unchanged canary is not confidentiality; refusal of retrieval
is not deletion; spare capacity is not completed recovery. The existing valid
positive for each FX case exercises the same service/scope. For a deliberately
unavailable property the test proves refusal and honest reporting only; it never
qualifies that property. All markers/canaries are synthetic pool-test fixtures.

| Guarantee ID | Property class | Required negative observable | Cases and valid control |
|---|---|---|---|
| `isolation.read` | Confidentiality | PR-01: unrelated host and live-neighbour reads denied; neither marker in any returned bytes/logs/artifacts, independently of writes | FX-01; permitted own-input bytes returned exactly |
| `pool.isolation.write` | Integrity | PR-02: protected host/live-neighbour bytes and metadata unchanged under forbidden writes | FX-01; permitted own-output writes succeed |
| `ipc.isolation`, `execution.descriptors` | Interface isolation and authority | PR-03: actual inherited-handle/namespace inventory contains no undeclared interface; forbidden connects/handle use denied with no response or service effect | FX-02; declared guest I/O works |
| `pool.isolation.residue` | Confidentiality and cleanup completion | PR-04: prior disk/memory/cache/snapshot markers absent from next execution; actual removal/reset confirmed, not merely no reuse | FX-03/04/05/22; fresh own data works after timely cleanup |
| `pool.isolation.exclusive` | Concurrency isolation | PR-05: actual admitted physical/layer scope has no overlapping foreign execution throughout allocation, including simultaneous admissions | FX-05/07; one exclusive job or explicitly compatible shared jobs run only in their own class |
| `pool.isolation.side-channel` | Confidentiality, intentionally absent | PR-06: no elimination qualification exists; requirement refuses and every platform status stays absent, never inferred from exclusivity | FX-07/25; explicit reduced requirement retains disclosed residual leakage; no elimination claim |
| `network.egress` | Network confinement | PR-07: trusted outer capture sees no denied DNS/address/protocol/destination traffic, even on proxy failure; traffic counters stay bounded | FX-10/11; admitted transfer reaches only allowed fixture |
| `pool.network.ingress` | Network confinement and authorization | PR-08: unsolicited/wrong-source traffic establishes no job connection or accepted control transfer | FX-12; authenticated scoped transfer actually completes |
| `pool.credential.absent` | Confidentiality and authority absence | PR-09: launch inventory has no forbidden synthetic credential in files/environment/handles; broker records zero pool binding/issue/renew effects | FX-08; secret-free job starts without broker client |
| `pool.identity.separated` | Authentication and authority | PR-10: guest/forwarded UID yields no host peer identity, signer response or authorized platform effect | FX-02/09; exact authorized native fixture retains only its own rights |
| `process.stop` | Completion and availability | PR-11: whole-account process inventory reaches zero over quiet period by original bound, including escaped/OS-spawned work | FX-19/22; actual timely stop, including transient unknown |
| `limit.cpu`, `pool.limit.elapsed-work` | Resource boundedness | PR-12: trusted aggregate CPU rate, cumulative CPU-time and elapsed-work observations never exceed admitted ceilings; limit-triggered stop actually completes within its response bound | FX-18/19; within-budget work completes and correct unused budget remains |
| `limit.memory` | Resource boundedness and recovery availability | PR-13: trusted peak charged memory stays within hard ceiling; actual reserved recovery completes under memory saturation | FX-19/20; within-memory work and timely saturated recovery succeed |
| `limit.disk`, `limit.io`, `pool.limit.storage` | Resource boundedness and accounting | PR-14: trusted byte/inode/I/O/retained-debt counters stay within caps across retry and identity changes | FX-19/20/22; valid storage work succeeds without resetting prior debt |
| `pool.limit.output` | Resource boundedness and intake integrity | PR-15: actual log/artifact bytes/count/expansion/parser-work observations stay within caps; no partial result is called whole | FX-06/16/20; valid bounded whole result actually publishes |
| `pool.time.authority` | Freshness and rollback resistance | PR-16: accepted authority never outlives current external validity; original expiry/budget remains unchanged after clock/reboot/retry changes | FX-09/18; fresh exact authority permits only its original budget |
| `pool.input.integrity` | Integrity and access authorization | PR-17: actual materialized bytes match approved input/image digests; unauthorized digest request yields no content | FX-04/12/13; authorized exact approved bytes materialize |
| `pool.input.interpretation` | Interpretation confinement and integrity | PR-18: every external interpreter records no outside-root write, partial publication, hook execution or discovery on invalid input | FX-06; benign bundle fully materializes within root or stays opaque |
| `pool.result.provenance` | Binding integrity and evidence honesty | PR-19: accepted result matches exact request/input/dependency/attempt/output identities; missing dependency or mismatched bytes cannot become verified success | FX-15/17/26; complete manifest and blobs publish once as host-reported evidence |
| `pool.result.inert` | Non-execution and interpretation confinement | PR-20: trusted execution/discovery/render activation observations stay zero throughout import/review, including telemetry | FX-06/16; inert artifact/text remains inspectable as data |
| `pool.journal.durable` | Crash consistency and effect uniqueness | PR-21: crash/restore observations retain original effect identity, at most one physical start, and every blob obligation; no fabricated completion | FX-22; intact original effect actually reconciles without a second start |
| `pool.control.bounded` | Availability and resource boundedness | PR-22: under bounded hostile load, trusted queue/work/debt remain capped AND actual independent valid request/stop/revoke completes by its applicable original bound | FX-19/20; other principal completes valid work during saturation |
| `update.requalified`, `qualification.revocation` | Freshness and revocation completion | PR-23: no actual new start consumes changed/revoked qualification; active revoked work actually stops/qualified-narrows by B-revoke | FX-13/14/23; only exact reviewed new tuple starts after full evidence |

The read-denial narrowing in FX-01 leaves write denial intact. It therefore has
to fail PR-01 even though PR-02 and ordinary own-input/output controls still pass.
Likewise no property can borrow another row's side-effect oracle or unavailable
status to claim coverage. These are documentary coverage requirements; backend
qualification has to implement and exercise the actual independent observations.

#### FX-01 — Backend boundary

- Threats: TM-ISO-01, TM-DATA-04; controls: TC-02, TC-03, TC-13, TC-21.
- Negative: named ReadHostDenied and ReadLiveNeighbourDenied fixtures use distinct
  synthetic markers in unrelated host data and a live neighbour's data. Direct
  paths, qualified mount/link routes and inherited descriptors all deny reads;
  neither marker appears in returned bytes/logs/artifacts (PR-01). Separately,
  forbidden writes leave protected host/live-neighbour bytes/metadata unchanged
  (PR-02). Unsupported isolation refuses before payload release.
- Positive: own-input reads return the exact permitted bytes and own-output writes
  succeed in the same profile, with both unrelated domains still inaccessible.
- Narrowing control: ReadDenialOnlyRemoved keeps write denial, normal own-input
  reads/output and canary integrity, but removes unrelated read denial. The named
  read cases fail for denied-read/disclosure assertions even without any write;
  an unchanged canary cannot kill this control.

#### FX-02 — Host services and handles

- Threats: TM-ISO-02, TM-CRED-03; controls: TC-03, TC-09.
- Negative: host sockets, inherited handles and guest-UID impersonation cannot
  yield a host service effect, signer response or registrar identity.
- Positive: admitted guest I/O works; a separately authorized native peer fixture
  retains only its own service rights.

#### FX-03 — Sequential residue

- Threats: TM-DATA-01; controls: TC-04, TC-22.
- Negative: later jobs cannot read seeded disk/memory/snapshot markers; interrupted
  cleanup prohibits reuse rather than returning a success receipt.
- Positive: verified teardown permits a fresh job; prior results remain separately
  retrievable only by their authorized requester.

#### FX-04 — Cache and store scope

- Threats: TM-DATA-02, TM-DATA-04; controls: TC-05, TC-12, TC-21.
- Negative: unauthorized digest lookup, shared-cache write and substituted bytes
  refuse without mutation or disclosure.
- Positive: authorized exact immutable input and private writable cache work.

#### FX-05 — Devices and composed topology

- Threats: TM-DATA-03, TM-SIDE-01; controls: TC-06, TC-07, TC-23.
- Negative: unqualified reset/DMA or unknown outer co-tenancy refuses; an
  interrupted device reset cannot release capacity or inherit exclusive evidence.
- Positive: the device-free qualified tuple runs; any device/composed variant
  passes only its independently qualified reset and topology case.

#### FX-06 — External interpretation

- Threats: TM-DATA-05; controls: TC-25.
- Negative: authorized digest-matching bundles with unsafe paths/types, escaping
  links, devices, collisions or expansion excess refuse in each applicable
  interpreter; no outside-root write, partial publication or payload launch.
- Positive: the adjacent supported benign bundle publishes wholly within its root;
  opaque mode passes identical bytes and host observation sees no content parser.

#### FX-07 — Sharing admission

- Threats: TM-SIDE-01; controls: TC-07, TC-21.
- Negative: incompatible exclusivity/sensitivity requests cannot co-schedule even
  under simultaneous admission; side-channel elimination is never reported `present`.
- Positive: compatible non-sensitive jobs run only in the approved sharing class.

#### FX-08 — Credential absence

- Threats: TM-CRED-01, TM-CRED-02; controls: TC-01, TC-08.
- Negative: synthetic platform-token injection, secret-bearing declarations and
  untrusted bind/issue/renew requests refuse without release or payload start.
- Positive: secret-free input/image execution works without a broker client.

#### FX-09 — Identity and action authority

- Threats: TM-CRED-03, TM-AUTH-02; controls: TC-09, TC-21.
- Negative: validly signed wrong-action/audience/target, widened delegation and
  job-selected protocol cannot authorize any concrete service effect.
- Positive: the fresh exact authorized action passes under the protected protocol.

#### FX-10 — Egress and abuse bounds

- Threats: TM-NET-01; controls: TC-10, TC-19, TC-20.
- Negative: denied traffic and proxy-failure fallback cannot leave; a controlled
  compromised-host fixture cannot bypass independent upstream containment.
- Positive: one pinned allowed dependency transfer succeeds within its budget.

#### FX-11 — DNS and destination rechecks

- Threats: TM-NET-02; controls: TC-11, TC-12.
- Negative: controlled rebinding, redirects, alternate resolvers and address-family
  variants cannot reach private, metadata, loopback or platform fixtures.
- Positive: DNS/redirect chains wholly within admitted policy complete.

#### FX-12 — Transfer integrity and ingress

- Threats: TM-NET-03; controls: TC-12, TC-15.
- Negative: altered inputs/results, wrong endpoint identity, replayed launch and
  unsolicited ingress refuse without a second launch or protected data release.
- Positive: fresh authorized exact transfer succeeds; identical retry is idempotent.

#### FX-13 — Supply chain

- Threats: TM-SUP-01; controls: TC-13, TC-25.
- Negative: changed bytes behind a tag, unapproved layer/backend/profile and
  revoked rollback refuse before payload or job-controlled host hook execution.
- Positive: approved exact digests launch, with package hooks inside the runner.

#### FX-14 — Compromise fence

- Threats: TM-SUP-02, TM-QUAL-02; controls: TC-14, TC-23.
- Negative: a host-reported healthy state or fresh guest cannot clear an external
  compromise/revocation fence or substitute old qualification after restore.
- Positive: independently authorized rebuild/re-enrollment admits only the new tuple.

#### FX-15 — Result provenance and dependencies

- Threats: TM-RES-01; controls: TC-15.
- Negative: change one request/input/attempt/generation/output binding or omit a
  runtime dependency; no verified success. Changed bytes at the same allowed
  dependency name produce a different manifest/input identity.
- Positive: complete current provenance and exact bounded blobs publish once;
  an identical authorized retry returns the original disposition.

#### FX-16 — Inert result and telemetry consumers

- Threats: TM-RES-02, TM-DATA-05; controls: TC-16, TC-25.
- Negative: unsafe paths/types, hooks, active markup and instruction-like log text
  cannot execute, trigger discovery, escape quarantine or partially import.
- Positive: bounded inert artifacts and harmless instruction-looking text can be
  inspected as data with no authority change.

#### FX-17 — Host report is not truth

- Threats: TM-RES-03, TM-QUAL-01; controls: TC-17, TC-23.
- Negative: a valid fixture host signature over a false pass cannot satisfy an
  independent-verification/attestation requirement or self-qualify its host.
- Positive: the report is retained only as host-reported evidence; separately
  obtained independent evidence supports its specifically stated claim.

#### FX-18 — Time and continuity

- Threats: TM-TIME-01; controls: TC-18.
- Negative: guest/host clock changes, stale authority samples and rebooted elapsed
  state cannot revive expiry, extend budgets or make old results current.
- Positive: a fresh authorized job obeys elapsed bounds; stop remains available
  during an admission time hold.

#### FX-19 — Host resource pressure

- Threats: TM-DOS-01; controls: TC-19, TC-22.
- Negative: bounded CPU/process/memory/disk/I/O pressure is measured against
  the admitted ceilings. CW-06/07/09/16 require actual whole-account stop and
  quiet-period confirmation by the original applicable bound under saturation;
  fenced/unknown scope without timely completion fails qualification.
- Positive: within-budget work completes, and actual stop/recovery completes by
  the same bound under load, including transient unknown resolved in time.
- Narrowing control: CM-06/07/09/16 remove only stuck-path completion/deadline
  enforcement, retaining normal work, fences and nominal reserve; the cases fail.

#### FX-20 — Control-plane resource pressure

- Threats: TM-DOS-02; controls: TC-20.
- Negative: bounded repeated/oversized/deep/expanding submissions produce
  intended quota/schema refusal with measured bounded parsing work, debt and no
  partial import. CW-14/16 require actual valid intake/recovery completion by the
  applicable original bound under load, not nominal capacity or an unknown reply.
- Positive: another admitted principal's valid result actually publishes within
  B-intake; protected stop/revoke completes within its own bound even after a
  transient unknown/stall. Rejected siblings retain separate safe-failure checks.
- Narrowing control: CM-14/16 drop completion only on the stuck branch while
  retaining normal success/refusal and fences; their named witnesses fail.

#### FX-21 — Declaration and class intersection

- Threats: TM-AUTH-01; controls: TC-08, TC-21, TC-23.
- Negative: caller-selected trust class, host paths, credentials, unpublished device
  or unsupported capability refuses without placement or fallback.
- Positive: the exact recorded untrusted class runs only on a qualified pool tuple;
  platform-host slice-0 refusal remains unchanged.

#### FX-22 — Lifecycle races and custody

- Threats: TM-LIFE-01; controls: TC-04, TC-15, TC-22.
- Negative: interrupted launch/cancel/stop/export with concurrent retries cannot
  cause another physical start, stale signal, premature deletion/reuse or a complete
  result claim before every blob has custody. CW-06/09/11/12 require actual stop,
  quiet-period zero and residue/cache reset by their original applicable bounds;
  CW-13/21 require intact original evidence before deletion/completion, never
  fenced/unknown substituted for those observations.
- Positive: original effects reconcile without duplicate work; transient unknown
  stop/destroy resolves within the original bounds. Confirmed absence, actual
  cleanup and full custody permit new admitted work. Delayed event-only custody
  completes before deletion; no arbitrary reconciliation timeout is imposed.
- Narrowing control: CM-06/09/11/12/13/21 skip the corresponding completion only
  while stuck/unknown, keeping normal success and fences; named witnesses fail.

#### FX-23 — Qualification and updates

- Threats: TM-QUAL-01, TM-QUAL-02; controls: TC-13, TC-23.
- Negative: self-asserted, borrowed, expired/revoked or changed-tuple evidence
  refuses new start. CW-08 requires immediate start/release fencing AND actual
  whole-account stop or confirmed qualified non-revoked narrowing by the original
  B-revoke. A live revoked execution past that deadline fails qualification even
  if fenced/unknown. CW-19/22 forbid reopening before complete independent evidence.
- Negative, RevocationExceptionRequired: an ordinarily approved `B-revoke = 600
  seconds` without an explicit owner decision MUST refuse at admission with
  `guarantee_unavailable`, no allocation/start and no admitted receipt; promising
  completion at detection + 500 seconds cannot rescue admission. Independently
  test a later trigger with no decision. Keep qualification and all other gates
  valid so they cannot mask this refusal. InvalidDecision variants use missing
  scope, wrong tuple, unverified, expired and not-yet-valid decisions; none may
  authorize admission, start, resume or restart.
- Positive: independently reviewed current evidence enables only its exact scope;
  RevocationBaselineAllowed admits both `B-revoke = 300 seconds` and a shorter
  bound, then actually confirms whole-account stop including quiet period, or
  qualified non-revoked narrowing, by the original detection + bound (including
  exactly at 300 seconds). RevocationExceptionAllowed
  admits `B-revoke = 600 seconds` only with a valid explicit exactly scoped owner
  decision in the admission policy record, visible with its validity/baseline/
  actual timing and weaker status in the receipt and scheduler answer; actual
  disposition at detection + 500 seconds satisfies that admitted exception. Pair
  the later-trigger negative with its own exactly authorized trigger control.
  Failed narrowing still stops within that same original deadline; retries and
  recovery never reset it. Authorized intact-state recovery remains usable.
- Class cases, TimingBaselineExceptionRequired/Allowed: for every comparable
  surface in the timing table, a looser window/bound or later trigger without the
  decision refuses before dependent effects; equal/stricter values and a valid
  explicit timing-only exception admit within the same scope. Decision expiry or
  binding change refuses at start/resume/restart. Currentness, immediate fences
  and non-waivable prerequisites remain mandatory even with a valid decision.
- Narrowing control: CM-08/19/22 drop only stuck-path completion/activation gates;
  normal success and all fences remain; the named witnesses fail.
  OwnerExceptionOnlyRemoved retains ordinary qualification/bound approval and all
  timing/disposition checks, but omits only the explicit owner-exception gate;
  RevocationExceptionRequired's 600-second variant MUST fail. Separately removing
  each other timing surface's exception gate MUST fail its named
  TimingBaselineExceptionRequired variant; valid controls remain admitted.

#### FX-24 — Operator access and retention

- Threats: TM-OPS-01; controls: TC-24.
- Negative: unauthorized/post-deletion retrieval refuses, but that alone cannot
  prove deletion. CW-20 checks actual covered artifact/log/backup copies removed
  with deletion evidence by the original B-delete; fenced/unknown retained bytes
  past the bound fail qualification. Expiry cannot discharge pending custody.
- Positive: authorized pre-expiry retrieval and disclosed operator access work;
  eligible covered copies actually delete by B-delete after published expiry,
  including a transient unknown deletion resolved within the original bound.
- Narrowing control: CM-20 drops deletion completion only while stuck, retaining
  access denial, normal deletion and custody accounting; CW-20 fails.

#### FX-25 — Guarantee honesty and acceptance

- Threats: TM-AUTH-01, TM-QUAL-02; controls: TC-21, TC-23.
- Negative: missing/stale exact weaker acceptance, unverified evidence or changed
  compensation refuses; no weaker entry is relabelled `present` in answer/receipt.
  At start, resume and restart, separately omit/change the matrix binding or use a
  missing, expired or not-yet-valid operator interval while all other evidence is
  current; require the intended acceptance refusal and no transition/work effect.
- Positive: a currently qualified weaker entry with exact operator acceptance and
  requester acknowledgement runs under its disclosed reduced requirement. Each
  transition also has a valid current matrix/interval control with identical bounds.

#### FX-26 — Boundary receipt binding

- Threats: TM-RES-01, TM-RES-03, TM-LIFE-01; controls: TC-15, TC-17, TC-22.
- Negative: job-written, wrong-generation, replayed, incomplete or mismatched
  receipts refuse; expired receipt validity or stale policy/qualification/revocation
  epochs also refuse with otherwise valid bindings and signature. A boundary-only
  report cannot prove launch/absence. CW-04 fails
  if payload release precedes applied boundary or durable verified receipt/binding;
  CW-05 fails if physical start is claimed without separate original start evidence.
- Positive: protected exact receipt verifies as a host claim before code release;
  separate start evidence records that execution. Transient publication uncertainty
  resolves before dependent code/claims, without overstating computation truth.
- Narrowing control: CM-04/05 skip pending-path publication/order evidence while
  preserving ordinary starts and fences; their named witnesses fail.

Qualification records MUST preserve exact source/configuration identities,
commands, production entry, platform/tuple, exit codes, paired outcomes and
reviewer scope. Unrun, skipped and truncated evidence MUST remain unverified.
No table in this proposal changes status merely because its document checker passes.

## Open questions for the operator

Each numbered question is an activation decision contained in this CIP.
Recommendations are proposed answers, not assumed permission.

1. **Q-FX-01 — EIC integration ownership.** Who coordinates the CIP-0025 adapters
   and module-owned carriers for this class? Recommended: assign a cross-module
   specification owner and approve the exact integration mapping before activation;
   use the filed CIP-0025 definitions and retain the pool-specific additions here.
2. **Q-FX-02 — Pool operations and custody.** Who operates and rebuilds dedicated
   hosts and holds external quarantine authority? Recommended: a designated pool
   operations team with named recovery responsibility and separation from job
   submitters; no station/platform services or private operator data on pool hosts.
3. **Q-FX-03 — Submission eligibility and authentication.** Which principals may
   submit and which protected service verifies them? Recommended: initially an
   explicit principal allowlist with attenuated action/target grants, per-principal
   budgets and current revocation; keep anonymous public submission disabled.
4. **Q-FX-04 — Network default.** Is any dependency egress enabled initially?
   Recommended: `none` by default; approve bounded destination/protocol/DNS rules
   and independent upstream enforcement separately, never unrestricted internet.
5. **Q-FX-05 — Retention.** What lifetimes and release events govern artifacts,
   logs and backups? Recommended: retain pending delivery under quota until
   authenticated acknowledgement or explicit disposition; after acknowledgement,
   retain outputs seven days and diagnostics at most 24 hours, with no hidden
   backup extension. Publish deletion evidence and operator access before launch.
6. **Q-FX-06 — Qualification authority and revocation.** Who accepts evidence and
   what happens to active jobs on drift/compromise? Recommended: independent
   qualification approval and immediate external start/release fences; require
   `B-revoke <= 300 seconds` from detection, with confirmed whole-account stop
   including quiet period, or qualified non-revoked narrowing, by that original
   deadline. A longer bound or later trigger requires the explicit owner decision,
   scope and current validity recorded for admission and disclosed in the receipt
   and scheduler
   answer under Timing baselines above; ordinary bound approval is insufficient.
   Retain custody/fences on failure; no clock reset, self-cleared revocation or
   automatic reuse.
7. **Q-FX-07 — Guarantee mapping acceptance.** Who accepts this pool mapping and
   local definitions against station parity `71dd888` before activation? Recommended:
   EIC/station and pool owners review the exact shared/local mapping; retain all
   per-property weaker/absent distinctions and refuse unknown/unverified IDs.
8. **Q-FX-08 — Numerical limits.** Which concrete budgets apply to each class?
   Recommended: publish hard CPU/memory/process/storage/I/O/output/time and intake
   caps per tuple plus principal/global budgets, reserving independent recovery
   capacity; no soft-only substitute without explicit qualified weaker acceptance.
9. **Q-FX-09 — Pool enrollment/report authentication.** How are jobs delivered and
   receipts authenticated without platform authority on hosts? Recommended:
   isolated pool-only reporting identity and mediated gateways with no transitive
   service rights; review custody/revocation/freshness before provisioning any key.
10. **Q-FX-10 — Sharing, devices and leakage.** Which initial classes are allowed?
    Recommended: exclusive secret-free device-free execution first; shared/composed
    topologies or devices require distinct qualified tuples, disclosed leakage and
    operator-approved policies. Do not claim advanced side-channel elimination.

## Threat catalogue

This appendix is normative for every threat, control, adversary and interpretation
identifier used in this CIP. The full threat model is maintained separately; this
proposal requires no unpublished file to interpret these identifiers. The catalogue
is specific to the external pool and does not define station conformance. A control
reference states an obligation, not evidence that its implementation is qualified.
Existing Design requirements and qualification cases remain independently required.

| Threat ID | Threat statement | Required controls | Adversaries |
|---|---|---|---|
| TM-ISO-01 | A job breaches its execution boundary and gains host-kernel, VMM or supervisor control. | TC-01, TC-02, TC-13, TC-14 | AD-01 |
| TM-ISO-02 | Payload access to management interfaces or inherited handles turns a host service into a deputy. | TC-01, TC-03, TC-09, TC-11 | AD-01 |
| TM-DATA-01 | A later job recovers an earlier job's data from storage or memory that was declared reusable. | TC-04, TC-22, TC-24 | AD-03 |
| TM-DATA-02 | A mutable or improperly authorized shared cache reveals data or changes another job's inputs. | TC-05, TC-12, TC-21 | AD-01, AD-03 |
| TM-DATA-03 | Unreset device state or DMA exposes data or authority beyond the admitted execution. | TC-02, TC-04, TC-06, TC-23 | AD-01, AD-03 |
| TM-DATA-04 | Object-store access substitutes inputs or reveals another requester's private artifacts. | TC-05, TC-12, TC-15, TC-21, TC-24 | AD-02, AD-04 |
| TM-DATA-05 | Parsing job-controlled bytes outside the runner causes unauthorized state, code execution or unbounded work. | TC-02, TC-12, TC-13, TC-16, TC-19, TC-20, TC-22, TC-25 | AD-01, AD-02, AD-04, AD-05 |
| TM-SIDE-01 | Concurrent hardware sharing discloses a neighbour's information through shared-resource observations. | TC-06, TC-07, TC-21, TC-23 | AD-03 |
| TM-CRED-01 | Platform credentials or service authority become reachable on a pool host or inside a job. | TC-01, TC-03, TC-08, TC-09 | AD-01, AD-04 |
| TM-CRED-02 | Code, caches or retained artifacts expose sensitive material submitted with a job. | TC-04, TC-08, TC-10, TC-24 | AD-01, AD-03, AD-04 |
| TM-CRED-03 | A guest or forwarded identity is accepted as a native host or station principal. | TC-01, TC-03, TC-09, TC-21 | AD-01, AD-04 |
| TM-NET-01 | Pool traffic becomes a channel for exfiltration or attacks against external systems. | TC-01, TC-10, TC-19, TC-20 | AD-01, AD-02, AD-04 |
| TM-NET-02 | DNS answers, redirects or address-family changes evade the destination restrictions. | TC-03, TC-10, TC-11, TC-12 | AD-01, AD-05 |
| TM-NET-03 | An attacker substitutes or replays traffic, or creates unsolicited job ingress. | TC-10, TC-12, TC-15, TC-21 | AD-05 |
| TM-SUP-01 | Unapproved image, dependency, backend or policy bytes replace the admitted software supply chain. | TC-02, TC-05, TC-13, TC-23 | AD-02, AD-04, AD-05 |
| TM-SUP-02 | Host boot or firmware compromise survives the disposal of an individual runner. | TC-01, TC-13, TC-14, TC-23 | AD-01, AD-04 |
| TM-RES-01 | A fabricated, substituted or replayed result is accepted for the wrong inputs or execution attempt. | TC-12, TC-15, TC-18, TC-22 | AD-02, AD-04, AD-05 |
| TM-RES-02 | Artifact, log or telemetry bytes activate behavior in an importer, viewer or reviewer. | TC-16, TC-19, TC-20, TC-21 | AD-01, AD-02, AD-04 |
| TM-RES-03 | A compromised host authenticates a false claim that computation or cleanup succeeded. | TC-15, TC-17, TC-23 | AD-04 |
| TM-TIME-01 | Clock changes revive expired authority, qualification or elapsed-work allowances. | TC-15, TC-18, TC-22, TC-23 | AD-01, AD-04 |
| TM-DOS-01 | Payload resource consumption prevents bounded execution or the host's recovery operations. | TC-19, TC-20, TC-22 | AD-01, AD-03 |
| TM-DOS-02 | Submission, transfer or result floods consume shared control-plane capacity. | TC-12, TC-16, TC-19, TC-20 | AD-02, AD-04, AD-05 |
| TM-AUTH-01 | A submitter's declaration falsely upgrades its authority, class or available capabilities. | TC-01, TC-08, TC-21, TC-23 | AD-02 |
| TM-AUTH-02 | A consumer treats delivery or a valid signature as sufficient action-specific permission. | TC-09, TC-12, TC-18, TC-21 | AD-02, AD-04, AD-05 |
| TM-LIFE-01 | An interrupted or retried lifecycle effect produces overlapping execution or premature reuse. | TC-04, TC-15, TC-19, TC-22 | AD-01, AD-02, AD-04 |
| TM-QUAL-01 | A host's own assertion or unrelated evidence is accepted as qualification for its tuple. | TC-17, TC-21, TC-23 | AD-04 |
| TM-QUAL-02 | Update, revocation or restored state leaves outdated qualification usable for admission or running work. | TC-13, TC-14, TC-18, TC-22, TC-23 | AD-04, AD-05 |
| TM-OPS-01 | Administrative access or retention exposes job data beyond the confidentiality disclosed to authors. | TC-01, TC-08, TC-24 | AD-06, AD-04 |

### Adversary vocabulary

| ID | Capability and trust assumption |
|---|---|
| AD-01 | Job code can choose hostile instructions, system calls, files, protocols, children and races within every offered interface. |
| AD-02 | A submitter can choose declarations, inputs, image/dependency references and output text, and repeat submissions under permitted identities. |
| AD-03 | Another job can choose shared-state content and observe concurrent hardware or later reuse of the same machine. |
| AD-04 | A dishonest host controls its kernel, supervisor, storage, clocks and reports; it can inspect jobs and misuse its own reporting signer. |
| AD-05 | A network attacker controls hostile endpoints or DNS replies and can observe, delay, replay, inject or alter unprotected traffic. |
| AD-06 | Platform administrators and operators control admission, infrastructure, stores and delivery; authors must assume they can inspect job plaintext. |

### Control obligations

The referenced services MUST enforce these controls together with the detailed
Design requirements. An unsupported or unqualified required control keeps admission
closed. These descriptions allocate no new module wire fields or service authority.

| Control ID | Required control |
|---|---|
| TC-01 | Separate pool machines and networks from platform services; keep platform authority, credentials and unrelated operator data off those machines. |
| TC-02 | Establish the complete backend boundary before any controlled instruction; minimize privileges, devices and host/kernel interfaces and reject unsupported combinations. |
| TC-03 | Exclude host management sockets, namespace access and inherited handles; allow only specifically admitted minimal guest I/O. |
| TC-04 | Provide fresh job storage/memory and confirm termination plus cleanup before reuse; uncertain destruction leaves the placement quarantined. |
| TC-05 | Give jobs private mutable caches; authorize and verify every shared object's digest, keep it immutable and read-only, including dependencies. |
| TC-06 | Refuse devices initially; later admission requires independently qualified DMA containment and complete reset of device state. |
| TC-07 | Admit only approved concurrency/sharing classes, reject incompatible placements and disclose the remaining side-channel exposure. |
| TC-08 | Issue no platform credentials, subscription bindings or broker leases to pool work; the initial secret-free class also rejects supplied job credentials. |
| TC-09 | Preserve separate guest and native authority; forbid signer/registrar forwarding, UID translation and borrowed station identities. |
| TC-10 | Deny egress by default; bound approved dependencies, bandwidth and connection counts, enforce upstream containment and provide an abuse response. |
| TC-11 | Check every resolved destination and redirect across address families; deny private, local, link-local, metadata and platform addresses. |
| TC-12 | Authenticate and integrity-check bounded transfers, prevent replay and unsolicited ingress, and never infer authority from network location. |
| TC-13 | Pin approved image/backend/policy digests and provenance; constrain layer preparation under TC-25, control updates and refuse revoked rollback targets. |
| TC-14 | Hold compromise fences outside the affected host; require a trusted rebuild/re-enrollment process authorized independently before reuse. |
| TC-15 | Bind accepted results to requester, request, complete input/dependency manifest, attempt, host/boot generation, policy and output bytes; reject stale or duplicate attempts. |
| TC-16 | Validate and publish results, logs and telemetry as bounded whole objects; keep consumption inert, exclude unsafe paths/types, discovery, hooks, active rendering and automatic execution, and apply TC-25 to outside parsing. |
| TC-17 | Disclose the actual evidence level; require independent trusted checks for stronger claims and never infer truth or hardware attestation from a host signature. |
| TC-18 | Use independent current authority time and monotonic budgets; neither guest nor host reports may extend grants, evidence validity or original deadlines. |
| TC-19 | Enforce admitted CPU, memory, process, disk, I/O, output and runtime ceilings while preserving actual stop, observation and cleanup capacity. |
| TC-20 | Cap per-principal and aggregate admission, transfer, parsing, queue, storage/debt and result work; protect independent control and recovery capacity. |
| TC-21 | Authenticate recorded class and concrete action/target authority, enforce attenuation/currentness, and intersect caller, owner, platform and exact capability restrictions. |
| TC-22 | Persist original effects, execution identity and fences; uncertain launch, stop, export or destruction cannot authorize duplicate execution or reuse. |
| TC-23 | Require independently reviewed production-entry evidence for the complete tuple, paired positive/negative cases, current validity, revocation and change invalidation. |
| TC-24 | Disclose sensitivity exclusions, operator access and retention; authorize artifact retrieval/deletion and preserve administrative audit evidence. |
| TC-25 | Register every outside interpreter with closed formats, safe roots/types and streaming byte/count/expansion/work caps; use private constrained staging, reject partial publication and unauthorized effects, and keep opaque content uninterpreted. |

### Interpretation inventory

Each listed surface MUST have an enforcing service, admitted format and limits,
and paired qualification evidence before activation. Prefer interpretation inside
the already isolated runner. A new outside surface MUST extend this inventory and
its qualification coverage before admission; no ambient shell, hooks, plugins or
repository discovery can substitute for the declared service.

| ID | Surface and responsible service | Location and restriction | Controls | Threats |
|---|---|---|---|---|
| IP-01 | Submission/declaration/authority parsing by admission and scheduler | Outside; only registered bounded message formats | TC-12, TC-20, TC-21 | TM-AUTH-02, TM-DOS-02 |
| IP-02 | Input lookup and transfer framing by the authorized gateway | Outside; object contents opaque wherever possible | TC-12, TC-21, TC-25 | TM-DATA-04, TM-DATA-05 |
| IP-03 | Input extraction and root construction by the materializer or approved preparation worker | Inside preferred; any external staging obeys TC-25 and runs no workload code | TC-25 | TM-DATA-05 |
| IP-04 | Image/layer parsing and assembly by the approved loader | Outside loading only under approved bounded preparation; job formats inside or separately admitted under TC-25 | TC-13, TC-25 | TM-SUP-01, TM-DATA-05 |
| IP-05 | Dependency transfer/DNS/redirect metadata by proxy and scoped gateway | Outside destination/framing checks; content remains opaque | TC-11, TC-12, TC-15, TC-25 | TM-NET-02, TM-DATA-05, TM-RES-01 |
| IP-06 | Package resolution/extraction/install behavior by job tooling | Inside after start only; never a host package manager acting for the job | TC-02, TC-15, TC-25 | TM-ISO-01, TM-RES-01, TM-DATA-05 |
| IP-07 | Guest/device/status messages by supervisor and backend adapter | Outside; only qualified bounded interfaces | TC-02, TC-03, TC-20, TC-25 | TM-ISO-01, TM-ISO-02, TM-DOS-02, TM-DATA-05 |
| IP-08 | Logs/error text/telemetry/display by collector and inert renderer | Outside; content cannot choose commands or metric formats | TC-16, TC-20, TC-25 | TM-RES-02, TM-DOS-02, TM-DATA-05 |
| IP-09 | Artifact intake/extraction/publication by collector and quarantine importer | Outside; bounded validation precedes atomic whole publication | TC-16, TC-20, TC-25 | TM-RES-02, TM-DATA-05 |
| IP-10 | Cancellation/observation/status parsing by lifecycle and authority services | Outside; commands bind the exact identity and generation | TC-12, TC-21, TC-22 | TM-AUTH-02, TM-LIFE-01 |
| IP-11 | Qualification/health reports by independent admission gate | Outside; a report cannot authorize its own tuple | TC-17, TC-23 | TM-QUAL-01 |
| IP-12 | Cleanup/export recovery and paths by constrained collector/reconciler | Outside; metadata remains untrusted on every retry | TC-22, TC-25 | TM-LIFE-01, TM-DATA-05 |
| IP-13 | Candidate and report inspection by result consumer/review adapter | Outside; inert content outside all control discovery roots | TC-16, TC-21 | TM-RES-02 |

[station-parity]: https://github.com/relux-works/swarma-user-manager/blob/71dd888e23350d736ea74589ea1f5b4692258a2d/spec/platform-parity.md
