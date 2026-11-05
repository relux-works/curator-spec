package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"strconv"
	"strings"
	"testing"
)

func root() string { return filepath.Join("..", "..") }

// Proves the published schemas and semantic reasons satisfy every frozen input;
// no native runtime, settings, filesystem mutation or child execution is tested.
func TestPublishedCorpus(t *testing.T) {
	var output bytes.Buffer
	if code := run(root(), &output); code != 0 {
		t.Fatalf("corpus failed (exit %d):\n%s", code, output.String())
	}
}

// Proves the independently specified inclusive range for every admitted integer,
// and rejects neighboring out-of-range values; this does not prove native effect.
func TestRangeAndCanonicalSpelling(t *testing.T) {
	compiled, err := schemas(root())
	if err != nil {
		t.Fatal("schema setup failed")
	}
	for n := 1; n <= 65536; n++ {
		raw := `{"BASH_MAX_OUTPUT_LENGTH":"` + strconv.Itoa(n) + `"}`
		if semantic("declaration", raw) != "accept" || !schemaAccepts(compiled["declaration"], raw) {
			t.Fatalf("admitted integer rejected at range position %d", n)
		}
	}
	for _, s := range []string{"0", "-1", "-0", "65537", "65538", "99999", strings.Repeat("9", 200)} {
		b, _ := json.Marshal(map[string]string{setting: s})
		if semantic("declaration", string(b)) == "accept" || schemaAccepts(compiled["declaration"], string(b)) {
			t.Fatal("out-of-range control admitted")
		}
	}
	for _, s := range []string{"", "01", "+1", " 1", "1 ", "1.0", "1e3", "١", "1\n"} {
		b, _ := json.Marshal(map[string]string{setting: s})
		if got := semantic("declaration", string(b)); got != "claude_env_value_not_integer" {
			t.Fatalf("lexical control gave wrong reason: %s", got)
		}
		if schemaAccepts(compiled["declaration"], string(b)) {
			t.Fatal("noncanonical string accepted by schema")
		}
	}
}

func changedLeaves(a, b any) int {
	am, aOK := a.(map[string]any)
	bm, bOK := b.(map[string]any)
	if !aOK || !bOK {
		if reflect.DeepEqual(a, b) {
			return 0
		}
		return 1
	}
	keys := map[string]bool{}
	for k := range am {
		keys[k] = true
	}
	for k := range bm {
		keys[k] = true
	}
	n := 0
	for k := range keys {
		av, aPresent := am[k]
		bv, bPresent := bm[k]
		if aPresent != bPresent {
			n++
		} else {
			n += changedLeaves(av, bv)
		}
	}
	return n
}

// Proves six executable defect plants each change one leaf from a valid control
// and reach their required rejection, rather than any error or setup failure.
func TestSingleDefectPlants(t *testing.T) {
	b, err := os.ReadFile(filepath.Join(root(), "conformance", "machine-claude-env-v1", "plants.json"))
	if err != nil {
		t.Fatal("plant corpus unavailable")
	}
	var plants []plant
	if json.Unmarshal(b, &plants) != nil || len(plants) != 6 {
		t.Fatal("six plants required")
	}
	seen := map[string]bool{}
	for _, p := range plants {
		t.Run(p.ID, func(t *testing.T) {
			if seen[p.ID] {
				t.Fatal("duplicate plant")
			}
			seen[p.ID] = true
			good, errA := decodeStrict(p.Valid)
			bad, errB := decodeStrict(p.Invalid)
			if errA != nil || errB != nil || changedLeaves(good, bad) != 1 {
				t.Fatal("plant is not a single valid-JSON leaf change")
			}
			if semantic(p.Entry, p.Valid) != "accept" || semantic(p.Entry, p.Invalid) != p.Want || p.Want == "accept" {
				t.Fatal("positive control or intended rejection failed")
			}
		})
	}
	for _, name := range []string{"unknown-name", "non-integer", "zero", "negative", "over-bound", "non-claude"} {
		if !seen[name] {
			t.Fatalf("required plant missing: %s", name)
		}
	}
}

