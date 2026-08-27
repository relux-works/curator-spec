package main

import (
	"crypto/sha256"
	"encoding/hex"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// TestCandidateCasesStayOutOfThePinnedSuite proves the split that keeps a
// released digest stable while an unreleased surface still ships cases. The
// schema set is read from the generator's own table, so a schema added to the
// candidate set without a home under conformance/next fails here.
func TestCandidateCasesStayOutOfThePinnedSuite(t *testing.T) {
	root := repositoryRoot(t)
	type indexEntry struct {
		Schema   string `json:"schema"`
		Instance string `json:"instance"`
	}
	var released, candidate []indexEntry
	readJSON(t, filepath.Join(root, "conformance", "v1", "schema-cases", "index.json"), &released)
	readJSON(t, filepath.Join(root, "conformance", "next", "schema-cases", "index.json"), &candidate)
	if len(candidateSchemaCases) == 0 {
		t.Fatal("the candidate schema-case table is empty")
	}
	for _, entry := range released {
		if candidateSchemaCases[entry.Schema] {
			t.Fatalf("candidate schema %s is indexed under the pinned suite", entry.Schema)
		}
	}
	seen := map[string]bool{}
	for _, entry := range candidate {
		if !candidateSchemaCases[entry.Schema] {
			t.Fatalf("released schema %s is indexed under the candidate suite", entry.Schema)
		}
		seen[entry.Schema] = true
		path := filepath.Join(root, "conformance", "next", "schema-cases", filepath.FromSlash(entry.Instance))
		if _, err := os.Stat(path); err != nil {
			t.Fatalf("candidate case %s is indexed but missing: %v", entry.Instance, err)
		}
	}
	for name := range candidateSchemaCases {
		if !seen[name] {
			t.Fatalf("candidate schema %s has no case under conformance/next", name)
		}
	}
	// No toolchain vector may sit inside the pinned suite.
	entries, err := os.ReadDir(filepath.Join(root, "conformance", "v1", "vectors"))
	if err != nil {
		t.Fatalf("read released vectors: %v", err)
	}
	for _, entry := range entries {
		if strings.HasPrefix(entry.Name(), "toolchain-") {
			t.Fatalf("candidate vector %s is inside the pinned suite", entry.Name())
		}
	}
}

// TestCandidateManifestMintsNoVersion keeps the candidate root honest about
// what it is: unreleased, unpinned, and owned by the task that mints it.
func TestCandidateManifestMintsNoVersion(t *testing.T) {
	var manifest map[string]any
	readJSON(t, filepath.Join(repositoryRoot(t), "conformance", "next", "manifest.json"), &manifest)
	if _, named := manifest["protocol_version"]; named {
		t.Fatal("the candidate manifest names a protocol version, which would mint one")
	}
	if manifest["released"] != false {
		t.Fatalf("the candidate manifest records released=%v", manifest["released"])
	}
	if manifest["candidate_against"] != protocolVersion {
		t.Fatalf("the candidate manifest names %v as its predecessor, want %s", manifest["candidate_against"], protocolVersion)
	}
	if manifest["release_pin_owner"] != candidateReleasePinOwner {
		t.Fatalf("the candidate manifest names %v as the pin owner, want %s", manifest["release_pin_owner"], candidateReleasePinOwner)
	}
}

// TestFrozenReleaseGuardRejectsASelfConsistentRewrite is the regression this
// whole split exists for. Generation rewrites the suite manifest and the
// release document pinning it in one pass, so the two agree afterwards;
// checking them against each other therefore accepts the rewrite. The guard
// compares against an authored record instead.
func TestFrozenReleaseGuardRejectsASelfConsistentRewrite(t *testing.T) {
	source := repositoryRoot(t)
	root := t.TempDir()
	for _, relative := range []string{
		"release/frozen.json",
		"release/1.0.0-rc.5.json",
		"conformance/v1/manifest.json",
		"conformance/v1/schema-cases/index.json",
	} {
		target := filepath.Join(root, filepath.FromSlash(relative))
		if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
			t.Fatalf("mkdir: %v", err)
		}
		payload, err := os.ReadFile(filepath.Join(source, filepath.FromSlash(relative)))
		if err != nil {
			t.Fatalf("read %s: %v", relative, err)
		}
		if err := os.WriteFile(target, payload, 0o644); err != nil {
			t.Fatalf("write %s: %v", relative, err)
		}
	}
	assertNoPanic(t, root)

	manifestPath := filepath.Join(root, "conformance", "v1", "manifest.json")
	var manifest map[string]any
	readJSON(t, manifestPath, &manifest)
	manifest["files"] = append(manifest["files"].([]any), map[string]any{
		"path": "vectors/toolchain-preflight.json", "sha256": "sha256:" + strings.Repeat("0", 64),
	})
	writeJSON(manifestPath, manifest)

	// Repin, exactly as regeneration does, so the pair is self-consistent.
	payload, err := os.ReadFile(manifestPath)
	if err != nil {
		t.Fatalf("reread manifest: %v", err)
	}
	sum := sha256.Sum256(payload)
	pin := "sha256:" + hex.EncodeToString(sum[:])
	documentPath := filepath.Join(root, "release", "1.0.0-rc.5.json")
	var document map[string]any
	readJSON(t, documentPath, &document)
	document["candidate_protocol_pin"].(map[string]any)["manifest_sha256"] = pin
	document["downstream_consumption"].(map[string]any)["required_manifest_sha256"] = pin
	writeJSON(documentPath, document)

	assertPanics(t, root, "generation rewrote frozen release 1.0.0-rc.5")
}

func assertNoPanic(t *testing.T, root string) {
	t.Helper()
	defer func() {
		if recovered := recover(); recovered != nil {
			t.Fatalf("the untouched frozen set failed the guard: %v", recovered)
		}
	}()
	assertFrozenReleaseIdentity(root)
}

func assertPanics(t *testing.T, root, fragment string) {
	t.Helper()
	defer func() {
		recovered := recover()
		if recovered == nil {
			t.Fatal("a rewritten frozen release passed the guard")
		}
		if message, ok := recovered.(string); !ok || !strings.Contains(message, fragment) {
			t.Fatalf("guard reported %v, want a message containing %q", recovered, fragment)
		}
	}()
	assertFrozenReleaseIdentity(root)
}
