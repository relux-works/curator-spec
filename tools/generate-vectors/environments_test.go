package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"io/fs"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"testing"
)

// The exact section 5.1 header for the composed determinism case. Recorded as
// a literal so a generator drift away from the prose grammar fails here, not
// only in the Python cross-check.
const composedEnvironmentHeader = "<!--\n" +
	"curator-root-context-v1\n" +
	"profile: companyA commit 0123456789abcdef0123456789abcdef01234567\n" +
	"compose: personal commit fedcba9876543210fedcba9876543210fedcba98\n" +
	"precedence: later-overrides-earlier\n" +
	"generated: Curator Protocol environments revision 1 (https://github.com/relux-works/curator-spec)\n" +
	"notice: generated file; direct edits are unsupported and are detected as drift; update the source profile repository or its composed profiles instead\n" +
	"-->\n"

func environmentTestChain(t *testing.T, names ...string) []environmentProfile {
	t.Helper()
	profiles := environmentFixtureProfiles()
	chain := make([]environmentProfile, 0, len(names))
	for _, name := range names {
		profile, ok := profiles[name]
		if !ok {
			t.Fatalf("unknown fixture profile %q", name)
		}
		chain = append(chain, profile)
	}
	return chain
}

func TestEnvironmentVectorGenerationIsDeterministic(t *testing.T) {
	readTree := func(root string) map[string][]byte {
		files := map[string][]byte{}
		err := filepath.WalkDir(root, func(path string, entry fs.DirEntry, err error) error {
			if err != nil || !entry.Type().IsRegular() {
				return err
			}
			payload, readErr := os.ReadFile(path)
			if readErr != nil {
				return readErr
			}
			relative, relErr := filepath.Rel(root, path)
			if relErr != nil {
				return relErr
			}
			files[filepath.ToSlash(relative)] = payload
			return nil
		})
		if err != nil {
			t.Fatal(err)
		}
		return files
	}
	one := t.TempDir()
	two := t.TempDir()
	writeEnvironmentVectors(filepath.Join(one, "vectors"), filepath.Join(one, "expected"))
	writeEnvironmentVectors(filepath.Join(two, "vectors"), filepath.Join(two, "expected"))
	left, right := readTree(one), readTree(two)
	if len(left) != len(right) {
		t.Fatalf("environment generation file inventories differ: %d vs %d", len(left), len(right))
	}
	for path, payload := range left {
		if !bytes.Equal(payload, right[path]) {
			t.Fatalf("environment generation is not deterministic for %s", path)
		}
	}
}

func TestEnvironmentHeaderGrammarIsExact(t *testing.T) {
	composed := environmentHeader(environmentTestChain(t, "companyA", "personal"), precedenceLaterOverridesEarlier)
	if composed != composedEnvironmentHeader {
		t.Fatalf("composed header drifted from the section 5.1 grammar:\n%s", composed)
	}
	single := environmentHeader(environmentTestChain(t, "companyA"), "")
	if strings.Contains(single, "compose:") || strings.Contains(single, "precedence:") {
		t.Fatal("uncomposed header must omit the compose and precedence lines")
	}
	if strings.Count(single, "\n") != 6 {
		t.Fatalf("uncomposed header must be exactly six lines, got %d", strings.Count(single, "\n"))
	}
	local := environmentHeader(environmentTestChain(t, "default"), "")
	if !strings.Contains(local, "profile: default state sha256:"+strings.Repeat("ab", 32)+"\n") {
		t.Fatal("local profile header must carry the state pin spelling")
	}
}

func TestEnvironmentZeroModuleOutputIsHeaderAlone(t *testing.T) {
	chain := environmentTestChain(t, "emptyoverlay")
	written, files := environmentRootContextFiles(chain, "claude_code", "monolithic", "")
	if !written {
		t.Fatal("a zero-module materialization must still write the root-context file")
	}
	if files["CLAUDE.md"] != environmentHeader(chain, "") {
		t.Fatal("zero-module output must be the header part alone")
	}
	composed := environmentTestChain(t, "emptyoverlay", "emptytoo")
	_, composedFiles := environmentRootContextFiles(composed, "claude_code", "monolithic", precedenceLaterOverridesEarlier)
	want := environmentJoin([]string{
		environmentHeader(composed, precedenceLaterOverridesEarlier),
		environmentChapter("emptyoverlay"),
		environmentChapter("emptytoo"),
	})
	if composedFiles["CLAUDE.md"] != want {
		t.Fatal("composed zero-module output must keep every empty chapter")
	}
	if _, noSurface := environmentRootContextFiles(environmentTestChain(t, "nocontext"), "claude_code", "monolithic", ""); noSurface != nil {
		t.Fatal("a profile without a context directory must write no root-context file")
	}
}

