# Curator Protocol Specification

**Version:** 1.0.0-rc.14

**Date:** 2026-10-02

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

## Project Skillfile MCP stage A

[Stage A revision 1](protocol/skillfile-mcp.md) and
[Decision 0029](decisions/0029-project-skillfile-mcp-stage-a.md) publish project
schema 3, package-first MCP trust, the [closed runtime-pin sheet](protocol/mcp-runtime-pins.md),
[versioned carriers](schemas/skillfile-mcp-v1/README.md) and
[a separate corpus](conformance/skillfile-mcp-v1/README.md). Inline arms remain
refused pending CIP-0002 admission. No native writer or launch qualification
is claimed by these specification artifacts.

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

## Accepted local hosted direction

[Local hosted launches](protocol/local-hosted-launches.md) freezes CIP-0016's
ownership, selection and receiver summary. Its
[semantic corpus](conformance/local-hosted-launches/README.md) covers required
and forbidden selection outcomes. Successor wire publication, four named
questions and real adapter qualification remain gated; acceptance enables no
production receiver and changes no released schema.
The [delegated-launch revision accepted on 2026-10-21](cips/CIP-0016-local-hosted-launches.md#revision-delegated-local-launches-2026-10-21)
records a transitional live-home route with per-runtime activation and
retirement. Home leases and exclusive profile homes remain proposed; filing
the amendment claims no implementation or qualification.

## Accepted login-readiness amendment

[Login readiness revision 1](protocol/login-readiness.md) freezes CIP-0015
leaf 1 with [standalone schemas](schemas/login-readiness-v1/README.md) and
[a separate corpus](conformance/login-readiness-v1/README.md). [Containing carriers](protocol/rc7-carriers.md) allocates complete
configuration/status/fragment successors;
released schema bytes and v1–v3 fragment rules remain unchanged. Acceptance
does not claim implementation or platform qualification.

## Profile Codex settings extension

The accepted [profile Codex settings contract](protocol/profile-codex-settings.md)
adopts CIP-0018 leaf 1 and D14: an empty package vocabulary, retained weighted
inheritance, machine-owned credential-store launch delivery and explicit
eligibility rules. Its
[member schemas](schemas/profile-codex-settings-v1/README.md) and
[conformance corpus](conformance/profile-codex-settings-v1/README.md) are
unreleased and separate from frozen rc.14 artifacts. Coordinated successor carriers are [published](schemas/rc7-carriers-v1/README.md);
supported-release qualification and strict covered delivery remain open before
producer activation; see [unresolved adoption questions](UNRESOLVED_QUESTIONS.md).

## Local setup-token source publication

[Protected local source](protocol/local-setup-token-source.md) publishes the
same-user/same-host Claude slice, closed [schemas](schemas/local-setup-token-v1/README.md)
and [publication corpus](conformance/local-setup-token-v1/README.md). Native
login stays default. Vendor execution and route qualification remain unverified;
launcher companion publication gates producer emission.

## Proposals

[Managed-home snapshots](protocol/managed-home-snapshots.md) specify the
Accepted CIP-0014 leaf-1 content, manifest and portable-descriptor contract.
Its [separate schemas](schemas/managed-home-snapshot-v1/README.md) and
[corpus](conformance/managed-home-snapshot-v1/README.md) preserve released
schema bytes and core-suite identities. Archive bytes/caps and runtime
projection remain gated; no implementation support is claimed.

[Workspace trust A1](protocol/environments.md#710-workspace-trust-ledger) adopts
[CIP-0020](cips/CIP-0020-workspace-trust-ledger.md)'s private exact-path ledger,
repository binding consent and revocation. The
[record schema](schemas/workspace-trust-v1/README.md) and
[executable corpus](conformance/workspace-trust-v1/README.md) qualify specification
consistency only. A2 projection/adapters and A3 tooling derivatives remain deferred.

Protocol and implementation designs are recorded as
[Curator Improvement Proposals](cips/README.md). Start with the
[CIP template](cips/TEMPLATE.md) and the Accepted process in
[CIP-0001](cips/CIP-0001-curator-improvement-proposals.md); adoption follows
[GOVERNANCE.md](GOVERNANCE.md).

[CIP-0022: MCP server declarations in the project Skillfile](cips/CIP-0022-mcp-server-declarations-in-project-skillfile.md)
proposes project schema 3, package-first resolution and digest-approved inline
contributions. It was accepted by the operator on 2026-10-22; normative grammar
publication and native qualification remain gates. No implementation support
is claimed.

[CIP-0023: Exact-plan hosted launches](cips/CIP-0023-exact-plan-hosted-launches.md)
proposes a snapshot-bound successor with detached sessions, doorbells, durable
records, per-runtime delegated retirement and admitted project snapshot inputs.
It was accepted by the operator on 2026-10-22; normative grammar publication
and native qualification remain gates. Acceptance publishes no wire schema or
runtime capability.

## CIP diagram sources

[Source index and phase/authority notes](cips/diagrams/README.md) map the B4 module views to their defining CIP sections. These views describe current contracts and proposed targets; they do not assert implementation or qualification.

| Figure | Source | Defining section |
|---|---|---|
| Donor components (C4 retained) | [donor-side.dsl](cips/diagrams/donor-side.dsl) | [D0–D3, D5, D12](cips/CIP-0009-donor-side-deployment-and-bridge.md#recommendation) |
| Donor components (PlantUML) | [donor-side.puml](cips/diagrams/donor-side.puml) | [D0–D3, D5, D9, D12](cips/CIP-0009-donor-side-deployment-and-bridge.md#recommendation) |
| First deployment | [donor-first-deployment.puml](cips/diagrams/donor-first-deployment.puml) | [D0–D4, D9–D10, D12](cips/CIP-0009-donor-side-deployment-and-bridge.md#recommendation) |
| Join handshake | [join-handshake.puml](cips/diagrams/join-handshake.puml) | [D4, D6, D9, D12](cips/CIP-0009-donor-side-deployment-and-bridge.md#recommendation) |
| Remote-worker turn | [remote-worker-turn.puml](cips/diagrams/remote-worker-turn.puml) | [D0–D5, D12; CIP-0008 R3/R5/R9](cips/CIP-0009-donor-side-deployment-and-bridge.md#recommendation) |
| Retirement sequence | [remote-worker-retire.puml](cips/diagrams/remote-worker-retire.puml) | [D7, D12](cips/CIP-0009-donor-side-deployment-and-bridge.md#recommendation) |
| Deployment variants | [donor-variants.puml](cips/diagrams/donor-variants.puml) | [D0–D3; CIP-0008 R9](cips/CIP-0009-donor-side-deployment-and-bridge.md#recommendation) |
| Independent lifecycle axes | [donor-lifecycle.puml](cips/diagrams/donor-lifecycle.puml) | [D7, D12](cips/CIP-0009-donor-side-deployment-and-bridge.md#recommendation) |
| State layout | [donor-layout.puml](cips/diagrams/donor-layout.puml) | [D0–D3, D5, D7, D12](cips/CIP-0009-donor-side-deployment-and-bridge.md#recommendation) |
| Credential source lifecycle | [credential-source-lifecycle.puml](cips/diagrams/credential-source-lifecycle.puml) | [C1–C6, Revision 2.2; CIP-0003 migration; CIP-0011 §2/§3](cips/CIP-0010-credentials-setup-token-and-inherited-auth.md#recommendation) |
| Configuration publication | [configuration-publication.puml](cips/diagrams/configuration-publication.puml) | [CIP-0002 admission/leases/PATH; CIP-0004 recommendation/migration; CIP-0006 design/migration](cips/CIP-0002-project-context-in-managed-launches.md#recommendation) |
| Tool admission | [tool-admission.puml](cips/diagrams/tool-admission.puml) | [Operator decision, option B, recommendation/security; shared D-PATH](cips/CIP-0007-manager-provisioned-cli-tools.md#recommendation) |
| Audit transport | [audit-transport.puml](cips/diagrams/audit-transport.puml) | [Recommendation §§1–7](cips/CIP-0005-audit-backends-and-cli-secret-transport.md#recommendation) |

## Tools

- Skillfile MCP stage-A gate: `python3 tools/validate.py` dispatches
  `tools/skillfile_mcp.py`; focused controls run with
  `python3 -B -m unittest discover -s tools -p 'test_skillfile_mcp.py'`.
  Inputs and expected verdicts live in `conformance/skillfile-mcp-v1/`; checks
  report to stdout and do not acquire packages or write native configuration.

Published `release/<version>.json` records are byte-frozen against release
tags. Regeneration updates [candidate metadata](conformance/candidate.json)
with the current core and source-suite manifest digests, without selecting the
next release version. Release preparation creates a new versioned record.
Validation requires local release tags (fetch tags in shallow checkouts).

- Python 3 with `python3 -m pip install -r requirements-dev.txt`: run
  `python3 tools/validate.py` and
  `python3 -B -m unittest discover -s tools -p "test_*.py"` for the existing
  schema/vector/link checks, including the later
  [managed Muse v4 cases](conformance/environments-muse-v4/README.md). Run
  `python3 -B -m unittest discover -s tools -p "test_muse_v4.py"` for its
  targeted schema and negative controls. The accepted source corpus has a standalone validation command
  in the conformance README linked above. Store local logs in `.temp/`.
  The same validator dispatch also checks the separate managed-home snapshot
  corpus; `tools/managed_home_snapshots.py` checks metadata and semantic
  counterexamples. It does not run a manager or launcher.
  Local hosted specification-data checks run with
  `python3 -B -m unittest discover -s tools -p "test_local_hosted_launches.py"`;
  they read `conformance/local-hosted-launches/cases.json` and do not launch providers.

- Login-readiness structural gate: `python3 tools/validate.py` calls
  `tools/login_readiness.py`; `python3 -B -m unittest discover -s tools -p
  "test_login_readiness.py"` checks refusal controls. Inputs live in
  `schemas/login-readiness-v1/` and `conformance/login-readiness-v1/`; local
  logs go in `.temp/`. No runtime login or Keychain probe runs here.

- Profile Codex settings: `python3 -B -m unittest discover -s tools -p 'test_profile_codex_settings.py' -v` checks the five member schemas,
  positive/negative cases and semantic-vector inventory. These tests also run
  in `make validate`; they do not qualify runtime entrypoints. Corpus outputs
  live in `conformance/profile-codex-settings-v1/`; logs belong in `.temp/`.
- Draft source marker: `python3 -B -m unittest discover -s tools -p 'test_source_marker.py' -v`
  validates manifestless v6 positives/negatives and narrowing controls through
  the published JSON Schema. `python3 tools/validate.py` also recomputes all
  ownership-vector refusal, preservation and re-derivation obligations from
  their inputs; marker tests include narrowing controls through that entry point.
  Fixtures live in `conformance/draft-sources-v2/`;
  logs go under `.temp/`. Ownership filesystem behavior requires a manager
  harness and is not executed by these specification checks.
- Whole-carrier publication: `python3 tools/rc7_carriers.py` and
  `python3 -B -m unittest discover -s tools -p 'test_rc7_carriers.py' -v`
  validate the complete successor corpus, including old/new compatibility.
  Status checks include the Muse home-source/file-backend relation and bounded
  cross-document execution prohibitions, with regression/narrowing controls.
  `python3 tools/check_rc7_carrier_controls.py` reports narrowing mutants and
  a bounded invalid-carrier plant. Fixtures are in `conformance/rc7-carriers-v1/`;
  these checks qualify no vendor runtime. Local logs belong in `.temp/`.
- Workspace trust A1: `python3 tools/workspace_trust.py` validates private record
  schemas and deterministic transition vectors; `python3 -B -m unittest discover
  -s tools -p 'test_workspace_trust.py' -v` runs the paired assertions.
  `python3 tools/check_workspace_trust_controls.py` reports the three required narrowing
  mutants plus binding-trigger, retry and bind grant-root admission controls;
  its `--mutant NAME` mode intentionally exits 1 on the named failure.
  Inputs live in `schemas/workspace-trust-v1/` and `conformance/workspace-trust-v1/`;
  logs go in `.temp/`. `make validate` includes the publication entry and tests.
  No filesystem, Git, crash-recovery or vendor runtime is qualified.
- Go: `go test ./tools/...` tests specification tooling;
  `go run ./tools/generate-vectors -root .` regenerates the released corpus
  under `conformance/v1/`, its release metadata, and the independent
  `conformance/skillfile-sources-v1/manifest.json` pin. It does not fold the
  accepted source-extension vectors into the core corpus.
- Network-contact classification: `python3 tools/network_contacts.py` checks
  the unreleased [section 9.1 detector supplement](conformance/context-detectors/README.md).
  Run `python3 -B -m unittest discover -s tools -p 'test_network_contacts.py' -v`
  for regression and negative controls, included in `make validate`.
  `python3 tools/check_network_contact_controls.py --mutant example-domain`
  and the same command with `--mutant substring` plant bounded mutants;
  both are expected to exit 1 with a named vector-test failure. Corpus inputs
  live in `conformance/context-detectors/`; local logs go in `.temp/`.
  These checks qualify no manager runtime.
- Make: `make validate` runs the existing Python/Go checks;
  `make regenerate-check` checks generator reproducibility against Git.
- Lychee: `lychee --no-progress --max-retries 3 --retry-wait-time 2 --accept 200,206,429,502,503,504 '**/*.md'`
  runs the CI Markdown link check locally; save its log under `.temp/`.

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

`1.0.0-rc.14` is a draft candidate. Portable remains the default CLI-only mode.
Verified mode is explicit, requires the platform-neutral
`host-execution-provider-v1` contract, and fails before execution rather than
silently downgrading. Provider binaries are separately installed trusted host
components and are never skill-vendored artifacts. This candidate specifies
the common contract for macOS, Linux, and Windows but ships no provider and
emits no verified platform claim. Exact core-suite and accepted
skillfile-sources-v1 identities are recorded in
[`release/1.0.0-rc.14.json`](release/1.0.0-rc.14.json). The source suite is
separately pinnable and remains consumable with core v1.0.0-rc.10; it does not
add a manifest schema v9 `directory` field to the core suite. Rc.13 and earlier
release metadata remain byte-frozen historical evidence. Scoped implementation
CI does not establish full rc.14 conformance or native platform claims.
Review evidence is published under [`reviews/`](reviews/). See
[COMPATIBILITY.md](COMPATIBILITY.md),
[SECURITY.md](SECURITY.md), and [GOVERNANCE.md](GOVERNANCE.md).

<!-- relux-ecosystem:start -->

## About Relux Works

This project is part of the open-source ecosystem of
[Relux Works](https://relux.works), an AI-native software development studio.

- Full catalog: [relux.works/en/open-source](https://relux.works/en/open-source/)
- Contact: ivan@relux.works

<!-- relux-ecosystem:end -->

### Local-source publication tools

`python3 tools/local_setup_token.py` checks the metadata-only publication
corpus; `python3 -B -m unittest discover -s tools -p 'test_local_setup_token.py' -v`
runs paired refusal tests. `python3 tools/check_local_setup_token_controls.py`
runs narrowing mutants; its `--plant secret` and `--plant branch` commands
intentionally exit 1 for disposable forbidden-field/unknown-branch plants.
`make validate` includes the publication checker and tests. Inputs live under
`schemas/local-setup-token-v1/` and `conformance/local-setup-token-v1/`;
transient logs go under `.temp/`. These commands never access credential stores
or execute a vendor harness.

The stage-A grammar oracle reuses `tools/ccj1_grammar.py` for lexical integer
spelling, pre-conversion token bounds, per-component portable paths and
private-catalog true-end guards. Run the shared positive, negative
and narrowing controls with
`python3 -B -m unittest discover -s tools -p test_ccj1_grammar.py`. These tests
emit no files and do not rewrite released schema documents.
