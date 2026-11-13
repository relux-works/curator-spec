// Command check-store-verification-v2 checks proposal metadata and counterexamples.
// It does not execute a manager or qualify filesystem or launcher behavior.
package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"reflect"
	"unicode/utf8"

	"github.com/santhosh-tekuri/jsonschema/v5"
)

const namespace = "conformance/environment-store-verification-v2"
const predecessorPath = "conformance/v1/vectors/environments-store-boundary.json"
const predecessorHash = "7efa5b09e450162cfb2937f25b3e29fab4699602e0990cfd295a4f695cb60413"
const unsupported = "store_verification_corpus_unsupported"

type observation struct {
	Diagnostic     string   `json:"diagnostic"`
	Check          string   `json:"failing_check"`
	Fragment       bool     `json:"fragment_emitted"`
	Current        bool     `json:"row_current"`
	Writes         []string `json:"writes"`
	Rebuilt        bool     `json:"store_rebuilt"`
	LockUnchanged  bool     `json:"lock_unchanged"`
	PlantPreserved bool     `json:"plant_preserved"`
	PathNamed      bool     `json:"path_named"`
	RuleNamed      bool     `json:"rule_named"`
}
type predecessor struct {
	Group string `json:"group"`
	Name  string `json:"name"`
}
type vector struct {
	Schema      string       `json:"schema"`
	Capability  string       `json:"capability"`
	Revision    int          `json:"capability_revision"`
	Name        string       `json:"name"`
	Kind        string       `json:"case_kind"`
	Operation   string       `json:"operation"`
	Condition   string       `json:"condition"`
	Member      string       `json:"member_kind"`
	Source      string       `json:"source_kind"`
	Home        string       `json:"home_state"`
	Levels      []int        `json:"verification_levels"`
	Expected    observation  `json:"expected"`
	Positive    string       `json:"positive_control"`
	Predecessor *predecessor `json:"predecessor"`
	Forbidden   []struct {
		Name        string      `json:"name"`
		Observation observation `json:"observation"`
	} `json:"forbidden_observations"`
}
type migration struct {
	Group         string  `json:"group"`
	Name          string  `json:"name"`
	Disposition   string  `json:"disposition"`
	OldDiagnostic *string `json:"old_diagnostic"`
	OldOutcome    *string `json:"old_outcome"`
	NewDiagnostic *string `json:"new_required_diagnostic"`
	Successor     string  `json:"successor_case"`
	Negative      bool    `json:"known_bad_remains_negative"`
}
type manifest struct {
	Schema      string `json:"schema"`
	Capability  string `json:"capability"`
	Revision    int    `json:"capability_revision"`
	Status      string `json:"status"`
	Cases       string `json:"cases"`
	Count       int    `json:"case_count"`
	Predecessor struct {
		Commit string `json:"commit"`
		Path   string `json:"path"`
		SHA256 string `json:"sha256"`
	} `json:"predecessor"`
	Migration []migration `json:"migration"`
}

// walk rejects duplicate decoded keys before a schema or typed reader sees them.
func walk(d *json.Decoder, depth int) error {
	if depth > 32 {
		return errors.New("JSON depth")
	}
	t, err := d.Token()
	if err != nil {
		return err
	}
	switch t {
	case json.Delim('{'):
		seen := map[string]bool{}
		for d.More() {
			k, err := d.Token()
			if err != nil {
				return err
			}
			s, ok := k.(string)
			if !ok || seen[s] {
				return errors.New("duplicate JSON key")
			}
			seen[s] = true
			if err := walk(d, depth+1); err != nil {
				return err
			}
		}
		_, err = d.Token()
	case json.Delim('['):
		for d.More() {
			if err := walk(d, depth+1); err != nil {
				return err
			}
		}
		_, err = d.Token()
	}
	return err
}
func strict(raw []byte, out any) error {
	if len(raw) > 4<<20 || !utf8.Valid(raw) {
		return errors.New("invalid JSON bytes")
	}
	d := json.NewDecoder(bytes.NewReader(raw))
	d.UseNumber()
	if err := walk(d, 0); err != nil {
		return err
	}
	if _, err := d.Token(); err != io.EOF {
		return errors.New("trailing JSON")
	}
	d = json.NewDecoder(bytes.NewReader(raw))
	d.DisallowUnknownFields()
	return d.Decode(out)
}
func decodeCases(raw []byte, schema *jsonschema.Schema) ([]vector, error) {
	bad := func(err error) ([]vector, error) { return nil, fmt.Errorf("%s: %w", unsupported, err) }
	var generic any
	if err := strict(raw, &generic); err != nil {
		return bad(err)
	}
	if err := schema.Validate(generic); err != nil {
		return bad(err)
	}
	var cases []vector
	if err := strict(raw, &cases); err != nil {
		return bad(err)
	}
	return cases, nil
}
func structural(condition string) string {
	switch condition {
	case "ownership", "permissions", "containment":
		return condition
	case "symlink":
		return "link_safety"
	case "hardlink":
		return "single_link"
	case "special":
		return "regular_types"
	}
	return ""
}

