# Protected command inventory schemas v1

These closed JSON Schema 2020-12 documents describe the new inventory, source
manifest, metadata and portable identity **subtree**. They do not add members to
any released environments lock. L1 owns the complete successor carrier.

[The protocol](../../protocol/protected-command-inventory.md) also requires CCJ-1
bytes, whole-artifact digest, source/class consistency, sorted distinct entry keys,
spellings and provenance, supported extractor/normalization, cleared entry sources
and immutable release authority. JSON Schema alone cannot prove these relations.
The [oracle and tests](../../tools/test_protected_inventory.py) enforce them with
the committed artifact. Missing/extra top-level fields have paired schema controls.

`inventory.schema.json` references `source.schema.json`; `artifact.schema.json`
references `identity.schema.json`. Supply a local registry of this directory's
`$id` values, never fetch schemas during a command check. See the
[data README](../../data/protected-commands/v1/README.md) for tools and reproduction.
