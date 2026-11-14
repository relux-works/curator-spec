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

type policyFixture struct {
	Global   *int     `json:"global_level,omitempty"`
	Minimums []int    `json:"profile_minimums"`
	Evidence []string `json:"local_evidence"`
	Centre   string   `json:"centre"`
}
type structuralFailure struct {
	Member    string `json:"member_kind"`
	Condition string `json:"condition"`
	Path      string `json:"path"`
}
type observation struct {
	RepairHint     bool     `json:"repair_hint,omitempty"`
	Warning        bool     `json:"warning_emitted,omitempty"`
	Path           string   `json:"offending_path,omitempty"`
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
	Policy      *policyFixture      `json:"policy,omitempty"`
	Failures    []structuralFailure `json:"structural_failures,omitempty"`
	Schema      string              `json:"schema"`
	Capability  string              `json:"capability"`
	Revision    int                 `json:"capability_revision"`
	Name        string              `json:"name"`
	Kind        string              `json:"case_kind"`
	Operation   string              `json:"operation"`
	Condition   string              `json:"condition"`
	Member      string              `json:"member_kind"`
	Source      string              `json:"source_kind"`
	Home        string              `json:"home_state"`
	Levels      []int               `json:"verification_levels"`
	Expected    observation         `json:"expected"`
	Positive    string              `json:"positive_control"`
	Predecessor *predecessor        `json:"predecessor"`
	Forbidden   []struct {
		Name        string      `json:"name"`
		Observation observation `json:"observation"`
	} `json:"forbidden_observations"`
}
type migration struct {
	Levels          []int    `json:"verification_levels"`
	LevelSuccessors []string `json:"level_successors"`
	Group           string   `json:"group"`
	Name            string   `json:"name"`
	Disposition     string   `json:"disposition"`
	OldDiagnostic   *string  `json:"old_diagnostic"`
	OldOutcome      *string  `json:"old_outcome"`
	NewDiagnostic   *string  `json:"new_required_diagnostic"`
	Successor       string   `json:"successor_case"`
	Negative        bool     `json:"known_bad_remains_negative"`
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
	case "special", "payload-absent":
		return "regular_types"
	}
	return ""
}

// policyObservation aggregates all local evidence; unavailable never masks mismatch.
// The bounded corpus models decisions, not centre transport or signed configuration.
func policyObservation(v vector) (observation, error) {
	want := observation{Writes: []string{}, LockUnchanged: true}
	p := v.Policy
	if p == nil || len(p.Evidence) == 0 {
		return want, errors.New("missing policy fixture")
	}
	global := 3
	if p.Global != nil {
		global = *p.Global
	}
	if global < 1 || global > 4 {
		return want, errors.New("invalid policy level")
	}
	level, weakening := global, false
	for _, n := range p.Minimums {
		if n < 1 || n > 4 {
			return want, errors.New("invalid profile level")
		}
		weakening = weakening || n < global
		if n > level {
			level = n
		}
	}
	if !reflect.DeepEqual(v.Levels, []int{level}) {
		return want, errors.New("effective policy level")
	}
	if weakening {
		want.Diagnostic = "startup_verification_weakening"
		return want, nil
	}
	mismatch, unavailable := false, false
	for _, e := range p.Evidence {
		switch e {
		case "pass":
		case "mismatch":
			mismatch = true
		case "unavailable":
			unavailable = true
		default:
			return want, errors.New("invalid local evidence")
		}
	}
	switch p.Centre {
	case "confirmed", "unreachable", "denied", "invalid":
	default:
		return want, errors.New("invalid centre outcome")
	}
	switch {
	case level == 1:
		want.Fragment = true
		want.Current = !mismatch && !unavailable
		want.Warning = mismatch || unavailable
	case mismatch:
		want.Diagnostic = "startup_verification_failed"
	case unavailable && level >= 3:
		want.Diagnostic = "startup_verification_unavailable"
	case level == 2:
		want.Fragment = true
		want.Current = !unavailable
		want.Warning = unavailable
	case level == 4 && (p.Centre == "denied" || p.Centre == "invalid"):
		want.Diagnostic = "verification_centre_" + p.Centre
	default:
		want.Fragment = true
		want.Warning = level == 4 && p.Centre == "unreachable"
		want.Current = true
	}
	return want, nil
}

