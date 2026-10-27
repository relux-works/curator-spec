# Governance and releases

The Curator Protocol is maintained in
`github.com/relux-works/curator-spec`. The repository is the canonical source
for normative prose, schemas, and conformance vectors.

## Changes

Every normative change MUST:

1. describe compatibility and security impact;
2. update all affected prose and JSON Schemas;
3. add or update positive and negative conformance vectors;
4. pass schema, determinism, link, and cross-implementation CI;
5. receive review from a maintainer other than the author when one is
   available.

Implementation behavior alone is not sufficient evidence for a protocol
change. Divergence opens a specification issue; implementations do not silently
become the standard.

## Proposals

Design proposals for the protocol and its implementations are written as
[Curator Improvement Proposals](cips/README.md), using the
[CIP template](cips/TEMPLATE.md). The operator accepted the process in
[CIP-0001](cips/CIP-0001-curator-improvement-proposals.md) on 2026-10-04.
Research evidence stays in the implementation repository's `.research/`.
A CIP proposes and argues; adoption of a protocol design produces Decision
record(s) and the affected normative prose, schemas, and conformance vectors
under this governance process. CIP acceptance alone does not amend the released
specification or replace the change and release requirements above and below.

## Release process

1. Update `CHANGELOG.md`, version metadata, schemas, and vector manifest.
2. Regenerate vectors twice and prove a clean second run.
3. Pass required checks on the protected default branch.
4. Create an annotated, cryptographically signed `v<version>` tag.
5. Publish a GitHub release containing the normative schemas and conformance
   archive with SHA-256 checksums.

### Source commits and release endorsement

This policy amendment separates source integration from release-tag custody
([Decision 0034](decisions/0034-source-commit-and-release-tag-trust.md)).
Reviewed source commits MAY land by a non-rewriting, exact-head fast-forward
once required review and checks pass. They need not be recreated by GitHub
squash merging. Source integration alone grants no release authority.

`tools/verify_release_commit.py` requires containment in fetched `origin/main`
for every accepted target in `relux-works/curator-spec`. It accepts an SSH
signature verified against either fixed repository input:
`maintainers.allowed_signers` or the commit-only `source.allowed_signers`.
The latter contains one explicitly authorized source key under neutral role
metadata. Ambient Git trust and caller-selected trust/API/ref roots cannot
substitute for these inputs. Alternatively, a locally PGP-signed target may
qualify through exact-target GitHub API verification: GitHub must be the
committer and report valid signed material. This is the existing GitHub-created
squash route, not trust in arbitrary GitHub-verified authors. Unknown refs,
keys, unsigned targets, mismatched responses and API uncertainty refuse.

Release CI separately verifies the annotated tag against only the unchanged
`maintainers.allowed_signers`, compares its exact target with the candidate,
and applies the same source provenance and containment check before the
remaining release gates. The release tag endorses that exact target; the
source-only key cannot supply that endorsement. The historical main check name
**Release target provenance** is retained, but a passing source check is not a
release approval. Changes to either trust input or this separation are
trust-policy governance changes requiring a decision record and independent
review. No existing key is removed or declared revoked by this amendment.

Release tags are immutable. A defective release is superseded by a new version
and remains available for audit.

## Independent stable review

Before a stable release, maintainers freeze a commit that already carries the
stable protocol version. One reviewer who is not a project maintainer or author
of the reviewed changes performs the security review. A different independent
reviewer performs the interoperability review. Affiliations and conflicts are
disclosed. Each reviewer explicitly attests that they are not a project
maintainer and did not author or commit the reviewed changes. Reports use
different stable public reviewer contacts, follow
`reviews/review-report-v2.schema.json`, and retain a public source URL
establishing authorship and discussion.

Critical and high findings must be resolved before release. A correction to a
normative file creates a new candidate that must be reviewed again. After a
report's `reviewed_commit`, only review evidence may change before the signed
release tag. `tools/release_gate.py` enforces the review type, result, finding
state, commit ancestry, and frozen normative diff. The operational sequence is
listed in `RELEASE.md`.

## Decision record

Changes that introduce a new schema version, alter signed bytes, or modify
trust semantics MUST include a short decision record under `decisions/`. The
record states context, decision, alternatives, compatibility impact, and
security impact.
