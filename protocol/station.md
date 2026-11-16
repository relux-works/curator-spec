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
run is a special case of the same lifecycle (section 12).

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
| CRO | curator-run, station operation | Runs outside the station account, for the party responsible for the station. Owns the station state record and commits every transition of section 3 (section 1.3). May evaluate gates [DEC D1; DEC D2; OWN-CR]. |
| CRX | curator-run, executor | Runs inside the station account after the privilege transition. It is part of the station. It commits nothing and evaluates no gate: a station cannot attest its own platform controls [DEC D2; OWN-CR; HP 7 "D-EXECUTOR"]. |
| UM | user manager | Creates, bumps and removes accounts; stops an account and proves absence [UM 1; BK05 "Two narrow privileged entries"; OWN-UM]. |
| LA | launcher | Starts one approved program under an active account and writes the start receipt; authoritative evaluator of the profile digests and the home skeleton [BK05 "Transition from root to agent"; HP 7; DEC D3]. |
| DI | dispatcher | Holds the session record, the slot table and the capacity claims; owns the physical start and stop authority; consumes the validated binding [BK07 "Dispatcher and the one-shot transaction"; RUL-2]. |
| GC | grant checker | The checker behind the message origin: chain view, observation, closure journal. It is the J1 join and the producer of the revocation feed [RUL-2; DEC D9]. |
| CU | Curator | Owns home content, composition, digests, the home lease, its independent process observer and the name latch record [C24 dec 9; HL01; HL observer]. |
| KS | key service | Holds the station keys and signs on request [C24 dec 1; BK06 "The kernel establishes the peer"]. |
| CB | credential broker | Holds enrolled credentials and issues bounded leases [C24 "Ownership and records"; BK09 "Mode without secrets at the agent"]. |
| MG | model gateway | Holds the leased model credential and forwards model requests for a station [BK09 "Model provider through the gateway"]. |
| AL | a2a link (message bridge) | Runs under the one shared messaging account, never under an agent account. Holds the carrier credential, checks messages before they become commands (J2) and accepts outgoing signed envelopes at its local submit endpoint [C24 dec 6; BK24 "What the bridge consists of"; RUL-1; RUL-3]. |
| SH | session host | Owns the logical session, the input queue and the input fence [BK07 "Service, runner and the single writer"]. |

### 1.3 The station state record

SR1. The state of a station is one value in one record, the station state
record. Its single owner and single writer is CRO. The record carries a
monotonically increasing state version, the records of section 4.1, the open
absence debts (U1), the open run (K5) and the capability flags (R24) [DEC D1].
NEW (DEC D1 marks this decision as new): no source names one owner of the
station state.

SR2. Every allowed cell of section 3 is one compare-and-set on the state
version, committed by CRO together with the record the cell names. Two
transitions attempted from one state version: exactly one commits, and the
other refuses `station_state_stale` and re-reads [DEC D1].

SR3. No other service commits a station state. A service performs an effect
for a station only under an operation that CRO recorded first, and reports the
outcome to CRO; the report is an event of section 2.2. Every effect request
carries the state version of its operation as its epoch. An effect owner that
has seen a higher epoch for the station refuses the request and reports the
refusal; the requester receives `station_state_stale` [DEC D1].

SR4. A start is atomic: CRO commits [stopped x start] by compare-and-set, and
the physical start request carries that state version as its epoch [DEC D1].

