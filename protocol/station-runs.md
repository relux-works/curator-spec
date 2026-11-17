# Runs inside a station (station-runs, PROPOSED)

Status: PROPOSED and non-normative. This companion holds the runs model that
station/1 v1 does not adopt: instruction delivery, runs inside a standing
station, and every record, gate, code, clock and implementation row that
exists only for them. Nothing in this file is a rule of station/1 v1, no cell
of [the station contract](station.md) depends on it, and an implementation of
station/1 v1 owes nothing in this file. The text below is carried over from
the station/1 draft unchanged in substance so the owner decision can be made
on it; known defects found in review are listed in section 9 and are not
fixed here.

The key words MUST, MUST NOT, MAY and SHOULD in the carried text describe the
proposal only; they bind nobody until the owner adopts this file.

## 1. Open owner questions

| Id | Question | Option A | Option B | Decides |
| --- | --- | --- | --- | --- |
| OQ20 | Runs: whether the proposed run model of this file is adopted, and whether conversation state may be carried across runs. | Adopt as proposed; each run starts from a fresh conversation. | Adopt as proposed; conversation state is carried, with a rule for what a later grant may read. | Owner. |
| Row 12 | Runs inside a station (row 12 of the comparison of what the action profile hands to the station contract): whether a standing station takes follow-up work as runs under per-instruction grants at all, as this file proposes. | Adopt this file (with OQ20 answered) and merge its table additions, vocabulary and rules into the station contract. | Do not adopt: a standing station's work input is then defined by a later contract, and this file is retired. | Owner. |
| store-loss recovery: v2 | Restoring a station after a store loss, fence or restore instead of the station/1 version 1 cut (every station in `lost`; exit only by operator re-provision from scratch for a name the key service has never bound, or by operator teardown into retirement for a name whose fresh census shows a live account, key-service-bound or not, ending in `retired`, never reused if the key service has bound it; the same open item in the station contract, section 15): a proof of its principal, pin and owner binding from an effect owner, and the cells that would spend it. Handing a lost name's retained keys to a new principal is a version 2 owner question under this item; version 1 never hands them over, on either exit. Restoring a station across the loss is all that remains under this item: the removal of a lost name's censused account and home and the release of its slot entry and account claim are version 1, by the teardown retirement (station contract SR3). Nothing in this companion spends it. | Define that proof and its carrying cells in version 2 of the station contract, and let a proved station leave `lost` by them; only there decide any hand-over of a lost name's retained keys to a new principal. | Keep the version 1 cut indefinitely: no station is restored across a loss; a never-bound name returns only by re-provision from scratch under a new generation, a name with a live account leaves only by retirement, a key-service-bound name is never reused, and any other station takes a new name. | Owner. |

Until OQ20 and Row 12 are decided, station/1 v1 defines no instruction
delivery and no run. A standing station's work input is out of scope of v1.
The store-loss recovery: v2 row above is a station-contract open item
named here as a pointer; deciding it adopts nothing in this companion.

## 2. Proposed additions to the lifecycle table

Adoption would add the row `held:run`, the three columns below, and the
definition "the running rows" for `running`, `held:live` and `held:run` to
the lifecycle table of the station contract. `held:run` would mean: unknown
outcome of a run; an instruction may or may not have been applied. The cells
below are the proposed columns against every state (the lifecycle cells stay
as in the station contract, except the "unknown or stranded outcome" cells of
`running` and `held:live`, which this proposal would route through the run
outcome as section 5 states).

