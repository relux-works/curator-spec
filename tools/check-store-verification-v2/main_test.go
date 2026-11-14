package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/santhosh-tekuri/jsonschema/v5"
)

func fixture(t *testing.T) ([]byte, *jsonschema.Schema, []vector) {
	t.Helper()
	raw, err := os.ReadFile(filepath.Join("../..", namespace, "vectors/environments-store-boundary.json"))
	if err != nil {
		t.Fatal(err)
	}
	schema, err := jsonschema.Compile(filepath.Join("../..", namespace, "cases.schema.json"))
	if err != nil {
		t.Fatal(err)
	}
	cases, err := decodeCases(raw, schema)
	if err != nil {
		t.Fatal(err)
	}
	return raw, schema, cases
}

// The complete proposal and predecessor mapping pass; this is metadata evidence only.
func TestProposal(t *testing.T) {
	if err := check("../.."); err != nil {
		t.Fatal(err)
	}
}

// Both carrier directions refuse before case evaluation, with a valid v2 neighbor.
// The legacy struct is the v1 carrier shape, not an execution of a manager reader.
func TestCarrierDirections(t *testing.T) {
	raw, schema, _ := fixture(t)
	old, err := os.ReadFile(filepath.Join("../..", predecessorPath))
	if err != nil {
		t.Fatal(err)
	}
	var legacy struct {
		Resolve []json.RawMessage `json:"resolve_cases"`
	}
	if err := json.Unmarshal(old, &legacy); err != nil || len(legacy.Resolve) == 0 {
		t.Fatalf("legacy positive: %v", err)
	}
	if err := json.Unmarshal(raw, &legacy); err == nil || !strings.Contains(err.Error(), "cannot unmarshal array") {
		t.Fatalf("legacy array refusal: %v", err)
	}
	if _, err := decodeCases(old, schema); err == nil || !strings.Contains(err.Error(), unsupported) {
		t.Fatalf("v2 old-carrier refusal: %v", err)
	}
	if _, err := decodeCases(raw, schema); err != nil {
		t.Fatal(err)
	}
}

// Closed-reader corruptions return the intended unsupported-corpus class and no partial cases.
func TestReaderRefusals(t *testing.T) {
	raw, schema, _ := fixture(t)
	cases := map[string][]byte{
		"unknown-revision":  bytes.Replace(raw, []byte(`"capability_revision": 2`), []byte(`"capability_revision": 3`), 1),
		"mixed-schema":      bytes.Replace(raw, []byte(`"curator.environment-store-case/2"`), []byte(`"curator.environment-store-case/1"`), 1),
		"unknown-field":     bytes.Replace(raw, []byte(`"schema":`), []byte(`"extra":0,"schema":`), 1),
		"duplicate":         bytes.Replace(raw, []byte(`"schema":`), []byte(`"schema":"duplicate","schema":`), 1),
		"missing":           bytes.Replace(raw, []byte(`"capability_revision": 2,`), nil, 1),
		"null":              bytes.Replace(raw, []byte(`"capability_revision": 2`), []byte(`"capability_revision": null`), 1),
		"fraction":          bytes.Replace(raw, []byte(`"capability_revision": 2`), []byte(`"capability_revision": 2.5`), 1),
		"decimal-spelling":  bytes.Replace(raw, []byte(`"capability_revision": 2`), []byte(`"capability_revision": 2.0`), 1),
		"exponent-spelling": bytes.Replace(raw, []byte(`"capability_revision": 2`), []byte(`"capability_revision": 2e0`), 1),
		"escaped-duplicate": bytes.Replace(raw, []byte(`"schema":`), []byte(`"\u0073chema":"duplicate","schema":`), 1),
		"empty":             []byte(`[]`), "utf8": []byte{'[', 0xff, ']'}, "trailing": append(append([]byte{}, raw...), []byte(`{}`)...),
	}
	for name, plant := range cases {
		t.Run(name, func(t *testing.T) {
			vs, err := decodeCases(plant, schema)
			if err == nil || !strings.Contains(err.Error(), unsupported) || vs != nil {
				t.Fatalf("wrong refusal: %d %v", len(vs), err)
			}
		})
	}
	if _, err := decodeCases(raw, schema); err != nil {
		t.Fatal(err)
	}
}

