# CIP-0016: Local hosted launches through curator-run

- **Status:** Draft
- **Owner:** ivan-curator (orchestrator); decision: operator
- **Created:** 2026-10-15
- **Related:** CIP-0014 (session materialization, proposed companion); owner decisions 2026-10-15 D1–D6, D9–D13
- **Affects:** curator-agent-launcher SPEC §§3, 4.6, 4.8–4.9, 10; skill-project-management sessionmanager and tb-sessiond; skill-agents-management hosted planning; swarma-session-host SH1 compatibility boundary

## Summary

`curator-run <env> --hosted` should launch a local task-board session before
availability of the dispatcher, for Claude Code, Codex and Muse together.
The caller composes a complete launch using Curator and agents-management;
the board's `tb-sessiond` admits that launch and owns its local execution.
Each launch uses a session snapshot produced by Curator, never a live managed
home, and a versioned receiver contract prevents the daemon from rebuilding
the profile or launch. This is a same-machine, same-OS-user integration,
not activation of the cross-account dispatcher or session-runner design.

This Draft proposes changes; it enables no route by itself. The public
contract must be adopted and its three runtime adapters qualified before
production advertises the capability. Owner decision 2026-10-15 (D2) requires
all three runtimes from the first supported release; owner decision
2026-10-15 (D3) makes replacing the old infrastructure entry point the priority.

## Motivation and user stories

An operator selects a Curator profile and launches a persistent board session
with one command. They can attach, detach, resume and use board goals without
asking a second composer to reinterpret the selected profile. The command
works on the local machine while dispatcher implementation is still pending.

A Codex user gets the board's private app-server and a private `CODEX_HOME`,
with their Curator-selected instructions and settings preserved. A Claude
user gets the daemon's PTY with the selected snapshot. A Muse user gets the
existing PTY integration with Curator's explicit root-context declaration.
No runtime is a placeholder for a later phase.

A native invocation remains native. Failure to reach a local host is visible
as a hosted refusal, never a native execution started as a fallback. A future
dispatcher deployment likewise cannot silently move a local launch to another
account or machine.

The operator can keep using `task-board claude` and `task-board codex` during
migration. This proposal does not require converting every existing command
into a Curator wrapper before the new entry point can ship.

## Current state

### Evidence baseline and limits

References below identify repository-relative paths, not machine paths.
The checked source snapshots are curator `00fec196`, curator-spec `d34d8a6`,
skill-project-management `b057ef468`, curator-agent-launcher `9ad2f016`
(SPEC `0.5.1-draft`), and swarma-session-host `255523d4` (spec r13).
Source reading establishes implementation structure, not a live launch or
successful provider qualification. No provider probes were run for this CIP.

The attached owner decisions are newer authority where the older contracts
conflict. In particular, owner decision 2026-10-15 (D1) assigns home content,
verification, repair and login readiness to Curator; owner decisions
2026-10-15 (D4) and (D5) require snapshots and `env materialize`.

### Launcher and hosted wire

curator-agent-launcher/SPEC.md §3 defines `--hosted`, `--native`,
`--untracked`, hosted-only `resume [SES-HANDLE]` and `--resume <id>`.
Sections 4.6 and 4.8 separate legacy `ax` routing from host selection;
no default means native and no receiver lookup. Enabled `ax` plus a hosted
selection refuses `host_configuration_conflict`.

Section 4.8 expressly makes production hosted lookup refuse
`session_host_missing` until the dispatcher path ships, even with task-board
on PATH. It also limits its dormant first phase to `claude_code`, gates
machine hosted defaults behind `session_host_default_not_ready`, and refuses
hosted source-side `--network`. Section 4.9 is a dormant contract tested with
injected receivers, not evidence of a public operational receiver.

Section 4.9 defines `urn:relux:task-board:session-launch-plan` `1.0.0`:
SHA-256 `content_digest` over CCJ-1 excluding only that member, pinned
producer, process binary/ordered argv/full env/cwd/stdin, managed home,
Curator fragment record, exec guard, closed restart template, resume intent,
session metadata and policy projection. Its `permission_mode` is the frozen
`native` constant; `execution_profile` distinguishes standard and yolo.
This CIP does not reinterpret that constant as permission recomputation.

The same section requires absolute binary/cwd/home, limits source paths to
4096 bytes, limits projected lookup names to 64 sorted unique names, and
bounds the object to 1 MiB and nesting depth to 16. Its remaining argv,
env, literal and versioned-data bounds also remain requirements. Attached
or piped stdin is unsupported in that phase. The private receiver uses
plan stdin, terminal fd3 and status fd4; status is length-prefixed JSON,
with a 64 KiB record bound and a closed diagnostic vocabulary.

The launcher owns composition and waits; the receiver owns terminal handling,
deadlines and completion. Malformed status is a protocol error; a truncated
clean stream is unavailable. Receiver exit alone is not a typed refusal.
Descriptor ingress is clear, then the receiver marks fd3/fd4 close-on-exec
before starting descendants (curator-agent-launcher/SPEC.md §4.9).

Section 10 specifies a separate, unimplemented target: a narrow one-shot
`curator-run exec --plan-fd N` under the dispatcher and agent-account
launcher. It is not today's local interactive receiver or a shipping
alternative to the unavailable hosted route (§§10, 10.1–10.2).

### Receiver scaffold and legacy launch plans

