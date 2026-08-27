// Command generate-vectors creates the Curator Protocol v1 conformance
// vectors without importing either conforming implementation.
package main

import (
	"bytes"
	"crypto/ed25519"
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
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"unicode/utf8"
)

const (
	protocolVersion                   = "1.0.0-rc.5"
	conformanceClaimV1ProtocolVersion = "1.0.0-rc.3"
	conformanceClaimV2ProtocolVersion = "1.0.0-rc.4"
	conformanceClaimV2CreatedAt       = "2026-07-20T00:00:00Z"
	rc5CreatedAt                      = "2026-07-28T00:00:00Z"
	fixedCommit                       = "0123456789abcdef0123456789abcdef01234567"
	fixedTime                         = "2026-07-13T00:00:00Z"
	genesis                           = "0000000000000000000000000000000000000000000000000000000000000000"
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

type schemaExample struct {
	name     string
	valid    bool
	instance any
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
	writeExternalRepositoryFixtures(suite)
	writeExternalRepositoryVectors(vectors)
	writeSchemaCases(suite, marker, ledger, audited, snapshot, entries[0], bundle, pinned)
	writeExternalRepositoryExpected(expected, marker)
	writeManifest(suite)
	writeRC5ReleaseMetadata(*root, suite)
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

func writeExternalRepositoryFixtures(suite string) {
	fixtures := filepath.Join(suite, "fixtures", "external-repository")
	sha256Commit := strings.Repeat("a", 64)
	validCommit := "tree " + strings.Repeat("a", 40) + "\n" +
		"parent " + strings.Repeat("b", 40) + "\n" +
		"author A U Thor <a@example.test> 1 +0000\n" +
		"committer C O Mitter <c@example.test> 2 +0000\n" +
		"gpgsig -----BEGIN PGP SIGNATURE-----\n payload\n -----END PGP SIGNATURE-----\n" +
		"x-curator-fixture opaque\n\nmessage\r\nbody\n"
	rawObjects := []any{
		rawObjectCase("valid-commit-with-signed-and-extra-headers", "commit", "sha1", []byte(validCommit), "valid"),
		rawObjectCase("reject-duplicate-tree-header", "commit", "sha1", []byte(
			"tree "+strings.Repeat("a", 40)+"\ntree "+strings.Repeat("b", 40)+"\nauthor A <a@b> 1 +0000\ncommitter C <c@d> 2 +0000\n\nmessage\n",
		), "build_repository_git_object_semantics_invalid"),
		rawObjectCase("reject-misordered-tree-after-parent", "commit", "sha1", []byte(
			"parent "+strings.Repeat("b", 40)+"\ntree "+strings.Repeat("a", 40)+"\nauthor A <a@b> 1 +0000\ncommitter C <c@d> 2 +0000\n\nmessage\n",
		), "build_repository_git_object_semantics_invalid"),
		rawObjectCase("reject-missing-header-message-separator", "commit", "sha1", []byte(
			"tree "+strings.Repeat("a", 40)+"\nauthor A <a@b> 1 +0000\ncommitter C <c@d> 2 +0000\nmessage\n",
		), "build_repository_git_object_semantics_invalid"),
		rawObjectCase("valid-signed-annotated-tag", "tag", "sha1", []byte(
			"object "+strings.Repeat("a", 40)+"\ntype commit\ntag v1.4.0\ntagger T Agger <t@example.test> 3 +0000\n\nrelease\n-----BEGIN PGP SIGNATURE-----\nopaque\n-----END PGP SIGNATURE-----\n",
		), "valid"),
		rawObjectCase("reject-duplicate-object-and-type-headers", "tag", "sha1", []byte(
			"object "+strings.Repeat("a", 40)+"\nobject "+strings.Repeat("b", 40)+"\ntype commit\ntype tag\ntag v1.4.0\n\nmessage\n",
		), "build_repository_git_object_semantics_invalid"),
		rawObjectCase("reject-tag-declared-target-type-mismatch", "tag", "sha1", []byte(
			"object "+strings.Repeat("a", 40)+"\ntype tag\ntag v1.4.0\n\nmessage\n",
		), "build_repository_git_object_semantics_invalid"),
		rawObjectCase("valid-sha256-commit", "commit", "sha256", []byte(
			"tree "+sha256Commit+"\nauthor A <a@b> 1 +0000\ncommitter C <c@d> 2 +0000\n\nsha256\n",
		), "valid"),
		treeObjectCase("valid-regular-and-executable-files", "sha1", []treeFixtureEntry{
			{mode: "100644", name: "README.md", objectID: strings.Repeat("1", 40)},
			{mode: "100755", name: "tool", objectID: strings.Repeat("2", 40)},
		}, "valid"),
		treeObjectCase("reject-symbolic-link", "sha1", []treeFixtureEntry{
			{mode: "120000", name: "link", objectID: strings.Repeat("1", 40)},
		}, "build_repository_git_object_semantics_invalid"),
		treeObjectCase("reject-submodule-gitlink", "sha1", []treeFixtureEntry{
			{mode: "160000", name: "submodule", objectID: strings.Repeat("1", 40)},
		}, "build_repository_git_object_semantics_invalid"),
		treeObjectCase("reject-special-file-mode", "sha1", []treeFixtureEntry{
			{mode: "100600", name: "special", objectID: strings.Repeat("1", 40)},
		}, "build_repository_git_object_semantics_invalid"),
	}
	writeJSON(filepath.Join(fixtures, "raw-objects.json"), map[string]any{
		"source_paths": []any{"network-private-store", "local-inert-copy"},
		"cases":        rawObjects,
	})

	pointer := "version https://git-lfs.github.com/spec/v1\noid sha256:" + strings.Repeat("a", 64) + "\nsize 1\n"
	lfsCases := []any{
		map[string]any{"name": "canonical-current-pointer", "bytes_base64": base64.StdEncoding.EncodeToString([]byte(pointer)), "expected_error": "build_repository_git_lfs_unsupported", "classification": "canonical"},
		map[string]any{"name": "accepted-crlf-blank-unsorted-and-no-terminal-lf", "bytes_base64": base64.StdEncoding.EncodeToString([]byte(
			"\r\nversion https://git-lfs.github.com/spec/v1\r\next-4-a! sha256:" + strings.Repeat("e", 64) + "\r\n\r\next-1-lower sha256:" + strings.Repeat("b", 64) + "\r\noid sha256:" + strings.Repeat("a", 64) + "\r\nsize +01",
		)), "expected_error": "build_repository_git_lfs_unsupported", "classification": "legacy-or-noncanonical"},
		map[string]any{"name": "accepted-exact-duplicate-key-last-value-wins", "bytes_base64": base64.StdEncoding.EncodeToString([]byte(
			"version https://git-lfs.github.com/spec/v1\next-1-a sha256:" + strings.Repeat("b", 64) + "\next-1-a sha256:" + strings.Repeat("c", 64) + "\noid sha256:" + strings.Repeat("a", 64) + "\nsize 1\n",
		)), "expected_error": "build_repository_git_lfs_unsupported", "classification": "legacy-or-noncanonical"},
		map[string]any{"name": "distinct-duplicate-priority-is-ordinary", "bytes_base64": base64.StdEncoding.EncodeToString([]byte(
			"version https://git-lfs.github.com/spec/v1\next-1-a sha256:" + strings.Repeat("b", 64) + "\next-1-b sha256:" + strings.Repeat("c", 64) + "\noid sha256:" + strings.Repeat("a", 64) + "\nsize 1\n",
		)), "expected": "ordinary-blob"},
		map[string]any{"name": "nonempty-size-zero-is-noncanonical", "bytes_base64": base64.StdEncoding.EncodeToString([]byte(
			"version https://git-lfs.github.com/spec/v1\noid sha256:" + strings.Repeat("a", 64) + "\nsize 0\n",
		)), "expected_error": "build_repository_git_lfs_unsupported", "classification": "legacy-or-noncanonical"},
		map[string]any{"name": "cutoff-1023-after-trim", "bytes_base64": base64.StdEncoding.EncodeToString(padTo([]byte(pointer), 1023, ' ')), "expected_error": "build_repository_git_lfs_unsupported", "classification": "legacy-or-noncanonical"},
		map[string]any{"name": "cutoff-1024-is-ordinary", "bytes_base64": base64.StdEncoding.EncodeToString(padTo([]byte(pointer), 1024, ' ')), "expected": "ordinary-blob"},
		map[string]any{"name": "near-miss-extension-starts-with-punctuation", "bytes_base64": base64.StdEncoding.EncodeToString([]byte(
			"version https://git-lfs.github.com/spec/v1\next-1-!a sha256:" + strings.Repeat("b", 64) + "\noid sha256:" + strings.Repeat("a", 64) + "\nsize 1\n",
		)), "expected": "ordinary-blob"},
		map[string]any{"name": "near-miss-uppercase-oid", "bytes_base64": base64.StdEncoding.EncodeToString([]byte(
			"version https://git-lfs.github.com/spec/v1\noid sha256:" + strings.Repeat("A", 64) + "\nsize 1\n",
		)), "expected": "ordinary-blob"},
		map[string]any{"name": "zero-byte-blob", "bytes_base64": "", "expected": "ordinary-blob"},
	}
	writeJSON(filepath.Join(fixtures, "lfs-pointers.json"), map[string]any{
		"parser_family":       "git-lfs-pointer-parser-v3.7.1",
		"candidate_min_bytes": 1,
		"candidate_max_bytes": 1023,
		"cases":               lfsCases,
	})

	sha1Config := "[core]\n\trepositoryformatversion = 0\n\tbare = false\n"
	sha256Config := "[core]\n\trepositoryformatversion = 1\n\tbare = false\n[extensions]\n\tobjectFormat = sha256\n\trefStorage = files\n"
	configCases := []any{
		localLayoutCase("valid-sha1-files-ref", map[string]string{"config": sha1Config, "HEAD": "ref: refs/heads/main\n", "refs/heads/main": fixedCommit + "\n"}, "admitted"),
		localLayoutCase("valid-sha256-detached-head", map[string]string{"config": sha256Config, "HEAD": sha256Commit + "\r\n"}, "admitted"),
		localLayoutCase("reject-gitfile", map[string]string{"dot-git-file": "gitdir: ../outside.git\n"}, "build_repository_local_gitfile_unsupported"),
		localLayoutCase("reject-bare-layout", map[string]string{"config": "[core]\nrepositoryformatversion = 0\nbare = true\n", "HEAD": fixedCommit + "\n"}, "build_repository_local_bare_unsupported"),
		localLayoutCase("reject-linked-worktree", map[string]string{"config": sha1Config, "HEAD": fixedCommit + "\n", "commondir": "../..\n"}, "build_repository_local_linked_worktree_unsupported"),
		localLayoutCase("reject-config-include", map[string]string{"config": sha1Config + "[include]\npath = ../outside\n", "HEAD": fixedCommit + "\n"}, "build_repository_local_format_unsupported"),
		localLayoutCase("reject-alternate-object-store", map[string]string{"config": sha1Config, "HEAD": fixedCommit + "\n", "objects/info/alternates": "/outside/objects\n"}, "build_repository_local_format_unsupported"),
		localLayoutCase("reject-replace-ref", map[string]string{"config": sha1Config, "HEAD": fixedCommit + "\n", "refs/replace/" + fixedCommit: strings.Repeat("b", 40) + "\n"}, "build_repository_local_format_unsupported"),
		localLayoutCase("reject-grafts", map[string]string{"config": sha1Config, "HEAD": fixedCommit + "\n", "info/grafts": fixedCommit + "\n"}, "build_repository_local_format_unsupported"),
		localLayoutCase("reject-promisor-sidecar", map[string]string{"config": sha1Config, "HEAD": fixedCommit + "\n", "objects/pack/pack-" + strings.Repeat("a", 40) + ".promisor": ""}, "build_repository_local_format_unsupported"),
		localLayoutCase("reject-partial-clone-config", map[string]string{"config": sha1Config + "[remote \"origin\"]\npromisor = true\npartialCloneFilter = blob:none\n", "HEAD": fixedCommit + "\n"}, "build_repository_local_format_unsupported"),
		localLayoutCase("source-filter-config-is-inert", map[string]string{"config": sha1Config + "[filter \"lfs\"]\nclean = git-lfs clean -- %f\nsmudge = git-lfs smudge -- %f\n", "HEAD": fixedCommit + "\n"}, "admitted-inert"),
		localLayoutCase("source-credential-helper-is-inert", map[string]string{"config": sha1Config + "[credential]\nhelper = !package-command\n", "HEAD": fixedCommit + "\n"}, "admitted-inert"),
		localLayoutCase("reject-reftable", map[string]string{"config": "[core]\nrepositoryformatversion = 1\nbare = false\n[extensions]\nrefStorage = reftable\n", "HEAD": fixedCommit + "\n"}, "build_repository_local_format_unsupported"),
		map[string]any{"name": "reject-link-or-special-administration-file", "entry_type": "symbolic-link-or-special", "expected_error": "build_repository_local_layout_unsafe", "path_opened": false},
	}
	writeJSON(filepath.Join(fixtures, "local-config-and-refs.json"), map[string]any{"cases": configCases})

	validSHA1Pack := packIndexCase("valid-empty-pack-v2-sha1", "sha1", 2, 2, "valid")
	indexChecksumMismatch := cloneMap(validSHA1Pack)
	indexChecksumMismatch["name"] = "reject-index-checksum-mismatch"
	indexChecksumMismatch["base_case"] = "valid-empty-pack-v2-sha1"
	indexChecksumMismatch["mutation"] = map[string]any{
		"target": "index", "operation": "xor-byte", "offset_from_end": 1, "xor": 1,
	}
	corruptIndex, err := hex.DecodeString(indexChecksumMismatch["index_hex"].(string))
	must(err)
	corruptIndex[len(corruptIndex)-1] ^= 1
	indexChecksumMismatch["index_hex"] = hex.EncodeToString(corruptIndex)
	delete(indexChecksumMismatch, "expected")
	indexChecksumMismatch["expected_error"] = "build_repository_local_object_format_unsupported"

	hashFamilyMismatch := cloneMap(validSHA1Pack)
	hashFamilyMismatch["name"] = "reject-pack-hash-family-mismatch"
	hashFamilyMismatch["base_case"] = "valid-empty-pack-v2-sha1"
	hashFamilyMismatch["fixture_object_format"] = "sha1"
	hashFamilyMismatch["object_format"] = "sha256"
	hashFamilyMismatch["mutation"] = map[string]any{
		"target": "repository_object_format", "operation": "replace", "from": "sha1", "to": "sha256",
	}
	delete(hashFamilyMismatch, "expected")
	hashFamilyMismatch["expected_error"] = "build_repository_local_object_format_unsupported"

	packCases := []any{
		validSHA1Pack,
		packIndexCase("valid-empty-pack-v3-sha1", "sha1", 3, 2, "valid"),
		packIndexCase("valid-empty-pack-v2-sha256", "sha256", 2, 2, "valid"),
		packIndexCase("reject-pack-v4", "sha1", 4, 2, "build_repository_local_object_format_unsupported"),
		packIndexCase("reject-index-v1", "sha1", 2, 1, "build_repository_local_object_format_unsupported"),
		map[string]any{"name": "reject-pack-without-index", "files": []any{"pack-" + strings.Repeat("a", 40) + ".pack"}, "expected_error": "build_repository_local_object_format_unsupported"},
		indexChecksumMismatch,
		hashFamilyMismatch,
	}
	writeJSON(filepath.Join(fixtures, "pack-index.json"), map[string]any{"cases": packCases})
}

func writeExternalRepositoryVectors(dir string) {
	cleanEnvironment := []any{
		"GIT_ATTR_NOSYSTEM=1", "GIT_CONFIG_GLOBAL=<empty>", "GIT_CONFIG_NOSYSTEM=1",
		"GIT_CONFIG_SYSTEM=<empty>", "GIT_EXEC_PATH=<fingerprinted>", "GIT_LITERAL_PATHSPECS=1",
		"GIT_NO_LAZY_FETCH=1", "GIT_NO_REPLACE_OBJECTS=1", "GIT_OPTIONAL_LOCKS=0",
		"GIT_PAGER=cat", "GIT_PROTOCOL_FROM_USER=0", "GIT_TERMINAL_PROMPT=0",
		"HOME=<operation-private>/home", "LANG=C", "LC_ALL=C",
		"PATH=<manager-owned-empty-or-exact-helper-directory>", "XDG_CONFIG_HOME=<operation-private>/config",
	}
	commonFetch := []any{
		"<absolute-trusted-git>", "--git-dir=<operation-private>/repo.git",
		"--no-replace-objects", "--no-lazy-fetch", "--no-optional-locks",
		"-c", "protocol.allow=never", "-c", "protocol.<selected>.allow=always",
		"-c", "protocol.version=0", "-c", "credential.helper=", "-c", "core.askPass=<manager-broker>",
		"-c", "core.hooksPath=<operation-private>/empty-hooks", "-c", "core.fsmonitor=false",
		"-c", "core.untrackedCache=false", "-c", "submodule.recurse=false",
		"-c", "fetch.recurseSubmodules=false", "-c", "maintenance.auto=false",
		"-c", "fetch.writeCommitGraph=false", "-c", "fetch.fsckObjects=true",
		"-c", "transfer.fsckObjects=true", "-c", "http.followRedirects=false",
		"-c", "http.sslVerify=true", "-c", "http.proxy=", "-c", "https.proxy=",
		"fetch", "--quiet", "--atomic", "--no-tags", "--no-recurse-submodules",
		"--no-auto-maintenance", "--no-write-fetch-head", "--no-write-commit-graph",
		"--refmap=", "--jobs=1", "--upload-pack=git-upload-pack", "--",
		"<validated-url>", "<one-manager-refspec>",
	}
	acquisitionCases := []any{
		acquisitionCase("sha1-untagged-https", "sha1", "https", fixedCommit+":refs/curator/locked", "source-resolved"),
		acquisitionCase("sha256-untagged-https", "sha256", "https", strings.Repeat("a", 64)+":refs/curator/locked", "source-resolved"),
		acquisitionCase("sha1-tagged-https", "sha1", "https", "refs/tags/v1.4.0:refs/curator/tag", "source-resolved"),
		acquisitionCase("sha256-tagged-ssh", "sha256", "ssh", "refs/tags/v2.0.0:refs/curator/tag", "source-resolved"),
		map[string]any{"name": "tag-moved", "object_format": "sha1", "transport": "https", "fetch_refspec": "refs/tags/v1.4.0:refs/curator/tag", "direct_oid_fetch_attempted": false, "expected_error": "build_repository_ref_moved", "audit_started": false, "artifact_cache_lookup": false, "compiler_started": false},
		map[string]any{"name": "tag-missing", "object_format": "sha1", "transport": "https", "fetch_refspec": "refs/tags/v1.4.0:refs/curator/tag", "direct_oid_fetch_attempted": false, "expected_error": "build_repository_source_unavailable", "audit_started": false, "artifact_cache_lookup": false, "compiler_started": false},
		map[string]any{"name": "tag-malformed-object", "object_format": "sha1", "transport": "https", "fetch_refspec": "refs/tags/v1.4.0:refs/curator/tag", "direct_oid_fetch_attempted": false, "expected_error": "build_repository_git_object_semantics_invalid", "audit_started": false, "artifact_cache_lookup": false, "compiler_started": false},
		map[string]any{"name": "untagged-missing-object", "object_format": "sha1", "transport": "https", "fetch_refspec": fixedCommit + ":refs/curator/locked", "expected_error": "build_repository_source_unavailable", "audit_started": false, "artifact_cache_lookup": false, "compiler_started": false},
		acquisitionCase("network-substitution-revision", "sha1", "https", fixedCommit+":refs/curator/effective", "source-resolved"),
		acquisitionCase("network-substitution-tag", "sha1", "ssh", "refs/tags/v1.4.0:refs/curator/effective", "source-resolved"),
		acquisitionCase("network-substitution-branch", "sha1", "https", "refs/heads/release/v2:refs/curator/effective", "source-resolved"),
		map[string]any{"name": "malformed-ref-rejected-before-git", "ref": "main^{commit}", "expected_error": "build_repository_identity_invalid", "git_started": false},
	}
	writeJSON(filepath.Join(dir, "external-repository-acquisition.json"), map[string]any{
		"protocol_version":  protocolVersion,
		"clean_environment": cleanEnvironment,
		"common_fetch_argv": commonFetch,
		"forbidden_fetch_features": []any{
			"configured-refspec", "depth", "filter", "helper-selected-transport", "mirror",
			"prune", "remote-name", "server-option", "source-upload-pack", "stdin-refspec", "tag-auto-follow",
		},
		"cases": acquisitionCases,
	})

	auditPhases := []any{
		"exact-source-acquisition", "raw-object-identity-and-graph-proof", "all-blob-lfs-scan",
		"immutable-snapshot-materialization", "whole-snapshot-validation", "build-source-digest",
		"descriptor-and-target-validation", "independent-external-audit",
	}
	cachePhases := append(append([]any{}, auditPhases...), "artifact-cache-lookup")
	buildPhases := append(append([]any{}, cachePhases...), "compiler", "receipt-publication", "marker-consumer-last-commit")
	wholeSnapshotOrder := append([]any{}, buildPhases...)
	writeJSON(filepath.Join(dir, "external-repository-lifecycle.json"), map[string]any{
		"whole_snapshot_order": wholeSnapshotOrder,
		"cache_cases": []any{
			lifecycleCase("verified-cache-hit", "cache-hit", nil, false, cachePhases),
			lifecycleCase("cache-miss", "would-preflight-and-build", nil, true, buildPhases),
			lifecycleCase("corrupt-receipt", "would-rebuild-untrusted-cache", "build_repository_receipt_invalid", true, buildPhases),
			lifecycleCase("corrupt-artifact", "would-rebuild-untrusted-cache", "build_repository_artifact_invalid", true, buildPhases),
			lifecycleCase("untrusted-protected-boundary", "would-rebuild-untrusted-cache", "build_repository_protected_boundary_untrusted", true, buildPhases),
			map[string]any{"name": "offline-syntax-only", "operation": "syntax", "state": "unverified-offline", "severity": "warning", "code": "build_repository_unverified_offline", "source_claimed": false, "audit_claimed": false, "cache_claimed": false, "mutation": false},
			map[string]any{"name": "offline-install", "operation": "install", "state": "blocked", "severity": "error", "code": "build_repository_source_unavailable", "cache_lookup": false, "compiler_started": false, "mutation": false},
		},
		"source_covering_cases": []any{
			map[string]any{
				"name": "external-source-dry-run", "operation": "dry-run", "result": "source-covered",
				"source_claimed": true, "audit_claimed": true, "ordered_phases": cachePhases,
				"artifact_cache_lookup": true, "compiler_started": false, "mutation": false,
			},
			map[string]any{
				"name": "external-audit-only", "operation": "audit", "result": "pass",
				"source_claimed": true, "audit_claimed": true, "ordered_phases": auditPhases,
				"artifact_cache_lookup": false, "compiler_started": false, "mutation": false,
			},
		},
		"mixed_build_cases": []any{
			map[string]any{"name": "schema6-local-only", "manifest_schema": 6, "drivers": []any{"go-v1"}, "receipt_versions": []any{1}, "marker_version": 2},
			map[string]any{"name": "schema7-local-only", "manifest_schema": 7, "drivers": []any{"go-v1"}, "receipt_versions": []any{1}, "marker_version": 3},
			map[string]any{"name": "schema7-external-only", "manifest_schema": 7, "drivers": []any{"go-repository-v1"}, "receipt_versions": []any{2}, "marker_version": 3},
			map[string]any{"name": "schema7-mixed", "manifest_schema": 7, "drivers": []any{"go-repository-v1", "go-v1"}, "receipt_versions": []any{2, 1}, "marker_version": 3, "expected_marker": "expected/external-repository/install-marker-v3-mixed.json"},
			map[string]any{"name": "schema7-substituted-external", "manifest_schema": 7, "drivers": []any{"go-repository-v1"}, "receipt_versions": []any{2}, "marker_version": 3, "declared_and_effective_sources": true},
		},
		"transaction_cases": []any{
			map[string]any{"name": "failure-before-publication", "failure_at": "build", "live_state_unchanged": true, "journal_retained_if_uncertain": true},
			map[string]any{"name": "failure-after-private-stage", "failure_at": "publication", "rollback": "restore-prior-complete-state", "consumer_marker_committed": false},
			map[string]any{"name": "marker-consumer-last", "failure_at": "marker-commit", "rollback": "restore-prior-complete-state", "partial_currentness_forbidden": true},
			map[string]any{"name": "recovery-uncertain-journal", "recovery": "fail-closed-or-rollback", "gc_retains_journal_roots": true},
		},
		"status_repair_gc_cases": []any{
			map[string]any{"name": "status-current", "remote_contacted": false, "state": "current", "severity": nil, "code": nil},
			map[string]any{"name": "status-missing-snapshot", "remote_contacted": false, "state": "non-current", "code": "build_repository_non_current"},
			map[string]any{"name": "status-unreadable-protected-state", "remote_contacted": false, "state": "unknown", "code": "build_repository_currentness_unknown"},
			map[string]any{
				"name":           "repair-reacquires-exact-source",
				"repeats":        []any{"acquisition", "object-proof", "audit", "transaction-publication"},
				"ordered_phases": buildPhases, "artifact_cache_lookup": true, "compiler_started": true,
			},
			map[string]any{"name": "gc-retains-roots", "roots": []any{"artifact-receipts", "in-flight-journals", "install-markers", "protected-snapshots", "uncertain-entries"}},
		},
		"path_shim_cases": []any{
			map[string]any{"name": "external-command-shim", "path_entry_derived_by_manager": true, "artifact_executed_during_install": false, "preserve_inherited_path": true, "forward_arguments": true, "preserve_exit_status": true},
			map[string]any{"name": "package-path-entry-rejected", "expected_error": "build_repository_package_output_forbidden", "shim_published": false},
			map[string]any{"name": "shim-collision-rolls-back", "expected_error": "build_repository_transaction_failed", "prior_shim_restored": true},
		},
		"signing_cases": []any{
			map[string]any{"name": "unsigned-local-build", "manager_post_signing": false, "artifact_executed_during_install": false, "result": "supported"},
			map[string]any{"name": "package-signing-request", "expected_error": "build_repository_package_signing_forbidden", "signer_started": false},
			map[string]any{"name": "platform-requires-local-signing", "expected_error": "build_repository_signer_policy_unsupported", "signer_started": false},
			map[string]any{"name": "release-pipeline-signing", "owner": "operator-release-pipeline", "manager_post_signing": false},
		},
	})

	writeJSON(filepath.Join(dir, "conformance-claim-v3-qualification.json"), map[string]any{
		"schema_version":       1,
		"protocol_version":     protocolVersion,
		"claim_schema_version": 3,
		"rules": []any{
			map[string]any{"name": "schema-valid-is-not-qualified", "required": "native-driver-platform-evidence"},
			map[string]any{"name": "driver-platform-subset", "required": "each driver platform is also top-level evidenced"},
			map[string]any{"name": "no-generic-driver", "allowed_drivers": []any{"go-repository-v1", "go-v1"}},
			map[string]any{"name": "no-unevidenced-platform", "required": "every emitted tuple has immutable passing evidence"},
		},
		"candidate_claims_emitted": []any{},
		"platforms": []any{
			map[string]any{"name": "linux", "status": "excluded", "until_task": "TASK-260728-1skseh"},
			map[string]any{"name": "macos", "status": "pending-downstream-native-evidence"},
			map[string]any{"name": "windows", "status": "pending-downstream-native-evidence"},
		},
	})
}

func writeExternalRepositoryExpected(expected string, markerV1 map[string]any) {
	receipt := validBuildReceiptV2(false, false)
	writeJSON(filepath.Join(expected, "external-repository", "build-receipt-v2.json"), receipt)
	mixed := validInstallMarkerV3(markerV1)
	writeJSON(filepath.Join(expected, "external-repository", "install-marker-v3-mixed.json"), mixed)
	externalRecord := mixed["builds"].(map[string]any)["golden-tool"].(map[string]any)
	writeJSON(filepath.Join(expected, "external-repository", "mixed-build-plan.json"), map[string]any{
		"schema_version": 7,
		"commands": []any{
			map[string]any{
				"name": "golden-tool", "driver": "go-repository-v1", "receipt_schema_version": 2,
				"cache_key": externalRecord["cache_key"], "receipt_sha256": externalRecord["receipt_sha256"],
			},
			map[string]any{"name": "local-helper", "driver": "go-v1", "receipt_schema_version": 1},
		},
		"marker_schema_version": 3,
		"publication_order":     []any{"golden-tool", "local-helper", "marker-consumer-last"},
	})
}

func writeRC5ReleaseMetadata(root, suite string) {
	manifest, err := os.ReadFile(filepath.Join(suite, "manifest.json"))
	must(err)
	digest := sha256.Sum256(manifest)
	pin := "sha256:" + hex.EncodeToString(digest[:])
	writeJSON(filepath.Join(root, "release", "1.0.0-rc.5.json"), map[string]any{
		"protocol_version": protocolVersion,
		"created_at":       rc5CreatedAt,
		"candidate_protocol_pin": map[string]any{
			"suite_root":      "conformance/v1",
			"manifest_sha256": pin,
		},
		"source_baseline_commit": "57c1f56846d221ecc55786bd3c2467ec32f11730",
		"legacy_release":         "1.0.0-rc.4",
		"downstream_consumption": map[string]any{
			"environment":                    "CURATOR_CONFORMANCE_ROOT",
			"required_manifest_sha256":       pin,
			"committed_release_pin_advanced": false,
		},
		"claim_v3": map[string]any{
			"claims_emitted":            []any{},
			"linux_excluded_until_task": "TASK-260728-1skseh",
			"macos_status":              "pending-downstream-native-evidence",
			"windows_status":            "pending-downstream-native-evidence",
		},
	})
}

type treeFixtureEntry struct {
	mode     string
	name     string
	objectID string
}

func rawObjectCase(name, objectType, objectFormat string, content []byte, outcome string) map[string]any {
	result := map[string]any{
		"name": name, "object_type": objectType, "object_format": objectFormat,
		"content_base64": base64.StdEncoding.EncodeToString(content),
		"object_id":      gitObjectID(objectFormat, objectType, content),
	}
	if outcome == "valid" {
		result["expected"] = "valid"
	} else {
		result["expected_error"] = outcome
	}
	return result
}

func treeObjectCase(name, objectFormat string, entries []treeFixtureEntry, outcome string) map[string]any {
	var content bytes.Buffer
	for _, entry := range entries {
		content.WriteString(entry.mode)
		content.WriteByte(' ')
		content.WriteString(entry.name)
		content.WriteByte(0)
		objectID, err := hex.DecodeString(entry.objectID)
		must(err)
		content.Write(objectID)
	}
	return rawObjectCase(name, "tree", objectFormat, content.Bytes(), outcome)
}

func gitObjectID(objectFormat, objectType string, content []byte) string {
	header := []byte(objectType + " " + strconv.Itoa(len(content)) + "\x00")
	payload := append(header, content...)
	if objectFormat == "sha1" {
		sum := sha1.Sum(payload)
		return hex.EncodeToString(sum[:])
	}
	sum := sha256.Sum256(payload)
	return hex.EncodeToString(sum[:])
}

func padTo(value []byte, length int, fill byte) []byte {
	if len(value) > length {
		panic("fixture prefix exceeds requested length")
	}
	result := append([]byte(nil), value...)
	return append(result, bytes.Repeat([]byte{fill}, length-len(result))...)
}

func localLayoutCase(name string, files map[string]string, outcome string) map[string]any {
	encoded := make(map[string]any, len(files))
	for path, content := range files {
		encoded[path] = base64.StdEncoding.EncodeToString([]byte(content))
	}
	result := map[string]any{"name": name, "files_base64": encoded}
	if strings.HasPrefix(outcome, "admitted") {
		result["expected"] = outcome
		result["source_process_started"] = false
	} else {
		result["expected_error"] = outcome
	}
	return result
}

func packIndexCase(name, objectFormat string, packVersion, indexVersion uint32, outcome string) map[string]any {
	pack := emptyPack(objectFormat, packVersion)
	hashWidth := 20
	if objectFormat == "sha256" {
		hashWidth = 32
	}
	packChecksum := pack[len(pack)-hashWidth:]
	index := emptyPackIndex(objectFormat, indexVersion, packChecksum)
	result := map[string]any{
		"name": name, "object_format": objectFormat,
		"pack_version": packVersion, "index_version": indexVersion,
		"pack_name": "pack-" + hex.EncodeToString(packChecksum) + ".pack",
		"pack_hex":  hex.EncodeToString(pack), "index_hex": hex.EncodeToString(index),
	}
	if outcome == "valid" {
		result["expected"] = "valid"
	} else {
		result["expected_error"] = outcome
	}
	return result
}

func emptyPack(objectFormat string, version uint32) []byte {
	header := make([]byte, 12)
	copy(header, []byte("PACK"))
	binary.BigEndian.PutUint32(header[4:8], version)
	binary.BigEndian.PutUint32(header[8:12], 0)
	return append(header, objectDigest(objectFormat, header)...)
}

func emptyPackIndex(objectFormat string, version uint32, packChecksum []byte) []byte {
	index := make([]byte, 8+256*4)
	copy(index, []byte{0xff, 0x74, 0x4f, 0x63})
	binary.BigEndian.PutUint32(index[4:8], version)
	index = append(index, packChecksum...)
	return append(index, objectDigest(objectFormat, index)...)
}

func objectDigest(objectFormat string, payload []byte) []byte {
	if objectFormat == "sha1" {
		sum := sha1.Sum(payload)
		return sum[:]
	}
	sum := sha256.Sum256(payload)
	return sum[:]
}

func acquisitionCase(name, objectFormat, transport, refspec, outcome string) map[string]any {
	return map[string]any{
		"name": name, "object_format": objectFormat, "transport": transport,
		"fetch_refspec": refspec, "direct_oid_fetch_attempted": false,
		"result": outcome, "audit_before_cache": true, "audit_before_compiler": true,
	}
}

func lifecycleCase(name, state string, code any, compilerStarted bool, orderedPhases []any) map[string]any {
	return map[string]any{
		"name": name, "state": state, "code": code,
		"source_proved": true, "audit_succeeded": true,
		"cache_lookup_after_audit": true, "compiler_started": compilerStarted,
		"ordered_phases": append([]any{}, orderedPhases...),
	}
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
		if version >= 6 {
			obj["build_roots"] = []any{"build"}
			obj["commands"] = map[string]any{
				"build-tool":  map[string]any{"type": "build", "driver": "go-v1", "source_dir": "build/cmd/tool"},
				"script-tool": map[string]any{"type": "script", "unix_path": "scripts/tool"},
				"system-tool": map[string]any{"type": "system", "command": "tool"},
			}
		}
		if version >= 7 {
			obj["build_repositories"] = map[string]any{
				"golden-tools": map[string]any{
					"git":           "https://github.com/example/golden-tools.git",
					"locked_commit": map[string]any{"object_format": "sha1", "hex": fixedCommit},
					"tag":           "v1.4.0",
				},
			}
			obj["commands"].(map[string]any)["golden-tool"] = map[string]any{
				"type": "build", "driver": "go-repository-v1", "repository": "golden-tools", "target": "golden-tool",
			}
		}
		return obj
	}
	cases := map[string]schemaCase{}
	additionalCases := map[string][]schemaExample{}
	for version := 1; version <= 7; version++ {
		invalid := map[string]any{"schema_version": version, "install": "echo unsafe"}
		if version == 1 {
			invalid = map[string]any{"schema_version": 1, "runtime_roots": []any{"scripts"}}
		} else if version >= 6 {
			invalid = map[string]any{"schema_version": version, "capabilities": map[string]any{}, "install": "echo unsafe"}
		}
		for _, prefix := range []string{"agent-skill", "csk-skill"} {
			name := fmt.Sprintf("%s-v%d.schema.json", prefix, version)
			cases[name] = schemaCase{validSkill(version), invalid}
			if version == 6 {
				additionalCases[name] = append(v6SchemaExamples(), legacyV7SchemaExamples(validSkill(version))...)
			} else if version == 7 {
				additionalCases[name] = v7SchemaExamples()
			} else {
				additionalCases[name] = legacyV7SchemaExamples(validSkill(version))
			}
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
	skillfileDevV2 := validSkillfileDevV2()
	cases["skillfile-dev-v2.schema.json"] = schemaCase{skillfileDevV2, withNestedField(validSkillfileDevV2(), []string{"build_repository_substitutions", "golden-skill", "golden-tools"}, "argv", []any{"go", "build"})}
	additionalCases["skillfile-dev-v2.schema.json"] = skillfileDevV2SchemaExamples()
	descriptor := validCuratorBuildV1()
	cases["curator-build-v1.schema.json"] = schemaCase{descriptor, without(descriptor, "targets")}
	additionalCases["curator-build-v1.schema.json"] = curatorBuildV1SchemaExamples()
	cases["install-marker-v1.schema.json"] = schemaCase{marker, without(marker, "locale")}
	receipt := validBuildReceiptV1()
	cases["build-receipt-v1.schema.json"] = schemaCase{receipt, without(receipt, "cache_key")}
	additionalCases["build-receipt-v1.schema.json"] = buildReceiptV1SchemaExamples()
	receiptV2 := validBuildReceiptV2(false, false)
	cases["build-receipt-v2.schema.json"] = schemaCase{receiptV2, without(receiptV2, "input")}
	additionalCases["build-receipt-v2.schema.json"] = buildReceiptV2SchemaExamples()
	markerV2 := validInstallMarkerV2(marker)
	cases["install-marker-v2.schema.json"] = schemaCase{markerV2, without(markerV2, "builds")}
	additionalCases["install-marker-v2.schema.json"] = installMarkerV2SchemaExamples(markerV2)
	markerV3 := validInstallMarkerV3(marker)
	cases["install-marker-v3.schema.json"] = schemaCase{markerV3, without(markerV3, "builds")}
	additionalCases["install-marker-v3.schema.json"] = installMarkerV3SchemaExamples(markerV3)
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
		map[string]any{"schema_version": 1, "protocol_version": conformanceClaimV1ProtocolVersion, "implementation": "example", "implementation_version": "1.0", "classes": []any{"core"}, "suite_sha256": "sha256:" + strings.Repeat("0", 64), "operating_systems": []any{"linux"}, "created_at": fixedTime, "result": "pass"},
		map[string]any{"schema_version": 1, "protocol_version": conformanceClaimV1ProtocolVersion, "result": "fail"},
	}
	claimV2 := validConformanceClaimV2()
	cases["conformance-claim-v2.schema.json"] = schemaCase{claimV2, without(claimV2, "implementation")}
	additionalCases["conformance-claim-v2.schema.json"] = conformanceClaimV2SchemaExamples()
	claimV3 := validConformanceClaimV3()
	cases["conformance-claim-v3.schema.json"] = schemaCase{claimV3, without(claimV3, "build_drivers")}
	additionalCases["conformance-claim-v3.schema.json"] = conformanceClaimV3SchemaExamples()

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
		for _, example := range additionalCases[name] {
			filename := example.name + ".json"
			writeJSON(filepath.Join(caseDir, filename), example.instance)
			index = append(index, map[string]any{
				"schema": name, "instance": filepath.ToSlash(filepath.Join(strings.TrimSuffix(name, ".schema.json"), filename)), "valid": example.valid,
			})
		}
	}
	writeJSON(filepath.Join(root, "index.json"), index)
}

func legacyV7SchemaExamples(valid map[string]any) []schemaExample {
	withTopLevel := func(field string, value any) map[string]any {
		manifest := deepCloneMap(valid)
		manifest[field] = value
		return manifest
	}
	withCommand := func(field string, value any) map[string]any {
		manifest := deepCloneMap(valid)
		commands, ok := manifest["commands"].(map[string]any)
		if !ok {
			commands = map[string]any{}
			manifest["commands"] = commands
		}
		command := map[string]any{"type": "system", "command": "legacy-tool"}
		command[field] = value
		commands["reserved-v7"] = command
		return manifest
	}
	return []schemaExample{
		{name: "invalid-v7-build-repositories", instance: withTopLevel("build_repositories", map[string]any{})},
		{name: "invalid-v7-top-level-repository", instance: withTopLevel("repository", "repo")},
		{name: "invalid-v7-top-level-target", instance: withTopLevel("target", "tool")},
		{name: "invalid-v7-top-level-driver", instance: withTopLevel("driver", "go-repository-v1")},
		{name: "invalid-v7-command-repository", instance: withCommand("repository", "repo")},
		{name: "invalid-v7-command-target", instance: withCommand("target", "tool")},
		{name: "invalid-v7-command-driver", instance: withCommand("driver", "go-repository-v1")},
	}
}

func validV7SkillManifest() map[string]any {
	return map[string]any{
		"schema_version": 7,
		"capabilities":   map[string]any{},
		"build_roots":    []any{"build"},
		"build_repositories": map[string]any{
			"golden-tools": map[string]any{
				"git":           "https://github.com/example/golden-tools.git",
				"locked_commit": map[string]any{"object_format": "sha1", "hex": fixedCommit},
				"tag":           "v1.4.0",
			},
		},
		"commands": map[string]any{
			"local-helper": map[string]any{"type": "build", "driver": "go-v1", "source_dir": "build/cmd/helper"},
			"golden-tool": map[string]any{
				"type": "build", "driver": "go-repository-v1", "repository": "golden-tools", "target": "golden-tool",
			},
		},
	}
}

func v7SchemaExamples() []schemaExample {
	withCommandField := func(field string, value any) map[string]any {
		manifest := validV7SkillManifest()
		manifest["commands"].(map[string]any)["golden-tool"].(map[string]any)[field] = value
		return manifest
	}
	withRepositoryField := func(field string, value any) map[string]any {
		manifest := validV7SkillManifest()
		manifest["build_repositories"].(map[string]any)["golden-tools"].(map[string]any)[field] = value
		return manifest
	}
	sha256Manifest := validV7SkillManifest()
	sha256Manifest["build_repositories"].(map[string]any)["golden-tools"].(map[string]any)["locked_commit"] =
		map[string]any{"object_format": "sha256", "hex": strings.Repeat("a", 64)}
	untaggedManifest := validV7SkillManifest()
	delete(untaggedManifest["build_repositories"].(map[string]any)["golden-tools"].(map[string]any), "tag")
	sshManifest := validV7SkillManifest()
	sshManifest["build_repositories"].(map[string]any)["golden-tools"].(map[string]any)["git"] = "ssh://git@github.com/example/golden-tools.git"
	scpManifest := validV7SkillManifest()
	scpManifest["build_repositories"].(map[string]any)["golden-tools"].(map[string]any)["git"] = "git@github.com:example/golden-tools.git"
	unicodeHTTPSManifest := validV7SkillManifest()
	unicodeHTTPSManifest["build_repositories"].(map[string]any)["golden-tools"].(map[string]any)["git"] = "https://example.com/组织/工具.git"
	tag255Manifest := validV7SkillManifest()
	tag255Manifest["build_repositories"].(map[string]any)["golden-tools"].(map[string]any)["tag"] = strings.Repeat("界", 85)

	examples := []schemaExample{
		{name: "valid-sha256-lock", valid: true, instance: sha256Manifest},
		{name: "valid-untagged-lock", valid: true, instance: untaggedManifest},
		{name: "valid-ssh-source", valid: true, instance: sshManifest},
		{name: "valid-scp-source", valid: true, instance: scpManifest},
		{name: "valid-unicode-https-source", valid: true, instance: unicodeHTTPSManifest},
		{name: "valid-tag-255-bytes", valid: true, instance: tag255Manifest},
		{name: "invalid-unselected-repository", instance: withNestedField(validV7SkillManifest(), []string{}, "build_repositories", map[string]any{
			"golden-tools": map[string]any{"git": "https://github.com/example/golden-tools.git", "locked_commit": map[string]any{"object_format": "sha1", "hex": fixedCommit}},
			"unused":       map[string]any{"git": "ssh://git@example.com/unused.git", "locked_commit": map[string]any{"object_format": "sha1", "hex": fixedCommit}},
		})},
		{name: "invalid-missing-repository", instance: withNestedField(validV7SkillManifest(), []string{"commands", "golden-tool"}, "repository", "missing")},
		{name: "invalid-sha1-width", instance: withRepositoryField("locked_commit", map[string]any{"object_format": "sha1", "hex": strings.Repeat("a", 64)})},
		{name: "invalid-sha256-width", instance: withRepositoryField("locked_commit", map[string]any{"object_format": "sha256", "hex": fixedCommit})},
		{name: "invalid-https-userinfo", instance: withRepositoryField("git", "https://user@example.com/repo.git")},
		{name: "invalid-explicit-port", instance: withRepositoryField("git", "https://example.com:8443/repo.git")},
		{name: "invalid-https-dot-component", instance: withRepositoryField("git", "https://example.com/org/../repo.git")},
		{name: "invalid-ssh-dot-component", instance: withRepositoryField("git", "ssh://git@example.com/./repo.git")},
		{name: "invalid-scp-dot-component", instance: withRepositoryField("git", "git@example.com:org/../repo.git")},
		{name: "invalid-ssh-metacharacter", instance: withRepositoryField("git", "git@example.com:repo;touch")},
		{name: "invalid-ssh-non-ascii", instance: withRepositoryField("git", "ssh://git@example.com/répo.git")},
		{name: "invalid-raw-revision-tag", instance: withRepositoryField("tag", "main^{commit}")},
		{name: "invalid-tag-256-bytes", instance: withRepositoryField("tag", strings.Repeat("a", 256))},
		{name: "invalid-tag-300-bytes", instance: withRepositoryField("tag", strings.Repeat("界", 100))},
		{name: "invalid-generic-driver", instance: withCommandField("driver", "go-v2")},
	}
	for _, field := range []string{"argv", "env", "output", "name", "credentials", "signing", "hooks", "plugins", "generator", "fallback"} {
		examples = append(examples, schemaExample{name: "invalid-command-" + field, instance: withCommandField(field, []any{})})
	}
	return examples
}

func validCuratorBuildV1() map[string]any {
	return map[string]any{
		"schema_version": 1,
		"targets": map[string]any{
			"golden-tool": map[string]any{"driver": "go-repository-v1", "build_root": ".", "source_dir": "cmd/golden-tool"},
			"admin-tool":  map[string]any{"driver": "go-repository-v1", "build_root": "tools/admin", "source_dir": "tools/admin/cmd/admin"},
		},
	}
}

func curatorBuildV1SchemaExamples() []schemaExample {
	target := func(buildRoot, sourceDir string) map[string]any {
		return map[string]any{"schema_version": 1, "targets": map[string]any{
			"tool": map[string]any{"driver": "go-repository-v1", "build_root": buildRoot, "source_dir": sourceDir},
		}}
	}
	withField := func(field string, value any) map[string]any {
		descriptor := validCuratorBuildV1()
		descriptor["targets"].(map[string]any)["golden-tool"].(map[string]any)[field] = value
		return descriptor
	}
	return []schemaExample{
		{name: "valid-root-target", valid: true, instance: target(".", ".")},
		{name: "valid-contained-target", valid: true, instance: target("tools/admin", "tools/admin/cmd/tool")},
		{name: "invalid-source-outside-build-root", instance: target("tools/admin", "cmd/tool")},
		{name: "invalid-parent-build-root", instance: target("../tools", "../tools/cmd/tool")},
		{name: "invalid-output", instance: withField("output", "bin/tool")},
		{name: "invalid-command-name", instance: withField("name", "tool")},
		{name: "invalid-argv", instance: withField("argv", []any{"go", "build"})},
		{name: "invalid-environment", instance: withField("environment", map[string]any{"GOFLAGS": "-mod=mod"})},
		{name: "invalid-signing", instance: withField("signing", "developer-id")},
		{name: "invalid-hook", instance: withField("hook", "post-build")},
		{name: "invalid-plugin", instance: withField("plugin", "custom")},
	}
}

func validSkillfileDevV2() map[string]any {
	return map[string]any{
		"schema_version": 2,
		"substitutions":  map[string]any{},
		"build_repository_substitutions": map[string]any{
			"golden-skill": map[string]any{
				"golden-tools": map[string]any{"path": "../golden-tools"},
			},
		},
	}
}

func skillfileDevV2SchemaExamples() []schemaExample {
	ordinaryOnly := map[string]any{
		"schema_version": 2,
		"substitutions": map[string]any{
			"golden-skill": map[string]any{"path": "../golden-skill"},
		},
	}
	emptyExternal := map[string]any{
		"schema_version":                 2,
		"substitutions":                  map[string]any{},
		"build_repository_substitutions": map[string]any{},
	}
	network := validSkillfileDevV2()
	network["build_repository_substitutions"].(map[string]any)["golden-skill"].(map[string]any)["golden-tools"] =
		map[string]any{"git": "ssh://git@example.com/golden-tools.git", "ref": map[string]any{"kind": "tag", "value": "v1.4.0"}}
	revision := validSkillfileDevV2()
	revision["build_repository_substitutions"].(map[string]any)["golden-skill"].(map[string]any)["golden-tools"] =
		map[string]any{"git": "https://example.com/golden-tools.git", "ref": map[string]any{"kind": "revision", "value": strings.Repeat("a", 64)}}
	branch := validSkillfileDevV2()
	branch["build_repository_substitutions"].(map[string]any)["golden-skill"].(map[string]any)["golden-tools"] =
		map[string]any{"git": "https://example.com/golden-tools.git", "ref": map[string]any{"kind": "branch", "value": "release/v2"}}
	branch256 := withNestedField(branch, []string{"build_repository_substitutions", "golden-skill", "golden-tools", "ref"}, "value", strings.Repeat("a", 256))
	rawRef := withNestedField(network, []string{"build_repository_substitutions", "golden-skill", "golden-tools", "ref"}, "kind", "revision")
	rawRef = withNestedField(rawRef, []string{"build_repository_substitutions", "golden-skill", "golden-tools", "ref"}, "value", "HEAD")
	return []schemaExample{
		{name: "valid-ordinary-only", valid: true, instance: ordinaryOnly},
		{name: "valid-empty-build-repository-substitutions", valid: true, instance: emptyExternal},
		{name: "valid-populated-build-repository-substitutions", valid: true, instance: validSkillfileDevV2()},
		{name: "valid-network-tag", valid: true, instance: network},
		{name: "valid-network-branch", valid: true, instance: branch},
		{name: "valid-network-sha256-revision", valid: true, instance: revision},
		{name: "invalid-path-and-git", instance: withNestedField(validSkillfileDevV2(), []string{"build_repository_substitutions", "golden-skill", "golden-tools"}, "git", "https://example.com/repo.git")},
		{name: "invalid-raw-ref", instance: rawRef},
		{name: "invalid-network-branch-256-bytes", instance: branch256},
		{name: "invalid-output", instance: withNestedField(validSkillfileDevV2(), []string{"build_repository_substitutions", "golden-skill", "golden-tools"}, "output", "bin/tool")},
		{name: "invalid-credentials", instance: withNestedField(validSkillfileDevV2(), []string{"build_repository_substitutions", "golden-skill", "golden-tools"}, "credentials", "secret")},
		{name: "invalid-target-ownership", instance: withNestedField(validSkillfileDevV2(), []string{"build_repository_substitutions", "golden-skill", "golden-tools"}, "target", "other")},
		{name: "invalid-driver-ownership", instance: withNestedField(validSkillfileDevV2(), []string{"build_repository_substitutions", "golden-skill", "golden-tools"}, "driver", "go-repository-v1")},
		{name: "invalid-command-ownership", instance: withNestedField(validSkillfileDevV2(), []string{"build_repository_substitutions", "golden-skill", "golden-tools"}, "command", "other")},
	}
}

func validDeclaredRepositorySource() map[string]any {
	return map[string]any{
		"identity":      map[string]any{"kind": "network-git", "value": "github.com/example/golden-tools"},
		"transport":     "https",
		"locked_commit": map[string]any{"object_format": "sha1", "hex": fixedCommit},
		"tag":           "v1.4.0",
	}
}

func validEffectiveRepositorySource(substituted, sha256Object bool) map[string]any {
	format, commit := "sha1", fixedCommit
	if sha256Object {
		format, commit = "sha256", strings.Repeat("a", 64)
	}
	effective := map[string]any{
		"identity":  map[string]any{"kind": "network-git", "value": "github.com/example/golden-tools"},
		"transport": "https", "object_format": format, "commit": commit, "substituted": substituted,
		"build_source": validBuildSourceIdentity(),
	}
	if substituted {
		effective["identity"] = map[string]any{"kind": "operator-local-git", "value": "sha256:" + strings.Repeat("e", 64)}
		delete(effective, "transport")
		effective["substitution"] = map[string]any{"type": "local-path"}
	}
	return effective
}

func validBuildReceiptV2(substituted, sha256Object bool) map[string]any {
	declared := validDeclaredRepositorySource()
	if sha256Object {
		declared["locked_commit"] = map[string]any{"object_format": "sha256", "hex": strings.Repeat("a", 64)}
	}
	input := map[string]any{
		"schema_version": 2, "driver": "go-repository-v1",
		"source": map[string]any{
			"repository": "golden-tools", "declared": declared,
			"effective":  validEffectiveRepositorySource(substituted, sha256Object),
			"descriptor": map[string]any{"path": "curator-build.json", "target": "golden-tool"},
		},
		"command": "golden-tool", "build_root": ".", "source_dir": "cmd/golden-tool",
		"target":    map[string]any{"goos": "darwin", "goarch": "arm64", "tuning": map[string]any{"GOARM64": "v8.0"}},
		"toolchain": map[string]any{"algorithm": "curator-go-toolchain-v1", "go_relpath": "bin/go", "go_version": "go version go1.26.1 darwin/arm64", "content_sha256": "sha256:" + strings.Repeat("c", 64)},
		"policy": map[string]any{
			"module_mode": "vendor", "network": "none", "workspace": false, "cgo": false,
			"compiler_directives": "reject-nonstandard-cgo-import-dynamic-v1", "target_mode": "native",
			"link_mode": "internal", "libgcc": "none", "package_assembly": false, "host_objects": false,
			"telemetry": "off-private", "source_kind": "locked-external-git-v1",
		},
	}
	return map[string]any{
		"schema_version": 2,
		"cache_key":      canonicalSHA256(input),
		"input":          input,
		"artifact":       map[string]any{"path": "bin/golden-tool", "sha256": "sha256:" + strings.Repeat("6", 64), "size": 1234567},
	}
}

func buildReceiptV2SchemaExamples() []schemaExample {
	withInputField := func(field string, value any) map[string]any {
		receipt := validBuildReceiptV2(false, false)
		receipt["input"].(map[string]any)[field] = value
		return receipt
	}
	networkSubstitution := validBuildReceiptV2(false, false)
	effective := networkSubstitution["input"].(map[string]any)["source"].(map[string]any)["effective"].(map[string]any)
	effective["identity"] = map[string]any{"kind": "network-git", "value": "git.example.com/forks/golden-tools"}
	effective["transport"] = "ssh"
	effective["substituted"] = true
	effective["substitution"] = map[string]any{
		"type": "network-git",
		"ref":  map[string]any{"kind": "branch", "value": "release"},
	}
	networkSubstitution["cache_key"] = canonicalSHA256(networkSubstitution["input"])
	sha256NetworkSubstitution := validBuildReceiptV2(false, true)
	sha256Effective := sha256NetworkSubstitution["input"].(map[string]any)["source"].(map[string]any)["effective"].(map[string]any)
	sha256Effective["identity"] = map[string]any{"kind": "network-git", "value": "git.example.com/forks/golden-tools"}
	sha256Effective["transport"] = "https"
	sha256Effective["substituted"] = true
	sha256Effective["substitution"] = map[string]any{
		"type": "network-git",
		"ref":  map[string]any{"kind": "revision", "value": strings.Repeat("a", 64)},
	}
	sha256NetworkSubstitution["cache_key"] = canonicalSHA256(sha256NetworkSubstitution["input"])
	sha1Revision64 := withNestedField(networkSubstitution, []string{"input", "source", "effective", "substitution", "ref"}, "kind", "revision")
	sha1Revision64 = withNestedField(sha1Revision64, []string{"input", "source", "effective", "substitution", "ref"}, "value", strings.Repeat("a", 64))
	sha256Revision40 := withNestedField(sha256NetworkSubstitution, []string{"input", "source", "effective", "substitution", "ref"}, "value", fixedCommit)
	unsubstitutedMismatch := withNestedField(validBuildReceiptV2(false, false), []string{"input", "source", "effective"}, "commit", strings.Repeat("1", 40))
	canonicalUppercaseGitSuffix := validBuildReceiptV2(false, false)
	for _, side := range []string{"declared", "effective"} {
		canonicalUppercaseGitSuffix["input"].(map[string]any)["source"].(map[string]any)[side].(map[string]any)["identity"] =
			map[string]any{"kind": "network-git", "value": "github.com/example/golden-tools.GIT"}
	}
	canonicalUppercaseGitSuffix["cache_key"] = canonicalSHA256(canonicalUppercaseGitSuffix["input"])
	identityWithLowercaseGitSuffix := validBuildReceiptV2(false, false)
	for _, side := range []string{"declared", "effective"} {
		identityWithLowercaseGitSuffix["input"].(map[string]any)["source"].(map[string]any)[side].(map[string]any)["identity"] =
			map[string]any{"kind": "network-git", "value": "github.com/example/golden-tools.git"}
	}
	identityWithUppercaseHost := validBuildReceiptV2(false, false)
	for _, side := range []string{"declared", "effective"} {
		identityWithUppercaseHost["input"].(map[string]any)["source"].(map[string]any)[side].(map[string]any)["identity"] =
			map[string]any{"kind": "network-git", "value": "GitHub.com/example/golden-tools"}
	}
	identityWithDotComponent := validBuildReceiptV2(false, false)
	for _, side := range []string{"declared", "effective"} {
		identityWithDotComponent["input"].(map[string]any)["source"].(map[string]any)[side].(map[string]any)["identity"] =
			map[string]any{"kind": "network-git", "value": "github.com/example/../golden-tools"}
	}
	sourceOutsideBuildRoot := validBuildReceiptV2(false, false)
	sourceOutsideBuildRoot["input"].(map[string]any)["build_root"] = "tools/admin"
	sourceOutsideBuildRoot["input"].(map[string]any)["source_dir"] = "other/cmd/tool"
	untagged := validBuildReceiptV2(false, false)
	delete(untagged["input"].(map[string]any)["source"].(map[string]any)["declared"].(map[string]any), "tag")
	untagged["cache_key"] = canonicalSHA256(untagged["input"])
	return []schemaExample{
		{name: "valid-local-substitution", valid: true, instance: validBuildReceiptV2(true, false)},
		{name: "valid-network-substitution", valid: true, instance: networkSubstitution},
		{name: "valid-network-sha256-revision", valid: true, instance: sha256NetworkSubstitution},
		{name: "valid-sha256", valid: true, instance: validBuildReceiptV2(false, true)},
		{name: "valid-untagged", valid: true, instance: untagged},
		{name: "valid-canonical-uppercase-git-suffix", valid: true, instance: canonicalUppercaseGitSuffix},
		{name: "invalid-unsubstituted-substitution", instance: withNestedField(validBuildReceiptV2(false, false), []string{"input", "source", "effective"}, "substitution", map[string]any{"type": "local-path"})},
		{name: "invalid-substituted-without-state", instance: withNestedField(validBuildReceiptV2(true, false), []string{"input", "source", "effective"}, "substitution", nil)},
		{name: "invalid-local-substitution-network-identity", instance: withNestedField(validBuildReceiptV2(true, false), []string{"input", "source", "effective"}, "identity", map[string]any{"kind": "network-git", "value": "example.com/repo"})},
		{name: "invalid-network-substitution-local-identity", instance: withNestedField(networkSubstitution, []string{"input", "source", "effective"}, "identity", map[string]any{"kind": "operator-local-git", "value": "sha256:" + strings.Repeat("e", 64)})},
		{name: "invalid-effective-commit-width", instance: withNestedField(validBuildReceiptV2(false, false), []string{"input", "source", "effective"}, "commit", strings.Repeat("a", 64))},
		{name: "invalid-unsubstituted-declared-effective-mismatch", instance: unsubstitutedMismatch},
		{name: "invalid-source-outside-build-root", instance: sourceOutsideBuildRoot},
		{name: "invalid-sha1-effective-revision-width", instance: sha1Revision64},
		{name: "invalid-sha256-effective-revision-width", instance: sha256Revision40},
		{name: "invalid-canonical-lowercase-git-suffix", instance: identityWithLowercaseGitSuffix},
		{name: "invalid-canonical-uppercase-host", instance: identityWithUppercaseHost},
		{name: "invalid-canonical-dot-component", instance: identityWithDotComponent},
		{name: "invalid-driver", instance: withInputField("driver", "go-v1")},
		{name: "invalid-output", instance: withInputField("output", "bin/other")},
		{name: "invalid-argv", instance: withInputField("argv", []any{"go", "build"})},
		{name: "invalid-trust-boolean", instance: withNestedField(validBuildReceiptV2(false, false), []string{}, "trusted", true)},
	}
}

func validBuildRecordV1ForMarkerV3() map[string]any {
	record := validBuildRecordV1("bin/local-helper", "1")
	record["receipt_schema_version"] = 1
	return record
}

func validBuildRecordV2ForMarkerV3(substituted bool) map[string]any {
	receipt := validBuildReceiptV2(substituted, false)
	record := map[string]any{
		"driver": "go-repository-v1", "receipt_schema_version": 2, "repository": "golden-tools",
		"declared_identity":      map[string]any{"kind": "network-git", "value": "github.com/example/golden-tools"},
		"declared_locked_commit": map[string]any{"object_format": "sha1", "hex": fixedCommit},
		"declared_tag":           "v1.4.0",
		"effective_identity":     map[string]any{"kind": "network-git", "value": "github.com/example/golden-tools"},
		"object_format":          "sha1", "commit": fixedCommit, "substituted": substituted,
		"build_source": validBuildSourceIdentity(), "descriptor_target": "golden-tool",
		"cache_key": receipt["cache_key"], "receipt_sha256": canonicalSHA256(receipt),
		"artifact_sha256": "sha256:" + strings.Repeat("6", 64), "artifact_path": "bin/golden-tool",
	}
	if substituted {
		record["effective_identity"] = map[string]any{"kind": "operator-local-git", "value": "sha256:" + strings.Repeat("e", 64)}
		record["substitution"] = map[string]any{"type": "local-path"}
	}
	return record
}

func markerV3WithExternalRecord(marker map[string]any, record map[string]any) map[string]any {
	result := cloneMap(marker)
	result["commands"] = []any{"golden-tool"}
	result["build_roots"] = []any{}
	result["builds"] = map[string]any{"golden-tool": record}
	delete(result, "build_source")
	return result
}

func validNetworkBuildRecordV2ForMarkerV3(objectFormat, refKind, refValue string) map[string]any {
	record := validBuildRecordV2ForMarkerV3(false)
	record["effective_identity"] = map[string]any{"kind": "network-git", "value": "git.example.com/forks/golden-tools"}
	record["substituted"] = true
	record["substitution"] = map[string]any{
		"type": "network-git",
		"ref":  map[string]any{"kind": refKind, "value": refValue},
	}
	if objectFormat == "sha256" {
		record["declared_locked_commit"] = map[string]any{"object_format": "sha256", "hex": strings.Repeat("a", 64)}
		record["object_format"] = "sha256"
		record["commit"] = strings.Repeat("a", 64)
	}
	return record
}

func validInstallMarkerV3(markerV1 map[string]any) map[string]any {
	marker := cloneMap(markerV1)
	marker["schema_version"] = 3
	marker["skill_schema_version"] = 7
	marker["runtime_roots"] = []any{}
	marker["build_roots"] = []any{"build"}
	marker["build_source"] = validBuildSourceIdentity()
	marker["commands"] = []any{"golden-tool", "local-helper"}
	marker["builds"] = map[string]any{
		"local-helper": validBuildRecordV1ForMarkerV3(),
		"golden-tool":  validBuildRecordV2ForMarkerV3(false),
	}
	return marker
}

func installMarkerV3SchemaExamples(validMarker map[string]any) []schemaExample {
	externalOnly := markerV3WithExternalRecord(validMarker, validBuildRecordV2ForMarkerV3(true))
	externalOnlyUnsubstituted := markerV3WithExternalRecord(validMarker, validBuildRecordV2ForMarkerV3(false))
	localOnly := cloneMap(validMarker)
	localOnly["commands"] = []any{"local-helper"}
	localOnly["builds"] = map[string]any{"local-helper": validBuildRecordV1ForMarkerV3()}
	emptyBuilds := cloneMap(validMarker)
	emptyBuilds["commands"] = []any{}
	emptyBuilds["build_roots"] = []any{}
	emptyBuilds["builds"] = map[string]any{}
	delete(emptyBuilds, "build_source")
	networkTag := markerV3WithExternalRecord(
		validMarker,
		validNetworkBuildRecordV2ForMarkerV3("sha1", "tag", "v1.4.0"),
	)
	networkBranch := markerV3WithExternalRecord(
		validMarker,
		validNetworkBuildRecordV2ForMarkerV3("sha1", "branch", "release/v2"),
	)
	networkSHA1Revision := markerV3WithExternalRecord(
		validMarker,
		validNetworkBuildRecordV2ForMarkerV3("sha1", "revision", fixedCommit),
	)
	networkSHA256Revision := markerV3WithExternalRecord(
		validMarker,
		validNetworkBuildRecordV2ForMarkerV3("sha256", "revision", strings.Repeat("a", 64)),
	)
	sha256External := validBuildRecordV2ForMarkerV3(false)
	sha256External["declared_locked_commit"] = map[string]any{"object_format": "sha256", "hex": strings.Repeat("a", 64)}
	sha256External["object_format"] = "sha256"
	sha256External["commit"] = strings.Repeat("a", 64)
	sha256Marker := markerV3WithExternalRecord(validMarker, sha256External)
	untaggedExternal := validBuildRecordV2ForMarkerV3(false)
	delete(untaggedExternal, "declared_tag")
	untaggedMarker := markerV3WithExternalRecord(validMarker, untaggedExternal)
	localIdentityMismatch := markerV3WithExternalRecord(validMarker, validBuildRecordV2ForMarkerV3(true))
	localIdentityMismatch["builds"].(map[string]any)["golden-tool"].(map[string]any)["effective_identity"] =
		map[string]any{"kind": "network-git", "value": "git.example.com/forks/golden-tools"}
	networkIdentityMismatch := markerV3WithExternalRecord(
		validMarker,
		validNetworkBuildRecordV2ForMarkerV3("sha1", "branch", "release/v2"),
	)
	networkIdentityMismatch["builds"].(map[string]any)["golden-tool"].(map[string]any)["effective_identity"] =
		map[string]any{"kind": "operator-local-git", "value": "sha256:" + strings.Repeat("e", 64)}
	sha1Revision64 := markerV3WithExternalRecord(
		validMarker,
		validNetworkBuildRecordV2ForMarkerV3("sha1", "revision", strings.Repeat("a", 64)),
	)
	sha256Revision40 := markerV3WithExternalRecord(
		validMarker,
		validNetworkBuildRecordV2ForMarkerV3("sha256", "revision", fixedCommit),
	)
	missingLocalSource := cloneMap(validMarker)
	delete(missingLocalSource, "build_source")
	externalWithTopSource := cloneMap(externalOnly)
	externalWithTopSource["build_source"] = validBuildSourceIdentity()
	return []schemaExample{
		{name: "valid-empty-builds", valid: true, instance: emptyBuilds},
		{name: "valid-external-only-substituted", valid: true, instance: externalOnly},
		{name: "valid-external-only-unsubstituted", valid: true, instance: externalOnlyUnsubstituted},
		{name: "valid-local-only", valid: true, instance: localOnly},
		{name: "valid-network-substitution-tag", valid: true, instance: networkTag},
		{name: "valid-network-substitution-branch", valid: true, instance: networkBranch},
		{name: "valid-network-sha1-revision", valid: true, instance: networkSHA1Revision},
		{name: "valid-network-sha256-revision", valid: true, instance: networkSHA256Revision},
		{name: "valid-sha256-external", valid: true, instance: sha256Marker},
		{name: "valid-untagged-external", valid: true, instance: untaggedMarker},
		{name: "invalid-missing-local-build-source", instance: missingLocalSource},
		{name: "invalid-external-only-build-source", instance: externalWithTopSource},
		{name: "invalid-local-receipt-version", instance: withNestedField(validMarker, []string{"builds", "local-helper"}, "receipt_schema_version", 2)},
		{name: "invalid-external-receipt-version", instance: withNestedField(validMarker, []string{"builds", "golden-tool"}, "receipt_schema_version", 1)},
		{name: "invalid-external-object-width", instance: withNestedField(validMarker, []string{"builds", "golden-tool"}, "commit", strings.Repeat("a", 64))},
		{name: "invalid-external-declared-effective-mismatch", instance: withNestedField(validMarker, []string{"builds", "golden-tool"}, "commit", strings.Repeat("1", 40))},
		{name: "invalid-marker-local-identity-kind-mismatch", instance: localIdentityMismatch},
		{name: "invalid-marker-network-identity-kind-mismatch", instance: networkIdentityMismatch},
		{name: "invalid-marker-sha1-effective-revision-width", instance: sha1Revision64},
		{name: "invalid-marker-sha256-effective-revision-width", instance: sha256Revision40},
		{name: "invalid-package-signing", instance: withNestedField(validMarker, []string{"builds", "golden-tool"}, "signing", "developer-id")},
	}
}

func validConformanceClaimV3() map[string]any {
	return map[string]any{
		"schema_version": 3, "protocol_version": "1.0.0-rc.5",
		"implementation": "example-manager", "implementation_version": "1.0",
		"classes": []any{"core", "manager"}, "suite_sha256": "sha256:" + strings.Repeat("0", 64),
		"operating_systems": []any{"macos", "windows"},
		"build_drivers": []any{
			map[string]any{"driver": "go-v1", "language": "go", "operating_systems": []any{"macos", "windows"}},
			map[string]any{"driver": "go-repository-v1", "language": "go", "operating_systems": []any{"macos", "windows"}},
		},
		"created_at": fixedTime, "result": "pass",
	}
}

func conformanceClaimV3SchemaExamples() []schemaExample {
	withField := func(field string, value any) map[string]any {
		claim := validConformanceClaimV3()
		claim[field] = value
		return claim
	}
	macosOnly := validConformanceClaimV3()
	macosOnly["operating_systems"] = []any{"macos"}
	for _, raw := range macosOnly["build_drivers"].([]any) {
		raw.(map[string]any)["operating_systems"] = []any{"macos"}
	}
	linuxUnqualified := validConformanceClaimV3()
	linuxUnqualified["operating_systems"] = []any{"linux"}
	for _, raw := range linuxUnqualified["build_drivers"].([]any) {
		raw.(map[string]any)["operating_systems"] = []any{"linux"}
	}
	return []schemaExample{
		{name: "valid-macos-only", valid: true, instance: macosOnly},
		{name: "invalid-linux-unqualified", instance: linuxUnqualified},
		{name: "invalid-rc4", instance: withField("protocol_version", conformanceClaimV2ProtocolVersion)},
		{name: "invalid-duplicate-platform", instance: withField("operating_systems", []any{"macos", "macos"})},
		{name: "invalid-duplicate-driver-assertion", instance: withField("build_drivers", []any{
			map[string]any{"driver": "go-v1", "language": "go", "operating_systems": []any{"macos"}},
			map[string]any{"driver": "go-v1", "language": "go", "operating_systems": []any{"windows"}},
		})},
		{name: "invalid-driver-platform-outside-claim", instance: withField("build_drivers", []any{
			map[string]any{"driver": "go-repository-v1", "language": "go", "operating_systems": []any{"linux"}},
		})},
		{name: "invalid-generic-driver", instance: withField("build_drivers", []any{map[string]any{"driver": "custom-v1", "language": "go", "operating_systems": []any{"macos"}}})},
		{name: "invalid-language-mismatch", instance: withField("build_drivers", []any{map[string]any{"driver": "go-repository-v1", "language": "rust", "operating_systems": []any{"macos"}}})},
		{name: "invalid-unknown-field", instance: withField("platform_verified", true)},
	}
}

func withNestedField(object map[string]any, path []string, field string, value any) map[string]any {
	cloned := deepCloneMap(object)
	current := cloned
	for _, component := range path {
		current = current[component].(map[string]any)
	}
	if value == nil {
		delete(current, field)
	} else {
		current[field] = value
	}
	return cloned
}

func deepCloneMap(value map[string]any) map[string]any {
	payload, err := json.Marshal(value)
	must(err)
	var cloned map[string]any
	must(json.Unmarshal(payload, &cloned))
	return cloned
}

func validConformanceClaimV2() map[string]any {
	return map[string]any{
		"schema_version":         2,
		"protocol_version":       conformanceClaimV2ProtocolVersion,
		"implementation":         "example-manager",
		"implementation_version": "1.0",
		"classes":                []any{"core", "manager"},
		"suite_sha256":           "sha256:" + strings.Repeat("0", 64),
		"operating_systems":      []any{"linux"},
		"created_at":             conformanceClaimV2CreatedAt,
		"result":                 "pass",
	}
}

func conformanceClaimV2SchemaExamples() []schemaExample {
	withField := func(field string, value any) map[string]any {
		claim := validConformanceClaimV2()
		claim[field] = value
		return claim
	}
	return []schemaExample{
		{"invalid-protocol-version-rc3", false, withField("protocol_version", conformanceClaimV1ProtocolVersion)},
		{"invalid-schema-version-1", false, withField("schema_version", 1)},
		{"invalid-duplicate-classes", false, withField("classes", []any{"manager", "manager"})},
		{"invalid-result-fail", false, withField("result", "fail")},
		{"invalid-unknown-field", false, withField("build_driver", "go-v1")},
	}
}

func validBuildSourceIdentity() map[string]any {
	return map[string]any{
		"algorithm":      "curator-build-source-v1",
		"content_sha256": "sha256:" + strings.Repeat("b", 64),
	}
}

func validGoBuildInputV1() map[string]any {
	return map[string]any{
		"schema_version": 1,
		"driver":         "go-v1",
		"build_source":   validBuildSourceIdentity(),
		"build_root":     "build",
		"command":        "golden-tool",
		"source_dir":     "build/cmd/golden-tool",
		"target": map[string]any{
			"goos": "darwin", "goarch": "arm64",
			"tuning": map[string]any{"GOARM64": "v8.0"},
		},
		"toolchain": map[string]any{
			"algorithm": "curator-go-toolchain-v1", "go_relpath": "bin/go",
			"go_version": "go version go1.26.1 darwin/arm64", "content_sha256": "sha256:" + strings.Repeat("c", 64),
		},
		"policy": map[string]any{
			"module_mode": "vendor", "network": "none", "workspace": false, "cgo": false,
			"compiler_directives": "reject-nonstandard-cgo-import-dynamic-v1",
			"target_mode":         "native", "link_mode": "internal", "libgcc": "none",
			"package_assembly": false, "host_objects": false, "telemetry": "off-private",
		},
	}
}

func validBuildReceiptV1() map[string]any {
	return map[string]any{
		"schema_version": 1,
		"cache_key":      "sha256:3fcd714a40e8918eb67dbd35d435875dcce6c9047da811a1fa26626e5e57be48",
		"input":          validGoBuildInputV1(),
		"artifact": map[string]any{
			"path": "bin/golden-tool", "sha256": "sha256:" + strings.Repeat("d", 64), "size": 1234567,
		},
	}
}

func buildReceiptV1SchemaExamples() []schemaExample {
	withTopLevelField := func(field string, value any) map[string]any {
		receipt := validBuildReceiptV1()
		receipt[field] = value
		return receipt
	}
	withInputField := func(field string, value any) map[string]any {
		receipt := validBuildReceiptV1()
		receipt["input"].(map[string]any)[field] = value
		return receipt
	}

	missingInput := without(validBuildReceiptV1(), "input")
	missingArtifact := without(validBuildReceiptV1(), "artifact")
	driverMismatch := validBuildReceiptV1()
	driverMismatch["input"].(map[string]any)["driver"] = "go-v2"
	buildSourceMismatch := validBuildReceiptV1()
	buildSourceMismatch["input"].(map[string]any)["build_source"].(map[string]any)["algorithm"] = "curator-build-source-v2"
	toolchainMismatch := validBuildReceiptV1()
	toolchainMismatch["input"].(map[string]any)["toolchain"].(map[string]any)["algorithm"] = "curator-go-toolchain-v2"
	policyMismatch := validBuildReceiptV1()
	policyMismatch["input"].(map[string]any)["policy"].(map[string]any)["network"] = "proxy"
	artifactMismatch := validBuildReceiptV1()
	artifactMismatch["artifact"].(map[string]any)["sha256"] = "sha256:UPPERCASE"

	examples := []schemaExample{
		{name: "invalid-missing-input", instance: missingInput},
		{name: "invalid-missing-artifact", instance: missingArtifact},
		{name: "invalid-driver-mismatch", instance: driverMismatch},
		{name: "invalid-build-source-algorithm", instance: buildSourceMismatch},
		{name: "invalid-toolchain-algorithm", instance: toolchainMismatch},
		{name: "invalid-policy-mismatch", instance: policyMismatch},
		{name: "invalid-artifact-hash", instance: artifactMismatch},
		{name: "invalid-unknown-input-field", instance: withInputField("output", "bin/other")},
	}
	for _, field := range []string{"trusted", "provenance", "manager_created"} {
		examples = append(examples, schemaExample{name: "invalid-self-asserted-" + strings.ReplaceAll(field, "_", "-"), instance: withTopLevelField(field, true)})
	}
	for _, field := range []string{"cache_path", "receipt_path", "lock_path"} {
		examples = append(examples, schemaExample{name: "invalid-physical-" + strings.ReplaceAll(field, "_", "-"), instance: withTopLevelField(field, "/tmp/cache")})
	}
	return examples
}

func validBuildRecordV1(artifactPath string, digit string) map[string]any {
	return map[string]any{
		"driver": "go-v1", "cache_key": "sha256:" + strings.Repeat(digit, 64),
		"receipt_sha256":  "sha256:" + strings.Repeat("e", 64),
		"artifact_sha256": "sha256:" + strings.Repeat("d", 64), "artifact_path": artifactPath,
	}
}

func validInstallMarkerV2(markerV1 map[string]any) map[string]any {
	marker := cloneMap(markerV1)
	marker["schema_version"] = 2
	marker["skill_schema_version"] = 6
	marker["runtime_roots"] = []any{}
	marker["build_roots"] = []any{"build"}
	marker["build_source"] = validBuildSourceIdentity()
	marker["builds"] = map[string]any{
		"golden-tool": validBuildRecordV1("bin/golden-tool", "3"),
	}
	return marker
}

func installMarkerV2SchemaExamples(validMarker map[string]any) []schemaExample {
	emptyBuilds := cloneMap(validMarker)
	emptyBuilds["build_roots"] = []any{}
	emptyBuilds["builds"] = map[string]any{}
	delete(emptyBuilds, "build_source")

	multipleBuilds := cloneMap(validMarker)
	multipleBuilds["commands"] = []any{"alpha-tool", "golden-tool"}
	multipleBuilds["build_roots"] = []any{"build", "tools"}
	multipleBuilds["builds"] = map[string]any{
		"golden-tool": validBuildRecordV1("bin/golden-tool", "3"),
		"alpha-tool":  validBuildRecordV1("bin/alpha-tool", "4"),
	}

	missingBuildRoots := without(validMarker, "build_roots")
	missingBuildSource := without(validMarker, "build_source")
	buildSourceWithEmptyBuilds := cloneMap(emptyBuilds)
	buildSourceWithEmptyBuilds["build_source"] = validBuildSourceIdentity()
	unknownTopLevel := cloneMap(validMarker)
	unknownTopLevel["cache_path"] = "/tmp/cache"
	unknownBuildField := cloneMap(validMarker)
	unknownBuildField["builds"].(map[string]any)["golden-tool"].(map[string]any)["receipt_path"] = "/tmp/receipt"
	driverMismatch := cloneMap(validMarker)
	driverMismatch["builds"].(map[string]any)["golden-tool"].(map[string]any)["driver"] = "go-v2"
	buildSourceMismatch := cloneMap(validMarker)
	buildSourceMismatch["build_source"].(map[string]any)["algorithm"] = "curator-build-source-v2"
	skillSchemaMismatch := cloneMap(validMarker)
	skillSchemaMismatch["skill_schema_version"] = 7
	receiptHashMismatch := cloneMap(validMarker)
	receiptHashMismatch["builds"].(map[string]any)["golden-tool"].(map[string]any)["receipt_sha256"] = "bad"
	artifactPathMismatch := cloneMap(validMarker)
	artifactPathMismatch["builds"].(map[string]any)["golden-tool"].(map[string]any)["artifact_path"] = "/absolute/cache/artifact"

	return []schemaExample{
		{name: "valid-empty-builds", valid: true, instance: emptyBuilds},
		{name: "valid-multiple-builds", valid: true, instance: multipleBuilds},
		{name: "invalid-missing-build-roots", instance: missingBuildRoots},
		{name: "invalid-missing-build-source", instance: missingBuildSource},
		{name: "invalid-build-source-with-empty-builds", instance: buildSourceWithEmptyBuilds},
		{name: "invalid-unknown-top-level", instance: unknownTopLevel},
		{name: "invalid-unknown-build-field", instance: unknownBuildField},
		{name: "invalid-driver-mismatch", instance: driverMismatch},
		{name: "invalid-build-source-algorithm", instance: buildSourceMismatch},
		{name: "invalid-skill-schema-version", instance: skillSchemaMismatch},
		{name: "invalid-receipt-hash", instance: receiptHashMismatch},
		{name: "invalid-artifact-path", instance: artifactPathMismatch},
	}
}

func v6SkillManifest(command map[string]any) map[string]any {
	return map[string]any{
		"schema_version": 6,
		"capabilities":   map[string]any{},
		"build_roots":    []any{"build"},
		"commands":       map[string]any{"build-tool": command},
	}
}

func v6SchemaExamples() []schemaExample {
	buildCommand := func() map[string]any {
		return map[string]any{"type": "build", "driver": "go-v1", "source_dir": "build/cmd/tool"}
	}
	withField := func(field string, value any) map[string]any {
		command := buildCommand()
		command[field] = value
		return v6SkillManifest(command)
	}

	examples := []schemaExample{
		{name: "invalid-build-missing-driver", instance: v6SkillManifest(map[string]any{"type": "build", "source_dir": "build/cmd/tool"})},
		{name: "invalid-build-missing-source-dir", instance: v6SkillManifest(map[string]any{"type": "build", "driver": "go-v1"})},
		{name: "invalid-build-root-dot", instance: map[string]any{"schema_version": 6, "capabilities": map[string]any{}, "build_roots": []any{"."}}},
		{name: "invalid-build-source-dir-dot", instance: v6SkillManifest(map[string]any{"type": "build", "driver": "go-v1", "source_dir": "."})},
		{name: "invalid-build-unsupported-driver", instance: v6SkillManifest(map[string]any{"type": "build", "driver": "custom-v1", "source_dir": "build/cmd/tool"})},
		{name: "invalid-build-mixed-script", instance: withField("unix_path", "scripts/tool")},
		{name: "invalid-build-mixed-system", instance: withField("command", "tool")},
	}
	for _, field := range []string{"args", "env", "flags", "hooks", "output", "scripts", "tags", "toolchain"} {
		examples = append(examples, schemaExample{
			name:     "invalid-build-" + field,
			instance: withField(field, []any{}),
		})
	}
	return examples
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

func canonicalSHA256(value any) string {
	digest := sha256.Sum256(canonicalBytes(value))
	return "sha256:" + hex.EncodeToString(digest[:])
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
