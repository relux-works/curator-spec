package main

import (
	"encoding/json"
	"fmt"
	"regexp"
	"strings"
	"testing"
)

// canonicalVersionRE is the section 2.1 grammar, restated here so the test
// measures the shipped schema against the contract rather than against itself.
var canonicalVersionRE = regexp.MustCompile(`\A(0|[1-9][0-9]{0,5})\.(0|[1-9][0-9]{0,5})\.(0|[1-9][0-9]{0,5})\z`)

func TestToolchainRequirementIsClosedAndCanonical(t *testing.T) {
	kinds := map[string]map[string]any{
		"at_least": atLeast("1.23.0"),
		"range":    rangeOf("1.23.0", "1.25.0"),
		"exact":    exactly("1.23.4"),
	}
	members := map[string][]string{
		"at_least": {"kind", "min"},
		"range":    {"kind", "min", "below"},
		"exact":    {"kind", "equals"},
	}
	for kind, value := range kinds {
		if len(value) != len(members[kind]) {
			t.Fatalf("%s carries %d members, want %d", kind, len(value), len(members[kind]))
		}
		for _, member := range members[kind] {
			if _, ok := value[member]; !ok {
				t.Fatalf("%s is missing %s", kind, member)
			}
		}
		for member, literal := range value {
			if member == "kind" {
				continue
			}
			if !canonicalVersionRE.MatchString(literal.(string)) {
				t.Fatalf("%s.%s %q is not a canonical version", kind, member, literal)
			}
		}
	}
	requirementValue := requirement("go", atLeast("1.23.0"))
	if len(requirementValue) != 2 || requirementValue["id"] != "go" {
		t.Fatalf("the requirement object is not exactly id and version: %v", requirementValue)
	}
}

// TestRegistryEntriesAreTotalOverTheirPlatforms is the registry half of the
// section 6.3 gate: it is what makes the Stage A host-pair check total.
func TestRegistryEntriesAreTotalOverTheirPlatforms(t *testing.T) {
	registry := toolchainRegistry()
	complete := 0
	for _, item := range registry["entries"].([]any) {
		entry := item.(map[string]any)
		if entry["status"] != "complete" {
			if _, ok := entry["drivers"]; ok {
				t.Fatalf("reserved entry %v claims a driver; reservation is not admission", entry["toolchain_id"])
			}
			continue
		}
		complete++
		systems := map[string]bool{}
		for _, pair := range entry["platforms"].([]any) {
			systems[pair.(map[string]any)["operating_system"].(string)] = true
		}
		for _, table := range []string{"primary_relpath", "probe"} {
			declared := entry[table].(map[string]any)
			if len(declared) != len(systems) {
				t.Fatalf("%v %s declares %d operating systems, platforms names %d",
					entry["toolchain_id"], table, len(declared), len(systems))
			}
			for name := range declared {
				if !systems[name] {
					t.Fatalf("%v %s declares %q outside its platforms set", entry["toolchain_id"], table, name)
				}
			}
		}
	}
	if complete != 1 {
		t.Fatalf("the registry declares %d complete entries, want exactly the go entry", complete)
	}
}

