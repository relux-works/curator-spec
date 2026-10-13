# CIP-0013: Machine base context

- **Status:** Draft
- **Owner:** manager implementation maintainer; decision: operator
- **Created:** 2026-10-13
- **Related:** [Decision 0023](../decisions/0023-machine-base-context.md) (Proposed); [Decision 0012](../decisions/0012-context-packages-and-semver-locks.md); [Decision 0015](../decisions/0015-per-project-policy.md)
- **Affects:** environments §§1.3–1.4, 2, 5–6, 8.2, 9.1–9.4, 10.3, 12–13; manager §§1, 7.1, 12; configuration, lock, header and conformance successors

**Revision 2026-10-14 — Draft revision 3.** Keys framing and output eligibility
to each profile's current lock version; clarifies migration, lockable keys,
approval rollout and base weights. Records the operator's request for
an opt-in machine base context. The proposed contract below is not adopted;
no normative specification, schema, vector, implementation or activation is
changed by filing it.

## Summary

A machine may explicitly select one ordinary context package as its base
overlay, delivered to every current and future profile, including `default`.
The package uses existing acquisition, resolution, audit and snapshot machinery;
its instruction bytes never live in the manager binary. A new base authority
rule keeps profile and project instructions subordinate to its chapters,
independently of chapter placement. Lock changes require explicit profile
update and approval, so a manager upgrade cannot inject or revise the base.

## Motivation and user stories

The operator requested this design on 2026-10-13: operating rules common to
all profiles must be opt-in, package-sourced, and independent of manager
upgrades. A fleet may require the same source without copying declarations
into each profile. An individual may leave the feature absent and retain
existing behavior. A profile containing only skills must still receive the
base instructions when the operator enables it.

For example, a package named `curator-root-context` could contain process-control
and destructive-git rules. This is an illustrative package name, not a
trusted source, a reserved package, a created repository or a shipped default.

## Current state

Evidence is specification reading at curator-spec commit
`5b5efa200ba86da56098470cdbdaad449d473a14` (rc.14 working specification).
[Environments](../protocol/environments.md) §6 already admits machine-only,
per-profile overlays, jointly resolved and recorded as `overlay` members.
Sections 1.4, 9.1 and 12.1 apply source constraints, signer policy and strict
audit. Sections 5.1–5.4 define deterministic chapter placement and the closed
`curator-root-context-v2` header. Sections 2 and 5.4 suppress root-context output when the root has no
`context`, even when `requires.contexts` brings modules into the closure;
§9.4 applies that rule to the builtin `default`. Revision 2 proposes fixing
the pure-umbrella case as well as adding base-only output.

Section 6 says weights order chapters and nothing else; it does not enforce
instruction meaning. Section 9.4 defines project/hybrid/profile **skill**
scope precedence, not a project context-package format. Sections 8.2 and
9.2 bind surfaces to a lock and require per-invocation system-delta consent;
12.2 allows a system file to forbid every overlay. [Manager](../profiles/manager.md)
§1 defines whole-key system locks; §7.1 supplies hardened trust defaults.
These are specification facts; they do not establish implementation
behavior or a qualification result.

## Design

### Options considered

| Option | Mechanism and trade-off | Disposition |
|---|---|---|
| Machine-wide package overlay | Reuses package machinery and a per-profile lock; needs a base role and an explicit precedence rule. | Requested design. |
| Repeat per-profile overlay declarations | Existing machinery, but omissions and future profiles escape the machine rule. | Does not satisfy the request. |
| Instructions embedded in the manager | Simple delivery, but executable upgrades silently control prompt bytes. | Excluded by the operator. |

### Recommendation

Specify the requested machine-wide overlay with the smallest additional role
metadata and authority rule; retain the flaws and adoption questions below.

**Exact configuration.** The new member is `environments.base_context`,
OPTIONAL and absent by default. When present it is exactly one object with
REQUIRED `name` and `git`, exactly one of `range`, `tag`, or `revision`, and
OPTIONAL `directory`. `name` uses the existing portable package grammar and
must equal the acquired manifest name. `git`, selectors and `directory` use
§§1 and 1.4 unchanged. No array, `null`, `path`, `local`, `weight`, instruction
text or additional member is allowed. The machine chooses the source and the
base role; package data cannot declare or alter composition.

**Consent and trust.** Absence adds nothing. A manager MAY suggest a well-known
source at first-time setup, but cannot write this member, acquire a base for
activation, or add it to a lock without explicit operator consent. Interactive
consent confirms the exact declaration. In headless use an explicitly supplied
configuration value is consent; no new flag is allocated here. Merely running
setup, selecting hardened posture, accepting unrelated setup defaults, or
receiving a suggestion is not consent. An operator-authored system value is
explicit machine configuration, including for fleet provisioning; it does
not require confirmation from every profile user. A suggested URL provides
no trust: source allowlist, `require_source_signers`, signer verification,
strict audit and protected-store checks all apply unchanged.

**Every profile and system locks.** The effective declaration is seeded into
every profile's resolution, including `default` and future installations.
It is a §6 overlay and coexists with per-profile overlays. A system file may
lock the whole `environments.base_context` object, including its source and
selector; machine overrides are ignored with the existing manager §1 warning.
Removing a machine declaration leaves its locked base in existing profiles
until profile update with approval. An unlocked system-file base is a default
that absence in the machine file cannot opt out of; remove that system
default explicitly. No null/false opt-out form is added.
An exact `revision` can enforce a particular commit; locking a range locks
the source and range, not a particular resolved version. `overlays_allowed`
continues to cover **all** overlays, including the base. When it is false and
a base is configured, effective configuration is invalid and fails closed
under manager §1; the base must not be silently dropped. A fleet requiring a
base must keep overlays permitted. Hardened posture neither supplies nor
exempts a base; all its trust defaults and refusals remain in force. The
base is a direct package for §3 system-module admission, as other active
overlays are; its dependencies retain the existing admission rules.

**Weight and authority.** Reserve no new numeric weight outside §2's existing
range: `2147483647` under `winner=higher-weight`, and `0` under
`winner=lower-weight`. Record that endpoint as the base member's `weight`
in the lock. If another member has that same endpoint weight, the base wins the tie and is placed
at the prevailing end; the ordinary topological tie rule applies among the
remaining members. The machine-derived base weight overrides package and
requirement weights, root `weights`, and per-profile overlay weights. The
base has no configurable weight. A change of precedence policy must use an
explicit `profile update` to publish the corresponding lock weight; ordinary
resolve or a manager upgrade never rewrites it.

