# Unresolved questions

## Environment store verification revision-2 proposal

The [unreleased proposal](protocol/environment-store-verification-v2.md) records
structural refusal before repair, retained same-pin/home restoration and a
separate incompatible qualification carrier. Its revision-2 carrier and reader
transition await specification acceptance and a landed pin. Runtime consumer
adoption, all-member hardlink checks, exact post-failure state, both actual reader
directions and retained positive repair qualification remain implementation
gates. Metadata checks do not settle these gates or alter revision-1 claims.

## Opt-in separate managed-home login (Q6)

[Draft Decision 0032](decisions/0032-managed-home-separate-login.md) records the
settled shared-owner default and explicit operator-owned exception. Owner
questions: who may perform remote attended bootstrap, and whether to keep
same-account Codex shared-owner/separate-home combinations unavailable under
CIP-0010 C2 or commission a separate compatible design. Recommended: retain C2.
Lane/home machine-selector grammar, bootstrap exclusion, successor posture and
receiver carriers, protected revocation reads and exact provider qualification
remain publication/activation gates. This draft implements none of them.

## Home-lease consumer publication gates

Owner decision 2026-10-27 settled **refuse**, one profile per Werkstatt and one
managed home per unattended lane in [CIP-0016](cips/CIP-0016-local-hosted-launches.md).
The [home-lease contract](protocol/home-leases.md) requires authoritative manager
and no-start observation; a launcher-forwarded terminal assertion alone is not
accepted evidence. No additional operator choice is pending for that rule.

Before runtime qualification, curator-run must publish its closed manager
registry/status and no-start observation read contract (including process
incarnation and descendant/ownership completion), and its lane/Werkstatt
allocation admission contract. These consumer interfaces and their joint
launcher/fake-manager/real-Curator fixture remain publication/integration gates.
Without the observer, release retains the lease; the operator break path remains
explicit, revision-checked and audited. This spec PR starts no implementation.

## Policy-derived workspace trust activation

