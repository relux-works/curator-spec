package main

import "strings"

// managerConfigV2EnvironmentDefaults is the environments §12.1 default of every
// knob, spelled exactly as the schema's `default` members spell it. A vector
// that omits `environments` expects this object; a vector that sets some knobs
// expects this object with those knobs replaced.
func managerConfigV2EnvironmentDefaults() map[string]any {
	return map[string]any{
		"current_profile":         nil,
		"scoped_current":          map[string]any{},
		"overlays":                map[string]any{},
		"overlay_default_weight":  1000,
		"overlays_allowed":        true,
		"precedence":              map[string]any{"winner": "higher-weight", "placement": "winner-last"},
		"forms":                   map[string]any{},
		"system_prompt_files":     map[string]any{},
		"targets":                 map[string]any{},
		"isolation":               map[string]any{},
		"xdg_seed_allowlist":      []any{"git", "gh", "ssh"},
		"passable_env_names":      nil,
		"mcp_package_allowlist":   []any{},
		"shadow_acknowledged":     []any{},
		"secret_material_waivers": []any{},
		"backup_retention":        5,
		"require_current_profile": nil,
		"in_place_mode":           map[string]any{},
	}
}

// managerConfigV2EveryKnob sets every environments §12.1 knob to a non-default
// value so that the positive case exercises every grammar the schema encodes.
func managerConfigV2EveryKnob() map[string]any {
	return map[string]any{
		"current_profile": "companyA",
		"scoped_current":  map[string]any{"pi": "personal", "xcode-coding-assistant": "companyA"},
		"overlays": map[string]any{
			"companyA": []any{
				map[string]any{"source": "https://github.com/example/personal-context", "range": "^1.2", "weight": 2000},
				map[string]any{"source": "https://github.com/example/team-context", "tag": "v2.0.0", "directory": "packages/team"},
				map[string]any{"source": "/Users/operator/context"},
			},
		},
		"overlay_default_weight": 500,
		"overlays_allowed":       false,
		"precedence":             map[string]any{"winner": "lower-weight", "placement": "winner-first"},
		"forms":                  map[string]any{"claude_code": "referenced", "opencode": "monolithic"},
		"system_prompt_files":    map[string]any{"companyA": map[string]any{"pi": "append"}},
		"targets": map[string]any{
			"xcode-coding-assistant": map[string]any{"participation": "enabled", "consented": true},
		},
		"isolation":             map[string]any{"companyA": map[string]any{"codex_cli": "isolated", "pi": "shared"}},
		"xdg_seed_allowlist":    []any{"git", "gh"},
		"passable_env_names":    []any{"FIGMA_API_KEY", "GITHUB_TOKEN"},
		"mcp_package_allowlist": []any{"https://github.com/example/figma-devmode-mcp"},
		"shadow_acknowledged":   []any{map[string]any{"env": "pi", "path": "AGENTS.override.md"}},
		"secret_material_waivers": []any{
			map[string]any{
				"pin": strings.Repeat("cd", 20), "file": "context/root.md",
				"span": []any{120, 164}, "reason": "documented placeholder token in the onboarding example",
			},
		},
		"backup_retention":        0,
		"require_current_profile": "companyA",
		"in_place_mode":           map[string]any{"codex_cli": "copied"},
	}
}

func validManagerConfigV2() map[string]any {
	return map[string]any{
		"schema_version": 2, "skills_root": "/tmp/skills", "preferred_locale": nil,
		"projects":         map[string]any{"app": map[string]any{"path": "/tmp/app", "project_alias": nil}},
		"audit_registries": []any{map[string]any{"name": "primary", "url": "HTTPS://registry.example"}},
		"audit":            map[string]any{"cache_ttl_seconds": 0, "offline_grace_seconds": 0},
		"environments":     managerConfigV2EveryKnob(),
	}
}

