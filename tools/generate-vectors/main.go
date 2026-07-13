// Command generate-vectors creates the Curator Protocol v1 conformance
// vectors without importing either conforming implementation.
package main

import (
	"crypto/ed25519"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"unicode/utf8"
)

const (
	protocolVersion = "1.0.0-rc.1"
	fixedCommit     = "0123456789abcdef0123456789abcdef01234567"
	fixedTime       = "2026-07-13T00:00:00Z"
	genesis         = "0000000000000000000000000000000000000000000000000000000000000000"
)

var includeRoots = map[string]bool{
	"SKILL.md": true, "agents": true, "references": true, ".skill_triggers": true,
	"assets": true, "templates": true, "examples": true, "data": true,
}

var excludedPatterns = []string{
	".git", ".github", ".gitlab-ci.yml", ".venv", "__pycache__", "*.pyc",
	"node_modules", "tests", "test", "__tests__", "README*", "CHANGELOG*",
	"LICENSE*", "Makefile", "setup.py", "pyproject.toml", "requirements*.txt",
	".DS_Store", ".gitignore",
}

type schemaCase struct {
	valid   any
	invalid any
}

func main() {
	root := flag.String("root", ".", "specification repository root")
	flag.Parse()
	suite := filepath.Join(*root, "conformance", "v1")
	fixture := filepath.Join(suite, "fixtures", "skill")
	expected := filepath.Join(suite, "expected")
	vectors := filepath.Join(suite, "vectors")
	must(os.MkdirAll(filepath.Join(expected, "registry"), 0o755))
	must(os.MkdirAll(vectors, 0o755))

	snapshotFiles := regularFiles(fixture)
	snapshotHash := contentHash(fixture, snapshotFiles)
	writeText(filepath.Join(expected, "snapshot_sha256.txt"), snapshotHash+"\n")

	selected := selectedContextFiles(fixture)
	writeJSON(filepath.Join(expected, "context_files.json"), selected)
	contextHash := contentHash(fixture, selected)
	writeText(filepath.Join(expected, "context_sha256.txt"), contextHash+"\n")

	marker := map[string]any{
		"schema_version": 1, "name": "golden-skill", "source": "golden-skill",
		"ref_kind": "revision", "ref": fixedCommit, "commit": fixedCommit,
		"content_sha256": contextHash, "locale": nil, "agents": []any{"codex_cli"},
		"commands": []any{"golden-tool"}, "dependencies": []any{},
		"skill_schema_version": 5, "runtime_roots": []any{"scripts"},
		"installed_at": "2000-01-01T00:00:00Z", "files": stringsToAny(selected),
		"activation": map[string]any{"context": true, "commands": []any{"golden-tool"}},
		"requirers":  []any{"<project>"},
	}
	writeJSON(filepath.Join(expected, "marker.json"), marker)
	ledger := map[string]any{"schema_version": 1, "entries": []any{"golden-skill"}}
	writeJSON(filepath.Join(expected, "adapter-ledger.json"), ledger)

	seed := make([]byte, ed25519.SeedSize)
	for index := range seed {
		seed[index] = byte(index)
	}
	private := ed25519.NewKeyFromSeed(seed)
	public := private.Public().(ed25519.PublicKey)
	pinned := "ed25519:" + base64.StdEncoding.EncodeToString(public)
	writeText(filepath.Join(expected, "registry", "pinned_key.txt"), pinned+"\n")

	auditedBody := map[string]any{
		"schema_version": 1,
		"name":           "golden-skill", "source_identity": "git.example.com/skills/golden-skill",
		"commit": fixedCommit, "content_sha256": snapshotHash, "status": "audited",
		"audit": map[string]any{"auditor": "golden", "note": "заметка", "sequence": 1},
	}
	audited := sign(auditedBody, private, public)
	revokedBody := map[string]any{
		"schema_version": 1,
		"name":           "golden-skill", "source_identity": "git.example.com/skills/golden-skill",
		"commit": fixedCommit, "content_sha256": snapshotHash, "status": "revoked",
		"audit": map[string]any{"reason": "test revocation"},
	}
	revoked := sign(revokedBody, private, public)
	forged := cloneMap(audited)
	forged["status"] = "revoked"
	wrongKeyID := cloneMap(audited)
	wrongKeyID["sig"].(map[string]any)["key_id"] = "0000000000000000"
	writeJSON(filepath.Join(expected, "registry", "record_audited.json"), audited)
	writeJSON(filepath.Join(expected, "registry", "record_revoked.json"), revoked)
	writeJSON(filepath.Join(expected, "registry", "record_forged.json"), forged)
	writeJSON(filepath.Join(expected, "registry", "record_wrong_key_id.json"), wrongKeyID)

	entries := buildLog([]map[string]any{audited, revoked})
	writeJSON(filepath.Join(expected, "registry", "log.json"), map[string]any{"entries": mapsToAny(entries), "next_cursor": nil})
	rootHash := merkleRoot(entries)
	head := entries[len(entries)-1]["entry_hash"].(string)
	snapshot := sign(map[string]any{
		"schema_version": 1, "merkle_root": rootHash, "log_size": len(entries),
		"head": head, "version": len(entries), "created_at": fixedTime,
	}, private, public)
	writeJSON(filepath.Join(expected, "registry", "snapshot.json"), snapshot)
	bundle := map[string]any{
		"schema_version": 1, "records": []any{audited, revoked},
		"snapshot": snapshot, "public_key": pinned,
	}
	writeJSON(filepath.Join(expected, "registry", "bundle.json"), bundle)

	writeCanonicalVectors(vectors)
	writeBehaviorVectors(vectors, snapshotHash)
	writeSchemaCases(suite, marker, ledger, audited, snapshot, entries[0], bundle, pinned)
	writeManifest(suite)
}

