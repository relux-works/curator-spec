package main

import (
	"bytes"
	"crypto/sha1"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
	"testing"
)

func TestGeneratedCorpusIsByteExactAndDeterministic(t *testing.T) {
	repository := repositoryRoot(t)
	first := seedGenerationRoot(t, repository)
	second := seedGenerationRoot(t, repository)
	if err := generate(first); err != nil {
		t.Fatal(err)
	}
	firstHash := directoryHash(t, filepath.Join(first, "interop", "rc5", "external-repository"))
	if err := generate(second); err != nil {
		t.Fatal(err)
	}
	secondHash := directoryHash(t, filepath.Join(second, "interop", "rc5", "external-repository"))
	if firstHash != secondHash {
		t.Fatalf("two independent clean-root generations differ: %s != %s", firstHash, secondHash)
	}
	t.Logf("two independent clean-root generations: sha256=%s", firstHash)

	want := filepath.Join(repository, "interop", "rc5", "external-repository")
	got := filepath.Join(first, "interop", "rc5", "external-repository")
	assertDirectoriesEqual(t, want, got)
}

func TestCorpusManifestAndSourceInventory(t *testing.T) {
	root := repositoryRoot(t)
	corpus := filepath.Join(root, "interop", "rc5", "external-repository")
	manifest := readObject(t, filepath.Join(corpus, "manifest.json"))
	seen := map[string]bool{}
	for _, raw := range manifest["files"].([]any) {
		entry := raw.(map[string]any)
		rel := entry["path"].(string)
		if seen[rel] {
			t.Fatalf("duplicate manifest path %s", rel)
		}
		seen[rel] = true
		payload, err := os.ReadFile(filepath.Join(corpus, filepath.FromSlash(rel)))
		if err != nil {
			t.Fatal(err)
		}
		if got := sha256Identity(payload); got != entry["sha256"] {
			t.Fatalf("manifest hash for %s = %s, want %v", rel, got, entry["sha256"])
		}
		if json.Number(fmt.Sprint(len(payload))) != entry["size"] {
			t.Fatalf("manifest size for %s = %d, want %v", rel, len(payload), entry["size"])
		}
	}
	for _, required := range []string{
		"README.md", "case-manifest.json", "source-inventory.json",
		"bundles/canonical-sha1-tagged.json", "bundles/canonical-sha256-untagged.json",
		"bundles/adversarial-local-stores.json", "expected/build-receipt-v2.json",
		"expected/install-marker-v3-mixed.json", "vectors/source-identities.json", "vectors/transport-and-process-boundaries.json",
		"expected/build-receipt-v1.ccj.json", "expected/build-receipt-v2.ccj.json",
		"expected/install-marker-v3-mixed-exact.json", "expected/receipt-marker-hashes.json",
	} {
		if !seen[required] {
			t.Fatalf("manifest does not inventory %s", required)
		}
	}

	inventory := readObject(t, filepath.Join(corpus, "source-inventory.json"))
	inventorySeen := map[string]bool{}
	for _, raw := range inventory["files"].([]any) {
		entry := raw.(map[string]any)
		rel := entry["path"].(string)
		if inventorySeen[rel] {
			t.Fatalf("duplicate source inventory path %s", rel)
		}
		inventorySeen[rel] = true
		payload, err := os.ReadFile(filepath.Join(root, filepath.FromSlash(rel)))
		if err != nil {
			t.Fatal(err)
		}
		if sha256Identity(payload) != entry["sha256"] || json.Number(fmt.Sprint(len(payload))) != entry["size"] {
			t.Fatalf("source inventory drift for %s", rel)
		}
	}

	caseManifest := readObject(t, filepath.Join(corpus, "case-manifest.json"))
	for _, raw := range caseManifest["cases"].([]any) {
		item := raw.(map[string]any)
		source := item["source"].(string)
		base, _, _ := strings.Cut(source, "#")
		if strings.HasPrefix(base, "conformance/") && !inventorySeen[base] {
			t.Fatalf("case %s references uninventoried source %s", item["id"], base)
		}
	}
	for _, rel := range []string{externalReceiptInput, externalMarkerInput, externalPlanInput, localReceiptInput} {
		if !inventorySeen[rel] {
			t.Fatalf("direct copied or transformed input is not inventoried: %s", rel)
		}
	}

	for _, name := range []string{"build-receipt-v2.json", "install-marker-v3-mixed.json", "mixed-build-plan.json"} {
		got, err := os.ReadFile(filepath.Join(corpus, "expected", name))
		if err != nil {
			t.Fatal(err)
		}
		want, err := os.ReadFile(filepath.Join(root, "conformance", "v1", "expected", "external-repository", name))
		if err != nil {
			t.Fatal(err)
		}
		if !bytes.Equal(got, want) {
			t.Fatalf("expected/%s is not byte-exact rc.5 conformance data", name)
		}
	}

	localReceipt := readObject(t, filepath.Join(corpus, "expected", "build-receipt-v1.ccj.json"))
	externalReceipt := readObject(t, filepath.Join(corpus, "expected", "build-receipt-v2.ccj.json"))
	marker := readObject(t, filepath.Join(corpus, "expected", "install-marker-v3-mixed-exact.json"))
	for name, receipt := range map[string]map[string]any{"local-helper": localReceipt, "golden-tool": externalReceipt} {
		input := receipt["input"].(map[string]any)
		if receipt["cache_key"] != sha256Identity(canonicalJSON(input)) {
			t.Fatalf("%s receipt has a false cache key", name)
		}
		payload, err := os.ReadFile(filepath.Join(corpus, "expected", map[string]string{"local-helper": "build-receipt-v1.ccj.json", "golden-tool": "build-receipt-v2.ccj.json"}[name]))
		if err != nil {
			t.Fatal(err)
		}
		if !bytes.Equal(payload, canonicalJSON(receipt)) {
			t.Fatalf("%s receipt is not stored as exact CCJ-1 bytes", name)
		}
		record := marker["builds"].(map[string]any)[name].(map[string]any)
		if record["cache_key"] != receipt["cache_key"] || record["receipt_sha256"] != sha256Identity(payload) {
			t.Fatalf("%s marker record does not bind its exact receipt", name)
		}
	}
}

