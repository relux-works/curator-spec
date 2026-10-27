# Home-lease v1 conformance

The [normative protocol](../../protocol/home-leases.md) owns these unreleased
vectors. This is specification evidence, not a Curator/launcher implementation
or a grant to activate the capability. All fixtures are synthetic.

`schema-cases.json` pairs each rejected UTF-8/JSON payload with an accepted
control against one of the four [closed schemas](../../schemas/home-leases-v1/README.md).
Literal duplicate keys and invalid UTF-8 are preserved as raw text/hex; these
are not representable as already-decoded JSON objects. All success operations
and declared code/reason pairs have controls.

`cases.json` is a semantic entry-point matrix, not a wire request format or a
mock runtime oracle. Each HL01–HL24 requirement and W01–W18 writer has a negative
scenario, post-call preservation/forbidden observations and a nearby positive
control. Additional rows fix exact CLI exits/reasons for race, release, bind and
break boundaries. Text expectations name the required observable invariants;
structured expectations pin the explicit code/exit projection. A negative can
be a safe successful no-op (unknown release), with creation of a record/event as
the forbidden outcome. Pair IDs refer to protocol obligations, not case names.

Terminal acquire replay vectors separately cover released and broken leases:
zero manager calls, not-started op.json, launcher refusal carrying Curator's
terminal reason, and unchanged record/binding/tombstone/audit. Each is paired
with a still-prepared lost-reply replay or fresh admission under a new request ID;
both admitting controls require exactly one manager call. Shape pairs reject
terminal records labeled `acquired`, mismatched terminal outcomes, changed
terminal retrievals and terminal outcomes carrying historical prepared snapshots.
HL07 pairs require terminal refusal before historical bind replay success.

The data checker verifies schema/decoder verdicts and requirement/pair coverage.
It executes no manager, launcher, lock, process, recovery engine or home writer.
Later runtime qualification must drive each real writer/CLI and consumer path
with isolated manager/provider fixtures, not merely replay these expected labels.
Check exact refusal, empty resolve stdout and complete byte/link/mode/lock/marker/
backup/audit preimages immediately after each attempted call. Inspect lease state
and permanent events separately from journals. For races use real shared locks
and process barriers, not timeouts as proof of the intended holder refusal.

For multi-holder and batch cases verify each identity and every target, including
prepared/unknown and disjoint controls. Cross identity cases cover platform case
rules, canonical aliases and symlink-aware identity. Crash controls include lost
acquire reply, manager-start-before-bind, dead launcher with surviving descendants,
audit/ledger publication and both forward/rollback recovery. Pending/corrupt state
must not be mistaken for an empty namespace. Use synthetic credential fixtures;
lease diagnostics need no credential content.

Run:

```sh
python3 tools/home_leases.py
python3 -B -m unittest discover -s tools -p 'test_home_leases.py'
python3 tools/validate.py
```

The focused tests plant an accepted negative and a missing positive/requirement
and require the intended checker failure. They do not substitute for future
runtime guard-bypass/ignore-unknown/omit-digest control plants. Logs belong in
`.temp/`; no generated output is written to managed/provider state.
