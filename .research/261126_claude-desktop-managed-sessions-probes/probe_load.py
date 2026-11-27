#!/usr/bin/env python3
"""D5: does `alwaysLoad: true` work in a --mcp-config file (the curator run channel)?

Local only: a mock Anthropic API on 127.0.0.1 records the first request and answers 400;
a dummy API key; throwaway CLAUDE_CONFIG_DIR and project per case; cleared environment.
ENABLE_TOOL_SEARCH=true, so MCP tools are deferred unless alwaysLoad keeps them loaded.
Prints only tool names and whether the probe tool is listed as deferred, never the request body.
"""
import http.server, json, os, select, shutil, signal, subprocess, sys, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
CLI = os.environ["PROBE_CLI"]
SERVER = os.path.join(HERE, "probe_server.py")
WORK = os.path.join(HERE, "work"); OUT = os.path.join(HERE, "out")
REQS = []
TOOL = "mcp__alpha__alpha_codeword"

class H(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("content-length") or 0))
        try: REQS.append((self.path, json.loads(body)))
        except Exception: REQS.append((self.path, None))
        msg = json.dumps({"type": "error", "error": {"type": "invalid_request_error", "message": "probe mock"}}).encode()
        self.send_response(400); self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(msg))); self.end_headers(); self.wfile.write(msg)
    def do_GET(self):
        REQS.append((self.path, "GET")); self.send_response(404); self.send_header("content-length", "0"); self.end_headers()
    def log_message(self, *a): pass

api = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=api.serve_forever, daemon=True).start()
PORT = api.server_address[1]

def alpha(always=None):
    cfg = {"type": "stdio", "command": "/usr/bin/python3", "args": [SERVER, "alpha"],
           "env": {"PROBE_LOG": os.path.join(OUT, "alpha.server.log")}}
    if always is not None: cfg["alwaysLoad"] = always
    return cfg

def case(name, user_servers=None, flag_servers=None, strict=True, tool_search="true"):
    h, j = os.path.join(WORK, "h_" + name), os.path.join(WORK, "proj_" + name)
    shutil.rmtree(h, ignore_errors=True); shutil.rmtree(j, ignore_errors=True); os.makedirs(h); os.makedirs(j)
    json.dump({}, open(os.path.join(h, "settings.json"), "w"))
    json.dump({"hasCompletedOnboarding": True, "mcpServers": user_servers or {}}, open(os.path.join(h, ".claude.json"), "w"))
    args = []
    if flag_servers is not None:
        f = os.path.join(WORK, name + ".mcp-config.json")
        json.dump({"mcpServers": flag_servers}, open(f, "w"))
        args += ["--mcp-config", f] + (["--strict-mcp-config"] if strict else [])
    env = {"HOME": os.environ["HOME"], "USER": os.environ.get("USER", ""), "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
           "TMPDIR": os.environ.get("TMPDIR", "/tmp"), "CLAUDE_CONFIG_DIR": h, "DISABLE_AUTOUPDATER": "1",
           "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1", "ANTHROPIC_BASE_URL": f"http://127.0.0.1:{PORT}",
           "ANTHROPIC_API_KEY": "probe-dummy-key-not-a-secret"}
    if tool_search is not None: env["ENABLE_TOOL_SEARCH"] = tool_search
    REQS.clear()
    cmd = [CLI, "-p", "probe", "--output-format", "stream-json", "--verbose", "--max-turns", "1"] + args
    p = subprocess.Popen(cmd, cwd=j, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    init, end = None, time.time() + 60
    while time.time() < end:
        r, _, _ = select.select([p.stdout], [], [], 0.5)
        if r:
            line = p.stdout.readline()
            if not line: break
            try: m = json.loads(line)
            except Exception: continue
            if m.get("type") == "system" and m.get("subtype") == "init": init = m
        elif p.poll() is not None: break
    try: os.killpg(p.pid, signal.SIGKILL)
    except Exception: pass
    msgs = [(path, b) for path, b in REQS if isinstance(b, dict) and "tools" in b]
    if not msgs:
        print(f"{name}: no model request with tools; paths={[x[0] for x in REQS]}; init_tool_present={bool(init and TOOL in init.get('tools', []))}")
        return
    path, b = msgs[0]
    names = [t.get("name") for t in b["tools"]]
    defer_flag = sorted(t.get("name") for t in b["tools"] if t.get("defer_loading"))
    text = json.dumps(b.get("messages", [])) + json.dumps(b.get("system", ""))
    verdict = ("LOADED (full schema in tools[])" if TOOL in names and TOOL not in defer_flag
               else "DEFERRED" if (TOOL in defer_flag or (TOOL not in names and "alpha_codeword" in text)) else "ABSENT")
    srv_status = [(s["name"], s["status"]) for s in (init or {}).get("mcp_servers", [])]
    print(f"{name}: {verdict}; ToolSearch_in_tools={'ToolSearch' in names}; n_tools={len(names)}; "
          f"mcp_in_tools={[n for n in names if n.startswith('mcp__')]}; defer_loading={defer_flag}; "
          f"listed_in_messages={'alpha_codeword' in text}; init_servers={srv_status}; version={(init or {}).get('claude_code_version')}")

if __name__ == "__main__":
    os.makedirs(WORK, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    print("mock API port", PORT)
    case("d5_flag_default", flag_servers={"alpha": alpha()})                    # control: expect DEFERRED
    case("d5_flag_always", flag_servers={"alpha": alpha(True)})                 # D5 question
    case("d5_userjson_always", user_servers={"alpha": alpha(True)})             # CLI analogue of fact 18
    case("d5_userjson_default", user_servers={"alpha": alpha()})                # control
    case("d5_flag_always_toolsearch_auto", flag_servers={"alpha": alpha(True)}, tool_search=None)  # default env
