# Curator Protocol conformance

This document is normative. A conformance claim names the protocol release,
conformance classes, implementation version, operating system, and shared-suite
commit or release tag.

## 1. Authority

Conformance is determined by the released normative prose, JSON Schemas, and
vectors in this repository. Reference implementation behavior is informative.
When sources conflict, the release has a specification defect and no
implementation behavior silently resolves it.

## 2. Classes

### Core reader/writer

A core implementation:

1. validates skill schemas 1 through 5, Skillfile schema 1, development
   substitutions, install markers, and adapter ledgers;
2. applies portable identifier, path, source identity, and schema-version
   rejection rules;
3. computes context selection and content hashes exactly;
4. resolves closures, conflicts, cycles, activation, and deterministic order;
5. reads markers written by another core implementation and writes markers
   accepted by it.

### Manager

A manager satisfies the core class and the complete lifecycle, scope, adapter,
MCP, audit-decision, atomicity, shell, status, and garbage-collection rules of
`profiles/manager.md`. It never executes package-provided code at install time.

### Registry client

A registry client validates every registry schema; implements CCJ-1, Ed25519
verification with key-id binding, record matching, deny-wins federation,
snapshot persistence and clock bounds, paginated HTTP, caching, and error
handling.

### Registry service

A registry service implements authenticated submission, countersigning,
auditor-scoped idempotency, snapshot-bound deterministic pagination,
serialized durable append, append-only log, exact Merkle tree, immutable
snapshots, authenticated bundle export/import, verified recovery, and rollback
safe backup/restore according to `profiles/registry-service.md`.

## 3. Shared suite

`conformance/v1/manifest.json` lists every normative vector and SHA-256 digest.
The suite contains:

- valid and invalid examples for every JSON Schema;
- portable identifier, path, and source-identity tables;
- context-selection and raw-tree hash fixtures;
- closure graphs including diamond, conflict, cycle, narrowing, and tie order;
- normalized install marker and adapter ledger objects;
- CCJ-1 exact bytes and rejection cases;
- valid, forged, wrong-key-id, revoked, and malformed signed records;
- snapshot rollback, freeze, future-skew, incomplete-field, and equivocation
  cases;
- first-use, deleted-after-use, corrupted, and unavailable durable client
  rollback-state cases;
- retry classification and execution bounds, unchanged idempotent POST bytes,
  total deadlines, redirect refusal, cursor cycles, and response limits;
- shell-neutral runtime launchers, idempotent machine bootstrap, closure-scoped
  upgrades, fetch deduplication, and persistent-side-effect-free dry runs;
- transparency chain, Merkle, bundle, pagination, caching, and deny-wins cases;
- conjunctive registry queries, exact artifact identity, snapshot-bound pages,
  scoped idempotency, concurrent writers, transaction rollback, crash recovery,
  immutable snapshots, restore checkpoints, key rotation, transport bounds,
  rate limiting, and cache-control cases.

Files under `conformance/v1/expected` are generated only by
`tools/generate-vectors`. The generator imports no implementation packages.
Updating expected bytes is a protocol change and requires a reviewed diff.

## 4. Execution

From the specification repository:

```text
make validate
make regenerate-check
```

Implementations receive the absolute suite root through
`CURATOR_CONFORMANCE_ROOT`. They MUST NOT substitute repository-local golden
fixtures. Specification CI checks out pinned implementation revisions and
invokes their conformance entrypoints directly; orchestration contains no
expected protocol values.

Specification CI checks out released implementation revisions and executes:

```text
CURATOR_CONFORMANCE_ROOT=<spec>/conformance/v1 go test -v ./internal/interop ./internal/closure ./internal/skillspec
CURATOR_CONFORMANCE_ROOT=<spec>/conformance/v1 python -m pytest -v tests/test_protocol_conformance.py  # manager
CURATOR_CONFORMANCE_ROOT=<spec>/conformance/v1 python -m pytest -v tests/test_protocol_conformance.py  # registry service
```

The suite runs on Linux, macOS, and Windows. A skipped vector is a failure in
the specification gate. Implementation repositories MAY skip the external
suite only when `CURATOR_CONFORMANCE_ROOT` is absent from a developer checkout;
their required release CI always supplies it.

`.github/workflows/implementations.yml` pins every implementation by full Git
commit ID. A pin may advance only after that implementation has passed the
same released suite in its own required CI. Branch names and mutable tags MUST
NOT be used as implementation pins.

## 5. Claim format

A machine-readable claim conforms to `schemas/v1/conformance-claim-v1.schema.json`.
At minimum it records protocol version, implementation name and version,
classes, suite digest, operating systems, timestamp, and pass result. Claims do
not replace release CI evidence or artifact attestations.

## 6. Release gate

A protocol release candidate may be published only when:

1. all schemas compile under Draft 2020-12;
2. every example has the expected validation result;
3. two consecutive vector generations are byte-identical;
4. Go and Python pass the same suite on all three operating systems;
5. registry-service vectors pass;
6. Markdown links and version references are valid;
7. required security and interoperability review reports have no open critical
   or high findings;
8. the release commit and tag are cryptographically signed.

For a stable version, `python tools/release_gate.py --version <version>` also
requires two schema-valid independent reports, no open critical or high
findings, and no normative diff after either reviewed commit.