func TestRepositoryBundlesContainSelfConsistentRawGitObjects(t *testing.T) {
	root := filepath.Join(repositoryRoot(t), "interop", "rc5", "external-repository", "bundles")
	for _, name := range []string{
		"canonical-sha1-tagged.json", "canonical-sha1-tag-moved.json",
		"canonical-sha1-tag-missing.json", "canonical-sha256-untagged.json",
	} {
		bundle := readObject(t, filepath.Join(root, name))
		format := bundle["object_format"].(string)
		objects := map[string]map[string]any{}
		last := ""
		for _, raw := range bundle["objects"].([]any) {
			object := raw.(map[string]any)
			id := object["id"].(string)
			if id <= last {
				t.Fatalf("%s objects are not strictly sorted", name)
			}
			last = id
			content, err := base64.StdEncoding.DecodeString(object["content_base64"].(string))
			if err != nil {
				t.Fatal(err)
			}
			if json.Number(fmt.Sprint(len(content))) != object["size"] {
				t.Fatalf("%s object %s has false size", name, id)
			}
			if got := objectID(format, object["type"].(string), content); got != id {
				t.Fatalf("%s object %s recomputes as %s", name, id, got)
			}
			objects[id] = object
		}
		for _, raw := range bundle["refs"].([]any) {
			ref := raw.(map[string]any)
			if objects[ref["object_id"].(string)] == nil {
				t.Fatalf("%s ref %s points outside bundle", name, ref["name"])
			}
		}
		commit := bundle["selected_commit"].(string)
		if objects[commit] == nil || objects[commit]["type"] != "commit" {
			t.Fatalf("%s selected commit is absent or not a commit", name)
		}
		materialization := bundle["materialization"].(map[string]any)
		if materialization["harness_materialization_required"] != true || materialization["manager_specific_semantics_required"] != false {
			t.Fatalf("%s has a manager-specific materialization contract: %#v", name, materialization)
		}
		validateSnapshot(t, name, bundle["expected_snapshot"].(map[string]any))
	}

	moved := readObject(t, filepath.Join(root, "canonical-sha1-tag-moved.json"))
	if terminalTagCommit(t, moved) == moved["locked_commit"] {
		t.Fatal("moved-tag bundle does not move the tag away from the immutable lock")
	}
	matching := readObject(t, filepath.Join(root, "canonical-sha1-tagged.json"))
	if terminalTagCommit(t, matching) != matching["locked_commit"] {
		t.Fatal("matching-tag bundle does not terminate at the immutable lock")
	}
	missing := readObject(t, filepath.Join(root, "canonical-sha1-tag-missing.json"))
	for _, raw := range missing["refs"].([]any) {
		if strings.HasPrefix(raw.(map[string]any)["name"].(string), "refs/tags/") {
			t.Fatal("missing-tag bundle unexpectedly contains a tag ref")
		}
	}
}

