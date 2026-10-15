# Managed-home snapshot schemas

These additive closed schemas implement
[CIP-0014 leaf 1](../../protocol/managed-home-snapshots.md). They do not alter
released `schemas/v1` bytes or claim manager/launcher support.

- `managed-home-snapshot-v1.schema.json`: source-bound manifest and portable
  regular-file inventory; file paths include `home/`.
- `snapshot-launch-v1.schema.json`: relative-home descriptor, preserving the
  existing precedence, permission and channel shapes; the optional Muse
  `root_context: {"exclusive": true}` is coordinated with CIP-0017. This is
  not a fragment revision. Exact env maps are closed per adapter.

JSON Schema validates structure. The normative protocol additionally requires
sorted unique paths, collision/ancestor rejection, full byte/size/mode
correspondence, adapter/profile binding, canonical LF framing and declared
channel references in the inventory. No schema asserts syscall safety,
authorization, secret freedom or runtime protection. Opencode's shape is
reserved; successful materialization remains unsupported.

Run `python3 tools/validate.py` and
`python3 -B -m unittest discover -s tools -p 'test_*.py'` from the root.
Cases, exact metadata bytes and semantic counterexamples live in the separate
[conformance namespace](../../conformance/managed-home-snapshot-v1/README.md).
