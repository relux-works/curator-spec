# Machine Claude environment member schemas (proposal)

These Draft 2020-12 schemas belong to the
[proposed contract](../../protocol/machine-claude-env-proposal.md).
`claude-env.schema.json` validates only the optional member's object value;
absence is handled by the future containing carrier. `projection.schema.json`
validates only a synthetic extension contribution for the corpus's named
runtimes, not a full child environment or runtime registry.

They allocate neither configuration 9 nor `curator.launcher-config/3`.
Those proposed numbers depend on final schema-8 acceptance and review allocation.
No existing configuration/profile/lock/release schema is changed. A future
complete containing publication must preserve every admitted predecessor form.

Duplicate-key detection, pre-side-effect refusal, exact diagnostics, ordinary
edit preservation and native runtime behavior are semantic obligations outside
JSON Schema's decoded-instance model. The Go checker validates both schemas
and those bounded input semantics; production/runtime claims remain separate.
