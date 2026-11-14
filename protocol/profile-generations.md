# Profile generations: joint chapter skeleton

Design proposal, 2026-11-14. Semantic agreement is closed; runtime binding, complete carrier allocations and affected technical MUSTs are not frozen. This is an authoring skeleton and vector inventory, not an adopted revision or qualification result.

## Placement, stewardship and numbering

Proposed chapter: **`protocol/profile-generations.md`**, beside `protocol/environments.md`, `protocol/managed-home-snapshots.md`, `protocol/home-leases.md` and `protocol/project-context.md`. These baseline files were inspected at **S = ab6b1b0960473b359c84d96e7c7749b9be6011e0**; the proposed chapter is absent from that pinned tree. No file or number is reserved by this document.

Request from the specification editors: **candidate CIP-0033** (`cips/CIP-0033-profile-generations.md`) and **candidate Decision 0038** (`decisions/0038-profile-generations.md`), subject to checking all later reservations before assigning either. If occupied, request the next unassigned numbers instead. These are proposed reservation requests, not allocated identities; reserve the proposal first and record the decision upon adoption. Allocate each next unassigned number **including reservations**, never infer availability from missing files. The numbering rule is `cips/README.md:30–39 @S`. Keep the older proposal's identity and replay intact; a replacement gets a new number, not reused 0014. Status/process references: `cips/README.md:11–26,56–67 @S`.

The initiating editor drafts from the accepted semantic texts and shared probe receipts; the peer editor co-edits existing-carrier boundaries, and the registry authority reviews evidence/negative coverage. Publish a draft skeleton first, then fill probe-dependent mechanisms after shared probes and operator binding choice. Do not freeze those sections before evidence. There is one integrated chapter and one traceability table, not separate normative forks. Named production mappings and probe receipts live outside the specification repository.

## Neutral-role convention

All **new** shared prose, schemas, examples and nonnormative implementation notes use neutral roles: **manager, consumer, native authority, session custodian, observer, auditor, issuer, operator, adapter**. Manager product/implementation names belong in external mappings and receipts, not new explanatory prose. **Exact existing specification paths and normative adapter environment IDs are protocol identifiers**, not implementation attribution: preserve and resolve paths such as `protocol/profile-codex-settings.md` and `cips/CIP-0028-claude-read-scope.md`, and IDs such as `claude_code`, `codex_cli`, `pi`, `opencode` when the owning protocol requires them. Do not replace these references with opaque owner-only aliases or rename frozen carriers. New adapter-roster sections reference the owning identifier vocabulary; exact native binary qualification remains in external receipts. Historical contracts, reference identity and bytes are preserved. This is prospective neutral authoring, not a repository-wide rewrite.

## Chapter and section list

**N** = semantic rule agreed for normative drafting, still requiring formal adoption and closed carriers. **P** = mechanism or policy allocation dependent on probes/editor/operator confirmation; do not turn it into an executable default yet. A section may contain both, separated explicitly.

| Anchor | Section and owning rule | Marker / gate |
| --- | --- | --- |
| §1.1 | Scope: opt-in global profiles first; project views later; trusted-code loader boundary, no sandbox claim | N |
| §1.2 | Compatibility: legacy omission/replay, unchanged existing declarations/locks/global delivery; unsupported new capability refuses | N |
| §1.3 | Explicit registration and consumer mode; no discovery-selected mode or downgrade | N; P exact successor fields/flags |
| §1.4 | Terminology, four identities and normative-reference hierarchy | N |
| §2.1 | Finite package manifest vocabulary, sources and selected directory semantics | N; P closed version allocation |
| §2.2 | Exact raw acquisition, independent content hash framing and inadmissible-tree refusal | N |
| §2.3 | Ordered graph/overlay composition; raw closure union before projection | N |
| §2.4 | New edge-scoped whole-skill include/exclude semantics; separate legacy collection rules | N; P selector tuple bytes/edge identity |
| §2.5 | Effective projection, declared omissions and unsupported-capability refusal | N; P closed projection/omission carrier |
| §2.6 | Deterministic context rendering: header digest, environment, form, order and LF inputs | N equal-input boundary; P common successor header identity |
| §2.7 | Operational locks remain private; export is an explicit projection, never a relabelled full lock | N; P lock/projection correspondence schema |
| §3.1 | Rejecting positive evidence successor, exact subject AND match and policy/check-set identity | N; P schema number/object fields |
| §3.2 | Static default plus explicitly required optional model predicate; failure versus revocation authority | N; P check policy identifiers |
| §3.3 | Broad same-framing negatives, deny-wins, both consumer lanes and retrieval paths | N |
| §3.4 | Schema-2/hash-2 new negatives; positive-only successor initially; future negatives dual-issued | N |
| §3.5 | Hash-1 retention without cross-framing match, real hash-2 reissue and migration coverage | N |
| §3.6 | Snapshot/cache/offline/bundle completeness, rollback/freshness and required authority coverage | N L3 gate; P exact receipt/limits and other-level mapping |
| §4.1 | Stable native authority: physical path/backend identity, private origin and explicit adoption | N; P qualified reference mechanics |
| §4.2 | Immutable content-addressed generation: canonical manifest, no secrets, content reuse | N; P successor digest domain/carrier |
| §4.3 | Local versioned control receipt and admitted runtime projection | N; P concrete canonical keys/channels |
| §4.4 | Session/project binding: generation + control + authority + policy + native locator | N; P closed binding versions |
| §5.1 | Verified materialization/export, atomic publication, no live use of a mutable managed delivery | N; P fixed authority versus generation mapping |
| §5.2 | Explicit update/activation, pending versus active generation, no automatic live-session rebinding | N |
| §5.3 | L1–L4, minima/floor, mismatch/unavailable aggregation and mandatory independent gates | N preserve adopted level semantics; P successor carrier |
| §5.4 | Home drift and repair at every level; store restoration only at L3/L4 | N preserve baseline distinctions |
| §5.5 | Immutable inventory verification and carrier/descriptor correspondence before child start | N; P adapter-specific binding |
| §6.1 | Persistent native state is also a loader root; typed writes versus pinned/approved controls | N |
| §6.2 | Key/channel roster, unknown-key policy, write-back targets, external roots, base/role preservation | P per exact runtime tuple |
| §6.3 | Native compatible line/floor/capabilities versus strict exact tuple | N; P acceptance scope/invalidation/binary identity |
| §7.1 | Durable idempotent prepared-before-exec holder and non-admitting terminal replay | N; P successor holder/carrier |
| §7.2 | Exact observer registration/process incarnation/no-start/descendants; unknown never TTL-expires | N; P shared observer protocol and custodian selection |
| §7.3 | Invocation binding or serialized activation; retained-resumable protection and pending updates | N protection invariant; P qualified realization |
| §7.4 | GC roots, restart/recovery, complete state reads and interrupted publication | N |
| §7.5 | Default fenced operator break with CAS/durable audit; separately enabled abandonment exception | N successor policy; P fence proof interface |
| §8.1 | Single composition path → actual production start; mandatory controls before child | N; P adapter entry details |
| §8.2 | Native in-place auth or qualified single reference; rotation-safe authority continuity | N no-copy rule; P native qualification |
| §8.3 | Native resume/child entry, generation/control/policy verification and stopped readmission | N; P exact consumer/locator mapping |
| §8.4 | Stop/retention/retirement and private-state/export boundaries | N |
| §9.1 | Explicit native-project mode, declared ambient discovery and runtime policy | N |
| §9.2 | Explicit native-project verified against declaration/lock: approved base, hash inventory, extras, resume | N; P complete generated inventory after delivery support |
| §9.3 | Strict exact external protected sparse view; exact commit/content/path-set and exclusions | N architecture; P subject/adapter certification |
| §9.4 | Global profile plus repository profile; distinct from existing delivery-mode terminology | N architecture; P future composition carrier |
| §10.1 | Closed schemas, canonical bytes/signatures and independently grounded vectors | N |
| §10.2 | Static validation versus native qualification versus each consumer's production adoption | N |
| §10.3 | Normative traceability table; immutable source/corpus pins and successor adoption receipts | N |
| §10.4 | Exact tuple/observer evidence and supported/unsupported capability matrix | N; P receipts after probes |

