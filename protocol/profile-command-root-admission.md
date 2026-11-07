# Native command-root admission: owner decision packet

This is an **unaccepted proposal**, companion to
[profile command roots](profile-command-roots.md). All seven root-emission gates
remain **CLOSED**. Only their named owners can accept resolutions. This packet,
model checks and PR review record no acceptance, production names, journal numbers
or runtime receipts. Gateway naming remains open and independent.

## What the owner decides

- **Carrier:** recommend one coordinated version-5 manager/launcher message for
  Slice B-a (immutable named command roots), preserving the existing Codex contract.
  Allocate a launch record for sessions without pins; older pairs refuse.
- **Milestone and session integration:** recommend **operator prune, no automatic
  command-root garbage collection (GC)**. Keep native discovery, verification and
  identity delivery; give up automatic reclamation, a disk bound and A9/A10
  (pin-authority and restore-model checks) for now. Alternatively say “choose full
  pins”: supervision, request retirement and qualification come first. Pins stay additive.
  Incorrect prune can break a running lane's next tool call, silently select a
  command from base PATH, or make it go dark when its root holds `a2a`; the operator
  receives no warning from prune. There is no process-safety claim.
- **Companions:** recommend native scope for `profile-command-admission` and
  `managed-session-skill-cli`. Protected-name inventory and base-PATH checks remain
  substantial work. Hosted delivery is deferred: `curator-run werkstatt up` and
  hosted launch get no profile commands in this milestone; a keeper uses the direct
  native route, owns restart and arranges wake-ups through a2a hooks. This is the
  accepted delivery scope, not acceptance of these still-closed gates.
- **Policy:** recommend one explicit operator command under the manager lock with
  compare-and-swap (CAS: reject if the current revision differs from the expected
  one). It updates policy, lock and selection together; install and auto-upgrade
  never invoke it. Launches refuse until the operator acts: an auto-upgrade or
  profile update stops every launch on an unattended host until the operation runs.
- **State locations:** recommend the inventory and selection paths below and
  explicit migration of existing private directories. Pins add one session store;
  journal staging and backup paths still need owner acceptance.
- **Journal:** recommend two dedicated classes, publication and selection; reject
  extending existing `84-profile-generation` and `85-profile-routing` transactions.
  The journal owner assigns numbers and accepts inode preservation and crash
  evidence. Pins use one atomic record, not an engine transaction per launch.
- **Witness gate:** accept the matrix for implementation behind the fence below;
  accept actual receipts separately for emission and adoption. No receipt is claimed.

The scope is one non-root Linux OS user with several profiles and a2a identities.
A second agent under that same user can read and use the first agent's a2a access
credentials and rewrite policy; “protected” means cooperative integrity, not
isolation. Qualification is per measured Linux architecture; project/hybrid,
macOS/Windows runtime parity and hook command activation remain deferred.

## Seven decisions, no recorded acceptance

| Gate / status | What must be accepted; owners | Proposed resolution and acceptance still requested |
| --- | --- | --- |
| Joint v5 carrier — **CLOSED** | Curator manager and curator-run carrier/launcher | Accept a conditional B-a pair in the sole coordinated v5, preserving rc7 Codex requiredness and explicitly allocating unpinned provenance. Native Linux only initially; alternative is a later coordinated revision. |
| Protected admission policy — **CLOSED** | Curator manager and curator-run entry-point owners | Accept explicit manager-home input, pinned image bytes, selected locks and operator attestation; explicit policy operation with lock/CAS, never install or auto-upgrade. |
| Protected-state locations — **CLOSED** | Curator manager/journal and curator-run reader | Accept inventory and selected locations, scoped private-parent migration and actual journal staging/backup preflight. Pins alternative adds one session store; no replay tree or extra generation store. |
| Session integration — **CLOSED** | Curator manager, curator-run launcher/carrier, its skill-agents-management argv plugin owner and a2a identity owner | Recommend no process-pin operations for the no-GC milestone; accept protected discovery, boundary verification and native identity delivery below. Full pins instead needs the explicitly open supervision/retirement design. |
| Journal coverage — **CLOSED** | Curator manager and journal owner | Accept two dedicated publication/selection classes, target level and crash layout; assign numbers separately. Copying staged files changes inventory inode pins, so existing engine staging is insufficient. |
| Native runtime witnesses — **CLOSED** | Curator manager/journal, curator-run launcher and a2a owners | Accept the matrix for fenced implementation, then actual receipts for emission/adoption. No receipts are claimed here. |
| Companion admission — **CLOSED** | curator-spec, Curator command-publication, curator-run; hosted manager for whole-companion scope | Accept native scope for `profile-command-admission` and `managed-session-skill-cli` (recommended), or accept the whole companions. B-a alone does not satisfy the first; explicit native qualification must satisfy the second. |