| `winner` | `placement` | Base weight relative to other context members | Emitted position |
|---|---|---|---|
| `higher-weight` | `winner-last` | `2147483647`; wins endpoint ties | Last |
| `higher-weight` | `winner-first` | `2147483647`; wins endpoint ties | First |
| `lower-weight` | `winner-last` | `0`; wins endpoint ties | Last |
| `lower-weight` | `winner-first` | `0`; wins endpoint ties | First |

Weights alone cannot make instructions non-overridable. The minimal additional
rule is: **the designated base package's applicable chapters are the highest
authority for instruction conflicts; profile and project text MUST NOT
replace, weaken, exempt or override them.** The conceptual composition is base
overlay, then profile closure, then project layer: later scopes may refine
only within the base rules. Per-profile overlays belong to the profile layer.
This conceptual order is not the file order, which the table fixes under
both placement values. The generated header declares the base role; consumers
must preserve that role even if project instructions are loaded later.

The rule assigns instruction authority; it is not an OS sandbox or proof
that a model obeys arbitrary text. The manager cannot mechanically determine
contradictions in opaque Markdown or attest model obedience from placement.
If a consumer cannot preserve the declared authority, it cannot claim this
revision's base composition. How a consumer demonstrates that property is
an explicit adoption question, not a qualification claim here.

**Unification and scope boundaries.** If the profile closure also requires
the base name, seed all declarations into the same §1.4 constraint set.
Resolve one member and emit its chapter once, retaining its base role and
machine-derived weight. Incompatible ranges fail `context_range_conflict`;
source disagreement retains core §7 source-identity rules. No weight or role
can silently substitute a version. Repeating the base name in the explicit
per-profile overlay list remains an invalid duplicate declaration; requiring
it from a package is the admitted unification case.

The §9.4 project > hybrid > applicable-profile **skill** precedence remains
unchanged. Project/hybrid contexts, where a consumer already supports them,
are the last conceptual instruction layer and subordinate to the base.
This proposal adds no project context declaration, project package lock,
launch field, environment variable, command execution or sandbox. Decision
0015's project-policy questions remain open.

**Identity and update discipline.** The successor lock adds one OPTIONAL
top-level `base_context` member: the designated context member's name. That
member must exist and have `overlay: true`; absence means no base role.
This is necessary to distinguish the base from an ordinary overlay with the
same weight, and makes its identity part of the lock hash. The successor
marker carries the same OPTIONAL `base_context` name, checked against the
lock; it does not confer authority independently of the lock. A successor
header identifies the role with a `base: <name>` line. Existing lock/marker
member version, source, commit, weight and overlay fields carry the remaining
identity; no duplicate package or inline instruction field is added.

Initial installation locks the effective base through normal resolution and
audit after opt-in. For existing profiles, adding, removing or replacing the
base declaration, moving its package pin, or changing its precedence-derived
weight requires `profile update` (including `profile update --all`). Editing
configuration marks affected profiles non-current until that update succeeds.
`global update|upgrade` remains fetch-only under §9.2; it is not a base update
alias. Direct global skill additions/removals must retain the already locked
base pin and its locked dependency contribution; if new constraints cannot
coexist, report the existing resolution conflict and require profile update.
Reinstallation treated as update follows the same gate. No use, sync, resolve,
repair, status read, launch, migration replay or manager binary upgrade may
refresh the base or its pinned contribution implicitly.

Before publishing an affected lock, show the base's resolved-version/pin delta
and its context text delta, including added/removed modules, byte changes,
module order, class and selector changes. Base addition/removal/replacement,
pin movement or authority/weight change requires the existing explicit
per-invocation `--confirm-system-delta` approval, even for root-only modules
or unchanged module bytes at a moved pin. No standing configuration consent
pre-approves an update. Reuse §9.2's revision-B refusal
`profile_update_confirmation_required` and its no-write semantics. This new
opt-in feature must not activate under the warning-only revision-A gate;
existing system/MCP rollout behavior remains unchanged. Under `--all`, retain
§9.2's per-profile ordering and first-refusal behavior; this is not a newly
claimed all-profile atomic transaction.

`env status` reports the configured declaration and, per profile, the base
member's pinned version, commit, snapshot content digest and materialized
surface digest/currency. Profiles can temporarily hold different pins until
explicitly updated; that divergence is visible, never silently reconciled.
Configuration/role mismatch or surface drift is non-current; failed reads
report currency unknown, never an absent base. Use the existing stale-home,
drift, store and configuration failures, with no new refusal code or status
wire field allocated. Existing sessions keep their prior context in memory.

## Security considerations

Machine-wide scope increases the impact of a malicious context package. A
fleet source lock enforces provenance selection, not benevolent instructions.
The base crosses no acquisition or audit bypass and gets no additional
credential, MCP or execution authority. Package requirements still enter the
ordinary hard constraint set and source/signature checks. No suggestion is
an allowlist entry or signer authorization. Package instructions remain data
and never select manager configuration or launch composition.

Protected store, lock and marker checks, no-follow writes, audit and
absence-versus-read-failure discipline remain unchanged. Installation and
update operate under existing transaction locks; no live source bytes replace
a pinned snapshot during use. Approval occurs before lock publication or
surface writes. A manager upgrade may report an incompatible or stale surface,
but cannot repair it by fetching revised base instructions. Prompt authority
and byte reproducibility do not attest execution containment or obedience;
truncation and a consumer's native instruction hierarchy need qualification.

## Compatibility and migration

Propose **agent-environments revision 2**, not revision 1 plus new members.
Revision 1 is a closed surface; the new base authority and output eligibility
rules cannot be claimed by a revision-1 implementation. Preserve every frozen
schema and header meaning under [COMPATIBILITY.md](../COMPATIBILITY.md).
Adoption would add `manager-config-v4` (schema 4), `system-config-v3` (schema
3), `context-lock-v3` (schema 3, retaining `hash_version: 2`),
`agent-environment-marker-v4` (schema 4), and `curator-root-context-v3`.
The new configuration/lock/marker role members are OPTIONAL and have only the
shapes specified above. Unsupported versions are rejected explicitly;
no old schema is redefined or treated as carrying a base role.

Existing installs do not acquire a base when upgraded, migrated or switched
to hardened posture. The proposed §1.3 rule selects framing and output
eligibility by each profile's current lock version, independently of the
manager version and of base absence. A profile with context-lock-v2 uses
context-lock-v2, agent-environment-marker-v3 and eligible
curator-root-context-v2 output with revision-1 eligibility on
`profile use|sync|update` until explicit framing migration. Unchanged inputs
retain their prior bytes. Fresh revision-2 installs and profiles with
context-lock-v3 use context-lock-v3, agent-environment-marker-v4 and eligible
curator-root-context-v3 output with revision-2 eligibility on those operations.
With no locked base, the successor records omit base_context and the header
omits base:. Removing the effective declaration retains the locked role
until approved update; status reports that mismatch as non-current.

