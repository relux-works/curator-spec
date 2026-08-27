// Command generate-external-repository-corpus creates the implementation-neutral
// rc.5 external-build-repository interoperability corpus.
package main

import (
	"crypto/sha1"
	"crypto/sha256"
	"encoding/base64"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"io/fs"
	"os"
	"path"
	"path/filepath"
	"sort"
	"strings"
)

const (
	protocolVersion      = "1.0.0-rc.5"
	corpusVersion        = "rc5-external-repository-interop-v1"
	fixedCreatedAt       = "2026-08-05T00:00:00Z"
	sha1Lock             = "0123456789abcdef0123456789abcdef01234567"
	externalReceiptInput = "conformance/v1/expected/external-repository/build-receipt-v2.json"
	externalMarkerInput  = "conformance/v1/expected/external-repository/install-marker-v3-mixed.json"
	externalPlanInput    = "conformance/v1/expected/external-repository/mixed-build-plan.json"
	localReceiptInput    = "conformance/v1/expected/build-driver/receipt.ccj.json"
	localConfigInput     = "conformance/v1/fixtures/external-repository/local-config-and-refs.json"
)

type snapshotFile struct {
	path    string
	mode    string
	content []byte
}

type gitObject struct {
	id      string
	kind    string
	content []byte
}

type repositoryBundle struct {
	name         string
	objectFormat string
	files        []snapshotFile
	objects      []gitObject
	commit       string
	refs         map[string]string
	buildSource  string
}

type treeNode struct {
	files map[string]snapshotFile
	dirs  map[string]*treeNode
}

func main() {
	root := flag.String("root", ".", "specification repository root")
	flag.Parse()
	must(generate(*root))
}

func generate(root string) error {
	root, err := filepath.Abs(root)
	if err != nil {
		return err
	}
	out := filepath.Join(root, "interop", "rc5", "external-repository")
	if err := os.RemoveAll(out); err != nil {
		return err
	}
	if err := os.MkdirAll(out, 0o755); err != nil {
		return err
	}

	sha1Bundle := buildRepositoryBundle("canonical-sha1-tagged", "sha1", canonicalFiles())
	sha256Bundle := buildRepositoryBundle("canonical-sha256-untagged", "sha256", canonicalFiles())
	writeJSON(filepath.Join(out, "bundles", sha1Bundle.name+".json"), bundleJSON(sha1Bundle, true, false))
	movedBundle := sha1Bundle
	movedBundle.name = "canonical-sha1-tag-moved"
	writeJSON(filepath.Join(out, "bundles", movedBundle.name+".json"), bundleJSON(movedBundle, true, true))
	missingBundle := sha1Bundle
	missingBundle.name = "canonical-sha1-tag-missing"
	writeJSON(filepath.Join(out, "bundles", missingBundle.name+".json"), bundleJSON(missingBundle, false, false))
	writeJSON(filepath.Join(out, "bundles", sha256Bundle.name+".json"), bundleJSON(sha256Bundle, false, false))
	writeJSON(filepath.Join(out, "bundles", "adversarial-local-stores.json"), adversarialStores(root))

	writeJSON(filepath.Join(out, "vectors", "source-identities.json"), sourceIdentities())
	writeJSON(filepath.Join(out, "vectors", "expected-snapshots.json"), expectedSnapshots(sha1Bundle, sha256Bundle))
	writeJSON(filepath.Join(out, "vectors", "transport-and-process-boundaries.json"), transportAndProcessBoundaries())
	copyExact(root, out, externalReceiptInput, "expected/build-receipt-v2.json")
	copyExact(root, out, externalMarkerInput, "expected/install-marker-v3-mixed.json")
	copyExact(root, out, externalPlanInput, "expected/mixed-build-plan.json")
	writeExactReceiptMarkerOracles(root, out)

	sources := sourceInventory(root)
	writeJSON(filepath.Join(out, "source-inventory.json"), map[string]any{
		"protocol_version": protocolVersion,
		"corpus_version":   corpusVersion,
		"files":            sources,
	})
	writeJSON(filepath.Join(out, "case-manifest.json"), caseManifest(sha1Bundle, sha256Bundle))
	writeText(filepath.Join(out, "README.md"), corpusReadme())
	writeCorpusManifest(out)
	return nil
}

func canonicalFiles() []snapshotFile {
	descriptor := "{\n" +
		"  \"schema_version\": 1,\n" +
		"  \"targets\": {\n" +
		"    \"admin-tool\": {\n" +
		"      \"build_root\": \"tools/admin\",\n" +
		"      \"driver\": \"go-repository-v1\",\n" +
		"      \"source_dir\": \"tools/admin/cmd/admin-tool\"\n" +
		"    },\n" +
		"    \"golden-tool\": {\n" +
		"      \"build_root\": \".\",\n" +
		"      \"driver\": \"go-repository-v1\",\n" +
		"      \"source_dir\": \"cmd/golden-tool\"\n" +
		"    }\n" +
		"  }\n" +
		"}\n"
	return []snapshotFile{
		{path: "README.md", mode: "100644", content: []byte("# Golden external repository\n")},
		{path: "cmd/golden-tool/main.go", mode: "100644", content: []byte("package main\n\nimport \"fmt\"\n\nfunc main() { fmt.Println(\"golden\") }\n")},
		{path: "go.mod", mode: "100644", content: []byte("module example.com/golden-tools\n\ngo 1.26\n")},
		{path: "scripts/not-compiler-input", mode: "100755", content: []byte("#!/bin/sh\nexit 99\n")},
		{path: "skill-build.json", mode: "100644", content: []byte(descriptor)},
		{path: "tools/admin/cmd/admin-tool/main.go", mode: "100644", content: []byte("package main\n\nfunc main() {}\n")},
		{path: "tools/admin/go.mod", mode: "100644", content: []byte("module example.com/golden-tools/admin\n\ngo 1.26\n")},
	}
}

