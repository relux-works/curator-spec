# Home-lease v1 schemas

These closed, unreleased Draft 2020-12 documents accompany the
[home-lease contract](../../protocol/home-leases.md). They do not extend frozen
release schemas or `project-lease/1` and do not advertise an implemented CLI.

| Schema | Object |
| --- | --- |
| `holder.schema.json` | Closed prepared/bound launcher holder; explicit null pre-bind fields |
| `record.schema.json` | Curator-authored record and diagnostic row, including terminal phase |
| `event.schema.json` | Permanent reconciliation/break audit projection with prior record |
| `result.schema.json` | Operation-specific CLI result, closed exit/code/reason mapping and details |

Identifiers are case-sensitive opaque ASCII `[A-Za-z0-9][A-Za-z0-9_.:-]*`,
1–128 bytes; no slashes or control characters. Canonical environment IDs,
launcher and kind tags are exact lowercase tokens, not case-folded aliases.
Times are UTC RFC3339 strings with at most nanosecond precision. Revisions,
generations and PIDs are positive safe integers. The CLI's strict decoder also
rejects duplicate keys, non-integer numeric spelling, invalid UTF-8 and lone
surrogates. Reason text is 1–1024 Unicode characters without controls; a whitespace-only
operator reason is rejected by semantic admission. Holder data is not evidence.

Cross-record identity/CAS, exact revision increments, event/tombstone agreement,
count/order, canonical actual home identity and observation provenance are semantic
requirements; JSON Schema alone cannot prove them. Result `holders` contain
blocking records only for a leased-home diagnostic, with count equal to rows;
`list` includes terminal records too. No negative shape case counts as runtime
lease/no-write proof. See the [paired corpus](../../conformance/home-leases-v1/README.md).

Run `python3 tools/home_leases.py` and the focused unittest command in the corpus
README. Normal `python3 tools/validate.py` invokes the same corpus checks.