Configuring a base on a context-lock-v2 profile is not framing migration and
cannot publish a base until explicit migration and the required update
approval. The migration entry point is an adoption prerequisite registered
in open question 9; ordinary profile update is not that trigger. Migration
alone preserves pins and composition, while revision-2 eligibility separately
corrects pure-umbrella output. Read/use/repair and a manager upgrade never
migrate implicitly. Repair consumes the resulting lock and cannot move the
base. A new profile's initial install includes the explicitly configured
base. Old homes remain identifiable from their old markers until explicit
migration; the existing schema-1/schema-2 marker publication upgrade under
§7.4 remains within revision-1 framing and does not migrate a lock to v3.
No core object, shared filename, `workspace-result/1` field set, launch
fragment field, adapter or permission default changes.

Adoption must satisfy [GOVERNANCE.md](../GOVERNANCE.md): successor schemas,
positive/negative vectors, compatibility/security review, release notes and
cross-implementation checks. No released corpus or release pin changes here.

## Specification changes

The following quoted diffs are proposed replacements/additions against the
identified specification. They are normative **only if adopted**; the actual
`protocol/environments.md` and manager profile are unchanged by this draft.
Unquoted rules retain their existing meaning. Section numbers remain stable.

### Environments §§1.3–1.4: base identity and resolution seed

```diff
- Resolution (section 1.4) produces the profile **lock**: a strict schema-2
- object, `context-lock-v2`, naming the root and listing every closure member
- — context packages, skills, and MCP declarations, the root and the overlays
- among them. Each member records its `kind` (exactly `context`, `mcp`, or
- `skill`), `name`, canonical source identity (`source`; absent for a `path`
- package) and, when declared, its `directory` within the snapshot; its
- resolved `version` (absent for a skill pinned exactly whose source carries
- no version tag peeling to that commit); its pin — `commit`, or
- `state_sha256` for a `path` package, never both; its effective `weight`
- (section 6); its `required_by` list — the sorted names of its direct
- requirers, empty for the root and, for an overlay, the sorted names of any
- members that also require it; and `overlay`, true
- exactly for a machine overlay. Members are sorted by (`kind`, `name`),
- bytewise. A `path` member's source path stays in machine configuration and
- the environment marker; it never enters the lock, so the lock hash is the
- same on every machine that locks the same bytes.
+ Resolution (section 1.4) produces the profile **lock**: a strict object
+ in the format selected by the per-profile rule below, naming the root and
+ listing every closure member
+ — context packages, skills, and MCP declarations, the root and the overlays
+ among them. Each member records its `kind` (exactly `context`, `mcp`, or
+ `skill`), `name`, canonical source identity (`source`; absent for a `path`
+ package) and, when declared, its `directory` within the snapshot; its
+ resolved `version` (absent for a skill pinned exactly whose source carries
+ no version tag peeling to that commit); its pin — `commit`, or
+ `state_sha256` for a `path` package, never both; its effective `weight`
+ (section 6); its `required_by` list — the sorted names of its direct
+ requirers, empty for the root and, for an overlay, the sorted names of any
+ members that also require it; and `overlay`, true
+ exactly for a machine overlay. Members are sorted by (`kind`, `name`),
+ bytewise. A `path` member's source path stays in machine configuration and
+ the environment marker; it never enters the lock, so the lock hash is the
+ same on every machine that locks the same bytes.
+ For a profile whose lock is context-lock-v3, revision 2 adds OPTIONAL
+ top-level base_context, a context member name.
+ It is present exactly when a base role is locked, MUST name a member with
+ overlay: true, and participates in the lock hash. No old lock implies a base.
```

```diff
- 1. **Seed.** The constraint set holds the root's install declaration
-    (section 9.1) and every overlay declaration (section 6), each attributed
-    to the machine; the root and each overlay are pending names.
+ 1. **Seed.** The constraint set holds the root's install declaration
+    (section 9.1), the effective machine base_context declaration when
+    present for a fresh revision-2 install or a profile whose lock is
+    context-lock-v3, and every per-profile overlay declaration (section 6), each
+    attributed to the machine; the root and each overlay are pending names.
+    A profile requirement for the base name unifies on one member under
+    this section; an unsatisfied intersection fails context_range_conflict.
+    The designated member retains its base role when required by the closure.
```

```diff
- `context-lock-v2` adds REQUIRED top-level `hash_version: 2`, which applies to
- each member's `state_sha256`. New writers MUST use the v2 lock and MUST record
- the unprefixed 64-character lowercase hexadecimal digest from core §8 in
- `state_sha256`. An absent `hash_version` in a v1 lock means version 1; a v1
- lock MUST NOT be interpreted as carrying a v2 identity.
+ `context-lock-v2` adds REQUIRED top-level `hash_version: 2`, which applies to
+ each member's `state_sha256`. Writers of a profile whose lock is
+ context-lock-v2 MUST use the v2 lock and MUST record
+ the unprefixed 64-character lowercase hexadecimal digest from core §8 in
+ `state_sha256`. An absent `hash_version` in a v1 lock means version 1; a v1
+ lock MUST NOT be interpreted as carrying a v2 identity.
+ **Per-profile framing rule.** A profile whose current lock is context-lock-v2
+ MUST use context-lock-v2, agent-environment-marker-v3 and eligible
+ curator-root-context-v2 output, with revision-1 output eligibility, for
+ profile use, profile sync and profile update, until explicit framing
+ migration. Unchanged inputs MUST retain their prior bytes. A fresh
+ revision-2 install or a profile whose lock is context-lock-v3 MUST use
+ context-lock-v3, agent-environment-marker-v4 and eligible
+ curator-root-context-v3 output, with revision-2 output eligibility,
+ for those operations, whether or not a base is configured. Both lock
+ formats retain hash_version: 2. Read/use/repair and manager upgrades
+ MUST NOT migrate implicitly; ordinary profile update is not migration.
+ Configuring a base on a v2 profile is not migration and MUST NOT publish
+ a base before explicit migration and the required update approval.
+ The explicit framing-migration entry point must be specified before
+ adoption (open question 9); migration alone preserves pins and composition.
+ Existing schema-1/schema-2 marker upgrades under section 7.4 remain within
+ revision-1 framing and MUST NOT change a lock to context-lock-v3.
```

### Environments §2: output eligibility

