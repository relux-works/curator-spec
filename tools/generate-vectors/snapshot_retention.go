package main

import (
	"path/filepath"
	"sort"
	"strings"
	"time"
)

// Retention inputs are declared here; expected decisions are derived by the
// reference rule, rather than copied from a hand-maintained JSON artifact.
func writeSnapshotRetentionVectors(dir string) {
	entry := func(source, digit, used string, reachable bool) map[string]any {
		n := 40
		if digit == "f" {
			n = 64
		}
		return map[string]any{"source": source, "commit": strings.Repeat(digit, n), "last_used_at": used, "reachable": reachable}
	}
	cases := []any{
		map[string]any{
			"name":                  "empty-store",
			"now":                   "2026-09-30T12:00:00Z",
			"grace_seconds":         86400,
			"reference_set_certain": true,
			"policy":                map[string]any{"keep_last": nil, "older_than_seconds": nil},
			"entries":               []any{},
		},
		map[string]any{
			"name":                  "no-policy-removes-unreachable-outside-grace",
			"now":                   "2026-09-30T12:00:00Z",
			"grace_seconds":         86400,
			"reference_set_certain": true,
			"policy":                map[string]any{"keep_last": nil, "older_than_seconds": nil},
			"entries": []any{
				entry("github.com/example/skills", "a", "2026-09-27T12:00:00Z", true),
				entry("github.com/example/skills", "b", "2026-09-27T12:00:00Z", false),
			},
		},
		map[string]any{
			"name":                  "grace-retains-young-unreachable",
			"now":                   "2026-09-30T12:00:00Z",
			"grace_seconds":         86400,
			"reference_set_certain": true,
			"policy":                map[string]any{"keep_last": nil, "older_than_seconds": nil},
			"entries": []any{
				entry("github.com/example/skills", "a", "2026-09-29T13:00:00Z", false),
				entry("github.com/example/skills", "b", "2026-09-28T12:00:00Z", false),
			},
		},
		map[string]any{
			"name":                  "grace-boundary-age-equal-to-grace-is-removable",
			"now":                   "2026-09-30T12:00:00Z",
			"grace_seconds":         86400,
			"reference_set_certain": true,
			"policy":                map[string]any{"keep_last": nil, "older_than_seconds": nil},
			"entries": []any{
				entry("github.com/example/skills", "a", "2026-09-29T12:00:00Z", false),
			},
		},
		map[string]any{
			"name":                  "future-last-use-time-is-inside-grace",
			"now":                   "2026-09-30T12:00:00Z",
			"grace_seconds":         86400,
			"reference_set_certain": true,
			"policy":                map[string]any{"keep_last": nil, "older_than_seconds": nil},
			"entries": []any{
				entry("github.com/example/skills", "a", "2026-10-01T12:00:00Z", false),
			},
		},
		map[string]any{
			"name":                  "keep-last-is-per-source",
			"now":                   "2026-09-30T12:00:00Z",
			"grace_seconds":         86400,
			"reference_set_certain": true,
			"policy":                map[string]any{"keep_last": 2, "older_than_seconds": nil},
			"entries": []any{
				entry("github.com/example/skills", "a", "2026-09-20T12:00:00Z", false),
				entry("github.com/example/skills", "b", "2026-09-21T12:00:00Z", false),
				entry("github.com/example/skills", "c", "2026-09-22T12:00:00Z", false),
				entry("github.com/example/skills", "d", "2026-09-23T12:00:00Z", false),
				entry("project-management", "e", "2026-08-31T12:00:00Z", false),
			},
		},
		map[string]any{
			"name":                  "keep-last-counts-reachable-entries",
			"now":                   "2026-09-30T12:00:00Z",
			"grace_seconds":         86400,
			"reference_set_certain": true,
			"policy":                map[string]any{"keep_last": 2, "older_than_seconds": nil},
			"entries": []any{
				entry("github.com/example/skills", "a", "2026-09-28T12:00:00Z", true),
				entry("github.com/example/skills", "b", "2026-09-27T12:00:00Z", false),
				entry("github.com/example/skills", "c", "2026-09-26T12:00:00Z", false),
			},
		},
		map[string]any{
			"name":                  "keep-last-zero-adds-no-retention",
			"now":                   "2026-09-30T12:00:00Z",
			"grace_seconds":         86400,
			"reference_set_certain": true,
			"policy":                map[string]any{"keep_last": 0, "older_than_seconds": nil},
			"entries": []any{
				entry("github.com/example/skills", "a", "2026-09-28T12:00:00Z", false),
				entry("github.com/example/skills", "b", "2026-09-27T12:00:00Z", false),
			},
		},
		map[string]any{
			"name":                  "keep-last-tie-breaks-by-commit-bytes",
			"now":                   "2026-09-30T12:00:00Z",
			"grace_seconds":         86400,
			"reference_set_certain": true,
			"policy":                map[string]any{"keep_last": 1, "older_than_seconds": nil},
			"entries": []any{
				entry("github.com/example/skills", "b", "2026-09-25T12:00:00Z", false),
				entry("github.com/example/skills", "a", "2026-09-25T12:00:00Z", false),
				entry("github.com/example/skills", "c", "2026-09-25T12:00:00Z", false),
			},
		},
		map[string]any{
			"name":                  "older-than-retains-newer-entries",
			"now":                   "2026-09-30T12:00:00Z",
			"grace_seconds":         86400,
			"reference_set_certain": true,
			"policy":                map[string]any{"keep_last": nil, "older_than_seconds": 604800},
			"entries": []any{
				entry("github.com/example/skills", "a", "2026-09-27T12:00:00Z", false),
				entry("github.com/example/skills", "b", "2026-09-20T12:00:00Z", false),
			},
		},
		map[string]any{
			"name":                  "older-than-boundary-age-equal-is-retained",
			"now":                   "2026-09-30T12:00:00Z",
			"grace_seconds":         86400,
			"reference_set_certain": true,
			"policy":                map[string]any{"keep_last": nil, "older_than_seconds": 604800},
			"entries": []any{
				entry("github.com/example/skills", "a", "2026-09-23T12:00:00Z", false),
				entry("github.com/example/skills", "b", "2026-09-23T11:59:59Z", false),
			},
		},
		map[string]any{
			"name":                  "older-than-zero-adds-no-retention",
			"now":                   "2026-09-30T12:00:00Z",
			"grace_seconds":         86400,
			"reference_set_certain": true,
			"policy":                map[string]any{"keep_last": nil, "older_than_seconds": 0},
			"entries": []any{
				entry("github.com/example/skills", "a", "2026-09-28T12:00:00Z", false),
				entry("github.com/example/skills", "b", "2026-09-30T10:00:00Z", false),
			},
		},
		map[string]any{
			"name":                  "both-policies-retain-the-union",
			"now":                   "2026-09-30T12:00:00Z",
			"grace_seconds":         86400,
			"reference_set_certain": true,
			"policy":                map[string]any{"keep_last": 1, "older_than_seconds": 432000},
			"entries": []any{
				entry("github.com/example/skills", "a", "2026-09-20T12:00:00Z", false),
				entry("github.com/example/skills", "b", "2026-09-10T12:00:00Z", false),
				entry("github.com/example/skills", "c", "2026-09-26T12:00:00Z", false),
				entry("github.com/example/skills", "9", "2026-09-27T12:00:00Z", false),
				entry("project-management", "d", "2026-08-31T12:00:00Z", false),
				entry("project-management", "e", "2026-08-21T12:00:00Z", false),
			},
		},
		map[string]any{
			"name":                  "reachable-is-never-removed",
			"now":                   "2026-09-30T12:00:00Z",
			"grace_seconds":         86400,
			"reference_set_certain": true,
			"policy":                map[string]any{"keep_last": 0, "older_than_seconds": 0},
			"entries": []any{
				entry("github.com/example/skills", "a", "2025-08-26T12:00:00Z", true),
				entry("project-management", "b", "2025-08-26T12:00:00Z", true),
			},
		},
		map[string]any{
			"name":                  "uncertain-reference-set-removes-nothing",
			"now":                   "2026-09-30T12:00:00Z",
			"grace_seconds":         86400,
			"reference_set_certain": false,
			"policy":                map[string]any{"keep_last": nil, "older_than_seconds": nil},
			"entries": []any{
				entry("github.com/example/skills", "a", "2026-08-31T12:00:00Z", true),
				entry("github.com/example/skills", "b", "2026-08-31T12:00:00Z", false),
				entry("project-management", "c", "2026-08-01T12:00:00Z", false),
			},
		},
		map[string]any{
			"name":                  "uncertain-precedes-grace-and-keep-last",
			"now":                   "2026-09-30T12:00:00Z",
			"grace_seconds":         86400,
			"reference_set_certain": false,
			"policy":                map[string]any{"keep_last": 1, "older_than_seconds": nil},
			"entries": []any{
				entry("github.com/example/skills", "a", "2026-09-30T11:00:00Z", false),
				entry("github.com/example/skills", "b", "2026-09-27T12:00:00Z", false),
			},
		},
		map[string]any{
			"name":                  "sha256-object-format-commit",
			"now":                   "2026-09-30T12:00:00Z",
			"grace_seconds":         86400,
			"reference_set_certain": true,
			"policy":                map[string]any{"keep_last": nil, "older_than_seconds": nil},
			"entries": []any{
				entry("github.com/example/skills", "f", "2026-09-27T12:00:00Z", false),
				entry("github.com/example/skills", "a", "2026-09-27T12:00:00Z", true),
			},
		},
	}
	for _, raw := range cases {
		c := raw.(map[string]any)
		c["expected"] = snapshotRetentionExpected(c)
	}
	writeJSON(filepath.Join(dir, "snapshot-retention.json"), map[string]any{
		"actions":          []any{"retain", "remove"},
		"capability":       "snapshot-retention",
		"cases":            cases,
		"protocol_version": "1.0.0-rc.13",
		"reasons":          []any{"reachable", "reference_uncertain", "grace", "keep_last", "newer_than", "unreachable"},
		"rule":             "profiles/manager.md section 10.1: an entry is removed only when it is unreachable, the reference set is certain, its age is at least the grace period, it is outside the per-source keep-last window (publication time descending, then commit ascending by bytes; reachable entries count toward the window), and, when older_than_seconds is given, its age exceeds it. Each entry carries exactly one reason, from the first applicable rule: reachable, reference_uncertain, grace, keep_last, newer_than, unreachable. Age is now minus last_used_at in whole seconds. expected is ordered by source then commit by bytes.",
		"schema_version":   1,
	})
}

