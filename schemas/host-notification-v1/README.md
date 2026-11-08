# Draft notification containing schemas

Review-only companions to the [contract](../../protocol/host-notification-proposal.md).
No released schema is modified and no producer emission is authorized.

| File | Complete closed object |
| --- | --- |
| `manager-config-v7.schema.json` | Inspected predecessor, published schema-5 members plus build/script/execution and proxy/auth selections |
| `manager-config-v8.schema.json` | Same containing shape plus optional notification |
| `extensions-v7.schema.json` | Proxy and file/Keychain Claude OAuth references |
| `extensions.schema.json` | All predecessor selections plus exact off/Host notification |
| `launcher-config-v1.schema.json` | Supported old schemas 1/2/3/5/7; no notification |
| `launcher-config-v2.schema.json` | Schema 8 with extensions present, including empty or explicit off |

Required/default/null forms are explicit: `projects` is required, and
`environments` is an object. Published schema-5 member grammars and defaults are
referenced intact. Optional audit/registries/build/script/execution nulls and
admitted nullable environment knobs are retained; system-module-waiver,
permission and credential-store nulls are rejected. `node-v1` and `python3-v1`
are the admitted script bindings. `provider_directories:null` and
`source_signers:null` refuse within `environments` on both 7 and 8. Only new
schema-8 and `/2` versions use the raw-file integer-token profile in contract §3;
ordinary JSON Schema numerical equality alone cannot reject `8.0`/`8e0`.
Schema 7 and legacy versions retain released numeric-integer admission, including
`7.0`/`7e0`, `5.0`/`5e0` and `1.0`, with `/1`. The checker uses the unchanged
published schemas for legacy configuration controls, compiles only the new
carriers with strict integer-token typing and applies explicit target-path
semantics (the corpus target is POSIX). Schema 6 remains a separate family.

Contract §3 supplies reference byte bounds, Unicode trim/control checks,
platform clean absolute paths and unchanged predecessor semantic validation.
JSON Schema alone cannot prove those semantics, immutable workflow bytes,
editor behavior, authority, receiver support or exhaustive reader parity.
The complete containing schemas must preserve every admitted predecessor form
before any producer emits the successor. Draft publication does not satisfy or
defer that gate. Acceptance must reconcile any remaining reader/schema differences.

Run `python3 -B tools/host_notification.py` and focused controls with
`python3 -B -m unittest discover -s tools -p 'test_host_notification.py' -v`.
The repository validator dispatches the corpus; logs belong under `.temp/`.