At `b057ef468`, `skill-project-management/tools/board-cli/internal/sessionmanager/hosted_control.go:5–19`
authenticates `POST /v1/hosted/launch-plan`, decodes the request, then always
returns `session_host_capability_missing`. It never reaches provider launch.
`skill-project-management/tools/board-cli/internal/sessionmanager/hosted_control.go:22–32` checks protocol/build/schema compatibility but then
refuses even if a peer claims capabilities. `skill-project-management/tools/board-cli/internal/sessionmanager/hosted_types.go:8–24` reserves
control protocol 9 and schema `1.0.0`, advertising an empty capability list.

`skill-project-management/tools/board-cli/internal/sessionmanager/hosted_decode.go:19–100` bounds JSON, rejects duplicate keys, non-object
roots, trailing content, invalid UTF-8, prohibited numbers and excessive
depth. `skill-project-management/tools/board-cli/internal/sessionmanager/hosted_decode.go:274–302` checks the request shape, dispatch,
patterns and known-plan constraints and requires null network/host bundle.
It does not execute the process or establish content-digest authenticity.
The presence of a digest-shaped string is not digest verification.

The older plan is a separate contract:
`skill-project-management/tools/board-cli/internal/sessionmanager/launch_plan.go:16–34,74–86`
defines `agents-infra.primary-session-launch-plan`, interactive/managed-host/
managed-client argv variants and resolved settings. Its decoder rejects
unknown fields and trailing content (`skill-project-management/tools/board-cli/internal/sessionmanager/launch_plan.go:170–179`). Importing
that legacy plan is not importing the complete §4.9 process environment.

`skill-project-management/tools/board-cli/internal/sessionmanager/hosted_errors.go:10–54` supplies
existing launch, host, policy and resume refusals, with registry exit classes
1, 2, 6 and 16. Recognizing a refusal never activates its operation.

### Runtime process ownership and an evidence discrepancy

Claude's production host starts a composed executable with cwd and a
host-built environment under `pty.StartWithSize` in
`skill-project-management/tools/board-cli/internal/sessionmanager/claude_host.go:700–729`.
The PTY master belongs to the daemon; its loss on daemon replacement is
explicit in `skill-project-management/tools/board-cli/internal/sessionmanager/claude_host.go:822–823`. These facts do not show that the
existing factory already executes a hosted payload's exact environment.

Codex reserves a loopback endpoint, adds native-goal disabling and `--listen`
to managed-host argv, prepares a private home, and starts a private app-server
with a daemon-derived environment and substituted `CODEX_HOME`
(`skill-project-management/tools/board-cli/internal/sessionmanager/codex_host.go:73–98,161–189`).
`skill-project-management/tools/board-cli/internal/sessionmanager/codex_host.go:1572–1616` creates `codex-home`, renders `config.toml`, and
links native `auth.json` when available. `skill-project-management/tools/board-cli/internal/sessionmanager/codex_host.go:1648–1678` copies a
selected config-key set and adds project trust and tool policy. This is
current behavior to replace on the Curator hosted path, not a reusable
Curator home-content specification.

**Pinned code corrects one premise of the brief.** At the requested commit,
`skill-project-management/tools/board-cli/cmd/tb-sessiond/main.go:130–135` already registers
`musepty.NewMusePTYHostFactory()` alongside Claude and Codex.
`skill-project-management/tools/board-cli/internal/sessionmanager/musepty/muse_pty_launch.go:143–168`
provides that factory; `skill-project-management/tools/board-cli/internal/sessionmanager/musepty/muse_pty_host.go:92` describes starting an already
composed plan. The brief and swarma-session-host r13 §1.1 say Muse is not
registered. The code establishes registration; it does not establish hosted
admission, which remains closed at `skill-project-management/tools/board-cli/internal/sessionmanager/hosted_control.go:18–19`.
The implementation leaf must verify and reuse registration, not add a second
factory. The MSP host is not the proposed substitute for `musepty`.

### Authentication, homes and target ownership

The current control handler compares a bearer credential in constant time
(`skill-project-management/tools/board-cli/internal/sessionmanager/control.go:439–447`). The daemon
writes it to its private token file (`skill-project-management/tools/board-cli/internal/sessionmanager/daemon.go:189`); clients read that
file (`skill-project-management/tools/board-cli/internal/sessionmanager/client.go:123`) through the mode-0600 reader
(`skill-project-management/tools/board-cli/internal/sessionmanager/client.go:970–978`). swarma-session-host/spec/session-host.md §1.1 states
the resulting boundary: another process of the same OS user can use it.
This is neither per-process identity nor cross-account authorization.

Curator's current command dispatch has resolve/status/config/migrate/unmanage,
not `materialize` (curator/cmd/curator/env.go:63–89 at `00fec196`). Resolve
has `--repair` (same file:124–149). `env materialize --into <dir>` is thus
a dependency proposed by CIP-0014 and owner decision 2026-10-15 (D5), not
a command this source snapshot already provides.

curator-spec/protocol/environments.md §7.4 at `d34d8a6` defines credential
passthrough and Codex storage selection; §9 covers managed resolution.
The newer owner record reports Claude Code 2.1.299 on macOS 15 and Muse
1.4.8 on macOS 27. It distinguishes file and Keychain login and leaves Muse
refresh writes unmeasured. Those are supplied measurements, not tests rerun
here; no new CLI-version support range is inferred from them.

swarma-session-host/spec/session-host.md §1 ownership table assigns today's
and SH1 PTY/private app-server to the board daemon; the SH2+ target assigns
it to a per-session runner under the agent account. Section 2.1 explicitly
keeps the hosted route closed during extraction. This CIP proposes a later
local compatibility increment, requiring an explicit amendment of that
statement; it must not be mislabeled behavior-preserving SH1 extraction.

## Design

### Options considered

#### Receiver and selection

