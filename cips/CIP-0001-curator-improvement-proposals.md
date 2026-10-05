# CIP-0001: Curator Improvement Proposals

- **Status:** Accepted (operator, 2026-10-04)
- **Owner:** ivan-curator (orchestrator); decision: operator
- **Created:** 2026-10-04
- **Related:** TASK-261004-3pvg2k — introduce-cips-directory-and-process;
  STORY-261004-1lk8e9 — parent story for introducing CIPs;
  [Governance](../GOVERNANCE.md) — changes, releases, and decision records
- **Affects:** Documentation process in curator-spec; design proposals for
  curator, curator-run/launcher, and other implementations

## Summary

Introduce Curator Improvement Proposals as the home for protocol and
implementation design proposals in curator-spec `cips/`. Each CIP records the
problem, evidence, alternatives, recommendation, and operator questions using
one shared template. Research evidence remains in the implementation
repository's `.research/` and is cited from the proposal. The operator accepted
this process on 2026-10-04; adoption of a protocol design still follows the
existing governance requirements for decision records and normative artifacts.

## Motivation and user stories

The operator requires design proposals for the protocol and its implementations
to live together in curator-spec, with research evidence retained beside the
implementation being investigated. A reviewer needs to compare options and
security consequences before a design becomes an adopted decision. An
implementer needs to distinguish a proposed direction from released requirements
and from work that has actually shipped. Stable numbers and explicit statuses
let issues, decisions, and implementation tasks cite the same proposal over time.

## Current state

The specification baseline is 1.0.0-rc.14, as identified by
[`README.md`](../README.md). [GOVERNANCE.md, Changes](../GOVERNANCE.md#changes)
defines normative-change review and validation, and
[Decision record](../GOVERNANCE.md#decision-record) defines the records required
for schema versions, signed bytes, and trust semantics. Existing designs and
adopted choices are recorded under [`decisions/`](../decisions/).

Before this proposal, the repository had no `cips/` directory or shared CIP
template. This is a documentation-process proposal: no Curator main runtime
behavior or file:line evidence is needed, and no behavioral probe is claimed.
The initial core manifest SHA-256 is
`6f832d813efc768ea154a7d5076b512ab4be6aa9409d92e11469d21ea9bc69f5`;
this process does not change its inputs.

## Design

### Options considered

1. **Use issues alone.** Keep design discussion in issue threads. This provides
   familiar discussion and tracking, but lacks a stable, versioned section list
   and a clear separation between proposals and adoption. Security evidence and
   unresolved trust assumptions are harder to review together.
2. **Use decision records for proposals and adopted choices.** Extend the
   existing `decisions/` collection. This keeps designs close to their adoption
   records, but makes proposal and decision roles less distinct and can obscure
   whether a security-sensitive choice has been adopted.
3. **Add CIPs alongside decision records.** Store numbered designs in `cips/`,
   link issues and research, and retain decision records for adoption. This adds
   metadata and index maintenance but gives reviewers a consistent place to
   inspect alternatives, compatibility, and security before adoption.

### Recommendation

Adopt option 3, as decided by the operator on 2026-10-04. The
[process README](README.md) defines sequential, never-reused numbers, the
Draft, Review, Accepted, Rejected, Withdrawn, and Superseded statuses, and an
index. The operator or maintainer decides status and records the decision.
The [template](TEMPLATE.md) supplies the binding section list. Reservations
for CIP-0002 through CIP-0006 use the index label In preparation until files
are filed; that label is not an additional lifecycle status.

The operator gets explicit proposals and decision-ready questions. This change
adds no runtime mode, configuration key, or default.

## Security considerations

Proposal text and evidence links are review inputs, not executable authority.
An Accepted CIP does not bypass normative review, release gates, or trust
requirements. Research should identify the examined revision and measured
limits; hostile repository content or a changing checkout cannot establish an
unqualified implementation claim. Proposals should summarize secrets handling
without publishing credentials, tokens, or sensitive probe output.

This process adds no credential transport or execution boundary. Runtime
TOCTOU risks and hostile-repository mitigations belong in the relevant design
CIP and its adoption artifacts; this proposal makes no new runtime guarantee.

## Compatibility and migration

Existing issues and decision records keep their identities, content, and
adoption status. New design proposals use CIPs and link the relevant earlier
records. Research evidence remains in implementation `.research/` directories;
it is not relocated to curator-spec. No existing installation, configuration,
fragment, wire schema, or release metadata changes.

## Specification changes

Add `cips/README.md`, `cips/TEMPLATE.md`, and this process CIP. Add proposal
links in the root README and GOVERNANCE.md. The process itself requires no new
protocol Decision record, normative text, schema, or conformance vector.

Adoption of future protocol designs produces Decision record(s) and affected
normative prose, schemas, and vectors under GOVERNANCE.md. CIP acceptance
records a direction; those adoption artifacts establish the resulting
specification. Implementation-only CIPs identify their implementation scope.

## Implementation plan

1. Small docs leaf: add the process, binding template, and Accepted CIP-0001.
2. Small docs leaf: reserve CIP-0002 project context in managed launches,
   CIP-0003 Claude managed-home credential modes, CIP-0004 shell hook without
   sourcing and PATH append, CIP-0005 audit backends and CLI secret transport,
   and CIP-0006 legacy provider settings and MCP opt-outs in the index.
3. Small docs leaf: add discovery links and run repository validation before
   handing the documentation to review.

No runtime implementation or new conformance vector is needed for this process.
Each later CIP describes its own spec-first or lockstep adoption sequence.

## Test plan

Run `make validate` with the development Python dependencies in a virtual
environment. Check local links and formatting, verify that the template retains
the supplied section list, and inspect the index for the six assigned numbers
and their stated statuses. Verify that protocol, profiles, schemas, conformance,
and release artifacts are unchanged and that the core manifest digest stays
equal to the initial value.

This documentation process has no production entry point, runtime platform
matrix, or behavioral mutants. Future implementation CIPs retain the template's
requirements to describe production-entry tests and negative cases.

## Open questions for the operator

None. The operator decided on 2026-10-04 to introduce this process, retain
research in implementation `.research/`, and reserve CIP-0002 through CIP-0006.
Their design questions belong in their respective proposals when filed.
