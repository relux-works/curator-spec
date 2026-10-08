package main

import (
	"crypto/sha256"
	"encoding/hex"
	"os"
	"os/exec"
	"path/filepath"
	"testing"
)

// TestAcceptedContractDigestMatchesTag anchors the generator's frozen
// source-contract digest to the tag that froze the accepted manifest.
func TestAcceptedContractDigestMatchesTag(t *testing.T) {
	root := repositoryRoot(t)
	cmd := exec.Command("git", "show", skillfileSourcesAcceptedTag+":protocol/skillfile-sources.md")
	cmd.Dir = root
	payload, err := cmd.Output()
	if err != nil {
		t.Fatalf("cannot read accepted contract at %s: %v", skillfileSourcesAcceptedTag, err)
	}
	sum := sha256.Sum256(payload)
	if got := "sha256:" + hex.EncodeToString(sum[:]); got != skillfileSourcesAcceptedContractSHA256 {
		t.Fatalf("accepted contract digest = %s, want %s", got, skillfileSourcesAcceptedContractSHA256)
	}
}

func writeFixture(t *testing.T, root, relative, content string) {
	t.Helper()
	path := filepath.Join(root, filepath.FromSlash(relative))
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
}

func manifestEntries(t *testing.T, root, manifest string) (string, map[string]string) {
	t.Helper()
	document := readObject(t, filepath.Join(root, filepath.FromSlash(manifest)))
	suite, _ := document["suite"].(string)
	files, ok := document["files"].([]any)
	if !ok {
		t.Fatalf("%s files must be an array", manifest)
	}
	entries := map[string]string{}
	previous := ""
	for _, item := range files {
		entry, ok := item.(map[string]any)
		if !ok {
			t.Fatalf("%s entry is malformed: %#v", manifest, item)
		}
		path, _ := entry["path"].(string)
		digest, _ := entry["sha256"].(string)
		if path <= previous {
			t.Fatalf("%s entries are not sorted unique: %q after %q", manifest, path, previous)
		}
		previous = path
		entries[path] = digest
	}
	return suite, entries
}

// TestAcceptedManifestWriterPreservesDraftOwnedEntry proves the accepted
// manifest keeps the frozen tag digest for the draft-owned document while
// every other entry tracks live bytes.
func TestAcceptedManifestWriterPreservesDraftOwnedEntry(t *testing.T) {
	root := t.TempDir()
	writeFixture(t, root, "protocol/skillfile-sources.md", "# amended live contract\n")
	writeFixture(t, root, "protocol/repository-transport.md", "# transport\n")
	writeFixture(t, root, "docs/skillfile-sources.md", "# docs\n")
	writeFixture(t, root, "schemas/skillfile-sources-v1/source-types-v1.schema.json", "{}\n")
	writeFixture(t, root, "conformance/skillfile-sources-v1/index.json", "[]\n")
	writeFixture(t, root, "conformance/skillfile-sources-v1/manifest.json", "{}\n")

	writeSkillfileSourcesManifest(root)

	suite, entries := manifestEntries(t, root, "conformance/skillfile-sources-v1/manifest.json")
	if suite != "skillfile-sources-v1" {
		t.Fatalf("suite = %q, want skillfile-sources-v1", suite)
	}
	if len(entries) != 5 {
		t.Fatalf("entries = %d, want 5", len(entries))
	}
	if entries["protocol/skillfile-sources.md"] != skillfileSourcesAcceptedContractSHA256 {
		t.Fatalf(
			"draft-owned entry = %s, want frozen %s",
			entries["protocol/skillfile-sources.md"],
			skillfileSourcesAcceptedContractSHA256,
		)
	}
	live := sha256.Sum256([]byte("# transport\n"))
	if want := "sha256:" + hex.EncodeToString(live[:]); entries["protocol/repository-transport.md"] != want {
		t.Fatalf("live entry = %s, want %s", entries["protocol/repository-transport.md"], want)
	}
}

// TestDraftManifestWriterTracksLiveBytes proves the draft manifest pins the
// live source-contract input and draft files, excluding itself.
func TestDraftManifestWriterTracksLiveBytes(t *testing.T) {
	root := t.TempDir()
	writeFixture(t, root, "protocol/skillfile-sources.md", "# amended live contract\n")
	writeFixture(t, root, "schemas/draft-sources-v2/agent-skill-v9.schema.json", "{}\n")
	writeFixture(t, root, "conformance/draft-sources-v2/index.json", "[]\n")
	writeFixture(t, root, "conformance/draft-sources-v2/manifest.json", "stale\n")

	writeDraftSourcesManifest(root)

	suite, entries := manifestEntries(t, root, "conformance/draft-sources-v2/manifest.json")
	if suite != "draft-sources-v2" {
		t.Fatalf("suite = %q, want draft-sources-v2", suite)
	}
	if len(entries) != 3 {
		t.Fatalf("entries = %d, want 3", len(entries))
	}
	live := sha256.Sum256([]byte("# amended live contract\n"))
	if want := "sha256:" + hex.EncodeToString(live[:]); entries["protocol/skillfile-sources.md"] != want {
		t.Fatalf("draft contract entry = %s, want live %s", entries["protocol/skillfile-sources.md"], want)
	}

	writeFixture(t, root, "protocol/skillfile-sources.md", "# amended live contract\n# more\n")
	writeDraftSourcesManifest(root)
	_, rerun := manifestEntries(t, root, "conformance/draft-sources-v2/manifest.json")
	updated := sha256.Sum256([]byte("# amended live contract\n# more\n"))
	if want := "sha256:" + hex.EncodeToString(updated[:]); rerun["protocol/skillfile-sources.md"] != want {
		t.Fatalf("rerun contract entry = %s, want live %s", rerun["protocol/skillfile-sources.md"], want)
	}
}