| Option | Mechanism | Pros | Cons | Security |
|---|---|---|---|---|
| Wait for dispatcher | Keep both production gates shut until the cross-account path qualifies | One eventual platform route | Delays the required infrastructure exit | Stronger target boundary, but no local hosted capability |
| Local board receiver | Explicit hosted selection uses the board's existing daemon and control socket | Reuses session lifecycle now; fits D2/D3 | Maintains an interim local backend | Same-user bearer boundary; no account isolation claim |
| Execute through legacy wrappers | Launcher calls `task-board claude|codex` and lets them compose again | Small initial wiring | Loses exact-plan ownership and leaves Muse inconsistent | Ambient env and second composition can change the admitted launch |

Recommend the local board receiver, consistent with owner decisions
2026-10-15 (D2) and (D3). Legacy wrappers remain supported independently.

#### Codex process description

| Option | Mechanism | Pros | Cons | Security |
|---|---|---|---|---|
| Send interactive argv | Receiver converts a CLI launch into an app-server | Reuses legacy conversion | Contradicts execution of the composed process | Receiver can add settings outside the digest |
| Complete app-server plan | Receiver prepares resource identities first; caller then seals app-server argv/env | Exact invocation is reviewable; reuses local client transport | Requires bounded preparation and new wire version | Resource binding and one-use admission must be verified |
| Use app-server stdio | Caller plans stdio server; daemon mediates every client operation | Avoids loopback endpoint allocation | Replaces current managed-client attachment contract | Potentially narrower transport, but not qualified by current code |

Recommend a complete app-server plan. Preparation allocates resources, not
profile settings; it does not authorize an agent process. Transport changes
can be separate improvements after qualification, not assumptions in v0.

#### Session-home writer

| Option | Mechanism | Pros | Cons | Security |
|---|---|---|---|---|
| Reuse live managed home | Point the runtime directly at resolve's home | No copy | Violates D4; later repair changes running input | Digest check cannot prevent subsequent in-place mutation |
| Receiver copies selected files | Maintain a daemon-side profile-file list | Reuses current Codex pattern | Duplicates Curator ownership; list drifts | Omitted policy or copied secrets can escape intended semantics |
| Curator materializes snapshot | Caller asks Curator to populate a reserved private session directory | One content authority; satisfies D1/D4/D5 | Requires CIP-0014 and explicit policy layering | Manifest verification plus bounded session-owned overlay |

Recommend Curator materialization. A runtime can write native state in its
private session home; the initial snapshot is immutable evidence, not a
promise that a provider never writes to its runtime directory.

### Recommendation

#### H1. Explicit local mode and receiver identity

For the initial local release, `--hosted` explicitly selects the local
board backend. Native selection never probes it; receiver failure never
falls back to native. Preserve the existing host precedence, lock scope,
repeated-selector errors, `ax` conflict and network refusals from §4.8.
Do not silently turn an existing native default into hosted execution.

Introduce a versioned launcher backend selector with proposed values
`local-task-board` and, only when later implemented, `dispatcher`.
Its exact config location must be published with the launcher amendment;
it is not an existing v3 member. Absence in the first local release selects
`local-task-board` only after hosted mode has been explicitly requested.
That meaning stays stable on later upgrades. Selecting `dispatcher` before
it exists refuses; it does not select local execution instead.

Existing operator hosted defaults need an explicit local-backend migration
before they can use the new receiver. Machine hosted defaults retain
`session_host_default_not_ready` until upgrade-without-hangup is qualified.
This avoids treating old dormant defaults as consent to a newly available
backend. An explicit `--hosted` remains usable without enabling defaults.

The launcher starts the private task-board receiver command specified by
§4.9. That command is a transport client, not a second composer. It resolves
the authoritative board, connects to that board's existing control socket,
authenticates using the private token, and mediates terminal attachment and
status. The receiver executes in `tb-sessiond`, not in a new launcher-owned
session daemon. It does not accept an arbitrary repository-provided socket
or execute a board-provided binary to discover its endpoint.

Same machine and same OS user are admission requirements. Board identity,
owner binding and private state ownership must agree with the selected
board's normal session-management rules. This proposal does not let a
remote board service submit executable plans to the local socket.

#### H2. Preparation, composition and admission ordering

A complete app-server plan needs endpoint, private-home and session identity
before its digest can be computed. Do not solve this by appending options
after digest verification. Add a bounded preparation operation over the
same authenticated control socket, jointly versioned with hosted admission.
The following are proposed semantics, not existing endpoint names or fields.
Terminal/stdin and network gates run before preparation or receiver contact.

1. The caller identifies board, owner, runtime and intended session operation.
   The receiver checks local scope and protocol, then reserves a private
   session directory, session identity and generation. For Codex it also
   allocates the private app-server endpoint and transport policy values.
2. Preparation returns an opaque reservation and the exact resource values
   that composition needs. Its record binds board, owner, runtime, generation,
   expiry and allowed writable locations. Preparation runs no provider, no
   profile resolution and no arbitrary preparation command from the caller.
3. The caller runs `curator env materialize <env> --into <reserved-dir>` using
   the selected profile. Curator owns all home population and verification.
   The result identifies the snapshot, manifest and relocated launch fragment.
4. agents-management builds the runtime's hosted form from that fragment,
   requested model/effort, resume intent and the prepared transport values.
   `curator-run` composes the full environment and seals the complete plan.
5. The private receiver transports the plan and reservation to the daemon.
   Admission verifies the version, runtime capability, digest, snapshot,
   reservation, policy and ownership before any process can start.
6. The daemon records provenance and the admitted generation durably, consumes
   the reservation once, applies only the declared session-policy overlay,
   and starts the exact planned process. Attachment follows readiness.

