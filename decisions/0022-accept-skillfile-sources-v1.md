# Decision 0022: accept Skillfile sources revision 1 and repository transport revisions 1 and 2

## Status

Status: accepted

Accepted on 2026-09-24 by operator decision and agreement with the Curator
orchestrator. Decision 0020 remains reserved; this record uses the next
available number after Decision 0021.

## Context

Skillfile sources revision 1 and repository transport revisions 1 and 2 define
project-scope Skillfile schema 2, package snapshot identity, lock behavior and
bounded repository endpoint policy. Their schemas and vectors were developed
in a separate namespace so the accepted extension can retain an independent
pin from `schemas/v1` and `conformance/v1`.

The operator decided on 2026-09-24 to accept these revisions, make them
available by default in managers that implement the capability, and use the
lock replay rule in this record. Machine-global Skillfiles must continue to
follow the profile-lock model in `environments.md` §9.4 where that capability
exists.

Skill manifest v9 from issue #89 is outside this decision. It goes to the next
draft namespace and is not included in this acceptance.

For partial-client independence, the Curator orchestrator verified that the
source corpus references only definitions from `schemas/v1` that have remained
unchanged since rc.10. The accepted extension therefore does not require a
partial client to replace or reinterpret those definitions.

## Decision

1. Accept Skillfile sources revision 1 and repository transport revisions 1
   and 2 as normative specifications.
2. Managers that implement project-scope Skillfile schema 2 MUST enable this
   complete extension by default and MUST implement the full Skillfile sources
   revision together with both repository transport revisions. The protocol
   defines no operator switch for enabling or disabling the capability. A
   manager MAY omit project-scope schema-2 support; in that case it MUST reject
   schema 2 with the upgrade error. A manager that implements the extension
   MUST accept schema 2.
3. This extension defines project-scope Skillfiles. Machine-global Skillfiles
   follow `environments.md` §9.4 profile locks when the manager implements that
   capability. Without that capability, the manager MUST keep machine-global
   scope on Skillfile schema 1 and MUST reject schema 2 there with the upgrade
   error.
4. Installation with an existing lock consumes the locked snapshot. If it is
   missing from the manager's store, the manager re-materializes it from the
   declared source: Git and repository members are fetched by the locked commit
   object ID and checked for the locked object format and commit; path members
   are materialized from current bytes. The manager accepts the materialized
   result only when both package identity and `content_sha256` equal the lock;
   a mismatch fails with `source_snapshot_changed`. `source_snapshot_unavailable`
   applies only when the declared source cannot be reached or read. Replay never
   rewrites the lock, resolves, verifies or requires a declared tag or branch, or
   replaces a snapshot that is already present. This replay rule also governs
   transport revisions 1 and 2, including mirrors: their exact-tag verification
   applies to source resolution and explicit refresh/upgrade, where the ref is
   read. Changed manifest hashes continue to fail with `source_lock_stale`.
5. Keep schemas and vectors in their dedicated `skillfile-sources-v1`
   namespaces. Do not merge the corpus into `conformance/v1`. Definitions in
   `schemas/v1` remain unchanged by this decision.
6. Exclude Skill manifest v9 (#89) from this acceptance and handle it in the
   next draft namespace.

## Alternatives

- Keep the source and transport specifications as working drafts. Rejected
  because the operator and Curator orchestrator agreed to accept the complete
  revisions.
- Require an operator flag to turn schema 2 or either transport revision on.
  Rejected because support is a manager capability: implementing managers
  enable the accepted contract by default, while managers without it fail with
  the upgrade error.
- Fail whenever a locked snapshot is absent, or rebuild it from a path without
  comparing the locked identity and content hash. Rejected because the first
  makes a valid lock unusable after local store loss and the second could
  install drifted bytes under an old lock.
- Re-resolve a tag or branch during replay. Rejected because a mutable ref must
  not change the identity recorded by an existing lock.
- Merge the source vectors into the frozen v1 corpus. Rejected to preserve the
  extension's separate schema and corpus pin.
- Include Skill manifest v9 (#89) in this batch. Rejected; it remains for the
  next draft namespace.

## Compatibility impact

Skillfile schema 1 and existing `schemas/v1` definitions retain their current
meaning. A manager without the optional project-scope capability continues to
reject schema 2 with the upgrade error. A manager implementing the capability
accepts schema 2 and the complete transport revisions by default. The global
scope remains governed by profile locks when available and otherwise remains on
schema 1. The accepted schemas and conformance vectors remain in their own
namespace; release/version metadata is not changed by this decision record.

## Security impact

Replay of a missing snapshot does not turn a lock into permission to install
changed content. Path bytes are re-inventoried and checked against both locked
package identity and `content_sha256`; Git and repository members are fetched by
the locked commit object ID and checked for the locked object format and commit.
A mismatch fails closed as `source_snapshot_changed`, while
`source_snapshot_unavailable` identifies only an unreachable or unreadable
source. Replay leaves the lock bytes untouched, does not read, resolve, verify or
require a moved tag or branch, and does not replace a snapshot already present
in the store. Transport revisions 1 and 2 (including mirrors) apply exact-tag
verification only to resolution and explicit refresh/upgrade. Manifest hash
changes continue to fail with `source_lock_stale`.
