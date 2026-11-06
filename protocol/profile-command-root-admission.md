# Native command-root admission: owner decision packet

This is an **unaccepted proposal**, companion to
[profile command roots](profile-command-roots.md). Every root-emission gate
remains **CLOSED**. Each opens only after its named owners accept its resolution;
a model result, this document, a PR approval or an unrelated release is not that
acceptance. No production carrier, config revision or journal number is allocated.
The candidate schemas and vectors below are review instruments only.

The proposed milestone is one non-root Linux OS user, multiple installed profiles,
multiple operator-selected a2a identities, and a native provider launch whose real
tool shell finds that profile's commands on PATH. Qualification is per measured
Linux architecture, not an assertion that both Linux architectures passed.
Hosted delivery through a session manager, project/hybrid selection, Windows and
macOS runtime parity, hooks and gateway naming are deferred. Their future carriers
and witnesses can extend the proposal; none is inferred from a Linux result.
Gateway naming does not gate native root emission.

## Six decisions, no recorded acceptance

| Gate / status | What must be accepted; owners | Concrete proposed resolution | Acceptance still requested |
| --- | --- | --- | --- |
| Joint v5 carrier — **CLOSED** | One whole-object schema and compatibility rule; Curator manager and curator-run carrier/launcher owners | Conditional B-a pair in the sole coordinated v5 schema, retaining all rc7 Codex requiredness; native Linux only initially. See carrier below. | Both owners accept the conditional pair and unsupported-mode refusal; then integrate and qualify the sole schema. Alternative: a coordinated later revision. Recommend the conditional pair because v5 is unreleased. |
| Protected admission policy — **CLOSED** | Policy, provisioning and controlled legacy exclusion; Curator manager and curator-run entry-point owners | Operator-written private policy at `H/state/command-roots/admission.json`, exact admitted images/capabilities, selected lock and controlled writer cohort. Cooperative exclusion, not same-UID isolation. | Accept the candidate policy and operator-controlled native entry point under the fixed single-UID scope. For provisioning, choose operator-installed atomic replacement (recommended), or specify a new operator-authorized policy-management operation; the latter is deferred here. An old binary cannot be compelled to read a new policy. |
| Protected-state locations — **CLOSED** | Inventory, generation/selection/replay/pin stores, preflight and recovery discovery; Curator manager/journal owner, curator-run pin reader | Exact paths and record layouts below; all participate in the existing manager mutation/GC lock and 240-unit preflight. | Accept these layouts, including the session-pin path, and the journal owner's actual staging/backup paths. The hook reference store is not decided here. |
| Session integration — **CLOSED** | Issue/replay operation, revision contract, lease carrier and protected discovery; Curator manager, curator-run launcher/carrier, a2a identity owner for identity handoff | Separate strict JSON acquire response before verification; durable request replay; exact protected pin revalidation; policy-pinned manager. Native operator identity flags scope configuration only. | Accept the request/response/CAS contract below, supervisor observation contract and native identity flag/conflict behavior. A2a owner accepts identity configuration delivery, not an enforcement boundary. |
| Journal coverage — **CLOSED** | Coverage and recovery authority for publication, selection and sessions; Curator manager and journal owner | Named decision `native-command-root-journal-coverage`: dedicated classes for these three transitions, numbers assigned by journal owner. No implicit expansion of 84 or 85. | Journal owner chooses dedicated allocations (recommended) or explicitly extends existing classes with target/recovery rules. Manager owner accepts the resulting atomic plan. No number is requested by implication. |
| Native runtime witnesses — **CLOSED** | Actual Linux publication, launch, identity, restore, supervision and failure evidence; Curator manager/journal, curator-run launcher, a2a identity owners | Witness matrix below, including real tool-shell PATH and identity. No witness has been performed by this spec PR. | Owners accept the matrix and resolve `native-witness-bootstrap`: authorize a fenced, non-adoptable implementation/witness lane (recommended), or retain the implementation prohibition and leave this gate blocked. Production emission stays closed until witnesses are accepted. This proposal grants neither option. |