| State | instruction received | run start | run end |
| --- | --- | --- | --- |
| absent | refused: station_absent | refused: station_absent | refused: station_absent |
| provisioning | refused: station_not_enrolled | refused: station_not_running | refused: station_not_running |
| provisioned | refused: station_not_enrolled | refused: station_not_running | refused: station_not_running |
| enrolling | refused: station_not_enrolled | refused: station_not_running | refused: station_not_running |
| stopped | stopped; DI; R07; G9 | refused: station_not_running | refused: station_not_running |
| starting | starting; DI; R07; G9 | refused: station_not_running | refused: station_not_running |
| running | running; DI; R07; G9 | running; DI; R21; G15 | running; DI; R22; G16 |
| stopping | stopping; DI; R07; G9 | refused: station_not_running | refused: station_not_running |
| updating | updating; DI; R07; G9 | refused: station_not_running | refused: station_not_running |
| bumping | refused: station_busy | refused: station_not_running | refused: station_not_running |
| retiring | refused: station_retiring | refused: station_retiring | refused: station_retiring |
| retired | refused: station_retired | refused: station_retired | refused: station_retired |
| held:provision | refused: station_held | refused: station_held | refused: station_held |
| held:enroll | refused: station_held | refused: station_held | refused: station_held |
| held:account | refused: station_held | refused: station_held | refused: station_held |
| held:start | held:start; DI; R07; G9 | refused: station_held | refused: station_held |
| held:live | held:live; DI; R07; G9 | refused: station_held | held:live; DI; R22; G16 |
| held:run | held:run; DI; R07; G9 | refused: station_held | refused: station_held |
| held:stop | held:stop; DI; R07; G9 | refused: station_held | refused: station_held |
| held:update | held:update; DI; R07; G9 | refused: station_held | refused: station_held |
| held:bump | refused: station_held | refused: station_held | refused: station_held |
| held:retire | refused: station_held | refused: station_held | refused: station_held |

Against the lifecycle events, the proposed `held:run` row carried: process
appears and liveness reading missed to `held:stop` on R06; process exits and
host reboot to `stopping` on R05 and R11; stop requested to `stopping` on
R08 (G4); starter crash and unknown outcome self-looped on R10 and R17;
session journal lost to `held:stop` on R23; capability report self-looped on
R24; proof of the run outcome (completed or did not happen) to `running` on
R18 (G13); operator teardown order to `stopping` on R19 (G14); every
proposal refused `station_held`, every unexpected proof refused
`station_proof_unexpected`, and liveness restored recorded as cannot occur
(no missed reading is recorded in that row). On adoption this row, the
proposed columns table above (which lists no `lost` row), and this
row's journal-lost cell (to `held:stop` on R23, against the station
contract's entry of every record into `lost` on that event) are all to
be re-walked against the lifecycle table as it then stands.

Proposed event definitions (reported to the dispatcher; the dispatcher alone
would commit the cell):

| Event | Reported by | Meaning |
| --- | --- | --- |
| instruction received | AL | A message addressed to the station identity is reported for the J2 check at receipt (section 6); G9 spends the J2 refusal codes. |
| run start | SH | The session host is about to open a run for the oldest queued instruction. |
| run end | SH | The open run ended: the harness confirmed its end, or the dispatcher ordered its end because its grant was revoked or expired or the session authority closed, or its delivery was refused, or the J2-again check of G15 refused it terminally after R21 with outcome `not_started` and no delivery. |

## 3. Proposed records

| Id | Content | Precedes | Effect owners and their own write-ahead | Source |
| --- | --- | --- | --- | --- |
| R07 | Instruction entry: AL's J2 verdict at receipt (signer, the grant the instruction cites, revocation snapshot, replay check) and the disposition `queued` or `data`. | The queue entry at the session host. Nothing is delivered by this record. | AL: admission record beside the body. SH: queue entry. | BK24 "Trust gate"; BK24 "Doorbell, mailbox and session input"; ADD C |
| R21 | Run open: run identity, the instruction of R07 it serves, the grant it cites, AL's J2 verdict at this moment. | The run binding at the key service and the delivery to the harness. | KS: run binding. SH: delivery intent. | ADD C; RUL-2; BK24 "Doorbell, mailbox and session input" |
| R22 | Run close: run identity and one outcome of `ended`, `ended_by_revocation`, `ended_by_expiry`, `ended_by_suspension`, `not_started`, `interrupted`; `interrupted` is written by R05, R06, R08, R11 or R23 in place of R22 and includes may-have-applied (RN6). | The release of the run binding and the next run start. | KS: binding release. SH: queue advance. | ADD C |

