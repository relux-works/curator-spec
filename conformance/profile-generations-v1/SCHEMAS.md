# Profile generations: closed conformance meta-schemas

These unreleased Draft 2020-12 meta-schemas live beside the
[corpus](README.md), following the startup corpus layout. They validate
conformance metadata only. Every data object is closed and bounded.
Strict UTF-8 and duplicate JSON-member rejection additionally require an
appropriate parser; JSON Schema alone cannot enforce either.

| File | Shape and bounded correspondence |
| --- | --- |
| `pairs.schema.json` | Exactly 48 ordered pair IDs through per-position constants; known clause/gate IDs; explicit meta classification, paired extensions and relative input paths; all stubs/not-run |
| `a1.schema.json` | Ten bounded textual branches, fixed parent and exact contract/vector provenance constants; not an execution oracle |
| `reuse.schema.json` | Bounded relative input paths, Git blob/SHA-256 strings and unique complete entries |

Repository-relative paths reject absolute/drive paths, parent traversal,
backslashes and control characters. `pairs.schema.json` rejects a duplicate ID
even if its other fields differ, because each position has one fixed ID.
`reuse.schema.json` rejects duplicate complete entries; distinct objects naming
the same path with different hashes additionally require semantic uniqueness
checks. Shape alone does not check file existence, correct hashes, exact A1
wording, all trace links or the meaning of an expected outcome.

No production audit-record, exchange, generation, control, holder, fragment,
session or receipt schema is allocated. The corpus directory and schema IDs
reserve no production carrier/version. Those closed shapes and numerical
allocations remain the chapter's named P gates. See the
[chapter](../../protocol/profile-generations.md) and the
[external-check disclosure](README.md#validation-boundary).