func buildRepositoryBundle(name, objectFormat string, files []snapshotFile) repositoryBundle {
	root := &treeNode{files: map[string]snapshotFile{}, dirs: map[string]*treeNode{}}
	for _, file := range files {
		parts := strings.Split(file.path, "/")
		node := root
		for _, component := range parts[:len(parts)-1] {
			if node.dirs[component] == nil {
				node.dirs[component] = &treeNode{files: map[string]snapshotFile{}, dirs: map[string]*treeNode{}}
			}
			node = node.dirs[component]
		}
		node.files[parts[len(parts)-1]] = file
	}
	objects := map[string]gitObject{}
	treeID := emitTree(root, objectFormat, objects)
	commitContent := []byte("tree " + treeID + "\nauthor Corpus Generator <corpus@example.test> 946684800 +0000\ncommitter Corpus Generator <corpus@example.test> 946684800 +0000\n\nrc.5 canonical external repository\n")
	commit := newGitObject(objectFormat, "commit", commitContent)
	objects[commit.id] = commit
	result := make([]gitObject, 0, len(objects))
	for _, object := range objects {
		result = append(result, object)
	}
	sort.Slice(result, func(i, j int) bool { return result[i].id < result[j].id })
	return repositoryBundle{
		name: name, objectFormat: objectFormat, files: files, objects: result, commit: commit.id,
		refs: map[string]string{"refs/heads/main": commit.id}, buildSource: buildSourceIdentity(files),
	}
}

func emitTree(node *treeNode, objectFormat string, objects map[string]gitObject) string {
	type entry struct {
		mode, name, id string
	}
	entries := make([]entry, 0, len(node.files)+len(node.dirs))
	for name, file := range node.files {
		blob := newGitObject(objectFormat, "blob", file.content)
		objects[blob.id] = blob
		entries = append(entries, entry{mode: file.mode, name: name, id: blob.id})
	}
	for name, child := range node.dirs {
		entries = append(entries, entry{mode: "40000", name: name, id: emitTree(child, objectFormat, objects)})
	}
	sort.Slice(entries, func(i, j int) bool {
		left, right := entries[i].name, entries[j].name
		if entries[i].mode == "40000" {
			left += "/"
		}
		if entries[j].mode == "40000" {
			right += "/"
		}
		return left < right
	})
	var content []byte
	for _, item := range entries {
		content = append(content, []byte(item.mode+" "+item.name)...)
		content = append(content, 0)
		id, err := hex.DecodeString(item.id)
		must(err)
		content = append(content, id...)
	}
	tree := newGitObject(objectFormat, "tree", content)
	objects[tree.id] = tree
	return tree.id
}

func newGitObject(objectFormat, kind string, content []byte) gitObject {
	preimage := append([]byte(fmt.Sprintf("%s %d\x00", kind, len(content))), content...)
	var id string
	switch objectFormat {
	case "sha1":
		digest := sha1.Sum(preimage)
		id = hex.EncodeToString(digest[:])
	case "sha256":
		digest := sha256.Sum256(preimage)
		id = hex.EncodeToString(digest[:])
	default:
		panic("unsupported object format " + objectFormat)
	}
	return gitObject{id: id, kind: kind, content: append([]byte(nil), content...)}
}

func bundleJSON(bundle repositoryBundle, withTag, moved bool) map[string]any {
	refs := cloneStringMap(bundle.refs)
	lockedCommit := bundle.commit
	if withTag {
		target := bundle.commit
		if moved {
			movedCommit := newGitObject(bundle.objectFormat, "commit", []byte(
				"tree "+rootTreeID(bundle)+"\nauthor Corpus Generator <corpus@example.test> 946684801 +0000\ncommitter Corpus Generator <corpus@example.test> 946684801 +0000\n\nmoved tag target\n",
			))
			bundle.objects = append(bundle.objects, movedCommit)
			target = movedCommit.id
		}
		tagContent := []byte("object " + target + "\ntype commit\ntag v1.4.0\ntagger Corpus Generator <corpus@example.test> 946684800 +0000\n\nrc.5 tag\n")
		tag := newGitObject(bundle.objectFormat, "tag", tagContent)
		bundle.objects = append(bundle.objects, tag)
		refs["refs/tags/v1.4.0"] = tag.id
	}
	sort.Slice(bundle.objects, func(i, j int) bool { return bundle.objects[i].id < bundle.objects[j].id })
	objects := make([]any, 0, len(bundle.objects))
	for _, object := range bundle.objects {
		objects = append(objects, map[string]any{
			"id": object.id, "type": object.kind, "size": len(object.content),
			"content_base64": base64.StdEncoding.EncodeToString(object.content),
		})
	}
	files := make([]any, 0, len(bundle.files))
	for _, file := range sortedFiles(bundle.files) {
		files = append(files, map[string]any{
			"path": file.path, "mode": file.mode, "size": len(file.content),
			"sha256": sha256Identity(file.content), "content_base64": base64.StdEncoding.EncodeToString(file.content),
		})
	}
	return map[string]any{
		"schema_version": 1, "bundle_format": "raw-git-object-bundle-v1", "name": bundle.name,
		"object_format": bundle.objectFormat, "locked_commit": lockedCommit, "selected_commit": bundle.commit,
		"refs": sortedRefs(refs), "objects": objects,
		"expected_snapshot": map[string]any{
			"algorithm": "curator-build-source-v1", "content_sha256": bundle.buildSource, "files": files,
		},
		"materialization": map[string]any{
			"harness_materialization_required":    true,
			"manager_specific_semantics_required": false,
			"meaning":                             "write raw objects and refs into an operation-private test remote or inert local store without changing bytes",
		},
	}
}

