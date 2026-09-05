package main

import (
	"reflect"
	"strings"
	"testing"
)

func mustRange(t *testing.T, text string) versionRange {
	t.Helper()
	parsed, err := parseRange(text)
	if err != nil {
		t.Fatalf("range %q must parse", text)
	}
	return parsed
}

func rangeSpelling(r versionRange) string {
	var sets []string
	for _, set := range r {
		var items []string
		for _, c := range set {
			items = append(items, c.String())
		}
		sets = append(sets, strings.Join(items, " "))
	}
	return strings.Join(sets, " || ")
}

// The section 1.4 coercion table, spelled exactly as the text spells it.
func TestRangeCoercionTableIsExact(t *testing.T) {
	table := map[string]string{
		"1.2": ">=1.2.0 <1.3.0-0", "=1.2": ">=1.2.0 <1.3.0-0", ">=2.1": ">=2.1.0", ">1.2": ">=1.3.0",
		"<3": "<3.0.0-0", "<=1.2": "<1.3.0-0",
		"^1.2.3": ">=1.2.3 <2.0.0-0", "^0.2.3": ">=0.2.3 <0.3.0-0", "^0.0.3": ">=0.0.3 <0.0.4-0",
		"^1.4": ">=1.4.0 <2.0.0-0", "^0.1": ">=0.1.0 <0.2.0-0", "^0": ">=0.0.0 <1.0.0-0",
		"~1.2.3": ">=1.2.3 <1.3.0-0", "~1.2": ">=1.2.0 <1.3.0-0", "~1": ">=1.0.0 <2.0.0-0",
		"1.x": ">=1.0.0 <2.0.0-0", "1.2.x": ">=1.2.0 <1.3.0-0", "*": "*", "x": "*", "X": "*", "latest": "*",
		"1.2.3": "=1.2.3", "^1 || ^3": ">=1.0.0 <2.0.0-0 || >=3.0.0 <4.0.0-0", ">=1.0.0 <2": ">=1.0.0 <2.0.0-0",
	}
	for text, want := range table {
		if got := rangeSpelling(mustRange(t, text)); got != want {
			t.Fatalf("%q desugars to %q, want %q", text, got, want)
		}
	}
}

func TestExcludedRangeFormsAreRejected(t *testing.T) {
	for _, text := range []string{"1.2.3 - 2.3.4", "v1.2.3", "^v1", ">=v1.0.0", "", "||", "^1 ||", "1.2.3.4", "^01.2", ">>1", "1.2.3-", "latest || ^1", "1.2.3+build"} {
		if _, err := parseRange(text); err == nil {
			t.Fatalf("range %q must be rejected", text)
		}
	}
}

func TestVersionTagGrammar(t *testing.T) {
	for _, tag := range []string{"1.2.3", "v1.2", "v1.2.3+build.5", "v01.2.3", "v1.2.3-01", "V1.2.3", "stable", "v1.2.3-rc..1"} {
		if _, ok := parseTagVersion(tag); ok {
			t.Fatalf("tag %q must not be a version candidate", tag)
		}
	}
	for _, tag := range []string{"v0.0.0", "v2.0.0-rc.1", "v10.20.30-0.3.7"} {
		if _, ok := parseTagVersion(tag); !ok {
			t.Fatalf("tag %q must be a version candidate", tag)
		}
	}
	ordered := []string{"1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-alpha.beta", "1.0.0-beta", "1.0.0-beta.2", "1.0.0-beta.11", "1.0.0-rc.1", "1.0.0"}
	for index := 1; index < len(ordered); index++ {
		a, _ := parseVersion(ordered[index-1])
		b, _ := parseVersion(ordered[index])
		if compareVersions(a, b) >= 0 {
			t.Fatalf("%s must precede %s", ordered[index-1], ordered[index])
		}
	}
}

func TestPrereleaseAdmissionRule(t *testing.T) {
	check := func(rangeText, version string, want bool) {
		t.Helper()
		v, ok := parseVersion(version)
		if !ok {
			t.Fatalf("version %q must parse", version)
		}
		if got := rangeSatisfies(mustRange(t, rangeText), v); got != want {
			t.Fatalf("%q satisfies %q = %v, want %v", version, rangeText, got, want)
		}
	}
	check("^2.0.0-rc.0", "2.0.0-rc.1", true)
	check(">=2.0.0-rc.0", "2.0.0-rc.1", true)
	check("^2.0.0-rc.0", "2.1.0-rc.1", false)
	check(">=2.0.0-rc.0", "2.1.0-rc.1", false)
	check("*", "2.0.0-rc.1", false)
	check("latest", "2.0.0-rc.1", false)
	check(">=1.0.0", "2.0.0-rc.1", false)
	check("<3", "2.0.0-rc.1", false)
	check("<3", "3.0.0-rc.1", false)
	check("<3", "2.9.9", true)
	check("^1.2.3", "2.0.0-0", false)
	check("^0", "1.0.0", false)
	check("^0", "0.9.9", true)
}

