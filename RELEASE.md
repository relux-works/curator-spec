# Release checklist

This checklist is normative release procedure. `GOVERNANCE.md` defines who may
approve changes; CI enforces the mechanically verifiable items.

## Candidate

- [ ] All normative changes have compatibility and security impact notes.
- [ ] Structured wire changes use a new schema version and include a migration
  note. No deployed protocol identifier is removed or silently reinterpreted;
  legacy aliases remain covered by compatibility tests.
- [ ] `make validate` passes on Linux, macOS, and Windows.
- [ ] `make regenerate-check` proves byte-identical generated vectors.
- [ ] Go Curator, the independent Python manager, and Curator Skill Registry
  pass the same full-commit-pinned suite without skips on all three operating
  systems.
- [ ] Implementation pins refer to commits whose own required CI is green.
- [ ] `CHANGELOG.md`, `COMPATIBILITY.md`, `SECURITY.md`, and version metadata
  describe the candidate.

## Stable 1.0.0

- [ ] The stable-version candidate commit contains no placeholder review
  evidence and is frozen for independent review.
- [ ] An independent security reviewer publishes
  `reviews/1.0.0/security.json` with conclusion `pass`.
- [ ] An independent interoperability reviewer publishes
  `reviews/1.0.0/interoperability.json` with conclusion `pass`.
- [ ] The two reports identify different stable reviewer contacts, and each
  reviewer attests that they are neither a project maintainer nor an author or
  committer of the reviewed changes.
- [ ] Neither report has an open critical or high finding.
- [ ] Only `reviews/` changed after each report's `reviewed_commit`.
- [ ] The release commit and annotated `v1.0.0` tag verify against
  `maintainers.allowed_signers`.
- [ ] Release archives, SHA-256 checksums, and build-provenance attestations are
  present and immutable.

Run the local release gate before signing a tag:

```text
python tools/release_gate.py --version 1.0.0 --commit HEAD
```
