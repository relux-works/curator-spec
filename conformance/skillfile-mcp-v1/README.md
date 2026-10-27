# Project Skillfile MCP stage-A conformance

This separate namespace follows the
[normative stage-A contract](../../protocol/skillfile-mcp.md) and
[closed runtime-pin sheet](../../protocol/mcp-runtime-pins.md), with
[versioned schemas](../../schemas/skillfile-mcp-v1/README.md).
It changes no released core/source corpus or candidate pin.

The specification gate is `python3 tools/validate.py`; the focused unit gate is
`python3 -B -m unittest discover -s tools -p 'test_skillfile_mcp.py'`.
`cases.json` carries claimed positive/negative witnesses and named verdicts;
`coverage.json` records their complete inventory. Planning cases supply
synthetic package, audit/policy and native preimage observations. They do not
attest that a real resolver, audit backend or native writer established those
facts. Carrier cases check structure and semantic binding, not protected
storage. Unit controls narrow the actual specification checker, with intended
verdict mismatches rather than unrelated setup failures.

Stage A cannot exercise `mcp_inline_approval_required` or
`mcp_install_option_invalid`: every inline arm refuses unsupported even against
a forged approval, and every install option is ignored. Those later-stage
codes/inline carrier namespace remain reserved. The existing upgrade error is
represented as `upgrade_required` in these model vectors, not a new protocol
spelling replacing a manager's existing error.

Consumer qualification must separately exercise real install/preview/status,
exact locked snapshot replay, current protected approvals/ceilings, per-entry
ownership, lossless edits, failed reads, no-follow/race guards, rollback,
removal/drift decisions and total reporting. Use disposable homes and tripwire
runtimes/endpoints: no server, package runtime, auth or endpoint may be invoked.
A successful native write never proves CIP-0002 managed-launch admission.
Claude, Codex and Muse are the first adoption wave; no adapter/platform/version
is qualified by this specification corpus.

Review regression witnesses separate legacy package byte ceilings from inline
scalar limits for command, argument and URL; both planning and fully rehashed
locks are checked beside valid byte-bound siblings. Lock selectors cover exact
revision/OID-width and range/prerelease consistency. Raw negative zero is
rejected inside ignored options beside zero and negative-integer controls.
Existing source-signature/version/allowlist diagnostics have exact refusal rows
and closed-carrier valid/unknown-code siblings. Unit narrowing plants relax
individual byte, selector, parser and source gates and reproduce the old closed
enum; each must fail its named witness while valid controls still pass.
Full-document CCJ-1 manifest identity is tested independently of MCP
normalization, with whitespace/key-order, semantic-edit and faulty-canonicalizer
controls. These checks do not establish external source or protected authority.

Leaf-1 review follow-up also closes inherited final-LF schema matches. The
stage-A oracle builds a private catalog with shared true-end guards while
preserving released schema bytes. Eleven schema-boundary witnesses pair valid
siblings with actual field-specific guard-removal plants and an unrelated
unknown-field refusal. Existing lexical negative-zero cases now exercise the
same shared integer hook used by the leaf-1 decoder.

Re-review R6–R8 adds seven fully rehashed carrier final-LF witnesses, four
intermediate-component dot/space lock/plan witnesses, and four oversized signed
integer witnesses across text and UTF-8 bytes, each beside a valid sibling.
Planning cases with `raw_bytes: true` encode their stored `raw` string as UTF-8
before evaluation. Two adjacent package-directory refusals exercise admission
through the same shared portable-path primitive. Integer controls verify both
pre-conversion token bounds and the exact typed-refusal mapping; they never
disable the interpreter's integer digit guard. These are specification grammar
checks, without filesystem or manager qualification.
