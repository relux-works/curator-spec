# Antigravity managed-home conformance corpus (`antigravity-managed-home-v1`)

This corpus verifies the closed wire contracts allocated by
[CIP-0033](../../cips/CIP-0033-antigravity-managed-home.md):

- `launch-env-fragment-v7` (positive and negative cases for `antigravity`
  flag-transported homes, `AGY_CLI_FORCE_FILE_TOKEN_STORAGE=true`,
  `config/mcp_config.json`, `node-source-v2` `GEMINI_API_KEY` and
  `GOOGLE_APPLICATION_CREDENTIALS` channels, basename `!= ".gemini"`, and
  predecessor `launch-env-fragment-v6` rejection);
- `snapshot-launch-v2` (positive and negative cases for `home: {"path": "home",
  "transport": "flag"}`, empty `env: {}` carrying zero credential policy, and
  predecessor `snapshot-launch-v1` rejection).

Run standalone:

```sh
python3 tools/antigravity_managed_home.py
```

These checks also run as part of `tools/validate.py` and
`python3 -m unittest tools/test_antigravity_managed_home.py`.
