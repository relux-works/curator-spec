package main

import "path/filepath"

// Muse has four XDG parents, not a replacement HOME. No root-context or
// system/MCP target is generated while the vendor loading semantics are unknown.
func museHomeVariables(home string) map[string]any {
	return map[string]any{
		"XDG_CONFIG_HOME": home + "/config",
		"XDG_DATA_HOME":   home + "/data",
		"XDG_STATE_HOME":  home + "/state",
		"XDG_CACHE_HOME":  home + "/cache",
	}
}

func validMuseFragment() map[string]any {
	fragment := validLaunchEnvFragmentV2()
	fragment["fragment"] = "launch-env-fragment-v3"
	fragment["environment"] = "muse"
	fragment["env"] = museHomeVariables("/manager/environments/companyA/muse")
	delete(fragment, "system_prompt")
	delete(fragment, "mcp")
	return fragment
}

func museMarker() map[string]any {
	marker := validEnvironmentMarkerV3()
	marker["passthrough"] = []any{map[string]any{
		"path": "config/muse/auth.json", "isolation": "shared", "strategy": "file-link",
		"source_role": "native", "backend": "file", "backend_version": "1.4.1-R4503.1",
		"provenance": "provisioned",
	}}
	marker["seeds"] = []any{"config/muse/settings.json", "config/muse/trust.json"}
	marker["surfaces"] = map[string]any{}
	delete(marker, "seeded_projects")
	delete(marker, "codex_seed_record")
	return marker
}

func launchEnvFragmentV3SchemaExamples() []schemaExample {
	valid := validMuseFragment()
	cases := launchEnvFragmentV2SchemaExamples(valid)
	for _, environment := range []string{"claude_code", "codex_cli", "opencode", "pi"} {
		old := launchFragmentFor(environment, true, environment != "pi")
		old["fragment"] = "launch-env-fragment-v3"
		old["permissions"] = valid["permissions"]
		cases = append(cases, schemaExample{name: "valid-" + environment, valid: true, instance: old})
		extra := withField(old, "env", withField(old["env"].(map[string]any), "XDG_CACHE_HOME", "/manager/cache"))
		cases = append(cases, schemaExample{name: "invalid-extra-parent-" + environment, valid: false, instance: extra})
	}
	for _, variable := range []string{"XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME", "XDG_CACHE_HOME"} {
		cases = append(cases,
			schemaExample{name: "invalid-missing-" + variable, valid: false, instance: withField(valid, "env", without(valid["env"].(map[string]any), variable))},
			schemaExample{name: "invalid-wrong-parent-" + variable, valid: false, instance: withField(valid, "env", withField(valid["env"].(map[string]any), variable, "/foreign/parent"))},
		)
	}
	cases = append(cases,
		schemaExample{name: "invalid-HOME-added", valid: false, instance: withField(valid, "env", withField(valid["env"].(map[string]any), "HOME", "/manager/home"))},
		schemaExample{name: "invalid-HOME-substitution", valid: false, instance: withField(valid, "env", map[string]any{"HOME": "/manager/home"})},
		schemaExample{name: "invalid-unverified-system-prompt", valid: false, instance: withField(valid, "system_prompt", validLaunchEnvFragmentV2()["system_prompt"])},
		schemaExample{name: "invalid-unverified-mcp", valid: false, instance: withField(valid, "mcp", validLaunchEnvFragmentV2()["mcp"])},
		schemaExample{name: "invalid-v2-token", valid: false, instance: withField(valid, "fragment", "launch-env-fragment-v2")},
		schemaExample{name: "invalid-unknown-environment", valid: false, instance: withField(valid, "environment", "unknown")},
	)
	return cases
}

// These are conformance expectations, not a manager implementation or a
// refresh probe. The independent Python validator checks the closed inventory.
func musePassthroughExpectation(state string, repair bool) map[string]any {
	diagnostic, action, emit := "", "none", false
	switch state {
	case "live", "write-through-refresh":
		emit = true
	case "metadata-unreadable", "target-unreadable":
		diagnostic = "environment_passthrough_unreadable"
	default:
		diagnostic = "environment_home_stale"
		if repair {
			if state == "missing-link" {
				diagnostic, action, emit = "", "relink", true
			} else {
				diagnostic = "environment_credential_conflict"
			}
		}
	}
	status := "current"
	if diagnostic != "" || action == "relink" {
		status = "environment_passthrough_detached"
	}
	if diagnostic == "environment_passthrough_unreadable" {
		status = diagnostic
	}
	return map[string]any{"status": status, "diagnostic": diagnostic, "action": action, "emit_fragment": emit, "credential_bytes_changed": false}
}

func writeMuseEnvironmentVectors(dir, expected string) {
	fragment := validMuseFragment()
	writeJSON(filepath.Join(expected, "muse-home-layout.json"), map[string]any{
		"home": "/manager/environments/companyA/muse", "env": fragment["env"],
		"tool_directories": []any{"config/muse", "data/muse", "state", "cache"},
		"native_auth":      "/operator/config/muse/auth.json", "managed_auth": "config/muse/auth.json",
		"link_kind": "file-link", "seeds": []any{"config/muse/settings.json", "config/muse/trust.json"},
		"HOME": "/operator", "HOME_replaced": false,
	})
	writeJSON(filepath.Join(expected, "muse-fragment.json"), fragment)
	writeJSON(filepath.Join(expected, "muse-marker.json"), museMarker())
	cases := []any{}
	for _, state := range []string{"live", "write-through-refresh", "missing-link", "temp-rename-fork", "retargeted-link", "dangling-target", "metadata-unreadable", "target-unreadable"} {
		for _, repair := range []bool{false, true} {
			suffix := "resolve"
			if repair {
				suffix = "repair"
			}
			cases = append(cases, map[string]any{"name": state + "-" + suffix, "state": state, "repair": repair, "expected": musePassthroughExpectation(state, repair)})
		}
	}
	writeJSON(filepath.Join(dir, "environments-muse.json"), map[string]any{
		"schema_version": 1, "protocol_version": protocolVersion, "capability": "agent-environments",
		"normative": "protocol/environments.md sections 7.1, 7.4, and 10.2",
		"registry": map[string]any{
			"environment": "muse", "tool_version": "1.4.1-R4503.1", "home_variables": fragment["env"],
			"replace_HOME": false, "root_context_target": nil, "root_context_verified": false,
			"skills_target": "data/muse/skills", "skills_discovery_verified": false,
			"refresh_semantics": "unverified", "isolation_gap": "foreign-personal-context",
			"exec_yolo": []any{"--yolo"}, "serve_yolo": []any{"--disable-sandbox", "--trust-workspace"},
			"serve_session": map[string]any{"method": "session/start", "approvalMode": "allowAll"},
		},
		"fixtures": map[string]any{"layout": "expected/environments-muse/muse-home-layout.json", "fragment": "expected/environments-muse/muse-fragment.json", "marker": "expected/environments-muse/muse-marker.json"},
		"cases":    cases,
	})
}
