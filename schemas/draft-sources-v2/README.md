# Draft source namespace schemas (draft-sources-v2)

These unreleased Draft 2020-12 schemas define the manifest schema-9
dependency-directory amendment on top of the accepted
`skillfile-sources-v1` extension. This directory is a draft namespace, not a
new protocol release: the accepted `schemas/skillfile-sources-v1` and
`schemas/v1` corpora stay byte-frozen. Existing core and accepted-extension
definitions are reused by relative references
(`../v1/...` and `../skillfile-sources-v1/...`).

| Schema | Wire role |
|---|---|
| `install-marker-v6` | Marker v5 shape recording manifest schema 9 for subfolder installs |
| `agent-skill-v9` / `csk-skill-v9` | Opt-in manifest directory selection for transitive skill dependencies |

The [source contract](../../protocol/skillfile-sources.md) and
[core section 4.4](../../protocol/core.md#44-dependencies) define semantic
requirements beyond schema checks: the shared directory grammar, containment,
package identity, closure unification, lock and audit binding. Schemas alone
prove none of those filesystem or authorization properties. Run the
[draft validation command](../../conformance/draft-sources-v2/README.md) in
addition to the existing suites.

Marker v6 is marker v5 with `schema_version` 6 and `skill_schema_version`
through 9; it records schema-9 installations and changes nothing else.
Accepted marker v5 stays frozen with manifest versions through 8, so it
cannot record version 9.
