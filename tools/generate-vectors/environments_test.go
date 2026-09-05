package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"io/fs"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"strconv"
	"strings"
	"testing"
)

// The exact section 5.1 header for the composed determinism case. Recorded as
// a literal (apart from the lock hash, which is recomputed from the lock the
// same way the header does) so a generator drift away from the prose grammar
// fails here, not only in the Python cross-check.
func composedEnvironmentHeader(t *testing.T) string {
	t.Helper()
	closure := environmentFixtureClosure("companyA", "personal", "emptyoverlay")
	return "<!--\n" +
		"curator-root-context-v2\n" +
		"root: companyA 2.3.0 commit 0123456789abcdef0123456789abcdef01234567\n" +
		"member: companyA 2.3.0 commit 0123456789abcdef0123456789abcdef01234567 weight 100\n" +
		"member: emptyoverlay 0.1.0 commit 1111111111111111111111111111111111111111 weight 1000 overlay\n" +
		"member: personal 0.3.0 state sha256:abababababababababababababababababababababababababababababababab weight 1000 overlay\n" +
		"precedence: winner=higher-weight placement=winner-last\n" +
		"lock: " + lockHash(environmentLock(closure)) + "\n" +
		"generated: Curator Protocol environments revision 1 (https://github.com/relux-works/curator-spec)\n" +
		"notice: generated file; direct edits are unsupported and are detected as drift; update the source profile repository or its composed profiles instead\n" +
		"-->\n"
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
	for _, dir := range []string{one, two} {
		writeEnvironmentVectors(filepath.Join(dir, "vectors"), filepath.Join(dir, "expected"))
		writeContextVersionVectors(filepath.Join(dir, "vectors"))
		writeContextDetectorVectors(filepath.Join(dir, "vectors"))
	}
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
	closure := environmentFixtureClosure("companyA", "personal", "emptyoverlay")
	composed := environmentHeader(closure, defaultPrecedence)
	if composed != composedEnvironmentHeader(t) {
		t.Fatalf("composed header drifted from the section 5.1 grammar:\n%s", composed)
	}
	if !strings.HasPrefix(strings.SplitN(composed, "\n", 3)[1], "curator-root-context-v2") {
		t.Fatal("header type line must be curator-root-context-v2")
	}
	single := environmentHeader(environmentFixtureClosure("companyA"), defaultPrecedence)
	if strings.Count(single, "\n") != 9 {
		t.Fatalf("single-root header must be exactly nine lines, got %d", strings.Count(single, "\n"))
	}
	if strings.Count(single, "member: ") != 1 || strings.Count(single, "precedence: ") != 1 || strings.Count(single, "lock: sha256:") != 1 {
		t.Fatalf("single-root header must carry one member, one precedence, and one lock line:\n%s", single)
	}
	local := environmentHeader(environmentFixtureClosure("default"), defaultPrecedence)
	if !strings.Contains(local, "root: default 0.0.0 state sha256:"+strings.Repeat("ab", 32)+"\n") {
		t.Fatal("local root header must carry the state pin spelling")
	}
	if strings.Contains(local, " overlay") {
		t.Fatal("a root is never flagged overlay")
	}
}

func TestEnvironmentEmittedOrderUnderBothPrimitives(t *testing.T) {
	closure := environmentFixtureClosure("umbrella", "core", "org", "ios", "figma", "personal")
	names := func(policy precedencePolicy) []string {
		var out []string
		for _, member := range environmentEmittedOrder(closure, policy) {
			out = append(out, member.name)
		}
		return out
	}
	ascending := []string{"core", "org", "figma", "ios", "umbrella", "personal"}
	descending := []string{"personal", "umbrella", "figma", "ios", "org", "core"}
	for policy, want := range map[precedencePolicy][]string{
		{winnerHigherWeight, placementWinnerLast}:  ascending,
		{winnerLowerWeight, placementWinnerLast}:   descending,
		{winnerHigherWeight, placementWinnerFirst}: descending,
		{winnerLowerWeight, placementWinnerFirst}:  ascending,
	} {
		if got := names(policy); !reflect.DeepEqual(got, want) {
			t.Fatalf("emitted order under %+v = %v, want %v", policy, got, want)
		}
	}
	// figma and ios tie at weight 60 and keep their topological (name) order
	// under every pair: placement never inverts a tie.
	for _, policy := range []precedencePolicy{{winnerLowerWeight, placementWinnerLast}, {winnerHigherWeight, placementWinnerFirst}} {
		got := names(policy)
		figma, ios := -1, -1
		for index, name := range got {
			if name == "figma" {
				figma = index
			}
			if name == "ios" {
				ios = index
			}
		}
		if figma > ios {
			t.Fatalf("descending order inverted the figma/ios tie: %v", got)
		}
	}
	// The root participates as an ordinary node: core requires org, so org
	// precedes core in the topological pass, and the root, which requires
	// everything, comes last among equal weights.
	tie := environmentFixtureClosure("emptyoverlay", "emptytoo")
	if got := names(defaultPrecedence); len(got) == 0 {
		t.Fatal("no order")
	}
	var tieNames []string
	for _, member := range environmentEmittedOrder(tie, defaultPrecedence) {
		tieNames = append(tieNames, member.name)
	}
	if !reflect.DeepEqual(tieNames, []string{"emptyoverlay", "emptytoo"}) {
		t.Fatalf("equal-weight order must be the Kahn name order, got %v", tieNames)
	}
}

