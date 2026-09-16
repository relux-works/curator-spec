# Unreleased source extension schemas

These Draft 2020-12 schemas belong to `skillfile-sources-v1` and the separately
scoped `repository-transport-v1` and `repository-transport-v2` amendments.
The directory is a draft namespace,
not a new protocol release. It keeps the rc.9 schema corpus and generated
release identities byte-frozen. The `v1` in this directory versions the
extension namespace; each wire object's filename and `schema_version` identify
its own revision. Existing core definitions are reused by relative references.

| Schema | Wire role |
|---|---|
| `skillfile-v2` | Project acquisition table and disjoint selectors |
| `skillfile-lock-v1` | Full frozen skill membership and package identities |
| `source-types-v1` | Shared selector and disjoint package identity definitions |
| `local-snapshot-v1` | Deterministic admitted-file inventory |
| `source-policy-v1` | Operator endpoint/auth policy and explicit root inputs |
| `source-policy-v2` | Revision 2 policy: explicit ports, `mirror_of` mirrors, operator host aliases |
| `install-marker-v5` | Installed package/lock identity and runtime/build references |
| `build-receipt-v3` | Package-bound wrapper around existing closed build inputs |
| `source-audit-v1` | Machine audit report binding, not a registry attestation |

The [source contract](../../protocol/skillfile-sources.md) defines semantic
requirements beyond schema checks: normalized repository identity, alias
existence, ref resolution, metadata, physical containment, root-input coverage,
member uniqueness, digest recomputation, lock-to-marker equality, audit report
verification and endpoint failure classification. The
[transport contract](../../protocol/repository-transport.md) defines the
independent machine connection policy. Schemas alone prove none of those
filesystem or authorization properties. Run the
[draft validation command](../../conformance/draft-sources-v1/README.md) in
addition to the existing suite.

Marker v5 retains v4 attestation and legacy substitution evidence with explicit
local/Git applicability. Its build records retain the complete local/external
field sets with receipt version 3. The exhaustive migration and currentness,
strict-audit, repair and refresh rules are in source contract section 4.
