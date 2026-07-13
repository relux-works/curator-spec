# Curator Protocol Specification

**Version:** 1.0.0-rc.1

**Date:** 2026-07-13

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
- `csk-skill.json`;
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
| [Manager profile](profiles/manager.md) | Normative installation lifecycle, scopes, adapters, MCP, audit, and shell behavior |
| [Curator CLI](cli/curator.md) | Informative command and CI guide for the Go implementation |
| [Conformance](conformance/README.md) | Normative conformance classes, vectors, and execution contract |
| [`schemas/v1`](schemas/v1) | Normative JSON Schemas for every versioned wire object |
| [`conformance/v1`](conformance/v1) | Normative positive and negative test vectors |

The normative keywords **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL
NOT**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **NOT RECOMMENDED**, **MAY**,
and **OPTIONAL** are interpreted as described by RFC 2119 and RFC 8174 when,
and only when, they appear in all capitals.

JSON Schemas define structural validity. Normative prose defines semantic
behavior not expressible in a schema. Conformance vectors define exact bytes
and required outcomes. If these sources disagree, the release is defective;
an implementation is never the normative oracle.

## Implementations

- [Curator](https://github.com/relux-works/curator) is the Go reference
  implementation and provides static binaries for Linux, macOS, and Windows.
- [csk](https://github.com/ivanopcode/cocoaskills) is an independent Python
  implementation.
- [CocoaSkills Registry](https://github.com/ivanopcode/cocoaskills-registry)
  is an implementation of the registry-service profile.

The implementations are evidence that the protocol is independently
implementable. Conformance is established only by the released schemas and
shared test vectors, not by copying behavior from either codebase.

## Release status

`1.0.0-rc.1` remains a draft until it receives an independent security review
of the registry protocol and an independent interoperability review of the
shared suite. See [COMPATIBILITY.md](COMPATIBILITY.md),
[SECURITY.md](SECURITY.md), and [GOVERNANCE.md](GOVERNANCE.md).

<!-- relux-ecosystem:start -->

## About Relux Works

This project is part of the open-source ecosystem of
[Relux Works](https://relux.works), an AI-native software development studio.

- Full catalog: [relux.works/en/open-source](https://relux.works/en/open-source/)
- Contact: ivan@relux.works

<!-- relux-ecosystem:end -->
