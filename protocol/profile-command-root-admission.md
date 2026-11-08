# Native command-root admission: owner decision packet

This is an **unaccepted proposal**, companion to
[profile command roots](profile-command-roots.md). All seven root-emission gates
remain **CLOSED**. Only their named owners can accept resolutions. This packet,
model checks and PR review record no acceptance, production names, journal numbers
or runtime receipts. Gateway naming remains open and independent.
The native station-link revision is in [CIP-0032 Review](../cips/CIP-0032-native-a2a-station-link.md)
and [draft Decision 0037](../decisions/0037-native-a2a-station-link.md); neither is Accepted.

## What the owner decides

H below is the operator-selected manager-home directory. SAM means
skill-agents-management, whose provider plugins build launcher plans and argv.

- **Carrier:** recommend one coordinated version-5 manager/launcher message for
  Slice B-a (immutable named command roots), preserving the existing Codex contract.
  SAM owns the typed inputs and Codex rendering with the manager/launcher owners.
  The allocated unpinned launch record is retained until separate launcher provenance
  prune, with no automatic cleanup or disk bound; a failed record write stops
  launch. Command-root prune does not remove these records; older pairs refuse.
  Managed Codex
  gateway launches with a B-a pair or native identity flags refuse before planning.
  Hosted launches receiving a B-a pair refuse as version-unsupported. Every native
  launch, including resume and launches without B-a, drops inherited parent session
  selectors before planning; this ships as a separate launcher change.
- **Milestone and session integration:** recommend **operator prune, no automatic
  command-root garbage collection (GC)**. Keep native discovery, verification and
  identity delivery; give up automatic reclamation, a disk bound and A9/A10
  (pin-authority and restore-model checks) for now. Alternatively say “choose full
  pins”: supervision, request retirement and qualification come first. Pins stay additive.
  Incorrect prune can break a running lane's next tool call, silently select a
  command from base PATH, or make it go dark when its root holds `a2a`; the operator
  receives no warning from prune. There is no process-safety claim.
- **a2a identity and upgrades (owner decisions):** recommend removing inherited
  server/store overrides for an explicit native identity. The revised handover
  derives a Courier station link from the environment managed home; it does not
  admit a credential directory or a separate directory flag. The launcher owner
  may instead refuse nonempty overrides; that choice stays open, but a stale
  keeper-shell variable would then stop launch. Immutable roots end automatic
  refresh of `a2a`: the consumer (background process that wakes an idle lane)
  only re-executes when its pinned path resolves to a new file. Any live own-UID
  `a2a` process with that identity/config root and a different image blocks bind,
  not just the consumer. **Question for the a2a owner, beyond its source-only
  answer:** for this route, should hooks be installed by the selected generation's
  `a2a`? `hook install` records that binary's resolved absolute path, and the
  session-start hook binds from it in-process. On that proposed per-generation
  route, stop conflicting old-image processes, rewrite hook settings using the
  new generation, complete any required Codex re-trust, then start a new session
  and verify the new consumer's image. Stale settings can silently bind the old
  image even when PATH finds the new one. A stable host hook binary is a separate
  owner choice outside this immutable-path refresh claim; no gateway naming is
  decided here. The manager, launcher and a2a owners must accept the hook source
  and restart cost before enabling a2a-bearing roots. Urgent delivery fixes need
  this coordinated settings/trust/restart work and interrupt idle wake.
- **Companions:** recommend native scope for `profile-command-admission` and
  `managed-session-skill-cli`. Protected-name inventory and base-PATH checks remain
  substantial work. Hosted delivery is deferred: `curator-run werkstatt up` and
  hosted launch get no profile commands in this milestone; a keeper uses the direct
  native route and owns restart. Trusted a2a session-start hooks bind the idle-wake
  consumer inside tmux; outside tmux they report unavailable and do not wake an
  idle lane. Codex hooks require the printed trust step; changing the hook command may
  require re-trust on each generation upgrade. This is the
  milestone's stated scope, for owners to accept; these gates remain CLOSED.
- **Policy:** recommend one explicit operator command under the manager lock with
  compare-and-swap (CAS: reject if the current revision differs from the expected
  one). It updates policy, lock and selection together; install and auto-upgrade
  never invoke it. Launches refuse until the operator acts: a
  binary upgrade stops all launches on an unattended host until the operation runs;
  a profile update stops only that profile. A change to the retained ordered base
  PATH also stops launches until the operator updates policy. Spellings inside H's
  command-root namespace are excluded even after prune, without checking identity,
  existence or safety; they cannot enter the child PATH. That exclusion gives up
  detecting unsafe or substituted entries there. On the H route, provider resolution,
  release probing and planning must all use the admitted PATH or refuse before
  doing so; this widens the PATH environment SAM receives. Missing or world-writable entries outside
  that exclusion still refuse: fix the launching shell, not policy.
