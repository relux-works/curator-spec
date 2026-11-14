# Environment store verification, revision 2 (proposal)

This unreleased proposal defines the `agent-environments` revision-2 store
boundary. Revision 1 and its released vectors retain their original meaning.
Publication of this proposal is neither adoption nor implementation qualification.
The revision-1 environment contract remains the baseline except for the rules
and qualification scope explicitly replaced here.

## 0. Startup verification policy (normative)

This revision defines unsigned startup verification levels **1, 2, 3 and 4**.
The global default is **3**. Configuration signing is not required or provided
by this revision; signed configuration belongs to a later revision. These
levels govern profile/store evidence and the managed-home decision below.
They never relax structural safety,
configuration/lock parsing, source admission, credential authority, executable
availability, or the managed-home gate below.

| Level | Required local decision | Centre decision |
| --- | --- | --- |
| 1 (least safe) | Start on passed, unavailable or definitely mismatching evidence; warn for either non-pass outcome | None |
| 2 | Start if every check that could complete passed; unavailable checks warn; any definite mismatch refuses | None |
| 3 (default) | Start only if every required local item completed and passed | None |
| 4 | Require the level-3 local result and confirmation of every required item by the verification centre | Denied or invalid confirmation refuses; an absent or unreachable centre falls back to level 3 and warns |

Run every applicable local check before aggregating. A completed contradiction
is a **definite mismatch**; a check that cannot complete or lacks expected
evidence is **unavailable**, never a pass. In either observation order, mismatch
wins over unavailable for refusal at levels 2–4. At level 1 both warn. A centre
confirmation MUST NOT override a failed or incomplete local check. A reachable
centre's denial, malformed answer or incomplete confirmation is a refusal, not
unreachability, and MUST NOT trigger fallback. No configured centre/provider is
unavailable. A fallback invocation MUST satisfy every level-3 requirement.
Permitted degraded startup MUST emit a warning and MUST NOT report fully
verified status. A warning does not authenticate the admitted bytes.

The global configuration selects an integer level from 1 through 4; omission
means 3. Malformed or out-of-range policy MUST refuse
`startup_verification_invalid` without rewriting configuration.
System policy MAY lock this selection. Profiles MAY only raise this
global floor: each explicit root, overlay or transitive context minimum MUST be
at least the global level, otherwise refuse `startup_verification_weakening`.
The effective level is the maximum of the global level and every selected
minimum. Bind those minima in the profile lock; changing a source minimum
requires explicit recomposition. No per-launch argv or environment override
may lower the floor or bypass a system lock. This proposal defines the policy,
not a new machine, manifest or lock wire schema; unsupported successor carriers
continue to refuse under §4.

At level 1 this explicitly **relaxes** revision-1 `environments.md` §4's
"Store integrity is verified against the pin" requirement and §10.1's
"Store-trust verification" pin-hash no-fragment refusal: a definite pin mismatch
may warn and start, provided the home gate and every independent gate pass.
At levels 1 and 2 it replaces those sections' missing-hash-is-failure rule with
unavailable evidence (warning-start only at these levels). At levels 1 and 2 it
also replaces §4(b)/§10.1's Git pin-mismatch rebuilding with preservation of
mismatching evidence: `--repair` MUST NOT rewrite the store or expected evidence.
Level 2 still refuses definite pin mismatch. Levels 3 and 4 retain same-pin
Git byte restoration under §2. Revision-1 archive replay remains unchanged;
these are explicit revision-2, level-scoped incompatibilities, additional to
the six structural expectation changes.

**Managed-home decision.** After structural admission, drift of an existing
managed home without `--repair` MUST start at level 1, emitting a warning that
names `environment_home_stale` and the `--repair` hint. It MUST remain non-current
and MUST NOT silently repair or adopt home bytes. At levels 2, 3 and 4 the same
drift MUST refuse with `environment_home_stale` as the leading code and the
`--repair` hint: at level 2 the drift is a verifiable check that failed. This
level-1 warning-start explicitly relaxes revision-1 §10.1's stale-home
no-fragment refusal. The named check is `home_currency`. The home diagnostic
also takes precedence over pin-evidence errors in a read-only invocation;
this explicitly replaces §4/§10.1's pin-before-home diagnostic ordering in that
combination. An absent home remains a missing required input and refuses
`environment_home_stale` with the hint at every level; the drift warning-start
does not provision a missing home. Structural refusals still lead.
An unreadable/malformed marker
retains `environment_marker_unreadable`, never absence or a permissive warning.
`--repair` MUST restore a drifted or absent managed home from completely verified
store inputs before launch at **every** level, including 1 and 2. If verified
inputs are unavailable or mismatching, refuse without home writes; report
`environment_home_stale` as the leading code. Only levels 3/4 may first restore
ordinary Git bytes as specified in §2 and then repair the home. A current home
requires no reapplication merely because the level permits degraded evidence.
The level-1 drift warning-start grants no home mutation, adoption of home bytes,
or restoration from unverified store bytes. With `--repair`, permissive evidence
policy never authorizes launching before the drifted home is restored from
completely verified inputs.