func TestAdversarialLocalStoresMaterializeExactly(t *testing.T) {
	repository := repositoryRoot(t)
	bundle := readObject(t, filepath.Join(repository, "interop", "rc5", "external-repository", "bundles", "adversarial-local-stores.json"))
	materialized := map[string]string{}
	for _, raw := range bundle["cases"].([]any) {
		item := raw.(map[string]any)
		id := item["id"].(string)
		expected := item["expected"].(map[string]any)
		outcome, ok := expected["outcome"].(string)
		if !ok || outcome == "" {
			t.Fatalf("local-store case %s has no typed outcome", id)
		}
		if outcome == "rejected" {
			if code, ok := expected["code"].(string); !ok || code == "" {
				t.Fatalf("rejected local-store case %s has no typed error code", id)
			}
		}

		root := t.TempDir()
		materialized[id] = root
		for _, entryRaw := range item["entries"].([]any) {
			entry := entryRaw.(map[string]any)
			rel := filepath.Clean(filepath.FromSlash(entry["path"].(string)))
			if rel == "." || filepath.IsAbs(rel) || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
				t.Fatalf("local-store case %s has unsafe materialization path %q", id, rel)
			}
			destination := filepath.Join(root, rel)
			if err := os.MkdirAll(filepath.Dir(destination), 0o755); err != nil {
				t.Fatal(err)
			}
			switch entry["kind"] {
			case "regular":
				content, err := base64.StdEncoding.DecodeString(entry["content_base64"].(string))
				if err != nil {
					t.Fatalf("local-store case %s entry %s has invalid base64: %v", id, rel, err)
				}
				if entry["mode"] != "100644" {
					t.Fatalf("local-store case %s entry %s has unsupported mode %v", id, rel, entry["mode"])
				}
				if err := os.WriteFile(destination, content, 0o644); err != nil {
					t.Fatal(err)
				}
				got, err := os.ReadFile(destination)
				if err != nil || !bytes.Equal(got, content) {
					t.Fatalf("local-store case %s entry %s did not materialize byte-exactly: %v", id, rel, err)
				}
			case "symbolic-link":
				target := entry["target"].(string)
				if err := os.Symlink(target, destination); err != nil {
					t.Fatal(err)
				}
				got, err := os.Readlink(destination)
				if err != nil || got != target {
					t.Fatalf("local-store case %s entry %s symlink = %q, %v; want %q", id, rel, got, err, target)
				}
			default:
				t.Fatalf("local-store case %s entry %s has unknown kind %v", id, rel, entry["kind"])
			}
		}
	}

	accepted := readObject(t, filepath.Join(repository, filepath.FromSlash(localConfigInput)))
	acceptedByName := map[string]map[string]any{}
	for _, raw := range accepted["cases"].([]any) {
		item := raw.(map[string]any)
		acceptedByName[item["name"].(string)] = item
	}
	configCases := map[string]struct {
		acceptedName string
		configToken  string
	}{
		"partial-clone":           {acceptedName: "reject-partial-clone-config", configToken: "partialCloneFilter = blob:none"},
		"reftable":                {acceptedName: "reject-reftable", configToken: "refStorage = reftable"},
		"filter-config-inert":     {acceptedName: "source-filter-config-is-inert", configToken: "smudge = git-lfs smudge -- %f"},
		"credential-helper-inert": {acceptedName: "source-credential-helper-is-inert", configToken: "helper = !package-command"},
	}
	for id, expectedCase := range configCases {
		root, ok := materialized[id]
		if !ok {
			t.Fatalf("configuration case %s was not materialized", id)
		}
		files := acceptedByName[expectedCase.acceptedName]["files_base64"].(map[string]any)
		for _, rel := range []string{"HEAD", "config"} {
			want, err := base64.StdEncoding.DecodeString(files[rel].(string))
			if err != nil {
				t.Fatal(err)
			}
			got, err := os.ReadFile(filepath.Join(root, ".git", rel))
			if err != nil || !bytes.Equal(got, want) {
				t.Fatalf("configuration case %s .git/%s differs from accepted rc.5 bytes: %v", id, rel, err)
			}
		}
		config, err := os.ReadFile(filepath.Join(root, ".git", "config"))
		if err != nil {
			t.Fatal(err)
		}
		if !bytes.Contains(config, []byte(expectedCase.configToken)) {
			t.Fatalf("configuration case %s does not exercise %q", id, expectedCase.configToken)
		}
	}
}

