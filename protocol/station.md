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
defines vocabulary used by the cells (records, proofs, refusal codes, gates) or
states a rule that names the cells that carry it. No section describes a
second sequence of states. Where a section and the table disagree, the table
wins and the section is a defect.

This file defines no grant format, no wire schema and no file bytes. It states
where existing contracts attach.

### 1.1 Source keys

Every rule cites one of these keys or is marked NEW with a one-line reason.

| Key | Source |
| --- | --- |
| C24 "clause" | [CIP-0024](../cips/CIP-0024-agent-stations.md) on base `264244b321c7a2272450fc29bd9952f988d746d7`, by section title; "dec N" is item N of "Owner decisions". |
| C32 "clause" | [CIP-0032](../cips/CIP-0032-native-a2a-station-link.md), by section title. |
| HLnn | [Managed-home leases](home-leases.md), requirement HLnn; "HL observer" is its section "Independent observer before bind". |
| ENV n | [Environments protocol](environments.md), section n. |
| UM n | relux-works/swarma-user-manager `spec/stations-v0.md`, section n, at commit `04fe2b767ebbce15a4d2e7fa3b11738c41856609`. |
| GJ n | relux-works/swarma-user-manager `spec/generation-journal.md`, section n, same commit. |
| BKnn "title" | relux-works/swarma-docs `book/ru`, chapter file number nn, at commit `942a07f12e478841c483a624e94dc47100bb7571`. Section titles are English renderings of the Russian headings; section 16 lists the files and heading lines. |
| DF A, DF B.n, DF C | The dispatcher field inventory supplied as an input to this contract (digest prefix `ef4ab4eae619`), which reports swarma-dispatcher main `85a47091` (`spec/m0-launch.md` section 2, `spec/m0-executor-entry.md`). The dispatcher repository itself was not read. |
| NEW | Not in any source; the reason follows the mark. |

### 1.2 Services

The table names exactly these services. "launcher" alone always means the
privileged user launcher; CIP-0024 and HL05 use the word "launcher" for
curator-run, and this file does not.

| Abbr | Service | Role in one line |
| --- | --- | --- |
| UM | user-manager | Creates, bumps and removes accounts; proves absence [UM 1; BK05 "Two narrow privileged entries"]. |
| LA | launcher | Starts one approved program under an active account and writes the start receipt [BK05 "Transition from root to agent"]. |
| DI | dispatcher | Checks the grant chain, capacity and policy before a physical start; owns the execution record [BK07 "Dispatcher and the one-shot transaction"; C24 "Ownership and records"]. |
| CR | curator-run | Owns the station operations (create, up, down, retire) and their reconciliation [C24 dec 9]. |
| CU | Curator | Owns home content, composition, digests, the home lease and its independent process observer [C24 dec 9; HL01; HL observer]. |
| KS | key service | Holds every station key and signs on request [C24 dec 1; BK06 "The kernel establishes the peer"]. |
| CB | credential broker | Holds enrolled credentials and issues bounded leases [C24 "Ownership and records"; BK09 "Mode without secrets at the agent"]. |
| MG | model gateway | Holds the leased model credential and forwards model requests for a station [BK09 "Model provider through the gateway"]. |
| AL | a2a link | Carries messages for one station identity and checks them before they become commands [C24 dec 6; C32; BK24 "Trust gate"]. |
| SH | session host | Owns the logical session, the input queue and the input fence [BK07 "Service, runner and the single writer"]. |

## 2. Reading a cell

A cell has exactly one of four forms.

- `NEXT; SVC; Rnn; GATE` - the transition is allowed. `NEXT` is the next
  state. `SVC` is the single service that commits the transition: it is the
  only writer of the state change and of record `Rnn`. `Rnn` (section 4.1) is
  the durable record written BEFORE the effect. `GATE` is the closed set of
  refusal codes (section 4.3) returned when a precondition of this cell fails;
  a refused transition leaves the state unchanged. `no gate` means the event
  is an observation or a recovery step: it is recorded and never refused.
- `refused: code` - the pair is not allowed; nothing changes and the closed
  code is returned.
- `cannot occur: reason` - the event cannot be produced in this state.
- `OPEN OQn; until decided refused: code` - the sources leave the cell open;
  section 15 holds the question. NEW: an undecided cell refuses, because an
  empty cell would admit by omission.

