// Command validate-claude-env checks proposal fixtures, not a native launch.
package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"

	"github.com/santhosh-tekuri/jsonschema/v5"
)

const setting = "BASH_MAX_OUTPUT_LENGTH"

var canonicalInteger = regexp.MustCompile(`^-?(0|[1-9][0-9]*)$`)
var fixtureID = regexp.MustCompile(`^[a-z0-9][a-z0-9-]{0,79}$`)

type vector struct {
	ID          string `json:"id"`
	Claim       string `json:"claim"`
	Entry       string `json:"entry"`
	Input       string `json:"input_json"`
	Want        string `json:"want"`
	SchemaValid bool   `json:"schema_valid"`
}

type plant struct {
	ID      string `json:"id"`
	Claim   string `json:"claim"`
	Entry   string `json:"entry"`
	Valid   string `json:"valid_json"`
	Invalid string `json:"invalid_json"`
	Want    string `json:"want"`
}

func objectValue(d *json.Decoder) (any, error) {
	t, err := d.Token()
	if err != nil {
		return nil, errors.New("invalid JSON")
	}
	if delim, ok := t.(json.Delim); ok {
		switch delim {
		case '{':
			m := map[string]any{}
			for d.More() {
				key, err := d.Token()
				if err != nil {
					return nil, errors.New("invalid JSON")
				}
				name, ok := key.(string)
				if !ok {
					return nil, errors.New("invalid JSON")
				}
				if _, exists := m[name]; exists {
					return nil, errors.New("duplicate member")
				}
				value, err := objectValue(d)
				if err != nil {
					return nil, err
				}
				m[name] = value
			}
			end, err := d.Token()
			if err != nil || end != json.Delim('}') {
				return nil, errors.New("invalid JSON")
			}
			return m, nil
		case '[':
			var values []any
			for d.More() {
				value, err := objectValue(d)
				if err != nil {
					return nil, err
				}
				values = append(values, value)
			}
			end, err := d.Token()
			if err != nil || end != json.Delim(']') {
				return nil, errors.New("invalid JSON")
			}
			return values, nil
		default:
			return nil, errors.New("invalid JSON")
		}
	}
	return t, nil
}

func decodeStrict(raw string) (any, error) {
	d := json.NewDecoder(strings.NewReader(raw))
	d.UseNumber()
	v, err := objectValue(d)
	if err != nil {
		return nil, err
	}
	if _, err := d.Token(); err != io.EOF {
		return nil, errors.New("trailing input")
	}
	return v, nil
}

func declaration(v any) string {
	m, ok := v.(map[string]any)
	if !ok {
		return "claude_env_invalid"
	}
	for key := range m {
		if key != setting {
			return "claude_env_name_not_allowed"
		}
	}
	raw, present := m[setting]
	if !present {
		return "accept"
	}
	s, ok := raw.(string)
	if !ok || !canonicalInteger.MatchString(s) {
		return "claude_env_value_not_integer"
	}
	if s == "0" || strings.HasPrefix(s, "-") {
		return "claude_env_value_nonpositive"
	}
	n, err := strconv.ParseUint(s, 10, 32)
	if err != nil || n > 65536 {
		return "claude_env_value_over_bound"
	}
	return "accept"
}

func semantic(entry, raw string) string {
	v, err := decodeStrict(raw)
	if err != nil {
		return "claude_env_invalid"
	}
	if entry == "declaration" {
		return declaration(v)
	}
	if entry != "projection" {
		return "claude_env_invalid"
	}
	m, ok := v.(map[string]any)
	if !ok || len(m) != 2 {
		return "claude_env_invalid"
	}
	runtime, ok := m["runtime"].(string)
	if !ok {
		return "claude_env_invalid"
	}
	switch runtime {
	case "claude_code", "codex_cli", "opencode", "pi", "muse":
	default:
		return "claude_env_invalid"
	}
	if verdict := declaration(m["env"]); verdict != "accept" {
		return verdict
	}
	if runtime != "claude_code" && len(m["env"].(map[string]any)) != 0 {
		return "claude_env_runtime_ineligible"
	}
	return "accept"
}