func TestCaseMatrixCoversArchitectureThreatsAndLifecycle(t *testing.T) {
	root := filepath.Join(repositoryRoot(t), "interop", "rc5", "external-repository")
	manifest := readObject(t, filepath.Join(root, "case-manifest.json"))
	if manifest["implementation_neutral"] != true || manifest["manager_adapter"] != nil || manifest["physical_paths"] != "implementation-specific" {
		t.Fatalf("corpus carries a manager-specific assumption: %#v", manifest)
	}
	cases := map[string]map[string]any{}
	for _, raw := range manifest["cases"].([]any) {
		item := raw.(map[string]any)
		id := item["id"].(string)
		if cases[id] != nil {
			t.Fatalf("duplicate case %s", id)
		}
		cases[id] = item
		source := item["source"].(string)
		parts := strings.SplitN(source, "#", 2)
		base := parts[0]
		var sourcePath string
		if strings.HasPrefix(base, "conformance/") {
			sourcePath = filepath.Join(repositoryRoot(t), filepath.FromSlash(base))
		} else {
			sourcePath = filepath.Join(root, filepath.FromSlash(base))
		}
		payload, err := os.ReadFile(sourcePath)
		if err != nil {
			t.Fatalf("case %s source %s is not readable: %v", id, source, err)
		}
		if len(parts) == 2 && !jsonAnchorExists(payload, parts[1]) {
			t.Fatalf("case %s source anchor %s does not exist in %s", id, parts[1], base)
		}
	}
	for _, required := range []string{
		"sha1-tag-match-https", "sha1-tag-match-ssh", "sha1-tag-moved", "sha1-tag-missing", "sha256-untagged",
		"canonical-https-ssh-scp", "operator-local-identity", "monorepo-root-target", "monorepo-nested-target",
		"clean-git-session", "exact-fetch-closed-shape", "ssh-wrapper-closed-shape", "raw-object-reader-closed-shape",
		"local-substitution", "network-substitution-revision", "network-substitution-tag", "network-substitution-branch",
		"raw-object-malformed", "lfs-pointer", "submodule-gitlink", "symbolic-link", "special-file-mode",
		"alternate-object-store", "replace-ref", "graft", "promisor-pack", "partial-clone", "gitfile", "linked-worktree",
		"bare-repository", "reftable", "object-link", "filter-config-inert", "credential-helper-inert",
		"pack-v2-sha1", "pack-v3-sha1", "pack-v2-sha256", "pack-index-checksum-mismatch",
		"audit-order-cache-hit", "audit-order-cache-miss", "cache-corrupt-receipt", "cache-corrupt-artifact",
		"protected-offline-reuse", "offline-syntax-only", "offline-install-without-snapshot",
		"mixed-receipt-v1-v2-marker-v3", "external-receipt-v2-exact-bytes", "status-current", "status-corrupt",
		"repair-reacquires", "gc-retains-marker-and-journal-roots", "shim-path-structural", "path-collision", "package-argv-forbidden",
		"shim-collision-rollback", "consumer-last-rollback", "package-signing-request", "platform-requires-signing",
		"truthful-platform-claims",
	} {
		if cases[required] == nil {
			t.Fatalf("case matrix missing %s", required)
		}
	}
	coverage := manifest["architecture_v6_coverage"].(map[string]any)
	for _, threat := range []string{
		"source-lock-and-tag", "identity-and-substitution", "descriptor-and-output", "raw-object-boundary",
		"audit-and-cache", "receipt-marker-and-lifecycle", "transaction-path-signing-claims",
	} {
		references, ok := coverage[threat].([]any)
		if !ok || len(references) == 0 {
			t.Fatalf("architecture threat %s is uncovered", threat)
		}
		for _, raw := range references {
			if cases[raw.(string)] == nil {
				t.Fatalf("architecture threat %s references missing case %s", threat, raw)
			}
		}
	}
	threatMatrix := manifest["architecture_v6_threat_matrix"].([]any)
	wantThreats := []string{
		"mutable-or-symbolic-revision", "declared-effective-substitution-confusion", "replace-refs-or-grafts",
		"partial-clone-or-lazy-fetch", "alternates-or-object-store-escape", "fetch-default-or-tag-fallback",
		"ambient-config-url-proxy-helper", "ssh-mitm-system-config-or-variant-argv", "local-extension-ref-ambiguity",
		"malicious-or-incomplete-pack-metadata", "object-reader-transformation-or-process-escape", "commit-tag-parser-disagreement",
		"hook-filter-lfs-submodule-execution", "package-output-argv-or-signing-selection", "audit-bypass-on-cache-hit",
		"forged-cache", "shim-or-path-hijack", "partial-or-cross-project-install",
	}
	if len(threatMatrix) != len(wantThreats) {
		t.Fatalf("architecture threat matrix has %d rows, want %d", len(threatMatrix), len(wantThreats))
	}
	for index, want := range wantThreats {
		row := threatMatrix[index].(map[string]any)
		if row["threat"] != want {
			t.Fatalf("architecture threat row %d = %v, want %s", index, row["threat"], want)
		}
		for _, raw := range row["cases"].([]any) {
			if cases[raw.(string)] == nil {
				t.Fatalf("architecture threat %s references missing case %s", want, raw)
			}
		}
	}
	lifecycle := stringSet(manifest["lifecycle_boundaries"].([]any))
	lifecycleMatrix := manifest["lifecycle_matrix"].(map[string]any)
	for _, boundary := range []string{"syntax", "source-acquisition", "snapshot-proof", "audit", "cache", "compiler", "receipt", "publication", "status", "repair", "gc", "rollback"} {
		if !lifecycle[boundary] {
			t.Fatalf("lifecycle boundary %s is missing", boundary)
		}
		references, ok := lifecycleMatrix[boundary].([]any)
		if !ok || len(references) == 0 {
			t.Fatalf("lifecycle boundary %s has no case mapping", boundary)
		}
		for _, raw := range references {
			if cases[raw.(string)] == nil {
				t.Fatalf("lifecycle boundary %s references missing case %s", boundary, raw)
			}
		}
	}

}