Failure or cancellation before admission releases the reservation and leaves
no running provider. A bounded expiry handles an abandoned caller; expiry
cannot authorize reuse. Crash recovery must distinguish prepared, admitted,
started and unknown outcomes. Retrying an admitted reservation may return
its recorded result, but may not launch a second process. Uncertain process
liveness is not absence and does not authorize a fresh start.

Endpoint reservation does not prove an app-server will successfully bind.
If the current loopback transport releases an allocation socket before
provider bind, that handover has a residual race. Bind/readiness failure
refuses the start and records its outcome; the daemon must not choose a new
endpoint or rewrite argv. Retrying requires fresh preparation and a new plan.
The same-user boundary limits the claim; it does not remove the race.

#### H3. Versions, capabilities and exact execution

The frozen `1.0.0` shape is not extended in place. Recommend a new hosted
plan/capability contract `2.0.0` and control protocol 10, published together
by launcher and receiver. These are proposed successor versions, not current
advertisements. Protocol 9 and legacy routes keep their old meaning.

The capability response must distinguish runtime and operation. The first
local release requires every cell in this semantic matrix; wire token spelling
is successor publication work, not a claim about today's empty list.

| Runtime | Prepare / launch | Attach / resume | Goal application |
|---|---|---|---|
| Claude Code | Exact-plan PTY | PTY attach; typed session restart | Existing acknowledged revision adapter |
| Codex | Exact-plan private app-server | Private managed client; typed thread resume | Text directives; native goals disabled |
| Muse | Exact-plan musepty | PTY attach; typed Muse resume | Qualified musepty goal adapter |

A registered factory alone is insufficient.
Use closed per-runtime capability tokens in the existing list model or a
successor structured matrix, chosen and frozen jointly before implementation.
Advertise only operations supported by the actual adapter and provider build;
unknown tokens confer nothing. The public local release is gated on the
required three runtime rows, even if internal builds expose partial support.

Admission checks both capability schema and control protocol, supported plan
version, compatible producer/restart data, build compatibility and same-user
local scope. Do not weaken the current build-skew refusal by restarting a
live daemon automatically. Replacing the daemon can destroy PTY sessions.

Decode strictly, then recompute CCJ-1 SHA-256 over the received plan with only
`content_digest` omitted and compare it to the supplied value. Include every
successor preparation binding, snapshot reference, runtime discriminator and
policy input under that digest. A matching digest proves byte consistency,
not trusted authorship: an authenticated same-user caller can compose one.
Retain independent policy and reservation checks even for matching digests.

Exec uses `process.binary`, ordered `process.argv`, complete `process.env`,
`process.cwd`, declared stdin mode and the plan-selected home. No shell
concatenation, PATH re-resolution, ambient daemon env merge, new profile
resolve, default selection or retry-time argv conversion is allowed.
Session delivery variables must be allocated in preparation and included
in the plan, not appended by a legacy environment builder after admission.

The receiver may reject a plan whose policy it cannot enforce. It may not
silently repair or normalize that plan into a different process. Geometry,
attachment descriptors, process-group ownership and lifecycle bookkeeping
are host concerns; they confer no permission to add runtime arguments.
Validate the imported exec guard at the actual start boundary using the
shared module contract; never claim an imported plan is an in-hand build.

#### H4. Snapshot provenance, resume and goals

Persist the plan content digest, producer version/commit, runtime, Curator
profile name/pin/fragment digest/system-module fact, materialization manifest
identity, prepared resource identity, policy overlay identity and resulting
session generation. The fragment record describes the original Curator
input and its snapshot relocation; do not relabel a modified receiver home
as the untouched managed home. These are private session records.

Curator owns verification of materialized content and its supported native
credential strategy. The receiver verifies the materialization receipt and
binding and enforces path ownership/confinement, not a parallel list of
required profile files. If CIP-0014 lacks a verification API suitable at
admission, add it there before claiming this property.

Fresh launch verifies the initial materialization. Restart verifies its
persisted receipt and Curator-defined protected inputs; native writable state
is validated by the runtime, not compared with its prelaunch digest. Curator,
not the receiver, defines that separation and its resume verification API.

The initial manifest covers Curator's output before runtime writes. A separate
receipt identifies the receiver's bounded overlay. Neither receipt may be
updated to bless later provider writes as original snapshot bytes. Resume
uses the persisted session home and provenance, not a fresh live profile.
Repairing or selecting another profile does not mutate an active snapshot.

Elevate resume selectors through agents-management's typed grammar before
composition. Resolve latest/handle/native identity under board, owner,
location, runtime and generation checks. Refuse missing, ambiguous,
unreadable, mismatched or liveness-unknown records distinctly. A failed
resume never starts a new session. Restart uses the persisted closed restart
template and typed identity substitution, not reparsing the old native tail.

The session host retains board goal binding, revision ordering and native
reflection through its existing adapters. Launch success is not a claim
that a goal was acknowledged. Bind a requested goal before ordinary work
and report reflection failure through the existing goal vocabulary; do not
inject an unacknowledged goal as if applied. A session without a goal can
launch; goal absence is not itself failure. Codex retains text-directive
goals with native goals disabled until a separately adopted contract changes
that behavior. Every such disabling argument must already be in its plan.

#### H5. Runtime adapters and exact writers

| Runtime | Planned process and host ownership | Curator writes | Receiver writes |
|---|---|---|---|
| Claude Code | Final Claude argv/env under daemon-owned PTY | Snapshot and manifest; relocated `CLAUDE_CONFIG_DIR`; credential strategy | Private session records, trust/input/goal state and declared host policy |
| Codex | Final `codex app-server` form with prepared endpoint under daemon ownership | Entire initial private `CODEX_HOME`, manifest and credential strategy | Separate tool-policy/trust record and session/control records |
| Muse | Final Muse argv/env under registered `musepty` PTY | Snapshot/XDG layout, manifest, credential strategy and explicit `root_context` | PTY/session records, input/goal state and declared host policy |

