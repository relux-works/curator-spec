# CIP-0030: Package-prefixed version tags for directory overlays

- **Status:** Review
- **Owner:** Curator Core maintainer; decision: operator and protocol maintainer
- **Created:** 2026-11-05
- **Related:** [environments §§1.1–1.4 and 6](../protocol/environments.md); [proposal contract](../protocol/package-overlay-tags-proposal.md); [CIP-0021](CIP-0021-profile-skill-directories.md)
- **Affects:** Git context-package range resolution, including machine overlays; Curator candidate selection, lock serialization and replay

## Summary

A context package selected from a repository directory needs its own version
namespace. This proposal selects `<directory>/v<version>` tags, using the exact
declared directory, and checks the selected package manifest at the peeled
commit. Repository-root context packages retain plain `v<version>` tags. A
successor context lock records the complete selected tag alongside the commit.
The maintainer selected version 6, conditional on the version-5 acquisition
change landing first; the complete successor schema remains implementation work.

This remains an unreleased proposal with the maintainer decisions recorded
below. It emits no complete carrier, changes no released contract and does not
establish a supported install or runtime route.

## Motivation and user stories

Two independently versioned context packages share one repository. Updating
one package must not select a sibling's release or require the sibling to
publish the same version. The operator wants a predictable range through the
next major version. Dated requirement, 2026-11-05: «давай сделаем болеее
прогнозируемо, по семверу на некст мейжр».

For a package currently at `0.1.17`, `>=0.1.17 <1.0.0` admits `0.2.0` and
`0.9.9`, and excludes `0.1.16` and `1.0.0`. `^0.1.17` has a different,
next-minor ceiling and must not replace the requested expression. An existing
lock remains an exact pin until an explicit update succeeds.

## Current state

