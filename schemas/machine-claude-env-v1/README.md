# Machine Claude environment schemas (unreleased proposal)

These Draft 2020-12 schemas belong to the
[proposed contract](../../protocol/machine-claude-env-proposal.md).
CIP-0029 allocates configuration **9** and **`curator.launcher-config/3`** now
to `extensions.claude_env`, conditionally on
[spec #216](https://github.com/relux-works/curator-spec/pull/216) and its schema
**8** / **`/2`** predecessor. The draft may stack now; acceptance waits for the
final predecessor shape to be accepted. CIP-0029 remains **Review**; Decision 0035 remains **Proposed**.
Allocation does not decide adoption, which belongs to the operator.

| Schema | Scope and status |
| --- | --- |
| `claude-env.schema.json` | Closed member value, canonical string 1..65536; absence belongs to the containing carrier |
| `projection.schema.json` | Synthetic runtime/contribution corpus, never a complete launcher projection or child environment |
| `extensions.schema.json` | Draft closed containing extensions: proxy, file/Keychain OAuth references, notification off/host, optional Claude member |
| `manager-config-v9.schema.json` | Draft complete closed configuration outer shape, with predecessor member grammars referenced intact |
| `launcher-config-v3.schema.json` | Draft complete closed typed projection: `schema`, `config_schema`, `config_path`, `extensions`; this `/3` projection carries config schema 9 |

## Predecessor snapshot and pending reconciliation

The drafts use Core #216 head
[`f5d7cd472db973b9864f87e5ca4526f20e4a893c`](https://github.com/relux-works/curator/pull/216),
particularly [configuration](https://github.com/relux-works/curator/blob/f5d7cd472db973b9864f87e5ca4526f20e4a893c/internal/config/config.go)
and [launcher selections/projection](https://github.com/relux-works/curator/blob/f5d7cd472db973b9864f87e5ca4526f20e4a893c/internal/config/launcher_extensions.go).
That is an inspected draft snapshot, not the final accepted schema 8 or `/2`.
These are complete **outer-shape drafts**, not accepted complete carriers or
proof of exhaustive predecessor compatibility. No placeholder permits arbitrary
unknown outer or extension members. Referenced predecessor maps retain their
existing key/value grammars rather than becoming generic objects.

The configuration candidate references every schema-8 property except version
and extensions from the [notification predecessor](../host-notification-v1/README.md).
The only added member is `claude_env`; `/3` retains `/2`'s containing fields and
path grammar by reference. No predecessor selection is redefined in this stack.
`projects` remains required: the previous draft's claim that the inspected
reader allowed omission was incorrect. The shared schema-8 draft preserves
published and admitted nullable forms; final accepted predecessor reconciliation
still remains a pre-emission requirement.

Before this publication can satisfy the pre-emission gate, the following parts
**wait for #216's accepted final schema 8 and `/2`**:

- Reconcile the entire machine field set, required/default/null behavior,
  predecessor version admission and all nested grammars against the final
  predecessor. The reused schema-5 member definitions and added Core fields
  are a starting point, not a declaration that parser and schema already agree.
- Confirm both proxy/auth arms and both notification arms, their exact names,
  required fields, reference grammar, digest encoding and unknown-member
  refusal. Retain each admitted combination with absent, empty and selected
  `claude_env`; compare valid and invalid predecessor fixtures independently.
- Confirm the complete projection field set, version pair, selected-source path
  semantics and extension preservation. `/3` is the typed selection transport;
  it adds no runtime/env pair from the synthetic contribution schema.
- Resolve semantic constraints beyond these structural drafts: strict bytes and
  decoded duplicate names, platform-specific absolute/clean paths, home expansion,
  Unicode whitespace/control rejection, byte-length versus character limits,
  canonical credential-scope host/segments, and selected-source authority.
  Schema success alone does not establish any of these properties.

If #216 changes versions or admitted shape, re-review the allocation and update
all affected schemas and witnesses together. Existing schema/release bytes are
unchanged. The complete containing schemas must preserve every admitted
predecessor form before any producer emits the successor. **The gate remains
pre-emission**: this draft does not move it to release or qualification, and does
not authorize Core #238 to land or emit `/3` before reconciliation and acceptance.

## Validation and limits

Run `go run ./tools/validate-claude-env -root .` and
`go test ./tools/validate-claude-env -count=1` from the repository root.
Run `python3 tools/claude_env_carriers.py` and
`python3 -B -m unittest discover -s tools -p test_claude_env_carriers.py` for
the containing drafts, using the repository's pinned `requirements-dev.txt`.
This Python checker resolves only the explicit local dependency set and never
downloads schemas. The existing Go dependency uses RE2 and cannot compile all
predecessor ECMA-style regexes; the repository's Python schema stack checks
those unchanged bytes without regex translation or skipped constraints. [Containing cases](../../conformance/machine-claude-env-v1/containing-cases.json)
exercise these drafts. The Go tool separately checks the member cases and six
semantic plants. Logs
belong in ignored `.temp/`. The output explicitly reports final predecessor
parity as unverified.

Strict decoder rejection, production diagnostics, provider-discovery blocking,
ordinary edit preservation, pre-side-effect refusal and native runtime behavior
are semantic obligations outside JSON Schema's decoded-instance model. The
validator's carrier controls establish setup and structural verdicts only;
production/runtime claims remain separate.

Containing validation uses the integer-token profile inherited from the base
contract; `schema_version:9.0` and `9e0` refuse beside the valid integer-9
control. The predecessor configuration 8 and `/2` explicitly refuse
`claude_env`; their paired positive controls are in the containing corpus.
