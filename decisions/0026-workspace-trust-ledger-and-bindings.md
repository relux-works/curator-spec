# Decision 0026: Workspace trust ledger and binding consent

## Context

[CIP-0020](../cips/CIP-0020-workspace-trust-ledger.md) was accepted on
2026-10-17. Native trust seeds cannot establish environment-scoped operator
consent or distinguish replacement repositories at the same path.

## Decision

Adopt CIP sections 1–3 and the ledger/reference portion of section 6 as A1
in [environments section 7.10](../protocol/environments.md#710-workspace-trust-ledger).
Publish `workspace-trust-record-v1` as private machine state. One implicit-bind
record is one binding reference for one environment and repository root.
Installation or context extraction records that reference atomically with the
binding, without a second confirmation. Identity changes lapse authorization;
updates and retries cannot renew it. Explicit removal revokes all events at
the exact environment/path pair, retaining provenance and installed bindings.

## Alternatives

Native-state-only trust loses consent provenance. Prefix grants cross workspace
boundaries. Profile-name scoping crosses adapters. Remote-only identity cannot
distinguish a replacement root history. All are rejected.

## Compatibility impact

This is an unreleased additive private record namespace; released markers,
locks, fragments, corpus pins and signed bytes stay unchanged. Existing seeds
and `seeded_projects` do not migrate to grants. A new valid operator event is
required. A2 owns managed-home projection, ownership journals and adapter
qualification; A3 owns tooling derivatives and task-board hints. Neither is
activated or specified by A1. No Curator implementation is delivered here.

## Security impact

Admission is exact-path, no-follow across every component and held through
use. Repository discovery must not execute repository-controlled commands.
Read failure remains unknown, never absence. Private records never travel in
profiles, package snapshots, locks, exports or managed-home snapshots.
Revocation cannot erase independent vendor consent or terminate sessions.
The identity tuple is consent provenance, not content attestation, and cannot
detect a byte-identical clone or malicious commits on unchanged root history.

## Conformance boundary

[A1 conformance](../conformance/workspace-trust-v1/README.md) executes schema
admission and a deterministic transition oracle with paired positive/negative
vectors. Three narrowing mutants exercise that oracle. These checks establish
specification consistency only; real no-follow filesystem operations, Git
discovery, persistence, concurrency, crash recovery and vendor execution need
production-entry qualification in implementation repositories.
