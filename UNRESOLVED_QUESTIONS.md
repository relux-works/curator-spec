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

## Adopted decisions

These credential/permission decision drafts are **adopted** (operator
decision 2026-09-21, TASK-260921-3qcjsy, STORY-260921-3z0fgr; design
input the Fable-reviewed TASK-260916-2timlf work). Adoption records
the selected options and the resolved choices in each document; the
normative amendments land with the adoption, and the remaining
implementation and spec-revision work is tracked in named follow-up
leaves.

- [Decision 0017: environment credential modes](decisions/0017-environment-credential-modes.md) — adopted 2026-09-21: options 1–3 as recommended, open questions 1–7 resolved.
- [Decision 0018: curator run permission interface](decisions/0018-curator-run-permission-interface.md) — adopted 2026-09-21 with the 2026-09-16 amendment (TASK-260916-2fu85y, rev 2 after review): config-driven mode, interactive default `yolo` / headless default `native`, force-`native` lock, fail-closed legacy transport; open questions 1–7 resolved.

## Filed proposals

These B7 decision drafts are **proposed — not adopted**. Filing does not
authorize implementation, normative changes, workarounds, or draft landing.

- [Decision 0014: tool-configuration surfaces](decisions/0014-tool-configuration-surfaces.md)
- [Decision 0015: per-project policy and profile selection](decisions/0015-per-project-policy.md)
- [Decision 0016: skill command roots in managed homes](decisions/0016-managed-home-command-roots.md)
