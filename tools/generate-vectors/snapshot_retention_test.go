package main

import (
	"bytes"
	"os"
	"os/exec"
	"path/filepath"
	"testing"
)

// Run the real generator with the retention artifact absent. Checking drift
// against an already populated tree cannot prove that it generates the file.
func TestSnapshotRetentionCleanGeneration(t *testing.T) {
	root := t.TempDir()
	for _, dir := range []string{"conformance", "protocol", "docs", "schemas", "release"} {
		if err := os.CopyFS(filepath.Join(root, dir), os.DirFS(filepath.Join("..", "..", dir))); err != nil {
			t.Fatal(err)
		}
	}
	rel := filepath.Join("conformance", "v1", "vectors", "snapshot-retention.json")
	want, err := os.ReadFile(filepath.Join(root, rel))
	if err != nil {
		t.Fatal(err)
	}
	if err := os.Remove(filepath.Join(root, rel)); err != nil {
		t.Fatal(err)
	}
	for attempt := 0; attempt < 2; attempt++ {
		cmd := exec.Command("go", "run", ".", "-root", root)
		if out, err := cmd.CombinedOutput(); err != nil {
			t.Fatalf("generator: %v\n%s", err, out)
		}
		got, err := os.ReadFile(filepath.Join(root, rel))
		if err != nil {
			t.Fatalf("generator did not recreate retention vector: %v", err)
		}
		if !bytes.Equal(got, want) {
			t.Fatal("generated retention vector differs from the committed artifact")
		}
	}
}
