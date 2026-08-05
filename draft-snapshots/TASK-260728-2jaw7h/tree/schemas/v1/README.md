# Curator Protocol JSON Schemas v1

These Draft 2020-12 schemas are normative structural contracts. Semantic rules
that require filesystem, graph, cryptographic, ordering, or time context are in
the protocol documents and conformance vectors.

All `$id` values are stable identifiers. Relative `$ref` values resolve from
the containing schema. `common.schema.json` is a definition library and is not
a standalone wire object.

Schema examples and expected validation outcomes live under
`../../conformance/v1/schema-cases/`, except for the schemas whose surface is
minted but not yet released — `agent-skill-v8`, `csk-skill-v8`,
`skill-build-v2`, and the three manager-owned `toolchain-*` documents — whose
cases live under `../../conformance/next/schema-cases/`. Both roots are
validated identically; only the released one is pinned by a release document.

`agent-skill-v1.schema.json` through `agent-skill-v8.schema.json` are the
canonical skill-manifest schemas. The corresponding `csk-skill-*` schemas are
the legacy filenames with byte-equivalent versioned meaning.

Manifest schema selection is exact: the integer `schema_version` selects the
same-numbered schema. Schemas 1 through 6 do not acquire schema-7
`build_repositories` or `go-repository-v1` meaning. Schema 7 adds those fields
without changing the earlier schemas or their generated fixtures. Schemas 1
through 7 do not acquire the schema-8 `toolchain` requirement and reject it;
schema 8 adds that one member to both build commands and changes nothing else.

The external-repository wire family is:

- `skill-build-v1.schema.json` for repository-root logical targets;
- `skillfile-dev-v2.schema.json` for operator-only source substitutions;
- `build-receipt-v2.schema.json` for declared and effective repository input;
- `install-marker-v3.schema.json` for local, external, and mixed builds; and
- `conformance-claim-v3.schema.json` for rc.5 platform and language-driver
  assertions.

The toolchain family is:

- `toolchainRequirementV1` in `common.schema.json`, the one closed requirement
  object all three wire slots reference by `$ref` and never inline;
- `skill-build-v2.schema.json` for a descriptor target carrying it optionally;
- `toolchain-registry-v1.schema.json` for the manager-owned driver-to-toolchain
  registry, its per-operating-system relpaths and probes, its tested-family set,
  and its closed source-metadata disposition tables;
- `toolchain-guidance-catalog-v1.schema.json` for the manager-owned, revisioned
  installation guidance; and
- `toolchain-diagnostic-v1.schema.json` for the twelve diagnostics as a
  discriminated union keyed by firing site.

The registry and the catalog are manager policy documents rather than wire
objects: no package can supply, extend, or override either, and neither enters a
build input, a cache key, a receipt, a marker, or a claim.

Both compiled-build policies carry a REQUIRED `execution_policy` bound to the
single closed constant `manager-worker-v1` in `common.schema.json`. Marker-v3
build records and claim-v3 driver assertions carry the same constant. Marker v2
keeps its frozen rc.4 shape and binds the execution policy transitively through
its recorded cache key and receipt hash.

Cross-field constraints that Draft 2020-12 cannot express, including selected
repository existence, `source_dir` containment, declared/effective equality,
mixed-marker top-level `build_source` presence, the requirement that a receipt
cache key is the CCJ-1 digest of the input that carries its execution policy,
the equality of a requirement's `id` with the driver's registry primary
toolchain, and the strict ordering of a `range`'s own bounds, are enforced by
`tools/validate.py` and covered by deterministic generated cases. The last two
are deliberately not schema rejections: both are
`build_toolchain_requirement_invalid` at the validation stage, with the closed
violation tokens `id_not_primary` and `range_bounds_not_ordered`.
