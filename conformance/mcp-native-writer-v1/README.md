# Profile MCP native writer model, revision 1

This separate corpus checks the
[normative adaptation sheet](../../protocol/mcp-native-writer.md) and its
[protected carrier shapes](../../schemas/mcp-native-writer-v1/README.md).
`cases.json` states each claim, synthetic observations and independently
specified expected rows/effects; `coverage.json` is the exact inventory.
No old vector, released schema or core/source manifest is rewritten.

Run `python3 tools/validate.py` for the production gate, or
`python3 -B -m unittest discover -s tools -p 'test_mcp_native_writer.py'` for
focused model/carrier checks and bounded Python narrowing controls. Output is
stdout; task logs belong in `.temp/`. `make validate` includes both checks.
No vendor executable, server, endpoint, authentication or package acquisition
is invoked. Cases return intended effects over supplied observations, always
`mutated: false`; they do not edit any filesystem or qualify a native writer.

The 18 cases deferred by the original Curator stage-A reader are mapped below.
The five dispatch cases belong to the unchanged project reader, rather than
an invented profile-native output path. Profile identity deliberately replaces
project identity only in the **separate** profile action namespace; it never
reinterprets a project approval as a profile approval.

| Original stage-A case(s) | Adaptation coverage |
| --- | --- |
| `foreign-entry` | `foreign-equal-*`, `foreign-different-*`, `markerless-*`, `marker-owner-missing-*` freeze Claude/Codex native paths and protected record ownership. |
| `unreadable-preimage` | `unreadable-read-*`, `unreadable-marker_read-*`, `codex-base-unreadable`. |
| `action-no-authority`, `action-policy-denied`, `action-authorized` | `action-no-authority-*`, `action-policy-denied-*`, `restore-*` beside ordinary `*-added` controls. |
| `action-replay-project_id` | `action-replay-profile_id-*`, `action-replay-scope-*`, `scope-project`; project records remain a distinct inadmissible namespace. |
| `action-replay-name`, `action-replay-server_sha256`, `action-replay-content_sha256`, `action-replay-policy_sha256`, `action-replay-operation`, `action-replay-state` | Same named binding witnesses per writable adapter. Extra environment/path binding witnesses prevent cross-home replay. |
| `action-repository-record` | `action-repository-record-*`, with protected restore controls. |
| `global-upgrade`, `old-reader-upgrade`, `version-1`, `version-2`, `version-4` | Retained in [the original corpus](../skillfile-mcp-v1/README.md). `schema1-no-effect` / `schema2-no-effect` additionally check no profile-writer effect for legacy inputs with no declarations; they do not parse or admit MCP fields in those schemas. |

Additional witnesses cover missing/edited owned bytes, approved replacement,
explicit cleanup/removal/release, qualified adapter/transport/version/platform
selection, Muse typed refusal, absent selectors, a mixed total-refusal plan,
and Codex seed A/B live-base collisions. The model preserves opaque foreign
spans and supplied base observations byte-for-byte. Native parsing, byte-span
extraction, protected provenance, symlink/race handling and crash recovery
remain **consumer obligations**, not claims of this synthetic model.

The marker control removes only `owner` from the actual ownership schema's
required fields. The foreign-entry control bypasses only the conflict gate.
Each must produce its named verdict mismatch, while valid first-install
controls continue to pass; an unrelated error or unapplied plant is no proof.
A further control removes marker publication from an otherwise valid native
install effect and requires the exact added-state witness to fail. These
Python controls are not the future production writer's native mutant batch. Consumer delivery must supply those controls at real entrypoints and
prove coherent recovery independently for each advertised adapter.

The review regressions add ten rejected-neighbor witnesses (unprotected,
wrong profile/environment/path and missing owner, for both writable adapters),
eight joint add/remove/release witnesses and the Codex DEL encoding witness.
Valid protected-neighbor cases sit beside rejected neighbors. Every review
witness is mandatory in the corpus inventory. Focused tests additionally check
unchanged-plus-added records, joint restores/replacements, partial cleanup,
conflicting ledger preimages and independent JSON/TOML parser round-trips for
all ASCII controls, quotes, backslashes and representative Unicode arguments.

Effects retain one entry per NAME/environment pair. When a home ledger changes,
all its effects carry the same final `ownership` value, while only the last
pair that changes ownership has `write_ownership: true`; this is one publication
for the ledger key, separate from each pair's native edit. An empty final ledger
is represented by `ownership: null`. Read-only sets do not publish a ledger.
Rejected neighboring ledgers contribute no records. Conflicting validated
preimages refuse the entire set with no effects. No refusal-free synthetic
plan establishes real protected-store provenance or transactional publication.

New bounded controls relax neighbor provenance/profile-binding/owner gates,
disable only ledger composition, and remove only DEL escaping. Each catches
the named review verdict mismatch beside its valid sibling; the DEL control
also reproduces the independent parser's intended rejection. Separate schema
controls remove only environment/path cross-field constraints, detect the
malformed envelopes, and verify the independent binding guard still prevents
adoption. A preimage control
bypasses only snapshot agreement and demonstrates the forbidden successful
plan. These controls run against the actual model functions.