Carried run parts of lifecycle records and proofs, for the merge on adoption:
R05, R06, R08, R11 and R23 would each close an open run as `interrupted`; R17
would mark an unknown run outcome `unknown`; R18 would close a run
`not_started` on P4 and `ended_by_revocation` on the P3 that returns
`held:run` to `running` over a closed run authority; R24 would record a
run-authority closure naming the run or queued instruction it binds; proof P3
for a run would be the harness confirmation marker in the native transcript,
and proof P4 for a run would be the absence of that marker in a completely
read native transcript.

## 4. Proposed codes, gates and clock

| Code | Evaluator | Meaning | Carries |
| --- | --- | --- | --- |
| `station_run_open` | DI | A run is open or its outcome is unknown. | none |
| `station_run_not_open` | DI | No run is open. | none |
| `station_session_suspended` | DI | The capability session authority is recorded closed. | none |
| `message_signature_invalid` | AL | The signature over the exact bytes does not verify. | none |
| `message_grant_refused` | AL | The grant the instruction cites does not cover it, or is revoked or expired. | none |
| `message_revocation_unknown` | AL | The revocation state for that grant is unavailable. | none |
| `message_replayed` | AL | The message was already admitted. | none |
| `message_target_mismatch` | AL | The message is not addressed to this station identity. | none |

| Gate | Cells | Before the record, in order | After the record, in order |
| --- | --- | --- | --- |
| G9 | every [state x instruction received] that is not a refusal | AL, J2 at receipt: `message_target_mismatch`, `message_signature_invalid`, `message_replayed`, `message_revocation_unknown`, `message_grant_refused` | none |
| G15 | [running x run start] | `station_run_open`, `station_session_suspended`, `station_gateway_unready`; then AL, J2 again, temporary case only: `message_revocation_unknown` (the instruction stays at the head of the queue) | AL, J2 again, terminal case: `message_grant_refused` for a grant revoked, expired or not covering the instruction. It arrives after R21 as [running x run end] with outcome `not_started`, no delivery, and R22 advances the queue past that instruction. A refused run binding or a refused delivery is likewise [running x run end] `not_started`. No refused instruction stays at the head of the queue. |
| G16 | [running, held:live x run end]; [running, held:live x unknown or stranded outcome] | For "run end" only: `station_run_not_open`. For "unknown or stranded outcome" no run needs to be open: the cell commits with or without one and R17 records which, closing a run that was open as there stated. | none |

| Clock | Runs from, to | On expiry the dispatcher commits | Value | Source |
| --- | --- | --- | --- | --- |
| `run_bound` | R21, to R22. It is a bound on getting the run's end reported, never a grant clock: expiry or revocation of a run's grant is a feed report and ends the run through [running x run end] under section 7.1, and this clock claims no cell of it. | [running x unknown or stranded outcome] | A bound of the session-host contract, always no longer than the validity left in the grant the run cites; its value is OPEN OQ20. | ADD C |

## 5. Proposed run rules (RN, carried text)

RN1. A long-lived station has one account and one home across its life and
many runs over time [ADD C].

RN2. The session's grant authorizes the start and the holding of the station
and no instruction [AP 12].

