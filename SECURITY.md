# Security policy

## Reporting

Report suspected vulnerabilities privately to `ivan@relux.works`. Include the
affected protocol section or schema, a minimal reproducer, and the security
impact. Do not include secrets, private registry records, or production keys.

Acknowledgement is targeted within three business days. Coordinated disclosure
and release timing depend on severity and whether deployed implementations need
updates before publication.

## Security model

The protocol treats skill repositories, manifests, registry responses, cache
entries, and bundles as untrusted input. Conforming implementations MUST apply
the parsing limits and validation rules in the normative documents before
using paths, signatures, references, or configuration values.

The protocol provides integrity, provenance, revocation, rollback detection,
and deterministic installation. Capability declarations and source auditing
are review and policy surfaces; they are not runtime sandboxes. A successful
audit or registry attestation does not make skill-provided code safe to execute
without the consuming agent's own isolation and authorization controls.

Registry trust anchors are distributed out of band. Removing a key from the
pinned set revokes trust in signatures made solely by that key. Key rotation
and incident behavior are defined in `protocol/registry.md`.

## Release review

Stable protocol releases require:

1. schema and vector CI on all supported operating systems;
2. both conforming clients passing the same released vectors;
3. review of changes to canonicalization, hashing, signatures, snapshots,
   transparency logs, source identities, and path handling;
4. a signed release tag and immutable release artifacts.

`1.0.0-rc.1` is not promoted to stable until an independent security review
and an independent interoperability review are recorded in a public issue or
review report.