// checkObservation compares a supplied observation to the normative bounded model.
// It does not produce observations from filesystem operations.
func checkObservation(v vector, got observation) error {
	want := observation{Writes: []string{}, LockUnchanged: true}
	if check := structural(v.Condition); check != "" {
		want.Diagnostic, want.Check = "environment_store_untrusted", check
		if v.Member == "skill" && v.Condition == "hardlink" {
			want.Diagnostic = "skill_integrity_boundary_invalid"
		}
		want.PlantPreserved, want.PathNamed, want.RuleNamed = true, true, true
	} else {
		switch v.Condition {
		case "intact":
			want.Current = true
			want.Fragment = v.Operation != "status"
		case "pin-drift":
			if v.Operation == "repair" && v.Source == "git" {
				want.Fragment, want.Current, want.Rebuilt = true, true, true
				want.Writes = []string{"store", "home", "marker"}
			} else {
				want.Diagnostic, want.Check = "environment_store_untrusted", "pin_hash"
			}
		case "home-stale", "home-absent":
			if v.Operation == "repair" {
				want.Fragment, want.Current = true, true
				want.Writes = []string{"home", "marker"}
			} else {
				want.Diagnostic = "environment_home_stale"
			}
		case "marker-unreadable":
			want.Diagnostic = "environment_marker_unreadable"
		default:
			return errors.New("unknown condition")
		}
	}
	if !reflect.DeepEqual(got, want) {
		return errors.New("observation violates required diagnostic or post-state")
	}
	return nil
}
func validateCases(cases []vector) error {
	byName := map[string]vector{}
	for _, v := range cases {
		if _, ok := byName[v.Name]; ok {
			return fmt.Errorf("duplicate case %s", v.Name)
		}
		byName[v.Name] = v
		if err := checkObservation(v, v.Expected); err != nil {
			return fmt.Errorf("%s: %w", v.Name, err)
		}
		if structural(v.Condition) != "" && !reflect.DeepEqual(v.Levels, []int{1, 2, 3, 4}) {
			return fmt.Errorf("%s: missing fatal level", v.Name)
		}
		if v.Condition != "intact" && structural(v.Condition) == "" && !reflect.DeepEqual(v.Levels, []int{3, 4}) {
			return fmt.Errorf("%s: strict fixture level", v.Name)
		}
		for _, f := range v.Forbidden {
			if checkObservation(v, f.Observation) == nil {
				return fmt.Errorf("%s: undetected control %s", v.Name, f.Name)
			}
		}
	}
	for _, v := range cases {
		p, ok := byName[v.Positive]
		if !ok || p.Kind != "implementation" || p.Condition != "intact" || p.Operation != v.Operation || p.Member != v.Member {
			return fmt.Errorf("%s: invalid positive neighbor", v.Name)
		}
	}
	for _, member := range []string{"context", "mcp", "skill"} {
		for _, condition := range []string{"ownership", "permissions", "containment", "symlink", "hardlink", "special"} {
			for _, op := range []string{"resolve", "repair", "dry-run"} {
				name := member + "-" + condition + "-" + op + "-fatal-all-levels"
				v, ok := byName[name]
				if !ok || v.Kind != "implementation" || v.Condition != condition || v.Operation != op || v.Member != member {
					return fmt.Errorf("missing matrix case %s", name)
				}
			}
		}
	}
	return nil
}
func validateMigration(root string, m manifest, cases []vector) error {
	if m.Schema != "curator.environment-store-corpus/2" || m.Capability != "agent-environments" || m.Revision != 2 || m.Status != "proposal-unreleased" || m.Cases != "vectors/environments-store-boundary.json" || m.Count != len(cases) {
		return errors.New("manifest version or count")
	}
	if m.Predecessor.Commit != "43bf0a2506d5c354a73bbc3ea4623d4653db10c7" || m.Predecessor.Path != predecessorPath || m.Predecessor.SHA256 != predecessorHash {
		return errors.New("predecessor identity")
	}
	raw, err := os.ReadFile(filepath.Join(root, predecessorPath))
	if err != nil {
		return err
	}
	h := sha256.Sum256(raw)
	if hex.EncodeToString(h[:]) != predecessorHash {
		return errors.New("predecessor bytes changed")
	}
	var old map[string]json.RawMessage
	if err := json.Unmarshal(raw, &old); err != nil {
		return err
	}
	byName := map[string]vector{}
	for _, v := range cases {
		byName[v.Name] = v
	}
	byOld := map[string]migration{}
	for _, row := range m.Migration {
		key := row.Group + "/" + row.Name
		if _, ok := byOld[key]; ok {
			return errors.New("duplicate migration")
		}
		byOld[key] = row
	}
	tightened := map[string]bool{"dry-run-untrusted-reports-would-rebuild": true, "dry-run-mutates": true, "repair-path-entry-cannot-rebuild": true, "repair-local-entry-cannot-rebuild": true, "repair-rebuilds-entry-boundary-failure": true, "repair-reapplies-untrusted": true}
	count := 0
	for _, group := range []string{"resolve_cases", "repair_cases", "dry_run_cases", "status_cases"} {
		var rows []struct {
			Name         string  `json:"name"`
			Diagnostic   *string `json:"diagnostic"`
			Outcome      *string `json:"outcome"`
			Conforming   *bool   `json:"conforming"`
			Home         string  `json:"home"`
			EntryKind    string  `json:"entry_kind"`
			Ownership    bool    `json:"ownership"`
			Permissions  bool    `json:"permissions"`
			Containment  bool    `json:"containment"`
			RegularTypes bool    `json:"regular_types"`
			LinkSafety   bool    `json:"link_safety"`
			PinHash      bool    `json:"pin_hash_match"`
		}
		if err := json.Unmarshal(old[group], &rows); err != nil {
			return err
		}
		for _, old := range rows {
			count++
			row, ok := byOld[group+"/"+old.Name]
			if !ok {
				return fmt.Errorf("missing migration %s", old.Name)
			}
			v, ok := byName[row.Successor]
			if !ok || v.Predecessor == nil || *v.Predecessor != (predecessor{group, old.Name}) {
				return fmt.Errorf("wrong successor %s", old.Name)
			}
			condition := "intact"
			switch {
			case !old.Ownership:
				condition = "ownership"
			case !old.Permissions:
				condition = "permissions"
			case !old.Containment:
				condition = "containment"
			case !old.RegularTypes:
				condition = "special"
			case !old.LinkSafety:
				condition = "symlink"
			case !old.PinHash:
				condition = "pin-drift"
			case old.Home == "stale-old-marker":
				condition = "home-stale"
			case old.Home == "unprovisioned":
				condition = "home-absent"
			case old.Home == "unreadable-marker":
				condition = "marker-unreadable"
			}
			source := old.EntryKind
			if source == "" {
				// Released Resolve/status drivers pass gitRoot=false
				// to storeBoundaryFixture: their root is KindPath/StateHash.
				// Dry-run passes true; repair uses explicit entry_kind.
				source = "path"
				if group == "dry_run_cases" {
					source = "git"
				}
			}
			if v.Source != source {
				return fmt.Errorf("predecessor fixture source kind %s: got %s, want %s", old.Name, v.Source, source)
			}
			operation := map[string]string{"resolve_cases": "resolve", "dry_run_cases": "dry-run", "repair_cases": "repair", "status_cases": "status"}[group]
			if row.Successor != "legacy-"+old.Name || v.Condition != condition || v.Source != source || v.Home != old.Home || v.Operation != operation {
				return fmt.Errorf("changed predecessor plant %s", old.Name)
			}
			negative := old.Conforming != nil && !*old.Conforming
			disposition := "retained"
			if tightened[old.Name] {
				disposition = "tightened"
			}
			if negative {
				disposition += "-negative-control"
			}
			if row.Disposition != disposition || row.Negative != negative || (v.Kind == "checker-control") != negative || !reflect.DeepEqual(row.OldDiagnostic, old.Diagnostic) || !reflect.DeepEqual(row.OldOutcome, old.Outcome) {
				return fmt.Errorf("wrong disposition %s", old.Name)
			}
			wantDiag := ""
			if row.NewDiagnostic != nil {
				wantDiag = *row.NewDiagnostic
			}
			if wantDiag != v.Expected.Diagnostic {
				return fmt.Errorf("wrong successor diagnostic %s", old.Name)
			}
		}
	}
	if count != 38 || len(m.Migration) != count {
		return errors.New("migration coverage")
	}
	return nil
}
func check(root string) error {
	schema, err := jsonschema.Compile(filepath.Join(root, namespace, "cases.schema.json"))
	if err != nil {
		return err
	}
	raw, err := os.ReadFile(filepath.Join(root, namespace, "vectors/environments-store-boundary.json"))
	if err != nil {
		return err
	}
	cases, err := decodeCases(raw, schema)
	if err != nil {
		return err
	}
	if err := validateCases(cases); err != nil {
		return err
	}
	raw, err = os.ReadFile(filepath.Join(root, namespace, "manifest.json"))
	if err != nil {
		return err
	}
	manifestSchema, err := jsonschema.Compile(filepath.Join(root, namespace, "manifest.schema.json"))
	if err != nil {
		return err
	}
	var generic any
	if err := strict(raw, &generic); err != nil {
		return err
	}
	if err := manifestSchema.Validate(generic); err != nil {
		return err
	}
	var m manifest
	if err := strict(raw, &m); err != nil {
		return err
	}
	return validateMigration(root, m, cases)
}
func main() {
	root := flag.String("root", ".", "specification checkout root")
	flag.Parse()
	if err := check(*root); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	fmt.Println("environment-store revision-2 proposal metadata and controls: PASS (not runtime qualification)")
}