func validateSnapshot(t *testing.T, name string, snapshot map[string]any) {
	t.Helper()
	files := []snapshotFile{}
	paths := map[string]bool{}
	for _, raw := range snapshot["files"].([]any) {
		entry := raw.(map[string]any)
		path := entry["path"].(string)
		if paths[path] {
			t.Fatalf("%s snapshot repeats %s", name, path)
		}
		paths[path] = true
		content, err := base64.StdEncoding.DecodeString(entry["content_base64"].(string))
		if err != nil {
			t.Fatal(err)
		}
		if sha256Identity(content) != entry["sha256"] || json.Number(fmt.Sprint(len(content))) != entry["size"] {
			t.Fatalf("%s snapshot entry %s has false byte oracle", name, path)
		}
		files = append(files, snapshotFile{path: path, mode: entry["mode"].(string), content: content})
	}
	if got := buildSourceIdentity(files); got != snapshot["content_sha256"] {
		t.Fatalf("%s build source = %s, want %v", name, got, snapshot["content_sha256"])
	}
	if !paths["skill-build.json"] {
		t.Fatalf("%s snapshot has no sole descriptor", name)
	}
}

func terminalTagCommit(t *testing.T, bundle map[string]any) string {
	t.Helper()
	objects := map[string]map[string]any{}
	for _, raw := range bundle["objects"].([]any) {
		object := raw.(map[string]any)
		objects[object["id"].(string)] = object
	}
	var id string
	for _, raw := range bundle["refs"].([]any) {
		ref := raw.(map[string]any)
		if ref["name"] == "refs/tags/v1.4.0" {
			id = ref["object_id"].(string)
		}
	}
	if id == "" {
		t.Fatal("bundle has no v1.4.0 tag")
	}
	object := objects[id]
	content, err := base64.StdEncoding.DecodeString(object["content_base64"].(string))
	if err != nil {
		t.Fatal(err)
	}
	return strings.TrimPrefix(strings.SplitN(string(content), "\n", 2)[0], "object ")
}

