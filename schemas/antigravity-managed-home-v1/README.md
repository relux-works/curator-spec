# Antigravity managed-home schemas (`antigravity-managed-home-v1`)

This directory publishes the closed successor schemas allocated by
[CIP-0033](../../cips/CIP-0033-antigravity-managed-home.md) for the
`antigravity` (Antigravity CLI / `agy`) managed-home adapter:

| File | Discriminator / title | Purpose |
|---|---|---|
| `node-source-v2.schema.json` | `node-source-v2` | Extends `node-source-v1` with `GEMINI_API_KEY` and `GOOGLE_APPLICATION_CREDENTIALS` harness channels while keeping `node-source-v1` byte-frozen |
| `launch-env-fragment-v7.schema.json` | `launch-env-fragment-v7` | Complete closed successor to `launch-env-fragment-v6`: adds `antigravity`, top-level `home: {"path", "transport": "flag"}` (Antigravity-only), required `AGY_CLI_FORCE_FILE_TOKEN_STORAGE=true`, `config/mcp_config.json` file MCP channel, and `node-source-v2` projection |
| `snapshot-launch-v2.schema.json` | `snapshot-launch-v2` | Complete closed successor to `snapshot-launch-v1`: adds `antigravity` with `home: {"path": "home", "transport": "flag"}` and `env: {}` (no credential policy in portable snapshots) |

Predecessor schemas (`launch-env-fragment-v1` through `launch-env-fragment-v6`,
`node-source-v1`, and `snapshot-launch-v1`) retain their exact bytes and refuse
`antigravity`.
