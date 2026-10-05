# Curator Improvement Proposals

Curator Improvement Proposals (CIPs) describe and argue for changes to the
Curator protocol and its implementations. They preserve the problem, evidence,
alternatives, recommendation, and operator questions in one reviewable document.
The process was accepted by the operator on 2026-10-04 in
[CIP-0001](CIP-0001-curator-improvement-proposals.md).

## Relationship to issues, decisions, and the specification

An issue identifies a problem, tracks discussion, or requests work. A CIP
develops a design and links the relevant issues and board items. Research
evidence stays in the implementation repository's `.research/`; the CIP cites
that evidence and summarizes the findings needed to evaluate its design.

A CIP proposes and argues. Adoption of a protocol design produces Decision
record(s) under [`decisions/`](../decisions/) and updates the affected normative
prose, schemas, and conformance vectors under
[GOVERNANCE.md](../GOVERNANCE.md). Decision records capture the adopted choice
and its compatibility and security impact. The released specification remains
the authority for conformance; an Accepted CIP alone does not change it or
establish that an implementation has shipped. Implementation-only proposals
identify their implementation work without inventing a protocol change.

Existing decision records retain their identities and status. Introducing CIPs
does not renumber or retroactively reclassify them.

## Numbering and files

Use `CIP-NNNN-<slug>.md`, with a four-digit, sequential number and a descriptive
lowercase hyphenated slug. Allocate the next unassigned number in the index,
including any reservations. Numbers are never reused, even after rejection,
withdrawal, or supersession. A replacement proposal receives a new number and
links the earlier CIP.

Reserve a number by adding an **In preparation** index row. This label means
that no proposal file has been filed yet; it is not a CIP lifecycle status.
When the file is added, link it from the index and replace the reservation label
with its status. Do not link reservations to nonexistent files.

## Status and lifecycle

The operator or maintainer decides the status. Keep the file metadata and index
in agreement, and record the decision maker, date, and rationale or decision
reference when a proposal leaves review.

| Status | Meaning |
|---|---|
| Draft | A filed proposal being developed; unresolved questions remain explicit. |
| Review | A proposal ready for operator or maintainer consideration. |
| Accepted | The proposed direction has been adopted; specification and implementation work are tracked separately. |
| Rejected | The proposed direction was considered and declined. |
| Withdrawn | The proposal was withdrawn from consideration. |
| Superseded | A later CIP replaces it; retain and link both proposals. |

1. Reserve the next number and copy [TEMPLATE.md](TEMPLATE.md) into the named
   proposal file with Status: Draft.
2. Fill every required section, cite evidence, and link related work. Use an
   explicit explanation where a section does not apply.
3. Seek review with Status: Review. Revise the design and operator questions as
   discussion resolves them; return to Draft if more design work is needed.
4. Record the operator's or maintainer's Accepted, Rejected, or Withdrawn
   decision in the proposal and index. Preserve the document and its number.
5. For an accepted design, track the adoption artifacts and implementation
   work. Apply the governance requirements to every normative change.
6. If a later CIP replaces an accepted design, mark the earlier CIP Superseded
   and add reciprocal links. Its decision and release history remain available.

## Required contents

The [template](TEMPLATE.md) is the binding section list. Retain its title and
Status, Owner, Created, Related, and Affects metadata, followed by:

- Summary;
- Motivation and user stories;
- Current state;
- Design, including Options considered and Recommendation;
- Security considerations;
- Compatibility and migration;
- Specification changes;
- Implementation plan;
- Test plan;
- Open questions for the operator.

For implementation designs, cite file:line locations on the identified Curator
main revision, specification rc.14 section references, and measured probes.
State the revision and limits of the evidence. Do not infer implementation
behavior from a specification requirement or claim unperformed tests as results.
Keep operator questions numbered and decision-ready, with a recommended answer.

## Index

| Number | Title | Status |
|---|---|---|
| [CIP-0001](CIP-0001-curator-improvement-proposals.md) | Curator Improvement Proposals | Accepted |
| [CIP-0002](CIP-0002-project-context-in-managed-launches.md) | Project context in managed launches | Draft |
| [CIP-0003](CIP-0003-claude-managed-home-credential-modes.md) | Claude managed-home credential modes | Draft |
| [CIP-0004](CIP-0004-shell-hook-without-sourcing-and-path-append.md) | Shell hook without sourcing and PATH append | Draft |
| [CIP-0005](CIP-0005-audit-backends-and-cli-secret-transport.md) | Audit backends and CLI secret transport | Draft |
| [CIP-0006](CIP-0006-legacy-provider-settings-and-mcp-opt-outs.md) | Legacy provider settings and MCP opt-outs | Draft |
