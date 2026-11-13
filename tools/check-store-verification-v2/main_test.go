package main

import (
	"bytes"
	"encoding/json"
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
				plant[len(plant)-1].Levels = []int{1, 2, 3}
			case "matrix":
				plant = plant[:len(plant)-1]
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
