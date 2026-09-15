# Unresolved questions

## Advanced repository mappings (outside transport revision 1)

Custom ports, mirrors, SSH host aliases, reusable logical alias registries and
safe translation of user `insteadOf`/SSH configuration require a separate
identity and authorization design. Revision 1 rejects these forms; matching
content alone does not authorize identity equivalence.

No source extension implementation or release qualification is claimed. A
future release must assign publication metadata and qualify implementations
against the new schema and semantic vectors before advertising support.
Prebuilt binary distribution, compiler bootstrap, broader context/plugin/MCP
imports and toolchain-family reconciliation remain outside this amendment.

## Filed proposals

These B7 decision drafts are **proposed — not adopted**. Filing does not
authorize implementation, normative changes, workarounds, or draft landing.

- [Decision 0014: tool-configuration surfaces](decisions/0014-tool-configuration-surfaces.md)
- [Decision 0015: per-project policy and profile selection](decisions/0015-per-project-policy.md)
- [Decision 0016: skill command roots in managed homes](decisions/0016-managed-home-command-roots.md)