SR5. A read that only classifies (a journal read, an observation, a proof
check) is not an effect and needs no prior record. Between an outcome becoming
unknown and its record becoming durable, each effect owner's own rule holds
what it holds: a prepared or unknown home lease blocks [HL08], and an unknown
dispatcher record keeps its generation, account and quota [BK07 "Dispatcher
and the one-shot transaction"]. The station record adds no protection in that
window and removes none.

SR6. OPEN OQ18: whether the dispatcher's session record or this record is the
authoritative one for a standing station. Until decided, this record decides
the cells of section 3 and the dispatcher's session record decides authority
(the action profile's "session held" and its clearance).

## 2. Reading a cell

A cell has exactly one of three forms.

- `NEXT; CRO; Rnn; GATE` - the transition is allowed. `NEXT` is the one next
  state. `CRO` is the one service that commits it (SR2). `Rnn` (section 4.1)
  is the durable record written before the effect. `GATE` is the closed gate
  set of section 4.4, or `no gate` when the event is an observation or a
  recovery step that is recorded and never refused.
- `refused: code` - the pair is not allowed; nothing changes; CRO returns the
  closed code.
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
delivered once to every existing station record of the host.

### 2.1 States

One line each; the transitions are only in section 3. In prose, "a held row"
always means one of the ten rows whose name starts with `held:`; the bare word
is never used for a station state. The action profile's authority state of an
occupied slot is always written "session held" [ADD B].

| State | Meaning |
| --- | --- |
| `absent` | No station record, account, generation, home or binding exists for the name. |
| `provisioning` | A create is in flight under R01: an account and a `creating` generation may already exist. |
| `provisioned` | The account exists at an `active` generation and the home skeleton is installed and verified; the enroll inventory of R02 is not complete, so the station is not usable; nothing runs. |
| `enrolling` | An enroll is in flight under R02: some bindings may already be durable. |
| `stopped` | The enroll inventory is complete, nothing runs, no home lease is held, and absence is recorded by R09. |
| `starting` | A start is in flight under R03: the home lease is prepared, the physical start is requested or about to be, and no incarnation is bound. |
| `running` | Exactly one process incarnation is bound to the home lease (R04). At most one run is open (K5). |
| `stopping` | A stop is in force: the input fence and the start fence are closed and the absence proof is awaited. |
| `updating` | An approved profile update is in flight under R12. |
| `bumping` | A same-account generation bump is in flight under R14. |
| `retiring` | Forward-only removal is committed; nothing is admitted for the generation. |
| `retired` | No account or home exists for the name; the station record, the name record and the tombstones are retained. Reached by a retirement or by a create that did not happen. |
| `held:provision` | Unknown outcome of a create, or an open absence debt during a create. |
| `held:enroll` | Unknown or partial outcome of an enroll, or an open absence debt during an enroll. |
| `held:account` | Absence is unknown for an account that is not enrolled. |
| `held:start` | Unknown outcome of a start: a process may or may not exist. |
| `held:live` | The bound incarnation cannot be read. |
| `held:run` | Unknown outcome of a run: an instruction may or may not have been applied. |
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
- The held case is split into ten rows, so that every exit of every held case
  is a cell of the same table.
- `retiring` is a row: the generation journal makes `retiring` a commit point
  after which recovery only moves forward [GJ 4; UM 3; UM 5].
- A run has no row. It is a record of the station (R21, R22) with three
  columns and the row `held:run`; a row per run would repeat the `running`
  row [ADD C].

### 2.2 Events

Each event is reported to CRO by the one service named; CRO commits the cell.

| Event | Reported by | Meaning |
| --- | --- | --- |
| provision | the requester | Request to create the account, generation and home skeleton for a station name. |
| enroll | the requester | Request to complete the enroll inventory of a provisioned station: name latch, key bindings, message link, owner binding, slot entry. |
| start | the requester | Request to start a process incarnation; a restart is the same event (section 6). |
| proof: incarnation match | CU | CU presents proof P2 for the start of R03. A bind that CU refused is not this event: an unequal reading is "process appears" and an unreadable one is "liveness reading missed". |
| process appears | CU or UM | A kernel reading shows a task with the account in any uid field that the state does not explain. In `running` that is a task outside the resource group of the bound execution [BK05 "Load: a resource group per generation"]; in every other state it is any task not covered by a presented P2. |
| process exits | CRO, from the session manager | The session manager reports that the lead process started under R03 or bound by R04 exited. |
| liveness reading missed | CU | A scheduled reading of the bound tuple, or the reading of a bind attempt, is missing or unreadable. |
| liveness restored | CU | The first reading equal in all four fields to the tuple of R04 after a recorded missed reading. Equal readings with no missed reading before them stay in CU's reading log and are not events. |
| instruction received | AL | A message addressed to the station identity passed J2 at receipt (section 11). |
| run start | SH | The session host is about to open a run for the oldest queued instruction (K5). |
| run end | SH | The open run ended: the harness confirmed its end, or CRO ordered its end because its grant was revoked or expired or the session authority closed, or its delivery was refused. |
| stop requested | the requester, or CRO as the actor of U5 | An authorized stop of the station; section 7.1 lists every trigger. |
| stop confirmed | UM | UM presents the absence proof P1, alone or inside the never-started evidence P5. |
| starter crash | the restarted service | CRO, the dispatcher or the launcher died or restarted while it owned an operation or the execution of this station. A dispatcher restart is this column and never "capability report". |
| host reboot | CRO | The host restarted; the boot identifier changed. |
| capability report | KS, MG, AL, SH, CB, or DI for GC | A service the station depends on reports one capability of the station closed or open again, including at its own restart [ADD A.5]. The capabilities are: signing, carrier channel, model forwarding, input delivery, session authority. |
| session journal lost | DI | The dispatcher's session journal is lost, fenced or restored from a copy [ADD A.4]. |
| profile update approved | the requester | An approved release newer than the installed pin is to be installed [C24 dec 3]. |
| key rotation | the requester | Request to bind the station name to a new key. |
| generation bump | the requester | Request for the same-account generation bump [UM 6]. |
| retire | the requester | Request to remove the station. |
| unknown or stranded outcome | CRO, from a clock of section 4.5 or an owner's report | The effect in flight may or may not have happened (a lost reply, an expired bound, missing or contradictory evidence), or it ended in a terminal refusal after its forward-only commit point. |
| proof: effect completed | CRO, reading the effect owner | Proof P3 that the recorded effect completed. |
| proof: effect did not happen | CRO, reading the effect owner | Proof P4 that the recorded effect did not happen, was refused or was rolled back. |
| operator teardown order | the operator | Authenticated operator order to drive a held station down (U3). |

## 3. The lifecycle table

| State | provision | enroll | start | proof: incarnation match | process appears | process exits | liveness reading missed | liveness restored | instruction received | run start | run end | stop requested | stop confirmed | starter crash | host reboot | capability report | session journal lost | profile update approved | key rotation | generation bump | retire | unknown or stranded outcome | proof: effect completed | proof: effect did not happen | operator teardown order |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| absent | provisioning; CRO; R01; G1 | refused: station_absent | refused: station_absent | refused: station_proof_unexpected | cannot occur: no account uid is reserved for the name | cannot occur: no start was ever requested for the name | cannot occur: no incarnation is bound | cannot occur: no missed reading is recorded | refused: station_absent | refused: station_absent | refused: station_absent | refused: station_absent | refused: station_proof_unexpected | cannot occur: no operation or execution of this station is in flight | cannot occur: no station record exists to deliver the event to | cannot occur: no station record exists to deliver the event to | cannot occur: no station record exists to deliver the event to | refused: station_absent | refused: station_absent | refused: station_absent | refused: station_absent | cannot occur: no effect is in flight in this row | refused: station_proof_unexpected | refused: station_proof_unexpected | refused: station_not_held |
| provisioning | refused: station_busy | refused: station_busy | refused: station_busy | refused: station_proof_unexpected | held:provision; CRO; R06; no gate | cannot occur: no start was requested for this generation | cannot occur: no incarnation is bound | cannot occur: no missed reading is recorded | refused: station_not_enrolled | refused: station_not_running | refused: station_not_running | refused: station_not_running | refused: station_proof_unexpected | provisioning; CRO; R10; no gate | provisioning; CRO; R11; no gate | provisioning; CRO; R24; no gate | held:provision; CRO; R23; no gate | refused: station_busy | refused: station_not_enrolled | refused: station_busy | refused: station_busy | held:provision; CRO; R17; no gate | provisioned; CRO; R18; G13 | retired; CRO; R18; G13 | refused: station_not_held |
| provisioned | refused: station_exists | enrolling; CRO; R02; G2 | refused: station_not_enrolled | refused: station_proof_unexpected | held:account; CRO; R06; no gate | cannot occur: no start was requested for this generation | cannot occur: no incarnation is bound | cannot occur: no missed reading is recorded | refused: station_not_enrolled | refused: station_not_running | refused: station_not_running | refused: station_not_running | refused: station_proof_unexpected | cannot occur: no operation or execution of this station is in flight | provisioned; CRO; R11; no gate | provisioned; CRO; R24; no gate | held:account; CRO; R23; no gate | refused: station_not_enrolled | refused: station_not_enrolled | refused: station_not_enrolled | retiring; CRO; R15; G5 | cannot occur: no effect is in flight in this row | refused: station_proof_unexpected | refused: station_proof_unexpected | refused: station_not_held |
| enrolling | refused: station_exists | refused: station_busy | refused: station_not_enrolled | refused: station_proof_unexpected | held:enroll; CRO; R06; no gate | cannot occur: no start was requested for this generation | cannot occur: no incarnation is bound | cannot occur: no missed reading is recorded | refused: station_not_enrolled | refused: station_not_running | refused: station_not_running | refused: station_not_running | enrolling; CRO; R09; G11 | enrolling; CRO; R10; no gate | enrolling; CRO; R11; no gate | enrolling; CRO; R24; no gate | held:enroll; CRO; R23; no gate | refused: station_busy | refused: station_not_enrolled | refused: station_busy | refused: station_busy | held:enroll; CRO; R17; no gate | stopped; CRO; R18; G13 | provisioned; CRO; R18; G13 | refused: station_not_held |
| stopped | refused: station_exists | refused: station_already_enrolled | starting; CRO; R03; G3 | refused: station_proof_unexpected | held:stop; CRO; R06; no gate | stopped; CRO; R05; no gate | cannot occur: no incarnation is bound | cannot occur: no missed reading is recorded | stopped; CRO; R07; G9 | refused: station_not_running | refused: station_not_running | refused: station_not_running | refused: station_proof_unexpected | cannot occur: no operation or execution of this station is in flight | stopped; CRO; R11; no gate | stopped; CRO; R24; no gate | held:stop; CRO; R23; no gate | updating; CRO; R12; G6 | refused: station_rotation_unavailable | bumping; CRO; R14; G8 | retiring; CRO; R15; G5 | cannot occur: no effect is in flight in this row | refused: station_proof_unexpected | refused: station_proof_unexpected | refused: station_not_held |
| starting | refused: station_exists | refused: station_already_enrolled | refused: station_incarnation_exists | running; CRO; R04; G10 | held:start; CRO; R06; no gate | stopping; CRO; R05; no gate | starting; CRO; R06; no gate | cannot occur: no bound tuple exists to compare a reading with | starting; CRO; R07; G9 | refused: station_not_running | refused: station_not_running | stopping; CRO; R08; G4 | refused: station_proof_unexpected | starting; CRO; R10; no gate | stopping; CRO; R11; no gate | starting; CRO; R24; no gate | held:stop; CRO; R23; no gate | refused: station_busy | refused: station_rotation_unavailable | refused: station_busy | refused: station_busy | held:start; CRO; R17; no gate | refused: station_proof_unexpected | stopping; CRO; R18; G13 | refused: station_not_held |
| running | refused: station_exists | refused: station_already_enrolled | refused: station_incarnation_exists | refused: station_proof_unexpected | held:stop; CRO; R06; no gate | stopping; CRO; R05; no gate | held:live; CRO; R06; no gate | cannot occur: no missed reading is recorded | running; CRO; R07; G9 | running; CRO; R21; G15 | running; CRO; R22; G16 | stopping; CRO; R08; G4 | refused: station_proof_unexpected | running; CRO; R10; no gate | stopping; CRO; R11; no gate | running; CRO; R24; no gate | held:stop; CRO; R23; no gate | refused: station_busy | refused: station_rotation_unavailable | refused: station_busy | refused: station_busy | held:run; CRO; R17; G16 | refused: station_proof_unexpected | refused: station_proof_unexpected | refused: station_not_held |
| stopping | refused: station_exists | refused: station_already_enrolled | refused: station_incarnation_exists | refused: station_proof_unexpected | stopping; CRO; R06; no gate | stopping; CRO; R05; no gate | stopping; CRO; R06; no gate | stopping; CRO; R06; no gate | stopping; CRO; R07; G9 | refused: station_not_running | refused: station_not_running | refused: station_busy | stopped; CRO; R09; G11 | stopping; CRO; R10; no gate | stopping; CRO; R11; no gate | stopping; CRO; R24; no gate | held:stop; CRO; R23; no gate | refused: station_busy | refused: station_rotation_unavailable | refused: station_busy | refused: station_busy | held:stop; CRO; R17; no gate | refused: station_proof_unexpected | held:stop; CRO; R18; G13 | refused: station_not_held |
| updating | refused: station_exists | refused: station_already_enrolled | refused: station_busy | refused: station_proof_unexpected | held:update; CRO; R06; no gate | updating; CRO; R05; no gate | cannot occur: no incarnation is bound | cannot occur: no missed reading is recorded | updating; CRO; R07; G9 | refused: station_not_running | refused: station_not_running | refused: station_not_running | refused: station_proof_unexpected | updating; CRO; R10; no gate | updating; CRO; R11; no gate | updating; CRO; R24; no gate | held:update; CRO; R23; no gate | refused: station_busy | refused: station_rotation_unavailable | refused: station_busy | refused: station_busy | held:update; CRO; R17; no gate | stopped; CRO; R18; G13 | stopped; CRO; R18; G13 | refused: station_not_held |
| bumping | refused: station_exists | refused: station_already_enrolled | refused: station_busy | refused: station_proof_unexpected | held:bump; CRO; R06; no gate | bumping; CRO; R05; no gate | cannot occur: no incarnation is bound | cannot occur: no missed reading is recorded | refused: station_busy | refused: station_not_running | refused: station_not_running | refused: station_not_running | bumping; CRO; R09; G11 | bumping; CRO; R10; no gate | bumping; CRO; R11; no gate | bumping; CRO; R24; no gate | held:bump; CRO; R23; no gate | refused: station_busy | refused: station_rotation_unavailable | refused: station_busy | refused: station_busy | held:bump; CRO; R17; no gate | provisioned; CRO; R18; G13 | stopped; CRO; R18; G13 | refused: station_not_held |
| retiring | refused: station_retiring | refused: station_retiring | refused: station_retiring | refused: station_proof_unexpected | retiring; CRO; R06; no gate | retiring; CRO; R05; no gate | cannot occur: no incarnation is bound | cannot occur: no missed reading is recorded | refused: station_retiring | refused: station_retiring | refused: station_retiring | refused: station_retiring | retiring; CRO; R09; G11 | retiring; CRO; R10; no gate | retiring; CRO; R11; no gate | retiring; CRO; R24; no gate | held:retire; CRO; R23; no gate | refused: station_retiring | refused: station_retiring | refused: station_retiring | refused: station_retiring | held:retire; CRO; R17; no gate | retired; CRO; R16; G12 | retiring; CRO; R20; G13 | refused: station_not_held |
| retired | provisioning; CRO; R01; G1 | refused: station_retired | refused: station_retired | refused: station_proof_unexpected | cannot occur: no account uid is reserved for the name | retired; CRO; R05; no gate | cannot occur: no incarnation is bound | cannot occur: no missed reading is recorded | refused: station_retired | refused: station_retired | refused: station_retired | refused: station_retired | refused: station_proof_unexpected | cannot occur: no operation or execution of this station is in flight | retired; CRO; R11; no gate | retired; CRO; R24; no gate | retired; CRO; R23; no gate | refused: station_retired | refused: station_retired | refused: station_retired | refused: station_retired | cannot occur: no effect is in flight in this row | refused: station_proof_unexpected | refused: station_proof_unexpected | refused: station_not_held |
| held:provision | refused: station_held | refused: station_held | refused: station_held | refused: station_proof_unexpected | held:provision; CRO; R06; no gate | cannot occur: no start was requested for this generation | cannot occur: no incarnation is bound | cannot occur: no missed reading is recorded | refused: station_held | refused: station_held | refused: station_held | held:provision; CRO; R08; G4 | held:provision; CRO; R09; G11 | held:provision; CRO; R10; no gate | held:provision; CRO; R11; no gate | held:provision; CRO; R24; no gate | held:provision; CRO; R23; no gate | refused: station_held | refused: station_held | refused: station_held | refused: station_held | held:provision; CRO; R17; no gate | provisioned; CRO; R18; G13 | retired; CRO; R18; G13 | retiring; CRO; R19; G14 |
| held:enroll | refused: station_held | refused: station_held | refused: station_held | refused: station_proof_unexpected | held:enroll; CRO; R06; no gate | cannot occur: no start was requested for this generation | cannot occur: no incarnation is bound | cannot occur: no missed reading is recorded | refused: station_held | refused: station_held | refused: station_held | held:enroll; CRO; R08; G4 | held:enroll; CRO; R09; G11 | held:enroll; CRO; R10; no gate | held:enroll; CRO; R11; no gate | held:enroll; CRO; R24; no gate | held:enroll; CRO; R23; no gate | refused: station_held | refused: station_held | refused: station_held | refused: station_held | held:enroll; CRO; R17; no gate | stopped; CRO; R18; G13 | provisioned; CRO; R18; G13 | retiring; CRO; R19; G14 |
| held:account | refused: station_held | refused: station_held | refused: station_held | refused: station_proof_unexpected | held:account; CRO; R06; no gate | cannot occur: no start was requested for this generation | cannot occur: no incarnation is bound | cannot occur: no missed reading is recorded | refused: station_held | refused: station_held | refused: station_held | held:account; CRO; R08; G4 | provisioned; CRO; R09; G11 | held:account; CRO; R10; no gate | held:account; CRO; R11; no gate | held:account; CRO; R24; no gate | held:account; CRO; R23; no gate | refused: station_held | refused: station_held | refused: station_held | refused: station_held | held:account; CRO; R17; no gate | refused: station_proof_unexpected | refused: station_proof_unexpected | retiring; CRO; R19; G14 |
| held:start | refused: station_held | refused: station_held | refused: station_held | running; CRO; R04; G10 | held:start; CRO; R06; no gate | stopping; CRO; R05; no gate | held:start; CRO; R06; no gate | cannot occur: no bound tuple exists to compare a reading with | held:start; CRO; R07; G9 | refused: station_held | refused: station_held | stopping; CRO; R08; G4 | stopped; CRO; R09; G11 | held:start; CRO; R10; no gate | stopping; CRO; R11; no gate | held:start; CRO; R24; no gate | held:stop; CRO; R23; no gate | refused: station_held | refused: station_held | refused: station_held | refused: station_held | held:start; CRO; R17; no gate | held:start; CRO; R17; G13 | stopping; CRO; R18; G13 | stopping; CRO; R19; G14 |
| held:live | refused: station_held | refused: station_held | refused: station_held | refused: station_proof_unexpected | held:stop; CRO; R06; no gate | stopping; CRO; R05; no gate | held:live; CRO; R06; no gate | running; CRO; R06; no gate | held:live; CRO; R07; G9 | refused: station_held | held:live; CRO; R22; G16 | stopping; CRO; R08; G4 | stopped; CRO; R09; G11 | held:live; CRO; R10; no gate | stopping; CRO; R11; no gate | held:live; CRO; R24; no gate | held:stop; CRO; R23; no gate | refused: station_held | refused: station_held | refused: station_held | refused: station_held | held:stop; CRO; R17; G16 | refused: station_proof_unexpected | refused: station_proof_unexpected | stopping; CRO; R19; G14 |
| held:run | refused: station_held | refused: station_held | refused: station_held | refused: station_proof_unexpected | held:stop; CRO; R06; no gate | stopping; CRO; R05; no gate | held:stop; CRO; R06; no gate | cannot occur: no missed reading is recorded | held:run; CRO; R07; G9 | refused: station_held | refused: station_held | stopping; CRO; R08; G4 | stopped; CRO; R09; G11 | held:run; CRO; R10; no gate | stopping; CRO; R11; no gate | held:run; CRO; R24; no gate | held:stop; CRO; R23; no gate | refused: station_held | refused: station_held | refused: station_held | refused: station_held | held:run; CRO; R17; no gate | running; CRO; R18; G13 | running; CRO; R18; G13 | stopping; CRO; R19; G14 |
| held:stop | refused: station_held | refused: station_held | refused: station_held | refused: station_proof_unexpected | held:stop; CRO; R06; no gate | held:stop; CRO; R05; no gate | held:stop; CRO; R06; no gate | held:stop; CRO; R06; no gate | held:stop; CRO; R07; G9 | refused: station_held | refused: station_held | stopping; CRO; R08; G4 | stopped; CRO; R09; G11 | held:stop; CRO; R10; no gate | stopping; CRO; R11; no gate | held:stop; CRO; R24; no gate | held:stop; CRO; R23; no gate | refused: station_held | refused: station_held | refused: station_held | refused: station_held | held:stop; CRO; R17; no gate | refused: station_proof_unexpected | refused: station_proof_unexpected | stopping; CRO; R19; G14 |
| held:update | refused: station_held | refused: station_held | refused: station_held | refused: station_proof_unexpected | held:update; CRO; R06; no gate | held:update; CRO; R05; no gate | cannot occur: no incarnation is bound | cannot occur: no missed reading is recorded | held:update; CRO; R07; G9 | refused: station_held | refused: station_held | held:update; CRO; R08; G4 | held:update; CRO; R09; G11 | held:update; CRO; R10; no gate | held:update; CRO; R11; no gate | held:update; CRO; R24; no gate | held:update; CRO; R23; no gate | refused: station_held | refused: station_held | refused: station_held | refused: station_held | held:update; CRO; R17; no gate | stopped; CRO; R18; G13 | stopped; CRO; R18; G13 | retiring; CRO; R19; G14 |
| held:bump | refused: station_held | refused: station_held | refused: station_held | refused: station_proof_unexpected | held:bump; CRO; R06; no gate | held:bump; CRO; R05; no gate | cannot occur: no incarnation is bound | cannot occur: no missed reading is recorded | refused: station_held | refused: station_held | refused: station_held | held:bump; CRO; R08; G4 | held:bump; CRO; R09; G11 | held:bump; CRO; R10; no gate | held:bump; CRO; R11; no gate | held:bump; CRO; R24; no gate | held:bump; CRO; R23; no gate | refused: station_held | refused: station_held | refused: station_held | refused: station_held | held:bump; CRO; R17; no gate | provisioned; CRO; R18; G13 | stopped; CRO; R18; G13 | retiring; CRO; R19; G14 |
| held:retire | refused: station_held | refused: station_held | refused: station_held | refused: station_proof_unexpected | held:retire; CRO; R06; no gate | held:retire; CRO; R05; no gate | cannot occur: no incarnation is bound | cannot occur: no missed reading is recorded | refused: station_held | refused: station_held | refused: station_held | held:retire; CRO; R08; G4 | held:retire; CRO; R09; G11 | held:retire; CRO; R10; no gate | held:retire; CRO; R11; no gate | held:retire; CRO; R24; no gate | held:retire; CRO; R23; no gate | refused: station_held | refused: station_held | refused: station_held | refused: station_held | held:retire; CRO; R17; no gate | retired; CRO; R16; G12 | retiring; CRO; R18; G13 | retiring; CRO; R19; G14 |

Below, a cell is cited as [state x event]. "The running rows" means `running`,
`held:live` and `held:run`.

## 4. Vocabulary of the cells

### 4.1 Durable records

Every record is an entry of the station state record, written by CRO in the
same compare-and-set that commits the cell (SR2), before the effect that the
third column names. The fourth column lists the write-ahead records that the
effect owners MUST hold in their own stores before their own effects. This
file names the records and their order; their bytes belong to the owning
contracts. The record identifiers and their contents are NEW: no source
defines them.

| Id | Content | Precedes | Effect owners and their own write-ahead | Source |
| --- | --- | --- | --- | --- |
| R01 | Create operation: operation identity, station name, host, project, profile pin, the reference of the validated binding. | The request for an account. | DI: request and effect identity. UM: caller-scoped effect intent and the `creating` append before any account mutation; `active` only after identity, skeleton, persistence denial and static deny are verified. | C24 "Lifecycle and failure handling", create; UM 3; UM 4 |
| R02 | Enroll operation: the closed enroll inventory, one line per binding with its owner: name latch (CU), one key binding per purpose (KS), message link (AL), owner binding (CRO), slot entry (DI). | Every binding. | CU: latch record in manager state before the name file is published. KS: binding record for the exact (uid, generation). AL: registry entry before a station link is emitted [C32 "Recommendation"]. DI: slot table entry. | C24 "Lifecycle and failure handling", create; C24 "Ownership and records"; UM 6.2; BK24 "Owner channel" |
| R03 | Start operation: new operation, request, execution and lease-request identities, the state version as epoch, the binding reference, the release identity of the last R12; phase `lease_requested` before the first lease acquire [HL21]; phase `start_requested` before the physical-start request. NEW phase `start_requested`: without it a recovery cannot tell whether a request was sent. | The lease acquire and the physical start. | CU: prepared lease record, blocking before the acquire is acknowledged [HL06]. DI: request and effect identity with the consumed binding. LA: start receipt with the execution number, written as root before privileges are dropped; a second start of the same execution is rejected [BK05 "Transition from root to agent"]. | HL21; HL06; BK07 "Dispatcher and the one-shot transaction" |
| R04 | Bound holder: the digest of proof P2 and the exact `{pid, uid, boot_id, start_time}`. | The opening of the input fence. | CU: bound lease [HL07]. SH: the fence stays closed until R04 exists. | HL07; HL22; HL observer |
| R05 | Exit observation from the session manager, with the incarnation it concerns; closes an open run as `interrupted`. | The request for the absence proof. | DI and UM: journaled stop effect identity. | C24 "Lifecycle and failure handling"; BK05 "Load: a resource group per generation" |
| R06 | One observer reading: its class (unexplained process, missed, unreadable, restored), its producer and evidence digest, the origin state, the held case, and the effect identity or "none: observation". A reading of an unexplained process opens an absence debt (U1). A reading that leaves `running` closes an open run as `interrupted`. | Any reaction to the reading. | CU or UM: the reading itself, kept in its own store. | HL08; HL observer; DEC D4 |
| R07 | Instruction entry: AL's J2 verdict at receipt (signer, the grant the instruction cites, revocation snapshot, replay check) and the disposition `queued` or `data`. | The queue entry at the session host. Nothing is delivered by this record. | AL: admission record beside the body. SH: queue entry. | BK24 "Trust gate"; BK24 "Doorbell, mailbox and session input"; ADD C |
| R08 | Stop operation: reason (section 7.1), requester, the incarnation and lease it targets; closes an open run as `interrupted`. | The stop effect. The input fence and the start fence of the generation are closed first. | SH: fence closed. DI: journaled end of the session and stop effect (clock `end_to_absence` starts). UM: stop effect. | C24 "Lifecycle and failure handling", down; BK07 "Permission for a successor"; HP 4.7 |
| R09 | Absence acceptance: UM's proof P1 or P5 with its coverage, quiet interval, boot identifier and the fences held. It answers every absence debt older than it. | The release of the home lease [HL09; HL10] and of the execution claim; in retirement, the removal of the home. | UM: its own absence record. CU: release event and tombstone. DI: claim release and the clearance of the slot, which cites this proof [AP 7]. | UM 5; UM 6.1; HL09; BK07 "Dispatcher and the one-shot transaction" |
| R10 | Recovery entry: the operation found, its recorded phase, the classification taken. It releases nothing. Where the classification is unknown, the event "unknown or stranded outcome" follows and writes R17. | Any resumed step. | Each effect owner reconciles its own journal before new work [UM 3; BK07 "Dispatcher and the one-shot transaction"]. | C24 "Lifecycle and failure handling"; HL21; HL22 |
| R11 | Boot record: the boot identifier now read and the one in R04 or R03; closes an open run as `interrupted`. | The request for the absence proof. | none | HL05; BK07 "Wake-up and context transfer" |
| R12 | Update operation: approved release identity and the full control inventory with digests. On completion it is the amendment record of the plan pins (section 9.1). | The first replaced control; the trust pin is published last. | CU: composition intent. UM: skeleton install effect through trusted descriptors. | UM 7; C24 "Platform controls and approved updates"; HL14 |
| R13 | Reserved: rotation record of the key service. No cell of station/1 writes it: the key service authorizes no rotation today [OWN-KS]. | Nothing in station/1. | KS, in a later unit. | OWN-KS |
| R14 | Bump operation: the target generation, and the three conditions that UM holds before the successor is `active`: account-wide absence, the complete external-object inventory, and the two key-service confirmations. A completed bump ends in `provisioned`: the key bindings made under UM 6.2 are lines of the next enroll inventory that the enroll confirms and does not make again, and the lines that lived in the destroyed home (name file, station link) are made again. | The request to bump. | UM: effect intent and the `retiring` append for the old generation before stop or reset. KS owner: re-admission and new binding confirmations. | UM 6; UM 6.1; UM 6.2 |
| R15 | Retire operation: the export obligation and how it is discharged (a recorded export receipt or an operator waiver reference), the obligations check. | The request to retire. | UM: effect intent and the `retiring` append before stop or deletion. | UM 5; C24 "Lifecycle and failure handling", retire |
| R16 | Retired acceptance: UM's terminal result `removed` after verified cleanup and account absence. | The release of the account claim and of the slot entry. The station record and the name record are retained, with the last key identifier per purpose. | UM: the `removed` append. DI: claim and slot release. | UM 5; GJ 4; BK06 "The account ends, the identity remains" |
| R17 | Hold record: held case, origin state, the effect and its identity, what was sent, what was observed, and any carried owner code. An unknown run outcome marks the run `unknown`. | Every effect, release and resumed step after it. Nothing is released by it. | none | C24 "Lifecycle and failure handling", unknown; HL08 |
| R18 | Proof acceptance: which proof (section 4.2), its producer, its evidence digest, its kind and carried code, the effect or hold it answers. A P4 for a run closes the run `not_started`. | The state change. | CU: lease release event where the proof allows it [HL09]. | HL09; HL10 |
| R19 | Operator order: the authenticated, exact-content operator act for this station. | The teardown. | UM: operator retire act with its recorded waiver where used [UM 5]. | UM 2; UM 5; HL12; BK06 "The operator signs one action" |
| R20 | Forward step entry: a retirement step proved not done; the same effect identity runs it again. | The repeated step. | UM: its step log. | UM 3; UM 5 |
| R21 | Run open: run identity, the instruction of R07 it serves, the grant it cites, AL's J2 verdict at this moment. | The run binding at the key service and the delivery to the harness. | KS: run binding. SH: delivery intent. | ADD C; RUL-2; BK24 "Doorbell, mailbox and session input" |
| R22 | Run close: run identity and one outcome of `ended`, `ended_by_revocation`, `ended_by_expiry`, `ended_by_suspension`, `not_started`. | The release of the run binding and the next run start. | KS: binding release. SH: queue advance. | ADD C |
| R23 | Journal fence entry: the dispatcher's report that its session journal is lost, fenced or restored. It opens an absence debt for every state that has an account, and closes an open run as `interrupted`. Nothing is recorded as ended. | Every later step. | DI: its own fence mark. | ADD A.4; AP 10; BK07 "Dispatcher and the one-shot transaction" |
| R24 | Capability entry: the capability, `closed` or `open`, the reporter and its reason. | The gates that read the flag (G15). | The reporter's own closure record. | ADD A.5; BK09 "Model provider through the gateway"; BK06 "Message key and its attestation" |

### 4.2 Proofs

Only these proofs change a state. Each has one producer.

| Id | Name | What it is | Producer | Source |
| --- | --- | --- | --- | --- |
| P1 | absence proof | Zero tasks with the account in the real, effective, saved or filesystem uid field, for the whole configured quiet interval, from a complete root-readable enumeration of every task with stable process handles. Every thread is a task and counts. On Linux an empty resource group stands for this only where qualification showed it equal to account-wide absence. A partial, denied, unreadable or timed-out enumeration is not a proof. NEW condition: the proof is valid only while the input fence and the start fence of the generation stay closed; the reason is that a task could otherwise be created during the enumeration. The proof is per account, so one session per slot is assumed [AP 7]. It is the effect of the user manager's stop (enumerate, signal by stable handle with incarnation revalidation, prove by enumeration); nothing drops into the account to kill [OWN-UM]. | UM | UM 5 step 2; UM 6.1; HP 4.7; BK05 "Load: a resource group per generation" |
| P2 | incarnation match | A bind-time proof only. CU's own kernel reading of `pid`, `uid`, `boot_id` and `start_time`, taken in one pass, is byte-equal to the manager observation and to the requested holder, AND the proving manager's evidence that the process is the actual harness of this execution is present. Tuple equality alone does not bind. It is not a liveness reading (K4). | CU | HL observer; HL07 |
| P3 | recorded result | The recorded terminal result of the same effect identity, read from the effect owner's journal (observation state `recorded`). For an enroll and for an update it is P3 from every owner listed in the inventory of R02 or R12. For a run it is the harness confirmation marker found in the native transcript. | the effect owner, read by CRO | UM 3; HP 2; BK05 "Account, generation and journal"; BK07 "Queue and questions of the harness" |
| P4 | no-effect proof | One of three kinds, kept in R18. (a) An authoritative refusal of the effect by its owner under the recorded operation, with its closed code and no trace of the effect (for a start: no start receipt). (b) Observation state `rolled_back`, verified. (c) Observation state `not_recorded` with complete coverage. The states `unavailable` and `contradictory` are not this proof. For an enroll and for an update it is P4 from every owner of the inventory. For a bump it exists only while the old generation is still `active`. For a run it is the absence of the marker in a completely read native transcript. | the effect owner, read by CRO | HP 2; HL09; HL21; HL23; UM 3; UM 6.2; BK05 "Account, generation and journal" |
| P5 | never-started evidence | For an account that was never started: the generation is `active`, a complete read of the launcher's start receipts shows no launcher invocation recorded for the generation, and P1 is zero, all under a start fence closed since `active`. A trial start and a general kill by uid do not replace it. | UM | DEC D4; BK06 "Total stop"; HP 4.7 |

A changed boot identifier (R11) proves only that the bound incarnation ended.
It is not P1. NEW against the book, which says a changed boot identifier
confirms that the old processes are gone [BK07 "Wake-up and context
transfer"]: this contract still requires R09, because persistence under the
account is denied by qualification and not by the reboot.

### 4.3 Refusal codes

One closed set for the whole file. Every code has exactly one evaluating
service, which is the only service whose verdict produces it. Before a record
CRO returns the evaluator's code unchanged; after a record the code arrives in
P4 (section 2). The `station_*` and `message_*` names are NEW; codes of other
contracts are carried unchanged in the detail and never renamed [DEC D8].

| Code | Evaluator | Meaning | Carries |
| --- | --- | --- | --- |
| `station_absent` | CRO | No station record of this name exists. | none |
| `station_exists` | CRO | The name already has an account. | none |
| `station_retired` | CRO | The station is retired; only a new provision is admitted. | none |
| `station_retiring` | CRO | Removal is committed. | UM `generation_inactive` |
| `station_held` | CRO | The station is in a held row; only the cells of that row apply. | none |
| `station_not_held` | CRO | The teardown order applies only to a held row. | none |
| `station_not_enrolled` | CRO | The enroll inventory is not complete. | none |
| `station_already_enrolled` | CRO | The enroll inventory is complete. | none |
| `station_not_running` | CRO | No incarnation is bound. | none |
| `station_busy` | CRO | Another operation of the station is in flight. | UM `target_busy` |
| `station_incarnation_exists` | CRO | A start is in flight, bound or not yet proved gone. | none |
| `station_proof_unexpected` | CRO | No recorded effect or hold of this row awaits this proof. | none |
| `station_proof_mismatch` | CRO | The proof is not about the recorded effect identity, is not from its producer, or does not cover the whole inventory. | none |
| `station_operation_conflict` | CRO | Same operation identity, different arguments. | UM `request_id_conflict`; HL `request_conflict` |
| `station_state_stale` | CRO | The compare-and-set lost, or the request carries a stale epoch. | the effect owner's own stale-request detail |
| `station_absence_unproven` | CRO | An absence debt is open, or the presented proof is not P1, or the entry into `stopped` lacks R09. | UM `processes_remain`; HL `environment_lease_release_unconfirmed` |
| `station_bump_committed` | CRO | A no-effect proof was presented for a bump whose old generation is no longer `active`. | none |
| `station_rotation_unavailable` | CRO | No key rotation is authorized in station/1. | none |
| `station_run_open` | CRO | A run is open or its outcome is unknown. | none |
| `station_run_not_open` | CRO | No run is open. | none |
| `station_session_suspended` | CRO | The capability session authority is recorded closed. | none |
| `station_stop_not_authorized` | CRO | The requester may not stop this station. | none |
| `station_retire_not_authorized` | CRO | The requester may not retire this station. | none |
| `station_bump_not_authorized` | CRO | The requester may not bump this station. | none |
| `station_export_unresolved` | CRO | Neither a recorded export receipt nor an operator waiver exists. | none |
| `station_obligations_open` | CRO | Open obligations of the station block its removal. | none |
| `station_operator_act_invalid` | CRO | The operator act is not authenticated or not exact. | none |
| `station_owner_unbound` | CRO | The owner binding is not durable. | none |
| `station_credential_mode_refused` | CRO | The plan does not select the mode without secrets at the agent. | none |
| `station_link_unregistered` | CRO | The station link is not admitted. | C32 `native-environment-not-registered` |
| `session_home_lease_unavailable` | CRO | The home lease was not acquired; this is the existing code of HL21 and HL23, verbatim. | Curator's lease code and reason |
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
| `station_rotation_unrecorded` | KS | The key identifier of a purpose differs from the last one retained for the name. | none |
| `station_gateway_unready` | MG | The gateway path is not ready, or its readiness is unknown. | none |
| `message_signature_invalid` | AL | The signature over the exact bytes does not verify. | none |
| `message_grant_refused` | AL | The grant the instruction cites does not cover it, or is revoked or expired. | none |
| `message_revocation_unknown` | AL | The revocation state for that grant is unavailable. | none |
| `message_replayed` | AL | The message was already admitted. | none |
| `message_target_mismatch` | AL | The message is not addressed to this station identity. | none |
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
(section 2).

| Gate | Cells | Before the record, in order | After the record, in order |
| --- | --- | --- | --- |
| G1 | [absent, retired x provision] | `station_operation_conflict`, `station_state_stale`; then GC, J1: `station_grant_refused`, `station_revocation_unknown` | DI: `station_session_journal_fenced`, `station_binding_stale`, `station_account_shared`, `station_qualification_required`, `station_capacity_unavailable`. UM: `station_backend_unqualified`, `station_quota_exceeded`. |
| G2 | [provisioned x enroll] | `station_operation_conflict`, `station_state_stale`, `station_identity_mismatch`, `station_rotation_unrecorded` | KS: `station_key_unbound`. CRO: `station_link_unregistered`, `station_owner_unbound`. DI: `station_account_shared`. |
| G3 | [stopped x start] | the start gates 1 to 7 of section 6.2 | the start gates 8 to 18 of section 6.2 |
| G4 | every [state x stop requested] that is not a refusal | `station_state_stale`, `station_stop_not_authorized` | none: a stop effect is never refused after its record; its unknown outcome is the column "unknown or stranded outcome" |
| G5 | [provisioned, stopped x retire] | `station_state_stale`, `station_retire_not_authorized`, `station_export_unresolved`, `station_obligations_open` | UM: `station_cleanup_refused` |
| G6 | [stopped x profile update approved] | `station_state_stale`, `station_release_not_approved`, `station_home_leased`, `station_update_recovery_required` | none |
| G8 | [stopped x generation bump] | `station_state_stale`, `station_bump_not_authorized`, `station_export_unresolved`, `station_home_leased` | UM, while the old generation is still `active`: `station_backend_unqualified`. After the old generation is `retiring` nothing is a refusal: a terminal refusal is `station_bump_stranded` in the column "unknown or stranded outcome". |
| G9 | every [state x instruction received] that is not a refusal | AL, J2 at receipt: `message_target_mismatch`, `message_signature_invalid`, `message_replayed`, `message_revocation_unknown`, `message_grant_refused`; then CRO: `station_state_stale` | none |
| G10 | [starting, held:start x proof: incarnation match] | `station_state_stale`, `station_proof_mismatch`, `station_absence_unproven` | none |
| G11 | every [state x stop confirmed] that is not a refusal | `station_state_stale`, `station_absence_unproven` | none |
| G12 | [retiring, held:retire x proof: effect completed] | `station_state_stale`, `station_proof_mismatch`, `station_absence_unproven`, `station_cleanup_refused` | none |
| G13 | every other proof cell | `station_state_stale`, `station_proof_mismatch`, `station_bump_committed`, `station_absence_unproven` | none |
| G14 | every [held row x operator teardown order] | `station_state_stale`, `station_operator_act_invalid` | none |
| G15 | [running x run start] | `station_state_stale`, `station_run_open`, `station_session_suspended`, `station_gateway_unready`; then AL, J2 again: `message_revocation_unknown`, `message_grant_refused` | none: a refused run binding or a refused delivery is the event "run end" with outcome `not_started` |
| G16 | [running, held:live x run end]; [running, held:live x unknown or stranded outcome] | `station_state_stale`, `station_run_not_open` | none |

`station_absence_unproven` in G10, G12 and G13 guards only the cells whose
next state is `running`, `stopped`, `provisioned` or `retired`; a cell that
leads down (to `stopping`, `held:stop` or `retiring`) is never refused by it.
It is returned in three cases, in this order: an absence debt is open (U1);
the cell enters `stopped` from a
held row and no R09 was written after the hold record [DEC D4]; the cell
enters `stopped` from `enrolling` or `held:enroll` and no R09 carrying P5 for
this generation was written after R02 and after the latest R11 [DEC D4].
G7 is not used: no cell admits a key rotation.

### 4.5 Clocks

Every bound is in clock time and has one actor. When a bound expires, the
actor is CRO, and its one action is to commit the cell named. No value is
defined here; a value that no source gives is an open question, the bound and
the actor are not [ADD A.1; DEC D11].

| Clock | Runs from, to | On expiry CRO commits | Value | Source |
| --- | --- | --- | --- | --- |
| `effect_bound` | The record of an effect in flight (R01, R02, R12, R14, R15), to its proof. | [provisioning, enrolling, updating, bumping, retiring x unknown or stranded outcome] | The owner's configured bounds; no implicit default [UM 3]. | UM 3 |
| `start_detect` | Phase `start_requested` of R03, to P2 or P4. | [starting x unknown or stranded outcome] | The `detect` bound of the dispatcher policy [DF A]. | DF A; HL22 |
| `end_to_absence` | The dispatcher's journaled end of a session (written under R05, R08, R11 or R19), to R09. | [stopping x unknown or stranded outcome] | OPEN OQ21; until decided, the `stop` bound of the dispatcher policy [DF A]. | ADD A.1; AP 6 |
| `liveness_interval` | One reading of the bound tuple, to the next. | [running x liveness reading missed], reported by CU | OPEN OQ4. | DEC D11; HL observer |
| `silence_deadline` | The entry into `held:live`, to "liveness restored". | [held:live x stop requested], with CRO as requester and reason `liveness_silence` | OPEN OQ4. | DEC D11 |
| `run_bound` | R21, to R22. | [running x unknown or stranded outcome] | The validity of the grant the run cites; a shorter bound is OPEN OQ20. | ADD C |

NEW: the action at `silence_deadline` is a stop request. The reason is that
down is the one direction that is safe without the reading; nothing is
released by it, and P1 is still required in `stopping`.

## 5. Unknown outcomes

U1. Absence debt. Every reading of an unexplained process is recorded (R06),
whether or not a bind was attempted, and every journal fence entry (R23) for a
state that has an account is recorded. Each opens an absence debt in the
station record. A debt is answered only by an R09 written after it. While a
debt is open, every cell gated by G10, G12 or G13 that leads to `running`,
`stopped`, `provisioned` or `retired` refuses `station_absence_unproven`
[DEC D4]. In a quiet row the same reading moves the
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
`retired`) except by a proof of section 4.2 in a cell of that row. A held row
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
[stopping x stop confirmed], by [held:start, held:live, held:run, held:stop x
stop confirmed], or by a proof cell gated on R09 (section 4.4) [DEC D4].
Accepted cost, stated here and not hidden: a task that cannot be killed, on a
host that is not rebooted, keeps the account claim, the lease and the quota
for as long as it lives; the operator teardown order only returns such a
station to `stopping`.

U5. Who acts in a held row. The actor is never open; a deadline that no source
gives is.

| Held row | Entered by | Actor and first action | Leaves upward by |
| --- | --- | --- | --- |
| `held:provision` | unknown create; a reading or a lost journal during a create | CRO observes the create effect at UM; with an open debt it requests the stop [held:provision x stop requested] | P3 to `provisioned`; P4 to `retired`. A proved rollback admits no new provision by itself: that is a fresh operation [BK05 "Account, generation and journal"]. |
| `held:enroll` | unknown or partial enroll; a reading or a lost journal during an enroll | CRO observes every owner of the R02 inventory | P3 from every owner to `stopped`; P4 from every owner to `provisioned`. While one binding is durable and another is not, the row stays; resources of uncertain ownership are never deleted [C24 "Lifecycle and failure handling", create]. |
| `held:account` | a process or a lost journal at `provisioned` | CRO requests the stop [held:account x stop requested] | P1 to `provisioned`. |
| `held:start` | unknown start; an unexplained process during a start | CRO observes the start effect at DI and never sends a second start request [BK07 "Dispatcher and the one-shot transaction"] | P2 to `running`, only with no open debt; P1 to `stopped`. P4 leads down to `stopping`. A start receipt alone (P3) keeps the row: a started process is not a bound one. |
| `held:live` | a missed or unreadable reading of the bound tuple | CU reads again at `liveness_interval`; at `silence_deadline` CRO requests the stop | "liveness restored" to `running`; P1 to `stopped`. |
| `held:run` | unknown outcome of a run | SH keeps the input fence closed and looks for the marker in the native transcript [BK07 "Queue and questions of the harness"] | P3 to `running` with the run open; P4 to `running` with the run closed `not_started`. The instruction is not delivered again by any automatic step. |
| `held:stop` | a process outside the bound execution; a lost journal; an unknown stop; two unknowns at once | CRO requests the stop at once [held:stop x stop requested] | P1 to `stopped`. |
| `held:update` | unknown or partial update; a reading or a lost journal during an update | CRO observes CU and UM over the R12 inventory | P3 (every control at the new release, pin published) or P4 (every control at the old release) to `stopped`, each only with an R09 written after the hold. The next start verifies every digest again (section 6.2). |
| `held:bump` | unknown or stranded bump | CRO observes the bump effect at UM | P3 to `provisioned`; P4 to `stopped` only while the old generation is `active` (`station_bump_committed` otherwise). A stranded bump leaves only by the operator teardown order to `retiring`, which is the ordinary-retirement fallback of UM 6.1. No proof returns a generation that reached `retiring` or `removed` [UM 6.2; GJ 4; DEC D5]. |
| `held:retire` | unknown retirement step; a lost journal during retirement | CRO observes the retire effect at UM | P3 to `retired`. P4 leads to `retiring`, where the step runs again. |

## 6. Restart rule

### 6.1 What a restart is

A restart is the cell [stopped x start] taken again. It keeps the account, the
generation, the home, the station name and every key binding. It creates a new
process incarnation with new operation, request, execution and lease
identities [HL06; BK07 "Dispatcher and the one-shot transaction"; DF B.3]. It
is never a generation bump: a new conversation or a new incarnation MUST NOT
cause a bump [UM 6].

Every start, the first one included, begins from `stopped`, and `stopped` is
entered only with R09: P1 for a station that ran, P5 for one that never ran
(U4) [DEC D4; BK07 "Permission for a successor"; BK06 "Total stop"].

Who may request a start; the physical start has one path in every case, CRO to
the dispatcher to the launcher [HP 7 "R-START"; BK05 "Two narrow privileged
entries"]:

- the party responsible for the station, named by the grant (the raising
  orchestrator or the operator) [C24 dec 4];
- the operator, for a station of a permanent team, from the signed team
  description that the dispatcher reconciles, also after a reboot [BK05 "Homes
  and results"; BK07 "Dispatcher and the one-shot transaction"];
- the host after a crash or a reboot, only within a lifecycle permission that
  the owner granted for this station; without that permission a start is
  single and nobody may repeat it [BK07 "Permission for a successor"; BK07
  "Wake-up and context transfer"];
- nobody, when the station was stopped by a human, or when the lifecycle
  permission was withdrawn by owner cancellation, owner retirement, chain
  revocation, signed retirement of the station or a maintenance stop [BK07
  "Permission for a successor"].

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
| 1 | state version | The compare-and-set on the state version succeeds. | `station_state_stale` | CRO | DEC D1 |
| 2 | J1 | The grant chain covers this start for this principal, host, account and plan, and the revocation verdict for the exact chain is "not revoked". "Revoked" refuses `station_grant_refused`; "unavailable" refuses `station_revocation_unknown`. The verdict is the validated binding (section 11). | `station_grant_refused`, `station_revocation_unknown` | GC | RUL-2; DEC D9; BK13 "Revocation and unknown state" |
| 3 | identity latch | The name file equals, byte for byte, the latch record and the name the start carries (section 9.2). | `station_identity_mismatch` | CU | section 9.2 (PROPOSED) |
| 4 | key bindings | A binding for the exact (uid, generation) exists for each key purpose of section 10. This is a read; the key service decides again at every connection (KY3). | `station_key_unbound` | KS | BK06 "The kernel establishes the peer"; GJ 4; OWN-KS |
| 5 | message link | The station link is admitted. | `station_link_unregistered` | CRO | C32 "Recommendation"; OWN-CR |
| 6 | credential mode | The plan selects the mode without secrets at the agent. | `station_credential_mode_refused` | CRO | BK09 "Mode without secrets at the agent"; OWN-CR |
| 7 | gateway readiness | Gateway address, service lease, listener of this generation, qualified adapter. Unknown readiness refuses. | `station_gateway_unready` | MG | BK08 "Readiness before launch" |
| R03 | record line | Gates 1 to 7 are above this line. R03 is written here, by the compare-and-set of gate 1. Gates 8 to 18 are below it. | none | CRO | HL21; DEC D1 |
| 8 | home lease | The lease is acquired for the admitted digest; a terminal replay never admits. | `session_home_lease_unavailable` | CRO, on CU's lease result | HL06; HL21 |
| 9 | session journal | The dispatcher's session journal is intact, or the slot has a clearance. | `station_session_journal_fenced` | DI | ADD A.4; AP 10 |
| 10 | binding | The validated binding named in R03 exists, is unconsumed, is for this operation and is not older than the allowed age. | `station_binding_stale` | DI | RUL-2; ADD A.3 |
| 11 | lifecycle | A lifecycle permission covers this start; a human stop is not in force; the restart budget is not exhausted. | `station_lifecycle_not_permitted`, `station_restart_budget_exhausted` | DI | BK07 "Permission for a successor" |
| 12 | fixed fields | The fixed start fields of section 9.1 equal the values recorded at provision as last amended by a completed R12; R03 names that R12. | `station_plan_changed` | DI | BK07 "Permission for a successor"; DF A |
| 13 | qualification | The host qualification for the required guarantees is current. | `station_qualification_required` | DI | BK05 "Qualification revocation"; UM 1 |
| 14 | capacity | Capacity and policy admit the start; an unread pause state is a pause. | `station_capacity_unavailable` | DI | BK07 "Dispatcher and the one-shot transaction" |
| 15 | generation | The exact (uid, generation) is `active`, read under the generation lock. | `station_generation_inactive` | LA | GJ 1; GJ 6.1; HP 7 |
| 16 | quiet account | Zero tasks of the account and no unresolved prior execution or stop claim; a failed or partial scan keeps the start closed. | `station_account_not_quiet` | LA | HP 7 |
| 17 | profile digests | Under the generation lock: the trust pin equals trusted approved-release metadata; every platform control equals its approved digest; the admitted runtime mapping lists every discovery path the harness can load, in the home and in the work directories, and a loadable path that the station can write and that the mapping does not classify as data refuses. Missing, unreadable, extra effective or mismatching controls refuse before provider execution. The checked objects are bound to the admitted start. | `station_profile_digest_mismatch` | LA | C24 dec 2; UM 7; DEC D3; DEC D10 |
| 18 | home skeleton | Under the same lock: every path of section 8 has its owner, group, mode, type and link count; no stored ACL or file capability; no entry outside the closed list in a platform-owned directory. | `station_skeleton_invalid` | LA | UM 7; DEC D3 |

The launcher is the authoritative evaluator of gates 17 and 18: only the
process that opens the trusted handles under the generation lock can bind the
checked objects to the admitted start [DEC D3; UM 7]. This closes the earlier
open question on the evaluator (OQ9), pending the confirmation of the
user-manager owner, which is not recorded yet. CRO MAY run the same two checks
earlier and refuse with the same code; that is advice and never proof, and the
launcher repeats the checks [DEC D3; OWN-CR]. NEW, for DEC D8: CRO may run
that advice check only after gates 1 to 14 passed, in place of asking the
launcher; the reason is that an advice check run any earlier would return a
different code than an implementation without it for a start that fails two
gates. CRX evaluates no gate [DEC D2].

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
  Whether that state may be carried across runs is OPEN OQ20.
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
| K1 session identity | Four things are distinct. The station identity (name, account, generation, keys) is stable for the life of the station. A process incarnation is one bound kernel tuple; a restart consumes it and creates a new one. A run is one admitted instruction at work (K5). A harness session is conversation state in the home. One live incarnation per station: the state record admits one start per state version (SR2, SR4), and the launcher refuses an account that is not quiet. | [stopped x start]; [starting x proof: incarnation match]; [starting, running, stopping x start]; every held row x start | DF B.1; HL07; DEC D1; HP 7 |
| K2 lifetime | The horizon of a station is the validity of the session's grant: the grant that authorizes the start and the holding [AP 12]. It replaces the one-run runtime bound. A persistent station has no time bound per incarnation and is outside the quotas of temporary work [BK05 "Homes and results"; BK07 "Dispatcher and the one-shot transaction"]; what remains per incarnation is the clocks of section 4.5, the term of the message-key attestation (at most 86400 s, renewed by the key service ahead of expiry; a missed renewal closes the capability signing, not the station) [BK06 "Message key and its attestation"], and the model credential lease held by the gateway (K7). A task-lifetime station keeps the published bounds: account 24 hours by default and at most 7 days, one execution 4 hours by default and at most 12 [BK07 "Dispatcher and the one-shot transaction"]. Renewal: the dispatcher re-signs the leaf under the current chains and the broker replaces the binding of the same account and generation, old removed before new; the new scope is the intersection of the current chains with the originally admitted request; only a member of the existing chain may renew; a revoked right is never re-issued by maintenance [BK13 "Renewal without widening"]. How far ahead renewal happens is OPEN OQ2. Renewal of the dispatcher policy window, which the landed policy keeps finite [DF A], is OPEN OQ26. The action at expiry is OPEN OQ1; decided is that from expiry gate 2 refuses every start and the capability session authority closes. | [stopped x start] gate 2; [running x capability report]; [running x stop requested] if OQ1 is decided for a stop | DF A; DF B.2 |
| K3 restart rule | Section 6. The same account, generation and home are reused. A lost start is unknown: a held row, never a blind retry. | [stopped x start]; [starting x starter crash]; [starting x unknown or stranded outcome]; the `held:start` row | DF B.3; section 6 |
| K4 liveness | Two different things [DEC D11]. P2 is the bind-time proof and is produced once per incarnation. A liveness reading is CU's periodic kernel reading of the four fields, compared with the tuple of R04; "alive" means that reading is equal. A self-report, an a2a heartbeat, an answered message or a live bridge process is not liveness and is never merged into a termination verdict [BK24 "What the bridge consists of"]. A missed or unreadable reading is unknown, never a stop and never a release: the station enters `held:live`. CU reads again at `liveness_interval`; at `silence_deadline` CRO requests the stop (section 4.5). | [running x liveness reading missed]; [held:live x liveness restored]; [held:live x stop requested] | DF B.4; HL observer; HL08 |
| K5 follow-up work | Section 7.2 (PROPOSED). | [running x instruction received]; [running x run start]; [running x run end]; the `held:run` row | DF B.5; ADD C |
| K6 revocation while running | Section 7.1. | [running x capability report]; [running x run end]; [running x stop requested]; [stopped x start] gate 2 | DF B.6; RUL-2; DEC D9 |
| K7 credential and gateway lease | The station holds no model credential: the gateway holds the lease and the station holds a stub bound to one generation, one start and one account [BK09 "Model provider through the gateway"]. When the gateway's lease renewal fails, forwarding closes and the gateway reports the capability model forwarding closed; R24 records it, and [running x run start] refuses `station_gateway_unready` until the gateway reports it open again. The station is not stopped by that failure. NEW: the book states waiting for a needed provider login [BK07 "Wake-up and context transfer"]; the renewal case is applied by analogy. Whether a bounded wait escalates to a stop is OPEN OQ7. An account block after a leak match is different: it stops the session through [running x stop requested] [BK09 "Leak tripwire"]. | [running x capability report]; [running x run start] gate G15; [stopped x start] gate 7 | DF B.7 |
| K8 home and state | State that survives a restart lives only in the station-writable paths of section 8. Retirement duty: the work product is exported before the home is removed; a partial, unknown or failed export keeps the home, and only a recorded operator act waives the duty [BK07 "Dispatcher and the one-shot transaction"; UM 5]. Gate G5 admits a retire only with a recorded export receipt or that waiver. Who runs the export is OPEN OQ14; until it is decided no cell starts an export execution, so in this draft a retire is admitted only with the operator waiver, as in the first slice of the user manager [UM 5]. The account stays reserved and fenced until P1. Homes are never archived; keeping a retired home is a separate operator operation outside retirement [BK05 "Homes and results"]. | [provisioned, stopped x retire] gate G5; [retiring x stop confirmed]; [retiring x proof: effect completed] gate G12 | DF B.8 |
| K9 capacity | NEW: a station holds two claims; the sources name an account quota and an execution claim and do not join them for a station. The account claim lasts from R01 to R16 and is charged once across bumps [UM 6]. The execution claim lasts from R03 to R09 on every path, including a start that did not happen, and is never released from unknown [BK07 "Dispatcher and the one-shot transaction"]. A reclaim is a stop requested or a retire through this table; it is never a signal sent outside the table. Removal or re-creation of a persistent station needs the operator [BK05 "Homes and results"]; whether the dispatcher may request the stop of a persistent station without an operator act is OPEN OQ8. The cost of an unkillable task is in U4. | [running x stop requested]; [stopping x stop confirmed]; [retiring x proof: effect completed] | DF B.9; C24 "Host budget" |

### 7.1 Triggers of a stop, a suspension or a run end

Every trigger enters the table through the cell named. A suspension is the
capability session authority recorded closed (R24): no run starts, the open
run is ended, every use refuses at the gateway, and the process is not
stopped by the event. Revocation and expiry reach a running station through
the grant checker's feed to the dispatcher, which reports to CRO [RUL-2; DEC
D9]; that feed is a new seam and does not exist yet [DF C].

| Trigger | Observed by | Decided | Enters by | Open |
| --- | --- | --- | --- | --- |
| Owner stop of one station | CRO, from the party responsible or the operator | Stop; the station stays stopped until a human starts it [BK07 "Wake-up and context transfer"]. | [running x stop requested] | none; completion is bounded by `end_to_absence` |
| Total stop of the installation | Each service directly: UM freezes generations and closes ingress, SH stops sessions, DI ceases starts, MG closes uses [BK06 "Total stop"] | Stop of every station; resumption only by operator signature; a service restart does not lift it. | [running x stop requested] for each station | the delay, OQ5a |
| Qualification revoked | UM, the qualification reconciler [UM 1; BK05 "Qualification revocation"] | New starts close at detection; a running station is narrowed with confirmation or stopped within 300 seconds of detection, not reset by retries or restarts. | gate 13; [running x stop requested] | none |
| Account block after a leak match | MG and CB [BK09 "Leak tripwire"] | The session is stopped by the permitted path. | [running x stop requested] | the delay, OQ5b |
| A run's grant revoked or expired | GC, through its feed to DI | The run ends; the station does not [ADD C]. | [running x run end] with outcome `ended_by_revocation` or `ended_by_expiry` | the delay beyond max(S + A, F) with A at most 60 seconds [BK13 "Revocation and unknown state"], OQ5c |
| The session's grant revoked | GC, through its feed to DI | Suspension: every station of this contract is gateway-backed (K7), and on a gateway-backed host a revocation suspends [RUL-2; DEC D9]. Starts refuse at gate 2. The lifecycle permission is withdrawn [BK07 "Permission for a successor"]. | [running x capability report] | whether and when a suspended station is stopped, OQ5d |
| The session's grant expired | GC, by the verified-time watermark [BK13 "Renewal without widening"] | Suspension; starts refuse from expiry. | [running x capability report] | stop or keep, OQ1 |
| The seal of a cross-owner grant spent | The verifying service on its own chain node [BK14 "Revocation"] | The grant refuses from the observed spend; treated as revocation of the grant it seals. | as the two revocation rows | the bound on delivery of the spend, OQ5c |
| Device set changed | AL, by the device attestation of the carrier profile [BK24 "Assurance levels for human messages"] | A message from a device outside the pinned chain does not reach the level that can command; J2 refuses. No stop. | gate G9 and gate G15 | none |
| Policy removed | DI, by policy identity and revision [DF A] | Starts refuse at gate 11. | [stopped x start] | whether a running station is suspended, OQ5e |
| Revocation state unknown | GC | Starts refuse `station_revocation_unknown`; each use refuses, because "unavailable" is a refusal and a lost connection is not absence of revocation [BK13 "Revocation and unknown state"]. The capability session authority closes until the state is readable. | gate 2; [running x capability report] | whether a bounded unknown becomes a stop, OQ6 |
| Verified time lost | every service that checks time | Services hold at most 10 minutes by the monotonic clock and then stop everything that depends on time [BK13 "Renewal without widening"]. | [running x capability report], then as OQ6 decides | OQ6 |

### 7.2 Runs inside a station (K5, PROPOSED)

This subsection is PROPOSED. The owner decides it; until then it is not
normative, and no other reading is decided anywhere in this file [ADD C].

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
revoked or expired starts no run [ADD C; DEC D6; BK24 "Doorbell, mailbox and
session input"]. An instruction never causes a start: in a state without a
bound incarnation it is queued by R07 and nothing else happens [BK07 "Wake-up
and context transfer"].

RN4. A run has a start, an end and an unknown outcome. Its start is
[running x run start]: R21 is written before the key service binds the run and
before the session host delivers. Its end is [running x run end]: R22. Its
unknown outcome is [running x unknown or stranded outcome]: the station enters
`held:run`, the input fence closes, and only P3 or P4 over the native
transcript returns it to `running` [BK07 "Queue and questions of the
harness"]. NEW: at most one run is open at a time, because one dispatcher
writes into the input of a session [BK07 "Service, runner and the single
writer"].

RN5. Revocation or expiry of a run's grant ends that run and not the station;
the station's own lifetime follows the session's grant (K2, section 7.1) [ADD
C].

RN6. When the station leaves the running rows, the open run is closed as
`interrupted` by the record of that cell (R05, R06, R08, R11, R23). An
interrupted run and a run closed `not_started` are never delivered again by an
automatic step [BK07 "Queue and questions of the harness"].

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

## 8. Home skeleton

H is the station home. S is the dedicated group of the station, U its uid. The
list is closed: any other entry at H, or below a platform-owned directory,
fails gate 18. No path below H holds a model token, a carrier credential, a
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
| `H/.harness/state/` (harness state) | U:S | 0700 | the station | yes | Preserved; outside the cooperative write guard [HL17]. Never read as a control. Destroyed by a bump and by retirement. | UM 7; UM 6; ENV 8.1 |
| `H/work/` (work directories, the station's own repository clone) | U:S | 0700 | the station | yes | Preserved. Never read as a control: a loadable path below it that the mapping does not classify as data fails gate 17. Whether repository-native discovery from the clone is admitted at all is OPEN OQ23. Destroyed by a bump and by retirement. | UM 7; UM 6; DEC D10 |
| `H/tmp/` | U:S | 0700 | the station | yes | Preserved; not a place for state. Destroyed by a bump and by retirement. | UM 7; UM 6 |
| The a2a station link (`.a2a/` with `daemon.sock`, `identity`, `station`, `station.key`) and the hook-failure log `state/daemon-hook-failures.log` | OPEN OQ10, OQ11 | OPEN | OPEN | OPEN | OPEN | C32 "Recommendation"; C32 "Security considerations"; UM 7; UM 5 |
| The dispatcher caller key of an orchestrator station (first-run deviation, KY1) | U | 0600 | the installer | read only | OPEN OQ24: its path, and the unit that moves it to the key service. Not a platform control and not a station identity key. | DEC D7; BK06 "Which secrets exist" |

The a2a link row is OPEN because two sources contradict on its owner. C32
"Recommendation" requires that the managed home containing `.a2a` "must belong
to the launching effective UID"; UM 7 requires that the home root "is never
owned by U". C32 also places a station-readable secret file, `station.key`, in
the home, while UM 5 states "This station layout holds no private keys". The
row stays OPEN until OQ10 and OQ11 are decided. Decided already, and not part
of that question: the outgoing seam is the bridge's local submit endpoint, and
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
| Plan pins (worker plan, profile, harness, execution profile) | Fixed at every restart; the plan is reused byte for byte. | A pin changes only through [stopped x profile update approved]; the completed R12 is the amendment record that gate 12 compares against, and the next start is a new admission under J1 [C24 dec 3; BK07 "Permission for a successor"]. |
| The principal the grant names | Fixed. | Nobody: a station does not change hands by an edit [C24 "Ownership and records"]. |
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
- At every start the file, the record and the carried name are compared byte
  for byte (gate 3). A mismatch refuses `station_identity_mismatch` and
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
deviation, stated as it is: in the first-run cut the dispatcher caller key of
an orchestrator station is a file made by the installer, mode 0600, readable
by that caller account, so an injection into the orchestrator can use it; its
power is bounded by the orchestrator's grant [DEC D7; BK06 "Which secrets
exist"]. The deviation lasts until key-service custody of that key exists
(OQ24). The interim custody of CIP-0024 (one signing agent per station, key
file outside the station's access) meets the reach rule and is not the target
[C24 dec 1].

KY2. A station has three key purposes, each a separate key per station
identity: identity (purpose 1), request signing (purpose 7) and message
signing (purpose 9). A key of one purpose signs nothing of another purpose
[BK06 "Which secrets exist"; BK06 "Message key and its attestation"; OWN-KS].
The delegation key (purpose 8) is per parent, in a separate instance, and is
not a station key [OWN-KS].

KY3. The key service takes the caller from the kernel peer credential of the
connection, never from a field of the request, and admits it only when the
exact (uid, generation) is `active`; a retired or bumped generation loses its
bindings and its connections [BK06 "The kernel establishes the peer"; GJ 4;
UM 8]. Its refusals are its own closed codes: `generation_inactive`,
`generation_mismatch`, `peer_identity_unavailable`, `binding_not_found` and
`peer_binding_mismatch` [OWN-KS]. The kernel establishes the account; the
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
considerations"; BK06 "Message key and its attestation"]. Rights come only
through J1 and J2.

KY6. A station name is never bound to a new key. The key service authorizes
no rotation today: the key is stable per independent root, epoch and path
[OWN-KS]. Every [state x key rotation] refuses, and R13 is reserved for a
later unit. At enroll, the key identifier of each purpose MUST equal the last
one retained for the name (R16), where one is retained; otherwise gate G2
refuses `station_rotation_unrecorded`. Retiring an account does not revoke a
persistent identity, and a later enroll of the same name returns the same key
[BK06 "The account ends, the identity remains"; UM 5]. This closes the earlier
open question on rotation while running (OQ13): refuse, as the key service
owner answered.

## 11. Admission: J1, J2, the validated binding and the slot table

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

J2. Before a message becomes an instruction, the bridge checks the signature
and the grant the message cites [BK24 "Trust gate"; BK13 "Who checks the
right"]. The check is deterministic and asks no model. J2 is evaluated twice
for every instruction: at receipt (gate G9) and when its run starts (gate
G15) [DEC D6; ADD C; BK24 "Doorbell, mailbox and session input"]. Its output
is "instruction of action X on target Y under grant Z", "data", or a refusal
with a code of G9. A correctly signed message outside the actions of the
grant it cites is data and never an instruction; a relayed owner decision is
data [BK24 "Trust gate"; BK24 "Assurance levels for human messages"; C24
"Root context and authority"]. A message that CRO refuses by state stays in
the bridge's mailbox with its admission record; nothing is queued for it.

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

## 12. The one-task run

A one-task run is a station with one run, whose stop is followed at once by
its retirement. It uses the cells of section 3 and no other lifecycle. It
receives its own account, identity, keys, home and trust binding, with a
fresh context composed with the required root [C24 dec 7; C24 "Persistent
stations and task-lifetime spawn"]. NEW: it has no lifecycle permission, so
gate 11 refuses a second start; the sources say a start without that
permission is single [BK07 "Permission for a successor"]. Its bounds are those
of a task-lifetime station (K2). Retirement follows authoritative task
completion and durable handover, never provider exit or a delivered doorbell
[C24 "Persistent stations and task-lifetime spawn"]; which board transition
authorizes it is OPEN OQ16.

## 13. Who owns what

Exactly one owner per row. No service writes into another's state; it asks the
owner through the owner's interface and records its own request [C24
"Ownership and records"; UM 1; BK08 "One owner of the home"].

| Responsibility | Owner | Others may only | Source |
| --- | --- | --- | --- |
| Station state record: state, state version, records R01 to R24 | CRO | report events; perform effects under a recorded operation | DEC D1 |
| Station operations and their reconciliation | CRO | the session host and the party responsible request them | C24 dec 9; OWN-CR |
| Account and generation | UM | read the generation journal; the dispatcher requests create, bump and retire within its role, which is not in the landed dispatcher slice | C24 dec 9; UM 1; UM 2; GJ 1; OWN-DI |
| Home: paths, owners, modes, removal | UM | none write; the station writes inside its three writable paths | UM 1; UM 7 |
| Home: content, composition, digests, lease | CU | CRO requests and binds leases; nobody edits the lease store | C24 dec 9; HL01; UM 1 |
| Profile: approved release content and trust pin | CU | a station may request its own update and installs nothing unapproved | C24 dec 3; UM 7 |
| Session record, slot table, capacity claims | DI | read; the slot entry is requested by the enroll | RUL-2; ADD A.2 |
| Start and stop: physical authority, consumption of the validated binding | DI | CRO and the session host ask; no second privileged path exists | C24 "Ownership and records"; BK05 "Two narrow privileged entries"; RUL-2 |
| Grant check J1 and the revocation feed | GC | the dispatcher consumes the binding and the feed | RUL-2; DEC D9 |
| Start: privilege transition, start receipt, gates 15 to 18 | LA | the dispatcher invokes it | BK05 "Transition from root to agent"; HP 7; DEC D3 |
| Stop effect and absence proofs P1 and P5 | UM | all others consume R09; none substitutes its own | UM 5; UM 6.1; OWN-UM |
| Host qualification: issue and revocation | UM, the qualification reconciler | read | UM 1; BK05 "Qualification revocation" |
| Process observation: P2 and liveness readings | CU | CRO supplies the manager observation as input, never as proof | HL observer |
| Identity: latch record and name file (PROPOSED) | CU | read | section 9.2 |
| Identity: full typed identity (PROPOSED) | CRO | read | section 9.2; OWN-CR |
| Keys: custody, signing, bindings, run binding | KS | the station asks for a signature over a socket | C24 dec 1; C24 dec 9; RUL-2; OWN-KS |
| Message author: one account maps to one message-signing key | KS | a process under another account gets its own key or a refusal | section 10, KY4; RUL-1 |
| Dispatcher caller key of an orchestrator station (deviation) | the installer, until key-service custody | the caller account reads it | DEC D7 |
| Model credential: enrollment, lease issue, revocation | CB | the gateway holds a service lease | C24 dec 9; BK09 "Who holds the credentials" |
| Model credential: holding and use for a station's requests | MG | the station holds a stub only | BK09 "Model provider through the gateway" |
| Carrier credential and carrier account of a station identity | AL, under the shared messaging account | the station hands a signed envelope to the submit endpoint | RUL-3; BK24 "What the bridge consists of" |
| Messages: admission J2, mailbox | AL | the session host receives admitted items only | C24 dec 6; C32; BK24 "Trust gate" |
| Session: logical session, input queue, input fence, run delivery | SH | the bridge hands over admitted items; the station holds the harness channel under its account | BK07 "Service, runner and the single writer" |
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
| Two transitions from one state version | SR2: exactly one commits; the other refuses `station_state_stale` | one transition from one state version commits |
| Two processes of one station at once | [stopped x start] is the only start and is one compare-and-set; [starting, running, stopping x start] `station_incarnation_exists`; every held row x start `station_held`; gate 16 `station_account_not_quiet`; the launcher rejects a second start of one execution | a start from `stopped` binds one incarnation |
| `stopped` reached while a process may run | no cell enters `stopped` without R09 (U4); G13 `station_absence_unproven` | a quiet account reaches `stopped` by P1 |
| A process reading that is lost | [every row with an account x process appears] writes R06 | a bind with an equal reading writes R04 |
| A first start with no evidence that nothing ran | [enrolling x proof: effect completed] gate G13 without P5, `station_absence_unproven` | an enroll with P5 reaches `stopped` and starts |
| A start with a changed profile digest | gate 17, `station_profile_digest_mismatch` | approved unchanged controls admit the start |
| A station-written file loaded as a platform control | gate 17 and gate 18 | a file under `H/work/` classified as data does not block the start |
| A station reading another station's home | [absent x provision] creates the distinct group and modes; gate 18, `station_skeleton_invalid` | each station reads its own context and writes its own state |
| A station identity or message key readable by a station | [provisioned x enroll] binds keys only at the key service (R02); gate 18 | the station signs through its socket |
| A model token in a station account | gate 6, `station_credential_mode_refused` | a start in the mode without secrets reaches the model through the gateway |
| A carrier token in a station account | KY4; gate 18 for a file; the submit endpoint refuses `message_envelope_unsigned` | a signed envelope is published by the bridge |
| Release of an account while any thread runs under its uid | [stopping x stop confirmed] gate G11 and [retiring x proof: effect completed] gate G12, `station_absence_unproven` | a quiet account reaches `stopped` and `retired` |
| A generation that reached `retiring` or `removed` returned to use | [bumping, held:bump x proof: effect did not happen] gate G13, `station_bump_committed` | a bump refused before its commit returns to `stopped` |
| A retired name enrolled with a different key | [provisioned x enroll] gate G2, `station_rotation_unrecorded` | the same key enrolls |
| A process under station A signing with station B's key | key service: the request names no identity; `binding_not_found` or `signer_identity_mismatch` before any signature | station A signs as station A |
| Two stations sharing one account | [absent x provision] and [provisioned x enroll], `station_account_shared` | one station per account provisions and enrolls |
| A lost start retried blindly | [starting x starter crash] sends no second request; [starting x unknown or stranded outcome]; [held:start x start] `station_held` | a crash at phase `lease_requested` resumes the same acquire once |
| A missed liveness reading treated as a stop or a release | [running x liveness reading missed] goes to `held:live` and releases nothing | an equal reading keeps `running` |
| An instruction outside the grant it cites becoming a run | gate G9 and gate G15, `message_grant_refused` | an instruction inside its grant opens a run |
| A queued instruction whose grant was revoked opening a run | [running x run start] gate G15, J2 again | a queued instruction with a valid grant opens a run |
| An instruction causing a start | [stopped x instruction received] stays `stopped` and writes R07 only | a start request starts |
| A run delivered twice after an unknown outcome | `held:run`; RN6 | a run proved not applied is closed `not_started` and reported |
| A stop or reclaim outside the table | K9; [running x stop requested] is the only entry | an authorized stop request stops |
| Anything released from unknown | every held row: no cell releases without P1, P3 or P4 | a proved outcome leaves the held row |
| A session recorded as ended from a lost journal | [every row with an account x session journal lost] opens an absence debt and ends nothing | a station with an intact journal stops by P1 |
| A home archived at retirement | K8; [retiring x proof: effect completed] removes the home | the exported work product survives retirement |
| A profile update installed under a live or unknown lease | [starting, running, stopping x profile update approved] `station_busy`; gate G6 `station_home_leased` | an update installs in `stopped` |

## 15. Open questions

Each question has two options and the one who decides. None is decided here.
Closed since the previous draft: OQ9 (section 6.2, pending one confirmation),
OQ12 (section 9.2), OQ13 (KY6) and OQ17 (KY4).

| Id | Question | Option A | Option B | Decides |
| --- | --- | --- | --- | --- |
| OQ1 | A running station whose session grant expired (K2): after the suspension. | Stop it through [running x stop requested]. | Keep it suspended with no stop. | Owner, with the dispatcher owner. |
| OQ2 | How far ahead a grant is renewed (K2). | A fixed lead before expiry, set by policy. | A fraction of the grant's validity. | Grant contract owner; operator. |
| OQ3 | The restart budget (section 6.1). | A count and backoff carried in the lifecycle permission of each station. | One host policy default, with a per-station override. | Dispatcher owner and session host owner; operator. |
| OQ4 | The values of `liveness_interval` and `silence_deadline` (section 4.5). | One platform constant each. | A per-policy value inside a published bound. | Curator, with the curator-run owner. |
| OQ5a | Total stop: the maximum delay to the stop request. | The 300 seconds already used for qualification revocation. | A bound of its own, published by the operator path. | Owner. |
| OQ5b | Account block after a leak match: the maximum delay to the stop request. | The 300 seconds already used for qualification revocation. | A bound of its own, set by the broker and gateway contract. | Owner. |
| OQ5c | A run's grant revoked, expired or sealed: the maximum delay from the feed to the run end. | The propagation bound of the snapshot, with no further delay. | A named bound added to it. | Owner. |
| OQ5d | A station suspended by revocation of the session's grant. | Stop it after a bound. | Keep it suspended until an owner stop. | Owner. |
| OQ5e | Policy removed while a station runs. | Suspend the station. | Refuse starts only. | Owner. |
| OQ6 | A running station while the revocation state or the verified time is unknown: after the suspension. | Keep it suspended with no time limit. | Stop it after a bounded time, for example the 10 minute monotonic bound. | Owner. |
| OQ7 | A station whose model forwarding stays closed (K7). | Wait with no limit. | Stop after a policy bound. | Credential broker and gateway owner; operator. |
| OQ8 | A stop of a persistent station requested by the dispatcher to reclaim its execution claim (K9). | Operator only. | The dispatcher, inside a policy the operator signed. | Owner. |
| OQ10 | Where the a2a station link lives and who owns its parent (section 8). | In a station-owned directory inside H, keeping the C32 ownership rule. | In the root-owned sticky native directory, by amending the C32 ownership rule. | a2a owner and user-manager owner; the operator decides CIP-0032. |
| OQ11 | The station-readable `station.key` of the C32 link under one account per station. | Keep it as a link secret that is not a station key, since the account is already authenticated by the kernel peer. | Remove it and authenticate the link by the kernel peer only. | a2a owner; operator. |
| OQ14 | Who runs the export of the work product before removal (K8). | A fixed approved program under the station account, as its own fenced execution through the launcher, after confirmed absence and while the generation is `active`; this adds an export event to the table. | The user manager, from quarantine, after the stop. | User-manager owner and dispatcher owner. |
| OQ15 | Whose long-lived identity holds a workplace, the agent's or the place's [BK07 "Workbench"]. | The agent's identity occupies the place by lease. | The place owns the identity; the agent is replaceable. | Owners, as the book states. |
| OQ16 | Which board transition authorizes the automatic retirement of a one-task station [C24 "Open questions for the operator", item 2]. | The board's authoritative completed state with durable required outcomes. | A separate explicit release by the raising orchestrator. | Operator. |
| OQ18 | Which record is authoritative for a standing station (SR6). | The station state record of CRO. | The dispatcher's session record, with the station record as its projection. | curator-run owner and dispatcher owner. |
| OQ19 | Which unit defines the form of the validated binding (section 11). | The grant checker's contract. | The dispatcher's hook contract. | Grant checker owner and dispatcher owner. |
| OQ20 | Runs (section 7.2): whether the proposed run model is adopted, and whether conversation state may be carried across runs. | Adopt as proposed; each run starts from a fresh conversation. | Adopt as proposed; conversation state is carried, with a rule for what a later grant may read. | Owner. |
| OQ21 | The value of `end_to_absence` (section 4.5). | The `stop` bound of the dispatcher policy. | A bound of its own, published with the user manager's quiet interval. | Dispatcher owner and user-manager owner. |
| OQ22 | Entries a harness creates in `H/.harness/` beside `state/` (section 8). | None are admitted; the adapter redirects them into `state/`. | A closed list of entry classes per runtime mapping, each classified as data. | Curator and the user-manager owner. |
| OQ23 | Repository-native discovery from the station's clone (section 8). | Strict mode: nothing in the clone is loaded as a control. | Native-project mode, with every loadable path listed in the runtime mapping. | Curator; operator. |
| OQ24 | The dispatcher caller key of an orchestrator station (KY1). | Keep the installer-made file at a path the installer contract publishes, until custody moves. | Move request signing to the key service (purpose 7) before the first enforcing run. | Key service owner and dispatcher owner. |
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
| The dispatcher caller key in the orchestrator's home | `06-klyuchi.md`, line 9 "Which secrets exist" | same: the book names it an explicit exception, and KY1 keeps it as a named deviation |
| One account is one message author at the key holder; the bridge under the shared messaging account | `06-klyuchi.md`, line 51; `24-soobscheniya-i-most.md`, lines 187, 218 | same |
| The account ends, the identity remains | `06-klyuchi.md`, line 96 | same |
| No model credential at the station; stub and gateway | `09-uchetnye-dannye.md`, lines 101, 148 | refines: the book keeps a readable-token mode as an owner-selected exception; station/1 admits only the mode without secrets |
| Waiting on closed model forwarding (K7) | `07-zapusk-i-host-sessiy.md`, line 151; `09-uchetnye-dannye.md`, line 162 | refines: the book states waiting for a new provider login; the renewal case is applied by analogy |
| J1 behind the message origin | `13-doverennosti.md`, line 28 "Who checks the right" | refines: the book places the check at the dispatcher; the ruling places the checker behind the origin and has the dispatcher consume its binding |
| J2 at the bridge, at receipt and at delivery | `24-soobscheniya-i-most.md`, lines 109, 169 | same |
| Runs inside a station | none | new (PROPOSED) |
| Unknown delivery resolved from the native transcript | `07-zapusk-i-host-sessiy.md`, line 111 "Queue and questions of the harness" | same |
| Revocation propagation bound and "unavailable" as refusal | `13-doverennosti.md`, line 94 "Revocation and unknown state" | same |
| Renewal without widening; the 10 minute bound on lost verified time | `13-doverennosti.md`, line 124 | same |
| Qualification revocation within 300 seconds | `05-polzovatel-i-set.md`, line 283 | same |
| Cross-owner grant seal | `14-doverennosti-mezhdu-vladelcami.md`, line 40 "Revocation" | same |
| Unknown outcome is not absence; no blind repeat | `22-effekty-ostanovka-federaciya.md`, line 7; `05-polzovatel-i-set.md`, line 47 | same; the held rows are new |
| Lost dispatcher state: unknown records keep their claims; the node opens by operator decision | `07-zapusk-i-host-sessiy.md`, line 44 | same; the absence debt is new |
| Owner channel bound at raising | `24-soobscheniya-i-most.md`, line 89 "Owner channel" | same |
| Platform-owned controls checked before every start | `07-zapusk-i-host-sessiy.md`, line 38 "Immutable launch boundaries"; `08-curator.md`, line 31 | same |
| Total stop | `06-klyuchi.md`, line 122 | same |
| One owner of the station state with a compare-and-set | none | new |
| Name latch and synthetic name | none | new (PROPOSED) |
| The single lifecycle table, the held rows, records R01 to R24 | none | new |

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
| curator-agent-launcher | Station state record with the compare-and-set and epochs | new | 2 | none | two transitions from one state version: exactly one commits |
| curator-agent-launcher | Station operations with phases, including `start_requested` | extends the launcher lifecycle record named in C24 "Current state"; new | 3 | the unit above; curator lease store; the dispatcher's standing-runtime mode | a crash after `start_requested` yields `held:start` and no second start request |
| curator-agent-launcher | Start gate order and refusal mapping, with the early advice check | new | 1 (owner) | the launcher's gates 15 to 18 | a mismatching digest refuses before provider execution, with no provider child |
| curator-agent-launcher | Session-manager observation: process, termination and no-start on every command | contract and one consumer landed (owner); remainder new | 1 (owner) | none | an observation without a process tuple cannot bind |
| curator-agent-launcher | Station link admission | no existing element (owner): only a presence check of a credential file | 1 | OQ10, OQ11 | a legacy credential directory refuses before planning |
| curator-agent-launcher | Full typed identity latch (PROPOSED) | new | 2 (owner) | the latch record; the owner's admission | the same name with a changed kind or origin refuses before the latch seam is called and leaves the station record as found |
| swarma-user-manager | Account writer for create, retire and bump | contract exists: `spec/stations-v0.md`; journal format and offline tools exist; new | 4 | journal adapter alignment [UM 11] | a replayed create allocates no second identity |
| swarma-user-manager | Stop, P1 and the external-object inventory | contract exists: UM 6.1; new | 3 | qualified Linux backend | a double-forked survivor yields `processes_remain` and no release |
| swarma-user-manager | P5, the never-started evidence | new | 1 | the launcher's receipts | a generation with a start receipt gets no P5 |
| swarma-user-manager | Skeleton install with `H/.identity/` | contract exists: UM 7; new | 2 | section 8 | a station cannot replace a managed file through its sticky parent |
| swarma-user-manager | Launcher: start receipt and gates 15 to 18 | new | 2 | none | a second start of one execution is rejected |
| swarma-user-manager | Static deny rule and test-uid probe | not yet opened (owner) | not sized | none | not stated by the owner |
| swarma-user-manager | Service-account creation | not yet opened (owner) | not sized | none | not stated by the owner |
| swarma-user-manager | Per-account firewall rules | not yet opened (owner) | not sized | none | not stated by the owner |
| swarma-dispatcher | Daemon configuration unit | on the owner's board | 2 to 3 (owner) | none; precedes any standing-runtime work | not stated by the owner |
| swarma-dispatcher | Standing-runtime mode beside the one-launch budget | new [DF C] | 4 to 6 (owner) | the unit above; K1 to K4 | a second start of one station is refused |
| swarma-dispatcher | Consumption of the validated binding at every start | hooks exist for one run (owner); new for restarts | 1 (owner) | OQ19 | a stale binding admits no start |
| swarma-dispatcher | Revocation feed, consumer side | new [DF C] | 2 (owner) | the producer below; OQ5, OQ6 | an unknown revocation state never counts as "not revoked" |
| swarma-dispatcher | Claims for the life of a station and reclaim through a stop | new | 1 (owner) | OQ8 | a reclaim sends no signal outside a stop request |
| swarma-dispatcher | Slot table, journal-loss fence and clearance | new | 1 | none | a slot with a lost journal and no clearance admits no start |
| swarma-dispatcher | Run level: one execution, many runs | new | 1 | OQ20 | a second run start while a run is open refuses |
| grant checker behind the message origin | Revocation feed, producer side | new seam | 1 (ruling) | chain observation | a revoked session grant reaches the dispatcher as a closed capability |
| swarma-keymaker | Live bindings keyed by (uid, generation), purpose-9 selection, intent, result and recovery | partly exists (owner) | 3 to 4 (owner) | generation journal reader | a payload carrying another author is refused `signer_identity_mismatch` before any signature, beside station A signing as station A |
| swarma-keymaker | Run binding | new | 1 | the unit above; OQ20 | a run with no R21 gets no binding |
| swarma-keymaker | Rotation record R13 | later unit, not in station/1 (owner) | 1 (owner) | the first unit | a name with a different key and no R13 does not enroll |
| swarma-keymaker | Provisioning before `active` for a bump | open in UM 6.2; new | 2 | joint contract with the user manager | a binding before re-admission refuses |
| swarma-credential-broker and gateway | Service leases and a listener per generation | contract extension unpublished per the book; new | 4 | broker contract extension | a credential sent by the station is rejected; no token reaches the station environment |
| swarma-credential-broker and gateway | Renewal failure closes forwarding and reports the capability | new | 1 | OQ7 | a failed renewal forwards nothing and stops nothing |
| swarma-credential-broker and gateway | Gateway install unit | named by the owner of the user manager | not sized | the service-account unit | not stated by the owner |
| a2a-swarm | J2 at the bridge, at receipt and at run start | new | 3 | grant contract | a correctly signed message outside the grant it cites is data, never an instruction |
| a2a-swarm | Bridge submit endpoint | new; on the first-step path | 1 (ruling) | none | an unsigned body is refused `message_envelope_unsigned` |
| a2a-swarm | Station link under one account per station | enrollment exists per C32; new | 1 | OQ10, OQ11 | a link with a foreign owner is not admitted |
| swarma-session-host | Input fence tied to R04; capability flags | new | 2 | curator lease store | input before a bound lease is not delivered |
| swarma-session-host | Restart inside a lifecycle permission and budget | new | 2 | OQ3 | a restart without permission is refused |
| swarma-session-host | Run delivery: open, end, unknown, transcript marker | new | 2 | OQ20 | a run with an unknown outcome is not delivered again |
| task-board | Station element equal to the router snapshot | named in C24 "Implementation plan", leaf 2; new | 2 | shared record version | an assignment to a station in a held row is refused |

Total of the sized units: 71 to 75 LU. Four units are not sized by their
owners and are outside that total.

## 18. Sources not carried

CIP-0024 sections "Wave 1 project mode" (beyond OQ23), "Host budget" (beyond
K9), "Compatibility and migration" and question 1 of its open questions
concern project-source discovery, heavy-run scheduling and the migration of
existing work places; they are not station lifecycle and are not restated. The
station record fields of the registry (the router snapshot list) stay with
their owners [C24 "Ownership and records"]. Network profiles, resource limits
and the guarantee matrix [BK05] bound a running station and add no state or
event. The restore of the generation journal [UM 8] closes every consumer at
once and reaches a station only as `station_generation_inactive`. The process
fate table of the launcher [HP 7 "R-FATE"] is carried only as the column
"starter crash" and the column "capability report". The macOS station backend
[UM 1] is outside the first deployment, a Linux host.