func lockMember(t *testing.T, lock map[string]any, name string) map[string]any {
	t.Helper()
	for _, member := range lock["members"].([]any) {
		entry := member.(map[string]any)
		if entry["name"] == name {
			return entry
		}
	}
	t.Fatalf("lock has no member %s", name)
	return nil
}

func resolveCase(t *testing.T, name string) resolutionResult {
	t.Helper()
	for _, item := range resolutionCases() {
		if item.name == name {
			return resolveClosure(item.input)
		}
	}
	t.Fatalf("no resolution case %s", name)
	return resolutionResult{}
}

func TestWorkedExampleLockMatchesDecision0012(t *testing.T) {
	result := resolveCase(t, "worked-example-default-policy")
	if result.err != nil {
		t.Fatalf("worked example failed: %s %v", result.err.diagnostic, result.err.detail)
	}
	want := []struct {
		name, kind, version, pin string
		weight                   int
		requiredBy               []any
		overlay                  bool
	}{
		{"companyA-root-context-core", "context", "3.2.1", strings.Repeat("1", 40), 0, []any{"companyA-root-context-developers-core", "companyA-root-context-ios-developer-umbrella"}, false},
		{"companyA-root-context-developers-core", "context", "1.6.0", strings.Repeat("3", 40), 20, []any{"companyA-root-context-ios-developer-umbrella"}, false},
		{"companyA-root-context-developers-figma", "context", "1.1.0", strings.Repeat("4", 40), 40, []any{"companyA-root-context-ios-developer-umbrella"}, false},
		{"companyA-root-context-developers-ios", "context", "2.4.2", strings.Repeat("5", 40), 60, []any{"companyA-root-context-ios-developer-umbrella"}, false},
		{"companyA-root-context-ios-developer-umbrella", "context", "2.3.0", strings.Repeat("6", 40), 100, []any{}, false},
		{"companyA-root-context-organizational-structure", "context", "1.0.4", strings.Repeat("2", 40), 10, []any{"companyA-root-context-core"}, false},
		{"personal", "context", "0.3.0", strings.Repeat("a", 64), 1000, []any{}, true},
		{"figma-devmode", "mcp", "1.2.0", strings.Repeat("7", 40), 0, []any{"companyA-root-context-ios-developer-umbrella"}, false},
		{"pdf", "skill", "1.2.5", strings.Repeat("8", 40), 0, []any{"companyA-root-context-ios-developer-umbrella"}, false},
		{"swiftui", "skill", "4.3.0", strings.Repeat("9", 40), 0, []any{"companyA-root-context-developers-ios", "companyA-root-context-ios-developer-umbrella"}, false},
	}
	members := result.lock["members"].([]any)
	if len(members) != len(want) {
		t.Fatalf("lock has %d members, want %d", len(members), len(want))
	}
	for index, item := range want {
		entry := members[index].(map[string]any)
		pin := entry["commit"]
		if item.overlay {
			pin = entry["state_sha256"]
		}
		if entry["name"] != item.name || entry["kind"] != item.kind || entry["version"] != item.version || pin != item.pin || entry["weight"] != item.weight || entry["overlay"] != item.overlay || !reflect.DeepEqual(entry["required_by"], item.requiredBy) {
			t.Fatalf("member %d = %#v, want %+v", index, entry, item)
		}
	}
	if lockMember(t, result.lock, "companyA-root-context-developers-figma")["directory"] != "contexts/figma" {
		t.Fatal("the figma member must record its directory")
	}
	if _, present := lockMember(t, result.lock, "personal")["source"]; present {
		t.Fatal("a path member has no source")
	}
	if len(result.warnings) != 0 {
		t.Fatalf("worked example must resolve without warnings: %v", result.warnings)
	}
}

