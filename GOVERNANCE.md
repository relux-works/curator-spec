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

## Release process

1. Update `CHANGELOG.md`, version metadata, schemas, and vector manifest.
2. Regenerate vectors twice and prove a clean second run.
3. Pass required checks on the protected default branch.
4. Create an annotated, cryptographically signed `v<version>` tag.
5. Publish a GitHub release containing the normative schemas and conformance
   archive with SHA-256 checksums.

Release tags are immutable. A defective release is superseded by a new version
and remains available for audit.

## Decision record

Changes that introduce a new schema version, alter signed bytes, or modify
trust semantics MUST include a short decision record under `decisions/`. The
record states context, decision, alternatives, compatibility impact, and
security impact.
