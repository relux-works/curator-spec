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
	protocolVersion = "1.0.0-rc.3"
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
	writeSkillManifestResolutionVectors(vectors)
	writeManagerConfigVectors(vectors, pinned)
	writeManagerLifecycleVectors(vectors)
	writeSchemaCases(suite, marker, ledger, audited, snapshot, entries[0], bundle, pinned)
	writeManifest(suite)
}

func writeSkillManifestResolutionVectors(dir string) {
	canonical := "{\"schema_version\":1,\"commands\":{}}\n"
	legacyEquivalent := "{\n  \"commands\": {},\n  \"schema_version\": 1\n}\n"
	writeJSON(filepath.Join(dir, "skill-manifest-resolution.json"), []any{
		map[string]any{
			"name": "canonical-only", "files": map[string]any{"agent-skill.json": canonical},
			"expected_source": "agent-skill.json", "expected_commands": []any{},
		},
		map[string]any{
			"name": "legacy-only", "files": map[string]any{"csk-skill.json": canonical},
			"expected_source": "csk-skill.json", "expected_commands": []any{},
		},
		map[string]any{
			"name":            "equal-dual-manifests",
			"files":           map[string]any{"agent-skill.json": canonical, "csk-skill.json": legacyEquivalent},
			"expected_source": "agent-skill.json", "expected_commands": []any{},
		},
		map[string]any{
			"name": "conflicting-dual-manifests",
			"files": map[string]any{
				"agent-skill.json": canonical,
				"csk-skill.json":   "{\"schema_version\":1,\"commands\":{\"legacy\":{\"type\":\"system\",\"command\":\"legacy\"}}}\n",
			},
			"error": "conflicting_skill_manifests",
		},
		map[string]any{
			"name":  "invalid-canonical-does-not-fallback",
			"files": map[string]any{"agent-skill.json": "{\n", "csk-skill.json": canonical},
			"error": "manifest_invalid",
		},
		map[string]any{
			"name":  "invalid-legacy-does-not-hide-behind-canonical",
			"files": map[string]any{"agent-skill.json": canonical, "csk-skill.json": "{\n"},
			"error": "manifest_invalid",
		},
		map[string]any{
			"name":            "runtime-fallback-without-modern-manifest",
			"files":           map[string]any{"agents/runtime.json": "{\"commands\":{\"legacy\":\"scripts/legacy\"}}\n"},
			"expected_source": "agents/runtime.json", "expected_commands": []any{"legacy"},
		},
		map[string]any{
			"name": "pure-context-without-manifest", "files": map[string]any{},
			"expected_source": nil, "expected_commands": []any{},
		},
	})
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
		map[string]any{"name": "negative-zero", "input_text": "{\"n\":-0}", "error": "non_shortest_integer"},
		map[string]any{"name": "unsafe-integer", "input_text": "{\"n\":9007199254740992}", "error": "unsafe_integer"},
		map[string]any{"name": "lone-surrogate", "input_text": "{\"s\":\"\\ud800\"}", "error": "invalid_unicode"},
	})
}