```diff
- - **`context`** (OPTIONAL) carries the module manifest of section 3. `context`
-   MAY be absent: a package with no modules of its own is a pure umbrella and
-   declares no root-context surface — materialization writes no root-context
-   file for a profile whose root has no `context` (this is distinct from a
-   `context` with zero applicable modules, section 5.4). When `context` is
-   present the package root MUST contain the `context/` directory the
-   modules live in.
+ - **`context`** (OPTIONAL) carries the module manifest of section 3.
+   It MAY be absent: a package with no modules of its own is a pure umbrella.
+   Framing and eligibility follow section 1.3. For a profile whose lock is
+   context-lock-v2, only a root declaring context has a root-context surface.
+   For a profile whose lock is context-lock-v3, a root-context surface exists
+   when any locked context member declares context, or the lock designates
+   base_context. Materialization
+   MUST write that surface even when the root has no context of its own: a
+   pure umbrella with requires.contexts emits the applicable closure modules.
+   This is distinct from a declared context with zero applicable modules
+   (section 5.4), which produces the header alone. With neither condition
+   there is no root-context surface and no file is written. When context is
+   present the package root MUST contain the context/ directory the modules
+   live in. No package manifest may designate the machine base or composition.
```

### Environments §5: emitted order and materialization identity

```diff
- Materialized root context is a pure function of (lock, precedence policy,
- environment identifier, form). Identical inputs MUST yield byte-identical
- output on every platform and in every mode. The rules below define the
- exact bytes; they are a determinism conformance-vector surface.
+ Materialized root context is a pure function of (lock, precedence policy,
+ environment identifier, form). Identical inputs MUST yield byte-identical
+ output on every platform and in every mode. The rules below define the
+ exact bytes; they are a determinism conformance-vector surface.
+ A context-lock-v3 records the base role and its endpoint weight under
+ section 6. Framing follows section 1.3; output eligibility follows section 2.
```

```diff
- **Emitted order.** The lock's `context` members are sorted by effective
- weight under the precedence policy of section 6: ascending weight under
- `winner=higher-weight` and descending under `winner=lower-weight` when
- `placement=winner-last`; the reverse when `placement=winner-first`, so the
- prevailing end of the order is emitted last or first as declared. Members
- of equal weight keep their relative core §7 topological order in every
- case; the root participates in that order as an ordinary node, and
- `placement` never inverts a tie. This is the **emitted order**, and it is
- the order of the header's `member:` lines and of the chapters.
+ **Emitted order.** The lock's `context` members are sorted by effective
+ weight under the precedence policy of section 6: ascending weight under
+ `winner=higher-weight` and descending under `winner=lower-weight` when
+ `placement=winner-last`; the reverse when `placement=winner-first`, so the
+ prevailing end of the order is emitted last or first as declared. The
+ designated base wins endpoint-weight ties and is emitted at the
+ prevailing end under placement, independently of topological position.
+ Other equal-weight members retain their relative core §7 topological order;
+ the root remains an ordinary node unless it is also the designated base.
+ Placement never inverts a tie among those other members. This is the
+ **emitted order**, and it is
+ the order of the header's `member:` lines and of the chapters.
```

### Environments §5.1: generation header

```diff
- Every materialized root-context file begins with the generation header, an
- HTML comment that markdown renderers do not display. Its grammar is closed;
- a writer MUST emit exactly these lines in exactly this order, each
- terminated by one LF:
+ Every materialized root-context file begins with the generation header, an
+ HTML comment that markdown renderers do not display. Framing follows
+ section 1.3. For a profile whose lock is context-lock-v3, a writer MUST emit
+ the v3 header below; for context-lock-v2 it MUST retain the frozen v2 header
+ on profile use, profile sync and profile update until explicit migration.
+ Each header grammar is closed; a writer MUST emit its lines in exactly the
+ specified order, each terminated by one LF:
```

```diff
- curator-root-context-v2
+ curator-root-context-v3
  root: <name> <version> <pin>
+ base: <name>
  member: <name> <version> <pin> weight <n>
  member: <name> <version> <pin> weight <n> overlay
  precedence: winner=<winner> placement=<placement>
  lock: sha256:<64 lowercase hex>
- generated: Curator Protocol environments revision 1 (https://github.com/relux-works/curator-spec)
+ generated: Curator Protocol environments revision 2 (https://github.com/relux-works/curator-spec)
```

The header replacement above applies only for a profile whose lock is
context-lock-v3, even with no base. The quoted §1.3 rule selects the header
on `profile use|sync|update`; a context-lock-v2 profile retains the v2 header
and revision-1 eligibility until explicit migration.
The `base:` line appears exactly once immediately after `root:` when the
lock has `base_context`, and is absent otherwise. Its name must equal that
lock member. The line declares the highest instruction authority, independent
of `placement`; profile/project text cannot override that layer. Existing
`member:` lines still appear once per context member in emitted order; the
base retains `overlay`. The existing `notice:` line and closing comment
remain byte-identical. No free-form rule text is embedded in the manager or
added to the header. The old header grammar remains frozen.

### Environments §5.4: empty and pure-umbrella roots

```diff
- A root-context materialization whose applicable module set is empty produces
- the header part alone. Empty output (zero bytes) never occurs, the file is
- always written, and a zero-module materialization is valid, not an error.
- Chapters exist only for members with applicable modules, so a lock whose
- members all lack applicable modules for an environment yields the header
- and nothing else. In the referenced form no module files are materialized
- and, for `opencode`, the managed `instructions` array is empty. This is
- distinct from a profile whose root declares no `context` (section 2), for
- which no root-context surface exists and no file is written.
+ Root-context eligibility follows sections 1.3 and 2. A profile whose lock
+ is context-lock-v2 retains revision-1 eligibility: a root without context
+ receives no file. For a profile whose lock is context-lock-v3, a root
+ without context receives a file if a locked dependency declares context
+ or a base role is active. A pure umbrella with requires.contexts in that
+ profile therefore MUST emit the applicable locked closure chapters,
+ whether or not a base is configured.
+ A root-context materialization whose applicable module set is empty produces
+ the header part alone. Empty output (zero bytes) never occurs, the file is
+ always written, and a zero-module materialization is valid, not an error.
+ Chapters exist only for members with applicable modules, so a lock whose
+ members all lack applicable modules for an environment yields the header
+ and nothing else. In the referenced form no module files are materialized
+ and, for opencode, the managed instructions array is empty. An ineligible
+ profile under section 2 has no root-context surface and receives no file.
```

### Environments §6: machine overlay and authority rule