func writeCanonicalVectors(dir string) {
	inputs := []struct {
		name  string
		value any
	}{
		{"sorted-object", map[string]any{"z": "заметка", "a": []any{true, nil, 0, -12}}},
		{"string-escapes", map[string]any{"s": "\b\f\n\r\t<>/&\\\""}},
		{"nested-signature-kept", map[string]any{"endorsement": map[string]any{"sig": map[string]any{"key_id": "nested"}}, "sig": map[string]any{"key_id": "outer"}}},
	}
	var valid []any
	for _, item := range inputs {
		valid = append(valid, map[string]any{
			"name": item.name, "input": item.value, "canonical_utf8": string(canonicalBytes(item.value)),
		})
	}
	writeJSON(filepath.Join(dir, "canonical-valid.json"), valid)
	writeJSON(filepath.Join(dir, "canonical-invalid.json"), []any{
		map[string]any{"name": "duplicate-key", "input_text": "{\"a\":1,\"a\":2}", "error": "duplicate_key"},
		map[string]any{"name": "fraction", "input_text": "{\"n\":1.5}", "error": "non_integer_number"},
		map[string]any{"name": "unsafe-integer", "input_text": "{\"n\":9007199254740992}", "error": "unsafe_integer"},
		map[string]any{"name": "lone-surrogate", "input_text": "{\"s\":\"\\ud800\"}", "error": "invalid_unicode"},
	})
}

