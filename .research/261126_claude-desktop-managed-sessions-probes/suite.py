#!/usr/bin/env python3
import hashlib, json, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import probe
P = os.path.dirname(os.path.abspath(__file__))
_base = os.path.join(P, "out", "p0.init.json")
if not os.path.exists(_base):  # baseline: empty settings, one user-scope server "alpha"
    os.makedirs(os.path.join(P, "out"), exist_ok=True)
    _h, _j = os.path.join(P, "h_p0"), os.path.join(P, "proj_p0")
    os.makedirs(_h, exist_ok=True); os.makedirs(_j, exist_ok=True)
    json.dump({}, open(os.path.join(_h, "settings.json"), "w"))
    json.dump({"hasCompletedOnboarding": True, "mcpServers": {"alpha": {"type": "stdio", "command": "/usr/bin/python3",
               "args": [os.path.join(P, "probe_server.py"), "alpha"], "env": {}}}}, open(os.path.join(_h, ".claude.json"), "w"))
    if not probe.run("p0", _h, _j)[0]: sys.exit("baseline produced no init message")
BASE = json.load(open(_base))
BASE_TOOLS = {t for t in BASE["tools"] if not t.startswith("mcp__")}
BASE_SKILLS = set(BASE["skills"])
def srv(name, env=None, extra_args=None):
    e = {"PROBE_LOG": os.path.join(P, "out", "%s.server.log")}
    e.update(env or {})
    return name, {"type": "stdio", "command": "/usr/bin/python3", "args": [os.path.join(P, "probe_server.py"), name] + (extra_args or []), "env": e}
def case(name, settings=None, servers=(), proj_settings=None, mcp_json=None, env=None, args=None, home_skill=False):
    h, j = os.path.join(P, "h_" + name), os.path.join(P, "proj_" + name)
    shutil.rmtree(h, ignore_errors=True); shutil.rmtree(j, ignore_errors=True)
    os.makedirs(h); os.makedirs(j)
    json.dump(settings or {}, open(os.path.join(h, "settings.json"), "w"), indent=1)
    ms = {}
    for n, cfg in servers:
        cfg = json.loads(json.dumps(cfg).replace("%s", name)); ms[n] = cfg
    json.dump({"hasCompletedOnboarding": True, "mcpServers": ms}, open(os.path.join(h, ".claude.json"), "w"), indent=1)
    if home_skill: shutil.copytree(os.path.join(P, "fixtures", "home-skill"), os.path.join(h, "skills"))
    if proj_settings is not None:
        os.makedirs(os.path.join(j, ".claude")); json.dump(proj_settings, open(os.path.join(j, ".claude", "settings.json"), "w"), indent=1)
    if mcp_json is not None:
        mj = {"mcpServers": {n: json.loads(json.dumps(c).replace("%s", name)) for n, c in mcp_json}}
        json.dump(mj, open(os.path.join(j, ".mcp.json"), "w"), indent=1)
    init, first, err = probe.run(name, h, j, env or {}, args or [])
    if not init:
        print(f"{name}: NO INIT {first[:2]} {err[:300]}"); return
    tools = set(init["tools"]); mcp_tools = sorted(t for t in tools if t.startswith("mcp__"))
    removed = sorted(BASE_TOOLS - tools); added = sorted((tools - BASE_TOOLS) - set(mcp_tools))
    sk = set(init.get("skills", []));
    servers_s = [(s["name"], s["status"], s.get("source")) for s in init.get("mcp_servers", [])]
    plugs = [p.get("source") for p in init.get("plugins", [])]
    log = os.path.join(P, "out", name + ".server.log")
    loglines = [l.split(" ", 1)[1].strip() for l in open(log)] if os.path.exists(log) else []
    print(f"{name}: servers={servers_s} mcp_tools={mcp_tools} -tools={removed} +tools={added} "
          f"-skills={sorted(BASE_SKILLS - sk)[:4]}{'...' if len(BASE_SKILLS - sk) > 4 else ''} +skills={sorted(sk - BASE_SKILLS)} plugins={plugs} log={loglines}")
A, B, G = srv("alpha"), srv("beta"), srv("gamma")
allow_a = {"allowedMcpServers": [{"serverName": "alpha"}]}
which = sys.argv[1] if len(sys.argv) > 1 else "all"
if which in ("all", "p1"):
    case("p1_allow_user", allow_a, [A, B])
    case("p1_denied_user", {"deniedMcpServers": [{"serverName": "beta"}]}, [A, B])
    case("p1_proj_widen_allow", allow_a, [A, B], proj_settings={"allowedMcpServers": [{"serverName": "alpha"}, {"serverName": "beta"}]})
    case("p1_projmcp_ctrl", {}, [A], proj_settings={"enableAllProjectMcpServers": True}, mcp_json=[G])
    case("p1_projmcp_vs_allow", allow_a, [A], proj_settings={"enableAllProjectMcpServers": True}, mcp_json=[G])
if which in ("all", "p2"):
    case("p2_env_true", {}, [A], env={"ENABLE_TOOL_SEARCH": "true"})
    case("p2_env_false", {}, [A], env={"ENABLE_TOOL_SEARCH": "false"})
    case("p2_proc_true_settings_false", {"env": {"ENABLE_TOOL_SEARCH": "false"}}, [A], env={"ENABLE_TOOL_SEARCH": "true"})
    case("p2_proc_false_settings_true", {"env": {"ENABLE_TOOL_SEARCH": "true"}}, [A], env={"ENABLE_TOOL_SEARCH": "false"})