## Normative traceability table to carry into the chapter

Every amended clause and owning schema needs its own row, even where authoritative text remains in another file. Required columns: **baseline OID + file + clause/line, add/amend/supersede/preserve disposition, one authoritative successor anchor, carrier/capability version, N/P, joint decision, vector IDs**. An omnibus “update environments” row is insufficient. Row splits below identify the minimum coordinated scope; final authoring must add a row for any further affected clause. A trace row does not itself adopt a revision or duplicate the rule's authoritative text.

Unless marked D, baseline is S. “New” means **unallocated rejecting successor**, not an assigned version. “Keep” preserves old bytes/schema; new semantics require new capability. Q labels are agreed semantic positions; vector labels are local inventory IDs pending allocation.

| Baseline file:line / clause | Disposition → authoritative successor | Carrier / status | Decision; paired vectors |
| --- | --- | --- | --- |
| `cips/CIP-0014-managed-home-snapshots.md:147` design; :168 recommendation | Amend through new proposal; preserve historical record → §4–§8 | New; N/P | Q4; V1–V18 |
| Same file :177 command/destination; :223 closure/relocation | Amend derivation, not old replay → §5.1/§5.5 | Snapshot successor; P | Q4; V1,V12 |
| Same file :272 manifest/digest; :326 publication | Preserve v1; add generation/control identity and activation → §4.2/§5.2 | New; N/P | Q1/Q4; Q1-V7,Q4-V12 |
| Same file :389 adapter/overlays; :433 delivery/verification | Amend authority binding/consumer gates → §6/§8 | New; P | Q4; V2,V6–V11 |
| `protocol/managed-home-snapshots.md:9` §1 | Preserve no-live-mutable-delivery; distinguish native authority → §4.1/§5.1 | V1 kept; new capability; N/P | Q4; V1,V2 |
| Same :37 §2 | Preserve verified atomic export; add activation transaction → §5.1/§7.4 | V1 kept; new publication; N | Q4; V12–V14 |
| Same :99 §3 | Preserve closed content/relocation; no credential inventory → §4.2/§5.5 | V1 kept; new generation; N/P | Q1/Q4; Q1-V5,Q4-V11 |
| Same :141 §4, especially :175 home bindings and :204 source-home digest | Preserve snapshot-v1 identity; amend successor variables to stable authority plus generation → §4.1–§4.4/§5.1 | New descriptor; P | Q4; V1,V2,V7,V11 |
| Same :226 §5 | Preserve capture/structural refusal → §5.5 | Keep; N | Q1/Q4; Q1-V5,Q4-V12 |
| Same :267 §6; :293 pending writable-slot interpretation | Amend only after binding proof/operator choice → §6.1/§8.1–§8.3 | New adapter capability; P | Q4; V2,V6–V11 |
| Same :301 §7 | Preserve opaque transport and verification bounds → §5.5/§8.4 | Keep; N | Q1/Q4; Q1-V7,Q4-V12 |
| `protocol/environments.md:89` §1; :229 §1.3; :310 §1.4 | Preserve operational lock; new exchange projection → §2.1/§2.7 | Existing kept; new projection; N/P | Q1; V1,V3,V7 |
| Same :470 §2; :552 skill directories; :606 §2.2 | Preserve package/directory/MCP declarations; new capability grammar → §2.1/§2.5 | New finite subset; N/P | Q1; V3,V6,V7 |
| Same :734 §3; :968 §5; :1044 §5.1; :1182 §5.4 | Preserve ordering/zero cases/frozen legacy header; define successor render inputs → §2.6 | Existing header kept; new input identity; N/P | Q1; V1,V2 |
| Same :837 §4; :1241 §5.6 | Preserve structural admission/hash meaning; bind generation inventory → §2.2/§5.5 | Hash 1/2 kept; new manifest; N/P | Q1; V4,V5 |
| Same :1305 §6 | Add explicit edge projection after raw union → §2.3/§2.4 | New edge carrier; N/P | Q2; V1–V9 |
| Same :1422 §7; :1557 §7.2; :1572 §7.3; :2125 §7.8 | Amend adapter/launch bindings; preserve old registry record replay → §6.2/§8.1 | New adapter/fragment; P | Q4; V1–V6,V10 |
| Same :1637 §7.4; :2008 §7.5; :2035 §7.6 | Replace unsupported seed-as-authority assumptions only in successor → §4.1/§6.1/§8.2 | New authority/control; P | Q4; V3–V5,V7,V11 |
| Same :2167 §7.9; :2225 §7.10 | Add compatible-line receipt, preserve exact trust authority → §6.3/§4.3 | New runtime/control policy; P | Q4; V3,V19 |
| Same :2383 §8; :2466 §8.2; :2625 §8.3.1; :2674 §8.4 | Keep old marker modes; add generation/control atomic publication → §5.1/§5.2/§7.4 | New marker; N/P | Q4; V3,V12–V14 |
| Same :2777 §9.1; :2916 §9.2 | Preserve legacy install; add explicit pin/activation lifecycle → §1.2/§5.2 | New opt-in; N/P | Q1/Q4; Q1-V6,Q4-V2,V20 |
| Same :3088 §9.3; :3105 §9.4 | Preserve existing scope/skills; new selection and delivery receipt → §2.4/§2.5 | New; N/P | Q2; V1–V9 |
| Same :3567 §10; :3891 §10.2; :4187 §10.3 | Add single consumer path and admitted control/authority projection → §8.1/§4.4 | Fragment successor; N/P | Q4; V6,V9,V10,V20 |
| Same :4301 §10.5 | Amend materialization consumer to generation + stable native state → §5.1/§8.1–§8.4 | Descriptor/session successor; P | Q4; V1,V2,V7–V11 |
| Same :4482 §12; :4681 §12.1; :4786 §12.2 | Preserve config locks; add retained roots/policy and no implicit authority adoption → §5.3/§7.4 | New policy; N/P | Q4; V13,V19 |
| Same :5116 home-lease amendment | Preserve old API; coordinate successor namespace/custody → §7 | New holder binding; N/P | Q4; V12–V18 |
| `protocol/environment-store-verification-v2.md:11` level table; :26 aggregation; :37 minima | Preserve merged levels/default/floor and warning semantics → §5.3 | Existing levels kept; successor field reserved; N/P | Q4; V19; startup corpus |
| Same :63 home decision, including :78 repair; :91 structural checks; :117 restoration | Preserve L1 drift warning/L2–L4 refusal, home repair every level, store repair only L3/L4 → §5.4 | Keep; N | Q4; V3,V12; startup corpus |
| `protocol/project-context.md:10` §1; :47 §2 | Preserve explicit registration authority/mode; extend binding types → §1.3/§4.4/§9 | New carrier; N/P | Q4; V20 |
| Same :102 §3 | Preserve snapshot/selection; distinguish raw/effective identity → §2/§9.3 | Existing kept; new projection; N/P | Q1/Q2; Q1-V3–V5,Q2-V8 |
| Same :190 §4 | Add verified-native inventory of declared skills/MCP plus approved base/extras → §9.2 | New required capability; N/P | Q4; V3,V4,V9,V20 |
| Same :220 §5; :244 exact adapter; :258 §5.1 | Preserve strict exact qualification; add native line and verified-native mode → §6.3/§9.1–§9.3 | New adapter/mode; N/P | Q4; V4–V10,V19,V20 |
| Same :296 §6 | Extend retained generation/control/authority and custodian reconciliation → §7/§8.3 | New holder/session; N/P | Q4; V9,V12–V18 |
| Same :329 §7; :395 §8 | Wire mode at registration/start/resume, refuse unsupported with no downgrade → §1.3/§8.1/§9 | New fragment/CLI contract; N/P | Q4; V6,V9,V20 |
| `protocol/home-leases.md:10` §1; :54 HL05 | Preserve trusted authority; add common exclusive namespace/typed generation identities → §4.1/§7.1 | Successor holder; P | Q4; V7,V14–V17 |
| Same :71 HL06; :87 HL07 | Preserve prepared/idempotent/non-admitting replay/exact bind → §7.1 | Existing replay kept; new carrier; N/P | Q4; V12,V14,V17 |
| Same :97 HL08; :103 HL09; :124 HL11 | Preserve unknown/no-TTL/exact descendants/independent holders; add retained-resumable binding → §7.2/§7.3 | New observer/session; N/P | Q4; V2,V13–V17 |
| Same :129 HL12; :137 HL13 | Preserve historical abandonment; successor fenced default + enabled exception + atomic audit → §7.5 | Explicit successor policy; N/P | Q4; V18 |
| Same :144 §3; :265 §5; :314 §6 | Coordinate guarded writers/recovery/consumer qualification with generations → §5.2/§7.4/§10.2 | New binding; P | Q4; V3,V12,V13,V17 |
| `protocol/provisioning-origin.md:9` §1; :52 §2 | Preserve private native origin; authority/generation separation, explicit no-copy/reference → §4.1/§8.2 | Old origin kept; new binding; N/P | Q4; V7,V11 |
| Same :85 §3; :108 §4; :127 §5 | Preserve atomic lifecycle and explicit legacy adoption; add authority continuity → §7.4/§8.2 | New authority binding; P | Q4; V7,V11–V14 |
| `protocol/core.md:1505` activation union; :1521 §8 | Preserve union and v1/v2 hash semantics, no extraction permission inferred → §2.2/§2.3 | Keep; N | Q1/Q2; Q1-V4,V5,Q2-V2,V5,V6 |
| `protocol/skillfile-sources.md:16` §1, especially :61–78; :83 §2; :119 §3 | Preserve collection duplicate/nonempty/missing-member rules; new edge grammar is distinct → §2.1/§2.4 | Existing kept; new edge; N/P | Q1/Q2; Q1-V3,Q2-V1–V9 |
| Same :205 §4 | Preserve admitted local authority; do not forge portable Git subject → §2.2/§3.1 | Local future capability unsupported initially; N | Q3; V2 |
| `protocol/registry.md:94` §3; :102 schema/hash versions; :111 negative match | Add exact new positive, keep framing equality and broad negative rules → §3.1/§3.3–§3.5 | Positive successor unallocated; schema 2/hash 2 negatives; N/P | Q3; V1–V9,V12 |
| Same :128 §4; :134 deny-wins | Preserve independent negative aggregation across names/sources/lanes → §3.3 | Retrieval successor, old negatives kept; N/P | Q3; V4–V9 |
| Same :171 §5; :288 §5.1; :338 §7; :358 §8 | Add explicit negative completeness/freshness/migration coverage; no advisory reinterpretation → §3.6 | New required coverage receipt; P | Q3; V8,V9,V11 |
| Same :394 §9; :505 §9.3; :569 §10 | Add both-lane publication/query/page/cache vectors; new negatives remain schema 2 → §3.3/§3.4/§10.1 | Versioned endpoint/record capabilities; N/P | Q3; V3,V6–V9 |
| `protocol/profile-skill-plan-proposal.md:19,95,120,168,221` | Preserve planning versus activation distinction; coordinate new edge selection/delivery/retention → §2.5/§8.1/§9.2 | Existing lock 5 kept; new delivery capability; P | Q2/Q4; Q2-V5–V8,Q4-V4,V9 |
| `protocol/profile-command-roots.md:40,104,191,237,313,499,538` | Preserve independent command-root admission/carrier gates; add generation/session binding and GC roots → §2.5/§7.4/§8.1 | Owning command carriers kept; successor correspondence; N/P | Q1/Q4; Q1-V6,V7,Q4-V6,V9,V13 |
| `protocol/profile-command-path.md:8,54,132,233`; `protocol/profile-command-root-admission.md:103,183,265,286,742` | Preserve rollout/admission gates; no automatic activation from path/plan parsing → §6.1/§8.1/§10.2 | Owning carriers kept; binding extension; P | Q4; V3,V6,V10,V12 |
| `protocol/rc7-carriers.md:11,71,148,219,242` | Preserve closed allocation and no alias/successor guessing → §1.2/§2.7/§10.1 | Existing versions kept; complete new carriers; N/P | Q1/Q3; Q1-V7,Q3-V3 |
| `protocol/profile-codex-settings.md:11,50,96,143,178,243` @S | Preserve settings inheritance/launch ownership; qualify successor control/auth boundaries → §2.1/§4.3/§6.2/§8.2 | New adapter projection, old settings carrier kept; P | Q4; V3,V7,V11 |
| `decisions/0010-agent-environment-profiles.md:22,202,488,587,682,711` | Preserve historical decision; record explicit successor authority/generation rationale → §1/§4/§5/§8 | New decision; N/P | Q1/Q4; Q1-V6,Q4-V1,V2,V7,V11 |
| `decisions/0012-context-packages-and-semver-locks.md:249,446,480,531,547,645,669` | Preserve raw-lock/header semantics; new projection/render input boundary → §2 | New decision/carriers; N/P | Q1/Q2; all |
| `decisions/0013-execution-ownership-and-launch-plans.md:87,218,286,445,477`; `decisions/0019-fragment-consumers-and-one-construction-site.md:68,93` | Preserve single composer and actual consumer boundary → §8.1/§8.3/§10.2 | New binding, owning launch plan kept; N/P | Q4; V6,V9,V10 |
| `decisions/0029-provisioning-origin.md:10`; `decisions/0032-managed-home-separate-login.md:28,92,164` | Preserve explicit private login selection; add stable authority and rotation receipts → §4.1/§8.2 | Existing record kept; new authority capability; P | Q4; V7,V11 |
| D1 `decisions/0033-launch-lock-refresh-compatible.md:53,91` | Draft only: amend ordinary auto-refresh proposal to explicit new-generation activation; preserve original resume pin → §5.2/§8.3 | Not adopted baseline; successor if accepted; N/P | Q4; V1,V2,V9 |
| D2 `cips/CIP-0028-claude-read-scope.md:11` | Draft only: keep read-scope alternatives outside certification until qualified → §6.2/§9.3/§10.4 | No certification inherited; P | Q4; V5,V6,V10 |
| `schemas/v1/audit-record-v1.schema.json:1` | Preserve hash-1 replay and old-reader rejection; never match hash-2 subject → §3.1/§3.5 | Keep immutable; N | Q3; V3,V9 |
| `schemas/v1/audit-record-v2.schema.json:1` | Preserve ordinary records and broad v2 negatives; allocate rejecting positive successor separately → §3.1/§3.4 | Old schema kept; new positive unallocated; N/P | Q3; V1–V12 |
| `schemas/managed-home-snapshot-v1/managed-home-snapshot-v1.schema.json:6` | Preserve complete v1 manifest; allocate distinct immutable generation manifest → §4.2/§5.1 | Rejecting successor, not optional v1 fields; P | Q1/Q4; Q1-V7,Q4-V12 |
| `schemas/managed-home-snapshot-v1/snapshot-launch-v1.schema.json:1` | Preserve v1 descriptor; add stable authority/control/generation correspondence → §4.1/§4.4/§5.1 | Rejecting successor; P | Q4; V1,V2,V7,V11 |
| `schemas/project-context-leaf1-v1/registration.schema.json:7,43` | Preserve existing explicit mode; add verified variant only through supported capability → §1.3/§9.2 | Rejecting mode/capability successor; P | Q4; V20 |
| `schemas/project-context-leaf1-v1/composition.schema.json:7,115` | Bind explicit variant and admitted projection at composition, without mode default change → §4.4/§9.2 | Rejecting capability successor; P | Q4; V9,V20 |
| `schemas/project-context-leaf1-v1/adapter.schema.json:7` | Coordinate exact tuple and native-line capabilities → §6.3 | New adapter; P | Q4; V6,V19 |
| `schemas/project-context-leaf1-v1/control-receipt.schema.json:7` | Bind canonical key/channel projection and policy → §4.3/§6.2 | New control receipt; P | Q4; V3,V9 |
| `schemas/project-context-leaf1-v1/generation.schema.json:7` | Bind immutable content identity separately from native authority → §4.2/§4.4 | New generation; P | Q4; V1,V2,V9 |
| `schemas/project-context-leaf1-v1/root-binding.schema.json:1` | Retain exact protected-root/native authority correspondence → §4.4/§7.4 | New root binding; P | Q4; V9,V13 |
| `schemas/project-context-leaf1-v1/lease.schema.json:1` | Coordinate session/observer retention identity → §7.1/§7.2 | New lease binding; P | Q4; V14–V18 |
| `schemas/project-context-leaf1-v1/item.schema.json:1` | Preserve exact admitted item; defer unsupported path-set subject → §2.2/§9.3 | Old item kept; new subject deferred; P | Q4; V4,V10 |
| `schemas/project-context-leaf1-v1/snapshot-manifest.schema.json:1` | Bind selected native view to immutable inventory → §4.2/§9.3 | New view correspondence; P | Q4; V4,V9 |
| `schemas/project-context-leaf1-v1/project-context.schema.json:1` | Coordinate explicit variant and exact checkout binding → §9 | New capability; P | Q4; V6,V9,V20 |
| `schemas/project-context-leaf1-v1/fragment-members.schema.json:1` | Bind generation/control/authority in actual consumer projection → §4.4/§8.1 | New fragment; P | Q4; V6,V9 |
| `schemas/project-context-leaf1-v1/command-environment.schema.json:1` | Keep command authority separate while binding admitted view → §8.1/§9.3 | Owning command gate kept; extension explicit; P | Q4; V6,V10 |
| `schemas/home-leases-v1/holder.schema.json:1` | Preserve old prepared/bound union; add coordinated custodian binding → §7.1/§7.2 | Rejecting successor; P | Q4; V14–V17 |
| `schemas/home-leases-v1/record.schema.json:7` | Preserve old replay; new authority/generation/unknown retention binding → §7.1/§7.4 | Rejecting successor; P | Q4; V12–V17 |
| `schemas/home-leases-v1/event.schema.json:1` | Preserve atomic audit; explicit fenced/default and exception policy → §7.5 | Rejecting successor; P | Q4; V18 |
| `schemas/home-leases-v1/result.schema.json:1` | Preserve non-admitting terminal outcomes; distinguish pending activation and recovery → §7.1/§7.3/§7.5 | Rejecting successor; P | Q4; V2,V12,V18 |
| `schemas/provisioning-origin-v1/provisioning-origin-v1.schema.json:1` | Preserve private origin; new generation references its admitted authority → §4.1/§4.4 | Old bytes kept; new reference; P | Q4; V7,V11 |
| `schemas/profile-skill-plan-v1/context-lock-v5.schema.json:6,80` | Preserve directory/hash/lock identity; no complete-lock interchange claim → §2.1/§2.7 | Lock 5 kept; explicit correspondence successor; P | Q1/Q2; Q1-V3,Q2-V8 |
| `schemas/profile-skill-plan-v1/profile-skill-plan-v1.schema.json:1` | Preserve plan versus activation; new edge selection binds declared semantics → §2.4/§2.5 | New projection/edge carrier; P | Q2; V8,V9 |
| `schemas/profile-command-roots-v1/root-receipt.schema.json:1` | Preserve independent command-root admission; bind admitted generation → §4.4/§8.1 | Keep existing; explicit correspondence successor; P | Q4; V6,V9 |
| `schemas/profile-command-roots-v1/inventory.schema.json:1` | Preserve exact command inventory correspondence → §5.5/§8.1 | Keep existing; explicit correspondence successor; P | Q4; V6 |
| `schemas/profile-command-roots-v1/session-pin.schema.json:1` | Coordinate retained generation/control/authority pin → §4.4/§8.3 | Keep existing; explicit correspondence successor; P | Q4; V9,V13 |
| `schemas/profile-command-roots-v1/generation-marker.schema.json:1` | Distinguish complete immutable content from mutable activation → §4.2/§5.2 | Keep existing; explicit correspondence successor; P | Q4; V12 |
| `schemas/profile-command-roots-v1/snapshot-retention.schema.json:1` | Preserve all active/unknown/resumable command roots → §7.4 | Keep existing; explicit correspondence successor; P | Q4; V13 |
| `schemas/profile-command-roots-v1/launcher-state.schema.json:1` | Coordinate prepared/bound consumer state and terminal replay → §7.1/§8.1 | Keep existing; explicit correspondence successor; P | Q4; V6,V12 |
| `schemas/v1/launch-env-fragment-v4.schema.json:1` | Preserve closed fragment; generation/authority binding requires a new complete carrier → §4.4/§8.1 | Existing kept; rejecting successor; P | Q1/Q4; Q1-V7,Q4-V6,V9 |
| `schemas/rc7-carriers-v1/launch-env-fragment-v5.schema.json:1` | Preserve required-understanding boundaries; no optional generation metadata shortcut → §1.2/§4.4/§8.1 | Existing kept; rejecting successor; P | Q1/Q4; Q1-V7,Q4-V6,V9 |
| `conformance/environment-store-verification-v2/README.md:40`; existing manifest | Preserve 185 baseline rows; add successor corpus rather than changing old outcomes → §10.1/§10.3 | New corpus/version; N/P | Q4; V3,V12,V19; all startup controls |