## 1. Structural refusal before repair

Every selected immutable store entry MUST satisfy ownership, private mutation
permissions, containment, regular-file types and link safety before repair may
write anything. Files MUST be single-link regular files; payload symlinks,
hardlinks and special files are forbidden. These checks cover context, MCP and
skill members, including legacy carriers. Managed adapter links pointing into
an independently verified store remain a distinct, permitted surface.

An observed violation, or inability to prove a required structural boundary,
MUST refuse at each startup verification level 1 through 4. Neither permissive
verification nor `--repair` or dry-run repair can convert it to a warning or a
rebuild plan. The diagnostic MUST name the offending path and violated rule. Check enclosing
boundaries first, then selected members in their recorded lock member order.
When several members fail, the first failing member determines the primary
path and diagnostic; a later skill failure MUST NOT replace an earlier
non-skill failure. Within that member use ownership → permissions → containment
→ regular types → link safety → single-link → portable-path checks, reporting
the first violated rule. The skill-integrity class applies only to a skill
member's hardlink or nonportable/colliding path, not to ownership failure.
The invocation MUST emit no launch fragment, start no child, follow no payload
link, and preserve the violating entry, profile lock, existing home and marker.
It MUST NOT stage, rebuild, replace, reapply or journal a repair first. Reporting
permitted rejection telemetry is not a repair write.

The refusal does not authorize an automatic out-of-band recovery. Recovery is a
separate explicit operation under the existing ownership and transaction rules.

## 2. Retained regular-file and home restoration

Whole-entry absence is an availability condition, not a regular-file type
violation, only when no-follow metadata reports exactly `ENOENT` for the selected
entry leaf after every existing ancestor and every other selected member passes
its structural checks. Missing intermediate ancestors, dangling links, reparse
points, unreadable or unknown metadata, and a present entry missing a named
payload MUST still refuse structurally at all levels. With `--repair`, levels 3
and 4 MAY recreate a proven absent Git entry from the same revalidated recorded
pin, using the existing credential authority and mutation lock. Recheck all
selected boundaries and the entry/parents under that lock before staging and
before publication; a late structural plant MUST be refused and preserved.
Verify the recreated entry before emitting a fragment. Levels 1 and 2 and
read-only invocations MUST NOT recreate it and retain
`environment_store_untrusted` with the named `regular_types` absence check.
An absent context path/local entry without a revalidatable Git snapshot retains
`environment_repair_failed` for both strict repair **and strict dry-run**,
names the `regular_types` absence check and offending path, and performs no
writes. It MUST NOT report a rebuild plan, success or a structural violation. Strict
absent-Git dry-run retains `would-rebuild-untrusted-store`, names the absence
check and performs no writes; permissive dry-run retains the absence refusal.
Under `context-lock-v1`, `context-lock-v2` and rc.7 lock schema 4
(`environments.md` §1.3 and `rc7-carriers.md`), state pins belong only to context
members; MCP and skill members require Git source pins (`environments.md`
§2.2 and §2). No implementation carrier nickname defines a new spec schema. Path/local MCP or skill
admission is outside this proposal.
This exception does not weaken the low-level missing-named-target validator,
change pins or locks, authorize a fetch, or permit repair of missing payloads.

After all structural checks pass, strict local verification levels 3 and 4 MAY
restore ordinary regular-file bytes from the same revalidated recorded Git pin.
Expected evidence, selected closure and pins MUST remain unchanged. A changed
or unavailable expected identity MUST NOT be manufactured from installed bytes.
Level 1 warning-start and level 2 mismatch-refusal do not authorize rewriting
their mismatching evidence. Level 4 still requires its separate centre decision;
an absent or unreachable centre uses the §0 local-level-3 warning path.

The §0 managed-home gate applies independently at all four levels.
An intact current home remains a no-op. Provisioning an absent home and repairing
a stale home remain permitted only from structurally valid, completely verified
inputs under the existing bounded mutation lock and atomic transaction. A stale
marker is replaced with the correct binding; a swapped old marker never
authenticates changed source bytes. This amendment grants no credential
migration, implicit lock migration, new pin, execution or installation authority.
Existing explicit identity-migration rules remain separately versioned.

## 3. Diagnostic compatibility

| Failure | Required primary diagnostic | Named rule |
| --- | --- | --- |
| Ownership, permissions, containment, payload symlink or special file | `environment_store_untrusted` | The corresponding existing boundary check |
| Skill payload hardlink or nonportable/colliding skill path | `skill_integrity_boundary_invalid` | `single_link` for hardlinks; the exact portable-path rule otherwise |
| Non-skill payload hardlink | `environment_store_untrusted` | `single_link` |
| Unavailable pinned Git object or failed regular-byte restoration | Existing pin/repair refusal | The actual pin/repair rule; never structural restoration |