- **State locations:** recommend the inventory and selection paths below and
  explicit migration of existing private directories. Pins add one session store;
  journal staging and backup paths still need owner acceptance. Supply H via a
  launcher flag before `--` (spelling owned by the launcher). Recommend delivering
  `CURATOR_CONFIG=H/config.json` to child/tool shells, including Codex `inherit=core`
  without identity flags, through SAM's typed block. The launcher and SAM owners
  must accept this wider input. H-only gateway launches must carry it in the plan
  or refuse. A tool-shell `curator` can then change H's lock and stop that profile's
  launches; the Linux witness must cover this choice.
- **Journal:** recommend two dedicated classes, publication and selection; reject
  extending existing `84-profile-generation` and `85-profile-routing` transactions.
  The journal owner assigns numbers and accepts inode preservation and crash
  evidence. Pins use one atomic record, not an engine transaction per launch.
- **Witness gate:** accept the matrix for implementation behind the fence below;
  accept actual receipts separately for emission and adoption. No receipt is claimed.

The scope is one non-root Linux OS user with several profiles and a2a identities.
Courier runs under its own OS user and retains credentials and operational state
outside station reach. Stations sharing one UID can still read and use each other's
`station.key` and rewrite policy. Station identity isolation is real only with one
OS user per station; the shared-UID milestone claims no such isolation.
“Protected” policy addresses accident and cooperative integrity. Qualification is per measured Linux
architecture; project/hybrid, macOS/Windows runtime parity and hook command activation remain deferred.

## Seven decisions, no recorded acceptance

