# Curator Protocol JSON Schemas v1

These Draft 2020-12 schemas are normative structural contracts. Semantic rules
that require filesystem, graph, cryptographic, ordering, or time context are in
the protocol documents and conformance vectors.

All `$id` values are stable identifiers. Relative `$ref` values resolve from
the containing schema. `common.schema.json` is a definition library and is not
a standalone wire object.

Schema examples and expected validation outcomes live under
`../../conformance/v1/schema-cases/`.

`agent-skill-v1.schema.json` through `agent-skill-v5.schema.json` are the
canonical skill-manifest schemas. The corresponding `csk-skill-*` schemas are
the unchanged legacy series retained for protocol 1.x readers.