func TestEnvironmentNoChapterMemberAppearsInHeaderOnly(t *testing.T) {
	closure := environmentFixtureClosure("companyA", "personal", "emptyoverlay")
	_, files := environmentRootContextFiles(closure, "claude_code", "monolithic", defaultPrecedence)
	document := files["CLAUDE.md"]
	if !strings.Contains(document, "member: emptyoverlay 0.1.0") {
		t.Fatal("the no-chapter member must appear as a member: line")
	}
	if strings.Contains(document, "## Context: emptyoverlay") {
		t.Fatal("a member with no applicable module must contribute no chapter")
	}
	want := environmentJoin([]string{
		environmentHeader(closure, defaultPrecedence),
		"---\n\n## Context: companyA 2.3.0\n",
		"# Base\n\nShared engineering context.\n",
		"# Style\n\nWrite tersely.\n",
		"# Claude\n\nClaude-only guidance.\n",
		"---\n\n## Context: personal 0.3.0\n",
		"# Personal\n\nPersonal overlay context.\n",
	})
	if document != want {
		t.Fatalf("composed monolithic bytes drifted:\n%s", document)
	}
	single := environmentFixtureClosure("companyA")
	_, singleFiles := environmentRootContextFiles(single, "codex_cli", "monolithic", defaultPrecedence)
	if strings.Contains(singleFiles["AGENTS.md"], "Claude-only") || !strings.Contains(singleFiles["AGENTS.md"], "## Context: companyA 2.3.0\n") {
		t.Fatalf("single-root codex output must carry the chapter and honor the selector:\n%s", singleFiles["AGENTS.md"])
	}
}

func TestEnvironmentZeroModuleOutputIsHeaderAlone(t *testing.T) {
	closure := environmentFixtureClosure("emptyoverlay")
	written, files := environmentRootContextFiles(closure, "claude_code", "monolithic", defaultPrecedence)
	if !written {
		t.Fatal("a zero-module materialization must still write the root-context file")
	}
	if files["CLAUDE.md"] != environmentHeader(closure, defaultPrecedence) {
		t.Fatal("zero-module output must be the header part alone")
	}
	composed := environmentFixtureClosure("emptyoverlay", "emptytoo")
	_, composedFiles := environmentRootContextFiles(composed, "claude_code", "monolithic", defaultPrecedence)
	if composedFiles["CLAUDE.md"] != environmentHeader(composed, defaultPrecedence) {
		t.Fatal("composed zero-module output must be the header alone: no chapter without applicable modules")
	}
	if _, noSurface := environmentRootContextFiles(environmentFixtureClosure("nocontext"), "claude_code", "monolithic", defaultPrecedence); noSurface != nil {
		t.Fatal("a root without a context directory must write no root-context file")
	}
}

func TestEnvironmentReferencedFormGroupsPerPackage(t *testing.T) {
	closure := environmentFixtureClosure("companyA", "personal")
	_, files := environmentRootContextFiles(closure, "claude_code", "referenced", defaultPrecedence)
	for _, path := range []string{".agent-context/modules/companyA/00-base.md", ".agent-context/modules/personal/00-base.md"} {
		if _, ok := files[path]; !ok {
			t.Fatalf("referenced form must materialize %s", path)
		}
	}
	if !strings.Contains(files["CLAUDE.md"], "@.agent-context/modules/personal/00-base.md\n") {
		t.Fatal("claude_code reference parts must use the @path line")
	}
	if strings.Contains(files["CLAUDE.md"], "Personal overlay context") {
		t.Fatal("module bytes must not be inlined in the referenced root file")
	}
}