```diff
+ OPTIONAL environments.base_context names exactly one context package by
+ { name, git, range | tag | revision, directory? }; all other members and
+ source kinds are invalid. Absence adds nothing. It joins every profile's
+ composition as an overlay, including default and future profiles. Package
+ data MUST NOT declare, request or alter this role or any composition.
+ Per-profile overlays remain admitted. A per-profile overlay declaration
+ repeating the base name is environment_composition_invalid; a package
+ requirement for it unifies under §1.4 rather than duplicating the member.
+
+ The base member's lock weight MUST be 2147483647 under
+ winner=higher-weight and 0 under winner=lower-weight, the endpoints of
+ section 2's existing domain, overriding all other assignments. The base wins equal-endpoint ties; placement emits
+ it at the prevailing end. Ordinary weight rules apply to other members.

- **Precedence policy.** Weights order chapters and nothing else in this
- revision. They never merge instruction text and they never resolve a
- version constraint: an empty range intersection fails regardless of
- weights. Machine configuration declares the precedence policy as two
- independent, closed primitives:
+ **Precedence policy.** Weights order chapters and do not merge instructions
+ or resolve version constraints: an empty intersection fails regardless of
+ weights. Revision 2 additionally designates the base package's applicable
+ chapters as the highest instruction authority: profile and project text MUST
+ NOT replace, weaken, exempt or override them. Conceptual composition is base,
+ profile closure (including per-profile overlays), project layer; physical
+ placement follows the policy. This does not attest opaque text interpretation,
+ model obedience or OS enforcement. Base dependencies do not inherit the role.
+ Machine configuration declares two independent, closed primitives:

- composition policy of section 12.1 (`overlays_allowed`) lets a machine
- forbid overlays entirely.
+ composition policy of section 12.1 (overlays_allowed) forbids every overlay,
+ including the base. A configured base with overlays_allowed=false is invalid
+ effective configuration under manager §1 and fails closed, never silently
+ omitting the base. With no base the existing prohibition remains unchanged.
```

### Environments §8.2: marker successor

```diff
- ### 8.2 Environment marker, schemas 1 through 3
+ ### 8.2 Environment marker, schemas 1 through 4
```

```diff
- Every in-place surface set and every managed home carries a per-home
- **environment marker**, `.agent-environment.json`, beside the managed
- surfaces. Its supported wire formats are the strict schema-1 object
- (`agent-environment-marker-v1.schema.json`), schema-2 object
- (`agent-environment-marker-v2.schema.json`), and schema-3 object
- (`agent-environment-marker-v3.schema.json`). Current writers MUST use schema
- 3 and include `hash_version: 2`. Schema-1 and schema-2 markers remain
- supported as framing version 1; their existing upgrade rule is the
- otherwise-required marker publication stated in section 7.4. The marker
- records:
+ Every in-place surface set and every managed home carries the existing
+ environment marker beside its surfaces. Framing follows section 1.3.
+ For a profile whose lock is context-lock-v3, marker writes use
+ agent-environment-marker-v4, schema 4, retaining schema-3 fields and
+ hash_version: 2, even without a base. A context-lock-v2 profile uses
+ schema 3 on profile use, profile sync and profile update until explicit
+ framing migration. Schema-1/schema-2 markers remain readable; their
+ existing upgrade trigger is the otherwise-required marker publication
+ under section 7.4, within revision-1 framing. Schema 4 adds
+ OPTIONAL base_context, a context member name present exactly when the lock
+ designates it as base, and MUST agree with the lock. Mismatch is non-current;
+ malformed reads follow section 8.4.1, never absence. The version value is
+ exactly 4 for schema 4; existing version/hash meanings remain unchanged.
+ Eligible context-less roots record the ordinary root-context surface with
+ actual paths and content hash. The recorded fields follow, with the version/hash bullets amended below:
```

```diff
- - `version` — exactly `1`, `2`, or `3` for the corresponding schema;
+ - `version` — exactly `1`, `2`, `3`, or `4` for the corresponding schema;
```

```diff
- - `hash_version` — REQUIRED with value `2` in schema 3; absent in schemas 1
-   and 2, which means framing version 1. It versions every snapshot-state and
-   materialized-surface content hash in the marker, not the CCJ-1 `lock_sha256`;
+ - `hash_version` — REQUIRED with value `2` in schemas 3 and 4; absent in schemas 1
+   and 2, which means framing version 1. It versions every snapshot-state and
+   materialized-surface content hash in the marker, not the CCJ-1 `lock_sha256`;
```

### Environments §9.1: installation and explicit opt-in

```diff
- Installation **resolves** the closure under section 1.4 — the root, the
- machine overlays declared for the profile name, and every requirement they
- carry transitively — **audits** every member, **writes the lock** (section
- 1.3), and installs every member's store entry (section 4). Every closure
- member passes the same gates: canonical source identity and the core §6.1
- allowlist for `git` sources, the MCP package allowlist for `mcp` members,
- snapshot validation under sections 2 and 3 (and core §3–§4 for skills), and
- the audit below. Profiles installed from any number of repositories coexist
- as one machine profile set, and two profiles whose locks share a member
- share its store entry.
+ Installation **resolves** the closure under section 1.4 — the root, the
+ effective machine base when present, the per-profile machine overlays
+ declared for the profile name, and every requirement they
+ carry transitively — **audits** every member, **writes the lock** (section
+ 1.3), and installs every member's store entry (section 4). Every closure
+ member passes the same gates: canonical source identity and the core §6.1
+ allowlist for `git` sources, the MCP package allowlist for `mcp` members,
+ snapshot validation under sections 2 and 3 (and core §3–§4 for skills), and
+ the audit below. Profiles installed from any number of repositories coexist
+ as one machine profile set, and two profiles whose locks share a member
+ share its store entry.
+ A setup suggestion MUST NOT add a base without explicit operator consent:
+ confirmation of the exact declaration interactively, or an explicitly
+ supplied configuration value headlessly. A suggested URL grants no trust.
+ The base passes the same source, signer, snapshot, strict-audit and system-
+ module surfacing gates. Reinstall-as-update follows section 9.2 approval.
```

### Environments §9.2: update and approval

