package main

import (
	"crypto/ed25519"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func TestCCJ1RemovesOnlyOuterSignature(t *testing.T) {
	value := map[string]any{
		"z": "заметка",
		"endorsement": map[string]any{
			"sig": map[string]any{"key_id": "nested"},
		},
		"sig": map[string]any{"key_id": "outer"},
	}
	want := `{"endorsement":{"sig":{"key_id":"nested"}},"z":"заметка"}`
	if got := string(canonicalBytes(value)); got != want {
		t.Fatalf("CCJ-1 = %s, want %s", got, want)
	}
}

func TestCCJ1Escapes(t *testing.T) {
	value := map[string]any{"s": "\b\f\n\r\t<>/&\\\""}
	want := `{"s":"\b\f\n\r\t<>/&\\\""}`
	if got := string(canonicalBytes(value)); got != want {
		t.Fatalf("CCJ-1 escapes = %s, want %s", got, want)
	}
}

func TestGeneratedRegistryVectors(t *testing.T) {
	root := repositoryRoot(t)
	registryDir := filepath.Join(root, "conformance", "v1", "expected", "registry")
	pinnedPayload, err := os.ReadFile(filepath.Join(registryDir, "pinned_key.txt"))
	if err != nil {
		t.Fatal(err)
	}
	pinned := strings.TrimSpace(string(pinnedPayload))
	publicBytes, err := base64.StdEncoding.DecodeString(strings.TrimPrefix(pinned, "ed25519:"))
	if err != nil {
		t.Fatal(err)
	}
	public := ed25519.PublicKey(publicBytes)

	for _, name := range []string{"record_audited.json", "record_revoked.json", "snapshot.json"} {
		object := readObject(t, filepath.Join(registryDir, name))
		if !verifySignedVector(object, public) {
			t.Fatalf("%s must verify", name)
		}
	}
	if verifySignedVector(readObject(t, filepath.Join(registryDir, "record_forged.json")), public) {
		t.Fatal("forged record must not verify")
	}
	if verifySignedVector(readObject(t, filepath.Join(registryDir, "record_wrong_key_id.json")), public) {
		t.Fatal("record with wrong key id must not verify")
	}

	logObject := readObject(t, filepath.Join(registryDir, "log.json"))
	rawEntries, ok := logObject["entries"].([]any)
	if !ok || len(rawEntries) != 2 {
		t.Fatalf("log entries = %#v", logObject["entries"])
	}
	entries := make([]map[string]any, len(rawEntries))
	prev := genesis
	for index, raw := range rawEntries {
		entry := raw.(map[string]any)
		entries[index] = entry
		if entry["prev_hash"] != prev {
			t.Fatalf("entry %d prev_hash = %v, want %s", index+1, entry["prev_hash"], prev)
		}
		record := entry["record"].(map[string]any)
		sum := sha256.Sum256(append([]byte(prev), canonicalBytes(record)...))
		prev = hex.EncodeToString(sum[:])
		if entry["entry_hash"] != prev {
			t.Fatalf("entry %d hash = %v, want %s", index+1, entry["entry_hash"], prev)
		}
	}
	snapshot := readObject(t, filepath.Join(registryDir, "snapshot.json"))
	if snapshot["head"] != prev || snapshot["merkle_root"] != merkleRoot(entries) {
		t.Fatal("snapshot does not commit to the generated log")
	}

	bundle := readObject(t, filepath.Join(registryDir, "bundle.json"))
	if bundle["snapshot"].(map[string]any)["head"] != snapshot["head"] {
		t.Fatal("bundle snapshot differs from the standalone snapshot")
	}
}

func verifySignedVector(object map[string]any, public ed25519.PublicKey) bool {
	sig, ok := object["sig"].(map[string]any)
	if !ok || sig["algorithm"] != "ed25519" {
		return false
	}
	keyHash := sha256.Sum256(public)
	if sig["key_id"] != hex.EncodeToString(keyHash[:])[:16] {
		return false
	}
	signatureText, ok := sig["signature"].(string)
	if !ok {
		return false
	}
	signature, err := base64.StdEncoding.DecodeString(signatureText)
	return err == nil && ed25519.Verify(public, canonicalBytes(object), signature)
}

func readObject(t *testing.T, path string) map[string]any {
	t.Helper()
	file, err := os.Open(path)
	if err != nil {
		t.Fatal(err)
	}
	defer file.Close()
	decoder := json.NewDecoder(file)
	decoder.UseNumber()
	var object map[string]any
	if err := decoder.Decode(&object); err != nil {
		t.Fatal(err)
	}
	return object
}

func repositoryRoot(t *testing.T) string {
	t.Helper()
	_, file, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("cannot locate test file")
	}
	return filepath.Clean(filepath.Join(filepath.Dir(file), "..", ".."))
}