This table registers `skill_integrity_boundary_invalid` as a runtime primary
code for the skill-only rules above, and `single_link` as the named check token
meaning exactly one filesystem link to each payload regular file. Unavailable
link metadata refuses under that check; directory link counts are not payload
regular-file link counts.

| Policy/home condition | Required code or warning |
| --- | --- |
| Definite local mismatch refused by §0 | `startup_verification_failed` for generic evidence; a pin mismatch retains `environment_store_untrusted` / `pin_hash` as the specific primary code unless the home gate leads |
| Incomplete local check refused by §0 | `startup_verification_unavailable` |
| Malformed or out-of-range policy | `startup_verification_invalid` |
| Profile minimum below global floor | `startup_verification_weakening` |
| Level-4 unreachable/absent centre | `verification_centre_unavailable` warning, then local level 3 |
| Centre denial / invalid confirmation | `verification_centre_denied` / `verification_centre_invalid` |
| Drifted existing home without `--repair`, level 1 | `environment_home_stale` warning and `--repair` hint; start, non-current, no writes; check `home_currency` |
| Drifted existing home without `--repair`, levels 2–4 / absent home at every level | Leading `environment_home_stale` refusal with `--repair`; existing-home check `home_currency` |

An enclosing-boundary refusal retains its existing class. Lock-file and
marker-file entry-class boundary failures **retain revision-1 §4(b)/§10.1**:
real operations rebuild from revalidated evidence under the existing transaction;
dry-run reports `would-rebuild-untrusted-store` with no writes. An unreadable or
malformed lock remains the revision-1 exception: `environment_store_untrusted`,
no rebuild or plan. This proposal's refuse-first structural change concerns
immutable **store entries**, not lock/marker entry-class recovery. A reader
MUST NOT infer that permissive levels bypass any of these carrier checks. Path/local entry
structural refusals now use `environment_store_untrusted` before any attempted
rebuild, replacing the revision-1 `environment_repair_failed` result. Dry-run
immutable-store-entry structural refusals likewise use `environment_store_untrusted`, rather than
`would-rebuild-untrusted-store`. An error after an unauthorized reapplication is
still non-conforming even if no fragment was emitted.

## 4. Version, reader and carrier migration

This is an incompatible capability revision: a manager claiming these rules
MUST qualify `agent-environments` revision 2 and MUST NOT claim the incompatible
revision-1 repair expectations. The released revision-1 corpus is an immutable
archive, not a file to update in place. Historical replay remains required
evidence: a recorded incompatibility is a failure of that historical claim,
never a skipped case or a passing full-conformance result.

The successor vector carrier is a nonempty JSON array of closed
`curator.environment-store-case/2` objects. Each object explicitly binds
`capability: "agent-environments"` and `capability_revision: 2`. It lives only in
`conformance/environment-store-verification-v2`; it is not selected by a release
number or by adding fields to the old object. A revision-1 object reader MUST
reject this array rather than decode empty case groups. A revision-2 reader
MUST reject the revision-1 object and unknown, missing or mixed discriminators
before interpreting cases. Neither reader may infer a revision from filenames.
`store_verification_corpus_unsupported` identifies this qualification-reader
refusal; it is not a new runtime CLI diagnostic.

Existing runtime configuration, manifest, lock, marker and launch-fragment
carriers retain their own exact structural readers and byte identities. They
encode data, not a promise that a planted boundary will be repaired. No field
is injected into an old carrier and startup performs no automatic rewrite.
Safe legacy native profiles must retain their upgrade witness with unchanged
lock/home bytes. Unsupported successor data carriers remain explicit refusals.
Data readability MUST NOT be reported as revision-1 behavioral conformance.

Adoption requires a reviewed signed specification revision, its exact corpus
pin and a version-aware implementation reader. Consumers switch the selected
qualification namespace explicitly; they do not reinterpret the old root.
Qualification against a reviewed but unlanded specification head is
non-canonical. Only the landed specification pin may support a canonical claim.

## 5. Required evidence

The successor corpus lists every predecessor row's disposition, every changed
diagnostic and each retained same-pin/home restoration control. Every new fatal
case has a valid intact neighbor and a forbidden observation that the checker
must reject. Known-bad `dry-run-mutates` and `repair-reapplies-untrusted` remain
negative controls; they are not relabelled as successful implementations.

Implementation qualification MUST exercise all four levels and real repair and
dry-run entry points, assert the intended refusal and unchanged post-failure
state, and prove zero child execution. Same-pin restoration controls MUST still
pass. Version controls MUST exercise both reader directions. Metadata/schema
validation and recorded counterexamples do not establish filesystem, syscall,
platform, race, launcher or runtime conformance.
