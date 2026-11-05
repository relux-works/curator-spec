# Package-prefixed context range selection — proposal contract

Status: unreleased proposal; conditional context-lock version 6 selected by
the maintainer on 2026-11-05; no complete carrier or runtime release emitted.
See [CIP-0030](../cips/CIP-0030-package-prefixed-overlay-ranges.md).

## 1. Directory and namespace

For a Git context-package range, the canonical source identity and agreed
directory select the namespace. An omitted directory selects the snapshot root
and plain `v<version>` tags. A declared nonempty directory must satisfy core §2
without cleaning or normalization. A range tag is exactly
`<directory>/v<version>`, and the full constructed tag must satisfy core §6.3,
including its 255-byte bound. The prefix is the declared directory, not the
manifest name or a basename. A legitimate nested directory has its complete
nested prefix; a child prefix is not a candidate for its parent directory.

Compare exact Unicode scalar bytes and case. Do not trim, URL-decode, fold,
normalize or repair directory/tag spellings. Ignore irrelevant or malformed
tag names as non-candidates, following environments §1.4. Refuse a malformed
directory with `profile_source_invalid` before resolving. A valid portable
directory that cannot form a safe namespaced ref cannot use range selection;
its existing exact-revision route remains available. Do not pass unqualified
revision expressions to Git.

## 2. Selection and admission

Filter candidates by namespace before applying the existing complete range
semantics in environments §1.4. No plain-root, sibling or alternate-prefix
fallback is permitted. For `>=0.1.17 <1.0.0`, stable `0.1.17`, `0.2.0` and
`0.9.9` satisfy; `0.1.16`, `1.0.0`, `1.0.1` and prereleases do not. Preserve
explicit prerelease constraints under the existing same-core rule.

Select the highest satisfying version under the existing deterministic closure
algorithm. Preserve source/directory agreement, constraint intersection and
already chosen lower-version stabilization. Namespace filtering must be the
same during overlay-name discovery and closure resolution; the former must not
preselect a repository-wide release. A successful fixed-point resolution binds
the chosen complete tag and peeled commit.

No candidate is `context_range_conflict`. A selected context manifest's version
must exactly equal the parsed tag version; mismatch is
`context_version_mismatch`, with no lower-version retry. Verify the selected
package name and snapshot under the existing contract. Acquisition, object and
source-signature failures retain their existing typed diagnostics and must not
be relabeled as no candidate. Neither a tag suffix nor a manifest alone proves
source authorization. Preserve lightweight/annotated peeling and full object-ID
validation under the effective object format.

## 3. Lock identity and replay

The successor member evidence is the exact tuple `(source, directory, version,
tag, commit)`, alongside the complete containing lock's existing fields. A
namespaced range selection must preserve the full `tag`, not reconstruct it
from version or name. Bind it in canonical bytes. The maintainer selected
context lock version 6 with closed member `tag`, required for namespaced range
selections, conditional on the version-5 acquisition change landing first.
Retain that complete baseline and keep the successor number behind one
implementation constant. This proposal does not emit the complete schema.
Existing lock discriminators continue to forbid the new field.

Ordinary replay reads the existing lock and must not reselect the newest
in-range tag. New tags cannot advance a pin without explicit update. If a
checked tag now peels elsewhere, existing strict-tag policy refuses; advisory
policy warns and retains the original commit. A ref race at admission cannot
publish a mismatched tuple. Existing acquisition policy determines when a ref
is observed; this proposal introduces no automatic network lookup on status or
offline replay. Missing/unreadable objects and uncertain observations retain
their existing refusal or unknown states, never a guessed successful match.

Failed resolution or admission publishes no accepted lock, registration or
profile replacement. Private operation staging/cache writes permitted by the
existing acquisition contract are not successful adoption and do not justify
changing a prior pin. Keep old locks usable without synthesizing a tag. A
lock-preserving operation cannot migrate to this new identity.

## 4. Boundaries and evidence

Exact arbitrary tags and revisions remain exact selectors. An explicitly
named namespaced version tag must use its declared directory's manifest and
version; arbitrary non-version tags retain their existing manifest-version
semantics. Paths, skill and MCP packages remain outside this amendment.

The [fixture corpus](../conformance/package-overlay-tags-proposal/README.md)
contains synthetic metadata projections. Its executable model accepts only
the two documented stable range spellings used by those fixtures. It is not a
general semver parser, Git resolver, lock schema validator, security admission
boundary or test of filesystem atomicity. The full existing range corpus and
real supported entrypoints remain mandatory implementation acceptance evidence.