func writeBehaviorVectors(dir, snapshotHash string) {
	writeJSON(filepath.Join(dir, "source-identities.json"), []any{
		map[string]any{"input": "git@git.example.com:skills/a.git", "identity": "git.example.com/skills/a"},
		map[string]any{"input": "https://GIT.example.com/Skills/A.git", "identity": "git.example.com/Skills/A"},
		map[string]any{"input": "ssh://git@git.example.com/skills/a", "identity": "git.example.com/skills/a"},
		map[string]any{"input": "file:///tmp/a", "identity": nil},
		map[string]any{"input": "https://git.example.com:8443/skills/a", "error": "explicit_port"},
		map[string]any{"input": "https://git.example.com/skills%2Fa", "error": "percent_escape"},
		map[string]any{"input": "https://git.example.com/skills/a?q=1", "error": "query"},
	})
	writeJSON(filepath.Join(dir, "portable-paths.json"), []any{
		map[string]any{"input": "scripts/tool", "valid": true},
		map[string]any{"input": "références/文書.md", "valid": true},
		map[string]any{"input": "../escape", "valid": false},
		map[string]any{"input": "scripts\\tool", "valid": false},
		map[string]any{"input": "CON", "valid": false},
		map[string]any{"input": "dir/NUL.txt", "valid": false},
		map[string]any{"input": "trailing. ", "valid": false},
	})
	writeJSON(filepath.Join(dir, "closures.json"), []any{
		map[string]any{
			"name": "deterministic-diamond", "nodes": []any{"app", "alpha", "beta", "base"},
			"edges":                   []any{[]any{"app", "beta"}, []any{"app", "alpha"}, []any{"alpha", "base"}, []any{"beta", "base"}},
			"expected_provider_order": []any{"base", "alpha", "beta", "app"},
		},
		map[string]any{"name": "cycle", "edges": []any{[]any{"a", "b"}, []any{"b", "a"}}, "error": "dependency_cycle"},
		map[string]any{"name": "commit-conflict", "requirements": []any{
			map[string]any{"name": "base", "commit": strings.Repeat("a", 40)},
			map[string]any{"name": "base", "commit": strings.Repeat("b", 40)},
		}, "error": "commit_conflict"},
	})
	writeJSON(filepath.Join(dir, "registry-resolution.json"), []any{
		map[string]any{"name": "audited-only", "records": []any{"record_audited.json"}, "expected": "audited"},
		map[string]any{"name": "deny-wins", "records": []any{"record_audited.json", "record_revoked.json"}, "expected": "revoked"},
		map[string]any{"name": "forged-ignored", "records": []any{"record_forged.json"}, "expected": "unknown"},
		map[string]any{"name": "wrong-key-id-ignored", "records": []any{"record_wrong_key_id.json"}, "expected": "unknown"},
	})
	writeJSON(filepath.Join(dir, "registry-behavior.json"), map[string]any{
		"artifact_hash": snapshotHash,
		"snapshot":      map[string]any{"max_age_seconds": 604800, "future_skew_seconds": 300, "rollback_rejected": true, "equal_version_equivocation_rejected": true},
		"cache":         map[string]any{"ttl_seconds": 3600, "offline_grace_seconds": 604800, "body_limit_bytes": 16777216, "record_limit": 10000},
		"pagination":    map[string]any{"default_limit": 100, "maximum_limit": 1000, "cursor_bound_to_query": true},
		"submission":    map[string]any{"idempotency_key": "sha256_of_ccj1", "retention_seconds": 86400},
	})
}

