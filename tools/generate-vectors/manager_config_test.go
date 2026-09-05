package main

import (
	"bytes"
	"encoding/json"
	"path/filepath"
	"sort"
	"strings"
	"testing"
)

// managerConfigV2Knobs is the environments §12.1 knob list as schema
// properties: the first segment of every table row, spelled byte for byte.
var managerConfigV2Knobs = []string{
	"current_profile", "scoped_current", "overlays", "overlay_default_weight", "overlays_allowed",
	"precedence", "forms", "system_prompt_files", "targets", "isolation", "xdg_seed_allowlist",
	"passable_env_names", "mcp_package_allowlist", "shadow_acknowledged", "secret_material_waivers",
	"backup_retention", "require_current_profile", "in_place_mode",
}

func TestManagerConfigV2IsSchemaOnePlusOneClosedEnvironmentsObject(t *testing.T) {
	root := repositoryRoot(t)
	schema := readObject(t, filepath.Join(root, "schemas", "v1", "manager-config-v2.schema.json"))
	assertPropertySet(t, "manager config v2", schema, []string{
		"schema_version", "skills_root", "default_agents", "preferred_locale", "adapter_mode",
		"worktree_alias_pattern", "projects", "allowed_sources", "audit", "audit_registries",
		"disable_builtin_registries", "environments",
	})
	// `env` is absent from this list only because environments §12.1 spells the
	// `shadow_acknowledged` item as `{ env, path }` — an environment identifier,
	// not a variable map — and the knob names are copied byte for byte.
	assertNoDeclaredProperties(t, "manager config v2", schema, []string{
		"driver", "argv", "args", "environment", "toolchain", "output", "output_path", "output-path",
		"hook", "hooks", "build", "build_policy", "build-policy", "build_policy_override",
		"build-policy-override", "build_policy_overrides", "build-policy-overrides",
	})
	defs := schema["$defs"].(map[string]any)
	environments := defs["environments"].(map[string]any)
	assertPropertySet(t, "manager config v2 environments", environments, managerConfigV2Knobs)
	if environments["additionalProperties"] != false {
		t.Fatalf("the environments object must be closed")
	}
	for _, name := range []string{"overlay", "precedence", "systemPromptFiles", "target", "shadowAcknowledgement", "secretMaterialWaiver"} {
		def, ok := defs[name].(map[string]any)
		if !ok || def["additionalProperties"] != false {
			t.Fatalf("$defs.%s must be a closed object", name)
		}
	}
	for _, key := range []string{"skills_root", "projects", "audit", "audit_registries"} {
		ref, _ := schema["properties"].(map[string]any)[key].(map[string]any)["$ref"].(string)
		if !strings.HasPrefix(ref, "manager-config-v1.schema.json#/properties/") {
			t.Fatalf("schema-2 %s must reuse the schema-1 shape, got %q", key, ref)
		}
	}
}

func TestManagerConfigV2FixturesCoverEveryKnob(t *testing.T) {
	keys := func(value map[string]any) []string {
		var out []string
		for key := range value {
			out = append(out, key)
		}
		sort.Strings(out)
		return out
	}
	want := append([]string(nil), managerConfigV2Knobs...)
	sort.Strings(want)
	if got := keys(managerConfigV2EnvironmentDefaults()); strings.Join(got, ",") != strings.Join(want, ",") {
		t.Fatalf("defaults fixture knobs %v, want %v", got, want)
	}
	if got := keys(managerConfigV2EveryKnob()); strings.Join(got, ",") != strings.Join(want, ",") {
		t.Fatalf("every-knob fixture knobs %v, want %v", got, want)
	}
	valid := validManagerConfigV2()
	defaults := managerConfigV2EnvironmentDefaults()
	for knob, value := range managerConfigV2EveryKnob() {
		if equalJSON(value, defaults[knob]) {
			t.Fatalf("every-knob fixture leaves %s at its default; the positive case would not exercise it", knob)
		}
	}
	examples := managerConfigV2SchemaExamples(valid)
	seen := map[string]bool{}
	mutated := map[string]bool{}
	for _, example := range examples {
		if seen[example.name] {
			t.Fatalf("schema example name repeated: %s", example.name)
		}
		seen[example.name] = true
		if example.valid {
			continue
		}
		instance := example.instance.(map[string]any)
		env, _ := instance["environments"].(map[string]any)
		for knob, value := range env {
			if !equalJSON(value, valid["environments"].(map[string]any)[knob]) {
				mutated[knob] = true
			}
		}
		if len(env) != len(managerConfigV2Knobs) && instance["schema_version"] == 2 {
			// the unknown-field case adds a key; every other negative keeps the knob set
			if len(env) != len(managerConfigV2Knobs)+1 {
				t.Fatalf("negative example %s changes the knob set", example.name)
			}
		}
	}
	for _, knob := range managerConfigV2Knobs {
		if !mutated[knob] {
			t.Fatalf("no negative schema example narrows the grammar of %s", knob)
		}
	}
	vectors := managerConfigV2Vectors()
	versions := map[any]bool{}
	for _, raw := range vectors {
		vector := raw.(map[string]any)
		versions[vector["input"].(map[string]any)["schema_version"]] = true
	}
	if !versions[1] || !versions[2] {
		t.Fatalf("schema-2 vectors must include a schema-1 rejection and schema-2 cases, got %v", versions)
	}
}

func equalJSON(left, right any) bool {
	leftBytes, err := json.Marshal(left)
	if err != nil {
		return false
	}
	rightBytes, err := json.Marshal(right)
	if err != nil {
		return false
	}
	return bytes.Equal(leftBytes, rightBytes)
}
