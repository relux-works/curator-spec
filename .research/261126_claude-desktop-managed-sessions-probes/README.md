# Probes for facts 48-64, 67 and 72

Headless probes of the Claude Code CLI binary that Claude Desktop runs for its sessions. Each probe uses a throwaway `CLAUDE_CONFIG_DIR` and project directory, a cleared environment and `ANTHROPIC_BASE_URL` pointing at a closed local port. No login is used and no request leaves the machine. Only the `system/init` message is captured.

Set the binary and run a group (`p1` ... `p8`). The first run also records the baseline case `p0` that every case is compared against:

```bash
export PROBE_CLI="$HOME/Library/Application Support/Claude/claude-code/<version>/<hash>/claude.app/Contents/MacOS/claude"
python3 -I suite.py p1
```

Results are written to `out/<case>.init.json` and `out/<case>.server.log`. The test MCP server logs a hash of `PROBE_SECRET`, never its value.

## Probe 67 (D5): when MCP tools are loaded

`probe_load.py` answers a question that `system/init` cannot: is an MCP tool sent to the model up front or deferred behind `ToolSearch`. A mock Anthropic API on `127.0.0.1` records the first model request and answers 400. The API key is a dummy value, no login is used, and nothing leaves the machine. Only tool names are printed, never the request body.

```bash
python3 -I probe_load.py
```

## Fact 72: what a Desktop session sent

`transcript_shape.py` summarizes a Claude Desktop session transcript (`<CLAUDE_CONFIG_DIR>/projects/<project>/<session>.jsonl`): the tools loaded up front (the `api-request-shape` record), the deferred tools (`deferred_tools_delta`) and the servers whose instructions entered the prompt (`mcp_instructions_delta`). Probes D1-D3 were read this way.

```bash
python3 -I transcript_shape.py <session>.jsonl
```