func adversarialStores(root string) map[string]any {
	regular := func(path, content string) map[string]any {
		return map[string]any{"path": path, "kind": "regular", "mode": "100644", "content_base64": base64.StdEncoding.EncodeToString([]byte(content))}
	}
	acceptedEntries := acceptedLocalStoreEntries(root)
	cases := []any{
		storeCase("alternate-object-store", "build_repository_local_format_unsupported", regular(".git/objects/info/alternates", "/outside/objects\n")),
		storeCase("replace-ref", "build_repository_local_format_unsupported", regular(".git/refs/replace/"+sha1Lock, strings.Repeat("b", 40)+"\n")),
		storeCase("graft", "build_repository_local_format_unsupported", regular(".git/info/grafts", sha1Lock+"\n")),
		storeCase("promisor-pack", "build_repository_local_format_unsupported", regular(".git/objects/pack/pack-"+strings.Repeat("a", 40)+".promisor", "")),
		storeCase("partial-clone", "build_repository_local_format_unsupported", acceptedEntries["reject-partial-clone-config"]...),
		storeCase("gitfile", "build_repository_local_gitfile_unsupported", regular(".git", "gitdir: ../outside.git\n")),
		storeCase("linked-worktree", "build_repository_local_linked_worktree_unsupported", regular(".git/commondir", "../..\n")),
		storeCase("bare-repository", "build_repository_local_bare_unsupported", regular("config", "[core]\n\tbare = true\n")),
		storeCase("reftable", "build_repository_local_format_unsupported", acceptedEntries["reject-reftable"]...),
		storeCase("object-link", "build_repository_local_layout_unsafe", map[string]any{"path": ".git/objects/aa/unsafe", "kind": "symbolic-link", "target": "../../../../outside"}),
		map[string]any{"id": "filter-config-inert", "entries": asAnyEntries(acceptedEntries["source-filter-config-is-inert"]), "expected": map[string]any{"outcome": "admitted-inert", "child_started": false}},
		map[string]any{"id": "credential-helper-inert", "entries": asAnyEntries(acceptedEntries["source-credential-helper-is-inert"]), "expected": map[string]any{"outcome": "admitted-inert", "child_started": false}},
	}
	return map[string]any{
		"schema_version": 1, "base_bundle": "canonical-sha1-tagged.json",
		"mutation_semantics": "replace or add exactly the listed administration entries; do not infer missing bytes",
		"cases":              cases,
	}
}

func acceptedLocalStoreEntries(root string) map[string][]map[string]any {
	wanted := map[string]bool{
		"reject-partial-clone-config":       true,
		"reject-reftable":                   true,
		"source-filter-config-is-inert":     true,
		"source-credential-helper-is-inert": true,
	}
	result := map[string][]map[string]any{}
	fixture := readJSONObject(filepath.Join(root, filepath.FromSlash(localConfigInput)))
	for _, raw := range fixture["cases"].([]any) {
		item := raw.(map[string]any)
		name := item["name"].(string)
		if !wanted[name] {
			continue
		}
		files := item["files_base64"].(map[string]any)
		paths := make([]string, 0, len(files))
		for rel := range files {
			paths = append(paths, rel)
		}
		sort.Strings(paths)
		for _, rel := range paths {
			encoded := files[rel].(string)
			if _, err := base64.StdEncoding.DecodeString(encoded); err != nil {
				panic(fmt.Sprintf("generate external repository corpus: invalid base64 in %s#%s/%s: %v", localConfigInput, name, rel, err))
			}
			result[name] = append(result[name], map[string]any{
				"path": path.Join(".git", rel), "kind": "regular", "mode": "100644", "content_base64": encoded,
			})
		}
	}
	for name := range wanted {
		if len(result[name]) == 0 {
			panic(fmt.Sprintf("generate external repository corpus: missing accepted local-store fixture %s#%s", localConfigInput, name))
		}
	}
	return result
}

func asAnyEntries(entries []map[string]any) []any {
	result := make([]any, len(entries))
	for index, entry := range entries {
		result[index] = entry
	}
	return result
}

func storeCase(id, code string, entries ...map[string]any) map[string]any {
	values := make([]any, len(entries))
	for index, entry := range entries {
		values[index] = entry
	}
	return map[string]any{"id": id, "entries": values, "expected": map[string]any{"outcome": "rejected", "code": code, "audit_started": false, "compiler_started": false}}
}

func sourceIdentities() map[string]any {
	project := "git.example.test/projects/interop"
	selectorInput := "./fixtures/../repositories/golden-tools"
	selector := normalizeSelector(selectorInput)
	localPreimage := canonicalJSON(map[string]string{
		"algorithm": "curator-operator-local-git-v1", "project": project, "selector": selector,
	})
	return map[string]any{
		"schema_version": 1,
		"network_cases": []any{
			identityCase("https", "https://Git.Example.Test/Org/Golden-Tools.git", "git.example.test/Org/Golden-Tools"),
			identityCase("ssh-uri", "ssh://builder@Git.Example.Test/Org/Golden-Tools.git", "git.example.test/Org/Golden-Tools"),
			identityCase("scp", "builder@Git.Example.Test:Org/Golden-Tools.git", "git.example.test/Org/Golden-Tools"),
			identityCase("unicode-https", "https://example.test/工具/repo.git", "example.test/工具/repo"),
			map[string]any{"id": "https-userinfo-rejected", "input": "https://user@example.test/repo.git", "expected_error": "build_repository_identity_invalid"},
			map[string]any{"id": "dot-component-rejected", "input": "ssh://example.test/org/../repo.git", "expected_error": "build_repository_identity_invalid"},
		},
		"local_case": map[string]any{
			"project": project, "selector_input": selectorInput, "normalized_selector": selector,
			"ccj1_preimage_base64": base64.StdEncoding.EncodeToString(localPreimage),
			"expected_identity":    map[string]any{"kind": "operator-local-git", "value": sha256Identity(localPreimage)},
		},
	}
}

func identityCase(id, input, canonical string) map[string]any {
	return map[string]any{"id": id, "input": input, "expected_identity": map[string]any{"kind": "network-git", "value": canonical}}
}

