# Profile generations — agreed semantic draft

Unreleased N-only successor draft. Baseline **S = ab6b1b0960473b359c84d96e7c7749b9be6011e0**;
authoring skeleton **c59ec5f4a7e78e0f0ce90b92a3be831b2a9d0ace**.
This draft is not adopted wire text, native qualification or permission to execute.
The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT,
RECOMMENDED, NOT RECOMMENDED, MAY and OPTIONAL are interpreted as RFC 2119/8174
when written in capitals.

Every semantic clause has a stable `PG-…` ID. **N** marks agreed semantics;
**P** marks an unresolved placeholder with named dependency. N/P mixed skeleton
sections keep their semantic obligations and technical placeholders separate.
No P placeholder allocates production bytes, version numbers, home variables,
control rosters, transport or executable defaults. No CIP/decision number is
reserved here. Concrete runtime probes still await operators.

New prose, examples, vectors and implementation notes use neutral roles only:
manager, consumer, native authority, session custodian, observer, auditor, issuer,
operator and adapter. Exact existing paths, schema members and adapter IDs remain
protocol identifiers; historical bytes and references are preserved. Named native
mappings, account choices and probe receipts remain outside this specification.

Historical rules below refer to S and the clause-level trace table. A successor
obligation applies only after its complete capability is adopted. It does not
silently change frozen replay or supply a missing production caller.

## 1. Scope, compatibility and terminology

### 1.1 Scope

<a id="pg-scope-01"></a>
**PG-SCOPE-01 (N).** This draft defines opt-in named global-profile semantics. A manager
MUST preserve ordinary project, global and machine-scoped delivery when the new managed
entry is not selected. Selecting a profile alone MUST NOT enable managed mode or
authorize repository discovery. Repository composition and strict project views are
separate capabilities; support for global delivery MUST NOT imply their availability.

<a id="pg-scope-02"></a>
**PG-SCOPE-02 (N).** The guarantee is control of admitted native loader inputs under a
trusted-code boundary. A consumer MUST NOT describe it as confinement of hostile code,
general filesystem access or tools. Unmanaged launches into the same native authority
are outside the trusted-manager guarantee; a manager MUST NOT claim to protect inputs
consumed through such a launch. An unsupported requested capability MUST refuse before
native child or provider creation; it MUST NOT select a different mode or runtime.

### 1.2 Compatibility and old replay

<a id="pg-compat-01"></a>
**PG-COMPAT-01 (N).** Existing declarations, operational locks, closed configuration
objects, default audit policy, global visibility, delivery modes, ignore behavior,
update/removal/GC behavior and shell entry flows MUST retain their existing meaning
outside this capability. No default profile is required. Legacy global resources MUST
NOT silently join a named profile. Explicit migration MUST preview selected inputs,
external native discoveries and omissions before operator approval; encountering an
external native discovery MUST NOT authorize its adoption.

<a id="pg-compat-02"></a>
**PG-COMPAT-02 (N).** A manager MUST preserve frozen schemas, canonical bytes,
signatures, headers and conformance expectations. It MUST NOT relabel an old object or
accept new authority semantics in a closed old carrier. New required semantics MUST use
a separately understood capability and complete versioned carrier; unsupported required
semantics MUST refuse atomically. Snapshot-v1 home bindings and source-home digest MUST
retain their original meaning. Existing checkout × profile × environment project homes
and registrations in project-context §5/§5.1 MUST retain their meaning. Migration to the
profile × runtime native authority MUST be explicit through a successor capability; a
consumer MUST NOT reinterpret old home identity or registration in place.

### 1.3 Explicit registration and consumer mode

<a id="pg-mode-01"></a>
**PG-MODE-01 (N).** A new managed registration and start MUST explicitly select
native-project or strict mode; omission at the new entry MUST refuse. Omission outside
that entry MUST remain legacy behavior. The mode MUST be bound at registration,
composition, launch and resume, exposed by an explicit registration-mode interface, and
never inferred from encountered files. The legacy effective-posture/1 mode none and its
independent permission/no-tools resolution MUST retain their meaning outside the new
capability. A consumer MUST NOT reinterpret none as either explicit managed mode.

<a id="pg-mode-02"></a>
**PG-MODE-02 (N).** Changing an admitted mode MUST require operator action and a fresh
registration/composition identity. A manager MUST continue to accept an existing
registration carrier when it already expresses the same mode semantics; selecting that
mode through an interface flag alone MUST NOT require a new carrier. A consumer MUST NOT
accept new authority, generation, provenance or variant semantics as unrecognized
additions to an old carrier; it MUST require their owning successor capability.

<a id="pg-p-013"></a>
**PG-P-013 (P — placeholder).** Shared carrier editors: exact successor
registration/fragment members, mode/variant flags and migration dispatch; completion
also depends on the consumer entry probes and PG-P-044.

### 1.4 Terminology and reference hierarchy

Editorial terminology: **G1** means the shared native binding probes; **G2**
means the integrated specification-drafting stage. A stage label conveys neither
execution permission nor native qualification. In this document G2 drafts only
agreed N semantics; each P allocation remains pending its named evidence/decision.

<a id="pg-terms-01"></a>
**PG-TERMS-01 (N).** The native authority is the approved stable private state/backend
identity holding native auth, sessions and history; PG-AUTH-01 owns its scope and
launch-binding obligation. The generation is immutable selected nonsecret content; the
local control receipt binds approved loader controls. The project/session binding
relates these objects to mode, policy, runtime and native locator. A consumer MUST
distinguish all four. A portable content digest MUST NOT stand in for native authority,
a session-manager counter or an existing effective-posture/1 protected generation
identity.

<a id="pg-terms-02"></a>
**PG-TERMS-02 (N).** N clauses state agreed successor semantics, subject to adoption and
the complete owning carriers. P entries are explicit unresolved mechanisms, not
executable defaults. A manager MUST NOT advertise a capability on the strength of a
schema draft, fixture label, static source read or this document alone. Historical
references remain authoritative for old replay until an explicitly adopted successor
replaces the identified clause.

## 2. Package exchange, composition and projection

### 2.1 Finite package and directory vocabulary

<a id="pg-package-01"></a>
**PG-PACKAGE-01 (N).** The initial exchange subset MUST retain the closed manifest-1/2
vocabulary, context dependencies, modules, selectors and weights of environments §2–§3.
Existing skill/MCP declarations MUST be preserved. For the initial schema-2 settings
subset, consumers MUST accept only absent/empty settings and MUST refuse nonempty
settings unless a separately adopted owning capability supports them. Manifest,
operational-lock, content-framing and evidence versions MUST be dispatched
independently.

<a id="pg-package-02"></a>
**PG-PACKAGE-02 (N).** A schema-1 skill requirement carrying a selected directory MUST
refuse; schema 2 MUST resolve that directory as the package root without repository-root
or sibling fallback. In normalized subjects the root directory is the required empty
string; in manifest-1/2 root selection remains omission and a literal dot refuses. The
collection selector dot retains its separate meaning. Name/source/commit/kind/directory
MUST identify the actual acquired member.

<a id="pg-p-021"></a>
**PG-P-021 (P — placeholder).** Exchange/carrier editors: complete closed exchange
projection and version reservations; preserve the existing manifest settings identifier
vocabulary rather than inventing new fields.

### 2.2 Acquisition and content identity

<a id="pg-hash-01"></a>
**PG-HASH-01 (N).** New raw package content identities MUST use core §8 framing version
2 exactly, including its domain bytes, length framing, unsigned UTF-8 path order and
byte-preserving file content. The existing version-1 opaque-NUL guard MUST remain
version-1 behavior. Version 2 MUST hash NUL bytes as data. Framing MUST be compared as
well as digest; mode/mtime are not added to this hash.

<a id="pg-hash-02"></a>
**PG-HASH-02 (N).** Acquisition MUST independently refuse escaping, linked, special,
nonportable or platform-colliding payloads before publication under core §2 and the
structural rules. A standalone hash algorithm's link omission or per-path hardlink
record MUST NOT be interpreted as extraction permission. Missing selected content MUST
NOT fall back to another root.

<a id="pg-hash-03"></a>
**PG-HASH-03 (N).** Portable initial evidence MUST identify independently acquired
Git-backed packages at a full resolved commit. Local/path state MUST NOT be represented
by an invented Git commit or portable machine path. Consumers MUST preserve ordinary
local authority under its existing contract. They MUST refuse local portable evidence
and exact path-set subjects unless a separate adopted capability covers that subject;
initial package evidence does not provide that capability.

### 2.3 Graph and overlay union

<a id="pg-compose-01"></a>
**PG-COMPOSE-01 (N).** Composition MUST preserve core §7 dependency ordering and
activation union for resolved contributions. If the §2.4 edge-filter capability is
selected, the manager MUST resolve and pin the complete raw closure before projection;
conflicting same-name source/commit/directory identities MUST refuse before filters can
hide them. In contexts-only delivery, only delivered context members MUST be resolved,
pinned and audited; deferred skill/MCP closure MUST NOT be represented as resolved or
audited. Same-name conflicts among resolved members MUST refuse in either path. Overlay
and edge provenance MUST remain attached to surviving requirements.

<a id="pg-compose-02"></a>
**PG-COMPOSE-02 (N).** Independent surviving contributions MUST unite
context/runtime/command requirements under core §7. One edge's exclusion MUST NOT remove
a full or other requirement imposed through another edge. A full contribution retains
every command; context plus narrowed runtime retains context and the selected command
union.

### 2.4 New edge-scoped whole-skill selection

<a id="pg-filter-01"></a>
**PG-FILTER-01 (N).** This is a new edge-projection capability, not a compatibility
claim for an unlocated historical filter directive. Each application MUST identify one
declaration/overlay occurrence, its declaring and referenced raw subjects, role and
occurrence, including a synthetic root edge. Candidates MUST be the referenced pinned
whole-skill inventory with full/context/runtime/command provenance. Literal
kind/source/directory/name selectors MUST resolve within that edge; bare names, globs
and native-file patterns are outside this capability.

<a id="pg-filter-02"></a>
**PG-FILTER-02 (N).** Before filtering, the complete raw closure MUST be resolved,
pinned and audited. Omitted include MUST select all eligible edge candidates; present
empty include MUST select none; exclude MUST win. Duplicate selectors within either list
MUST refuse rather than deduplicate. Overlap between lists MAY be present. An explicit
missing include MUST refuse even if also excluded; a missing exclude MUST be harmless.
Accepted selector sets MUST have a canonical order; host locale and container iteration
order MUST NOT define it.

Editorial: canonical selector byte allocation remains PG-P-024.

<a id="pg-filter-03"></a>
**PG-FILTER-03 (N).** The effective projection MUST preserve independent-edge provenance
and support closure. Retaining a caller while removing required support MUST refuse;
hidden private retention is not the initial rule. A selection change MUST require
explicit recomposition and a new effective identity even when output happens to be
equal. Raw audit identity MUST remain unchanged.

<a id="pg-filter-04"></a>
**PG-FILTER-04 (N).** Legacy collection acquisition MUST retain its nonempty
include/result, folder/wildcard grammar and duplicate/missing-member rules. New edge
omission/empty projection MUST NOT weaken those rules. The initial contexts-only
delivery MUST refuse filter carriers; it MUST NOT emulate filters by silently omitting
requirements.

<a id="pg-p-024"></a>
**PG-P-024 (P — placeholder).** Selection editors and originating rule owner: canonical
tuple byte encoding/order, edge occurrence encoding, required-understanding carrier and
version. No filter emission or historical compatibility assertion before those
decisions.

### 2.5 Effective delivery and explicit omissions

<a id="pg-delivery-01"></a>
**PG-DELIVERY-01 (N).** Without an explicit contexts-only selection, an unsupported
required skill or MCP delivery MUST refuse without publication. With that selection, the
manager MUST bind the raw declaration digest, delivered context closure and
deterministic deferred-omission inventory in a required-understanding receipt, visible
and checked at install, inspect, launch and session admission.

<a id="pg-delivery-02"></a>
**PG-DELIVERY-02 (N).** Contexts-only MUST audit delivered raw context members and apply
their negative checks. It MUST NOT assert resolution, audit, activation or complete-lock
interoperability for deferred skill/MCP closure. It MUST NOT omit required context
dependencies or admit an unsupported edge-filter capability. Skill plan parsing or
command-root metadata MUST NOT by itself authorize runtime activation.

<a id="pg-p-025"></a>
**PG-P-025 (P — placeholder).** Projection and command-carrier owners: closed
omission/projection correspondence, capability/version and delivery receipt; no
production carrier is allocated here.

### 2.6 Deterministic rendering

<a id="pg-render-01"></a>
**PG-RENDER-01 (N).** Rendering MUST use smallest-ready-name dependency order followed
by stable effective-weight order under declared winner/placement. Equal weights MUST
retain dependency order under either direction. Module applicability, environment/class,
module order and the exact LF part/join rules of environments §5 MUST be preserved.
Absent root context MUST yield no root-context file; present context with zero
applicable modules MUST yield the defined header-only result.

<a id="pg-render-02"></a>
**PG-RENDER-02 (N).** Byte-identical output MUST be claimed only for equal complete
render inputs, including header identity and supplied lock digest, precedence,
environment and form. Equal root/overlay selections with different operational-lock
header inputs do not establish identical documents. A projection digest MUST NOT be
relabelled as an existing full-lock header hash; frozen headers MUST remain unchanged.

Editorial: successor header allocation remains PG-P-026.

<a id="pg-p-026"></a>
**PG-P-026 (P — placeholder).** Exchange editors: common successor render-input/header
identity and canonical digest domain, or explicitly limited equal-input comparison.
Q1-V1 pins the distinction; no new header bytes are frozen here.

### 2.7 Operational locks and export

<a id="pg-lock-01"></a>
**PG-LOCK-01 (N).** Operational locks MUST remain consumer-private unless a complete
whole-lock exchange capability is separately adopted. Export MUST be an explicit,
verified projection binding its original raw/effective identities and omissions. It MUST
NOT relabel or disclose a full private lock as portable content or discard
required-understanding semantics.

<a id="pg-p-027"></a>
**PG-P-027 (P — placeholder).** Lock and exchange owners: closed projection/lock
correspondence and schema dispatch; complete-lock interchange remains outside the
initial capability.

## 3. Evidence and negative authority

### 3.1 Exact positive evidence

<a id="pg-grant-01"></a>
**PG-GRANT-01 (N).** Initial positive profile evidence MUST use a new rejecting shared
record schema, distinct from schemas 1/2, with content framing 2. An old ordinary reader
MUST reject that positive rather than grant a same-commit skill. A nested old-schema
metadata extension or endpoint separation alone MUST NOT be used as the selected
rollout.

Editorial: schema 3 is not reserved; the number and closed body remain PG-P-031.

<a id="pg-grant-02"></a>
**PG-GRANT-02 (N).** Positive authorization MUST require the conjunction of accepted
signature/issuer, name, canonical source, full commit, framing and digest, subject type,
kind, selected directory and every required policy/check/review predicate. A wrong
commit with identical bytes MUST NOT grant. The issuer MUST sign the complete body under
the existing CCJ-1/Ed25519 rules. Evidence MUST be per delivered raw member; package
evidence MUST NOT authorize an exact path-set.

<a id="pg-grant-03"></a>
**PG-GRANT-03 (N).** A new profile reader MUST NOT treat ordinary schema-2 audited
positives as satisfying the successor evidence policy. Unsupported positive semantics
MUST NOT grant. Failed positive audit MUST NOT automatically become a broad revocation;
negative status and issuer authority are separate.

<a id="pg-p-031"></a>
**PG-P-031 (P — placeholder).** Registry signer, validator and client owners: reserve
rejecting schema number and complete closed subject/policy/check/model/signature fields,
status validity and canonical fixtures. No production evidence body is allocated by the
conformance meta-schemas.

### 3.2 Static and optional model predicates

<a id="pg-review-01"></a>
**PG-REVIEW-01 (N).** Static checking MUST be the default. Model review MUST require
explicit request or adopted policy and be a distinct signed review kind/predicate
binding its provenance. Static failure MUST block even if model review passes. Required
model evidence that is missing, failed or not the required kind MUST refuse; static-only
evidence MUST NOT be relabelled reviewed. No implicit model invocation follows from
verification.

<a id="pg-p-032"></a>
**PG-P-032 (P — placeholder).** Audit/policy owners: checker/check-set versions, policy
identifiers/digests, model/review/prompt provenance and complete result/report syntax.

### 3.3 Independent broad negative matching

<a id="pg-deny-01"></a>
**PG-DENY-01 (N).** A consumer MUST retrieve and verify recognized negatives under
configured negative authority independently of positive subject/name/policy filters. A
verified revocation MUST deny when framing is equal AND either content digest matches OR
canonical source and full commit both match. Positive name/kind/directory/review
constraints MUST NOT narrow that negative predicate. Deny wins over any otherwise exact
grant.

<a id="pg-deny-02"></a>
**PG-DENY-02 (N).** Unknown positive semantics MUST NOT suppress a valid recognized
negative in the same response. Consumers MUST NOT interpret an arbitrary unknown outer
schema as a revocation. Query/index/latest/page/cache/offline/bundle/federation paths
MUST preserve the required broad negative set; exact-name-only lookup is insufficient.

### 3.4 Negative issuance and both lanes

<a id="pg-negative-01"></a>
**PG-NEGATIVE-01 (N).** The initial rejecting successor schema is positive-only. New
package revocations MUST be valid separately signed schema-2/hash-2 records delivered to
both ordinary hash-2 skill and exact profile lanes of every participating manager. If
successor negatives are later allocated, new negatives MUST also be separately valid
schema-2/hash-2 records until a jointly adopted migration replaces dual issuance.
Successor-only negative issuance MUST NOT enable rollout.

### 3.5 Framing migration

<a id="pg-migration-01"></a>
**PG-MIGRATION-01 (N).** Hash-1 negatives MUST remain retrieved but MUST NOT match
hash-2 subjects by digest or source+commit, even when bytes are equal. Before enabling
required hash-2 grants, authorized issuers MUST reissue actual signed hash-2 negatives
and provide coverage for each required negative authority. Consumers MUST NOT synthesize
re-signing, convert old grants, infer framing from digest or claim hash-1 records
provide hash-2 coverage.

### 3.6 Completeness, freshness and offline evidence

<a id="pg-coverage-01"></a>
**PG-COVERAGE-01 (N).** At default L3, missing, unavailable, incomplete, rolled-back or
expired required negative/migration coverage MUST block rollout/admission. A known
matching revocation MUST NOT become a warning. Offline evidence MUST identify the
possessed negative set and freshness bounds, not assert absence of newer remote
negatives. Legacy advisory policy MUST NOT be silently redefined; an unsupported
degraded profile policy MUST refuse.

<a id="pg-p-036"></a>
**PG-P-036 (P — placeholder).** Registry/policy owners: coverage/freshness and rollback
receipt, required authority set, validity limits and lower-level mapping. L3 refusal
semantics are agreed; receipt bytes and other-level policy remain open.

## 4. Authority, content and binding objects

### 4.1 Stable native authority

<a id="pg-auth-01"></a>
**PG-AUTH-01 (N).** Within one custody namespace, a named profile × runtime MUST have at
most one operator-approved stable native authority holding native auth, sessions and
history; every successor launch for that profile × runtime MUST bind that authority. Its
identity MUST NOT be derived per launch, per generation or per checkout. The manager MAY
leave unused profile × runtime pairs unprovisioned. The admitted authority MUST retain
its approved private physical-path/backend/origin identity across content updates.
Current profile selectors MUST NOT replace captured origin. Adoption of an existing or
foreign authority MUST require explicit operator action. Profile removal/opt-out MUST
preserve native credentials by default; explicit logout MUST delete only authority owned
by that operation's approved custody namespace.

Amendment boundary at S: this successor changes the native authority scope of
`protocol/project-context.md:222` (§5 first paragraph). The approved projection at :232
and composition/lease/busy rules at :298/:311 attach to the per-checkout binding and
its generation projection through PG-BINDING-01, separately from §5.1 mode/registration.
Old homes and registrations keep their original meaning under PG-COMPAT-02. Shared
fixed-path concurrency remains PG-P-051/073 under PG-ACTIVATE-01; strict worktree trust
and cross-checkout history confinement remain PG-P-062/093. Exact home-variable and
auth mappings remain PG-P-051/082.

<a id="pg-auth-02"></a>
**PG-AUTH-02 (N).** One operator-approved profile × runtime authority across managers is
the target only with qualified common custody, exclusion and refresh coordination.
Separately approved custody namespaces MAY retain separate stable homes/logins as an
explicitly selected initial binding while common custody is unqualified. Namespace
selection does not change PG-AUTH-01's scope. A manager MUST NOT silently fall back,
copy rotating credentials or adopt another authority.

<a id="pg-p-041"></a>
**PG-P-041 (P — placeholder).** Operator, authority and session-custodian owners: shared
versus explicitly separate authority mapping; G1 path/backend/rotation and multi-reader
evidence; actual common exclusion namespace and adoption carrier.

### 4.2 Immutable content generation

