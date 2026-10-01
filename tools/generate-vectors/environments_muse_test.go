package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"testing"
)

func TestMuseGeneratedFixtures(t *testing.T) {
	root := t.TempDir()
	writeMuseEnvironmentVectors(filepath.Join(root, "vectors"), filepath.Join(root, "expected", "environments-muse"))
	read := func(path string) map[string]any {
		t.Helper()
		payload, err := os.ReadFile(filepath.Join(root, path))
		if err != nil {
			t.Fatal(err)
		}
		var result map[string]any
		if err := json.Unmarshal(payload, &result); err != nil {
			t.Fatal(err)
		}
		return result
	}
	fragment := read("expected/environments-muse/muse-fragment.json")
	want := map[string]any{
		"XDG_CONFIG_HOME": "/manager/environments/companyA/muse/config",
		"XDG_DATA_HOME":   "/manager/environments/companyA/muse/data",
		"XDG_STATE_HOME":  "/manager/environments/companyA/muse/state",
		"XDG_CACHE_HOME":  "/manager/environments/companyA/muse/cache",
	}
	if fragment["fragment"] != "launch-env-fragment-v3" || !reflect.DeepEqual(fragment["env"], want) {
		t.Fatalf("wrong Muse fragment: %v", fragment)
	}
	for _, forbidden := range []string{"system_prompt", "mcp", "HOME"} {
		if _, exists := fragment[forbidden]; exists {
			t.Fatalf("invented or forbidden member: %s", forbidden)
		}
	}
	vector := read("vectors/environments-muse.json")
	if len(vector["cases"].([]any)) != 16 {
		t.Fatal("link-state coverage must be 16/16")
	}
	marker := read("expected/environments-muse/muse-marker.json")
	if len(marker["surfaces"].(map[string]any)) != 0 {
		t.Fatal("Muse must not claim unverified context surfaces")
	}
}

func TestMuseCredentialRefusals(t *testing.T) {
	for _, state := range []string{"temp-rename-fork", "retargeted-link", "dangling-target", "metadata-unreadable", "target-unreadable"} {
		for _, repair := range []bool{false, true} {
			got := musePassthroughExpectation(state, repair)
			if got["emit_fragment"] != false || got["action"] != "none" || got["credential_bytes_changed"] != false {
				t.Fatalf("%s repair=%v silently admitted or rewrote credentials: %v", state, repair, got)
			}
		}
	}
}