func schemas(root string) (map[string]*jsonschema.Schema, error) {
	c := jsonschema.NewCompiler()
	c.LoadURL = func(string) (io.ReadCloser, error) {
		return nil, errors.New("undeclared schema resource")
	}
	base := "https://relux-works.github.io/curator-spec/schemas/machine-claude-env-v1/"
	files := map[string]string{"declaration": "claude-env.schema.json", "projection": "projection.schema.json"}
	for _, name := range files {
		b, err := os.ReadFile(filepath.Join(root, "schemas", "machine-claude-env-v1", name))
		if err != nil {
			return nil, errors.New("schema resource unavailable")
		}
		if err := c.AddResource(base+name, bytes.NewReader(b)); err != nil {
			return nil, errors.New("invalid schema resource")
		}
	}
	result := map[string]*jsonschema.Schema{}
	for entry, name := range files {
		s, err := c.Compile(base + name)
		if err != nil {
			return nil, errors.New("schema compilation failed")
		}
		result[entry] = s
	}
	return result, nil
}

func schemaAccepts(s *jsonschema.Schema, raw string) bool {
	var instance any
	if s == nil || json.Unmarshal([]byte(raw), &instance) != nil {
		return false
	}
	return s.Validate(instance) == nil
}

func validVerdict(s string) bool {
	switch s {
	case "accept", "claude_env_invalid", "claude_env_name_not_allowed", "claude_env_value_not_integer", "claude_env_value_nonpositive", "claude_env_value_over_bound", "claude_env_runtime_ineligible":
		return true
	}
	return false
}

// check runs every vector, including those after a failure, without input output.
func check(w io.Writer, compiled map[string]*jsonschema.Schema, cases []vector) int {
	failures := 0
	for _, item := range cases {
		if !fixtureID.MatchString(item.ID) || !validVerdict(item.Want) || item.Claim == "" || compiled[item.Entry] == nil {
			fmt.Fprintln(w, "FAIL invalid-corpus-metadata")
			failures++
			continue
		}
		got := semantic(item.Entry, item.Input)
		schemaOK := schemaAccepts(compiled[item.Entry], item.Input)
		if got != item.Want || schemaOK != item.SchemaValid {
			fmt.Fprintf(w, "FAIL %s expected=%s actual=%s schema-valid=%t\n", item.ID, item.Want, got, schemaOK)
			failures++
		} else {
			fmt.Fprintf(w, "PASS %s verdict=%s\n", item.ID, got)
		}
	}
	return failures
}

func load(root string) ([]vector, error) {
	var cases []vector
	b, err := os.ReadFile(filepath.Join(root, "conformance", "machine-claude-env-v1", "cases.json"))
	if err != nil || json.Unmarshal(b, &cases) != nil || len(cases) == 0 {
		return nil, errors.New("case corpus unavailable or invalid")
	}
	var plants []plant
	b, err = os.ReadFile(filepath.Join(root, "conformance", "machine-claude-env-v1", "plants.json"))
	if err != nil || json.Unmarshal(b, &plants) != nil || len(plants) != 6 {
		return nil, errors.New("six control plants required")
	}
	for _, p := range plants {
		cases = append(cases,
			vector{p.ID + "-control", p.Claim, p.Entry, p.Valid, "accept", true},
			vector{p.ID + "-plant", p.Claim, p.Entry, p.Invalid, p.Want, false})
	}
	return cases, nil
}

func run(root string, w io.Writer) int {
	compiled, err := schemas(root)
	if err != nil {
		fmt.Fprintln(w, "FAIL schema-setup")
		return 2
	}
	cases, err := load(root)
	if err != nil {
		fmt.Fprintln(w, "FAIL corpus-setup")
		return 2
	}
	failures := check(w, compiled, cases)
	fmt.Fprintf(w, "cases=%d failures=%d runtime-cases=0\n", len(cases), failures)
	if failures != 0 {
		return 1
	}
	return 0
}

func main() {
	root := flag.String("root", ".", "specification checkout")
	flag.Parse()
	os.Exit(run(*root, os.Stdout))
}