// managerConfigV2SchemaExamples carries one negative per closed-object rule and
// one per value grammar of the `environments` object, plus the positive shapes
// a schema-1 reader would have accepted: minimal, and an empty `environments`.
func managerConfigV2SchemaExamples(valid map[string]any) []schemaExample {
	withEnvironments := func(mutate func(env map[string]any)) map[string]any {
		config := deepCloneMap(valid)
		env := config["environments"].(map[string]any)
		mutate(env)
		return config
	}
	withKnob := func(knob string, value any) map[string]any {
		return withEnvironments(func(env map[string]any) { env[knob] = value })
	}
	withOverlay := func(overlay map[string]any) map[string]any {
		return withKnob("overlays", map[string]any{"companyA": []any{overlay}})
	}
	minimal := map[string]any{"schema_version": 2, "skills_root": "/tmp/skills", "projects": map[string]any{}}
	emptyEnvironments := deepCloneMap(minimal)
	emptyEnvironments["environments"] = map[string]any{}
	schemaOne := deepCloneMap(valid)
	schemaOne["schema_version"] = 1
	return []schemaExample{
		{name: "valid-minimal", valid: true, instance: minimal},
		{name: "valid-empty-environments", valid: true, instance: emptyEnvironments},
		{name: "valid-overlay-path-source", valid: true, instance: withOverlay(map[string]any{"source": "/Users/operator/context"})},
		{name: "valid-overlay-path-windows-backslash", valid: true, instance: withOverlay(map[string]any{"source": "C:\\Users\\operator\\context"})},
		{name: "valid-overlay-path-windows-slash", valid: true, instance: withOverlay(map[string]any{"source": "C:/Users/operator/context"})},
		{name: "valid-overlay-path-windows-lowercase-drive", valid: true, instance: withOverlay(map[string]any{"source": "c:\\users\\operator\\context"})},
		{name: "valid-overlay-path-relative", valid: true, instance: withOverlay(map[string]any{"source": "packages/team-context"})},
		{name: "valid-overlay-path-colon-later-segment", valid: true, instance: withOverlay(map[string]any{"source": "packages/team:context"})},
		{name: "valid-overlay-path-windows-double-slash", valid: true, instance: withOverlay(map[string]any{"source": "C://Users/operator/context"})},
		{name: "valid-overlay-git-single-letter-host", valid: true, instance: withOverlay(map[string]any{"source": "c:example/team-context", "range": "^1.2"})},
		{name: "valid-overlay-git-scp", valid: true, instance: withOverlay(map[string]any{"source": "git@github.com:example/team-context", "range": "^1.2"})},
		{name: "valid-overlay-git-scp-no-user", valid: true, instance: withOverlay(map[string]any{"source": "github.com:example/team-context", "tag": "v2.0.0"})},
		{name: "valid-overlay-git-ssh-uppercase", valid: true, instance: withOverlay(map[string]any{"source": "SSH://github.com/example/personal-context", "range": "^1.2"})},
		{name: "valid-overlay-git-git-uppercase", valid: true, instance: withOverlay(map[string]any{"source": "GIT://github.com/example/team-context", "tag": "v2.0.0"})},
		{name: "valid-overlay-git-http-uppercase", valid: true, instance: withOverlay(map[string]any{"source": "HTTP://github.com/example/extra-context", "range": "^2.0"})},
		{name: "valid-overlay-git-https-uppercase", valid: true, instance: withOverlay(map[string]any{"source": "HTTPS://github.com/example/x", "revision": strings.Repeat("ab", 20)})},
		{name: "invalid-schema-version-1", instance: schemaOne},
		// closed-object rules
		{name: "invalid-unknown-environments-field", instance: withKnob("overlay_weight", 1)},
		{name: "invalid-unknown-overlay-field", instance: withOverlay(map[string]any{"source": "https://github.com/example/x", "range": "^1", "branch": "main"})},
		{name: "invalid-unknown-precedence-field", instance: withKnob("precedence", map[string]any{"winner": "higher-weight", "order": "last"})},
		{name: "invalid-unknown-system-prompt-environment", instance: withKnob("system_prompt_files", map[string]any{"companyA": map[string]any{"codex_cli": "append"}})},
		{name: "invalid-unknown-target-field", instance: withKnob("targets", map[string]any{"xcode-coding-assistant": map[string]any{"participation": "auto", "home": "/tmp"}})},
		{name: "invalid-unknown-shadow-field", instance: withKnob("shadow_acknowledged", []any{map[string]any{"env": "pi", "path": "AGENTS.override.md", "reason": "x"}})},
		{name: "invalid-unknown-waiver-field", instance: withKnob("secret_material_waivers", []any{map[string]any{"pin": strings.Repeat("cd", 20), "file": "context/root.md", "span": []any{1, 2}, "reason": "x", "expires": "never"}})},
		// value grammars, one per knob
		{name: "invalid-current-profile-grammar", instance: withKnob("current_profile", "Company A")},
		{name: "invalid-scoped-current-value", instance: withKnob("scoped_current", map[string]any{"pi": "-personal"})},
		{name: "invalid-overlay-two-requirement-forms", instance: withOverlay(map[string]any{"source": "https://github.com/example/x", "range": "^1", "tag": "v1.0.0"})},
		{name: "invalid-overlay-no-requirement-form", instance: withOverlay(map[string]any{"source": "https://github.com/example/x"})},
		{name: "invalid-overlay-path-requirement-form", instance: withOverlay(map[string]any{"source": "/Users/operator/context", "revision": strings.Repeat("ab", 20)})},
		{name: "invalid-overlay-path-windows-requirement-form", instance: withOverlay(map[string]any{"source": "C:\\Users\\operator\\context", "revision": strings.Repeat("ab", 20)})},
		{name: "invalid-overlay-path-windows-slash-requirement-form", instance: withOverlay(map[string]any{"source": "C:/Users/operator/context", "range": "^1.2"})},
		{name: "invalid-overlay-path-relative-requirement-form", instance: withOverlay(map[string]any{"source": "packages/team-context", "tag": "v2.0.0"})},
		{name: "invalid-overlay-file-url-with-form", instance: withOverlay(map[string]any{"source": "file:///Users/operator/context", "revision": strings.Repeat("ab", 20)})},
		{name: "invalid-overlay-git-scp-no-requirement-form", instance: withOverlay(map[string]any{"source": "git@github.com:example/team-context"})},
		{name: "invalid-overlay-git-uppercase-no-requirement-form", instance: withOverlay(map[string]any{"source": "HTTPS://github.com/example/x"})},
		{name: "invalid-overlay-unknown-scheme", instance: withOverlay(map[string]any{"source": "svn://github.com/example/x"})},
		{name: "invalid-overlay-file-url", instance: withOverlay(map[string]any{"source": "file:///Users/operator/context"})},
		{name: "invalid-overlay-scp-host-grammar", instance: withOverlay(map[string]any{"source": "git@my_host:example/x"})},
		{name: "invalid-overlay-scp-backslash-path", instance: withOverlay(map[string]any{"source": "github.com:\\example\\x"})},
		{name: "invalid-overlay-bare-drive-letter", instance: withOverlay(map[string]any{"source": "C:"})},
		{name: "invalid-overlay-scp-host-grammar-no-user", instance: withOverlay(map[string]any{"source": "my_host:example/x"})},
		{name: "invalid-overlay-scp-host-grammar-with-form", instance: withOverlay(map[string]any{"source": "git@my_host:example/x", "range": "^1.2"})},
		{name: "invalid-overlay-path-directory", instance: withOverlay(map[string]any{"source": "/Users/operator/context", "directory": "packages/team"})},
		{name: "invalid-overlay-unknown-scheme-with-form", instance: withOverlay(map[string]any{"source": "svn://github.com/example/x", "revision": strings.Repeat("ab", 20)})},
		{name: "invalid-overlay-revision-grammar", instance: withOverlay(map[string]any{"source": "https://github.com/example/x", "revision": "HEAD"})},
		{name: "invalid-overlay-range-grammar", instance: withOverlay(map[string]any{"source": "https://github.com/example/x", "range": "^1.0.0 (latest)"})},
		{name: "invalid-overlay-tag-grammar", instance: withOverlay(map[string]any{"source": "https://github.com/example/x", "tag": "v1..0"})},
		{name: "invalid-overlay-empty-source", instance: withOverlay(map[string]any{"source": "", "range": "^1"})},
		{name: "invalid-overlay-directory-traversal", instance: withOverlay(map[string]any{"source": "https://github.com/example/x", "range": "^1", "directory": "../outside"})},
		{name: "invalid-overlay-negative-weight", instance: withOverlay(map[string]any{"source": "https://github.com/example/x", "range": "^1", "weight": -1})},
		{name: "invalid-overlay-default-weight-negative", instance: withKnob("overlay_default_weight", -1)},
		{name: "invalid-overlays-allowed-type", instance: withKnob("overlays_allowed", "yes")},
		{name: "invalid-precedence-winner", instance: withKnob("precedence", map[string]any{"winner": "later"})},
		{name: "invalid-precedence-placement", instance: withKnob("precedence", map[string]any{"placement": "last"})},
		{name: "invalid-form-value", instance: withKnob("forms", map[string]any{"claude_code": "split"})},
		{name: "invalid-system-prompt-files-value", instance: withKnob("system_prompt_files", map[string]any{"companyA": map[string]any{"pi": "on"}})},
		{name: "invalid-target-participation", instance: withKnob("targets", map[string]any{"xcode-coding-assistant": map[string]any{"participation": "always"}})},
		{name: "invalid-target-consented-type", instance: withKnob("targets", map[string]any{"xcode-coding-assistant": map[string]any{"consented": "yes"}})},
		{name: "invalid-isolation-value", instance: withKnob("isolation", map[string]any{"companyA": map[string]any{"codex_cli": "private"}})},
		{name: "invalid-xdg-seed-entry-path", instance: withKnob("xdg_seed_allowlist", []any{"git/config"})},
		{name: "invalid-xdg-seed-entry-opencode", instance: withKnob("xdg_seed_allowlist", []any{"opencode"})},
		{name: "invalid-passable-env-name-grammar", instance: withKnob("passable_env_names", []any{"FIGMA API KEY"})},
		{name: "invalid-mcp-package-allowlist-duplicate", instance: withKnob("mcp_package_allowlist", []any{"https://github.com/example/mcp", "https://github.com/example/mcp"})},
		{name: "invalid-shadow-acknowledged-missing-path", instance: withKnob("shadow_acknowledged", []any{map[string]any{"env": "pi"}})},
		{name: "invalid-waiver-span-arity", instance: withKnob("secret_material_waivers", []any{map[string]any{"pin": strings.Repeat("cd", 20), "file": "context/root.md", "span": []any{1}, "reason": "x"}})},
		{name: "invalid-waiver-pin-grammar", instance: withKnob("secret_material_waivers", []any{map[string]any{"pin": "sha256:" + strings.Repeat("cd", 32), "file": "context/root.md", "span": []any{1, 2}, "reason": "x"}})},
		{name: "invalid-backup-retention-negative", instance: withKnob("backup_retention", -1)},
		{name: "invalid-require-current-profile-grammar", instance: withKnob("require_current_profile", "")},
		{name: "invalid-in-place-mode-value", instance: withKnob("in_place_mode", map[string]any{"codex_cli": "managed-home"})},
	}
}