// TestValueClassifiersAreOrderedAndTotal pins the section 3.1.1 rules on the
// shipped tables: forbidden classes first among value classes, exactly one
// catch-all and it is last, and the absence class first and matching no value.
func TestValueClassifiersAreOrderedAndTotal(t *testing.T) {
	tables := map[string][]any{
		"go":   goMetadataSources(),
		"rust": expectedRustMetadataSources(),
	}
	for name, sources := range tables {
		for _, item := range sources {
			source := item.(map[string]any)
			for _, fieldItem := range source["fields"].([]any) {
				field := fieldItem.(map[string]any)
				if field["disposition"] != "classified" {
					continue
				}
				classes := field["classes"].([]any)
				label := fmt.Sprintf("%s %v#%v", name, source["path"], field["field_path"])
				catchAll := 0
				seenOther := false
				for index, classItem := range classes {
					class := classItem.(map[string]any)
					if class["catch_all"] == true {
						catchAll++
						if index != len(classes)-1 {
							t.Fatalf("%s: catch-all class is not last", label)
						}
					}
					if class["matches"] == "absence" && index != 0 {
						t.Fatalf("%s: the absence class is not first", label)
					}
					if class["matches"] != "value" {
						continue
					}
					if class["disposition"] == "forbidden" {
						if seenOther {
							t.Fatalf("%s: forbidden class %v follows a compared or ignored one",
								label, class["name"])
						}
					} else {
						seenOther = true
					}
				}
				if catchAll != 1 {
					t.Fatalf("%s: %d catch-all classes, want exactly one", label, catchAll)
				}
			}
		}
	}
}

// TestGuidanceCatalogExercisesAllThreeCoverageModes keeps the corpus from
// silently narrowing to whichever shape happens to be easiest to generate. All
// three are valid, so all three must be exercised.
func TestGuidanceCatalogExercisesAllThreeCoverageModes(t *testing.T) {
	catalog := guidanceCatalog()
	byReason := map[string]map[string][]bool{}
	for _, item := range catalog["entries"].([]any) {
		entry := item.(map[string]any)
		reason := entry["reason"].(string)
		if byReason[reason] == nil {
			byReason[reason] = map[string][]bool{}
		}
		platform := entry["platform"].(string)
		byReason[reason][platform] = append(byReason[reason][platform], entry["active"].(bool))
	}
	modes := map[string]int{}
	for reason, platforms := range byReason {
		anyActive := false
		exactActive := 0
		for platform, states := range platforms {
			for _, active := range states {
				if !active {
					continue
				}
				if platform == "any" {
					anyActive = true
				} else {
					exactActive++
				}
			}
		}
		switch {
		case anyActive && exactActive == 0:
			modes["any"]++
		case !anyActive && exactActive > 0:
			modes["per_os"]++
		case anyActive && exactActive > 0:
			modes["hybrid"]++
		default:
			t.Fatalf("reason %q has no active coverage at all", reason)
		}
	}
	for _, mode := range []string{"any", "per_os", "hybrid"} {
		if modes[mode] == 0 {
			t.Fatalf("no reason exercises the %s coverage mode: %v", mode, modes)
		}
	}
}

// TestRetiredGuidanceStaysResolvable pins the one-way monotone lifecycle.
func TestRetiredGuidanceStaysResolvable(t *testing.T) {
	retired := 0
	byID := map[string]map[string]any{}
	for _, item := range guidanceCatalog()["entries"].([]any) {
		entry := item.(map[string]any)
		byID[entry["guidance_id"].(string)] = entry
	}
	for _, entry := range byID {
		successor, ok := entry["superseded_by"]
		if !ok {
			continue
		}
		retired++
		if entry["active"] == true {
			t.Fatalf("%v is active and carries superseded_by", entry["guidance_id"])
		}
		target, ok := byID[successor.(string)]
		if !ok {
			t.Fatalf("%v supersedes the absent %v", entry["guidance_id"], successor)
		}
		if target["active"] != true {
			t.Fatalf("%v supersedes a retired entry", entry["guidance_id"])
		}
	}
	if retired == 0 {
		t.Fatal("the catalog carries no retired entry, so the lifecycle is untested")
	}
}

// siteKey and payloadKey render a firing site as (code, stage, discriminant).
// The discriminant is load-bearing rather than decorative: `platform_unsupported`
// fires twice inside stage A with different established sets, so a key that
// dropped it would let either half satisfy the other's obligation.
func siteKey(site map[string]any) string {
	key := site["code"].(string) + "@" + site["stage"].(string)
	discriminant, ok := site["discriminant"].(map[string]any)
	if !ok {
		return key
	}
	for _, member := range []string{"check", "substep"} {
		if value, present := discriminant[member]; present {
			return key + "/" + value.(string)
		}
	}
	return key
}

