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
