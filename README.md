# Curator Protocol Specification

**Version:** 1.0.0-rc.13

**Date:** 2026-09-26

**Status:** Draft release candidate

**Authors:** Ivan Oparin, Alexey Grigorev

**License:** MIT

Curator is an open protocol for declarative, reproducible, security-gated
installation of AI agent skills. It defines portable skill and project
manifests, deterministic dependency closure and installation artifacts, MCP
requirements, and a cryptographically verifiable audit-registry protocol.

The specification is implementation-neutral. A conforming manager may use any
language, command name, machine-home directory, environment variables, user
interface, or internal architecture. Compatibility identifiers inherited from
the deployed protocol remain unchanged:

- `Skillfile.json` and `Skillfile.dev.json`;
- `agent-skill.json` (canonical) and `csk-skill.json` (legacy read alias);
- `.csk-install.json` and `.csk-managed.json`;
- `.agents/` as the portable project installation root.

These names are wire identifiers, not ownership claims by a particular
implementation.

## Specification set

The release consists of the following documents and artifacts:

| Part | Role |
|---|---|
| [Protocol core](protocol/core.md) | Normative package, manifest, identity, closure, hashing, and marker rules |
| [Registry protocol](protocol/registry.md) | Normative canonical JSON, signatures, records, snapshots, log, bundles, cache, and HTTP rules |
| [Assurance protocol](protocol/assurance.md) | Normative portable/verified selection, provider, evidence, identity, and fail-closed rules |
| [Manager profile](profiles/manager.md) | Normative installation lifecycle, scopes, adapters, MCP, audit, and shell behavior |
| [Registry service profile](profiles/registry-service.md) | Normative production guarantees for pagination, transactions, durability, recovery, keys, and operations |
| [Curator CLI](cli/curator.md) | Informative command and CI guide for the Go implementation |
| [Conformance](conformance/README.md) | Normative conformance classes, vectors, and execution contract |
| [External repositories](docs/external-build-repositories.md) | Author and operator guide for schema 7 and `go-repository-v1` |
| [Assurance modes](docs/assurance-modes.md) | Operator guidance for portable and separately installed verified providers |
| [`schemas/v1`](schemas/v1) | Normative JSON Schemas for every versioned wire object |
| [`conformance/v1`](conformance/v1) | Normative positive and negative test vectors |
| [Release checklist](RELEASE.md) | Candidate, independent review, signing, checksum, and attestation gates |

The normative keywords **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL
NOT**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **NOT RECOMMENDED**, **MAY**,
and **OPTIONAL** are interpreted as described by RFC 2119 and RFC 8174 when,
and only when, they appear in all capitals.

JSON Schemas define structural validity. Normative prose defines semantic
behavior not expressible in a schema. Conformance vectors define exact bytes
and required outcomes. If these sources disagree, the release is defective;
an implementation is never the normative oracle.

## Accepted source extension

[Skillfile sources revision 1](protocol/skillfile-sources.md) defines the
optional project-scope schema-2 lane for local and Git acquisition,
individual/collection selection and frozen package identity. The accepted
[repository transport revisions 1 and 2](protocol/repository-transport.md)
define machine endpoint policy (revision 1 endpoints; revision 2 adds ports,
declared mirrors and host aliases). See the
[author/operator guide](docs/skillfile-sources.md),
[schemas](schemas/skillfile-sources-v1/README.md) and the dedicated
[conformance corpus](conformance/skillfile-sources-v1/README.md). These schemas
and vectors remain in their own namespace; they are not merged into
`conformance/v1`.

## Tools

- Python 3 with `python3 -m pip install -r requirements-dev.txt`: run
  `python3 tools/validate.py` and
  `python3 -B -m unittest discover -s tools -p "test_*.py"` for the existing
  schema/vector/link checks. The accepted source corpus has a standalone validation command
  in the conformance README linked above. Store local logs in `.temp/`.
- Go: `go test ./tools/...` tests specification tooling;
  `go run ./tools/generate-vectors -root .` regenerates the released corpus
  under `conformance/v1/`, its release metadata, and the independent
  `conformance/skillfile-sources-v1/manifest.json` pin. It does not fold the
  accepted source-extension vectors into the core corpus.
- Make: `make validate` runs the existing Python/Go checks;
  `make regenerate-check` checks generator reproducibility against Git.

## Implementations

- [Curator](https://github.com/relux-works/curator) is the Go reference
  implementation and provides static binaries for Linux, macOS, and Windows.
- [csk](https://github.com/ivanopcode/cocoaskills) is an independent Python
  implementation.
- [Curator Skill Registry](https://github.com/relux-works/curator-skill-registry)
  is an implementation of the registry-service profile.

The implementations are evidence that the protocol is independently
implementable. Conformance is established only by the released schemas and
shared test vectors, not by copying behavior from either codebase.

A pinned implementation must demonstrably *consume* what this repository
publishes, not merely pass against it: a family's presence in the conformance
root was never evidence that anything read it.
[`.github/ci/implementation-coverage.tsv`](.github/ci/implementation-coverage.tsv)
names the cases each pin must be observed passing for the schema-8 families,
and `tools/implementation_coverage.py` enforces that ledger against each run's
own result stream and against this suite's published manifest.

## Release status

`1.0.0-rc.13` is a draft candidate. Portable remains the default CLI-only mode.
Verified mode is explicit, requires the platform-neutral
`host-execution-provider-v1` contract, and fails before execution rather than
silently downgrading. Provider binaries are separately installed trusted host
components and are never skill-vendored artifacts. This candidate specifies
the common contract for macOS, Linux, and Windows but ships no provider and
emits no verified platform claim. Exact core-suite and accepted
skillfile-sources-v1 identities are recorded in
[`release/1.0.0-rc.13.json`](release/1.0.0-rc.13.json). The source suite is
separately pinnable and remains consumable with core v1.0.0-rc.10; it does not
add a manifest schema v9 `directory` field to the core suite. Rc.9 and earlier
release metadata remain byte-frozen historical evidence. Review evidence is
published under [`reviews/`](reviews/). See
[COMPATIBILITY.md](COMPATIBILITY.md),
[SECURITY.md](SECURITY.md), and [GOVERNANCE.md](GOVERNANCE.md).

<!-- relux-ecosystem:start -->

## About Relux Works

This project is part of the open-source ecosystem of
[Relux Works](https://relux.works), an AI-native software development studio.

- Full catalog: [relux.works/en/open-source](https://relux.works/en/open-source/)
- Contact: ivan@relux.works

<!-- relux-ecosystem:end -->
