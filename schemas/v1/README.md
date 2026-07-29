# Curator Protocol JSON Schemas v1

These Draft 2020-12 schemas are normative structural contracts. Semantic rules
that require filesystem, graph, cryptographic, ordering, or time context are in
the protocol documents and conformance vectors.

All `$id` values are stable identifiers. Relative `$ref` values resolve from
the containing schema. `common.schema.json` is a definition library and is not
a standalone wire object.

Schema examples and expected validation outcomes live under
`../../conformance/v1/schema-cases/`.

`agent-skill-v1.schema.json` through `agent-skill-v7.schema.json` are the
canonical skill-manifest schemas. The corresponding `csk-skill-*` schemas are
the legacy filenames with byte-equivalent versioned meaning.

Manifest schema selection is exact: the integer `schema_version` selects the
same-numbered schema. Schemas 1 through 6 do not acquire schema-7
`build_repositories` or `go-repository-v1` meaning. Schema 7 adds those fields
without changing the earlier schemas or their generated fixtures.

The external-repository wire family is:

- `skill-build-v1.schema.json` for repository-root logical targets;
- `skillfile-dev-v2.schema.json` for operator-only source substitutions;
- `build-receipt-v2.schema.json` for declared and effective repository input;
- `install-marker-v3.schema.json` for local, external, and mixed builds; and
- `conformance-claim-v3.schema.json` for rc.5 platform and language-driver
  assertions.

Both compiled-build policies carry a REQUIRED `execution_policy` bound to the
single closed constant `manager-worker-v1` in `common.schema.json`. Marker-v3
build records and claim-v3 driver assertions carry the same constant. Marker v2
keeps its frozen rc.4 shape and binds the execution policy transitively through
its recorded cache key and receipt hash.

Cross-field constraints that Draft 2020-12 cannot express, including selected
repository existence, `source_dir` containment, declared/effective equality,
mixed-marker top-level `build_source` presence, and the requirement that a
receipt cache key is the CCJ-1 digest of the input that carries its execution
policy, are enforced by `tools/validate.py` and covered by deterministic
generated cases.