Claude must consume the plan environment, not `claudeHostEnvironment`'s
ambient daemon environment. Existing PTY readiness, detach and terminal
ownership behavior can be reused through an adapter for the new contract.
The adapter must not add plugin, context or remote-control tokens. Session
metadata and any remote-control intent come from the same admitted plan.
Owner decision 2026-10-15 (D11) does not require Remote Control for swarm
agents; this CIP adds no requirement to enable it for local hosted launches.

Codex is an app-server plan from the start, not interactive CLI argv plus
receiver conversion. agents-management supplies its hosted process form,
including the prepared endpoint, native-goal setting and profile-derived
`-c key=value` settings. The receiver retains its private managed-client
attachment transport, but cannot expose that endpoint as a public service.
The terminal belongs to the attached client; the app-server is not wrapped
in a PTY to mimic an interactive Codex invocation.

For Codex, the receiver allocates the private session folder, then Curator
materializes directly into the reserved private home. The caller never
points `CODEX_HOME` at a live managed home. The receiver does not invoke
`preparePrivateCodexHome` to select/copy configuration keys or link auth;
Curator is the only authority for those contents, per owner decisions
2026-10-15 (D1), (D4) and (D5). Profile-level settings and inheritance reach
the process through launch `-c` settings, per owner decision 2026-10-15 (D13).
The receiver must not turn that ownership into profile-config rewriting.

The only receiver policy overlay is session-owned tool policy and trust:
for the current Codex adapter this includes `sandbox_mode`,
`approval_policy` and the selected workspace trust entries. Publish its
closed key set and precedence in the successor contract. It cannot change
models, profile settings, instruction paths, MCP declarations or login.
Do not infer that an arbitrary `-c` table replaces an existing MCP table;
the current host's merge warning at `skill-project-management/tools/board-cli/internal/sessionmanager/codex_host.go:1619–1626` still applies.
Context-builder confinement is a separate contract and is not admitted by
this local primary-session mode.

The receiver writes the admitted tool-policy record beside the home, never
into its `config.toml`. Preparation supplies that closed policy projection;
agents-management includes its startup `-c` overrides in the app-server argv
before the plan is sealed. The receiver applies the same declared policy
through supported thread APIs; it cannot append launch overrides itself.
The runtime owns any native writes to `config.toml`. Curator materializes its
initial bytes; neither launcher nor receiver subsequently rewrites them.
This preserves owner decision 2026-10-15 (D13) in private snapshots too.

The startup overlay must remain effective when a client attach causes cold
resume; a thread/start-only override is insufficient. Qualification must
prove this using the real supported app-server release, including conflicting
native config and repeated attach. The current code does not establish that
startup overrides satisfy it. If native startup/API layering cannot enforce
the split, the implementation leaf stops for a supported mechanism decision;
rewriting config or silently weakening policy is not an admitted fallback.

Curator decides whether Codex receives `cli_auth_credentials_store="file"`
and Muse receives `TBH_CREDENTIAL_BACKEND=file`; agents-management applies
the decision in argv/env, per owner decision 2026-10-15 (D9). The receiver
neither logs in nor writes or reconnects `auth.json`. Runtime credential
refresh is native runtime behavior, not receiver snapshot maintenance.
Curator owns any shared-login exception to ordinary regular-file snapshots;
CIP-0014 must make that exception explicit rather than the receiver inventing
one. Muse refresh remains unmeasured, per owner decision 2026-10-15 (D10).

Muse must use the existing `musepty` factory registration and adapt its launch
and restore paths to the successor plan. The daemon must advertise Muse only
when this real registered path passes qualification; an MSP-only capability
or a test-only factory does not satisfy D2. agents-management reads explicit
fragment `root_context`, per owner decision 2026-10-15 (D12), and must not
inspect Curator's file layout to infer it. The launcher environment registry
and system mapping must admit `muse`; the older §3 table is not sufficient.

#### H6. Spawn boundary

`task-board spawn` is out of scope: these are headless board runs already
carrying a Curator fragment through the spawn composer, rather than terminal
primary sessions entering this receiver. The production spawn gate requires that fragment at
`skill-project-management/tools/board-cli/internal/spawn/spawn.go:434–442`;
its resolver is in `skill-project-management/tools/board-cli/internal/spawn/curator_fragment.go:126–146,234`.
A gap remains: carrying a fragment alone does not prove a per-run immutable
snapshot, so those paths need separate adoption of CIP-0014/D4, with their
own entry-point evidence. This proposal neither reroutes spawns through the
terminal-only hosted contract nor claims that snapshot gap is resolved.

## Security considerations

The scope is the same OS-user trust boundary as current local board session
commands. A process that can read the control token can ask the daemon to
launch code as that user. The bearer is not delegated execution authority,
producer signing, a per-process identity or a boundary against hostile
same-user processes. Keep token, socket/endpoint metadata, preparation records,
plans, manifests and logs in private session state; never place them in the
repository or expose the socket over a network.

Absolute binary paths and content digests are necessary integrity controls,
not proof that an executable is trustworthy. Recheck exec-guard and snapshot
bindings immediately before start; refuse unreadable or drifted evidence.
Private directories and descriptor-based/no-follow operations should prevent
accidental symlink substitution. Same-user mutation between validation and
use remains a residual unless immutable handles or equivalent enforcement
close it. Do not claim the local release implements the cross-account
platform's executable attestation or sandbox.

