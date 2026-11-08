# Machine Claude environment proposal corpus

This corpus is outside the frozen release manifest. It checks the
[proposed contract](../../protocol/machine-claude-env-proposal.md), not an
implementation or real runtime. Inputs are synthetic and contain no native
settings, environment dump or authentication material.

Run from the repository root:

```bash
go run ./tools/validate-claude-env -root .
go test ./tools/validate-claude-env
```

`cases.json` binds an independently stated claim, a real JSON Schema verdict
and a specific semantic verdict to each input. `plants.json` starts from a
valid declaration or contribution and introduces one defect per required
vector: unknown name, non-integer, zero, negative, over-bound and non-Claude
injection. Each plant must reach its intended refusal; its adjacent valid
control must pass. Tests also plant wrong corpus expectations to establish
that the checker detects a false acceptance and a false rejection, runs later
cases, and returns an aggregate failure.

The schema checks and semantic checks intentionally differ for duplicate JSON
members: JSON Schema sees a decoded object, while the strict byte decoder must
reject duplicates. Other refusal-class mismatches or setup failures are not
successful controls. The command prints only fixture IDs and stable codes,
never input values or raw parser/schema errors. This does not prove production
diagnostic redaction, no-write/no-child invariants or actual output spilling.

The future implementation must run the actual selected parser/editor/status,
projection, child launch/resume and real-runtime witnesses in contract section
5. No such runtime case is measured by this corpus.

Corpus metadata is itself a closed input: each case requires exactly `id`,
`claim`, `entry`, `input_json`, `want` and `schema_valid`; each plant requires
exactly `id`, `claim`, `entry`, `valid_json`, `invalid_json` and `want`. Field
names are case-sensitive. Duplicate (including escaped), missing, unknown,
case-variant or wrongly typed metadata fields, malformed/invalid-UTF-8 JSON and trailing
values refuse with fixed corpus-setup output. No last-wins decoding is allowed.
Paired command controls prove these refusals and nearby valid corpus loading.

## File-level diagnostic mapping and carrier setup

The member semantic code remains `claude_env_invalid`. When a declaration
vector is embedded in a containing configuration that is not strict JSON,
including duplicate decoded names, contract §4 maps the neutral diagnostic
`malformed JSON in config <path>` to that code. The five declaration vectors
`duplicate-name`, `escaped-duplicate-name`, `malformed`, `trailing-json` and
`trailing-comma` describe this mapping in their claims; their verdicts and the
six single-defect plants are unchanged. Invalid UTF-8 has the same strict-file
rule and remains covered by decoder tests. Member validation still uses its
fixed member path and code; unrelated containing errors keep their diagnostics.
Provider-discovery blocking depends on identifiable member declaration, not
rendered text. A synthetic checker result does not prove Core diagnostics or
that discovery behavior.

Before interpreting an embedded vector, an implementation declaration driver
must accept the same carrier with a valid member. An unrelated invalid carrier
is a setup failure and must not count as detection of any member defect.
`test_carrier_setup_control` checks a valid containing-schema control,
an unrelated unknown-field rejection and embedding of declaration cases.
The production driver must additionally verify the exact neutral file-level
form for strict-file failures; this repository executes no production driver.

## Containing-schema draft cases

`containing-cases.json` is a separate structural corpus with exactly `id`,
`claim`, `entry`, `input_json` and `schema_valid` per item. `entry` is
`configuration` or `launcher`. It covers the complete draft outer shapes,
predecessor selections/combinations, absent/empty/selected Claude declarations,
unknown containing fields, version mismatch and malformed predecessor arms.
Its schema verdicts are not additional `claude_env` diagnostic codes. Metadata
has strict closed admission controls alongside those of the member corpus. Paired
wrong-expectation plants must fail the actual checker aggregate and still run
later cases. None establishes exhaustive final-schema-8 preservation.

The [schema README](../../schemas/machine-claude-env-v1/README.md) lists what
waits for Core #216. Conditional allocation and draft fixture success do not
satisfy the unchanged pre-emission gate or permit Core #238 landing.

Predecessor negatives explicitly validate schema 8 and `/2` against the base
schemas: each refuses `claude_env`, paired with the identical carrier without
that member as a positive control (`schema8-control`, `launcher2-control`).
The checker compiles the containing schemas with the base integer-token profile;
plain JSON Schema alone does not distinguish integral decimal/exponent tokens.

The focused unit tests replay the reviewer plants on disposable schema copies:

| Plant | Required named failure |
| --- | --- |
| P1: schema-8 extensions admit `claude_env` | `schema8-claude-env-refused`, `launcher2-claude-env-refused`; paired controls still pass |
| P2: `/3` accepts config schema 8 | `launcher-old-config` |
| P3: v9 drops notification | `configuration-notification-host` and other notification vectors |
| P4: v9 drops build SSH | `configuration-unrelated-fields` |

Each changes the intended schema verdict and returns checker exit 1, rather
than a setup error; restored controls return 0. The declaration corpus keeps
the escaped `\u0668` spelling for the Unicode-digit fixture. Core consumers
must re-copy the intentional Q1 claim edits; no unrelated digit re-encoding
is required. Strict-file diagnostic names in the two corpora are one refusal,
as stated in contract §4.