func snapshotRetentionExpected(c map[string]any) []any {
	entries := append([]any(nil), c["entries"].([]any)...)
	policy := c["policy"].(map[string]any)
	now, err := time.Parse(time.RFC3339, c["now"].(string))
	must(err)
	used := func(e map[string]any) time.Time {
		t, err := time.Parse(time.RFC3339, e["last_used_at"].(string))
		must(err)
		return t
	}
	sort.Slice(entries, func(i, j int) bool {
		a, b := entries[i].(map[string]any), entries[j].(map[string]any)
		if a["source"] != b["source"] {
			return a["source"].(string) < b["source"].(string)
		}
		if !used(a).Equal(used(b)) {
			return used(a).After(used(b))
		}
		return a["commit"].(string) < b["commit"].(string)
	})
	ranks := map[string]int{}
	result := []any{}
	for _, raw := range entries {
		e := raw.(map[string]any)
		source := e["source"].(string)
		rank := ranks[source]
		ranks[source]++
		age := int(now.Sub(used(e)) / time.Second)
		reason := "unreachable"
		switch {
		case e["reachable"].(bool):
			reason = "reachable"
		case !c["reference_set_certain"].(bool):
			reason = "reference_uncertain"
		case age < c["grace_seconds"].(int):
			reason = "grace"
		case policy["keep_last"] != nil && rank < policy["keep_last"].(int):
			reason = "keep_last"
		case policy["older_than_seconds"] != nil && age <= policy["older_than_seconds"].(int):
			reason = "newer_than"
		}
		action := "retain"
		if reason == "unreachable" {
			action = "remove"
		}
		result = append(result, map[string]any{"source": source, "commit": e["commit"], "action": action, "reason": reason})
	}
	sort.Slice(result, func(i, j int) bool {
		a, b := result[i].(map[string]any), result[j].(map[string]any)
		if a["source"] != b["source"] {
			return a["source"].(string) < b["source"].(string)
		}
		return a["commit"].(string) < b["commit"].(string)
	})
	return result
}
