package musenative

import (
	"bytes"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"

	"github.com/santhosh-tekuri/jsonschema/v5"
)

const frozenHash = "afc824151de968d1bd2c3c9a15d6bf4024ad6920f0f0a56351ee755b56aa9847"
const schemaName = "launch-env-fragment-v4-muse-native.schema.json"
const base = "https://relux-works.github.io/curator-spec/schemas/"

func root() string { return filepath.Join("..", "..") }
func load(t *testing.T, name string) []byte {
	t.Helper()
	b, err := os.ReadFile(filepath.Join(root(), name))
	if err != nil {
		t.Fatal(err)
	}
	return b
}
func object(t *testing.T, raw []byte) map[string]any {
	t.Helper()
	var v map[string]any
	if err := json.Unmarshal(raw, &v); err != nil {
		t.Fatal(err)
	}
	return v
}

// The Go engine uses RE2 rather than ECMAScript Unicode escapes. Translate
// only equivalent control-character escapes in patterns in memory; never rewrite a file.
func regexDialect(raw []byte) []byte {
	var v any
	if json.Unmarshal(raw, &v) != nil {
		return raw
	}
	var visit func(any)
	visit = func(x any) {
		switch x := x.(type) {
		case map[string]any:
			for k, value := range x {
				if k == "pattern" {
					if s, ok := value.(string); ok {
						x[k] = strings.NewReplacer(`\u0000`, `\x00`, `\u001f`, `\x1f`, `\u007f`, `\x7f`, `\u009f`, `\x9f`).Replace(s)
					}
				} else {
					visit(value)
				}
			}
		case []any:
			for _, value := range x {
				visit(value)
			}
		}
	}
	visit(v)
	b, _ := json.Marshal(v)
	return b
}

func compile(t *testing.T, successor []byte) (*jsonschema.Schema, *jsonschema.Schema) {
	t.Helper()
	c := jsonschema.NewCompiler()
	c.LoadURL = func(string) (io.ReadCloser, error) { return nil, fmt.Errorf("undeclared schema resource") }
	// Register the exact externally referenced definitions. Unreferenced
	// repository/source patterns use ECMAScript features unavailable in RE2;
	// the production Python gate validates the complete raw schema resources.
	for name, names := range map[string][]string{
		"common.schema.json":                      {"identifier", "hex256", "portablePath"},
		"agent-environment-marker-v1.schema.json": {"precedence"},
		"agent-mcp-v1.schema.json":                {"envNames"},
	} {
		doc := object(t, load(t, "schemas/v1/"+name))
		defs := doc["$defs"].(map[string]any)
		projected := map[string]any{}
		for _, key := range names {
			projected[key] = defs[key]
		}
		b, _ := json.Marshal(map[string]any{"$schema": doc["$schema"], "$id": doc["$id"], "$defs": projected})
		if err := c.AddResource(base+"v1/"+name, bytes.NewReader(regexDialect(b))); err != nil {
			t.Fatal(err)
		}
	}
	if err := c.AddResource(base+"v1/launch-env-fragment-v4.schema.json", bytes.NewReader(regexDialect(load(t, "schemas/v1/launch-env-fragment-v4.schema.json")))); err != nil {
		t.Fatal(err)
	}
	if err := c.AddResource(base+"muse-native-v1/"+schemaName, bytes.NewReader(regexDialect(successor))); err != nil {
		t.Fatal(err)
	}
	old, err := c.Compile(base + "v1/launch-env-fragment-v4.schema.json")
	if err != nil {
		t.Fatal(err)
	}
	now, err := c.Compile(base + "muse-native-v1/" + schemaName)
	if err != nil {
		t.Fatal(err)
	}
	return old, now
}
func accepts(s *jsonschema.Schema, v map[string]any) bool {
	if s.Validate(v) != nil {
		return false
	}
	if v["environment"] != "muse" {
		return true
	}
	env := v["env"].(map[string]any)
	config := env["XDG_CONFIG_HOME"].(string)
	home := strings.TrimSuffix(config, "/config")
	if home == "" {
		return false
	}
	for key, suffix := range map[string]string{"XDG_CONFIG_HOME": "/config", "XDG_DATA_HOME": "/data", "XDG_STATE_HOME": "/state", "XDG_CACHE_HOME": "/cache"} {
		if env[key] != home+suffix {
			return false
		}
	}
	return true
}

// Pins actual frozen bytes, not merely a mutable README checksum.
func TestFrozenSchema(t *testing.T) {
	b := load(t, "schemas/v1/launch-env-fragment-v4.schema.json")
	if fmt.Sprintf("%x", sha256.Sum256(b)) != frozenHash {
		t.Fatal("frozen v4 bytes changed")
	}
	if fmt.Sprintf("%x", sha256.Sum256(append(append([]byte{}, b...), '\n'))) == frozenHash {
		t.Fatal("byte-change control failed")
	}
}