The checked implementation seams are Curator manager
[`163c2e98`](https://github.com/relux-works/curator/blob/163c2e98bd5d9596dca1f51f73b8f4393e8101b8/internal/envprofile/skill_projection_plan.go)
(unconditional companion-adoption refusal) and launcher
[`2045339f`](https://github.com/relux-works/curator-agent-launcher/blob/2045339f703ee8190705c116a05197b12b684b71/internal/fragment/fragment.go)
(v1–v4 reader). The launcher also currently rejects native identity flags.
These observations explain missing work; they are not an accepted implementation
or witness. The existing global shim/routing publication is not a B-a generation.

## Candidate carrier integration

The recommended joint schema adds the existing B-a `command_root` definition to
rc7 v5 and makes `command_root` and `path_prepend` required together. Neither is
required when neither is present. Bare v5 `path_prepend` is refused in this
candidate. All other rc7 members, unknown-member refusals, typed Codex policy
requiredness and pre-emission consumer support requirements remain intact. Do not
replace every inherited absolute-path definition with the Windows model. Native
Linux paths use the inherited grammar; Windows root emission remains unadmitted
until a coordinated Windows schema and witnesses are accepted. No-command profiles
keep their existing behavior and gain no B-a claim.

This is a candidate composition in `native_root_admission.py`, not an alternate
normative whole-object schema. The released v1–v4 tokens remain unchanged and
`path_prepend` remains inert there. Old launcher + new manager refuses v5; new
launcher + old manager refuses before invocation through the policy. No downgrade,
empty-root substitute, ambient fallback or implicit capability inference.

## Candidate protected paths and records

Let `H` be the canonical manager home, `P` the validated profile name, `G` a fresh
64-hex materialization identity, `L` a 64-hex lease ID and `R` a durable 64-hex
request ID. The manager is the sole writer of operational records; the operator
alone provisions/updates admission. Every parent is private and no-follow checked,
directories mode 0700, records mode 0600, same non-root owner. Symlink, foreign
owner, unknown/corrupt record and escaping component refuse without mutation.
These are cooperative integrity checks against accidental substitution, not
protection from a malicious process with the same UID.

| Object | Exact candidate location | Closed record content / authority |
| --- | --- | --- |
| Inventory | `H/environments/P/commands/G/platform/inventory.json` | Existing `profile-command-inventory/1`; command chains and local object identities, pinned by receipt and external state. No search/discovery heuristic. |
| Generation state | `H/state/command-roots/g/G.json` | Candidate generation record: `profile`, full seven-field `binding`, exact `root` and `inventory` paths. Immutable; full G globally reserved under manager lock. Existing receipt/marker/inventory pins and source/build evidence remain authoritative. |
| Selected generation | `H/state/command-roots/selected/P.json` | Candidate selection record: `profile`, full `binding`, monotone `revision`. Lock 5 does not alone identify a materialization G; selected lock and this pointer must agree. CAS update in the publication/routing transaction. |
| Session pin | `H/state/command-roots/sessions/L.json` | Existing proposed `profile-command-session-pin/1`. Exact pin/revision is checked through the admitted manager, never selected by a provider. |
| Request replay | `H/state/command-roots/requests/P/R.json` | Candidate replay record: canonical full `request`, issued full `pin`. Written atomically with pin before acknowledgement; duplicate exact requests return the same issued pin, never latest G. Terminal records remain for conflict detection. |
| Admission | `H/state/command-roots/admission.json` | Candidate policy below. Not generated by packages, a profile, provider or manager auto-upgrade. |

The [candidate schema](../schemas/profile-command-roots-v1/native-admission-proposal.schema.json)
closes the policy, generation, selection, acquire and replay records. Candidate
record discriminators are deliberately prefixed `candidate/`; they are not wire
allocations. If accepted, the owners must allocate their production names and
integrate them into the sole normative schemas before implementation admission.
The full pin response is the already proposed session-pin record, not an extra
lease field silently added to rc7 or the existing resolve argv.

The inventory path is shorter than the already bounded root receipt. For Linux,
the inventory overhead is 115 bytes beyond `len(H)+len(P)`; generation state is
92 beyond `len(H)`; session pin is 99 beyond `len(H)`; replay is 100 beyond
`len(H)+len(P)`. The candidate path validator computes all paths rather than
trusting these explanatory constants. The receipt bound `H+P <= 101` on Linux
therefore fits inventory, generation, selected, replay and session records within
240 bytes. In the existing cross-platform model the export budget remains
`home+profile+export <= 135/134/129` and receipt `home+profile <= 101/100/99`
for Linux/macOS/Windows, including Windows UTF-16 units. These bounds do not
admit runtime parity. A 64-character profile and arbitrary long home cannot both
be promised: preflight refuses the actual combination before any writes.

Every journal live, staged, backup, reservation and replay path must also pass
the same actual 240-unit check before the transaction writes anything. No journal
layout is guessed here: accepting the named journal decision must provide these
paths and a longest-path vector. Until then the locations and journal gates stay
closed despite the candidate final paths fitting. No unhashed external inventory
or nested fallback store is permitted.

## Candidate policy and controlled entry point

The closed policy has `record`, monotone `revision`, canonical `manager_home`,
nonzero numeric `uid`, `entry_point`, `writer_cohort`, pinned `manager` and
`launcher` images, and `profiles`. Each image contains absolute `path`, raw-byte
`sha256`, signed `distribution_sha256` and exact capability `profile-command-roots-v1`.
A profile entry contains `profile`, `lock_sha256`, `required: true`. The entry
point contains its absolute `path` and `legacy_excluded: true`; writer cohort is
exactly `operator-controlled`. The booleans describe an operator obligation and
must be witnessed; they are not evidence that a legacy executable was fenced.
Policy revision is CAS-updated by the operator through private atomic replacement;
a changed manager/launcher image or selected profile lock requires an explicit
operator update. Unknown/duplicate entries, stale locks and unsupported policy
refuse before manager invocation or provider start, without rewriting policy.

The operator selects the home and invokes this controlled entry point. The new
launcher reads the fixed private policy location, verifies home/UID and admitted
image/distribution pins against operator installation trust, then invokes the
policy's absolute manager image. It never searches PATH, provider homes, siblings
or environment overrides for a manager. Packages cannot nominate their own trust
anchor. Admission and the launched tools' manager access must use this same
protected discovery. An operator can run a different legacy binary under the
same UID; that route is explicitly outside qualification. If the operator cannot
exclude legacy entry points from this workflow and writer cohort, activation
refuses. OS-enforced isolation is outside the fixed single-UID milestone and is not
supplied by mode 0600. The decision requested here is the policy provisioning
contract, not a reconsideration of identity enforcement or the OS-user scope.

## Candidate native acquire, replay and identity

Proposed manager operation: the policy-pinned absolute manager executable runs
`profile command session acquire --format json`, with one strict, duplicate-key
rejecting UTF-8 JSON request on stdin and no trailing record. This is a proposed
new operation, not a claim about current CLI support. The closed candidate acquire
request contains `record`, `request_id`, `profile`, full `binding`, `supervisor_instance`,
`boot_id`, `process_domain`, `process_started_at`, `if_revision: 0`. Unknown fields,
wrong profile/selected binding or an unverifiable supervisor incarnation refuse.
The launcher persists R before its first call. Manager reserves L, verifies the
request against selected protected state and supervisor proof under its existing
mutation/GC lock, and journals request + active revision-1 pin before returning the pin.
For this native proposal the supervisor establishes its domain before acquire;
there is no separately allocated activate operation.
The pin is a GC edge before full byte verification starts.

Under the manager lock, replay lookup by R precedes current-selection checks;
only a new R is subject to new issuance against the current selection.
On exact replay of R, the full canonical request must equal its durable preimage:
return the originally issued pin and revision, even after a newer generation is
selected. A different payload under R is `session-request-conflict`, no writes.
A terminal/released or unknown pin returned by replay does not authorize another
start. Request replay must not create a second L, refresh the incarnation, renew
liveness or retarget to current G. Proposed cap: 4096 request/terminal records and
256 retained roots per profile, no TTL eviction; new IDs past the cap refuse,
known exact retries still work. Fenced epoch maintenance remains a future explicit
operation, not an automatic reset.

The response delivers L and every pin field directly to the launcher before
verification. The launcher checks request identity, revision, supervisor instance,
boot ID, domain, start incarnation, profile and full binding against its durable
request and a fresh protected manager observation. A response cannot be its own
authority. Before spawn it repeats the metadata/object-identity boundary checks
and asks the same manager for `profile command session check --format json`,
stdin `{lease_id, if_revision, request_id}`; this proposed read returns the exact
active protected pin or refuses. Acquire issues active revision 1 only after the
supervisor domain is established and verified. Exact acquire replay is read-only;
phase changes increment revision by CAS. A stale revision, different request or
incarnation is an intended refusal, not a new lease. Same-UID check/use mutation remains outside the contract.

Release uses the exact lease/request/revision and an admitted supervisor's confirmed
quiescence of the whole domain. Loss of observer, PID reuse or missing proof
marks unknown and retains the edge; wall clock and a dead leader alone do not
release it. Break additionally requires explicit operator action, proven domain
fencing, current revision, nonempty reason and durable audit before terminal state.
Check never mutates; failed acquire/release/break leaves pin, replay record and
retention edges unchanged. Exact terminal retries are idempotent only against
the recorded request/revision transition; no restoration of active authority.
Supervisor/kernel evidence acquisition and durability still need native witnesses.

Proposed native identity flags are explicit operator inputs `--a2a <identity>` and
`--a2a-config-dir <absolute-directory>`. A qualified identity launch supplies both
flags together; a half pair refuses before manager invocation. Neither flag keeps
the inherited environment without a new identity-delivery claim. Identity syntax
and actual configuration loading remain owned by a2a. Conflicts with inherited `A2A_*` values
refuse; identical values may pass. Without flags, existing inherited values pass
through without inventing an identity. With flags, the launcher supplies the
selected `A2A_AGENT` and `A2A_CONFIG_DIR` to the launched agent and its actual tool
shell. Provider session IDs are not manufactured. The a2a owner must accept the
identity/config contract and image-identity interaction with byte-identical named
copies. One UID means configuration scoping only: agents can read/change each
other's configuration. There is no identity enforcement or secret isolation claim.
Native flags do not install a hosted doorbell or hooks. Codex tool-shell environment
policy, including `inherit=core`, needs a real launch witness; parsing flags alone
cannot show that the agent's commands or identity survive that boundary.

## Journal decision and native witnesses

For `native-command-root-journal-coverage`, the recommendation is dedicated named
classes `profile-command-root-publication`, `profile-command-root-selection` and
`profile-command-root-session`; **numbers are for the journal owner to assign**.
Publication covers immutable tree, inventory, marker, receipt and generation
state. Selection covers the selected pointer and lock/routing transition in one
outer transaction. Session covers pin + replay creation, phase/revision transition,
terminal replay and permanent break audit. Existing `84-profile-generation` and
`85-profile-routing` publish global runtime and routing today; that is not authority
to include these targets. Alternative: explicitly extend their target whitelists
and recovery contract if the journal owner chooses. Hook references/settings are
separately gated and are not part of this native request.

For each covered transaction, preparing/rollback yields all old preimages;
prepared/committing/cleanup yields a complete new postimage; an unknown journal
preserves its evidence and refuses. No partial live tree/pointer, acknowledged
undurable pin, lost replay entry or premature GC is allowed. The owner must choose
actual staging/backup paths and demonstrate every crash phase and same-request
restart before accepting coverage. The existing in-memory phase model does not
qualify filesystem durability.

`native-witness-bootstrap` is a real unresolved admission decision: actual runtime
witnesses need code, while the current rule forbids implementation before all six
gates open. Recommend an owner-authorized, fenced witness-only implementation lane
with no production root emission, capability release or adoption. Alternative:
keep the prohibition and this gate closed until another already admitted route
can produce those witnesses. Accepting a witness plan alone must not be described
as actual execution. This spec PR implements neither option and authorizes no
exception. The owner must decide before implementation begins.

The owners are asked to accept this minimum witness matrix, then actual receipts:

| Native witness | Required observation and negative control |
| --- | --- |
| Real launch and identity | Two profiles with different sentinel command bytes, two operator identities/config directories, one non-root UID. Real provider tool shells run commands found through the forwarded profile PATH and report the selected a2a identity. Wrong inherited identity refuses; no ambient decoy executes. Include Codex shell policy where claimed. |
| Carrier/admission age pairs | Every old/new manager/launcher pair, stale/missing/corrupt policy and unsupported mode: named refusal, zero provider starts, unchanged protected state; admitted pair actually starts. |
| Verification and publication | Published native IDs and all byte pins; tamper each selected object, equal-byte object substitution, ambient decoy and deadline exhaustion refuse before start. Valid control launches; report byte counts, shape, monotonic latency and architecture against the 10-second bound/qualification targets. |
| Retention and restore | G1 live while G2 runs; pinned repeat still launches G1. Explicit repair creates G3 from identical immutable inputs, preserves G1 and every live edge, never retargets. Unknown old session refuses restore until proven quiescent or explicitly fenced/audited; valid reconciliation succeeds. GC union and no-write failures observed on real stores. |
| Supervision and journal | Manager/observer loss, surviving descendants, reused PID/start and boot/domain changes retain unknown edges and refuse stale start/release. Proven domain quiescence releases; fenced operator break is audited. Crash/restart every assigned journal phase, including acquire/replay and selection, has complete old/new state and exact replay. |

Receipts must bind exact manager/launcher/a2a revisions, schema/model revisions,
platform/architecture, non-root ownership, commands and exit statuses, and show
post-refusal state. Sanitized logs must preserve the distinguishing evidence.
No receipts from a different head, hosted empty decision, prepared lock, global
shim publication or a parser-only test substitute for this matrix.

## Bounded model closure and limits

A9 is closed **in the model** by independent protected pin authority comparisons
in both launcher and session checks: lease/request/revision/supervisor/boot/domain/
start/phase fields each have a named refusal vector. A valid revision advance updates
both pin and independent authority as a positive control; editing the pin alone
refuses. This does not prove how an OS observer obtains that authority.

A10 is closed **in the model** by distinct restore inputs: no edge, a live old-G
session edge, and an unknown old-G session edge. Unknown refuses unless confirmed
quiescent or explicitly fenced by an operator with revision and durable audit.
A successful restore preserves the old edge and evidence verbatim and creates
fresh G; it does not migrate an old session. Dropping or retargeting that edge
refuses with unchanged preimages. Reconciliation/break permits repair but this
projection conservatively retains the old record; separate confirmed terminal
release/GC handles reclamation. Native durable reconciliation remains a witness.

Named positive/negative vectors and guard plants live in
[test_native_root_admission.py](../tools/test_native_root_admission.py) and the
[command-root corpus](../conformance/profile-command-roots-v1/README.md).
Their candidate policy checks prove shape and authority consistency, not signed
installation trust, legacy exclusion, real supervisor observation or runtime
identity. Every such missing witness keeps its corresponding gate closed.
