#!/usr/bin/env python3
"""Run the Claude CLI headless in a throwaway config dir; capture only the system/init message."""
import json, os, select, signal, subprocess, sys, time
CLI = os.environ["PROBE_CLI"]
def run(name, home, proj, extra_env=None, args=None, timeout=45):
    env = {"HOME": os.environ["HOME"], "USER": os.environ.get("USER", ""), "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
           "TMPDIR": os.environ.get("TMPDIR", "/tmp"), "CLAUDE_CONFIG_DIR": home, "DISABLE_AUTOUPDATER": "1",
           "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1", "ANTHROPIC_BASE_URL": "http://127.0.0.1:9"}
    env.update(extra_env or {})
    cmd = [CLI, "-p", "probe", "--output-format", "stream-json", "--verbose", "--max-turns", "1"] + (args or [])
    p = subprocess.Popen(cmd, cwd=proj, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    init, first = None, []
    end = time.time() + timeout
    while time.time() < end:
        r, _, _ = select.select([p.stdout], [], [], 0.5)
        if r:
            line = p.stdout.readline()
            if not line: break
            if len(first) < 5: first.append(line.decode(errors="replace")[:400])
            try: msg = json.loads(line)
            except Exception: continue
            if msg.get("type") == "system" and msg.get("subtype") == "init": init = msg; break
        elif p.poll() is not None: break
    try: os.killpg(p.pid, signal.SIGKILL)
    except Exception: pass
    err = p.stderr.read().decode(errors="replace")[:1500]
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", name + ".init.json"), "w") as h:
        json.dump(init, h, indent=1)
    return init, first, err
if __name__ == "__main__":
    name, home, proj = sys.argv[1:4]
    extra = dict(kv.split("=", 1) for kv in os.environ.get("PROBE_ENV", "").split("\x1f") if kv)
    args = [a for a in os.environ.get("PROBE_ARGS", "").split("\x1f") if a]
    init, first, err = run(name, home, proj, extra, args)
    if not init:
        print(f"[{name}] NO INIT. first lines: {first}\nstderr: {err}"); sys.exit(1)
    keys = sorted(init.keys())
    print(f"[{name}] init keys: {keys}")
    print(f"  version={init.get('claude_code_version')} apiKeySource={init.get('apiKeySource')} tools={len(init.get('tools', []))}")
    print("  mcp_servers:", init.get("mcp_servers"))