// Each planted observation is rejected by the model while its expected observation passes.
// This proves checker sensitivity, not that a manager emits either observation.
func TestObservationControls(t *testing.T) {
	_, _, cases := fixture(t)
	for _, v := range cases {
		t.Run(v.Name, func(t *testing.T) {
			if err := checkObservation(v, v.Expected); err != nil {
				t.Fatal(err)
			}
			for _, f := range v.Forbidden {
				if err := checkObservation(v, f.Observation); err == nil || !strings.Contains(err.Error(), "observation violates") {
					t.Fatalf("control %s: %v", f.Name, err)
				}
			}
		})
	}
}

// Missing levels, missing matrix members and false-valid neighbors cannot pass coverage.
func TestCoverageControls(t *testing.T) {
	_, _, cases := fixture(t)
	if err := validateCases(cases); err != nil {
		t.Fatal(err)
	}
	for name, refusal := range map[string]string{"level": "missing fatal level", "matrix": "missing matrix case", "neighbor": "invalid positive neighbor", "expected": "observation violates"} {
		t.Run(name, func(t *testing.T) {
			plant := append([]vector{}, cases...)
			switch name {
			case "level":
				plant[103].Levels = []int{1, 2, 3}
			case "matrix":
				plant = append(plant[:103], plant[104:]...)
			case "neighbor":
				plant[len(plant)-1].Positive = "missing"
			case "expected":
				plant[len(plant)-1].Expected.Fragment = true
			}
			if err := validateCases(plant); err == nil || !strings.Contains(err.Error(), refusal) {
				t.Fatalf("wrong coverage refusal: %v", err)
			}
		})
	}
}

// Frozen predecessor identity and exhaustive migration cannot be weakened by the manifest.
func TestMigrationControls(t *testing.T) {
	_, _, cases := fixture(t)
	raw, err := os.ReadFile(filepath.Join("../..", namespace, "manifest.json"))
	if err != nil {
		t.Fatal(err)
	}
	for name, refusal := range map[string]string{"positive": "", "missing-row": "missing migration", "changed-negative": "wrong disposition", "old-diagnostic": "wrong disposition", "identity": "predecessor identity"} {
		t.Run(name, func(t *testing.T) {
			var m manifest
			if err := strict(raw, &m); err != nil {
				t.Fatal(err)
			}
			switch name {
			case "missing-row":
				m.Migration = m.Migration[1:]
			case "changed-negative":
				for i := range m.Migration {
					if m.Migration[i].Negative {
						m.Migration[i].Negative = false
						break
					}
				}
			case "old-diagnostic":
				wrong := "invented"
				m.Migration[0].OldDiagnostic = &wrong
			case "identity":
				m.Predecessor.SHA256 = "wrong"
			}
			err := validateMigration("../..", m, cases)
			if (name == "positive") != (err == nil) {
				t.Fatalf("migration verdict: %v", err)
			}
			if err != nil && !strings.Contains(err.Error(), refusal) {
				t.Fatalf("wrong migration refusal: %v", err)
			}
		})
	}
	// The 24 released Resolve/status fixtures are path/state roots; four
	// dry-run fixtures are Git, and ten repair rows retain their explicit
	// mapping. Swapping either source kind must fail beside the positive.
	var m manifest
	if err := strict(raw, &m); err != nil {
		t.Fatal(err)
	}
	plant := append([]vector{}, cases...)
	pathPredecessors := 0
	for _, v := range cases {
		if v.Predecessor != nil && (v.Predecessor.Group == "resolve_cases" || v.Predecessor.Group == "status_cases") {
			if v.Source != "path" {
				t.Fatalf("non-repair predecessor fixture is %s", v.Source)
			}
			pathPredecessors++
		}
	}
	if pathPredecessors != 24 {
		t.Fatalf("path predecessor coverage: %d", pathPredecessors)
	}
	for i := range plant {
		if plant[i].Predecessor != nil {
			if plant[i].Source != "path" {
				t.Fatal("source control did not select a path predecessor")
			}
			plant[i].Source = "git"
			break
		}
	}
	if err := validateMigration("../..", m, plant); err == nil || !strings.Contains(err.Error(), "predecessor fixture source kind") {
		t.Fatalf("wrong plant refusal: %v", err)
	}
	plant = append([]vector{}, cases...)
	dryRunPredecessors := 0
	for i, v := range plant {
		if v.Predecessor != nil && v.Predecessor.Group == "dry_run_cases" {
			if v.Source != "git" {
				t.Fatalf("dry-run predecessor fixture is %s", v.Source)
			}
			dryRunPredecessors++
			if dryRunPredecessors == 1 {
				plant[i].Source = "path"
			}
		}
	}
	if dryRunPredecessors != 4 {
		t.Fatalf("Git dry-run predecessor coverage: %d", dryRunPredecessors)
	}
	if err := validateMigration("../..", m, plant); err == nil || !strings.Contains(err.Error(), "predecessor fixture source kind") {
		t.Fatalf("wrong dry-run plant refusal: %v", err)
	}
}

