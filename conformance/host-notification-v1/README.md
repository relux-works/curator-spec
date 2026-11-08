# Draft Host notification conformance

Review-only separate corpus; not added to frozen release manifests.
[Contract](../../protocol/host-notification-proposal.md) and
[schemas](../../schemas/host-notification-v1/README.md) define the proposed rules.

`cases.json` records strict input JSON, entrypoint and exact stable code/path.
It covers absence/off/Host controls, both auth stores with proxy, old-schema
refusals, containing versions and fields, system supply/lock boundaries,
reference/digest bounds, duplicate/escaped duplicate/trailing JSON and envelope
pairing. `edit-cases.json` pins required env/project/auth preservation states;
it is a contract fixture, not an executed editor roundtrip.

Run `python3 -B tools/host_notification.py` for schema and selection semantics.
Run `python3 -B -m unittest discover -s tools -p 'test_host_notification.py' -v`
for strict decoding, checker false-verdict controls, editor downgrade witnesses
and isolated intended-reason plants. The same corpus is dispatched by `tools/validate.py`.
Each process must run with scrubbed Git/SSH/XDG/runtime selectors, disposable
absolute HOME and a deadline at most 600 seconds; keep logs under `.temp/`.

| Plant | Named witness | Intended detection |
| --- | --- | --- |
| Admit notification in schema 7 | `schema7-admit` | `launcher_selection_invalid` at `extensions` must not become admission |
| Admit extra Host fields | `host-extra` | Same selection refusal must not become admission |
| Admit extra off fields | `off-extra` | Same selection refusal must not become admission |
| Drop workflow-reference newline guard | `reference-newline` | Selection refusal must not become admission |
| Admit uppercase digest | `uppercase-digest` | Same selection refusal must not become admission |
| Relax environment list/object members to admit null | `env-provider-directories-null-7/8`, `env-source-signers-null-7/8` | Shape refusal must not become admission; paired list/object controls pass |
| Revert Core name-first precedence | `precedence-unknown-9`, `precedence-unknown-8`, `precedence-unknown-1` | All three must remain shape refusals |
| Emit `/1` in schema-8 envelope | `projection-8` | Valid `/2` control must not become `launcher_projection_invalid` at `schema` |

Plants mutate copied schemas, compile them, require the exact changed verdict,
then require aggregate failure naming that witness. Setup failure or any unrelated
crash does not count. Restored controls pass. Published schema-5 configuration
fixtures provide exactly one independent valid predecessor migration control:
`config-valid.json`; the other four `config-*.json` files are invalid controls.
Coverage is
bounded, and no assertion of exhaustive production equivalence follows.

The source review's five Core plants are evidence from a different instrument;
these schema plants independently protect the corresponding proposed rules.
This corpus executes no Core/launcher binary, real editor, receiver or runtime,
and does not establish old `/1` byte equality or Host workflow authorization.

The reviewer's original Core-order plant E is now the required passing control;
reverting to the previous version/extension-first order must fail the three
mixed-defect witnesses. A correct-order control cannot honestly be called a
killed mutation. The regression plant shows the old order is now detected.

Version vectors require integer tokens; the checker compiles schemas with the
strict integer-token profile documented in contract §3. Decimal/exponent
integral versions are a declared Core divergence. Path vectors use a fixed
POSIX target, with explicit Windows helper controls. Relative and unclean
projection paths are declared launcher #92 divergences. Edit fixtures include
auth changes, a non-writing plan with a changed planned result, stale apply
and restore refusals preserving the current state, 2→7 and 7→7 transitions.
They assert per-member invariants and still execute no real editor.
