# Managed-home snapshot conformance

This separate, unreleased corpus freezes CIP-0014 leaf-1 metadata, not archive
encoding or runtime behavior. Its authority is
[the snapshot protocol](../../protocol/managed-home-snapshots.md).
Released core and source-suite identities are unchanged.

`index.json` follows the repository's `{schema, instance, valid}` convention.
`vectors.json` names canonical golden `manifest.json` and `launch.json` bytes,
content files, exact SHA-256 identities and named semantic counterexamples.
The corpus manifest pins all corpus files, its schemas and normative input.
No credential, machine path or local identity is a fixture input.

## Checks and bounds

Run from the repository root:

```sh
python3 tools/validate.py
python3 -B -m unittest discover -s tools -p 'test_*.py'
```

The first command checks schema cases, exact bytes, digests, entry-set/mode
identity, descriptor references, portable/source-bound comparison and corpus
pins through its normal dispatch. The tests include narrowing controls and
prove the checker is invoked. Counters report measured cases, not manager
coverage. For reproducibility, metadata uses CCJ-1 plus one LF; `digests.json`
pins exact output bytes. The fixtures deliberately include an executable
skill asset and root, system and MCP content.

These commands execute **zero** real `curator env materialize`, hosted launch,
attach/resume, archive, dispatcher or runtime-protection cases. Destination
handles/ACLs, recovery refusal, concurrent capture, source-link protection,
secret detection and adapter qualification require the production entry tests
named in CIP-0014. Their future mutants M1–M11 are not killed by parsing this
corpus. Archive encoding/caps and runtime B confirmation remain open.