func writeBehaviorVectors(dir, snapshotHash string) {
	writeJSON(filepath.Join(dir, "identifiers.json"), []any{
		map[string]any{"input": "skill-youtrack", "valid": true},
		map[string]any{"input": "9lives", "valid": true},
		map[string]any{"input": "a.b_c-d", "valid": true},
		map[string]any{"input": "", "valid": false},
		map[string]any{"input": "-leading", "valid": false},
		map[string]any{"input": ".hidden", "valid": false},
		map[string]any{"input": "has space", "valid": false},
		map[string]any{"input": "unicode-é", "valid": false},
		map[string]any{"input": "trailing.", "valid": false},
		map[string]any{"input": "CON", "valid": false},
		map[string]any{"input": "nul.txt", "valid": false},
		map[string]any{"input": "COM1.log", "valid": false},
		map[string]any{"input": strings.Repeat("a", 129), "valid": false},
	})
	writeJSON(filepath.Join(dir, "locale-selectors.json"), []any{
		map[string]any{"input": "en", "valid": true},
		map[string]any{"input": "pt-BR", "valid": true},
		map[string]any{"input": "zh-Hans-CN", "valid": true},
		map[string]any{"input": "", "valid": false},
		map[string]any{"input": "-en", "valid": false},
		map[string]any{"input": "en-", "valid": false},
		map[string]any{"input": "pt_BR", "valid": false},
		map[string]any{"input": "../en", "valid": false},
		map[string]any{"input": "русский", "valid": false},
		map[string]any{"input": strings.Repeat("a", 65), "valid": false},
	})
	writeJSON(filepath.Join(dir, "source-identities.json"), []any{
		map[string]any{"input": "git@git.example.com:skills/a.git", "identity": "git.example.com/skills/a"},
		map[string]any{"input": "https://GIT.example.com/Skills/A.git", "identity": "git.example.com/Skills/A"},
		map[string]any{"input": "ssh://git@git.example.com/skills/a", "identity": "git.example.com/skills/a"},
		map[string]any{"input": "file:///tmp/a", "identity": nil},
		map[string]any{"input": "https://git.example.com:8443/skills/a", "error": "explicit_port"},
		map[string]any{"input": "https://git.example.com/skills%2Fa", "error": "percent_escape"},
		map[string]any{"input": "https://git.example.com/skills/a?q=1", "error": "query"},
		map[string]any{"input": "git@git.example.com:skills/a b", "error": "whitespace"},
		map[string]any{"input": "git@git.example.com:skills/a#fragment", "error": "fragment"},
		map[string]any{"input": "git@g.example:" + strings.Repeat("a", 4096), "error": "identity_too_long"},
	})
	writeJSON(filepath.Join(dir, "portable-paths.json"), []any{
		map[string]any{"input": "scripts/tool", "valid": true},
		map[string]any{"input": "références/文書.md", "valid": true},
		map[string]any{"input": "directory with space/file name.md", "valid": true},
		map[string]any{"input": "", "valid": false},
		map[string]any{"input": "/absolute", "valid": false},
		map[string]any{"input": "../escape", "valid": false},
		map[string]any{"input": ".", "valid": false},
		map[string]any{"input": "a/..", "valid": false},
		map[string]any{"input": "scripts/", "valid": false},
		map[string]any{"input": "scripts//tool", "valid": false},
		map[string]any{"input": "scripts\\tool", "valid": false},
		map[string]any{"input": "stream:name", "valid": false},
		map[string]any{"input": "control\u0085name", "valid": false},
		map[string]any{"input": "CON", "valid": false},
		map[string]any{"input": "dir/NUL.txt", "valid": false},
		map[string]any{"input": "trailing.", "valid": false},
		map[string]any{"input": "trailing ", "valid": false},
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
		"pagination": map[string]any{
			"default_limit": 100, "maximum_limit": 1000,
			"cursor_bound_to_query": true, "cursor_bound_to_snapshot": true,
			"filter_operator": "and",
		},
		"submission": map[string]any{
			"idempotency_key": "sha256_of_ccj1", "idempotency_scope": "auditor_and_key",
			"retention_seconds": 86400,
		},
	})
	writeRegistryServiceVectors(dir)
	writeRegistryClientVectors(dir)
}