// The explicit availability matrix cannot lose a case, change a frozen source
// fixture, mix strict/permissive levels or relabel a present missing payload.
// These are metadata controls; no filesystem recovery is exercised here.
func TestAvailabilityCoverageControls(t *testing.T) {
	_, _, cases := fixture(t)
	if err := validateCases(cases); err != nil {
		t.Fatal(err)
	}
	for name, refusal := range map[string]string{
		"missing": "missing availability case", "source": "missing availability case",
		"level-partition":    "whole-entry availability level partition",
		"payload-as-absence": "observation violates", "permissive-recovery": "observation violates",
		"strict-rejection": "observation violates", "dry-run-write": "observation violates",
	} {
		t.Run(name, func(t *testing.T) {
			plant := append([]vector{}, cases...)
			target := "context-git-repair-strict"
			if name == "payload-as-absence" {
				target = "context-missing-payload-repair"
			}
			if name == "permissive-recovery" {
				target = "context-git-repair-permissive"
			}
			if name == "dry-run-write" {
				target = "context-git-dry-run-strict"
			}
			found := false
			for i := range plant {
				if plant[i].Name != target {
					continue
				}
				found = true
				switch name {
				case "missing":
					plant = append(plant[:i], plant[i+1:]...)
				case "source":
					plant[i].Source = "path"
					plant[i].Expected.Diagnostic = "environment_repair_failed"
					plant[i].Expected.Fragment = false
					plant[i].Expected.Current = false
					plant[i].Expected.Rebuilt = false
					plant[i].Expected.Writes = []string{}
					plant[i].Expected.Check = "regular_types"
					plant[i].Expected.PathNamed = true
					plant[i].Expected.RuleNamed = true
				case "level-partition":
					plant[i].Levels = []int{1, 2, 3, 4}
					plant[i].Expected = observation{Diagnostic: "environment_store_untrusted", Check: "regular_types", Writes: []string{}, LockUnchanged: true, PathNamed: true, RuleNamed: true}
				case "payload-as-absence":
					plant[i].Condition = "entry-absent"
				case "permissive-recovery":
					plant[i].Expected = observation{Fragment: true, Current: true, Rebuilt: true, Writes: []string{"store"}, LockUnchanged: true}
				case "strict-rejection":
					plant[i].Expected = observation{Diagnostic: "environment_store_untrusted", Check: "regular_types", Writes: []string{}, LockUnchanged: true, PathNamed: true, RuleNamed: true}
				case "dry-run-write":
					plant[i].Expected.Writes = []string{"store"}
				}
				break
			}
			if !found {
				t.Fatal("control target missing")
			}
			if err := validateCases(plant); err == nil || !strings.Contains(err.Error(), refusal) {
				t.Fatalf("wrong availability refusal: %v", err)
			}
		})
	}
}