| Gate / status | What must be accepted; owners | Proposed resolution and acceptance still requested |
| --- | --- | --- |
| Joint v5 carrier — **CLOSED** | Curator manager, curator-run carrier/launcher and skill-agents-management (SAM) owner | Accept a conditional B-a pair in the sole coordinated v5, preserving rc7 Codex requiredness and accepting the allocated unpinned provenance below. Native Linux only initially; alternative is a later coordinated revision. |
| Protected admission policy — **CLOSED** | Curator manager and curator-run entry-point owners | Accept explicit manager-home input, pinned image bytes, selected locks and operator attestation; explicit policy operation with lock/CAS, never install or auto-upgrade. |
| Protected-state locations — **CLOSED** | Curator manager/journal and curator-run reader | Accept inventory and selected locations, scoped private-parent migration and actual journal staging/backup preflight. Pins alternative adds one session store; no replay tree or extra generation store. |
| Session integration — **CLOSED** | Curator manager, curator-run launcher/carrier, its skill-agents-management argv plugin owner and a2a identity owner | Recommend no process-pin operations for the no-GC milestone; accept protected discovery, boundary verification and native identity delivery below, including the wider SAM input: the admitted PATH for provider resolution/release probing/planning and `CURATOR_CONFIG=H/config.json` on every H launch. Accept the four-key removal versus nonempty-value refusal choice and the open a2a hook-binary source, settings rewrite/possible re-trust and old-image-process stop/restart cost below. Full pins instead needs the explicitly open supervision/retirement design. |
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
publication checks; the closed retained evidence [allocated below](#base-path-evidence-and-launch-recheck)
supplies the launcher's comparison source. At launch, classify inherited PATH
using [PATH section 3](profile-command-path.md#3-path-construction-and-admission),
selecting its unattended column for the H route, and compare ordered retained lists
after root-namespace exclusion. Refuse a difference; do not hide it by replacing
the inherited base with the stored list. B-a does not use Slice A's `Supervisor`, `Domain` or
routing admission: immutable named roots remove the singleton routing they protect.
Paired vectors include `git`, `ls`, `sh`, `cd`, registry/platform names, aliases,
dynamic-only collisions and ordinary names, preserving preimages. Curator owns
the production checker; spec owners allocate its contract. This is M to L work,
not deletion of the refusal. Whole-companion adoption is the named alternative.

For `managed-session-skill-cli`, accept native current/all-profile verification,
PATH admission and per-launch provenance, no-export behavior and final-tool-shell
witnesses. Hosted active delivery and its joint manager carrier remain closed;
existing hosted unavailable-command behavior is unchanged for older fragments.
A hosted launch receiving a B-a pair refuses by the existing
`fragment_version_unsupported` route, with zero starts: dropping those commands
would silently fall through to base PATH. B-a supplies the native
immutable-root design, but neither a design nor a prepared lock qualifies adoption.

Historical source observations below are retained from the earlier packet, not
refreshed by the station-link revision.

Launcher
[`2045339f703ee8190705c116a05197b12b684b71`](https://github.com/relux-works/curator-agent-launcher/blob/2045339f703ee8190705c116a05197b12b684b71/internal/fragment/fragment.go)
reads v1–v4; parsed `path_prepend` has no native consumer yet. `--a2a` exists
for hosted doorbell wiring and route selection, and is refused on native launches.
The former proposed `--a2a-config-dir` is removed from native admission;
`--native --a2a <identity>` instead derives a station link from the managed home.
These are missing implementation seams,
not runtime evidence. Existing global shim publication is not B-a materialization.

Source follow-up: launcher main remains
[`2045339f`](https://github.com/relux-works/curator-agent-launcher/blob/2045339f703ee8190705c116a05197b12b684b71/internal/plan/context.go)
with SAM v0.5.74; [SAM main `d97ec516`](https://github.com/relux-works/skill-agents-management/blob/d97ec5166f479c08410881dc38c9cc945dfdc433/pkg/agentic/systems/codex/args.go)
owns provider argv rendering. SAM's [gateway proposal at `a48fa206`](https://github.com/relux-works/skill-agents-management/blob/a48fa206dcd11e13b625231140b03475eb1aea7f/pkg/agentic/codex_gateway.go)
is still open, not current main. Its exact-process checks motivate the milestone
exclusion below; none is claimed implemented by this packet. The launcher owner
also sequences its existing pending change before B-a implementation.
The [a2a hook/bind documentation at `ebb308fc`](https://github.com/relux-works/a2a-swarm/blob/ebb308fc863f672812b2dd3a403056f3e2916575/docs/cli.md)
confirms tmux-only automatic binding and Codex's separate hook trust step; this is
a documentation read, not a wake-up witness. The a2a owner's source-only answer
addressed the earlier credential-directory pair, the transport/store change below,
the three-key scrub and the image-guard contract for implementation. That historical
answer does not accept the revised station-link contract and supplies no runtime
receipts or gate acceptance. Verified against [a2a main `afa27bab`](https://github.com/relux-works/a2a-swarm/tree/afa27babaf64c9f8247c13fd4a3214754116cf8b):
`internal/config/config.go`, `internal/cli/credentials.go`, `identity.go`, `bind.go`,
`bind_process.go`, `bind_process_linux.go`, `bind_refresh.go` and `onboard.go`.
At that same main commit, `hookinstall.go` records the installing binary's resolved
path, `bind_hook.go` calls bind in-process and `bind.go` spawns that image. These
hook-source/upgrade implications extend the owner's answer and remain a question
for the a2a owner. This follow-up text still needs its owners' exact-head review.

## Candidate carrier integration

Add `command_root` and `path_prepend` together to the sole coordinated rc7 v5;
neither is required when neither is present. Bare v5 prepend refuses. Preserve
all other rc7 ownership, unknown-member and typed Codex policy requirements.
The candidate model restricts B-a to Linux; it leaves the inherited path grammar
intact. No-command profiles retain existing behavior and gain no B-a claim.
The no-GC choice uses the allocated unpinned provenance below; the existing
closed `launcher-path-state/2` still requires a lease and is not relaxed. The
allocated candidate shape needs joint-carrier acceptance before emission. Candidate composition is a review
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
H is a launcher-owned flag before `--`, never a forwarded provider argument;
its spelling is for the launcher owner to propose. This input is proposed;
it is not a claim that today's launcher has such a setting. `CURATOR_CONFIG`,
ambient PATH or a provider cannot override the pinned manager once selected.
The launcher sets the manager's home from H; a conflicting inherited
`CURATOR_CONFIG` refuses. **Recommendation for the curator-run launcher and SAM
owners:** set `CURATOR_CONFIG=H/config.json` in the planning environment and deliver
it to the provider child and tool shells, including Codex `inherit=core` with or
without identity flags, using the SAM-rendered typed block specified below,
so a tool-shell `curator` resolves the same home. H is a directory, whereas
[`CURATOR_CONFIG` names its config file](https://github.com/relux-works/curator/blob/163c2e98bd5d9596dca1f51f73b8f4393e8101b8/internal/config/config.go);
do not set it to the bare directory.
This propagation widens SAM's proposed per-launch typed input beyond a2a identity;
the launcher and SAM owners must accept it. On an H-only managed gateway launch,
include the locator in the planning environment and admitted SAM rendering, or
refuse before start; never overlay it after planning. This is proposed, not current
launcher behavior, and needs the H-in-a-tool-shell witness below. Legacy resolution
remains unchanged.

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
| Retained base PATH | `H/state/command-roots/base-path.json` | Closed `candidate/native-base-path/1` below; replaced in the same operator transaction as policy/selection. |
| Launcher provenance | `${XDG_STATE_HOME}/swarma/launcher/<launch_id>.json` (state-home fallback `${HOME}/.local/state`) | Operator prune uses closed `candidate/native-root-launch/1` below; full pins keeps `launcher-path-state/2`. Launcher-owned provenance, no admission authority or retention edge. |
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

## Allocated unpinned launch record

The closed `$defs/unpinned_launch` in the [candidate schema](../schemas/profile-command-roots-v1/native-admission-proposal.schema.json)
allocates `candidate/native-root-launch/1`: `prior_state` (the existing
`launcher-path-state/1`, including its unpredictable 32-hex `launch_id`), the full
seven-field `command_root` binding, `effective_path`, `path_value`,
`policy_revision`, `selection_revision` and `base_path_sha256` (raw evidence-file
bytes). There is no lease or session pin, and unknown members refuse. Prior
profile/lock/plan and root binding must agree with the selected generation;
PATH order/value must match the constructed child environment. Keep the existing
private/exclusive/atomic durable publication requirements before spawn; failure
refuses without a child. It records the pre-spawn observation, not successful
execution, live-process authority or runtime qualification.

Retention is one file per launch until **explicit operator-invoked launcher
provenance prune**, implemented/owned by the launcher; no automatic expiry,
cleanup or disk bound. This is separate from manager command-root prune. Deleting
a provenance file never authorizes root GC; keeping it is not a pin. Full pins
stays an additive alternative. These complete proposed shapes use candidate
tokens refused by production readers; no production token or gate is opened.

## Base PATH evidence and launch recheck

The closed `$defs/base_path_evidence` allocates `candidate/native-base-path/1`
with exactly `record`, canonical `manager_home`, `uid`, `policy_revision`, Linux
`platform` and ordered `retained` absolute path strings. The manager classifies
the operator-supplied PATH under section 3's unattended column, excluding known
root namespaces and applying its defaults when required, and retains that list.
The operator command atomically replaces this file alongside policy/selection;
its home/UID/revision/platform must match the observations used by the launcher.

The launcher applies those same predicates/exclusions/defaults to its inherited
PATH and requires **ordered equality** with `retained`, not set equality. Emit
section 3's drop/exclusion diagnostic; then prepend only the freshly verified
selected root and protected tools to the admitted list. An inherited current or
older B-a root is excluded **by canonical spelling inside H's command-root
namespace**, before filesystem predicates, even if operator prune removed it;
recognized aliases outside that spelling namespace still require readable identity
evidence. These entries never enter the child PATH. Exclusion gives up checking
existence, safety and publication identity inside that namespace, including
substituted or world-writable entries; only the freshly verified selected root is
inserted. Missing/unreadable or world-writable entries outside this spelling
exclusion still refuse under the unattended rule; fix the launching shell PATH,
not the policy operation. On the H route, provider resolution, the release probe
and planning MUST all use the admitted PATH constructed for the launch, or refuse
before resolving, probing or planning with another PATH. This widens the PATH
environment SAM receives; do not pass raw parent PATH and overlay it after planning.
On the H route, remove `CODEX_MANAGED_PACKAGE_ROOT` from the environment supplied
to provider resolution, release probing and planning, or refuse before those stages.
SAM reads this managed-package selector before PATH and filters it only from the
child environment; child-only filtering is insufficient.
An excluded spelling containing `codex` or `claude` must supply neither a release
probe nor the provider executable. Do not blindly substitute stored PATH to conceal a difference.
Any launching-shell PATH change that changes the retained ordered list stops
launches until the operator runs the policy operation again. This costs operator
work after environment changes; benign drops/exclusions alone do not change it.
The bounded model receives classified lists; native classification, identities
and namespace recognition still need the disposable-Linux witness below.

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
the same UID. In the station-link proposal, Courier credentials, state, mailbox
and locks move behind its separate OS user, outside station reach. Under one
shared station UID, any station can still read another's `station.key` and
impersonate its identity to Courier. Mode 0600 and `A2A_CONFIG_DIR` scope configuration
but cannot isolate stations sharing a UID; real station isolation needs one OS
user per station. Legacy binaries outside the controlled workflow are unqualified.

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
Launcher verification takes **no manager lock**: it reads atomically replaced
policy, selection and base-PATH evidence, rejects missing/incoherent records, and
rechecks both policy and selection revisions at the final spawn boundary. A
concurrent policy or selection change refuses. There is no locked-read exception. These comparisons establish consistency with the
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
or provenance: use the allocated unpinned candidate shape above, and keep
production readers refusing it until the joint allocation is accepted. Verification of
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
or unlocked bypass is promised. The operator-prune launcher avoids acquire and takes no manager lock for
verification; the operator policy/prune operations can still contend. Launches
also call `env resolve --repair` unconditionally on current launcher main; that
repair can take the manager mutation lock and wait up to the 30-second timeout.
Unlocked verification does not remove that launch-time wait unless the B-a route
changes the resolve call. This is source reading, not timing.

### Native station-link handover (Review)

Native identity launch takes `--native --a2a <identity>`. The launcher derives
`A2A_CONFIG_DIR` from the environment's resolved managed home M as `M/.a2a`,
never from an independent directory flag or inherited credential-directory pair.
M is the environment managed home, not the manager home H above. The former
proposed `--a2a-config-dir` is not admitted on the native route and refuses
`native-a2a-config-dir-unsupported` before planning. The launcher's existing
identity syntax validation remains a precondition. Hosted `--a2a`, doorbell
wiring and route selection are unchanged; this revision admits no hosted station
handover or new hook/doorbell behavior.

The handover shape follows **a2a owner design note v0**: the station holds a link
and an authentication secret; Courier, under its own OS user, holds all a2a
credentials, state, mailbox and locks. The grants lane proposes the same station
link shape, intended as one design. This packet allocates no separate challenge,
wire protocol for either lane. The supplied a2a owner and curator-run answers
below settle enrollment lifetime and key length for this Review proposal; they
do not accept the whole proposal or open a root-emission gate.

`M/.a2a` MUST be a directory, not a symlink, mode exactly 0700, owned by the
station UID. Its closed entry set is exactly:

| Entry | Meaning and launcher observation |
| --- | --- |
| `courier.sock` | Station-UID-owned regular file, not a symlink, whose non-secret value is the absolute Courier socket path. This file is the only socket-path source: no per-OS default is specified. It is a path file, not the socket object or a symlink to it. |
| `identity` | Station-UID-owned regular file, not a symlink, containing exactly one line matching `^[a-z0-9._=-]{1,64}\n`: ASCII name followed by one LF, no spaces or BOM. The name before LF equals the registered identity selected by `--a2a`; no trimming or normalization. |
| `station.key` | Station-UID-owned regular file, not a symlink, mode exactly 0600 and size equal to the versioned **a2a enroll contract** key length, currently **32 bytes** as supplied by the a2a owner for enrollment. This value belongs to a2a, never a launcher constant. Unavailable contract value refuses. The launcher checks metadata only and MUST NOT open/read its secret contents. |

No credentials, state, mailbox, lock or additional entry is allowed. For example,
`credentials.json` is an extra-entry refusal even if its bytes resemble a valid
old credential store. The legacy credential-directory pair is not admitted on
this native route. A matching inherited pair alone proves no station admission.

Before constructing a plan or starting a provider, the launcher checks the
no-follow directory and entry observations and the two non-secret file values.
Unavailable metadata or either public-file read refuses `native-station-unreadable`;
this does not require or permit reading the key. Implementations must bind
the checks to the same directory rather than follow a replacement symlink.
This bounded model receives observations, not live files, and qualifies neither
OS observation nor TOCTOU handling. A missing or bad station directory/entry
refuses with stable operator-facing code `native-environment-not-registered`,
meaning **environment not registered with Courier**. The finer codes below are
content-free sub-reasons under that code, including unavailable contract value;
no file contents, secret bytes or arbitrary extra-entry names are echoed. Invalid
managed-home input retains its separate precondition code:

| Condition | Stable sub-reason (or managed-home precondition code) |
| --- | --- |
| Managed home is not an admitted absolute locator | `native-identity-directory` |
| Courier secret-size contract is unresolved | `native-station-contract-unresolved` |
| Observed directory is not the derived managed-home locator | `native-station-directory-location` |
| Required metadata or either public-file value unavailable | `native-station-unreadable` |
| Directory missing | `native-station-directory-missing` |
| Directory is a symlink or another non-directory | `native-station-directory-type` |
| Directory mode differs from 0700 | `native-station-directory-mode` |
| Directory owner differs from the station UID | `native-station-directory-owner` |
| Any extra entry, including `credentials.json` | `native-station-extra-entry` |
| Any of the three required entries missing | `native-station-missing-entry` |
| Any entry is a symlink or another nonregular object | `native-station-entry-type` |
| Any entry owner differs from the station UID | `native-station-entry-owner` |
| Key mode differs from 0600 | `native-station-key-mode` |
| Key byte size differs from the Courier contract | `native-station-key-size` |
| Identity bytes violate the exact one-line grammar | `native-station-identity-format` |
| Well-formed identity name differs from `--a2a` | `native-station-identity` |
| Socket-path value is not absolute | `native-station-socket-absolute` |

#### Station enrollment contract (owner answers folded into Review)

Registration is **per environment**, not per launch: the station is the managed
environment. Its key lives for the environment lifetime and rotates on environment
recreation or explicit rotate. Enrollment is a two-sided pipe **outside launch**:

1. As the Courier OS user, `register-station ... --emit -` mints the station secret
   and emits exactly one closed JSON line to the pipe.
2. As the station OS user, `a2a courier enroll --dir <home>/.a2a --from -` consumes
   that line, creates the 0700 directory and its three entries owned by the caller,
   and refuses existing entries without `--rotate`. Here `<home>` is M.

The launcher never calls registration/enrollment and never writes `M/.a2a`;
neither launcher nor agent mints the secret. No enrollment JSON or secret passes
through the launcher's argv, environment, logs or plan. Only
`A2A_AGENT=<identity>` and `A2A_CONFIG_DIR=M/.a2a` are delivered at launch.
This is the supplied a2a owner and curator-run handover contract, not a Courier
implementation or authentication receipt. The model receives the key length
from a versioned a2a enroll-contract value (currently 32); it does not read the
key contents to establish length or choose a format. If that contract value is
unavailable, admission still refuses `native-station-contract-unresolved` under
`native-environment-not-registered`.

A later a2a leaf adds an admin socket through which the Curator manager may drive
the same enrollment pipe. This is a **future seam**, with no admin socket,
manager-driven enrollment or automatic launch-time enrollment claimed here.
Both former lifecycle/caller and key-length questions are resolved by these
answers. Publishing/consuming the versioned a2a contract and qualifying real
enrollment remain implementation dependencies, not new product decisions in
this revision. All root-emission gates remain CLOSED.

For native explicit identity, compare exactly `A2A_AGENT` and `A2A_CONFIG_DIR`
against the identity and derived station-link directory: nonempty differing
inherited values refuse `native-identity-conflict`; identical or empty/unset
values pass only after link admission. An orchestrator launching another identity
must scrub its own pair first. The existing four-key rule is unchanged: on the
native route **with an explicit identity**, remove inherited `A2A_MATRIX_URL`,
`A2A_MATRIX_SERVER_NAME`, `A2A_SECRET_STORE` and `A2A_MATRIX_REGISTRATION_TOKEN`
before planning, or refuse on a nonempty value. **Recommend removing all four**,
including matching/empty values; the launcher owner's removal versus nonempty-value
refusal choice remains open. The model checks only the existing removal variant.
Without explicit identity this four-key rule does not apply. Other `A2A_*` keys
are not claimed covered by the two-key comparison or this named four-key rule.

For **every native launch**, including resume and launches without B-a, remove inherited `A2A_SESSION_ID`,
`CODEX_THREAD_ID` and `CLAUDE_CODE_SESSION_ID` **before planning**, with or without
identity flags; never invent
replacement session IDs. Forwarded arguments after `--` are uninspected and may
include `resume`; the launcher cannot reliably distinguish new sessions. The
runtime supplies its own metadata. This is its own separately reviewed launcher
change, so the plan's exact environment already includes the scrub. This follows
a2a's documented session rule (`docs/cli.md`, source revision
`f8b88dd425ccc65f0f3f8324e92d081570486d81`), including its Claude bind/lease
selector. The a2a owner's answer accepts this set at a2a main `711ed0d6`;
rechecked unchanged at main `afa27babaf64c9f8247c13fd4a3214754116cf8b`.
Keep `TMUX` and `TMUX_PANE`: bind requires its own pane/socket.
`CLAUDECODE`, `CODEX_SANDBOX` and `CODEX_SANDBOX_NETWORK_DISABLED` are onboard
runtime-detection inputs, not session selectors, and need no scrub under this rule.
A missed selector makes bind refuse, but lease-taking commands can use the
inherited session, so refusal alone is not a substitute for scrubbing.
Whether Claude Code overwrites an inherited selector is unverified.
Without identity flags the identity/config pair passes through without a new claim.
For Codex `inherit=core`, the launcher passes typed per-launch values to the
**SAM Codex plugin**, which revalidates and renders a `-c` block separate from
`codex_settings`: `shell_environment_policy.set.A2A_AGENT` and `.A2A_CONFIG_DIR`
when native identity selects the admitted station link, plus `.CURATOR_CONFIG=H/config.json` on
every H launch, **including without identity flags**. The planning environment
and provider child contain the same home locator. Identity and this non-secret
launcher home locator are not lock properties or a vocabulary extension.
SAM owns rendering and the typed-input extension, with the launcher owning value
selection; it is separate from `codex_settings`. The launcher never appends this
provider block after planning, nor mutates shared daemon configuration.
For Claude, retain the existing Claude environment carrier and precedence
requirements for these same two non-secret values; this proposal introduces no
secret-bearing settings or new Claude carrier. The final tool-shell keys must
match the selected pair when present and the home
locator on every H launch; parent-env inheritance alone does not deliver it under
`inherit=core`. This carrier integration,
PATH survival through shell startup and provider settings precedence are **W0 open
questions** for real Claude/Codex tool shells on Linux. In particular settings
`env.A2A_AGENT` can bypass a parent-env check: a conflict must refuse or be prevented
by accepted per-launch precedence, then witnessed. No parser/model supplies W0.
An external keeper reports limited clean-account observations with mock transport:
Codex 0.166.0 default inherit kept `A2A_*`, `inherit=core` removed them, and
`inherit=core` plus `shell_environment_policy.set` delivered both selected values
and dropped a third sentinel; plain `login=true` produced a nonlogin shell.
Claude Code 2.1.317 with `--dangerously-skip-permissions` kept inherited `A2A_*`
and prepended PATH. These are not qualification. Real transport, settings
precedence and settings `env.A2A_AGENT` remain for **W0 tool-shell delivery**;
SAM's Claude V3 yolo row refuses nonempty explicit settings env, so a `--settings` override
is not a universal answer. The a2a owner's source-only answer is incorporated
above; Linux identity, transport and image-guard receipts remain owed.
Native flags install no doorbell or hooks. The a2a image guard across generations
remains unchanged and needs the matrix controls below. Immutable roots also keep
the consumer's pinned launch path unchanged, ending automatic refresh on that
route. Stopping it and starting a new session alone does not deliver a fix:
`hook install` records its own resolved binary path, and the session-start hook
binds in-process. G1 settings can bind a G1 consumer without error in a G2 session,
regardless of G2 on PATH. The proposed per-generation hook source requires settings
rewrite by G2 and possible Codex re-trust, stopping any conflicting old-image
process (not only the consumer), a new session and verification of the G2 consumer
image. The hook-source choice goes beyond the a2a owner's answer and remains a
question for that owner; restart/trust acceptance remains open, including urgent
fix rollout. A stable host hook binary would be outside this immutable-root claim;
no gateway naming or hook activation is accepted here.

### Managed Codex gateway exclusion

For this operator-prune milestone, a B-a pair **or explicit native a2a identity**
on a managed Codex gateway route refuses `native_root_gateway_unsupported`,
before plan construction, with zero provider starts. The refusal is launcher-owned;
plain native delivery without that gateway is the nearby positive control.
Every-native session scrub still runs before planning and is not excluded.
The proposed SAM gateway verifier binds exact argv and the final plan's complete environment
plus only the admitted token; post-plan PATH/identity/config overlays cannot pass.
Joint SAM/launcher work is required to admit them later. This is a milestone
exclusion, not a new gateway naming decision. That proposed gateway admits Codex
0.164.0; the reported 0.166.0 observation is not a gateway witness.

## Journal decision and native witnesses

Recommend exactly two dedicated classes, publication and selection; the journal
owner assigns their names/numbers. Extending `84-profile-generation` or
`85-profile-routing` is rejected: their lock-keyed generation file and routing
file scopes stay unchanged. Publication targets `environments/P/commands/G`
(**not** P or the whole commands directory); inventory, marker and receipt are
inside that target. Selection covers pointer/lock/routing, authorized policy and retained base-PATH
evidence postimages in one outer transaction with publication. The inode problem is
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

Witnesses below run on **disposable non-root Linux accounts**, not the development
workstation. The W0 observations above are navigation only.

| Native witness | Required observation and negative control |
| --- | --- |
| W0 tool-shell delivery | Real Claude and Codex Linux tool shells: profile PATH survives startup; Codex `inherit=core` receives selected identity/config. Settings `env.A2A_AGENT`/config override conflict is prevented or refuses; valid matching settings work. Record actual precedence and carrier, not parent env alone. |
| Real launch and identity | Two profiles with different sentinel bytes, two identities/config directories, one UID. Actual tool shells find selected commands and report selected identity. Nonempty inherited conflict refuses; empty values pass. New sessions never reuse inherited `A2A_SESSION_ID`/`CODEX_THREAD_ID`/`CLAUDE_CODE_SESSION_ID`; valid runtime-owned metadata works. No ambient decoy executes. |
| Explicit native pair transport/store | Inherit `A2A_MATRIX_URL` differing from selected `matrix.env`: it must not reach the new identity; under recommended removal a matching inherited URL still permits selected routing. Under the open nonempty-value refusal variant, matching as well as differing nonempty URLs refuse with zero starts; unset is its launch control. Exercise the other three named overrides as well. Recommended removal drops all four before planning; the launcher owner may instead choose nonempty-value refusal, witnessed as zero starts. Unset control launches; without an explicit pair the new four-key rule is not applied. |
| a2a image guard across generations | Linux image identity is dev/inode of `/proc/<pid>/exe`. Any live own-UID `a2a` process with the same identity and canonical config root, regardless of command, participates in the different-image refusal: a byte-identical copy in a new root is refused as a different image; a hard link to the same inode passes the image comparison (other bind and command-root admission guards still apply). The scan covers only own-UID processes whose executable name starts with `a2a`, so the published executable name MUST retain that prefix; a differently named copy is invisible to this scan and is not a bypass claim. Nearby distinct identity/config-root controls behave as current a2a permits. With immutable roots the consumer does not refresh to a newly published generation. Stop all conflicting old-image processes, not only the consumer. For the proposed per-generation hook source, install settings using G2, complete required trust, start a new session and assert the consumer's `/proc/<pid>/exe` dev/inode equals G2's image, not merely successful bind or G2 on PATH. Stale G1 settings with G2 on PATH and no old process can successfully bind G1: this MUST fail the upgrade witness. Rewritten G2 settings plus an observed G2 consumer are the positive control. Hook-source choice and settings/trust/restart cost await a2a-owner acceptance. |
| Carrier/admission age pairs | Every old/new manager/launcher pair, explicit H with missing/corrupt/stale policy, unsupported mode, policy CAS mismatch: named refusal, zero starts, unchanged state; admitted pair starts. Hosted `--a2a` alone still works; native `--a2a` uses the derived station link and refuses the removed directory flag. Missing/symlink/wrong-owner/wrong-mode directories, credential-looking extras, missing or symlink/nonregular entries, key mode/size errors, identity mismatch and relative socket values each refuse before planning, with zero starts and unchanged files; a valid station link is the positive control. Secret contents are never read by the launcher or reflected in a plan, environment, argv or log. |
| Managed Codex gateway exclusion | Exercise each selector on launcher main: explicit `--network`, launcher proxy profile, and the operator gateway default without either explicit selector. Main computes these after `plan.Build`; the proposed refusal must determine the effective gateway route before building the plan rather than reuse that later variable. B-a pair or explicit native a2a identity: `native_root_gateway_unsupported` before planning, zero starts and unchanged state. Nearby supported plain-native pair/identity and ordinary gateway without either input remain admitted. Scrub is already in the planning environment. |
| Every-native pre-plan scrub | New/resume, with/without B-a or native identity flags: all three inherited session selectors are absent from the planning environment; runtime-owned metadata still works. `TMUX`/`TMUX_PANE` remain intact for bind; the three onboard-only runtime markers are not scrubbed as selectors. No forwarded-argv inspection or fabricated replacement. Separate launcher change and review. |
| H in a tool shell | Exercise Claude, Codex default-inherit and Codex `inherit=core`, with and without identity flags; SAM's typed block supplies the locator where needed under `inherit=core`. The planning environment, provider child and actual tool-shell `curator` receive `CURATOR_CONFIG=H/config.json` and use H. Witness settings `env.CURATOR_CONFIG` precedence: a conflicting override is prevented or refuses, and matching settings work where SAM admits settings env. Claude V3 yolo refuses any nonempty explicit settings `env`, including a matching locator. Missing or different delivery fails the witness; absent/matching inherited values pass and a conflicting inherited locator refuses. H-only managed gateway includes the locator in the admitted plan or refuses without a post-plan overlay. Verify launcher flag before `--`, pinned absolute manager, legacy control and the same-home lock-update consequence. Launcher and SAM owners accept this wider input before implementation. |
| Base PATH recheck | Same retained ordered list passes; reordering/addition/removal refuses with no start, no replacement fallback. A shell holding a current/older or pruned root passes by canonical spelling within H's command-root namespace before filesystem checks, giving up identity/existence/safety checks on excluded entries; a readable recognized alias also passes. Outside the spelling exclusion, missing/unreadable/world-writable entries refuse and require fixing the launching shell, not policy. H selects unattended policy. Put a provider-named `codex` or `claude` decoy in an excluded H-namespace spelling **before the real provider in the launching shell's PATH**: it is neither release-probed nor started; provider resolution, release probing and planning use the admitted PATH or refuse. The nearby provider outside the excluded namespace is resolved/probed/started. Also inherit `CODEX_MANAGED_PACKAGE_ROOT` naming an installed Codex layout both under an excluded spelling and **outside H**: it is removed before resolution/release probing/planning or launch refuses; that binary is neither probed nor started. With the selector absent, the admitted-PATH provider works. Observe policy/selection change during verification: spawn-boundary recheck refuses without taking the manager lock. |
| Unpinned provenance | Durable candidate record before spawn, consistent binding/revisions/evidence digest and final PATH; write failure refuses. No lease fabricated, no automatic expiry; explicit launcher provenance prune removes only those files, never admits root GC. |
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
consistency and intended refusals, including supplied station-link metadata,
closed entries, public identity/socket values and metadata-only key checks,
unpinned provenance, ordered retained
PATH, H-namespace spelling exclusion, supplied planning/tool-shell home-locator
observations, route exclusions and spawn revisions. These pure models do not
exercise launcher planning order, atomic filesystem reads, SAM rendering or
provider/tool-shell behavior. The text checks cover seven packet rows and eight named roots gate declarations,
detecting accidental status changes; it records no owner acceptance. Production readers still refuse
candidate tokens. Runtime questions and every unaccepted gate remain open.
