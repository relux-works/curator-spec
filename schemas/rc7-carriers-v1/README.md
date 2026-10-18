# Coordinated whole-carrier schemas

These complete closed Draft 2020-12 schemas implement the
[normative allocation](../../protocol/rc7-carriers.md). They are unreleased,
separate from `schemas/v1`, and preserve all old schemas byte-for-byte.

| Schema | Whole object |
|---|---|
| `manager-config-v5` | Configuration including the frozen machine selector subtree |
| `env-status-v1` | Full readiness matrix including frozen login rows and enclosing metadata |
| `agent-context-v2` | Context manifest with absent/empty-only package settings and optional skill directory |
| `context-lock-v4` | Lock with optional skill directory, precedence, effective `{}` and empty provenance |
| `agent-environment-marker-v5` | Marker recording effective `{}` and existing lock pin |
| `launch-env-fragment-v5` | All-adapter fragment with one Codex settings transport |

The schema filenames above carry `.schema.json` suffixes. Required fields,
exact discriminants and cross-field constraints are in each complete schema;
retained non-schema constraints are checked by `tools/rc7_carriers.py` through
the production spec validator. Frozen row/subtree and member schemas remain
inputs, never substitutes for enclosing validation. Version 4 fragments remain
unchanged, including their legacy payload; version 5 forbids that payload.
Snapshot descriptors remain separate. CIP-0021 extends only these unreleased
manifest/lock successors with skill-directory selection; published manifest 1
and locks 1–2 retain their original refusal. The [skill-directory corpus](../../conformance/profile-skill-directories-v1/README.md)
contains the successor schema cases and the schema-1 refusal control.

Run `python3 tools/rc7_carriers.py`,
`python3 -B -m unittest discover -s tools -p 'test_rc7_carriers.py' -v`, and
`make validate`. The [corpus](../../conformance/rc7-carriers-v1/README.md) states
what these structural/semantic publication checks do and do not establish.