<a id="pg-generation-01"></a>
**PG-GENERATION-01 (N).** A generation MUST be immutable and content-addressed from its
declared nonsecret selected inputs and inventory. Credentials, native history and
private authority locators MUST NOT enter its portable bytes or hashes. Identical
complete generation inputs MUST reuse their content identity subject to verification on
reuse; the source-home-bound snapshot-v1 digest MUST NOT become that identity.

<a id="pg-p-042"></a>
**PG-P-042 (P — placeholder).** Generation/carrier editors: complete manifest, digest
domain/canonicalization, selected-input closure and correspondence with raw audit
subjects; no successor manifest fields are allocated here.

### 4.3 Local control projection

<a id="pg-control-01"></a>
**PG-CONTROL-01 (N).** A control receipt MUST identify approved local loader controls
separately from portable generation and native auth/history. A stable native home MUST
be treated as a persistent loader root, not an unconstrained writable seed. Credential
values/history hashes MUST NOT serve as control evidence.

<a id="pg-p-043"></a>
**PG-P-043 (P — placeholder).** Per-tuple G1 control/write-back probes plus
control-carrier owner: exact keys, types, scopes, approved digests and canonical
key/channel encoding; see PG-P-062.

### 4.4 Session/project binding

<a id="pg-binding-01"></a>
**PG-BINDING-01 (N).** Each admitted session/project binding MUST relate the original
generation, control receipt, authority, policy, mode/variant and runtime policy to its
private native locator. Portable generation identity, native session-manager counter and
process incarnation MUST remain distinct. Selecting current/latest content MUST NOT
replace a retained original binding. In the successor, approved project control-item
projection, composition, lease and busy-update rules MUST attach to the per-checkout
binding/generation projection, not silently acquire profile × runtime scope from a
shared native authority. Each leased checkout binding MUST have at most one materialized
composition; concurrent launches on that binding MUST use that composition and require
qualified concurrent native-state access. Repair, switching, skill/CLI sync or changed
compositions targeting that binding MUST wait for its live/unknown leases or refuse
before writes. Checkout scoping MUST NOT bypass shared-path protection under
PG-ACTIVATE-01 and PG-ROOTS-01.

Scope note: cross-checkout concurrency and shared fixed-path projection are unresolved
at PG-P-051/073; separate checkout bindings are not evidence of independent native
reads/writes. The strict trust/history mapping remains PG-P-062/093.

<a id="pg-p-044"></a>
**PG-P-044 (P — placeholder).** Session, project, fragment and command-carrier owners:
complete closed successor binding/locator/retention correspondence; G1 native
resume/child/custody evidence and operator custodian choice.

## 5. Materialization and startup

### 5.1 Materialization and publication

<a id="pg-publish-01"></a>
**PG-PUBLISH-01 (N).** A manager MUST verify selected immutable inputs and
correspondence before publishing a complete generation or exporting its consumer
projection. Publication MUST be atomic under the authoritative mutation transaction and
preserve prior admitted state on interruption. A live consumer MUST NOT use mutable
managed delivery as its content generation. Snapshot-v1 export and home-variable
semantics MUST remain unchanged.

<a id="pg-publish-02"></a>
**PG-PUBLISH-02 (N).** A generation MUST be retained as a protected root before reuse
verification and before any native start. A partial publication MUST NOT emit a
success/admitting receipt. Interrupted state MUST preserve uncertainty and roots until
authoritative recovery; installed bytes MUST NOT manufacture missing expected evidence.

<a id="pg-p-051"></a>
**PG-P-051 (P — placeholder).** G1 root/skill/MCP live A/B and native authority probes,
then operator binding choice: invocation projection versus serialized fixed paths, exact
home-variable mapping and Runtime B confirmation; descriptor/carrier owners allocate the
realization. Cross-checkout shared-authority projection and concurrency depend on
PG-P-073.

### 5.2 Explicit update and activation

<a id="pg-update-01"></a>
**PG-UPDATE-01 (N).** On the new pinned-generation track, update/recomposition MUST be
explicit. Preparing desired B MUST NOT change active A or authorize activation. Faithful
resume MUST NOT refresh. Rollback selects retained admitted content for new sessions
without changing live bindings. An active-A launch, if supported, MUST be explicit and
disclosed rather than silently substituting A for requested B.

<a id="pg-p-052"></a>
**PG-P-052 (P — placeholder).** G1 binding and roots/writer race evidence: qualified
activation transaction, pending/active status and readmission carrier; coordinate the
draft ordinary-launch-refresh proposal without changing its historical text.

### 5.3 Startup levels and independent gates

<a id="pg-level-01"></a>
**PG-LEVEL-01 (N).** The successor MUST preserve the level meanings, default L3,
aggregation, global floor/system lock and raise-only minima of
environment-store-verification-v2 §0. Mismatch MUST win over unavailable at L2–L4; L1
MUST warn for either. L2 MUST refuse any definite mismatch and warn for unavailable
checks; L3 MUST require every required local item to complete and pass. L4 MUST satisfy
L3 locally and require centre confirmation of every required item. An absent,
unconfigured or unreachable centre MUST warn and fall back to a fully passing L3. A
reachable centre's denial, malformed answer or absent/incomplete confirmation of any
required item MUST refuse and MUST NOT trigger fallback. Unsupported requested
policy/level MUST refuse, not weaken.

<a id="pg-level-02"></a>
**PG-LEVEL-02 (N).** Permissive store evidence MUST NOT bypass structural, parsing,
source, credential-authority, executable, explicit-mode, required policy or mandatory
runtime gates. Degraded starts MUST warn and MUST NOT report fully verified status.
Consumers MUST NOT accept new minimum/level fields as unrecognized additions to closed
legacy objects.

Editorial: this chapter supplies no signed configuration section; successor level fields
remain PG-P-053.

<a id="pg-p-053"></a>
**PG-P-053 (P — placeholder).** Startup/carrier and registry-policy owners: successor
level/minimum field allocation, mapping of generation/control/negative receipts to check
classes and supported lower-level combinations; retain baseline level semantics.
Unknown-loader-control mapping below L3 remains pending here; independent structural and
mandatory gates are unchanged.

### 5.4 Home drift and same-pin repair

<a id="pg-repair-01"></a>
**PG-REPAIR-01 (N).** For the baseline managed-home decision, existing home drift
without repair MUST warn, remain non-current and start only at L1; L2–L4 MUST refuse.
Without repair, an absent home MUST refuse at every level. A structural violation MUST
refuse at every level, including with repair. Explicit repair MUST restore an
absent/drifted home from completely verified inputs before launch at every level. L3/L4
MAY first restore ordinary store bytes from the same revalidated pin; L1/L2 MUST NOT
perform that store-byte restoration. Unavailable/mismatching inputs MUST NOT authorize
repair or stale launch under repair.

<a id="pg-repair-02"></a>
**PG-REPAIR-02 (N).** Repair MUST preserve expected identities, selected closure,
authority and pins. It MUST NOT adopt observed drift, change a retained generation or
claim to heal already consumed live memory. Repair MUST NOT bypass overlapping-writer
protection.

<a id="pg-p-054"></a>
**PG-P-054 (P — placeholder).** Startup/holder owners and G1 mixed-write/interruption
probes: classify successor state-home versus generation drift and decide whether any
same-pin live restoration can satisfy protected-writer rules. No live repair exception
is enabled by this draft.

### 5.5 Inventory and consumer correspondence

<a id="pg-inventory-01"></a>
**PG-INVENTORY-01 (N).** Before native child creation, the consumer MUST verify the
admitted generation inventory and descriptor/control/binding correspondence under its
adopted policy. Structural/link/path failures MUST produce no child, provider start or
partial publication. A successful shape check MUST NOT replace content verification or
required authority evidence.

<a id="pg-p-055"></a>
**PG-P-055 (P — placeholder).** Adapter and fragment owners after G1: exact projected
paths, closure/relocation constraints and structural-to-native binding receipt. A
conformance alias is not a production descriptor.

## 6. Native controls and runtime policy

### 6.1 Native state as loader input

<a id="pg-loader-01"></a>
**PG-LOADER-01 (N).** Native persistent state MUST NOT silently introduce loader
controls. Loader-bearing files/keys, overrides, external resources and mixed-file
selectors MUST be pinned/neutralized or covered by explicit approved control evidence.
Only individually measured typed trust/UI/onboarding transitions MAY be writable under
that policy; an entire mixed seed file MUST NOT receive blanket exemption. At L3 and L4,
an unknown loader control MUST refuse admission. A manager MUST NOT silently strip,
refresh or relabel a legacy seed to satisfy the new control policy; explicit migration
and the seed's owning lifecycle rules MUST apply.

<a id="pg-loader-02"></a>
**PG-LOADER-02 (N).** Allowed state writes MUST preserve unrelated approved controls.
Entry-time digest verification MUST NOT be represented as prevention of live reload. If
native consumption can precede enforcement of a promised live control invariant, that
realization MUST remain unsupported for that claim; later drift detection MUST NOT
retroactively certify it.

### 6.2 Per-tuple roster and base/role channels

<a id="pg-p-062"></a>
**PG-P-062 (P — placeholder).** G1 per exact tuple: enumerate every native loader layer,
home/override/external skill/rule/MCP/config/plugin/agent/resource channel; determine
precedence, types, write-back targets, unknown-key handling and base/role preservation.
Observe native home, appended/profile root and nested scopes separately at startup, late
read, default prompt snapshot/rebuild, resume and child entry. Missing observations
remain unqualified. No file/key roster or instruction equivalence is frozen here.
Include strict trust scoping and cross-checkout native-history loader channels within a
shared authority; coordinate with PG-P-093.

### 6.3 Native-compatible versus strict runtime policy

<a id="pg-runtime-01"></a>
**PG-RUNTIME-01 (N).** Strict qualification MUST bind the exact runtime
version/platform/architecture tuple and required capabilities; compatible-range
acceptance MUST NOT transfer to strict. Native-project MAY use an adopted qualified
compatible line/floor and required capability policy. Compatible drift within that
policy MAY warn at L1/L2; L3/L4 MUST require recorded acceptance/requalification.
Unknown major or failed/unknown required capability MUST refuse at every level.

<a id="pg-runtime-02"></a>
**PG-RUNTIME-02 (N).** Resume MUST compare the actual binary against the recorded
runtime policy and generation/control binding. It MUST NOT silently accept the installed
binary under a substituted policy. An unadmitted exact probe candidate MUST refuse;
mock/source evidence MUST NOT be promoted to native acceptance of another binary.

<a id="pg-p-063"></a>
**PG-P-063 (P — placeholder).** Adapter and consumer owners after G1: actual binary
identity, line/floor encoding, required capability roster, acceptance
scope/expiry/invalidation and same-line requalification receipt.

## 7. Holders, retention and recovery

### 7.1 Durable preparation and exact replay

<a id="pg-holder-01"></a>
**PG-HOLDER-01 (N).** Before native execution, the manager MUST durably publish a
blocking prepared holder and canonical request identity. Planned
authority/content/control/policy metadata MUST remain separate from native session,
session-manager generation counter and process incarnation, which MUST be null before
authoritative post-start binding. The actual custodian MUST journal one guarded start
intent before child creation; uncertain intent MUST NOT authorize another start.

<a id="pg-replay-01"></a>
**PG-REPLAY-01 (N).** Validation of syntax, applicable isolation/access preconditions,
current authority and registration MUST precede durable outcome retrieval. An exact
committed nonterminal bind retry with its original canonical payload and expected
revision MUST retrieve the committed outcome without another CAS, revision increment,
logical bind or native start. Different original payload/tuple/revision MUST refuse as
request conflict; a distinct new stale mutation MUST refuse as revision conflict.

Qualification note: fixed disposable-host isolation applies through PG-ISOLATION-01/02
to qualification fixtures, including the agreed A1 fixture. It is not an added
production HL06/HL07 replay precondition.

<a id="pg-replay-02"></a>
**PG-REPLAY-02 (N).** Current terminal disposition MUST take precedence over historical
admitting success. Bind replay after release/break MUST be non-admitting and MUST NOT
revive a binding or permit late execution. Exact acquire outcome retrieval MAY succeed
non-admitting, preserving its historical contract. Replay/bind MUST NOT be treated as
liveness or fresh-start authority. Fresh admission after terminal disposition MUST
require a new request.

<a id="pg-p-071"></a>
**PG-P-071 (P — placeholder).** Holder, fragment and custodian owners: rejecting
successor holder/session/outcome carrier and canonical request/operation allocation.
Preserve home-leases HL05–HL07; accepted fixture operations are not additions to the old
closed union.

### 7.2 Observation, incarnation and no-start

<a id="pg-observer-01"></a>
**PG-OBSERVER-01 (N).** Only the enrolled authoritative custodian MAY provide native
session/process-start/host/registration incarnation and owned-descendant evidence for
bind/reconciliation. PID presence/reuse, launcher death, EOF, detach, age, TTL, a model
response or an unsigned forwarded assertion MUST NOT prove terminal/no-start or release
protection. Prepared, active and unknown holders MUST block conflicting writers; unknown
MUST NOT expire.

<a id="pg-nostart-01"></a>
**PG-NOSTART-01 (N).** No-start release MUST require the exact start slot to be durably
closed/revoked, ownership reconciled and no native call/start proven. A delayed old
prepared reply or launcher MUST NOT execute after that closure. A crash after exec
before bind MUST retain uncertainty and every protected root; fabricated pre-exec
process identity MUST NOT resolve it.

<a id="pg-p-072"></a>
**PG-P-072 (P — placeholder).** Operator and actual session/observer owners: custodian
enrollment, coordinated namespace, exact transport/authentication, finite closed
operation schemas/bounds, descendant/no-start/fence proof interface and failure mapping.
G1 shared fixture evidence and each real consumer integration remain required.

### 7.3 Binding realization and resume retention

<a id="pg-activate-01"></a>
**PG-ACTIVATE-01 (N).** Invocation binding MAY admit concurrent A/B only after the exact
tuple qualifies independent instruction, skill and MCP channels: the same live A MUST
still observe A after B activation while new B observes B. Preparation alone and a
resumed replacement of A MUST NOT satisfy that claim. Fixed-path binding MUST refuse or
keep B pending while active, unknown or retained-resumable A protects those paths.

<a id="pg-retention-01"></a>
**PG-RETENTION-01 (N).** Resume retention MUST be independent of process/holder
termination. Stop, EOF, release or break MUST NOT silently retire A. Retirement MUST be
explicit under policy, record loss of faithful resume and preserve independent sibling
roots. An A resume MUST restore/retain its exact admitted projection under exclusion or
refuse; it MUST NOT follow B.

<a id="pg-p-073"></a>
**PG-P-073 (P — placeholder).** G1 live A/B/root-refresh/skill/MCP/resume results and
operator choice: qualify invocation binding or serialize fixed projection; allocate
pending/active and retained/retired carriers plus explicit stopped readmission. Include
two-checkout shared-authority concurrency against a single-checkout control; separate
bindings alone do not qualify fixed-path independence.

### 7.4 GC, guarded writers and recovery

<a id="pg-roots-01"></a>
**PG-ROOTS-01 (N).** Activation, collection and guarded restoration MUST revalidate the
complete holder/resume/publication roots and expected revision in the same serialized
authority transaction as mutation. A prior roots query MUST NOT authorize a later writer
across new-holder/resume races. Incomplete/unreadable/corrupt/pending authority MUST
retain protection, never become an empty root set.

<a id="pg-roots-02"></a>
**PG-ROOTS-02 (N).** Restart MUST reconstruct every active, prepared, unknown,
retained-resume and sibling root. Collection MUST remove only proven unreferenced
terminal content. Preparing B or releasing/breaking one holder MUST NOT collect A
protected by another root. Publication/reconciliation interruption MUST preserve prior
authoritative state or recoverable protected uncertainty.

<a id="pg-p-074"></a>
**PG-P-074 (P — placeholder).** Holder/store/custodian owners and G1 crash/race probes:
exact journal/publication/recovery and GC carrier correspondence; no timer-based lease
or live-writer exception is allocated.

### 7.5 Fenced operator break and explicit exception

<a id="pg-break-01"></a>
**PG-BREAK-01 (N).** The successor default operator break MUST target one holder with
explicit per-operation intent, bounded nonempty reason reference, expected revision and
independently verified descendant fencing. Tombstone and durable audit MUST commit
atomically. Missing proof, stale CAS or audit failure MUST retain protection or
recoverable pending state; retry MUST produce one logical audit event, and sibling
holders MUST survive.

<a id="pg-break-02"></a>
**PG-BREAK-02 (N).** Deliberate abandonment MAY exist only as a separately enabled
explicit protection exception with reason/CAS/audit and a disclosure that protection was
abandoned. It MUST NOT be labelled terminal evidence or a process kill. Historical HL12
abandonment remains unchanged; this is a stricter successor default, not retroactive
refusal of old replay.

<a id="pg-p-075"></a>
**PG-P-075 (P — placeholder).** Policy/holder owners: exception enablement and bounded
reason carrier, fence proof/verification interface, atomic audit/tombstone schema; G1
targeted break/audit-loss controls and actual custody confirmation.

## 8. Consumer and session lifecycle

### 8.1 One construction path and actual entry

<a id="pg-entry-01"></a>
**PG-ENTRY-01 (N).** A consumer MUST enter through the admitted composition,
verification, materialization and prepared-holder path and enforce mandatory mode,
permission, memory and capability gates before child/provider creation. Metadata
inspection, a returned launch contribution or unused helper MUST NOT count as production
delivery. Unsupported strict refusal alone MUST NOT count as successful native-project
entry.

<a id="pg-entry-02"></a>
**PG-ENTRY-02 (N).** A production completion claim MUST include its actual selected
start and native resume callers with paired refusals. Start-only and resume milestones
MAY be separate releases, but start-only MUST NOT be reported as complete session
lifecycle. Parsing a skill plan or command carrier MUST NOT bypass its independent
activation/admission gates.

<a id="pg-p-081"></a>
**PG-P-081 (P — placeholder).** Consumer/adapter owners after G1: exact entry/session
kind and fragment/command projection; each consumer supplies its own source-head and
actual caller evidence, not inherited discovery qualification.

### 8.2 Native auth continuity

<a id="pg-authflow-01"></a>
**PG-AUTHFLOW-01 (N).** Authentication on the initial successor MUST use approved native
in-place login/rotation at stable authority or one qualified rotation-safe native
reference. Per-generation/per-manager token copies MUST NOT supply hand-off. Wrong
authority/path/backend MUST refuse rather than silently changing auth. Shared reader
domains MUST coordinate refresh or explicitly serialize/refuse shared use. Existing
credential-source contracts MUST retain their meaning outside this capability. An
existing selected source MUST NOT be treated as a qualified successor reference solely
because its legacy consumer can deliver it. Until its source-specific authority/control
correspondence is explicitly adopted and qualified under PG-P-082, selecting that source
at the successor entry MUST refuse before credential retrieval, native child or provider
creation. Consumers MUST NOT silently replace the source with native login, change its
backend, or copy its material into a generation.

<a id="pg-authflow-02"></a>
**PG-AUTHFLOW-02 (N).** Login/turn/resume, refresh success, actual token rotation and
real revocation/staleness MUST be separate observed predicates. Synthetic
copied-authority refusal proves location/provenance only. It MUST NOT qualify OS-store
isolation, real expiry, rotation or revocation. A credential's presence MUST NOT be
reported as a usable session.

<a id="pg-p-082"></a>
**PG-P-082 (P — placeholder).** Operator and source/consumer owners must decide the
successor eligibility and explicit migration of each existing selected credential
source, including the adopted node setup-token source and the selected launcher OAuth
store. An environment-variable delivery channel alone establishes neither equivalence
nor disqualification as a rotation-safe native reference. Completion requires separately
authorized disposable account/OS-store and multi-reader probes, native backend/path
derivation, source-to-authority/control correspondence, reader coordination, fallback
refusal and actual login/refresh/resume qualification. Account, budget, rotation,
home-variable and backend choices remain unresolved; no legacy source is reclassified by
this draft.

### 8.3 Resume, child and readmission

<a id="pg-resume-01"></a>
**PG-RESUME-01 (N).** Faithful resume/child entry MUST verify the original generation
inventory/hash, approved controls/policy, native authority reference/locator,
mode/base/extras and actual runtime-policy binding. Changed/missing/drifted required
binding MUST refuse before native/provider creation while preserving the original
locator and protected roots, or require explicitly stopped readmission with a new
identity. Latest/continue selection MUST NOT stand in for original identity.

<a id="pg-resume-02"></a>
**PG-RESUME-02 (N).** Those checks MUST NOT be described as verification of credential
semantics, every native-history byte, past live memory or all already consumed loader
inputs. Native child ownership MAY include threads within one process; it MUST remain
part of authoritative custody rather than a driver-created substitute child.

<a id="pg-p-083"></a>
**PG-P-083 (P — placeholder).** G1 native session/resume/child correlation and control
observations; session/adapter owners define closed private locator and successor
readmission/policy receipt. Unsupported entries remain explicitly unqualified.

### 8.4 Stop, privacy and retirement

<a id="pg-privacy-01"></a>
**PG-PRIVACY-01 (N).** Stopping a process MUST NOT retire resume roots or authorize
credential deletion. Portable/shared receipts MUST exclude native/private absolute
locators, real process/session/account identifiers, credential values or hashes, native
history hashes, raw transcripts/provider payloads, prompt/tool contents, inherited
environment and free-text secret-bearing diagnostics.