func payloadKey(payload map[string]any) string {
	key := payload["code"].(string) + "@" + payload["stage"].(string)
	for _, member := range []string{"check", "substep"} {
		if value, present := payload[member]; present {
			return key + "/" + value.(string)
		}
	}
	return key
}

// TestDiagnosticPayloadsCoverEveryFiringSite is the union's completeness half:
// a site with no instance is a shape nobody exercised.
func TestDiagnosticPayloadsCoverEveryFiringSite(t *testing.T) {
	sites := map[string]bool{}
	for _, item := range diagnosticSites() {
		sites[siteKey(item.(map[string]any))] = true
	}
	instantiated := map[string]bool{}
	for _, payload := range diagnosticPayloads() {
		key := payloadKey(payload)
		if !sites[key] {
			t.Fatalf("payload %s is not a declared firing site", key)
		}
		instantiated[key] = true
	}
	for site := range sites {
		if !instantiated[site] {
			t.Fatalf("firing site %s carries no payload instance", site)
		}
	}
}

// TestConditionalMembersFollowTheirEstablishingStep is the payload rule in one
// assertion: a payload carries exactly the values established before it fires.
func TestConditionalMembersFollowTheirEstablishingStep(t *testing.T) {
	expected := map[string][2]bool{}
	for _, item := range diagnosticSites() {
		site := item.(map[string]any)
		expected[siteKey(site)] = [2]bool{
			site["effective_requirement"].(bool),
			site["resolved_version"].(bool),
		}
	}
	for _, payload := range diagnosticPayloads() {
		key := payloadKey(payload)
		want := expected[key]
		_, hasRequirement := payload["effective_requirement"]
		_, hasVersion := payload["resolved_version"]
		if hasRequirement != want[0] {
			t.Fatalf("%s effective_requirement present=%v, site says %v", key, hasRequirement, want[0])
		}
		if hasVersion != want[1] {
			t.Fatalf("%s resolved_version present=%v, site says %v", key, hasVersion, want[1])
		}
		if _, hasPrerelease := payload["prerelease"]; hasPrerelease != want[1] {
			t.Fatalf("%s prerelease does not follow resolved_version", key)
		}
	}
}

// TestRequirementInvalidNeverEchoesThePackageValue is the no-echo rule.
func TestRequirementInvalidNeverEchoesThePackageValue(t *testing.T) {
	for _, payload := range diagnosticPayloads() {
		if payload["code"] != "build_toolchain_requirement_invalid" {
			continue
		}
		members := map[string]bool{}
		for member := range payload {
			members[member] = true
		}
		for _, forbidden := range []string{"value", "literal", "requirement", "raw", "input"} {
			if members[forbidden] {
				t.Fatalf("requirement_invalid carries %q, which reproduces an unvalidated package byte", forbidden)
			}
		}
	}
}

// TestSchemaEightWireSurfaceCarriesNoResolutionInput is the generator-side half
// of the release gate: the positive case a manager will copy must be clean.
func TestSchemaEightWireSurfaceCarriesNoResolutionInput(t *testing.T) {
	manifest := validV8SkillManifest()
	commands := manifest["commands"].(map[string]any)
	for name, item := range commands {
		command := item.(map[string]any)
		if command["type"] != "build" {
			continue
		}
		toolchain, ok := command["toolchain"].(map[string]any)
		if !ok {
			t.Fatalf("build command %q carries no toolchain requirement", name)
		}
		if len(toolchain) != 2 {
			t.Fatalf("build command %q toolchain is not exactly id and version", name)
		}
		for _, forbidden := range forbiddenWireFieldNames {
			if _, present := command[forbidden.field]; present {
				t.Fatalf("build command %q carries the resolution input %q", name, forbidden.field)
			}
		}
	}
	descriptor := validSkillBuildV2()
	for name, item := range descriptor["targets"].(map[string]any) {
		target := item.(map[string]any)
		for _, forbidden := range forbiddenWireFieldNames {
			if _, present := target[forbidden.field]; present {
				t.Fatalf("descriptor target %q carries the resolution input %q", name, forbidden.field)
			}
		}
	}
}