func writeRegistryServiceVectors(dir string) {
	commitA := strings.Repeat("a", 40)
	commitB := strings.Repeat("b", 40)
	hashA := "sha256:" + strings.Repeat("1a", 32)
	hashB := "sha256:" + strings.Repeat("2b", 32)
	sourceA := "git.example.com/skills/alpha"
	sourceB := "mirror.example.com/skills/beta"
	record := func(id, name, source, commit, contentHash, status string) map[string]any {
		return map[string]any{
			"id": id,
			"record": map[string]any{
				"schema_version": 1, "name": name, "source_identity": source,
				"commit": commit, "content_sha256": contentHash, "status": status,
				"audit": map[string]any{"case": id},
			},
		}
	}
	records := []any{
		record("alpha-audited", "alpha", sourceA, commitA, hashA, "audited"),
		record("alpha-revoked", "alpha", sourceA, commitA, hashA, "revoked"),
		record("alpha-equivocated", "alpha", sourceA, commitA, hashB, "pending"),
		record("beta-mirror", "beta", sourceB, commitB, hashA, "audited"),
	}
	writeJSON(filepath.Join(dir, "registry-service.json"), map[string]any{
		"artifact_key": []any{"name", "source_identity", "commit", "content_sha256"},
		"sort_key":     []any{"name", "source_identity", "commit", "content_sha256"},
		"records":      records,
		"query_cases": []any{
			map[string]any{
				"name":         "identity-pair-keeps-content-equivocation",
				"query":        map[string]any{"source_identity": sourceA, "commit": commitA},
				"expected_ids": []any{"alpha-revoked", "alpha-equivocated"},
			},
			map[string]any{
				"name":         "content-hash-matches-mirrors",
				"query":        map[string]any{"content_sha256": hashA},
				"expected_ids": []any{"alpha-revoked", "beta-mirror"},
			},
			map[string]any{
				"name":         "all-filters-are-conjunctive",
				"query":        map[string]any{"source_identity": sourceA, "commit": commitA, "content_sha256": hashB},
				"expected_ids": []any{"alpha-equivocated"},
			},
			map[string]any{
				"name":         "conjunctive-mismatch-is-empty",
				"query":        map[string]any{"source_identity": sourceB, "commit": commitB, "content_sha256": hashB},
				"expected_ids": []any{},
			},
			map[string]any{"name": "source-without-commit", "query": map[string]any{"source_identity": sourceA}, "error": "invalid_query"},
			map[string]any{"name": "commit-without-source", "query": map[string]any{"commit": commitA}, "error": "invalid_query"},
		},
		"pagination": map[string]any{
			"query":                        map[string]any{"content_sha256": hashA, "limit": 1},
			"boundary_log_size":            4,
			"expected_pages":               []any{[]any{"alpha-revoked"}, []any{"beta-mirror"}},
			"append_after_first_page":      record("alpha-recovered", "alpha", sourceA, commitA, hashA, "audited"),
			"expected_original_cursor_ids": []any{"beta-mirror"},
			"expected_new_query_ids":       []any{"alpha-recovered", "beta-mirror"},
			"cursor_rejections":            []any{"changed_query", "changed_limit", "wrong_endpoint", "expired", "unavailable_snapshot"},
			"invalid_cursor_status":        404,
		},
		"idempotency_cases": []any{
			map[string]any{
				"name": "same-auditor-replay", "auditors": []any{"auditor-a", "auditor-a"},
				"key": "request-1", "body_ids": []any{"alpha-audited", "alpha-audited"},
				"statuses": []any{201, 200}, "appends": 1,
			},
			map[string]any{
				"name": "same-auditor-conflict", "auditors": []any{"auditor-a", "auditor-a"},
				"key": "request-2", "body_ids": []any{"alpha-audited", "alpha-equivocated"},
				"statuses": []any{201, 409}, "appends": 1,
			},
			map[string]any{
				"name": "different-auditors-do-not-conflict", "auditors": []any{"auditor-a", "auditor-b"},
				"key": "shared-key", "body_ids": []any{"alpha-audited", "alpha-equivocated"},
				"statuses": []any{201, 201}, "appends": 2,
			},
		},
		"transaction_cases": []any{
			map[string]any{"name": "concurrent-writers", "writers": 32, "expected_first_seq": 1, "expected_last_seq": 32, "contiguous": true},
			map[string]any{"name": "failure-before-commit", "injection_point": "after_log_insert", "state_unchanged": true},
			map[string]any{"name": "bundle-import-failure", "injection_point": "before_import_ledger", "state_unchanged": true},
		},
		"snapshot": map[string]any{
			"version_equals_log_size": true, "created_at_immutable_per_boundary": true,
			"key_rotation_preserves_body": true,
		},
		"recovery_cases": []any{
			map[string]any{"name": "valid-restart", "mutation": "none", "ready": true},
			map[string]any{"name": "broken-previous-hash", "mutation": "prev_hash", "ready": false},
			map[string]any{"name": "broken-entry-hash", "mutation": "entry_hash", "ready": false},
			map[string]any{"name": "missing-sequence", "mutation": "sequence_gap", "ready": false},
			map[string]any{"name": "idempotency-orphan", "mutation": "idempotency_seq", "ready": false},
			map[string]any{"name": "import-ledger-orphan", "mutation": "import_seq", "ready": false},
			map[string]any{"name": "missing-service-metadata", "mutation": "metadata", "ready": false},
			map[string]any{"name": "missing-schema-table", "mutation": "schema_table", "ready": false},
		},
		"restore_cases": []any{
			map[string]any{"name": "checkpoint-equal", "restored_version": 8, "checkpoint_version": 8, "matching_head": true, "ready": true},
			map[string]any{"name": "checkpoint-rollback", "restored_version": 7, "checkpoint_version": 8, "matching_head": false, "ready": false},
			map[string]any{"name": "checkpoint-equivocation", "restored_version": 8, "checkpoint_version": 8, "matching_head": false, "ready": false},
		},
		"limits": map[string]any{
			"body_bytes": 16777216, "page_items": 1000, "cursor_characters": 4096,
			"idempotency_key_characters": 256, "idempotency_retention_seconds": 86400,
		},
		"transport_cases": []any{
			map[string]any{"name": "maximum-page-size", "query_limit": 1000, "status": 200},
			map[string]any{"name": "oversize-page", "query_limit": 1001, "status": 400, "error": "invalid_query"},
			map[string]any{"name": "oversize-cursor", "cursor_characters": 4097, "status": 404, "error": "invalid_cursor"},
			map[string]any{"name": "oversize-request-body", "body_bytes": 16777217, "status": 413, "error": "request_too_large"},
			map[string]any{"name": "compressed-request-body", "content_encoding": "gzip", "status": 415, "error": "unsupported_media_type"},
			map[string]any{"name": "maximum-idempotency-key", "idempotency_key_characters": 256, "status": 201},
			map[string]any{"name": "oversize-idempotency-key", "idempotency_key_characters": 257, "status": 400, "error": "invalid_idempotency_key"},
			map[string]any{"name": "non-visible-idempotency-key", "idempotency_key": "contains space", "status": 400, "error": "invalid_idempotency_key"},
			map[string]any{"name": "network-rate-limit", "configured_requests": 1, "status": 429, "error": "rate_limited", "retry_after": true},
			map[string]any{"name": "auditor-rate-limit", "configured_submissions": 1, "status": 429, "error": "rate_limited", "retry_after": true},
		},
		"cache_cases": []any{
			map[string]any{"name": "public-read", "request": "GET /v1/snapshot", "cache_control": "public"},
			map[string]any{"name": "authenticated-write", "request": "POST /v1/records", "cache_control": "no-store"},
			map[string]any{"name": "error-response", "request": "GET /v1/records invalid", "cache_control": "no-store"},
		},
	})
}

