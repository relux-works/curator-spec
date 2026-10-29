# Muse invocation-policy specification data

This separate corpus accompanies [environments §10.2](../../protocol/environments.md#102-the-launch-environment-fragment),
[CIP-0017's dated amendment](../../cips/CIP-0017-muse-root-context-and-credential-store.md#invocation-policy-amendment-2026-10-29)
and [Draft Decision 0035](../../decisions/0035-muse-invocation-context-policy.md).
Canonical review, checks, signing and publication remain gates. No frozen schema,
released vector, manifest, fragment revision or default-strict argv fixture changes.

`vectors.json` is specification data, **not a public wire schema or mock runtime**.
`choice`, route, position and spelling labels are corpus metadata, not allocated
API members, flags, native grammar or diagnostic codes. `permit-declaration`
means the declared expected result is consistent with the requirement, not that
a launch ran or is admitted. Digest/provenance values are neutral synthetic
binding labels, not hashes computed over the example fragment or authenticated
manager attestations. `/fixture/` paths name no actual home or credential store.

The closed cases declare strict defaults and exact exclusion projections,
explicit interactive MIXED without enabling argv/cached `true`, each forbidden
route, absent/invalid fact, unchanged complete fragment/profile identity, and
unsupported/dropped/replaced policy/capability/fidelity on both dispatch routes.
Argument metadata covers each personal rules/skills dimension, combined switches,
equivalent joined/separated configuration labels and alternate option positions,
form switches, opaque data and unknown/unparseable semantics. Every argument row
applies to both choices and both permission modes in `argument_matrix`; this
declares invariance, not executed native combinations. Refusal rows must never
be reclassified as MIXED or successful strict fallback.

There are 43 selection, 2 identity, 29 argument and 14 fidelity declarations
(88 rows). Selection metadata `selector_source` describes an attempted source,
not a runtime/configuration field: `none` means no explicit or competing selector;
`explicit` identifies an invocation choice; environment, configuration, profile,
permission-yolo and default labels describe attempted inherited allowance with
no explicit choice. Each inherited row stays strict on interactive/exec/dry-run,
with the existing exact form argv. Explicit alias/unknown strings, booleans,
numeric zero/one, empty string and explicit null refuse with effective null.
An explicit null declaration is distinct from outer-option absence; neither is
coerced into allowance. Exact strict/allowance controls remain adjacent coverage.
These rows pin the selector boundary as specification data, not native parsing.

The checker independently fixes required case inputs, coverage and expected
declarations from §10.2, rather than trusting a fixture-supplied success label.
It compares complete original/retained identity, including raw fact, full
fragment, profile/lock, env/backend, provenance and whole-fragment digest.
Duplicate JSON declarations and extra/missing corpus members are rejected.
It constructs no argv or process, guesses no native grammar and simulates no
provider. Real parser behavior, opaque-data recognition, precedence/loading,
capability/fidelity, `ChildEnv`, seal/final execution and all native behavior
remain **unverified**. The unchanged historical argv corpus is the default-strict
specification control; neither data checker qualifies a runtime.

Run the focused commands from the repository root with Python 3/std-library only:

```sh
python3 -B -m unittest discover -s tools -p 'test_muse_invocation_policy.py' -v
python3 -B -m unittest discover -s tools -p 'test_muse_launch_argv.py' -v
```

Existing CI's `test_*.py` unittest discovery includes the new checker without a
workflow change. For isolated local runs, provide only an allowlisted child
environment with an absolute owned scratch HOME/XDG/temp tree and no inherited
Git, SSH/auth or provider selectors; never retarget the running worker. Logs and
disposable known-violation copies belong under task-local `.temp/`. Bounded
controls must change only disposable corpus copies, retain unchanged positive
controls and record the named intended failing assertion and real nonzero exit.
No skipped plant, setup error or unrelated crash is detector evidence. Full
schema/determinism/link/cross-implementation CI remains a separate actual gate.