// checkObservation compares a supplied observation to the normative bounded model.
// It does not produce observations from filesystem operations.
func checkObservation(v vector, got observation) error {
	want := observation{Writes: []string{}, LockUnchanged: true}
	condition, member := v.Condition, v.Member
	if condition == "multiple-structural" {
		if len(v.Failures) < 2 {
			return errors.New("missing ordered structural failures")
		}
		first := v.Failures[0]
		condition, member = first.Condition, first.Member
		want.Path = first.Path
		for _, f := range v.Failures {
			if structural(f.Condition) == "" || f.Path == "" || (f.Member != "context" && f.Member != "mcp" && f.Member != "skill") {
				return errors.New("invalid ordered structural failure")
			}
		}
	}
	if check := structural(condition); check != "" {
		want.Diagnostic, want.Check = "environment_store_untrusted", check
		if member == "skill" && condition == "hardlink" {
			want.Diagnostic = "skill_integrity_boundary_invalid"
		}
		want.PlantPreserved, want.PathNamed, want.RuleNamed = true, true, true
	} else {
		switch v.Condition {
		case "verification-policy":
			var err error
			want, err = policyObservation(v)
			if err != nil {
				return err
			}
		case "entry-absent":
			strict := reflect.DeepEqual(v.Levels, []int{3, 4})
			want.Diagnostic, want.Check = "environment_store_untrusted", "regular_types"
			want.PathNamed, want.RuleNamed = true, true
			if strict && v.Operation == "repair" && v.Source == "git" {
				want = observation{Fragment: true, Current: true, Rebuilt: true, Writes: []string{"store", "home", "marker"}, LockUnchanged: true}
				if v.Home == "current" {
					want.Writes = []string{"store"}
				}
			} else if strict && v.Operation == "repair" {
				want.Diagnostic = "environment_repair_failed"
			} else if strict && v.Operation == "dry-run" {
				want.Diagnostic = "environment_repair_failed"
				if v.Source == "git" {
					want.Diagnostic = "would-rebuild-untrusted-store"
				}
			}
		case "intact":
			want.Current = true
			want.Fragment = v.Operation != "status"
		case "pin-drift":
			level := v.Levels[0]
			if v.Home != "current" && (v.Operation != "repair" || level < 3) {
				want.Diagnostic = "environment_home_stale"
				if v.Home == "stale-old-marker" {
					want.Check = "home_currency"
				}
			} else if level == 1 {
				want.Fragment = v.Operation != "status"
				want.Warning = true
			} else if v.Operation == "repair" && v.Source == "git" && level >= 3 {
				want.Fragment, want.Current, want.Rebuilt = true, true, true
				want.Writes = []string{"store", "home", "marker"}
				if v.Home == "current" {
					want.Writes = []string{"store"}
				}
			} else {
				want.Diagnostic, want.Check = "environment_store_untrusted", "pin_hash"
			}
		case "home-stale", "home-absent":
			if v.Operation == "repair" {
				want.Fragment, want.Current = true, true
				want.Writes = []string{"home", "marker"}
			} else {
				want.Diagnostic = "environment_home_stale"
				if v.Condition == "home-stale" {
					want.Check = "home_currency"
				}
			}
		case "marker-unreadable":
			want.Diagnostic = "environment_marker_unreadable"
		default:
			return errors.New("unknown condition")
		}
	}
	if want.Diagnostic == "environment_home_stale" {
		want.RepairHint = true
		// Level1 may start with a drifted existing home only without --repair.
		// An absent home is still a missing required input; repair requires verified inputs.
		if v.Operation == "resolve" && v.Home == "stale-old-marker" && reflect.DeepEqual(v.Levels, []int{1}) {
			want.Fragment, want.Warning = true, true
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
		admitted := v.Member == "context" && (v.Source == "git" || v.Source == "path" || v.Source == "local") || (v.Member == "mcp" || v.Member == "skill") && v.Source == "git"
		if !admitted {
			return fmt.Errorf("%s: member/source admission", v.Name)
		}
		if _, ok := byName[v.Name]; ok {
			return fmt.Errorf("duplicate case %s", v.Name)
		}
		byName[v.Name] = v
		if err := checkObservation(v, v.Expected); err != nil {
			return fmt.Errorf("%s: %w", v.Name, err)
		}
		if (structural(v.Condition) != "" || v.Condition == "multiple-structural") && !reflect.DeepEqual(v.Levels, []int{1, 2, 3, 4}) {
			return fmt.Errorf("%s: missing fatal level", v.Name)
		}
		if v.Condition == "verification-policy" && (v.Home != "current" || v.Operation != "resolve" || v.Member != "context" || v.Source != "git") {
			return fmt.Errorf("%s: policy fixture scope", v.Name)
		}
		if v.Condition == "multiple-structural" && (v.Failures[0].Member != v.Member || v.Operation != "resolve") {
			return fmt.Errorf("%s: ordered member fixture scope", v.Name)
		}
		if v.Condition == "entry-absent" {
			valid := (v.Operation == "resolve" && reflect.DeepEqual(v.Levels, []int{1, 2, 3, 4})) ||
				((v.Operation == "repair" || v.Operation == "dry-run") && (reflect.DeepEqual(v.Levels, []int{1, 2}) || reflect.DeepEqual(v.Levels, []int{3, 4})))
			if !valid {
				return fmt.Errorf("%s: whole-entry availability level partition", v.Name)
			}
		}
		switch v.Condition {
		case "home-stale", "home-absent", "marker-unreadable":
			valid := reflect.DeepEqual(v.Levels, []int{1, 2, 3, 4})
			if v.Condition == "home-stale" && v.Operation == "resolve" {
				valid = reflect.DeepEqual(v.Levels, []int{1}) || reflect.DeepEqual(v.Levels, []int{2}) || reflect.DeepEqual(v.Levels, []int{2, 3, 4})
			}
			if !valid {
				return fmt.Errorf("%s: missing home gate level", v.Name)
			}
		case "pin-drift":
			if !reflect.DeepEqual(v.Levels, []int{3, 4}) && !reflect.DeepEqual(v.Levels, []int{1}) && !reflect.DeepEqual(v.Levels, []int{2}) {
				return fmt.Errorf("%s: pin verdict level partition", v.Name)
			}
		}
		if (v.Condition == "verification-policy") != (v.Policy != nil) || (v.Condition == "multiple-structural") != (len(v.Failures) > 0) {
			return fmt.Errorf("%s: fixture discriminator", v.Name)
		}
		for _, f := range v.Forbidden {
			if checkObservation(v, f.Observation) == nil {
				return fmt.Errorf("%s: undetected control %s", v.Name, f.Name)
			}
		}
	}
	for _, v := range cases {
		p, ok := byName[v.Positive]
		if !ok || p.Kind != "implementation" || (p.Condition != "intact" && !(p.Condition == "verification-policy" && p.Expected.Fragment && p.Expected.Current)) || p.Operation != v.Operation || p.Member != v.Member {
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
	for _, member := range []string{"context", "mcp", "skill"} {
		for _, fixture := range []struct {
			suffix, source, operation, condition string
			levels                               []int
		}{
			{"git-repair-strict", "git", "repair", "entry-absent", []int{3, 4}},
			{"git-repair-permissive", "git", "repair", "entry-absent", []int{1, 2}},
			{"git-read-only", "git", "resolve", "entry-absent", []int{1, 2, 3, 4}},
			{"git-dry-run-strict", "git", "dry-run", "entry-absent", []int{3, 4}},
			{"git-dry-run-permissive", "git", "dry-run", "entry-absent", []int{1, 2}},
			{"path-repair-strict", "path", "repair", "entry-absent", []int{3, 4}},
			{"local-repair-strict", "local", "repair", "entry-absent", []int{3, 4}},
			{"path-dry-run-strict", "path", "dry-run", "entry-absent", []int{3, 4}},
			{"local-dry-run-strict", "local", "dry-run", "entry-absent", []int{3, 4}},
			{"missing-payload-resolve", "git", "resolve", "payload-absent", []int{1, 2, 3, 4}},
			{"missing-payload-repair", "git", "repair", "payload-absent", []int{1, 2, 3, 4}},
			{"missing-payload-dry-run", "git", "dry-run", "payload-absent", []int{1, 2, 3, 4}},
		} {
			// Retained lock carriers admit state pins only for context members.
			if member != "context" && fixture.source != "git" {
				continue
			}
			name := member + "-" + fixture.suffix
			v, ok := byName[name]
			if !ok || v.Kind != "implementation" || v.Member != member || v.Source != fixture.source || v.Operation != fixture.operation || v.Condition != fixture.condition || !reflect.DeepEqual(v.Levels, fixture.levels) || v.Predecessor != nil {
				return fmt.Errorf("missing availability case %s", name)
			}
		}
	}
	for _, boundary := range []struct {
		name   string
		levels []int
	}{
		{"level1-legacy-intact-updated-store-old-marker-stale", []int{1}},
		{"level2-home-drift-refuses", []int{2}},
	} {
		v, ok := byName[boundary.name]
		if !ok || v.Condition != "home-stale" || v.Home != "stale-old-marker" || v.Operation != "resolve" || v.Member != "context" || v.Source != "path" || !reflect.DeepEqual(v.Levels, boundary.levels) {
			return fmt.Errorf("missing home drift boundary %s", boundary.name)
		}
	}
	for _, name := range []string{"precedence-context-first", "precedence-skill-first", "precedence-skill-ownership"} {
		if v, ok := byName[name]; !ok || v.Condition != "multiple-structural" {
			return fmt.Errorf("missing precedence case %s", name)
		}
	}
	requiredPolicy := []string{"centre-unreachable", "centre-denied", "centre-invalid", "centre-unreachable-local-unavailable", "centre-denied-local-unavailable", "centre-invalid-local-unavailable", "default-pass", "default-unavailable", "floor-raise-pass", "floor-raise-unavailable", "floor-transitive-centre-denied", "floor-weakening"}
	for level := 1; level <= 4; level++ {
		for _, suffix := range []string{"pass", "unavailable", "mismatch", "mismatch-unavailable", "unavailable-mismatch"} {
			requiredPolicy = append(requiredPolicy, fmt.Sprintf("level%d-%s", level, suffix))
		}
	}
	for _, name := range requiredPolicy {
		if v, ok := byName["policy-"+name]; !ok || v.Condition != "verification-policy" {
			return fmt.Errorf("missing policy case %s", name)
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
			if condition == "pin-drift" || (condition == "home-stale" && operation == "resolve") {
				disposition = "level-scoped"
			}
			if negative {
				disposition += "-negative-control"
			}
			if row.Disposition != disposition || row.Negative != negative || (v.Kind == "checker-control") != negative || !reflect.DeepEqual(row.OldDiagnostic, old.Diagnostic) || !reflect.DeepEqual(row.OldOutcome, old.Outcome) {
				return fmt.Errorf("wrong disposition %s", old.Name)
			}
			if !reflect.DeepEqual(row.Levels, v.Levels) {
				return fmt.Errorf("wrong migration levels %s", old.Name)
			}
			if condition == "pin-drift" || (condition == "home-stale" && operation == "resolve") {
				lowerCount := 2
				if condition == "home-stale" {
					lowerCount = 1
				}
				if len(row.LevelSuccessors) != lowerCount {
					return fmt.Errorf("missing level successors %s", old.Name)
				}
				for i, name := range row.LevelSuccessors {
					lower, ok := byName[name]
					if !ok || name != fmt.Sprintf("level%d-%s", i+1, v.Name) || lower.Predecessor != nil || lower.Kind != "implementation" || lower.Condition != v.Condition || lower.Home != v.Home || lower.Source != v.Source || lower.Member != v.Member || lower.Operation != v.Operation || !reflect.DeepEqual(lower.Levels, []int{i + 1}) {
						return fmt.Errorf("wrong level successor %s", old.Name)
					}
				}
			} else if len(row.LevelSuccessors) != 0 {
				return fmt.Errorf("unexpected level successors %s", old.Name)
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