func expectedSnapshots(sha1Bundle, sha256Bundle repositoryBundle) map[string]any {
	return map[string]any{
		"schema_version": 1,
		"cases": []any{
			map[string]any{"id": "sha1", "bundle": "bundles/canonical-sha1-tagged.json", "object_format": "sha1", "commit": sha1Bundle.commit, "build_source": map[string]any{"algorithm": "curator-build-source-v1", "content_sha256": sha1Bundle.buildSource}, "descriptor_targets": []any{"admin-tool", "golden-tool"}},
			map[string]any{"id": "sha256", "bundle": "bundles/canonical-sha256-untagged.json", "object_format": "sha256", "commit": sha256Bundle.commit, "build_source": map[string]any{"algorithm": "curator-build-source-v1", "content_sha256": sha256Bundle.buildSource}, "descriptor_targets": []any{"admin-tool", "golden-tool"}},
		},
		"whole_snapshot_includes": []any{"README.md", "scripts/not-compiler-input", "skill-build.json", "tools/admin"},
		"selected_targets": []any{
			map[string]any{"target": "golden-tool", "build_root": ".", "source_dir": "cmd/golden-tool", "artifact_path_template": "bin/<manifest-command-key>[.exe]"},
			map[string]any{"target": "admin-tool", "build_root": "tools/admin", "source_dir": "tools/admin/cmd/admin-tool", "artifact_path_template": "bin/<manifest-command-key>[.exe]"},
		},
	}
}