S is the baseline pin above. D1 = **0d3bd4e8d7c33e6ba95de30673205936bf6c4e34**, draft file blob **75fd9ccd4be8957a9d6ab813cf39833221f4fa57**. D2 = **ee33b1d601e8a16116b7e91d0aa9b821dd016e25**, whose `cips/CIP-0028-claude-read-scope.md` blob is **0f39cccfc6efea2bf50668be080886602731cfb3**; [resolvable draft clause:11](https://github.com/relux-works/curator-spec/blob/ee33b1d601e8a16116b7e91d0aa9b821dd016e25/cips/CIP-0028-claude-read-scope.md#L11). S's `protocol/profile-codex-settings.md` blob is **874d64bfc9fddbf3042b6ba73bb30d8b4cf83975**; [resolvable baseline clause:11](https://github.com/relux-works/curator-spec/blob/ab6b1b0960473b359c84d96e7c7749b9be6011e0/protocol/profile-codex-settings.md#L11). These exact paths/OIDs resolve without any owner-only packet. Neither draft is promoted to main. Successor decision/CIP numbers remain unallocated.

The older include/exclude directive has no verified immutable normative pointer in this evidence set. Therefore §2.4 adopts **new** agreed edge semantics, with the collection rules preserved; no invented historical compatibility claim. Signed configuration remains deferred: the adopted startup revision explicitly does not provide configuration signing (`protocol/environment-store-verification-v2.md:11–14 @S`). Reserve future required capabilities; do not claim signed local config or path-set evidence exists.

### §10.3 — Reused, unchanged vector input files

All inputs below are pinned at **S**, reused **unchanged**. They are baseline expectations/bytes, not new native qualification or additional allocated Q rows. New consumers add successor witnesses; they must not rewrite old verdicts, symbolic-commit meanings or frozen framing bytes. The chapter's corpus manifest must enumerate and hash every member of the referenced input closure at S.

| Existing input file(s) / line | Use / owning successor inventory |
| --- | --- |
| `conformance/v1/vectors/content-hashes-v2.json:1` | Existing framing/collision/NUL witnesses, reused unchanged for §2.2 and Q1-V4; [pinned input](https://github.com/relux-works/curator-spec/blob/ab6b1b0960473b359c84d96e7c7749b9be6011e0/conformance/v1/vectors/content-hashes-v2.json#L1). |
| `conformance/rc7-carriers-v1/index.json:1` and each `instance` it names under `cases/` | Existing complete valid/invalid carrier inputs, unchanged for §10.1/§10.3 and Q1-V7/Q3-V3; index is the finite file list, not an unbounded directory scan. [Pinned index](https://github.com/relux-works/curator-spec/blob/ab6b1b0960473b359c84d96e7c7749b9be6011e0/conformance/rc7-carriers-v1/index.json#L1). |
| `conformance/rc7-carriers-v1/canonical.json:1`, `compatibility.json:1`, `delivery-vectors.json:1`, `decisions.json:1` | Reuse unchanged canonical byte/digest, old/new reader, delivery/refusal and decision inputs. Include every `instance`/`bytes` file (`cases/`, `canonical/*.ccj`) and compatibility `old_control`/`new_control` file: old controls resolve from the specification root, new controls from this corpus directory. Owning schema references remain unchanged normative dependencies. Pin that finite closure at S. [Canonical input](https://github.com/relux-works/curator-spec/blob/ab6b1b0960473b359c84d96e7c7749b9be6011e0/conformance/rc7-carriers-v1/canonical.json#L1); the [family inventory:3](https://github.com/relux-works/curator-spec/blob/ab6b1b0960473b359c84d96e7c7749b9be6011e0/conformance/rc7-carriers-v1/README.md#L3) defines these roles and explicitly limits runtime proof. |
| `conformance/profile-skill-directories-v1/fixtures.json:1`, `vectors.json:1`, `schema-cases.json:1`, `lock-identity.json:1` | Existing selected-directory acquisition, hash/lock/lifecycle and structural cases for §2.1/§2.2/§2.7, Q1-V3 and Q2 controls. Reuse unchanged source files; any materialized symbolic-commit substitution has a separate receipt and never changes the pinned baseline. [Structural inventory:9](https://github.com/relux-works/curator-spec/blob/ab6b1b0960473b359c84d96e7c7749b9be6011e0/conformance/profile-skill-directories-v1/README.md#L9), [lifecycle inputs:51](https://github.com/relux-works/curator-spec/blob/ab6b1b0960473b359c84d96e7c7749b9be6011e0/conformance/profile-skill-directories-v1/README.md#L51). |

Runtime-holder state/refusal controls and fixed socket/helper preflight controls expand the corresponding Q4 fixture subcases; development/release storage controls expand auth/store subcases. They do not change the **48** agreed paired-row identities or imply a production schema allocation. Versioned fixture state/refusal vocabulary is shared by adapters; exact production carriers and probe-dependent MUSTs still wait for evidence.

## Conformance inventory: all 48 paired rows

IDs below preserve the round-2 discussion labels for coverage only. They are **not allocated shared corpus IDs**. Every row requires both the forbidden outcome and its nearby valid control, unchanged preimages on rejection, and a specific diagnostic/transition assertion. Expand multi-case rows into fixture instances; do not reduce them to a single happy-path test. Static vector passes do not qualify a native runtime or a production caller.

### Q1 — package, hash and rendering: 7 pairs

| ID | Paired witness and required result | Owner section |
| --- | --- | --- |
| Q1-V1 | Equal complete canonical render inputs / changed weight, tie direction or header digest: identical bytes only for equal header/lock/environment/form inputs; proper stable ordering otherwise | §2.3/§2.6 |
| Q1-V2 | Absent context / present context with zero applicable modules: no file versus specified header-only result | §2.6 |
| Q1-V3 | Schema-1 directory / schema-2 selected directory; root omission / literal dot: reject unsupported field, bind exact directory; omitted profile root normalizes empty, profile dot refuses, collection dot remains valid | §2.1 |
| Q1-V4 | NUL/collision plant / regular bytes: v2 hashes exact bytes with collision-distinguishing framing; v1 refuses opaque NUL before hashing | §2.2 |
| Q1-V5 | Linked/special/colliding acquisition / regular contained tree: refuse extraction before publication; standalone hash vectors keep separate link semantics | §2.2 |
| Q1-V6 | Required skill/MCP without delivery / explicit contexts-only: refuse without writes versus admit declared context projection with visible omissions, never full audited closure | §2.5 |
| Q1-V7 | Unsupported/invalid closed input / supported closed input: precise refusal without publication versus deterministic admitted projection | §1.2/§2.7 |

### Q2 — new edge projection and old collection rules: 9 pairs

| ID | Paired witness and required result | Owner section |
| --- | --- | --- |
| Q2-V1 | Omitted / empty / overlapping filters on same pinned edge: all / none / exclusion wins | §2.4 |
| Q2-V2 | Conflicting same-name raw closure hidden by filter / valid exact selectors: conflict refuses before projection; valid member passes | §2.3/§2.4 |
| Q2-V3 | Duplicate collection or same edge-list entry / unique entries: both duplicates refuse; include/exclude overlap is permitted and distinct from duplicates | §2.4 |
| Q2-V4 | Missing include even when excluded / missing exclude: first refuses in both grammars, second harmless | §2.4 |
| Q2-V5 | Edge A excludes, edge B requires full / no B: B retains activation/provenance; without B the excluded contribution is absent, subject to support closure | §2.3/§2.4 |
| Q2-V6 | Context plus narrowed runtime edge / full edge: context+selected-command union versus all commands; parser acceptance alone is insufficient | §2.3 |
| Q2-V7 | Retained caller with excluded support / caller excluded or support restored: reject broken projection versus valid closure | §2.4 |
| Q2-V8 | Changed / unchanged selection, including changed selector with same output: bind declared edge semantics/projection pin; raw audit identity unchanged; canonical unchanged input deterministic | §2.4/§2.7 |
| Q2-V9 | Legacy empty collection include / new empty edge include: legacy refuses, new edge can contribute nothing; first contexts-only carrier refuses unsupported filters | §2.4/§2.5 |

Full raw closure admission/audit precedes filters in this new capability. The contexts-only omission concession does not silently weaken that requirement for an edge-filter carrier.

### Q3 — grants, negatives and migration: 12 pairs

| ID | Paired witness and required result | Owner section |
| --- | --- | --- |
| Q3-V1 | Wrong commit/name/source/kind/directory/type/framing/policy / exact satisfying record: every wrong field denies grant, exact AND permits | §3.1 |
| Q3-V2 | Invented Git authority for local input / independently acquired exact Git package: refuse false subject, valid subject can pass | §3.1 |
| Q3-V3 | Successor positive at old schema-1-only and schema-2 ordinary readers / new profile reader: old readers reject and cannot grant a skill; new reader requires complete exact policy | §3.1 |
| Q3-V4 | Revoke C1/H plus grant C2/H moved or renamed / no revoke: same-framing hash denial remains broad; no negative leaves exact grant usable | §3.3 |
| Q3-V5 | Revoke source/commit/H1 plus grant same source/commit/H2 in another kind/directory / unrelated revoke: source+commit denies; unrelated negative permits neighbor | §3.3 |
| Q3-V6 | Known valid negative alongside unknown positive semantics / unknown positive alone: first still denies, second never authorizes; unknown handling cannot suppress negative retrieval | §3.3 |
| Q3-V7 | Successor-only negative detector / schema-2/hash-2 negative / unrelated control: expose and reject split-lane denial; valid negative denies ordinary and profile hash-2 lanes in both managers; future successor negatives require dual issuance | §3.4 |
| Q3-V8 | Schema-2 negative plus successor positive / name-only retrieval drops negative: deny first; second fails completeness; independently test source+commit and hash-only negative lookup including cache/bundle paths | §3.3/§3.6 |
| Q3-V9 | Retrieved hash-1 negative / actual reissued hash-2 negative: hash-1 never matches hash-2 even with equal digest; incomplete migration blocks required rollout; real v2 negative denies both v2 lanes, unrelated negative permits | §3.5 |
| Q3-V10 | Static fail+model pass, absent/failed required model / required predicates pass: bad cases refuse, both pass permits; static-only remains default when model not required | §3.2 |
| Q3-V11 | Missing/rolled-back/expired required negatives / timely complete required set: new required policy refuses first; complete set permits otherwise exact grant; no silent legacy-advisory change | §3.6 |
| Q3-V12 | Conditional shared-key alternative / independently segregated trust keys: detector exposes unsafe ordinary grant; hypothetical segregation must cover every affected legacy trust set and broad negatives; separate endpoint alone fails | §3.1/§3.3 |

The selected initial successor is **positive-only**. Failed audit is not a broad revocation without separately authorized negative issuance. New revocations are schema-2/hash-2 records; if successor negatives are later allocated, dual issuance remains mandatory until a jointly adopted migration replaces it.

### Q4 — native authority, binding and recovery: 20 pairs

| ID | Paired witness and required result | Owner section |
| --- | --- | --- |
| Q4-V1 | Live A after B preparation / fresh B: actual late instruction/skill/MCP reads stay A; prepared B is not activated B | §5.2/§7.3 |
| Q4-V2 | A after allowed invocation activation / forbidden fixed-path activation: simultaneous A→A/B→B only if qualified; otherwise pending/refusal while active or retained-resumable A protected | §7.3 |
| Q4-V3 | Unapproved loader mutation / typed trust/UI write: refuse or retain non-admission for first, permit measured second; known-bad unsealed-control plant detects effect | §6.1/§6.2 |
| Q4-V4 | Native global skill / selected profile skill: enforce declared mode/root policy, preserve selected skill; native discovery is not strict exclusion | §6.2/§9.1 |
| Q4-V5 | Foreign parent memory/rules / selected profile/project instructions: enforce selected memory-off contract at start/late/resume/child without suppressing valid selected instructions | §6.2 |
| Q4-V6 | Real authorized fresh entry / failed mandatory gate: actual selected consumer starts; missing gate refuses before child, no substitute mode/runtime | §8.1 |
| Q4-V7 | Native disposable login / wrong authority: correct stable authority binds, wrong path/backend refuses; no copied credentials | §4.1/§8.2 |
| Q4-V8 | Real model turn / broken content protection: actual admitted generation used; attempted shadow/rewrite refuses combination; inert launch insufficient | §5.5/§8.1 |
| Q4-V9 | Native resume / missing or wrong generation-control receipt: correct resume stays A; bad receipt refuses or explicit stopped readmission, never silent B | §8.3 |
| Q4-V10 | Child entry / unadmitted discovery: selected child binding/context works, external roots never become strict-trusted silently | §6.2/§8.3 |
| Q4-V11 | Refresh from every reader domain / wrong backend or stale copied credential: each reader follows native rotation at approved authority; no secret payload in receipt | §8.2 |
| Q4-V12 | Partial / complete publication: preserve prior generation/holder roots versus admit exact complete new generation; no partial success receipt | §5.1/§7.4 |
| Q4-V13 | Restart/GC with protected A / terminal-unreferenced generation: reconstruct active/unknown/resumable roots; collect only proven unreferenced terminal content | §7.4 |
| Q4-V14 | Launcher crash / authoritative no-start: crash leaves unknown protection; exact no-start allows admitted release | §7.2 |
| Q4-V15 | Reused PID / exact terminal incarnation: first cannot prove release; exact registered observer/session/generation/process and descendants can | §7.2 |
| Q4-V16 | Detached live/uncertain descendant / all descendants terminal: first retains protection, exact terminal tree permits release | §7.2 |
| Q4-V17 | Missing/stale/re-registered observer / exact current observer: refuse release/bind admission with uncertainty; current authoritative evidence necessary | §7.2 |
| Q4-V18 | Audited fenced break / absent fence, exception enablement, reason, CAS or audit: default unfenced break refuses; valid targeted transaction unblocks; explicit abandonment is separate loss-of-protection exception; audit failure retains protection | §7.5 |
| Q4-V19 | Compatible native drift / unknown major or capability loss: L1/L2 warn within policy, L3/L4 recorded acceptance; mandatory capability loss/unknown major refuses all levels; strict exact tuple only | §6.3 |
| Q4-V20 | No mode / explicit mode / unsupported strict: legacy omission unchanged; actual native start passes its own gates; unsupported strict refuses without discovery selection/downgrade | §1.3/§9.1–§9.3 |

Inventory count: **7 + 9 + 12 + 20 = 48 paired rows**. Runtime rows require native observer receipts in addition to static vectors; known-bad plants qualify the observer, not the product. Existing startup corpus and signed-record bytes stay immutable. New corpus manifests bind exact expected outcomes and source pin; each consumer's adoption receipt separately binds its production head and actual exercised caller.

## G2 closure checklist

1. Reserve complete positive-evidence, edge/projection/omission, adapter, authority, generation, control, holder/session and fragment versions through their existing owners; do not reuse provisional numbers.
2. Resolve canonical render/header identity, selector tuple encoding and negative completeness/freshness/level mapping. These are remaining allocations, not reopened semantic alternatives.
3. Attach shared probe evidence for control roster, base/priority, binding, native login/rotation/resume and exact observer incarnation/fencing. Operator selects qualified realization and custodian; unsupported remains refusal.
4. Finalize every P clause and add individual authoritative rows for any further schema or clause changed during drafting. Preserve old replay and exact historical reference identities; allocate the new corpus and enumerate all 48 paired rows plus startup/mode/consumer integration controls.
5. Peer editor, registry authority, holder/custodian and adapter owners review their sections; adoption and production integration follow separately. A draft, static fixture or default strict refusal is not successful native entry.