type vector struct {
	Schema   string `json:"schema"`
	Instance string `json:"instance"`
	Valid    bool   `json:"valid"`
}

// Exercises the complete new corpus with a second schema engine, preserving
// one-parent semantics. It proves no native execution or store availability.
func TestSuccessorCorpus(t *testing.T) {
	old, now := compile(t, load(t, "schemas/muse-native-v1/"+schemaName))
	var cases []vector
	if err := json.Unmarshal(load(t, "conformance/muse-native-v1/schema-cases/index.json"), &cases); err != nil {
		t.Fatal(err)
	}
	if len(cases) != 25 {
		t.Fatalf("case inventory: %d", len(cases))
	}
	seen := map[string]bool{}
	for _, c := range cases {
		if c.Schema != schemaName || seen[c.Instance] {
			t.Fatal("schema binding or duplicate case")
		}
		seen[c.Instance] = true
		t.Run(c.Instance, func(t *testing.T) {
			v := object(t, load(t, "conformance/muse-native-v1/schema-cases/"+c.Instance))
			if got := accepts(now, v); got != c.Valid {
				t.Fatalf("accept=%v want=%v", got, c.Valid)
			}
			if c.Instance == "valid-muse-native.json" && accepts(old, v) {
				t.Fatal("old reader admitted native")
			}
			if c.Instance == "valid-muse-file.json" && !accepts(old, v) {
				t.Fatal("old file form lost")
			}
		})
	}
}

// All predecessor v4 cases keep their verdict. Native-with-file remains
// invalid; this does not silently reinterpret a previously invalid mixed form.
func TestPredecessorCasesRetained(t *testing.T) {
	_, now := compile(t, load(t, "schemas/muse-native-v1/"+schemaName))
	var cases []vector
	if err := json.Unmarshal(load(t, "conformance/environments-muse-v4/schema-cases/index.json"), &cases); err != nil {
		t.Fatal(err)
	}
	for _, c := range cases {
		if c.Schema != "launch-env-fragment-v4.schema.json" {
			continue
		}
		t.Run(c.Instance, func(t *testing.T) {
			v := object(t, load(t, "conformance/environments-muse-v4/schema-cases/"+c.Instance))
			if got := accepts(now, v); got != c.Valid {
				t.Fatalf("predecessor accept=%v want=%v", got, c.Valid)
			}
		})
	}
}

func museThen(v map[string]any) map[string]any {
	for _, raw := range v["allOf"].([]any) {
		branch := raw.(map[string]any)
		condition := branch["if"].(map[string]any)["properties"].(map[string]any)["environment"].(map[string]any)
		if condition["const"] == "muse" {
			return branch["then"].(map[string]any)
		}
	}
	panic("missing Muse branch")
}

// Normalizing URI relocation leaves only the intentionally changed Muse arm.
// Other adapters and every common field must remain structurally identical.
func TestOnlyMuseArmChanges(t *testing.T) {
	old := object(t, load(t, "schemas/v1/launch-env-fragment-v4.schema.json"))
	raw := load(t, "schemas/muse-native-v1/"+schemaName)
	raw = bytes.ReplaceAll(raw, []byte(base+"v1/"), nil)
	now := object(t, raw)
	now["$id"] = old["$id"]
	now["title"] = old["title"]
	for _, doc := range []map[string]any{old, now} {
		m := museThen(doc)
		for k := range m {
			delete(m, k)
		}
	}
	if !reflect.DeepEqual(old, now) {
		t.Fatal("changed outside Muse arm")
	}
}