func writeRegistryClientVectors(dir string) {
	writeJSON(filepath.Join(dir, "registry-client.json"), map[string]any{
		"snapshot_transitions": []any{
			map[string]any{"name": "advance-after-key-rotation", "stored_version": 7, "candidate_version": 8, "same_body": false, "candidate_key": "new", "accepted": true},
			map[string]any{"name": "restore-rollback", "stored_version": 8, "candidate_version": 7, "same_body": false, "candidate_key": "new", "accepted": false},
			map[string]any{"name": "equal-version-repeat", "stored_version": 8, "candidate_version": 8, "same_body": true, "candidate_key": "new", "accepted": true},
			map[string]any{"name": "equal-version-equivocation", "stored_version": 8, "candidate_version": 8, "same_body": false, "candidate_key": "new", "accepted": false},
		},
		"retry_cases": []any{
			map[string]any{"name": "get-network", "method": "GET", "outcome": "network_error", "idempotency_key": false, "retry_permitted": true},
			map[string]any{"name": "get-rate-limit", "method": "GET", "outcome": "429", "idempotency_key": false, "retry_permitted": true},
			map[string]any{"name": "get-unavailable", "method": "GET", "outcome": "503", "idempotency_key": false, "retry_permitted": true},
			map[string]any{"name": "get-conflict", "method": "GET", "outcome": "409", "idempotency_key": false, "retry_permitted": false},
			map[string]any{"name": "post-idempotent-unavailable", "method": "POST", "outcome": "503", "idempotency_key": true, "retry_permitted": true},
			map[string]any{"name": "post-unsafe-unavailable", "method": "POST", "outcome": "503", "idempotency_key": false, "retry_permitted": false},
			map[string]any{"name": "post-idempotent-bad-request", "method": "POST", "outcome": "400", "idempotency_key": true, "retry_permitted": false},
		},
		"retry_policy": map[string]any{
			"max_attempts": 3, "get_total_deadline_seconds": 30,
			"post_total_deadline_seconds": 45, "follow_redirects": false,
		},
		"pagination_rejections": []any{
			map[string]any{"name": "repeated-cursor", "error": "pagination_cycle"},
			map[string]any{"name": "oversize-cursor", "characters": 4097, "error": "invalid_cursor"},
			map[string]any{"name": "record-limit", "records": 10001, "error": "record_limit"},
			map[string]any{"name": "oversize-response", "bytes": 16777217, "error": "body_limit"},
		},
		"state_key":                 "canonical_registry_url",
		"key_rotation_resets_state": false,
		"rollback_state_cases": []any{
			map[string]any{"name": "missing-on-first-use", "state": "missing", "accepted": true},
			map[string]any{"name": "deleted-after-prior-use", "state": "deleted", "accepted": false},
			map[string]any{"name": "corrupted-existing-state", "state": "malformed", "accepted": false},
			map[string]any{"name": "unavailable-state-directory", "state": "unavailable", "accepted": false},
		},
	})
}

