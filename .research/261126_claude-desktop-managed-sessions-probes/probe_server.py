#!/usr/bin/env python3
"""Probe MCP server: name from argv[1]; logs how PROBE_SECRET arrived (never the value)."""
import datetime, hashlib, json, os, re, sys
LOG = os.environ.get("PROBE_LOG") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.log")
NAME = sys.argv[1] if len(sys.argv) > 1 else "probe"
def state(v):
    if v is None: return "unset"
    if re.search(r"\$\{[^}]+\}", v): return "literal:" + v
    if v == "": return "empty"
    return "sha256:" + hashlib.sha256(v.encode()).hexdigest()[:12]
def log(m):
    with open(LOG, "a") as h: h.write(f"{datetime.datetime.now().isoformat(timespec='seconds')} {NAME} {m}\n")
def out(o): sys.stdout.write(json.dumps(o) + "\n"); sys.stdout.flush()
log(f"start PROBE_SECRET={state(os.environ.get('PROBE_SECRET'))} PROBE_DEFAULT={state(os.environ.get('PROBE_DEFAULT'))} argv1={sys.argv[2] if len(sys.argv)>2 else '-'}")
for line in sys.stdin:
    try: m = json.loads(line)
    except Exception: continue
    i = m.get("id"); meth = m.get("method")
    if i is None: continue
    if meth == "initialize":
        out({"jsonrpc": "2.0", "id": i, "result": {"protocolVersion": (m.get("params") or {}).get("protocolVersion", "2025-06-18"), "capabilities": {"tools": {}}, "serverInfo": {"name": NAME, "version": "0"}}})
    elif meth == "tools/list":
        out({"jsonrpc": "2.0", "id": i, "result": {"tools": [{"name": os.environ.get("PROBE_TOOL") or f"{NAME}_codeword", "description": "probe", "inputSchema": {"type": "object", "properties": {}}}]}})
    else:
        out({"jsonrpc": "2.0", "id": i, "error": {"code": -32601, "message": "n/a"}})