func writeSchemaCases(suite string, marker, ledger, audited, snapshot, logEntry, bundle map[string]any, pinned string) {
	validSkill := func(version int) map[string]any {
		obj := map[string]any{"schema_version": version, "commands": map[string]any{}}
		if version >= 2 {
			obj["runtime_roots"] = []any{}
		}
		if version >= 3 {
			obj["capabilities"] = map[string]any{}
		}
		if version >= 2 {
			obj["dependencies"] = map[string]any{"commands": map[string]any{}}
		}
		if version >= 4 {
			obj["dependencies"].(map[string]any)["skills"] = map[string]any{}
		}
		if version >= 5 {
			obj["dependencies"].(map[string]any)["mcp_servers"] = map[string]any{}
		}
		return obj
	}
	cases := map[string]schemaCase{}
	for version := 1; version <= 5; version++ {
		name := fmt.Sprintf("csk-skill-v%d.schema.json", version)
		invalid := map[string]any{"schema_version": version, "install": "echo unsafe"}
		if version == 1 {
			invalid = map[string]any{"schema_version": 1, "runtime_roots": []any{"scripts"}}
		}
		cases[name] = schemaCase{validSkill(version), invalid}
	}
	cases["skillfile-v1.schema.json"] = schemaCase{
		map[string]any{"schema_version": 1, "skills": []any{map[string]any{"name": "golden-skill", "revision": fixedCommit}}},
		map[string]any{"schema_version": 1, "skills": []any{map[string]any{"name": "golden-skill", "tag": "v1", "branch": "main"}}},
	}
	cases["hybrid-skillfile-v1.schema.json"] = schemaCase{
		map[string]any{"schema_version": 1, "skills": []any{map[string]any{"name": "golden-skill", "revision": fixedCommit, "targets": []any{"project-*"}}}},
		map[string]any{"schema_version": 1, "skills": []any{map[string]any{"name": "golden-skill", "revision": fixedCommit}}},
	}
	cases["skillfile-dev-v1.schema.json"] = schemaCase{
		map[string]any{"substitutions": map[string]any{"golden-skill": map[string]any{"path": "../golden-skill"}}},
		map[string]any{"substitutions": map[string]any{"golden-skill": map[string]any{"path": "x", "git": "https://example/x"}}},
	}
	cases["install-marker-v1.schema.json"] = schemaCase{marker, without(marker, "locale")}
	cases["adapter-ledger-v1.schema.json"] = schemaCase{ledger, map[string]any{"schema_version": 1, "entries": []any{"CON"}}}
	cases["audit-record-v1.schema.json"] = schemaCase{audited, without(audited, "sig")}
	cases["signature-envelope-v1.schema.json"] = schemaCase{audited["sig"], map[string]any{"algorithm": "rsa", "key_id": "bad", "signature": "bad"}}
	cases["registry-snapshot-v1.schema.json"] = schemaCase{snapshot, without(snapshot, "head")}
	cases["registry-log-entry-v1.schema.json"] = schemaCase{logEntry, map[string]any{"seq": 0}}
	cases["registry-bundle-v1.schema.json"] = schemaCase{bundle, without(bundle, "snapshot")}
	cases["manager-config-v1.schema.json"] = schemaCase{
		map[string]any{"schema_version": 1, "skills_root": "/tmp/skills", "projects": map[string]any{}},
		map[string]any{"schema_version": 1, "projects": map[string]any{}},
	}
	cases["system-config-v1.schema.json"] = schemaCase{map[string]any{"schema_version": 1, "locked": []any{"audit"}, "audit": map[string]any{}}, map[string]any{"schema_version": 1, "locked": []any{"skills_root"}}}
	cases["health-response-v1.schema.json"] = schemaCase{map[string]any{"status": "ok"}, map[string]any{"status": "degraded"}}
	cases["registry-meta-response-v1.schema.json"] = schemaCase{
		map[string]any{"name": "golden", "version": "1.0.0", "public_keys": []any{pinned}, "record_schema_versions": []any{1}, "policy": "test"},
		map[string]any{"name": "golden"},
	}
	cases["records-response-v1.schema.json"] = schemaCase{map[string]any{"records": []any{audited}, "next_cursor": nil}, map[string]any{"records": []any{}}}
	cases["log-response-v1.schema.json"] = schemaCase{map[string]any{"entries": []any{logEntry}, "next_cursor": nil}, map[string]any{"entries": []any{map[string]any{"seq": 0}}, "next_cursor": nil}}
	cases["submission-response-v1.schema.json"] = schemaCase{map[string]any{"seq": 1, "entry_hash": logEntry["entry_hash"]}, map[string]any{"seq": 0, "entry_hash": "bad"}}
	cases["error-response-v1.schema.json"] = schemaCase{map[string]any{"error": map[string]any{"code": "invalid_record", "message": "invalid record", "details": map[string]any{}}}, map[string]any{"detail": "invalid"}}
	cases["conformance-claim-v1.schema.json"] = schemaCase{
		map[string]any{"schema_version": 1, "protocol_version": protocolVersion, "implementation": "example", "implementation_version": "1.0", "classes": []any{"core"}, "suite_sha256": "sha256:" + strings.Repeat("0", 64), "operating_systems": []any{"linux"}, "created_at": fixedTime, "result": "pass"},
		map[string]any{"schema_version": 1, "protocol_version": protocolVersion, "result": "fail"},
	}

	root := filepath.Join(suite, "schema-cases")
	var index []any
	var names []string
	for name := range cases {
		names = append(names, name)
	}
	sort.Strings(names)
	for _, name := range names {
		caseDir := filepath.Join(root, strings.TrimSuffix(name, ".schema.json"))
		must(os.MkdirAll(caseDir, 0o755))
		writeJSON(filepath.Join(caseDir, "valid.json"), cases[name].valid)
		writeJSON(filepath.Join(caseDir, "invalid.json"), cases[name].invalid)
		index = append(index,
			map[string]any{"schema": name, "instance": filepath.ToSlash(filepath.Join(strings.TrimSuffix(name, ".schema.json"), "valid.json")), "valid": true},
			map[string]any{"schema": name, "instance": filepath.ToSlash(filepath.Join(strings.TrimSuffix(name, ".schema.json"), "invalid.json")), "valid": false},
		)
	}
	writeJSON(filepath.Join(root, "index.json"), index)
}

