# Agent station contract (station/1)

Status: unreleased draft contract. It is specification text only: it claims no
implemented service, enabled capability or qualified runtime, and it changes no
released schema, carrier or conformance vector. It is the normative successor
of the "Lifecycle and failure handling" and "Ownership and records" sections of
[CIP-0024](../cips/CIP-0024-agent-stations.md); the owner decisions recorded in
that CIP are not reopened here.

The key words MUST, MUST NOT, MAY and SHOULD have their RFC 2119 meanings.

## 1. Scope and method

A station is one long-lived agent (orchestrator, worker or reviewer) with one
operating-system account, one stable name, keys it can use and cannot read, one
home and one root context [C24 "Owner decisions"; UM 1; BK05 "Station and its
guarantees"]. A station survives restarts. It is the default unit; the one-task
station is a special case of the same lifecycle (section 12). Version 1 of
this contract is the lifecycle of a station only (section 7.2).

The contract is written by the one-table method. Section 3 holds the single
lifecycle table: rows are states, columns are events. Every other section
defines vocabulary used by the cells (records, proofs, refusal codes, gates,
clocks) or states a rule that names the cells that carry it. No section
describes a second sequence of states. Where a section and the table disagree,
the table wins and the section is a defect.

This file defines no grant format, no wire schema and no file bytes. It states
where existing contracts attach.

Every rule carries one of four marks:

- a source key of section 1.1 in brackets: the rule restates that source;
- `DEC Dn`, `ADD x` or `RUL-n`: the rule is decided by the contract owner or by
  a ruling supplied to this contract (section 1.1);
- `NEW` or `PROPOSED`: the rule is proposed here; the reason follows;
- `OPEN OQn`: the rule is undecided; section 15 holds the question and the
  decider.

### 1.1 Source keys

| Key | Source |
| --- | --- |
| C24 "clause" | [CIP-0024](../cips/CIP-0024-agent-stations.md) on base `264244b321c7a2272450fc29bd9952f988d746d7`, by section title; "dec N" is item N of "Owner decisions". |
| C32 "clause" | [CIP-0032](../cips/CIP-0032-native-a2a-station-link.md), by section title. |
| HLnn | [Managed-home leases](home-leases.md), requirement HLnn; "HL observer" is its section "Independent observer before bind". |
| ENV n | [Environments protocol](environments.md), section n. |
| UM n | relux-works/swarma-user-manager `spec/stations-v0.md`, section n, at commit `04fe2b767ebbce15a4d2e7fa3b11738c41856609`. |
| GJ n | relux-works/swarma-user-manager `spec/generation-journal.md`, section n, same commit. |
| HP n | relux-works/swarma-user-manager `spec/helper.md`, section n, same commit; "HP 7 R-x" is the named rule x of its section 7. |
| BKnn "title" | relux-works/swarma-docs `book/ru`, chapter file number nn, at commit `942a07f12e478841c483a624e94dc47100bb7571`. Section titles are English renderings of the Russian headings; section 16 lists the files and heading lines. |
| DF A, DF B.n, DF C | The dispatcher field inventory supplied as an input to this contract (digest prefix `ef4ab4eae619`), which reports swarma-dispatcher main `85a47091`. The dispatcher repository itself was not read. |
| DEC Dn | Decision n (D1 to D12) of the contract owner for the first fix round of this file. |
| ADD A.n, ADD B, ADD C | The contract owner's addendum on the hand-over from the action profile: items A.1 to A.5, B and C. |
| AP n | Row n of the comparison "what the action profile hands to the station contract" supplied with that addendum. The action profile (LIP-0030) and LIP-0013 were not read; they are cited only as that comparison quotes them. |
| RUL-1 | Ruling: one OS account is one message author at the key holder; the bridge runs under the one shared messaging account. |
| RUL-2 | Ruling: J1 is the grant checker behind the message origin; the dispatcher consumes the validated binding; revocation reaches a running session through that checker's feed. |
| RUL-3 | Ruling: the agent account holds no carrier credential; the hand-over seam is the bridge's local submit endpoint. |
| RUL-4 | Ruling: the action profile covers the authority of a session; the life of the process is this contract's. |
| OWN-KS, OWN-DI, OWN-CR, OWN-UM | Statements by the owners of the key service, the dispatcher, curator-run and the user manager on their own rows of this file, supplied as inputs. The repositories behind them were not read. |
| NEW, PROPOSED | Not in any source; the reason follows the mark. |

### 1.2 Services

The table names exactly these services. "launcher" alone always means the
privileged user launcher; CIP-0024 and HL05 use the word "launcher" for
curator-run, and this file does not.

| Abbr | Service | Role in one line |
| --- | --- | --- |
| CRO | curator-run, station operation | Runs outside the station account, in the requester's account, for the party responsible for the station. It is a client of the dispatcher: it proposes transitions of section 3 and commits none (section 1.3). Its gate checks are advice only and produce no contract code [DEC D2; OWN-CR]. |
| CRX | curator-run, executor | Runs inside the station account after the privilege transition. It is part of the station. It commits nothing and evaluates no gate: a station cannot attest its own platform controls [DEC D2; OWN-CR; HP 7 "D-EXECUTOR"]. |
| UM | user manager | Creates, bumps and removes accounts; stops an account and proves absence [UM 1; BK05 "Two narrow privileged entries"; OWN-UM]. |
| LA | launcher | Starts one approved program under an active account and writes the start receipt; authoritative evaluator of the profile digests and the home skeleton [BK05 "Transition from root to agent"; HP 7; DEC D3]. |
| DI | dispatcher | Holds the authoritative station state record (section 1.3), the slot table and the capacity claims, under its own service account, in a protected state directory reached over a socket whose kernel peer is checked; owns the physical start and stop authority; consumes the validated binding [BK07 "Dispatcher and the one-shot transaction"; BK07 "Workbench"; RUL-2]. |
| GC | grant checker | The checker behind the message origin: chain view, observation, closure journal. It is the J1 join and the producer of the revocation feed [RUL-2; DEC D9]. |
| CU | Curator | Owns home content, composition, digests, the home lease, its independent process observer and the name latch record [C24 dec 9; HL01; HL observer]. |
| KS | key service | Holds the station keys and signs on request [C24 dec 1; BK06 "The kernel establishes the peer"]. |
| CB | credential broker | Holds enrolled credentials and issues bounded leases [C24 "Ownership and records"; BK09 "Mode without secrets at the agent"]. |
| MG | model gateway | Holds the leased model credential and forwards model requests for a station [BK09 "Model provider through the gateway"]. |
| AL | a2a link (message bridge) | Runs under the one shared messaging account, never under an agent account. Holds the carrier credential and accepts outgoing signed envelopes at its local submit endpoint; checking a message before it could become work (J2) is no part of version 1 (section 11) [BK24 "What the bridge consists of"; RUL-1; RUL-3]. C24 dec 6 (a station's own a2a daemon and client per identity) is carried only in section 8's station-link rows, not for the shared account. |
| SH | session host | Owns the logical session, the input queue and the input fence, holds liveness of the logical session and reports it (including process exit) to DI, and owns no station state record [BK07 "Service, runner and the single writer"; BK07 "Wake-up and context transfer"]. |

### 1.3 The station state record

SR1. The state of a station is one value in one record, the station state
record. Its single owner and single writer is DI, as effect owner of the
physical start and stop, under its own service account, in a protected state
directory reached over a socket whose kernel peer is checked. The record
carries the lifecycle state, a monotonically increasing state version, the
records of section 4.1 (including the start and stop journal entries, the
operation identities and the unknown-outcome reconciliation entries), the
open absence debts (U1) and the capability flags (R24).
The station description (environment, model, profile, clone and identity as
raised) lives in the workbench registry on the board and is read-only to DI;
it decides no cell. SH holds liveness and reports it and owns no record of
this section. Nobody else writes this record. No record that the requester's
account can write is the station state: a process under the requester's
account that edits a record file directly produces no state that an effect
owner accepts, and CRO holds at most a read cache. This closes OQ18
[BK07 "Workbench"; BK07 "Wake-up and context transfer"; DEC D1 as amended by
the OQ18 ruling; OWN-DI; OWN-CR]. NEW in DEC D1's original mark, decided by
that ruling: no source before it names one owner of the station state.

SR2. Every allowed cell of section 3 is one compare-and-set on the state
version, committed by DI together with the record, and only with the record,
the cell names; that set is at exactly one place, the end of the cell, after
its gate set has been evaluated on the version read. A proposal from a
requester or from CRO carries the expected version it read; the comparison
of that expected version with the version at DI is a read, not the set. Two
transitions attempted from one state version: exactly one commits. The loser
is defined for every kind of event: for a proposal that carries an expected
version, DI returns `station_state_stale`, returns no gate verdict evaluated
above the failed set, changes nothing, and the proposer re-reads; for an
event reported by another service, which carries no expected version, a lost
set is not a refusal and is never returned to the reporter: DI queues the
event in its journal and commits it against the state it re-reads, and the
event is consumed only by that commit. Delivered-once and host-wide events
(section 2) and every observation reading take the second form, so a reading
is recorded whatever the version it raced [DEC D1 as amended].

SR3. No other service commits a station state. This rule governs every effect
a cell of section 3 names; maintenance that no cell names and that changes no
lifecycle state (grant, binding and attestation renewal, K2) is governed by
its owning contract and reaches this record only as a capability report where
it closes or opens a capability. CRO is a client that proposes
transitions to DI. UM, KS, CU, LA through DI, and every other service perform
an effect for a station only under an operation that DI recorded first, and
report the outcome to DI; the report is an event of section 2.2. Every effect
request carries the operation identity and, as its epoch, the state version
at which DI wrote that operation's record. The epoch of an operation is that
recording version for the whole operation: self-loop commits and phase
writes under the operation (for example the phases of R03, which are appends
under R03 and not state-version bumps) do not stale it. An effect owner
stores durably, before performing the effect, the highest operation epoch it
has accepted for that operation identity, and refuses a request whose
operation epoch is lower than the value stored for the same operation
identity or whose operation DI no longer shows open. Epochs are compared per
operation identity, never as one highest epoch per station: a stop operation
recorded inside a held row therefore fences nothing of the row's own open
operation (its P5 presentation, its R17 undo, its next step or its retry all
carry that operation's own identity and epoch). The owner's refusal after the
record is reported to DI and arrives as proof P4 in the row of the effect in
flight, carrying `station_state_stale` in its detail (section 2); only a
proposal that has written no record receives `station_state_stale` directly
[DEC D1 as amended]. Continuity: an epoch, being a journal position of DI's
state journal for the name, never repeats across a crash or a restore. A
restore or a fenced journal opens a new journal generation recorded ahead of
any earlier generation in DI's protected configuration, epochs compare as
(journal generation, position), and a DI that cannot prove its new generation
is ahead of every epoch it ever issued stays closed (section 17, daemon
configuration) and admits no cell but a hold. Loss or rollback never re-admits
a provision of a name whose reservation R00 cannot be proved absent by
inverse inventory of accounts, bindings and receipts; until that proof exists
the name is held, never absent again, and gate G1 refuses its provision with
`station_name_held`, evaluated by DI from that inverse inventory after any
journal generation change (section 4.4).

SR4. A start is atomic: DI commits [stopped x start] by the compare-and-set
of SR2 at the record line of section 6.2, and the physical start request
carries that operation's epoch and the execution identity of R03. DI owns the
start fence of each generation: closed from the generation's `active` append
until phase `start_requested` of R03 opens it for that one execution alone.
When the station commits any cell out of `starting`, the same commit closes
the fence for that execution and records the start as withdrawn. LA
revalidates fence, epoch and execution identity with DI immediately before
writing the start receipt and dropping privilege, under the generation lock:
a withdrawn, superseded or already-receipted execution starts nothing and is
refused with `station_state_stale` in the detail. Past that revalidation
point a start can no longer be withdrawn, and its process is handled only by
the ordinary reading, exit and stop cells [DEC D1 as amended; HP 7]. Before a
name's first provision, DI holds its durable reservation: [absent x provision]
is create-if-absent on the station name in DI's record store, writing R00 and
R01 in one commit; the losing create re-reads and is then answered by the row
it finds. So the first transition has a store record to race on even though
`absent` names no committed station record yet. [retired x provision] races
on the state version of the record `retired` retains, under the reservation
R00 that already exists for the name; it reuses that reservation and amends
its principal only under the recorded owner act of G1.

SR5. A read that only classifies (a journal read, an observation, a proof
check) is not an effect and needs no prior record. Between an outcome becoming
unknown and its record becoming durable, each effect owner's own rule holds
what it holds: a prepared or unknown home lease blocks [HL08], and an unknown
dispatcher record keeps its generation, account and quota [BK07 "Dispatcher
and the one-shot transaction"]. The station record adds no protection in that
window and removes none.

SR6. This record and DI's own session journal are one store under one owner:
for a standing station there is no second authoritative record. Where an
earlier text splits them, the dispatcher's journal decides both the cells of
section 3 and authority (the action profile's "session held" and its
clearance), and every slot clearance cites an entry of this record (R09),
never the reverse. On a fact both a board description and this record touch,
this record decides. Loss of the session journal is therefore loss or fencing
of this record's own store: the fence entry R23 is delivered once to every
station record that survives it, a name whose record does not survive is held
under SR3 by inverse inventory and is never read as absent, and no cell
reconstructs from a surviving board description a session the journal no
longer proves. This is the OQ18 ruling carried into SR1, and no part of OQ18
remains open.

## 2. Reading a cell

A cell has exactly one of three forms.

- `NEXT; DI; Rnn; GATE` - the transition is allowed. `NEXT` is the one next
  state. `DI` is the one service that commits it (SR2); a proposal by CRO or
  by a requester is not a commit. `Rnn` (section 4.1) is the durable record
  written in that commit, before the effect it names. `GATE` is the closed
  gate set of section 4.4, or `no gate` when the event is an observation or
  a recovery step that is recorded and never refused.
- `refused: code` - the pair is not allowed; nothing changes; DI returns the
  closed code to the proposer. A refusal of a reported event is recorded by
  DI and spends the report as section 4.4 states; `station_state_stale` is
  never such a refusal (SR2).
- `cannot occur: reason` - the event cannot be produced in this state.

A gate code marked "before the record" in section 4.4 refuses the cell and
leaves the state unchanged. A gate code marked "after the record" is the
refusal of an effect owner under the recorded operation: it is a known outcome,
never an unknown one; it arrives as proof P4 in the row of the effect in
flight and carries the same code.

A replay of an operation with the same operation identity and the same
arguments is not a new event: it returns the recorded outcome and the current
state. A replay with different arguments refuses `station_operation_conflict`
[UM 3; HL06; C24 "Lifecycle and failure handling", create].

Host-wide events (host reboot, session journal lost, capability report) are
delivered once to every existing station record of the host. Delivered once
means DI consumes each only by a commit against the row it re-reads (SR2):
the loser of a race for such an event is never the event itself. `retired`
is the one exception to "every station goes to a held row" on a lost journal:
it has no account and no P1 to take, stays `retired` on R23, and opens no
debt; `absent` has no record to deliver to until R00 exists.

### 2.1 States

One line each; the transitions are only in section 3. In prose, "a held row"
always means one of the nine rows whose name starts with `held:`; the bare word
is never used for a station state. The action profile's authority state of an
occupied slot is always written "session held" [ADD B].

| State | Meaning |
| --- | --- |
| `absent` | No committed station record exists for the name yet; [absent x provision] creates it by create-if-absent with reservation R00 (SR4), so no account, generation, home or binding can precede that commit. |
| `provisioning` | A create is in flight under R01: an account and a `creating` generation may already exist. |
| `provisioned` | The account exists at an `active` generation and the home skeleton is installed and verified; the enroll inventory of R02 is not complete, so the station is not usable; nothing runs. |
| `enrolling` | An enroll is in flight under R02: some bindings may already be durable. |
| `stopped` | The enroll inventory is complete, nothing runs, no home lease is held, and absence is recorded by R09. |
| `starting` | A start is in flight under R03: the home lease is prepared, the physical start is requested or about to be, and no incarnation is bound. |
| `running` | Exactly one process incarnation is bound to the home lease (R04). |
| `stopping` | A stop is in force: the input fence and the start fence are closed and the absence proof is awaited. |
| `updating` | An approved profile update is in flight under R12. |
| `bumping` | A same-account generation bump is in flight under R14. |
| `retiring` | Forward-only removal is committed; nothing is admitted for the generation. |
| `retired` | No account or home exists for the name; the station record, the name record and the tombstones are retained, with its origin (`retirement` or `create_no_effect`, from R16 or R18) and the principal and last key identifiers it retains. Reached by a retirement or by a create that did not happen; late exit or boot reports name an R03 and are recorded only for the `retirement` origin that can have one. |
| `held:provision` | Unknown outcome of a create, or an open absence debt during a create. |
| `held:enroll` | Unknown or partial outcome of an enroll, or an open absence debt during an enroll. |
| `held:account` | Absence is unknown for an account that is not enrolled. |
| `held:start` | Unknown outcome of a start: a process may or may not exist. |
| `held:live` | The bound incarnation cannot be read. |
| `held:stop` | Absence is unknown for an enrolled station. |
| `held:update` | Unknown or partial outcome of a profile update, or an open absence debt during one. |
| `held:bump` | Unknown or stranded outcome of a generation bump. |
| `held:retire` | Unknown outcome of a retirement step. |

Why the rows differ from the minimum state list (all NEW, each with its
reason):

- `enrolled` and `stopped` are one row, `stopped`: CIP-0024 ends create at a
  "usable, stopped station" [C24 "Lifecycle and failure handling", create],
  and the first start is made as safe as a later one by the never-started
  evidence P5 that the entry into `stopped` requires [DEC D4].
- `provisioning`, `enrolling`, `updating` and `bumping` are rows of their own,
  so that no effect in flight is hidden inside a quiet state [DEC D5].
- The held case is split into nine rows, so that every exit of every held case
  is a cell of the same table.
- `retiring` is a row: the generation journal makes `retiring` a commit point
  after which recovery only moves forward [GJ 4; UM 3; UM 5].
- Follow-up work inside a standing station has no row, column or record in
  version 1; the proposed run model is outside this contract (section 7.2).

### 2.2 Events

Each event is reported to DI by the one service named, or proposed to DI by
CRO for a requester; DI alone commits the cell (SR2). Gate 3, the identity
check of gate set G2 and the name-latch line of R02 are PROPOSED with section
9.2; until its two confirmations are recorded, no cell refuses solely for
the latch's absence, only for a present latch that mismatches.

| Event | Reported by | Meaning |
| --- | --- | --- |
| provision | the requester | Request to create the account, generation and home skeleton for a station name. |
| enroll | the requester | Request to complete the enroll inventory of a provisioned station: name latch, key bindings, message link, owner binding, slot entry, never-started evidence P5. |
| start | the requester | Request to start a process incarnation; a restart is the same event (section 6). |
| proof: incarnation match | CU | CU presents proof P2 for the start of R03. A bind that CU refused is not this event: an unequal reading is "process appears" and an unreadable one is "liveness reading missed". |
| process appears | CU or UM | A kernel reading shows a task with the account in any uid field that the state does not explain. In `running` that is a task outside the resource group of the bound execution [BK05 "Load: a resource group per generation"]; in every other state it is any task not covered by a presented P2. |
| process exits | SH | SH reports that the lead process started under R03 or bound by R04 exited. SH owns no record for it; DI records R05. |
| liveness reading missed | CU | A scheduled reading of the bound tuple, or the reading of a bind attempt, is missing or unreadable. |
| liveness restored | CU | The first reading equal in all four fields to the tuple of R04 after a missed reading recorded since that bind. A missed bind-attempt reading in `starting` is not since the bind, so this event cannot fall in `running`. Equal readings with no such missed reading before them stay in CU's reading log and are not events. |
| stop requested | the requester, or DI as the actor of U5, of a clock of section 4.5 or of section 7.1 | An authorized stop of the station; section 7.1 lists every trigger and its bound. Its record (R08, or the entering record of a cell into `stopping`) carries the stop operation identity the coming P1 must name. |
| stop confirmed | UM | UM presents the absence proof P1, alone or inside the never-started evidence P5, naming the stop operation (or the R02, R14 or retire operation) it answers and the quiet interval it covers. |
| starter crash | the restarted service, or DI for it | A service that owned an operation, an effect, an execution or a bind attempt of this station died or restarted: CRO, DI, LA, UM, CU as observer, KS or SH. A dispatcher restart is this column and never "capability report". |
| host reboot | DI | The host restarted; the boot identifier DI reads changed. |
| capability report | KS, MG, AL, SH, CB, UM, or DI for GC | A service the station depends on reports one capability of the station closed or open again, including at its own restart [ADD A.5]. The capabilities are: signing, carrier channel, model forwarding, input delivery, session authority, qualification. GC's revocation, expiry, seal and unreadable-state reports for the session grant, UM's report of a revoked qualification (as the capability qualification, with DI as the actor of the stop that follows), GC's and any service's verified-time-lost report, and DI's policy-removed report enter only by this column (as session authority, qualification or a time closure recorded in R24) and by the stop cell DI then commits under section 7.1; there is no other revocation path into the table. |
| session journal lost | DI | The dispatcher's session journal is lost, fenced or restored from a copy [ADD A.4]. |
| profile update approved | the requester, which may be the station itself | An approved release newer than the installed pin is to be installed [C24 dec 3]. A station's own trigger is a proposal to DI through its caller channel, evaluated by G6 like any other requester's, installs only an already-approved release, and is a no-op refusal `station_release_not_approved` when none exists; in a running row it refuses `station_busy` and may be proposed again once stopped. The station installs nothing itself. |
| key rotation | the requester | Request to bind the station name to a new key. |
| generation bump | the requester | Request for the same-account generation bump [UM 6]. |
| retire | the requester | Request to remove the station. |
| unknown or stranded outcome | DI, from a clock of section 4.5 or an owner's report | The effect in flight may or may not have happened (a lost reply, an expired bound, missing or contradictory evidence), or it ended in a terminal refusal after its forward-only commit point, or a multi-owner effect is known partial (at least one line recorded complete and at least one line terminally refused). A terminal refusal of a retirement step that UM marks repeatable with no trace is not this event: it is "proof: effect did not happen" and the step runs again under R20; a terminal refusal UM marks not repeatable is stranded and is this event. |
| proof: effect completed | DI, reading the effect owner | Proof P3 that the one recorded effect the proof names completed. In a held row it answers only the operation whose hold the row is (R01, R02, R03, R12, R14 or R15), never a stop operation; a stop's outcome arrives only as "stop confirmed" or as unknown. |
| proof: effect did not happen | DI, reading the effect owner | Proof P4 that the one recorded effect the proof names did not happen, was refused or was rolled back, under the same one-effect rule. A proof naming the stop operation, or any effect other than the row's operation, refuses `station_proof_mismatch` in G13 and moves nothing. |
| operator teardown order | the operator | Authenticated operator order to drive a held station down (U3). |

## 3. The lifecycle table

Gate 3, gate set G2's identity
check and the name-latch line of R02 are PROPOSED with section 9.2; until its
two confirmations are recorded, no cell refuses solely for their absence.
The table has 21 states by 22 events: 462 cells. In `held:start` and
`held:live` no stop operation can be open (a stop request
leaves those rows for `stopping`), so their "stop confirmed" cells refuse
`station_proof_unexpected` exactly as `starting` does, and their way to
`stopped` is [row x stop requested] then [stopping x stop confirmed]; in
`held:stop` a stop operation from `stopping` may still be open, and G11
admits a P1 there only when it names the operation that row awaits.

| State | provision | enroll | start | proof: incarnation match | process appears | process exits | liveness reading missed | liveness restored | stop requested | stop confirmed | starter crash | host reboot | capability report | session journal lost | profile update approved | key rotation | generation bump | retire | unknown or stranded outcome | proof: effect completed | proof: effect did not happen | operator teardown order |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| absent | provisioning; DI; R01; G1 | refused: station_absent | refused: station_absent | refused: station_proof_unexpected | cannot occur: no account uid is reserved for the name | cannot occur: no start was ever requested for the name | cannot occur: no incarnation is bound | cannot occur: no missed reading is recorded | refused: station_absent | refused: station_proof_unexpected | cannot occur: no operation or execution of this station is in flight | cannot occur: no station record exists to deliver the event to | cannot occur: no station record exists to deliver the event to | cannot occur: no station record exists to deliver the event to | refused: station_absent | refused: station_absent | refused: station_absent | refused: station_absent | cannot occur: no effect is in flight in this row | refused: station_proof_unexpected | refused: station_proof_unexpected | refused: station_not_held |
| provisioning | refused: station_busy | refused: station_busy | refused: station_busy | refused: station_proof_unexpected | held:provision; DI; R06; no gate | cannot occur: no start was requested for this generation | cannot occur: no incarnation is bound | cannot occur: no missed reading is recorded | refused: station_not_running | refused: station_proof_unexpected | provisioning; DI; R10; no gate | provisioning; DI; R11; no gate | provisioning; DI; R24; no gate | held:provision; DI; R23; no gate | refused: station_busy | refused: station_not_enrolled | refused: station_busy | refused: station_busy | held:provision; DI; R17; no gate | provisioned; DI; R18; G13 | retired; DI; R18; G13 | refused: station_not_held |
| provisioned | refused: station_exists | enrolling; DI; R02; G2 | refused: station_not_enrolled | refused: station_proof_unexpected | held:account; DI; R06; no gate | cannot occur: no start was requested for this generation | cannot occur: no incarnation is bound | cannot occur: no missed reading is recorded | refused: station_not_running | refused: station_proof_unexpected | cannot occur: no operation or execution of this station is in flight | provisioned; DI; R11; no gate | provisioned; DI; R24; no gate | held:account; DI; R23; no gate | refused: station_not_enrolled | refused: station_not_enrolled | refused: station_not_enrolled | retiring; DI; R15; G5 | cannot occur: no effect is in flight in this row | refused: station_proof_unexpected | refused: station_proof_unexpected | refused: station_not_held |
| enrolling | refused: station_exists | refused: station_busy | refused: station_not_enrolled | refused: station_proof_unexpected | held:enroll; DI; R06; no gate | cannot occur: no start was requested for this generation | cannot occur: no incarnation is bound | cannot occur: no missed reading is recorded | refused: station_not_running | enrolling; DI; R09; G11 | enrolling; DI; R10; no gate | enrolling; DI; R11; no gate | enrolling; DI; R24; no gate | held:enroll; DI; R23; no gate | refused: station_busy | refused: station_not_enrolled | refused: station_busy | refused: station_busy | held:enroll; DI; R17; no gate | stopped; DI; R18; G13 | provisioned; DI; R18; G13 | refused: station_not_held |
| stopped | refused: station_exists | refused: station_already_enrolled | starting; DI; R03; G3 | refused: station_proof_unexpected | held:stop; DI; R06; no gate | stopped; DI; R05; no gate | cannot occur: no incarnation is bound | cannot occur: no missed reading is recorded | refused: station_not_running | refused: station_proof_unexpected | cannot occur: no operation or execution of this station is in flight | stopped; DI; R11; no gate | stopped; DI; R24; no gate | held:stop; DI; R23; no gate | updating; DI; R12; G6 | refused: station_rotation_unavailable | bumping; DI; R14; G8 | retiring; DI; R15; G5 | cannot occur: no effect is in flight in this row | refused: station_proof_unexpected | refused: station_proof_unexpected | refused: station_not_held |
| starting | refused: station_exists | refused: station_already_enrolled | refused: station_incarnation_exists | running; DI; R04; G10 | held:start; DI; R06; no gate | stopping; DI; R05; no gate | starting; DI; R06; no gate | cannot occur: no bound tuple exists to compare a reading with | stopping; DI; R08; G4 | refused: station_proof_unexpected | starting; DI; R10; no gate | stopping; DI; R11; no gate | starting; DI; R24; no gate | held:stop; DI; R23; no gate | refused: station_busy | refused: station_rotation_unavailable | refused: station_busy | refused: station_busy | held:start; DI; R17; no gate | refused: station_proof_unexpected | stopping; DI; R18; G13 | refused: station_not_held |
| running | refused: station_exists | refused: station_already_enrolled | refused: station_incarnation_exists | refused: station_proof_unexpected | held:stop; DI; R06; no gate | stopping; DI; R05; no gate | held:live; DI; R06; no gate | cannot occur: a missed reading since the bind would have left this row for held:live, and a bind-attempt reading is not since the bind | stopping; DI; R08; G4 | refused: station_proof_unexpected | running; DI; R10; no gate | stopping; DI; R11; no gate | running; DI; R24; no gate | held:stop; DI; R23; no gate | refused: station_busy | refused: station_rotation_unavailable | refused: station_busy | refused: station_busy | cannot occur: no recorded lifecycle effect is in flight in this row | refused: station_proof_unexpected | refused: station_proof_unexpected | refused: station_not_held |
| stopping | refused: station_exists | refused: station_already_enrolled | refused: station_incarnation_exists | refused: station_proof_unexpected | stopping; DI; R06; no gate | stopping; DI; R05; no gate | stopping; DI; R06; no gate | stopping; DI; R06; no gate | refused: station_busy | stopped; DI; R09; G11 | stopping; DI; R10; no gate | stopping; DI; R11; no gate | stopping; DI; R24; no gate | held:stop; DI; R23; no gate | refused: station_busy | refused: station_rotation_unavailable | refused: station_busy | refused: station_busy | held:stop; DI; R17; no gate | refused: station_proof_unexpected | refused: station_proof_unexpected | refused: station_not_held |
| updating | refused: station_exists | refused: station_already_enrolled | refused: station_busy | refused: station_proof_unexpected | held:update; DI; R06; no gate | updating; DI; R05; no gate | cannot occur: no incarnation is bound | cannot occur: no missed reading is recorded | refused: station_not_running | refused: station_proof_unexpected | updating; DI; R10; no gate | updating; DI; R11; no gate | updating; DI; R24; no gate | held:update; DI; R23; no gate | refused: station_busy | refused: station_rotation_unavailable | refused: station_busy | refused: station_busy | held:update; DI; R17; no gate | stopped; DI; R18; G13 | stopped; DI; R18; G13 | refused: station_not_held |
| bumping | refused: station_exists | refused: station_already_enrolled | refused: station_busy | refused: station_proof_unexpected | held:bump; DI; R06; no gate | bumping; DI; R05; no gate | cannot occur: no incarnation is bound | cannot occur: no missed reading is recorded | refused: station_not_running | bumping; DI; R09; G11 | bumping; DI; R10; no gate | bumping; DI; R11; no gate | bumping; DI; R24; no gate | held:bump; DI; R23; no gate | refused: station_busy | refused: station_rotation_unavailable | refused: station_busy | refused: station_busy | held:bump; DI; R17; no gate | provisioned; DI; R18; G13 | stopped; DI; R18; G13 | refused: station_not_held |
| retiring | refused: station_retiring | refused: station_retiring | refused: station_retiring | refused: station_proof_unexpected | retiring; DI; R06; no gate | retiring; DI; R05; no gate | cannot occur: no incarnation is bound | cannot occur: no missed reading is recorded | refused: station_retiring | retiring; DI; R09; G11 | retiring; DI; R10; no gate | retiring; DI; R11; no gate | retiring; DI; R24; no gate | held:retire; DI; R23; no gate | refused: station_retiring | refused: station_retiring | refused: station_retiring | refused: station_retiring | held:retire; DI; R17; no gate | retired; DI; R16; G12 | retiring; DI; R20; G13 | refused: station_not_held |
| retired | provisioning; DI; R01; G1 | refused: station_retired | refused: station_retired | refused: station_proof_unexpected | cannot occur: no account uid is reserved for the name | retired; DI; R05; no gate | cannot occur: no incarnation is bound | cannot occur: no missed reading is recorded | refused: station_retired | refused: station_proof_unexpected | cannot occur: no operation or execution of this station is in flight | retired; DI; R11; no gate | retired; DI; R24; no gate | retired; DI; R23; no gate | refused: station_retired | refused: station_retired | refused: station_retired | refused: station_retired | cannot occur: no effect is in flight in this row | refused: station_proof_unexpected | refused: station_proof_unexpected | refused: station_not_held |
| held:provision | refused: station_held | refused: station_held | refused: station_held | refused: station_proof_unexpected | held:provision; DI; R06; no gate | cannot occur: no start was requested for this generation | cannot occur: no incarnation is bound | cannot occur: no missed reading is recorded | held:provision; DI; R08; G4 | held:provision; DI; R09; G11 | held:provision; DI; R10; no gate | held:provision; DI; R11; no gate | held:provision; DI; R24; no gate | held:provision; DI; R23; no gate | refused: station_held | refused: station_held | refused: station_held | refused: station_held | held:provision; DI; R17; no gate | provisioned; DI; R18; G13 | retired; DI; R18; G13 | retiring; DI; R19; G14 |
| held:enroll | refused: station_held | refused: station_held | refused: station_held | refused: station_proof_unexpected | held:enroll; DI; R06; no gate | cannot occur: no start was requested for this generation | cannot occur: no incarnation is bound | cannot occur: no missed reading is recorded | held:enroll; DI; R08; G4 | held:enroll; DI; R09; G11 | held:enroll; DI; R10; no gate | held:enroll; DI; R11; no gate | held:enroll; DI; R24; no gate | held:enroll; DI; R23; no gate | refused: station_held | refused: station_held | refused: station_held | refused: station_held | held:enroll; DI; R17; no gate | stopped; DI; R18; G13 | provisioned; DI; R18; G13 | retiring; DI; R19; G14 |
| held:account | refused: station_held | refused: station_held | refused: station_held | refused: station_proof_unexpected | held:account; DI; R06; no gate | cannot occur: no start was requested for this generation | cannot occur: no incarnation is bound | cannot occur: no missed reading is recorded | held:account; DI; R08; G4 | provisioned; DI; R09; G11 | held:account; DI; R10; no gate | held:account; DI; R11; no gate | held:account; DI; R24; no gate | held:account; DI; R23; no gate | refused: station_held | refused: station_held | refused: station_held | refused: station_held | held:account; DI; R17; no gate | refused: station_proof_unexpected | refused: station_proof_unexpected | retiring; DI; R19; G14 |
| held:start | refused: station_held | refused: station_held | refused: station_held | running; DI; R04; G10 | held:start; DI; R06; no gate | stopping; DI; R05; no gate | held:start; DI; R06; no gate | cannot occur: no bound tuple exists to compare a reading with | stopping; DI; R08; G4 | refused: station_proof_unexpected | held:start; DI; R10; no gate | stopping; DI; R11; no gate | held:start; DI; R24; no gate | held:stop; DI; R23; no gate | refused: station_held | refused: station_held | refused: station_held | refused: station_held | held:start; DI; R17; no gate | held:start; DI; R17; G13 | stopping; DI; R18; G13 | stopping; DI; R19; G14 |
| held:live | refused: station_held | refused: station_held | refused: station_held | refused: station_proof_unexpected | held:stop; DI; R06; no gate | stopping; DI; R05; no gate | held:live; DI; R06; no gate | running; DI; R06; no gate | stopping; DI; R08; G4 | refused: station_proof_unexpected | held:live; DI; R10; no gate | stopping; DI; R11; no gate | held:live; DI; R24; no gate | held:stop; DI; R23; no gate | refused: station_held | refused: station_held | refused: station_held | refused: station_held | cannot occur: no recorded lifecycle effect is in flight in this row | refused: station_proof_unexpected | refused: station_proof_unexpected | stopping; DI; R19; G14 |
| held:stop | refused: station_held | refused: station_held | refused: station_held | refused: station_proof_unexpected | held:stop; DI; R06; no gate | held:stop; DI; R05; no gate | held:stop; DI; R06; no gate | held:stop; DI; R06; no gate | stopping; DI; R08; G4 | stopped; DI; R09; G11 | held:stop; DI; R10; no gate | stopping; DI; R11; no gate | held:stop; DI; R24; no gate | held:stop; DI; R23; no gate | refused: station_held | refused: station_held | refused: station_held | refused: station_held | held:stop; DI; R17; no gate | refused: station_proof_unexpected | refused: station_proof_unexpected | stopping; DI; R19; G14 |
| held:update | refused: station_held | refused: station_held | refused: station_held | refused: station_proof_unexpected | held:update; DI; R06; no gate | held:update; DI; R05; no gate | cannot occur: no incarnation is bound | cannot occur: no missed reading is recorded | held:update; DI; R08; G4 | held:update; DI; R09; G11 | held:update; DI; R10; no gate | held:update; DI; R11; no gate | held:update; DI; R24; no gate | held:update; DI; R23; no gate | refused: station_held | refused: station_held | refused: station_held | refused: station_held | held:update; DI; R17; no gate | stopped; DI; R18; G13 | stopped; DI; R18; G13 | retiring; DI; R19; G14 |
| held:bump | refused: station_held | refused: station_held | refused: station_held | refused: station_proof_unexpected | held:bump; DI; R06; no gate | held:bump; DI; R05; no gate | cannot occur: no incarnation is bound | cannot occur: no missed reading is recorded | held:bump; DI; R08; G4 | held:bump; DI; R09; G11 | held:bump; DI; R10; no gate | held:bump; DI; R11; no gate | held:bump; DI; R24; no gate | held:bump; DI; R23; no gate | refused: station_held | refused: station_held | refused: station_held | refused: station_held | held:bump; DI; R17; no gate | provisioned; DI; R18; G13 | stopped; DI; R18; G13 | retiring; DI; R19; G14 |
| held:retire | refused: station_held | refused: station_held | refused: station_held | refused: station_proof_unexpected | held:retire; DI; R06; no gate | held:retire; DI; R05; no gate | cannot occur: no incarnation is bound | cannot occur: no missed reading is recorded | held:retire; DI; R08; G4 | held:retire; DI; R09; G11 | held:retire; DI; R10; no gate | held:retire; DI; R11; no gate | held:retire; DI; R24; no gate | held:retire; DI; R23; no gate | refused: station_held | refused: station_held | refused: station_held | refused: station_held | held:retire; DI; R17; no gate | retired; DI; R16; G12 | retiring; DI; R20; G13 | retiring; DI; R19; G14 |

Below, a cell is cited as [state x event]. "The running rows" means `running`
and `held:live`.

## 4. Vocabulary of the cells

### 4.1 Durable records

Every record is an entry of the station state record, written by DI in the
same compare-and-set that commits the cell (SR2), before the effect that the
third column names. The fourth column lists the write-ahead records that the
effect owners MUST hold in their own stores before their own effects. This
file names the records and their order; their bytes belong to the owning
contracts. The record identifiers and their contents, R00 included, are NEW:
no source defines them. R07, R21 and R22 are not used in version 1; their
identifiers are reserved for the proposed companion records of section 7.2
and no cell writes or reads them. A cell that enters `stopping` writes, as
part of the record it names (R05, R08, R11, R18 for a start, or R19), the stop
operation: its identity (the record's operation identity), the generation,
and the request to UM for the stop effect whose P1 must name that identity.
There is no entry into `stopping` that awaits a proof nobody requested. At
most one stop operation of a station is open at a time: a stop-requested
commit, and a record entering `stopping`, creates that operation only where
none is open; where one is open the commit records its request against the
open operation's identity and writes no second operation. R09 closes every
open stop operation of the station (R09).

| Id | Content | Precedes | Effect owners and their own write-ahead | Source |
| --- | --- | --- | --- | --- |
| R00 | Name reservation: the station name, the principal the provision grant names, and the journal generation and position of the create-if-absent commit. Written with R01 in that one commit (SR4) and retained for the life of the name, through `retired`. | The create request of R01 and every later use of the name. | DI: the store entry the create-if-absent races on. | NEW (SR4) |
| R01 | Create operation: operation identity, station name, host, project, profile pin, the reference of the validated binding, and for a re-provision of a retired name either the principal match against R00 and R16 or the recorded owner act that reassigns the name. | The request for an account. | DI: request and effect identity. UM: caller-scoped effect intent and the `creating` append before any account mutation; `active` only after identity, skeleton, persistence denial and static deny are verified. | C24 "Lifecycle and failure handling", create; UM 3; UM 4 |
| R02 | Enroll operation: the closed enroll inventory, one line per binding with its owner: name latch (CU), one key binding per purpose (KS, each line recording the key identifier of that purpose), message link (AL), owner binding (DI: the principal copied from the validated binding of R01, never named by the proposer), slot entry (DI), and never-started evidence (UM: P5 for this generation, requested by DI under this record once the generation is `active`, after every other line that can run a task, and presented through [enrolling, held:enroll x stop confirmed]). After a bump the lines classify as: latch record survives and its name file is published again byte-identical (made again, from the record); key bindings are made before `active` under R14 and only confirmed here, with the same key identifiers recorded per purpose against the latest R02 or R16 (KY6); message link lived in the destroyed home and is made again; owner binding and slot entry live in DI's record, survive, and are only confirmed; P5 is requested again for the new generation. | Every binding, and DI's request for P5. | CU: latch record in manager state before the name file is published. KS: binding record for the exact (uid, generation). AL: registry entry before a station link is emitted [C32 "Recommendation"]. DI: slot table entry, owner binding from R01's binding, and the P5 request. UM: the P5 evidence over LA's receipts, P1 and DI's fence record (SR4). | C24 "Lifecycle and failure handling", create; C24 "Ownership and records"; UM 6.2; BK24 "Owner channel"; DEC D4 |
| R03 | Start operation: new operation, request, execution and lease-request identities, the state version as epoch, the binding reference, the release identity of the last completed R12 (or the provision pin of R01 where no R12 completed), and, where a human stop (an R08 whose reason is the owner stop of section 7.1) stands, the lifting of that stop by this start where gate 11 admits it; phase `lease_requested` before the first lease acquire [HL21]; phase `start_requested` before the physical-start request, opening the start fence for this execution alone (SR4). Phases are appends under R03 and move no state version (SR3). NEW phase `start_requested`: without it a recovery cannot tell whether a request was sent. | The lease acquire and the physical start. | CU: prepared lease record, blocking before the acquire is acknowledged [HL06]. DI: request and effect identity with the consumed binding. LA: start receipt with the execution number, written as root before privileges are dropped; a second start of the same execution is rejected [BK05 "Transition from root to agent"]. | HL21; HL06; BK07 "Dispatcher and the one-shot transaction" |
| R04 | Bound holder: the digest of proof P2 and the exact `{pid, uid, boot_id, start_time}`. | The opening of the input fence. | CU: bound lease [HL07]. SH: the fence stays closed until R04 exists. | HL07; HL22; HL observer |
| R05 | Exit observation from SH, with the incarnation it concerns; where its cell enters `stopping`, it carries the stop operation (section 4.1 head). | Where its cell enters `stopping`, the request for the absence proof, which this record itself makes to UM; in a self-loop row it precedes nothing but the record. | DI: on an entry into `stopping` only, the journaled end of the session and the stop effect identity. UM: stop effect on that entry. | C24 "Lifecycle and failure handling"; BK05 "Load: a resource group per generation" |
| R06 | One observer reading: its class (unexplained process, missed, unreadable, restored), its producer and evidence digest, the origin state, the held case, and the effect identity or "none: observation". A reading of an unexplained process opens an absence debt (U1). | Any reaction to the reading. | CU or UM: the reading itself, kept in its own store. | HL08; HL observer; DEC D4 |
| R08 | Stop operation: operation identity, reason (section 7.1), requester, the incarnation and lease it targets. This is the operation a coming P1 names, except where another record entering `stopping` carries the stop operation (section 4.1 head). | The stop effect. The input fence and the start fence of the generation are closed first. | SH: fence closed. DI: stop effect; the journaled end of the session, and with it the clock `end_to_absence`, only where the cell enters `stopping`; in a held self-loop row this record requests the stop effect and writes no journaled end. UM: stop effect. | C24 "Lifecycle and failure handling", down; BK07 "Permission for a successor"; HP 4.7 |
| R09 | Absence acceptance: UM's proof P1 or P5 with the operation it names, its coverage, its quiet interval with both ends, boot identifier and the fences held. Its commit closes every open stop operation of the station. It answers only absence debts whose reading precedes the beginning of that interval, with both fences closed across the interval (U1); an acceptance merely written after a reading whose interval closed before it answers nothing. | The release of the home lease [HL09; HL10] and of the execution claim; in retirement, the removal of the home. | UM: its own absence record. CU: release event and tombstone. DI: claim release and the clearance of the slot, which cites this proof [AP 7]. | UM 5; UM 6.1; HL09; BK07 "Dispatcher and the one-shot transaction" |
| R10 | Recovery entry: the operation found, its recorded phase, the classification taken. It releases nothing. Where the classification is unknown, the event "unknown or stranded outcome" follows and writes R17. | Any resumed step. | Each effect owner reconciles its own journal before new work [UM 3; BK07 "Dispatcher and the one-shot transaction"]. | C24 "Lifecycle and failure handling"; HL21; HL22 |
| R11 | Boot record: the boot identifier now read and the one in R04 or R03; where its cell enters `stopping`, it carries the stop operation (section 4.1 head). | The request for the absence proof, which this record itself makes to UM where it carries a stop operation. | DI: where the cell enters `stopping`, the journaled end of the session and the stop effect identity; none in any other row. UM: stop effect on that entry. | HL05; BK07 "Wake-up and context transfer" |
| R12 | Update operation: approved release identity and the full control inventory with digests, and on P3 a completion mark. Only a completed R12 is the amendment record of the plan pins (section 9.1) and the release R03 and a later bump name; a rolled-back R12 amends nothing. | The first replaced control; the trust pin is published last. | CU: composition intent. UM: skeleton install effect through trusted descriptors. | UM 7; C24 "Platform controls and approved updates"; HL14 |
| R13 | Reserved: rotation record of the key service. No cell of station/1 writes it: the key service authorizes no rotation today [OWN-KS]. | Nothing in station/1. | KS, in a later unit. | OWN-KS |
| R14 | Bump operation: the target generation, and the three conditions that UM holds before the successor is `active`: account-wide absence (proved to this operation by [bumping x stop confirmed]), the complete external-object inventory, and the two key-service confirmations, which MUST carry for each purpose the same key identifier as the latest R02 or R16 records for the name under KY6; a confirmation with another identifier does not hold the condition and the bump cannot complete on it. The new home is installed at the release of the last completed R12, or at the provision pin of R01 where no R12 completed. A completed bump ends in `provisioned`; how each enroll line is treated there is in R02. | The request to bump. | UM: effect intent and the `retiring` append for the old generation before stop or reset. KS owner: re-admission and new binding confirmations. | UM 6; UM 6.1; UM 6.2 |
| R15 | Retire operation: the export obligation and how it is discharged (an operator waiver reference; a recorded export receipt counts as a discharge only from the decision recorded in OQ14, and no cell of this draft produces or verifies one), the obligations check, and for a one-task station the explicit release by the raising orchestrator (section 12). UM removes no home under this operation before its own P1 for the operation is accepted as R09 in `retiring`. | The request to retire. | UM: effect intent and the `retiring` append before stop or deletion; the stop and P1 of this operation before any home removal. | UM 5; C24 "Lifecycle and failure handling", retire |
| R16 | Retired acceptance: UM's terminal result `removed` after verified cleanup and account absence. | The release of the account claim and of the slot entry. The station record and the name record are retained, with the last key identifier per purpose. | UM: the `removed` append. DI: claim and slot release. | UM 5; GJ 4; BK06 "The account ends, the identity remains" |
| R17 | Hold record: held case, origin state, the effect and its identity, what was sent, what was observed, and any carried owner code. For a known partial enroll or update it carries the outcome of every inventory line and DI's undo request to each owner whose line completed under this operation alone; each undo request carries its own undo effect identity, recorded in this record for that line, and a later hold record for the same operation and line reuses the recorded undo identity and mints no second one, so an undo is never re-sent as a new effect under the operation's own identity. A line's undo is its owner's rollback of its own binding of this operation, and resources whose ownership is uncertain are never undone. A journal loss that lands a station in `held:stop` deliberately forgets the start outcome it fences: no later cell reconstructs it, and only P1 resolves the row. | Every effect, release and resumed step after it. Nothing is released by it. | none | C24 "Lifecycle and failure handling", unknown; HL08 |
| R18 | Proof acceptance: which proof (section 4.2), its producer, its evidence digest, its kind and carried code, the one effect identity it answers. A P4 for a create releases the account claim and the capacity charge of R01 on the entry into `retired` (the reservation R00 and the record stay). Where its cell enters `stopping` (a start that did not happen), it carries the stop operation (section 4.1 head). | The state change. | CU: lease release event where the proof allows it [HL09]. DI: where the cell enters `stopping`, the journaled end of the session and the stop effect identity. UM: stop effect on that entry. | HL09; HL10 |
| R19 | Operator order: the authenticated, exact-content operator act for this station; where its cell enters `retiring` it carries the export waiver and the disposition of open obligations that a retire would need at G5, and where its cell enters `stopping` it carries the stop operation (section 4.1 head). An R19 that enters `retiring` for a station with no session writes no journaled end and starts no `end_to_absence` clock: its absence acceptance is the R09 of [retiring x stop confirmed] under the retire operation, by that row's own path, so the retiring cell never waits silently for a clock nobody started. | The teardown. | UM: operator retire act with its recorded waiver where used [UM 5]; stop effect where the cell enters `stopping`. DI: journaled end where the cell enters `stopping`. | UM 2; UM 5; HL12; BK06 "The operator signs one action" |
| R20 | Forward step entry: a retirement step proved not done; the same effect identity runs it again. | The repeated step. | UM: its step log. | UM 3; UM 5 |
| R23 | Journal fence entry: the dispatcher's report that its session journal is lost, fenced or restored. It opens an absence debt for every state that has an account. Nothing is recorded as ended. | Every later step. | DI: its own fence mark. | ADD A.4; AP 10; BK07 "Dispatcher and the one-shot transaction" |
| R24 | Capability entry: the capability, `closed` or `open`, the reporter and its reason; for a session-authority report from the revocation feed, the feed snapshot number and time it rests on (section 7.1); for a first closure of the session authority because the revocation state is unreadable, the operator alarm DI raised at that entry (section 7.1). | The gates that read the flag and every later cell of section 7.1. | The reporter's own closure record; for a report that section 7.1 makes a stop trigger, DI's write-ahead stop order, committed as R08 in the row's stop-requested cell before any stop effect. | ADD A.5; BK09 "Model provider through the gateway"; BK06 "Message key and its attestation" |

### 4.2 Proofs

Only these proofs change a state. Each has one producer.

| Id | Name | What it is | Producer | Source |
| --- | --- | --- | --- | --- |
| P1 | absence proof | Bound to one operation: it names the stop operation identity it answers (from R08 or from the record entering `stopping`, or the R02, R14 or retire operation whose stop step it is), the account and generation, the boot identifier, and the quiet interval it covers with both ends. Zero tasks with the account in the real, effective, saved or filesystem uid field, for the whole configured quiet interval, from a complete root-readable enumeration of every task with stable process handles. Every thread is a task and counts. On Linux an empty resource group stands for this only where qualification showed it equal to account-wide absence. A partial, denied, unreadable or timed-out enumeration is not a proof. NEW condition: the proof is valid only while the input fence and the start fence of the generation stay closed; the reason is that a task could otherwise be created during the enumeration. The proof is per account, so one session per slot is assumed [AP 7]. It is the effect of the user manager's stop (enumerate, signal by stable handle with incarnation revalidation, prove by enumeration); nothing drops into the account to kill [OWN-UM]. | UM | UM 5 step 2; UM 6.1; HP 4.7; BK05 "Load: a resource group per generation" |
| P2 | incarnation match | A bind-time proof only. CU's own kernel reading of `pid`, `uid`, `boot_id` and `start_time`, taken in one pass, is byte-equal to the manager observation and to the requested holder, AND the proving manager's evidence that the process is the actual harness of this execution is present. Tuple equality alone does not bind. It is not a liveness reading (K4). | CU | HL observer; HL07 |
| P3 | recorded result | The recorded terminal result of the same effect identity, read from the effect owner's journal (observation state `recorded`). For an enroll and for an update it is P3 from every owner listed in the inventory of R02 or R12. It answers only the effect identity it names, never a stop operation. | the effect owner, read by DI | UM 3; HP 2; BK05 "Account, generation and journal"; BK07 "Queue and questions of the harness" |
| P4 | no-effect proof | One of three kinds, kept in R18. (a) An authoritative refusal of the effect by its owner under the recorded operation, with its closed code and no trace of the effect (for a start: no start receipt). (b) Observation state `rolled_back`, verified. (c) Observation state `not_recorded` with complete coverage. The states `unavailable` and `contradictory` are not this proof. For an enroll and for an update it is P4 from every owner of the inventory, where a line that completed under the operation counts only by kind (b) rolled back through the undo recorded in R17; that composite is exactly how a known partial enroll or update reaches this proof, and until every line is refused or rolled back the held row stays. For a bump it exists only while the old generation is still `active`. It answers only the effect identity it names, never a stop operation. | the effect owner, read by DI | HP 2; HL09; HL21; HL23; UM 3; UM 6.2; BK05 "Account, generation and journal" |
| P5 | never-started evidence | For one generation that was never started since it became `active` (the account may have run under an older generation before a bump): the generation is `active`, a complete read of the launcher's start receipts shows no launcher invocation recorded for that generation, and P1 for the R02 operation is zero, all under the start fence of SR4, owned and held closed by DI since the generation's `active` append and attested to UM from DI's fence record. DI requests it under R02 and UM presents it through [enrolling, held:enroll x stop confirmed]. A trial start and a general kill by uid do not replace it. | UM, from LA's receipts, its own P1 and DI's fence record | DEC D4; BK06 "Total stop"; HP 4.7 |

A changed boot identifier (R11) proves only that the bound incarnation ended.
It is not P1. NEW against the book, which says a changed boot identifier
confirms that the old processes are gone [BK07 "Wake-up and context
transfer"]: this contract still requires R09, because persistence under the
account is denied by qualification and not by the reboot.

### 4.3 Refusal codes

One closed set for the lifecycle cells; codes of other contracts appear only
verbatim where section 10 says so. Every code has exactly one evaluating
service, which is the only service whose verdict produces it; the advice
check of section 6.2 only relays the evaluator's code from its one position
and evaluates nothing in this sense. Before a record DI returns the
evaluator's code unchanged to the proposer; after a record the code arrives
in P4 (section 2). The `station_*` names, and the two retained `message_*` names of the bridge submit endpoint (KY4), are NEW; the instruction codes of the proposed companion are not codes of version 1; codes of other
contracts are carried unchanged in the detail and never renamed [DEC D8].

| Code | Evaluator | Meaning | Carries |
| --- | --- | --- | --- |
| `station_absent` | DI | No station record of this name exists. | none |
| `station_exists` | DI | The name already has an account. | none |
| `station_retired` | DI | The station is retired; only a new provision is admitted. | none |
| `station_retiring` | DI | Removal is committed. | UM `generation_inactive` |
| `station_held` | DI | The station is in a held row; only the cells of that row apply. | none |
| `station_not_held` | DI | The teardown order applies only to a held row. | none |
| `station_not_enrolled` | DI | The enroll inventory is not complete. | none |
| `station_already_enrolled` | DI | The enroll inventory is complete. | none |
| `station_not_running` | DI | No incarnation is bound. | none |
| `station_busy` | DI | Another operation of the station is in flight. | UM `target_busy` |
| `station_incarnation_exists` | DI | A start is in flight, bound or not yet proved gone. | none |
| `station_proof_unexpected` | DI | No recorded effect or hold of this row awaits this proof. | none |
| `station_proof_mismatch` | DI | The proof is not about the recorded effect identity or the open stop operation, is not from its producer, names another account, generation or boot identifier, or does not cover the whole inventory. | none |
| `station_principal_mismatch` | DI | The principal of the validated binding J1 produced for a re-provision of a retired name is not the principal R00 and R16 retain for the name, and no recorded owner act reassigns it. | none |
| `station_name_held` | DI | After a journal generation change, inverse inventory of accounts, bindings and receipts does not prove the name's reservation R00 absent, so the name is held and never absent again (SR3). | none |
| `station_operation_conflict` | DI | Same operation identity, different arguments. | UM `request_id_conflict`; HL `request_conflict` |
| `station_state_stale` | DI | The compare-and-set lost, or the request carries a stale epoch. | the effect owner's own stale-request detail |
| `station_absence_unproven` | DI | An absence debt the presented interval does not answer is open, or the presented proof is not P1 (alone, or inside P5 where the cell requires P5), or the entry into `stopped` lacks R09. | UM `processes_remain`; HL `environment_lease_release_unconfirmed` |
| `station_bump_committed` | DI | A no-effect proof was presented for a bump whose old generation is no longer `active`. | none |
| `station_rotation_unavailable` | DI | No key rotation is authorized in station/1. | none |
| `station_stop_not_authorized` | DI | The requester may not stop this station. | none |
| `station_retire_not_authorized` | DI | The requester may not retire this station. | none |
| `station_bump_not_authorized` | DI | The requester may not bump this station. | none |
| `station_export_unresolved` | DI | No operator waiver exists; a recorded export receipt counts only from the decision in OQ14. | none |
| `station_obligations_open` | DI | Open obligations of the station block its removal. | none |
| `station_operator_act_invalid` | DI | The operator act is not authenticated or not exact. | none |
| `station_owner_unbound` | DI | The owner binding is not durable. | none |
| `station_credential_mode_refused` | DI | The plan does not select the mode without secrets at the agent. | none |
| `station_link_unregistered` | DI | The station link is not admitted. | C32 `native-environment-not-registered` |
| `session_home_lease_unavailable` | CU | The home lease was not acquired for this R03's lease-request identity and admitted digest; this is the existing code of HL21 and HL23, verbatim. DI relays CU's verdict and evaluates nothing, and a terminal replay answer (`ok:true` for an earlier, terminal lease identity) is not such an acquisition and admits nothing at gate 8. | Curator's lease code and reason |
| `station_identity_mismatch` | CU | The name file, the latch record and the carried name are not byte-equal. | none |
| `station_home_leased` | CU | A lease holder (prepared, bound or unknown) blocks the change. | HL `environment_home_leased` |
| `station_release_not_approved` | CU | The release is not an approved release newer than the pin. | none |
| `station_update_recovery_required` | CU | A pending composition must be recovered first. | HL `environment_lease_recovery_required` |
| `station_grant_refused` | GC | The grant chain does not cover the request. | none |
| `station_revocation_unknown` | GC | The revocation verdict for the exact chain is "unavailable". | none |
| `station_session_journal_fenced` | DI | The dispatcher's session journal is lost or fenced and the slot has no clearance. | none |
| `station_binding_stale` | DI | No validated binding exists for this operation, or it is consumed, or older than the allowed age. | none |
| `station_lifecycle_not_permitted` | DI | No lifecycle permission covers this start, or a human stop is in force. | none |
| `station_restart_budget_exhausted` | DI | The restart budget is spent. | none |
| `station_plan_changed` | DI | A fixed start field differs from the recorded value. | none |
| `station_qualification_required` | DI | The host qualification for the required guarantees is not current. | none |
| `station_capacity_unavailable` | DI | Capacity or policy does not admit the start; an unread pause state is a pause. | none |
| `station_account_shared` | DI | The slot table already maps the account to another recipient. | none |
| `station_generation_inactive` | LA | The exact (uid, generation) is not `active`. | HP `generation_not_active` |
| `station_account_not_quiet` | LA | Tasks of the account exist, or a prior execution or stop claim is unresolved, or the scan is partial. | none |
| `station_profile_digest_mismatch` | LA | The trust pin, a control digest or a loadable discovery path does not match the approved release. | none |
| `station_skeleton_invalid` | LA | A path of section 8 has a wrong owner, group, mode, type, link count, ACL or capability, or an entry is outside the closed list. | none |
| `station_backend_unqualified` | UM | The backend, class or platform is not qualified. | UM `qualification_required`, `platform_unsupported`, `class_unsupported` |
| `station_quota_exceeded` | UM | The quota or the journal reserve does not admit the account. | UM `quota_exceeded`; GJ `journal_capacity_reserve` |
| `station_bump_stranded` | UM | The bump was refused terminally after its commit point. | UM `processes_remain`, `bump_uid_not_clean`, `bump_key_admission_unconfirmed` |
| `station_cleanup_refused` | UM | Cleanup is not admitted or not verified. | UM `cleanup_not_admitted`, `cleanup_pending`, `path_is_link`, `backend_failed` |
| `station_key_unbound` | KS | No binding for the exact (uid, generation) and purpose. | KS `binding_not_found`, `generation_inactive`, `generation_mismatch`, `peer_identity_unavailable`, `peer_binding_mismatch` |
| `station_rotation_unrecorded` | KS | The key identifier of a purpose differs from the one the latest R02, or R16 where a retirement is the latest record, holds for the name. | none |
| `station_gateway_unready` | MG | The gateway path is not ready, or its readiness is unknown. | none |
| `message_envelope_unsigned` | AL | The submit endpoint received something that is not a complete signed envelope. | none |
| `message_audience_mismatch` | AL | The envelope is not for the endpoint's own room and recipients. | none |

The key service's own closed codes (`generation_inactive`,
`generation_mismatch`, `peer_identity_unavailable`, `binding_not_found`,
`peer_binding_mismatch`, `signer_identity_mismatch`) are used verbatim outside
the lifecycle cells (section 10) [OWN-KS]. The home-lease codes of HL20 are
used verbatim by CU when it refuses a bind; such a refusal reaches the table
as an event (section 2.2), never as a gate.

### 4.4 Gate sets

Each gate set is evaluated in the order written. The first failing gate is the
refusal; no later gate is asked. Within one gate, its codes are tried in the
order written [DEC D8]. "Before" and "after" refer to the record of the cell
(section 2). A reported event whose cell refuses before the record is spent:
DI records the refusal, consumes the report, and returns nothing further for
it; a new fact needs a new report. The one exception is a lost
compare-and-set, which never spends a reported or delivered-once event (SR2).

| Gate | Cells | Before the record, in order | After the record, in order |
| --- | --- | --- | --- |
| G1 | [absent, retired x provision] | `station_operation_conflict`; then GC, J1: `station_grant_refused`, `station_revocation_unknown`; then, for `retired` only, DI: `station_principal_mismatch` (the principal of the validated binding J1 produced is not the principal R00 and R16 retain and no recorded owner act reassigns the name); and, after any journal generation change, DI from inverse inventory of accounts, bindings and receipts: `station_name_held` (the inventory does not prove R00 absent for the name, SR3) | DI: `station_session_journal_fenced`, `station_binding_stale`, `station_account_shared`, `station_qualification_required`, `station_capacity_unavailable`. UM: `station_backend_unqualified`, `station_quota_exceeded`. |
| G2 | [provisioned x enroll] | `station_operation_conflict`; GC, J1 for the enroll under the provision grant: `station_grant_refused`, `station_revocation_unknown`; then `station_identity_mismatch` (the latch record against the carried name only, and only for a present latch that mismatches, section 2.2; the published name file cannot be compared before R02 publishes it, so its byte comparison is the after-record check below), `station_rotation_unrecorded` | CU: `station_identity_mismatch` (the name file published under R02, byte for byte against the latch record; a mismatch is that line's refusal and reaches the row as P4 or as a known partial under R17). KS: `station_key_unbound`. DI: `station_link_unregistered`, `station_owner_unbound`, `station_account_shared`. The owner binding it checks is DI's copy of the principal from R01's validated binding (R02). |
| G3 | [stopped x start] | the start gates 1 to 7 of section 6.2 | the start gates 8 to 18 of section 6.2 |
| G4 | every [state x stop requested] that is not a refusal | `station_stop_not_authorized` | none: a stop effect is never refused after its record; its unknown outcome is the column "unknown or stranded outcome" |
| G5 | [provisioned, stopped x retire] | `station_retire_not_authorized` (for a one-task station this includes the absence of the explicit release of section 12), `station_export_unresolved`, `station_obligations_open`; the export check is vacuous and is skipped where DI's record shows the station never completed an enroll and never started, as in `provisioned`, because no work product can exist | UM: `station_cleanup_refused` |
| G6 | [stopped x profile update approved] | `station_release_not_approved`, `station_home_leased`, `station_update_recovery_required` | none |
| G8 | [stopped x generation bump] | `station_bump_not_authorized`, `station_export_unresolved`, `station_home_leased` | UM, while the old generation is still `active`: `station_backend_unqualified`. After the old generation is `retiring` nothing is a refusal: a terminal refusal is `station_bump_stranded` in the column "unknown or stranded outcome". |
| G10 | [starting, held:start x proof: incarnation match] | `station_proof_mismatch`, `station_absence_unproven` | none |
| G11 | every [state x stop confirmed] that is not a refusal | DI: `station_proof_mismatch` (the proof does not name the one operation the row awaits - in `stopping` the stop operation carried by the record that entered `stopping`; in a held row the stop operation requested in that row or, for the P5 presentation, R02; for the bump step R14; for a retire step R15 or R19 - or it names a closed operation, or another account, generation or boot identifier), then `station_absence_unproven` (not P1 alone or inside P5 where required, or a debt whose reading is not before the interval began, or a fence open across it) | none |
| G12 | [retiring, held:retire x proof: effect completed] | `station_proof_mismatch`, `station_absence_unproven`, `station_cleanup_refused` | none |
| G13 | every other proof cell | `station_proof_mismatch` (including a proof that names a stop operation, which no proof column ever answers), `station_bump_committed`, `station_absence_unproven` | none |
| G14 | every [held row x operator teardown order] | `station_operator_act_invalid`; then, only where the cell leads to `retiring`: `station_export_unresolved`, `station_obligations_open` (the order skips no check a retire needs; both are carried by R19; the export check is vacuous and is skipped where DI's record shows the station never completed an enroll and never started, exactly as at G5) | none |

`station_state_stale` is the verdict of no gate: it is returned only by the
compare-and-set at the end of a cell, to a proposer whose expected version
lost, with no gate verdict returned from above that set (SR2). Every proposal
gate set begins with the expected-version read (gate 1 of section 6.2 for a
start, and the same read first for G1, G2, G4, G5, G6, G8 and G14): the read
itself returns no code, the gates are then evaluated on the version read, and
the set at the end of the cell returns `station_state_stale` to the losing
proposer, so a stale proposal against an also-failing gate returns the gate
verdict of no gate and exactly that one code. Events
reported by another service carry no expected version: for them DI retries
the cell against the state it re-reads and never returns `station_state_stale`
to the reporter, and an observation reading is appended whatever the race
and committed against the row then current.

`station_absence_unproven` in G10, G12 and G13 guards only the cells whose
next state is `running`, `stopped`, `provisioned` or `retired`; a cell that
leads down (to `stopping`, `held:stop` or `retiring`) is never refused by it.
It is returned in four cases, in this order: an absence debt is open that the
proof or the last R09 does not answer under U1's interval rule; the cell
enters `stopped` from a held row and no answering R09 was written after the
hold record [DEC D4]; the cell enters `stopped` from `enrolling` or
`held:enroll` and no R09 carrying P5 for this generation was written after
R02 and after the latest R11 [DEC D4]; the cell enters `retired` from
`retiring` or `held:retire` and no R09 for the retire operation was written
after R15 or R19, which is also the gate that keeps UM from removing a home
without its own P1 (R15). The boot-identifier case belongs to the interval
rule, not to a separate freshness text: a P1 whose interval closed before a
reboot or before a debt's reading answers nothing after either.
G7 is not used: no cell admits a key rotation. G9, G15 and G16 are not used
in version 1; those identifiers belong to the proposed companion gate sets of
section 7.2.

### 4.5 Clocks

Every bound is in clock time and has one actor. When a bound expires, the
actor is DI, and its one action is to commit the cell named, as a proposal
from itself under SR2. No value is defined here except where a row gives one;
a value that no source gives is an open question, the bound and the actor are
not [ADD A.1; DEC D11].

| Clock | Runs from, to | On expiry DI commits | Value | Source |
| --- | --- | --- | --- | --- |
| `effect_bound` | The record of an effect in flight (R01, R02, R12, R14, R15), to its proof. | [provisioning, enrolling, updating, bumping, retiring x unknown or stranded outcome] | The owner's configured bounds; no implicit default [UM 3]. | UM 3 |
| `start_detect` | Phase `start_requested` of R03, to P2 or P4. | [starting x unknown or stranded outcome] | The `detect` bound of the dispatcher policy [DF A]. | DF A; HL22 |
| `end_to_absence` | The dispatcher's journaled end of a session (written under R05, R08, R11, R18 or R19 where it enters stopping, and in no other row), to R09. This clock runs only in `stopping`. An R19 that enters `retiring` with no session starts no such clock (R19). | [stopping x unknown or stranded outcome] | PROPOSED OQ21 option B, the dispatcher owner's answer pending the user-manager owner's confirmation: the dispatcher policy's stop bound plus the user manager's published quiet interval; until that confirmation, the `stop` bound of the dispatcher policy alone [DF A]. | ADD A.1; AP 6; OWN-DI |
| `liveness_interval` | One reading of the bound tuple, to the next. | [running x liveness reading missed], reported by CU | OPEN OQ4. | DEC D11; HL observer |
| `silence_deadline` | The entry into `held:live`, to "liveness restored". | [held:live x stop requested], with DI as requester and reason `liveness_silence` | OPEN OQ4. | DEC D11 |
| `revocation_to_stop` | DI's commit of the capability report that records a section 7.1 stop trigger, to DI's commit of the stop request it orders. | [starting, running, held:live, held:start x stop requested] with DI as requester; in any other row with a live or possibly live process the same through that row's stop-requested cell | 300 seconds, decided; the suspension that precedes the stop is effective at the report's commit and no later than the snapshot propagation bound of BK13. | Owner decision on OQ5; BK13 "Revocation and unknown state"; BK05 "Qualification revocation" |
| `verified_time_loss` | The first R24 entry recording verified time lost, to its recovery. | [row x stop requested] for everything that depends on time, through that row's stop-requested cell | At most 10 minutes by the monotonic clock, decided; not reset by restarts inside the loss. | BK13 "Renewal without widening"; owner decision on OQ6 |
| `account_bound` | R01 of a task-lifetime (including one-task) station, to R16 or to the R18 that releases its claim. | [starting, running x stop requested] with DI as requester, and no new start afterwards: gate 14 refuses it as policy | 24 hours by default, at most 7 days. | BK07 "Dispatcher and the one-shot transaction" |
| `execution_bound` | R04 of a task-lifetime (including one-task) station, to its R09. | [running x stop requested] with DI as requester | 4 hours by default, at most 12. | BK07 "Dispatcher and the one-shot transaction" |

NEW: the action at `silence_deadline` is a stop request. The reason is that
down is the one direction that is safe without the reading; nothing is
released by it, and P1 is still required in `stopping`.

## 5. Unknown outcomes

U1. Absence debt. Every reading of an unexplained process is recorded (R06),
whether or not a bind was attempted and whatever compare-and-set race it
lost on the way in (SR2), and every journal fence entry (R23) for a state
that has an account is recorded. Each opens an absence debt in the station
record. A debt is answered only by an R09 whose proof names the operation
the row awaits (G11) and whose quiet interval began after the
reading that opened the debt and closed with both fences closed across it;
an R09 that merely accepts an older proof after the reading answers nothing.
Comparison is by the interval and by the boot identifier the proof carries,
never by the time the acceptance was written. While a
debt is open, every cell gated by G10, G12 or G13 that leads to `running`,
`stopped`, `provisioned` or `retired` refuses `station_absence_unproven`
[DEC D4]. A debt opened in `retiring` is not left without a requester: in the same
commit that records it (R06 or R23), DI requests a fresh P1 from UM under the
open retire operation (R15 or R19), and [retiring x stop confirmed] answers
it. In a quiet row the same reading moves the
station to a held row, so no quiet row ever carries an open debt:
[provisioned x process appears], [stopped x process appears],
[provisioning, enrolling, updating, bumping x process appears].

U2. When an effect may or may not have happened, the station enters the held
row named in [state x unknown or stranded outcome], and R17 is written in that
commit. R10 may precede R17, because classification is a read and releases
nothing (SR5); R17 precedes every effect, release and resumed step after it.
Nothing is released from unknown: the home lease, the account reservation, the
capacity claims and the quota charge all stay [C24 "Lifecycle and failure
handling", unknown; HL08; BK07 "Dispatcher and the one-shot transaction"].

U3. No held row is left upward (to `running`, `stopped`, `provisioned` or
`retired`) except by a proof of section 4.2 in a cell of that row, or by
"liveness restored" out of `held:live`, the one upward exit whose evidence is
a reading and not a proof P1 to P5. A held row
may be left downward (to `stopping` or `retiring`) by a stop request, an exit
report, a reboot or the operator teardown order; nothing is released on a
downward move. The operator teardown order asserts no fact: it chooses the one
direction that is safe without the fact. NEW: the sources give the operator a
lease break, an abandon flag and a retire act, and none of them is a proof
[HL12; HL13; C24 "Lifecycle and failure handling"]; an audited lease break and
an abandoned operation change no cell and authorize no release.

U4. A stop or an absence is never inferred from a missing process, a dead
direct child, an empty or filtered lookup, a timeout, a quiet inbox, a
launcher exit, a changed boot identifier, a lost journal or a successful
command [C24 "Lifecycle and failure handling", unknown; UM 6.1; HL08; BK05
"Load: a resource group per generation"]. `stopped` is entered only by
[stopping x stop confirmed], by [held:stop x stop confirmed] where that
row's stop operation is open, by a proof cell gated on R09 (section 4.4), or
by a proof cell out of `updating` or `bumping` on the R09 that admitted the
station into `stopped` before that effect, with no debt opened since
[DEC D4]. Accepted costs, stated here and not hidden: a task that cannot be
killed, or a process enumeration that stays unreadable, on a host that is
not rebooted, blocks P1 the same way and keeps the account claim, the lease
and the quota for as long as it lasts; the operator teardown order only
returns such a station to `stopping`. A cleanup step that UM refuses
permanently likewise keeps a station in `retiring` or `held:retire` for as
long as it lasts: no cell forces `retired` without G12. And every refusal
below the record line of section 6.2, even one where no launcher invocation
can have happened, pays a full enumeration proof P1 before the station is
`stopped` again; that is the price of DEC D4, not an accident of it.

U5. Who acts in a held row. The actor is never open; a deadline that no source
gives is.

| Held row | Entered by | Actor and first action | Leaves upward by |
| --- | --- | --- | --- |
| `held:provision` | unknown create; a reading or a lost journal during a create | DI observes the create effect at UM and, on every entry into this row, requests the stop [held:provision x stop requested], whether or not a debt is already open, so no exit of this row waits for an R09 nobody requested | P3 to `provisioned`; P4 to `retired`. A proved rollback admits no new provision by itself: that is a fresh operation [BK05 "Account, generation and journal"]. |
| `held:enroll` | unknown or partial enroll; a reading or a lost journal during an enroll | DI observes every owner of the R02 inventory and, on every entry into this row, requests P5 under R02 as there stated (with an open debt it also requests the stop in the row [held:enroll x stop requested]), so no exit of this row waits for evidence nobody requested. On a known partial outcome DI writes the per-line outcomes and the undo requests of R17 before anything else proceeds. | P3 from every owner to `stopped`; P4 from every owner to `provisioned`, a completed line counting only rolled back through the R17 undo. While one binding is durable and another is not, the row stays; resources of uncertain ownership are never deleted [C24 "Lifecycle and failure handling", create]. No exit of this row waits for a stop nobody requested: the P1 cases enter through the self-loop stop request of the row or through the R02 request for P5. |
| `held:account` | a process or a lost journal at `provisioned` | DI requests the stop [held:account x stop requested] | P1 to `provisioned`. |
| `held:start` | unknown start; an unexplained process during a start | DI observes its own start effect at LA and never sends a second start request. Entering this row is a commit out of `starting`, so the same commit closes the fence and records the start as withdrawn (SR4): a launcher that revalidates the receipt after that commit refuses and starts nothing. A process whose receipt already passed revalidation before the withdrawal is not started again; it is accounted only by the ordinary cells of this row - P2 for that receipted execution, an exit report, or the stop and P1 path - and by no second start request [BK07 "Dispatcher and the one-shot transaction"] | P2 to `running`, only with no open debt. Down only: a stop request, an exit, a reboot or P4 leads to `stopping` and the entering record carries the stop operation; there is no direct P1 to `stopped` in this row (section 3 head). A start receipt alone (P3) keeps the row: a started process is not a bound one. |
| `held:live` | a missed or unreadable reading of the bound tuple | CU reads again at `liveness_interval`; at `silence_deadline` DI requests the stop | "liveness restored" to `running` (U3's one reading exit); down by a stop request to `stopping` and only there P1 to `stopped` (section 3 head). |
| `held:stop` | a process outside the bound execution; a lost journal; an unknown stop; two unknowns at once | DI requests the stop at once [held:stop x stop requested] | P1 to `stopped`. |
| `held:update` | unknown or partial update; a reading or a lost journal during an update | DI observes CU and UM over the R12 inventory, writes the per-line outcomes and undo requests of R17 on a known partial outcome, and, on every entry into this row, requests the stop in the row [held:update x stop requested], whether or not a debt is already open, so the R09 its exits need is always asked for in the row | P3 (every control at the new release, pin published) or P4 (every control at the old release) to `stopped`, each only with an R09 that answers every debt of the hold under U1. The next start verifies every digest again (section 6.2). |
| `held:bump` | unknown or stranded bump | DI observes the bump effect at UM and, on every entry into this row, requests the stop in the row [held:bump x stop requested], whether or not a debt is already open, so the R09 its exits may need is always asked for in the row | P3 to `provisioned`; P4 to `stopped` only while the old generation is `active` (`station_bump_committed` otherwise). A stranded bump leaves only by the operator teardown order to `retiring`, which is the ordinary-retirement fallback of UM 6.1. No proof returns a generation that reached `retiring` or `removed` [UM 6.2; GJ 4; DEC D5]. |
| `held:retire` | unknown retirement step; a lost journal during retirement | DI observes the retire effect at UM | P3 to `retired`. P4 leads to `retiring`, where the step runs again. |

## 6. Restart rule

### 6.1 What a restart is

A restart is the cell [stopped x start] taken again, and it is always a new
execution of the station in the dispatcher's sense, never a resumption of an
old one. It keeps the account, the generation, the home, the station name and
every key binding. It creates a new process incarnation with a fresh origin
(a fresh validated binding under J1, consumed by this R03 alone), a fresh
bind (a new P2 and R04; no bind survives an incarnation) and a new execution
record (this R03, with new operation, request, execution and lease
identities). The station identity and the logical session identity span such
executions; an execution and its incarnation do not, and a restart never
resumes an old execution identity or an old lease identity
[HL06; BK07 "Dispatcher and the one-shot transaction"; BK07 "Fence, parking
and restart"; DF B.3]. The order of a restart is fixed: end, prove empty
(P1), start; in cells, [running row x stop requested or process exits] to
`stopping`, [stopping x stop confirmed] to `stopped`, and only then
[stopped x start]. Where the end is unknown or the proof fails, the restart
refuses: every held row refuses "start" with `station_held`, the station
stays in its held row, and nothing without an operator act (the teardown
order, or a proof the row admits) frees it for a later start. A restart is
never a generation bump: a new conversation or a new incarnation MUST NOT
cause a bump [UM 6].

Every start, the first one included, begins from `stopped`, and `stopped` is
entered only with R09: P1 for a station that ran, P5 for a generation that
never ran (U4) [DEC D4; BK07 "Permission for a successor"; BK06 "Total
stop"]. The station operation requests P5 from the user manager under R02
once the generation is `active`; because DI owns the record (SR1), DI makes
that request and records its presentation, and UM presents it through
[enrolling x stop confirmed]; the same holds in `held:enroll` under U5.
Without that presentation no enroll finishes and no first start exists.

Who may request a start; the physical start has one path in every case, a
proposal to DI and DI to the launcher [HP 7 "R-START"; BK05 "Two narrow
privileged entries"]. The starts that need a lifecycle permission under this
section, and only those, are: a repeated start by host reconciliation after
a crash or a reboot, an automatic successor, a permanent-team start from the
signed team description DI reconciles, and any second start of a one-task
station. A first start proposed by the party responsible, and the single
start of a one-task station, need none. Gate 11 spends the permission and
budget check on exactly that list, and its human-stop check on every class
of start without exception, a manual repeated start by the party responsible
included:

- the party responsible for the station, named by the grant (the raising
  orchestrator or the operator) [C24 dec 4];
- the operator, for a station of a permanent team, from the signed team
  description that the dispatcher reconciles, also after a reboot [BK05 "Homes
  and results"; BK07 "Dispatcher and the one-shot transaction"];
- the host after a crash or a reboot, only within a lifecycle permission that
  the owner granted for this station; without that permission a start is
  single and nobody may repeat it [BK07 "Permission for a successor"; BK07
  "Wake-up and context transfer"];
- nobody but the party responsible or the operator, when the station was
  stopped by a human: their start lifts the human stop and R03 records the
  lifting (gate 11); no automatic, host-recovery or permanent-team start
  lifts it. Nobody, when the lifecycle permission was withdrawn by owner
  cancellation, owner retirement, chain revocation, signed retirement of
  the station or a maintenance stop [BK07 "Permission for a successor"].

A restart budget bounds automatic restarts so that successors cannot reset a
time window [BK07 "Permission for a successor"]; its count and backoff are
OPEN OQ3.

### 6.2 Start gates (G3)

Every gate is evaluated at every start, including restarts and native resume
[C24 "Platform controls and approved updates"; UM 7]. The order below is the
contract: the first failing gate is the refusal, and no later gate is asked
[DEC D8]. Gates 1 to 7 are reads; a failure refuses in [stopped x start] and
changes nothing. Gates 8 to 18 are verdicts of effect owners under R03; a
failure arrives as P4 in [starting x proof: effect did not happen], leads to
`stopping`, and reaches `stopped` only by P1 [DEC D4].

| # | Gate | Check | Code | Evaluator | Source |
| --- | --- | --- | --- | --- | --- |
| 1 | expected version | The version the proposal carries equals the version DI reads. This is a read, not the set: the one compare-and-set is at the R03 line below, and where it loses, DI returns `station_state_stale` and no verdict of gates 2 to 7 (SR2). | `station_state_stale` | DI | DEC D1 as amended |
| 2 | J1 | The grant chain covers this start for this principal, host, account and plan, and the revocation verdict for the exact chain is "not revoked". "Revoked" refuses `station_grant_refused`; "unavailable" refuses `station_revocation_unknown`. The verdict is the validated binding (section 11). | `station_grant_refused`, `station_revocation_unknown` | GC | RUL-2; DEC D9; BK13 "Revocation and unknown state" |
| 3 | identity latch | The name file equals, byte for byte, the latch record and the name the start carries (section 9.2). | `station_identity_mismatch` | CU | section 9.2 (PROPOSED) |
| 4 | key bindings | A binding for the exact (uid, generation) exists for each key purpose of section 10. This is a read; the key service decides again at every connection (KY3). The dispatcher caller is not a purpose of this gate whichever way OQ27 is decided: under OQ24 option A the installer-made caller key file is checked only at gate 18, never as a key-service binding; under the no-readable-key alternative DI authenticates its single caller by kernel peer uid and there is again nothing for this gate to check. Under the later purpose-6 unit its binding joins this read. | `station_key_unbound` | KS | BK06 "The kernel establishes the peer"; GJ 4; OWN-KS |
| 5 | message link | The station link is admitted, from AL's registry as DI reads it. The code is this contract's, evaluated by DI; no curator-run verdict produces it. | `station_link_unregistered` | DI | C32 "Recommendation" |
| 6 | credential mode | The plan DI holds for this start selects the mode without secrets at the agent. The code is this contract's, evaluated by DI; no curator-run verdict produces it. | `station_credential_mode_refused` | DI | BK09 "Mode without secrets at the agent" |
| 7 | gateway readiness | Gateway address, service lease, listener of this generation, qualified adapter. Unknown readiness refuses. | `station_gateway_unready` | MG | BK08 "Readiness before launch" |
| R03 | record line | Gates 1 to 7 are above this line and change nothing. R03 is written here by the one compare-and-set on the state version; if the set loses, the refusal is `station_state_stale` and no gate verdict above the line is returned. Gates 8 to 18 are below it. | none | DI | HL21; DEC D1 as amended |
| 8 | home lease | The lease is acquired for this R03's lease-request identity and the admitted digest. CU's verdict is relayed by DI, and a terminal replay answer (`ok:true` returned for an earlier, terminal lease identity under HL06, HL21 or HL23) is not an acquisition for this identity and never admits; it refuses with this gate's code in P4. | `session_home_lease_unavailable` | CU, relayed by DI | HL06; HL21 |
| 9 | session journal | The dispatcher's session journal is intact, or the slot has a clearance. | `station_session_journal_fenced` | DI | ADD A.4; AP 10 |
| 10 | binding | The validated binding named in R03 exists, is unconsumed, is for this operation and is not older than the allowed age. | `station_binding_stale` | DI | RUL-2; ADD A.3 |
| 11 | lifecycle | Every class of start, in two checks in this order. First, for every start: where a human stop stands (the latest R08 whose reason is the owner stop of section 7.1, not yet lifted), only a start proposed by the party responsible or the operator passes, and that start lifts the human stop, recorded in R03; every other proposer, a manual repeated start by anyone else included, refuses here. Second, only for a start in section 6.1's named list (a repeated, automatic, host-recovery or permanent-team start, or a one-task station's second start): a lifecycle permission covers this start and the restart budget is not exhausted; a one-task station has no such permission, so its second start refuses here. A first start by the party responsible and a one-task station's single start spend only the first check. | `station_lifecycle_not_permitted`, `station_restart_budget_exhausted` | DI | BK07 "Permission for a successor" |
| 12 | fixed fields | The fixed start fields of section 9.1 equal the values recorded at provision as last amended by the last completed R12; R03 names that R12. | `station_plan_changed` | DI | BK07 "Permission for a successor"; DF A |
| 13 | qualification | The host qualification for the required guarantees is current. | `station_qualification_required` | DI | BK05 "Qualification revocation"; UM 1 |
| 14 | capacity | Capacity and policy admit the start; an unread pause state is a pause. | `station_capacity_unavailable` | DI | BK07 "Dispatcher and the one-shot transaction" |
| 15 | generation | The exact (uid, generation) is `active`, read under the generation lock. | `station_generation_inactive` | LA | GJ 1; GJ 6.1; HP 7 |
| 16 | quiet account | Zero tasks of the account and no unresolved prior execution or stop claim; a failed or partial scan keeps the start closed. | `station_account_not_quiet` | LA | HP 7 |
| 17 | profile digests | Under the generation lock: the trust pin equals trusted approved-release metadata; every platform control equals its approved digest; the admitted runtime mapping lists every discovery path the harness can load, in the home and in the work directories. In explicit native-project mode (C24 dec 8) the mapping lists the project's own loadable paths in the clone as project controls of that mode, per mapping: a listed project control may be station-writable, is loaded as project instruction and never as platform authority, and the mode's visible non-isolation notice stands. This gate refuses only a loadable, station-writable path that the mapping neither lists as a project control of the selected mode nor classifies as data; in any other mode no path is a project control unless its mode's mapping says so. Missing, unreadable, extra effective or mismatching controls refuse before provider execution. The checked objects are bound to the admitted start. | `station_profile_digest_mismatch` | LA | C24 dec 2; C24 dec 8; UM 7; DEC D3; DEC D10 |
| 18 | home skeleton | Under the same lock: every path of section 8 has its owner, group, mode, type and link count; no stored ACL or file capability; no entry outside the closed list in a platform-owned directory. For the dispatcher caller key of an orchestrator station this gate states both outcomes of OQ27: under OQ24 option A, exactly the one file at the installer-published path, owner the station uid, mode 0600, is admitted by metadata alone (its bytes are never read here) and every other key-like file refuses; under the no-readable-key alternative no such file is admitted and any of them refuses. Until OQ10 and OQ11 are decided, any station-link entry likewise refuses here (section 8). | `station_skeleton_invalid` | LA | UM 7; DEC D3 |

The launcher is the authoritative evaluator of gates 17 and 18: only the
process that opens the trusted handles under the generation lock can bind the
checked objects to the admitted start [DEC D3; UM 7]. This closes the earlier
open question on the evaluator (OQ9), pending the confirmation of the
user-manager owner, which is not recorded yet. DI MAY run the same two checks
as advice; CRO's own pre-checks are proposal hygiene and produce no contract
code. The advice check has exactly one position in the order, between gates
16 and 17: it runs only where gates 1 to 16 all passed, and its result is
returned only then, in place of asking the launcher for gates 17 and 18. The
launcher remains the only evaluator in the registry sense of section 4.3: an
advice refusal is DI relaying the code the launcher is bound to return for
the same objects, and the launcher repeats the checks whenever it is asked;
if its own evaluation of the same start disagrees, the launcher's verdict
wins and the disagreement is a defect of the advice check, recorded as such.
CRX evaluates no gate [DEC D2; DEC D3; DEC D8]. That one position is what
makes the first code a function of the input alone:

| A start that fails | With the advice check | Without it |
| --- | --- | --- |
| gate 2 (grant revoked) and gate 17 | `station_grant_refused` at gate 2; advice never runs | `station_grant_refused` |
| gate 16 (account not quiet) and gate 17 | `station_account_not_quiet` at gate 16; advice never runs | `station_account_not_quiet` |
| gate 17 alone | `station_profile_digest_mismatch`, relayed at the advice position | `station_profile_digest_mismatch` at gate 17 |
| gate 17 and gate 18 | `station_profile_digest_mismatch`, relayed at the advice position | `station_profile_digest_mismatch` |

One order, one position: any two implementations return the same first code
for every start, including every start that fails two gates.

### 6.3 What a restart must never do

- Reuse a session reference. The operation, request, execution and lease
  identities, the manager session handle and generation, the controller epoch
  and the credential stub of the previous incarnation are dead; a surviving
  connection of an old controller has no right to write [HL06; BK07 "Service,
  runner and the single writer"; BK09 "Model provider through the gateway"].
  Harness conversation state in the home is not a session reference: a native
  resume is allowed only on the same host, harness, home and profile pin; a
  failed resume is reported and is not rebuilt automatically [BK07 "Wake-up
  and context transfer"; C24 "Persistent stations and task-lifetime spawn"].
  What any later work inside the incarnation may read of that state is not a
  question of version 1 (section 7.2).
- Widen authority. A restart cannot add an account, a harness or a profile
  even if a parent grant has grown since; widening needs a new provision [BK13
  "Renewal without widening"].
- Repair by guessing. A failed gate refuses and preserves what it found. No
  start rewrites the name file, re-pins the trust pin, replaces a digest,
  enrolls a link or adopts an account [C24 "Platform controls and approved
  updates"; HL03; C32 "Recommendation"; UM 3].
- Retry blindly. A lost start is `held:start`, never a second start request:
  [starting x starter crash] resumes only what HL21 permits (the identical
  lease acquire) and sends no second physical-start request [HL21; DF B.3;
  BK07 "Dispatcher and the one-shot transaction"].

## 7. Rules for a kept station

These nine rules answer items 1 to 9 of section B of the dispatcher field
inventory [DF B]. Each row names the cells that carry it.

| Rule | Statement | Carrying cells | Source |
| --- | --- | --- | --- |
| K1 session identity | Four things are distinct. The station identity (name, account, generation, keys) is stable for the life of the station. A process incarnation is one bound kernel tuple; a restart consumes it and creates a new one. A harness session is conversation state in the home. One live incarnation per station: the state record admits one start per state version (SR2, SR4), and the launcher refuses an account that is not quiet. | [stopped x start]; [starting x proof: incarnation match]; [starting, running, stopping x start]; every held row x start | DF B.1; HL07; DEC D1; HP 7 |
| K2 lifetime | The horizon of a station is the validity of the session's grant: the grant that authorizes the start and the holding [AP 12]. It replaces the one-shot runtime bound. A persistent station has no time bound per incarnation and is outside the quotas of temporary work [BK05 "Homes and results"; BK07 "Dispatcher and the one-shot transaction"]; what remains per incarnation is the clocks of section 4.5, the term of the message-key attestation (at most 86400 s, renewed by the key service ahead of expiry; a missed renewal closes the capability signing, not the station) [BK06 "Message key and its attestation"], and the model credential lease held by the gateway (K7). A task-lifetime station keeps the published bounds: account 24 hours by default and at most 7 days, one execution 4 hours by default and at most 12, each as a clock with DI as actor (`account_bound` and `execution_bound` of section 4.5) [BK07 "Dispatcher and the one-shot transaction"]. Renewal: the dispatcher re-signs the leaf under the current chains and the broker replaces the binding of the same account and generation, old removed before new; the new scope is the intersection of the current chains with the originally admitted request; only a member of the existing chain may renew; a revoked right is never re-issued by maintenance [BK13 "Renewal without widening"]. How far ahead renewal happens is OPEN OQ2. Renewal of the dispatcher policy window, which the landed policy keeps finite [DF A], is OPEN OQ26. At expiry, decided (OQ1 closed, option A): the capability session authority closes at expiry, gate 2 refuses every start from expiry, and a running station is stopped through [running x stop requested] committed by DI within the same 300 second bound as the other stop triggers of section 7.1. | [stopped x start] gate 2; [running x capability report]; [running x stop requested] | DF A; DF B.2; owner decision on OQ1 |
| K3 restart rule | Section 6. The same account, generation and home are reused. A lost start is unknown: a held row, never a blind retry. | [stopped x start]; [starting x starter crash]; [starting x unknown or stranded outcome]; the `held:start` row | DF B.3; section 6 |
| K4 liveness | Two different things [DEC D11]. P2 is the bind-time proof and is produced once per incarnation. A liveness reading is CU's periodic kernel reading of the four fields, compared with the tuple of R04; "alive" means that reading is equal. A self-report, an a2a heartbeat, an answered message or a live bridge process is not liveness and is never merged into a termination verdict [BK24 "What the bridge consists of"]. A missed or unreadable reading is unknown, never a stop and never a release: the station enters `held:live`. CU reads again at `liveness_interval`; at `silence_deadline` DI requests the stop (section 4.5). | [running x liveness reading missed]; [held:live x liveness restored]; [held:live x stop requested] | DF B.4; HL observer; HL08 |
| K5 follow-up work | Section 7.2: version 1 defines no instruction delivery and no run, and no cell carries follow-up work. | no cell | DF B.5 |
| K6 revocation while running | Section 7.1. | [running x capability report]; [running x stop requested]; [stopped x start] gate 2 | DF B.6; RUL-2; DEC D9 |
| K7 credential and gateway lease | The station holds no model credential: the gateway holds the lease and the station holds a stub bound to one generation, one start and one account [BK09 "Model provider through the gateway"]. When the gateway's lease renewal fails, forwarding closes and the gateway reports the capability model forwarding closed; R24 records it, and no start is admitted while gateway readiness is closed or unknown (gate 7) until the gateway reports it open again. A running station is not stopped by that failure. NEW: the book states waiting for a needed provider login [BK07 "Wake-up and context transfer"]; the renewal case is applied by analogy. Whether a bounded wait escalates to a stop is OPEN OQ7. An account block after a leak match is different: it stops the session through [running x stop requested] [BK09 "Leak tripwire"]. | [running x capability report]; [stopped x start] gate 7 | DF B.7 |
| K8 home and state | State that survives a restart lives only in the station-writable paths of section 8. Retirement duty: the work product is exported before the home is removed; a partial, unknown or failed export keeps the home, and only a recorded operator act waives the duty [BK07 "Dispatcher and the one-shot transaction"; UM 5]. Gate G5 admits a retire only with that waiver; a recorded export receipt counts as a discharge only from the decision recorded in OQ14, and no cell of this draft produces or verifies one, so an out-of-contract receipt admits nothing. Who runs the export is OPEN OQ14; until it is decided no cell starts an export execution, so in this draft a retire is admitted only with the operator waiver, as in the first slice of the user manager [UM 5]. The account stays reserved and fenced until P1. Homes are never archived; keeping a retired home is a separate operator operation outside retirement [BK05 "Homes and results"]. | [provisioned, stopped x retire] gate G5; [retiring x stop confirmed]; [retiring x proof: effect completed] gate G12 | DF B.8 |
| K9 capacity | NEW: a station holds two claims; the sources name an account quota and an execution claim and do not join them for a station. The account claim lasts from R01 to R16 (or, for a create that did not happen, to the R18 that accepts its P4 and releases it on the entry into `retired`; R00 is retained and is not a claim) and is charged once across bumps [UM 6]. The execution claim lasts from R03 to R09 on every path, including a start that did not happen, and is never released from unknown [BK07 "Dispatcher and the one-shot transaction"]. A reclaim is a stop requested or a retire through this table; it is never a signal sent outside the table, and decided (OQ8 closed, option A) it is the operator's alone: DI never requests the stop of a standing station to reclaim its claim, inside no policy; it may only report the claim standing. Removal or re-creation of a persistent station needs the operator [BK05 "Homes and results"]. The cost of an unkillable task is in U4. | [running x stop requested]; [stopping x stop confirmed]; [retiring x proof: effect completed] | DF B.9; C24 "Host budget" |

### 7.1 Triggers of a stop or a suspension

Every trigger enters the table through the cell named; there is no
revocation column because every report of this section is a capability
report or a stop request and nothing else (section 2.2). A suspension is the
capability session authority recorded closed (R24): no start is admitted
(gate 2), and the process is not stopped by that entry itself; for every
stop trigger below the decided stop follows the suspension. The stop itself
is a write-ahead order of DI: in the commit that records the trigger, or as
its immediate next commit in the same row, DI records the stop operation as
R08 in the row's stop-requested cell, with itself as requester, before any
stop effect is requested; no stop effect of this section precedes its order.
The decided bounds are one pair: from a validated revocation, expiry,
seal-spend or policy-removal report to the suspension is at most the
snapshot propagation bound max(S + A, F) with A at most 60 seconds
[BK13 "Revocation and unknown state"], the suspension taking effect at the
commit of [state x capability report] that records it; from that commit to
DI's commit of the stop order is at most 300 seconds more, the
qualification-revocation deadline, spent by the clock `revocation_to_stop`
and never reset by retries or restarts, the stop itself completing under
`end_to_absence`. Revocation and expiry reach a running station through the
grant checker's feed to DI, which records and acts as record owner [RUL-2;
DEC D9]; that feed is a new seam and does not exist yet [DF C]. The feed
carries a snapshot number and time, recorded in R24 with every session-
authority report it produces. A feed snapshot older than the propagation
bound above proves nothing about revocation: DI then records the session
authority under the unreadable case below (hold, operator alarm, no new
start, no stop) until a fresh snapshot arrives. At every restart of DI, DI
resyncs the complete snapshot from the grant checker before it admits any
start or clears any suspension, so reports missed while DI was down are
recovered by resync and never by waiting for the next push. OQ1, OQ5a to
OQ5e and OQ6 are closed by the owner decisions below and are no longer in
section 15.

| Trigger | Observed by | Decided | Enters by | Open |
| --- | --- | --- | --- | --- |
| Owner stop of one station | DI, on the proposal of the party responsible or the operator | Stop; the station stays stopped until the party responsible or the operator starts it, and that start lifts this human stop, recorded in R03 at gate 11 [BK07 "Wake-up and context transfer"]. | [running x stop requested] | none; completion is bounded by `end_to_absence` |
| Total stop of the installation (OQ5a, closed) | Each service directly: UM freezes generations and closes ingress, SH stops sessions, DI ceases starts, MG closes uses [BK06 "Total stop"] | Stop of every station within 300 seconds of the order, each through its stop-requested cell; resumption only by operator signature; a service restart does not lift it. | [running x stop requested] for each station, DI as actor | none |
| Qualification revoked | UM, the qualification reconciler [UM 1; BK05 "Qualification revocation"] | New starts close at detection; a running station is narrowed with confirmation or stopped within 300 seconds of detection, not reset by retries or restarts. UM reports the revocation as the capability qualification closed in this column; DI, as requester, then commits the stop order under `revocation_to_stop`. | [running x capability report], then [running x stop requested]; gate 13 for starts | none |
| Account block after a leak match (OQ5b, closed) | MG and CB [BK09 "Leak tripwire"] | Stop through [running x stop requested] within 300 seconds of the block report. | [running x capability report], then [running x stop requested] | none |
| The session's grant revoked or sealed (OQ5d, closed) | GC, through its feed to DI; the seal by the verifying service on its own chain node [BK14 "Revocation"] | Suspension at the report's commit, then stop within 300 seconds: on a gateway-backed host revocation suspends at once [RUL-2; DEC D9], and the decided stop follows it, so suspension is containment, never the end state of a revoked session. Starts refuse at gate 2. The lifecycle permission is withdrawn [BK07 "Permission for a successor"]. | [running x capability report], then [running x stop requested] under `revocation_to_stop` | none |
| The session's grant expired (OQ1, closed: option A) | GC, by the verified-time watermark [BK13 "Renewal without widening"] | Stop at expiry: suspension at expiry, then stop within 300 seconds; starts refuse from expiry. | [running x capability report], then [running x stop requested] | none |
| Policy removed while running (OQ5e, closed) | DI, by policy identity and revision [DF A] | Stop, not merely suspension: suspension at the report's commit, then stop within 300 seconds. Starts refuse at gate 11 and gate 14. | [running x capability report], then [running x stop requested]; [stopped x start] | none |
| Revocation state unreadable (OQ6 first case, closed) | GC, or DI itself where the feed snapshot is stale under the freshness bound above | Hold with no time limit: starts refuse `station_revocation_unknown`, because "unavailable" is a refusal and a lost connection is not absence of revocation [BK13 "Revocation and unknown state"]; no new start is admitted, and no stop is ordered for unreadability alone, so a running station keeps running under a grant that may in fact be revoked, which is the accepted cost of the hold. DI raises an operator alarm at the first such entry and records it in R24. Restarts inside the outage neither lift the hold nor clear the alarm; a fresh feed snapshot is the only exit. | gate 2; [running x capability report] with the alarm of R24 | none |
| Verified time lost (OQ6 second case, closed) | every service that checks time | The book's rule unchanged [BK13 "Renewal without widening"]: hold at most 10 minutes by the monotonic clock, then stop everything that depends on time. This is not the unreadable case above and takes none of its no-limit hold. | [running x capability report], then [row x stop requested] under `verified_time_loss` | none |

### 7.2 Work input of a standing station (out of scope in version 1)

Version 1 of this contract defines no instruction delivery and no run: no
event of section 2.2 delivers work to a standing station, no record opens
work inside an incarnation, and nothing in the lifecycle depends on how work
would arrive. A standing station's work input is out of scope until the
proposed companion [station-runs.md](station-runs.md) (PROPOSED,
non-normative) is decided by the owner; until then a station is provisioned,
enrolled, started, stopped, updated, bumped and retired under this contract,
and what it works on while `running` is no concern of any cell.

## 8. Home skeleton

H is the station home. S is the dedicated group of the station, U its uid. The
list is closed, the station-link row and the caller-key row excepted and
handled fail-closed as their rows and gate 18 state: any other entry at H,
or below a platform-owned directory, fails gate 18, and while OQ10, OQ11 and
OQ27 stand open the excepted entries fail it too except exactly as gate 18's
two stated outcomes admit. No path below H holds a model token, a carrier credential, a
private key or a lease record; those live with their holders (section 10;
BK09 "Mode without secrets at the agent"; BK24 "What the bridge consists of";
RUL-3; HL01). One exception is named in KY1. The actual discovery paths are
published per runtime mapping; `.harness` stands for the fixed protected
adapter destination [UM 7].

Nothing the station can write is read as a platform control [DEC D10]. The
adapter maps every effective control to a fixed protected path and rejects
unsupported discovery and override paths before launch, and no managed control
lies below a station-owned directory [UM 7]; gate 17 enforces it.

| Path | Owner:group | Mode | Written by | Station may write | Install, sync and repair | Source |
| --- | --- | --- | --- | --- | --- | --- |
| `H/` | root:S | 0750 | UM | no | Never replaced while a lease holder blocks; replaced whole only by a bump. | UM 7; HL14 |
| `H/AGENTS.md`, `H/CLAUDE.md` (the one selected by the approved runtime mapping) | root:S | 0640 | CU content, installed by UM | no | Replaced only by an approved release, in [stopped x profile update approved]. | UM 7; C24 dec 2 |
| `H/.platform/`, `H/.platform/skills/` and each skill directory | root:S | 0750; skill files 0640; approved executables 0750 | CU content, installed by UM | no | As above; closed approved inventory. | UM 7 |
| `H/.platform/trust-pin.json` | root:S | 0640 | CU through the approved-release path, published last | no | As above; never chosen by the station. | UM 7; C24 "Platform controls and approved updates" |
| `H/.identity/` and `H/.identity/name` (RESERVED, PROPOSED) | root:S | 0750; file 0640 | UM, with bytes from CU's latch record | no | Outside every approved-release inventory: an update neither replaces nor removes it. Published at enroll; after a bump, published again with identical bytes from the latch record. NEW path: no source names it; it is a directory of its own so that the replacement of `.platform` cannot touch it. | section 9.2; DEC D5 |
| `H/.harness/` | root:S | 1770 | UM | only inside `state/` | Root-owned entries are protected by the sticky parent. OPEN OQ22: which entries a harness itself creates here. Until decided, any entry other than `settings.json` and `state/` fails gate 18. | UM 7; DEC D10 |
| `H/.harness/settings.json` (hook settings) | root:S | 0640 | CU content, installed by UM | no | Replaced only by an approved release. | UM 7; C24 dec 2 |
| `H/.harness/state/` (harness state) | U:S | 0700 | the station | yes | Preserved; outside the cooperative write guard [HL17]. Never read as a control. Destroyed by a bump and by retirement. | UM 7; UM 6 |
| `H/work/` (work directories, the station's own repository clone) | U:S | 0700 | the station | yes | Preserved. Never read as a platform control: in explicit native-project mode (C24 dec 8) the mapping may list the clone's own loadable paths as project controls of that mode, and gate 17 then refuses only a loadable station-writable path it neither so lists nor classifies as data. What a later strict mode admits per runtime is OPEN OQ23. Destroyed by a bump and by retirement. | UM 7; UM 6; DEC D10; C24 dec 8 |
| `H/tmp/` | U:S | 0700 | the station | yes | Preserved; not a place for state. Destroyed by a bump and by retirement. | UM 7; UM 6 |
| The a2a station link (`.a2a/` with `daemon.sock`, `identity`, `station`, `station.key`) and the hook-failure log `state/daemon-hook-failures.log` | OPEN OQ10, OQ11 | OPEN | OPEN | OPEN | OPEN | C32 "Recommendation"; C32 "Security considerations"; UM 7; UM 5 |
| The dispatcher caller key of an orchestrator station (PROPOSED first-run deviation, KY1) | U | 0600 | the installer | read only | PROPOSED OQ24 option A and OPEN OQ27: gate 18 states both outcomes (this one file at the installer-published path admitted by metadata, or no such file admitted at all); its full path is named by the installer contract only under option A. Not a platform control and not a station identity key. Under the alternative no row exists here and DI authenticates its single caller by kernel peer uid. | DEC D7; BK06 "Which secrets exist"; OWN-KS |

The a2a link row is OPEN because two sources contradict on its owner. C32
"Recommendation" requires that the managed home containing `.a2a` "must belong
to the launching effective UID"; UM 7 requires that the home root "is never
owned by U". C32 also places a station-readable secret file, `station.key`, in
the home, while UM 5 states "This station layout holds no private keys". The
row stays OPEN until OQ10 and OQ11 are decided, and until then it is not a
hole in the closed list: gate 18 fails every station-link entry fail-closed,
so no start depends on a reading of this row, and KY1's "no key material in
the home" is the reading that wins for `station.key` while the questions
stand. One further conflict is recorded here as the owners' decision, not as a
reading of this contract: C32's own enroll step runs as the station user
[C32 "Recommendation"], so under the "process appears" definition that task
would put every enroll that ran it into `held:enroll`. The owners of the
a2a link and of the user manager, under OQ10, decide how that step is
accounted; until they decide, no station completes an enroll whose link
line needs it, this contract runs no station-user enroll step inside an
enroll, and gate 18 fails every station-link entry fail-closed exactly as
the row above states (the recommendation carried to those owners is a
recorded, receipted enroll execution whose tasks DI attributes to R02 and
whose end the P5 enumeration of R02 then proves). Decided already, and not
part of that question: the outgoing seam is the bridge's local submit
endpoint, and
no carrier credential is in the station account (KY4) [RUL-3].

One home serves one station. A profile home is never shared across stations
[HL24], and a station cannot traverse another home: H is 0750 with a distinct
group S and no supplementary membership [UM 7].

## 9. Identity

### 9.1 Start fields

| Field | For the life of the station | Who approves a change |
| --- | --- | --- |
| Host (the receiving dispatcher) | Fixed. | Nobody: another host is another station, by a new provision [DF A]. |
| Account and generation | Fixed at every restart. | The generation changes only through [stopped x generation bump], on the operator or dispatcher authority of UM 2 and UM 6. |
| Plan pins (worker plan, profile, harness, execution profile) | Fixed at every restart; the pin fields of the plan are reused byte for byte. The model selection and reasoning effort fields below are not pin fields and may change at a restart without touching this row. | A pin changes only through [stopped x profile update approved]; the completed R12 is the amendment record that gate 12 compares against, and the next start is a new admission under J1 [C24 dec 3; BK07 "Permission for a successor"]. |
| The principal the grant names | Fixed, and retained in R00 and R16 through retirement. | Nobody: a station does not change hands by an edit, and a retired name is re-provisioned only for that same principal or under a recorded owner act (G1, `station_principal_mismatch`). NEW: no source states this rule; the reason is that retirement retains the name's keys, so a new principal must not receive them by re-provision (KY6). |
| Station name | Fixed (section 9.2). | Nobody. |
| Model selection inside the catalog; reasoning effort | May change at a restart. | NEW: the party responsible for the start, inside the catalog and the grant; J1 admits it. The sources name the fields [DF A] and not the approver. |
| Prompt | May change at a restart. | The party responsible for the start; a goal is set by the caller, never by the station [BK07 "A goal does not belong to the agent"]. |

### 9.2 Name latch (PROPOSED)

This subsection is PROPOSED. It awaits two confirmations and is not normative
until both are recorded: the confirmation of the identity custody split by the
owner of the typed identity, and the owner's admission of the unit.

- A station has one stable name.
- The latch is a record, the latch record, kept by Curator in manager state
  outside the home. The name file `H/.identity/name` is its published copy. A
  profile update does not touch the file (section 8), and a bump, which
  destroys the whole home [UM 6], does not destroy the record: the enroll
  that follows a bump publishes identical bytes again and refuses
  `station_identity_mismatch` on any difference (gate G2) [DEC D5].
- At enroll the file is published from the record under R02 and compared
  against it only after that publication (gate G2, after the record); a
  before-record check compares the latch record with the carried name, never
  a file R02 has not published yet. At every start the file, the record and
  the carried name are compared byte for byte (gate 3). A mismatch refuses `station_identity_mismatch` and
  preserves both: nothing is rewritten, deleted or derived again.
- The latch record and its seam are owned by Curator. The full typed identity
  is owned by curator-run's station operation, which delivers it to the
  harness [C32 "Recommendation"; OWN-CR]; it is not admitted for
  implementation yet.
- For a station with no given identity, Curator derives a synthetic name once
  from {host_id, project_id, profile_id}: prefix `syn1:`, then SHA-256 over a
  tagged, length-prefixed encoding. The function is an input owned by the
  identity contract and is not redefined here.
- The latched name is not the a2a selector: a synthetic name never becomes an
  a2a agent name or a carrier localpart, so the grammar of the `identity` and
  `station` lines of the station link is not affected.

Whether the name follows the agent or the place is OPEN OQ15; sections 1, 6
and 9 are written for the reading that the name follows the agent.

## 10. Keys

KY1. A station can use keys and never read them. The holder of the station
keys is the key service. The station account reaches a socket of the key
service and never a key file; no key material is present in the home, the
plan, the environment, a record or a log [C24 dec 1; C24 "Security
considerations"; BK06 "The kernel establishes the peer"; OWN-KS]. One named
deviation is PROPOSED and not decided here (OQ24 option A, OPEN OQ27): in the
first enforcing run the dispatcher caller key of an orchestrator station
would be a file made by the installer and pinned by the static statement,
mode 0600, readable by that caller account, so an injection into the
orchestrator could use it, its power bounded by the orchestrator's grant
[DEC D7; BK06 "Which secrets exist"; OWN-KS]. That file contradicts C24
decision 1 ("The station can request signing but MUST NOT be able to read
the key file") and section 1 does not reopen owner decisions, so this
contract records it as a proposed deviation for the owner to amend or refuse
in OQ27 and does not adopt it: gates 4 and 18 each state both outcomes, the
alternative for the first run being that no station-readable caller key
exists at all and DI authenticates its single caller by kernel peer uid
until the purpose-6 station-caller unit of the key service (OQ24 option B)
exists. Whichever is decided, the deviation ends at that unit. The interim custody of CIP-0024 (one signing agent per station, key
file outside the station's access) meets the reach rule and is not the target
[C24 dec 1].

KY2. A station has three key purposes, each a separate key per station
identity: identity (purpose 1), request signing (purpose 7) and message
signing (purpose 9). A key of one purpose signs nothing of another purpose
[BK06 "Which secrets exist"; BK06 "Message key and its attestation"; OWN-KS].
The delegation key (purpose 8) is per parent, in a separate instance, and is
not a station key [OWN-KS]. Purpose 6, station-caller, is the dispatcher
caller custody of OQ24 option B: not a key purpose of a station today, and no
gate reads a purpose-6 binding until that unit exists (gate 4).

KY3. The key service takes the caller from the kernel peer credential of the
connection, never from a field of the request, and admits it only when the
exact (uid, generation) is `active`; a retired or bumped generation loses its
bindings and its connections [BK06 "The kernel establishes the peer"; GJ 4;
UM 8]. Its refusals are its own closed codes: `generation_inactive`,
`generation_mismatch`, `peer_identity_unavailable`, `binding_not_found`,
`peer_binding_mismatch` and `signer_identity_mismatch` [OWN-KS]. The kernel establishes the account; the
generation is the journal's current one for that account, so a survivor of an
old generation is excluded only by the complete absence proof that precedes
the successor's `active` (R14) [UM 6.1].

KY4. One OS account is one message author at the key holder [RUL-1; DEC D7].
The bridge runs under the one shared messaging account and never under an
agent account [BK24 "What the bridge consists of"]. Only the author-side step
runs under the agent's own account: the process that asks the key service to
sign that agent's message. The sign request names no identity, so "sign as
another station" cannot be expressed: a process under account A gets A's own
key, or `binding_not_found` when A has no message-author binding; a payload
that carries another key or another author is refused
`signer_identity_mismatch` before any signature [OWN-KS]. The agent account
holds no carrier credential. It hands a complete signed envelope to the
bridge's local submit endpoint, which accepts only a complete signed envelope
for its own room and recipients, refuses anything else
(`message_envelope_unsigned`, `message_audience_mismatch`) and keeps the
carrier token with the bridge's shared account [RUL-3; BK24 "The outgoing
path keeps exact bytes"]. Two stations sharing one account is not a valid
configuration: the slot table maps one recipient to one account (section 11),
and [absent x provision] and [provisioned x enroll] refuse
`station_account_shared`. Limit, stated: this rule is about the application
signature; at the carrier layer the bridge holds the per-identity carrier
client and is trusted not to publish unsigned content under a station
identity.

KY5. A verifying signature proves the author, not a right [C24 "Security
considerations"; BK06 "Message key and its attestation"]. Rights in this
contract come only through J1; the admission of a message as work is no
part of version 1 (section 7.2).

KY6. A station name is never bound to a new key. The key service authorizes
no rotation today: the key is stable per independent root, epoch and path
[OWN-KS]. Every [state x key rotation] refuses, and R13 is reserved for a
later unit. R02 records the key identifier of each purpose at every enroll (section
4.1). At enroll, and again in the key-service confirmations of a bump
(R14), the key identifier of each purpose MUST equal the one the latest
R02, or R16 where a retirement is the latest record, holds for the name,
where one is recorded; otherwise gate G2 refuses
`station_rotation_unrecorded` at enroll and the bump condition does not hold
at a bump, so KY6 is enforced on both paths and no successor generation
becomes `active` under another key. Retiring an account does not revoke a
persistent identity, and a later enroll of the same name returns the same key
[BK06 "The account ends, the identity remains"; UM 5], which is exactly why
re-provision of a retired name needs its original principal or a recorded
owner act (G1). Stated plainly, because the rule above has this cost: this
contract contains no remedy for a compromised station key short of retiring
the name itself and raising a new name under new keys; retiring only the
account returns the same key. This closes the earlier open question on
rotation while running (OQ13): refuse, as the key service owner answered.

## 11. Admission: J1, the validated binding and the slot table

This file states where the joins sit. It does not define grants.

J1. Before a station is provisioned or started, a grant is checked against
the chain. The checker is the grant checker behind the message origin, with
its chain view, its observation and its closure journal; the dispatcher
verifies no grant and consumes the validated binding [RUL-2; DEC D9; OWN-DI].
J1 is gate 2 of [stopped x start], so it is evaluated at every restart, and
the last gate before the record in G1. Its verdict is "admitted", "refused"
or "unavailable"; the last two both refuse, and a verdict is never reused
from an earlier start [BK07 "Dispatcher and the one-shot transaction"; BK13
"Revocation and unknown state"]. The book places this check at the
dispatcher [BK13 "Who checks the right"]; the ruling refines the book for the
first enforcing run.

Before a message could become work for a station it would be checked at the
bridge (the J2 of the sources [BK24 "Trust gate"]). Version 1 admits no
message as work and spends no code of that check (section 7.2); the proposed
form of J2 is carried in the companion of section 7.2. The bridge-side rules
this contract does carry are the submit endpoint and the carrier custody of
KY4, which bind whether or not the companion is adopted.

The validated binding (PROPOSED, OPEN OQ19) is what the grant checker hands
to the dispatcher [ADD A.3; AP 9]. Until the unit named in OQ19 defines its
form, this file fixes only what the cells need:

- written by the grant checker, once per admitted request, never by the
  requester or the station;
- members: the origin event reference and the prepared identity; the
  principal; the grant chain reference and its digest; the action and its
  target (host, account, generation, plan pins digest); the revocation
  verdict with its state number and time; the expiry;
- consumed once by the dispatcher, for the one operation that names it (R01
  or R03);
- stale, and refused `station_binding_stale`, when it is absent, already
  consumed, names another operation or target, is past its expiry, or carries
  a revocation verdict older than the allowed snapshot age of 60 seconds
  [BK13 "Revocation and unknown state"].

The slot table maps each recipient (a station identity) to exactly one
account. Its single owner is the dispatcher [ADD A.2; AP 8; RUL-2]. An entry
is written by the enroll (R02) and released by R16. How an account is created
stays with the user manager. After a lost session journal a slot is unusable
until its clearance, and the clearance is the dispatcher's record that cites
the R09 of that account [AP 7; AP 10].

Editable text is never the enforcement boundary of any join [C24 dec 4].

## 12. The one-task station

A one-task station is a station with one execution, whose stop is followed
at once by its retirement. It uses the cells of section 3 and no other lifecycle. It
receives its own account, identity, keys, home and trust binding, with a
fresh context composed with the required root [C24 dec 7; C24 "Persistent
stations and task-lifetime spawn"]. NEW: it has no lifecycle permission, so
gate 11, scoped as section 6.1 scopes it, admits its single start and
refuses a second start; the sources say a start without that permission is
single [BK07 "Permission for a successor"]. Its bounds are those of a
task-lifetime station (K2), spent by the clocks `account_bound` and
`execution_bound` of section 4.5. Retirement follows authoritative task
completion and durable handover, never provider exit or a delivered doorbell
[C24 "Persistent stations and task-lifetime spawn"], and decided (OQ16
closed, option B for the first step) it is authorized by an explicit release
from the raising orchestrator named by its provision grant, recorded in R15
and checked at G5 as part of `station_retire_not_authorized`; nothing is
inferred from a board state in the first step, and a raising orchestrator
that is gone leaves the release to the operator. A never-enrolled one-task
station retires without the export check (G5), and a station provisioned
onto a release that cannot enroll is repaired by that retire and a new
provision, never by a profile update out of `provisioned`, whose update
cells end in the enrolled row `stopped`; NEW, stated because it forecloses
the repair-by-update reading.

## 13. Who owns what

Exactly one owner per row. No service writes into another's state; it asks the
owner through the owner's interface and records its own request [C24
"Ownership and records"; UM 1; BK08 "One owner of the home"].

| Responsibility | Owner | Others may only | Source |
| --- | --- | --- | --- |
| Station state record: state, state version, epochs, start and stop journal, unknown-outcome reconciliation, records R00 to R24 | DI, under its own service account in a protected state directory over a kernel-peer-checked socket | propose transitions (CRO for a requester); report events; perform effects only under an operation DI recorded. The station description in the workbench registry on the board is read-only to DI and is owned there, outside this record. SH reports liveness and owns none of it. A record file edited directly under the requester's account produces no state any effect owner accepts. | BK07 "Workbench"; DEC D1 as amended by the OQ18 ruling; OWN-DI; OWN-CR |
| Station operations: proposal and client-side phase tracking | CRO | DI commits or refuses every proposed cell; the session host and the party responsible request operations through CRO or directly from DI | OWN-CR; DEC D1 as amended (C24 dec 9 names curator-run owner of the lifecycle; the OQ18 ruling refines it: CRO proposes and tracks, DI alone commits, SR1) |
| Station operations: reconciliation of the authoritative record | DI | effect owners report outcomes to DI | DEC D1 as amended |
| Account and generation | UM | read the generation journal; the dispatcher requests create, bump and retire within its role, which is not in the landed dispatcher slice | C24 dec 9; UM 1; UM 2; GJ 1; OWN-DI |
| Home: paths, owners, modes, removal | UM | none write; the station writes inside its three writable paths | UM 1; UM 7 |
| Home: content, composition, digests, lease | CU | DI requests and binds leases under R03; nobody edits the lease store | C24 dec 9; HL01; UM 1 |
| Profile: approved release content and trust pin | CU | a station may request its own update and installs nothing unapproved | C24 dec 3; UM 7 |
| Session record, slot table, capacity claims | DI | read; the slot entry is requested by the enroll | RUL-2; ADD A.2 |
| Start and stop: physical authority, consumption of the validated binding | DI | CRO and the session host ask; no second privileged path exists | C24 "Ownership and records"; BK05 "Two narrow privileged entries"; RUL-2 |
| Grant check J1 and the revocation feed | GC | the dispatcher consumes the binding and the feed | RUL-2; DEC D9 |
| Start: privilege transition, start receipt, gates 15 to 18 | LA | the dispatcher invokes it | BK05 "Transition from root to agent"; HP 7; DEC D3 |
| Stop effect and absence proofs P1 and P5 | UM | all others consume R09; none substitutes its own | UM 5; UM 6.1; OWN-UM |
| Host qualification: issue and revocation | UM, the qualification reconciler | read | UM 1; BK05 "Qualification revocation" |
| Process observation: P2 and liveness readings | CU | UM reports process-appears readings from its own enumerations (section 2.2) and owns the enumeration proof P1; DI supplies the manager observation as input, never as proof; SH reports logical-session liveness and process exit and owns no record | HL observer; BK07 "Wake-up and context transfer" |
| Identity: latch record and name file (PROPOSED) | CU | read | section 9.2 |
| Identity: full typed identity (PROPOSED) | CRO | read | section 9.2; OWN-CR |
| Keys: custody, signing, bindings | KS | the station asks for a signature over a socket | C24 dec 1; C24 dec 9; RUL-2; OWN-KS |
| Message author: one account maps to one message-signing key | KS | a process under another account gets its own key or a refusal | section 10, KY4; RUL-1 |
| Dispatcher caller key of an orchestrator station (PROPOSED deviation, OQ24 A; OPEN OQ27) | the installer, only if the owner adopts the deviation, until key-service purpose-6 custody | under option A the caller account reads it; under the alternative nobody does and DI authenticates its single caller by kernel peer uid | DEC D7; OWN-KS |
| Model credential: enrollment, lease issue, revocation | CB | the gateway holds a service lease | C24 dec 9; BK09 "Who holds the credentials" |
| Model credential: holding and use for a station's requests | MG | the station holds a stub only | BK09 "Model provider through the gateway" |
| Carrier credential and carrier account of a station identity | AL, under the shared messaging account | the station hands a signed envelope to the submit endpoint | RUL-3; BK24 "What the bridge consists of" |
| Messages: carrier custody and the local submit endpoint | AL | the station hands a signed envelope to the endpoint; no message is admitted as work in version 1 (section 7.2) | RUL-1; RUL-3; BK24 "Trust gate" |
| Session: logical session, input queue, input fence | SH | the station holds the harness channel under its account | BK07 "Service, runner and the single writer" |
| Export of the work product | OPEN OQ14 | none until decided | BK07 "Dispatcher and the one-shot transaction"; HP 7 "R-TRANSFER" |
| Fixed and changeable start fields | the approvers of section 9.1 | propose a change to the approver | DF A |

The station registry record and assignment belong to the task board, and
heavy-run scheduling to its own owner [C24 dec 9; C24 "Host budget"]; both are
outside the twelve services and write none of the records of section 4.1.

## 14. Negative obligations

Each forbidden outcome names the cell that enforces it. Each needs a nearby
valid control in the owning implementation.

| Forbidden outcome | Enforcing cell and code | Valid control beside it |
| --- | --- | --- |
| Two transitions from one state version | SR2: exactly one commits; a losing proposal refuses `station_state_stale` with no gate verdict, a losing reported or delivered-once event is queued by DI and committed against the re-read row | one transition from one state version commits, and a reported reading that raced it is still recorded |
| Two provisions of one name, or a name re-admitted after record loss | SR4: create-if-absent on R00; the losing create is answered by the row it finds; SR3: no provision while R00's absence is unproved after loss | one provision creates the reservation and proceeds |
| A state produced by editing a record file under the requester's account | SR1: only DI writes the record, under its own account in a protected directory; an edited file is no record and every effect owner takes state only from DI over its peer-checked socket | a proposal over that socket commits a cell |
| A physical start running after the station left `starting` | SR4: leaving `starting` closes the fence and records the withdrawal in the same commit; LA revalidates fence and epoch before the receipt and starts a withdrawn execution never | a start revalidated while still in `starting` binds one incarnation |
| Two processes of one station at once | [stopped x start] is the only start and is one compare-and-set; [starting, running, stopping x start] `station_incarnation_exists`; every held row x start `station_held`; gate 16 `station_account_not_quiet`; the launcher rejects a second start of one execution | a start from `stopped` binds one incarnation |
| `stopped` reached while a process may run | no cell enters `stopped` without R09 (U4); G13 `station_absence_unproven` | a quiet account reaches `stopped` by P1 |
| A process reading that is lost | [every row with an account x process appears] writes R06 | a bind with an equal reading writes R04 |
| A first start with no evidence that nothing ran | R02's P5 line requested by DI and presented in [enrolling x stop confirmed]; [enrolling x proof: effect completed] gate G13 without that P5, `station_absence_unproven` | an enroll whose P5 line completed reaches `stopped` and starts |
| A stale absence proof answering a newer reading | U1 and G11: the proof must name the open stop operation and its interval must begin after the reading; `station_proof_mismatch`, then `station_absence_unproven` | a proof enumerated under the open stop operation after the reading reaches `stopped` |
| A proof about a stop moving a held create or enroll | section 2.2 and G13: a proof column answers only the row's own operation; a stop proof there refuses `station_proof_mismatch` | the create's own P4 in the same row reaches `retired` |
| A start with a changed profile digest | gate 17, `station_profile_digest_mismatch` | approved unchanged controls admit the start |
| A station-written file loaded as a platform control | gate 17 and gate 18 | a file under `H/work/` classified as data does not block the start |
| A station reading another station's home | [absent x provision] creates the distinct group and modes; gate 18, `station_skeleton_invalid` | each station reads its own context and writes its own state |
| A station identity or message key readable by a station | [provisioned x enroll] binds keys only at the key service (R02); gate 18 | the station signs through its socket |
| A model token in a station account | gate 6, `station_credential_mode_refused` | a start in the mode without secrets reaches the model through the gateway |
| A carrier token in a station account | KY4; gate 18 for a file; the submit endpoint refuses `message_envelope_unsigned` | a signed envelope is published by the bridge |
| Release of an account while any thread runs under its uid | [stopping x stop confirmed] gate G11 and [retiring x proof: effect completed] gate G12, `station_absence_unproven` | a quiet account reaches `stopped` and `retired` |
| A generation that reached `retiring` or `removed` returned to use | [bumping, held:bump x proof: effect did not happen] gate G13, `station_bump_committed` | a bump refused before its commit returns to `stopped` |
| A retired name enrolled with a different key | [provisioned x enroll] gate G2, `station_rotation_unrecorded`, and the same identifier check in R14's bump confirmations | the same key enrolls and bumps |
| A retired name handed to a new principal with its retained key | [retired x provision] gate G1, `station_principal_mismatch`, without the original principal of R00 and R16 or a recorded owner act | the original principal re-provisions and enrolls with the same key |
| A process under station A signing with station B's key | key service: the request names no identity; `binding_not_found` or `signer_identity_mismatch` before any signature | station A signs as station A |
| Two stations sharing one account | [absent x provision] and [provisioned x enroll], `station_account_shared` | one station per account provisions and enrolls |
| A lost start retried blindly | [starting x starter crash] sends no second request; [starting x unknown or stranded outcome]; [held:start x start] `station_held` | a crash at phase `lease_requested` resumes the same acquire once |
| A missed liveness reading treated as a stop or a release | [running x liveness reading missed] goes to `held:live` and releases nothing | an equal reading keeps `running` |
| A stop or reclaim outside the table | K9; [running x stop requested] is the only entry | an authorized stop request stops |
| Anything released from unknown | every held row: no cell releases without P1, P3 or P4 | a proved outcome leaves the held row |
| A session recorded as ended from a lost journal | [every row with an account x session journal lost] opens an absence debt and ends nothing | a station with an intact journal stops by P1 |
| A home archived at retirement | K8; [retiring x proof: effect completed] removes the home | the exported work product survives retirement |
| A profile update installed under a live or unknown lease | [starting, running, stopping x profile update approved] `station_busy`; gate G6 `station_home_leased` | an update installs in `stopped` |
| A home removed without an absence proof | R15: UM removes no home before its P1 is accepted as R09 in `retiring`; [retiring x proof: effect completed] gate G12 `station_absence_unproven` without that R09 | a retirement with its R09 removes the home and reaches `retired` |
| A dispatcher daemon opening on an unpinned seam, or a fresh state inferred from a missing file | section 17 daemon configuration: with any unpinned seam DI stays closed and capacity-only; a latched must-exit of the launcher ends the DI process as a journal sync failure does; "fresh" is never inferred from a missing file, and SR3 keeps it closed where epoch continuity is unproved | a daemon whose seams are all pinned in protected configuration opens and admits starts |

## 15. Open questions

Each question has two options and the one who decides. None is decided here.
The runs questions (OQ20 and row 12) are no longer questions of this file;
they stand in the proposed companion of section 7.2 for the owner.
Closed since the previous draft: OQ9 (section 6.2, pending one confirmation),
OQ12 (section 9.2), OQ13 (KY6) and OQ17 (KY4). Closed in this draft by owner
decision and removed from the table: OQ1 (option A, stop at expiry, K2 and
section 7.1), OQ5a to OQ5e (stop within 300 seconds in every case, section
7.1), OQ6 (split: unreadable revocation state holds without a time limit
under an operator alarm, lost verified time stops after at most 10 minutes
monotonic, section 7.1), OQ8 (option A, operator-only reclaim, K9), OQ16
(option B for the first step, explicit release by the raising orchestrator,
section 12) and OQ18 (the dispatcher holds the authoritative station state
record, SR1, SR6 and section 13).

| Id | Question | Option A | Option B | Decides |
| --- | --- | --- | --- | --- |
| OQ2 | How far ahead a grant is renewed (K2). | A fixed lead before expiry, set by policy. | A fraction of the grant's validity. | Grant contract owner; operator. |
| OQ3 | The restart budget (section 6.1). | A count and backoff carried in the lifecycle permission of each station. | One host policy default, with a per-station override. | Dispatcher owner and session host owner; operator. |
| OQ4 | The values of `liveness_interval` and `silence_deadline` (section 4.5). | One platform constant each. | A per-policy value inside a published bound. | Curator, with the curator-run owner. |
| OQ7 | A station whose model forwarding stays closed (K7). | Wait with no limit. | Stop after a policy bound. | Credential broker and gateway owner; operator. |
| OQ10 | Where the a2a station link lives and who owns its parent (section 8). | In a station-owned directory inside H, keeping the C32 ownership rule. | In the root-owned sticky native directory, by amending the C32 ownership rule. | a2a owner and user-manager owner; the operator decides CIP-0032. |
| OQ11 | The station-readable `station.key` of the C32 link under one account per station. | Keep it as a link secret that is not a station key, since the account is already authenticated by the kernel peer. | Remove it and authenticate the link by the kernel peer only. | a2a owner; operator. |
| OQ14 | Who runs the export of the work product before removal (K8). | A fixed approved program under the station account, as its own fenced execution through the launcher, after confirmed absence and while the generation is `active`; this adds an export event to the table. | The user manager, from quarantine, after the stop. | User-manager owner and dispatcher owner. |
| OQ15 | Whose long-lived identity holds a workplace, the agent's or the place's [BK07 "Workbench"]. | The agent's identity occupies the place by lease. | The place owns the identity; the agent is replaceable. | Owners, as the book states. |
| OQ19 | Which unit defines the form of the validated binding (section 11). | The grant checker's contract. | The dispatcher's hook contract. | Grant checker owner and dispatcher owner. |
| OQ21 | The value of `end_to_absence` (section 4.5). PROPOSED: option B, the dispatcher owner's answer, pending the user-manager owner's confirmation. | The `stop` bound of the dispatcher policy. | The dispatcher policy's stop bound PLUS the user manager's published quiet interval. | Dispatcher owner (answered B) and user-manager owner (confirmation outstanding). |
| OQ22 | Entries a harness creates in `H/.harness/` beside `state/` (section 8). | None are admitted; the adapter redirects them into `state/`. | A closed list of entry classes per runtime mapping, each classified as data. | Curator and the user-manager owner. |
| OQ23 | Repository-native discovery beyond the first wave (section 8, gate 17). Wave 1 is explicit native-project mode by C24 dec 8 and is not this question; what the mapping classifies there is decided in gate 17. | Strict mode as the follow-up: nothing in the clone is loaded as a project control once a runtime is qualified for it. | Native-project mode indefinitely, with every loadable path listed as a project control per mapping. | Curator; operator. |
| OQ24 | The dispatcher caller key of an orchestrator station (KY1). PROPOSED: option A, the key service owner's answer for the first enforcing run, then the purpose-6 unit; adoption also needs OQ27. | Keep the installer-made file, pinned by the static statement, at a path the installer contract publishes, for the first enforcing run, until custody moves. | Move caller signing to the key service (purpose 6, station-caller) before the first enforcing run. | Key service owner (answered A, then the purpose-6 unit) and dispatcher owner. |
| OQ27 | May the first enforcing run deviate from C24 decision 1, "The station can request signing but MUST NOT be able to read the key file", by keeping a station-readable dispatcher caller key file (OQ24 option A, KY1)? | Yes: record the owners' amendment of decision 1 for this one key and run; gate 18 admits the one file by metadata until the purpose-6 unit. | No: no station-readable caller key exists in the first run; DI authenticates its single caller by kernel peer uid until the purpose-6 station-caller unit, and gate 18 refuses any such file. | Owner. |
| OQ26 | Renewal of the dispatcher policy window for a persistent station (K2). | The window is renewed with the grant, by the same act. | A persistent station carries no finite policy window. | Dispatcher owner; operator. |

## 16. Alignment with the Swarma book

Marks: same (cited, not copied), refines, conflicts (needs an owner decision),
new. Headings are English renderings; the line is the heading line in the file
at the pinned commit.

| Rule here | Book source (file, heading line) | Mark |
| --- | --- | --- |
| One agent, one account, one identity, own keys, home and root context | `05-polzovatel-i-set.md`, line 212 "Station and its guarantees" | same |
| States of the account and forward-only retirement | `05-polzovatel-i-set.md`, line 47 "Account, generation and journal" | same; the station states of section 3 are new on top of it |
| P1, the absence proof | `05-polzovatel-i-set.md`, line 17 "Load: a resource group per generation" | same |
| P3 and P4 as observation states | `05-polzovatel-i-set.md`, line 47 | same |
| P5, the never-started evidence | `06-klyuchi.md`, line 122 "Total stop" | refines: the book states the rule for the total stop; here it is required before every first start |
| Changed boot identifier is not P1 | `07-zapusk-i-host-sessiy.md`, line 151 "Wake-up and context transfer" | refines: the book says a changed boot identifier confirms that old processes are gone; this contract still requires R09 |
| Start receipt, single start of one execution | `05-polzovatel-i-set.md`, line 69 "Transition from root to agent" | same |
| Homes are never archived; export before removal | `05-polzovatel-i-set.md`, line 83 "Homes and results"; `07-zapusk-i-host-sessiy.md`, line 44 | same; the executor is OQ14 |
| Lifetime of persistent and task-lifetime stations; the permanent team | `05-polzovatel-i-set.md`, line 83; `07-zapusk-i-host-sessiy.md`, line 44 | same |
| Restart needs a lifecycle permission and proved absence | `07-zapusk-i-host-sessiy.md`, line 103 "Permission for a successor" | same |
| Keys: the agent asks a signer; kernel peer | `06-klyuchi.md`, lines 51, 86 | same |
| The dispatcher caller key in the orchestrator's home | `06-klyuchi.md`, line 9 "Which secrets exist" | conflicts (needs an owner decision): the book names it an explicit exception, C24 decision 1 forbids a station-readable key file, and KY1 therefore carries it only as PROPOSED with OQ27 to the owner |
| One account is one message author at the key holder; the bridge under the shared messaging account | `06-klyuchi.md`, line 51; `24-soobscheniya-i-most.md`, lines 187, 218 | same |
| The account ends, the identity remains | `06-klyuchi.md`, line 96 | same |
| No model credential at the station; stub and gateway | `09-uchetnye-dannye.md`, lines 101, 148 | refines: the book keeps a readable-token mode as an owner-selected exception; station/1 admits only the mode without secrets |
| Waiting on closed model forwarding (K7) | `07-zapusk-i-host-sessiy.md`, line 151; `09-uchetnye-dannye.md`, line 162 | refines: the book states waiting for a new provider login; the renewal case is applied by analogy |
| J1 behind the message origin | `13-doverennosti.md`, line 28 "Who checks the right" | refines: the book places the check at the dispatcher; the ruling places the checker behind the origin and has the dispatcher consume its binding |
| J2 at the bridge | `24-soobscheniya-i-most.md`, lines 109, 169 | not carried in version 1 (section 11); PROPOSED in the companion of section 7.2 |
| Runs inside a station, J2 and unknown delivery from a transcript | none in version 1 | not carried: PROPOSED in the companion of section 7.2, for the owner |
| Revocation propagation bound and "unavailable" as refusal | `13-doverennosti.md`, line 94 "Revocation and unknown state" | same |
| Renewal without widening; the 10 minute bound on lost verified time | `13-doverennosti.md`, line 124 | same |
| Qualification revocation within 300 seconds | `05-polzovatel-i-set.md`, line 283 | same |
| Cross-owner grant seal | `14-doverennosti-mezhdu-vladelcami.md`, line 40 "Revocation" | same |
| Unknown outcome is not absence; no blind repeat | `22-effekty-ostanovka-federaciya.md`, line 7; `05-polzovatel-i-set.md`, line 47 | same; the held rows are new |
| Lost dispatcher state: unknown records keep their claims; the node opens by operator decision | `07-zapusk-i-host-sessiy.md`, line 44 | same; the absence debt is new |
| Owner channel bound at raising | `24-soobscheniya-i-most.md`, line 89 "Owner channel" | same |
| Platform-owned controls checked before every start | `07-zapusk-i-host-sessiy.md`, line 38 "Immutable launch boundaries"; `08-curator.md`, line 31 | same |
| Total stop | `06-klyuchi.md`, line 122 | same |
| One owner of the station state with a compare-and-set: the dispatcher; the station description in the workbench registry on the board, read-only to it; the session host reporting liveness and owning no record | `07-zapusk-i-host-sessiy.md`, line 161 "Workbench"; line 151 "Wake-up and context transfer" | refines: the book gives the registry the launch description and the dispatcher the start and stop effects; the ruling joins them as SR1 and SR6 state |
| Stop within 300 seconds on revocation, expiry, seal, policy removal, total stop and account block; hold without limit and an operator alarm while the revocation state is unreadable | `05-polzovatel-i-set.md`, line 283; `13-doverennosti.md`, line 94 | refines: the 300 seconds are the book's qualification bound extended by owner decision; the 10 minute bound stays only on lost verified time, `13-doverennosti.md`, line 124 |
| Name latch and synthetic name | none | new (PROPOSED) |
| The single lifecycle table, the held rows, records R00 to R24 | none | new |

## 17. Implementation units

Sizes are in LU: one LU is producer, review, one fix round and landing, about
three hours. Sizes marked "owner" were given by the owner of the service on
its own row; the others are first estimates and are not calibrated against
delivered units. "Exists" cites what a source of this file or an owner
statement shows; nothing was run.

| Repository | Unit | Exists or new | LU | Depends on | First negative test |
| --- | --- | --- | --- | --- | --- |
| curator-spec | Paired vectors for the cells of section 3 | new | 3 | this file accepted | a start in `running` refuses `station_incarnation_exists`, beside a start in `stopped` that is admitted |
| curator-spec, with the grant checker and the dispatcher | Form of the validated binding (OQ19) | new | 1 | OQ19 | a consumed binding refuses `station_binding_stale` |
| curator | Home-lease store and independent observer | contract exists: `protocol/home-leases.md`, `schemas/home-leases-v1/`; implementation new | 3 | none | manager and record agree, the kernel reading differs: bind refuses |
| curator | Liveness readings over the bound incarnation | new | 1 | the unit above; OQ4 | an unreadable kernel field yields `held:live`, never a stop |
| curator | Latch record and name file | new | 1 | the two confirmations of section 9.2 | one changed byte in the name file refuses the start and leaves the file as found |
| curator | Approved-release composition and updater (R12, pin last) | new | 2 | user-manager skeleton interface | an update under a blocking lease refuses with no control changed |
| curator-agent-launcher | Station operations with phases, including `start_requested`, as the proposing client of the dispatcher's record | extends the launcher lifecycle record named in C24 "Current state"; new | 3 | curator lease store; the dispatcher's standing-runtime mode below, which owns the record, the compare-and-set and the epochs: there is no separate station-state service and no row for one | a crash after `start_requested` yields `held:start` and no second start request; a record file edited under the requester's account commits nothing |
| curator-agent-launcher | Start gate order as proposal hygiene and the advice check at its one position between gates 16 and 17; advice only, producing no contract code (section 6.2) | new | 1 (owner) | the launcher's gates 15 to 18 | the advice answer for a mismatching digest is returned only at the advice position and names no verdict of its own; the launcher's gate 17 refusal remains the one that binds, before provider execution |
| curator-agent-launcher | Session-manager observation: process, termination and no-start on every command | contract and one consumer landed (owner); remainder new | 1 (owner) | none | an observation without a process tuple cannot bind |
| curator-agent-launcher | Station link admission proposal | no existing element (owner): only a presence check of a credential file | 1 | OQ10, OQ11 | a legacy credential directory yields no admitted start: DI refuses `station_link_unregistered` at gate 5 on the proposal |
| curator-agent-launcher | Full typed identity latch (PROPOSED) | new | 2 (owner) | the latch record; the owner's admission | the same name with a changed kind or origin yields no admitted start: CU refuses `station_identity_mismatch` at gate 3 and the station record stands as found |
| swarma-user-manager | Account writer for create, retire and bump | contract exists: `spec/stations-v0.md`; journal format and offline tools exist; new | 4 | journal adapter alignment [UM 11] | a replayed create allocates no second identity |
| swarma-user-manager | Stop, P1 and the external-object inventory | contract exists: UM 6.1; new | 3 | qualified Linux backend | a double-forked survivor yields `processes_remain` and no release |
| swarma-user-manager | P5, the never-started evidence | new | 1 | the launcher's receipts and DI's start-fence record of SR4, from the dispatcher's standing-runtime unit | a generation with a start receipt gets no P5 |
| swarma-user-manager | Skeleton install with `H/.identity/` | contract exists: UM 7; new | 2 | section 8 | a station cannot replace a managed file through its sticky parent |
| swarma-user-manager | Launcher: start receipt and gates 15 to 18 | new | 2 | none | a second start of one execution is rejected |
| swarma-user-manager | Static deny rule and test-uid probe | not yet opened (owner) | not sized | none | not stated by the owner |
| swarma-user-manager | Service-account creation | not yet opened (owner) | not sized | none | not stated by the owner |
| swarma-user-manager | Per-account firewall rules | not yet opened (owner) | not sized | none | not stated by the owner |
| swarma-dispatcher | Daemon configuration unit | on the owner's board | 2 to 3 (owner) | none; precedes any standing-runtime work | with any seam unpinned in protected configuration the daemon stays closed and capacity-only and admits no start; a latched must-exit of the launcher ends the dispatcher process exactly as a journal sync failure does; a missing state file after a crash is never read as "fresh" (owner's stated negative) |
| swarma-dispatcher | Standing-runtime mode beside the one-launch budget, holding the authoritative station state record (SR1) with its compare-and-set, epochs, start fence and journal continuity, and DI's own evaluation of start gates 5 and 6 and of the link and owner checks of G2 (no contract code of those checks is produced by any client) | new [DF C] | 5 to 8 (owner) | the unit above; K1 to K4 | a second start of one station is refused; two transitions from one state version: exactly one commits; a name whose reservation may exist is never re-admitted as absent; a start withdrawn by leaving `starting` never reaches a receipt |
| swarma-dispatcher | Consumption of the validated binding at every start | hooks exist for one-shot executions (owner); new for restarts | 1 (owner) | OQ19 | a stale binding admits no start |
| swarma-dispatcher | Revocation feed, consumer side | new [DF C] | 2 (owner) | the producer below; the closed decisions of section 7.1 | an unknown revocation state never counts as "not revoked": it holds with an operator alarm and stops nothing; a revoked session grant is suspended at once and stopped within 300 seconds |
| swarma-dispatcher | Claims for the life of a station and reclaim through a stop | new | 1 (owner) | none: reclaim is operator-only (K9) | a reclaim sends no signal outside a stop request, and the dispatcher alone reclaims nothing |
| swarma-dispatcher | Slot table, journal-loss fence and clearance | new | 1 | none | a slot with a lost journal and no clearance admits no start |
| grant checker behind the message origin | Revocation feed, producer side | new seam | 1 (ruling) | chain observation | a revoked session grant reaches the dispatcher as a closed capability |
| swarma-keymaker | Live bindings keyed by (uid, generation), purpose-9 selection, intent, result and recovery | partly exists (owner) | 3 to 4 (owner) | generation journal reader | a payload carrying another author is refused `signer_identity_mismatch` before any signature, beside station A signing as station A |
| swarma-keymaker | Purpose-6 station-caller custody of the dispatcher caller key (OQ24, after the first enforcing run) | new | not sized | OQ24, OQ27; the first unit | a station-readable caller key file refuses at gate 18 once purpose-6 custody exists, beside a purpose-6 signing that succeeds |
| swarma-keymaker | Rotation record R13 | later unit, not in station/1 (owner) | 1 (owner) | the first unit | a name with a different key and no R13 does not enroll |
| swarma-keymaker | Provisioning before `active` for a bump | open in UM 6.2; new | 2 | joint contract with the user manager | a binding before re-admission refuses |
| swarma-credential-broker and gateway | Service leases and a listener per generation | contract extension unpublished per the book; new | 4 | broker contract extension | a credential sent by the station is rejected; no token reaches the station environment |
| swarma-credential-broker and gateway | Renewal failure closes forwarding and reports the capability | new | 1 | OQ7 | a failed renewal forwards nothing and stops nothing |
| swarma-credential-broker and gateway | Gateway install unit | named by the owner of the user manager | not sized | the service-account unit | not stated by the owner |
| a2a-swarm | Bridge submit endpoint | new; on the first-step path | 1 (ruling) | none | an unsigned body is refused `message_envelope_unsigned` |
| a2a-swarm | Station link under one account per station | enrollment exists per C32; new | 1 | OQ10, OQ11 | a link with a foreign owner is not admitted |
| swarma-session-host | Input fence tied to R04; capability flags | new | 2 | curator lease store | input before a bound lease is not delivered |
| swarma-session-host | Restart inside a lifecycle permission and budget | new | 2 | OQ3 | a restart without permission is refused |
| task-board | Station element equal to the router snapshot | named in C24 "Implementation plan", leaf 2; new | 2 | shared record version | an assignment to a station in a held row is refused |

Total of the sized units: 63 to 68 LU. Five units are not sized by their
owners and are outside that total. The change from the previous draft is the
lifecycle-only scope of version 1: the four units that existed only for the
proposed runs model (1, 1, 3 and 2 LU) moved to the companion of section
7.2, which is 7 LU less here; the OQ18 change of the previous draft stands
(the separate station-state record row is gone and the dispatcher's
standing-runtime row holds that record at 5 to 8 LU).

## 18. Sources not carried

CIP-0024 sections "Wave 1 project mode" (beyond OQ23), "Host budget" (beyond
K9), "Compatibility and migration" and question 1 of its open questions
concern project-source discovery, heavy-run scheduling and the migration of
existing work places; they are not station lifecycle and are not restated. The
station record fields of the registry (the router snapshot list) stay with
their owners [C24 "Ownership and records"]. Network profiles, resource limits
and the guarantee matrix [BK05] bound a running station and add no state or
event. CIP-0024's "Per-station a2a daemon" (a station's own daemon and client per
identity, its dec 6) is not carried as a rule of version 1: the bridge runs
under the one shared messaging account (KY4), and a per-station daemon would
arrive, if at all, with the adopted form of the station link under OQ10 and
OQ11 and the companion of section 7.2. The restore of the generation
journal [UM 8] closes every consumer at once and reaches a station only as
`station_generation_inactive`. The process
fate table of the launcher [HP 7 "R-FATE"] is carried only as the column
"starter crash" and the column "capability report". The macOS station backend
[UM 1] is outside the first deployment, a Linux host. ENV 8.1 is not cited
for the station home: its snapshot-lifetime rule keeps live sessions out of
managed homes, which are provisioning inputs there, while a station home is
the one long-lived home of UM 7 in which the bound incarnation of this
contract runs; the home rows of section 8 rest on UM 7 and UM 6 alone.