// TestEveryRejectingPreflightCaseAssertsTheNoMutationBoundary is the property
// the two stages exist to hold, asserted per case rather than in prose.
func TestEveryRejectingPreflightCaseAssertsTheNoMutationBoundary(t *testing.T) {
	rejecting := 0
	for _, item := range preflightCases() {
		expected := item.(map[string]any)["expected"].(map[string]any)
		if expected["outcome"] != "rejected" {
			continue
		}
		rejecting++
		for _, assertion := range []string{"compiler_started", "persistent_mutation"} {
			if expected[assertion] != false {
				t.Fatalf("case %v does not assert %s is false", item.(map[string]any)["case"], assertion)
			}
		}
	}
	if rejecting < 40 {
		t.Fatalf("only %d rejecting preflight cases; the negative inventory has shrunk", rejecting)
	}
}

// TestCaseIdentifiersAreUnique keeps two cases from claiming one inventory
// number, which would let a dropped case hide behind its twin.
func TestCaseIdentifiersAreUnique(t *testing.T) {
	groups := map[string][]any{
		"preflight": preflightCases(),
		"registry":  toolchainRegistryCases(),
		"guidance":  append(guidanceCases(), guidanceTransitionCases()...),
		"metadata":  goMetadataCases(),
		"payload":   diagnosticPayloadCases(),
	}
	seen := map[string]string{}
	for group, cases := range groups {
		for _, item := range cases {
			identifier := item.(map[string]any)["case"].(string)
			if previous, ok := seen[identifier]; ok {
				t.Fatalf("case %q is declared in both %s and %s", identifier, previous, group)
			}
			seen[identifier] = group
		}
	}
	for _, property := range goAlignmentTable()["properties"].([]any) {
		identifier := property.(map[string]any)["case"].(string)
		if previous, ok := seen[identifier]; ok {
			t.Fatalf("case %q is declared in both %s and the alignment properties", identifier, previous)
		}
		seen[identifier] = "alignment"
	}
	for _, item := range boundaryProbeContract()["cases"].([]any) {
		identifier := item.(map[string]any)["case"].(string)
		if previous, ok := seen[identifier]; ok {
			t.Fatalf("case %q is declared in both %s and the probe contract", identifier, previous)
		}
		seen[identifier] = "probe"
	}
}

// TestToolchainVectorsAreDeterministic re-renders every toolchain document and
// requires byte equality, because a vector corpus that depends on map iteration
// order cannot be pinned by a manifest digest.
func TestToolchainVectorsAreDeterministic(t *testing.T) {
	render := func(value any) string {
		encoded, err := json.Marshal(value)
		if err != nil {
			t.Fatalf("marshal: %v", err)
		}
		return string(encoded)
	}
	builders := map[string]func() any{
		"registry":  func() any { return toolchainRegistry() },
		"catalog":   func() any { return guidanceCatalog() },
		"preflight": func() any { return preflightCases() },
		"metadata":  func() any { return goMetadataCases() },
		"alignment": func() any { return goAlignmentTable() },
		"payloads":  func() any { return diagnosticPayloads() },
		"sites":     func() any { return diagnosticSites() },
	}
	for name, build := range builders {
		first := render(build())
		for attempt := 0; attempt < 4; attempt++ {
			if again := render(build()); again != first {
				t.Fatalf("%s is not deterministic across renders", name)
			}
		}
		if strings.TrimSpace(first) == "" || first == "null" {
			t.Fatalf("%s rendered empty", name)
		}
	}
}
