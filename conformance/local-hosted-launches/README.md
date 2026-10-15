# Local hosted semantic cases

This normative corpus accompanies [Local hosted launches](../../protocol/local-hosted-launches.md)
§§1–2, 7–8 and CIP-0016's curator-spec leaf. It lives outside the frozen core
corpus and is not a hosted wire schema or an implementation capability claim.
No released manifest or schema is changed.

`cases.json` is a semantic selection table. Its input labels describe effective
host selection after existing host precedence/locks and valid configuration;
they are not launcher configuration members. Cross every case with each of
`claude_code`, `codex_cli` and `muse` (18 × 3 = 54 required observations).
For implementation qualification drive the real launcher selection entry point
and instrument receiver lookup; helper-only checks do not qualify execution.
The receiver is otherwise compatible and all unrelated policy checks pass.
Successful routing rows assume an already-qualified local release. A `refuse`
row MUST start no provider. Compare the expected route and lookup observation;
compare a diagnostic/exit only where specified. `null` on the two publication
refusals (unmigrated operator default and unimplemented dispatcher) means the
CIP has not selected the diagnostic/exit, never that the refusal can succeed.

`receiver_lookup` includes attempted lookup/contact, not successful delivery.
Terminal, network and piped-stdin gates precede preparation/contact. Attached
plan stdin is rejected after composition and before handoff; its `receiver_lookup: null` deliberately
does not assert a preparation-contact count. The corpus does
not model a combined invalid-input precedence or change current host locks,
permission resolution or native network semantics. Existing precedence and
lock tests must remain in the launcher suite.

Each `forbidden_observation` changes one required observation, with all other
inputs fixed. It MUST be rejected as nonconforming alongside the corresponding
positive control. Refusal rows forbid native fallback; successful native/ax
rows forbid receiver lookup; admitted local rows forbid dispatcher routing.
Unknown wire diagnostics are deliberately not assigned by this corpus.

Run the repository's existing Python specification-data tests:

```sh
python3 -B -m unittest discover -s tools -p 'test_local_hosted_launches.py'
```

The tests pin the table, all runtime rows and required/forbidden projections.
They execute no launcher, daemon or provider and prove no reservation, digest,
snapshot, process, resume or goal property. CIP-0016's Test plan retains those
real-entry-point property suites and proposed runtime narrowing mutants. It
requires versioned wire cases once publication questions are resolved,
including strict decoding and old/new compatibility; no invented wire samples
are supplied here. Test logs belong under `.temp/`.