## Source seams and companion scope

Read at Curator
[`163c2e98bd5d9596dca1f51f73b8f4393e8101b8`](https://github.com/relux-works/curator/blob/163c2e98bd5d9596dca1f51f73b8f4393e8101b8/internal/envprofile/skill_projection_plan.go):
`RefuseSkillPlanAdoption` unconditionally names both companions.
[`skillruntime/admission.go`](https://github.com/relux-works/curator/blob/163c2e98bd5d9596dca1f51f73b8f4393e8101b8/internal/skillruntime/admission.go)
requires `CommandChecks.Inventory` and `BasePATH`; an interface is not a production
implementer. The [companion requirements](profile-skill-plan-proposal.md#required-companion-allocations)
remain applicable. Recommended narrowed work still includes a versioned protected-name
inventory with pinned aqua/mise registry inputs, POSIX/coreutils, shell builtins
and Linux platform names, provenance/completeness/upgrades and target alias rules.
It independently checks every export against the admitted destination base PATH,
including protected names absent there; unknown/unreadable evidence refuses.
The operator supplies the destination base PATH in the policy operation for
publication checks; its retained admission evidence (format to allocate with the
companion) supplies the launcher's comparison source. At launch, reclassify it
using [PATH section 3](profile-command-path.md#3-path-construction-and-admission)
and refuse on a difference. B-a does not use Slice A's `Supervisor`, `Domain` or
routing admission: immutable named roots remove the singleton routing they protect.
Paired vectors include `git`, `ls`, `sh`, `cd`, registry/platform names, aliases,
dynamic-only collisions and ordinary names, preserving preimages. Curator owns
the production checker; spec owners allocate its contract. This is M to L work,
not deletion of the refusal. Whole-companion adoption is the named alternative.

For `managed-session-skill-cli`, accept native current/all-profile verification,
PATH admission and per-launch provenance, no-export behavior and final-tool-shell
witnesses. Hosted active delivery and its joint manager carrier remain closed;
existing hosted unavailable-command behavior is unchanged. B-a supplies the native
immutable-root design, but neither a design nor a prepared lock qualifies adoption.

Launcher
[`2045339f703ee8190705c116a05197b12b684b71`](https://github.com/relux-works/curator-agent-launcher/blob/2045339f703ee8190705c116a05197b12b684b71/internal/fragment/fragment.go)
reads v1–v4; parsed `path_prepend` has no native consumer yet. `--a2a` exists
for hosted doorbell wiring and route selection, and is refused on native launches.
`--a2a-config-dir` is new proposed syntax. These are missing implementation seams,
not runtime evidence. Existing global shim publication is not B-a materialization.

## Candidate carrier integration

Add `command_root` and `path_prepend` together to the sole coordinated rc7 v5;
neither is required when neither is present. Bare v5 prepend refuses. Preserve
all other rc7 ownership, unknown-member and typed Codex policy requirements.
The candidate model restricts B-a to Linux; it leaves the inherited path grammar
intact. No-command profiles retain existing behavior and gain no B-a claim.
The no-GC choice also needs an explicitly unpinned provenance variant; the current
closed launcher-state schema still requires a lease. This is part of joint-carrier
acceptance, not permission to invent one. Candidate composition is a review
instrument, not another normative carrier.
Released v1–v4 and their inert prepend stay unchanged. Unsupported old/new pairs
refuse without downgrade, empty-root substitute, ambient fallback or inferred capability.

## Candidate protected paths and records

`H` comes from an explicit operator-supplied canonical absolute manager-home
launch input, outside profile/provider data. Its presence selects the B-a-required
workflow **before reading policy**. The controlled workflow always supplies it;
a missing/corrupt policy then refuses, even when all state under H disappeared.
Without that input the launcher may use its existing legacy resolution, but that
route is unqualified for B-a. A B-a pair on a route without H refuses.
It never infers legacy permission from missing policy.
This input is proposed, with production syntax still for the carrier owners;
it is not a claim that today's launcher has such a setting. `CURATOR_CONFIG`,
ambient PATH or a provider cannot override the pinned manager once selected.
The launcher sets the manager's home from H; a conflicting inherited
`CURATOR_CONFIG` refuses.

`P` follows the existing profile grammar (including `Work.1`); `G` is fresh 256-bit
materialization identity. The manager writes operational records; the launcher
writes its per-launch provenance. “Protected” has the single
[cooperative definition](profile-command-roots.md#protected-state-definition).
H itself and private state parents below H are no-follow checked, same-owner mode
0700, and
records mode 0600. Ancestors above H need not be operator-owned or 0700; their
route must still reject symlink substitution. Existing manager-created 0755
parents below H require explicit operator migration under the manager lock:
validate ownership/no-follow, narrow permissions without deleting contents,
revalidate, then enroll. Wrong owner, links or failed migration refuse enrollment;
install/launch do not silently chmod an existing home. Existing shared ancestors
below H are included in that migration, not exempted by being old.

| Object | Exact candidate location | Authority |
| --- | --- | --- |
| Inventory | `H/environments/P/commands/G/platform/inventory.json` | Existing inventory, command chains and native IDs, pinned by receipt/marker and selected binding. |
| Selected generation | `H/state/command-roots/selected/P.json` | Full seven-field binding, profile and monotone revision, coherent with policy's selected lock. CAS with selection/lock/routing. |
| Admission | `H/state/command-roots/admission.json` | Candidate operator policy, never auto-provisioned. |
| Launcher provenance | `${XDG_STATE_HOME}/swarma/launcher/` (fallback `${HOME}/.local/state`) | Full pins uses per-launch `launcher-path-state/2`; the recommended unpinned variant still needs allocation, per [path provenance](profile-command-path.md#4-provenance-and-witnesses); launcher-owned, no admission authority. |
| Session (pins alternative only) | `H/state/command-roots/sessions/R.json` | One atomic record containing canonical request, full pin and terminal audit; R is a fresh 64-hex session/request ID and the proposed lease ID is the same R. |

No `g/G.json` is needed: selected state already holds the external binding; the
receipt/marker/inventory remain authoritative and G is randomly reserved with
exclusive creation under the manager lock. Retained generations keep those
immutable records; no generation may overwrite a prior G. No `requests/` tree:
the session record is also the replay record. Pins add retention edges later
without replacing roots, selection or receipt formats. Before enabling automatic
GC, drain unpinned lanes or obtain operator attestation that they are stopped;
lanes started before pins have no retention edge.

All actual live, staged, backup and journal paths must pass the existing
240-unit preflight before writes. Inventory adds 115 Linux bytes to H+P;
selected adds 35; optional session adds 99 to H. Receipt H+P limits remain
101/100/99 and export H+P+export limits 135/134/129 for Linux/macOS/Windows,
with Windows UTF-16 units. Cross-platform arithmetic is no runtime admission.
Actual path computation, not constants, governs refusal. Journal layout still
needs owner acceptance and longest-path vectors; final-path fit does not open it.

## Candidate policy and controlled entry point

The candidate token is `candidate/native-root-policy/1`, distinct from the
`profile-command-admission` companion. Its closed record has revision,
manager_home, nonzero uid, manager/launcher absolute paths and raw-byte SHA-256
pins, and profile/selected-lock entries. Shared definitions use `$defs`.
No distribution digest is proposed without a signer, manifest and verifier.
`entry_point`, `legacy_excluded`, `writer_cohort` and image `capability` constants
are removed: constants prove no exclusion or capability under one UID.

The operator attests that legacy entry points are excluded from this workflow and writer cohort. Without that attestation, the manager MUST refuse activation/emission for that home. Running the operation with explicit operator intent is that attestation; a valid current policy is its evidence.
Packages must not nominate admission authority; package/profile/provider data is
not read as an authority source. Their code can nevertheless rewrite policy under
the same UID. A second agent under that UID can read and use the first agent's
a2a credentials, including access tokens and passwords. This limit is accepted;
0600 and `A2A_CONFIG_DIR` provide configuration scoping, not identity enforcement
or secret isolation. Legacy binaries outside the controlled workflow are unqualified.

Operator is a role, not a credential: on an unattended host, the keeper or
provisioning step acting for the owner, under the same UID, unauthenticated.
Bootstrap: (1) install manager/launcher binaries in the user's local bin and hash
actual image bytes; (2) choose H, validate private parents and migrate existing
ones; (3) install the profile and prepare its lock; (4) explicitly enroll with
`if_revision=0`, image pins, base PATH and that lock digest; (5) that same command
publishes and selects.
Updating policy, lock and selection is one operator command.

Recommend a new small explicit operator-invoked manager operation (S to M),
never invoked by install or auto-upgrade. Under the existing manager lock it
reads current policy revision (absence is revision 0 only for explicit initial
enrollment), compares it to the operator's `if_revision`, compares every proposed
profile lock to the intended selected-lock postimage, and writes revision N+1
by same-directory atomic replacement, file fsync and directory fsync. A mismatch
refuses unchanged. Selection/lock/routing and any authorized policy-lock update
share the outer selection transaction; ordinary updates cannot change the
allowlist and refuse if operator authorization is needed. Image changes need
explicit operator input. Never infer authorization from a new binary's presence.
The alternative is dropping policy lock pins and relying on selected state;
that changes the normative binding contract and needs separate owner acceptance.

The launcher compares canonical H and current UID to policy, selected profile and
lock to its policy entry, and actual manager/launcher image bytes to their policy
SHA-256 pins. It invokes that exact absolute manager, with no PATH lookup.
The observed revision is rechecked at the spawn boundary; a concurrent policy or
selection change refuses. These comparisons establish consistency with the
operator-provisioned policy, not signer provenance or same-UID security.

## Candidate native acquire, replay and identity

**Recommended operator-prune variant:** there is no acquire/release/request cap
or process-domain contract. Automatic command-root GC is disabled, including on
update, remove, rollback, repair and startup. Roots, their receipts and dependent
artifacts remain until explicit operator prune. Prune takes the manager lock,
requires explicit operator attestation that affected users/descendants are stopped,
and refuses selected, snapshot/resume, rollback, pending-journal or hook-reference
edges. If that attestation is wrong, Linux keeps already-running images alive,
but the lane's next tool call may fail or silently fall through to a same-named
base-PATH command added after admission; only the agent sees failures, and nobody
is warned about the silent substitution. If the root holds `a2a`, the lane cannot
post/read mail and goes dark until someone notices silence; prune reports success
without a running-lane refusal, warning log or signal to the operator.
There is no disk bound. No pin is fabricated to satisfy existing pin-shaped models
or provenance: the later accepted schema must explicitly represent the unpinned
variant, and production readers must reject it until allocated. Verification of
bytes, selection and object identities at the final spawn boundary still applies.
Supervision and request exhaustion fall away in this variant. A9/A10 remain
future pins-model checks, not requirements claimed satisfied for the milestone.

**Named full-pins alternative:** acquire/check/release/break would use one session
record at R, atomically renamed and directory-fsynced under the manager lock;
no engine journal or duplicate replay record. Exact canonical request replay returns
the same recorded pin, never current G. An altered request refuses; terminal or
unknown replay never authorizes start. Request/pin revision and supervisor/boot/
domain/start fields are compared with the launcher's retained request and a fresh
manager observation. Manager-sourced lease/revision/phase are not independent trust.
R is kept in launcher memory for same-process retries. It is not crash-resumable
launcher authority; a restarted launcher uses a new R and old sessions require
reconciliation. `prepared` is deliberately retained in the general pin schema for
future activation; this proposed alternative issues `active` revision 1 only.

This alternative **still needs design**, before acceptance: non-root Linux domain
observation (for example subreaper plus `/proc`, with escape/observer-loss handling),
the writer of `unknown`, release/break operations and live detached a2a descendants.
Do not assume cgroup delegation, root or a dead leader proves quiescence.
Size L, a multi-PR supervision/qualification cycle. It also needs bounded terminal
request retirement and prior-boot reconciliation with a conflict-preserving epoch
route after any cap (M to L). There is no admitted permanent 4096-launch limit or
silent TTL/reset. The candidate session schema models active issuance/replay
only; terminal audit/transition postimages remain part of this alternative
design work. Hook request-epoch maintenance remains separately CLOSED.
Selecting full pins requires those designs and witnesses, not acceptance of an
empty supervision promise.

**Lock availability:** source `prepareSkillPlan` holds the manager-home lock across
build preparation; `lockTimeout` is 30 seconds. Policy/selection and pins-alternative
acquire can therefore refuse during another profile's build. No latency guarantee
or unlocked bypass is promised. The operator-prune launch avoids acquire but any
required locked observation can still contend. This is source reading, not timing.

Native identity launch requires explicit native route selection (`--native`),
`--a2a <identity>` and proposed new `--a2a-config-dir <absolute-directory>` together.
Half-pair refusal applies **only to this native route**. Existing hosted `--a2a`
alone, hosted doorbell and route selection remain unchanged. The launcher's own
identity syntax validation remains a precondition; a2a owns loading/identity semantics.
For native explicit identity, compare exactly `A2A_AGENT` and `A2A_CONFIG_DIR`:
nonempty differing inherited values refuse, identical or empty/unset values pass.
An orchestrator launching another identity must scrub its own pair first.
Other `A2A_*` variables are not silently described as covered by this two-key check.

For every **new native session**, remove inherited `A2A_SESSION_ID`,
`CODEX_THREAD_ID` and `CLAUDE_CODE_SESSION_ID` before provider start, with or without
identity flags; never invent
replacement session IDs. The new runtime supplies its own metadata. This follows
a2a's documented session rule (`docs/cli.md`, source revision
`f8b88dd425ccc65f0f3f8324e92d081570486d81`), including its Claude bind/lease
selector. Whether Claude Code overwrites an inherited selector is unverified.
Without identity flags the identity/config pair passes through without a new claim.
For Codex `inherit=core`, propose a launcher-owned per-launch `-c` block setting
`shell_environment_policy.set.A2A_AGENT` and `.A2A_CONFIG_DIR`, separate from
`codex_settings`; identity is not a lock property or a vocabulary extension.
The launcher and its skill-agents-management argv plugin owner must coordinate
this block, without mutating shared daemon configuration.
The final tool-shell keys must match this selected pair. This carrier integration,
PATH survival through shell startup and provider settings precedence are **W0 open
questions** for real Claude/Codex tool shells on Linux. In particular settings
`env.A2A_AGENT` can bypass a parent-env check: a conflict must refuse or be prevented
by accepted per-launch precedence, then witnessed. No parser/model supplies W0.
An external keeper reports a limited Codex 0.166.0 observation in a clean account
with mock transport: default inherit kept `A2A_*`, `inherit=core` removed them,
and plain `login=true` produced a nonlogin shell. `set` delivery is still being
shown; this is not a qualified witness. The **W0 tool-shell delivery** row is awaited.
Native flags install no doorbell or hooks. The a2a image guard across generations
remains unchanged and needs the matrix controls below.

## Journal decision and native witnesses

Recommend exactly two dedicated classes, publication and selection; the journal
owner assigns their names/numbers. Extending `84-profile-generation` or
`85-profile-routing` is rejected: their lock-keyed generation file and routing
file scopes stay unchanged. Publication targets `environments/P/commands/G`
(**not** P or the whole commands directory); inventory, marker and receipt are
inside that target. Selection covers pointer/lock/routing and authorized policy
postimage in one outer transaction with publication. The inode problem is
real: current transaction staging copies files into sidecars, creating new native
IDs. Owner acceptance must include inode-preserving install or inventory/pin
construction after the final staging copy, before commit, and crash recovery
that keeps those same IDs. Hashing a pre-copy tree does not qualify.

Journal owner supplies actual live/stage/backup layout and longest-path vectors.
A G-level target keeps per-platform inventory/receipt suffixes within the path
budget; a profile-level copy needlessly duplicates the long suffix. Each phase
must restore complete old preimages or complete new postimages; unknown journals
preserve evidence and refuse. Pins alternative atomically updates one session
record including request, pin, prior transition and audit; its atomic durability
still needs crash receipts, but no third engine class is requested.

Gate six has two acceptance steps: an accepted matrix admits implementation;
accepted runtime receipts admit emission and adoption. **The implementation fence**
is: retain production `RefuseSkillPlanAdoption` until receipts are accepted;
use disposable HOME only; use candidate tokens refused by production readers;
claim no released capability; create no journal in a real home. This single fence
replaces the separate `native-witness-bootstrap` exception lane. It does not open
any gate in this PR or allocate production schema. Accepted normative allocations
still precede production implementation of those contracts.

| Native witness | Required observation and negative control |
| --- | --- |
| W0 tool-shell delivery | Real Claude and Codex Linux tool shells: profile PATH survives startup; Codex `inherit=core` receives selected identity/config. Settings `env.A2A_AGENT`/config override conflict is prevented or refuses; valid matching settings work. Record actual precedence and carrier, not parent env alone. |
| Real launch and identity | Two profiles with different sentinel bytes, two identities/config directories, one UID. Actual tool shells find selected commands and report selected identity. Nonempty inherited conflict refuses; empty values pass. New sessions never reuse inherited `A2A_SESSION_ID`/`CODEX_THREAD_ID`/`CLAUDE_CODE_SESSION_ID`; valid runtime-owned metadata works. No ambient decoy executes. |
| a2a image guard across generations | Same identity/config root across old/new a2a images retains today's refusal; nearby distinct identity or config-root controls behave as current a2a permits. No claim that byte-identical named copies bypass the guard. |
| Carrier/admission age pairs | Every old/new manager/launcher pair, explicit H with missing/corrupt/stale policy, unsupported mode, policy CAS mismatch: named refusal, zero starts, unchanged state; admitted pair starts. Hosted `--a2a` alone still works, native half pair refuses, valid explicit native pair passes syntax validation. |
| Verification and publication | Tamper bytes, substitute equal-byte native objects, ambient decoy or exhaust deadline: zero starts. Valid control launches. Report shape/bytes/architecture and monotonic latency against 10-second bound and qualification targets. Inventory identities survive final journal staging. |
| Retention and restore, operator prune | G1 remains while G2 runs; identical-input repair creates G3 and preserves G1. Update/startup never automatically collect old roots. Operator prune refuses without stop attestation or with retained protected edges; explicit stopped/unreferenced control prunes. Disk growth is disclosed. No process-pin safety claim. |
| Journal crash/restart | Every accepted publication/selection phase yields complete old/new state at actual target paths, with correct native IDs and no partial pointers or policy locks. Unknown journal preserves evidence and refuses. |
| Full-pins alternative only | Add non-root supervision loss/escape/descendant/PID/boot controls, exact replay/revision checks, quiescent release, audited fenced break and request-retirement/epoch restart after caps. Restore unknown sessions refuses until reconciliation. This row is open design plus runtime work, absent from the recommended milestone. |

Receipts bind exact manager/launcher/a2a and schema/model revisions, platform and
architecture, non-root ownership, commands, exit statuses and post-refusal state.
No parser, prepared lock, shim publication or model vector substitutes for them.

## Bounded model checks and limits

A9 checks fresh pin-authority comparisons in launcher/session models: each
lease/request/revision/supervisor/boot/domain/start/phase mismatch refuses.
Updating pin and authority together is the valid revision-advance control.
A10 separates no-edge/live/unknown-session restore inputs and checks observer
confirmation plus descendant quiescence, or operator intent/fencing/revision/reason
and durable audit. Repair retains old evidence and never retargets a session.
Each added negative has a named guard plant and a nearby positive control.
These are bounded checks for the **pins alternative**; they establish neither
native observer provenance nor durable recovery. They are inapplicable to the
recommended no-GC milestone until pins are added.

The [candidate schema](../schemas/profile-command-roots-v1/native-admission-proposal.schema.json),
[named tests/plants](../tools/test_native_root_admission.py) and
[corpus](../conformance/profile-command-roots-v1/README.md) validate shape,
consistency and intended refusals. The text checks cover seven packet rows and eight named roots gate declarations,
detecting accidental status changes; it records no owner acceptance. Production readers still refuse
candidate tokens. Runtime questions and every unaccepted gate remain open.