func TestEnvironmentOpencodeConfigIsExactCCJ1WithTrailingLF(t *testing.T) {
	_, files := environmentRootContextFiles(environmentFixtureClosure("companyA"), "opencode", "referenced", defaultPrecedence)
	want := `{"instructions":[".agent-context/modules/companyA/00-base.md",".agent-context/modules/companyA/10-style.md"]}` + "\n"
	if files["opencode.json"] != want {
		t.Fatalf("managed opencode.json bytes drifted: %q", files["opencode.json"])
	}
	if files["AGENTS.md"] != environmentHeader(environmentFixtureClosure("companyA"), defaultPrecedence) {
		t.Fatal("the opencode referenced root file must be the header part alone")
	}
	_, empty := environmentRootContextFiles(environmentFixtureClosure("emptyoverlay"), "opencode", "referenced", defaultPrecedence)
	if empty["opencode.json"] != `{"instructions":[]}`+"\n" {
		t.Fatalf("zero-module managed opencode.json bytes drifted: %q", empty["opencode.json"])
	}
}

func TestEnvironmentSystemPromptOutputHasNoHeader(t *testing.T) {
	written, files := environmentSystemPromptFiles(environmentFixtureClosure("companyA", "personal"), "claude_code", defaultPrecedence)
	if !written {
		t.Fatal("applicable system modules must produce the system-prompt file")
	}
	want := "You are the companyA reviewer.\n\nPrefer short answers.\n"
	if files[environmentSystemPromptPath] != want {
		t.Fatalf("system-prompt output drifted: %q", files[environmentSystemPromptPath])
	}
	if strings.Contains(files[environmentSystemPromptPath], environmentHeaderMarker) || strings.Contains(files[environmentSystemPromptPath], "## Context:") {
		t.Fatal("system-prompt output must carry neither the generation header nor chapter parts")
	}
	// Emitted order applies to system modules too: under lower-weight the
	// overlay's module comes first.
	_, reversed := environmentSystemPromptFiles(environmentFixtureClosure("companyA", "personal"), "claude_code", precedencePolicy{winnerLowerWeight, placementWinnerLast})
	if reversed[environmentSystemPromptPath] != "Prefer short answers.\n\nYou are the companyA reviewer.\n" {
		t.Fatalf("system-prompt order must follow the emitted order: %q", reversed[environmentSystemPromptPath])
	}
	if written, _ := environmentSystemPromptFiles(environmentFixtureClosure("selective"), "codex_cli", defaultPrecedence); written {
		t.Fatal("a selector-excluded system module must leave the file absent")
	}
}

func TestEnvironmentMCPBytesPerAdapter(t *testing.T) {
	closure := environmentFixtureClosure("companyA", "figma-devmode", "docs-remote", "codex-only")
	written, files := environmentMCPFiles(closure, "claude_code")
	if !written {
		t.Fatal("claude_code MCP set is non-empty")
	}
	wantClaude := `{"mcpServers":{"docs-remote":{"type":"http","url":"https://mcp.example.com/docs"},"figma-devmode":{"args":["-y","figma-developer-mcp","--stdio"],"command":"npx","type":"stdio"}}}` + "\n"
	if files[".agent-context/mcp/claude_code.json"] != wantClaude {
		t.Fatalf("claude_code MCP bytes drifted: %q", files[".agent-context/mcp/claude_code.json"])
	}
	_, files = environmentMCPFiles(closure, "codex_cli")
	wantCodex := "[mcp_servers.codex-only]\ncommand = \"uvx\"\nargs = []\n[mcp_servers.figma-devmode]\ncommand = \"npx\"\nargs = [\"-y\", \"figma-developer-mcp\", \"--stdio\"]\n"
	if files[environmentCodexMCPPath] != wantCodex {
		t.Fatalf("codex_cli MCP bytes drifted: %q", files[environmentCodexMCPPath])
	}
	_, files = environmentMCPFiles(closure, "opencode")
	wantOpencode := `{"mcp":{"docs-remote":{"type":"remote","url":"https://mcp.example.com/docs"},"figma-devmode":{"command":["npx","-y","figma-developer-mcp","--stdio"],"type":"local"}}}` + "\n"
	if files[".agent-context/mcp/opencode.json"] != wantOpencode {
		t.Fatalf("opencode MCP bytes drifted: %q", files[".agent-context/mcp/opencode.json"])
	}
	if written, _ := environmentMCPFiles(closure, "pi"); written {
		t.Fatal("pi has no MCP file")
	}
	if written, _ := environmentMCPFiles(environmentFixtureClosure("companyA"), "claude_code"); written {
		t.Fatal("an empty resolved set writes no file")
	}
	if got := environmentEnvNames(closure, "claude_code"); !reflect.DeepEqual(got, []string{"DOCS_ORG", "DOCS_TOKEN", "FIGMA_API_KEY"}) {
		t.Fatalf("env_names union must be sorted: %v", got)
	}
	if got := environmentEnvNames(closure, "codex_cli"); !reflect.DeepEqual(got, []string{"FIGMA_API_KEY"}) {
		t.Fatalf("codex env_names must exclude servers outside its set: %v", got)
	}
	if tomlBasicString("a\"b\\c\n") != `"a\"b\\c\n"` {
		t.Fatalf("TOML basic string escaping drifted: %s", tomlBasicString("a\"b\\c\n"))
	}
}

