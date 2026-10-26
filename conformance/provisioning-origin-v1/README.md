# Provisioning-origin/1 conformance

`schema-cases.json` contains complete private record positives and negatives.
`authority-cases.json` pins expected Codex file-credential authority for custom
A under current selector B, retarget conflict, absent-link repair, missing
records and exact binding mismatches. Paths and values are invented fixtures.

Run `python3 tools/provisioning_origin.py`, `python3 tools/validate.py` and
`python3 -B -m unittest discover -s tools -p 'test_provisioning_origin.py' -v`.
The unit tests plant wrong authority and disabled schema admission through the
real publication entry and require the intended refusal with valid controls.
Logs belong in `.temp/`.

These checks establish grammar and expected-authority projection only. They
perform no native filesystem inspection, transactions, credential reads, CLI
adoption, cache qualification or runtime execution. Implementation tests must
exercise all lifecycle, concurrency and fault-injection obligations in the
[normative amendment](../../protocol/provisioning-origin.md#5-conformance-and-limits).