Q1 authority and the distinct `policy-grant` event are settled in
[CIP-0020 §2.1](cips/CIP-0020-workspace-trust-ledger.md#21-policy-derived-grants-q1-first-slice)
and [Decision 0031](decisions/0031-policy-derived-workspace-trust.md).
Environments integration, protected command/approval storage, per-release
hook discovery/approval/reload/revocation qualification and command-free
canonical SSH destination evaluation remain delivery gates. The same-UID
tamper limitation remains until CIP-0024 protection. Unattended lanes' default
without the vendor sandbox requires its separate runtime-policy mapping;
project trust grants no bypass authority. None of these gates permits a
package self-grant, hidden prompt or unqualified launch fallback.

## Managed-session profile command PATH publication gates

The [native-first companion](protocol/profile-command-path.md) fixes no-export
and unavailable launch semantics, closed root/receipt schema and independent
verification, interactive protected tools, closed base-PATH predicates and
native state-file provenance. Curator and curator-run still need native
release-pair support and real qualification. Hosted delivery needs a joint
carrier amendment owned by curator-run and the session host, with Curator for
binding: required-understanding request/schema/module pins, PATH/root/receipt
binding, start checks and manager record. `launch-delegated/1` remains closed;
until then hosted commands are explicitly unavailable with a diagnostic and
no refusal for that reason. Caller-local empty provenance proves no final
hosted PATH. Slice B's exact generation-root and lease/GC carrier remains open.
Project `command_environment` plus `path_prepend` still needs a combined carrier.
No-export/empty continuation does not clear `profile_skill_companion_required`;
all-profile native/hosted witnesses and the separate protected-command inventory
companion remain required. Abstract vectors are not runtime qualification.

## Agent stations

[CIP-0024](cips/CIP-0024-agent-stations.md) is Draft. Its operator decisions of
2026-10-22/23 are settled: one account and distinct signer per station, interim
ssh-agent custody with inaccessible keys and UID-restricted sockets, target
Keymaker custody, platform-owned controls checked before start, approved-release
updates, service-enforced orchestrator/owner trust and owner-chat binding,
Swarm/Colony/Swarm cell/Station hierarchy, per-station a2a daemon, retained
fresh-context spawn and the 11-Werkstatt native-project pilot; strict follows
per runtime. Service ownership is split explicitly. Remaining operator questions
are the pilot's initial heavy-run host budget and the authoritative
task-completion/retention horizon
for task-lifetime stations. Service adapters against the pinned
router/FRONT-DOOR baseline, protected profile releases, colony manifest mapping,
Keymaker/broker and native-project qualification are publication gates, not
additional undecided ownership choices.

## Muse managed-context residuals

The revision-1 admission in [environments §§7.1, 7.9, and 10.2](protocol/environments.md)
records the Muse Code 1.4.7 monolithic own-file target, measured foreign
personal-context sources, and target-bound `exec` and interactive exclusion.
Skills discovery, system-prompt discovery, model-visible foreign removal,
and a reproducible size threshold remain unverified. Workspace precedence in
observed conflicts is a residual; `serve` cannot exclude foreign personal
context. The required admission vectors are listed in environments §13 for
delivery with the target and both forms' exclusion argv; existing vectors
do not qualify the added requirements.

**CIP-0017 state.** [The Accepted CIP](cips/CIP-0017-muse-root-context-and-credential-store.md)
resolves the no-root-surface case: omit `root_context`, pass neither exclusion,
and retain the foreign-context residual. Native/unset managed Muse backend
selection resolves to file; explicit Keychain refuses. Still open for later
leaves: exact consumer module tag, exact 1.4.8 exclusion build and P1–P4 replay
before consumer release, token-refresh and concurrent-writer behavior,
Linux/Windows native qualification, and broker rotation/lifetime. The credential
admission is optimistic now; unmeasured exclusion and refresh remain separate.

## Advanced repository mappings decided by transport revision 2

Non-default endpoint ports, operator-declared mirrors and operator-declared
host aliases are now decided normatively by [repository transport revision
2](protocol/repository-transport.md) (source-policy schema 2, additive over
schema 1). Ports are machine-policy endpoint properties stripped before
canonicalization; mirrors require an exact-key `mirror_of` attestation;
aliases resolve only from operator source-policy, never from user ssh/git
configuration.

## Still open: reusable alias registries and user-configuration import

Reusable cross-machine logical alias registries and safe translation of user
`insteadOf`/SSH configuration remain undecided and are rejected. Matching
content alone does not authorize identity equivalence, and user configuration
is usable only through explicit operator admission, unchanged from revision 1.

No source extension implementation or release qualification is claimed. A
future release must assign publication metadata and qualify implementations
against the new schema and semantic vectors before advertising support.
Prebuilt binary distribution, compiler bootstrap, broader context/plugin/MCP
imports and toolchain-family reconciliation remain outside this amendment.

## Adopted decisions

These credential/permission decision drafts are **adopted** (operator
decision 2026-09-21, TASK-260921-3qcjsy, STORY-260921-3z0fgr; design
input the Fable-reviewed TASK-260916-2timlf work). Adoption records
the selected options and the resolved choices in each document; the
normative amendments land with the adoption, and the remaining
implementation and spec-revision work is tracked in named follow-up
leaves.

- [Decision 0017: environment credential modes](decisions/0017-environment-credential-modes.md) — adopted 2026-09-21: options 1–3 as recommended, open questions 1–7 resolved.
- [Decision 0018: curator run permission interface](decisions/0018-curator-run-permission-interface.md) — adopted 2026-09-21 with the 2026-09-16 amendment (TASK-260916-2fu85y, rev 2 after review): config-driven mode, interactive default `yolo` / headless default `native`, force-`native` lock, fail-closed legacy transport; open questions 1–7 resolved.

The launch-profile decisions below were adopted 2026-10-01 by the operator.
Their proposal text is preserved; normative amendments and their open
questions remain follow-ups.

- [Decision 0019: fragment consumers and one construction site](decisions/0019-fragment-consumers-and-one-construction-site.md) — adopted 2026-10-01 by the operator.
- [Decision 0021: sessions enter through curator run and are hosted through the ax contract](decisions/0021-sessions-enter-through-curator-run.md) — adopted 2026-10-01 by the operator.

## Managed-home snapshot activation gates

CIP-0014 is Accepted under owner decision 2026-10-15. Its normative leaf 1
is [published separately](protocol/managed-home-snapshots.md). The following
remain open and MUST NOT be inferred from acceptance:

- Exact archive encoding, header/padding/end bytes, resource caps, plan wire
  bindings and cross-service refusal mappings: joint leaf 5 publication.
- Runtime B's sealed-content/private-state view: an interpretation of D6
  awaiting operator confirmation, then per-adapter/platform protection and
  start/login/model-turn/native-resume qualification in leaves 3/6.
- Opencode profile-local skills discovery and ambient state bounds; export
  refuses meanwhile. Muse skill discovery and refresh writes remain unverified.

The materialize diagnostic family is resolved in snapshot §5. D12's portable
Muse root-context fact is coordinated with CIP-0017; its fragment revision
and credential policy remain outside this leaf.

## Filed proposals

These decision drafts are **proposed — not adopted** (0014–0016 from
migration workstream B7).
Filing does not authorize implementation, normative changes, workarounds,
or draft landing.

- [Decision 0014: tool-configuration surfaces](decisions/0014-tool-configuration-surfaces.md)
- [Decision 0015: per-project policy and profile selection](decisions/0015-per-project-policy.md)
- [Decision 0016: skill command roots in managed homes](decisions/0016-managed-home-command-roots.md)


## Local hosted publication and qualification

[CIP-0016](cips/CIP-0016-local-hosted-launches.md) is Accepted by owner decision
2026-10-15. [Local hosted launches §8](protocol/local-hosted-launches.md#8-publication-questions-retained)
retains four open questions: exact successor wire/capabilities/preparation
framing; backend configuration and migration spelling; supported Codex policy
layering across cold resume; and CIP-0014's Curator-owned credential exceptions.
Recommended answers are not frozen fields or measured behavior. Launcher SPEC
§§3, 4.6, 4.8–4.9 amendments and receiver qualification remain follow-up work;
local activation must not defer Codex, wait for dispatcher, or use live homes.

## Login readiness publication and qualification

[CIP-0015](cips/CIP-0015-login-readiness-and-profile-preparation.md) is Accepted;
[login readiness revision 1](protocol/login-readiness.md) freezes leaf 1's row,
selector and store projection. Full containing manager-config/status revisions and fragment 5 are now
[published](protocol/rc7-carriers.md) with the Codex successors.
No v1–v3 fragment extension is admitted. Metadata-only platform probes, Codex
keyring scope/precedence, Windows, Muse refresh, optional explicit
vendor diagnostics, broker adoption and destination readiness remain later-leaf
work. The strict all-participants aggregate is decided: a participating ambient
OpenCode row currently prevents green check/prepare, deliberately and visibly.

## Profile Codex settings (CIP-0018)

1. **Carrier allocation published.** [Containing carriers](protocol/rc7-carriers.md)
   allocates manifest 2, lock 4, marker 5 and fragment 5 with one policy payload;
   snapshot descriptors remain separate. Runtime enablement still needs the
   following qualification and strict covered consumer support.
2. **Supported-release qualification.** Establish scalar CLI precedence over
   a conflicting seed and backend selection for login, app-server and token
   refresh on every supported Codex release. Until measured, these capabilities
   remain unknown and producers remain disabled. CIP-0015 must also adopt the
   explicit eligibility matrix before isolated/file is enabled.

The accepted [normative text](protocol/profile-codex-settings.md#7-wire-allocation-conformance-and-rollout)
and [CIP questions 4–5](cips/CIP-0018-profile-level-codex-settings.md#open-questions-for-the-operator)
define the required decisions and evidence. These are later adoption gates,
not behavior inferred or implemented by the normative leaf.

## Local setup-token activation gates

The [local-source publication](protocol/local-setup-token-source.md) settles
the C7 same-user sequencing carve-out, carriers and public facade contract.
Remaining delivery gates are the separately reviewed launcher SPEC entry/plan
companion, the T3a public API module pin, T1/T2 custody/policy implementation,
T3b real final-executor qualification and T4 real task-board headless uptake.
No supported tuple is established by the metadata corpus. Direct-only and
interactive hosted rows remain distinct. `tb-sessiond` lookup/restart is
refused under existing hosted §§4/6; enabling it requires an explicit later
amendment, not a callback or hidden wrapper. Unqualified vendor child-leak or
settings-reload behavior keeps capability unavailable.

The [proposed hosted-station amendment](protocol/local-setup-token-hosted-qualification-proposal.md)
does not lift those refusals. Before implementation, the owning lanes must name
T1/T2 source-store/policy, T3a public API and launcher/manager consumption writers
and published pins; acceptance of qualification prose cannot silently assign
them to injection work. Re-pin evolving station account/key/path/lifecycle
contracts and jointly publish the hosted carrier/final-owner bindings. Real
destination enrollment, harness containment and pilot activation retain separate
owner routes; neutral contract fixtures establish none of them.

## Project Skillfile MCP declarations (CIP-0022)

[CIP-0022 owner decisions, 2026-10-22](cips/CIP-0022-mcp-server-declarations-in-project-skillfile.md#owner-decisions-2026-10-22)
resolve all five questions with the recommended answers: package-first staging,
initially ignored install options, shared closed runtime pin grammar, no initial
inline audit waivers and separate carrier/writer contracts. Normative publication
and per-adapter native qualification remain engineering gates, not open owner
questions; no native writer or managed admission is enabled by acceptance.

## Project context acceptance candidate (CIP-0002)

[CIP-0002 owner decisions, 2026-10-22](cips/CIP-0002-project-context-in-managed-launches.md#owner-decisions-2026-10-22)
record acceptance and resolve both remaining questions. Project context is always
additive after the profile root context in the composed managed-home file;
project-general precedes environment-specific context, deeper after shallower.
The separate root/system override item is withdrawn, not deferred. Explicitly
opted-in private memory stays per Werkstatt until explicit deletion, never
published, reused across Werkstätten or promoted to knowledge. Default and
first-slice memory remain off. Earlier home, permission, PATH and first-wave
choices remain decided. Closed grammar/vectors, a new outer carrier and actual
source-exclusion/route qualification still need publication and qualification;
published fragment v4/v5 remain unchanged.

## Exact-plan successor (CIP-0023)

[CIP-0023 owner decisions, 2026-10-22](cips/CIP-0023-exact-plan-hosted-launches.md#owner-decisions-2026-10-22)
resolve all six questions as recommended: joint first runtime cohort followed
by per-runtime retirement, jointly published exact/3 contracts, protected
at-least-once doorbells, Curator-owned capture with distinct session/capture
leases, retained native-policy/credential gates and explicit legacy retention.
Normative schema publication and actual runtime qualification remain gates.
No production capability is activated by acceptance.

## Profile-declared Codex project trust

[Seed revision C](protocol/codex-seed-c.md) deliberately admits no declared
project-trust exception. Whether a profile should ever declare trust remains
a separate product decision requiring a reviewed typed vocabulary extension,
including authority, path existence, symlink handling, precedence and lifecycle
ownership. The current empty-only `codex_settings` grammar remains in force.
Legacy seed entries have no reliable copied-versus-user-authored provenance;
this question does not authorize repair, migration or trust deletion.

## Native command-root milestone decisions

The [seven-gate owner packet](protocol/profile-command-root-admission.md) remains
unaccepted. Recommend operator prune with no automatic command-root GC (no disk
bound), explicit policy lock/CAS, two journal classes and native companion scope.
Full pins instead needs non-root Linux supervision and request retirement designs.
W0 must establish real tool-shell PATH/identity delivery and settings precedence.
Journal inode preservation/staging paths and actual runtime receipts remain open.
No production names, numbers, gate opening or capability are allocated here.


## Machine Host notification publication (CIP-0031, Review)

The schema-8 and `/2` [proposal](protocol/host-notification-proposal.md#6-contract-ownership-and-cip-0023)
allocates `curator-host-notification/1` as a selection identifier only. CIP-0023
assigns protected binding publication to the manager owner and joint
notification/event publication to launcher and manager owners; it does not
name this contract. The owner must identify its publisher and decide whether
it adapts the doorbell binding or defines a separate lifecycle before receiver
activation. No owner or workflow-digest/binding-digest equivalence is inferred.
F3's [source-owner decision](https://github.com/relux-works/curator/pull/216#issuecomment-6716173552)
by the Curator orchestrator as Curator source owner (2026-11-08) is recorded: the claude-auth editor admits and preserves
schema 8 (later 9 when admitted); implementation and real-editor qualification
remain outstanding. Complete predecessor-form reconciliation and acceptance
remain required before producer emission; draft validation does not waive them.

Core follow-ups for the Review carrier: reject integral decimal/exponent version
tokens (`8.0`/`8e0`) and make selection-lock refusals input-free. Launcher #92
needs absolute, clean `config_path` validation. These are declared divergences
in [contract §§3–4](protocol/host-notification-proposal.md), not qualification.

## Machine Claude environment containing-carrier gate

[CIP-0029](cips/CIP-0029-machine-claude-output-limit.md) remains Review and
[Decision 0035](decisions/0035-machine-claude-output-limit.md) remains Proposed;
operator adoption is pending. Configuration 9 and `curator.launcher-config/3`
are allocated now, conditionally on
[spec #216](https://github.com/relux-works/curator-spec/pull/216) and its schema 8 /
`/2` predecessor. The draft may stack now; acceptance waits for the final
predecessor shape to be accepted. The
[containing-schema drafts](schemas/machine-claude-env-v1/README.md#predecessor-snapshot-and-pending-reconciliation)
await its final accepted shape, complete predecessor-form preservation and
reader/schema reconciliation before any producer emits a successor.
This remains a landing gate for [Core #238](https://github.com/relux-works/curator/pull/238);
draft publication and scoped validator success do not discharge it. No move
from pre-emission to release/qualification is authorized by this amendment.

Core #238 follow-up: its inspected head
`4f7f7681589f4c2bdc2953749afcbd973fb20b6f` accepts integral decimal/exponent
version tokens `9.0`/`9e0` as 9 through `integerValue`. The proposal requires
integer token 9. Reject those spellings with the integer refusal before
qualification, alongside the predecessor schema-8 token follow-up. This is a
declared Core divergence in the
[containing-schema contract](schemas/machine-claude-env-v1/README.md), based on
source inspection; no Core binary or runtime qualification is claimed.


## Native a2a station handover (CIP-0032, Review)

The [Review proposal](cips/CIP-0032-native-a2a-station-link.md) and
[draft Decision 0037](decisions/0037-native-a2a-station-link.md) fold in the supplied
a2a owner and curator-run answers. Both former questions are closed: enrollment
is per environment through the external pipe between the a2ad (the a2a daemon) user and station user, never
at launch; **a2a owner statements, a2ad (the a2a daemon) protocol version 1** now name Go
package `daemon.StationKeyLen = 32` and `ProtocolVersion = 1`. The launcher
checks the published size; curator-run accepted either form and preferred no size
stat. Its module-version pin/lookup remains curator-run implementation work.
The canonical-path rule is an a2a owner statement, a2ad (the a2a daemon) protocol version 1.
Consuming that pinned contract, real
enrollment qualification and the future admin-socket seam remain implementation
dependencies; no root-emission gate opens or status becomes Accepted.

The canonical enrollment-record question is closed by the **a2a owner statement,
a2ad (the a2a daemon) protocol version 1**: no station path is stored. Every reader requires
an absolute supplied D with `EvalSymlinks(D) == D`. a2ad (the a2a daemon) hello authenticates
by secret and UID, not path. No new owner question is introduced here.


### 2026-11-10 name-map follow-up

The Source rename map does not name the model's example socket value
`/run/courier/service.sock`, its private Python helpers `courier_socket_path`
and `courier_contract`, the test selector
`test_courier_socket_bytes_vectors_and_plants`, or the `courier-socket-*` plant
label. These remain unchanged pending an explicit mapping; they are not
additional admitted station entries or daemon default paths. The station
pointer filename and failure-log filename do follow the supplied map.