<a id="pg-privacy-02"></a>
**PG-PRIVACY-02 (N).** An exporter MUST use typed in-memory extraction, bounded
classes/aliases and nonsecret generation/control/source digests. Unexpected fields MUST
fail the affected observation closed without raw fallback dumps. Private native history
and mappings MUST require approved retention; a safe shared receipt MUST NOT imply
native history is absent.

## 9. Project variants and future views

### 9.1 Explicit native-project mode

<a id="pg-native-01"></a>
**PG-NATIVE-01 (N).** Native-project MUST disclose its native repository/global
discovery surfaces and approved control policy. Native discovery MUST NOT be represented
as strict exclusion. A mode MUST preserve all mandatory independent gates; unsupported
permissions/memory controls MUST NOT be bypassed by calling the entry native.

### 9.2 Native-project verified against declarations

<a id="pg-verified-01"></a>
**PG-VERIFIED-01 (N).** This explicit variant MUST bind frozen project declarations,
lock and applicable machine-scoped project materialization, adapter/version and exact
expected skill/MCP path/hash inventory. An optional native base MUST be an explicit
operator-approved machine-owned versioned receipt scoped to
paths/cwd/runtime/adapter/digest, not learned from observed drift. Extra native outputs
MUST refuse unless explicit allowed-extra scope/digest is recorded and the weakened
claim disclosed.

<a id="pg-verified-02"></a>
**PG-VERIFIED-02 (N).** The variant MUST compare native files against expected output
before launch and resume and preserve valid declared content as its positive control. It
MUST be described as a drift check using the same renderer, not an independent oracle or
strict isolation. Live-session mutation is not prevented. Instruction/hook/environment
surfaces outside the admitted inventory MUST NOT be claimed verified.

<a id="pg-p-092"></a>
**PG-P-092 (P — placeholder).** Delivery, inventory and consumer owners after actual
skill/MCP activation and native resume: complete generated inventory, base/extras
carrier and native projections. No incomplete delivery or dormant caller qualifies this
variant.

### 9.3 Protected exact project views and strict

<a id="pg-strict-01"></a>
**PG-STRICT-01 (N).** A strict repository profile MUST use an externally protected
sparse checkout/view pinned to full commit and exact selected path inventory, outside
the mutable source repository, without implicit sync. It MUST require exact subject
approval/evidence and a separately qualified exact runtime tuple for startup, late
discovery, resume and child exclusions. Ambient native inputs, including outputs from
the same manager, MUST NOT be exempt from exclusion/re-admission. Strict trust MUST
remain limited to the admitted checkout's prepared worktree; sharing native authority
MUST NOT admit another checkout's trust or retained history as selected context.

<a id="pg-strict-02"></a>
**PG-STRICT-02 (N).** This architecture MUST NOT enable unsupported path-set evidence or
claim sparse preparation from directory scaffolding. Package evidence alone MUST NOT
authorize a selected path set. Strict remains the trusted-code loader boundary of
PG-SCOPE-02; no native-project success transfers certification.

<a id="pg-p-093"></a>
**PG-P-093 (P — placeholder).** Second-track protected-view probe, operator selection
and runtime certification; view/subject editors allocate exact inventory framing,
approval and provenance/retention carriers. No strict tuple or sparse implementation is
qualified here. Shared-authority worktree-trust and cross-checkout history confinement
depend on the PG-P-062 roster and strict certification.

### 9.4 Global plus repository composition

<a id="pg-repository-01"></a>
**PG-REPOSITORY-01 (N).** Repository composition is an architectural extension only,
pending joint operator and protocol-editor discussion before implementation. A
discovered repository profile MUST remain a proposal, not automatic authority. Any
future combination of a named global profile with an approved repository profile MUST be
explicit, preserve provenance and use a separate capability from existing
machine/project delivery terminology. Until that capability is separately adopted,
repository composition MUST refuse without changing global/legacy behavior.

<a id="pg-p-094"></a>
**PG-P-094 (P — placeholder).** Second-track operator/design decision: repository
selection/adoption, composition carrier and mode terminology distinct from existing
delivery modes; preserve room for repository layers without changing old formats.

## 10. Conformance and adoption

### 10.1 Closed schemas and paired conformance

<a id="pg-conformance-01"></a>
**PG-CONFORMANCE-01 (N).** Adopted carriers MUST have complete closed schemas, strict
UTF-8/duplicate/unknown-member handling, finite bounds, canonical bytes and signature
vectors where applicable. The conformance inventory MUST preserve all 48 paired rows in
Appendix B and require exact forbidden outcomes, unchanged preimages and nearby valid
controls. A timeout, unrelated error or reject-everything implementation MUST NOT
satisfy a refusal control.

<a id="pg-conformance-02"></a>
**PG-CONFORMANCE-02 (N).** Conformance witnesses MUST pair known-bad detector controls
with valid neighbors and expose the intended violation independently of the
implementation under test. Two consumers agreeing MUST NOT alone establish correctness.
Exporter witnesses MUST reject or redact synthetic secret-shaped plants while permitting
a valid typed neighbor, with no raw fallback dump. New fixture subcases MAY expand a row
but MUST NOT silently change frozen baseline bytes/verdicts or allocate production
fields. Conformance meta-schema validation MUST NOT be represented as grant, holder or
launch authority.

### 10.2 Static validation, qualification and adoption

<a id="pg-adoption-01"></a>
**PG-ADOPTION-01 (N).** Static schema/model/source results, native qualification and
actual consumer adoption MUST be recorded separately. A manager MUST bind adoption to
its exact source head, corpus pin and exercised production callers. Discovery results
for an exact native tuple MAY be shared as evidence, but each consumer MUST prove its
own integration and MUST NOT inherit native results across a changed
binary/platform/session-kind tuple.

### 10.3 Traceability and immutable input corpus

<a id="pg-trace-01"></a>
**PG-TRACE-01 (N).** A conforming successor publication MUST include one trace row per
amended document clause and owning schema, identifying baseline OID/path/clause, a
specific preserve/add/amend/supersede disposition, one authoritative successor clause,
carrier/capability status, N/P status, joint decision and exact paired vector IDs or an
explicit meta-clause classification. A trace row MUST NOT itself adopt an amendment.
Publication conformance MUST reject missing rows, omnibus document-only dispositions and
vector links that omit the owning clause from the corpus mapping. Splitting a baseline
clause across successor owners MUST preserve every vector assigned to that baseline
clause in the predecessor skeleton revision c59ec5f; publication conformance MUST reject loss of that coverage
as well as inconsistent clause references.

<a id="pg-trace-02"></a>
**PG-TRACE-02 (N).** Frozen baseline vector inputs and startup corpus MUST be reused
unchanged at their recorded source identity. A successor corpus MUST enumerate/hash its
finite input closure and distinguish stubs from instantiated witnesses and executed
results. A current draft stub or semantic catalog validation MUST NOT be reported as
native conformance.

### 10.4 Exact tuple and observer evidence

<a id="pg-evidence-01"></a>
**PG-EVIDENCE-01 (N).** Evidence MUST distinguish native
loader/request/skill/tool-plus-endpoint/auth observations, behavioral inference,
synthetic policy controls and lifecycle-custodian proof. Root home/profile instructions,
nested scopes and base/role preservation MUST remain separate; nested success MUST NOT
certify root rereads. Live-A claims MUST observe the same process/session at their
stated barrier; a replacement resume is not live A. Unsupported/unobserved cells MUST
remain unqualified, with first failures and bounded retries retained.

<a id="pg-isolation-01"></a>
**PG-ISOLATION-01 (N).** Every qualification native entry, including no-account/mock
legs, MUST use a dedicated nonshared disposable host/context without personal
credential-service or agent-socket access. Operator transport MUST be console or
dedicated-key transport with forwarding and inherited multiplexing disabled. Child
environments MUST be constructed from an explicit empty-to-allowlist policy;
agent/credential-helper/token selectors, ambient forge helpers and unapproved egress
MUST be absent. A temporary home or home-derived credential item name MUST NOT be
treated as isolated OS credential storage.

<a id="pg-isolation-02"></a>
**PG-ISOLATION-02 (N).** Fixed preflight MUST refuse a fixture-only planted agent-socket
selector before native/provider start with zero child/agent-query/signature effects. The
adjacent allowlisted canary entry MUST start. OS-managed state outside fixture files
MUST remain inside an approved isolated OS context; personal credential stores/search
lists/browser sessions MUST NOT be inspected, modified or used as controls. Receipts
MUST carry policy digests/attestations and typed predicates, not credential payloads.

<a id="pg-p-104"></a>
**PG-P-104 (P — placeholder).** G1 approved
artifact/source/binary/OS/architecture/session-kind manifests, fixed-isolation controls,
per-channel observations and actual observer custody; owners choose qualified
realization and supported matrix after receipts. The external design digests are
provenance, not passed probes.

## Appendix A. Normative traceability

The following rows identify the coordinated old clauses and owning schemas.
The per-N index then states each rule's specific disposition and exact paired
IDs. Each listed vector contains that authoritative clause in `clause_refs`;
P clauses also occur in `pending_gates`. Every skeleton baseline clause retains
the union of its agreed vector coverage when split across authoritative owners;
no row is populated from a generic inverse vector lookup. A meta clause has no individual
subject pair and is explicitly classified in the corpus. Vector references
denote planned coverage, not executed or complete instantiated witnesses.

Unless marked D1/D2, every baseline reference is at S. New carrier means
unallocated successor, not a reserved number. Existing carriers retain their
old bytes and replay. Trace publication does not itself adopt any amendment.