func TestResolutionCaseOutcomes(t *testing.T) {
	expectVersion := func(caseName, member, version string) {
		t.Helper()
		result := resolveCase(t, caseName)
		if result.err != nil {
			t.Fatalf("%s failed: %s %v", caseName, result.err.diagnostic, result.err.detail)
		}
		if got := lockMember(t, result.lock, member)["version"]; got != version {
			t.Fatalf("%s: %s resolved to %v, want %s", caseName, member, got, version)
		}
	}
	expectError := func(caseName, diagnostic string) map[string]any {
		t.Helper()
		result := resolveCase(t, caseName)
		if result.err == nil {
			t.Fatalf("%s must fail with %s, got lock %v", caseName, diagnostic, result.lock)
		}
		if result.err.diagnostic != diagnostic {
			t.Fatalf("%s failed with %s, want %s", caseName, result.err.diagnostic, diagnostic)
		}
		return result.err.detail
	}
	expectVersion("downward-reselection", "lib", "1.5.0")
	expectVersion("selection-never-increases", "app", "1.0.0")
	expectVersion("selection-never-increases", "lib", "2.0.0")
	if result := resolveCase(t, "selection-never-increases"); len(result.lock["members"].([]any)) != 3 {
		t.Fatalf("helper must leave the closure: %v", result.lock["members"])
	}
	expectVersion("prerelease-admission", "core", "2.0.0-rc.1")
	expectVersion("prerelease-excluded-by-latest", "root", "1.0.0")
	expectVersion("exact-constraint-unification", "core", "3.2.1")
	expectVersion("or-highest-member", "core", "3.1.0")
	expectVersion("latest-is-star", "root", "1.2.0")
	expectVersion("non-version-tag-exact", "root", "0.9.0")
	expectVersion("skill-exact-dependency", "fonts", "1.1.0")
	expectVersion("overlay-git-explicit-weight", "team", "1.1.0")
	if got := lockMember(t, resolveCase(t, "overlay-git-explicit-weight").lock, "team")["weight"]; got != 250 {
		t.Fatalf("overlay declaration weight must outrank the edge weight, got %v", got)
	}
	if got := lockMember(t, resolveCase(t, "overlay-git-explicit-weight").lock, "team")["overlay"]; got != true {
		t.Fatal("a required package that is also an overlay is flagged overlay")
	}
	detail := expectError("range-conflict-empty-intersection", "context_range_conflict")
	if detail["name"] != "core" || len(detail["requirers"].([]any)) != 2 || !reflect.DeepEqual(detail["candidates"], []any{"2.5.0", "3.1.0"}) {
		t.Fatalf("conflict detail must name every requirer and the candidates considered: %v", detail)
	}
	expectError("exact-constraints-disagree", "context_range_conflict")
	expectError("exact-outside-range", "context_range_conflict")
	expectError("no-version-tags", "context_range_conflict")
	expectError("overlay-joint-resolution-conflict", "context_range_conflict")
	expectError("version-mismatch", "context_version_mismatch")
	expectError("weight-conflict", "context_weight_conflict")
	expectError("weights-not-root", "context_weights_not_root")
	expectError("weights-duplicate", "context_weights_duplicate")
	expectError("weight-unknown", "context_weight_unknown")
	expectError("overlay-duplicate-name", "environment_composition_invalid")
	rootWins := resolveCase(t, "weight-conflict-root-map-wins")
	if rootWins.err != nil || len(rootWins.warnings) != 1 || rootWins.warnings[0]["diagnostic"] != "context_weight_conflict" {
		t.Fatalf("a disagreement the root map names is a warning: %v %v", rootWins.err, rootWins.warnings)
	}
	if got := lockMember(t, rootWins.lock, "shared")["weight"]; got != 70 {
		t.Fatalf("the root has the final word, got weight %v", got)
	}
}

// Narrowing the gate: a mutated input that must change the outcome.
func TestResolutionGateNarrows(t *testing.T) {
	input := workedExampleInput()
	// Widening the ios requirement to admit 3.0.0 pulls swiftui to ^5, which
	// the umbrella's ^4 forbids: the joint constraint set fails instead of
	// silently keeping 4.3.0.
	umbrella := input.Packages["companyA-root-context-ios-developer-umbrella"]
	for commit, manifest := range umbrella.Commits {
		if manifest.Version != "2.3.0" {
			continue
		}
		for index := range manifest.Requires {
			if manifest.Requires[index].Name == "companyA-root-context-developers-ios" {
				manifest.Requires[index].Value = ">=2.1"
			}
		}
		umbrella.Commits[commit] = manifest
	}
	result := resolveClosure(input)
	if result.err == nil || result.err.diagnostic != "context_range_conflict" || result.err.detail["name"] != "swiftui" {
		t.Fatalf("widened range must surface the swiftui conflict, got %v %v", result.err, result.lock)
	}
	// Two different locks hash differently, and the hash is the CCJ-1 digest.
	base := resolveClosure(workedExampleInput()).lock
	if lockHash(base) != canonicalSHA256(base) {
		t.Fatal("lock hash is not the CCJ-1 digest")
	}
	changed := cloneMap(base)
	changed["root"] = "other"
	if lockHash(changed) == lockHash(base) {
		t.Fatal("different locks must hash differently")
	}
}