Effects inside a transition are executed by their owners, each under its own
write-ahead record; section 4.1 lists them per record. A replay of an operation
with the same operation identity and the same arguments is not a new event: it
returns the recorded outcome and the current state, and a replay with different
arguments refuses `station_operation_conflict` [UM 3; HL06; C24 "Lifecycle and
failure handling", create]. Where a cell names two next states, the choice is
fixed by a durable record named in the cell, never by a guess.

### 2.1 States

One line each; the transitions are only in section 3.

| State | Meaning |
| --- | --- |
| `absent` | No account, generation, home or binding exists for the station name, and no retained name record. |
| `provisioned` | The account exists at an `active` generation and the home skeleton is installed and verified; no identity or key is bound; nothing runs. |
| `stopped` | Identity and keys are bound, nothing runs, no home lease is held, and absence is established by the absence record or by no-start evidence. |
| `starting` | A start is admitted: the home lease is prepared and the start effect is requested or about to be; no incarnation is bound. |
| `running` | Exactly one process incarnation is bound to the home lease; productive input is allowed. |
| `stopping` | A stop is in force: no new work, the start fence is closed, the absence proof is awaited. |
| `retiring` | Forward-only removal is committed; nothing is admitted for the generation. |
| `retired` | Account and home are removed; the name and its tombstones are retained. |
| `held:provision` | Unknown outcome of a provision. |
| `held:enroll` | Unknown outcome of an enroll. |
| `held:start` | Unknown outcome of a start: a process may or may not exist. |
| `held:live` | The bound incarnation cannot be read, or a second process tree was seen under the account. |
| `held:stop` | Absence is unknown: a stop effect has an unknown outcome, or a process was seen where none may run. |
| `held:control` | Unknown outcome of a profile update or a key rotation. |
| `held:bump` | Unknown or terminally refused outcome of a generation bump. |
| `held:retire` | Unknown outcome of a retirement step. |

Reasons for the differences from the minimum state list of the task:

- `enrolled` and `stopped` are merged into `stopped`. CIP-0024 defines the end
  of create as a "usable, stopped station" [C24 "Lifecycle and failure
  handling", create], and a never-started account is proved quiet by no-start
  evidence exactly as a stopped one is by the absence record [BK06 "Total
  stop"]. Every cell of the two rows would be identical.
- `held` is split by case, so that each held case has its own exits in the
  same table instead of in a second table.
- `retiring` is added: the generation journal makes `retiring` a commit point
  after which recovery only moves forward [GJ 4; UM 3; UM 5].

### 2.2 Events

| Event | Meaning |
| --- | --- |
| provision | Request to create the account, generation and home skeleton for a station name. |
| enroll | Request to bind identity, keys, message link and owner to a provisioned station. |
| start | Request to start a process incarnation; a restart is the same event (section 6). |
| process appears | The Curator observer reads a process under the account from the kernel [HL observer]. |
| process exits | The session manager reports that the started or bound lead process exited. |
| liveness reading missed | A scheduled observer reading of the bound incarnation is missing or unreadable. |
| instruction received | A message addressed to the station identity arrives at the a2a link. |
| stop requested | An authorized stop of the station; section 7 lists every trigger. |
| stop confirmed | The user-manager presents the absence proof P1 (section 4.2). |
| starter crash | curator-run, the dispatcher or the launcher dies while it owns an operation. |
| host reboot | The host restarts; the boot identifier changes. |
| profile update approved | An approved release newer than the installed pin is to be installed [C24 dec 3]. |
| key rotation | Request to replace a key bound to the station name by a new key. |
| generation bump | Request for the same-account generation bump [UM 6]. |
| retire | Request to remove the station. |
| unknown outcome | An effect requested from this state may or may not have happened: a lost reply, an expired bound, missing or contradictory evidence. |
| proof: effect completed | Proof P3 that the recorded effect completed. |
| proof: effect did not happen | Proof P4 that the recorded effect did not happen or was rolled back. |
| operator teardown order | Authenticated operator order to drive a held station down (section 5). |

## 3. The lifecycle table

| State | provision | enroll | start | process appears | process exits | liveness reading missed | instruction received | stop requested | stop confirmed | starter crash | host reboot | profile update approved | key rotation | generation bump | retire | unknown outcome | proof: effect completed | proof: effect did not happen | operator teardown order |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| absent | provisioned; CR; R01; G1 | refused: station_absent | refused: station_absent | cannot occur: no account or uid exists for the station | cannot occur: no incarnation exists | cannot occur: no incarnation exists | refused: station_absent | refused: station_absent | refused: station_absent | absent; CR; R10; no gate | absent; CR; R10; no gate | refused: station_absent | refused: station_absent | refused: station_absent | refused: station_absent | held:provision; CR; R17; no gate | refused: station_proof_unexpected | refused: station_proof_unexpected | refused: station_not_held |
| provisioned | refused: station_exists | stopped; CR; R02; G2 | refused: station_not_enrolled | held:stop; CU; R06; no gate | cannot occur: no incarnation was started | cannot occur: no incarnation is bound | refused: station_not_enrolled | refused: station_not_running | refused: station_proof_unexpected | provisioned; CR; R10; no gate | provisioned; CR; R10; no gate | provisioned; CU; R12; G6 | refused: station_not_enrolled | refused: station_not_enrolled | retiring; CR; R15; G5 | held:enroll when the effect is an enroll, held:control when it is an update; CR; R17; no gate | refused: station_proof_unexpected | refused: station_proof_unexpected | refused: station_not_held |
| stopped | refused: station_exists | refused: station_already_enrolled | starting; CR; R03; G3 | held:stop; CU; R06; no gate | cannot occur: no incarnation is started or bound | cannot occur: no incarnation is bound | stopped; AL; R07; G9 | refused: station_not_running | refused: station_proof_unexpected | stopped; CR; R10; no gate | stopped; CR; R10; no gate | stopped; CU; R12; G6 | stopped; KS; R13; G7 | provisioned; UM; R14; G8 | retiring; CR; R15; G5 | held:control when the effect is an update or a rotation, held:bump when it is a bump; CR; R17; no gate | refused: station_proof_unexpected | refused: station_proof_unexpected | refused: station_not_held |
| starting | refused: station_exists | refused: station_already_enrolled | refused: station_incarnation_exists | running; CU; R04; G10 | stopping; CR; R05; no gate | cannot occur: readings are scheduled only for a bound incarnation | starting; AL; R07; G9 | stopping; CR; R08; G4 | refused: station_proof_unexpected | starting when R03 is at phase lease_requested, else held:start; CR; R10; no gate | stopping; CR; R11; no gate | refused: station_busy | refused: station_busy | refused: station_busy | refused: station_busy | held:start; CR; R17; no gate | refused: station_proof_unexpected | stopped; CR; R18; G13 | refused: station_not_held |
| running | refused: station_exists | refused: station_already_enrolled | refused: station_incarnation_exists | running when the reading equals the tuple of R04, else held:live; CU; R06; no gate | stopping; CR; R05; no gate | held:live; CU; R06; no gate | running; AL; R07; G9 | stopping; CR; R08; G4 | refused: station_proof_unexpected | running; CR; R10; no gate | stopping; CR; R11; no gate | refused: station_busy | OPEN OQ13; until decided refused: station_busy | refused: station_busy | refused: station_busy | cannot occur: no lifecycle effect is in flight while running; a failed reading is the liveness column | refused: station_proof_unexpected | refused: station_proof_unexpected | refused: station_not_held |
| stopping | refused: station_exists | refused: station_already_enrolled | refused: station_incarnation_exists | stopping; CU; R06; no gate | stopping; CR; R05; no gate | stopping; CU; R06; no gate | stopping; AL; R07; G9 | stopping; CR; R08; G4 | stopped; UM; R09; G11 | stopping; CR; R10; no gate | stopping; CR; R11; no gate | refused: station_busy | refused: station_busy | refused: station_busy | refused: station_busy | held:stop; CR; R17; no gate | refused: station_proof_unexpected | refused: station_proof_unexpected | refused: station_not_held |
| retiring | refused: station_retiring | refused: station_retiring | refused: station_retiring | retiring; UM; R20; no gate | retiring; UM; R20; no gate | cannot occur: no incarnation is bound after the retiring commit | refused: station_retiring | refused: station_retiring | retiring; UM; R09; G11 | retiring; CR; R10; no gate | retiring; CR; R10; no gate | refused: station_retiring | refused: station_retiring | refused: station_retiring | refused: station_retiring | held:retire; CR; R17; no gate | retired; UM; R16; G12 | cannot occur: no proof undoes a step after the retiring commit | refused: station_not_held |
| retired | provisioned; CR; R01; G1 | refused: station_retired | refused: station_retired | cannot occur: the account is removed | cannot occur: no incarnation exists | cannot occur: no incarnation exists | refused: station_retired | refused: station_retired | refused: station_retired | retired; CR; R10; no gate | retired; CR; R10; no gate | refused: station_retired | refused: station_retired | refused: station_retired | refused: station_retired | held:provision; CR; R17; no gate | refused: station_proof_unexpected | refused: station_proof_unexpected | refused: station_not_held |
| held:provision | refused: station_held | refused: station_held | refused: station_held | held:provision; CU; R06; no gate | cannot occur: no incarnation was started | cannot occur: no incarnation is bound | refused: station_held | refused: station_held | held:provision; UM; R09; G11 | held:provision; CR; R10; no gate | held:provision; CR; R10; no gate | refused: station_held | refused: station_held | refused: station_held | refused: station_held | held:provision; CR; R17; no gate | provisioned; CR; R18; G13 | absent or retired, the origin recorded in R17; CR; R18; G13 | retiring; CR; R19; G14 |
| held:enroll | refused: station_held | refused: station_held | refused: station_held | held:enroll; CU; R06; no gate | cannot occur: no incarnation was started | cannot occur: no incarnation is bound | refused: station_held | refused: station_held | held:enroll; UM; R09; G11 | held:enroll; CR; R10; no gate | held:enroll; CR; R10; no gate | refused: station_held | refused: station_held | refused: station_held | refused: station_held | held:enroll; CR; R17; no gate | stopped; CR; R18; G13 | provisioned; CR; R18; G13 | retiring; CR; R19; G14 |
| held:start | refused: station_held | refused: station_held | refused: station_held | running; CU; R04; G10 | stopping; CR; R05; no gate | cannot occur: no incarnation is bound | held:start; AL; R07; G9 | stopping; CR; R08; G4 | stopped; UM; R09; G11 | held:start; CR; R10; no gate | stopping; CR; R11; no gate | refused: station_held | refused: station_held | refused: station_held | refused: station_held | held:start; CR; R17; no gate | held:start; CR; R18; G13 | stopped; CR; R18; G13 | stopping; CR; R19; G14 |
| held:live | refused: station_held | refused: station_held | refused: station_held | running when the hold records only missed readings and this reading equals the tuple of R04, else held:live; CU; R06; no gate | stopping; CR; R05; no gate | held:live; CU; R06; no gate | held:live; AL; R07; G9 | stopping; CR; R08; G4 | refused: station_proof_unexpected | held:live; CR; R10; no gate | stopping; CR; R11; no gate | refused: station_held | refused: station_held | refused: station_held | refused: station_held | cannot occur: no lifecycle effect is in flight in this row; the hold is an observation | refused: station_proof_unexpected | refused: station_proof_unexpected | stopping; CR; R19; G14 |
| held:stop | refused: station_held | refused: station_held | refused: station_held | held:stop; CU; R06; no gate | held:stop; CR; R05; no gate | held:stop; CU; R06; no gate | held:stop; AL; R07; G9 | stopping; CR; R08; G4 | provisioned when R17 records that origin, else stopped; UM; R09; G11 | held:stop; CR; R10; no gate | stopping; CR; R11; no gate | refused: station_held | refused: station_held | refused: station_held | refused: station_held | held:stop; CR; R17; no gate | refused: station_proof_unexpected | refused: station_proof_unexpected | stopping; CR; R19; G14 |
| held:control | refused: station_held | refused: station_held | refused: station_held | held:control; CU; R06; no gate | cannot occur: no incarnation is started or bound | cannot occur: no incarnation is bound | refused: station_held | refused: station_held | held:control; UM; R09; G11 | held:control; CR; R10; no gate | held:control; CR; R10; no gate | refused: station_held | refused: station_held | refused: station_held | refused: station_held | held:control; CR; R17; no gate | provisioned or stopped, the origin recorded in R17; CR; R18; G13 | provisioned or stopped, the origin recorded in R17; CR; R18; G13 | retiring; CR; R19; G14 |
| held:bump | refused: station_held | refused: station_held | refused: station_held | held:bump; UM; R14; no gate | cannot occur: no incarnation is started or bound | cannot occur: no incarnation is bound | refused: station_held | refused: station_held | refused: station_proof_unexpected | held:bump; CR; R10; no gate | held:bump; CR; R10; no gate | refused: station_held | refused: station_held | refused: station_held | refused: station_held | held:bump; CR; R17; no gate | provisioned; CR; R18; G13 | stopped; CR; R18; G13 | retiring; CR; R19; G14 |
| held:retire | refused: station_held | refused: station_held | refused: station_held | held:retire; UM; R20; no gate | held:retire; UM; R20; no gate | cannot occur: no incarnation is bound after the retiring commit | refused: station_held | refused: station_held | held:retire; UM; R09; G11 | held:retire; CR; R10; no gate | held:retire; CR; R10; no gate | refused: station_held | refused: station_held | refused: station_held | refused: station_held | held:retire; CR; R17; no gate | retired; UM; R16; G12 | retiring; CR; R18; G13 | retiring; CR; R19; G14 |

Below, a cell is cited as [state x event].

## 4. Vocabulary of the cells

### 4.1 Durable records

Each record is written before the effect it precedes. The second column is the
committing service of the cell. The third column names the write-ahead records
that the effect owners MUST also hold before their own effects. This file
names the records and their order; their bytes belong to the owning contracts.

| Id | Written by | Content, and what it precedes | Effect owners and their own write-ahead | Source |
| --- | --- | --- | --- | --- |
| R01 | CR | Create operation: operation identity, station name, host, project, profile pin, phase `provision_requested`. Precedes the request for an account. | DI: request and effect identity. UM: caller-scoped effect intent and the `creating` generation append before any account mutation; `active` only after identity, skeleton, persistence denial and static deny are verified. | C24 "Lifecycle and failure handling", create; UM 3; UM 4; GJ 4 |
| R02 | CR | Same operation, phase `enroll_requested`, listing the bindings to be made. Precedes every binding. The station is marked usable only after all bindings are durable. | CU: name latch intent in manager state before the name file is published. KS: binding record for the exact (uid, generation), one per key purpose. AL: registry entry before a station link is emitted [C32 "Recommendation"]. CR: owner binding in protected station metadata. | C24 "Lifecycle and failure handling", create; C24 "Ownership and records"; UM 6.2; BK24 "Owner channel" |
| R03 | CR | Start operation: new operation, request, execution and lease-request identities; phase `lease_requested` before the first lease acquire [HL21]; phase `start_requested` before the physical-start request. NEW phase `start_requested`: without it a crash cannot be classified. | CU: prepared lease record, blocking before the acquire is acknowledged [HL06]. DI: request and effect identity with the J1 verdict. LA: start receipt with the execution number, written as root before privileges are dropped; a second start of the same execution is rejected [BK05 "Transition from root to agent"]. | HL21; HL06; BK07 "Dispatcher and the one-shot transaction" |
| R04 | CU | Bound holder: exact `{pid, uid, boot_id, start_time}` after the independent kernel reading equals the manager observation and the requested holder. Precedes the opening of the input fence. | SH: the fence stays closed until R04 exists. | HL07; HL22; HL observer |
| R05 | CR | Exit observation from the session manager record, with the incarnation it concerns. Precedes the request for the absence proof. | DI and UM: journaled stop effect identity. | C24 "Lifecycle and failure handling"; BK05 "Load: a resource group per generation" |
| R06 | CU | One observer reading, kept in manager state: equal to the bound tuple, unequal, missing, unreadable, or a process where none may run. On a missing or unreadable reading the lease phase becomes `unknown` and the holder is kept. Precedes any reaction to the reading. Where a cell enters or stays in a held row on a reading, R06 is the hold record, and an equal reading that leaves `held:live` is its own acceptance record. | none | HL08; HL observer |
| R07 | AL | Admission record of one message: signer, grant chain verdict, revocation snapshot, replay check, disposition `delivered` or `kept_undelivered`. Precedes the hand-over to the session host. | SH: queue entry before delivery. | BK24 "Trust gate"; BK07 "Queue and questions of the harness" |
| R08 | CR | Stop operation: reason (section 7), requester, the incarnation and lease it targets. Precedes the stop signal. The input fence and the start fence for the generation are closed first. | SH: fence closed. DI and UM: journaled stop effect. | C24 "Lifecycle and failure handling", down; BK07 "Permission for a successor" |
| R09 | UM | Absence record: proof P1 with its coverage, quiet interval, boot identifier and the fences held. Precedes the release of the home lease [HL09; HL10], of the execution capacity claim and, in retirement, the removal of the home. | CU: release event and tombstone. DI: capacity release. | UM 5; UM 6.1; HL09; BK07 "Dispatcher and the one-shot transaction" |
| R10 | CR | Recovery entry: the operation found, its recorded phase, the classification taken. Precedes any resumed step; where the classification is a hold, R17 follows it before anything else. | Each effect owner reconciles its own journal before new work [UM 3; BK07 "Dispatcher and the one-shot transaction"]. | C24 "Lifecycle and failure handling"; HL21; HL22 |
| R11 | CR | Boot record: the boot identifier now read and the one in R04 or R03. Precedes the request for the absence proof. | none | HL05; BK07 "Wake-up and context transfer" |
| R12 | CU | Update composition intent: approved release identity and the full control inventory with digests. Precedes the first replaced control; the trust pin is published last. | UM: skeleton install effect through trusted descriptors. | UM 7; C24 "Platform controls and approved updates"; HL14 |
| R13 | KS | Rotation record: station name, key purpose, old and new public key identifiers, the authorizing act. Precedes the first signature by the new key. | none | NEW: no source defines the record; the task requires that a name is never re-bound to a new key without one. |
| R14 | UM | Bump effect intent and the `retiring` append for the old generation. Precedes the stop, the reset and the successor. | KS owner: re-admission and new binding confirmations before the successor is `active`. | UM 6; UM 6.2 |
| R15 | CR | Retire operation: export outcome or operator waiver reference, obligations check. Precedes the request to retire. | UM: effect intent and the `retiring` append before stop or deletion. | UM 5; C24 "Lifecycle and failure handling", retire |
| R16 | UM | The `removed` append and the terminal result, after verified cleanup and account absence. Precedes the release of the account reservation. The name record is retained. | CR: retained name record with the last key identifiers per purpose. | UM 5; GJ 4; BK06 "The account ends, the identity remains" |
| R17 | CR | Hold record: held case, origin state, the effect and its identity, what was sent, what was observed. Precedes everything else; from this record on nothing is released. | none | C24 "Lifecycle and failure handling", unknown; HL08 |
| R18 | CR | Proof acceptance: which proof (section 4.2), its producer, its evidence digest, the hold it answers. Precedes the state change out of held. | CU: lease release event where the proof allows it [HL09]. | HL09; HL10 |
| R19 | CR | Operator order: the authenticated, exact-content operator act for this station. Precedes the teardown. | UM: operator retire act with its recorded waiver where used [UM 5]. | UM 2; UM 5; HL12; BK06 "The operator signs one action" |
| R20 | UM | Retirement step log: one entry of the retiring effect per observation or step outcome, including errors and unknown results. Precedes the next step of the same effect. | none | UM 3; UM 5; BK05 "Homes and results" |

### 4.2 Proofs

Only these proofs change a state. Each has one producer.

| Id | Name | What it is | Producer | Source |
| --- | --- | --- | --- | --- |
| P1 | absence proof | Zero tasks of the account for the whole configured quiet interval, from a complete root-readable task inventory by real, effective, saved and filesystem uid with stable process handles, taken while the input fence and the start fence of the generation stay closed. Every thread is a task and counts. On Linux an empty resource group stands for this only where qualification showed it equal to account-wide absence. A partial, denied or timed-out inventory is not a proof. | UM | UM 5 step 2; UM 6.1; BK05 "Load: a resource group per generation"; BK06 "Total stop" |
| P2 | incarnation match | The Curator observer's own kernel reading of `pid`, `uid`, `boot_id` and `start_time` equals the manager observation and the requested holder, in one pass. | CU | HL observer; HL07 |
| P3 | recorded result | The recorded terminal result of the same effect identity, read from the effect owner's journal. | the effect owner, read by CR | UM 3; BK05 "Account, generation and journal" |
| P4 | no-effect proof | For a start: settled operation and manager evidence that no start was made, or an authoritative refusal of the start with no start receipt. For other effects: a verified rollback, or authoritative absence of the effect record where the owner's journal is intact. Missing evidence and contradictory evidence are not this proof. | the effect owner, read by CR | HL09; HL21; HL23; UM 3; BK05 "Account, generation and journal" |

A changed boot identifier (R11) proves only that the bound incarnation ended.
It is not P1.

### 4.3 Refusal codes

The set is closed. A code in the right column is carried unchanged in the
refusal detail when the refusing service is its owner.

| Code | Meaning | Carries |
| --- | --- | --- |
| `station_absent` | No station of this name exists. | none |
| `station_exists` | The name already has an account. | none |
| `station_retired` | The station is retired; only a new provision is admitted. | none |
| `station_retiring` | Removal is committed. | UM `generation_inactive` |
| `station_held` | The station is held; only the cells of its held row apply. | none |
| `station_not_held` | The teardown order applies only to a held station. | none |
| `station_not_enrolled` | Identity and keys are not bound. | none |
| `station_already_enrolled` | Identity and keys are already bound. | none |
| `station_not_running` | Nothing is running to stop. | none |
| `station_busy` | A lease holder (prepared, bound or unknown) blocks the change. | HL `environment_home_leased`; UM `target_busy`; C24 `werkstatt_busy` |
| `station_incarnation_exists` | A start is in flight, bound or not yet proved gone. | none |
| `station_proof_unexpected` | No recorded effect or hold awaits this proof. | none |
| `station_operation_conflict` | Same operation identity, different arguments. | UM `request_id_conflict`; HL `request_conflict` |

Gate sets:

| Gate | Cells | Closed codes |
| --- | --- | --- |
| G1 | provision | `station_account_shared`, `station_grant_refused`, `station_qualification_required` (UM `qualification_required`, `platform_unsupported`, `class_unsupported`), `station_capacity_unavailable` (UM `quota_exceeded`, GJ `journal_capacity_reserve`), `station_operation_conflict` |
| G2 | enroll | `station_identity_mismatch`, `station_rotation_unrecorded`, `station_account_shared`, `station_key_unbound` (UM `bump_key_admission_unconfirmed`), `station_link_unregistered` (C32 `native-environment-not-registered`), `station_owner_unbound`, `station_operation_conflict` |
| G3 | start | the start gates of section 6.2 |
| G4 | stop requested | `station_stop_not_authorized` |
| G5 | retire | `station_retire_not_authorized`, `station_export_unresolved` (UM `cleanup_not_admitted`), `station_obligations_open` |
| G6 | profile update approved | `station_release_not_approved`, `station_busy`, `station_update_recovery_required` (HL `environment_lease_recovery_required`) |
| G7 | key rotation | `station_rotation_not_authorized`, `station_generation_inactive` |
| G8 | generation bump | `station_bump_not_authorized`, `station_export_unresolved`, `station_qualification_required`, `station_busy` |
| G9 | instruction received | `message_signature_invalid`, `message_grant_refused`, `message_revocation_unknown`, `message_replayed`, `message_target_mismatch` |
| G10 | process appears, as a bind | HL `environment_lease_holder_mismatch`, HL `environment_lease_authority_refused`, HL `environment_lease_revision_conflict`, verbatim with their reasons [HL20; HL observer] |
| G11 | stop confirmed | `station_absence_unproven` (UM `processes_remain`; HL `environment_lease_release_unconfirmed`) |
| G12 | retired commit | `station_absence_unproven`, `station_cleanup_pending` (UM `cleanup_pending`, `path_is_link`, `backend_failed`) |
| G13 | proof acceptance | `station_proof_mismatch`; `station_absence_unproven` when the hold lists a process observation (R06) not yet answered by R09 |
| G14 | operator teardown order | `station_operator_act_invalid` |

The key service has two codes of its own, used outside the lifecycle cells
(section 10): `message_author_account_mismatch` and `signer_generation_inactive`.

## 5. Unknown outcomes

U1. When an effect may or may not have happened, the station enters the held
row named in [state x unknown outcome] and R17 is written first. When the
unknown is an observation, the cell names R06 and that reading is the hold
record. A process seen while a station is already held is added to the hold
and blocks the proof exits of that row until R09 answers it (G13). Nothing is
released from unknown: the home lease, the account reservation, the capacity
claim and the quota charge all stay [C24 "Lifecycle and failure handling",
unknown; HL08; BK07 "Dispatcher and the one-shot transaction"; DF B.3].

U2. Only a proof of section 4.2 or the operator teardown order leaves a held
row. The exits are the cells of that row and nowhere else:

- `held:provision`: P3 [held:provision x proof: effect completed]; P4
  [held:provision x proof: effect did not happen]. A proved rollback returns to
  the origin and does not admit a new provision by itself: that is a fresh
  operation [BK05 "Account, generation and journal"].
- `held:enroll`: P3 for every binding of R02, or P4 for the bindings this
  operation created; resources of uncertain ownership are never deleted [C24
  "Lifecycle and failure handling", create].
- `held:start`: P2 [held:start x process appears]; P4 [held:start x proof:
  effect did not happen]; P1 [held:start x stop confirmed]. P3 alone (a start
  receipt exists) does not leave the row: a started process is not a bound one.
- `held:live`: P2, and only when the hold was a missed reading [held:live x
  process appears]. A second process tree is cleared only through `stopping`
  and P1.
- `held:stop`: P1 only [held:stop x stop confirmed].
- `held:control`: P3 or P4; both return to the origin, and the next start
  re-verifies every digest and binding (section 6.2).
- `held:bump`: P3 [held:bump x proof: effect completed]; P4 only when the old
  generation never reached `retiring` [UM 6.2]; otherwise the operator teardown
  order, which is the ordinary-retirement fallback of UM 6.1.
- `held:retire`: P3 [held:retire x proof: effect completed]; P4 re-runs the
  step forward under the same effect identity.

U3. The operator teardown order asserts no fact. It chooses the one direction
that is safe without the fact: down. It leads to `stopping`, where P1 is still
required, or to `retiring`, where every step is still verified. An audited
home-lease break [HL12; HL13] and an abandoned operation [C24 "Lifecycle and
failure handling"] remove a protection or a fence; they are not proofs, they
change no cell, and they never authorize a release or a retirement.

U4. A stop or an absence is never inferred from a missing process, a dead
direct child, an empty or filtered lookup, a timeout, a quiet inbox, a launcher
exit, a changed boot identifier or a successful command [C24 "Lifecycle and
failure handling", unknown; UM 6.1; HL08; BK05 "Load: a resource group per
generation"]. The pair `stopping` and `held:stop` has exactly one exit, P1;
this is intended.

## 6. Restart rule

### 6.1 What a restart is

A restart is the cell [stopped x start] taken again. It keeps the account, the
generation, the home, the station name and every key binding. It creates a new
process incarnation with new operation, request, execution and lease
identities [HL06; BK07 "Dispatcher and the one-shot transaction"; DF B.3]. It is
never a generation bump: a new conversation or a new incarnation MUST NOT
cause a bump [UM 6].

Who may start:

- the party responsible for the station, named by the grant (the raising
  orchestrator or the operator), through curator-run [C24 dec 4];
- the host after a crash or a reboot, only through the dispatcher and only
  within a lifecycle permission that the owner granted for this station;
  without that permission a start is single and nobody may repeat it [BK07
  "Permission for a successor"; BK07 "Wake-up and context transfer"];
- nobody, when the station was stopped by a human, or when the lifecycle
  permission was withdrawn by owner cancellation, owner retirement, chain
  revocation, signed retirement of the station or a maintenance stop [BK07
  "Permission for a successor"].

A restart is admitted only from `stopped`, that is after P1 or P4 for the
previous incarnation [BK07 "Permission for a successor"]. A restart budget
bounds automatic restarts so that successors cannot reset a time window [BK07
"Permission for a successor"]; its count and backoff are OQ3.

### 6.2 Start gates (G3)

Every gate is evaluated at every start, including restarts and native resume
[C24 "Platform controls and approved updates"; UM 7]. A gate that fails before
R03 refuses in [stopped x start]. A gate that fails after R03 is a no-start
outcome: it arrives as P4 in [starting x proof: effect did not happen] and
carries the same code.

| Gate | Check | Code | Evaluated by | Source |
| --- | --- | --- | --- | --- |
| lifecycle | A lifecycle permission covers this start; the restart budget is not exhausted; a human stop is not in force. | `station_lifecycle_not_permitted`, `station_restart_budget_exhausted` | DI | BK07 "Permission for a successor" |
| fixed fields | The fixed start fields of section 9.1 equal the values recorded at provision. | `station_plan_changed` | DI | BK07 "Permission for a successor"; DF A |
| generation | The exact (uid, generation) is `active` in the generation journal, read under its lock protocol. | `station_generation_inactive` | LA | GJ 1; GJ 6.1; BK05 "Transition from root to agent" |
| profile digests | The trust pin equals trusted approved-release metadata, and every platform control equals its approved digest; missing, unreadable, extra effective or mismatching controls refuse before provider execution; the checked objects are bound to the admitted start. | `station_profile_digest_mismatch` | OPEN OQ9: the executing service is disputed between sources; the gate and its code are not. | C24 dec 2; C24 "Platform controls and approved updates"; UM 7; BK07 "Immutable launch boundaries" |
| home skeleton | Every path of section 8 has its owner, group, mode, type and link count; no stored ACL or file capability; no entry outside the closed list in a platform-owned directory. | `station_skeleton_invalid` | same as profile digests | UM 7 |
| identity latch | The name file equals, byte for byte, the name in Curator's protected station record and the name the start carries (section 9.2). | `station_identity_mismatch` | CU | section 9.2 (PROPOSED) |
| key bindings | A binding for the exact (uid, generation) exists for each key purpose of section 10. | `station_key_unbound` | KS, asked by CR | BK06 "The kernel establishes the peer"; GJ 4 |
| message link | The station link is admitted. | `station_link_unregistered` | CR | C32 "Recommendation" |
| credential mode | The plan selects the mode without secrets at the agent; the gateway path is ready: gateway address, service lease, listener of this generation, qualified adapter. Unknown readiness refuses. | `station_credential_mode_refused`, `station_gateway_unready` | CR for the plan; MG for readiness | BK09 "Mode without secrets at the agent"; BK08 "Readiness before launch" |
| J1 | The grant chain covers this start for this principal, host, account and plan; the revocation verdict for the exact chain is "not revoked". "Revoked" and "unavailable" both refuse. | `station_grant_refused`, `station_revocation_unknown` | DI | section 11 |
| qualification | The host qualification for the required guarantees is current. | `station_qualification_required` | DI | BK05 "Qualification revocation"; UM 1 |
| capacity | Capacity and policy admit the start; an unread pause state is a pause. | `station_capacity_unavailable` | DI | BK07 "Dispatcher and the one-shot transaction" |
| home lease | The lease is acquired for the admitted digest; a terminal replay never admits. | `session_home_lease_unavailable`, verbatim | CU, asked by CR | HL06; HL21 |

### 6.3 What a restart must never do

- Reuse a session reference. The operation, request, execution and lease
  identities, the manager session handle and generation, the controller epoch
  and the credential stub of the previous incarnation are dead; a surviving
  connection of an old controller has no right to write [HL06; BK07 "Service,
  runner and the single writer"; BK09 "Model provider through the gateway"].
  Harness conversation state in the home is not a session reference: it is
  kept, and a native resume is allowed only on the same host, harness, home and
  profile pin; a failed resume is reported and is not rebuilt automatically
  [BK07 "Wake-up and context transfer"; C24 "Persistent stations and
  task-lifetime spawn"].
- Widen authority. A restart cannot add an account, a harness or a profile
  even if a parent grant has grown since; widening needs a new provision [BK13
  "Renewal without widening"].
- Repair by guessing. A failed gate refuses and preserves what it found. No
  start rewrites the name file, re-pins the trust pin, replaces a digest,
  enrolls a link or adopts an account [C24 "Platform controls and approved
  updates"; HL03; C32 "Recommendation"; UM 3].
- Retry blindly. A lost start is `held:start`, never a second start request
  [DF B.3; BK07 "Dispatcher and the one-shot transaction"].

## 7. Rules for a kept station

These nine rules answer items 1 to 9 of section B of the dispatcher field
inventory [DF B]. Each row names the cells that carry it.

| Rule | Statement | Carrying cells | Source |
| --- | --- | --- | --- |
| K1 session identity | Three things are distinct. The station identity (name, account, generation, keys) is stable for the life of the station. A process incarnation is one bound kernel tuple; a restart consumes it and creates a new one with new identities. A harness session is conversation state in the home; a restart keeps it. One live incarnation per station: a second start refuses. | [stopped x start] creates the identities (R03); [starting x process appears] binds the incarnation (R04); [starting, running, stopping x start] refuse `station_incarnation_exists`; every held row x start refuses `station_held` | DF B.1; HL07; BK07 "Dispatcher and the one-shot transaction"; section 6 |
| K2 lifetime | The horizon of a station is the validity of the grant chain admitted by J1, inside the dispatcher policy window. It replaces the one-run runtime bound. A persistent station has no time bound per incarnation; what remains per incarnation is the start-detect bound and the stop bound of the policy, the term of the message-key attestation (at most 86400 s, renewed by the key service ahead of expiry; a missed renewal closes message signing, not the station), and the model credential lease held by the gateway (K7). A task-lifetime station keeps the published bounds: account 24 hours by default and at most 7 days, one execution 4 hours by default and at most 12. Renewal: the dispatcher re-signs the leaf under the current chains and the broker replaces the binding of the same account and generation, old removed before new; the new scope is the intersection of the current chains with the originally admitted request; only a member of the existing chain may renew, a revoked right is never re-issued by maintenance, and extending a persistent grant is an operator act. How far ahead renewal must happen is OQ2. The action at expiry is OQ1; what is decided is that from expiry J1 refuses every start and J2 refuses every instruction. | [stopped x start] gate J1; [running x instruction received] gate G9; [running x stop requested] when OQ1 is decided for a stop | DF A; DF B.2; BK05 "Homes and results"; BK06 "Message key and its attestation"; BK07 "Dispatcher and the one-shot transaction"; BK13 "Renewal without widening"; BK06 "The operator signs one action" |
| K3 restart rule | Section 6. The same account, generation and home are reused. A lost start is unknown: held, never retried blindly. | [stopped x start]; [starting x starter crash]; [starting x unknown outcome]; the `held:start` row | DF B.3; section 6 |
| K4 liveness | "Alive" means that the bound process incarnation is read from the kernel by the Curator observer (P2). A self-report, an a2a heartbeat or an answered message is not liveness and is never merged into a termination verdict. A missed or unreadable reading is unknown, never a stop: the station enters `held:live`, the lease stays, and the operator or the reconciler acts. The reading interval and the silence deadline are OQ4. | [running x process appears]; [running x liveness reading missed]; the `held:live` row | DF B.4; HL observer; HL08; C24 "Lifecycle and failure handling" |
| K5 follow-up work | A later instruction reaches a running station through its message identity: the a2a link of that identity, in the owner channel or a project room. Each instruction is checked by J2 against the grant actions before it becomes a command. A new instruction is not a new start: it writes R07 and never R03. To a station that is not running, an admitted message is kept undelivered and starts nothing. | [running x instruction received]; [stopped, starting, stopping, held:start, held:live, held:stop x instruction received] | DF B.5; BK24 "Trust gate"; BK24 "Owner channel"; BK07 "Wake-up and context transfer" |
| K6 revocation while running | Section 7.1. | [running x stop requested]; [stopped x start] gate J1; [running x instruction received] gate G9 | DF B.6; section 7.1 |
| K7 credential and gateway lease | The station holds no model credential: the gateway holds the lease and the station holds a stub bound to one generation, one start and one account. When the gateway's lease renewal fails, forwarding closes and the station loses model access. The station is not stopped by that failure: it idles, the session host keeps its input fence closed and messages accumulate until the path is ready again. A later start re-checks gateway readiness. Whether a bounded idle escalates to a stop is OQ7. An account block after a leak match is different: it stops the session through [running x stop requested]. | no transition; [stopped x start] gate credential mode; [running x stop requested] for an account block | DF B.7; BK09 "Model provider through the gateway"; BK09 "Leak tripwire"; BK07 "Wake-up and context transfer" |
| K8 home and state | State that survives a restart lives only in the station-writable paths of section 8. Retirement duty: the work product is exported before the home is removed; a partial, unknown or failed export keeps the home, and only a recorded operator act waives the duty. The account stays reserved and fenced until P1 over every task succeeds. Homes are never archived; keeping a retired home is a separate operator operation outside retirement. | [stopped x retire] gate G5; [retiring x stop confirmed]; [retiring x proof: effect completed] gate G12 | DF B.8; BK07 "Dispatcher and the one-shot transaction"; BK05 "Homes and results"; UM 5 |
| K9 capacity | A station holds two claims. The account claim lasts from provision to `retired` and is charged once across bumps. The execution claim lasts from `starting` until R09 and is never released from unknown. A reclaim is a stop requested or a retire through this table, by the operator, or by the dispatcher for a non-persistent allocation it owns; it is never a signal sent outside the table. Whether the dispatcher may reclaim the execution claim of a persistent station without an operator act is OQ8. | [running x stop requested]; [stopping x stop confirmed] releases the execution claim; [retiring x proof: effect completed] releases the account claim | DF B.9; UM 6; BK07 "Dispatcher and the one-shot transaction"; BK05 "Two narrow privileged entries"; C24 "Host budget" |

### 7.1 Triggers of a stop

Every trigger enters the table through [running x stop requested] with its
reason recorded in R08, or through a gate. The last column is the maximum
delay from the observation to the stop request.

| Trigger | Observed by | What is decided | Maximum delay to the stop |
| --- | --- | --- | --- |
| Owner stop of one station | CR, from the party responsible for the station or the operator | Stop through the table; the station stays stopped until a human starts it [BK07 "Wake-up and context transfer"]. | Immediate on receipt; completion within the stop bound of the policy [DF A]. |
| Total stop of the installation | Each service directly: UM freezes generations and closes ingress, SH stops sessions, DI ceases starts, MG closes uses [BK06 "Total stop"] | Stop of every station; resumption only by operator signature. | No number in the sources; OQ5. |
| Qualification revoked | UM, the qualification reconciler [UM 1; BK05 "Qualification revocation"] | New starts close at detection; a running station is narrowed with confirmation or stopped. | 300 seconds from detection, not reset by retries or restarts. |
| Account block after a leak match | MG and CB [BK09 "Leak tripwire"] | The session is stopped by the permitted path. | No number in the sources; OQ5. |
| Grant revoked | DI at every start through the revocation check; MG and AL at every use [BK13 "Revocation and unknown state"]. A feed into the dispatcher for a running station does not exist yet [DF C]. | Starts refuse; every use refuses no later than max(S + A, F), with A at most 60 seconds. | OPEN OQ5 for the stop of the running process. |
| Grant expired | Same observers, by the verified-time watermark [BK13 "Renewal without widening"] | Starts and instructions refuse from expiry. | OPEN OQ1. |
| The seal of a cross-owner grant spent | The verifying service on its own chain node [BK14 "Revocation"] | The grant refuses from the observed spend; privileged actions stop when the last block is older than 60 minutes (monetary or irreversible) or 90 minutes (other). | OPEN OQ5; the sources give no upper bound on delivery of the spend. |
| Device set changed | AL, by the device attestation of the carrier profile [BK24 "Assurance levels for human messages"] | A message from a device outside the pinned chain does not reach the level that can command; J2 refuses. | OPEN OQ5. |
| Policy removed | DI, by policy identity and revision [DF A] | Starts refuse. | OPEN OQ5. |

Unknown revocation state. Decided: a start refuses `station_revocation_unknown`
and each use refuses, because "unavailable" is a refusal and a lost connection
is not absence of revocation [BK13 "Revocation and unknown state"]; without a
verified time source services hold at most 10 minutes by the monotonic clock
and then stop everything that depends on time [BK13 "Renewal without
widening"]. Whether the running station is held or stopped, and after how
long, is OQ6.

## 8. Home skeleton

H is the station home. S is the dedicated group of the station, U its uid. The
list is closed: any other entry at H, or below a platform-owned directory,
fails the home skeleton gate. No path below H holds a model token, a private
key, a credential of the carrier or a lease record; those live with their
holders (section 10; BK09 "Mode without secrets at the agent"; C32 "Security
considerations"; HL01). The actual discovery paths are published per runtime
mapping; `.harness` stands for the fixed protected adapter destination [UM 7].

| Path | Owner:group | Mode | Written by | Station may write | Install, sync and repair | Source |
| --- | --- | --- | --- | --- | --- | --- |
| `H/` | root:S | 0750 | UM | no | Never replaced while a lease holder blocks; replaced whole only by a bump. | UM 7; HL14 |
| `H/AGENTS.md`, `H/CLAUDE.md` (the one selected by the approved runtime mapping) | root:S | 0640 | CU content, installed by UM | no | Replaced only by an approved release, in [provisioned or stopped x profile update approved]. | UM 7; C24 dec 2 |
| `H/.platform/`, `H/.platform/skills/` and each skill directory | root:S | 0750; skill files 0640; approved executables 0750 | CU content, installed by UM | no | As above; closed approved inventory. | UM 7 |
| `H/.platform/trust-pin.json` | root:S | 0640 | CU through the approved-release path, published last | no | As above; never chosen by the station. | UM 7; C24 "Platform controls and approved updates" |
| `H/.platform/identity-name` (RESERVED, PROPOSED) | root:S | 0640 | CU, once, at enroll | no | Never rewritten by install, sync or repair. NEW path name: the task reserves the path and no source names it. | section 9.2 |
| `H/.harness/` | root:S | 1770 | UM | creates and removes its own entries only | Root-owned entries protected by the sticky parent. | UM 7 |
| `H/.harness/settings.json` (hook settings) | root:S | 0640 | CU content, installed by UM | no | Replaced only by an approved release. | UM 7; C24 dec 2 |
| `H/.harness/state/` (harness state) | U:S | 0700 | the station | yes | Preserved; outside the cooperative write guard [HL17]. Destroyed by a bump and by retirement. | UM 7; UM 6; ENV 8.1 |
| `H/work/` (work directories, the station's own repository clone) | U:S | 0700 | the station | yes | Preserved. Destroyed by a bump and by retirement. | UM 7; UM 6; C24 "Lifecycle and failure handling" |
| `H/tmp/` | U:S | 0700 | the station | yes | Preserved; not a place for state. Destroyed by a bump and by retirement. | UM 7; UM 6 |
| The a2a station link (`.a2a/` with `daemon.sock`, `identity`, `station`, `station.key`) and the hook-failure log beside it | OPEN OQ10, OQ11 | OPEN | OPEN | OPEN | OPEN | C32 "Recommendation"; UM 7; UM 5 |

The a2a link row is OPEN because two sources contradict on its owner. C32
"Recommendation" requires that the managed home containing `.a2a` "must belong
to the launching effective UID"; UM 7 requires that the home root "is never
owned by U". C32 also places a station-readable secret file, `station.key`, in
the home, while UM 5 states "This station layout holds no private keys" and
section 10 gives the station a socket and never a file. The row stays OPEN
until OQ10 and OQ11 are decided; the rest of the list does not depend on it.

One home serves one station. A profile home is never shared across stations
[HL24], and a station cannot traverse another home: H is 0750 with a distinct
group S and no supplementary membership [UM 7].

## 9. Identity

### 9.1 Start fields

| Field | For the life of the station | Who approves a change |
| --- | --- | --- |
| Host (the receiving dispatcher) | Fixed. | Nobody: another host is another station, by a new provision [DF A]. |
| Account and generation | Fixed at every restart. | The generation changes only through [stopped x generation bump], on the operator or dispatcher authority of UM 2 and UM 6. |
| Plan pins (worker plan, profile, harness, execution profile) | Fixed at every restart; the plan is reused byte for byte. | A pin changes only through [stopped x profile update approved], that is by an approved release; the next start is then a new admission under J1 [C24 dec 3; BK07 "Permission for a successor"]. |
| The principal the grant names | Fixed. | Nobody: a station does not change hands by an edit; re-parenting is not achieved by editing a file [C24 "Ownership and records"]. |
| Station name | Fixed (section 9.2). | Nobody. |
| Model selection inside the catalog; reasoning effort | May change at a restart. | The party responsible for the start, inside the catalog and the grant; J1 admits it [DF A; BK07 "Launch nesting"]. |
| Prompt | May change at a restart. | The party responsible for the start; a goal is set by the caller, never by the station [BK07 "A goal does not belong to the agent"]. |

### 9.2 Name latch (PROPOSED)

This subsection is PROPOSED. It awaits two owner confirmations and is not
normative until both are recorded.

- A station has one stable name.
- The latch: the name file is created once, at enroll (R02). At every start
  it is compared byte for byte (gate "identity latch"). A mismatch refuses
  `station_identity_mismatch` and preserves both the file and the record:
  nothing is rewritten, deleted or re-derived.
- The name file and its seam are owned by Curator Core. The full typed
  identity is owned by the launcher of the session entry; in the terms of
  section 1.2 that is curator-run, which delivers the typed identity to the
  harness [C32 "Recommendation"]. Section 13 holds the two rows.
- For a station with no given identity, Core derives a synthetic name once
  from {host_id, project_id, profile_id}: prefix `syn1:`, then SHA-256 over a
  tagged, length-prefixed encoding. The function is an input owned by the
  identity contract and is not redefined here.

Open points of this subsection are OQ12.

## 10. Keys

KY1. A station can use keys and never read them. The holder of every station
key is the key service. The station account reaches a socket of the key
service and never a key file; no key material, private-key path or secret
value is present in the home, the plan, the environment, a record or a log
[C24 dec 1; C24 "Security considerations"; BK06 "The kernel establishes the
peer"]. The interim custody of CIP-0024 (one signing agent per station, key
file outside the station's access, socket limited to the station uid) meets
the same reach rule and is not the target [C24 dec 1].

KY2. A station needs three key purposes, each a separate key per station
identity: identity, request signing and message signing. A key of one purpose
signs nothing of another purpose [BK06 "Which secrets exist"; BK06 "Message
key and its attestation"]. The message-signing key is distinct from the
request key and from any delegation key.

KY3. The key service takes the caller from the kernel peer credential of the
connection, never from a field of the request, and admits it only when the
exact (uid, generation) is `active`; a retired or bumped generation loses its
bindings and its connections [BK06 "The kernel establishes the peer"; GJ 4;
UM 8]. It refuses `signer_generation_inactive` otherwise.

KY4. One account is exactly one message author. Each station identity runs its
message sender under its own account. The key service maps the calling
account, as the kernel reports it, to the message-signing key of that one
identity. A sender under any other account signs nothing: the key service
refuses `message_author_account_mismatch` before any signature is produced.
Two stations sharing one account is not a valid configuration:
[absent x provision] and [provisioned x enroll] refuse
`station_account_shared`. Here "message sender" means the process that submits
message bytes for signature; a transport component that only carries signed
bytes runs under its own service account and signs nothing [BK05 "Who holds
privileges"]. Source: binding ruling recorded with this contract; BK06 "The
kernel establishes the peer"; C24 dec 1; C24 "Owner decisions" (no pooling).

KY5. A verifying signature proves the author, not a right [C24 "Security
considerations"; BK06 "Message key and its attestation"]. Rights come only
through J1 and J2.

KY6. A station name is never bound to a new key without R13. At enroll, the
key identifier of each purpose MUST equal the last one retained for the name
(R16), or an R13 for that purpose MUST exist; otherwise the cell refuses
`station_rotation_unrecorded`. Retiring an account does not revoke a
persistent identity, and a later enroll of the same name may return the same
key [BK06 "The account ends, the identity remains"; UM 5].

## 11. Admission: J1 and J2

This file states where the two joins sit. It does not define grants.

J1. Before a station is started, the starter checks a grant against the chain.
The starter is the dispatcher [BK13 "Who checks the right"; C24 "Root context
and authority"]. J1 sits in the gate set G3 of [stopped x start], and so at
every restart; it also sits in G1 of [absent x provision] and [retired x
provision]. Interface: input is the grant chain reference, the principal, the
host, the (account, generation) and the plan pins; output is one of "admitted",
"refused" or "unavailable", where the last two both refuse; the verdict is
recorded with the dispatcher's effect identity before the physical start. The
check is repeated at every start and never reused from an earlier one [BK07
"Dispatcher and the one-shot transaction"; BK13 "Revocation and unknown
state"].

J2. Before a message becomes a command, the message bridge checks the
signature and the grant. The bridge is the a2a link [BK24 "Trust gate"; BK13
"Who checks the right"]. J2 sits in the gate set G9 of every [state x
instruction received] cell that is not a plain refusal. Interface: input is
the exact signed bytes, the grant references and the current revocation
snapshot; the check is deterministic and asks no model; output is "command of
action X on target Y", "data", or a refusal with a code of G9; the admission
record R07 is written before the hand-over. A correctly signed message outside
the grant actions is data and never a command; a relayed owner decision is
data [BK24 "Trust gate"; BK24 "Assurance levels for human messages"; C24 "Root
context and authority"].

Editable text is never the enforcement boundary of either join [C24 dec 4].

## 12. The one-task run

A one-task run is a station whose first stop is also its retirement. It uses
the same table and no other lifecycle: [absent x provision], [provisioned x
enroll], [stopped x start], [starting x process appears], [running x stop
requested] or [running x process exits], [stopping x stop confirmed], then
[stopped x retire] at once. It receives its own account, identity, keys, home
and trust binding, with a fresh context composed with the required root [C24
dec 7; C24 "Persistent stations and task-lifetime spawn"]. It has no lifecycle
permission, so [stopped x start] refuses a second start. Its bounds are those
of a task-lifetime station (K2). Retirement follows authoritative task
completion and durable handover, never provider exit or a delivered doorbell
[C24 "Persistent stations and task-lifetime spawn"]; which board transition
authorizes it is OQ16.

## 13. Who owns what

Exactly one owner per row. No service writes into another's state; it asks the
owner through the owner's interface and records its own request [C24
"Ownership and records"; UM 1; BK08 "One owner of the home"].

| Responsibility | Owner | Others may only | Source |
| --- | --- | --- | --- |
| Account and generation | UM | read the generation journal; the dispatcher requests create, bump and retire within its role | C24 dec 9; UM 1; UM 2; GJ 1 |
| Home: paths, owners, modes, removal | UM | none write; the station writes inside its three writable paths | UM 1; UM 7 |
| Home: content, composition, digests, lease | CU | curator-run requests and binds leases; nobody edits the lease store | C24 dec 9; HL01; UM 1 |
| Profile: approved release content and trust pin | CU | a station may request its own update and installs nothing unapproved | C24 dec 3; UM 7 |
| Start and stop: the station operation and its record | CR | the session host and the party responsible request it | C24 dec 9 |
| Start and stop: physical authority, grant check J1, capacity claims | DI | curator-run and the session host ask; no second privileged path exists | C24 "Ownership and records"; BK05 "Two narrow privileged entries"; BK07 "Dispatcher and the one-shot transaction" |
| Start: privilege transition and start receipt | LA | the dispatcher invokes it | BK05 "Transition from root to agent" |
| Absence proof | UM | all others consume R09; none substitutes its own | UM 5; UM 6.1 |
| Process observation of the bound incarnation | CU | curator-run supplies the manager observation as input, never as proof | HL observer |
| Identity: name file and its seam (PROPOSED) | CU | read | section 9.2 |
| Identity: full typed identity (PROPOSED) | CR | read | section 9.2; C32 "Recommendation" |
| Keys: custody, signing, bindings, rotation record | KS | the station asks for a signature over a socket | C24 dec 1; C24 dec 9; BK06 "The kernel establishes the peer" |
| Message author: one account maps to one message-signing key | KS | a sender under another account gets a refusal | section 10, KY4 |
| Model credential: enrollment, lease issue, revocation | CB | the gateway holds a service lease | C24 dec 9; BK09 "Who holds the credentials" |
| Model credential: holding and use for a station's requests | MG | the station holds a stub only | BK09 "Model provider through the gateway" |
| Messages: transport for one identity, admission J2 | AL | the session host receives admitted items only | C24 dec 6; C32; BK24 "Trust gate" |
| Session: logical session, input queue, input fence | SH | the bridge hands over admitted items; the station holds the harness channel under its account | BK07 "Service, runner and the single writer" |
| Fixed and changeable start fields | the approvers of section 9.1 | propose a change to the approver | DF A |

The station registry record and assignment belong to the task board [C24 dec
9]; the task board is outside the ten services and writes none of the records
of section 4.1.

## 14. Negative obligations

Each forbidden outcome names the cell that enforces it. Each needs a nearby
valid control in the owning implementation.

| Forbidden outcome | Enforcing cell and code | Valid control beside it |
| --- | --- | --- |
| Two processes of one station at once | [starting, running, stopping x start] `station_incarnation_exists`; every held row x start `station_held`; the launcher rejects a second start of one execution (R03) | a start from `stopped` binds one incarnation |
| A start with a changed profile digest | [stopped x start] gate profile digests, `station_profile_digest_mismatch` | approved unchanged controls admit the start |
| A station reading another station's home | [absent x provision] creates the distinct group and modes; [stopped x start] gate home skeleton, `station_skeleton_invalid` | each station reads its own context and writes its own state |
| A key file readable by a station | [provisioned x enroll] binds keys only at the key service (R02); [stopped x start] gate home skeleton | the station signs through its socket |
| A token in a station account | [stopped x start] gate credential mode, `station_credential_mode_refused` | a start in the mode without secrets reaches the model through the gateway |
| Release of an account while any thread runs under its uid | [stopping x stop confirmed] and [retiring x proof: effect completed], `station_absence_unproven` | a quiet account reaches `stopped` and `retired` |
| A retired name reused with a new key without a recorded rotation | [provisioned x enroll] gate G2, `station_rotation_unrecorded` | the same key, or a new key with R13, enrolls |
| A process under station A asking to sign as station B | key service, `message_author_account_mismatch`, before any signature; the single binding is made in [provisioned x enroll] | station A signs as station A |
| Two stations sharing one account | [absent x provision] and [provisioned x enroll], `station_account_shared` | one station per account provisions and enrolls |
| A lost start retried blindly | [starting x starter crash], [starting x unknown outcome], [held:start x start] `station_held` | a crash at phase `lease_requested` resumes the same start once |
| A missed liveness reading treated as a stop | [running x liveness reading missed] goes to `held:live`, not `stopping` or `stopped` | an equal reading keeps `running` |
| An instruction outside the grant actions becoming a command | [running x instruction received] gate G9, `message_grant_refused` | an instruction inside the grant is delivered |
| An instruction causing a start | [stopped x instruction received] stays `stopped` and writes R07 only | a start request starts |
| A stop or reclaim outside the table | K9; [running x stop requested] is the only entry | an authorized stop request stops |
| Anything released from unknown | every held row: no cell releases without P1, P3 or P4 | a proved outcome leaves held |
| A home archived at retirement | K8; [retiring x proof: effect completed] removes the home | the exported work product survives retirement |
| A profile update installed under a live or unknown lease | [starting, running, stopping x profile update approved] `station_busy` | an update installs in `stopped` |

## 15. Open questions

Each question has two options and the owner who decides. None is decided here.

| Id | Question | Option A | Option B | Decides |
| --- | --- | --- | --- | --- |
| OQ1 | A running station whose grant horizon is reached (K2). | Stop it through [running x stop requested]. | Keep it running without new work: J1 and J2 refuse, no stop. | Operator, with the dispatcher owner. |
| OQ2 | How far ahead a grant is renewed (K2). | A fixed lead before expiry, set by policy. | A fraction of the grant's validity. | Grant contract owner; operator. |
| OQ3 | The restart budget (section 6.1). | A count and backoff carried in the lifecycle permission of each station. | One host policy default, with a per-station override. | Dispatcher owner and session host owner; operator. |
| OQ4 | The liveness reading interval and the silence deadline (K4). | One platform constant. | A per-policy value inside a published bound. | Curator Core, with the curator-run owner. |
| OQ5 | A running station after a grant revocation, a spent seal, a changed device set, a removed policy, a total stop or an account block (section 7.1). | Stop within the 300 second deadline already used for qualification revocation. | Contain by use only: gates refuse, the process is not stopped by the event. | Operator. |
| OQ6 | A running station while the revocation state is unknown (section 7.1). | Hold it without new work until the state is readable, with no time limit. | Stop it after a bounded time, for example the 10 minute monotonic bound. | Operator. |
| OQ7 | A station idling after a failed gateway lease renewal (K7). | Idle with no limit. | Stop after a policy bound. | Credential broker and gateway owner; operator. |
| OQ8 | Reclaiming the execution claim of a persistent station (K9). | Operator only. | The dispatcher, inside a policy the operator signed. | Operator. |
| OQ9 | Which service executes the profile digest and home skeleton gates. CIP-0024 says "the launcher MUST verify their digests" and uses "launcher" for curator-run; UM 7 says "the later launcher must acquire the same interlock, verify the protected pin" from trusted handles, which is the privileged launcher. | curator-run, before it requests the physical start. | The privileged launcher, under the generation lock, binding the checked objects to the start. | Curator Core and the user-manager owner. |
| OQ10 | Where the a2a station link lives and who owns its parent (section 8). | In a station-owned directory inside H, keeping the C32 ownership rule. | In the root-owned sticky native directory, by amending the C32 ownership rule. | a2a owner and user-manager owner; the operator decides CIP-0032. |
| OQ11 | The station-readable `station.key` of the C32 link under one account per station. | Keep it as a link secret that is not a station key, since the account is already authenticated by the kernel peer. | Remove it and authenticate the link by the kernel peer only. | a2a owner; operator. |
| OQ12 | Identity (section 9.2): (a) the two pending owner confirmations; (b) how the latched name relates to the `identity` and `station` lines of the C32 link, whose grammar `[a-z0-9._=-]{1,64}` admits neither the colon nor the length of a `syn1:` name; (c) whether the latch survives a generation bump, which destroys the whole home [UM 6]. | (b) the latched name is a separate name, mapped to the link lines by the identity contract; (c) Core keeps the latch record in manager state and re-publishes identical bytes after a bump. | (b) the link grammar is amended to carry the latched name; (c) a bump ends the name and an operator act issues the next one. | Curator Core and the identity contract owner; a2a owner for (b). |
| OQ13 | Key rotation while the station is running. | Refuse; stop first. | Allow, closing connections bound to the old key. | Key service owner. |
| OQ14 | Who runs the export of the work product before removal (K8). The book has a fixed program under the station account before removal for a one-shot run, and export by the user-manager after the stop for a slot generation; UM 5 has no export in its first slice. | A fixed program under the station account, before the retiring commit. | The user-manager, from quarantine, after the stop. | User-manager owner and dispatcher owner. |
| OQ15 | Whose long-lived identity holds a workplace, the agent's or the place's; the book leaves it open [BK07 "Workbench"]. It decides whether the station name follows the agent or the place. | The agent's identity occupies the place by lease. | The place owns the identity; the agent is replaceable. | Owners, as the book states. |
| OQ16 | Which board transition authorizes the automatic retirement of a one-task station, and how long its result metadata is kept [C24 "Open questions for the operator", item 2]. | The board's authoritative completed state with durable required outcomes. | A separate explicit release by the raising orchestrator. | Operator. |
| OQ17 | The reading of "message sender" in KY4. | The author-side process that submits bytes for signature runs under the station account; the carrier client runs under the shared messaging account, as the book places it. | The whole sender, carrier client included, runs under the station account; this conflicts with the book's placement of the bridge and needs an owner decision. | Operator. |

## 16. Alignment with the Swarma book

Marks: same (cited, not copied), refines, conflicts (needs an owner decision),
new. Headings are English renderings; the line is the heading line in the file
at the pinned commit.

| Rule here | Book source (file, heading line) | Mark |
| --- | --- | --- |
| One agent, one account, one identity, own keys, home and root context | `05-polzovatel-i-set.md`, line 212 "Station and its guarantees" | same |
| States of the account and forward-only retirement | `05-polzovatel-i-set.md`, line 47 "Account, generation and journal" | same; the station states of section 3 are new on top of it |
| P1, the absence proof | `05-polzovatel-i-set.md`, line 17 "Load: a resource group per generation" | same |
| Changed boot identifier is not P1 | `07-zapusk-i-host-sessiy.md`, line 151 "Wake-up and context transfer" | refines: the book says a changed boot identifier confirms that old processes are gone; this contract still requires R09 before `stopped` |
| Start receipt, single start of one execution | `05-polzovatel-i-set.md`, line 69 "Transition from root to agent" | same |
| Homes are never archived; export before removal | `05-polzovatel-i-set.md`, line 83 "Homes and results"; `07-zapusk-i-host-sessiy.md`, line 44 | same; the executor is OQ14 |
| Lifetime of persistent and task-lifetime stations | `05-polzovatel-i-set.md`, line 83; `07-zapusk-i-host-sessiy.md`, line 44 | same |
| Restart needs a lifecycle permission and proved absence | `07-zapusk-i-host-sessiy.md`, line 103 "Permission for a successor" | same |
| Keys: the agent asks a signer; kernel peer; three purposes | `06-klyuchi.md`, lines 9, 51, 86 | same |
| One account is exactly one message author (KY4) | `06-klyuchi.md`, line 51; `05-polzovatel-i-set.md`, line 125 "Who holds privileges" | refines under option A of OQ17; conflicts under option B |
| The account ends, the identity remains; R13 on a new key | `06-klyuchi.md`, line 96 | refines: the rotation record is new |
| No model credential at the station; stub and gateway | `09-uchetnye-dannye.md`, lines 101, 148 | refines: the book keeps a readable-token mode as an owner-selected exception; station/1 admits only the mode without secrets |
| Idle on a failed gateway lease renewal (K7) | `07-zapusk-i-host-sessiy.md`, line 151; `09-uchetnye-dannye.md`, line 162 | refines: the book states waiting for a new provider login; the renewal case is applied by analogy, and OQ7 stays open |
| J1 at the dispatcher, J2 at the bridge | `13-doverennosti.md`, line 28 "Who checks the right"; `24-soobscheniya-i-most.md`, line 109 "Trust gate" | same |
| Revocation propagation bound and "unavailable" as refusal | `13-doverennosti.md`, line 94 "Revocation and unknown state" | same |
| Renewal without widening | `13-doverennosti.md`, line 124 | same |
| Qualification revocation within 300 seconds | `05-polzovatel-i-set.md`, line 283 | same |
| Cross-owner grant seal | `14-doverennosti-mezhdu-vladelcami.md`, line 40 "Revocation" | same |
| Unknown outcome is not absence; no blind repeat | `22-effekty-ostanovka-federaciya.md`, line 7; `05-polzovatel-i-set.md`, line 47 | same; the held rows are new |
| Owner channel bound at raising | `24-soobscheniya-i-most.md`, line 89 "Owner channel" | same |
| Platform-owned controls checked before every start | `07-zapusk-i-host-sessiy.md`, line 38 "Immutable launch boundaries"; `08-curator.md`, line 31 | same; the executing service is OQ9 |
| Total stop | `06-klyuchi.md`, line 122 | same |
| Name latch and synthetic name | none | new (PROPOSED) |
| The single lifecycle table, the held cases, records R01 to R20 | none | new |

## 17. Implementation units

Sizes are in LU: one LU is producer, review, one fix round and landing, about
three hours. The sizes are first estimates and are not calibrated against
delivered units. "Exists" cites what a source of this file shows; nothing was
run and no repository other than this one and the two pinned references was
read.

| Repository | Unit | Exists or new | LU | Depends on | First negative test |
| --- | --- | --- | --- | --- | --- |
| curator-spec | Paired vectors for the cells of section 3 | new | 2 | this file accepted | a start in `running` refuses `station_incarnation_exists`, beside a start in `stopped` that is admitted |
| curator-spec | Action profile naming what the grant carries for a station start | new | 1 | section 9.1 | a start with a changed fixed field refuses `station_plan_changed` |
| curator | Home-lease store and independent observer | contract exists: `protocol/home-leases.md`, `schemas/home-leases-v1/`; implementation new | 3 | none | manager and record agree, the kernel reading differs: bind refuses |
| curator | Liveness reading R06 over the bound incarnation | new | 1 | the unit above; OQ4 | an unreadable kernel field yields `held:live`, never a stop |
| curator | Name latch | new | 1 | the two confirmations of section 9.2 | one changed byte in the name file refuses the start and leaves the file as found |
| curator | Approved-release composition and updater (R12, pin last) | new | 2 | user-manager skeleton interface | an update under a blocking lease refuses with no control changed |
| curator-agent-launcher | Station operations with phases, including `start_requested` | extends the launcher lifecycle record named in C24 "Current state"; new | 3 | curator lease store | a crash after `start_requested` yields `held:start` and no second start request |
| curator-agent-launcher | Start gate set G3 and its refusal mapping | new | 2 | OQ9 | a mismatching digest refuses before provider execution, with no provider child |
| curator-agent-launcher | Session-manager observation, schema v2 | contract exists: HL23; new | 1 | none | an observation without a process tuple cannot bind |
| curator-agent-launcher | Station link admission | bounded model exists: `tools/native_root_admission.py`; new | 1 | OQ10, OQ11 | a legacy credential directory refuses before planning |
| swarma-user-manager | Account writer for create, retire and bump | contract exists: `spec/stations-v0.md`; journal format and offline tools exist: `spec/generation-journal.md`; new | 4 | journal adapter alignment [UM 11] | a replayed create allocates no second identity |
| swarma-user-manager | P1: account-wide absence and the external-object inventory | contract exists: UM 6.1; new | 3 | qualified Linux backend | a double-forked survivor yields `processes_remain` and no release |
| swarma-user-manager | Skeleton install with the reserved name path | contract exists: UM 7; new | 2 | section 8 | a station cannot replace a managed file through its sticky parent |
| swarma-user-manager | Launcher: start receipt, and the digest gate if OQ9 picks B | new | 2 | OQ9 | a second start of one execution is rejected |
| swarma-dispatcher | Standing-runtime mode beside the one-launch budget | new [DF C] | 4 | K1 to K4 | a second start of one station is refused |
| swarma-dispatcher | J1 at every start, with "unavailable" as refusal | one-run admission exists per DF A; new for restarts | 1 | grant contract | an unavailable revocation verdict admits no start |
| swarma-dispatcher | Revocation feed for running stations | new [DF C] | 2 | OQ5, OQ6 | an unknown revocation state never counts as "not revoked" |
| swarma-dispatcher | Claims for the life of a station and reclaim through a stop | new | 1 | OQ8 | a reclaim sends no signal outside a stop request |
| swarma-keymaker | Per-purpose bindings keyed by (uid, generation) and the peer-to-author mapping | contract referenced by UM 6.2; new | 2 | generation journal reader | a process under station A asking to sign as station B is refused before any signature |
| swarma-keymaker | Rotation record R13 | new | 1 | the unit above | a retired name with a new key and no R13 does not enroll |
| swarma-keymaker | Provisioning before `active` for a bump | open in UM 6.2; new | 2 | joint contract with the user-manager | a binding before re-admission refuses |
| swarma-credential-broker and gateway | Service leases and a listener per generation | contract extension unpublished per the book; new | 4 | broker contract extension | a credential sent by the station is rejected; no token reaches the station environment |
| swarma-credential-broker and gateway | Renewal failure closes forwarding; the station idles | new | 1 | OQ7 | a failed renewal forwards nothing and stops nothing |
| a2a-swarm | J2 at the bridge | new | 3 | grant contract | a correctly signed message outside the grant actions is data, never a command |
| a2a-swarm | Station link under one account per station | enrollment exists per C32; new | 1 | OQ10, OQ11, OQ17 | a sender under another account obtains no signature |
| swarma-session-host | Input fence tied to R04; parking on an unready gateway | new | 2 | curator lease store | input before a bound lease is not delivered |
| swarma-session-host | Restart inside a lifecycle permission and budget | new | 2 | OQ3 | a restart without permission is refused |
| task-board | Station element equal to the router snapshot | named in C24 "Implementation plan", leaf 2; new | 2 | shared record version | an assignment to a held station is refused |

## 18. Sources not carried

CIP-0024 sections "Wave 1 project mode", "Host budget" (beyond K9),
"Compatibility and migration" and question 1 of its open questions concern
project-source discovery, heavy-run scheduling and the migration of existing
work places; they are not station lifecycle and are not restated. The
station record fields of the registry (the router snapshot list) stay with
their owners [C24 "Ownership and records"]. Network profiles, resource limits
and the guarantee matrix [BK05] bound a running station and add no state or
event. The macOS station backend [UM 1] is outside the first deployment, a
Linux host.