if which in ("all", "p3"):
    print("expected sha256(probe-value-1)[:12] =", hashlib.sha256(b"probe-value-1").hexdigest()[:12], " (probe-value-2) =", hashlib.sha256(b"probe-value-2").hexdigest()[:12])
    a3 = srv("alpha", {"PROBE_SECRET": "${CURATOR_PROBE_SECRET}", "PROBE_DEFAULT": "${CURATOR_PROBE_MISSING:-fallback}"}, ["${CURATOR_PROBE_SECRET}"])
    b3 = srv("beta", {"PROBE_SECRET": "${CURATOR_PROBE_MISSING}"})
    case("p3_expand_proc_env", {}, [a3, b3], env={"CURATOR_PROBE_SECRET": "probe-value-1"})
    case("p3_expand_settings_env", {"env": {"CURATOR_PROBE_SECRET": "probe-value-2"}}, [a3])
if which in ("all", "p4"):
    for tag, rule in [("star", "mcp__*"), ("prefix", "mcp__al*"), ("server_tools_star", "mcp__alpha__*"), ("server_ctrl", "mcp__alpha"), ("star_star", "mcp__*__*")]:
        case("p4_deny_" + tag, {"permissions": {"deny": [rule]}}, [A, B])
if which in ("all", "p5"):
    case("p5_bundled_ctrl", {"disableBundledSkills": True}, [])
    case("p5_bundled_proj_reenable", {"disableBundledSkills": True}, [], proj_settings={"disableBundledSkills": False})
    case("p5_bundled_proj_reenable_ss_user", {"disableBundledSkills": True}, [], proj_settings={"disableBundledSkills": False}, args=["--setting-sources", "user"])
    case("p5_deny_vs_proj_allow", {"permissions": {"deny": ["WebFetch"]}}, [], proj_settings={"permissions": {"allow": ["WebFetch"]}})
    plug = ["--plugin-dir", os.path.join(P, "fixtures", "probeplug")]
    case("p5_plugin_none", {}, [], args=plug)
    case("p5_plugin_user_off", {"enabledPlugins": {"probeplug@inline": False}}, [], args=plug)
    case("p5_plugin_proj_on", {"enabledPlugins": {"probeplug@inline": False}}, [], proj_settings={"enabledPlugins": {"probeplug@inline": True}}, args=plug)
    case("p5_override_ctrl", {"skillOverrides": {"probe-home-skill": "off"}}, [], home_skill=True)
    case("p5_override_proj_on", {"skillOverrides": {"probe-home-skill": "off"}}, [], proj_settings={"skillOverrides": {"probe-home-skill": "on"}}, home_skill=True)
if which in ("p6",):
    U = srv("0b7c5c2e-1111-4222-8333-944455556666")
    case("p6_deny_uuid_shape", {"permissions": {"deny": ["mcp__*-*-*-*-*"]}}, [A, U, srv("claude-in-chrome")])
    case("p6_deny_case", {"permissions": {"deny": ["mcp__ALPHA"]}}, [A, B])
    case("p6_allow_merge", allow_a, [A, B], proj_settings={"allowedMcpServers": [{"serverName": "beta"}]})
    case("p6_userdenied_vs_projallow", {"deniedMcpServers": [{"serverName": "gamma"}]}, [A], proj_settings={"enableAllProjectMcpServers": True, "allowedMcpServers": [{"serverName": "alpha"}, {"serverName": "gamma"}]}, mcp_json=[G])
    case("p6_permdeny_vs_projmcp", {"permissions": {"deny": ["mcp__gamma"]}}, [A], proj_settings={"enableAllProjectMcpServers": True}, mcp_json=[G])
    plug = ["--plugin-dir", os.path.join(P, "fixtures", "probeplug")]
    case("p6_skilldeny_bundled", {"permissions": {"deny": ["Skill(simplify)"]}}, [])
    case("p6_skilldeny_plugin_star", {"permissions": {"deny": ["Skill(probeplug:*)"]}}, [], proj_settings={"enabledPlugins": {"probeplug@inline": True}}, args=plug)
    case("p6_skilldeny_plugin_exact", {"permissions": {"deny": ["Skill(probeplug:probe-plug-skill)"]}}, [], args=plug)
    case("p6_tooldeny_skill", {"permissions": {"deny": ["Skill"]}}, [], home_skill=True)
if which in ("p7",):
    names = ["acme-mcp-tracker", "a-b-c-d", "a-b-c-d-e", "0b7c5c2e-1111-4222-8333-944455556666"]
    case("p7_uuid_mask_specificity", {"permissions": {"deny": ["mcp__*-*-*-*-*"]}}, [srv(n) for n in names])
    case("p7_denied_wildcard", {"deniedMcpServers": [{"serverName": "be*"}]}, [A, B])
    case("p7_proj_env_overrides_user_env", {"env": {"ENABLE_TOOL_SEARCH": "false"}}, [A], proj_settings={"env": {"ENABLE_TOOL_SEARCH": "true"}})
if which in ("p8",):
    ns = ["acme-tracker", "a-b-c-d", "0b7c5c2e-1111-4222-8333-944455556666"]
    case("p8_mask_full_name", {"permissions": {"deny": ["mcp__*-*-*-*-*"]}}, [srv(n, {"PROBE_TOOL": "batch"}) for n in ns])