A hostile project may supply instructions or configuration to the agent.
It must not select a control endpoint, move the session home, promote trust,
change preparation ownership or inject daemon env. Session policy can narrow
or refuse the plan; it cannot silently broaden it. Permission mode follows
the admitted caller plan, not the terminal's presence or a daemon default.

The complete process env may include approved credential values. Transport
it privately; redact diagnostics and persist only the secret-safe execution
record allowed by the secret policy. A digest does not justify storing raw
env, argv or credentials in board outcomes. Resume must require fresh
resolution of secret inputs where raw persistence is prohibited and refuse
if the admitted policy cannot be reconstructed without guessing. The caller
performs any fresh secret resolution and seals a new restart plan bound to
the same snapshot; the daemon never resolves credentials or mutates the
previously admitted process to refresh them.

Materialization provides initial session isolation from Curator repair, not
isolation from the same user or native provider writes. Credential refresh,
Keychain availability and cleanup of abandoned snapshots remain operational
risks. Receiver cleanup must never follow links into a native or managed home.
No raw credential copies, login probes or new secret-persistence mechanisms
are authorized merely by adopting the local hosted transport.

The daemon still owns PTY lifetime. Daemon replacement may kill Claude or
Muse sessions; this CIP must not market upgrade-without-hangup or enable
machine hosted defaults before that property is established independently.

## Compatibility and migration

The existing `task-board claude|codex` commands keep working. Making them thin
wrappers over the same prepared-plan API is recommended to reduce duplicate
composition, but is not a prerequisite or a new requirement on existing
users. Legacy converters stay separate from the exact-plan execution adapter;
reusing a factory does not justify ambient environment inheritance.

Roll out Curator materialization first, then the hosted planning and receiver
contracts together, and finally activate production lookup. A mixed old/new
installation refuses protocol or capability admission without restarting the
daemon. Keep both old refusal scaffolds and legacy commands testable during
migration. Do not accept new fields under frozen schema `1.0.0`.

The initial public support set is Claude, Codex and Muse, per owner decision
2026-10-15 (D2). Partial development capabilities are not a supported release.
Operator defaults require explicit backend migration; machine defaults remain
gated. No migration rewrites homes or starts a session during a status read.

When dispatcher/session runners arrive, keep Curator materialization,
fragment provenance, caller composition, exact process semantics, typed
resume, policy admission and refusal classification. Replace local preparation
and transport with dispatcher allocation and admitted runner resources.
The caller must explicitly select that backend; availability is not consent.

Owner decision 2026-10-15 (D6) then requires a plan-covered snapshot archive:
the caller materializes, dispatcher relays it, and agent-account
`curator-run exec` verifies/unpacks it read-only. Local home paths and the
board bearer do not travel as remote authority. The session runner takes
over PTY/app-server ownership; the service host retains logical lifecycle.
Do not copy local control protocol 10 directly onto the unpublished dispatcher
wire or bypass its broker, account and lifecycle admission contracts.

## Specification changes

These normative sketches become binding only through later adoption. The
implementation leaves must publish concrete schemas, capability tokens,
preparation framing and conformance vectors in lockstep. No schema file or
normative protocol document is changed by this Draft.

### Launcher §3 and §4.6 amendment

Add canonical `muse` to the environment/system mapping. `--hosted` MUST route
the complete composed plan to the selected receiver, without invoking a
legacy primary-session composer. Native and legacy `ax` routing MUST retain
their existing selection and conflict semantics. Help MUST describe hosted
support as local, same-user, and gated on receiver capability.

### Launcher §4.8 amendment sketch

Replace the unconditional dispatcher-wait refusal with explicit local backend
selection H1. An explicitly selected hosted launch MUST use the selected
board's `tb-sessiond` through its existing authenticated control transport.
A missing receiver MUST refuse `session_host_missing`; an unreachable one
MUST refuse `session_host_unavailable`. Neither condition permits fallback.

The launcher MUST check protocol and runtime-specific operation capabilities.
It MUST support Claude Code, Codex and Muse as the initial public hosted set.
Unsupported runtime and missing capability remain refusals, not requests to
construct another runtime's process. Machine-default, `ax`, network and
terminal/stdin gates MUST remain as specified unless separately amended.

### Launcher §4.9 amendment sketch

A successor plan MUST cover the complete hosted process, runtime,
preparation binding, snapshot identity and closed host-policy overlay with
`content_digest`. Codex MUST describe an app-server process. Preparation
MUST precede materialization and composition where resource values affect
argv/env/home; launch admission MUST NOT fill in process placeholders.

The private receiver command, terminal/status descriptor isolation, status
framing, registry messages and redaction MUST preserve the current boundary.
Terminal stdin remains the local supported mode; attached/piped payload
stdin MUST refuse until separately specified. Status records MUST NOT expose
native argument values or turn provider stderr into a typed control error.

### Receiver amendment sketch

Replace unconditional capability refusal only for the newly versioned,
qualified local path. The route MUST authenticate, strictly decode, verify
the actual content digest and materialization binding, validate reservation,
board/owner/generation, runtime capabilities, exec guard and policy, then
record provenance before launch. Old version routes MUST keep their published
semantics; a generic factory registration MUST NOT enable hosted admission.

A receiver MUST execute the exact process and apply only the plan-declared
session overlay. It MUST NOT resolve/repair profiles, choose settings,
reconstruct argv/env or maintain a home-content list. It MUST preserve typed
resume errors and goal acknowledgment semantics. Unknown or unreadable
liveness MUST NOT be treated as a new-session opportunity.