func buildLog(records []map[string]any) []map[string]any {
	prev := genesis
	entries := make([]map[string]any, 0, len(records))
	for index, record := range records {
		sum := sha256.Sum256(append([]byte(prev), canonicalBytes(record)...))
		hash := hex.EncodeToString(sum[:])
		entries = append(entries, map[string]any{"seq": index + 1, "entry_hash": hash, "prev_hash": prev, "record": record})
		prev = hash
	}
	return entries
}

func merkleRoot(entries []map[string]any) string {
	if len(entries) == 0 {
		return genesis
	}
	level := make([][]byte, len(entries))
	for index, entry := range entries {
		decoded, err := hex.DecodeString(entry["entry_hash"].(string))
		must(err)
		level[index] = decoded
	}
	for len(level) > 1 {
		var next [][]byte
		for index := 0; index < len(level); index += 2 {
			right := level[index]
			if index+1 < len(level) {
				right = level[index+1]
			}
			sum := sha256.Sum256(append(append([]byte{}, level[index]...), right...))
			next = append(next, sum[:])
		}
		level = next
	}
	return hex.EncodeToString(level[0])
}

func regularFiles(root string) []string {
	var files []string
	must(filepath.WalkDir(root, func(path string, entry fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if entry.Type().IsRegular() {
			rel, relErr := filepath.Rel(root, path)
			if relErr != nil {
				return relErr
			}
			files = append(files, filepath.ToSlash(rel))
		}
		return nil
	}))
	sort.Strings(files)
	return files
}

func selectedContextFiles(root string) []string {
	var manifest struct {
		RuntimeRoots []string       `json:"runtime_roots"`
		Commands     map[string]any `json:"commands"`
	}
	payload, err := os.ReadFile(filepath.Join(root, "csk-skill.json"))
	must(err)
	must(json.Unmarshal(payload, &manifest))
	var files []string
	for _, rel := range regularFiles(root) {
		parts := strings.Split(rel, "/")
		if !includeRoots[parts[0]] && !(parts[0] == "scripts" && len(manifest.Commands) == 0) {
			continue
		}
		if excluded(parts) || underRoot(rel, manifest.RuntimeRoots) {
			continue
		}
		files = append(files, rel)
	}
	return files
}

func excluded(parts []string) bool {
	for _, part := range parts {
		for _, pattern := range excludedPatterns {
			matched, _ := filepath.Match(pattern, part)
			if matched {
				return true
			}
		}
	}
	return false
}

func underRoot(path string, roots []string) bool {
	for _, root := range roots {
		if path == root || strings.HasPrefix(path, strings.TrimRight(root, "/")+"/") {
			return true
		}
	}
	return false
}

func contentHash(root string, files []string) string {
	digest := sha256.New()
	for index, rel := range files {
		if index > 0 {
			_, _ = digest.Write([]byte{0})
		}
		_, _ = digest.Write([]byte(rel))
		_, _ = digest.Write([]byte{0})
		payload, err := os.ReadFile(filepath.Join(root, filepath.FromSlash(rel)))
		must(err)
		_, _ = digest.Write(payload)
	}
	return "sha256:" + hex.EncodeToString(digest.Sum(nil))
}

func sign(body map[string]any, private ed25519.PrivateKey, public ed25519.PublicKey) map[string]any {
	record := cloneMap(body)
	signature := ed25519.Sign(private, canonicalBytes(record))
	keyHash := sha256.Sum256(public)
	record["sig"] = map[string]any{"algorithm": "ed25519", "key_id": hex.EncodeToString(keyHash[:])[:16], "signature": base64.StdEncoding.EncodeToString(signature)}
	return record
}

func canonicalBytes(value any) []byte {
	if object, ok := value.(map[string]any); ok {
		body := cloneMap(object)
		delete(body, "sig")
		return canonicalValue(body)
	}
	return canonicalValue(value)
}

