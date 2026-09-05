package main

// systemConfigV2LockableKeys is the environments §12.2 lockable set, spelled as
// the `locked` array of system-config schema 2 spells it.
var systemConfigV2LockableKeys = []string{
	"overlays_allowed", "precedence", "mcp_package_allowlist",
	"passable_env_names", "require_current_profile", "isolation",
}

// systemConfigV2EveryKey sets every §12.2 lockable knob to a non-default value
// so that the positive case exercises every grammar the schema encodes.
// `isolation` is `shared` only: §12.2 makes it lockable in that direction alone.
func systemConfigV2EveryKey() map[string]any {
	return map[string]any{
		"overlays_allowed":        false,
		"precedence":              map[string]any{"winner": "lower-weight", "placement": "winner-first"},
		"mcp_package_allowlist":   []any{"https://github.com/example/figma-devmode-mcp"},
		"passable_env_names":      []any{"FIGMA_API_KEY", "GITHUB_TOKEN"},
		"require_current_profile": "companyA",
		"isolation":               map[string]any{"companyA": map[string]any{"claude_code": "shared", "codex_cli": "shared"}},
	}
}

func validSystemConfigV2() map[string]any {
	locked := []any{"audit", "allowed_sources"}
	for _, key := range systemConfigV2LockableKeys {
		locked = append(locked, "environments."+key)
	}
	return map[string]any{
		"schema_version":   2,
		"locked":           locked,
		"audit":            map[string]any{},
		"allowed_sources":  []any{"https://github.com/example/"},
		"preferred_locale": "en",
		"environments":     systemConfigV2EveryKey(),
	}
}

// systemConfigV2SchemaExamples carries the positive shapes a schema-1 reader
// would have accepted (minimal, an empty `environments`, a schema-1 `locked`
// set) and one negative per closed-object rule, per §12.2 grammar, and per
// `locked` entry that is not a §12.2 key.
func systemConfigV2SchemaExamples(valid map[string]any) []schemaExample {
	withKnob := func(knob string, value any) map[string]any {
		config := deepCloneMap(valid)
		env := config["environments"].(map[string]any)
		env[knob] = value
		return config
	}
	withLocked := func(locked ...any) map[string]any {
		config := deepCloneMap(valid)
		config["locked"] = locked
		return config
	}
	minimal := map[string]any{"schema_version": 2}
	emptyEnvironments := map[string]any{"schema_version": 2, "environments": map[string]any{}}
	schemaOneLocked := map[string]any{"schema_version": 2, "locked": []any{"audit"}, "audit": map[string]any{}}
	schemaOne := deepCloneMap(valid)
	schemaOne["schema_version"] = 1
	return []schemaExample{
		{name: "valid-minimal", valid: true, instance: minimal},
		{name: "valid-empty-environments", valid: true, instance: emptyEnvironments},
		{name: "valid-schema-1-locked-set", valid: true, instance: schemaOneLocked},
		{name: "invalid-schema-version-1", instance: schemaOne},
		// closed-object rules
		{name: "invalid-unknown-environments-field", instance: withKnob("overlay_default_weight", 1000)},
		{name: "invalid-unlockable-environments-knob", instance: withKnob("current_profile", "companyA")},
		{name: "invalid-unknown-precedence-field", instance: withKnob("precedence", map[string]any{"winner": "higher-weight", "order": "last"})},
		// `locked` entries
		{name: "invalid-locked-unknown-environments-key", instance: withLocked("environments.overlays")},
		{name: "invalid-locked-unlockable-environments-key", instance: withLocked("environments.current_profile")},
		{name: "invalid-locked-bare-environments", instance: withLocked("environments")},
		{name: "invalid-locked-unprefixed-knob", instance: withLocked("overlays_allowed")},
		{name: "invalid-locked-duplicate", instance: withLocked("environments.isolation", "environments.isolation")},
		// value grammars, one per §12.2 key
		{name: "invalid-overlays-allowed-type", instance: withKnob("overlays_allowed", "yes")},
		{name: "invalid-precedence-winner", instance: withKnob("precedence", map[string]any{"winner": "later"})},
		{name: "invalid-precedence-placement", instance: withKnob("precedence", map[string]any{"placement": "last"})},
		{name: "invalid-mcp-package-allowlist-duplicate", instance: withKnob("mcp_package_allowlist", []any{"https://github.com/example/mcp", "https://github.com/example/mcp"})},
		{name: "invalid-mcp-package-allowlist-empty-entry", instance: withKnob("mcp_package_allowlist", []any{""})},
		{name: "invalid-passable-env-name-grammar", instance: withKnob("passable_env_names", []any{"FIGMA API KEY"})},
		{name: "invalid-require-current-profile-grammar", instance: withKnob("require_current_profile", "")},
		{name: "invalid-isolation-isolated-direction", instance: withKnob("isolation", map[string]any{"companyA": map[string]any{"claude_code": "isolated"}})},
		{name: "invalid-isolation-value", instance: withKnob("isolation", map[string]any{"companyA": map[string]any{"codex_cli": "private"}})},
		{name: "invalid-isolation-profile-grammar", instance: withKnob("isolation", map[string]any{"Company A": map[string]any{"codex_cli": "shared"}})},
	}
}