| Condition | Existing refusal to reuse | Exit |
|---|---|---:|
| Malformed plan, digest mismatch or invalid preparation binding | `launch_plan_invalid` | 2 |
| Unsupported negotiated version | `session_host_protocol_unsupported` | 6 |
| Required runtime operation unavailable | `session_host_capability_missing` | 6 |
| Runtime outside supported set | `session_host_provider_unsupported` | 6 |
| Different account or unsupported execution scope | `session_host_scope_unsupported` | 6 |
| Missing terminal / unsupported stdin | `session_host_terminal_required` / `session_host_stdin_unsupported` | 6 |
| Enforced policy or snapshot drift | `policy_refused` | 16 |
| Secret-bearing forbidden metadata | `secret_policy_violation` | 16 |
| Missing/ambiguous/unreadable resume | `session_resume_not_found` / `session_resume_ambiguous` / `session_resume_unreadable` | 1 |
| Location/identity mismatch | `session_resume_location_mismatch` / `session_resume_identity_mismatch` | 1 |
| Liveness cannot be established | `session_liveness_unknown` | 1 |

Use only registry-permitted detail fields/reasons; do not invent a new reason
string under an old envelope. An empty allowed details object is preferable
to a private parser error. Any new diagnostic must be separately registered
with both peers before emission. The successor admission/preparation wire is
still publication work; this table does not claim it already exists.

### Decision and extraction amendments

Adopt a decision recording H1–H6, snapshot ownership and all-three-runtime
release gating. Amend swarma-session-host's SH1 compatibility notes to name
this later local increment separately from extraction, and correct its Muse
registration statement against the chosen source pin. Leave §10 dispatcher
activation gates intact; local admission supplies no evidence for them.

## Implementation plan

Sizes are relative leaves, not elapsed-time promises. Each repository owns
its changes; this CIP authoring task changes only this file.

1. **S — curator-spec + curator-agent-launcher:** adopt the ownership/selection
   decision and publish successor schema, capability matrix, preparation
   lifecycle, config spelling and vectors. Resolve the publication questions
   below before enabling a runtime. Include old/new compatibility vectors.
2. **M — curator:** implement CIP-0014 materialization and verification into
   reserved directories, with manifests, relocation and explicit credential
   exceptions. Prove profile repair cannot alter a running session snapshot.
3. **M — skill-agents-management:** add hosted process forms for Claude,
   Codex app-server and Muse PTY, typed restart/resume and prepared-resource
   inputs. Apply D9/D12/D13 at composition, with no profile-file inspection.
4. **M — skill-project-management:** add authenticated bounded preparation,
   one-use reservations and successor admission with digest/snapshot checks,
   durable provenance and fail-closed crash outcomes. Keep legacy gate tests.
5. **M — skill-project-management:** adapt Claude/Muse PTY execution to exact
   argv/env and verify the existing Muse factory registration at the real
   daemon construction site. Preserve attach/detach, resume and goal contracts.
6. **M — skill-project-management:** adapt Codex's private app-server path,
   separating Curator population from the separate policy record/launch overlay,
   preserving snapshot config and proving policy survives client attach/cold resume.
7. **M — curator-agent-launcher:** replace dormant production lookup with
   local receiver discovery, preparation/materialization/composition and
   versioned handoff. Release only with all three runtime rows qualified.
8. **S — skill-project-management + curator-agent-launcher:** document explicit
   default migration, mixed-version refusals and operational daemon lifetime.
   Recommend wrapper convergence without making it an activation dependency.
9. **M, later — swarma-dispatcher + curator-agent-launcher + curator-spec:**
   retain caller composition and archive identity while changing allocation,
   executor and transport to the dispatcher/runner contracts. No local-backend
   success may be reused as cross-account qualification evidence.

## Test plan

These are required future implementation tests, not executed results from
this documentation task. They must drive production `curator-run`, the private
receiver command, the actual control route and registered runtime factories;
helper-only tests are insufficient. Use the repositories' Go harnesses and
existing provider fixtures, plus bounded qualified-release smoke tests.

### Production-entry properties and negative cases

| Proposed test name | Property and negative cases |
|---|---|
| `TestLocalHostedSelectionIsExplicit` | Native causes zero receiver contacts; unreachable hosted refuses; absent/read-failed config differ; dispatcher selection never falls back |
| `TestHostedNegotiationRequiresRuntimeOperations` | Wrong version, forged capability claims, missing per-runtime launch/resume and unregistered adapters refuse before provider I/O |
| `TestHostedAdmissionRecomputesWholePlanDigest` | Change each process/fragment/snapshot/policy/preparation member; recompute canonical bytes; reject duplicate/trailing/oversized JSON and stale digest |
| `TestHostedReservationIsBoundAndConsumedOnce` | Wrong board/owner/runtime/generation, expired reservation, replay and crash between record/start cannot create a second execution |
| `TestHostedProcessMatchesAdmittedPlan` | Capture the executed binary, ordered argv, env, cwd and home for every runtime; poison daemon env and legacy defaults; no silent recomposition |
| `TestHostedSnapshotHasOneContentAuthority` | Real materialize entry, manifest validation and relocation; mutate managed home after snapshot; forbid receiver copying/relinking auth or selecting profile files |
| `TestHostedCodexPlansAppServerBeforeAdmission` | Real factory sees prepared endpoint/home and planned app-server flags; collision refuses without endpoint/argv retry mutation |
| `TestHostedCodexOverlayPreservesConfigAndPolicy` | All materialized config bytes unchanged by receiver; no native/managed config write; deny overlay escape; same tool policy after attach and forced cold resume |
| `TestHostedMuseUsesRegisteredPTYAndRootContext` | Daemon construction reaches actual musepty factory; explicit root_context honored; no layout inference or MSP substitution |
| `TestHostedResumeCannotBecomeNewLaunch` | Missing, unreadable, ambiguous, wrong-location, wrong-identity and unknown-liveness cases refuse; restart uses recorded template/home |
| `TestHostedGoalsRequireAcknowledgedRevision` | No-goal launch succeeds; stale/unacknowledged goal is not applied; verify runtime-specific reflection and ordering |
| `TestHostedTransportKeepsPrivateDescriptors` | Real descriptor ingress, close-on-exec, grandchild isolation, malformed versus truncated status, secret-safe errors and process exit preservation |