func canonicalValue(value any) []byte {
	switch typed := value.(type) {
	case map[string]any:
		keys := make([]string, 0, len(typed))
		for key := range typed {
			keys = append(keys, key)
		}
		sort.Strings(keys)
		var out strings.Builder
		out.WriteByte('{')
		for index, key := range keys {
			if index > 0 {
				out.WriteByte(',')
			}
			out.Write(canonicalString(key))
			out.WriteByte(':')
			out.Write(canonicalValue(typed[key]))
		}
		out.WriteByte('}')
		return []byte(out.String())
	case []any:
		var out strings.Builder
		out.WriteByte('[')
		for index, item := range typed {
			if index > 0 {
				out.WriteByte(',')
			}
			out.Write(canonicalValue(item))
		}
		out.WriteByte(']')
		return []byte(out.String())
	case string:
		return canonicalString(typed)
	case nil:
		return []byte("null")
	case bool:
		if typed {
			return []byte("true")
		}
		return []byte("false")
	case int:
		return []byte(strconv.Itoa(typed))
	case int64:
		return []byte(strconv.FormatInt(typed, 10))
	case json.Number:
		value, err := strconv.ParseInt(string(typed), 10, 64)
		must(err)
		if value < -9007199254740991 || value > 9007199254740991 {
			panic("CCJ-1 integer outside safe range")
		}
		return []byte(strconv.FormatInt(value, 10))
	default:
		panic(fmt.Sprintf("unsupported CCJ-1 value %T", value))
	}
}

func canonicalString(value string) []byte {
	if !utf8.ValidString(value) {
		panic("invalid UTF-8")
	}
	var out strings.Builder
	out.WriteByte('"')
	for _, r := range value {
		switch r {
		case '"':
			out.WriteString(`\"`)
		case '\\':
			out.WriteString(`\\`)
		case '\b':
			out.WriteString(`\b`)
		case '\f':
			out.WriteString(`\f`)
		case '\n':
			out.WriteString(`\n`)
		case '\r':
			out.WriteString(`\r`)
		case '\t':
			out.WriteString(`\t`)
		default:
			if r < 0x20 {
				fmt.Fprintf(&out, `\u%04x`, r)
			} else {
				out.WriteRune(r)
			}
		}
	}
	out.WriteByte('"')
	return []byte(out.String())
}

func cloneMap(value map[string]any) map[string]any { return cloneAny(value).(map[string]any) }
func cloneAny(value any) any {
	switch typed := value.(type) {
	case map[string]any:
		out := map[string]any{}
		for key, item := range typed {
			out[key] = cloneAny(item)
		}
		return out
	case []any:
		out := make([]any, len(typed))
		for index, item := range typed {
			out[index] = cloneAny(item)
		}
		return out
	default:
		return typed
	}
}

func without(value map[string]any, key string) map[string]any {
	out := cloneMap(value)
	delete(out, key)
	return out
}
func stringsToAny(values []string) []any {
	out := make([]any, len(values))
	for index, value := range values {
		out[index] = value
	}
	return out
}
func mapsToAny(values []map[string]any) []any {
	out := make([]any, len(values))
	for index, value := range values {
		out[index] = value
	}
	return out
}

func writeManifest(suite string) {
	var files []string
	must(filepath.WalkDir(suite, func(path string, entry fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if !entry.Type().IsRegular() {
			return nil
		}
		rel, relErr := filepath.Rel(suite, path)
		if relErr != nil {
			return relErr
		}
		rel = filepath.ToSlash(rel)
		if rel == "manifest.json" {
			return nil
		}
		payload, readErr := os.ReadFile(path)
		if readErr != nil {
			return readErr
		}
		sum := sha256.Sum256(payload)
		files = append(files, rel+"\tsha256:"+hex.EncodeToString(sum[:]))
		return nil
	}))
	sort.Strings(files)
	entries := make([]any, 0, len(files))
	for _, line := range files {
		parts := strings.SplitN(line, "\t", 2)
		entries = append(entries, map[string]any{"path": parts[0], "sha256": parts[1]})
	}
	writeJSON(filepath.Join(suite, "manifest.json"), map[string]any{"protocol_version": protocolVersion, "generated_at": fixedTime, "generator": "tools/generate-vectors", "files": entries})
}

func writeJSON(path string, value any) {
	must(os.MkdirAll(filepath.Dir(path), 0o755))
	file, err := os.Create(path)
	must(err)
	encoder := json.NewEncoder(file)
	encoder.SetEscapeHTML(false)
	encoder.SetIndent("", "  ")
	must(encoder.Encode(value))
	must(file.Close())
}

func writeText(path, text string) {
	must(os.MkdirAll(filepath.Dir(path), 0o755))
	must(os.WriteFile(path, []byte(text), 0o644))
}
func must(err error) {
	if err != nil {
		panic(fmt.Sprintf("generate conformance vectors: %v", err))
	}
}
