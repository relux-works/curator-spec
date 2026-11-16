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

## Independent bind observer (observation v2 d5)

The unreleased holder revision follows accepted d5 §§3/6, SHA-256
`82ed29271b60db5712793a9874b7e2f3d7425cc8c88cb26e8d8ebdf0e902bac4`.
Existing bound controls now carry the exact four-field process; original pair
names and unrelated refusals are retained. New `observer-*` schema pairs cover
prepared-only legacy parsing, bound tuple closure, both tagged variants, integer
ranges, lowercase boot UUIDs and decimal-string grammar/boundaries. Each negative
has a valid nearby control, including zero and 20-digit decimal strings.

`cases.json` adds HL07 semantic pairs with stable IDs at the start of negative
`setup`. Every `observer-linux-*` case has a matching native Linux control;
every `observer-darwin-*` case has a matching native macOS control. A successful
control independently reads every kernel field and binds the equal tuple at the
acquired revision. Every refusal preserves the blocking record/revision,
acquisition binding, ledger/audit preimages, other holders and home contents;
it forbids a bound publication, successful bind reply, productive input and
implicit release/break, including on retry/replay.
Negative expectations are closed `{exit, code, reason, stdout_fragment, changed}`
projections of the protocol's observer refusal rows: exit 1 for mismatch or
unavailable authority, exit 2 for malformed bound data. Positives pin exit 0,
null code, `bound` and `changed:true`. A refusal object is JSON stdout, not a
resolve fragment; `stdout_fragment:false` does not mean empty JSON stdout.

| Suffix after `observer-linux-` or `observer-darwin-` | Required negative |
| --- | --- |
| `pid-mismatch` | Independently read PID differs. |
| `pid-reuse-within-boot` | Same PID/boot, different birth time. |
| `pid-reuse-across-boots` | Same PID/birth time, different boot UUID. |
| `wrong-real-uid` | Only the independently read real uid differs. |
| `manager-record-agree-kernel-disagrees` | Manager tuple equals its authoritative record and requested holder, but Core reads a different start time; **REFUSE**. |
| `record-kernel-agree-holder-disagrees` | Record/observation and Core agree, but the curator-run holder differs; **REFUSE**. |
| `holder-kernel-agree-observation-disagrees` | Holder and Core agree, but the authoritative observation differs; **REFUSE**. |
| `observation-unavailable` | The read-only v2 observation fails or is unavailable; a matching holder/kernel pair cannot replace it. |
| `start-time-hz-mismatch` (Linux) / `start-time-usec-mismatch` (macOS) | The remaining member of the tagged birth identity also must match. |
| `vanished-pid`, `unreadable-*` | Vanished PID or any unreadable tuple/variant field refuses despite cached manager/record agreement. |
| `missing-process` | Valid observation without process means unknown; never bind or release. |
| `unsupported-kind`, `unsupported-native-variant` | Reject an unknown tag and a known but unsupported opposite-platform variant; never coerce. |
| `legacy-process-cannot-bind` | Prepared legacy data stays parseable but a legacy bound holder refuses. |

Linux additionally requires `incarnation-changed-pid`,
`incarnation-changed-start-time` and `incarnation-changed-boot-id`: a change
during the single stat/status/stat and boot pass refuses, even if mixed readings
would match. `stat-comm-last-parenthesis` pairs an unparseable/truncated stat
refusal with a matching valid stat whose `comm` contains spaces and `)`.
Field 22 is the twentieth suffix token after the last `)`, never a token from
splitting the whole line. The checker inventory pins 23 Linux and 19 macOS rows.

These semantic rows specify later real-observer obligations. The current checker
checks exact row inventory, closed refusal/positive decisions, preservation and
replay invariants, in addition to HL/W coverage. It checks no kernel reads or
runtime verdicts. Missing, duplicate or weakened rows fail on the named case.
The manager-record disagreement row is not qualified merely by agreeing with its
expected label. Linux/macOS runtime tests, skipped-start-time-comparison control,
real launcher/proving-manager docking and M3 evidence belong to implementation
qualification. No release rule or productive-input authority is added here.

## Checker and runtime evidence limits

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
and require the intended checker failure. `test_observer_semantic_contract`
also rejects dropped/duplicated observer rows, a success in Core's negative,
wrong reasons/exits, refusal writes and missing positive/preservation/replay
controls. Corpus floors are 198 schema pairs and 110 semantic pairs. Changing
Core's negative to success must fail `make validate` at that row. Non-ASCII tail
digit pairs (`"1\u0661"`) independently guard `[0-9]` after the first digit.
These checks do not substitute for future
runtime guard-bypass/ignore-unknown/omit-digest control plants. Logs belong in
`.temp/`; no generated output is written to managed/provider state.
