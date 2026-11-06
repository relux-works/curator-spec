# Lock-bound profile command roots (Slice B-a)

This unreleased additive contract proposes B-a members for the already allocated
coordinated `launch-env-fragment-v5` and defines `profile-command-root/2`,
`launcher-path-state/2`, `profile-command-reference/1`,
`profile-command-generation/1`, `profile-command-inventory/1`,
`profile-command-session-pin/1`, snapshot sidecar `profile-command-roots/1`,
and capability `profile-command-roots-v1`.
It extends [Slice A](profile-command-path.md), environments §9.4/§10.2 and
Manager Profile §12. It changes no released carrier. The joint v5 carrier
must coordinate other v5 extensions before emission; this leaf is not authority
to discard another required extension. The sole normative whole-object v5 schema
is [coordinated rc7 v5](../schemas/rc7-carriers-v1/launch-env-fragment-v5.schema.json).
The closed [B-a member model](../schemas/profile-command-roots-v1/fragment-members.schema.json)
is non-emittable: it requires both proposed members only for B-a model inputs.
The fixture validator composes it in memory with rc7 v5, preserving rc7 Codex
ownership and modelling Windows paths/profile bounds; that composition allocates
no wire carrier. The rc7 schema still rejects `command_root`. Joint requiredness
for non-B-a fragments and Windows path admission require carrier-owner acceptance;
emission remains CLOSED until that joint schema is accepted. Proposed resolution:
a conditional B-a member pair preserving rc7 in the [native decision packet](profile-command-root-admission.md#candidate-carrier-integration). Lock 5, journal 84/85, config schemas
8/9 and lock 6 remain their owning lanes' allocations. No new lock, config,
launcher-config or journal number is allocated here.

B-a needs journal coverage for generation publication and selection;
reference/settings transitions remain hook work. The full-pins alternative uses
one atomic session record, not a per-launch engine transaction. Existing
84-profile-generation and
85-profile-routing retain their existing scopes: this document does not silently
extend them. The journal owner must accept dedicated publication/selection
coverage before implementation of those journal contracts; extending 84/85 is
not proposed. The atomic state transitions below are
specification models, not evidence that an existing transaction class covers them.
Proposed resolution: the named [journal coverage decision](profile-command-root-admission.md#journal-decision-and-native-witnesses),
with dedicated classes recommended and numbers left to the journal owner.

Owner acceptance is requested in the [seven-gate native decision packet](profile-command-root-admission.md).
Its candidate resolutions do not open any gate.

## Compatibility and admission

Once the root-emission gates below open, an admitted manager MUST emit v5 for
a native interactive profile with active B-a commands, without a capability advert.
The coordinated carrier's separate rule for nonempty Codex policy still requires
every selected consumer to support v5 and typed settings before emission. That
rule is not a B-a capability advert. Otherwise, the revision is the transport
signal; existing resolve argv needs no new flag. An older launcher presented v5
rejects an unknown token or unknown required member before provider start. A new
launcher verifies v5 and refuses unsupported required semantics; neither side
retries v1–v4, emits an empty-root decision, or starts on ambient PATH for B-a.
`env resolve --repair` MUST NOT create, replace, renew or compile a command root.
Resolve checks the selected binding and metadata evidence without a full
command-byte hash; the launcher performs the single full verification before
start. A tampered selected root refuses even if no command would be invoked.
An unselected retained generation does not block another generation's launch.
Existing managed-home repair behavior remains separately gated.
Root reconstruction is only the explicit operator operation below.

| Manager / launcher | Profile with B-a commands | No-command profile |
| --- | --- | --- |
| New / new | Emit v5; verify and apply exactly once or refuse. | Existing no-prepend behavior. |
| New / old | Emit v5; old reader rejects unknown revision, zero provider starts. Nonempty Codex policy additionally requires the coordinated carrier's pre-emission support gate. | Existing supported fragment. |
| New / rc7-only reader | B-a admission refuses unsupported required members; rc7 v5 alone cannot attest B-a. | Existing rc7 behavior within its qualification. |
| Old / new | Old manager is refused by writer/admission policy for a B-a home; no resolve or provider start. | Existing v1–v4 may be admitted without a B-a claim. |
| Old / old | B-a home admission refuses before manager invocation; no fallback. | Existing behavior, no B-a claim. |

A reader cannot infer required commands from an old fragment's absence of a
field. The operator provisions admission binding selected profile/lock and exact
manager/launcher image bytes. New launchers read it before invoking the absolute
manager image, never a PATH lookup. No distribution signer is implied.
The operator attests that legacy entry points are excluded from this workflow and writer cohort. Without that attestation, the manager MUST refuse activation/emission for that home.
Lock revision rejection alone is not admission. Uncontrolled legacy entry points
remain unqualified. The [candidate policy](profile-command-root-admission.md#candidate-policy-and-controlled-entry-point)
uses an explicit operator-invoked operation with lock/CAS; install and auto-upgrade
never invoke it. No new config revision is allocated here.

### Protected state definition

“Protected” means operator-provisioned, same-owner private state checked for
cooperative integrity; it provides no exclusion against another process under
the same UID. Such a process can read and use another agent's a2a credentials,
including access tokens and passwords, and rewrite admission. This accepted limit
is configuration scoping, not identity enforcement or secret isolation.

**CLOSED root-emission gate — protected admission policy:** the policy schema,
protected location, provisioning/update authority and legacy entry-point exclusion
contract require acceptance by the admission/carrier owners. For a home requiring
B-a, absent, corrupt or unsupported policy MUST refuse before manager invocation;
absence never means legacy permission. This is a required acceptance rule, not an
allocated policy carrier. The compatibility truth table assumes this fence and
does not qualify its implementation. Proposed resolution: the exact
[operator policy and controlled entry point](profile-command-root-admission.md#candidate-policy-and-controlled-entry-point),
with same-UID configuration scoping and explicit legacy-route limits.

V1–v4 `path_prepend` remains reserved/inert and can never attest B-a. A v5
fragment with bare `path_prepend` and no `command_root` likewise cannot attest
B-a, even when wire-valid under the current unreleased rc7 schema. For B-a,
`command_environment` remains excluded by [project context](project-context.md).
Project/hybrid precedence and hosted session-manager delivery are deferred;
those modes MUST refuse a request requiring B-a until their own carrier is
adopted. Existing hosted empty decisions and one-shot D-PATH behavior retain
their previous meaning and make no profile-command delivery claim.

## Root, inventory and fragment

The exact POSIX root is
`<manager-home>/environments/<profile>/commands/<generation>/<platform>/bin`.
Windows serializes one drive-qualified path with `/`, for example
`C:/Curator/environments/work/commands/<generation>/windows-amd64/bin`.
Lock and generation are complete lowercase 64-hex identifiers. Generation is a
fresh materialization identity, never reused, including for identical lock bytes.
The lock hash remains bound in the fragment, receipt and marker; it is redundant
in the path. Publication reserves the complete generation identity under the
manager lock and refuses collisions without replacing existing evidence.
Platform is exactly `darwin-arm64`, `darwin-amd64`, `linux-arm64`, `linux-amd64`,
`windows-arm64` or `windows-amd64`, and equals the admitted execution platform.
Profile is 1–64 ASCII bytes: an alphanumeric first character, then
alphanumerics, dot, underscore or hyphen, with no final dot. B-a profile fields
and the fixture composition enforce this grammar. Path normalization, device
basenames and native component bounds additionally require semantic checks;
schema acceptance alone does not attest those rules.
Reject device basenames, trailing dots/spaces, dot segments, links/reparse points,
UNC, drive-relative paths, alternate streams, controls and native PATH lists.
Do not case-fold or shorten names to admit them.

Export names match `[a-z][a-z0-9-]{0,62}` and cannot start `curator-`, name a
Windows device (CON/PRN/AUX/NUL/COM1–9/LPT1–9), or collide under native lookup.
The plan has one provider declaration per export: two active skills claiming
one name refuse even for identical bytes. Context-only/system prerequisites
export nothing. The complete sorted plan union must equal receipt and inventory
names; another profile's root cannot satisfy it.

POSIX native images are private regular files `bin/<name>`, mode 0500, owned
by the operator, link count one. B-a root mode is exactly 0700 (a deliberate
narrowing of Slice A's no-write rule). Metadata remains operator-controlled.
Windows native exports have exactly `<name>.cmd` and `<name>.exe`, protected
by the admitted private DACL; both are independently pinned. Script exports
have an admitted fixed forwarder and complete interpreter chain; they cannot
search PATH or infer undeclared siblings. Fixed forwarding grammar, native
object evidence and independent decoding retain the Slice A rules. Each chain
has at most eight hops; its terminal executable digest equals the receipt.

Every component is at most 255 UTF-8 bytes. Every declared absolute path,
including generation marker, root receipt, all command/interpreter/forwarder
paths, Windows suffixes, gateway and protected record paths, is at most 240
UTF-8 bytes and on Windows 240 UTF-16 units. Check the longest path before writes,
not just the marker. At most 256 exports, 1024 checked files, 1 MiB for each
marker/receipt/inventory, 64 MiB total script/forwarder bytes and 1 GiB total
native bytes are admitted. Over-limit admission refuses before publication.
For ASCII command paths the combined budget is `home + profile + export <= 135/134/129` for Linux/macOS/
Windows respectively (the Windows bound includes the suffix). Receipt paths
also require `home + profile <= 101/100/99`. These sums, not the independent
grammar maxima, determine admission; a 64-byte profile and 63-byte export need
not fit together. Native unit and every protected-record path checks still apply.

Coordinated v5 retains the rc7 adapter/permissions/module contract: for Codex,
`codex_settings` is the sole typed payload and legacy
`credential_store.config_overrides` is forbidden. B-a proposes one
`path_prepend` directory plus `command_root`, required together in its member
model; it does not restore v4 Codex ownership. Its binding contains complete
lock/plan/generation/platform and exact receipt/marker/inventory SHA-256 pins.
Profile and lock must agree with protected selected state. New digest fields
are lowercase 64-hex without a prefix; inherited Slice A fields keep `sha256:`.
The protected inventory records the root and every ordered command hop's path,
kind, owner, mode/DACL, device/volume, inode/file ID, digest and next target.
These IDs are local materialization evidence, not portable build/cache keys.

The root receipt is `bin/.curator-profile-command-root.json`; `generation.json`
is in the platform directory immediately above `bin`. The inventory's bytes
are pinned by the receipt, the receipt by the marker, and all three by external
protected selected/retention state and the fragment. No object hashes itself. The
receipt binds source/commit/directory, driver, original build receipt and final
executable digest for each export. Unknown inventory entries refuse. Equal-byte
object substitution is detected for the root and command chain objects. Metadata
files and generation directories are byte/boundary checked, not claimed to have
pinned native object identities; equal-byte replacement of those metadata files
alone is outside the substitution claim.

**CLOSED root-emission gate — protected-state locations:** the inventory's exact
location, selected/retention-store layout and optional session-store path below
have not been accepted. The reference/binding store is separately covered by the hook-activation gates.
Implementations MUST NOT infer them from this corpus, search provider homes or
emit B-a until the source/carrier owners accept those locations and include every
resulting record path in the 240-unit preflight. This gate applies independently
of the gateway naming decision. In-memory metadata observations below model
byte/binding checks only;
they do not prove inventory discovery or record-path length coverage. Proposed
resolution: the exact [protected paths and candidate records](profile-command-root-admission.md#candidate-protected-paths-and-records),
including final-path bounds; journal staging/backup paths still need owner choice.

## Independent admission gates

Root emission and native launcher `path_prepend` delivery require the joint v5
carrier, protected root-state locations, protected admission policy, journal
coverage, session integration, native runtime witnesses and companion admission.
They do not depend
on the gateway naming decision, settings adapters, gateway aggregate or Windows
dispatcher pins. Hook activation additionally requires every hook gate below;
accepting this proposal opens none of these gates.

**CLOSED root-emission gate — session integration:** the source/carrier owners
must accept protected manager discovery, identity delivery and the milestone
retention choice. Recommend [operator prune without automatic command-root GC](profile-command-root-admission.md#candidate-native-acquire-replay-and-identity):
no acquire/release/request cap or process-domain observation is required. It gives
up automatic reclamation, a disk bound and A9/A10 relevance for now. Full pins is
the named additive alternative; it still needs non-root Linux supervision (L)
and terminal-request/prior-boot retirement with an after-cap route (M to L).
Its one atomic session record replaces a duplicate request tree. Missing accepted
integration refuses B-a before start. Hook pins remain separately gated.
A9's bounded pin-authority comparisons are retained for that alternative; they
obtain no OS observer authority or runtime qualification.

**CLOSED root-emission gate — companion admission:** source owners must accept
`profile-command-admission` and `managed-session-skill-cli`. Recommend the
[native milestone scope](profile-command-root-admission.md#source-seams-and-companion-scope),
including protected-name inventory with pinned aqua/mise inputs and independent
admitted-base-PATH collision checks, plus actual final-tool-shell delivery.
B-a does not discharge command admission. Full companion adoption remains the
alternative. Curator's unconditional adoption refusal and `CommandChecks` seam
remain until accepted contracts and runtime receipts qualify their replacement.

The process-pin and automatic-GC provisions below describe the **full-pins
alternative and future hooks**.
They do not silently require pins for the recommended no-GC milestone. If owners
select operator prune, all automatic command-root and dependent-artifact collection
is disabled (including update/remove/repair/startup); explicit prune under the
manager lock needs operator stop attestation and refuses selected/snapshot/resume/
rollback/journal/reference edges. Roots and dependent evidence persist otherwise.
Pins stay additive. The production carrier/provenance must explicitly allocate
an unpinned variant before use; no dummy pin or released capability is inferred.
Both choices remain proposals with every gate CLOSED.

## Verification budget, process pins and GC

Publication verifies the full root against immutable plan/build inputs. The
launcher independently verifies all bindings, native identities, decoded chains
and exact bytes before provider start; it executes nothing to discover trust.
Full verification occurs once per launch. The final spawn boundary rechecks
metadata pins and all object identities against that verified observation,
without a second full rehash. Same-user check/use races remain outside this
cooperative integrity contract. A cached previous launch verdict is insufficient.
No network, compiler, resolver, recursive scan or command-root repair runs here.

Hook invocation checks the three metadata byte pins, protected reference revision,
root identity, and only the selected command's complete chain and exact bytes.
It does not hash unrelated commands. Scope is at most eight hops, 64 MiB script/
forwarder bytes or 1 GiB native bytes plus 3 MiB metadata; the same caps refuse
before hashing. Implementations MUST enforce a 10-second verification deadline
per full launch or selected-chain hook check, measured by monotonic clock;
expiry refuses before child start. Qualification must report platform, profile
shape, bytes and measured latency. Targets are <=1 second for a 150 MiB launch
and <=100 ms for a <=15 MiB hook on the declared qualification machine; targets
are performance gates for that machine, not measured claims in this spec.
Independent reflink copies (`clonefile`/`FICLONE`) are allowed if they retain
private mutation, distinct IDs and link count one. Hard links remain forbidden.

For the full-pins alternative, the manager issues a durable session pin under
the existing manager mutation/GC lock before verification. Its protected store is
`<manager-home>/state/command-roots/sessions/<request_id>.json`; the closed
[session pin schema](../schemas/profile-command-roots-v1/session-pin.schema.json)
uses discriminator `profile-command-session-pin/1` and binds lease ID, exact root binding/profile, supervisor instance, boot ID,
OS process-start incarnation and process-domain ID, revision and disposition.
The launcher MUST jointly match lease ID, profile and full binding to an active
manager-issued pin before start. In this alternative lease ID equals request ID;
one atomic session record contains request, pin and audit. The launcher keeps its
request in memory for same-process retries only; a new launcher does not resume
that authority.
The issuer is the admitted manager, not the tool or provider. The launcher or
hook gateway runs as a supervisor which spawns the selected image; the gateway
itself does not exec away. It forwards stdin/stdout/stderr, cwd, environment and
signals and waits/reaps the entire domain (including descendants). POSIX argv[0]
is the absolute named image; Windows uses that exact application name and checked
argument encoding. Script argv starts with the pinned interpreter and fixed
arguments, followed by caller arguments. No shell parses caller arguments.

Acquire/publish/bind/release/list/break use the same manager lock and held-operation
primitives as [home leases](home-leases.md), but these pins are separate root
retention, not a change to HL23's native-home-lease policy or its closed record.
Release requires the admitted supervisor observer's exact boot/domain/incarnation
proof of all descendants quiescent, or proved no-start. A dead PID, timeout or
client assertion alone does not release. Lost observer contact leaves `unknown`.
An operator may break one pin only with explicit operator intent, exact revision,
reason and independently recorded domain fencing (or verified prior-boot identity
and terminated domain); break atomically records the prior pin and permanent audit
before a terminal tombstone. It cannot claim to stop processes. Stale restored
pins thus have a stated reconciliation/break route. Unknown pins never disappear
silently. No per-hook unreleasable exec lease is created.

The GC lock covers reservation, complete liveness enumeration, publication,
revalidation and deletion; it is released during hashing and process lifetime.
A durable pin makes the root live before hashing begins. After hashing, reacquire
and revalidate pin revision/objects before start; GC cannot remove a pinned root.
GC liveness unions installed locks, nonterminal process pins, snapshots/resumes,
rollback slots, pending journals and persistent references. Unknown or corrupt
state retains conservatively and refuses collection; complete state with no
edges permits collection. Descendants retain independently of the original PID.
Cache receipts and source artifacts are live through every retained generation.

For full pins, persist `launcher-path-state/2` before child start. It contains unchanged `/1`
`prior_state`, command-root binding, lease ID, `effective_path` and native-joined
`path_value`. Prior state records base/global admission, not the resulting PATH.
The result is exactly protected-tools → selected root → admitted base, constructed
once and passed unchanged to child/provenance. The prefixed prior profile/lock/
plan binding must agree; the Slice A global generation is not substituted for
the B-a materialization generation. Missing evidence, mismatched PATH or root
refuses `profile_command_root_invalid`, with zero provider starts and no ambient
retry. A `/1` record cannot attest B-a.

## Persistent command API and gateway ABI

**OPEN owner question — gateway naming and trust:** should hooks use a stable
per-settings-resource gateway with a protected revisioned binding, or a path
naming each retained generation? The maintainer must decide; this proposal records
no approval. The stable form below is a provisional model only. Either form must
support per-project settings with per-agent hook identity, including two settings
resources on the same profile and command. Neither requires a separate profile.

With the stable form, trust on an approved gateway path covers later generations
explicitly activated by the operator; a stale settings copy follows the current
binding. Activation must be an explicit installer action. With a per-generation
form, settings continue to name their old generation until rewritten; command
changes may require human re-trust on every upgrade, affecting unattended use.
Both forms retain old roots until release proof and refuse released bindings.
The decision changes gateway naming/binding/settings transitions, not root
identity, launcher PATH or retention requirements.

**CLOSED hook-activation gate — gateway naming decision:** hooks MUST NOT activate
until the maintainer accepts a form and its trust/upgrade costs. This gate is
independent of native root emission. All stable-form rules below, including
resource namespace, proofs, path discovery and alias transitions, depend on this
open decision.

After acceptance of the session-integration gate, the admitted manager must
publish its absolute image and manager-home identity in protected launch context.
Adapted tools receive that context through the admitted
launcher integration; they MUST NOT discover the manager via PATH, env overrides
or executable siblings. No new environment literal is added to a frozen carrier.
Outside that integration, explicit operator invocation of the admitted absolute
manager is required. An unadapted tool writing raw `os.Executable()` has no
persistent-hook support; the manager cannot police arbitrary tool settings.

The CLI is `<admitted-manager> profile command <operation> ... --format json`:

| Operation | Required arguments and behavior |
| --- | --- |
| `retain` | `--profile P --command N --settings-resource ABS --request-id HEX64`; manager selects/verifies the installed root and exported command, binds caller operator authority, returns existing identical request or durable prepared reference. Conflicting replay refuses. |
| `list` | `--profile P`; read-only complete sorted prepared/active/released reference inventory with IDs, revisions and bindings; uncertain store refuses, never lists empty. |
| `activate` | `--reference ID --if-revision N --settings-sha256 HEX64`; adapted installer supplies the accepted settings-adapter proof (including unchanged stable-path settings), then CAS switches the resource-specific protected binding and retains rollback preimage. No caller-only digest assertion supplies proof. |
| `release` | `--reference ID --if-revision N`; same operator and settings adapter prove that no current selection, in-flight invocation or registered rollback record retains that reference ID; stable-path text alone is insufficient. Unknown state refuses; terminal identical retry is unchanged. |
| `repair` | `--profile P --operator --reason TEXT`; preserve old evidence and build a fresh generation from identical pinned inputs; never an alias of `env resolve --repair`. |

Requests are strict UTF-8 JSON/argv with no duplicate, unknown or missing fields.
The operation result is exactly `{ok,code,reason,changed,references}`: `ok` boolean,
`code` null or a diagnostic below, `reason` one of `retained`, `listed`,
`activated`, `released`, `repaired`, `invalid_root`, `in_use`, `limit`,
`authority`, `conflict`, `unconfirmed`, `invalid_arguments`; `changed` boolean;
`references` a sorted array of closed reference records (empty for repair/refusal).
Success exits 0 with null code; semantic refusal exits 1, usage exits 2; refusal
has `ok:false,changed:false`. Stdout contains only that single JSON object and LF.
Human diagnostics go to stderr. Caller authority is the admitted local operator
UID/SID and protected manager/settings registration, not the record's owner string
or a package declaration. This is same-OS-user intent, not authentication against
malicious code running as that user.

The provisional stable namespace is per canonical settings resource and command,
not one resource per profile. Its `settings-id` is the complete lowercase SHA-256
of the adapter's canonical resource identity. Registration must detect a digest
collision by comparing the complete canonical identity and refuse it before any
write. Distinct projects/agents can retain and activate independent bindings on
the same profile/command; their hook arguments and identity remain caller data.
Multiple hooks within one resource may share its binding. Resource canonicalization
and registration are subject to the settings-adapter and gateway-decision gates.

The stable gateway is intentionally a mutable protected alias: a stale copy of
the same settings command follows its currently active binding. Releasing an
old reference ID does not revoke that path while another active binding exists.
At most one reference is active for a gateway. Activation atomically displaces
the previous active reference into prepared rollback retention and increments
both changed records' revisions; the selected reference becomes active. An
invocation captures that selected reference ID and its revision under the same
lock as selection and pin acquisition; it never changes a running domain's root.
The bounded HookModel exercises per-reference revision CAS but its ID list and
active/rollback pointers are model projections, not the CLI's full record list
or an accepted persistent aggregate encoding. These stable-form projections
depend on the open gateway decision; stale settings do not identify an old reference ID.
HookModel currently fixes the command to `a2a` and keys retain/selection by settings
resource and generation. It does not model the text's resource-and-command key or
two commands in one resource; hook admission remains closed on that distinction.

Idempotency is by `(profile, command, canonical settings resource, selected
root binding)`, with request replay indexed durably. A crash before settings
write can find/reuse a prepared record by list; after write, activate/release can
resume by revision. At most 256 nonterminal references and 256 distinct retained
roots per profile are admitted across all edge types. A 257th new reference/root
or an over-cap snapshot refuses `profile_command_reference_limit` before writes;
no eviction or truncated snapshot. These caps match the bounded retention carrier
and bound worst-case native storage to 256 GiB per profile (plus capped metadata/
scripts). Installed profiles and snapshots are separately operator-bounded;
there is no claim of a machine-wide disk quota. Age/TTL alone cannot reclaim.
At most 4096 reference request/tombstone entries per profile are stored; a new
request past that cap refuses the same limit diagnostic, while known identical
retries still work. The caps are per profile, so settings resources multiply their
use: with one
command and one rollback per resource, 256 references serve at most 128 resources.
At one new request per resource per upgrade, 4096 entries allow at most
`floor(4096 / resources)` upgrades (204 at 20 resources); fresh-ID retries also
consume entries. These are bounds, not an upgrade guarantee. To bound replay
metadata, operators must explicitly archive/fence the old request
epoch before a later maintenance transition. This slice does not allocate that
transition or silently discard replay protection.

**CLOSED reference-admission gate — request-epoch maintenance:** before operation
beyond this finite cap, the reference-store owner must accept an explicit fenced
archive/epoch transition preserving durable replay/conflict evidence. No implicit
reset or availability beyond 4096 new requests is claimed. Terminal references do not
retain executable roots. The cap is an operational availability tradeoff, not
permission to spend unbounded disk.

Subject to the gateway naming decision, the provisional stable gateway is
`<manager-home>/command-gateways/<profile>/<settings-id>/bin/<command>` (Windows `.cmd`, plus
an independently pinned private `.exe` dispatcher). It is a private native
manager dispatcher copy, mode 0500 in a 0700 directory on POSIX, private-DACL on
Windows, never a symlink. Its protected reference record lives outside provider
homes, indexes the settings resource and pins distribution identity, gateway
bytes and revision. The externally admitted absolute gateway image path is its discovery anchor:
remove the exact `/command-gateways/<profile>/<settings-id>/bin/<command>` suffix (`.exe` for
the Windows dispatcher) to derive manager-home. Recheck that native executable
path and every boundary against the admitted gateway record before reading
protected state. Copies moved to another path have no admission. This requires
no per-home recompilation or PATH/env-derived manager discovery; environment
variables cannot retarget the protected manager-home.
The protected binding selects one retained root, never ambient/machine-current.

**CLOSED hook-activation gate — gateway aggregate and Windows pins:** even
if a stable path is accepted, hook activation stays closed until the source
owners accept the protected aggregate/store encoding,
atomic selection and displaced-reference representation, and independent byte
pins/native evidence for both the Windows `.cmd` forwarder and `.exe` dispatcher.
`gateway_sha256` in the current reference model pins the bytes at `gateway` only
(the `.cmd` on Windows); it cannot attest the separate dispatcher. The Windows
reference fixture is a partial record consistency model, not a complete admission
record. No inferred path or second pin is allocated here. External admission must
verify both images before either executes; missing accepted evidence refuses.

**CLOSED hook-activation gate — registered settings adapter and proofs:** the
source owners must accept adapter registration/provisioning, protected registry
location/schema, canonical resource identity, supported settings/rollback scope,
atomic observation/write semantics and caller authority. No registration operation
is allocated by this proposal. For a stable path, activation proof must bind the
resource, exact unchanged or rewritten settings bytes, expected old reference and
revision, proposed reference and operator intent to the CAS transition; merely
finding the gateway string or accepting a caller digest proves nothing. Release
proof must enumerate protected selection/rollback/in-flight edges by reference ID
and prove detachment or independently observed quiescence. An unchanged settings
file cannot identify which generation is releasable. Unknown copies or incomplete
scope refuse release. The aggregate and adapter contracts must make these proofs
implementable before activation; the boolean model inputs do not qualify them.

Gateway integrity MUST be checked by the admitted hook runner or external
supervisor *before* executing the gateway, against protected byte/distribution
pins and native object evidence. Self-check alone is insufficient. Hook runners
that only execute a raw path and cannot perform this admission are unqualified
for integrity/guard-hook claims; same-user gateway replacement remains a residual
there. A distribution identity is a digest of the admitted signed distribution
manifest, whose signer is verified by protected manager policy; a self-declared
digest is not signer evidence. Subject to the gateway naming decision, security
upgrades may replace the dispatcher under that external admission while preserving stable path and reference reader ABI.
They do not wait for every reference to be released. Unknown required record
semantics refuse invocation until the compatible dispatcher is installed.

At invocation, externally verify gateway, read protected record, reserve session
pin, check selected chain and spawn its exact retained image. Preserve caller
stdio/env/cwd except admitted fixed manager context; do not grant trust,
credentials or enrollment. Refusal starts no command, emits no stdout and exits
126 with `curator: <code>/<reason>` on stderr. The hook runner MUST explicitly map
this refusal to a blocking guard failure; the settings-adapter gate must include
the provider's supported blocking configuration (for example Claude Code
`onFailure: block` where supported) and a witnessed refusal. Until then, claim
only no-target-execution, not that a particular provider blocks a tool call.
Successful calls propagate target exit/signal status. POSIX signal forwarding
includes termination and interrupt; Windows must witness equivalent cancellation
and descendant quiescence before native qualification.

Subject to the gateway naming decision, the adapted installer stages a retained
binding, atomically writes/verifies settings (or proves unchanged bytes), then
activates under CAS; profile update alone cannot activate it. Stable path avoids
a changed command string on upgrade, but does not itself prove Codex trust rules.
Before activation old settings use the old binding; after activation the new
binding is live and old remains in rollback until release proof. A concurrent
hook captures a specific revision under the GC lock and retains it independently.
Missing root/reference/pin refuses with no fallback. Removal detaches selection;
purge refuses while any edge remains. Rollback switches only to a still-retained
verified binding, retaining both until settings proof is complete.

## Publication, restore and snapshots

Install/update privately stage and verify all outputs before atomic publication
of lock/root/protected records/routing. Compile/audit/collision/pin or admission
refusal preserves all old lock/root/marker/receipt/pointer/prompt and unrelated
preimages. Existing handled adapter-conflict exceptions remain precisely their
old contract, not permission to publish a failed root. Inactive profiles may
publish their own generation without retargeting any current/running profile.

**Native runtime gate remains CLOSED for restore:** A10's model vectors now
separate no edge, live-pin and unknown-session inputs and enforce preservation,
quiescence or fenced audited break. They do not witness persistent retained edges
or native reconciliation. Matrix acceptance admits fenced implementation;
accepted runtime receipts precede emission and adoption. With operator prune,
no pin reconciliation is claimed or needed; old generations are not auto-collected.

Explicit repair after restore/migration preserves old evidence at its old
path and materializes a new generation under the same lock from identical source,
plan and build-content pins. New native IDs produce new receipt/inventory/marker
pins; old evidence is never relabeled or overwritten. Installed selection can
move to the new verified generation. Live references/snapshots remain bound to
the old generation and refuse if its IDs drift; an adapted installer explicitly
retains/activates a new binding, with rollback proof before old release. Restored
snapshots need explicit recapture; they are never silently retargeted. Dead-domain
reconciliation or audited fenced break removes stale pins; genuine live pins keep
old evidence while reconstruction at a fresh path proceeds. No stale lease can
force an in-place repair. Missing pinned immutable inputs refuse.

[Managed-home snapshots](managed-home-snapshots.md) admit B-a only through its
separate tool-resource contract here: a required-understanding local retention
sidecar `profile-command-roots/1`, keyed by exact descriptor digest in protected
state. It binds the complete root set and reference IDs, without adding absolute
paths/binaries or fields to old portable descriptors. Sidecar roots/references
must exist and match the exact capture; omission, mismatch or unsupported sidecar
refuses B-a resume. Historical context-only reads retain old meaning. GC must
understand all required retention versions; legacy collectors/writers must be
excluded by admission policy. This is local retention, not portable executable
restoration or hosted transport qualification.

## Diagnostics, conformance and adoption

| Diagnostic | Meaning |
| --- | --- |
| `profile_command_root_invalid` | Missing/tampered/unsupported binding, root, pin, gateway or admission; zero child starts. |
| `profile_command_root_in_use` | Purge blocked by any live/unknown retention edge. |
| `profile_command_reference_limit` | Reference/root/sidecar cap; no writes. |
| `profile_command_reference_authority` | Wrong operator or unregistered settings adapter. |
| `profile_command_reference_conflict` | Request payload or revision mismatch. |
| `profile_command_reference_unconfirmed` | Settings/rollback/descendant proof unavailable. |
| `usage` | Invalid operation arguments; exit 2. |

The corpus maps `reference-owner` to authority; `reference-id`,
`reference-settings`, `reference-revision` and `session-request` to conflict;
`session-unconfirmed` and `session-break-unconfirmed` to unconfirmed; and
`reference-cap`/`retention-cap` to limit. Other integrity/shape refusals use
`profile_command_root_invalid`. These mappings distinguish unavailable proof
from invalid evidence rather than collapsing both to an integrity refusal.

Resolve emits no fragment on refusal, exit 1. Older launcher diagnostic mapping
may report `resolve_invocation_failed`; this still stops provider start. It must
not downgrade. The [corpus](../conformance/profile-command-roots-v1/README.md)
uses closed carriers, required case IDs, exact refusal reasons, deterministic
generation and independent semantic checks. It models roots, references, PATH,
retention, repair/publication and hook transitions. These models prove spec
choices only: no real process, filesystem race, hook trust, platform parity,
transaction durability or signed distribution validation is qualified here.

Native identity: named private copies preserve bytes and portable build receipts,
not native inode identity across profiles/generations. Linux Go `os.Executable()`
and `/proc/self/exe` identify the named file; comm has a 15-byte mutable bound.
macOS `ps comm=` is caller-controlled argv[0] (untruncated); `ucomm=` is the image
basename with native truncation (an observed bound of 16 bytes; platform
qualification is still required).
Gateway argv[0] is pinned to the absolute image so `Base()` yields its name.
Windows image identity is the named `.exe`; scripts run an interpreter. These
are source observations, not fresh runtime measurements. a2a's dev:ino
image guard can refuse a bind across byte-identical generations/profiles/repair;
this fail-closed cost requires tool adaptation. Hosted and machine-current cache
routes may still identify as `artifact`, so they gain no basename guarantee.
Sibling helpers remain outside B-a; undeclared keychain helpers cannot be copied
or inferred. Self-update/deleting immutable images is forbidden.

Before native root-delivery adoption, Curator and curator-run must witness real
isolated publication, no-write refusals and restore; full pins additionally needs
supervision and release/break. Both need two versions concurrently, all age pairs, tamper with ambient decoy and full-launch
verification budgets. Journal owner coverage and protected legacy-entry exclusion
are native admission gates. The [native witness packet](profile-command-root-admission.md#journal-decision-and-native-witnesses)
splits matrix acceptance for fenced implementation from receipt acceptance for
emission/adoption; it supplies no runtime receipt. The fence is defined there once.
Hook adoption additionally requires pre-start external
gateway admission, selected-chain verification budgets, real retain/settings/
upgrade/GC/hook execution and witnessed hook-runner blocking semantics. Those hook
witnesses do not gate native root delivery. Future capability release must bind this namespace,
required-ID corpus and these exact runtime witnesses in the release inventory/gate;
rc.14 remains byte-frozen and gains no capability claim. The design's earlier
shim/path proposal must be updated by its owner at implementation adoption.
Curator's landed Slice A seam publishes forwarding shims under `global/bin` and
refuses skill-plan adoption. That seam does not emit a B-a profile root or prove
launcher delivery; the manager owner must select the B-a delivery path explicitly
at adoption, without silently treating the global generation as a B-a generation.

OS source references: [Go Darwin](https://go.dev/src/os/executable_darwin.go),
[Go procfs](https://go.dev/src/os/executable_procfs.go),
[Go Windows](https://go.dev/src/os/executable_windows.go),
[Linux comm](https://kernel.org/doc/html/v6.10/filesystems/proc.html).

A10 is checked in the bounded transaction model for the pins alternative:
plain, live-pin and unknown-session
repair have distinct edge inputs; unknown refuses without confirmed quiescence
or fenced audited operator break. Repair preserves old edges verbatim, refusing
drop or retarget. No persistent reconciliation or migration is qualified.

The session/launcher models check only their explicit authority inputs; they do
not qualify a supervisor observer, pre-start revision revalidation or protected
manager discovery. Hook chain inputs contain no session pin. Those obligations
remain closed under the session-integration/runtime gates, regardless of a model
acceptance. The distinct repair-edge vectors qualify only that bounded projection;
they are not native store/reconciliation witnesses.