func TestEnvironmentOpencodeConfigIsExactCCJ1WithTrailingLF(t *testing.T) {
	_, files := environmentRootContextFiles(environmentTestChain(t, "companyA"), "opencode", "referenced", "")
	want := `{"instructions":[".agent-context/modules/companyA/00-base.md",".agent-context/modules/companyA/10-style.md"]}` + "\n"
	if files["opencode.json"] != want {
		t.Fatalf("managed opencode.json bytes drifted: %q", files["opencode.json"])
	}
	if files["AGENTS.md"] != environmentHeader(environmentTestChain(t, "companyA"), "") {
		t.Fatal("the opencode referenced root file must be the header part alone")
	}
	_, empty := environmentRootContextFiles(environmentTestChain(t, "emptyoverlay"), "opencode", "referenced", "")
	if empty["opencode.json"] != `{"instructions":[]}`+"\n" {
		t.Fatalf("zero-module managed opencode.json bytes drifted: %q", empty["opencode.json"])
	}
}

func TestEnvironmentSystemPromptOutputHasNoHeader(t *testing.T) {
	written, files := environmentSystemPromptFiles(environmentTestChain(t, "companyA", "personal"), "claude_code")
	if !written {
		t.Fatal("applicable system modules must produce the system-prompt file")
	}
	want := "You are the companyA reviewer.\n\nPrefer short answers.\n"
	if files[environmentSystemPromptPath] != want {
		t.Fatalf("system-prompt output drifted: %q", files[environmentSystemPromptPath])
	}
	if strings.Contains(files[environmentSystemPromptPath], environmentHeaderMarker) {
		t.Fatal("system-prompt output must not carry the generation header")
	}
	if written, _ := environmentSystemPromptFiles(environmentTestChain(t, "selective"), "codex_cli"); written {
		t.Fatal("a selector-excluded system module must leave the file absent")
	}
}

func TestEnvironmentSchemaCasesCoverTheClosedSurfaces(t *testing.T) {
	root := repositoryRoot(t)
	payload, err := os.ReadFile(filepath.Join(root, "conformance", "v1", "schema-cases", "index.json"))
	if err != nil {
		t.Fatal(err)
	}
	var index []map[string]any
	if err := json.Unmarshal(payload, &index); err != nil {
		t.Fatal(err)
	}
	byInstance := map[string]bool{}
	for _, entry := range index {
		schema, _ := entry["schema"].(string)
		instance, _ := entry["instance"].(string)
		valid, _ := entry["valid"].(bool)
		byInstance[schema+"|"+instance] = valid
	}
	requireCase := func(schema, name string, valid bool) {
		t.Helper()
		key := schema + "|" + strings.TrimSuffix(schema, ".schema.json") + "/" + name
		actual, present := byInstance[key]
		if !present {
			t.Fatalf("missing generated schema case %s for %s", name, schema)
		}
		if actual != valid {
			t.Fatalf("schema case %s for %s declares valid=%v, want %v", name, schema, actual, valid)
		}
	}
	for schema, examples := range map[string][]schemaExample{
		"profilefile-v1.schema.json": profilefileSchemaExamples(map[string]any{
			"version": 1, "profiles": map[string]any{"companyA": "profiles/companyA"},
		}),
		"context-manifest-v1.schema.json":         contextManifestSchemaExamples(validContextManifestV1()),
		"agent-environment-marker-v1.schema.json": environmentMarkerSchemaExamples(validEnvironmentMarkerV1()),
		"launch-env-fragment-v1.schema.json":      launchEnvFragmentSchemaExamples(validLaunchEnvFragmentV1()),
	} {
		requireCase(schema, "valid.json", true)
		requireCase(schema, "invalid.json", false)
		for _, example := range examples {
			requireCase(schema, example.name+".json", example.valid)
		}
	}
}