// Current-home same-pin recovery changes only the store. The proposal model
// must accept that observation and reject redundant home/marker changes;
// stale and absent homes retain their separate required restoration writes.
// These are metadata controls, not filesystem or syscall observations.
func TestCurrentHomeRepairWriteScopes(t *testing.T) {
	_, _, cases := fixture(t)
	wanted := map[string]bool{
		"legacy-repair-rebuilds-git-entry-from-snapshot": false,
		"context-git-repair-strict":                      false,
		"mcp-git-repair-strict":                          false,
		"skill-git-repair-strict":                        false,
	}
	homeRepairs := 0
	for _, v := range cases {
		if _, ok := wanted[v.Name]; ok {
			wanted[v.Name] = true
			t.Run(v.Name, func(t *testing.T) {
				good := v.Expected
				good.Writes = []string{"store"}
				if err := checkObservation(v, good); err != nil {
					t.Errorf("current-home store-only observation refused: %v", err)
				}
				bad := good
				bad.Writes = []string{"store", "home", "marker"}
				if err := checkObservation(v, bad); err == nil || !strings.Contains(err.Error(), "observation violates") {
					t.Errorf("redundant current-home writes accepted: %v", err)
				}
			})
		}
		if v.Operation == "repair" && v.Expected.Fragment && (v.Home == "stale-old-marker" || v.Home == "unprovisioned") {
			homeRepairs++
			t.Run(v.Name, func(t *testing.T) {
				if err := checkObservation(v, v.Expected); err != nil {
					t.Fatalf("required home restoration refused: %v", err)
				}
				bad := v.Expected
				bad.Writes = []string{"store"}
				if err := checkObservation(v, bad); err == nil || !strings.Contains(err.Error(), "observation violates") {
					t.Errorf("missing home restoration writes accepted: %v", err)
				}
			})
		}
	}
	for name, found := range wanted {
		if !found {
			t.Errorf("required current-home row missing: %s", name)
		}
	}
	if homeRepairs != 4 {
		t.Errorf("home restoration controls = %d; want 4", homeRepairs)
	}
}

// Both metadata entry points refuse unreachable non-context state pins. The
// complete valid corpus and legal context/Git neighbors must still pass; these
// checks establish metadata admission, not a runtime store-repair observation.
func TestMemberSourceCompatibility(t *testing.T) {
	var admissionRefusal func(*jsonschema.ValidationError) bool
	admissionRefusal = func(e *jsonschema.ValidationError) bool {
		if strings.HasPrefix(e.KeywordLocation, "/items/anyOf") && e.InstanceLocation == "/0" {
			return true
		}
		for _, cause := range e.Causes {
			if admissionRefusal(cause) {
				return true
			}
		}
		return false
	}
	_, schema, cases := fixture(t)
	if err := validateCases(cases); err != nil {
		t.Fatal(err)
	}
	byName := map[string]vector{}
	for _, v := range cases {
		byName[v.Name] = v
	}
	for _, name := range []string{"context-path-repair-strict", "context-local-repair-strict", "mcp-git-repair-strict", "skill-git-repair-strict"} {
		t.Run("valid/"+name, func(t *testing.T) {
			v, ok := byName[name]
			if !ok {
				t.Fatal("valid source neighbor missing")
			}
			raw, err := json.Marshal([]vector{v})
			if err != nil {
				t.Fatal(err)
			}
			got, err := decodeCases(raw, schema)
			if err != nil || len(got) != 1 {
				t.Fatalf("valid member/source refused: %v", err)
			}
		})
	}
	for _, member := range []string{"mcp", "skill"} {
		for _, source := range []string{"path", "local"} {
			t.Run("forbidden/"+member+"/"+source, func(t *testing.T) {
				v, ok := byName[member+"-git-repair-strict"]
				if !ok {
					t.Fatal("Git source neighbor missing")
				}
				v.Name = "reintroduced-" + member + "-" + source
				v.Source = source
				v.Expected = byName["context-path-repair-strict"].Expected
				raw, err := json.Marshal([]vector{v})
				if err != nil {
					t.Fatal(err)
				}
				got, err := decodeCases(raw, schema)
				var schemaErr *jsonschema.ValidationError
				if err == nil || got != nil || !strings.Contains(err.Error(), unsupported) || !errors.As(err, &schemaErr) || !admissionRefusal(schemaErr) {
					t.Errorf("closed reader missed member/source admission: %v", err)
				}
				plant := append(append([]vector{}, cases...), v)
				if err := validateCases(plant); err == nil || !strings.Contains(err.Error(), "member/source admission") {
					t.Errorf("corpus checker missed member/source plant: %v", err)
				}
			})
		}
	}
}