func TestEnvironmentLockIsSortedAndHashed(t *testing.T) {
	closure := environmentFixtureClosure("companyA", "figma-devmode", "docs-remote", "personal")
	lock := environmentLock(closure)
	members := lock["members"].([]any)
	var keys []string
	for _, member := range members {
		entry := member.(map[string]any)
		keys = append(keys, entry["kind"].(string)+"|"+entry["name"].(string))
	}
	if !sort.StringsAreSorted(keys) {
		t.Fatalf("lock members must be sorted by (kind, name): %v", keys)
	}
	var root map[string]any
	for _, member := range members {
		if member.(map[string]any)["name"] == "companyA" {
			root = member.(map[string]any)
		}
		if member.(map[string]any)["name"] == "docs-remote" && !reflect.DeepEqual(member.(map[string]any)["required_by"], []any{"companyA"}) {
			t.Fatal("mcp members are required by the root")
		}
	}
	if len(root["required_by"].([]any)) != 0 || root["overlay"] != false {
		t.Fatal("the root has no requirers and is not an overlay")
	}
	if lockHash(lock) != canonicalSHA256(lock) {
		t.Fatal("lock hash must be sha256 over the CCJ-1 bytes")
	}
	// The header binds the lock hash: a different lock is a different header.
	other := environmentFixtureClosure("companyA", "personal")
	if environmentHeader(closure, defaultPrecedence) == environmentHeader(other, defaultPrecedence) {
		t.Fatal("headers of different locks must differ")
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
		if strings.HasPrefix(schema, "profilefile-v1") || strings.HasPrefix(schema, "context-manifest-v1") {
			t.Fatalf("withdrawn schema %s still has cases", schema)
		}
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
		"agent-context-v1.schema.json":            agentContextSchemaExamples(validAgentContextV1()),
		"agent-mcp-v1.schema.json":                agentMCPSchemaExamples(validAgentMCPV1()),
		"context-lock-v1.schema.json":             contextLockSchemaExamples(validContextLockV1()),
		"agent-environment-marker-v1.schema.json": environmentMarkerSchemaExamples(validEnvironmentMarkerV1()),
		"launch-env-fragment-v1.schema.json":      launchEnvFragmentSchemaExamples(validLaunchEnvFragmentV1()),
	} {
		requireCase(schema, "valid.json", true)
		requireCase(schema, "invalid.json", false)
		positives, negatives := 0, 0
		for _, example := range examples {
			requireCase(schema, example.name+".json", example.valid)
			if example.valid {
				positives++
			} else {
				negatives++
			}
			if strings.HasPrefix(example.name, "valid-") != example.valid {
				t.Fatalf("schema case %s for %s is misnamed for its validity", example.name, schema)
			}
		}
		if positives < 3 || negatives < 8 {
			t.Fatalf("%s needs positive and negative cases per closed member, got %d/%d", schema, positives, negatives)
		}
		found := false
		for _, example := range examples {
			if strings.Contains(example.name, "unknown-field") {
				found = true
			}
		}
		if !found {
			t.Fatalf("%s has no unknown-member rejection case", schema)
		}
	}
	for _, withdrawn := range []string{"profilefile-v1.schema.json", "context-manifest-v1.schema.json"} {
		if _, err := os.Stat(filepath.Join(root, "schemas", "v1", withdrawn)); !os.IsNotExist(err) {
			t.Fatalf("withdrawn schema %s still exists", withdrawn)
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