// Narrowing back to file-only kills the native positive; widening the native
// arm kills its backend/override negatives. Each mutation has a valid neighbour.
func TestGuardMutations(t *testing.T) {
	raw := load(t, "schemas/muse-native-v1/"+schemaName)
	native := object(t, load(t, "conformance/muse-native-v1/schema-cases/valid-muse-native.json"))
	file := object(t, load(t, "conformance/muse-native-v1/schema-cases/valid-muse-file.json"))
	_, valid := compile(t, raw)
	if !accepts(valid, native) || !accepts(valid, file) {
		t.Fatal("valid neighbours refused")
	}
	narrow := object(t, raw)
	museThen(narrow)["properties"].(map[string]any)["credential_store"].(map[string]any)["properties"].(map[string]any)["selection"] = map[string]any{"const": "file"}
	b, _ := json.Marshal(narrow)
	_, restricted := compile(t, b)
	if accepts(restricted, native) || !accepts(restricted, file) {
		t.Fatal("narrowing control failed")
	}
	wide := object(t, raw)
	arm := museThen(wide)["oneOf"].([]any)[1].(map[string]any)["properties"].(map[string]any)
	delete(arm, "env")
	b, _ = json.Marshal(wide)
	_, widened := compile(t, b)
	mixed := object(t, load(t, "conformance/muse-native-v1/schema-cases/invalid-native-with-backend.json"))
	if accepts(valid, mixed) || !accepts(widened, mixed) || !accepts(widened, native) {
		t.Fatal("backend guard control failed")
	}
	override := object(t, raw)
	museThen(override)["properties"].(map[string]any)["credential_store"].(map[string]any)["properties"].(map[string]any)["config_overrides"] = true
	b, _ = json.Marshal(override)
	_, unprotected := compile(t, b)
	withOverride := object(t, load(t, "conformance/muse-native-v1/schema-cases/invalid-native-with-overrides.json"))
	if accepts(valid, withOverride) || !accepts(unprotected, withOverride) || !accepts(unprotected, native) {
		t.Fatal("override guard control failed")
	}
}

// The in-memory regex dialect projection still rejects NUL in a path, next
// to the unchanged valid native neighbour. Raw schemas use the Python gate.
func TestNULPathRejected(t *testing.T) {
	_, schema := compile(t, load(t, "schemas/muse-native-v1/"+schemaName))
	v := object(t, load(t, "conformance/muse-native-v1/schema-cases/valid-muse-native.json"))
	if schema.Validate(v) != nil {
		t.Fatal("valid neighbour refused")
	}
	v["env"].(map[string]any)["XDG_CONFIG_HOME"] = "/fixture/muse/config\x00"
	if schema.Validate(v) == nil {
		t.Fatal("NUL path admitted")
	}
}

type policyCase struct {
	Name       string            `json:"name"`
	Platform   string            `json:"platform"`
	Isolation  string            `json:"isolation"`
	Configured string            `json:"configured"`
	Supported  bool              `json:"supported_route"`
	Expected   map[string]string `json:"expected"`
}

// Contract mapping, not an implementation of native login or a vendor probe.
func policy(c policyCase) map[string]string {
	if c.Configured != "native" && c.Configured != "absent" && c.Configured != "file" {
		return map[string]string{"diagnostic": "environment_credential_store_unsupported"}
	}
	native := c.Platform == "darwin" && c.Isolation == "shared" && (c.Configured == "native" || c.Configured == "absent")
	if native {
		if !c.Supported {
			return map[string]string{"diagnostic": "environment_credential_store_unsupported"}
		}
		return map[string]string{"effective_store": "native", "fixture": "valid-muse-native.json"}
	}
	return map[string]string{"effective_store": "file", "fixture": "valid-muse-file.json"}
}

// Linux native resolves to file, never refusal merely for lacking Keychain.
// The selected fixture must also satisfy the complete successor grammar.
func TestPlatformPolicyPairs(t *testing.T) {
	var cases []policyCase
	if err := json.Unmarshal(load(t, "conformance/muse-native-v1/policy-cases.json"), &cases); err != nil {
		t.Fatal(err)
	}
	if len(cases) != 18 {
		t.Fatalf("policy inventory: %d", len(cases))
	}
	required := map[string]bool{"native-route-unavailable": false, "unknown-machine-store": false}
	for _, platform := range []string{"darwin", "linux"} {
		for _, isolation := range []string{"shared", "isolated"} {
			for _, configured := range []string{"absent", "native", "file", "keychain"} {
				required[platform+"-"+isolation+"-"+configured] = false
			}
		}
	}
	_, schema := compile(t, load(t, "schemas/muse-native-v1/"+schemaName))
	for _, c := range cases {
		if seen, ok := required[c.Name]; !ok || seen {
			t.Fatal("unknown or duplicate policy case")
		}
		required[c.Name] = true
		if c.Name != "native-route-unavailable" && c.Name != "unknown-machine-store" && c.Name != c.Platform+"-"+c.Isolation+"-"+c.Configured {
			t.Fatal("policy name/input disagreement")
		}
		t.Run(c.Name, func(t *testing.T) {
			if !reflect.DeepEqual(policy(c), c.Expected) {
				t.Fatalf("policy mismatch: %v", policy(c))
			}
			if fixture := c.Expected["fixture"]; fixture != "" {
				v := object(t, load(t, "conformance/muse-native-v1/schema-cases/"+fixture))
				if !accepts(schema, v) || v["credential_store"].(map[string]any)["selection"] != c.Expected["effective_store"] {
					t.Fatal("policy/fragment disagreement")
				}
			}
		})
	}
	for name, seen := range required {
		if !seen {
			t.Fatalf("missing required policy case %s", name)
		}
	}
}