The property matrix must run for every runtime where its property applies;
report measured rows passed/rows required, with named skipped or unknown rows.
A registered factory, accepted digest or login-present row is not a substitute
for a process/goal/credential property it does not measure.

### Narrowing mutants worth killing

| Mutant | What it narrows the gate to | Named test required to fail | Survival bound |
|---|---|---|---|
| Verify digest only for binary/argv | Ignores env, snapshot and policy integrity | `TestHostedAdmissionRecomputesWholePlanDigest` | If it survives, those excluded fields are unproven |
| Check reservation owner but ignore generation | Same-owner stale reservation admitted | `TestHostedReservationIsBoundAndConsumedOnce` | Generation/replay protection unproven |
| Check only Claude capability | Other runtimes borrow Claude admission | `TestHostedNegotiationRequiresRuntimeOperations` | Codex/Muse operation admission unproven |
| Overlay env only when daemon lacks a name | Ambient daemon env wins collisions | `TestHostedProcessMatchesAdmittedPlan` | Exact env proven only for absent ambient keys |
| Copy policy into snapshot config for one key | Allows a receiver write to a runtime-owned file | `TestHostedCodexOverlayPreservesConfigAndPolicy` | Immutability unproven for that key |
| Set Codex policy only on thread/start | Cold resume loads weaker policy | `TestHostedCodexOverlayPreservesConfigAndPolicy` | Policy proven only for initial thread creation |
| Refuse missing resume but retry unreadable | Read failure starts ordinary work | `TestHostedResumeCannotBecomeNewLaunch` | Missing-record handling only; read-error bound unproven |
| Read Muse context from layout for one value | Explicit fragment ignored in that case | `TestHostedMuseUsesRegisteredPTYAndRootContext` | Root-context support limited to coincident layout |

None of these mutants was executed for this Draft. Future evidence must name
the actual failing test per killed mutant, report every survivor, and retain
its stated bound. A proposed test name here is not measured mutant evidence.

Qualification starts on supported macOS and Linux targets, using the same OS
user and disposable session directories. Record exact provider and toolchain
versions, transport, environment identity and cleanup outcomes. Unsupported
OS/runtime combinations refuse capability rather than borrowing another
platform's green result. Native login/Keychain and token refresh need separate
Curator qualification; the supplied Claude Code 2.1.299 / Muse 1.4.8 findings
do not qualify unmeasured releases or refresh behavior.

For the documentation leaf, verify template sections, source citations,
required-content coverage, public hygiene and exactly one new CIP file.
Run the repository's existing validation/property suites and retain real exit
codes. Do not create implementation tests or alter normative artifacts merely
to make a Draft design appear operational.

## Open questions for the operator

1. **Successor wire publication.** Use plan/capability `2.0.0` with control
   protocol 10, or introduce a separate local contract family while preserving
   version 9. Recommend the successor versions: the frozen Claude-only payload
   must not silently gain preparation, snapshot and runtime semantics. Publish
   exact capability tokens/matrix and preparation schemas jointly before code.
   A new family isolates interim code but duplicates negotiation; a major
   version reuses transport but requires explicit peer upgrade. Both must
   reject unknown versions without broadening the same-user trust boundary.
2. **Backend config spelling.** Add a launcher-level `hosted_backend` member
   or a versioned per-environment backend member alongside `host`. Recommend
   per-environment selection, following host precedence/locks, with explicit
   `local-task-board` migration and stable absent-selection semantics in H1.
   Dispatcher selection must remain a separate opt-in when it ships.
   One global member is simpler but cannot select by environment; scoped
   selection fits existing locks but adds config validation. Both must keep
   repository data unable to select the control endpoint.
3. **Codex policy layering.** Qualify native startup `-c` overrides plus
   supported thread APIs, or qualify a separate native policy-file mechanism
   if the supported release offers one. Recommend startup overrides composed
   before admission, with the policy record outside the snapshot and proof
   across cold resume. If neither works, stop activation for a supported
   mechanism decision. Receiver rewriting of any runtime `config.toml` is
   excluded by D13, not a third option. Startup overrides reuse native APIs
   but need cold-resume proof; a native policy file separates ownership but
   needs an actual supported API. Both must preserve enforced policy.
4. **Materialization credential exceptions.** Let CIP-0014 expose an explicit
   Curator-owned shared-login strategy, or restrict the first local mode to
   self-contained snapshots with separately prepared login. Recommend the
   explicit strategy, consistent with D1/D5/D9/D10, while keeping the receiver
   unable to invent credential links. Refresh semantics remain unmeasured;
   neither optimistic Muse admission nor local transport proves them.
   Sharing preserves login continuity but couples native refresh writes;
   self-contained login separates state but adds login/refresh lifecycle work.
   Neither permits receiver-owned credential copying or secret diagnostics.

These are publication choices with recommended answers, not permission to
reopen D2 by deferring Codex, wait for dispatcher despite D3, or run against
live managed homes contrary to D4. Adoption must settle their wire-level
form before claiming the local hosted capability.
