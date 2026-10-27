# Effective posture paired conformance

This additive corpus accompanies [EPA01–EPA06 and EPA-C1](../../protocol/effective-posture.md).
It is not a released launcher schema or proof of provider admission.

- `fixtures.json`: full closed posture carriers and synthetic external authority
  observations. `0.0.0-fixture` and qualification fixture IDs identify future
  positive controls; **no real provider is certified**. Current binding values
  stand for independently admitted digest observations, not validated locks.
- `cases.json`: 26 adjacent admit/refuse pairs, each with an explicit independently
  specified expected reason. A branch selects a named fixture then applies only
  the listed `replace` or `remove` operations to its array-of-keys path. No reason
  is generated from the checker. Empty changes use the exact fixture.
- `default-yolo.ccj` and `golden.json`: canonical wire bytes, length and SHA-256.
  The record has no trailing newline. The separate identity is not a signature.
- [`test_effective_posture.py`](../../tools/test_effective_posture.py): paired
  canonical/schema rejections, independent literals for required counterexamples,
  currentness/provenance and checker control plants.

The first nine pairs cover all requested refusal families, with separate stale
lock and plan controls. Remaining pairs cover a permission/tools downgrade,
policy coverage/relaxations, missing lane approval, provenance substitution,
terminal/missing lease, provider qualification binding, suffix/policy drift,
source spoofing, unknown qualification, default consistency, isolation bypass,
honest incomplete yolo inspection and generation drift. A passing synthetic
strict/no-tools control is not permission to use an uncertified real adapter.

The launcher-state fixture follows proposed spec #194 at
`264275f35cd2a87aabb04952a1d48f5c27200224`; its hosted entry is a future negotiated
carrier fixture, not evidence the hosted provenance carrier exists. The home
lease uses merged #193's prepared shape and bare-hex lock field. The oracle
checks record identity/digest and the specified cross-record relations; the
owning #194/#193 validators, live ownership, authoritative observation and
safe publication remain consumer obligations. It never probes a provider,
reads real settings, loads credentials, changes configuration or launches a child.

Run from repository root:

```sh
python tools/effective_posture.py
python -B -m unittest discover -s tools -p 'test_effective_posture.py'
```

Outputs go to stdout. Capture task evidence under ignored `.temp/`. Existing
`make validate`/hosted unittest discovery automatically discovers this new test;
shared validators and frozen suites are unchanged. Oracle `posture_*` labels
are corpus categories; curator-run owns the stable public refusal codes/exits.