```diff
- 3. after the audit gate passes and before the lock is published or any
-    surface is re-materialized, `profile update` MUST print the
-    resolved-version delta of the candidate lock against the old lock, then
-    the section 2.3 surfacing rows for the candidate lock's MCP set, and
-    MUST emit `mcp_package_allowlist_empty` when the MCP package allowlist
-    is empty; printing never fails the update, and the confirmation gate
-    below runs after all three;
+ 3. after the audit gate passes and before the lock is published or any
+    surface is re-materialized, `profile update` MUST print the
+    resolved-version delta of the candidate lock against the old lock, then
+    the base version/pin and context text delta (including root-only modules,
+    module additions/removals, bytes, class, selector and order changes), then
+    the section 2.3 surfacing rows for the candidate lock's MCP set, and
+    MUST emit `mcp_package_allowlist_empty` when the MCP package allowlist
+    is empty; printing never fails the update, and the confirmation gate
+    below runs after all four. The new text-delta print is separate from
+    the unchanged lock-delta grammar; its exact grammar is an adoption prerequisite listed
+    in this proposal's open questions, not an allocated wire format;
```

```diff
+ An active base and its pinned contribution MUST NOT move through manager
+ upgrade, use, sync, resolve, repair, status, launch or global skill edits.
+ Initial install resolves the opted-in base; subsequent base addition,
+ removal, replacement, pin or policy-derived weight changes require profile
+ update, including --all, and explicit per-invocation --confirm-system-delta.
+ Configuration edits alone do not update existing locks or surfaces.
+ Print the base version/pin and context text delta before approval and
+ publication, including module additions/removals, byte, class, selector
+ and order changes. Require approval even for root-only base modules or
+ a moved pin with unchanged context bytes. No standing consent is allowed.
+ Reuse revision-B profile_update_confirmation_required and leave the old
+ lock and all surfaces unchanged on refusal. Enable this feature only with
+ that enforcing gate; existing system/MCP rollout semantics remain intact.
+ --all keeps existing per-profile sequencing and first-refusal semantics.
+ global update|upgrade remains fetch-only; it cannot change the base lock.
```

```diff
- **System-delta confirmation.** When the delta introduces or changes a
- `class: system` module or an MCP declaration, the update needs an explicit
- per-run confirmation. The trigger is exactly:
-
- - a member new to the lock that carries a `class: system` module, or a
-   moved member whose system-module inventory differs — the sorted list of
-   (`path`, `environments` selector, bytes) over its `class: system`
-   manifest entries, compared between the old and the new snapshot;
-   admission under section 3 does not narrow the trigger; or
- - an `mcp` member new to the lock, or a moved one whose MCP declaration
-   differs — the CCJ-1 bytes ([`registry.md`](registry.md) §1) of the
-   declaration object as the lock and the materialization read it:
-   `transport`, `command`, `args`, `env_names`, the `url` of an `http`
-   declaration, and the `environments` selector. Any byte difference
-   triggers — a changed `url`, a changed selector, or a reordered array
-   (CCJ-1 preserves array order) — and no field is narrowed out; absent
-   (an `http` declaration carries no `command` or `args`) differs from
-   present.
+ **System-delta confirmation.** When the delta introduces or changes a
+ `class: system` module, an MCP declaration, or the base contribution,
+ the update needs an explicit
+ per-run confirmation. The trigger is exactly:
+
+ - a member new to the lock that carries a `class: system` module, or a
+   moved member whose system-module inventory differs — the sorted list of
+   (`path`, `environments` selector, bytes) over its `class: system`
+   manifest entries, compared between the old and the new snapshot;
+   admission under section 3 does not narrow the trigger;
+ - an `mcp` member new to the lock, or a moved one whose MCP declaration
+   differs — the CCJ-1 bytes ([`registry.md`](registry.md) §1) of the
+   declaration object as the lock and the materialization read it:
+   `transport`, `command`, `args`, `env_names`, the `url` of an `http`
+   declaration, and the `environments` selector. Any byte difference
+   triggers — a changed `url`, a changed selector, or a reordered array
+   (CCJ-1 preserves array order) — and no field is narrowed out; absent
+   (an `http` declaration carries no `command` or `args`) differs from
+   present; or
+ - a base addition, removal or replacement, a changed base pin, or a changed
+   base authority or policy-derived weight, including a base with only
+   root-class modules and pin movement with unchanged module bytes.
+   The base contribution includes its locked dependency contribution;
+   detect a dependency pin change as a moved member in the lock delta
+   under this section. Such changes also require approval.
```

```diff
- - **Revision A (warning release).** The manager warns
-   `profile_update_system_delta`, naming every member the trigger names
-   and carrying the migration hint `revision B refuses with
-   profile_update_confirmation_required unless --confirm-system-delta is
-   given`, and proceeds. Old behavior is otherwise kept.
+ - **Revision A (warning release).** The manager MUST reject
+   environments.base_context as unsupported configuration, before resolution
+   or any write; no base trigger has a warn-and-proceed path. For the existing
+   system-module and MCP triggers, it warns
+   `profile_update_system_delta`, naming every member those triggers name
+   and carrying the migration hint `revision B refuses with
+   profile_update_confirmation_required unless --confirm-system-delta is
+   given`, and proceeds. Old behavior is otherwise kept.
```

### Environments §9.4: migration, skill edits and project layer

```diff
- **Migration.** On first use of the profile surface, the existing
- machine-local global scope is renamed into a builtin profile `default` with
- a synthesized `local` root — no `context`, version `0.0.0` — whose lock
- carries only the migrated global skills as direct declarations. `default`
- carries source kind `local`: no git identity, no requirement, no commit;
- its root's store key and pin are its state hash, recomputed when its state
- changes, and its lock hash follows. A root with no `context` declares no
- root-context surface (section 2), so no root-context file is written for
- `default`; it materializes skills alone. Switching, `profile sync`, and
- `env status` treat a `local` profile exactly like an installed one. A
- machine that never installs another profile observes no behavior change:
- `default` simply is the current profile and existing global installations
- keep their behavior byte-for-byte. Migration reads each global skill's
- install record to synthesize the lock; a record it cannot read is a loss
- with reason under the section 8.4.1 inventory-candidate row — never "not
- installed" — and migration stops before any write with
- `environment_import_lossy` naming the skill. Unlike import, the migration
- path admits no consent flag: the operator makes the record readable — or
- removes the skill through the normal global-remove path — and retries;
- the skill is never dropped silently.
+ **Migration.** On first use of the profile surface, the existing
+ machine-local global scope is renamed into a builtin profile `default` with
+ a synthesized `local` root — no `context`, version `0.0.0` — whose lock
+ carries the migrated global skills as direct declarations. With explicit
+ base opt-in, initial migration resolves the base jointly; migration of an
+ existing profile never adds or refreshes a base implicitly. `default`
+ carries source kind `local`: no git identity, no requirement, no commit;
+ its root's store key and pin are its state hash, recomputed when its state
+ changes, and its lock hash follows. With no base and no context declaration
+ anywhere in its context closure,
+ default materializes skills alone under section 2. With a locked base it
+ MUST receive the section-5 root-context output, including a header alone
+ when no root modules apply. Switching, `profile sync`, and
+ `env status` treat a `local` profile exactly like an installed one. For a
+ machine with no base that never installs another profile, default
+ remains current and global skill behavior is unchanged. Explicit revision-2
+ framing migration changes lock and marker bytes as specified in sections
+ 1.3 and 8.2; it is not byte-for-byte preservation of those records. Until
+ then, a profile whose lock is context-lock-v2 retains revision-1 framing
+ and eligibility, including no root-context file for its context-less root.
+ Migration reads each global skill's
+ install record to synthesize the lock; a record it cannot read is a loss
+ with reason under the section 8.4.1 inventory-candidate row — never "not
+ installed" — and migration stops before any write with
+ `environment_import_lossy` naming the skill. Unlike import, the migration
+ path admits no consent flag: the operator makes the record readable — or
+ removes the skill through the normal global-remove path — and retries;
+ the skill is never dropped silently.
+ Direct global skill edits retain the base pin and its locked contribution;
+ incompatible constraints fail resolution and require profile update.
+ Conceptual instruction layering is base overlay, profile closure, project
+ layer; the project cannot override the base. Existing project, hybrid and
+ applicable-profile skill precedence is unchanged. No project context format,
+ lock, MCP policy or launch field is introduced.
```

