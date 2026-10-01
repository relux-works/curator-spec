package main

import (
	"bytes"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

// TestGeneratorPreservesHandAuthoredSchemaCases drives the real generator
// entry point against a copy of the repository and proves that regeneration
// never deletes schema-case fixtures it did not emit itself, such as the
// released agent-environment-marker-v1 and launch-env-fragment-v1 cases.
func TestGeneratorPreservesHandAuthoredSchemaCases(t *testing.T) {
	if testing.Short() {
		t.Skip("runs the full generator")
	}
	repo, err := filepath.Abs(filepath.Join("..", ".."))
	if err != nil {
		t.Fatal(err)
	}
	root := t.TempDir()
	entries, err := os.ReadDir(repo)
	if err != nil {
		t.Fatal(err)
	}
	for _, entry := range entries {
		if name := entry.Name(); name != ".git" && name != ".temp" && name != ".task-board" {
			copyTree(t, filepath.Join(repo, name), filepath.Join(root, name))
		}
	}
	caseRoot := filepath.Join(root, "conformance", "v1", "schema-cases")
	released := []string{
		"agent-environment-marker-v1/valid-no-composition.json",
		"launch-env-fragment-v1/valid-file-channels.json",
	}
	sentinel := filepath.Join(caseRoot, "hand-authored-sentinel-v1", "valid.json")
	must(os.MkdirAll(filepath.Dir(sentinel), 0o755))
	must(os.WriteFile(sentinel, []byte("{}\n"), 0o644))
	// Remove the copied Muse family so a missing production call cannot be
	// satisfied by pre-existing checkout fixtures.
	for _, path := range []string{
		"conformance/v1/vectors/environments-muse.json",
		"conformance/v1/expected/environments-muse/muse-home-layout.json",
		"conformance/v1/expected/environments-muse/muse-fragment.json",
		"conformance/v1/expected/environments-muse/muse-marker.json",
		"conformance/v1/schema-cases/launch-env-fragment-v3",
		"conformance/v1/schema-cases/agent-environment-marker-v3/valid-muse-shared.json",
	} {
		must(os.RemoveAll(filepath.Join(root, path)))
	}

	cmd := exec.Command("go", "run", ".", "-root", root)
	var out bytes.Buffer
	cmd.Stdout, cmd.Stderr = &out, &out
	if err := cmd.Run(); err != nil {
		t.Fatalf("generator failed: %v\n%s", err, out.String())
	}
	// Assert the real CLI entry emits the Muse family and schema cases,
	// rather than proving only that an uncalled helper can emit them.
	for _, path := range []string{
		"conformance/v1/vectors/environments-muse.json",
		"conformance/v1/expected/environments-muse/muse-home-layout.json",
		"conformance/v1/expected/environments-muse/muse-fragment.json",
		"conformance/v1/expected/environments-muse/muse-marker.json",
		"conformance/v1/schema-cases/launch-env-fragment-v3/invalid-HOME-added.json",
		"conformance/v1/schema-cases/agent-environment-marker-v3/valid-muse-shared.json",
	} {
		if _, err := os.Stat(filepath.Join(root, path)); err != nil {
			t.Fatalf("generator CLI did not emit %s: %v", path, err)
		}
	}
	for _, rel := range append(released, "hand-authored-sentinel-v1/valid.json") {
		want, err := os.ReadFile(filepath.Join(repo, "conformance", "v1", "schema-cases", rel))
		if strings.HasPrefix(rel, "hand-authored") {
			want, err = []byte("{}\n"), nil
		}
		if err != nil {
			t.Fatal(err)
		}
		got, err := os.ReadFile(filepath.Join(caseRoot, rel))
		if err != nil {
			t.Fatalf("regeneration deleted hand-authored fixture %s: %v", rel, err)
		}
		if !bytes.Equal(got, want) {
			t.Fatalf("regeneration rewrote hand-authored fixture %s", rel)
		}
	}
}

func copyTree(t *testing.T, src, dst string) {
	t.Helper()
	info, err := os.Lstat(src)
	if err != nil {
		t.Fatal(err)
	}
	if !info.IsDir() && !info.Mode().IsRegular() {
		return
	}
	err = filepath.Walk(src, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		rel, _ := filepath.Rel(src, path)
		target := filepath.Join(dst, rel)
		if info.IsDir() {
			return os.MkdirAll(target, 0o755)
		}
		if !info.Mode().IsRegular() {
			return nil
		}
		data, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		return os.WriteFile(target, data, info.Mode().Perm())
	})
	if err != nil {
		t.Fatal(err)
	}
}