func objectID(format, kind string, content []byte) string {
	preimage := append([]byte(fmt.Sprintf("%s %d\x00", kind, len(content))), content...)
	if format == "sha1" {
		digest := sha1.Sum(preimage)
		return hex.EncodeToString(digest[:])
	}
	digest := sha256.Sum256(preimage)
	return hex.EncodeToString(digest[:])
}

func seedGenerationRoot(t *testing.T, repository string) string {
	t.Helper()
	root := t.TempDir()
	for _, raw := range sourceInventory(repository) {
		rel := raw.(map[string]any)["path"].(string)
		copyFile(t, filepath.Join(repository, filepath.FromSlash(rel)), filepath.Join(root, filepath.FromSlash(rel)))
	}
	return root
}

func copyFile(t *testing.T, source, destination string) {
	t.Helper()
	payload, err := os.ReadFile(source)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Dir(destination), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(destination, payload, 0o644); err != nil {
		t.Fatal(err)
	}
}

func assertDirectoriesEqual(t *testing.T, want, got string) {
	t.Helper()
	wantFiles := relativeFiles(t, want)
	gotFiles := relativeFiles(t, got)
	if strings.Join(wantFiles, "\n") != strings.Join(gotFiles, "\n") {
		t.Fatalf("generated file inventory differs\nwant: %v\ngot: %v", wantFiles, gotFiles)
	}
	for _, rel := range wantFiles {
		wantBytes, err := os.ReadFile(filepath.Join(want, filepath.FromSlash(rel)))
		if err != nil {
			t.Fatal(err)
		}
		gotBytes, err := os.ReadFile(filepath.Join(got, filepath.FromSlash(rel)))
		if err != nil {
			t.Fatal(err)
		}
		if !bytes.Equal(wantBytes, gotBytes) {
			t.Fatalf("generated bytes differ for %s", rel)
		}
	}
}

func directoryHash(t *testing.T, root string) string {
	t.Helper()
	hash := sha256.New()
	for _, rel := range relativeFiles(t, root) {
		payload, err := os.ReadFile(filepath.Join(root, filepath.FromSlash(rel)))
		if err != nil {
			t.Fatal(err)
		}
		hash.Write([]byte(rel))
		hash.Write([]byte{0})
		hash.Write(payload)
	}
	return hex.EncodeToString(hash.Sum(nil))
}

func relativeFiles(t *testing.T, root string) []string {
	t.Helper()
	files := []string{}
	if err := filepath.WalkDir(root, func(path string, entry fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if entry.Type().IsRegular() {
			rel, err := filepath.Rel(root, path)
			if err != nil {
				return err
			}
			files = append(files, filepath.ToSlash(rel))
		}
		return nil
	}); err != nil {
		t.Fatal(err)
	}
	sort.Strings(files)
	return files
}

func readObject(t *testing.T, path string) map[string]any {
	t.Helper()
	payload, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	decoder := json.NewDecoder(bytes.NewReader(payload))
	decoder.UseNumber()
	var value map[string]any
	if err := decoder.Decode(&value); err != nil {
		t.Fatal(err)
	}
	return value
}

func stringSet(values []any) map[string]bool {
	result := map[string]bool{}
	for _, value := range values {
		result[value.(string)] = true
	}
	return result
}

func jsonAnchorExists(payload []byte, anchor string) bool {
	decoder := json.NewDecoder(bytes.NewReader(payload))
	decoder.UseNumber()
	var value any
	if decoder.Decode(&value) != nil {
		return false
	}
	var walk func(any) bool
	walk = func(current any) bool {
		switch typed := current.(type) {
		case map[string]any:
			if _, ok := typed[anchor]; ok {
				return true
			}
			for key, child := range typed {
				if (key == "id" || key == "name" || key == "target") && child == anchor {
					return true
				}
				if walk(child) {
					return true
				}
			}
		case []any:
			for _, child := range typed {
				if walk(child) {
					return true
				}
			}
		}
		return false
	}
	return walk(value)
}

func repositoryRoot(t *testing.T) string {
	t.Helper()
	_, file, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("cannot resolve test source")
	}
	return filepath.Clean(filepath.Join(filepath.Dir(file), "..", ".."))
}
