# Unresolved questions

## Advanced repository mappings decided by transport revision 2

Non-default endpoint ports, operator-declared mirrors and operator-declared
host aliases are now decided normatively by [repository transport revision
2](protocol/repository-transport.md) (source-policy schema 2, additive over
schema 1). Ports are machine-policy endpoint properties stripped before
canonicalization; mirrors require an exact-key `mirror_of` attestation;
aliases resolve only from operator source-policy, never from user ssh/git
configuration.

## Still open: reusable alias registries and user-configuration import

Reusable cross-machine logical alias registries and safe translation of user
`insteadOf`/SSH configuration remain undecided and are rejected. Matching
content alone does not authorize identity equivalence, and user configuration
is usable only through explicit operator admission, unchanged from revision 1.

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

These credential/permission decision drafts are likewise **proposed —
not adopted** (TASK-260916-vht714, STORY-260916-1on1d2, from the
Fable-reviewed TASK-260916-2timlf design). Filing does not authorize
implementation, normative changes, workarounds, or draft landing.

- [Decision 0017: environment credential modes](decisions/0017-environment-credential-modes.md)
- [Decision 0018: curator run permission interface](decisions/0018-curator-run-permission-interface.md)