func transportAndProcessBoundaries() map[string]any {
	return map[string]any{
		"schema_version": 1,
		"git_session": map[string]any{
			"environment_source": "empty",
			"required": []any{
				"GIT_CONFIG_NOSYSTEM=1", "GIT_NO_LAZY_FETCH=1", "GIT_NO_REPLACE_OBJECTS=1",
				"GIT_OPTIONAL_LOCKS=0", "GIT_PROTOCOL_FROM_USER=0", "GIT_TERMINAL_PROMPT=0",
				"LC_ALL=C", "LANG=C", "PATH=<manager-owned-empty-or-exact-helper-directory>",
			},
			"forbidden_inherited_families": []any{"GIT_*", "SSH_*", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"},
			"unexpected_child":             map[string]any{"outcome": "rejected", "code": "build_repository_git_process_unexpected"},
		},
		"fetch": map[string]any{
			"source_count": 1, "destination_namespace": "refs/curator/", "stdin": "closed",
			"forbidden":        []any{"configured-refspec", "depth", "filter", "mirror", "prune", "remote-name", "server-option", "stdin-refspec", "tag-auto-follow"},
			"unexpected_state": []any{"FETCH_HEAD", "remote-tracking-ref", "local-head", "local-tag", "commit-graph", "maintenance-state"},
		},
		"ssh_wrapper": map[string]any{
			"accepted_argv": []any{"<absolute-manager-wrapper>", "<host-or-user-at-host>", "git-upload-pack '<validated-ascii-path>'"},
			"argc":          3, "shell_started": false, "known_hosts": "operator-selected", "ssh_config": "manager-owned-empty",
			"forbidden": []any{"-G", "-p", "-4", "-6", "-o", "SendEnv", "extra-operand", "proxy-command", "proxy-jump", "forwarding", "tty", "control-master"},
		},
		"object_reader": map[string]any{
			"request": "<full-lowercase-object-id> LF", "response": "<same-id> SP <type> SP <size> LF <exact-content> LF",
			"forbidden":          []any{"--batch-command", "--batch-all-objects", "--follow-symlinks", "--textconv", "--filters", "--filter", "--use-mailmap", "--path", "revision-expression", "child-process", "network"},
			"malformed_response": map[string]any{"outcome": "rejected", "code": "build_repository_incomplete_source"},
		},
	}
}

func sourceInventory(root string) []any {
	paths := []string{
		"decisions/0005-external-build-repositories.md",
		"profiles/manager.md",
		"protocol/core.md",
		"schemas/v1/agent-skill-v7.schema.json",
		"schemas/v1/build-receipt-v2.schema.json",
		"schemas/v1/install-marker-v3.schema.json",
		"schemas/v1/skill-build-v1.schema.json",
		"conformance/v1/schema-cases/agent-skill-v7/invalid-command-argv.json",
		"conformance/v1/schema-cases/build-receipt-v2/valid-local-substitution.json",
		"conformance/v1/fixtures/external-repository/lfs-pointers.json",
		localConfigInput,
		"conformance/v1/fixtures/external-repository/pack-index.json",
		"conformance/v1/fixtures/external-repository/raw-objects.json",
		localReceiptInput,
		externalReceiptInput,
		externalMarkerInput,
		externalPlanInput,
		"conformance/v1/vectors/conformance-claim-v3-qualification.json",
		"conformance/v1/vectors/external-repository-acquisition.json",
		"conformance/v1/vectors/external-repository-lifecycle.json",
	}
	result := make([]any, 0, len(paths))
	for _, rel := range paths {
		payload, err := os.ReadFile(filepath.Join(root, filepath.FromSlash(rel)))
		must(err)
		result = append(result, map[string]any{"path": rel, "sha256": sha256Identity(payload), "size": len(payload)})
	}
	return result
}

func writeExactReceiptMarkerOracles(root, out string) {
	external := readJSONObject(filepath.Join(root, filepath.FromSlash(externalReceiptInput)))
	externalBytes := canonicalJSON(external)
	writeBytes(filepath.Join(out, "expected", "build-receipt-v2.ccj.json"), externalBytes)

	local := readJSONObject(filepath.Join(root, filepath.FromSlash(localReceiptInput)))
	localInput := local["input"].(map[string]any)
	localInput["command"] = "local-helper"
	localInput["source_dir"] = "build/cmd/local-helper"
	local["cache_key"] = sha256Identity(canonicalJSON(localInput))
	local["artifact"].(map[string]any)["path"] = "bin/local-helper"
	localBytes := canonicalJSON(local)
	writeBytes(filepath.Join(out, "expected", "build-receipt-v1.ccj.json"), localBytes)

	marker := readJSONObject(filepath.Join(root, filepath.FromSlash(externalMarkerInput)))
	builds := marker["builds"].(map[string]any)
	localRecord := builds["local-helper"].(map[string]any)
	localRecord["cache_key"] = local["cache_key"]
	localRecord["receipt_sha256"] = sha256Identity(localBytes)
	localRecord["artifact_path"] = local["artifact"].(map[string]any)["path"]
	localRecord["artifact_sha256"] = local["artifact"].(map[string]any)["sha256"]
	externalRecord := builds["golden-tool"].(map[string]any)
	externalRecord["cache_key"] = external["cache_key"]
	externalRecord["receipt_sha256"] = sha256Identity(externalBytes)
	externalRecord["artifact_path"] = external["artifact"].(map[string]any)["path"]
	externalRecord["artifact_sha256"] = external["artifact"].(map[string]any)["sha256"]
	writeJSON(filepath.Join(out, "expected", "install-marker-v3-mixed-exact.json"), marker)
	writeJSON(filepath.Join(out, "expected", "receipt-marker-hashes.json"), map[string]any{
		"schema_version": 1,
		"receipt_v1":     map[string]any{"path": "build-receipt-v1.ccj.json", "cache_key": local["cache_key"], "receipt_sha256": sha256Identity(localBytes)},
		"receipt_v2":     map[string]any{"path": "build-receipt-v2.ccj.json", "cache_key": external["cache_key"], "receipt_sha256": sha256Identity(externalBytes)},
		"marker_v3":      map[string]any{"path": "install-marker-v3-mixed-exact.json", "receipt_versions": []any{1, 2}},
	})
}

func readJSONObject(filePath string) map[string]any {
	payload, err := os.ReadFile(filePath)
	must(err)
	decoder := json.NewDecoder(strings.NewReader(string(payload)))
	decoder.UseNumber()
	var value map[string]any
	must(decoder.Decode(&value))
	return value
}

func caseManifest(sha1Bundle, sha256Bundle repositoryBundle) map[string]any {
	caseOf := func(id, category, source, outcome string, extra map[string]any) map[string]any {
		item := map[string]any{"id": id, "category": category, "source": source, "expected": map[string]any{"outcome": outcome}}
		for key, value := range extra {
			item["expected"].(map[string]any)[key] = value
		}
		return item
	}
	errorCase := func(id, category, source, code string) map[string]any {
		return caseOf(id, category, source, "rejected", map[string]any{"code": code, "mutation": false})
	}
	cases := []any{
		caseOf("sha1-tag-match-https", "acquisition", "bundles/canonical-sha1-tagged.json", "source-resolved", map[string]any{"commit": sha1Bundle.commit, "transport": "https", "fetch": "exact-tag-only"}),
		caseOf("sha1-tag-match-ssh", "acquisition", "bundles/canonical-sha1-tagged.json", "source-resolved", map[string]any{"commit": sha1Bundle.commit, "transport": "ssh", "fetch": "exact-tag-only"}),
		errorCase("sha1-tag-moved", "acquisition", "bundles/canonical-sha1-tag-moved.json", "build_repository_ref_moved"),
		errorCase("sha1-tag-missing", "acquisition", "bundles/canonical-sha1-tag-missing.json", "build_repository_source_unavailable"),
		caseOf("sha256-untagged", "acquisition", "bundles/canonical-sha256-untagged.json", "source-resolved", map[string]any{"commit": sha256Bundle.commit, "fetch": "full-oid-only"}),
		errorCase("untagged-object-missing", "acquisition", "conformance/v1/vectors/external-repository-acquisition.json#untagged-missing-object", "build_repository_source_unavailable"),
		caseOf("canonical-https-ssh-scp", "identity", "vectors/source-identities.json", "canonicalized", map[string]any{"equal_network_identity": true}),
		caseOf("operator-local-identity", "identity", "vectors/source-identities.json#local_case", "canonicalized", map[string]any{"absolute_path_disclosed": false}),
		caseOf("clean-git-session", "process-boundary", "vectors/transport-and-process-boundaries.json#git_session", "accepted", map[string]any{"ambient_config_applied": false, "unexpected_children": false}),
		caseOf("exact-fetch-closed-shape", "process-boundary", "vectors/transport-and-process-boundaries.json#fetch", "accepted", map[string]any{"default_refspec_applied": false, "fetch_head_written": false}),
		caseOf("ssh-wrapper-closed-shape", "process-boundary", "vectors/transport-and-process-boundaries.json#ssh_wrapper", "accepted", map[string]any{"shell_started": false, "system_config_applied": false}),
		caseOf("raw-object-reader-closed-shape", "process-boundary", "vectors/transport-and-process-boundaries.json#object_reader", "accepted", map[string]any{"transformations_applied": false, "child_started": false}),
		caseOf("monorepo-root-target", "target", "vectors/expected-snapshots.json#golden-tool", "selected", map[string]any{"output_manager_derived": true}),
		caseOf("monorepo-nested-target", "target", "vectors/expected-snapshots.json#admin-tool", "selected", map[string]any{"nearest_module_enforced": true}),
		caseOf("local-substitution", "substitution", "conformance/v1/schema-cases/build-receipt-v2/valid-local-substitution.json", "accepted", map[string]any{"declared_and_effective_retained": true}),
		caseOf("network-substitution-revision", "substitution", "conformance/v1/vectors/external-repository-acquisition.json#network-substitution-revision", "accepted", map[string]any{"declared_and_effective_retained": true}),
		caseOf("network-substitution-tag", "substitution", "conformance/v1/vectors/external-repository-acquisition.json#network-substitution-tag", "accepted", map[string]any{"declared_and_effective_retained": true}),
		caseOf("network-substitution-branch", "substitution", "conformance/v1/vectors/external-repository-acquisition.json#network-substitution-branch", "accepted", map[string]any{"declared_and_effective_retained": true}),
		errorCase("raw-object-malformed", "raw-object", "conformance/v1/fixtures/external-repository/raw-objects.json#reject-duplicate-tree-header", "build_repository_git_object_semantics_invalid"),
		errorCase("lfs-pointer", "raw-object", "conformance/v1/fixtures/external-repository/lfs-pointers.json#canonical-current-pointer", "build_repository_git_lfs_unsupported"),
		errorCase("submodule-gitlink", "raw-object", "conformance/v1/fixtures/external-repository/raw-objects.json#reject-submodule-gitlink", "build_repository_git_object_semantics_invalid"),
		errorCase("symbolic-link", "raw-object", "conformance/v1/fixtures/external-repository/raw-objects.json#reject-symbolic-link", "build_repository_git_object_semantics_invalid"),
		errorCase("special-file-mode", "raw-object", "conformance/v1/fixtures/external-repository/raw-objects.json#reject-special-file-mode", "build_repository_git_object_semantics_invalid"),
		errorCase("alternate-object-store", "local-store", "bundles/adversarial-local-stores.json#alternate-object-store", "build_repository_local_format_unsupported"),
		errorCase("replace-ref", "local-store", "bundles/adversarial-local-stores.json#replace-ref", "build_repository_local_format_unsupported"),
		errorCase("graft", "local-store", "bundles/adversarial-local-stores.json#graft", "build_repository_local_format_unsupported"),
		errorCase("promisor-pack", "local-store", "bundles/adversarial-local-stores.json#promisor-pack", "build_repository_local_format_unsupported"),
		errorCase("partial-clone", "local-store", "bundles/adversarial-local-stores.json#partial-clone", "build_repository_local_format_unsupported"),
		errorCase("gitfile", "local-store", "bundles/adversarial-local-stores.json#gitfile", "build_repository_local_gitfile_unsupported"),
		errorCase("linked-worktree", "local-store", "bundles/adversarial-local-stores.json#linked-worktree", "build_repository_local_linked_worktree_unsupported"),
		errorCase("bare-repository", "local-store", "bundles/adversarial-local-stores.json#bare-repository", "build_repository_local_bare_unsupported"),
		errorCase("reftable", "local-store", "bundles/adversarial-local-stores.json#reftable", "build_repository_local_format_unsupported"),
		errorCase("object-link", "local-store", "bundles/adversarial-local-stores.json#object-link", "build_repository_local_layout_unsafe"),
		caseOf("filter-config-inert", "local-store", "bundles/adversarial-local-stores.json#filter-config-inert", "admitted-inert", map[string]any{"child_started": false}),
		caseOf("credential-helper-inert", "local-store", "bundles/adversarial-local-stores.json#credential-helper-inert", "admitted-inert", map[string]any{"child_started": false}),
		caseOf("pack-v2-sha1", "pack-index", "conformance/v1/fixtures/external-repository/pack-index.json#valid-empty-pack-v2-sha1", "accepted", map[string]any{"checksums_recomputed": true}),
		caseOf("pack-v3-sha1", "pack-index", "conformance/v1/fixtures/external-repository/pack-index.json#valid-empty-pack-v3-sha1", "accepted", map[string]any{"checksums_recomputed": true}),
		caseOf("pack-v2-sha256", "pack-index", "conformance/v1/fixtures/external-repository/pack-index.json#valid-empty-pack-v2-sha256", "accepted", map[string]any{"checksums_recomputed": true}),
		errorCase("pack-index-checksum-mismatch", "pack-index", "conformance/v1/fixtures/external-repository/pack-index.json#reject-index-checksum-mismatch", "build_repository_local_object_format_unsupported"),
		caseOf("audit-order-cache-hit", "audit-ordering", "conformance/v1/vectors/external-repository-lifecycle.json#verified-cache-hit", "cache-hit", map[string]any{"audit_before_cache": true, "compiler_started": false}),
		caseOf("audit-order-cache-miss", "audit-ordering", "conformance/v1/vectors/external-repository-lifecycle.json#cache-miss", "built", map[string]any{"audit_before_cache": true, "audit_before_compiler": true}),
		caseOf("cache-corrupt-receipt", "cache", "conformance/v1/vectors/external-repository-lifecycle.json#corrupt-receipt", "rebuilt", map[string]any{"code": "build_repository_receipt_invalid"}),
		caseOf("cache-corrupt-artifact", "cache", "conformance/v1/vectors/external-repository-lifecycle.json#corrupt-artifact", "rebuilt", map[string]any{"code": "build_repository_artifact_invalid"}),
		caseOf("protected-offline-reuse", "cache", "bundles/canonical-sha1-tagged.json", "cache-hit", map[string]any{"network_started": false, "snapshot_revalidated": true, "audit_before_cache": true}),
		caseOf("offline-syntax-only", "offline", "conformance/v1/vectors/external-repository-lifecycle.json#offline-syntax-only", "warning", map[string]any{"code": "build_repository_unverified_offline", "source_claimed": false}),
		errorCase("offline-install-without-snapshot", "offline", "conformance/v1/vectors/external-repository-lifecycle.json#offline-install", "build_repository_source_unavailable"),
		caseOf("mixed-receipt-v1-v2-marker-v3", "receipt-marker", "expected/install-marker-v3-mixed-exact.json", "accepted", map[string]any{"receipt_versions": []any{1, 2}, "marker_version": 3}),
		caseOf("external-receipt-v2-exact-bytes", "receipt-marker", "expected/build-receipt-v2.ccj.json", "accepted", map[string]any{"canonical_bytes": true}),
		caseOf("status-current", "lifecycle", "conformance/v1/vectors/external-repository-lifecycle.json#status-current", "current", map[string]any{"network_started": false, "mutation": false}),
		caseOf("status-corrupt", "lifecycle", "conformance/v1/vectors/external-repository-lifecycle.json#status-unreadable-protected-state", "unknown", map[string]any{"network_started": false, "mutation": false}),
		caseOf("repair-reacquires", "lifecycle", "conformance/v1/vectors/external-repository-lifecycle.json#repair-reacquires-exact-source", "repaired", map[string]any{"audit_before_cache": true}),
		caseOf("gc-retains-marker-and-journal-roots", "lifecycle", "conformance/v1/vectors/external-repository-lifecycle.json#gc-retains-roots", "retained", map[string]any{"exec_started": false}),
		caseOf("shim-path-structural", "path-shim", "conformance/v1/vectors/external-repository-lifecycle.json#external-command-shim", "accepted", map[string]any{"artifact_executed": false}),
		errorCase("path-collision", "path-shim", "conformance/v1/vectors/external-repository-lifecycle.json#package-path-entry-rejected", "build_repository_package_output_forbidden"),
		errorCase("package-argv-forbidden", "process-boundary", "conformance/v1/schema-cases/agent-skill-v7/invalid-command-argv.json", "manifest_invalid"),
		errorCase("shim-collision-rollback", "rollback", "conformance/v1/vectors/external-repository-lifecycle.json#shim-collision-rolls-back", "build_repository_transaction_failed"),
		caseOf("consumer-last-rollback", "rollback", "conformance/v1/vectors/external-repository-lifecycle.json#marker-consumer-last", "committed", map[string]any{"consumer_last": true}),
		errorCase("package-signing-request", "signing", "conformance/v1/vectors/external-repository-lifecycle.json#package-signing-request", "build_repository_package_signing_forbidden"),
		errorCase("platform-requires-signing", "signing", "conformance/v1/vectors/external-repository-lifecycle.json#platform-requires-local-signing", "build_repository_signer_policy_unsupported"),
		caseOf("truthful-platform-claims", "platform-claim", "conformance/v1/vectors/conformance-claim-v3-qualification.json", "no-candidate-claims", map[string]any{"linux_excluded": true, "native_evidence_required": true}),
	}
	return map[string]any{
		"schema_version": 1, "protocol_version": protocolVersion, "corpus_version": corpusVersion,
		"implementation_neutral": true, "manager_adapter": nil, "physical_paths": "implementation-specific",
		"cases": cases,
		"architecture_v6_coverage": map[string]any{
			"source-lock-and-tag":             []any{"sha1-tag-match-https", "sha1-tag-moved", "sha1-tag-missing", "sha256-untagged", "untagged-object-missing"},
			"identity-and-substitution":       []any{"canonical-https-ssh-scp", "operator-local-identity", "local-substitution", "network-substitution-revision", "network-substitution-tag", "network-substitution-branch"},
			"descriptor-and-output":           []any{"monorepo-root-target", "monorepo-nested-target", "path-collision"},
			"raw-object-boundary":             []any{"raw-object-malformed", "lfs-pointer", "submodule-gitlink", "symbolic-link", "special-file-mode", "alternate-object-store", "replace-ref", "graft", "promisor-pack", "partial-clone", "filter-config-inert", "credential-helper-inert", "pack-index-checksum-mismatch"},
			"audit-and-cache":                 []any{"audit-order-cache-hit", "audit-order-cache-miss", "cache-corrupt-receipt", "cache-corrupt-artifact", "protected-offline-reuse"},
			"receipt-marker-and-lifecycle":    []any{"mixed-receipt-v1-v2-marker-v3", "external-receipt-v2-exact-bytes", "status-current", "status-corrupt", "repair-reacquires", "gc-retains-marker-and-journal-roots"},
			"transaction-path-signing-claims": []any{"shim-path-structural", "shim-collision-rollback", "consumer-last-rollback", "package-signing-request", "platform-requires-signing", "truthful-platform-claims"},
		},
		"architecture_v6_threat_matrix": []any{
			threat("mutable-or-symbolic-revision", "sha1-tag-moved", "sha256-untagged"),
			threat("declared-effective-substitution-confusion", "local-substitution", "network-substitution-revision"),
			threat("replace-refs-or-grafts", "replace-ref", "graft"),
			threat("partial-clone-or-lazy-fetch", "promisor-pack", "partial-clone", "raw-object-reader-closed-shape"),
			threat("alternates-or-object-store-escape", "alternate-object-store", "object-link"),
			threat("fetch-default-or-tag-fallback", "exact-fetch-closed-shape", "sha1-tag-missing", "untagged-object-missing"),
			threat("ambient-config-url-proxy-helper", "clean-git-session", "credential-helper-inert", "filter-config-inert"),
			threat("ssh-mitm-system-config-or-variant-argv", "ssh-wrapper-closed-shape", "sha1-tag-match-ssh"),
			threat("local-extension-ref-ambiguity", "gitfile", "linked-worktree", "bare-repository", "reftable"),
			threat("malicious-or-incomplete-pack-metadata", "pack-v2-sha1", "pack-v3-sha1", "pack-v2-sha256", "pack-index-checksum-mismatch"),
			threat("object-reader-transformation-or-process-escape", "raw-object-reader-closed-shape", "raw-object-malformed"),
			threat("commit-tag-parser-disagreement", "raw-object-malformed", "sha1-tag-moved"),
			threat("hook-filter-lfs-submodule-execution", "lfs-pointer", "submodule-gitlink", "filter-config-inert"),
			threat("package-output-argv-or-signing-selection", "path-collision", "package-argv-forbidden", "package-signing-request"),
			threat("audit-bypass-on-cache-hit", "audit-order-cache-hit", "protected-offline-reuse"),
			threat("forged-cache", "cache-corrupt-receipt", "cache-corrupt-artifact"),
			threat("shim-or-path-hijack", "shim-path-structural", "shim-collision-rollback"),
			threat("partial-or-cross-project-install", "consumer-last-rollback", "shim-collision-rollback"),
		},
		"lifecycle_boundaries": []any{"syntax", "source-acquisition", "snapshot-proof", "audit", "cache", "compiler", "receipt", "publication", "status", "repair", "gc", "rollback"},
		"lifecycle_matrix": map[string]any{
			"syntax": []any{"canonical-https-ssh-scp", "offline-syntax-only"}, "source-acquisition": []any{"sha1-tag-match-https", "sha1-tag-moved", "sha1-tag-missing", "sha256-untagged"},
			"snapshot-proof": []any{"raw-object-malformed", "lfs-pointer", "pack-index-checksum-mismatch"}, "audit": []any{"audit-order-cache-hit", "audit-order-cache-miss"},
			"cache": []any{"audit-order-cache-hit", "cache-corrupt-receipt", "cache-corrupt-artifact", "protected-offline-reuse"}, "compiler": []any{"audit-order-cache-miss", "package-argv-forbidden"},
			"receipt": []any{"external-receipt-v2-exact-bytes", "mixed-receipt-v1-v2-marker-v3"}, "publication": []any{"consumer-last-rollback", "shim-collision-rollback"},
			"status": []any{"status-current", "status-corrupt"}, "repair": []any{"repair-reacquires"}, "gc": []any{"gc-retains-marker-and-journal-roots"}, "rollback": []any{"shim-collision-rollback", "consumer-last-rollback"},
		},
	}
}

func threat(name string, cases ...string) map[string]any {
	values := make([]any, len(cases))
	for index, value := range cases {
		values[index] = value
	}
	return map[string]any{"threat": name, "cases": values}
}

func corpusReadme() string {
	return `# rc.5 external-repository interoperability corpus

This directory is the implementation-neutral shared corpus for protocol
` + protocolVersion + `. It is generated from the accepted specification and
the released conformance vectors; it contains no Curator- or csk-specific
harness adapter.

` + "`case-manifest.json`" + ` is the entry point. Repository bundles use
` + "`raw-git-object-bundle-v1`" + `: full raw object bytes, object IDs, refs,
snapshot bytes, modes, and expected build-source identities. A downstream
harness may materialize those bytes as an operation-private HTTP/SSH test
remote or as an inert local store, but it must not rewrite object, ref, or
snapshot bytes. Physical cache, staging, receipt, and lock paths remain
implementation-specific.

Regenerate and verify from the repository root:

` + "```text\ngo run ./tools/generate-external-repository-corpus -root .\ngo test ./tools/generate-external-repository-corpus\n```" + `

` + "`manifest.json`" + ` hashes every other corpus file. ` + "`source-inventory.json`" + `
pins the exact accepted specification/schema/vector inputs. Expected receipt
and marker files are copied byte-for-byte from the rc.5 conformance suite.
`
}

func buildSourceIdentity(files []snapshotFile) string {
	sorted := sortedFiles(files)
	preimage := []byte("curator-build-source-v1\x00")
	for _, file := range sorted {
		preimage = append(preimage, 'F')
		preimage = binary.BigEndian.AppendUint64(preimage, uint64(len([]byte(file.path))))
		preimage = append(preimage, []byte(file.path)...)
		preimage = binary.BigEndian.AppendUint64(preimage, uint64(len(file.content)))
		preimage = append(preimage, file.content...)
	}
	return sha256Identity(preimage)
}

func sortedFiles(files []snapshotFile) []snapshotFile {
	result := append([]snapshotFile(nil), files...)
	sort.Slice(result, func(i, j int) bool { return result[i].path < result[j].path })
	return result
}

func rootTreeID(bundle repositoryBundle) string {
	commit := objectByID(bundle.objects, bundle.commit)
	first := strings.SplitN(string(commit.content), "\n", 2)[0]
	return strings.TrimPrefix(first, "tree ")
}

func objectByID(objects []gitObject, id string) gitObject {
	for _, object := range objects {
		if object.id == id {
			return object
		}
	}
	panic("missing object " + id)
}

func normalizeSelector(value string) string {
	cleaned := path.Clean(strings.ReplaceAll(value, "\\", "/"))
	if cleaned == "." {
		return ""
	}
	return cleaned
}

func canonicalJSON(value any) []byte {
	payload, err := json.Marshal(value)
	must(err)
	return payload
}

func sortedRefs(refs map[string]string) []any {
	keys := make([]string, 0, len(refs))
	for key := range refs {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	result := make([]any, 0, len(keys))
	for _, key := range keys {
		result = append(result, map[string]any{"name": key, "object_id": refs[key]})
	}
	return result
}

func cloneStringMap(value map[string]string) map[string]string {
	result := make(map[string]string, len(value))
	for key, item := range value {
		result[key] = item
	}
	return result
}

func copyExact(root, out, source, destination string) {
	payload, err := os.ReadFile(filepath.Join(root, filepath.FromSlash(source)))
	must(err)
	writeBytes(filepath.Join(out, filepath.FromSlash(destination)), payload)
}

func writeCorpusManifest(root string) {
	entries := []any{}
	must(filepath.WalkDir(root, func(filePath string, entry fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if !entry.Type().IsRegular() {
			return nil
		}
		rel, err := filepath.Rel(root, filePath)
		if err != nil {
			return err
		}
		rel = filepath.ToSlash(rel)
		if rel == "manifest.json" {
			return nil
		}
		payload, err := os.ReadFile(filePath)
		if err != nil {
			return err
		}
		entries = append(entries, map[string]any{"path": rel, "sha256": sha256Identity(payload), "size": len(payload)})
		return nil
	}))
	sort.Slice(entries, func(i, j int) bool {
		return entries[i].(map[string]any)["path"].(string) < entries[j].(map[string]any)["path"].(string)
	})
	writeJSON(filepath.Join(root, "manifest.json"), map[string]any{
		"schema_version": 1, "protocol_version": protocolVersion, "corpus_version": corpusVersion,
		"generated_at": fixedCreatedAt, "generator": "tools/generate-external-repository-corpus", "files": entries,
	})
}

func sha256Identity(payload []byte) string {
	digest := sha256.Sum256(payload)
	return "sha256:" + hex.EncodeToString(digest[:])
}

func writeJSON(filePath string, value any) {
	must(os.MkdirAll(filepath.Dir(filePath), 0o755))
	file, err := os.Create(filePath)
	must(err)
	encoder := json.NewEncoder(file)
	encoder.SetEscapeHTML(false)
	encoder.SetIndent("", "  ")
	must(encoder.Encode(value))
	must(file.Close())
}

func writeText(filePath, value string) {
	writeBytes(filePath, []byte(value))
}

func writeBytes(filePath string, value []byte) {
	must(os.MkdirAll(filepath.Dir(filePath), 0o755))
	must(os.WriteFile(filePath, value, 0o644))
}

func must(err error) {
	if err != nil {
		panic(fmt.Sprintf("generate external repository corpus: %v", err))
	}
}