| Baseline file:line / clause | Specific disposition | Carrier / N–P status | Decision; exact paired vector IDs | Authoritative successor |
| --- | --- | --- | --- | --- |
| `cips/CIP-0014-managed-home-snapshots.md:147` design; :168 recommendation | Add portable content-addressed selected generation; preserve snapshot-v1 source-home digest | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V1 | [PG-GENERATION-01](#pg-generation-01) |
| `cips/CIP-0014-managed-home-snapshots.md:147` design; :168 recommendation | Add qualified live A/B realization or protected fixed-path pending/refusal | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V2, Q4-V8 | [PG-ACTIVATE-01](#pg-activate-01) |
| `cips/CIP-0014-managed-home-snapshots.md:147` design; :168 recommendation | Add separate approved loader-control identity without credential/history hashes | N; old seed/adapter carriers retained; key/runtime receipts P-043/062/063 | Q4; Q4-V3 | [PG-CONTROL-01](#pg-control-01) |
| `cips/CIP-0014-managed-home-snapshots.md:147` design; :168 recommendation | Preserve native discovery disclosure and mandatory independent permissions/memory gates | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V4 | [PG-NATIVE-01](#pg-native-01) |
| `cips/CIP-0014-managed-home-snapshots.md:147` design; :168 recommendation | Preserve protected external exact sparse view; require complete exact-tuple loader exclusions | N architecture; project carriers/qualification P-092–094 | Q4; Q4-V5 | [PG-STRICT-01](#pg-strict-01) |
| `cips/CIP-0014-managed-home-snapshots.md:147` design; :168 recommendation | Preserve one actual construction path and all independent pre-start gates | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V6, Q4-V10 | [PG-ENTRY-01](#pg-entry-01) |
| `cips/CIP-0014-managed-home-snapshots.md:147` design; :168 recommendation | Amend successor project-home authority to stable profile × runtime; preserve origin and owned logout | N; old origin/source bindings retained; authority/reference mapping P-041/051/082 | Q4; Q4-V7, Q4-V11 | [PG-AUTH-01](#pg-auth-01) |
| `cips/CIP-0014-managed-home-snapshots.md:147` design; :168 recommendation | Add original generation/control/authority/mode/runtime verification before faithful resume or stopped readmission | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V9 | [PG-RESUME-01](#pg-resume-01) |
| `cips/CIP-0014-managed-home-snapshots.md:147` design; :168 recommendation | Preserve verified atomic export; add generation publication separate from stable authority | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V12 | [PG-PUBLISH-01](#pg-publish-01) |
| `cips/CIP-0014-managed-home-snapshots.md:147` design; :168 recommendation | Preserve guarded mutation locking; add atomic holder/resume/root revalidation for every writer | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V13 | [PG-ROOTS-01](#pg-roots-01) |
| `cips/CIP-0014-managed-home-snapshots.md:147` design; :168 recommendation | Preserve blocking uncertainty and exact authoritative incarnation/descendant observation | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V14, Q4-V15, Q4-V16, Q4-V17 | [PG-OBSERVER-01](#pg-observer-01) |
| `cips/CIP-0014-managed-home-snapshots.md:147` design; :168 recommendation | Amend successor default to targeted fenced break with atomic durable audit and CAS | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V18 | [PG-BREAK-01](#pg-break-01) |
| `cips/CIP-0014-managed-home-snapshots.md` :177 command/destination; :223 closure/relocation | Add portable content-addressed selected generation; preserve snapshot-v1 source-home digest | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V1 | [PG-GENERATION-01](#pg-generation-01) |
| `cips/CIP-0014-managed-home-snapshots.md` :177 command/destination; :223 closure/relocation | Preserve verified atomic export; add generation publication separate from stable authority | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V12 | [PG-PUBLISH-01](#pg-publish-01) |
| `cips/CIP-0014-managed-home-snapshots.md` :272 manifest/digest; :326 publication | Add portable content-addressed selected generation; preserve snapshot-v1 source-home digest | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q1; Q1-V7 | [PG-GENERATION-01](#pg-generation-01) |
| `cips/CIP-0014-managed-home-snapshots.md` :272 manifest/digest; :326 publication | Preserve verified atomic export; add generation publication separate from stable authority | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V12 | [PG-PUBLISH-01](#pg-publish-01) |
| `cips/CIP-0014-managed-home-snapshots.md` :389 adapter/overlays; :433 delivery/verification | Add qualified live A/B realization or protected fixed-path pending/refusal | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V2, Q4-V8 | [PG-ACTIVATE-01](#pg-activate-01) |
| `cips/CIP-0014-managed-home-snapshots.md` :389 adapter/overlays; :433 delivery/verification | Preserve one actual construction path and all independent pre-start gates | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V6, Q4-V10 | [PG-ENTRY-01](#pg-entry-01) |
| `cips/CIP-0014-managed-home-snapshots.md` :389 adapter/overlays; :433 delivery/verification | Preserve distinct existing source contracts outside this capability; refuse successor selection until source-specific adoption/qualification, without fallback, backend substitution or credential copy | N protection invariant; successor source eligibility and explicit migration remain P-082; authority/reference realization P-041/051/082 | Q4; Q4-V7, Q4-V11 | [PG-AUTHFLOW-01](#pg-authflow-01) |
| `cips/CIP-0014-managed-home-snapshots.md` :389 adapter/overlays; :433 delivery/verification | Add original generation/control/authority/mode/runtime verification before faithful resume or stopped readmission | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V9 | [PG-RESUME-01](#pg-resume-01) |
| `protocol/managed-home-snapshots.md:9` §1 | Preserve verified atomic export; add generation publication separate from stable authority | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V1 | [PG-PUBLISH-01](#pg-publish-01) |
| `protocol/managed-home-snapshots.md:9` §1 | Add qualified live A/B realization or protected fixed-path pending/refusal | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V2 | [PG-ACTIVATE-01](#pg-activate-01) |
| `protocol/managed-home-snapshots.md` :37 §2 | Preserve verified atomic export; add generation publication separate from stable authority | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V12 | [PG-PUBLISH-01](#pg-publish-01) |
| `protocol/managed-home-snapshots.md` :37 §2 | Preserve guarded mutation locking; add atomic holder/resume/root revalidation for every writer | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V13 | [PG-ROOTS-01](#pg-roots-01) |
| `protocol/managed-home-snapshots.md` :37 §2 | Preserve blocking uncertainty and exact authoritative incarnation/descendant observation | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V14 | [PG-OBSERVER-01](#pg-observer-01) |
| `protocol/managed-home-snapshots.md` :99 §3 | Preserve structural pre-start refusal; add generation/control/binding inventory correspondence | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q1; Q1-V5 | [PG-INVENTORY-01](#pg-inventory-01) |
| `protocol/managed-home-snapshots.md` :99 §3 | Preserve private auth/origin boundary; extend shared-receipt exclusions to lifecycle identities/content | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V11 | [PG-PRIVACY-01](#pg-privacy-01) |
| `protocol/managed-home-snapshots.md` :141 §4, especially :175 home bindings and :204 source-home digest | Add portable content-addressed selected generation; preserve snapshot-v1 source-home digest | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V1 | [PG-GENERATION-01](#pg-generation-01) |
| `protocol/managed-home-snapshots.md` :141 §4, especially :175 home bindings and :204 source-home digest | Add qualified live A/B realization or protected fixed-path pending/refusal | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V2 | [PG-ACTIVATE-01](#pg-activate-01) |
| `protocol/managed-home-snapshots.md` :141 §4, especially :175 home bindings and :204 source-home digest | Amend successor project-home authority to stable profile × runtime; preserve origin and owned logout | N; old origin/source bindings retained; authority/reference mapping P-041/051/082 | Q4; Q4-V7, Q4-V11 | [PG-AUTH-01](#pg-auth-01) |
| `protocol/managed-home-snapshots.md` :226 §5 | Preserve structural pre-start refusal; add generation/control/binding inventory correspondence | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q1; Q1-V5 | [PG-INVENTORY-01](#pg-inventory-01) |
| `protocol/managed-home-snapshots.md` :226 §5 | Preserve verified atomic export; add generation publication separate from stable authority | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V12 | [PG-PUBLISH-01](#pg-publish-01) |
| `protocol/managed-home-snapshots.md` :267 §6; :293 pending writable-slot interpretation | Add qualified live A/B realization or protected fixed-path pending/refusal | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V2, Q4-V8 | [PG-ACTIVATE-01](#pg-activate-01) |
| `protocol/managed-home-snapshots.md` :267 §6; :293 pending writable-slot interpretation | Preserve one actual construction path and all independent pre-start gates | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V6, Q4-V10 | [PG-ENTRY-01](#pg-entry-01) |
| `protocol/managed-home-snapshots.md` :267 §6; :293 pending writable-slot interpretation | Preserve distinct existing source contracts outside this capability; refuse successor selection until source-specific adoption/qualification, without fallback, backend substitution or credential copy | N protection invariant; successor source eligibility and explicit migration remain P-082; authority/reference realization P-041/051/082 | Q4; Q4-V7, Q4-V11 | [PG-AUTHFLOW-01](#pg-authflow-01) |
| `protocol/managed-home-snapshots.md` :267 §6; :293 pending writable-slot interpretation | Add original generation/control/authority/mode/runtime verification before faithful resume or stopped readmission | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V9 | [PG-RESUME-01](#pg-resume-01) |
| `protocol/managed-home-snapshots.md` :301 §7 | Preserve private operational locks; add verified export projection rather than relabelling | N; manifests/locks/headers retained; exchange/projection allocation P | Q1; Q1-V7 | [PG-LOCK-01](#pg-lock-01) |
| `protocol/managed-home-snapshots.md` :301 §7 | Preserve structural pre-start refusal; add generation/control/binding inventory correspondence | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V12 | [PG-INVENTORY-01](#pg-inventory-01) |
| `protocol/environments.md:89` §1; :229 §1.3; :310 §1.4 | Preserve frozen headers; narrow equality to complete equal render/header inputs | N; manifests/locks/headers retained; exchange/projection allocation P | Q1; Q1-V1 | [PG-RENDER-02](#pg-render-02) |
| `protocol/environments.md:89` §1; :229 §1.3; :310 §1.4 | Preserve manifest selected-directory grammar; add normalized exact subject root identity | N; manifests/locks/headers retained; exchange/projection allocation P | Q1; Q1-V3 | [PG-PACKAGE-02](#pg-package-02) |
| `protocol/environments.md:89` §1; :229 §1.3; :310 §1.4 | Preserve private operational locks; add verified export projection rather than relabelling | N; manifests/locks/headers retained; exchange/projection allocation P | Q1; Q1-V7 | [PG-LOCK-01](#pg-lock-01) |
| `protocol/environments.md` :470 §2; :552 skill directories; :606 §2.2 | Preserve manifest selected-directory grammar; add normalized exact subject root identity | N; manifests/locks/headers retained; exchange/projection allocation P | Q1; Q1-V3 | [PG-PACKAGE-02](#pg-package-02) |
| `protocol/environments.md` :470 §2; :552 skill directories; :606 §2.2 | Preserve manifest vocabulary and declarations; restrict the initial supported settings subset | N; manifests/locks/headers retained; exchange/projection allocation P | Q1; Q1-V6, Q1-V7 | [PG-PACKAGE-01](#pg-package-01) |
| `protocol/environments.md` :734 §3; :968 §5; :1044 §5.1; :1182 §5.4 | Preserve stable dependency/weight/module/LF ordering and absent versus header-only output | N; baseline hash/union/render semantics retained | Q1; Q1-V1, Q1-V2 | [PG-RENDER-01](#pg-render-01) |
| `protocol/environments.md` :837 §4; :1241 §5.6 | Preserve core hash-1 guard and exact hash-2 byte framing | N; baseline hash/union/render semantics retained | Q1; Q1-V4 | [PG-HASH-01](#pg-hash-01) |
| `protocol/environments.md` :837 §4; :1241 §5.6 | Preserve independent structural acquisition refusal; deny extraction authority inferred from hashing | N; baseline hash/union/render semantics retained | Q1; Q1-V5 | [PG-HASH-02](#pg-hash-02) |
| `protocol/environments.md` :1305 §6 | Add literal include/exclude, duplicate/missing-member rules and canonical selector order | N; new edge capability P-024/025; legacy collections retained | Q2; Q2-V1, Q2-V2, Q2-V3, Q2-V4 | [PG-FILTER-02](#pg-filter-02) |
| `protocol/environments.md` :1305 §6 | Preserve independent-edge full/context/runtime/command activation union | N; baseline hash/union/render semantics retained | Q2; Q2-V5, Q2-V6 | [PG-COMPOSE-02](#pg-compose-02) |
| `protocol/environments.md` :1305 §6 | Add surviving-edge provenance/support closure and explicit effective-identity recomposition | N; new edge capability P-024/025; legacy collections retained | Q2; Q2-V7 | [PG-FILTER-03](#pg-filter-03) |
| `protocol/environments.md` :1305 §6 | Preserve ordering/union; add full-closure gate only for filters and retain contexts-only deferral | N; baseline ordering/union kept; edge P-024/025 and contexts-only P-025 | Q2; Q2-V8 | [PG-COMPOSE-01](#pg-compose-01) |
| `protocol/environments.md` :1305 §6 | Preserve legacy collection rules; refuse filters on initial contexts-only delivery | N; new edge capability P-024/025; legacy collections retained | Q2; Q2-V9 | [PG-FILTER-04](#pg-filter-04) |
| `protocol/environments.md` :1422 §7; :1557 §7.2; :1572 §7.3; :2125 §7.8 | Preserve structural pre-start refusal; add generation/control/binding inventory correspondence | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V1 | [PG-INVENTORY-01](#pg-inventory-01) |
| `protocol/environments.md` :1422 §7; :1557 §7.2; :1572 §7.3; :2125 §7.8 | Add qualified live A/B realization or protected fixed-path pending/refusal | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V2 | [PG-ACTIVATE-01](#pg-activate-01) |
| `protocol/environments.md` :1422 §7; :1557 §7.2; :1572 §7.3; :2125 §7.8 | Add separate approved loader-control identity without credential/history hashes | N; old seed/adapter carriers retained; key/runtime receipts P-043/062/063 | Q4; Q4-V3 | [PG-CONTROL-01](#pg-control-01) |
| `protocol/environments.md` :1422 §7; :1557 §7.2; :1572 §7.3; :2125 §7.8 | Preserve native discovery disclosure and mandatory independent permissions/memory gates | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V4 | [PG-NATIVE-01](#pg-native-01) |
| `protocol/environments.md` :1422 §7; :1557 §7.2; :1572 §7.3; :2125 §7.8 | Preserve protected external exact sparse view; require complete exact-tuple loader exclusions | N architecture; project carriers/qualification P-092–094 | Q4; Q4-V5 | [PG-STRICT-01](#pg-strict-01) |
| `protocol/environments.md` :1422 §7; :1557 §7.2; :1572 §7.3; :2125 §7.8 | Preserve one actual construction path and all independent pre-start gates | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V6, Q4-V10 | [PG-ENTRY-01](#pg-entry-01) |
| `protocol/environments.md` :1637 §7.4; :2008 §7.5; :2035 §7.6 | Amend successor seed admission with typed approved controls and L3 unknown-control refusal; preserve seed lifecycle | N; old seed/adapter carriers retained; key/runtime receipts P-043/062/063 | Q4; Q4-V3, Q4-V4, Q4-V5 | [PG-LOADER-01](#pg-loader-01) |
| `protocol/environments.md` :1637 §7.4; :2008 §7.5; :2035 §7.6 | Preserve distinct existing source contracts outside this capability; refuse successor selection until source-specific adoption/qualification, without fallback, backend substitution or credential copy | N protection invariant; successor source eligibility and explicit migration remain P-082; authority/reference realization P-041/051/082 | Q4; Q4-V7, Q4-V11 | [PG-AUTHFLOW-01](#pg-authflow-01) |
| `protocol/environments.md` :2167 §7.9; :2225 §7.10 | Add separate approved loader-control identity without credential/history hashes | N; old seed/adapter carriers retained; key/runtime receipts P-043/062/063 | Q4; Q4-V3 | [PG-CONTROL-01](#pg-control-01) |
| `protocol/environments.md` :2167 §7.9; :2225 §7.10 | Add native compatible-line policy; preserve strict exact-tuple qualification | N; old seed/adapter carriers retained; key/runtime receipts P-043/062/063 | Q4; Q4-V19 | [PG-RUNTIME-01](#pg-runtime-01) |
| `protocol/environments.md` :2383 §8; :2466 §8.2; :2625 §8.3.1; :2674 §8.4 | Add separate approved loader-control identity without credential/history hashes | N; old seed/adapter carriers retained; key/runtime receipts P-043/062/063 | Q4; Q4-V3 | [PG-CONTROL-01](#pg-control-01) |
| `protocol/environments.md` :2383 §8; :2466 §8.2; :2625 §8.3.1; :2674 §8.4 | Preserve verified atomic export; add generation publication separate from stable authority | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V12 | [PG-PUBLISH-01](#pg-publish-01) |
| `protocol/environments.md` :2383 §8; :2466 §8.2; :2625 §8.3.1; :2674 §8.4 | Preserve guarded mutation locking; add atomic holder/resume/root revalidation for every writer | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V13 | [PG-ROOTS-01](#pg-roots-01) |
| `protocol/environments.md` :2383 §8; :2466 §8.2; :2625 §8.3.1; :2674 §8.4 | Preserve blocking uncertainty and exact authoritative incarnation/descendant observation | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V14 | [PG-OBSERVER-01](#pg-observer-01) |
| `protocol/environments.md` :2777 §9.1; :2916 §9.2 | Preserve legacy delivery/defaults; add explicit migration preview and no implicit global adoption | N; legacy entry/carriers retained; managed successor interface P-013/044 | Q1/Q4; Q1-V6, Q4-V20 | [PG-COMPAT-01](#pg-compat-01) |
| `protocol/environments.md` :2777 §9.1; :2916 §9.2 | Amend successor ordinary refresh to explicit desired-generation update; preserve faithful resume pin | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V2 | [PG-UPDATE-01](#pg-update-01) |
| `protocol/environments.md` :3088 §9.3; :3105 §9.4 | Add literal include/exclude, duplicate/missing-member rules and canonical selector order | N; new edge capability P-024/025; legacy collections retained | Q2; Q2-V1, Q2-V2, Q2-V3, Q2-V4 | [PG-FILTER-02](#pg-filter-02) |
| `protocol/environments.md` :3088 §9.3; :3105 §9.4 | Preserve independent-edge full/context/runtime/command activation union | N; baseline hash/union/render semantics retained | Q2; Q2-V5, Q2-V6 | [PG-COMPOSE-02](#pg-compose-02) |
| `protocol/environments.md` :3088 §9.3; :3105 §9.4 | Add surviving-edge provenance/support closure and explicit effective-identity recomposition | N; new edge capability P-024/025; legacy collections retained | Q2; Q2-V7 | [PG-FILTER-03](#pg-filter-03) |
| `protocol/environments.md` :3088 §9.3; :3105 §9.4 | Preserve ordering/union; add full-closure gate only for filters and retain contexts-only deferral | N; baseline ordering/union kept; edge P-024/025 and contexts-only P-025 | Q2; Q2-V8 | [PG-COMPOSE-01](#pg-compose-01) |
| `protocol/environments.md` :3088 §9.3; :3105 §9.4 | Preserve legacy collection rules; refuse filters on initial contexts-only delivery | N; new edge capability P-024/025; legacy collections retained | Q2; Q2-V9 | [PG-FILTER-04](#pg-filter-04) |
| `protocol/environments.md` :3567 §10; :3891 §10.2; :4187 §10.3 | Preserve one actual construction path and all independent pre-start gates | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V6, Q4-V10, Q4-V20 | [PG-ENTRY-01](#pg-entry-01) |
| `protocol/environments.md` :3567 §10; :3891 §10.2; :4187 §10.3 | Add original generation/control/authority/mode/runtime verification before faithful resume or stopped readmission | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V9 | [PG-RESUME-01](#pg-resume-01) |
| `protocol/environments.md` :4301 §10.5 | Preserve verified atomic export; add generation publication separate from stable authority | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V1 | [PG-PUBLISH-01](#pg-publish-01) |
| `protocol/environments.md` :4301 §10.5 | Add qualified live A/B realization or protected fixed-path pending/refusal | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V2, Q4-V8 | [PG-ACTIVATE-01](#pg-activate-01) |
| `protocol/environments.md` :4301 §10.5 | Preserve distinct existing source contracts outside this capability; refuse successor selection until source-specific adoption/qualification, without fallback, backend substitution or credential copy | N protection invariant; successor source eligibility and explicit migration remain P-082; authority/reference realization P-041/051/082 | Q4; Q4-V7, Q4-V11 | [PG-AUTHFLOW-01](#pg-authflow-01) |
| `protocol/environments.md` :4301 §10.5 | Add original generation/control/authority/mode/runtime verification before faithful resume or stopped readmission | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V9 | [PG-RESUME-01](#pg-resume-01) |
| `protocol/environments.md` :4301 §10.5 | Preserve one actual construction path and all independent pre-start gates | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V10 | [PG-ENTRY-01](#pg-entry-01) |
| `protocol/environments.md` :4482 §12; :4681 §12.1; :4786 §12.2 | Preserve guarded mutation locking; add atomic holder/resume/root revalidation for every writer | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V13 | [PG-ROOTS-01](#pg-roots-01) |
| `protocol/environments.md` :4482 §12; :4681 §12.1; :4786 §12.2 | Preserve merged L1–L4 floor, aggregation and centre-versus-confirmation fallback distinction | N; merged startup meanings retained; successor check/carrier mapping P-053/054 | Q4; Q4-V19 | [PG-LEVEL-01](#pg-level-01) |
| `protocol/environments.md` :5116 home-lease amendment | Preserve HL07 original-revision committed bind replay with applicable production access gates | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V12 | [PG-REPLAY-01](#pg-replay-01) |
| `protocol/environments.md` :5116 home-lease amendment | Preserve guarded mutation locking; add atomic holder/resume/root revalidation for every writer | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V13 | [PG-ROOTS-01](#pg-roots-01) |
| `protocol/environments.md` :5116 home-lease amendment | Preserve blocking uncertainty and exact authoritative incarnation/descendant observation | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V14, Q4-V15, Q4-V16, Q4-V17 | [PG-OBSERVER-01](#pg-observer-01) |
| `protocol/environments.md` :5116 home-lease amendment | Amend successor default to targeted fenced break with atomic durable audit and CAS | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V18 | [PG-BREAK-01](#pg-break-01) |
| `protocol/environment-store-verification-v2.md:11` level table; :26 aggregation; :37 minima | Preserve merged L1–L4 floor, aggregation and centre-versus-confirmation fallback distinction | N; merged startup meanings retained; successor check/carrier mapping P-053/054 | Q4; Q4-V19 | [PG-LEVEL-01](#pg-level-01) |
| `protocol/environment-store-verification-v2.md` :63 home decision, including :78 repair; :91 structural checks; :117 restoration | Preserve home-only repair at every level, store restoration only at L3/L4 and structural refusal | N; merged startup meanings retained; successor check/carrier mapping P-053/054 | Q4; Q4-V3, Q4-V12 | [PG-REPAIR-01](#pg-repair-01) |
| `protocol/project-context.md:10` §1; :47 §2 | Preserve legacy none/permission resolution; add explicit managed-mode admission and registration correspondence | N; legacy entry/carriers retained; managed successor interface P-013/044 | Q4; Q4-V20 | [PG-MODE-01](#pg-mode-01) |
| `protocol/project-context.md` :102 §3 | Preserve manifest selected-directory grammar; add normalized exact subject root identity | N; manifests/locks/headers retained; exchange/projection allocation P | Q1; Q1-V3 | [PG-PACKAGE-02](#pg-package-02) |
| `protocol/project-context.md` :102 §3 | Preserve core hash-1 guard and exact hash-2 byte framing | N; baseline hash/union/render semantics retained | Q1; Q1-V4 | [PG-HASH-01](#pg-hash-01) |
| `protocol/project-context.md` :102 §3 | Preserve independent structural acquisition refusal; deny extraction authority inferred from hashing | N; baseline hash/union/render semantics retained | Q1; Q1-V5 | [PG-HASH-02](#pg-hash-02) |
| `protocol/project-context.md` :102 §3 | Add immutable generation/control/authority/policy/native-locator relation distinct from counters | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q2; Q2-V8 | [PG-BINDING-01](#pg-binding-01) |
| `protocol/project-context.md` :190 §4 | Add declaration/lock/generated-inventory variant with approved base and explicit extras | N architecture; project carriers/qualification P-092–094 | Q4; Q4-V3, Q4-V4, Q4-V20 | [PG-VERIFIED-01](#pg-verified-01) |
| `protocol/project-context.md` :190 §4 | Add launch/resume drift comparison and disclose renderer/live-mutation limits | N architecture; project carriers/qualification P-092–094 | Q4; Q4-V9 | [PG-VERIFIED-02](#pg-verified-02) |
| `protocol/project-context.md` :220 §5; :244 exact adapter; :258 §5.1 | Add native compatible-line policy; preserve strict exact-tuple qualification | N; old seed/adapter carriers retained; key/runtime receipts P-043/062/063 | Q4; Q4-V19 | [PG-RUNTIME-01](#pg-runtime-01) |
| `protocol/project-context.md` :220 §5; :244 exact adapter; :258 §5.1 | Preserve protected external exact sparse view; require complete exact-tuple loader exclusions | N architecture; project carriers/qualification P-092–094 | Q4; Q4-V5, Q4-V10 | [PG-STRICT-01](#pg-strict-01) |
| `protocol/project-context.md` :220 §5; :244 exact adapter; :258 §5.1 | Add declaration/lock/generated-inventory variant with approved base and explicit extras | N architecture; project carriers/qualification P-092–094 | Q4; Q4-V20 | [PG-VERIFIED-01](#pg-verified-01) |
| `protocol/project-context.md` :220 §5; :244 exact adapter; :258 §5.1 | Preserve native discovery disclosure and mandatory independent permissions/memory gates | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V4 | [PG-NATIVE-01](#pg-native-01) |
| `protocol/project-context.md` :220 §5; :244 exact adapter; :258 §5.1 | Preserve one actual construction path and all independent pre-start gates | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V6 | [PG-ENTRY-01](#pg-entry-01) |
| `protocol/project-context.md` :220 §5; :244 exact adapter; :258 §5.1 | Preserve distinct existing source contracts outside this capability; refuse successor selection until source-specific adoption/qualification, without fallback, backend substitution or credential copy | N protection invariant; successor source eligibility and explicit migration remain P-082; authority/reference realization P-041/051/082 | Q4; Q4-V7 | [PG-AUTHFLOW-01](#pg-authflow-01) |
| `protocol/project-context.md` :220 §5; :244 exact adapter; :258 §5.1 | Add qualified live A/B realization or protected fixed-path pending/refusal | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V8 | [PG-ACTIVATE-01](#pg-activate-01) |
| `protocol/project-context.md` :220 §5; :244 exact adapter; :258 §5.1 | Add original generation/control/authority/mode/runtime verification before faithful resume or stopped readmission | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V9 | [PG-RESUME-01](#pg-resume-01) |
| `protocol/project-context.md` :296 §6 | Add original generation/control/authority/mode/runtime verification before faithful resume or stopped readmission | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V9 | [PG-RESUME-01](#pg-resume-01) |
| `protocol/project-context.md` :296 §6 | Preserve HL07 original-revision committed bind replay with applicable production access gates | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V12 | [PG-REPLAY-01](#pg-replay-01) |
| `protocol/project-context.md` :296 §6 | Preserve guarded mutation locking; add atomic holder/resume/root revalidation for every writer | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V13 | [PG-ROOTS-01](#pg-roots-01) |
| `protocol/project-context.md` :296 §6 | Preserve blocking uncertainty and exact authoritative incarnation/descendant observation | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V14, Q4-V15, Q4-V16, Q4-V17 | [PG-OBSERVER-01](#pg-observer-01) |
| `protocol/project-context.md` :296 §6 | Amend successor default to targeted fenced break with atomic durable audit and CAS | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V18 | [PG-BREAK-01](#pg-break-01) |
| `protocol/project-context.md` :329 §7; :395 §8 | Preserve legacy none/permission resolution; add explicit managed-mode admission and registration correspondence | N; legacy entry/carriers retained; managed successor interface P-013/044 | Q4; Q4-V20 | [PG-MODE-01](#pg-mode-01) |
| `protocol/project-context.md` :329 §7; :395 §8 | Preserve one actual construction path and all independent pre-start gates | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V6 | [PG-ENTRY-01](#pg-entry-01) |
| `protocol/project-context.md` :329 §7; :395 §8 | Add original generation/control/authority/mode/runtime verification before faithful resume or stopped readmission | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V9 | [PG-RESUME-01](#pg-resume-01) |
| `protocol/home-leases.md:10` §1; :54 HL05 | Preserve distinct existing source contracts outside this capability; refuse successor selection until source-specific adoption/qualification, without fallback, backend substitution or credential copy | N protection invariant; successor source eligibility and explicit migration remain P-082; authority/reference realization P-041/051/082 | Q4; Q4-V7 | [PG-AUTHFLOW-01](#pg-authflow-01) |
| `protocol/home-leases.md:10` §1; :54 HL05 | Preserve blocking uncertainty and exact authoritative incarnation/descendant observation | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V14, Q4-V15, Q4-V16, Q4-V17 | [PG-OBSERVER-01](#pg-observer-01) |
| `protocol/home-leases.md` :71 HL06; :87 HL07 | Preserve HL07 original-revision committed bind replay with applicable production access gates | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V12, Q4-V14, Q4-V17 | [PG-REPLAY-01](#pg-replay-01) |
| `protocol/home-leases.md` :97 HL08; :103 HL09; :124 HL11 | Add qualified live A/B realization or protected fixed-path pending/refusal | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V2 | [PG-ACTIVATE-01](#pg-activate-01) |
| `protocol/home-leases.md` :97 HL08; :103 HL09; :124 HL11 | Preserve guarded mutation locking; add atomic holder/resume/root revalidation for every writer | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V13 | [PG-ROOTS-01](#pg-roots-01) |
| `protocol/home-leases.md` :97 HL08; :103 HL09; :124 HL11 | Preserve blocking uncertainty and exact authoritative incarnation/descendant observation | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V14, Q4-V15, Q4-V16, Q4-V17 | [PG-OBSERVER-01](#pg-observer-01) |
| `protocol/home-leases.md` :129 HL12; :137 HL13 | Amend successor default to targeted fenced break with atomic durable audit and CAS | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V18 | [PG-BREAK-01](#pg-break-01) |
| `protocol/home-leases.md:144` §3; :265 §5 | Preserve guarded mutation locking; add atomic holder/resume/root revalidation for every writer | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V3, Q4-V12, Q4-V13, Q4-V17 | [PG-ROOTS-01](#pg-roots-01) |
| `protocol/provisioning-origin.md:9` §1; :52 §2 | Amend successor project-home authority to stable profile × runtime; preserve origin and owned logout | N; old origin/source bindings retained; authority/reference mapping P-041/051/082 | Q4; Q4-V7, Q4-V11 | [PG-AUTH-01](#pg-auth-01) |
| `protocol/provisioning-origin.md` :85 §3; :108 §4; :127 §5 | Preserve distinct existing source contracts outside this capability; refuse successor selection until source-specific adoption/qualification, without fallback, backend substitution or credential copy | N protection invariant; successor source eligibility and explicit migration remain P-082; authority/reference realization P-041/051/082 | Q4; Q4-V7, Q4-V11 | [PG-AUTHFLOW-01](#pg-authflow-01) |
| `protocol/provisioning-origin.md` :85 §3; :108 §4; :127 §5 | Preserve guarded mutation locking; add atomic holder/resume/root revalidation for every writer | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V12, Q4-V13 | [PG-ROOTS-01](#pg-roots-01) |
| `protocol/provisioning-origin.md` :85 §3; :108 §4; :127 §5 | Preserve blocking uncertainty and exact authoritative incarnation/descendant observation | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V14 | [PG-OBSERVER-01](#pg-observer-01) |
| `protocol/core.md:1505` activation union; :1521 §8 | Preserve core hash-1 guard and exact hash-2 byte framing | N; baseline hash/union/render semantics retained | Q1; Q1-V4 | [PG-HASH-01](#pg-hash-01) |
| `protocol/core.md:1505` activation union; :1521 §8 | Preserve independent structural acquisition refusal; deny extraction authority inferred from hashing | N; baseline hash/union/render semantics retained | Q1; Q1-V5 | [PG-HASH-02](#pg-hash-02) |
| `protocol/core.md:1505` activation union; :1521 §8 | Preserve independent-edge full/context/runtime/command activation union | N; baseline hash/union/render semantics retained | Q2; Q2-V2, Q2-V5, Q2-V6 | [PG-COMPOSE-02](#pg-compose-02) |
| `protocol/skillfile-sources.md:16` §1, especially :61–78; :83 §2; :119 §3 | Preserve manifest selected-directory grammar; add normalized exact subject root identity | N; manifests/locks/headers retained; exchange/projection allocation P | Q1; Q1-V3 | [PG-PACKAGE-02](#pg-package-02) |
| `protocol/skillfile-sources.md:16` §1, especially :61–78; :83 §2; :119 §3 | Add literal include/exclude, duplicate/missing-member rules and canonical selector order | N; new edge capability P-024/025; legacy collections retained | Q2; Q2-V1, Q2-V2, Q2-V3, Q2-V4 | [PG-FILTER-02](#pg-filter-02) |
| `protocol/skillfile-sources.md:16` §1, especially :61–78; :83 §2; :119 §3 | Preserve legacy collection rules; refuse filters on initial contexts-only delivery | N; new edge capability P-024/025; legacy collections retained | Q2; Q2-V5, Q2-V6, Q2-V7, Q2-V8, Q2-V9 | [PG-FILTER-04](#pg-filter-04) |
| `protocol/skillfile-sources.md` :205 §4 | Preserve local authority; restrict portable first-form evidence to exact Git packages | N; baseline hash/union/render semantics retained | Q3; Q3-V2 | [PG-HASH-03](#pg-hash-03) |
| `protocol/registry.md:94` §3; :102 schema/hash versions; :111 negative match | Strengthen positive grant to complete subject AND policy/check/review matching | N; old signed records retained; positive/policy/coverage allocation P-031/032/036 | Q3; Q3-V1, Q3-V2, Q3-V12 | [PG-GRANT-02](#pg-grant-02) |
| `protocol/registry.md:94` §3; :102 schema/hash versions; :111 negative match | Add rejecting positive-only successor; preserve old-reader refusal and separate negative issuance | N; old signed records retained; positive/policy/coverage allocation P-031/032/036 | Q3; Q3-V3 | [PG-GRANT-01](#pg-grant-01) |
| `protocol/registry.md:94` §3; :102 schema/hash versions; :111 negative match | Preserve broad same-framing hash OR source+commit negative matching independently of positives | N; old signed records retained; positive/policy/coverage allocation P-031/032/036 | Q3; Q3-V4, Q3-V5 | [PG-DENY-01](#pg-deny-01) |
| `protocol/registry.md:94` §3; :102 schema/hash versions; :111 negative match | Preserve known negatives despite unknown positives; extend retrieval completeness across channels | N; old signed records retained; positive/policy/coverage allocation P-031/032/036 | Q3; Q3-V6, Q3-V8 | [PG-DENY-02](#pg-deny-02) |
| `protocol/registry.md:94` §3; :102 schema/hash versions; :111 negative match | Add initial positive-only rollout with schema-2/hash-2 negatives and future dual issuance | N; old signed records retained; positive/policy/coverage allocation P-031/032/036 | Q3; Q3-V7 | [PG-NEGATIVE-01](#pg-negative-01) |
| `protocol/registry.md:94` §3; :102 schema/hash versions; :111 negative match | Preserve framing separation; add real signed hash-2 negative reissue before rollout | N; old signed records retained; positive/policy/coverage allocation P-031/032/036 | Q3; Q3-V9 | [PG-MIGRATION-01](#pg-migration-01) |
| `protocol/registry.md` :128 §4; :134 deny-wins | Preserve broad same-framing hash OR source+commit negative matching independently of positives | N; old signed records retained; positive/policy/coverage allocation P-031/032/036 | Q3; Q3-V4, Q3-V5 | [PG-DENY-01](#pg-deny-01) |
| `protocol/registry.md` :128 §4; :134 deny-wins | Preserve known negatives despite unknown positives; extend retrieval completeness across channels | N; old signed records retained; positive/policy/coverage allocation P-031/032/036 | Q3; Q3-V6, Q3-V8 | [PG-DENY-02](#pg-deny-02) |
| `protocol/registry.md` :128 §4; :134 deny-wins | Add initial positive-only rollout with schema-2/hash-2 negatives and future dual issuance | N; old signed records retained; positive/policy/coverage allocation P-031/032/036 | Q3; Q3-V7 | [PG-NEGATIVE-01](#pg-negative-01) |
| `protocol/registry.md` :128 §4; :134 deny-wins | Preserve framing separation; add real signed hash-2 negative reissue before rollout | N; old signed records retained; positive/policy/coverage allocation P-031/032/036 | Q3; Q3-V9 | [PG-MIGRATION-01](#pg-migration-01) |
| `protocol/registry.md` :171 §5; :288 §5.1; :338 §7; :358 §8 | Add required L3 negative coverage/freshness refusal without changing legacy advisory policy | N; old signed records retained; positive/policy/coverage allocation P-031/032/036 | Q3; Q3-V8, Q3-V11 | [PG-COVERAGE-01](#pg-coverage-01) |
| `protocol/registry.md` :171 §5; :288 §5.1; :338 §7; :358 §8 | Preserve framing separation; add real signed hash-2 negative reissue before rollout | N; old signed records retained; positive/policy/coverage allocation P-031/032/036 | Q3; Q3-V9 | [PG-MIGRATION-01](#pg-migration-01) |
| `protocol/registry.md` :394 §9; :505 §9.3; :569 §10 | Add rejecting positive-only successor; preserve old-reader refusal and separate negative issuance | N; old signed records retained; positive/policy/coverage allocation P-031/032/036 | Q3; Q3-V3 | [PG-GRANT-01](#pg-grant-01) |
| `protocol/registry.md` :394 §9; :505 §9.3; :569 §10 | Preserve known negatives despite unknown positives; extend retrieval completeness across channels | N; old signed records retained; positive/policy/coverage allocation P-031/032/036 | Q3; Q3-V6, Q3-V8 | [PG-DENY-02](#pg-deny-02) |
| `protocol/registry.md` :394 §9; :505 §9.3; :569 §10 | Add initial positive-only rollout with schema-2/hash-2 negatives and future dual issuance | N; old signed records retained; positive/policy/coverage allocation P-031/032/036 | Q3; Q3-V7 | [PG-NEGATIVE-01](#pg-negative-01) |
| `protocol/registry.md` :394 §9; :505 §9.3; :569 §10 | Preserve framing separation; add real signed hash-2 negative reissue before rollout | N; old signed records retained; positive/policy/coverage allocation P-031/032/036 | Q3; Q3-V9 | [PG-MIGRATION-01](#pg-migration-01) |
| `protocol/profile-skill-plan-proposal.md:19,95,120,168,221` | Preserve independent-edge full/context/runtime/command activation union | N; baseline hash/union/render semantics retained | Q2; Q2-V5, Q2-V6 | [PG-COMPOSE-02](#pg-compose-02) |
| `protocol/profile-skill-plan-proposal.md:19,95,120,168,221` | Add surviving-edge provenance/support closure and explicit effective-identity recomposition | N; new edge capability P-024/025; legacy collections retained | Q2; Q2-V7, Q2-V8 | [PG-FILTER-03](#pg-filter-03) |
| `protocol/profile-skill-plan-proposal.md:19,95,120,168,221` | Preserve one actual construction path and all independent pre-start gates | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V4 | [PG-ENTRY-01](#pg-entry-01) |
| `protocol/profile-skill-plan-proposal.md:19,95,120,168,221` | Add original generation/control/authority/mode/runtime verification before faithful resume or stopped readmission | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V9 | [PG-RESUME-01](#pg-resume-01) |
| `protocol/profile-command-roots.md:40,104,191,237,313,499,538` | Add explicit incomplete context delivery and visible required-understanding omissions | N; manifests/locks/headers retained; exchange/projection allocation P | Q1; Q1-V6 | [PG-DELIVERY-01](#pg-delivery-01) |
| `protocol/profile-command-roots.md:40,104,191,237,313,499,538` | Preserve private operational locks; add verified export projection rather than relabelling | N; manifests/locks/headers retained; exchange/projection allocation P | Q1; Q1-V7 | [PG-LOCK-01](#pg-lock-01) |
| `protocol/profile-command-roots.md:40,104,191,237,313,499,538` | Preserve one actual construction path and all independent pre-start gates | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V6 | [PG-ENTRY-01](#pg-entry-01) |
| `protocol/profile-command-roots.md:40,104,191,237,313,499,538` | Add original generation/control/authority/mode/runtime verification before faithful resume or stopped readmission | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V9 | [PG-RESUME-01](#pg-resume-01) |
| `protocol/profile-command-roots.md:40,104,191,237,313,499,538` | Preserve guarded mutation locking; add atomic holder/resume/root revalidation for every writer | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V13 | [PG-ROOTS-01](#pg-roots-01) |
| `protocol/profile-command-path.md:8,54,132,233`; `protocol/profile-command-root-admission.md:103,183,265,286,742` | Amend successor seed admission with typed approved controls and L3 unknown-control refusal; preserve seed lifecycle | N; old seed/adapter carriers retained; key/runtime receipts P-043/062/063 | Q4; Q4-V3 | [PG-LOADER-01](#pg-loader-01) |
| `protocol/profile-command-path.md:8,54,132,233`; `protocol/profile-command-root-admission.md:103,183,265,286,742` | Preserve one actual construction path and all independent pre-start gates | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V6, Q4-V10 | [PG-ENTRY-01](#pg-entry-01) |
| `protocol/profile-command-path.md:8,54,132,233`; `protocol/profile-command-root-admission.md:103,183,265,286,742` | Preserve verified atomic export; add generation publication separate from stable authority | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V12 | [PG-PUBLISH-01](#pg-publish-01) |
| `protocol/rc7-carriers.md:11,71,148,219,242` | Preserve frozen carriers and checkout-scoped homes; add explicit successor-only authority migration | N; legacy entry/carriers retained; managed successor interface P-013/044 | Q1; Q1-V7 | [PG-COMPAT-02](#pg-compat-02) |
| `protocol/rc7-carriers.md:11,71,148,219,242` | Add rejecting positive-only successor; preserve old-reader refusal and separate negative issuance | N; old signed records retained; positive/policy/coverage allocation P-031/032/036 | Q3; Q3-V3 | [PG-GRANT-01](#pg-grant-01) |
| `protocol/profile-codex-settings.md:11,50,96,143,178,243` @S | Add separate approved loader-control identity without credential/history hashes | N; old seed/adapter carriers retained; key/runtime receipts P-043/062/063 | Q4; Q4-V3 | [PG-CONTROL-01](#pg-control-01) |
| `protocol/profile-codex-settings.md:11,50,96,143,178,243` @S | Preserve distinct existing source contracts outside this capability; refuse successor selection until source-specific adoption/qualification, without fallback, backend substitution or credential copy | N protection invariant; successor source eligibility and explicit migration remain P-082; authority/reference realization P-041/051/082 | Q4; Q4-V7, Q4-V11 | [PG-AUTHFLOW-01](#pg-authflow-01) |
| `decisions/0010-agent-environment-profiles.md:22,202,488,587,682,711` | Add explicit incomplete context delivery and visible required-understanding omissions | N; manifests/locks/headers retained; exchange/projection allocation P | Q1; Q1-V6 | [PG-DELIVERY-01](#pg-delivery-01) |
| `decisions/0010-agent-environment-profiles.md:22,202,488,587,682,711` | Add portable content-addressed selected generation; preserve snapshot-v1 source-home digest | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V1 | [PG-GENERATION-01](#pg-generation-01) |
| `decisions/0010-agent-environment-profiles.md:22,202,488,587,682,711` | Add qualified live A/B realization or protected fixed-path pending/refusal | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V2 | [PG-ACTIVATE-01](#pg-activate-01) |
| `decisions/0010-agent-environment-profiles.md:22,202,488,587,682,711` | Amend successor project-home authority to stable profile × runtime; preserve origin and owned logout | N; old origin/source bindings retained; authority/reference mapping P-041/051/082 | Q4; Q4-V7 | [PG-AUTH-01](#pg-auth-01) |
| `decisions/0010-agent-environment-profiles.md:22,202,488,587,682,711` | Preserve distinct existing source contracts outside this capability; refuse successor selection until source-specific adoption/qualification, without fallback, backend substitution or credential copy | N protection invariant; successor source eligibility and explicit migration remain P-082; authority/reference realization P-041/051/082 | Q4; Q4-V11 | [PG-AUTHFLOW-01](#pg-authflow-01) |
| `decisions/0012-context-packages-and-semver-locks.md:249,446,480,531,547,645,669` | Preserve stable dependency/weight/module/LF ordering and absent versus header-only output | N; baseline hash/union/render semantics retained | Q1; Q1-V1, Q1-V2 | [PG-RENDER-01](#pg-render-01) |
| `decisions/0012-context-packages-and-semver-locks.md:249,446,480,531,547,645,669` | Preserve manifest selected-directory grammar; add normalized exact subject root identity | N; manifests/locks/headers retained; exchange/projection allocation P | Q1; Q1-V3 | [PG-PACKAGE-02](#pg-package-02) |
| `decisions/0012-context-packages-and-semver-locks.md:249,446,480,531,547,645,669` | Preserve core hash-1 guard and exact hash-2 byte framing | N; baseline hash/union/render semantics retained | Q1; Q1-V4 | [PG-HASH-01](#pg-hash-01) |
| `decisions/0012-context-packages-and-semver-locks.md:249,446,480,531,547,645,669` | Preserve independent structural acquisition refusal; deny extraction authority inferred from hashing | N; baseline hash/union/render semantics retained | Q1; Q1-V5 | [PG-HASH-02](#pg-hash-02) |
| `decisions/0012-context-packages-and-semver-locks.md:249,446,480,531,547,645,669` | Add explicit incomplete context delivery and visible required-understanding omissions | N; manifests/locks/headers retained; exchange/projection allocation P | Q1; Q1-V6 | [PG-DELIVERY-01](#pg-delivery-01) |
| `decisions/0012-context-packages-and-semver-locks.md:249,446,480,531,547,645,669` | Preserve private operational locks; add verified export projection rather than relabelling | N; manifests/locks/headers retained; exchange/projection allocation P | Q1; Q1-V7 | [PG-LOCK-01](#pg-lock-01) |
| `decisions/0012-context-packages-and-semver-locks.md:249,446,480,531,547,645,669` | Add literal include/exclude, duplicate/missing-member rules and canonical selector order | N; new edge capability P-024/025; legacy collections retained | Q2; Q2-V1, Q2-V2, Q2-V3, Q2-V4 | [PG-FILTER-02](#pg-filter-02) |
| `decisions/0012-context-packages-and-semver-locks.md:249,446,480,531,547,645,669` | Preserve independent-edge full/context/runtime/command activation union | N; baseline hash/union/render semantics retained | Q2; Q2-V5, Q2-V6 | [PG-COMPOSE-02](#pg-compose-02) |
| `decisions/0012-context-packages-and-semver-locks.md:249,446,480,531,547,645,669` | Add surviving-edge provenance/support closure and explicit effective-identity recomposition | N; new edge capability P-024/025; legacy collections retained | Q2; Q2-V7 | [PG-FILTER-03](#pg-filter-03) |
| `decisions/0012-context-packages-and-semver-locks.md:249,446,480,531,547,645,669` | Preserve ordering/union; add full-closure gate only for filters and retain contexts-only deferral | N; baseline ordering/union kept; edge P-024/025 and contexts-only P-025 | Q2; Q2-V8 | [PG-COMPOSE-01](#pg-compose-01) |
| `decisions/0012-context-packages-and-semver-locks.md:249,446,480,531,547,645,669` | Preserve legacy collection rules; refuse filters on initial contexts-only delivery | N; new edge capability P-024/025; legacy collections retained | Q2; Q2-V9 | [PG-FILTER-04](#pg-filter-04) |
| `decisions/0013-execution-ownership-and-launch-plans.md:87,218,286,445,477`; `decisions/0019-fragment-consumers-and-one-construction-site.md:68,93` | Preserve one actual construction path and all independent pre-start gates | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V6, Q4-V10 | [PG-ENTRY-01](#pg-entry-01) |
| `decisions/0013-execution-ownership-and-launch-plans.md:87,218,286,445,477`; `decisions/0019-fragment-consumers-and-one-construction-site.md:68,93` | Add original generation/control/authority/mode/runtime verification before faithful resume or stopped readmission | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V9 | [PG-RESUME-01](#pg-resume-01) |
| `decisions/0029-provisioning-origin.md:10`; `decisions/0032-managed-home-separate-login.md:28,92,164` | Amend successor project-home authority to stable profile × runtime; preserve origin and owned logout | N; old origin/source bindings retained; authority/reference mapping P-041/051/082 | Q4; Q4-V7 | [PG-AUTH-01](#pg-auth-01) |
| `decisions/0029-provisioning-origin.md:10`; `decisions/0032-managed-home-separate-login.md:28,92,164` | Preserve distinct existing source contracts outside this capability; refuse successor selection until source-specific adoption/qualification, without fallback, backend substitution or credential copy | N protection invariant; successor source eligibility and explicit migration remain P-082; authority/reference realization P-041/051/082 | Q4; Q4-V11 | [PG-AUTHFLOW-01](#pg-authflow-01) |
| D1 `decisions/0033-launch-lock-refresh-compatible.md:53,91` | Amend successor ordinary refresh to explicit desired-generation update; preserve faithful resume pin | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V1, Q4-V2 | [PG-UPDATE-01](#pg-update-01) |
| D1 `decisions/0033-launch-lock-refresh-compatible.md:53,91` | Add original generation/control/authority/mode/runtime verification before faithful resume or stopped readmission | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V9 | [PG-RESUME-01](#pg-resume-01) |
| D2 `cips/CIP-0028-claude-read-scope.md:11` | Preserve protected external exact sparse view; require complete exact-tuple loader exclusions | N architecture; project carriers/qualification P-092–094 | Q4; Q4-V5, Q4-V10 | [PG-STRICT-01](#pg-strict-01) |
| D2 `cips/CIP-0028-claude-read-scope.md:11` | Preserve one actual construction path and all independent pre-start gates | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V6 | [PG-ENTRY-01](#pg-entry-01) |
| `schemas/v1/audit-record-v1.schema.json:1` | Add rejecting positive-only successor; preserve old-reader refusal and separate negative issuance | N; old signed records retained; positive/policy/coverage allocation P-031/032/036 | Q3; Q3-V3 | [PG-GRANT-01](#pg-grant-01) |
| `schemas/v1/audit-record-v1.schema.json:1` | Preserve framing separation; add real signed hash-2 negative reissue before rollout | N; old signed records retained; positive/policy/coverage allocation P-031/032/036 | Q3; Q3-V9 | [PG-MIGRATION-01](#pg-migration-01) |
| `schemas/v1/audit-record-v2.schema.json:1` | Strengthen positive grant to complete subject AND policy/check/review matching | N; old signed records retained; positive/policy/coverage allocation P-031/032/036 | Q3; Q3-V1, Q3-V2, Q3-V12 | [PG-GRANT-02](#pg-grant-02) |
| `schemas/v1/audit-record-v2.schema.json:1` | Add rejecting positive-only successor; preserve old-reader refusal and separate negative issuance | N; old signed records retained; positive/policy/coverage allocation P-031/032/036 | Q3; Q3-V3 | [PG-GRANT-01](#pg-grant-01) |
| `schemas/v1/audit-record-v2.schema.json:1` | Preserve broad same-framing hash OR source+commit negative matching independently of positives | N; old signed records retained; positive/policy/coverage allocation P-031/032/036 | Q3; Q3-V4, Q3-V5 | [PG-DENY-01](#pg-deny-01) |
| `schemas/v1/audit-record-v2.schema.json:1` | Preserve known negatives despite unknown positives; extend retrieval completeness across channels | N; old signed records retained; positive/policy/coverage allocation P-031/032/036 | Q3; Q3-V6, Q3-V8 | [PG-DENY-02](#pg-deny-02) |
| `schemas/v1/audit-record-v2.schema.json:1` | Add initial positive-only rollout with schema-2/hash-2 negatives and future dual issuance | N; old signed records retained; positive/policy/coverage allocation P-031/032/036 | Q3; Q3-V7 | [PG-NEGATIVE-01](#pg-negative-01) |
| `schemas/v1/audit-record-v2.schema.json:1` | Preserve framing separation; add real signed hash-2 negative reissue before rollout | N; old signed records retained; positive/policy/coverage allocation P-031/032/036 | Q3; Q3-V9 | [PG-MIGRATION-01](#pg-migration-01) |
| `schemas/v1/audit-record-v2.schema.json:1` | Preserve static default; add explicit signed additive model-review predicate | N; old signed records retained; positive/policy/coverage allocation P-031/032/036 | Q3; Q3-V10 | [PG-REVIEW-01](#pg-review-01) |
| `schemas/v1/audit-record-v2.schema.json:1` | Add required L3 negative coverage/freshness refusal without changing legacy advisory policy | N; old signed records retained; positive/policy/coverage allocation P-031/032/036 | Q3; Q3-V11 | [PG-COVERAGE-01](#pg-coverage-01) |
| `schemas/managed-home-snapshot-v1/managed-home-snapshot-v1.schema.json:6` | Add portable content-addressed selected generation; preserve snapshot-v1 source-home digest | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q1; Q1-V7 | [PG-GENERATION-01](#pg-generation-01) |
| `schemas/managed-home-snapshot-v1/managed-home-snapshot-v1.schema.json:6` | Preserve verified atomic export; add generation publication separate from stable authority | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V12 | [PG-PUBLISH-01](#pg-publish-01) |
| `schemas/managed-home-snapshot-v1/snapshot-launch-v1.schema.json:1` | Add portable content-addressed selected generation; preserve snapshot-v1 source-home digest | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V1 | [PG-GENERATION-01](#pg-generation-01) |
| `schemas/managed-home-snapshot-v1/snapshot-launch-v1.schema.json:1` | Add qualified live A/B realization or protected fixed-path pending/refusal | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V2 | [PG-ACTIVATE-01](#pg-activate-01) |
| `schemas/managed-home-snapshot-v1/snapshot-launch-v1.schema.json:1` | Amend successor project-home authority to stable profile × runtime; preserve origin and owned logout | N; old origin/source bindings retained; authority/reference mapping P-041/051/082 | Q4; Q4-V7 | [PG-AUTH-01](#pg-auth-01) |
| `schemas/managed-home-snapshot-v1/snapshot-launch-v1.schema.json:1` | Preserve distinct existing source contracts outside this capability; refuse successor selection until source-specific adoption/qualification, without fallback, backend substitution or credential copy | N protection invariant; successor source eligibility and explicit migration remain P-082; authority/reference realization P-041/051/082 | Q4; Q4-V11 | [PG-AUTHFLOW-01](#pg-authflow-01) |
| `schemas/project-context-leaf1-v1/registration.schema.json:7,43` | Preserve legacy none/permission resolution; add explicit managed-mode admission and registration correspondence | N; legacy entry/carriers retained; managed successor interface P-013/044 | Q4; Q4-V20 | [PG-MODE-01](#pg-mode-01) |
| `schemas/project-context-leaf1-v1/composition.schema.json:7,115` | Add immutable generation/control/authority/policy/native-locator relation distinct from counters | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V9 | [PG-BINDING-01](#pg-binding-01) |
| `schemas/project-context-leaf1-v1/composition.schema.json:7,115` | Add declaration/lock/generated-inventory variant with approved base and explicit extras | N architecture; project carriers/qualification P-092–094 | Q4; Q4-V20 | [PG-VERIFIED-01](#pg-verified-01) |
| `schemas/project-context-leaf1-v1/adapter.schema.json:7` | Preserve one actual construction path and all independent pre-start gates | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V6 | [PG-ENTRY-01](#pg-entry-01) |
| `schemas/project-context-leaf1-v1/adapter.schema.json:7` | Add native compatible-line policy; preserve strict exact-tuple qualification | N; old seed/adapter carriers retained; key/runtime receipts P-043/062/063 | Q4; Q4-V19 | [PG-RUNTIME-01](#pg-runtime-01) |
| `schemas/project-context-leaf1-v1/control-receipt.schema.json:7` | Add separate approved loader-control identity without credential/history hashes | N; old seed/adapter carriers retained; key/runtime receipts P-043/062/063 | Q4; Q4-V3, Q4-V9 | [PG-CONTROL-01](#pg-control-01) |
| `schemas/project-context-leaf1-v1/generation.schema.json:7` | Add portable content-addressed selected generation; preserve snapshot-v1 source-home digest | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V1, Q4-V2 | [PG-GENERATION-01](#pg-generation-01) |
| `schemas/project-context-leaf1-v1/generation.schema.json:7` | Add immutable generation/control/authority/policy/native-locator relation distinct from counters | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V9 | [PG-BINDING-01](#pg-binding-01) |
| `schemas/project-context-leaf1-v1/root-binding.schema.json:1` | Add immutable generation/control/authority/policy/native-locator relation distinct from counters | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V9 | [PG-BINDING-01](#pg-binding-01) |
| `schemas/project-context-leaf1-v1/root-binding.schema.json:1` | Preserve guarded mutation locking; add atomic holder/resume/root revalidation for every writer | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V13 | [PG-ROOTS-01](#pg-roots-01) |
| `schemas/project-context-leaf1-v1/lease.schema.json:1` | Preserve blocking uncertainty and exact authoritative incarnation/descendant observation | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V14, Q4-V15, Q4-V16, Q4-V17 | [PG-OBSERVER-01](#pg-observer-01) |
| `schemas/project-context-leaf1-v1/lease.schema.json:1` | Amend successor default to targeted fenced break with atomic durable audit and CAS | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V18 | [PG-BREAK-01](#pg-break-01) |
| `schemas/project-context-leaf1-v1/item.schema.json:1` | Refuse package evidence as path-set approval and keep strict separate from native success | N architecture; project carriers/qualification P-092–094 | Q4; Q4-V4, Q4-V10 | [PG-STRICT-02](#pg-strict-02) |
| `schemas/project-context-leaf1-v1/snapshot-manifest.schema.json:1` | Preserve structural pre-start refusal; add generation/control/binding inventory correspondence | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V4, Q4-V9 | [PG-INVENTORY-01](#pg-inventory-01) |
| `schemas/project-context-leaf1-v1/project-context.schema.json:1` | Preserve one actual construction path and all independent pre-start gates | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V6 | [PG-ENTRY-01](#pg-entry-01) |
| `schemas/project-context-leaf1-v1/project-context.schema.json:1` | Add original generation/control/authority/mode/runtime verification before faithful resume or stopped readmission | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V9 | [PG-RESUME-01](#pg-resume-01) |
| `schemas/project-context-leaf1-v1/project-context.schema.json:1` | Preserve legacy none/permission resolution; add explicit managed-mode admission and registration correspondence | N; legacy entry/carriers retained; managed successor interface P-013/044 | Q4; Q4-V20 | [PG-MODE-01](#pg-mode-01) |
| `schemas/project-context-leaf1-v1/fragment-members.schema.json:1` | Preserve one actual construction path and all independent pre-start gates | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V6 | [PG-ENTRY-01](#pg-entry-01) |
| `schemas/project-context-leaf1-v1/fragment-members.schema.json:1` | Add immutable generation/control/authority/policy/native-locator relation distinct from counters | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V9 | [PG-BINDING-01](#pg-binding-01) |
| `schemas/project-context-leaf1-v1/command-environment.schema.json:1` | Preserve one actual construction path and all independent pre-start gates | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V6 | [PG-ENTRY-01](#pg-entry-01) |
| `schemas/project-context-leaf1-v1/command-environment.schema.json:1` | Preserve protected external exact sparse view; require complete exact-tuple loader exclusions | N architecture; project carriers/qualification P-092–094 | Q4; Q4-V10 | [PG-STRICT-01](#pg-strict-01) |
| `schemas/home-leases-v1/holder.schema.json:1` | Preserve prepared-null holder; add durable one-start intent and separated content identities | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V14, Q4-V17 | [PG-HOLDER-01](#pg-holder-01) |
| `schemas/home-leases-v1/holder.schema.json:1` | Preserve blocking uncertainty and exact authoritative incarnation/descendant observation | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V15, Q4-V16 | [PG-OBSERVER-01](#pg-observer-01) |
| `schemas/home-leases-v1/record.schema.json:7` | Preserve HL07 original-revision committed bind replay with applicable production access gates | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V12 | [PG-REPLAY-01](#pg-replay-01) |
| `schemas/home-leases-v1/record.schema.json:7` | Preserve guarded mutation locking; add atomic holder/resume/root revalidation for every writer | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V13 | [PG-ROOTS-01](#pg-roots-01) |
| `schemas/home-leases-v1/record.schema.json:7` | Preserve blocking uncertainty and exact authoritative incarnation/descendant observation | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V14, Q4-V15, Q4-V16, Q4-V17 | [PG-OBSERVER-01](#pg-observer-01) |
| `schemas/home-leases-v1/event.schema.json:1` | Amend successor default to targeted fenced break with atomic durable audit and CAS | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V18 | [PG-BREAK-01](#pg-break-01) |
| `schemas/home-leases-v1/result.schema.json:1` | Add qualified live A/B realization or protected fixed-path pending/refusal | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V2 | [PG-ACTIVATE-01](#pg-activate-01) |
| `schemas/home-leases-v1/result.schema.json:1` | Preserve HL06/HL07 terminal precedence and no replay revival or fresh-start authority | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V12 | [PG-REPLAY-02](#pg-replay-02) |
| `schemas/home-leases-v1/result.schema.json:1` | Amend successor default to targeted fenced break with atomic durable audit and CAS | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V18 | [PG-BREAK-01](#pg-break-01) |
| `schemas/provisioning-origin-v1/provisioning-origin-v1.schema.json:1` | Amend successor project-home authority to stable profile × runtime; preserve origin and owned logout | N; old origin/source bindings retained; authority/reference mapping P-041/051/082 | Q4; Q4-V7 | [PG-AUTH-01](#pg-auth-01) |
| `schemas/provisioning-origin-v1/provisioning-origin-v1.schema.json:1` | Preserve distinct existing source contracts outside this capability; refuse successor selection until source-specific adoption/qualification, without fallback, backend substitution or credential copy | N protection invariant; successor source eligibility and explicit migration remain P-082; authority/reference realization P-041/051/082 | Q4; Q4-V11 | [PG-AUTHFLOW-01](#pg-authflow-01) |
| `schemas/profile-skill-plan-v1/context-lock-v5.schema.json:6,80` | Preserve manifest selected-directory grammar; add normalized exact subject root identity | N; manifests/locks/headers retained; exchange/projection allocation P | Q1; Q1-V3 | [PG-PACKAGE-02](#pg-package-02) |
| `schemas/profile-skill-plan-v1/context-lock-v5.schema.json:6,80` | Preserve private operational locks; add verified export projection rather than relabelling | N; manifests/locks/headers retained; exchange/projection allocation P | Q2; Q2-V8 | [PG-LOCK-01](#pg-lock-01) |
| `schemas/profile-skill-plan-v1/profile-skill-plan-v1.schema.json:1` | Add surviving-edge provenance/support closure and explicit effective-identity recomposition | N; new edge capability P-024/025; legacy collections retained | Q2; Q2-V8 | [PG-FILTER-03](#pg-filter-03) |
| `schemas/profile-skill-plan-v1/profile-skill-plan-v1.schema.json:1` | Add delivered-context audit boundary without claiming deferred skill/MCP closure | N; manifests/locks/headers retained; exchange/projection allocation P | Q2; Q2-V9 | [PG-DELIVERY-02](#pg-delivery-02) |
| `schemas/profile-command-roots-v1/root-receipt.schema.json:1` | Preserve one actual construction path and all independent pre-start gates | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V6 | [PG-ENTRY-01](#pg-entry-01) |
| `schemas/profile-command-roots-v1/root-receipt.schema.json:1` | Add immutable generation/control/authority/policy/native-locator relation distinct from counters | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V9 | [PG-BINDING-01](#pg-binding-01) |
| `schemas/profile-command-roots-v1/inventory.schema.json:1` | Preserve structural pre-start refusal; add generation/control/binding inventory correspondence | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V6 | [PG-INVENTORY-01](#pg-inventory-01) |
| `schemas/profile-command-roots-v1/session-pin.schema.json:1` | Add immutable generation/control/authority/policy/native-locator relation distinct from counters | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V9 | [PG-BINDING-01](#pg-binding-01) |
| `schemas/profile-command-roots-v1/session-pin.schema.json:1` | Preserve guarded mutation locking; add atomic holder/resume/root revalidation for every writer | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V13 | [PG-ROOTS-01](#pg-roots-01) |
| `schemas/profile-command-roots-v1/generation-marker.schema.json:1` | Preserve verified atomic export; add generation publication separate from stable authority | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V12 | [PG-PUBLISH-01](#pg-publish-01) |
| `schemas/profile-command-roots-v1/snapshot-retention.schema.json:1` | Preserve guarded mutation locking; add atomic holder/resume/root revalidation for every writer | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V13 | [PG-ROOTS-01](#pg-roots-01) |
| `schemas/profile-command-roots-v1/launcher-state.schema.json:1` | Preserve one actual construction path and all independent pre-start gates | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V6 | [PG-ENTRY-01](#pg-entry-01) |
| `schemas/profile-command-roots-v1/launcher-state.schema.json:1` | Preserve prepared-null holder; add durable one-start intent and separated content identities | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V12 | [PG-HOLDER-01](#pg-holder-01) |
| `schemas/v1/launch-env-fragment-v4.schema.json:1` | Preserve private operational locks; add verified export projection rather than relabelling | N; manifests/locks/headers retained; exchange/projection allocation P | Q1; Q1-V7 | [PG-LOCK-01](#pg-lock-01) |
| `schemas/v1/launch-env-fragment-v4.schema.json:1` | Preserve one actual construction path and all independent pre-start gates | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V6 | [PG-ENTRY-01](#pg-entry-01) |
| `schemas/v1/launch-env-fragment-v4.schema.json:1` | Add immutable generation/control/authority/policy/native-locator relation distinct from counters | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V9 | [PG-BINDING-01](#pg-binding-01) |
| `schemas/rc7-carriers-v1/launch-env-fragment-v5.schema.json:1` | Preserve frozen carriers and checkout-scoped homes; add explicit successor-only authority migration | N; legacy entry/carriers retained; managed successor interface P-013/044 | Q1; Q1-V7 | [PG-COMPAT-02](#pg-compat-02) |
| `schemas/rc7-carriers-v1/launch-env-fragment-v5.schema.json:1` | Preserve one actual construction path and all independent pre-start gates | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V6 | [PG-ENTRY-01](#pg-entry-01) |
| `schemas/rc7-carriers-v1/launch-env-fragment-v5.schema.json:1` | Add immutable generation/control/authority/policy/native-locator relation distinct from counters | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V9 | [PG-BINDING-01](#pg-binding-01) |
| `conformance/environment-store-verification-v2/README.md:40`; existing manifest | Preserve home-only repair at every level, store restoration only at L3/L4 and structural refusal | N; merged startup meanings retained; successor check/carrier mapping P-053/054 | Q4; Q4-V3, Q4-V12 | [PG-REPAIR-01](#pg-repair-01) |
| `conformance/environment-store-verification-v2/README.md:40`; existing manifest | Preserve merged L1–L4 floor, aggregation and centre-versus-confirmation fallback distinction | N; merged startup meanings retained; successor check/carrier mapping P-053/054 | Q4; Q4-V19 | [PG-LEVEL-01](#pg-level-01) |
| `protocol/home-leases.md:314` §6 | Preserve the exact consumer qualification/adoption boundary; no native result inferred from a publication | N; publication/corpus obligation; no production carrier | Publication/meta; none — meta clause | [PG-ADOPTION-01](#pg-adoption-01) |
| `conformance/environment-store-verification-v2/README.md:40`; existing manifest | Preserve the frozen startup corpus; add separately instantiated successor witnesses rather than editing old verdicts | N; publication/corpus obligation; no production carrier | Publication/meta; none — meta clause | [PG-CONFORMANCE-01](#pg-conformance-01) |
| `protocol/project-context.md:222` §5 first paragraph | Amend successor authority scope; preserve old checkout homes until explicit migration | N; old origin/source bindings retained; authority/reference mapping P-041/051/082 | Q4; Q4-V2, Q4-V7, Q4-V9, Q4-V11 | [PG-AUTH-01](#pg-auth-01) |
| `protocol/project-context.md:260` §5.1 | Preserve checkout-scoped explicit mode/registration and fresh identities on an operator mode change | N; legacy entry/carriers retained; managed successor interface P-013/044 | Q4; Q4-V20 | [PG-MODE-02](#pg-mode-02) |
| `protocol/project-context.md:232` §5 paragraph 2 | Attach approved project control-item projection to the per-checkout binding/generation; sharing authority does not merge approvals | N; projection correspondence P-044/051; concurrency P-073 | Q4; Q4-V2, Q4-V3 | [PG-BINDING-01](#pg-binding-01) |
| `protocol/project-context.md:232` §5 paragraph 2 | Preserve strict trust only for the prepared checkout; do not admit sibling trust/history through shared authority | N invariant; shared-authority control/history confinement P-062/093 | Q4; Q4-V2, Q4-V4, Q4-V5, Q4-V10 | [PG-STRICT-01](#pg-strict-01) |
| `protocol/project-context.md:298` §6 composition and lease | Attach one leased materialized composition to each checkout binding/generation; reserve qualified native-state access | N; binding carrier P-044; cross-checkout fixed-path concurrency P-051/073 | Q4; Q4-V2, Q4-V9, Q4-V14 | [PG-BINDING-01](#pg-binding-01) |
| `protocol/project-context.md:298` §6 composition and lease | Preserve prepared/active/unknown reconciliation per checkout binding without weakening shared authority protection | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V14, Q4-V15, Q4-V16, Q4-V17 | [PG-OBSERVER-01](#pg-observer-01) |
| `protocol/project-context.md:311` §6 busy mutation | Preserve wait/refusal and transactional root recheck for binding-targeted mutations and any protected shared paths | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V3, Q4-V12, Q4-V13 | [PG-ROOTS-01](#pg-roots-01) |
| `protocol/project-context.md:311` §6 busy mutation | Keep cross-checkout B pending/refused when A protects shared fixed paths; separate binding is not concurrency proof | N protection invariant; shared-path realization P-051/073 | Q4; Q4-V2 | [PG-ACTIVATE-01](#pg-activate-01) |
| `protocol/project-context.md:311` §6 resume | Preserve original checkout composition and current authority on resume; no fresh launch fallback | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V9 | [PG-RESUME-01](#pg-resume-01) |
| `protocol/effective-posture.md:36,52` EPA02 | Preserve legacy none and independent permission/no-tools intent; require explicit mode at the new entry | N; legacy entry/carriers retained; managed successor interface P-013/044 | Q4; Q4-V20 | [PG-MODE-01](#pg-mode-01) |
| `protocol/effective-posture.md:39,99` binding/EPA05 | Preserve protected plan generation identity; keep it distinct from content/authority/counter domains | N; old origin/source bindings retained; authority/reference mapping P-041/051/082 | Q4; Q4-V9 | [PG-TERMS-01](#pg-terms-01) |
| `schemas/effective-posture-v1/record.schema.json:1` | Preserve closed legacy posture and none semantics; do not insert successor authority fields | N; legacy entry/carriers retained; managed successor interface P-013/044 | Q4; Q4-V20 | [PG-MODE-01](#pg-mode-01) |
| `protocol/local-setup-token-source.md:10,16,20,104` L1/L3 | Preserve distinct existing source contracts outside this capability; refuse successor selection until source-specific adoption/qualification, without fallback, backend substitution or credential copy | N protection invariant; successor source eligibility and explicit migration remain P-082; authority/reference realization P-041/051/082 | Q4; Q4-V7, Q4-V11 | [PG-AUTHFLOW-01](#pg-authflow-01) |
| `schemas/local-setup-token-v1/source-projection-v1.schema.json:1` | Preserve distinct existing source contracts outside this capability; refuse successor selection until source-specific adoption/qualification, without fallback, backend substitution or credential copy | N protection invariant; successor source eligibility and explicit migration remain P-082; authority/reference realization P-041/051/082 | Q4; Q4-V7, Q4-V11 | [PG-AUTHFLOW-01](#pg-authflow-01) |
| `schemas/local-setup-token-v1/local-final-exec-v1.schema.json:1` | Preserve distinct existing source contracts outside this capability; refuse successor selection until source-specific adoption/qualification, without fallback, backend substitution or credential copy | N protection invariant; successor source eligibility and explicit migration remain P-082; authority/reference realization P-041/051/082 | Q4; Q4-V7, Q4-V11 | [PG-AUTHFLOW-01](#pg-authflow-01) |
| `protocol/login-readiness.md:12,29,52` §1/§1.1 | Preserve metadata presence distinct from successful login, inference, refresh and rotation | N; old origin/source bindings retained; authority/reference mapping P-041/051/082 | Q4; Q4-V7, Q4-V11 | [PG-AUTHFLOW-02](#pg-authflow-02) |
| `schemas/login-readiness-v1/login-row-v1.schema.json:1` | Preserve metadata presence distinct from successful login, inference, refresh and rotation | N; old origin/source bindings retained; authority/reference mapping P-041/051/082 | Q4; Q4-V7, Q4-V11 | [PG-AUTHFLOW-02](#pg-authflow-02) |
| `protocol/codex-seed-c.md:10,18,45,65` §1–§3 | Preserve existing seed/marker bytes and unrelated settings; refuse unsupported successor controls without silent stripping | N; old seed/adapter carriers retained; key/runtime receipts P-043/062/063 | Q4; Q4-V3, Q4-V4, Q4-V5, Q4-V8, Q4-V10 | [PG-LOADER-01](#pg-loader-01) |
| `schemas/codex-seed-c-v1/agent-environment-marker-v7.schema.json:1` | Preserve marker 7 and recorded seed revision; marker is not approval for arbitrary control mutation | N; old seed/adapter carriers retained; key/runtime receipts P-043/062/063 | Q4; Q4-V3 | [PG-LOADER-01](#pg-loader-01) |

S is the baseline pin above. D1 = **0d3bd4e8d7c33e6ba95de30673205936bf6c4e34**, draft file blob **75fd9ccd4be8957a9d6ab813cf39833221f4fa57**. D2 = **ee33b1d601e8a16116b7e91d0aa9b821dd016e25**, whose `cips/CIP-0028-claude-read-scope.md` blob is **0f39cccfc6efea2bf50668be080886602731cfb3**; [resolvable draft clause:11](https://github.com/relux-works/curator-spec/blob/ee33b1d601e8a16116b7e91d0aa9b821dd016e25/cips/CIP-0028-claude-read-scope.md#L11). S's `protocol/profile-codex-settings.md` blob is **874d64bfc9fddbf3042b6ba73bb30d8b4cf83975**; [resolvable baseline clause:11](https://github.com/relux-works/curator-spec/blob/ab6b1b0960473b359c84d96e7c7749b9be6011e0/protocol/profile-codex-settings.md#L11). These exact paths/OIDs resolve without any owner-only packet. Neither draft is promoted to main. Successor decision/CIP numbers remain unallocated.

The older include/exclude directive has no verified immutable normative pointer in this evidence set. Therefore §2.4 adopts **new** agreed edge semantics, with the collection rules preserved; no invented historical compatibility claim. Signed configuration remains deferred: the merged startup proposal explicitly does not provide configuration signing (`protocol/environment-store-verification-v2.md:11–14 @S`). Reserve future required capabilities; do not claim signed local config or path-set evidence exists.

### A.1 Stable-clause amendment index

Every N rule has a specific disposition. Exact pair IDs mirror the corpus;
the six publication/meta clauses are listed there with an explicit reason.

| Authoritative clause | Baseline clause(s) @S unless marked draft | Specific disposition | Carrier / status | Decision; exact vector IDs |
| --- | --- | --- | --- | --- |
| [PG-SCOPE-01](#pg-scope-01) | protocol/environments.md:2777; protocol/project-context.md:10 | Preserve legacy scope; add opt-in named global delivery with separate project capabilities | N; legacy entry/carriers retained; managed successor interface P-013/044 | Q1/Q4; Q1-V6, Q4-V20 |
| [PG-SCOPE-02](#pg-scope-02) | protocol/project-context.md:232,241,244; protocol/home-leases.md:97; unmanaged-entry boundary added | Preserve trusted-code limit; add unmanaged-entry exclusion and unsupported-capability refusal | N; legacy entry/carriers retained; managed successor interface P-013/044 | Q4; Q4-V5, Q4-V10, Q4-V20 |
| [PG-COMPAT-01](#pg-compat-01) | protocol/environments.md:2777,2916; protocol/skillfile-sources.md:119; explicit migration discovery preview added | Preserve legacy delivery/defaults; add explicit migration preview and no implicit global adoption | N; legacy entry/carriers retained; managed successor interface P-013/044 | Q1/Q4; Q1-V6, Q1-V7, Q4-V20 |
| [PG-COMPAT-02](#pg-compat-02) | protocol/rc7-carriers.md:11,43; protocol/managed-home-snapshots.md:175,204; protocol/project-context.md:222,260; protocol/effective-posture.md:36,39,52 | Preserve frozen carriers and checkout-scoped homes; add explicit successor-only authority migration | N; legacy entry/carriers retained; managed successor interface P-013/044 | Q1/Q3/Q4; Q1-V3, Q1-V7, Q3-V3, Q4-V20 |
| [PG-MODE-01](#pg-mode-01) | protocol/project-context.md:47,258,329; schemas/project-context-leaf1-v1/registration.schema.json:43; protocol/effective-posture.md:36,52; schemas/effective-posture-v1/record.schema.json:1 | Preserve legacy none/permission resolution; add explicit managed-mode admission and registration correspondence | N; legacy entry/carriers retained; managed successor interface P-013/044 | Q4; Q4-V6, Q4-V20 |
| [PG-MODE-02](#pg-mode-02) | protocol/project-context.md:47,258,329; schemas/project-context-leaf1-v1/registration.schema.json:43 | Preserve registration mode carrier; require fresh identity for changed semantics and reject unrecognized additions | N; legacy entry/carriers retained; managed successor interface P-013/044 | Q4; Q4-V20 |
| [PG-TERMS-01](#pg-terms-01) | protocol/managed-home-snapshots.md:175,204; protocol/provisioning-origin.md:52; protocol/home-leases.md:54; protocol/project-context.md:222,260; protocol/effective-posture.md:39 | Define four distinct identity domains; preserve old protected-generation/counter meanings and refer authority scope to PG-AUTH-01 | N; old origin/source bindings retained; authority/reference mapping P-041/051/082 | Q4; Q4-V7, Q4-V9 |
| [PG-TERMS-02](#pg-terms-02) | protocol/environment-store-verification-v2.md:3; cips/README.md:11 | Add publication-status and capability-claim hierarchy without changing historical replay | N; publication/corpus obligation; no production carrier | Publication/meta; none — meta clause |
| [PG-PACKAGE-01](#pg-package-01) | protocol/environments.md:470,521; protocol/rc7-carriers.md:71 | Preserve manifest vocabulary and declarations; restrict the initial supported settings subset | N; manifests/locks/headers retained; exchange/projection allocation P | Q1; Q1-V2, Q1-V3, Q1-V6, Q1-V7 |
| [PG-PACKAGE-02](#pg-package-02) | protocol/environments.md:552; protocol/skillfile-sources.md:61 | Preserve manifest selected-directory grammar; add normalized exact subject root identity | N; manifests/locks/headers retained; exchange/projection allocation P | Q1; Q1-V3 |
| [PG-HASH-01](#pg-hash-01) | protocol/core.md:1521,1533,1563 | Preserve core hash-1 guard and exact hash-2 byte framing | N; baseline hash/union/render semantics retained | Q1; Q1-V4 |
| [PG-HASH-02](#pg-hash-02) | protocol/core.md:49; protocol/environment-store-verification-v2.md:91 | Preserve independent structural acquisition refusal; deny extraction authority inferred from hashing | N; baseline hash/union/render semantics retained | Q1; Q1-V5 |
| [PG-HASH-03](#pg-hash-03) | protocol/skillfile-sources.md:205; protocol/environments.md:1241 | Preserve local authority; restrict portable first-form evidence to exact Git packages | N; baseline hash/union/render semantics retained | Q1/Q3; Q1-V7, Q3-V1, Q3-V2 |
| [PG-COMPOSE-01](#pg-compose-01) | protocol/core.md:1505; protocol/environments.md:1305 | Preserve ordering/union; add full-closure gate only for filters and retain contexts-only deferral | N; baseline ordering/union kept; edge P-024/025 and contexts-only P-025 | Q1/Q2; Q1-V1, Q1-V6, Q2-V2, Q2-V5, Q2-V8, Q2-V9 |
| [PG-COMPOSE-02](#pg-compose-02) | protocol/core.md:1505; protocol/environments.md:1305 | Preserve independent-edge full/context/runtime/command activation union | N; baseline hash/union/render semantics retained | Q1/Q2; Q1-V1, Q2-V2, Q2-V5, Q2-V6 |
| [PG-FILTER-01](#pg-filter-01) | protocol/environments.md:1305; protocol/core.md:1505; schemas/profile-skill-plan-v1/profile-skill-plan-v1.schema.json:1 | Add edge-occurrence whole-skill selectors distinct from legacy acquisition grammar | N; new edge capability P-024/025; legacy collections retained | Q2; Q2-V1, Q2-V2, Q2-V5, Q2-V8 |
| [PG-FILTER-02](#pg-filter-02) | protocol/skillfile-sources.md:61,73; protocol/core.md:1505 | Add literal include/exclude, duplicate/missing-member rules and canonical selector order | N; new edge capability P-024/025; legacy collections retained | Q2; Q2-V1, Q2-V2, Q2-V3, Q2-V4, Q2-V9 |
| [PG-FILTER-03](#pg-filter-03) | protocol/environments.md:1305; protocol/core.md:1505; schemas/profile-skill-plan-v1/profile-skill-plan-v1.schema.json:1 | Add surviving-edge provenance/support closure and explicit effective-identity recomposition | N; new edge capability P-024/025; legacy collections retained | Q2; Q2-V1, Q2-V5, Q2-V7, Q2-V8 |
| [PG-FILTER-04](#pg-filter-04) | protocol/skillfile-sources.md:61,73; protocol/core.md:1505 | Preserve legacy collection rules; refuse filters on initial contexts-only delivery | N; new edge capability P-024/025; legacy collections retained | Q2; Q2-V3, Q2-V4, Q2-V5, Q2-V6, Q2-V7, Q2-V8, Q2-V9 |
| [PG-DELIVERY-01](#pg-delivery-01) | protocol/environments.md:552,606; protocol/profile-skill-plan-proposal.md:168; protocol/profile-command-roots.md:40 | Add explicit incomplete context delivery and visible required-understanding omissions | N; manifests/locks/headers retained; exchange/projection allocation P | Q1/Q2; Q1-V6, Q2-V9 |
| [PG-DELIVERY-02](#pg-delivery-02) | protocol/environments.md:552,606; protocol/profile-skill-plan-proposal.md:168; protocol/profile-command-roots.md:40 | Add delivered-context audit boundary without claiming deferred skill/MCP closure | N; manifests/locks/headers retained; exchange/projection allocation P | Q1/Q2; Q1-V6, Q2-V9 |
| [PG-RENDER-01](#pg-render-01) | protocol/environments.md:734,980,1003,1182 | Preserve stable dependency/weight/module/LF ordering and absent versus header-only output | N; baseline hash/union/render semantics retained | Q1; Q1-V1, Q1-V2 |
| [PG-RENDER-02](#pg-render-02) | protocol/environments.md:980,1044 | Preserve frozen headers; narrow equality to complete equal render/header inputs | N; manifests/locks/headers retained; exchange/projection allocation P | Q1; Q1-V1, Q1-V2 |
| [PG-LOCK-01](#pg-lock-01) | protocol/environments.md:229; schemas/profile-skill-plan-v1/context-lock-v5.schema.json:6 | Preserve private operational locks; add verified export projection rather than relabelling | N; manifests/locks/headers retained; exchange/projection allocation P | Q1/Q2; Q1-V7, Q2-V8 |
| [PG-GRANT-01](#pg-grant-01) | protocol/registry.md:94,111; schemas/v1/audit-record-v1.schema.json:1; schemas/v1/audit-record-v2.schema.json:1 | Add rejecting positive-only successor; preserve old-reader refusal and separate negative issuance | N; old signed records retained; positive/policy/coverage allocation P-031/032/036 | Q3; Q3-V1, Q3-V3, Q3-V4, Q3-V5, Q3-V7, Q3-V9, Q3-V12 |
| [PG-GRANT-02](#pg-grant-02) | protocol/registry.md:94,111; schemas/v1/audit-record-v1.schema.json:1; schemas/v1/audit-record-v2.schema.json:1 | Strengthen positive grant to complete subject AND policy/check/review matching | N; old signed records retained; positive/policy/coverage allocation P-031/032/036 | Q3; Q3-V1, Q3-V2, Q3-V3, Q3-V4, Q3-V5, Q3-V7, Q3-V8, Q3-V9, Q3-V10, Q3-V11, Q3-V12 |
| [PG-GRANT-03](#pg-grant-03) | protocol/registry.md:94,111; schemas/v1/audit-record-v1.schema.json:1; schemas/v1/audit-record-v2.schema.json:1 | Refuse ordinary positives as successor grants; keep failed audit distinct from revocation | N; old signed records retained; positive/policy/coverage allocation P-031/032/036 | Q3; Q3-V1, Q3-V2, Q3-V3, Q3-V6, Q3-V10, Q3-V12 |
| [PG-REVIEW-01](#pg-review-01) | protocol/registry.md:94,102 | Preserve static default; add explicit signed additive model-review predicate | N; old signed records retained; positive/policy/coverage allocation P-031/032/036 | Q3; Q3-V10 |
| [PG-DENY-01](#pg-deny-01) | protocol/registry.md:111,128,394,505,569 | Preserve broad same-framing hash OR source+commit negative matching independently of positives | N; old signed records retained; positive/policy/coverage allocation P-031/032/036 | Q3; Q3-V4, Q3-V5, Q3-V6, Q3-V7, Q3-V8, Q3-V9, Q3-V12 |
| [PG-DENY-02](#pg-deny-02) | protocol/registry.md:111,128,394,505,569 | Preserve known negatives despite unknown positives; extend retrieval completeness across channels | N; old signed records retained; positive/policy/coverage allocation P-031/032/036 | Q3; Q3-V4, Q3-V5, Q3-V6, Q3-V7, Q3-V8, Q3-V12 |
| [PG-NEGATIVE-01](#pg-negative-01) | protocol/registry.md:102,111; schemas/v1/audit-record-v2.schema.json:1 | Add initial positive-only rollout with schema-2/hash-2 negatives and future dual issuance | N; old signed records retained; positive/policy/coverage allocation P-031/032/036 | Q3; Q3-V4, Q3-V5, Q3-V7, Q3-V9 |
| [PG-MIGRATION-01](#pg-migration-01) | protocol/registry.md:111; schemas/v1/audit-record-v1.schema.json:1 | Preserve framing separation; add real signed hash-2 negative reissue before rollout | N; old signed records retained; positive/policy/coverage allocation P-031/032/036 | Q3; Q3-V9 |
| [PG-COVERAGE-01](#pg-coverage-01) | protocol/registry.md:171,288,338,358; protocol/environment-store-verification-v2.md:11 | Add required L3 negative coverage/freshness refusal without changing legacy advisory policy | N; old signed records retained; positive/policy/coverage allocation P-031/032/036 | Q3; Q3-V8, Q3-V9, Q3-V11 |
| [PG-AUTH-01](#pg-auth-01) | protocol/provisioning-origin.md:9,52,108; decisions/0032-managed-home-separate-login.md:28,92; protocol/project-context.md:222,260 | Amend used successor authority to at most one stable profile × runtime identity; preserve explicit adoption and owned logout | N; old origin/source bindings retained; authority/reference mapping P-041/051/082 | Q4; Q4-V2, Q4-V7, Q4-V9, Q4-V11 |
| [PG-AUTH-02](#pg-auth-02) | protocol/provisioning-origin.md:9,52,108; decisions/0032-managed-home-separate-login.md:28,92; protocol/project-context.md:222; explicit custody-namespace scope added | Add explicit separately approved custody namespaces while common sharing remains unqualified | N; old origin/source bindings retained; authority/reference mapping P-041/051/082 | Q4; Q4-V7, Q4-V11 |
| [PG-GENERATION-01](#pg-generation-01) | protocol/managed-home-snapshots.md:99,204; schemas/managed-home-snapshot-v1/managed-home-snapshot-v1.schema.json:6 | Add portable content-addressed selected generation; preserve snapshot-v1 source-home digest | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q1/Q4; Q1-V7, Q4-V1, Q4-V2, Q4-V8, Q4-V12 |
| [PG-CONTROL-01](#pg-control-01) | protocol/environments.md:1637; protocol/project-context.md:190; schemas/project-context-leaf1-v1/control-receipt.schema.json:7; protocol/codex-seed-c.md:10,18,45,65 | Add separate approved loader-control identity without credential/history hashes | N; old seed/adapter carriers retained; key/runtime receipts P-043/062/063 | Q4; Q4-V3, Q4-V9, Q4-V19 |
| [PG-BINDING-01](#pg-binding-01) | protocol/project-context.md:220,296,232,298,311; protocol/home-leases.md:54; schemas/project-context-leaf1-v1/root-binding.schema.json:1 | Amend successor project projection/composition/lease/busy scope to checkout binding; preserve original generation and shared-path protection | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q2/Q4; Q2-V8, Q4-V1, Q4-V2, Q4-V3, Q4-V9, Q4-V13, Q4-V14, Q4-V19 |
| [PG-PUBLISH-01](#pg-publish-01) | protocol/managed-home-snapshots.md:9,37,226; protocol/home-leases.md:71; protocol/environments.md:2625 | Preserve verified atomic export; add generation publication separate from stable authority | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V1, Q4-V12 |
| [PG-PUBLISH-02](#pg-publish-02) | protocol/managed-home-snapshots.md:9,37,226; protocol/home-leases.md:71; protocol/environments.md:2625 | Add retained root before verification/start and non-admitting partial publication | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V12 |
| [PG-UPDATE-01](#pg-update-01) | protocol/environments.md:2916; D1 decisions/0033-launch-lock-refresh-compatible.md:53,91 (draft only) | Amend successor ordinary refresh to explicit desired-generation update; preserve faithful resume pin | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V1, Q4-V2 |
| [PG-LEVEL-01](#pg-level-01) | protocol/environment-store-verification-v2.md:11,26,37 | Preserve merged L1–L4 floor, aggregation and centre-versus-confirmation fallback distinction | N; merged startup meanings retained; successor check/carrier mapping P-053/054 | Q4; Q4-V3, Q4-V12, Q4-V19 |
| [PG-LEVEL-02](#pg-level-02) | protocol/environment-store-verification-v2.md:11,26,37 | Preserve independent hard gates under permissive store levels and closed old configuration | N; merged startup meanings retained; successor check/carrier mapping P-053/054 | Q3/Q4; Q3-V11, Q4-V3, Q4-V6, Q4-V12, Q4-V19 |
| [PG-REPAIR-01](#pg-repair-01) | protocol/environment-store-verification-v2.md:63,78,91,117; protocol/home-leases.md:97 | Preserve home-only repair at every level, store restoration only at L3/L4 and structural refusal | N; merged startup meanings retained; successor check/carrier mapping P-053/054 | Q4; Q4-V3, Q4-V12, Q4-V19 |
| [PG-REPAIR-02](#pg-repair-02) | protocol/environment-store-verification-v2.md:63,78,91,117; protocol/home-leases.md:97 | Preserve pins and expected bytes; add no live-memory healing or overlapping-writer exception | N; merged startup meanings retained; successor check/carrier mapping P-053/054 | Q4; Q4-V3, Q4-V12, Q4-V19 |
| [PG-INVENTORY-01](#pg-inventory-01) | protocol/managed-home-snapshots.md:226; protocol/environment-store-verification-v2.md:91; protocol/environments.md:2625 | Preserve structural pre-start refusal; add generation/control/binding inventory correspondence | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q1/Q4; Q1-V5, Q1-V7, Q4-V1, Q4-V3, Q4-V4, Q4-V6, Q4-V8, Q4-V9, Q4-V12 |
| [PG-LOADER-01](#pg-loader-01) | protocol/environments.md:1637; protocol/project-context.md:190,244; protocol/codex-seed-c.md:10,18,45; schemas/codex-seed-c-v1/agent-environment-marker-v7.schema.json:1 | Amend successor seed admission with typed approved controls and L3/L4 unknown-control refusal; preserve seed lifecycle | N; old seed/adapter carriers retained; key/runtime receipts P-043/062/063 | Q4; Q4-V3, Q4-V4, Q4-V5, Q4-V8, Q4-V10 |
| [PG-LOADER-02](#pg-loader-02) | protocol/environments.md:1637; protocol/project-context.md:190,244 | Add mixed-write preservation and limits of entry-time checks versus live reload | N; old seed/adapter carriers retained; key/runtime receipts P-043/062/063 | Q4; Q4-V3, Q4-V5, Q4-V8 |
| [PG-RUNTIME-01](#pg-runtime-01) | protocol/project-context.md:244; protocol/environments.md:2167; schemas/project-context-leaf1-v1/adapter.schema.json:7 | Add native compatible-line policy; preserve strict exact-tuple qualification | N; old seed/adapter carriers retained; key/runtime receipts P-043/062/063 | Q4; Q4-V19 |
| [PG-RUNTIME-02](#pg-runtime-02) | protocol/project-context.md:244; protocol/environments.md:2167; schemas/project-context-leaf1-v1/adapter.schema.json:7 | Add actual-binary versus original runtime-policy comparison on resume | N; old seed/adapter carriers retained; key/runtime receipts P-043/062/063 | Q4; Q4-V9, Q4-V19 |
| [PG-HOLDER-01](#pg-holder-01) | protocol/home-leases.md:54,71; schemas/home-leases-v1/holder.schema.json:1 | Preserve prepared-null holder; add durable one-start intent and separated content identities | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V12, Q4-V13, Q4-V14, Q4-V17 |
| [PG-REPLAY-01](#pg-replay-01) | protocol/home-leases.md:71,87; schemas/home-leases-v1/result.schema.json:1 | Preserve HL07 original-revision committed bind replay with applicable production access gates | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V12, Q4-V14, Q4-V17 |
| [PG-REPLAY-02](#pg-replay-02) | protocol/home-leases.md:71,87; schemas/home-leases-v1/result.schema.json:1 | Preserve HL06/HL07 terminal precedence and no replay revival or fresh-start authority | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V12, Q4-V14, Q4-V18 |
| [PG-OBSERVER-01](#pg-observer-01) | protocol/home-leases.md:97,103; protocol/project-context.md:296 | Preserve blocking uncertainty and exact authoritative incarnation/descendant observation | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V14, Q4-V15, Q4-V16, Q4-V17 |
| [PG-NOSTART-01](#pg-nostart-01) | protocol/home-leases.md:97,103; protocol/project-context.md:296 | Add durably closed no-start slot and protection across exec-before-bind crashes | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V12, Q4-V14, Q4-V15 |
| [PG-ACTIVATE-01](#pg-activate-01) | protocol/home-leases.md:97,124; protocol/managed-home-snapshots.md:267,293; schemas/profile-command-roots-v1/snapshot-retention.schema.json:1 | Add qualified live A/B realization or protected fixed-path pending/refusal | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V1, Q4-V2, Q4-V8 |
| [PG-RETENTION-01](#pg-retention-01) | protocol/home-leases.md:97,124; protocol/managed-home-snapshots.md:267,293; schemas/profile-command-roots-v1/snapshot-retention.schema.json:1 | Add resume roots independent of process termination and explicit retirement | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V2, Q4-V9, Q4-V13, Q4-V14, Q4-V18 |
| [PG-ROOTS-01](#pg-roots-01) | protocol/home-leases.md:97,124,144,265; protocol/environments.md:5116 | Preserve guarded mutation locking; add atomic holder/resume/root revalidation for every writer | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V2, Q4-V3, Q4-V12, Q4-V13, Q4-V14, Q4-V17, Q4-V18 |
| [PG-ROOTS-02](#pg-roots-02) | protocol/home-leases.md:97,124,144,265; protocol/environments.md:5116 | Preserve uncertain/sibling roots; add restart reconstruction and no premature collection | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V12, Q4-V13, Q4-V14, Q4-V16, Q4-V18 |
| [PG-BREAK-01](#pg-break-01) | protocol/home-leases.md:129,137; schemas/home-leases-v1/event.schema.json:1 | Amend successor default to targeted fenced break with atomic durable audit and CAS | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V18 |
| [PG-BREAK-02](#pg-break-02) | protocol/home-leases.md:129,137; schemas/home-leases-v1/event.schema.json:1 | Preserve historical HL12 abandonment; add separately enabled and disclosed successor exception | N; old holder replay retained; successor custody/retention/recovery P-071–075 | Q4; Q4-V18 |
| [PG-ENTRY-01](#pg-entry-01) | decisions/0019-fragment-consumers-and-one-construction-site.md:68,93; protocol/environments.md:3567,4187; protocol/project-context.md:329 | Preserve one actual construction path and all independent pre-start gates | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V4, Q4-V6, Q4-V8, Q4-V10, Q4-V20 |
| [PG-ENTRY-02](#pg-entry-02) | decisions/0019-fragment-consumers-and-one-construction-site.md:68,93; protocol/environments.md:3567,4187; protocol/project-context.md:329 | Add production start/resume completion evidence distinct from dormant helper completion | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V6, Q4-V10, Q4-V20 |
| [PG-AUTHFLOW-01](#pg-authflow-01) | protocol/provisioning-origin.md:52,85,108; protocol/managed-home-snapshots.md:293; protocol/local-setup-token-source.md:10,16,20,104; schemas/local-setup-token-v1/source-projection-v1.schema.json:1 | Preserve distinct existing source contracts outside this capability; refuse successor selection until source-specific adoption/qualification, without fallback, backend substitution or credential copy | N protection invariant; successor source eligibility and explicit migration remain P-082; authority/reference realization P-041/051/082 | Q4; Q4-V7, Q4-V11 |
| [PG-AUTHFLOW-02](#pg-authflow-02) | protocol/provisioning-origin.md:52,85,108; protocol/managed-home-snapshots.md:293; protocol/login-readiness.md:12,29,52; schemas/login-readiness-v1/login-row-v1.schema.json:1 | Preserve presence-versus-validity boundary; separate login, turn, refresh, rotation and revocation observations | N; old origin/source bindings retained; authority/reference mapping P-041/051/082 | Q4; Q4-V7, Q4-V11 |
| [PG-RESUME-01](#pg-resume-01) | protocol/project-context.md:296,395; schemas/profile-command-roots-v1/session-pin.schema.json:1; protocol/home-leases.md:103 | Add original generation/control/authority/mode/runtime verification before faithful resume or stopped readmission | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V9, Q4-V10 |
| [PG-RESUME-02](#pg-resume-02) | protocol/project-context.md:296,395; schemas/profile-command-roots-v1/session-pin.schema.json:1; protocol/home-leases.md:103 | Limit resume claim to recorded bindings; preserve native child ownership without history/live-memory proof | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V9, Q4-V10 |
| [PG-PRIVACY-01](#pg-privacy-01) | protocol/provisioning-origin.md:9; protocol/home-leases.md:66; protocol/managed-home-snapshots.md:301 | Preserve private auth/origin boundary; extend shared-receipt exclusions to lifecycle identities/content | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V7, Q4-V11 |
| [PG-PRIVACY-02](#pg-privacy-02) | protocol/provisioning-origin.md:9; protocol/home-leases.md:66; protocol/managed-home-snapshots.md:301 | Add typed bounded exporter extraction and approved private-history retention without raw fallback | N; consumer/session/receipt correspondence P-081–083 | Q4; Q4-V7, Q4-V11 |
| [PG-NATIVE-01](#pg-native-01) | protocol/project-context.md:244,258 | Preserve native discovery disclosure and mandatory independent permissions/memory gates | N; generation/projection/binding carrier allocation P-042/044/051/052/055 | Q4; Q4-V4, Q4-V6, Q4-V20 |
| [PG-VERIFIED-01](#pg-verified-01) | protocol/project-context.md:190,244,329; schemas/project-context-leaf1-v1/composition.schema.json:115 | Add declaration/lock/generated-inventory variant with approved base and explicit extras | N architecture; project carriers/qualification P-092–094 | Q4; Q4-V3, Q4-V4, Q4-V9, Q4-V20 |
| [PG-VERIFIED-02](#pg-verified-02) | protocol/project-context.md:190,244,329; schemas/project-context-leaf1-v1/composition.schema.json:115 | Add launch/resume drift comparison and disclose renderer/live-mutation limits | N architecture; project carriers/qualification P-092–094 | Q4; Q4-V3, Q4-V4, Q4-V9, Q4-V20 |
| [PG-STRICT-01](#pg-strict-01) | protocol/project-context.md:220,232,244; schemas/project-context-leaf1-v1/item.schema.json:1 | Preserve exact protected sparse-view exclusion; qualify strict checkout trust/history within shared authority | N architecture; project carriers/qualification P-092–094 | Q4; Q4-V2, Q4-V4, Q4-V5, Q4-V6, Q4-V10, Q4-V20 |
| [PG-STRICT-02](#pg-strict-02) | protocol/project-context.md:220,232,244; schemas/project-context-leaf1-v1/item.schema.json:1 | Refuse package evidence as path-set approval and keep strict separate from native success | N architecture; project carriers/qualification P-092–094 | Q4; Q4-V4, Q4-V10, Q4-V20 |
| [PG-REPOSITORY-01](#pg-repository-01) | protocol/project-context.md:10,47; protocol/environments.md:1305 | Reserve architecture only; refuse discovered repository composition pending joint operator/editor agreement | N architecture; project carriers/qualification P-092–094 | Q4; Q4-V20 |
| [PG-CONFORMANCE-01](#pg-conformance-01) | protocol/rc7-carriers.md:43; protocol/home-leases.md:314; conformance/environment-store-verification-v2/README.md:40 | Add closed bounded successor-publication and independently grounded paired-witness obligations | N; publication/corpus obligation; no production carrier | Publication/meta; none — meta clause |
| [PG-CONFORMANCE-02](#pg-conformance-02) | protocol/rc7-carriers.md:43; protocol/home-leases.md:314; conformance/environment-store-verification-v2/README.md:40 | Add paired detector/exporter witness methodology without production lifecycle test requirements | N; publication/corpus obligation; no production carrier | Publication/meta; none — meta clause |
| [PG-ADOPTION-01](#pg-adoption-01) | protocol/environment-store-verification-v2.md:3; protocol/home-leases.md:314 | Preserve publication-versus-qualification distinction; add exact-head per-consumer adoption receipts | N; publication/corpus obligation; no production carrier | Publication/meta; none — meta clause |
| [PG-TRACE-01](#pg-trace-01) | New successor trace/corpus rule; conformance/environment-store-verification-v2/README.md:40 preserved | Add checked per-clause/schema amendment and vector correspondence publication | N; publication/corpus obligation; no production carrier | Publication/meta; none — meta clause |
| [PG-TRACE-02](#pg-trace-02) | New successor trace/corpus rule; conformance/environment-store-verification-v2/README.md:40 preserved | Preserve immutable baseline inputs; require finite identity closure and explicit stub/result classification | N; publication/corpus obligation; no production carrier | Publication/meta; none — meta clause |
| [PG-EVIDENCE-01](#pg-evidence-01) | New successor qualification obligations; protocol/home-leases.md:103,314 and protocol/managed-home-snapshots.md:293 preserved | Add bounded evidence classes and separate root/base/nested/live-session observations | N qualification contract; actual tuple/receipt evidence P-104 | Q4; Q4-V1, Q4-V2, Q4-V5, Q4-V6, Q4-V8, Q4-V10, Q4-V11 |
| [PG-ISOLATION-01](#pg-isolation-01) | New successor qualification obligations; protocol/home-leases.md:103,314 and protocol/managed-home-snapshots.md:293 preserved | Add fixed disposable-context isolation for qualification native entries only | N qualification contract; actual tuple/receipt evidence P-104 | Q4; Q4-V6, Q4-V7 |
| [PG-ISOLATION-02](#pg-isolation-02) | New successor qualification obligations; protocol/home-leases.md:103,314 and protocol/managed-home-snapshots.md:293 preserved | Add planted-socket rejection/valid canary and isolated OS-store qualification controls | N qualification contract; actual tuple/receipt evidence P-104 | Q4; Q4-V6, Q4-V7 |

### A.2 Unresolved placeholder register

This register is an editorial index. Each linked P clause names its responsible
editors, probe or operator decision; no row selects a realization.

| Placeholder | Section | Pending mechanism or decision |
| --- | --- | --- |
| [PG-P-013](#pg-p-013) | §1.3 | Registration/fragment successor and explicit mode/variant interface |
| [PG-P-021](#pg-p-021) | §2.1 | Finite exchange carrier and version reservation |
| [PG-P-024](#pg-p-024) | §2.4 | Selector tuple, canonical byte order and edge identity |
| [PG-P-025](#pg-p-025) | §2.5 | Omission/projection/delivery receipt correspondence |
| [PG-P-026](#pg-p-026) | §2.6 | Complete common rendering and header identity |
| [PG-P-027](#pg-p-027) | §2.7 | Private lock/export correspondence |
| [PG-P-031](#pg-p-031) | §3.1 | Rejecting positive schema, complete signed body and canonical fixtures |
| [PG-P-032](#pg-p-032) | §3.2 | Static/model policy, checks and provenance identifiers |
| [PG-P-036](#pg-p-036) | §3.6 | Negative coverage, freshness, rollback and lower-level mapping |
| [PG-P-041](#pg-p-041) | §4.1 | Shared versus separate authority and common custodian/exclusion |
| [PG-P-042](#pg-p-042) | §4.2 | Generation manifest, inventory closure and digest domain |
| [PG-P-043](#pg-p-043) | §4.3 | Canonical control key/channel projection and receipt |
| [PG-P-044](#pg-p-044) | §4.4 | Session/project/fragment/locator binding and retention correspondence |
| [PG-P-051](#pg-p-051) | §5.1 | G1 live binding results, home-variable mapping and Runtime B decision |
| [PG-P-052](#pg-p-052) | §5.2 | Activation transaction, pending/active status and readmission |
| [PG-P-053](#pg-p-053) | §5.3 | Successor level/minimum fields and check-class mapping |
| [PG-P-054](#pg-p-054) | §5.4 | State-home drift, same-pin repair and overlapping-writer boundary |
| [PG-P-055](#pg-p-055) | §5.5 | Exact adapter paths, relocation and consumer correspondence |
| [PG-P-062](#pg-p-062) | §6.2 | Complete G1 per-tuple loader/control/write-back/base-role roster |
| [PG-P-063](#pg-p-063) | §6.3 | Binary identity, compatible line, capabilities and acceptance invalidation |
| [PG-P-071](#pg-p-071) | §7.1 | Successor holder, canonical operations and durable outcome carrier |
| [PG-P-072](#pg-p-072) | §7.2 | Observer custody, namespace, transport and descendant/no-start proof |
| [PG-P-073](#pg-p-073) | §7.3 | Qualified invocation binding or serialized projection and retirement |
| [PG-P-074](#pg-p-074) | §7.4 | Publication/recovery journal, GC and guarded-writer correspondence |
| [PG-P-075](#pg-p-075) | §7.5 | Fencing proof, explicit abandonment policy and atomic audit |
| [PG-P-081](#pg-p-081) | §8.1 | Actual selected consumer/session kind and command/fragment projection |
| [PG-P-082](#pg-p-082) | §8.2 | Operator and source/consumer-owner decision on successor source eligibility/migration; authorized authority/reference/refresh/rotation qualification |
| [PG-P-083](#pg-p-083) | §8.3 | Native resume/child ownership and stopped readmission carrier |
| [PG-P-092](#pg-p-092) | §9.2 | Complete declaration-verified inventory and approved base/extras |
| [PG-P-093](#pg-p-093) | §9.3 | Protected project view, exact path-set subject and strict certification |
| [PG-P-094](#pg-p-094) | §9.4 | Repository profile selection/adoption and future composition carrier |
| [PG-P-104](#pg-p-104) | §10.4 | Authorized exact tuple, fixed isolation, evidence and supported matrix |

### A.3 Reused baseline input families

All five families below are reused unchanged at S. The finite closure is
enumerated in `conformance/profile-generations-v1/reuse.json` (96 files), with
Git blob and SHA-256 for each file. Per-pair `input_files` links the applicable
baseline inputs; `input_note` distinguishes their limited role from missing
successor/native witnesses. An empty list has an explicit deferral reason.
No symbolic commit substitution, schema pass or baseline case executes a native
probe or materializes a new successor witness.

| Family / exact inventory entry points @S | Use and corresponding pairs |
| --- | --- |
| `conformance/v1/vectors/content-hashes-v2.json:1` | Hash/NUL/framing baseline for Q1-V4/V5 and Q3 framing controls; acquisition remains an independent gate. |
| `conformance/rc7-carriers-v1/index.json:1`, `conformance/rc7-carriers-v1/canonical.json:1`, `conformance/rc7-carriers-v1/compatibility.json:1`, `conformance/rc7-carriers-v1/delivery-vectors.json:1`, `conformance/rc7-carriers-v1/decisions.json:1` | Closed-reader/canonical/delivery baseline for Q1-V6/V7 and Q4-V20. `reuse.json` includes every referenced instance/byte/old-control/new-control file; old controls resolve from repository root, other references from this corpus directory. |
| `conformance/profile-skill-directories-v1/fixtures.json:1`, `conformance/profile-skill-directories-v1/vectors.json:1`, `conformance/profile-skill-directories-v1/schema-cases.json:1`, `conformance/profile-skill-directories-v1/lock-identity.json:1` | Raw selected-directory, structural and lock baselines for Q1-V3/V5 and Q2. New edge-filter instances remain deferred. |
| `conformance/environment-store-verification-v2/manifest.json:1`, `conformance/environment-store-verification-v2/vectors/environments-store-boundary.json:1` | Existing startup level/home-repair/store-repair input family for Q4-V3/V12/V19; not native binding evidence. |
| `conformance/v1/vectors/registry-resolution.json:1`, `conformance/v1/vectors/registry-client.json:1`, `conformance/v1/vectors/registry-behavior.json:1`, `conformance/v1/vectors/registry-service.json:1` | Broad negative/retrieval/cache baseline for all Q3 rows; successor positive and policy/coverage instances remain deferred. |

Startup-family schemas/README and the other enumerated baseline control files
retain their exact S identities. No production schema or additional paired-row
identity is allocated by this draft corpus.

## Appendix B. Paired conformance inventory

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

### B.1 Conformance meta-schemas, stubs and A1

All three closed draft meta-schemas live beside the corpus under
`conformance/profile-generations-v1/`, following the startup corpus layout.
No `schemas/profile-generations-v1/` production family is allocated.
The [schema notes](../conformance/profile-generations-v1/SCHEMAS.md) distinguish
shape checks from semantic correspondence. The
[corpus notes](../conformance/profile-generations-v1/README.md) disclose external
authoring checks and the absence of a versioned dispatcher/checker integration.

`pairs.json` retains the original 48 `paired_requirement` texts and adds explicit
clause/gate/input correspondence plus paired semantic subcases. Those additions
expand the existing row identities; they are not executed witnesses or new
production carrier fields. The six meta clauses are individually classified.

A1 in `a1.json` expands Q4-V12; that parent references PG-HOLDER-01,
PG-REPLAY-01/02 and PG-P-071. Exact committed original-revision retrieval
precedes fresh CAS; terminal bind is non-admitting; applicable authority/access
gates remain. Fixed qualification isolation applies to the fixture, not every
production replay. `reuse.json` pins the finite unchanged baseline closure.
Production grant/control/holder/fragment shapes and native evidence remain P.

## Appendix C. Editorial tensions and proposed resolutions

These are explicit provenance/decision notes, not additional production choices.

| ID | Tension in input revisions | Proposed resolution / draft treatment |
| --- | --- | --- |
| E01 | Earlier nested old-schema evidence versus later rejecting successor | Use the later agreed rejecting positive-only successor (PG-GRANT-01); retain the nested shared-key case only as an unsafe-design detector. Registry owners still reserve the number/body at PG-P-031. |
| E02 | Earlier equal-selection rendering shorthand versus later header-input amendment | Require equal complete inputs, including header identity (PG-RENDER-02). Different operational-lock headers are not byte-identical; successor header allocation remains PG-P-026. |
| E03 | Earlier repository-wide removal of named identities versus prospective neutral-role exception | The public joint skeleton adopted prospective neutral authoring: [protocol/profile-generations.md:13–15 at c59ec5f](https://github.com/relux-works/curator-spec/blob/c59ec5f4a7e78e0f0ce90b92a3be831b2a9d0ace/protocol/profile-generations.md#L13). Preserve historical paths, adapter IDs and bytes; no repository-wide rewrite. |
| E04 | Stable authority/generation goal versus snapshot-v1 exported-home binding | Keep snapshot-v1 unchanged; draft four successor identities but leave Runtime B/home-variable realization at PG-P-051 until probes and operator confirmation. |
| E05 | Earlier same-pin live restoration allowance versus overlapping-writer protection | Preserve the no-overlap/protected-root floor; do not enable a live repair exception. Holder/startup owners resolve permitted same-pin restoration with binding/write-back probes at PG-P-054/074; no live-memory-healing claim. |
| E06 | Earlier schema-number examples and G2-after-probes schedule versus this N-only drafting request | No numeric production reservations or probe-dependent defaults. Draft agreed semantics now; retain every P gate, closed conformance meta-schemas only, then complete production schemas after owners and evidence. |
| E07 | Explicit managed mode and portable generation versus effective-posture/1 none and protected generation identity | Preserve `protocol/effective-posture.md:36,39,52 @S`, including independent permission/no-tools/default intent. PG-MODE-01 refuses omission only at the new managed entry; PG-TERMS-01 does not relabel the old protected plan generation identity. Any correspondence stays PG-P-013/044. |
| E08 | Existing selected credential sources versus qualified successor references | Preserve the adopted node-source contract and the distinct selected launcher OAuth-store path outside this capability. PG-AUTHFLOW-01 requires refusal of any selected source lacking successor adoption and qualification, with no implicit native-login fallback or credential copy. Whether either existing delivery mechanism can satisfy the qualified-reference contract, or instead needs an explicitly approved migration to native in-place auth, is an owner decision at PG-P-082. No blanket successor source eligibility decision is made here. |
| E09 | Checkout-scoped project rules versus shared profile × runtime native authority | Amend `protocol/project-context.md:222,232,298,311 @S` only through the successor. PG-AUTH-01 owns the authority used by launches; PG-BINDING-01 attaches approved project projection, composition, lease and busy rules to the per-checkout binding/generation. PG-COMPAT-02 preserves old homes and §5.1 mode/registration at :260. Separate bindings do not prove shared-path concurrency: PG-P-051/073 and PG-ACTIVATE-01 govern pending/refusal. Strict worktree trust and cross-checkout history confinement remain PG-P-062/093; shared authority is not strict qualification. |
| E10 | Login presence versus usable session/refresh assertion | Preserve `protocol/login-readiness.md:12,29,52 @S` and the closed login row. PG-AUTHFLOW-02 keeps presence metadata separate from actual login/turn/refresh/rotation evidence; no readiness upgrade or secret-reading status operation is introduced. |
| E11 | Existing seed-C preservation versus new sealed/approved loader controls | Preserve `protocol/codex-seed-c.md:10,18,45,65 @S` and marker 7. PG-LOADER-01 refuses unadmitted controls rather than silently stripping, refreshing or relabelling an existing seed. Explicit migration follows the seed lifecycle; successor control projection remains PG-P-043/062. |

## G2 completion boundary

N text is drafted; no native mechanism is frozen. Before adoption, shared carrier,
registry, holder, session and adapter owners finish each P entry, reserve numbers
including existing reservations, supply complete rejecting carrier schemas and
instantiated byte/signature/race witnesses, and review every trace row. Native
probes require separate operator/account/host/custody decisions. A static draft,
fixture refusal or unqualified strict tuple is not production native entry.
