#!/usr/bin/env python3
"""Summarize what a Claude Desktop session actually sent: loaded tools (api-request-shape), deferred tools, MCP servers."""
import collections, json, sys
def server(n): return n.split("__")[1] if n.startswith("mcp__") and n.count("__") >= 2 else None
def summ(names):
    b = sorted(n for n in names if not n.startswith("mcp__")); g = collections.defaultdict(list)
    for n in names:
        s = server(n)
        if s: g[s].append(n.split("__", 2)[2])
    return b, {k: sorted(v) for k, v in sorted(g.items())}
f = sys.argv[1]; lines = [json.loads(l) for l in open(f) if l.strip()]
shape = next((m for m in lines if m.get("type") == "api-request-shape"), None)
loaded = [t.get("name") for t in (shape or {}).get("shape", {}).get("tools", []) if isinstance(t, dict)]
deferred = []; instr = []; skills = None
for m in lines:
    a = m.get("attachment") or {}
    if a.get("type") == "deferred_tools_delta": deferred += a.get("addedNames", [])
    if a.get("type") == "mcp_instructions_delta": instr += a.get("addedNames", [])
    if a.get("type") == "skill_listing": skills = a
lb, lm = summ(loaded); db, dm = summ(deferred)
print("transcript:", f.rsplit("/", 1)[-1], "cli:", (shape or {}).get("version"))
print("LOADED builtin:", lb); print("LOADED mcp:", json.dumps(lm, ensure_ascii=False))
print("DEFERRED builtin:", db); print("DEFERRED mcp servers:", {k: len(v) for k, v in dm.items()})
print("ToolSearch loaded:", "ToolSearch" in loaded, "| deferred list present:", bool(deferred))
print("servers with instructions:", sorted(set(instr)))
if skills: print("skill_listing:", json.dumps(skills, ensure_ascii=False)[:300])
