# Codex provisioning seed, revision C

This normative, unreleased amendment extends [environments section 7.4](environments.md)
for new `codex_cli` managed-home provisioning only. It is separate from the
frozen rc.14 schemas and A/B vectors. Acceptance specifies requirements; it
does not assert implementation adoption or qualify a vendor release.

## 1. Seed transformation

Revision C MUST apply revision B's MCP exclusion and additionally remove the
entire top-level `projects` member and all descendants from the native
`config.toml` seed. No project-trust entry is inherited. This includes trusted
and untrusted entries, empty tables, existing and missing paths, paths from
another host and paths naming symlinks. A manager MUST NOT inspect project
path existence, resolve those paths, or follow their links to decide whether
to retain an entry. Removal is unconditional, not an allowlist of local paths.

Every other top-level member MUST retain its decoded TOML value, including
model and TUI settings and unrelated profile settings. Filtering MAY change
TOML formatting, comments and table order; byte-for-byte preservation of a
filtered document is not required. If neither excluded member is present,
the original bytes MUST be copied unchanged. The native source MUST remain
byte-for-byte unchanged. Output MUST parse as TOML. Invalid TOML fails with
`environment_seed_unreadable` before the first provisioning write; a manager
MUST NOT fall back to a whole copy or silently skip the seed. Existing seed
absence, regular-file, read-failure and transaction rules remain in force.

Filtered revision-C serialization MUST be deterministic: repeated provisioning
from identical native input under the same adopted manager implementation MUST
produce identical seed bytes. This does not prescribe one canonical TOML
encoding across different implementations or versions, and does not relax the
decoded-value preservation requirement or existing-home byte guarantees.

Revision C retains B's `mcp_native_servers_not_inherited` warning and sorted
native-MCP-name snapshot, emitted exactly when that snapshot is nonempty.
Trust removal adds no diagnostic containing project paths, names, values or
config excerpts. This revision allocates no new trust-status diagnostic.

## 2. Ownership and legacy homes

Revision A remains the whole-copy legacy rule. Revision B remains the legacy
MCP-only exclusion rule: it retains project trust. A manager MUST NOT rewrite
either definition or reinterpret a B record as evidence that trust was absent.

Revision C MUST NOT migrate, refresh, strip or relabel an existing home's
seed or recorded seed revision on resolve, repair, update, switch, skill sync
or status. Native config changes do not refresh a seed. This applies to A,
B, C and pre-rule homes, even when a copied trust path is now missing.
Other independently required repair work remains permitted under its own
contract; the prohibition here covers seed bytes and seed-record identity.

After provisioning seeds are tool-owned. Legacy records contain no project
trust provenance: a copied entry and a later user-authored entry can have
identical bytes. A manager therefore cannot infer permission to delete one.
Re-provisioning is a separate explicitly requested lifecycle operation under
the existing home/backup rules, never an automatic repair or status action.

No profile-declared trust grammar or exception is admitted. In particular,
`codex_settings` remains empty-only under [its section 1](profile-codex-settings.md#1-closed-manifest-vocabulary-environments-section-2).
The [follow-up question](../UNRESOLVED_QUESTIONS.md#profile-declared-codex-project-trust)
requires a separately reviewed typed extension.

## 3. Marker and status

This amendment allocates complete `agent-environment-marker-v7`, the successor
of [marker 6](../schemas/local-setup-token-v1/README.md). Its only structural
changes are `version: 7` and the `codex_seed_record.revision` enum `A | B | C`.
All other fields, required members, closures and semantics remain unchanged,
including credential-source rules. It adds no project-path snapshot, trust
authority or package identity input. The [full schema](../schemas/codex-seed-c-v1/agent-environment-marker-v7.schema.json)
is mandatory; a member projection is not a substitute for carrier validation.

A C writer MUST publish marker 7 with recorded revision `C` when provisioning
the declared seed. Earlier marker schemas remain byte-unchanged and reject C;
an old reader MUST refuse an unsupported marker, never infer B semantics.
Marker 7 can retain A/B records during another independently required marker
publication. C adoption MUST NOT trigger a standalone marker upgrade, record
relabel or seed write on an existing home. Readers continue to support the
older adopted marker versions under their existing rules.

The `codex-seed` posture row reports the shipped revision, now also `C`;
per-home reporting uses the recorded revision. Under C, B/C records retain
their `mcp_native_servers_not_inherited` rows, and a nonempty A snapshot keeps
its ungoverned-name rows plus `mcp_seed_unstripped` and the re-provision hint.
An empty A snapshot does not warn about inherited servers. A pre-rule home
retains the existing unknown-snapshot warning. B under C adds no warning or
non-current verdict merely for the revision difference. Trust entries are
not enumerated, and neither status nor `--check` writes or repairs anything.

This amendment adds no JSON status field or carrier: the existing shipped
revision field admits C only for consumers adopting this amendment. Frozen
status vectors and their closed A/B readers remain unchanged. Unsupported
revision consumers MUST refuse, never silently downgrade C to B.

## 4. Conformance and limits

The [separate corpus](../conformance/codex-seed-c-v1/README.md) pairs excluded
trust entries with preserved unrelated settings, legacy A/B positives and
existing-home preservation witnesses. The production spec validator checks
the corpus and full marker successor, with narrowing controls in unit tests.
Frozen A/B schemas and vectors remain legacy evidence.

These are specification-data checks, not manager execution. Adopting managers
MUST independently test provisioning, source preservation, invalid-TOML
zero writes, existing-home byte/marker preservation and status read-only
behavior, with nearby positive controls and bounded narrowing mutants.
They MUST test repeated real serialization of the same filtered native input
for byte-identical output, and decoded preservation of unrelated nested tables
and arrays. The specification-data checker is not a TOML serializer and cannot
establish those manager execution properties.
They MUST use invented paths and disposable homes, never real trust files.
