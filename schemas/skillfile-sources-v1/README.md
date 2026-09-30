# Skillfile source and repository transport schemas

These accepted Draft 2020-12 schemas define `skillfile-sources-v1` and the
separately scoped `repository-transport-v1` and `repository-transport-v2`
revisions. This dedicated namespace keeps its extension schemas separate from
the established `schemas/v1` definitions. The `v1` in this directory versions
the extension namespace; each wire object's filename and `schema_version`
identify its own revision. Existing core definitions are reused by relative
references and remain unchanged.

| Schema | Wire role |
|---|---|
| `skillfile-v2` | Project acquisition table and disjoint selectors |
| `skillfile-lock-v1` | Full frozen v1-framed skill membership and package identities |
| `skillfile-lock-v2` | Current lock with required `hash_version: 2` for member content hashes |
| `source-types-v1` | Shared selector and disjoint package identity definitions |
| `local-snapshot-v1` | Deterministic admitted-file inventory |
| `source-policy-v1` | Operator endpoint/auth policy and explicit root inputs |
| `source-policy-v2` | Revision 2 policy: explicit ports, `mirror_of` mirrors, operator host aliases |
| `install-marker-v5` | Frozen v1-framed installed package/lock identity and runtime/build references |
| `install-marker-v6` | Current source-extension marker with required `hash_version: 2` |
| `build-receipt-v3` | Package-bound wrapper around existing closed build inputs |
| `source-audit-v1` | Frozen v1-framed machine audit report binding, not a registry attestation |
| `source-audit-v2` | Current audit report with required `hash_version: 2` |

The [source contract](../../protocol/skillfile-sources.md) defines semantic
requirements beyond schema checks: normalized repository identity, alias
existence, ref resolution, metadata, physical containment, root-input coverage,
member uniqueness, digest recomputation, lock-to-marker equality, audit report
verification and endpoint failure classification. The
[transport contract](../../protocol/repository-transport.md) defines the
independent machine connection policy. Schemas alone prove none of those
filesystem or authorization properties. Run the
[corpus validation command](../../conformance/skillfile-sources-v1/README.md) in
addition to the existing suite.

The v1 lock, marker and source-audit schemas remain frozen and mean framing
version 1. Current writers use v2 shapes and record `hash_version: 2`; readers
compare the version and digest together, and never equate a v1 identity with a
v2 identity.

Marker v5 retains v4 attestation and legacy substitution evidence with explicit
local/Git applicability. Its build records retain the complete local/external
field sets with receipt version 3. The exhaustive migration and currentness,
strict-audit, repair and refresh rules are in source contract section 4.