The implementation evidence below is a read-only inspection of Curator commit
[`330556ab88278fe7a40f12ff7ae136db8b006798`](https://github.com/relux-works/curator/commit/330556ab88278fe7a40f12ff7ae136db8b006798).
It is source evidence, not a measurement of an installed executable:

| Location at that revision | Observed contract gap |
|---|---|
| [`internal/envprofile/overlays.go:89`](https://github.com/relux-works/curator/blob/330556ab88278fe7a40f12ff7ae136db8b006798/internal/envprofile/overlays.go#L89) | `commitFor` receives the requirement before the directory manifest is read at line 93. |
| [`internal/envprofile/gitsource.go:269`](https://github.com/relux-works/curator/blob/330556ab88278fe7a40f12ff7ae136db8b006798/internal/envprofile/gitsource.go#L269) | `Candidates` assumes one package per source; its API has no directory. |
| [`internal/pkgversion/pkgversion.go:96`](https://github.com/relux-works/curator/blob/330556ab88278fe7a40f12ff7ae136db8b006798/internal/pkgversion/pkgversion.go#L96) | `ParseTag` accepts only tags beginning with `v`. |
| [`internal/envprofile/gitsource.go:700`](https://github.com/relux-works/curator/blob/330556ab88278fe7a40f12ff7ae136db8b006798/internal/envprofile/gitsource.go#L700) | Root preselection lists repository-wide tags; exact-tag checking reads the root manifest. |
| [`internal/contextresolve/contextresolve.go:129`](https://github.com/relux-works/curator/blob/330556ab88278fe7a40f12ff7ae136db8b006798/internal/contextresolve/contextresolve.go#L129) | Candidate enumeration lacks the directory that `Manifest` already receives. |
| [`internal/contextresolve/contextresolve.go:702`](https://github.com/relux-works/curator/blob/330556ab88278fe7a40f12ff7ae136db8b006798/internal/contextresolve/contextresolve.go#L702) | Selection checks manifest version against selected version before installation. Preserve this check. |
| [`internal/contextlock/contextlock.go:49`](https://github.com/relux-works/curator/blob/330556ab88278fe7a40f12ff7ae136db8b006798/internal/contextlock/contextlock.go#L49) | Members carry directory, version and commit, but no selected tag. |

The rc.14 baseline and current amendments define strict version/range semantics
in environments §1.4, exact locks in §1.3, and portable paths and safe Git refs
in core §§2 and 6.3. The [closed lock-4 member schema](../schemas/rc7-carriers-v1/context-lock-v4.schema.json)
has no tag member. A new optional field under that old discriminator would be
an incompatible widening, even though the existing `directory` field suffices
to locate the package.

No actual profile installation, network acquisition, lock migration, signed-tag
verification or lifecycle test was performed for this proposal. The accompanying
Go checker exercises only the explicitly bounded metadata fixtures described in
the [corpus README](../conformance/package-overlay-tags-proposal/README.md).

## Design

### Options considered

1. **Repository-wide tags with manifest filtering.** Retains current acquisition,
   but conflates independent package versions. Searching lower tags after a
   selected manifest mismatch can hide a broken release. Reject.
2. **Exact package-directory tag namespace.** Selects one namespace before
   comparing versions, preserves source identity and source-signature policy,
   and makes sibling releases irrelevant. Requires a directory-aware candidate
   API and explicit lock evolution. Recommend.
3. **A separate repository for every package.** Fits current plain-tag behavior,
   but forces a repository/custody change and prevents independent packages in
   one repository. Remains an operator choice; not required by this design.

### Recommendation

Adopt the [proposal contract](../protocol/package-overlay-tags-proposal.md).
For Git context packages with nonempty `directory`, a range sees only exact
`<directory>/v<version>` tags. For the snapshot root it sees only plain
`v<version>` tags. No case folding, path cleaning, Unicode normalization,
prefix aliases or plain-tag fallback occurs. Both initial overlay-name
discovery and final closure resolution use the same namespace.

The range language remains environments §1.4. In particular, prereleases remain
opt-in under its existing same-core prerelease rule; this proposal does not ban
all prereleases or silently admit them to a stable range. The chosen highest
candidate must have a valid matching manifest. A mismatch refuses; it does not
silently fall back to a lower version.

Namespaced range resolutions require a successor lock binding the complete
tag and exact commit. Existing exact-revision and arbitrary exact-tag forms
retain their contracts; they do not become implicit range requests.

## Security considerations

A hostile repository may publish a higher sibling version, a nested prefix,
case or Unicode lookalikes, a malformed tag, or a tag whose selected manifest
claims another version. Namespace selection precedes version selection; whole
safe-ref and portable-directory validation precede Git execution. Directory
bytes may be valid for an exact revision while unable to form a safe tag
namespace, for example a directory containing a space. Reject that range use
explicitly; do not ban the directory from exact-revision selection.

Keep the canonical-source allowlist, raw transport preservation, source signer
allowlist, tag/commit verification, selected-tree checks and protected-store
boundary. Candidate discovery is not signature admission. Bind the exact full
tag to its peeled commit and recheck it at the existing acquisition/admission
boundary; a moved or uncertain ref cannot substitute new bytes into a lock.
Ordinary replay keeps the locked commit. Existing strict-tag versus advisory
warning behavior remains; a warning does not repin the member.

No credentials, private source content or native configuration enter the corpus.
Signature, acquisition and filesystem atomicity controls still require real
isolated implementation tests; metadata agreement is not their substitute.

## Compatibility and migration

Root packages keep plain tags. Directory ranges intentionally stop accepting
plain repository tags. Mixed repositories select the namespace determined by
the declaration; no transition fallback is implicit. Existing installed locks
remain readable and usable under their current exact pins. Only an explicit
update or reinstall may resolve a new range and write the complete version-6 successor after its prerequisites land.

The successor must preserve every field required by its chosen containing
baseline, including precedence, settings and contribution provenance. The
proposed `tag` field participates in canonical lock bytes and lock identity.
Old readers reject the successor. Old lock versions, manifests, frozen vectors
and release hashes remain unchanged; `--preserve-lock` cannot perform this
migration. No automatic migration on use, status, sync or launch is introduced.

This scope covers Git **context** package ranges, including roots and transitive
context requirements needed for the same directory-aware resolver contract.
Skill/MCP version discovery and path sources keep their existing semantics;
extending them is a separate decision. Context requirers still must agree on
canonical source and directory. The directory comes from that agreed tuple,
never from the package name or the first discovered manifest.

## Specification changes

Publish an unreleased amendment to environments §§1.1, 1.3, 1.4 and 6 with
namespace compatibility, lock identity and retained signature policy. The
maintainer decision of 2026-11-05 selects **context lock version 6**, conditional
on [the version-5 acquisition change](https://github.com/relux-works/curator/pull/192)
landing first. Its closed member schema adds `tag`, required for namespaced
range selections, and retains every field of that complete version-5 baseline.
Old discriminators must not admit the new field. The implementation keeps the
successor version behind one constant until that prerequisite is satisfied.
This proposal emits no complete version-6 schema; the fixture `lock` projection
is not that whole schema.

The proposal corpus remains outside frozen `conformance/v1` and candidate
release hashes. A passing bounded fixture checker establishes no implementation
coverage, release qualification or native adoption.

## Implementation plan

1. **Small: contract and carrier.** Apply the recorded scope, no-fallback
   transition and conditional version-6 decision. Complete the successor schema
   after version 5 lands. Independent review binds this proposal and the
   eventual complete amendment.
2. **Medium: directory-aware selection.** Thread the agreed directory through
   context candidate enumeration, overlay preselection, root discovery and
   exact version-tag/manifest checks. Use one namespace rule in both passes.
3. **Medium: lock and replay.** Serialize/hash/validate the complete tag and
   commit; preserve old readers, existing exact pins, signer checks, strict-tag
   posture and no-write failure. Perform this after the separately queued
   implementation changes in [PR192](https://github.com/relux-works/curator/pull/192),
   [PR197](https://github.com/relux-works/curator/pull/197) and
   [PR207](https://github.com/relux-works/curator/pull/207).
4. **Medium: docking and actual qualification.** Run the real install/update/
   replay/refusal pairs in isolated repositories and homes, then review the
   integrated exact head. Signed source delivery and actual supported adoption
   follow separately; no fixture home counts as host adoption.

## Test plan

The [metadata corpus](../conformance/package-overlay-tags-proposal/cases.json)
pairs root and directory selection, nested legitimate directories, next-major
boundaries, sibling/nested/plain/case lookalikes, malformed version tags,
prerelease exclusion, manifest mismatch, stable tie independence, moved-tag
strict refusal and advisory retained-pin behavior. It also exercises later-case
execution when the first expectation is deliberately wrong.

Implementation acceptance must additionally run the actual supported CLI for
install, explicit update, use/sync/resolve/status and lock-preserving repair,
across supported macOS, Linux and Windows targets. Witness old lock bytes,
registration, profile files, roots, skills, settings and credential-link metadata
before/after failures; no accepted lock or registration may be published on
refusal. Test annotated and lightweight tags, both object formats, source
signatures and moved-ref races. Test arbitrary exact tags/revisions and explicit
prerelease constraints against existing conformance cases. A deliberately broken
namespace filter, removed version check, removed pin equality check and early
return in the checker must each be detected by their intended control, with
nearby valid and restored controls. These runtime controls are required future
work, not results of this proposal's metadata checker.

## Recorded maintainer decisions

The maintainer decided the following on 2026-11-05:

1. **Directory-prefixed candidates have no plain-tag fallback.** Existing locks
   remain exact; new resolution uses the declared namespace.
2. **The rule covers all Git context-package directory ranges.** Initial name
   discovery and closure resolution use the same namespace. Skill, MCP and path
   contracts remain unchanged.
3. **The complete successor is context lock version 6 with closed member `tag`,
   required for namespaced range selections.** This is conditional on version 5
   landing first. Preserve its full baseline, keep the version behind one
   implementation constant and do not widen old discriminators.
4. **Current prerelease and strict-tag policy remains.** Stable next-major ranges
   exclude prereleases; explicit prerelease constraints and advisory moved-tag
   warnings retain their existing meanings without repinning.