### Environments §10.3: influence boundary

```diff
+ The base package is subject to the same profile-influence boundary.
+ Neither its role nor its instructions select adapters, launch variables,
+ permission bypasses, credentials or manager policy. A consumer composing
+ project instructions MUST preserve base authority regardless of load order;
+ it MUST NOT claim revision-2 base composition if it cannot do so.
```

### Environments §§12, 12.1–12.2: status, configuration and locking

```diff
+ env status reports the effective base declaration and each profile's
+ locked base version, commit, snapshot digest and surface digest/currency.
+ Effective-declaration/role mismatch or drift is non-current. Failed reads
+ have unknown currency, never an absence-shaped fallback. No new status
+ wire field or refusal code is allocated by this proposal.

+ | base_context | { name, git, range \| tag \| revision, directory? } | absent | 6 |
+ This knob is carried by manager-config-v4, not earlier schemas. It adds
+ nothing when absent, including under hardened posture. Existing hardened
+ source/signature, audit, transitive-system and MCP rules apply unchanged.

+ system-config-v3 admits environments.base_context and adds that exact
+ spelling to locked. A lock replaces the declaration whole, including
+ name, source, directory and selector, under manager §1. Locking it on
+ requires a valid object, never null or a Boolean. An exact revision pins
+ a commit; a range does not. overlays_allowed continues to cover the base;
+ false plus a configured base fails closed as invalid configuration.
```

```diff
- The manager §1 `locked` set is extended, for managers implementing this
- capability, by exactly these keys under `environments`:
- `overlays_allowed`, `precedence`, `mcp_package_allowlist`,
- `passable_env_names`, `require_current_profile`, `transitive_system_modules`,
- `isolation`, `provider_directories`, `source_signers`,
- `require_source_signers`, and `permissions` — a locked provider list is fleet
- policy for which provider directories every machine trusts. A system
+ The manager §1 `locked` set is extended, for managers implementing this
+ capability, by exactly these keys under `environments` in system-config-v2:
+ `overlays_allowed`, `precedence`, `mcp_package_allowlist`,
+ `passable_env_names`, `require_current_profile`, `transitive_system_modules`,
+ `isolation`, `provider_directories`, `source_signers`,
+ `require_source_signers`, and `permissions` — a locked provider list is fleet
+ policy for which provider directories every machine trusts. System-config-v3
+ adds exactly environments.base_context to this set; system-config-v2 retains
+ its closed list and rejects that key. A system
```

```diff
- a locked `overlays_allowed: false` empties every overlay list with the
- manager §1 warning. The manager §1 credential rule stands: no key that
+ a locked overlays_allowed: false empties every per-profile overlay list
+ with the manager §1 warning only when no base is configured. With a
+ configured base the effective configuration is invalid and fails closed
+ under manager §1; no required base is silently dropped.
+ The manager §1 credential rule stands: no key that
```

### Manager §§1, 7.1 and 12: configuration and capability references

```diff
- 1. `locked` contains only `audit_registries`,
-    `disable_builtin_registries`, `allowed_sources`, and `audit`, and under
-    schema 2 additionally `security_posture` and the environments protocol
-    section 12.2 keys, named
-    as `environments.overlays_allowed`, `environments.precedence`,
-    `environments.mcp_package_allowlist`, `environments.passable_env_names`,
-    `environments.require_current_profile`, `environments.isolation`,
-    `environments.transitive_system_modules`,
-    `environments.provider_directories`, `environments.source_signers`,
-    `environments.require_source_signers`, and `environments.permissions`.
-    No other `environments` knob is lockable or carried by the system file.
+ 1. `locked` contains only `audit_registries`,
+    `disable_builtin_registries`, `allowed_sources`, and `audit`, and under
+    schema 2 additionally `security_posture` and the environments protocol
+    section 12.2 keys, named
+    as `environments.overlays_allowed`, `environments.precedence`,
+    `environments.mcp_package_allowlist`, `environments.passable_env_names`,
+    `environments.require_current_profile`, `environments.isolation`,
+    `environments.transitive_system_modules`,
+    `environments.provider_directories`, `environments.source_signers`,
+    `environments.require_source_signers`, and `environments.permissions`.
+    Schema 3 (system-config-v3) additionally admits exactly
+    environments.base_context; schema 2 keeps the closed list above.
+    No other environments knob is lockable or carried by the system file.
```

```diff
+ manager-config-v4 and system-config-v3 carry the environments revision-2
+ base_context surface. Their older versions retain their closed fields and
+ reject the new member. The additional lock key is exactly
+ environments.base_context; whole-object replacement follows §1 rule 2.
+ A configured base with overlays_allowed=false is invalid effective
+ configuration and fails closed; no silent omission is allowed.
+ Hardened posture does not enable a base and does not exempt it from any
+ trust gate. §12 lifecycle, materialization, status and lock references for
+ revision-2 managers follow the proposed environments rules above.
```

Environments §13 would add the vector families listed below. All changed
schemas, normative prose, CLI references and release migration notes belong
to a later adoption change. This draft adds no figure; the policy table above
is the only ordering illustration, and no existing figure depicts this new
role or is changed by the draft.

## Implementation plan