// Proves the checker detects falsely expected acceptance and rejection, still
// runs a later case, and emits no input value; production redaction is separate.
func TestCheckerControlsAndRedaction(t *testing.T) {
	compiled, err := schemas(root())
	if err != nil {
		t.Fatal("schema setup failed")
	}
	const marker = "SYNTHETIC_VALUE_MUST_NOT_APPEAR"
	cases := []vector{
		{"false-accept", "An unknown name must refuse", "declaration", `{"UNKNOWN":"` + marker + `"}`, "accept", true},
		{"false-reject", "A canonical positive must pass", "declaration", `{"BASH_MAX_OUTPUT_LENGTH":"8000"}`, "claude_env_value_over_bound", false},
		{"later-valid", "Later cases still run", "declaration", `{}`, "accept", true},
	}
	var output bytes.Buffer
	if failures := check(&output, compiled, cases); failures != 2 {
		t.Fatalf("wrong failed-control count: %d", failures)
	}
	text := output.String()
	if !strings.Contains(text, "PASS later-valid") || !strings.Contains(text, "actual=claude_env_name_not_allowed") || !strings.Contains(text, "actual=accept") {
		t.Fatal("intended checker detections or later case absent")
	}
	if strings.Contains(text, marker) || strings.Contains(text, "8000") || strings.Contains(text, "UNKNOWN") {
		t.Fatal("checker exposed an input value or unknown name")
	}
}

// Proves each known violation fails the command's actual aggregate path when
// planted as an expected acceptance; a later positive still executes.
func TestCommandFailureControls(t *testing.T) {
	b, err := os.ReadFile(filepath.Join(root(), "conformance", "machine-claude-env-v1", "plants.json"))
	if err != nil {
		t.Fatal("plant corpus unavailable")
	}
	var plants []plant
	if json.Unmarshal(b, &plants) != nil {
		t.Fatal("invalid plant corpus")
	}
	for _, p := range plants {
		t.Run(p.ID, func(t *testing.T) {
			fixture := t.TempDir()
			for _, name := range []string{
				"schemas/machine-claude-env-v1/claude-env.schema.json",
				"schemas/machine-claude-env-v1/projection.schema.json",
				"conformance/machine-claude-env-v1/plants.json",
			} {
				data, err := os.ReadFile(filepath.Join(root(), name))
				if err != nil || os.MkdirAll(filepath.Dir(filepath.Join(fixture, name)), 0700) != nil || os.WriteFile(filepath.Join(fixture, name), data, 0600) != nil {
					t.Fatal("isolated control fixture setup failed")
				}
			}
			cases := []vector{
				{"known-violation", p.Claim, p.Entry, p.Invalid, "accept", true},
				{"later-positive", p.Claim, p.Entry, p.Valid, "accept", true},
			}
			data, err := json.Marshal(cases)
			if err != nil || os.WriteFile(filepath.Join(fixture, "conformance", "machine-claude-env-v1", "cases.json"), data, 0600) != nil {
				t.Fatal("control corpus setup failed")
			}
			var output bytes.Buffer
			if code := run(fixture, &output); code != 1 {
				t.Fatalf("expected semantic mismatch exit1, got%d", code)
			}
			if !strings.Contains(output.String(), "FAIL known-violation expected=accept actual="+p.Want) || !strings.Contains(output.String(), "PASS later-positive") || !strings.Contains(output.String(), "failures=1 runtime-cases=0") {
				t.Fatal("intended rejection, aggregate failure or later positive missing")
			}
		})
	}
}

// Proves malformed, trailing and duplicate input is a fixed refusal without a
// parser's reflected payload; JSON Schema alone cannot detect duplicate keys.
func TestStrictDecoder(t *testing.T) {
	for _, input := range []string{
		`{"BASH_MAX_OUTPUT_LENGTH":"1","BASH_MAX_OUTPUT_LENGTH":"2"}`,
		`{"runtime":"claude_code","env":{"BASH_MAX_OUTPUT_LENGTH":"1","BASH_MAX_OUTPUT_LENGTH":"2"}}`,
		`{"BASH_MAX_OUTPUT_LENGTH":"1"} {}`,
		`{"BASH_MAX_OUTPUT_LENGTH":`,
	} {
		if got := semantic("declaration", input); got != "claude_env_invalid" {
			t.Fatalf("strict input gave wrong reason: %s", got)
		}
	}
}