RN3. Every admitted instruction creates its own run inside the station, bound
to the grant that instruction cites. A later instruction reaches the station
through its message identity: the bridge of that identity, in the owner
channel or a project room [BK24 "Owner channel"]. J2 checks it at receipt
([state x instruction received], gate G9, R07) and again when its run starts
([running x run start], gate G15, R21). A queued instruction whose grant was
revoked or expired starts no run and does not stay in the queue: its run is
opened by R21 only to be closed at once by [running x run end] with outcome
`not_started`, no delivery, and R22 advances the queue to the next
instruction (G15) [ADD C; DEC D6; BK24 "Doorbell, mailbox and session
input"]. Only a temporary refusal (`message_revocation_unknown`, a closed
capability, an open run) leaves an instruction at the head of the queue. An instruction never causes a start: in a state without a
bound incarnation it is queued by R07 and nothing else happens [BK07 "Wake-up
and context transfer"].

RN4. A run has a start, an end and an unknown outcome. Its start is
[running x run start]: R21 is written before the key service binds the run and
before the session host delivers. Its end is [running x run end]: R22. Its
unknown outcome is [running x unknown or stranded outcome]: the station enters
`held:run`, the input fence closes, and only P3 or P4 over the native
transcript returns it to `running`, the run closed `ended_by_revocation`
instead of left open where its grant died in the hold (R18) [BK07 "Queue and
questions of the harness"]. A session-host restart while a run is open is
the event "unknown or stranded outcome", not a capability report and not a
starter crash, because the delivery state is exactly what is lost. Grant
expiry and revocation are never this event and never `run_bound`: they are
feed reports under section 7.1 and end the run through [running x run end]
or record its authority closed in `held:run`; no cell claims them twice.
NEW: at most one run is open at a time, because one dispatcher writes into
the input of a session [BK07 "Service, runner and the single writer"].

RN5. Revocation or expiry of a run's grant ends that run and not the station,
within the snapshot propagation bound and never later than 300 seconds from
the validated report (section 7.1); the station's own lifetime follows the
session's grant (K2, section 7.1) [ADD C].

RN6. When the station leaves the running rows, the open run is closed as
`interrupted` by the record of that cell (R05, R06, R08, R11, R23), which
writes that outcome in place of R22 (section 4.1). `interrupted` includes
may-have-applied: the instruction may already have been applied before the
exit, the transcript check of `held:run` is not owed on this path, and the
run's requester MUST reconcile before asking again. An interrupted run and a
run closed `not_started` are never delivered again by an automatic step
[BK07 "Queue and questions of the harness"].

RN7. What stays open, in one sentence: whether the model's conversation may
continue across runs, because carried context is exactly what the rule
against entering an existing run guards (OPEN OQ20).

RN8. Delivery, signing and carrier effects while `running` [DEC D6]. An
unknown delivery is RN4. An unknown outcome of attestation issuance closes the
capability signing with no fallback to the earlier attestation [BK06 "Message
key and its attestation"]; a lost carrier channel closes the capability
carrier channel. Both are [running x capability report]: they change no state
and are recorded by R24, so the station is never reported as reachable on a
capability that is recorded closed.

## 6. Proposed admission of instructions (J2, carried text)

J2. Before a message becomes an instruction, the bridge checks the signature
and the grant the message cites [BK24 "Trust gate"; BK13 "Who checks the
right"]. The check is deterministic and asks no model. J2 is evaluated twice
for every instruction: at receipt (gate G9) and when its run starts (gate
G15) [DEC D6; ADD C; BK24 "Doorbell, mailbox and session input"]. Its output
is "instruction of action X on target Y under grant Z", "data", or a refusal
with a code of G9. A correctly signed message outside the actions of the
grant it cites is data and never an instruction; a relayed owner decision is
data [BK24 "Trust gate"; BK24 "Assurance levels for human messages"; C24
"Root context and authority"]. A message that DI refuses by state stays in
the bridge's mailbox with its admission record; nothing is queued for it.

## 7. Proposed run rows for the stop and suspension triggers

| Trigger | Observed by | Decided in the proposal | Enters by | Open |
| --- | --- | --- | --- | --- |
| A run's grant revoked, expired or sealed (OQ5c, closed) | GC, through its feed to DI | The run ends within the snapshot propagation bound and never later than 300 seconds from the validated report; the station does not stop for this alone [ADD C]. In `held:run` the same report is recorded as run authority closed and the run never returns open (R18, U5). A queued instruction of that grant ends `not_started` at its run start and leaves the queue (G15). | [running, held:run x capability report]; [running x run end] with outcome `ended_by_revocation` or `ended_by_expiry` | none |
| Device set changed | AL, by the device attestation of the carrier profile [BK24 "Assurance levels for human messages"] | A message from a device outside the pinned chain does not reach the level that can command; J2 refuses. No stop. | gate G9 and gate G15 | none |

## 8. Proposed negative obligations and implementation units

| Forbidden outcome | Enforcing cell and code | Valid control beside it |
| --- | --- | --- |
| An instruction outside the grant it cites becoming a run | gate G9 and gate G15, `message_grant_refused` | an instruction inside its grant opens a run |
| A queued instruction whose grant was revoked opening a run, or a refused instruction blocking the queue | [running x run start] gate G15: terminal J2 refusal ends `not_started` after R21 and R22 advances the queue; only a temporary refusal keeps its place | a queued instruction with a valid grant opens a run, behind one that was refused terminally and left |
| An instruction causing a start | [stopped x instruction received] stays `stopped` and writes R07 only | a start request starts |
| A run delivered twice after an unknown outcome | `held:run`; RN6 | a run proved not applied is closed `not_started` and reported |

| Repository | Unit | Exists or new | LU | Depends on | First negative test |
| --- | --- | --- | --- | --- | --- |
| swarma-dispatcher | Run level: one execution, many runs | new | 1 | OQ20 | a second run start while a run is open refuses |
| swarma-keymaker | Run binding | new | 1 | the unit above; OQ20 | a run with no R21 gets no binding |
| a2a-swarm | J2 at the bridge, at receipt and at run start | new | 3 | grant contract | a correctly signed message outside the grant it cites is data, never an instruction |
| swarma-session-host | Run delivery: open, end, unknown, transcript marker | new | 2 | OQ20 | a run with an unknown outcome is not delivered again |

## 9. Known open defects of this proposal (not fixed)

Review of the carried text found the following defects. They are defects of
this proposal, recorded so adoption cannot overlook them; fixing them is part
of deciding section 1, not of station/1 v1. The station parts of the third
and fourth items (a write-ahead stop order with a dispatcher clock, a
freshness bound on the revocation feed with a resync at a dispatcher restart,
an entry for a revoked qualification, and the hold on an unreadable
revocation state) are decided and fixed in the station contract; only their
run parts are open here.

| # | Defect |
| --- | --- |
| D1 | A missed liveness reading: the record text closes an open run as `interrupted` when a reading leaves `running`, while the run rules keep a run open in `held:live` and give it run-end cells there. One of the two must be chosen. |
| D2 | A run left open or `unknown` blocks the queue forever: the run closers do not include the operator order, and the hold record marks a run `unknown` without closing it, so after a teardown every later run start refuses and no cell closes the stale run. |
| D3 | Revocation at run grain: nothing orders the end of an open run ahead of its effect with a clock, the run-start gate has no code for a closed run authority, and a queued instruction under a revoked grant can open a run while a snapshot lags. |
| D4 | Unreadable revocation state at run grain: the carried text both ends the open run under a suspension and lets an open run finish with no stop for unreadability alone. One reading must be chosen. |
| D5 | A closed capability (signing, input delivery, carrier channel, run authority) is stated to leave an instruction at the head of the queue, but the run-start gate has pre-record codes only for session authority and the gateway, so the instruction is instead opened and closed `not_started` and dropped. |
| D6 | A correctly signed message outside the actions of the grant it cites is stated to be data and never an instruction, while the code registry, the trigger rows and the negative obligations refuse it at J2. One disposition must be chosen. |
| D7 | The order of the state check and J2 for unauthenticated input: a forged message reaches state-refusal cells before J2, and their codes reveal whether a name exists and its state. The admission order must be decided without that exposure. |
| D8 | At a run grant's expiry, the run bound races the feed's run end: which one claims the cell is undecided. |