// managerConfigV2Vectors extends `vectors/manager-config.json` for schema 2.
// `expected.environments` is the effective knob set after schema defaults are
// applied, so a reader proves it fills exactly the §12.1 defaults.
func managerConfigV2Vectors() []any {
	base := func() map[string]any {
		return map[string]any{"schema_version": 2, "skills_root": "./skills", "projects": map[string]any{}}
	}
	withEnvironments := func(env map[string]any) map[string]any {
		config := base()
		config["environments"] = env
		return config
	}
	expectedWith := func(overrides map[string]any) map[string]any {
		expected := managerConfigV2EnvironmentDefaults()
		for key, value := range overrides {
			expected[key] = value
		}
		return expected
	}
	everyKnob := managerConfigV2EveryKnob()
	schemaOneWithEnvironments := map[string]any{
		"schema_version": 1, "skills_root": "./skills", "projects": map[string]any{},
		"environments": map[string]any{"backup_retention": 5},
	}
	partial := map[string]any{
		"current_profile":  "companyA",
		"backup_retention": 0,
		"precedence":       map[string]any{"winner": "lower-weight"},
		"forms":            map[string]any{"claude_code": "referenced"},
	}
	return []any{
		map[string]any{
			"name": "schema2-minimal-defaults", "input": base(), "valid": true,
			"expected": map[string]any{
				"default_agents": []any{"codex_cli"}, "adapter_mode": "auto",
				"environments": managerConfigV2EnvironmentDefaults(),
			},
		},
		map[string]any{
			"name": "schema2-empty-environments-defaults", "input": withEnvironments(map[string]any{}), "valid": true,
			"expected": map[string]any{"environments": managerConfigV2EnvironmentDefaults()},
		},
		map[string]any{
			"name": "schema2-partial-knobs-fill-defaults", "input": withEnvironments(partial), "valid": true,
			"expected": map[string]any{
				"environments": expectedWith(map[string]any{
					"current_profile":  "companyA",
					"backup_retention": 0,
					"precedence":       map[string]any{"winner": "lower-weight", "placement": "winner-last"},
					"forms":            map[string]any{"claude_code": "referenced"},
				}),
			},
		},
		map[string]any{
			"name": "schema2-every-knob", "input": withEnvironments(everyKnob), "valid": true,
			"expected": map[string]any{"environments": everyKnob},
		},
		map[string]any{"name": "schema1-rejects-environments", "input": schemaOneWithEnvironments, "valid": false},
		map[string]any{"name": "schema2-unknown-environments-field", "input": withEnvironments(map[string]any{"overlay_weight": 1}), "valid": false},
		map[string]any{"name": "schema2-overlay-two-requirement-forms", "input": withEnvironments(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "https://github.com/example/x", "range": "^1", "tag": "v1.0.0"}}}}), "valid": false},
		map[string]any{
			"name": "schema2-overlay-path-source", "input": withEnvironments(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "/Users/operator/context"}}}}), "valid": true,
			"expected": map[string]any{"environments": expectedWith(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "/Users/operator/context"}}}})},
		},
		map[string]any{"name": "schema2-overlay-path-requirement-form", "input": withEnvironments(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "/Users/operator/context", "revision": strings.Repeat("ab", 20)}}}}), "valid": false},
		map[string]any{
			"name": "schema2-overlay-path-windows-backslash", "input": withEnvironments(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "C:\\Users\\operator\\context"}}}}), "valid": true,
			"expected": map[string]any{"environments": expectedWith(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "C:\\Users\\operator\\context"}}}})},
		},
		map[string]any{
			"name": "schema2-overlay-path-windows-slash", "input": withEnvironments(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "C:/Users/operator/context"}}}}), "valid": true,
			"expected": map[string]any{"environments": expectedWith(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "C:/Users/operator/context"}}}})},
		},
		map[string]any{
			"name": "schema2-overlay-path-relative", "input": withEnvironments(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "packages/team-context"}}}}), "valid": true,
			"expected": map[string]any{"environments": expectedWith(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "packages/team-context"}}}})},
		},
		map[string]any{
			"name": "schema2-overlay-path-colon-later-segment", "input": withEnvironments(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "packages/team:context"}}}}), "valid": true,
			"expected": map[string]any{"environments": expectedWith(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "packages/team:context"}}}})},
		},
		map[string]any{
			"name": "schema2-overlay-path-windows-lowercase-drive", "input": withEnvironments(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "c:\\users\\operator\\context"}}}}), "valid": true,
			"expected": map[string]any{"environments": expectedWith(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "c:\\users\\operator\\context"}}}})},
		},
		map[string]any{
			"name": "schema2-overlay-path-windows-double-slash", "input": withEnvironments(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "C://Users/operator/context"}}}}), "valid": true,
			"expected": map[string]any{"environments": expectedWith(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "C://Users/operator/context"}}}})},
		},
		map[string]any{
			"name": "schema2-overlay-git-single-letter-host", "input": withEnvironments(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "c:example/team-context", "range": "^1.2"}}}}), "valid": true,
			"expected": map[string]any{"environments": expectedWith(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "c:example/team-context", "range": "^1.2"}}}})},
		},
		map[string]any{
			"name": "schema2-overlay-git-scp", "input": withEnvironments(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "git@github.com:example/team-context", "range": "^1.2"}}}}), "valid": true,
			"expected": map[string]any{"environments": expectedWith(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "git@github.com:example/team-context", "range": "^1.2"}}}})},
		},
		map[string]any{
			"name": "schema2-overlay-git-scp-no-user", "input": withEnvironments(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "github.com:example/team-context", "tag": "v2.0.0"}}}}), "valid": true,
			"expected": map[string]any{"environments": expectedWith(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "github.com:example/team-context", "tag": "v2.0.0"}}}})},
		},
		map[string]any{
			"name": "schema2-overlay-git-ssh-uppercase", "input": withEnvironments(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "SSH://github.com/example/personal-context", "range": "^1.2"}}}}), "valid": true,
			"expected": map[string]any{"environments": expectedWith(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "SSH://github.com/example/personal-context", "range": "^1.2"}}}})},
		},
		map[string]any{
			"name": "schema2-overlay-git-git-uppercase", "input": withEnvironments(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "GIT://github.com/example/team-context", "tag": "v2.0.0"}}}}), "valid": true,
			"expected": map[string]any{"environments": expectedWith(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "GIT://github.com/example/team-context", "tag": "v2.0.0"}}}})},
		},
		map[string]any{
			"name": "schema2-overlay-git-http-uppercase", "input": withEnvironments(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "HTTP://github.com/example/extra-context", "range": "^2.0"}}}}), "valid": true,
			"expected": map[string]any{"environments": expectedWith(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "HTTP://github.com/example/extra-context", "range": "^2.0"}}}})},
		},
		map[string]any{
			"name": "schema2-overlay-git-https-uppercase", "input": withEnvironments(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "HTTPS://github.com/example/x", "revision": strings.Repeat("ab", 20)}}}}), "valid": true,
			"expected": map[string]any{"environments": expectedWith(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "HTTPS://github.com/example/x", "revision": strings.Repeat("ab", 20)}}}})},
		},
		map[string]any{"name": "schema2-overlay-file-url", "input": withEnvironments(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "file:///Users/operator/context"}}}}), "valid": false},
		map[string]any{"name": "schema2-overlay-scp-backslash-path", "input": withEnvironments(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "github.com:\\example\\x"}}}}), "valid": false},
		map[string]any{"name": "schema2-overlay-bare-drive-letter", "input": withEnvironments(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "C:"}}}}), "valid": false},
		map[string]any{"name": "schema2-overlay-scp-host-grammar", "input": withEnvironments(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "git@my_host:example/x"}}}}), "valid": false},
		map[string]any{"name": "schema2-overlay-scp-host-grammar-with-form", "input": withEnvironments(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "git@my_host:example/x", "range": "^1.2"}}}}), "valid": false},
		map[string]any{"name": "schema2-overlay-path-directory", "input": withEnvironments(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "/Users/operator/context", "directory": "packages/team"}}}}), "valid": false},
		map[string]any{"name": "schema2-overlay-path-windows-requirement-form", "input": withEnvironments(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "C:\\Users\\operator\\context", "revision": strings.Repeat("ab", 20)}}}}), "valid": false},
		map[string]any{"name": "schema2-overlay-path-windows-slash-requirement-form", "input": withEnvironments(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "C:/Users/operator/context", "range": "^1.2"}}}}), "valid": false},
		map[string]any{"name": "schema2-overlay-path-relative-requirement-form", "input": withEnvironments(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "packages/team-context", "tag": "v2.0.0"}}}}), "valid": false},
		map[string]any{"name": "schema2-overlay-file-url-with-form", "input": withEnvironments(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "file:///Users/operator/context", "revision": strings.Repeat("ab", 20)}}}}), "valid": false},
		map[string]any{"name": "schema2-overlay-git-scp-no-requirement-form", "input": withEnvironments(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "git@github.com:example/team-context"}}}}), "valid": false},
		map[string]any{"name": "schema2-overlay-git-uppercase-no-requirement-form", "input": withEnvironments(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "HTTPS://github.com/example/x"}}}}), "valid": false},
		map[string]any{"name": "schema2-overlay-unknown-scheme", "input": withEnvironments(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "svn://github.com/example/x"}}}}), "valid": false},
		map[string]any{"name": "schema2-overlay-unknown-scheme-with-form", "input": withEnvironments(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "svn://github.com/example/x", "revision": strings.Repeat("ab", 20)}}}}), "valid": false},
		map[string]any{"name": "schema2-overlay-range-grammar", "input": withEnvironments(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "https://github.com/example/x", "range": "^1.0.0 (latest)"}}}}), "valid": false},
		map[string]any{"name": "schema2-overlay-tag-grammar", "input": withEnvironments(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "https://github.com/example/x", "tag": "v1..0"}}}}), "valid": false},
		map[string]any{"name": "schema2-overlay-empty-source", "input": withEnvironments(map[string]any{"overlays": map[string]any{"companyA": []any{map[string]any{"source": "", "range": "^1"}}}}), "valid": false},
		map[string]any{"name": "schema2-precedence-winner-grammar", "input": withEnvironments(map[string]any{"precedence": map[string]any{"winner": "later-overrides-earlier"}}), "valid": false},
		map[string]any{"name": "schema2-negative-backup-retention", "input": withEnvironments(map[string]any{"backup_retention": -1}), "valid": false},
		map[string]any{"name": "schema2-isolation-value-grammar", "input": withEnvironments(map[string]any{"isolation": map[string]any{"companyA": map[string]any{"claude_code": "keychain"}}}), "valid": false},
	}
}
