# Project Skillfile MCP stage-A schemas

These complete closed Draft 2020-12 schemas implement the
[normative contract](../../protocol/skillfile-mcp.md). They form a new
`skillfile-mcp-v1` namespace; no released schema or pin is replaced.

| Schema | Carrier |
| --- | --- |
| `skillfile-v3.schema.json` | Project schema 2 fields plus optional `mcp_servers`; other scope/version dispatch is semantic. |
| `declaration-v1.schema.json` | Recognized URL, closed inline and closed package arms. Recognizing inline syntax never authorizes stage-A activation. |
| `mcp-lock-v1.schema.json` | Whole stage-A lock: unchanged enclosed skills lock, project/full-document CCJ-1 manifest identity, sorted exact package/server bindings, own digest. |
| `mcp-approval-v1.schema.json` | Protected package ownership-action authorization; never a stage-B inline approval. |
| `mcp-plan-v1.schema.json` | Whole stage-A plan: identity, dry-run state, pair rows, ignored option names and own digest. |

Semantic constraints include lexical URLs, runtime pins, canonical identities,
legacy package UTF-8 byte ceilings (separate from inline scalar maxLength),
revision/commit and range/version consistency, normalization/digests, sorted
unique record keys, matching enclosing manifest
identity, path/outcome/code consistency and refusal atomicity. The normative
contract defines those constraints in addition to JSON Schema. An approval
object's shape cannot establish protected storage, approver authority, current
policy or project identity. Repository-supplied objects never grant authority.
The stage-B inline approval namespace is reserved and has no accepted instance.

Use `python3 tools/validate.py` for the complete repository gate. The dedicated
semantic checker and corpus are published with stage A; none of these schema
checks executes an MCP runtime or qualifies a native adapter.