func writeManagerConfigVectors(dir, pinned string) {
	minimal := map[string]any{
		"schema_version": 1,
		"skills_root":    "./skills",
		"projects":       map[string]any{},
	}
	configured := map[string]any{
		"schema_version":   1,
		"skills_root":      "./skills",
		"preferred_locale": nil,
		"projects": map[string]any{
			"app": map[string]any{
				"path": "./app", "agents": []any{"codex_cli"},
				"project_alias": nil, "checkout_alias": nil,
			},
		},
		"audit_registries": []any{
			map[string]any{
				"name": "primary", "url": "HTTPS://REGISTRY.EXAMPLE:443/api/",
				"public_keys": []any{pinned},
			},
		},
		"audit": map[string]any{
			"max_request_bytes": 2048, "snapshot_max_age_seconds": 86400,
			"snapshot_clock_skew_seconds": 0, "cache_ttl_seconds": 0,
			"offline_grace_seconds": 0,
		},
	}
	base := func() map[string]any {
		return map[string]any{"schema_version": 1, "skills_root": "./skills", "projects": map[string]any{}}
	}
	with := func(key string, value any) map[string]any {
		result := base()
		result[key] = value
		return result
	}
	writeJSON(filepath.Join(dir, "manager-config.json"), []any{
		map[string]any{
			"name": "minimal-defaults", "input": minimal, "valid": true,
			"expected": map[string]any{
				"default_agents": []any{"codex_cli"}, "adapter_mode": "auto",
				"registry_urls": []any{}, "snapshot_max_age_seconds": 604800,
				"snapshot_clock_skew_seconds": 300, "cache_ttl_seconds": 3600,
				"offline_grace_seconds": 604800, "max_request_bytes": 1048576,
			},
		},
		map[string]any{
			"name": "canonical-registry-and-zero-cache", "input": configured, "valid": true,
			"expected": map[string]any{
				"default_agents": []any{"codex_cli"}, "adapter_mode": "auto",
				"project_alias": "app", "checkout_alias": "app",
				"registry_urls":            []any{"https://registry.example/api"},
				"snapshot_max_age_seconds": 86400, "snapshot_clock_skew_seconds": 0,
				"cache_ttl_seconds": 0, "offline_grace_seconds": 0,
				"max_request_bytes": 2048,
			},
		},
		map[string]any{"name": "unknown-top-level", "input": with("typo", true), "valid": false},
		map[string]any{"name": "invalid-project-key", "input": with("projects", map[string]any{"-app": map[string]any{"path": "./app"}}), "valid": false},
		map[string]any{"name": "invalid-project-alias", "input": with("projects", map[string]any{"app": map[string]any{"path": "./app", "project_alias": "App Label"}}), "valid": false},
		map[string]any{"name": "unknown-project-field", "input": with("projects", map[string]any{"app": map[string]any{"path": "./app", "typo": true}}), "valid": false},
		map[string]any{"name": "duplicate-agents", "input": with("default_agents", []any{"codex_cli", "codex_cli"}), "valid": false},
		map[string]any{"name": "unknown-registry-field", "input": with("audit_registries", []any{map[string]any{"name": "r", "url": "https://r.example", "required": true}}), "valid": false},
		map[string]any{"name": "malformed-pinned-key", "input": with("audit_registries", []any{map[string]any{"name": "r", "url": "https://r.example", "public_keys": []any{"ed25519:bad"}}}), "valid": false},
		map[string]any{"name": "insecure-registry", "input": with("audit_registries", []any{map[string]any{"name": "r", "url": "http://r.example"}}), "valid": false},
		map[string]any{"name": "duplicate-canonical-registry", "input": with("audit_registries", []any{map[string]any{"name": "one", "url": "https://R.EXAMPLE:443/"}, map[string]any{"name": "two", "url": "https://r.example"}}), "valid": false},
		map[string]any{"name": "empty-preferred-locale", "input": with("preferred_locale", ""), "valid": false},
		map[string]any{"name": "negative-cache-ttl", "input": with("audit", map[string]any{"cache_ttl_seconds": -1}), "valid": false},
		map[string]any{"name": "oversize-backend-request", "input": with("audit", map[string]any{"max_request_bytes": 10485761}), "valid": false},
		map[string]any{"name": "unknown-source-policy-field", "input": with("audit", map[string]any{"source_policy": map[string]any{"classification": "public"}}), "valid": false},
	})
}