// The policy fixtures distinguish both permissive boundaries, order-independent
// mismatch aggregation, centre fallback/denial, default3 and a monotone floor.
// Narrowing or broadening each verdict is detected beside the complete positive.
func TestPolicyBoundaryControls(t *testing.T) {
	_, _, cases := fixture(t)
	if err := validateCases(cases); err != nil {
		t.Fatal(err)
	}
	for _, v := range cases {
		if v.Condition != "verification-policy" {
			continue
		}
		t.Run(v.Name, func(t *testing.T) {
			if err := checkObservation(v, v.Expected); err != nil {
				t.Fatal(err)
			}
			bad := v.Expected
			bad.Fragment = !bad.Fragment
			if err := checkObservation(v, bad); err == nil || !strings.Contains(err.Error(), "observation violates") {
				t.Fatalf("changed verdict accepted: %v", err)
			}
			if v.Expected.Warning {
				bad = v.Expected
				bad.Warning = false
				if err := checkObservation(v, bad); err == nil {
					t.Fatal("missing warning accepted")
				}
			}
		})
	}
	for _, name := range []string{"policy-level1-pass", "policy-level2-unavailable", "policy-level3-unavailable", "policy-centre-unreachable", "policy-floor-weakening"} {
		plant := append([]vector{}, cases...)
		for i, v := range plant {
			if v.Name == name {
				plant = append(plant[:i], plant[i+1:]...)
				break
			}
		}
		if err := validateCases(plant); err == nil || !(strings.Contains(err.Error(), "missing policy case") || (name == "policy-level1-pass" && strings.Contains(err.Error(), "invalid positive neighbor"))) {
			t.Fatalf("missing boundary %s: %v", name, err)
		}
	}
}

// Home currency/hint and repair are mandatory at all levels; level1 pin drift
// cannot silently rewrite evidence. The scope manifest exposes low-level rows.
func TestHomeAndLevelScopeControls(t *testing.T) {
	_, _, cases := fixture(t)
	raw, err := os.ReadFile(filepath.Join("../..", namespace, "manifest.json"))
	if err != nil {
		t.Fatal(err)
	}
	var m manifest
	if err := strict(raw, &m); err != nil {
		t.Fatal(err)
	}
	if err := validateMigration("../..", m, cases); err != nil {
		t.Fatal(err)
	}
	for _, v := range cases {
		if v.Expected.Diagnostic == "environment_home_stale" {
			if err := checkObservation(v, v.Expected); err != nil {
				t.Fatal(err)
			}
			bad := v.Expected
			bad.RepairHint = false
			if err := checkObservation(v, bad); err == nil {
				t.Fatalf("%s lost repair hint", v.Name)
			}
			if v.Condition == "home-stale" {
				bad = v.Expected
				bad.Check = ""
				if err := checkObservation(v, bad); err == nil {
					t.Fatalf("%s lost home_currency", v.Name)
				}
			}
		}
		if v.Condition == "pin-drift" && len(v.Levels) == 1 && v.Levels[0] == 1 {
			bad := v.Expected
			bad.Writes = []string{"store"}
			bad.Rebuilt = true
			if err := checkObservation(v, bad); err == nil {
				t.Fatalf("%s rewrote evidence", v.Name)
			}
		}
	}
	for i, row := range m.Migration {
		if len(row.LevelSuccessors) == 0 {
			continue
		}
		plant := m
		plant.Migration = append([]migration{}, m.Migration...)
		plant.Migration[i].LevelSuccessors = nil
		if err := validateMigration("../..", plant, cases); err == nil || !strings.Contains(err.Error(), "missing level successors") {
			t.Fatalf("hidden low-level scope: %v", err)
		}
		plant = m
		plant.Migration = append([]migration{}, m.Migration...)
		plant.Migration[i].Disposition = "retained"
		if err := validateMigration("../..", plant, cases); err == nil || !strings.Contains(err.Error(), "wrong disposition") {
			t.Fatalf("unscoped disposition: %v", err)
		}
		break
	}
}