1. **Spec adoption (bounded documentation change).** Review the open questions,
   adopt or revise Decision 0023, and publish revision-2 prose and the named
   successor schemas without modifying frozen versions. Update manager/CLI
   references, compatibility and changelog together.
2. **Conformance (bounded contract change).** Add the vectors below and bind
   their new corpus/version identity under the release process. Define the
   consumer authority evidence before any qualification claim.
3. **Manager implementation (separate change).** Add explicit consent and
   configuration validation, joint seeding, base role/pinning, header and
   marker emission, empty-root output, update approval and status checks.
   No executable contains base instruction text.
4. **Consumer qualification (separate change).** Verify every supported
   adapter/form/platform and actual project instruction loading; qualify
   authority preservation and truncation limits. Release only after governance
   checks. No new package is created by this proposal.

## Test plan

The following conformance vectors are required before adoption. They must
exercise the implementing manager's entry points; runtime conformance remains
prospective.

Drive actual setup, `profile install`, `profile update`, `profile sync`,
`env resolve`, and `env status` entry points in the adopting implementation.

| Vector family | Positive/negative coverage | Narrowing mutant to kill |
|---|---|---|
| Absent member | On profile use/sync/update, a context-lock-v2 profile uses context-lock-v2/agent-environment-marker-v3/curator-root-context-v2 and revision-1 eligibility until explicit migration, retaining prior bytes for unchanged inputs; fresh installs and context-lock-v3 profiles use context-lock-v3/agent-environment-marker-v4/curator-root-context-v3 and revision-2 eligibility without base_context or base:; configuration alone does not migrate; upgrade adds no base under either posture | Absent-base fresh installs fall back to lock-v2/marker-v3/header-v2 |
| Consent required | Explicit interactive declaration confirmation or headless config; suggestion-only and unrelated consent add nothing | Setup confirmation for another setting counts as base consent |
| Pure umbrella closure | Root has no context and only requires.contexts; dependency root modules produce chapters without a base in both forms, selectors excluding all modules produce header alone; legacy eligibility retained before migration | Eligibility requires root.context or base and ignores dependency context |
| Default with base only | `default` root lacks `context`; applicable base chapters emitted in monolithic/referenced forms, header alone for zero applicable modules | Output eligibility still checks only root.context |
| Both precedence primitives | All four winner/placement pairs, endpoint ties, extreme root/overlay weights; header identifies base; project load preserves authority | Base wins only under higher-weight/winner-last, or loses equal-weight tie |
| Requirement unification | Base required by profile resolves once with base role and machine weight | Unification drops the base role when a requirement also names it |
| Range conflict | Compatible intersection unifies; incompatible base/profile ranges fail context_range_conflict with old lock unchanged | Base weight silently selects its version despite incompatible range |
| System-file lock | Whole declaration replaces machine value; conflicting overlays_allowed=false fails; hardened trust gates still apply | Lock changes source but lets machine override selector, or silently drops base |
| Update approval | Revision A rejects base_context as unsupported before resolution or writes, never warns and proceeds for a base change; revision B covers root-only delta, add/remove/replace, selector/order/class changes, pin-only movement and moved locked base dependencies; flag admits, absent flag preserves old lock/surfaces | Approval checks only class: system modules |
| Status and drift | Version and digests reported; config/role/hash mismatch non-current; read failure unknown; upgrade/repair/global edits cannot move pin | Status treats unreadable base metadata as absent, or repair refreshes base |

Conformance must establish determinism, one-name-one-pin and no-write-on-
refusal, including negative cases that detect narrowing each approval or
validation rule. No implementation or conformance result is claimed by this
proposal.

## Open questions for the operator

1. **Authority at the consumer boundary.** Weight placement cannot enforce
   model obedience or reconcile contradictory arbitrary Markdown. Recommended:
   adopt the explicit base authority rule, qualify preservation through each
   consumer's native instruction hierarchy, and claim only that bounded
   property. If universal obedience is required, this design cannot provide
   it; a separate enforcement contract is needed before implementation.
2. **Project context consumer.** §9.4 freezes skill scope precedence, not a
   project context format. Recommended: preserve it and require base authority
   from existing consumers; defer new project context/package policy to
   Decision 0015. Adoption needs a named first consumer and its load contract.
3. **Fleet forbids all overlays.** Requiring a base while locking
   overlays_allowed=false contradicts the existing meaning. Recommended:
   reject that effective configuration and require the fleet to permit
   overlays; do not invent an exemption or silently omit the base.
4. **Approval rollout and migration.** Existing §9.2 has a warning-only stage.
   Recommended: offer this new opt-in feature only with the enforcing gate,
   while retaining the earlier system/MCP rollout. Adoption must document
   explicit revision-2 migration and the availability of that gate; it must
   not reinterpret a warning as approval.

5. **Fleet lock with a stale profile.** Status makes a missing base role
   non-current, but launch/use/resolve disposition for a fleet-locked base
   needs an adoption rule. Recommended: define refusal at those entry points
   before claiming fleet enforcement; name the existing diagnostic to reuse
   there. No diagnostic or launch behavior is invented in this draft.
6. **Base text-delta print grammar.** The §9.2 step-3 addition must become
   conformance-testable before adoption. Recommended: specify a closed,
   deterministic line grammar covering module additions/removals, bytes,
   class, selector and order, independently of the unchanged lock-delta
   grammar. The first consumer is profile update; no format is allocated here.
7. **Invalid configuration refusal scope.** A base configured under an
   overlays_allowed=false lock is invalid regardless of which file supplies
   it. Recommended: apply manager §1 rule 4 to the whole effective
   configuration, and document which read-only diagnostics remain available
   before adoption; do not claim a narrower per-profile exception.
8. **Base/root identity and declaration mismatch.** Root weights cannot
   override the base endpoint, and existing duplicate-weight validation
   remains. The root equalling the configured base still needs a rule:
   recommended, unify one member with both root and overlay roles after
   validating source identity, and specify how legacy root/overlay duplicate
   rejection is amended. The first consumer is profile install. Also name
   the existing diagnostic to reuse when declaration name and acquired
   manifest name differ; no new code is allocated here.

9. **Explicit framing-migration entry point.** What explicit profile update
   entry point migrates a context-lock-v2 profile to context-lock-v3,
   agent-environment-marker-v4 and curator-root-context-v3 with revision-2
   output eligibility? Recommended: one explicitly requested framing-migration
   mode of profile update; its invocation syntax must be specified before
   adoption and is not allocated here. Ordinary profile update and configuring
   a base are not migration. The mode preserves existing pins and composition;
   any base addition is a separate update subject to approval after migration.
   The first consumer is profile update; use/sync/repair cannot trigger it.