// The section 1.2 byte-exactness vector: the expected hash is the core
// section 8 content hash over the fixture's regular files, .gitattributes
// included, and the fixture bytes themselves carry the properties the
// acquisition contract asserts (CRLF, mixed endings, literal $Format:).
func TestSnapshotAcquisitionVectorIsTheRawFixtureHash(t *testing.T) {
	root := repositoryRoot(t)
	fixture := filepath.Join(root, "conformance", "v1", "fixtures", "byte-exact")
	scratch := t.TempDir()
	writeSnapshotAcquisitionVectors(filepath.Join(scratch, "vectors"), fixture, filepath.Join(scratch, "expected"))
	vector := readObject(t, filepath.Join(scratch, "vectors", "snapshot-acquisition.json"))
	if vector["capability"] != "agent-environments" || vector["capability_revision"] != json.Number("1") || vector["protocol_version"] != protocolVersion {
		t.Fatalf("snapshot-acquisition vector has the wrong identity: %#v", vector)
	}
	cases := vector["cases"].([]any)
	if len(cases) != 1 {
		t.Fatalf("expected exactly one acquisition case, got %d", len(cases))
	}
	item := cases[0].(map[string]any)
	if item["fixture"] != "fixtures/byte-exact" || item["name"] != "byte-exact-snapshot" {
		t.Fatalf("unexpected case identity: %#v", item)
	}
	expectedText, err := os.ReadFile(filepath.Join(scratch, "expected", "byte-exact-snapshot_sha256.txt"))
	if err != nil {
		t.Fatal(err)
	}
	files := regularFiles(fixture)
	want := []string{".gitattributes", "crlf.txt", "lf.txt", "mixed.txt", "subst.txt"}
	if strings.Join(files, ",") != strings.Join(want, ",") {
		t.Fatalf("fixture inventory = %v, want %v", files, want)
	}
	hash := contentHash(fixture, files)
	if item["expected_sha256"] != hash || string(expectedText) != hash+"\n" {
		t.Fatalf("expected hash %s is not the raw fixture content hash %s", item["expected_sha256"], hash)
	}
	// Hashing without .gitattributes must not alias: the attribute file is a
	// regular file of the committed tree and is part of the snapshot.
	if contentHash(fixture, files[1:]) == hash {
		t.Fatal("content hash ignores .gitattributes")
	}
	read := func(name string) []byte {
		payload, readErr := os.ReadFile(filepath.Join(fixture, name))
		if readErr != nil {
			t.Fatal(readErr)
		}
		return payload
	}
	if string(read(".gitattributes")) != "* text=auto\nsubst.txt export-subst\n" {
		t.Fatalf("fixture .gitattributes bytes drifted: %q", read(".gitattributes"))
	}
	if bytes.Contains(read("lf.txt"), []byte("\r")) {
		t.Fatal("lf.txt carries a CR")
	}
	if crlf := read("crlf.txt"); !bytes.Contains(crlf, []byte("\r\n")) || bytes.Contains(bytes.ReplaceAll(crlf, []byte("\r\n"), nil), []byte("\n")) {
		t.Fatalf("crlf.txt is not CRLF-only: %q", crlf)
	}
	if mixed := read("mixed.txt"); !bytes.Contains(mixed, []byte("\r\n")) || !bytes.Contains(bytes.ReplaceAll(mixed, []byte("\r\n"), nil), []byte("\n")) {
		t.Fatalf("mixed.txt does not mix LF and CRLF: %q", mixed)
	}
	if subst := read("subst.txt"); !bytes.Contains(subst, []byte("$Format:%H$")) || !bytes.Contains(subst, []byte("$Format:%h$")) {
		t.Fatalf("subst.txt lost its literal placeholders: %q", subst)
	}
	// The per-file digests in the vector must be the digests of the fixture
	// bytes, so a checkout that normalized an ending fails here.
	for _, entry := range item["files"].([]any) {
		record := entry.(map[string]any)
		payload := read(record["path"].(string))
		sum := sha256.Sum256(payload)
		if record["sha256"] != "sha256:"+hex.EncodeToString(sum[:]) || record["bytes"] != json.Number(strconv.Itoa(len(payload))) {
			t.Fatalf("file record for %s does not match the fixture bytes", record["path"])
		}
	}
}