// First failing lock member chooses the path and skill-only class; later
// failures cannot take over. Absent path/local dry-run is repair_failed, not a
// rebuild plan. These bounded model checks do not exercise manager syscalls.
func TestPrecedenceAndAbsentDryRunControls(t *testing.T) {
	_, _, cases := fixture(t)
	for _, v := range cases {
		if v.Condition != "multiple-structural" && v.Name != "context-path-dry-run-strict" && v.Name != "context-local-dry-run-strict" {
			continue
		}
		t.Run(v.Name, func(t *testing.T) {
			if err := checkObservation(v, v.Expected); err != nil {
				t.Fatal(err)
			}
			bad := v.Expected
			if v.Condition == "multiple-structural" {
				bad.Path = v.Failures[1].Path
			} else {
				bad.Diagnostic = "would-rebuild-untrusted-store"
			}
			if err := checkObservation(v, bad); err == nil || !strings.Contains(err.Error(), "observation violates") {
				t.Fatalf("wrong primary accepted: %v", err)
			}
			if v.Condition == "multiple-structural" {
				bad = v.Expected
				if bad.Diagnostic == "skill_integrity_boundary_invalid" {
					bad.Diagnostic = "environment_store_untrusted"
				} else {
					bad.Diagnostic = "skill_integrity_boundary_invalid"
				}
				if err := checkObservation(v, bad); err == nil {
					t.Fatal("wrong skill class accepted")
				}
			}
		})
	}
	for _, target := range []string{"precedence-context-first", "context-path-dry-run-strict", "context-local-dry-run-strict"} {
		plant := append([]vector{}, cases...)
		for i, v := range plant {
			if v.Name == target {
				plant = append(plant[:i], plant[i+1:]...)
				break
			}
		}
		if err := validateCases(plant); err == nil {
			t.Fatalf("missing fixture accepted: %s", target)
		}
	}
}

// Policy fixture metadata cannot hide a drifted home behind a permissive
// verdict, and all-level home gates cannot be narrowed to strict-only coverage.
func TestFixtureScopeAndHomeCoverage(t *testing.T) {
	_, _, cases := fixture(t)
	if err := validateCases(cases); err != nil {
		t.Fatal(err)
	}
	for _, plantKind := range []string{"policy-home", "home-levels", "pin-levels", "fixture-kind"} {
		t.Run(plantKind, func(t *testing.T) {
			plant := append([]vector{}, cases...)
			target, refusal := "policy-level1-pass", "policy fixture scope"
			if plantKind == "home-levels" {
				target = "legacy-intact-updated-store-old-marker-stale"
				refusal = "missing home gate level"
			}
			if plantKind == "pin-levels" {
				target = "legacy-swapped-system-prompt-bytes-untrusted"
				refusal = "pin verdict level partition"
			}
			if plantKind == "fixture-kind" {
				refusal = "fixture discriminator"
			}
			found := false
			for i, v := range plant {
				if v.Name == target {
					found = true
					switch plantKind {
					case "policy-home":
						plant[i].Home = "stale-old-marker"
					case "home-levels":
						plant[i].Levels = []int{3, 4}
					case "pin-levels":
						plant[i].Levels = []int{2, 3, 4}
					case "fixture-kind":
						plant[i].Condition = "intact"
						plant[i].Levels = []int{1, 2, 3, 4}
					}
					break
				}
			}
			if !found {
				t.Fatal("control target missing")
			}
			if err := validateCases(plant); err == nil || !strings.Contains(err.Error(), refusal) {
				t.Fatalf("wrong scope/coverage refusal: %v", err)
			}
		})
	}
}
