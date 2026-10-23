# Local setup-token publication conformance

This T0 corpus exercises the [published metadata contract](../../protocol/local-setup-token-source.md).
`cases.json` contains independently stated command diagnostics beside valid
metadata controls; `controls.json` contains one positive object per schema.
`tools/local_setup_token.py` validates full schemas, retained whole-carrier
semantics, machine-only source policy and local binding/route witnesses.
`tools/validate.py` calls the checker during the normal repository gate.

| T0 requirement row | Named test | Narrowing mutant killed |
|---|---|---|
| ST-01 machine/package/lock/store/isolation | test_st01_authority_store_and_isolation | node-file-store |
| ST-06 migration/native preservation | test_st06_native_preservation_and_explicit_adoption | repair-migration |
| ST-07 closed carriers/local binding | test_st07_local_binding_and_required_understanding; test_st07_nested_unknown_source_diagnostic; test_st07_malformed_extension_typed_refusal; test_st07_review_regressions_reach_publication_gate; test_st07_unknown_carrier_discriminators_typed_refusal; test_repeated_semantic_regressions_reach_publication_gate | other-uid, stale-policy, unknown-node-branch, nested-unknown-source, null-required-extension, future-fragment-as-usage, future-marker-as-usage |
| ST-09 secret fields/snapshot exclusion | test_st09_secret_fields_and_closed_snapshots | source-secret-path, source-token-field, snapshot-source |
| ST-13 route/relocation evidence | test_st13_route_and_snapshot_are_not_authority; test_st13_unsupported_plan_route_typed_refusal; test_repeated_semantic_regressions_reach_publication_gate | direct-as-spawn, caller-present-as-qualified, direct-plan-route-as-usage |

Each negative asserts its exact diagnostic and unchanged input beside a
positive control. The checker has no secret-store or process-start interface;
these are publication/semantic checks, not proof of runtime no-read/no-write
behavior. No vendor, live credential, Keychain, network or user home is used.
Only disposable synthetic sentinel values occur in invalid fixtures.

The ST-07 regressions distinguish unknown source modes at every published
source location (including the fragment independently of the plan extension)
from malformed supported metadata. Unknown modes refuse
`credential_injection_unavailable`; null/scalar/list source containers and
required extension values refuse `usage` without exceptions. Valid node
siblings pass and every witness preserves its input. The corpus-entry test
adds both exact review witnesses through the production checker load seam;
the public CLI and repository gate use that same `check_corpus` entry point.
These are publication diagnostics, not runtime source admission evidence.

Whole-carrier discriminators (manager, status, marker, fragment and final-exec
plan) and unsupported routes inside the plan are classified before generic
shape validation. Unsupported revisions/routes refuse
`credential_injection_unavailable`; missing or wrong-kind discriminators/routes
remain `usage`. This includes standalone and nested fragment revisions and
integer-valued JSON version numbers. The repeated-review regressions preserve
all inputs and pair these refusals with valid siblings and malformed supported
metadata. Narrowing controls change only fragment v99, marker v99 or direct-only
route to the wrong `usage` diagnostic while retaining other semantic refusals.
They prove typed diagnostic coverage, not runtime authorization or delivery.

```sh
python3 tools/local_setup_token.py
python3 -B -m unittest discover -s tools -p 'test_local_setup_token.py' -v
python3 tools/check_local_setup_token_controls.py
python3 tools/check_local_setup_token_controls.py --plant secret
python3 tools/check_local_setup_token_controls.py --plant branch
make validate
```

Both `--plant` commands intentionally exit **1**: a forbidden token member or
unknown required source branch is planted into a valid disposable sibling,
while its expected verdict stays valid. The production publication checker
must fail with the intended error; then the unmodified sibling passes.
The mutant command exits 0 only when each applied narrowing mutation causes a
named assertion failure, without setup errors or skipped tests. It reports a
table with explicit survivor bounds, including any surviving mutations.

Coverage is 5/5 T0 ST rows and 11/11 schema families, each with positive and
negative controls. This is not 15/15 runtime ST coverage. The design's
ST-02–05/08/10–12/14–15 runtime filesystem, input, atomicity, readiness-reader,
conflict, leak/reload, revoke/expiry, login and error-classification obligations
belong to T1–T4 and remain unrun here. Snapshot tests cover closed descriptor
and manifest fields, not byte-level archive sanitation. The old containing
status is already structurally able to express node; the new v2 relation does
not establish qualification of old status readers. Arbitrary encoded secret
values in allowed strings remain a sanitation/qualification obligation.

## Proposed hosted-station witnesses

[`hosted-qualification-cases.json`](hosted-qualification-cases.json) accompanies
[proposed section 10](../../protocol/local-setup-token-source.md#10-proposed-hosted-station-qualification-amendment).
It pairs account/lock, destination-layout, false-isolation, generation/cutover
and post-revoke recovery counterexamples with valid controls. These are
neutral contract/test-plan fixtures, not a new wire schema or runtime results.
Review their expected behavior against section 10; parsing the JSON alone does
not execute any witness. Existing `cases.json` and the publication checker
continue to reject unsupported hosted routes and incorrect local bindings.

The commands above qualify the existing metadata corpus only. Synthetic
executor tests, real-harness leakage controls, owner-run OAuth enrollment and
the qualified station pilot are distinct later gates. No real continuity row,
credential, account, HOME or lifecycle operation is populated or executed by
these fixtures.
