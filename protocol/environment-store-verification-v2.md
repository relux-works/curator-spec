# Environment store verification, revision 2 (proposal)

This unreleased proposal defines the `agent-environments` revision-2 store
boundary. Revision 1 and its released vectors retain their original meaning.
Publication of this proposal is neither adoption nor implementation qualification.
The revision-1 environment contract remains the baseline except for the rules
and qualification scope explicitly replaced here.

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
rebuild plan. The diagnostic MUST name the offending path and violated rule.
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
An absent state/path entry without a revalidatable Git snapshot retains
`environment_repair_failed` for strict repair and performs no writes. Strict
absent-Git dry-run retains `would-rebuild-untrusted-store`, names the absence
check and performs no writes; permissive dry-run retains the absence refusal.
This exception does not weaken the low-level missing-named-target validator,
change pins or locks, authorize a fetch, or permit repair of missing payloads.

After all structural checks pass, strict local verification levels 3 and 4 MAY
restore ordinary regular-file bytes from the same revalidated recorded Git pin.
Expected evidence, selected closure and pins MUST remain unchanged. A changed
or unavailable expected identity MUST NOT be manufactured from installed bytes.
Level 1 warning-start and level 2 mismatch-refusal do not authorize rewriting
their mismatching evidence. Level 4 still requires its separate centre decision;
an absent or unreachable centre uses the specified local-level-3 warning path.

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
| Skill payload hardlink or nonportable/colliding skill path | `skill_integrity_boundary_invalid` | The exact payload/path rule |
| Non-skill payload hardlink | `environment_store_untrusted` | Single-link regular-file requirement |
| Unavailable pinned Git object or failed regular-byte restoration | Existing pin/repair refusal | The actual pin/repair rule; never structural restoration |

An enclosing-boundary refusal retains its existing class. Path/local entry
structural refusals now use `environment_store_untrusted` before any attempted
rebuild, replacing the revision-1 `environment_repair_failed` result. Dry-run
structural refusals likewise use `environment_store_untrusted`, rather than
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