func writeManagerLifecycleVectors(dir string) {
	writeJSON(filepath.Join(dir, "manager-lifecycle.json"), map[string]any{
		"launcher_cases": []any{
			map[string]any{
				"name": "skill-command-without-shell-activation", "platforms": []any{"unix", "windows"},
				"required_path_roles":     []any{"command_directory", "implementation_runtime", "system_dependencies"},
				"preserve_inherited_path": true, "forward_arguments": true, "preserve_exit_status": true,
			},
			map[string]any{
				"name": "declared-system-command-without-profile", "platforms": []any{"unix", "windows"},
				"required_path_roles":     []any{"command_directory", "implementation_runtime", "system_dependencies"},
				"preserve_inherited_path": true, "forward_arguments": true, "preserve_exit_status": true,
			},
		},
		"bootstrap_cases": []any{
			map[string]any{"name": "missing-config-if-missing", "config": "missing", "if_missing": true, "force": false, "outcome": "created"},
			map[string]any{"name": "existing-config-if-missing", "config": "existing-invalid", "if_missing": true, "force": false, "outcome": "unchanged-success"},
			map[string]any{"name": "if-missing-with-force", "config": "either", "if_missing": true, "force": true, "outcome": "usage-error"},
		},
		"upgrade_cases": []any{
			map[string]any{"name": "selected-project-closure", "scope": "project", "selection": "one", "fetch": []any{"direct", "transitive"}, "exclude": []any{"unrelated"}},
			map[string]any{"name": "all-projects-deduplicate", "scope": "project", "selection": "all", "deduplicate": true},
			map[string]any{"name": "global-closure", "scope": "global", "selection": "global", "fetch": []any{"direct", "transitive"}, "exclude": []any{"unrelated"}},
		},
		"dry_run_cases": []any{
			map[string]any{"name": "project-upgrade", "scope": "project", "forbidden_persistent_effects": []any{"source-fetch", "source-clone", "snapshot-cache", "response-cache", "audit-state", "registry-state", "configuration", "runtime", "project-artifacts"}},
			map[string]any{"name": "global-upgrade", "scope": "global", "forbidden_persistent_effects": []any{"source-fetch", "source-clone", "snapshot-cache", "response-cache", "audit-state", "registry-state", "configuration", "runtime", "global-artifacts"}},
		},
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
		invalid := map[string]any{"schema_version": version, "install": "echo unsafe"}
		if version == 1 {
			invalid = map[string]any{"schema_version": 1, "runtime_roots": []any{"scripts"}}
		}
		for _, prefix := range []string{"agent-skill", "csk-skill"} {
			name := fmt.Sprintf("%s-v%d.schema.json", prefix, version)
			cases[name] = schemaCase{validSkill(version), invalid}
		}
	}
	cases["skillfile-v1.schema.json"] = schemaCase{
		map[string]any{"schema_version": 1, "project": map[string]any{"alias": "Golden iOS"}, "skills": []any{map[string]any{"name": "golden-skill", "revision": fixedCommit}}},
		map[string]any{"schema_version": 1, "skills": []any{map[string]any{"name": "golden-skill", "tag": "v1", "branch": "main"}}},
	}
	cases["hybrid-skillfile-v1.schema.json"] = schemaCase{
		map[string]any{"schema_version": 1, "project": map[string]any{"alias": "Golden iOS"}, "skills": []any{map[string]any{"name": "golden-skill", "revision": fixedCommit, "targets": []any{"project-*"}}}},
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
		map[string]any{
			"schema_version": 1, "skills_root": "/tmp/skills", "preferred_locale": nil,
			"projects":         map[string]any{"app": map[string]any{"path": "/tmp/app", "project_alias": nil}},
			"audit_registries": []any{map[string]any{"name": "primary", "url": "HTTPS://registry.example"}},
			"audit":            map[string]any{"cache_ttl_seconds": 0, "offline_grace_seconds": 0},
		},
		map[string]any{"schema_version": 1, "projects": map[string]any{}},
	}
	cases["system-config-v1.schema.json"] = schemaCase{map[string]any{"schema_version": 1, "locked": []any{"audit"}, "audit": map[string]any{}, "preferred_locale": "en"}, map[string]any{"schema_version": 1, "locked": []any{"skills_root"}}}
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
	payload, err := os.ReadFile(filepath.Join(root, "agent-skill.json"))
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
