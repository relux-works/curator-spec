# Codex seed-C conformance witnesses

This separate unreleased corpus implements the [normative amendment](../../protocol/codex-seed-c.md).
`cases.json` uses synthetic TOML input and expected output. The path labels
foreign, missing, existing and symlink describe required implementation cases;
this data checker does not create or inspect those paths. All four are
excluded unconditionally, paired with preserved model/TUI settings.
The 22-case inventory includes a filtered positive preserving unrelated nested
tables, scalar arrays, inline-table arrays and arrays of tables, including a
nested member named `projects`. Its paired unit controls mutate array elements
and require the production checker to reject the exact preservation violation.
Repeated real filtered serialization must produce identical bytes under the
same adopting implementation; these data witnesses do not execute a serializer.
Other controls cover empty config/projects, MCP exclusion and warnings, legacy A/B
provisioning, invalid TOML and no-write repair/status for pre-rule and A/B/C
records. Expected existing-home config bytes must match the input exactly.
The `diagnostic` field is the primary warning/error, not an exhaustive status
row inventory; legacy A ungoverned-name rows remain covered by the frozen
A/B posture corpus. `writes` names managed-home paths only, never native paths.

The checker validates complete marker 7 positives, full old-carrier B/C controls,
unknown revisions/fields, unrelated settings restrictions and predecessor
schema identity. Unit tests deliberately narrow project exclusion, unrelated
setting preservation, legacy writes/record identity, MCP diagnostics, schema
closure and corpus inventory. A failure to import tooling is not a successful
negative control. Coverage concerns specification publication only; no
filesystem transaction, manager, launcher or vendor runtime is qualified.

```sh
python3 tools/codex_seed_c.py
python3 -B -m unittest discover -s tools -p 'test_codex_seed_c.py' -v
make validate
git diff --check
```

`tools/validate.py` dispatches the same checker. Local logs belong in `.temp/`.
Frozen `conformance/v1/vectors/environments-codex-seed.json` remains A/B-only;
it is not regenerated or claimed as revision-C coverage.
