package main

import (
	"bytes"
	"crypto/ed25519"
	"crypto/sha256"
	"encoding/base64"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"runtime"
	"strings"
	"testing"
	"unicode/utf8"
)

const (
	legacyWireBaselineCommit        = "57c1f56846d221ecc55786bd3c2467ec32f11730"
	conformanceClaimV1SchemaSHA256  = "c9f49460618ccc8b1d7d2dfaf760fc6ad3a53a870a6685a685ddc148d3c87b3f"
	conformanceClaimV1ValidSHA256   = "799682489be118331135d91798db90b8d020cbb703207331824ab113f037693c"
	conformanceClaimV1InvalidSHA256 = "de9568757a2bb89c87702e47f6d9c162df24f5ee964f1ef49b9e191ed94b7017"
	// The published marker-v1 legacy-read evidence for the shared golden
	// skill. Writers emit marker schema 2 for schema 1 through 6, so this file
	// is never the writer golden and its bytes stay frozen.
	frozenSharedMarkerV1SHA256 = "80989f850887814ec09c724a7dd891ac7e2422d5fef7e31f330be3554aa9b28a"
	// rc4GoV1ReceiptExampleSHA256 is the accepted rc.4 candidate digest of the
	// generated go-v1 receipt example, recorded so the authorized
	// execution-policy revision can prove it no longer reproduces those bytes.
	rc4GoV1ReceiptExampleSHA256 = "93217cf1ce2965435042f8e20ebfec45498bae67a128cc16f38b3f4c8b64ecab"
	// The repository-root build descriptor is manager-neutral. Schema 7 is
	// unreleased, so the implementation-branded predecessor name is not an
	// alias: it must be absent from every protocol surface. The retired stem
	// is assembled from parts so the absence guard can scan its own source.
	repositoryDescriptorName   = "skill-build.json"
	repositoryDescriptorSchema = "skill-build-v1.schema.json"
	retiredDescriptorStem      = "curator" + "-build"
	// The schema-6 build-source digest algorithm namespace shares that stem
	// but is a different identifier bound into byte-frozen rc.4 artifacts.
	buildSourceAlgorithmNamespace = retiredDescriptorStem + "-source"
	frozenBuildSourceAlgorithm    = buildSourceAlgorithmNamespace + "-v1"
	// The descriptor path is part of the external build input, so the neutral
	// name is a cache-identity revision of the unreleased candidate. These are
	// the exact pre-rename external identities, recorded so the candidate can
	// prove it no longer reproduces them.
	preRenameExternalCacheKey      = "sha256:07dd911a7edc29b906a021aa6e1449632ce91c2e5a3eb0ea4f851cb84fe5c492"
	preRenameExternalReceiptSHA256 = "sha256:11d2bf4df52638ef353b3286c426261eac2a73b0b64a32f85d78c04490072cea"
	// The local go-v1 receipt example carries no descriptor, so the rename
	// must leave its bytes exactly where the execution-policy revision left
	// them.
	localGoV1ReceiptExampleSHA256 = "1a887eb6bb436a3491250b0814dded2a1b1d108640ba67837ba9e89b1183daf3"
	// The build-driver golden suite is carried forward from the accepted
	// schema-6 rc.4 work into rc.5. The build-source and toolchain identities
	// are byte-preserved because neither depends on the execution policy; the
	// cache key and receipt hash are the revised portable rc.5 identities.
	buildDriverCacheKey        = "sha256:529370122ae11e2e961d5265b1a020e046bcd43165b2eb96b05e73a51187ac9b"
	buildDriverReceiptSHA256   = "sha256:919fbbad8e6ce95532219fd952c2309d0d7026f85209650508fd6834af4020cd"
	buildDriverToolchainSHA256 = "sha256:baf7c5f3b9c3f1fae3da4c356381bf74442aa7f8f0b6fb2304c9c10833d6032e"
	buildDriverBuildSourceHash = "sha256:27cdcac0734aa3e069e95a10341e89b118a07c60002516e7b401e95477f01332"
	// The reserved hardened profile and the pre-revision rc.4 shape are the
	// two non-portable go-v1 inputs. Each derives its own key, which is what
	// proves the portable identity is a miss rather than an alias.
	buildDriverHardenedCacheKey = "sha256:13736230d33ce59de7f7323dcd4cffd510655ad8dabd5ee9e8b6cb182ec70037"
	buildDriverLegacyCacheKey   = "sha256:3fcd714a40e8918eb67dbd35d435875dcce6c9047da811a1fa26626e5e57be48"
	// The forged-receipt regression stays internally self-consistent, so its
	// digest moves with the execution-policy revision. This is the rc.5 value;
	// the superseded rc.4 value is recorded next to it so a reader can see the
	// supersession is deliberate.
	buildDriverForgedReceiptSHA256      = "sha256:e15a8b198ddc4b9892747af3fc070713e72b72ad121512f7bdd5919d3581bd6d"
	supersededRC4ForgedReceiptSHA256    = "sha256:9a23f5b77e6173b0f10e7ed43cd2b21aa3b99f3a34945ec432fbb31338a6186d"
	buildDriverEdgeBuildSourceSHA256    = "sha256:68008c9a1131c1295d78f4f7d184c3df5f7382a88d8d40333be7cf02b2ee4de9"
	buildDriverMarkerEmbedLegacySHA256  = "sha256:829a040a1455fdf96e2731aa5c089e7e42dbcec2a51b1db3222a610f0ffb5b35"
	buildDriverNormalizedGoVersionValue = "go version go1.25.5 darwin/arm64"
)

func TestSchemaV7WireSurfacesAreClosedAndVersioned(t *testing.T) {
	root := repositoryRoot(t)
	for _, filename := range []string{
		"agent-skill-v7.schema.json",
		"csk-skill-v7.schema.json",
		"skill-build-v1.schema.json",
		"skillfile-dev-v2.schema.json",
		"build-receipt-v2.schema.json",
		"install-marker-v3.schema.json",
		"conformance-claim-v3.schema.json",
	} {
		schema := readObject(t, filepath.Join(root, "schemas", "v1", filename))
		if schema["additionalProperties"] != false {
			t.Fatalf("%s must reject unknown top-level fields", filename)
		}
	}
	canonical := readObject(t, filepath.Join(root, "schemas", "v1", "agent-skill-v7.schema.json"))
	legacy := readObject(t, filepath.Join(root, "schemas", "v1", "csk-skill-v7.schema.json"))
	delete(canonical, "$id")
	delete(canonical, "title")
	delete(legacy, "$id")
	delete(legacy, "title")
	if !reflect.DeepEqual(canonical, legacy) {
		t.Fatal("agent-skill and csk-skill schema 7 differ beyond identity metadata")
	}

	common := readObject(t, filepath.Join(root, "schemas", "v1", "common.schema.json"))
	defs := common["$defs"].(map[string]any)
	for _, name := range []string{
		"buildRepositoryV1", "repositoryBuildCommandV1", "skillBuildTargetV1",
		"declaredRepositorySourceV1", "effectiveRepositorySourceV1",
		"goRepositoryBuildInputV1", "buildRecordV1WithReceiptVersion", "buildRecordV2",
	} {
		definition := defs[name].(map[string]any)
		if definition["additionalProperties"] != false {
			t.Fatalf("%s must reject unknown fields", name)
		}
	}
	repositoryCommand := defs["repositoryBuildCommandV1"].(map[string]any)
	if got, want := repositoryCommand["required"], []any{"type", "driver", "repository", "target"}; !reflect.DeepEqual(got, want) {
		t.Fatalf("repository command required fields = %#v, want %#v", got, want)
	}
	encoded, err := json.Marshal(map[string]any{"schemas": []any{
		defs["buildRepositoryV1"], defs["repositoryBuildCommandV1"], defs["skillBuildTargetV1"],
	}})
	if err != nil {
		t.Fatal(err)
	}
	for _, forbidden := range []string{"argv", "env", "output", "filename", "credentials", "signing", "hooks", "plugins", "generator", "fallback"} {
		if strings.Contains(string(encoded), `"`+forbidden+`"`) {
			t.Fatalf("schema-7 package-controlled surface exposes forbidden field %q", forbidden)
		}
	}
	skillfileDev := readObject(t, filepath.Join(root, "schemas", "v1", "skillfile-dev-v2.schema.json"))
	if containsValue(skillfileDev["required"].([]any), "build_repository_substitutions") {
		t.Fatal("Skillfile.dev schema 2 must keep build_repository_substitutions optional")
	}
}

// TestRepositoryDescriptorIsManagerNeutral proves the schema-7 candidate binds
// exactly one repository-root descriptor name, that the retired
// implementation-branded name survives nowhere as an alias or a path, and that
// the rename did not reach the byte-frozen schema-6 build-source algorithm
// that happens to share its stem.
func TestRepositoryDescriptorIsManagerNeutral(t *testing.T) {
	root := repositoryRoot(t)

	descriptor := readObject(t, filepath.Join(root, "schemas", "v1", repositoryDescriptorSchema))
	if id, _ := descriptor["$id"].(string); !strings.HasSuffix(id, "/"+repositoryDescriptorSchema) {
		t.Fatalf("descriptor schema $id = %v, want a %s identity", descriptor["$id"], repositoryDescriptorSchema)
	}
	if got, want := descriptor["title"], repositoryDescriptorName+" schema 1"; got != want {
		t.Fatalf("descriptor schema title = %v, want %q", got, want)
	}

	common := readObject(t, filepath.Join(root, "schemas", "v1", "common.schema.json"))
	defs := common["$defs"].(map[string]any)
	if _, ok := defs["skillBuildTargetV1"]; !ok {
		t.Fatal("common schema has no neutral descriptor target definition")
	}
	selection := defs["repositoryDescriptorSelectionV1"].(map[string]any)
	path := selection["properties"].(map[string]any)["path"].(map[string]any)
	if got, want := path["const"], repositoryDescriptorName; got != want {
		t.Fatalf("descriptor selection path const = %v, want %q", got, want)
	}
	if len(path) != 1 {
		t.Fatalf("descriptor selection path must be a bare const, got %#v", path)
	}

	// The generated receipt example and the registry entries agree with the
	// single fixed name.
	receipt := readObject(t, filepath.Join(root, "conformance", "v1", "schema-cases", "build-receipt-v2", "valid.json"))
	source := receipt["input"].(map[string]any)["source"].(map[string]any)
	if got := source["descriptor"].(map[string]any)["path"]; got != repositoryDescriptorName {
		t.Fatalf("generated receipt selects descriptor %v, want %q", got, repositoryDescriptorName)
	}
	var index []map[string]any
	readJSON(t, filepath.Join(root, "conformance", "v1", "schema-cases", "index.json"), &index)
	neutralCases := 0
	for _, item := range index {
		if item["schema"] == repositoryDescriptorSchema {
			neutralCases++
		}
	}
	if neutralCases == 0 {
		t.Fatalf("schema-case index has no %s cases", repositoryDescriptorSchema)
	}

	// Nothing under the repository may name the retired descriptor, and the
	// retired schema artifact and case directory must be gone.
	for _, gone := range []string{
		filepath.Join(root, "schemas", "v1", retiredDescriptorStem+"-v1.schema.json"),
		filepath.Join(root, "conformance", "v1", "schema-cases", retiredDescriptorStem+"-v1"),
	} {
		if _, err := os.Stat(gone); !os.IsNotExist(err) {
			t.Fatalf("retired descriptor path still present: %s", gone)
		}
	}
	frozenAlgorithmSeen := false
	err := filepath.WalkDir(root, func(candidate string, entry os.DirEntry, err error) error {
		if err != nil {
			return err
		}
		name := entry.Name()
		if entry.IsDir() {
			if name == ".git" || name == ".temp" || name == ".venv" || name == "__pycache__" {
				return filepath.SkipDir
			}
			return nil
		}
		if !entry.Type().IsRegular() {
			return nil
		}
		payload, err := os.ReadFile(candidate)
		if err != nil {
			return err
		}
		if !utf8.Valid(payload) {
			return nil
		}
		text := string(payload)
		if strings.Contains(text, frozenBuildSourceAlgorithm) {
			frozenAlgorithmSeen = true
		}
		for offset := 0; ; {
			hit := strings.Index(text[offset:], retiredDescriptorStem)
			if hit < 0 {
				return nil
			}
			hit += offset
			if !strings.HasPrefix(text[hit:], buildSourceAlgorithmNamespace) {
				relative, relErr := filepath.Rel(root, candidate)
				if relErr != nil {
					relative = candidate
				}
				line := strings.Count(text[:hit], "\n") + 1
				t.Fatalf("%s:%d: retired repository descriptor name is not an alias and must be absent", filepath.ToSlash(relative), line)
			}
			offset = hit + 1
		}
	})
	if err != nil {
		t.Fatal(err)
	}
	if !frozenAlgorithmSeen {
		t.Fatalf("frozen schema-6 build-source algorithm %s disappeared", frozenBuildSourceAlgorithm)
	}
}

// TestDescriptorRenameIsACacheIdentityRevision proves the neutral descriptor
// name misses rather than aliases: every external cache key is the exact CCJ-1
// digest of its own input, the pre-rename external identities are no longer
// produced, and local go-v1 builds keep the identities they already had.
func TestDescriptorRenameIsACacheIdentityRevision(t *testing.T) {
	root := repositoryRoot(t)

	receipt := readObject(t, filepath.Join(root, "conformance", "v1", "schema-cases", "build-receipt-v2", "valid.json"))
	input := receipt["input"].(map[string]any)
	key := canonicalSHA256(input)
	if receipt["cache_key"] != key {
		t.Fatalf("receipt v2 cache_key = %v, want SHA-256(CCJ-1(input)) %s", receipt["cache_key"], key)
	}
	if key == preRenameExternalCacheKey {
		t.Fatal("the neutral descriptor name aliases the pre-rename external cache key")
	}

	marker := readObject(t, filepath.Join(root, "conformance", "v1", "expected", "external-repository", "install-marker-v3-mixed.json"))
	builds := marker["builds"].(map[string]any)
	external := builds["golden-tool"].(map[string]any)
	if external["cache_key"] != key {
		t.Fatalf("mixed marker external cache_key = %v, want %s", external["cache_key"], key)
	}
	if external["receipt_sha256"] == preRenameExternalReceiptSHA256 {
		t.Fatal("mixed marker still carries the pre-rename external receipt hash")
	}

	local := filepath.Join(root, "conformance", "v1", "schema-cases", "build-receipt-v1", "valid.json")
	payload, err := os.ReadFile(local)
	if err != nil {
		t.Fatal(err)
	}
	sum := sha256.Sum256(payload)
	if got := hex.EncodeToString(sum[:]); got != localGoV1ReceiptExampleSHA256 {
		t.Fatalf("local go-v1 receipt example changed: digest %s, want %s", got, localGoV1ReceiptExampleSHA256)
	}
}

func TestGeneratedSchemaV7CasesCoverEveryWireBranch(t *testing.T) {
	root := repositoryRoot(t)
	var index []map[string]any
	readJSON(t, filepath.Join(root, "conformance", "v1", "schema-cases", "index.json"), &index)
	required := map[string][]string{
		"agent-skill-v7.schema.json": {
			"valid.json", "valid-sha256-lock.json", "valid-untagged-lock.json", "valid-ssh-source.json",
			"valid-scp-source.json", "valid-unicode-https-source.json", "valid-tag-255-bytes.json",
			"invalid-unselected-repository.json",
			"invalid-missing-repository.json", "invalid-sha1-width.json", "invalid-sha256-width.json",
			"invalid-https-dot-component.json", "invalid-ssh-dot-component.json", "invalid-scp-dot-component.json",
			"invalid-ssh-metacharacter.json", "invalid-ssh-non-ascii.json",
			"invalid-tag-256-bytes.json", "invalid-tag-300-bytes.json",
			"invalid-command-argv.json", "invalid-command-env.json", "invalid-command-output.json",
			"invalid-command-credentials.json", "invalid-command-signing.json", "invalid-command-hooks.json",
			"invalid-command-plugins.json", "invalid-generic-driver.json",
		},
		"skill-build-v1.schema.json": {
			"valid.json", "valid-root-target.json", "valid-contained-target.json",
			"invalid-source-outside-build-root.json", "invalid-output.json", "invalid-argv.json",
			"invalid-environment.json", "invalid-signing.json", "invalid-hook.json", "invalid-plugin.json",
		},
		"skillfile-dev-v2.schema.json": {
			"valid.json", "valid-ordinary-only.json", "valid-empty-build-repository-substitutions.json",
			"valid-populated-build-repository-substitutions.json",
			"valid-network-tag.json", "valid-network-branch.json", "valid-network-sha256-revision.json",
			"invalid-path-and-git.json", "invalid-raw-ref.json", "invalid-output.json", "invalid-credentials.json",
			"invalid-network-branch-256-bytes.json",
			"invalid-target-ownership.json", "invalid-driver-ownership.json", "invalid-command-ownership.json",
		},
		"build-receipt-v2.schema.json": {
			"valid.json", "valid-local-substitution.json", "valid-network-substitution.json",
			"valid-network-sha256-revision.json", "valid-sha256.json", "valid-untagged.json",
			"valid-canonical-uppercase-git-suffix.json",
			"invalid-unsubstituted-substitution.json", "invalid-substituted-without-state.json",
			"invalid-local-substitution-network-identity.json", "invalid-network-substitution-local-identity.json",
			"invalid-effective-commit-width.json", "invalid-output.json", "invalid-argv.json",
			"invalid-unsubstituted-declared-effective-mismatch.json", "invalid-source-outside-build-root.json",
			"invalid-sha1-effective-revision-width.json", "invalid-sha256-effective-revision-width.json",
			"invalid-canonical-lowercase-git-suffix.json", "invalid-canonical-uppercase-host.json",
			"invalid-canonical-dot-component.json",
		},
		"install-marker-v3.schema.json": {
			"valid.json", "valid-empty-builds.json",
			"valid-external-only-substituted.json", "valid-external-only-unsubstituted.json",
			"valid-local-only.json", "valid-network-substitution-tag.json",
			"valid-network-substitution-branch.json", "valid-network-sha1-revision.json",
			"valid-network-sha256-revision.json", "valid-sha256-external.json",
			"valid-untagged-external.json",
			"invalid-missing-local-build-source.json", "invalid-external-only-build-source.json",
			"invalid-local-receipt-version.json", "invalid-external-receipt-version.json",
			"invalid-external-declared-effective-mismatch.json",
			"invalid-marker-local-identity-kind-mismatch.json",
			"invalid-marker-network-identity-kind-mismatch.json",
			"invalid-marker-sha1-effective-revision-width.json",
			"invalid-marker-sha256-effective-revision-width.json",
		},
		"conformance-claim-v3.schema.json": {
			"valid.json", "valid-macos-only.json", "invalid-rc4.json",
			"invalid-duplicate-platform.json", "invalid-generic-driver.json",
			"invalid-language-mismatch.json", "invalid-unknown-field.json",
			"invalid-duplicate-driver-assertion.json", "invalid-driver-platform-outside-claim.json",
		},
	}
	for schema, names := range required {
		got := indexedSchemaCases(index, schema)
		for _, name := range names {
			valid, ok := got[name]
			if !ok {
				t.Fatalf("%s missing generated case %s", schema, name)
			}
			if strings.HasPrefix(name, "invalid-") && valid {
				t.Fatalf("%s case %s must be invalid", schema, name)
			}
			if strings.HasPrefix(name, "valid") && !valid {
				t.Fatalf("%s case %s must be valid", schema, name)
			}
		}
	}
	if got := indexedSchemaCases(index, "csk-skill-v7.schema.json"); !reflect.DeepEqual(got, indexedSchemaCases(index, "agent-skill-v7.schema.json")) {
		t.Fatal("canonical and legacy manifest schema-7 cases differ")
	}
	legacyV7Cases := []string{
		"invalid-v7-build-repositories.json",
		"invalid-v7-top-level-repository.json",
		"invalid-v7-top-level-target.json",
		"invalid-v7-top-level-driver.json",
		"invalid-v7-command-repository.json",
		"invalid-v7-command-target.json",
		"invalid-v7-command-driver.json",
	}
	for _, prefix := range []string{"agent-skill", "csk-skill"} {
		for version := 1; version <= 6; version++ {
			schema := fmt.Sprintf("%s-v%d.schema.json", prefix, version)
			got := indexedSchemaCases(index, schema)
			for _, name := range legacyV7Cases {
				if valid, ok := got[name]; !ok || valid {
					t.Fatalf("%s must carry invalid legacy guard case %s", schema, name)
				}
			}
		}
	}
}

func TestManifestSchemasV1ThroughV6RemainByteStableAndV7Separate(t *testing.T) {
	root := repositoryRoot(t)
	for _, prefix := range []string{"agent-skill", "csk-skill"} {
		for version := 1; version <= 6; version++ {
			schema := readObject(t, filepath.Join(root, "schemas", "v1", fmt.Sprintf("%s-v%d.schema.json", prefix, version)))
			properties := schema["properties"].(map[string]any)
			if _, ok := properties["build_repositories"]; ok {
				t.Fatalf("%s v%d gained schema-7 build_repositories", prefix, version)
			}
			payload, err := json.Marshal(schema)
			if err != nil {
				t.Fatal(err)
			}
			if strings.Contains(string(payload), "go-repository-v1") {
				t.Fatalf("%s v%d gained schema-7 driver semantics", prefix, version)
			}
		}
	}
}

func TestConformanceClaimV2SchemaAndGeneratedCases(t *testing.T) {
	root := repositoryRoot(t)
	claim := readObject(t, filepath.Join(root, "schemas", "v1", "conformance-claim-v2.schema.json"))
	if claim["additionalProperties"] != false {
		t.Fatal("conformance claim v2 must reject unknown fields")
	}
	wantRequired := []any{"schema_version", "protocol_version", "implementation", "implementation_version", "classes", "suite_sha256", "operating_systems", "created_at", "result"}
	if got := claim["required"]; !reflect.DeepEqual(got, wantRequired) {
		t.Fatalf("conformance claim v2 required fields = %#v, want %#v", got, wantRequired)
	}
	properties := claim["properties"].(map[string]any)
	if len(properties) != len(wantRequired) {
		t.Fatalf("conformance claim v2 properties = %#v, want exactly the required fields", properties)
	}
	if properties["schema_version"].(map[string]any)["const"] != json.Number("2") {
		t.Fatalf("conformance claim v2 schema_version is not fixed at 2: %#v", properties["schema_version"])
	}
	if properties["protocol_version"].(map[string]any)["const"] != conformanceClaimV2ProtocolVersion {
		t.Fatalf("conformance claim v2 protocol_version is not fixed at %s: %#v", conformanceClaimV2ProtocolVersion, properties["protocol_version"])
	}
	if properties["result"].(map[string]any)["const"] != "pass" {
		t.Fatalf("conformance claim v2 result is not fixed at pass: %#v", properties["result"])
	}
	for _, field := range []string{"classes", "operating_systems"} {
		if properties[field].(map[string]any)["uniqueItems"] != true {
			t.Fatalf("conformance claim v2 %s must reject duplicates", field)
		}
	}

	var index []map[string]any
	readJSON(t, filepath.Join(root, "conformance", "v1", "schema-cases", "index.json"), &index)
	wantCases := map[string]bool{
		"valid.json":                        true,
		"invalid.json":                      false,
		"invalid-protocol-version-rc3.json": false,
		"invalid-schema-version-1.json":     false,
		"invalid-duplicate-classes.json":    false,
		"invalid-result-fail.json":          false,
		"invalid-unknown-field.json":        false,
	}
	if got := indexedSchemaCases(index, "conformance-claim-v2.schema.json"); !reflect.DeepEqual(got, wantCases) {
		t.Fatalf("conformance claim v2 cases = %#v, want %#v", got, wantCases)
	}

	valid := readObject(t, filepath.Join(root, "conformance", "v1", "schema-cases", "conformance-claim-v2", "valid.json"))
	wantValid := validConformanceClaimV2()
	wantValid["schema_version"] = json.Number("2")
	if !reflect.DeepEqual(valid, wantValid) {
		t.Fatalf("generated conformance claim v2 = %#v, want %#v", valid, wantValid)
	}
	manifest := readObject(t, filepath.Join(root, "conformance", "v1", "manifest.json"))
	if manifest["protocol_version"] != protocolVersion {
		t.Fatalf("generated manifest protocol_version = %v, want %s", manifest["protocol_version"], protocolVersion)
	}
}

// TestRC4CompiledArtifactsRemainByteFrozen guards every rc.4 compiled-build
// artifact whose bytes the authorized execution-policy revision does not
// touch. The go-v1 receipt example is deliberately absent: its policy object
// gains the portable execution-policy identity, so its bytes and logical cache
// key MUST change. That single intentional change is proved separately by
// TestGoV1ExecutionPolicyRevisionCannotAliasRC4.
func TestRC4CompiledArtifactsRemainByteFrozen(t *testing.T) {
	root := repositoryRoot(t)
	want := map[string]string{
		"schemas/v1/agent-skill-v6.schema.json":                       "982832e410f85e415e16e8f9104c3b9af23f6d846bbfbe5497ff170dde947f6f",
		"schemas/v1/csk-skill-v6.schema.json":                         "2148eafc4fa110311b52f528651424e2f53c69042235338fb2c8b414035eab9c",
		"schemas/v1/build-receipt-v1.schema.json":                     "f673a8815f5a5f752bc5b612f20c4ba63d9e8dcce61f5af6e7afe11b131c7ab9",
		"schemas/v1/install-marker-v2.schema.json":                    "6d7b65dbdf684272815fb0e61cc4eb02103d09dfdd397de948bd836293debeb2",
		"schemas/v1/conformance-claim-v2.schema.json":                 "4c05a97a1aa9f7dafe629a406a853239928413e79e95488ac2b20ebd0c52a38c",
		"conformance/v1/schema-cases/agent-skill-v6/valid.json":       "cf029927b7032aaad2fb17931133a897fc8183cce3d091df7321912ad152d634",
		"conformance/v1/schema-cases/csk-skill-v6/valid.json":         "cf029927b7032aaad2fb17931133a897fc8183cce3d091df7321912ad152d634",
		"conformance/v1/schema-cases/install-marker-v2/valid.json":    "538d12bb89d2d15259bbb378efc9e6496fe7de195af82099da36fd9d7a1e2c73",
		"conformance/v1/schema-cases/conformance-claim-v2/valid.json": "f7e7cc86f33ea03ee9bb4d149e1dba29cf34f5ceaf5504df8a9e91c659a1835f",
	}
	for path, digest := range want {
		payload, err := os.ReadFile(filepath.Join(root, filepath.FromSlash(path)))
		if err != nil {
			t.Fatal(err)
		}
		sum := sha256.Sum256(payload)
		if got := hex.EncodeToString(sum[:]); got != digest {
			t.Fatalf("rc.4 artifact changed from accepted baseline %s: %s digest %s, want %s", legacyWireBaselineCommit, path, got, digest)
		}
	}
}

// TestPublishedRC5ReleaseMetadataRemainsByteFrozen prevents regeneration for a
// later candidate from rewriting the already-published rc.5 release record.
func TestPublishedRC5ReleaseMetadataRemainsByteFrozen(t *testing.T) {
	root := repositoryRoot(t)
	payload, err := os.ReadFile(filepath.Join(root, "release", "1.0.0-rc.5.json"))
	if err != nil {
		t.Fatal(err)
	}
	sum := sha256.Sum256(payload)
	got := "sha256:" + hex.EncodeToString(sum[:])
	if got != rc5ReleaseMetadataSHA256 {
		t.Fatalf("published rc.5 release metadata changed: digest %s, want %s", got, rc5ReleaseMetadataSHA256)
	}
}

func TestRC6ReleaseMetadataRemainsByteFrozen(t *testing.T) {
	root := repositoryRoot(t)
	payload, err := os.ReadFile(filepath.Join(root, "release", "1.0.0-rc.6.json"))
	if err != nil {
		t.Fatal(err)
	}
	sum := sha256.Sum256(payload)
	got := "sha256:" + hex.EncodeToString(sum[:])
	if got != rc6ReleaseMetadataSHA256 {
		t.Fatalf("historical rc.6 release metadata changed: digest %s, want %s", got, rc6ReleaseMetadataSHA256)
	}
}

func TestRC7ReleaseMetadataRemainsByteFrozen(t *testing.T) {
	root := repositoryRoot(t)
	payload, err := os.ReadFile(filepath.Join(root, "release", "1.0.0-rc.7.json"))
	if err != nil {
		t.Fatal(err)
	}
	sum := sha256.Sum256(payload)
	got := "sha256:" + hex.EncodeToString(sum[:])
	if got != rc7ReleaseMetadataSHA256 {
		t.Fatalf("historical rc.7 release metadata changed: digest %s, want %s", got, rc7ReleaseMetadataSHA256)
	}
}

func TestRC8ReleaseMetadataPinsSuiteWithoutClaimFabrication(t *testing.T) {
	root := repositoryRoot(t)
	manifest, err := os.ReadFile(filepath.Join(root, "conformance", "v1", "manifest.json"))
	if err != nil {
		t.Fatal(err)
	}
	sum := sha256.Sum256(manifest)
	manifestIdentity := "sha256:" + hex.EncodeToString(sum[:])
	metadata := readObject(t, filepath.Join(root, "release", "1.0.0-rc.8.json"))
	if metadata["protocol_version"] != protocolVersion {
		t.Fatalf("rc.8 release protocol_version = %v, want %s", metadata["protocol_version"], protocolVersion)
	}
	pin := metadata["candidate_protocol_pin"].(map[string]any)
	downstream := metadata["downstream_consumption"].(map[string]any)
	if pin["manifest_sha256"] != manifestIdentity || downstream["required_manifest_sha256"] != manifestIdentity {
		t.Fatalf("rc.8 release does not pin manifest %s", manifestIdentity)
	}
	history := metadata["historical_release"].(map[string]any)
	if history["protocol_version"] != "1.0.0-rc.7" ||
		history["metadata_sha256"] != rc7ReleaseMetadataSHA256 ||
		history["source_commit"] != rc7SourceCommit ||
		history["immutable"] != true {
		t.Fatalf("rc.8 historical rc.7 identity is invalid: %#v", history)
	}
	claim := metadata["claim_v4"].(map[string]any)
	claims, ok := claim["claims_emitted"].([]any)
	if claim["claim_protocol_version"] != protocolVersion ||
		!ok || len(claims) != 0 {
		t.Fatalf("rc.8 release fabricates claim evidence: %#v", claim)
	}
}

func TestAssuranceModesAreClosedFailClosedAndNonAliasing(t *testing.T) {
	root := repositoryRoot(t)
	vector := readObject(t, filepath.Join(root, "conformance", "v1", "vectors", "assurance-modes.json"))
	platforms := vector["platforms"].([]any)
	if !reflect.DeepEqual(platforms, []any{"linux", "macos", "windows"}) {
		t.Fatalf("provider contract platforms = %#v", platforms)
	}
	policies := vector["policies"].([]any)
	if len(policies) != 2 {
		t.Fatalf("assurance policies = %d, want 2", len(policies))
	}
	portable := policies[0].(map[string]any)
	verified := policies[1].(map[string]any)
	if portable["mode"] != "portable" || portable["default"] != true || portable["provider_contract"] != nil {
		t.Fatalf("portable policy is not the CLI-only default: %#v", portable)
	}
	if verified["mode"] != "verified" || verified["default"] != false || verified["provider_contract"] != verifiedProviderContract {
		t.Fatalf("verified policy is not explicit and provider-backed: %#v", verified)
	}
	identities := vector["cache_identities"].([]any)
	keys := map[string]bool{}
	for _, raw := range identities {
		entry := raw.(map[string]any)
		input := entry["input"]
		want := sha256Identity(canonicalBytes(input))
		if entry["expected_key"] != want {
			t.Fatalf("stale assurance cache key: got %v, want %s", entry["expected_key"], want)
		}
		keys[want] = true
	}
	if len(keys) != 2 {
		t.Fatal("portable and verified cache identities alias")
	}
	for _, raw := range vector["fail_closed_cases"].([]any) {
		entry := raw.(map[string]any)
		if entry["execution_started"] != false || entry["fallback_mode"] != nil {
			t.Fatalf("case is not fail-closed: %#v", entry)
		}
	}
	if claims := vector["release_claims"].([]any); len(claims) != 0 {
		t.Fatalf("rc.8 fabricates verified claims: %#v", claims)
	}
}

// TestGoV1ExecutionPolicyRevisionCannotAliasRC4 proves that the portable
// execution policy is a real cache-identity revision: the generated go-v1
// receipt no longer carries the rc.4 candidate bytes or cache key, its key is
// the exact CCJ-1 digest of its own input, and neither the reserved hardened
// identity nor the pre-revision input can produce the portable key.
func TestGoV1ExecutionPolicyRevisionCannotAliasRC4(t *testing.T) {
	root := repositoryRoot(t)
	path := filepath.Join(root, "conformance", "v1", "schema-cases", "build-receipt-v1", "valid.json")
	payload, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	sum := sha256.Sum256(payload)
	if got := hex.EncodeToString(sum[:]); got == rc4GoV1ReceiptExampleSHA256 {
		t.Fatal("go-v1 receipt example still carries the pre-revision rc.4 bytes")
	}

	receipt := readObject(t, path)
	input, ok := receipt["input"].(map[string]any)
	if !ok {
		t.Fatal("go-v1 receipt example has no input")
	}
	policy, ok := input["policy"].(map[string]any)
	if !ok || policy["execution_policy"] != portableExecutionPolicy {
		t.Fatalf("go-v1 receipt policy does not declare the portable execution policy: %#v", policy)
	}
	portableKey := canonicalSHA256(input)
	if receipt["cache_key"] != portableKey {
		t.Fatalf("go-v1 receipt cache_key = %v, want SHA-256(CCJ-1(input)) %s", receipt["cache_key"], portableKey)
	}
	if portableKey == legacyRC4GoV1CacheKey {
		t.Fatal("portable execution policy aliases the rc.4 candidate cache key")
	}

	legacyKey := canonicalSHA256(legacyRC4GoBuildInputV1())
	if legacyKey != legacyRC4GoV1CacheKey {
		t.Fatalf("pre-revision input key = %s, want the recorded rc.4 key %s", legacyKey, legacyRC4GoV1CacheKey)
	}
	hardened := validGoBuildInputV1()
	hardened["policy"].(map[string]any)["execution_policy"] = reservedHardenedExecutionPolicy
	hardenedKey := canonicalSHA256(hardened)
	for _, other := range []string{legacyKey, hardenedKey} {
		if portableKey == other {
			t.Fatalf("portable cache key aliases %s", other)
		}
	}
	if legacyKey == hardenedKey {
		t.Fatal("pre-revision and reserved hardened cache keys alias each other")
	}
}

func TestExternalRepositoryFixtureMatrixAndExactBytes(t *testing.T) {
	root := repositoryRoot(t)
	fixtures := filepath.Join(root, "conformance", "v1", "fixtures", "external-repository")
	fixtureFiles, err := filepath.Glob(filepath.Join(fixtures, "*.json"))
	if err != nil {
		t.Fatal(err)
	}
	for _, fixture := range fixtureFiles {
		info, err := os.Stat(fixture)
		if err != nil {
			t.Fatal(err)
		}
		if info.Size() > 65_536 {
			t.Fatalf("%s exceeds the 65536-byte shared-fixture limit", filepath.Base(fixture))
		}
	}
	raw := readObject(t, filepath.Join(fixtures, "raw-objects.json"))
	rawCases := namedObjects(t, raw["cases"])
	for _, required := range []string{
		"valid-commit-with-signed-and-extra-headers", "valid-sha256-commit",
		"reject-duplicate-tree-header", "reject-misordered-tree-after-parent",
		"reject-missing-header-message-separator", "valid-signed-annotated-tag",
		"reject-duplicate-object-and-type-headers", "reject-tag-declared-target-type-mismatch",
		"valid-regular-and-executable-files", "reject-symbolic-link",
		"reject-submodule-gitlink", "reject-special-file-mode",
	} {
		if _, ok := rawCases[required]; !ok {
			t.Fatalf("raw-object fixture missing %s", required)
		}
	}
	for name, object := range rawCases {
		content, err := base64.StdEncoding.DecodeString(object["content_base64"].(string))
		if err != nil {
			t.Fatalf("%s content is not base64: %v", name, err)
		}
		if got := gitObjectID(object["object_format"].(string), object["object_type"].(string), content); got != object["object_id"] {
			t.Fatalf("%s object id = %s, want %v", name, got, object["object_id"])
		}
	}

	lfs := readObject(t, filepath.Join(fixtures, "lfs-pointers.json"))
	lfsCases := namedObjects(t, lfs["cases"])
	for name, wantLength := range map[string]int{"cutoff-1023-after-trim": 1023, "cutoff-1024-is-ordinary": 1024} {
		payload, err := base64.StdEncoding.DecodeString(lfsCases[name]["bytes_base64"].(string))
		if err != nil {
			t.Fatal(err)
		}
		if len(payload) != wantLength {
			t.Fatalf("%s bytes = %d, want %d", name, len(payload), wantLength)
		}
	}
	if lfsCases["cutoff-1023-after-trim"]["expected_error"] != "build_repository_git_lfs_unsupported" ||
		lfsCases["cutoff-1024-is-ordinary"]["expected"] != "ordinary-blob" {
		t.Fatal("LFS cutoff fixtures do not straddle the exact 1024-byte boundary")
	}

	packs := readObject(t, filepath.Join(fixtures, "pack-index.json"))
	packCases := namedObjects(t, packs["cases"])
	for _, name := range []string{"valid-empty-pack-v2-sha1", "valid-empty-pack-v3-sha1", "valid-empty-pack-v2-sha256"} {
		item := packCases[name]
		if err := validateEmptyPackIndex(item, item["object_format"].(string), true); err != nil {
			t.Fatalf("%s is not an exact valid pack/index fixture: %v", name, err)
		}
	}

	checksumCase := packCases["reject-index-checksum-mismatch"]
	checksumBase := packCases[checksumCase["base_case"].(string)]
	basePack, _ := hex.DecodeString(checksumBase["pack_hex"].(string))
	baseIndex, _ := hex.DecodeString(checksumBase["index_hex"].(string))
	mutatedPack := append([]byte{}, basePack...)
	mutatedIndex := append([]byte{}, baseIndex...)
	mutation := checksumCase["mutation"].(map[string]any)
	if mutation["target"] != "index" || mutation["operation"] != "xor-byte" ||
		mutation["offset_from_end"] != json.Number("1") || mutation["xor"] != json.Number("1") {
		t.Fatalf("index-checksum mutation is not the exact executable operation: %#v", mutation)
	}
	mutatedIndex[len(mutatedIndex)-1] ^= 1
	casePack, _ := hex.DecodeString(checksumCase["pack_hex"].(string))
	caseIndex, _ := hex.DecodeString(checksumCase["index_hex"].(string))
	differences := 0
	for index := range baseIndex {
		if baseIndex[index] != caseIndex[index] {
			differences++
			if index != len(baseIndex)-1 {
				t.Fatalf("index-checksum fixture mutates byte %d instead of the final checksum byte", index)
			}
		}
	}
	if !bytes.Equal(casePack, mutatedPack) || !bytes.Equal(caseIndex, mutatedIndex) || differences != 1 {
		t.Fatal("index-checksum fixture does not materialize exactly one final-byte XOR")
	}
	if err := validateEmptyPackIndex(checksumCase, "sha1", false); err != nil {
		t.Fatalf("index-checksum fixture does not isolate its declared checksum fault: %v", err)
	}
	if checksumCase["expected_error"] != "build_repository_local_object_format_unsupported" {
		t.Fatalf("index-checksum fixture has unstable error: %v", checksumCase["expected_error"])
	}

	familyCase := packCases["reject-pack-hash-family-mismatch"]
	familyBase := packCases[familyCase["base_case"].(string)]
	familyMutation := familyCase["mutation"].(map[string]any)
	if familyMutation["target"] != "repository_object_format" ||
		familyMutation["operation"] != "replace" ||
		familyMutation["from"] != "sha1" || familyMutation["to"] != "sha256" {
		t.Fatalf("hash-family mutation is not the exact executable operation: %#v", familyMutation)
	}
	if familyCase["fixture_object_format"] != "sha1" || familyCase["object_format"] != "sha256" ||
		familyCase["pack_hex"] != familyBase["pack_hex"] || familyCase["index_hex"] != familyBase["index_hex"] {
		t.Fatalf("hash-family fixture does not preserve exact SHA-1 bytes under a SHA-256 declaration: %#v", familyCase)
	}
	if err := validateEmptyPackIndex(familyCase, "sha1", true); err != nil {
		t.Fatalf("hash-family fixture is not independently valid SHA-1 data: %v", err)
	}
	if err := validateEmptyPackIndex(familyCase, "sha256", true); err == nil {
		t.Fatal("hash-family fixture unexpectedly validates under its declared SHA-256 format")
	}
	if familyCase["expected_error"] != "build_repository_local_object_format_unsupported" {
		t.Fatalf("hash-family fixture has unstable error: %v", familyCase["expected_error"])
	}
}

// TestPortableGoHostExecutionPolicyContract verifies the executable portable
// execution contract: a fixed manager-owned worker graph, the exact mandatory
// controls, honest capability evidence, the six hardened guarantees deferred to
// the follow-up story, closed package influence, and non-aliasing cache
// identities.
func TestPortableGoHostExecutionPolicyContract(t *testing.T) {
	root := repositoryRoot(t)
	vector := readObject(t, filepath.Join(root, "conformance", "v1", "vectors", "go-host-execution-policy.json"))
	if vector["execution_policy"] != portableExecutionPolicy ||
		vector["reserved_hardened_execution_policy"] != reservedHardenedExecutionPolicy ||
		vector["hardened_profile_owner"] != hardenedExecutionOwner {
		t.Fatalf("execution-policy vector does not separate portable from hardened: %#v", vector)
	}
	if got, want := vector["drivers"], []any{"go-repository-v1", "go-v1"}; !reflect.DeepEqual(got, want) {
		t.Fatalf("execution policy drivers = %#v, want %#v", got, want)
	}
	wantGraph := []any{
		"manager-parent", "identity-verified-manager-owned-worker",
		"fingerprinted-goroot-bin-go", "fingerprinted-goroot-pkg-tool-child",
	}
	if !reflect.DeepEqual(vector["process_graph"], wantGraph) {
		t.Fatalf("process graph = %#v, want the fixed four-node graph %#v", vector["process_graph"], wantGraph)
	}

	states := vector["session_states"].([]any)
	positions := map[string]int{}
	for index, raw := range states {
		name := raw.(string)
		if _, duplicate := positions[name]; duplicate {
			t.Fatalf("session state %s appears twice", name)
		}
		positions[name] = index
	}
	for _, ordered := range [][2]string{
		{"parent-native-control-availability-probe", "parent-worker-identity-verification"},
		{"parent-worker-identity-verification", "worker-launch"},
		{"worker-identity-proof-and-nonce-acknowledgement", "worker-control-application-and-evidence"},
		{"worker-control-application-and-evidence", "worker-fixed-go-list"},
		{"worker-fixed-go-list", "parent-complete-package-graph-validation"},
		{"parent-complete-package-graph-validation", "parent-authenticated-build-permit"},
		{"parent-authenticated-build-permit", "worker-fixed-go-build"},
		{"worker-fixed-go-build", "parent-artifact-verification"},
		{"parent-artifact-verification", "parent-post-exec-identity-reverification"},
		{"parent-post-exec-identity-reverification", "worker-domain-teardown"},
	} {
		before, ok := positions[ordered[0]]
		after, present := positions[ordered[1]]
		if !ok || !present || before >= after {
			t.Fatalf("worker session does not order %s before %s: %#v", ordered[0], ordered[1], states)
		}
	}

	controls := namedObjects(t, vector["mandatory_controls"])
	wantMandatory := []string{
		"fixed-offline-vendored-go", "fixed-argument-vectors", "fixed-empty-environment",
		"fixed-manager-selected-process-graph", "identity-verified-manager-owned-worker",
		"pre-launch-worker-identity-verification", "post-exec-identity-reverification",
		"frozen-source-snapshot-integrity", "manager-private-staging-roots",
		"manager-derived-output-path", "bounded-wall-clock-deadline", "bounded-combined-output",
		"bounded-artifact-size", "closed-standard-input-and-descriptors", "worker-domain-teardown",
		"no-artifact-execution", "inventory-native-controls-applied",
		"closed-capability-evidence-record",
	}
	if len(controls) != len(wantMandatory) {
		t.Fatalf("mandatory portable controls = %d, want exactly %d", len(controls), len(wantMandatory))
	}
	for _, required := range wantMandatory {
		control, ok := controls[required]
		if !ok {
			t.Fatalf("mandatory portable control %s is missing", required)
		}
		if control["portable"] != true || control["enforced"] != "always" || control["hardened_guarantee"] != false {
			t.Fatalf("mandatory control %s is not an always-enforced portable control: %#v", required, control)
		}
	}

	inventory, ok := vector["native_control_inventory"].(map[string]any)
	if !ok {
		t.Fatal("execution policy has no native-control inventory")
	}
	if inventory["version"] != nativeControlInventoryVersion || inventory["exhaustive"] != true ||
		inventory["probe_timing"] != "pre-worker-launch" || inventory["probe_scope"] != "per-operation" {
		t.Fatalf("native-control inventory is not the exhaustive versioned authority: %#v", inventory)
	}
	if !reflect.DeepEqual(inventory["platforms"], []any{"macos", "windows"}) ||
		!reflect.DeepEqual(inventory["availability_states"], []any{"available", "unavailable"}) ||
		!reflect.DeepEqual(inventory["unavailable_reasons"], []any{unavailableNativeControlReason}) {
		t.Fatalf("native-control inventory vocabulary is not closed: %#v", inventory)
	}
	native := namedObjects(t, inventory["controls"])
	wantNative := map[string]map[string]string{
		"descendant-domain-termination": {
			"macos": "process-group-and-session-teardown", "windows": "job-object-kill-on-close",
		},
		"active-process-count-limit": {
			"macos": "", "windows": "job-object-active-process-limit",
		},
		"aggregate-memory-limit": {
			"macos": "", "windows": "job-object-process-and-job-memory-limit",
		},
		"per-file-size-limit": {"macos": "rlimit-fsize", "windows": ""},
		"inherited-handle-restriction": {
			"macos":   "close-on-exec-and-explicit-descriptor-release",
			"windows": "explicit-handle-inheritance-list",
		},
	}
	if len(native) != len(wantNative) {
		t.Fatalf("native-control inventory = %d controls, want exactly %d", len(native), len(wantNative))
	}
	for name, mechanisms := range wantNative {
		control, present := native[name]
		if !present {
			t.Fatalf("native control %s is missing from the exhaustive inventory", name)
		}
		if control["applied_when_available"] != true || control["hardened_guarantee"] != false {
			t.Fatalf("native control %s is not an available-only portable control: %#v", name, control)
		}
		platforms, typed := control["platforms"].(map[string]any)
		if !typed || len(platforms) != len(mechanisms) {
			t.Fatalf("native control %s has no exact per-platform availability: %#v", name, control)
		}
		for platform, mechanism := range mechanisms {
			state, closed := platforms[platform].(map[string]any)
			if !closed || len(state) != 3 {
				t.Fatalf("native control %s has no closed %s record: %#v", name, platform, platforms)
			}
			want := map[string]any{
				"availability": "available", "mechanism": mechanism, "unavailable_reason": nil,
			}
			if mechanism == "" {
				want = map[string]any{
					"availability": "unavailable", "mechanism": nil,
					"unavailable_reason": unavailableNativeControlReason,
				}
			}
			if !reflect.DeepEqual(state, want) {
				t.Fatalf("native control %s %s availability = %#v, want %#v", name, platform, state, want)
			}
		}
	}

	deferred := namedObjects(t, vector["deferred_hardened_guarantees"])
	wantDeferred := []string{
		"total-network-denial", "read-only-source-and-toolchain",
		"private-build-root-only-writes", "hard-aggregate-descendant-resource-bounds",
		"exact-executable-allowlisting", "fail-closed-capability-preflight",
	}
	if len(deferred) != len(wantDeferred) {
		t.Fatalf("deferred hardened guarantees = %d, want exactly %d", len(deferred), len(wantDeferred))
	}
	for _, required := range wantDeferred {
		guarantee, ok := deferred[required]
		if !ok {
			t.Fatalf("hardened guarantee %s is not deferred", required)
		}
		if guarantee["deferred_to"] != hardenedExecutionOwner ||
			guarantee["portable_profile_claims"] != false ||
			guarantee["rejects_portable_build"] != false {
			t.Fatalf("hardened guarantee %s is not honestly deferred: %#v", required, guarantee)
		}
	}

	influence := namedObjects(t, vector["package_influence_cases"])
	for _, required := range []string{
		"package-selected-executable", "package-selected-argv", "package-selected-environment",
		"package-selected-output-path", "package-selected-flags", "package-selected-hooks",
		"package-selected-plugins", "package-selected-generators",
	} {
		item, ok := influence[required]
		if !ok {
			t.Fatalf("package-influence case %s is missing", required)
		}
		if item["manifest_field"] != nil || item["descriptor_field"] != nil {
			t.Fatalf("%s is expressible in a closed package surface: %#v", required, item)
		}
		if item["expected_error"] != "build_execution_package_influence_forbidden" ||
			item["worker_started"] != false || item["compiler_started"] != false || item["published"] != false {
			t.Fatalf("%s does not fail before the worker and the compiler: %#v", required, item)
		}
	}

	identity := namedObjects(t, vector["identity_and_protocol_cases"])
	for _, required := range []string{
		"pre-launch-identity-mismatch", "worker-executable-symlink-substitution",
		"worker-executable-replaced-between-checks", "worker-identity-proof-mismatch",
		"post-build-toolchain-identity-mismatch", "post-build-source-snapshot-mutated",
		"unexpected-program-started-below-the-worker",
		"build-permit-before-complete-list-validation",
		"replayed-session-nonce", "out-of-order-protocol-message", "oversize-protocol-message",
		"unknown-protocol-message-kind", "second-build-request-in-one-session",
		"mandatory-control-cannot-be-applied",
	} {
		item, ok := identity[required]
		if !ok {
			t.Fatalf("identity/protocol case %s is missing", required)
		}
		if item["published"] != false {
			t.Fatalf("%s publishes despite a rejected execution boundary: %#v", required, item)
		}
		code, _ := item["expected_error"].(string)
		if !strings.HasPrefix(code, "build_execution_") {
			t.Fatalf("%s does not use a stable execution diagnostic: %#v", required, item)
		}
	}
	for _, beforeWorker := range []string{
		"pre-launch-identity-mismatch", "worker-executable-symlink-substitution",
		"mandatory-control-cannot-be-applied",
	} {
		if identity[beforeWorker]["worker_started"] != false {
			t.Fatalf("%s must fail before the worker starts: %#v", beforeWorker, identity[beforeWorker])
		}
	}
	for _, beforeCompiler := range []string{
		"build-permit-before-complete-list-validation", "replayed-session-nonce",
		"out-of-order-protocol-message", "oversize-protocol-message", "unknown-protocol-message-kind",
	} {
		if identity[beforeCompiler]["compiler_started"] != false {
			t.Fatalf("%s must fail before the compiler starts: %#v", beforeCompiler, identity[beforeCompiler])
		}
	}

	assertCapabilityEvidenceRecord(t, vector, native, deferred)

	evidence := namedObjects(t, vector["capability_evidence_cases"])
	wantEvidence := []string{
		"available-native-control-is-applied", "unavailable-native-control-does-not-reject",
		"capability-evidence-is-not-cache-input",
		"unavailable-control-cannot-be-reported-as-applied",
		"available-control-cannot-be-reported-as-unavailable",
		"unknown-native-control-is-rejected", "missing-native-control-entry-is-rejected",
		"duplicate-native-control-entry-is-rejected",
		"unknown-evidence-record-version-is-rejected",
		"hardened-guarantee-claimed-under-portable-policy",
		"hardened-execution-policy-in-evidence-record",
	}
	if len(evidence) != len(wantEvidence) {
		t.Fatalf("capability-evidence cases = %d, want exactly %d", len(evidence), len(wantEvidence))
	}
	for _, name := range wantEvidence {
		item, present := evidence[name]
		if !present {
			t.Fatalf("capability-evidence case %s is missing", name)
		}
		if item["changes_cache_key"] != false {
			t.Fatalf("capability evidence %s leaks into cache identity: %#v", name, item)
		}
		valid, boolean := item["record_valid"].(bool)
		if !boolean || item["build_permitted"] != valid || (item["expected_error"] == nil) != valid {
			t.Fatalf("capability evidence %s does not bind its verdict to record validity: %#v", name, item)
		}
		control, _ := item["control"].(string)
		_, inInventory := native[control]
		if item["in_inventory"] != inInventory {
			t.Fatalf("capability evidence %s misstates inventory membership: %#v", name, item)
		}
		_, isDeferred := deferred[control]
		var want any
		switch {
		case isDeferred || item["record_execution_policy"] != portableExecutionPolicy:
			want = "build_execution_hardened_claim_forbidden"
		case !inInventory || fmt.Sprint(item["entry_count"]) != "1" ||
			item["record_version"] != capabilityEvidenceRecordVersion ||
			(item["availability"] == "available" && item["status"] != "applied") ||
			(item["availability"] == "unavailable" && item["status"] != "unavailable"):
			want = "build_execution_capability_evidence_invalid"
		}
		if item["expected_error"] != want {
			t.Fatalf("capability evidence %s expects %v, want %v", name, item["expected_error"], want)
		}
		if item["expected_error"] == "build_execution_control_unavailable" {
			t.Fatalf("capability evidence %s turns reporting state into a mandatory rejection: %#v", name, item)
		}
	}
	unavailable := evidence["unavailable-native-control-does-not-reject"]
	if unavailable["availability"] != "unavailable" || unavailable["status"] != "unavailable" ||
		unavailable["build_permitted"] != true || unavailable["expected_error"] != nil {
		t.Fatalf("an unavailable inventory control must not reject a portable build: %#v", unavailable)
	}

	assertExecutionFailureBoundary(t, vector, native, controls, deferred)

	identities := vector["cache_identity"].(map[string]any)
	if identities["aliases"] != false {
		t.Fatal("cache-identity vector does not assert non-aliasing")
	}
	keys := map[string]string{}
	for _, name := range []string{"portable", "reserved_hardened", "legacy_rc4_without_execution_policy"} {
		entry, ok := identities[name].(map[string]any)
		if !ok {
			t.Fatalf("cache identity %s is missing", name)
		}
		input := entry["input"].(map[string]any)
		want := canonicalSHA256(input)
		if entry["cache_key"] != want {
			t.Fatalf("cache identity %s key = %v, want SHA-256(CCJ-1(input)) %s", name, entry["cache_key"], want)
		}
		for other, existing := range keys {
			if existing == want {
				t.Fatalf("cache identity %s aliases %s", name, other)
			}
		}
		keys[name] = want
	}
	if identities["portable"].(map[string]any)["schema_valid"] != true ||
		identities["reserved_hardened"].(map[string]any)["schema_valid"] != false ||
		identities["legacy_rc4_without_execution_policy"].(map[string]any)["schema_valid"] != false {
		t.Fatalf("only the portable execution policy may be schema valid: %#v", identities)
	}
	if keys["legacy_rc4_without_execution_policy"] != legacyRC4GoV1CacheKey {
		t.Fatalf("recorded pre-revision key = %s, want %s", keys["legacy_rc4_without_execution_policy"], legacyRC4GoV1CacheKey)
	}
}

// assertCapabilityEvidenceRecord proves the per-operation reporting record is
// closed: exact fields, exact states, one entry per inventory control, a stated
// probe time, result-only exposure, and exclusion from every hashed identity.
func assertCapabilityEvidenceRecord(t *testing.T, vector map[string]any, native, deferred map[string]map[string]any) {
	t.Helper()
	record, ok := vector["capability_evidence_record"].(map[string]any)
	if !ok {
		t.Fatal("execution policy has no closed capability-evidence record")
	}
	if record["record_version"] != capabilityEvidenceRecordVersion ||
		record["inventory_version"] != nativeControlInventoryVersion ||
		record["entry_cardinality"] != "exactly-one-per-inventory-control" ||
		record["result_only"] != true {
		t.Fatalf("capability-evidence record is not closed and result-only: %#v", record)
	}
	for key, want := range map[string][]any{
		"record_fields":        {"controls", "execution_policy", "platform", "record_version"},
		"control_entry_fields": {"availability", "name", "probed_at", "status"},
		"availability_states":  {"available", "unavailable"},
		"status_states":        {"applied", "unavailable"},
		"probe_timings":        {"pre-worker-launch"},
		"exposed_in":           {"dry-run-plan-result", "install-result", "status-result"},
		"excluded_from":        {"cache-key", "conformance-claim", "install-marker", "receipt"},
	} {
		if !reflect.DeepEqual(record[key], want) {
			t.Fatalf("capability-evidence %s = %#v, want %#v", key, record[key], want)
		}
	}
	rules := map[string]any{}
	for _, raw := range record["consistency_rules"].([]any) {
		rule := raw.(map[string]any)
		rules[rule["rule"].(string)] = rule["expected_error"]
	}
	wantRules := map[string]any{
		"available-control-must-report-status-applied":           "build_execution_capability_evidence_invalid",
		"unavailable-control-must-report-status-unavailable":     "build_execution_capability_evidence_invalid",
		"exactly-one-entry-per-inventory-control":                "build_execution_capability_evidence_invalid",
		"no-entry-outside-the-inventory":                         "build_execution_capability_evidence_invalid",
		"unknown-record-version-is-rejected":                     "build_execution_capability_evidence_invalid",
		"availability-probed-per-operation-before-worker-launch": "build_execution_capability_evidence_invalid",
		"no-deferred-hardened-guarantee-entry":                   "build_execution_hardened_claim_forbidden",
		"record-execution-policy-must-be-the-portable-identity":  "build_execution_hardened_claim_forbidden",
	}
	if !reflect.DeepEqual(rules, wantRules) {
		t.Fatalf("capability-evidence consistency rules = %#v, want %#v", rules, wantRules)
	}

	examples, ok := record["examples"].(map[string]any)
	if !ok || len(examples) != 2 {
		t.Fatalf("capability-evidence record lacks per-platform examples: %#v", record["examples"])
	}
	for _, platform := range []string{"macos", "windows"} {
		example, present := examples[platform].(map[string]any)
		if !present || len(example) != 4 {
			t.Fatalf("%s evidence example is not the closed record: %#v", platform, examples[platform])
		}
		if example["record_version"] != capabilityEvidenceRecordVersion ||
			example["execution_policy"] != portableExecutionPolicy || example["platform"] != platform {
			t.Fatalf("%s evidence example is not portable-policy state: %#v", platform, example)
		}
		entries := example["controls"].([]any)
		if len(entries) != len(native) {
			t.Fatalf("%s evidence example reports %d controls, want %d", platform, len(entries), len(native))
		}
		seen := map[string]bool{}
		for _, raw := range entries {
			entry := raw.(map[string]any)
			if len(entry) != 4 || entry["probed_at"] != "pre-worker-launch" {
				t.Fatalf("%s evidence entry is not the closed shape: %#v", platform, entry)
			}
			name := entry["name"].(string)
			if _, known := native[name]; !known || seen[name] {
				t.Fatalf("%s evidence entry %s is unknown or duplicated", platform, name)
			}
			if _, isDeferred := deferred[name]; isDeferred {
				t.Fatalf("%s evidence example reports the deferred guarantee %s", platform, name)
			}
			seen[name] = true
			availability := native[name]["platforms"].(map[string]any)[platform].(map[string]any)["availability"]
			status := "unavailable"
			if availability == "available" {
				status = "applied"
			}
			if entry["availability"] != availability || entry["status"] != status {
				t.Fatalf("%s evidence entry %s contradicts the inventory: %#v", platform, name, entry)
			}
		}
	}
}

// assertExecutionFailureBoundary proves exactly one portable rejection path: a
// missing mandatory control rejects before the worker, while an unavailable
// inventory control and every deferred hardened guarantee never do.
func assertExecutionFailureBoundary(t *testing.T, vector map[string]any, native, controls, deferred map[string]map[string]any) {
	t.Helper()
	boundary, ok := vector["failure_boundary"].(map[string]any)
	if !ok || len(boundary) != 3 {
		t.Fatalf("the portable failure boundary is not stated exactly once: %#v", vector["failure_boundary"])
	}
	mandatory := boundary["missing_mandatory_portable_control"].(map[string]any)
	if mandatory["rejects_build"] != true ||
		mandatory["expected_error"] != "build_execution_control_unavailable" ||
		mandatory["fails_before"] != "worker-launch" || mandatory["published"] != false {
		t.Fatalf("a missing mandatory portable control does not reject before the worker: %#v", mandatory)
	}
	for _, key := range []string{"unavailable_inventory_native_control", "missing_deferred_hardened_capability"} {
		entry := boundary[key].(map[string]any)
		if entry["rejects_build"] != false || entry["expected_error"] != nil ||
			entry["fails_before"] != nil || entry["published"] != true {
			t.Fatalf("%s is treated as a portable rejection: %#v", key, entry)
		}
	}

	guards := namedObjects(t, vector["deferred_capability_rejection_guards"])
	if len(guards) != len(deferred) {
		t.Fatalf("deferred rejection guards = %d, want %d", len(guards), len(deferred))
	}
	record, _ := vector["capability_evidence_record"].(map[string]any)
	exampleControls := map[string]bool{}
	for _, raw := range record["examples"].(map[string]any) {
		for _, entry := range raw.(map[string]any)["controls"].([]any) {
			exampleControls[entry.(map[string]any)["name"].(string)] = true
		}
	}
	for name, guard := range guards {
		if _, isDeferred := deferred[name]; !isDeferred {
			t.Fatalf("rejection guard %s does not name a deferred hardened guarantee", name)
		}
		if guard["in_mandatory_controls"] != false || guard["in_native_control_inventory"] != false ||
			guard["in_capability_evidence_record"] != false ||
			guard["portable_rejection_code"] != nil || guard["build_permitted_when_absent"] != true {
			t.Fatalf("deferred guarantee %s can reject a portable build: %#v", name, guard)
		}
		_, asMandatory := controls[name]
		_, asNative := native[name]
		if asMandatory || asNative || exampleControls[name] {
			t.Fatalf("deferred guarantee %s also appears as a portable control", name)
		}
	}

	semantics, ok := vector["policy_semantics"].(map[string]any)
	if !ok || len(semantics) != len(deferred) {
		t.Fatalf("portable policy semantics do not answer every deferred guarantee: %#v", vector["policy_semantics"])
	}
	answered := map[string]bool{}
	for key, raw := range semantics {
		entry := raw.(map[string]any)
		if len(entry) != 5 {
			t.Fatalf("policy semantics %s is not the closed shape: %#v", key, entry)
		}
		guarantee, _ := entry["deferred_hardened_guarantee"].(string)
		if _, isDeferred := deferred[guarantee]; !isDeferred || answered[guarantee] {
			t.Fatalf("policy semantics %s does not answer one deferred guarantee: %#v", key, entry)
		}
		answered[guarantee] = true
		for _, field := range []string{"value", "means", "does_not_mean"} {
			if text, typed := entry[field].(string); !typed || text == "" {
				t.Fatalf("policy semantics %s has no exact %s", key, field)
			}
		}
	}
	network := semantics["network"].(map[string]any)
	if network["policy_field"] != "network" || network["value"] != "none" ||
		network["deferred_hardened_guarantee"] != "total-network-denial" {
		t.Fatalf("policy network=none has no stated portable meaning: %#v", network)
	}
}

// TestExecutionPolicyIsBoundIntoReceiptMarkerAndClaim proves the portable
// identity reaches every downstream evidence surface, so a portable artifact
// can never be read as hardened output.
func TestExecutionPolicyIsBoundIntoReceiptMarkerAndClaim(t *testing.T) {
	root := repositoryRoot(t)
	cases := filepath.Join(root, "conformance", "v1", "schema-cases")

	receiptV1 := readObject(t, filepath.Join(cases, "build-receipt-v1", "valid.json"))
	receiptV2 := readObject(t, filepath.Join(root, "conformance", "v1", "expected", "external-repository", "build-receipt-v2.json"))
	for name, receipt := range map[string]map[string]any{"receipt v1": receiptV1, "receipt v2": receiptV2} {
		policy := receipt["input"].(map[string]any)["policy"].(map[string]any)
		if policy["execution_policy"] != portableExecutionPolicy {
			t.Fatalf("%s does not bind the portable execution policy: %#v", name, policy)
		}
		if receipt["cache_key"] != canonicalSHA256(receipt["input"]) {
			t.Fatalf("%s cache key does not cover its execution policy", name)
		}
	}

	marker := readObject(t, filepath.Join(root, "conformance", "v1", "expected", "external-repository", "install-marker-v3-mixed.json"))
	builds := marker["builds"].(map[string]any)
	if len(builds) == 0 {
		t.Fatal("mixed marker has no build records")
	}
	for command, raw := range builds {
		record := raw.(map[string]any)
		if record["execution_policy"] != portableExecutionPolicy {
			t.Fatalf("marker record %s does not record the execution policy: %#v", command, record)
		}
	}

	claim := readObject(t, filepath.Join(cases, "conformance-claim-v3", "valid.json"))
	drivers := claim["build_drivers"].([]any)
	if len(drivers) == 0 {
		t.Fatal("claim v3 example declares no build drivers")
	}
	for _, raw := range drivers {
		driver := raw.(map[string]any)
		if driver["execution_policy"] != portableExecutionPolicy {
			t.Fatalf("claim driver %v does not name its execution policy: %#v", driver["driver"], driver)
		}
	}

	common := readObject(t, filepath.Join(root, "schemas", "v1", "common.schema.json"))
	defs := common["$defs"].(map[string]any)
	closed, ok := defs["goExecutionPolicyV1"].(map[string]any)
	if !ok || closed["const"] != portableExecutionPolicy || len(closed) != 1 {
		t.Fatalf("execution-policy identity is not a single closed constant: %#v", closed)
	}
	for _, def := range []string{"buildRecordV1WithReceiptVersion", "buildRecordV2", "goBuildPolicyV1", "goRepositoryBuildPolicyV1"} {
		record := defs[def].(map[string]any)
		if !containsValue(record["required"].([]any), "execution_policy") {
			t.Fatalf("%s does not require an execution policy: %#v", def, record["required"])
		}
		if record["properties"].(map[string]any)["execution_policy"].(map[string]any)["$ref"] != "#/$defs/goExecutionPolicyV1" {
			t.Fatalf("%s does not reuse the closed execution-policy identity", def)
		}
	}

	// Marker v2 keeps its frozen rc.4 shape; its execution-policy binding is
	// transitive through the cache key and receipt hash it records.
	markerV2 := readObject(t, filepath.Join(root, "schemas", "v1", "install-marker-v2.schema.json"))
	recordRef := markerV2["properties"].(map[string]any)["builds"].(map[string]any)["additionalProperties"].(map[string]any)["$ref"]
	if recordRef != "common.schema.json#/$defs/buildRecordV1" {
		t.Fatalf("marker v2 build record changed shape: %v", recordRef)
	}
	if containsValue(defs["buildRecordV1"].(map[string]any)["required"].([]any), "execution_policy") {
		t.Fatal("frozen marker v2 build record must not gain an execution-policy field")
	}
}

func TestExternalRepositoryBehaviorCoverageAndOrdering(t *testing.T) {
	root := repositoryRoot(t)
	vectors := filepath.Join(root, "conformance", "v1", "vectors")
	acquisition := readObject(t, filepath.Join(vectors, "external-repository-acquisition.json"))
	acquisitionCases := namedObjects(t, acquisition["cases"])
	for _, required := range []string{
		"sha1-untagged-https", "sha256-untagged-https", "sha1-tagged-https",
		"sha256-tagged-ssh", "tag-moved", "tag-missing", "tag-malformed-object",
		"untagged-missing-object", "network-substitution-revision",
		"network-substitution-tag", "network-substitution-branch",
		"malformed-ref-rejected-before-git",
	} {
		if _, ok := acquisitionCases[required]; !ok {
			t.Fatalf("acquisition vectors missing %s", required)
		}
	}
	for _, name := range []string{"tag-moved", "tag-missing", "tag-malformed-object"} {
		item := acquisitionCases[name]
		if item["direct_oid_fetch_attempted"] != false || item["audit_started"] != false ||
			item["artifact_cache_lookup"] != false || item["compiler_started"] != false {
			t.Fatalf("%s violates exact-tag fail-before-audit/cache/compiler ordering: %#v", name, item)
		}
	}

	lifecycle := readObject(t, filepath.Join(vectors, "external-repository-lifecycle.json"))
	order := lifecycle["whole_snapshot_order"].([]any)
	position := map[string]int{}
	for index, raw := range order {
		position[raw.(string)] = index
	}
	for _, later := range []string{"artifact-cache-lookup", "compiler"} {
		if position["independent-external-audit"] >= position[later] {
			t.Fatalf("external audit must precede %s: %#v", later, order)
		}
	}
	for field, required := range map[string][]string{
		"cache_cases":            {"verified-cache-hit", "cache-miss", "corrupt-receipt", "corrupt-artifact", "untrusted-protected-boundary", "offline-syntax-only", "offline-install"},
		"source_covering_cases":  {"external-source-dry-run", "external-audit-only"},
		"mixed_build_cases":      {"schema6-local-only", "schema7-local-only", "schema7-external-only", "schema7-mixed", "schema7-substituted-external"},
		"transaction_cases":      {"failure-before-publication", "failure-after-private-stage", "marker-consumer-last", "recovery-uncertain-journal"},
		"status_repair_gc_cases": {"status-current", "status-missing-snapshot", "status-unreadable-protected-state", "repair-reacquires-exact-source", "gc-retains-roots"},
		"path_shim_cases":        {"external-command-shim", "package-path-entry-rejected", "shim-collision-rolls-back"},
		"signing_cases":          {"unsigned-local-build", "package-signing-request", "platform-requires-local-signing", "release-pipeline-signing"},
	} {
		cases := namedObjects(t, lifecycle[field])
		for _, name := range required {
			if _, ok := cases[name]; !ok {
				t.Fatalf("%s missing required case %s", field, name)
			}
		}
	}
	cacheCases := namedObjects(t, lifecycle["cache_cases"])
	sourceCoveringCases := namedObjects(t, lifecycle["source_covering_cases"])
	statusCases := namedObjects(t, lifecycle["status_repair_gc_cases"])
	for _, path := range []struct {
		name            string
		item            map[string]any
		cache, compiler bool
	}{
		{name: "verified cache hit", item: cacheCases["verified-cache-hit"], cache: true},
		{name: "cache miss", item: cacheCases["cache-miss"], cache: true, compiler: true},
		{name: "source-covering dry run", item: sourceCoveringCases["external-source-dry-run"], cache: true},
		{name: "audit-only operation", item: sourceCoveringCases["external-audit-only"]},
		{name: "repair operation", item: statusCases["repair-reacquires-exact-source"], cache: true, compiler: true},
	} {
		if err := validateAuditPath(path.item, position, path.cache, path.compiler); err != nil {
			t.Fatalf("%s ordering is invalid: %v", path.name, err)
		}
	}
	for _, name := range []string{"external-source-dry-run", "external-audit-only"} {
		item := sourceCoveringCases[name]
		if item["source_claimed"] != true || item["audit_claimed"] != true || item["mutation"] != false {
			t.Fatalf("%s is not a non-mutating source-covering proof: %#v", name, item)
		}
	}
	syntaxOnly := cacheCases["offline-syntax-only"]
	for _, field := range []string{"source_claimed", "audit_claimed", "cache_claimed", "mutation"} {
		if syntaxOnly[field] != false {
			t.Fatalf("syntax-only case must not claim %s: %#v", field, syntaxOnly)
		}
	}

	qualification := readObject(t, filepath.Join(vectors, "conformance-claim-v3-qualification.json"))
	if claims := qualification["candidate_claims_emitted"].([]any); len(claims) != 0 {
		t.Fatalf("candidate must not fabricate native platform claims: %#v", claims)
	}
	platforms := namedObjects(t, qualification["platforms"])
	if platforms["linux"]["status"] != "excluded" || platforms["linux"]["until_task"] != "TASK-260728-1skseh" {
		t.Fatalf("Linux qualification boundary is not exact: %#v", platforms["linux"])
	}
}

func TestExternalRepositoryReceiptAndMarkerUseExactCCJ1Hashes(t *testing.T) {
	root := repositoryRoot(t)
	expected := filepath.Join(root, "conformance", "v1", "expected", "external-repository")
	receipt := readObject(t, filepath.Join(expected, "build-receipt-v2.json"))
	marker := readObject(t, filepath.Join(expected, "install-marker-v3-mixed.json"))
	plan := readObject(t, filepath.Join(expected, "mixed-build-plan.json"))
	if err := validateExternalReceiptOracles(receipt, marker, plan); err != nil {
		t.Fatal(err)
	}

	badReceipt := cloneMap(receipt)
	badReceipt["cache_key"] = "sha256:" + strings.Repeat("0", 64)
	if err := validateExternalReceiptOracles(badReceipt, marker, plan); err == nil {
		t.Fatal("receipt oracle validation accepted a false cache key")
	}
	badMarker := cloneMap(marker)
	badMarker["builds"].(map[string]any)["golden-tool"].(map[string]any)["receipt_sha256"] =
		"sha256:" + strings.Repeat("0", 64)
	if err := validateExternalReceiptOracles(receipt, badMarker, plan); err == nil {
		t.Fatal("receipt oracle validation accepted a false marker receipt hash")
	}
}

func TestConformanceClaimV1RemainsByteFrozen(t *testing.T) {
	root := repositoryRoot(t)
	claim := readObject(t, filepath.Join(root, "schemas", "v1", "conformance-claim-v1.schema.json"))
	assertPropertySet(t, "conformance claim v1", claim, []string{
		"schema_version", "protocol_version", "implementation", "implementation_version", "classes",
		"suite_sha256", "operating_systems", "created_at", "result",
	})
	properties := claim["properties"].(map[string]any)
	if properties["schema_version"].(map[string]any)["const"] != json.Number("1") {
		t.Fatalf("conformance claim v1 schema_version changed: %#v", properties["schema_version"])
	}
	if properties["protocol_version"].(map[string]any)["const"] != conformanceClaimV1ProtocolVersion {
		t.Fatalf("conformance claim v1 protocol_version changed: %#v", properties["protocol_version"])
	}

	want := map[string]string{
		filepath.Join("schemas", "v1", "conformance-claim-v1.schema.json"):                         conformanceClaimV1SchemaSHA256,
		filepath.Join("conformance", "v1", "schema-cases", "conformance-claim-v1", "valid.json"):   conformanceClaimV1ValidSHA256,
		filepath.Join("conformance", "v1", "schema-cases", "conformance-claim-v1", "invalid.json"): conformanceClaimV1InvalidSHA256,
	}
	for path, digest := range want {
		payload, err := os.ReadFile(filepath.Join(root, path))
		if err != nil {
			t.Fatal(err)
		}
		if got := sha256.Sum256(payload); hex.EncodeToString(got[:]) != digest {
			t.Fatalf("conformance claim v1 artifact changed: %s", filepath.ToSlash(path))
		}
	}
}

func TestManifestSchemasV1ThroughV5PreserveLegacyBuildBoundary(t *testing.T) {
	root := repositoryRoot(t)
	common := readObject(t, filepath.Join(root, "schemas", "v1", "common.schema.json"))
	defs := common["$defs"].(map[string]any)
	wantCommand := map[string]any{"oneOf": []any{
		map[string]any{"$ref": "#/$defs/scriptCommand"},
		map[string]any{"$ref": "#/$defs/systemCommand"},
	}}
	if !reflect.DeepEqual(defs["command"], wantCommand) {
		t.Fatalf("legacy command union no longer contains only script and system: %#v", defs["command"])
	}
	for definition, commandType := range map[string]string{"scriptCommand": "script", "systemCommand": "system"} {
		command := defs[definition].(map[string]any)
		properties := command["properties"].(map[string]any)
		if command["additionalProperties"] != false || properties["type"].(map[string]any)["const"] != commandType {
			t.Fatalf("%s no longer closes the legacy type %q command shape: %#v", definition, commandType, command)
		}
	}

	for _, manifest := range []string{"agent-skill", "csk-skill"} {
		for version := 1; version <= 5; version++ {
			name := fmt.Sprintf("%s-v%d", manifest, version)
			schema := readObject(t, filepath.Join(root, "schemas", "v1", name+".schema.json"))
			properties := schema["properties"].(map[string]any)
			if properties["schema_version"].(map[string]any)["const"] != json.Number(fmt.Sprint(version)) {
				t.Fatalf("%s schema_version changed: %#v", name, properties["schema_version"])
			}
			if _, ok := properties["build_roots"]; ok {
				t.Fatalf("%s assigns protocol semantics to build_roots", name)
			}
			commands := properties["commands"].(map[string]any)
			if commands["additionalProperties"].(map[string]any)["$ref"] != "common.schema.json#/$defs/command" {
				t.Fatalf("%s does not use the script/system-only command union; type build may be accepted: %#v", name, commands)
			}
			if version == 1 {
				if schema["additionalProperties"] != true {
					t.Fatalf("%s must preserve deployed additionalProperties extension behavior", name)
				}
				continue
			}
			if schema["additionalProperties"] != false {
				t.Fatalf("%s must reject incidental build_roots as an unknown field", name)
			}
		}
	}
}

func TestLegacyManifestSchemaCaseNamesAndValiditySurviveRegeneration(t *testing.T) {
	root := repositoryRoot(t)
	var index []map[string]any
	readJSON(t, filepath.Join(root, "conformance", "v1", "schema-cases", "index.json"), &index)
	want := map[string]bool{
		"valid.json":                           true,
		"invalid.json":                         false,
		"invalid-v7-build-repositories.json":   false,
		"invalid-v7-top-level-repository.json": false,
		"invalid-v7-top-level-target.json":     false,
		"invalid-v7-top-level-driver.json":     false,
		"invalid-v7-command-repository.json":   false,
		"invalid-v7-command-target.json":       false,
		"invalid-v7-command-driver.json":       false,
	}
	for _, manifest := range []string{"agent-skill", "csk-skill"} {
		for version := 1; version <= 5; version++ {
			schema := fmt.Sprintf("%s-v%d.schema.json", manifest, version)
			if got := indexedSchemaCases(index, schema); !reflect.DeepEqual(got, want) {
				t.Fatalf("legacy cases for %s changed during rc.4 regeneration: %#v, want %#v", schema, got, want)
			}
		}
	}
}

func TestManifestV6SchemasHaveCanonicalLegacyParity(t *testing.T) {
	root := repositoryRoot(t)
	canonical := readObject(t, filepath.Join(root, "schemas", "v1", "agent-skill-v6.schema.json"))
	legacy := readObject(t, filepath.Join(root, "schemas", "v1", "csk-skill-v6.schema.json"))

	if got, want := canonical["$id"], "https://relux-works.github.io/curator-spec/schemas/v1/agent-skill-v6.schema.json"; got != want {
		t.Fatalf("canonical $id = %v, want %s", got, want)
	}
	if got, want := canonical["title"], "agent-skill.json schema 6"; got != want {
		t.Fatalf("canonical title = %v, want %s", got, want)
	}
	if got, want := legacy["$id"], "https://relux-works.github.io/curator-spec/schemas/v1/csk-skill-v6.schema.json"; got != want {
		t.Fatalf("legacy $id = %v, want %s", got, want)
	}
	if got, want := legacy["title"], "csk-skill.json schema 6"; got != want {
		t.Fatalf("legacy title = %v, want %s", got, want)
	}
	delete(canonical, "$id")
	delete(canonical, "title")
	delete(legacy, "$id")
	delete(legacy, "title")
	if !reflect.DeepEqual(canonical, legacy) {
		t.Fatal("canonical and legacy v6 schemas differ beyond $id and title")
	}
	if canonical["additionalProperties"] != false {
		t.Fatal("v6 manifest must reject unknown top-level properties")
	}
	if got, want := canonical["required"], []any{"schema_version", "capabilities"}; !reflect.DeepEqual(got, want) {
		t.Fatalf("v6 required fields = %#v, want %#v", got, want)
	}
	properties := canonical["properties"].(map[string]any)
	if properties["schema_version"].(map[string]any)["const"] != json.Number("6") {
		t.Fatalf("v6 schema_version is not fixed at 6: %#v", properties["schema_version"])
	}
	if properties["build_roots"].(map[string]any)["$ref"] != "common.schema.json#/$defs/pathSet" {
		t.Fatalf("v6 build_roots does not use the portable path set: %#v", properties["build_roots"])
	}
	if properties["commands"].(map[string]any)["additionalProperties"].(map[string]any)["$ref"] != "common.schema.json#/$defs/commandV6" {
		t.Fatalf("v6 commands do not use commandV6: %#v", properties["commands"])
	}
	if properties["dependencies"].(map[string]any)["$ref"] != "common.schema.json#/$defs/dependenciesV5" {
		t.Fatalf("v6 dependencies do not preserve v5: %#v", properties["dependencies"])
	}
}

func TestManifestV6CommandUnionIsSeparateAndStrict(t *testing.T) {
	root := repositoryRoot(t)
	common := readObject(t, filepath.Join(root, "schemas", "v1", "common.schema.json"))
	defs := common["$defs"].(map[string]any)

	legacyUnion := map[string]any{"oneOf": []any{
		map[string]any{"$ref": "#/$defs/scriptCommand"},
		map[string]any{"$ref": "#/$defs/systemCommand"},
	}}
	if !reflect.DeepEqual(defs["command"], legacyUnion) {
		t.Fatalf("schemas 1 through 5 command union changed: %#v", defs["command"])
	}
	v6Union := map[string]any{"oneOf": []any{
		map[string]any{"$ref": "#/$defs/scriptCommand"},
		map[string]any{"$ref": "#/$defs/systemCommand"},
		map[string]any{"$ref": "#/$defs/buildCommandV6"},
	}}
	if !reflect.DeepEqual(defs["commandV6"], v6Union) {
		t.Fatalf("v6 command union = %#v, want strict script/system/build union", defs["commandV6"])
	}

	build := defs["buildCommandV6"].(map[string]any)
	if build["additionalProperties"] != false {
		t.Fatal("build command must reject additional properties")
	}
	wantRequired := []any{"type", "driver", "source_dir"}
	if !reflect.DeepEqual(build["required"], wantRequired) {
		t.Fatalf("build required = %#v, want %#v", build["required"], wantRequired)
	}
	properties := build["properties"].(map[string]any)
	if len(properties) != 3 || properties["type"].(map[string]any)["const"] != "build" || properties["driver"].(map[string]any)["const"] != "go-v1" || properties["source_dir"].(map[string]any)["$ref"] != "#/$defs/portablePath" {
		t.Fatalf("build command properties are not the closed v6 surface: %#v", properties)
	}
}

func TestGeneratedManifestV6CasesCoverBuildRejections(t *testing.T) {
	root := repositoryRoot(t)
	var index []map[string]any
	readJSON(t, filepath.Join(root, "conformance", "v1", "schema-cases", "index.json"), &index)

	want := map[string]bool{
		"valid.json":                            true,
		"invalid.json":                          false,
		"invalid-build-missing-driver.json":     false,
		"invalid-build-missing-source-dir.json": false,
		"invalid-build-root-dot.json":           false,
		"invalid-build-source-dir-dot.json":     false,
		"invalid-build-unsupported-driver.json": false,
		"invalid-build-mixed-script.json":       false,
		"invalid-build-mixed-system.json":       false,
	}
	for _, field := range []string{"args", "env", "flags", "hooks", "output", "scripts", "tags", "toolchain"} {
		want["invalid-build-"+field+".json"] = false
	}
	for _, name := range []string{
		"invalid-v7-build-repositories", "invalid-v7-top-level-repository",
		"invalid-v7-top-level-target", "invalid-v7-top-level-driver",
		"invalid-v7-command-repository", "invalid-v7-command-target",
		"invalid-v7-command-driver",
	} {
		want[name+".json"] = false
	}
	for _, schema := range []string{"agent-skill-v6.schema.json", "csk-skill-v6.schema.json"} {
		prefix := strings.TrimSuffix(schema, ".schema.json") + "/"
		got := map[string]bool{}
		for _, item := range index {
			if item["schema"] != schema {
				continue
			}
			instance := strings.TrimPrefix(item["instance"].(string), prefix)
			got[instance] = item["valid"].(bool)
		}
		if !reflect.DeepEqual(got, want) {
			t.Fatalf("%s cases = %#v, want %#v", schema, got, want)
		}
	}

	valid := readObject(t, filepath.Join(root, "conformance", "v1", "schema-cases", "agent-skill-v6", "valid.json"))
	commands := valid["commands"].(map[string]any)
	build := commands["build-tool"].(map[string]any)
	if build["type"] != "build" || build["driver"] != "go-v1" || build["source_dir"] != "build/cmd/tool" || len(build) != 3 {
		t.Fatalf("generated valid build command is not exact: %#v", build)
	}
	if _, ok := commands["script-tool"]; !ok {
		t.Fatal("generated v6 case does not preserve script commands")
	}
	if _, ok := commands["system-tool"]; !ok {
		t.Fatal("generated v6 case does not preserve system commands")
	}
}

func TestManifestSchemasAndCasesV1ThroughV5RemainFrozen(t *testing.T) {
	root := repositoryRoot(t)
	digest := sha256.New()
	for _, prefix := range []string{"agent-skill", "csk-skill"} {
		for version := 1; version <= 5; version++ {
			paths := []string{
				filepath.Join("schemas", "v1", fmt.Sprintf("%s-v%d.schema.json", prefix, version)),
				filepath.Join("conformance", "v1", "schema-cases", fmt.Sprintf("%s-v%d", prefix, version), "valid.json"),
				filepath.Join("conformance", "v1", "schema-cases", fmt.Sprintf("%s-v%d", prefix, version), "invalid.json"),
			}
			for _, path := range paths {
				payload, err := os.ReadFile(filepath.Join(root, path))
				if err != nil {
					t.Fatal(err)
				}
				sum := sha256.Sum256(payload)
				fmt.Fprintf(digest, "%x  %s\n", sum, filepath.ToSlash(path))
			}
		}
	}
	if got, want := hex.EncodeToString(digest.Sum(nil)), "f10e21533825869a0bd61b4b0f6db6c6702d6c2043ea54a4b1e9d54f9f8e7998"; got != want {
		t.Fatalf("v1-v5 wire schemas or generated evidence changed from frozen baseline %s: digest %s, want %s", legacyWireBaselineCommit, got, want)
	}
}

func TestBuildReceiptV1SchemaIsStrictAndPortable(t *testing.T) {
	root := repositoryRoot(t)
	receipt := readObject(t, filepath.Join(root, "schemas", "v1", "build-receipt-v1.schema.json"))
	if receipt["additionalProperties"] != false {
		t.Fatal("build receipt must reject unknown fields")
	}
	if got, want := receipt["required"], []any{"schema_version", "cache_key", "input", "artifact"}; !reflect.DeepEqual(got, want) {
		t.Fatalf("receipt required fields = %#v, want %#v", got, want)
	}
	properties := receipt["properties"].(map[string]any)
	if len(properties) != 4 || properties["schema_version"].(map[string]any)["const"] != json.Number("1") {
		t.Fatalf("receipt top-level surface is not closed schema 1: %#v", properties)
	}
	if properties["cache_key"].(map[string]any)["$ref"] != "common.schema.json#/$defs/sha256" || properties["input"].(map[string]any)["$ref"] != "common.schema.json#/$defs/goBuildInputV1" || properties["artifact"].(map[string]any)["$ref"] != "common.schema.json#/$defs/buildArtifactV1" {
		t.Fatalf("receipt does not use the strict common definitions: %#v", properties)
	}

	common := readObject(t, filepath.Join(root, "schemas", "v1", "common.schema.json"))
	defs := common["$defs"].(map[string]any)
	input := defs["goBuildInputV1"].(map[string]any)
	if input["additionalProperties"] != false {
		t.Fatal("go-v1 build input must reject unknown fields")
	}
	wantInputRequired := []any{"schema_version", "driver", "build_source", "build_root", "command", "source_dir", "target", "toolchain", "policy"}
	if !reflect.DeepEqual(input["required"], wantInputRequired) {
		t.Fatalf("build input required fields = %#v, want %#v", input["required"], wantInputRequired)
	}
	inputProperties := input["properties"].(map[string]any)
	if len(inputProperties) != len(wantInputRequired) || inputProperties["driver"].(map[string]any)["const"] != "go-v1" {
		t.Fatalf("go-v1 build input is not closed: %#v", inputProperties)
	}
	for field, ref := range map[string]string{
		"build_source": "#/$defs/buildSourceIdentity",
		"build_root":   "#/$defs/portablePath",
		"command":      "#/$defs/identifier",
		"source_dir":   "#/$defs/portablePath",
		"target":       "#/$defs/goNativeTargetV1",
		"toolchain":    "#/$defs/goToolchainIdentityV1",
		"policy":       "#/$defs/goBuildPolicyV1",
	} {
		if inputProperties[field].(map[string]any)["$ref"] != ref {
			t.Fatalf("build input %s = %#v, want ref %s", field, inputProperties[field], ref)
		}
	}

	buildSource := defs["buildSourceIdentity"].(map[string]any)
	if buildSource["additionalProperties"] != false || !reflect.DeepEqual(buildSource["required"], []any{"algorithm", "content_sha256"}) {
		t.Fatalf("build source identity is not strict: %#v", buildSource)
	}
	if buildSource["properties"].(map[string]any)["algorithm"].(map[string]any)["const"] != "curator-build-source-v1" {
		t.Fatalf("build source algorithm is not fixed: %#v", buildSource)
	}
	toolchain := defs["goToolchainIdentityV1"].(map[string]any)
	toolchainProperties := toolchain["properties"].(map[string]any)
	if toolchain["additionalProperties"] != false || toolchainProperties["algorithm"].(map[string]any)["const"] != "curator-go-toolchain-v1" || toolchainProperties["go_relpath"].(map[string]any)["const"] != "bin/go" {
		t.Fatalf("toolchain identity is not strict and portable: %#v", toolchain)
	}
	policy := defs["goBuildPolicyV1"].(map[string]any)
	if policy["additionalProperties"] != false || len(policy["properties"].(map[string]any)) != 12 {
		t.Fatalf("go-v1 policy is not fixed: %#v", policy)
	}
	if policy["properties"].(map[string]any)["execution_policy"].(map[string]any)["$ref"] != "#/$defs/goExecutionPolicyV1" {
		t.Fatalf("go-v1 policy does not bind the closed execution-policy identity: %#v", policy)
	}
	if !containsValue(policy["required"].([]any), "execution_policy") {
		t.Fatalf("go-v1 policy does not require an execution policy: %#v", policy)
	}
	artifact := defs["buildArtifactV1"].(map[string]any)
	if artifact["additionalProperties"] != false || !reflect.DeepEqual(artifact["required"], []any{"path", "sha256", "size"}) || len(artifact["properties"].(map[string]any)) != 3 {
		t.Fatalf("receipt artifact is not one closed path/hash/size record: %#v", artifact)
	}

	encoded, err := json.Marshal(map[string]any{"receipt": receipt, "common": common})
	if err != nil {
		t.Fatal(err)
	}
	for _, forbidden := range []string{"trusted", "provenance", "manager_created", "cache_path", "receipt_path", "lock_path"} {
		if strings.Contains(string(encoded), `"`+forbidden+`"`) {
			t.Fatalf("portable receipt schemas expose forbidden field %q", forbidden)
		}
	}
}

func TestInstallMarkerV2SchemaHasConditionalBuildMetadata(t *testing.T) {
	root := repositoryRoot(t)
	marker := readObject(t, filepath.Join(root, "schemas", "v1", "install-marker-v2.schema.json"))
	if marker["additionalProperties"] != false {
		t.Fatal("marker v2 must reject unknown fields")
	}
	required := marker["required"].([]any)
	for _, field := range []any{"build_roots", "builds"} {
		if !containsValue(required, field) {
			t.Fatalf("marker v2 does not require %s: %#v", field, required)
		}
	}
	if containsValue(required, "build_source") {
		t.Fatal("marker v2 cannot unconditionally require build_source")
	}
	properties := marker["properties"].(map[string]any)
	skillVersion := properties["skill_schema_version"].(map[string]any)
	if skillVersion["minimum"] != json.Number("0") || skillVersion["maximum"] != json.Number("6") {
		t.Fatalf("marker v2 skill schema range = %#v, want 0 through 6", skillVersion)
	}
	if properties["build_roots"].(map[string]any)["$ref"] != "common.schema.json#/$defs/pathSet" || properties["build_source"].(map[string]any)["$ref"] != "common.schema.json#/$defs/buildSourceIdentity" {
		t.Fatalf("marker v2 build roots/source are not portable common definitions: %#v", properties)
	}
	builds := properties["builds"].(map[string]any)
	if builds["propertyNames"].(map[string]any)["$ref"] != "common.schema.json#/$defs/identifier" || builds["additionalProperties"].(map[string]any)["$ref"] != "common.schema.json#/$defs/buildRecordV1" {
		t.Fatalf("marker v2 builds are not strict command records: %#v", builds)
	}
	conditionals := marker["allOf"].([]any)
	if len(conditionals) != 1 {
		t.Fatalf("marker v2 conditionals = %#v, want one build-source conditional", conditionals)
	}
	conditional := conditionals[0].(map[string]any)
	if !reflect.DeepEqual(conditional["then"], map[string]any{"required": []any{"build_source"}}) || !reflect.DeepEqual(conditional["else"], map[string]any{"not": map[string]any{"required": []any{"build_source"}}}) {
		t.Fatalf("marker v2 build_source conditional is not exact: %#v", conditional)
	}

	common := readObject(t, filepath.Join(root, "schemas", "v1", "common.schema.json"))
	record := common["$defs"].(map[string]any)["buildRecordV1"].(map[string]any)
	wantRecordRequired := []any{"driver", "cache_key", "receipt_sha256", "artifact_sha256", "artifact_path"}
	if record["additionalProperties"] != false || !reflect.DeepEqual(record["required"], wantRecordRequired) || len(record["properties"].(map[string]any)) != len(wantRecordRequired) {
		t.Fatalf("marker v2 build record is not closed: %#v", record)
	}
}

func TestGeneratedBuildReceiptAndMarkerV2Cases(t *testing.T) {
	root := repositoryRoot(t)
	var index []map[string]any
	readJSON(t, filepath.Join(root, "conformance", "v1", "schema-cases", "index.json"), &index)

	receiptWant := map[string]bool{
		"valid.json": false, "invalid.json": false,
	}
	receiptWant["valid.json"] = true
	for _, name := range []string{
		"invalid-missing-input", "invalid-missing-artifact", "invalid-driver-mismatch",
		"invalid-build-source-algorithm", "invalid-toolchain-algorithm", "invalid-policy-mismatch",
		"invalid-hardened-execution-policy", "invalid-missing-execution-policy",
		"invalid-artifact-hash", "invalid-unknown-input-field", "invalid-self-asserted-trusted",
		"invalid-self-asserted-provenance", "invalid-self-asserted-manager-created",
		"invalid-physical-cache-path", "invalid-physical-receipt-path", "invalid-physical-lock-path",
	} {
		receiptWant[name+".json"] = false
	}
	if got := indexedSchemaCases(index, "build-receipt-v1.schema.json"); !reflect.DeepEqual(got, receiptWant) {
		t.Fatalf("build receipt cases = %#v, want %#v", got, receiptWant)
	}

	markerWant := map[string]bool{"valid.json": true, "invalid.json": false, "valid-empty-builds.json": true, "valid-multiple-builds.json": true}
	for _, name := range []string{
		"invalid-missing-build-roots", "invalid-missing-build-source", "invalid-build-source-with-empty-builds",
		"invalid-unknown-top-level", "invalid-unknown-build-field", "invalid-driver-mismatch",
		"invalid-build-source-algorithm", "invalid-skill-schema-version", "invalid-receipt-hash", "invalid-artifact-path",
	} {
		markerWant[name+".json"] = false
	}
	if got := indexedSchemaCases(index, "install-marker-v2.schema.json"); !reflect.DeepEqual(got, markerWant) {
		t.Fatalf("marker v2 cases = %#v, want %#v", got, markerWant)
	}

	empty := readObject(t, filepath.Join(root, "conformance", "v1", "schema-cases", "install-marker-v2", "valid-empty-builds.json"))
	if _, ok := empty["build_source"]; ok || len(empty["builds"].(map[string]any)) != 0 || len(empty["build_roots"].([]any)) != 0 {
		t.Fatalf("empty-build marker does not omit build_source and retain empty build fields: %#v", empty)
	}
	multiplePath := filepath.Join(root, "conformance", "v1", "schema-cases", "install-marker-v2", "valid-multiple-builds.json")
	multiple := readObject(t, multiplePath)
	if got, want := multiple["build_roots"], []any{"build", "tools"}; !reflect.DeepEqual(got, want) {
		t.Fatalf("generated build_roots = %#v, want sorted %#v", got, want)
	}
	payload, err := os.ReadFile(multiplePath)
	if err != nil {
		t.Fatal(err)
	}
	buildsOffset := strings.Index(string(payload), `"builds": {`)
	if buildsOffset < 0 {
		t.Fatal("generated marker has no builds object")
	}
	buildsPayload := string(payload)[buildsOffset:]
	if strings.Index(buildsPayload, `"alpha-tool"`) >= strings.Index(buildsPayload, `"golden-tool"`) {
		t.Fatal("generated build record keys are not lexically ordered")
	}
}

func TestInstallMarkerV1RemainsByteFrozen(t *testing.T) {
	root := repositoryRoot(t)
	marker := readObject(t, filepath.Join(root, "schemas", "v1", "install-marker-v1.schema.json"))
	assertPropertySet(t, "install marker v1", marker, []string{
		"schema_version", "name", "source", "ref_kind", "ref", "commit", "content_sha256", "locale",
		"agents", "commands", "dependencies", "skill_schema_version", "runtime_roots", "installed_at", "files",
		"git", "requirements", "mcp_servers", "attestation", "activation", "requirers", "substituted",
	})
	properties := marker["properties"].(map[string]any)
	if properties["schema_version"].(map[string]any)["const"] != json.Number("1") || properties["skill_schema_version"].(map[string]any)["maximum"] != json.Number("5") {
		t.Fatalf("install marker v1 historical version bounds changed: %#v", properties)
	}
	for _, field := range []string{"build_roots", "build_source", "builds", "receipt", "receipt_sha256"} {
		if _, ok := properties[field]; ok {
			t.Fatalf("install marker v1 gained build-era field %q", field)
		}
	}

	want := map[string]string{
		filepath.Join("schemas", "v1", "install-marker-v1.schema.json"):                         "aff8070c3e4e77a45aee3fc0b8c21be24d1e7a759a199357698611662cead855",
		filepath.Join("conformance", "v1", "schema-cases", "install-marker-v1", "valid.json"):   "80989f850887814ec09c724a7dd891ac7e2422d5fef7e31f330be3554aa9b28a",
		filepath.Join("conformance", "v1", "schema-cases", "install-marker-v1", "invalid.json"): "c0ea74c822c68409311723a3855eca80ced5ef1801739d4bbfe6ce0916c8d0fa",
	}
	for path, digest := range want {
		payload, err := os.ReadFile(filepath.Join(root, path))
		if err != nil {
			t.Fatal(err)
		}
		if got := sha256.Sum256(payload); hex.EncodeToString(got[:]) != digest {
			t.Fatalf("marker v1 artifact changed: %s", filepath.ToSlash(path))
		}
	}
}

func TestSharedFixturePublishesBothLegacyAndWriterMarkers(t *testing.T) {
	root := repositoryRoot(t)
	expected := filepath.Join(root, "conformance", "v1", "expected")
	legacyPath := filepath.Join(expected, "marker.json")
	writerPath := filepath.Join(expected, "marker-v2.json")

	payload, err := os.ReadFile(legacyPath)
	if err != nil {
		t.Fatal(err)
	}
	if digest := sha256.Sum256(payload); hex.EncodeToString(digest[:]) != frozenSharedMarkerV1SHA256 {
		t.Fatalf("frozen marker-v1 legacy-read evidence changed bytes")
	}

	legacy := readObject(t, legacyPath)
	writer := readObject(t, writerPath)
	if legacy["schema_version"] != json.Number("1") || writer["schema_version"] != json.Number("2") {
		t.Fatalf("shared fixture markers do not carry their own schema identity")
	}
	if writer["skill_schema_version"] != json.Number("5") {
		t.Fatalf("the writer golden describes a different golden skill: %v", writer["skill_schema_version"])
	}
	if roots, ok := writer["build_roots"].([]any); !ok || len(roots) != 0 {
		t.Fatalf("the golden skill declares no build roots: %#v", writer["build_roots"])
	}
	if builds, ok := writer["builds"].(map[string]any); !ok || len(builds) != 0 {
		t.Fatalf("the golden skill activates no compiled command: %#v", writer["builds"])
	}
	if _, ok := writer["build_source"]; ok {
		t.Fatal("build_source is legal only alongside a non-empty builds object")
	}

	delta := map[string]bool{}
	for key := range legacy {
		if !reflect.DeepEqual(legacy[key], writer[key]) {
			delta[key] = true
		}
	}
	for key := range writer {
		if !reflect.DeepEqual(legacy[key], writer[key]) {
			delta[key] = true
		}
	}
	want := map[string]bool{"schema_version": true, "build_roots": true, "builds": true}
	if !reflect.DeepEqual(delta, want) {
		t.Fatalf("the writer golden restates a different installation; it differs in %v", delta)
	}

	derived, err := json.Marshal(sharedFixtureMarkerV2(legacy))
	if err != nil {
		t.Fatal(err)
	}
	published, err := json.Marshal(writer)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(derived, published) {
		t.Fatalf("the published writer golden is not what the generator derives: %s", derived)
	}
}

func TestFixedConfigurationAndEvidenceSchemasRemainByteFrozen(t *testing.T) {
	root := repositoryRoot(t)
	want := map[string]string{
		"manager-config-v1.schema.json":         "8c45cedfd962e27e23dbe8e28a49306d997aeef77f39b8bfc06de81c6ef7c657",
		"system-config-v1.schema.json":          "6a89fb538621f78132a09208ee4cd5c57ea78d530d96596cef15a8814a9f38c3",
		"audit-record-v1.schema.json":           "06c97bcc2562688ac399ba948be25258fa3d3954b29abaf5d972b6e142ed8cb4",
		"registry-bundle-v1.schema.json":        "b02188a5dd17d02a0921d86ccf0ee6650f74482e95dd050829815f8d8adc49c5",
		"registry-log-entry-v1.schema.json":     "62d21c6d0c87097e5fa32217bb2b22035f099007bf5801ec44635680e1fa00ed",
		"registry-meta-response-v1.schema.json": "5aa736ea0d0c3edc78fe99b130ad00def38694e3b94d2b6898a87bf97a028164",
		"registry-snapshot-v1.schema.json":      "6d166071d904c13a93ddf9d84b21fa3377e8bba58df263459f9161f649b031ab",
		"records-response-v1.schema.json":       "041f507e5d37b1e39297f66628af37fbcfa2dd587a2da08bd9a29dc704690087",
		"log-response-v1.schema.json":           "0513f35b75f291c0295dc80cc2c97d390190c38aa7421edb03de94ec17932f86",
		"submission-response-v1.schema.json":    "463e72cc9750340a6d89f14e7407e1b3d7b16f700e3cd913f2933a8d00dd28a5",
		"health-response-v1.schema.json":        "6da2b960e6d8140ba18da2a4f87e5207c406d979b3907ae5bc5716374f9d4e7d",
		"error-response-v1.schema.json":         "06ebd9618eb42ae61e7bcb34959a15e0eb3796bcf44d2b6741b74871d223c0bb",
	}
	for filename, digest := range want {
		payload, err := os.ReadFile(filepath.Join(root, "schemas", "v1", filename))
		if err != nil {
			t.Fatal(err)
		}
		if got := sha256.Sum256(payload); hex.EncodeToString(got[:]) != digest {
			t.Fatalf("fixed configuration/evidence schema changed from frozen baseline %s: %s", legacyWireBaselineCommit, filename)
		}
	}
}

func TestManagerAndSystemConfigV1ExposeNoBuildPolicyOverrides(t *testing.T) {
	root := repositoryRoot(t)
	manager := readObject(t, filepath.Join(root, "schemas", "v1", "manager-config-v1.schema.json"))
	assertPropertySet(t, "manager config v1", manager, []string{
		"schema_version", "skills_root", "default_agents", "preferred_locale", "adapter_mode",
		"worktree_alias_pattern", "projects", "allowed_sources", "audit", "audit_registries",
		"disable_builtin_registries",
	})
	system := readObject(t, filepath.Join(root, "schemas", "v1", "system-config-v1.schema.json"))
	assertPropertySet(t, "system config v1", system, []string{
		"schema_version", "locked", "skills_root", "default_agents", "preferred_locale", "adapter_mode",
		"worktree_alias_pattern", "projects", "allowed_sources", "disable_builtin_registries", "audit",
		"audit_registries",
	})
	for name, schema := range map[string]map[string]any{"manager config v1": manager, "system config v1": system} {
		assertNoDeclaredProperties(t, name, schema, []string{
			"driver", "argv", "args", "environment", "env", "toolchain", "output", "output_path", "output-path",
			"hook", "hooks", "build", "build_policy", "build-policy", "build_policy_override",
			"build-policy-override", "build_policy_overrides", "build-policy-overrides",
		})
	}
}

func TestRegistryAndAuditSchemasRemainSourceEvidenceOnly(t *testing.T) {
	root := repositoryRoot(t)
	wantProperties := map[string][]string{
		"audit-record-v1.schema.json":           {"schema_version", "name", "source_identity", "commit", "content_sha256", "status", "audit", "endorsements", "sig"},
		"registry-bundle-v1.schema.json":        {"schema_version", "records", "snapshot", "public_key"},
		"registry-log-entry-v1.schema.json":     {"seq", "entry_hash", "prev_hash", "record"},
		"registry-meta-response-v1.schema.json": {"name", "version", "public_keys", "record_schema_versions", "policy", "limits"},
		"registry-snapshot-v1.schema.json":      {"schema_version", "merkle_root", "log_size", "head", "version", "created_at", "sig"},
		"records-response-v1.schema.json":       {"records", "next_cursor"},
		"log-response-v1.schema.json":           {"entries", "next_cursor"},
		"submission-response-v1.schema.json":    {"seq", "entry_hash"},
		"health-response-v1.schema.json":        {"status"},
		"error-response-v1.schema.json":         {"error"},
	}
	for filename, want := range wantProperties {
		schema := readObject(t, filepath.Join(root, "schemas", "v1", filename))
		assertPropertySet(t, filename, schema, want)
		assertNoDeclaredProperties(t, filename, schema, []string{
			"artifact", "artifacts", "artifact_path", "artifact_sha256", "attestation", "local_attestation",
			"receipt", "receipts", "receipt_sha256", "receipt_provenance", "provenance", "build_receipt",
			"build_source", "cache_key",
		})
	}

	audit := readObject(t, filepath.Join(root, "schemas", "v1", "audit-record-v1.schema.json"))
	if got, want := audit["required"], []any{"name", "source_identity", "commit", "content_sha256", "status", "sig"}; !reflect.DeepEqual(got, want) {
		t.Fatalf("audit record no longer attests the frozen source identity: required = %#v, want %#v", got, want)
	}
}

func TestManagerLifecycleReusesPortableBuildDriverIdentity(t *testing.T) {
	root := repositoryRoot(t)
	lifecycle := readObject(t, filepath.Join(root, "conformance", "v1", "vectors", "manager-lifecycle.json"))
	buildDrivers := readObject(t, filepath.Join(root, "conformance", "v1", "vectors", "build-drivers.json"))
	fixture := lifecycle["compiled_build_fixture"].(map[string]any)
	identity := buildDrivers["portable_identity"].(map[string]any)

	if lifecycle["schema_version"] != json.Number("1") {
		t.Fatalf("manager lifecycle schema version = %#v, want 1", lifecycle["schema_version"])
	}
	if fixture["source_vector"] != "build-drivers.json#/portable_identity" {
		t.Fatalf("lifecycle fixture does not identify its source vector: %#v", fixture)
	}
	for lifecycleField, buildDriverField := range map[string]string{
		"execution_policy": "execution_policy",
		"build_input":      "build_input",
		"cache_key":        "cache_key",
		"stored_receipt":   "stored_receipt",
		"receipt_sha256":   "receipt_sha256",
		"artifact":         "artifact",
	} {
		if !reflect.DeepEqual(fixture[lifecycleField], identity[buildDriverField]) {
			t.Fatalf("lifecycle %s does not reuse build-driver %s", lifecycleField, buildDriverField)
		}
	}
	buildInput := fixture["build_input"].(map[string]any)
	policy := buildInput["policy"].(map[string]any)
	if fixture["execution_policy"] != portableExecutionPolicy ||
		policy["execution_policy"] != portableExecutionPolicy {
		t.Fatalf("lifecycle fixture is not bound to %q: %#v", portableExecutionPolicy, fixture)
	}
	if fixture["logical_command"] != buildInput["command"] {
		t.Fatalf("lifecycle logical command is inconsistent with the reused input: %#v", fixture)
	}
}

func TestManagerLifecyclePlanningOrderAndCompiledDryRun(t *testing.T) {
	root := repositoryRoot(t)
	vector := readObject(t, filepath.Join(root, "conformance", "v1", "vectors", "manager-lifecycle.json"))

	planning := namedObjects(t, vector["planning_cases"])
	assertNamedSet(t, planning, []string{"all-source-and-trust-gates-before-build"})
	plan := planning["all-source-and-trust-gates-before-build"]
	wantGates := []any{
		"complete-snapshot-tree-validation",
		"dual-manifest-parse-and-schema-validation",
		"runtime-build-root-and-source-dir-validation",
		"static-build-root-context-and-runtime-exclusion",
		"curator-build-source-v1",
		"provider-first-closure",
		"command-shim-portable-and-platform-collision-planning",
		"source-allowlist-and-snapshot-checks",
		"source-audit-policy",
		"trusted-registry-resolution",
		"attestation-revocation-and-moved-tag-policy",
	}
	if got := plan["required_before_toolchain_or_cache"]; !reflect.DeepEqual(got, wantGates) {
		t.Fatalf("compiled planning gate order = %#v, want %#v", got, wantGates)
	}
	then := plan["then"].([]any)
	if !reflect.DeepEqual(then[len(then)-2:], []any{"go-list", "go-build"}) {
		t.Fatalf("source-aware build commands do not follow all planning gates: %#v", then)
	}
	failure := plan["failure_at_any_gate"].(map[string]any)
	if len(failure["go_commands"].([]any)) != 0 || failure["cache_lookup"] != false || len(failure["persistent_mutations"].([]any)) != 0 {
		t.Fatalf("planning gate failure is not side-effect free: %#v", failure)
	}

	orders := namedObjects(t, vector["build_order_cases"])
	assertNamedSet(t, orders, []string{"provider-first-and-lexical-command-order"})
	order := orders["provider-first-and-lexical-command-order"]
	if got, want := order["expected_provider_order"], []any{"data-provider", "ui-provider", "app"}; !reflect.DeepEqual(got, want) {
		t.Fatalf("provider order = %#v, want %#v", got, want)
	}
	if got, want := order["expected_build_order"], []any{
		"data-provider/alpha-tool", "data-provider/zeta-tool", "data-provider/é-tool",
		"ui-provider/beta-tool", "app/golden-tool",
	}; !reflect.DeepEqual(got, want) {
		t.Fatalf("build order = %#v, want %#v", got, want)
	}

	dryRuns := namedObjects(t, vector["dry_run_cases"])
	compiled := dryRuns["compiled-cache-miss-is-read-only"]
	if !reflect.DeepEqual(compiled["allowed_go_commands"], []any{"telemetry-off", "version", "env"}) ||
		!reflect.DeepEqual(compiled["forbidden_go_commands"], []any{"list", "build"}) {
		t.Fatalf("compiled dry-run Go command boundary = %#v", compiled)
	}
	for _, state := range []any{
		"audit-state", "registry-state", "toolchain-probe-memo", "compiled-artifact-cache",
		"project-lock", "cache-build-lock", "manager-home-lock", "journal", "runtime-tree",
		"context-tree", "install-marker", "command-shim", "adapter-ledger", "adapter-mirror",
		"consumer-ledger", "gc-metadata",
	} {
		if !containsValue(compiled["forbidden_persistent_effects"].([]any), state) {
			t.Fatalf("compiled dry-run does not forbid mutation of %q", state)
		}
	}
	if compiled["operation_private_state_after"] != "absent" || compiled["artifact_executed"] != false {
		t.Fatalf("compiled dry-run cleanup/execution outcome = %#v", compiled)
	}
}

func TestManagerLifecyclePrivateBuildPublicationAndCrossProjectIsolation(t *testing.T) {
	root := repositoryRoot(t)
	vector := readObject(t, filepath.Join(root, "conformance", "v1", "vectors", "manager-lifecycle.json"))

	privateBuilds := namedObjects(t, vector["private_build_cases"])
	assertNamedSet(t, privateBuilds, []string{
		"all-misses-stage-and-verify-before-home-lock",
		"second-build-failure-preserves-persistent-state",
	})
	staged := privateBuilds["all-misses-stage-and-verify-before-home-lock"]
	if staged["manager_home_lock_during_build"] != false || len(staged["shared_mutations_before_all_verified"].([]any)) != 0 {
		t.Fatalf("private builds enter shared mutation too early: %#v", staged)
	}
	failed := privateBuilds["second-build-failure-preserves-persistent-state"]
	if failed["persistent_state_before"] != failed["persistent_state_after"] || failed["manager_home_lock_acquired"] != false {
		t.Fatalf("second build failure changed persistent state: %#v", failed)
	}
	if !reflect.DeepEqual(failed["events"], []any{
		"golden-tool-staged-and-verified", "second-tool-go-list-passed", "second-tool-go-build-failed", "operation-private-staging-removed",
	}) {
		t.Fatalf("second build failure trace is ambiguous: %#v", failed["events"])
	}

	publication := namedObjects(t, vector["cache_publication_cases"])
	assertNamedSet(t, publication, []string{
		"publish-complete-immutable-entry-under-home-lock", "concurrent-identical-winner",
		"concurrent-determinism-mismatch", "corrupt-live-entry", "untrusted-cache-boundary",
	})
	if publication["publish-complete-immutable-entry-under-home-lock"]["publication"] != "atomic-complete-directory" ||
		publication["publish-complete-immutable-entry-under-home-lock"]["merge_existing_entry"] != false {
		t.Fatal("protected publication does not require atomic immutable entries")
	}
	if publication["concurrent-identical-winner"]["result"] != "reuse-winner" || publication["concurrent-identical-winner"]["staged_loser"] != "discard" {
		t.Fatal("identical cache race winner is not explicit")
	}
	if publication["concurrent-determinism-mismatch"]["result"] != "determinism-or-corruption-error" || publication["concurrent-determinism-mismatch"]["install_targets_mutated"] != false {
		t.Fatal("cache determinism mismatch outcome is not isolated")
	}
	if publication["corrupt-live-entry"]["result"] != "replace-from-verified-staging" || publication["corrupt-live-entry"]["adopt_or_repair_candidate"] != false {
		t.Fatal("corrupt live cache handling is not explicit")
	}
	if publication["untrusted-cache-boundary"]["result"] != "rebuild-into-new-protected-state" || publication["untrusted-cache-boundary"]["candidate_reused"] != false {
		t.Fatal("untrusted boundary handling is not explicit")
	}

	projects := namedObjects(t, vector["cross_project_cases"])
	assertNamedSet(t, projects, []string{
		"two-project-success-preserves-both-consumers",
		"successful-project-survives-other-project-rollback",
	})
	if got, want := projects["two-project-success-preserves-both-consumers"]["consumer_ledger_after"], []any{"project-alpha", "project-beta"}; !reflect.DeepEqual(got, want) {
		t.Fatalf("two-project consumer ledger = %#v, want %#v", got, want)
	}
	rollback := projects["successful-project-survives-other-project-rollback"]
	if !reflect.DeepEqual(rollback["consumer_ledger_after_rollback"], []any{"project-alpha"}) || rollback["project_alpha_targets_unchanged"] != true {
		t.Fatalf("failed project rollback did not preserve the successful project: %#v", rollback)
	}
}

func TestManagerLifecycleTransactionsRecoveryStatusRepairAndGC(t *testing.T) {
	root := repositoryRoot(t)
	vector := readObject(t, filepath.Join(root, "conformance", "v1", "vectors", "manager-lifecycle.json"))

	transactions := namedObjects(t, vector["transaction_cases"])
	assertNamedSet(t, transactions, []string{
		"deterministic-lock-order", "deterministic-target-order-and-consumer-last", "reverse-rollback-under-home-lock",
	})
	locks := transactions["deterministic-lock-order"]
	if got, want := locks["expected_project_lock_order"], []any{"project-alpha", "project-z", "project-é"}; !reflect.DeepEqual(got, want) {
		t.Fatalf("project lock order = %#v, want %#v", got, want)
	}
	if locks["cache_build_lock_released_before_home_lock"] != true || locks["then_manager_home_lock"] != true {
		t.Fatalf("cache/home lock ordering is incomplete: %#v", locks)
	}
	targets := transactions["deterministic-target-order-and-consumer-last"]
	commitOrder := targets["expected_commit_order"].([]any)
	if commitOrder[len(commitOrder)-1] != "consumer-ledger/machine" || targets["consumer_ledger_committed_last"] != true {
		t.Fatalf("consumer is not last in commit order: %#v", targets)
	}
	rollback := transactions["reverse-rollback-under-home-lock"]
	wantRestore := reverseAny(rollback["commit_order"].([]any))
	if !reflect.DeepEqual(rollback["expected_restore_order"], wantRestore) || rollback["manager_home_lock_held_through_rollback"] != true {
		t.Fatalf("rollback is not reverse and locked: %#v", rollback)
	}

	recovery := namedObjects(t, vector["recovery_cases"])
	assertNamedSet(t, recovery, []string{
		"interrupted-global-journal-recovered-by-transaction-id", "install-recovery-runs-after-private-builds",
	})
	global := recovery["interrupted-global-journal-recovered-by-transaction-id"]
	if global["journal_owner"] != "global" || global["scan_scope"] != "all-incomplete-journals" ||
		!reflect.DeepEqual(global["successful_project_consumers_after"], []any{"project-alpha"}) {
		t.Fatalf("global journal recovery is incomplete: %#v", global)
	}
	if recovery["install-recovery-runs-after-private-builds"]["recovery_before_build"] != false {
		t.Fatal("install recovery is incorrectly modeled as a pre-build pass")
	}

	status := namedObjects(t, vector["status_cases"])
	assertNamedSet(t, status, []string{"compiled-installation-current", "compiled-currentness-failure-matrix"})
	if status["compiled-installation-current"]["result"] != "current" || status["compiled-installation-current"]["artifact_executed"] != false {
		t.Fatal("compiled current status outcome is incomplete")
	}
	wantNonCurrent := []any{
		"missing-raw-snapshot", "context-visible-build-root", "runtime-copied-build-root", "untrusted-cache-boundary",
		"unsupported-driver", "unsupported-toolchain", "corrupt-receipt", "corrupt-artifact", "wrong-native-target",
		"build-source-mismatch", "cache-key-mismatch", "receipt-hash-mismatch", "artifact-path-mismatch", "artifact-hash-mismatch",
	}
	nonCurrent := status["compiled-currentness-failure-matrix"]
	if !reflect.DeepEqual(nonCurrent["independent_conditions"], wantNonCurrent) || len(nonCurrent["mutations"].([]any)) != 0 {
		t.Fatalf("compiled non-current matrix = %#v", nonCurrent)
	}

	repair := namedObjects(t, vector["repair_cases"])
	assertNamedSet(t, repair, []string{"repair-rebuilds-invalid-compiled-entry"})
	rebuild := repair["repair-rebuilds-invalid-compiled-entry"]
	if got, want := rebuild["independent_conditions"], []any{"missing", "corrupt", "wrong-target", "wrong-toolchain", "untrusted-boundary"}; !reflect.DeepEqual(got, want) {
		t.Fatalf("repair matrix = %#v, want %#v", got, want)
	}
	for _, step := range []any{"complete-snapshot-validation", "source-audit", "registry-and-attestation-gates", "operation-private-build", "protected-publication", "journaled-commit"} {
		if !containsValue(rebuild["required_pipeline"].([]any), step) {
			t.Fatalf("repair pipeline misses %q", step)
		}
	}

	gc := namedObjects(t, vector["gc_cases"])
	assertNamedSet(t, gc, []string{"locked-mark-and-sweep-compiled-cache", "post-commit-gc-failure-is-maintenance-warning"})
	sweep := gc["locked-mark-and-sweep-compiled-cache"]
	if sweep["only_lock"] != "manager-home-mutation-lock" || sweep["protected_boundary_revalidated"] != true || sweep["receipt_content_alone_is_live_reference"] != false {
		t.Fatalf("locked GC boundary/reference model = %#v", sweep)
	}
	if sweep["artifact_executed"] != false || sweep["entry_adopted"] != false {
		t.Fatalf("GC executes or adopts cache content: %#v", sweep)
	}
	if gc["post-commit-gc-failure-is-maintenance-warning"]["successful_installation_rolled_back"] != false {
		t.Fatal("post-commit GC warning incorrectly rolls back installation")
	}
}

func TestManagerLifecycleGenerationIsDeterministic(t *testing.T) {
	one := t.TempDir()
	two := t.TempDir()
	writeManagerLifecycleVectors(one)
	writeManagerLifecycleVectors(two)
	left, err := os.ReadFile(filepath.Join(one, "manager-lifecycle.json"))
	if err != nil {
		t.Fatal(err)
	}
	right, err := os.ReadFile(filepath.Join(two, "manager-lifecycle.json"))
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(left, right) {
		t.Fatal("manager lifecycle generation is not deterministic")
	}
}

func TestGeneratedGoBuildFixtureContextAndIdentity(t *testing.T) {
	root := repositoryRoot(t)
	vector := readObject(t, filepath.Join(root, "conformance", "v1", "vectors", "build-drivers.json"))
	fixture := vector["fixture"].(map[string]any)
	if fixture["root"] != "fixtures/go-build-skill" {
		t.Fatalf("build fixture root = %v", fixture["root"])
	}
	wantContext := []any{"SKILL.md", "assets/prompt.md"}
	if got := fixture["expected_context_files"]; !reflect.DeepEqual(got, wantContext) {
		t.Fatalf("build fixture context = %#v, want %#v", got, wantContext)
	}
	excluded := fixture["excluded_context_files"].([]any)
	for _, required := range []any{
		"assets/build-tool/go.mod",
		"assets/build-tool/internal/render/empty.txt",
		"assets/build-tool/internal/render/template.txt",
		"assets/build-tool/vendor/example.com/curator/vendored/decorate/decorate.go",
		"scripts/skill-helper",
	} {
		if !containsValue(excluded, required) {
			t.Fatalf("build fixture exclusion misses %s", required)
		}
	}

	fixtureRoot := filepath.Join(root, "conformance", "v1", "fixtures", "go-build-skill")
	manifest := readObject(t, filepath.Join(fixtureRoot, "agent-skill.json"))
	if manifest["schema_version"] != json.Number("6") || !reflect.DeepEqual(manifest["build_roots"], []any{"assets/build-tool"}) {
		t.Fatalf("fixture manifest does not declare the exact schema-6 build root: %#v", manifest)
	}
	commands := manifest["commands"].(map[string]any)
	if commands["golden-tool"].(map[string]any)["driver"] != "go-v1" || commands["skill-helper"].(map[string]any)["type"] != "script" {
		t.Fatalf("fixture commands do not mix the closed build and script shapes: %#v", commands)
	}
	renderSource, err := os.ReadFile(filepath.Join(fixtureRoot, "assets", "build-tool", "internal", "render", "render.go"))
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Contains(renderSource, []byte("//go:embed template.txt")) || !bytes.Contains(renderSource, []byte("//go:embed empty.txt")) || !bytes.Contains(renderSource, []byte("example.com/curator/vendored/decorate")) {
		t.Fatal("fixture does not contain the transitive embed and vendored dependency")
	}

	preimage, err := os.ReadFile(filepath.Join(root, "conformance", "v1", "expected", "build-driver", "build-source.preimage.bin"))
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.HasPrefix(preimage, []byte(frozenBuildSourceAlgorithm+"\x00")) {
		t.Fatal("build-source preimage lacks its domain prefix")
	}
	identity := fixture["build_source"].(map[string]any)
	if got := sha256Identity(preimage); got != identity["content_sha256"] || got != buildDriverBuildSourceHash {
		t.Fatalf("fixture build-source digest = %s, vector = %v, want %s", got, identity["content_sha256"], buildDriverBuildSourceHash)
	}
	if !bytes.Contains(preimage, []byte(".csk-install.json")) {
		t.Fatal("fixture build-source preimage omits the root marker")
	}
}

func TestBuildDriverPortableIdentityIsByteExact(t *testing.T) {
	root := repositoryRoot(t)
	vector := readObject(t, filepath.Join(root, "conformance", "v1", "vectors", "build-drivers.json"))
	identity := vector["portable_identity"].(map[string]any)
	if identity["execution_policy"] != portableExecutionPolicy {
		t.Fatalf("portable identity execution policy = %v, want %q", identity["execution_policy"], portableExecutionPolicy)
	}
	if identity["cache_key"] != buildDriverCacheKey {
		t.Fatalf("cache key = %v, want %s", identity["cache_key"], buildDriverCacheKey)
	}
	if identity["receipt_sha256"] != buildDriverReceiptSHA256 {
		t.Fatalf("receipt hash = %v, want %s", identity["receipt_sha256"], buildDriverReceiptSHA256)
	}
	policy := identity["build_input"].(map[string]any)["policy"].(map[string]any)
	if policy["execution_policy"] != portableExecutionPolicy {
		t.Fatalf("portable build input does not require the execution policy: %#v", policy)
	}
	inputBytes := canonicalBytes(identity["build_input"])
	if got := string(inputBytes); got != identity["build_input_ccj_utf8"] {
		t.Fatalf("build input CCJ-1 bytes differ: %q != %q", got, identity["build_input_ccj_utf8"])
	}
	if got := sha256Identity(inputBytes); got != buildDriverCacheKey {
		t.Fatalf("build input digest = %s, want %s", got, buildDriverCacheKey)
	}
	receiptBytes := canonicalBytes(identity["stored_receipt"])
	if got := string(receiptBytes); got != identity["stored_receipt_ccj_utf8"] {
		t.Fatalf("stored receipt bytes differ: %q != %q", got, identity["stored_receipt_ccj_utf8"])
	}
	if bytes.HasSuffix(receiptBytes, []byte("\n")) || sha256Identity(receiptBytes) != buildDriverReceiptSHA256 {
		t.Fatal("stored receipt is not exact canonical JSON without a terminal newline")
	}
	for name, want := range map[string][]byte{
		"build-input.ccj.json": inputBytes,
		"receipt.ccj.json":     receiptBytes,
	} {
		payload, err := os.ReadFile(filepath.Join(root, "conformance", "v1", "expected", "build-driver", name))
		if err != nil {
			t.Fatal(err)
		}
		if !bytes.Equal(payload, want) {
			t.Fatalf("expected artifact %s does not carry exact CCJ-1 bytes", name)
		}
	}
	for name, want := range map[string]string{
		"cache-key.txt":           buildDriverCacheKey,
		"receipt-sha256.txt":      buildDriverReceiptSHA256,
		"build-source-sha256.txt": buildDriverBuildSourceHash,
		"toolchain-sha256.txt":    buildDriverToolchainSHA256,
	} {
		payload, err := os.ReadFile(filepath.Join(root, "conformance", "v1", "expected", "build-driver", name))
		if err != nil {
			t.Fatal(err)
		}
		if string(payload) != want+"\n" {
			t.Fatalf("expected artifact %s = %q, want %q", name, payload, want+"\n")
		}
	}
	artifact := identity["artifact"].(map[string]any)
	if artifact["path"] != "bin/golden-tool" || artifact["sha256"] != "sha256:"+strings.Repeat("d", 64) || artifact["size"] != json.Number("1234567") {
		t.Fatalf("artifact identity changed: %#v", artifact)
	}
	marker := identity["marker"].(map[string]any)
	build := marker["builds"].(map[string]any)["golden-tool"].(map[string]any)
	if build["cache_key"] != buildDriverCacheKey || build["receipt_sha256"] != buildDriverReceiptSHA256 || build["artifact_sha256"] != artifact["sha256"] {
		t.Fatalf("marker build identity is inconsistent: %#v", build)
	}
}

// TestBuildDriverCacheIdentityMissesInsteadOfAliasing proves the rc.5 portable
// identity, the reserved hardened profile, and the pre-revision rc.4 shape are
// three distinct keys, that each key is the exact CCJ-1 digest of its own
// stored input, and that only the portable one is schema-valid.
func TestBuildDriverCacheIdentityMissesInsteadOfAliasing(t *testing.T) {
	root := repositoryRoot(t)
	vector := readObject(t, filepath.Join(root, "conformance", "v1", "vectors", "build-drivers.json"))
	identity := vector["cache_identity"].(map[string]any)
	if identity["aliases"] != false {
		t.Fatalf("build-driver cache identity claims aliasing: %#v", identity["aliases"])
	}
	cases := map[string]struct {
		policy any
		key    string
		valid  bool
	}{
		"portable":                            {portableExecutionPolicy, buildDriverCacheKey, true},
		"reserved_hardened":                   {reservedHardenedExecutionPolicy, buildDriverHardenedCacheKey, false},
		"legacy_rc4_without_execution_policy": {nil, buildDriverLegacyCacheKey, false},
	}
	seen := map[string]string{}
	for name, want := range cases {
		entry, ok := identity[name].(map[string]any)
		if !ok {
			t.Fatalf("cache identity has no %s entry", name)
		}
		if entry["execution_policy"] != want.policy {
			t.Fatalf("%s execution policy = %v, want %v", name, entry["execution_policy"], want.policy)
		}
		if entry["schema_valid"] != want.valid {
			t.Fatalf("%s schema_valid = %v, want %v", name, entry["schema_valid"], want.valid)
		}
		derived := canonicalSHA256(entry["input"])
		if derived != entry["cache_key"] || derived != want.key {
			t.Fatalf("%s cache key = %v, derived %s, want %s", name, entry["cache_key"], derived, want.key)
		}
		if previous, duplicate := seen[derived]; duplicate {
			t.Fatalf("%s aliases %s at %s", name, previous, derived)
		}
		seen[derived] = name
	}
	if identity["reserved_hardened"].(map[string]any)["hardened_profile_owner"] != hardenedExecutionOwner {
		t.Fatal("reserved hardened entry does not name its deferred owner story")
	}

	// The same two non-portable inputs also appear as explicit named
	// rejections, so a reader never has to infer the negative from the
	// identity block alone.
	rejections := namedObjects(t, vector["rejection_cases"])
	for name, key := range map[string]string{
		"legacy-rc4-input-without-execution-policy": buildDriverLegacyCacheKey,
		"reserved-hardened-execution-policy":        buildDriverHardenedCacheKey,
	} {
		item, ok := rejections[name]
		if !ok {
			t.Fatalf("rejection %s is missing", name)
		}
		input := item["input"].(map[string]any)
		if input["derived_cache_key"] != key || canonicalSHA256(input["build_input"]) != key {
			t.Fatalf("%s does not carry its own derived key: %#v", name, input)
		}
		expected := item["expected"].(map[string]any)
		if expected["schema_valid"] != false || expected["aliases_portable_cache_key"] != false || expected["cache_lookup_performed"] != false {
			t.Fatalf("%s is not an explicit schema-invalid non-alias negative: %#v", name, expected)
		}
	}
}

func TestBuildDriverPositiveProcessCacheAndDryRunCoverage(t *testing.T) {
	root := repositoryRoot(t)
	vector := readObject(t, filepath.Join(root, "conformance", "v1", "vectors", "build-drivers.json"))
	positive := namedObjects(t, vector["positive_cases"])
	wantPositive := []string{
		"schema-6-mixed-script-and-build-commands",
		"build-root-excluded-from-agent-context",
		"valid-standard-library-only-main",
		"valid-vendor-only-main-with-transitive-embed",
		"fixed-environment-and-five-direct-argv-forms",
		"portable-execution-policy-is-required-input",
		"protected-cache-hit",
		"compiler-free-dry-run-miss",
	}
	assertNamedSet(t, positive, wantPositive)

	policyCase := positive["portable-execution-policy-is-required-input"]
	if policyCase["execution_policy"] != portableExecutionPolicy || policyCase["cache_key"] != buildDriverCacheKey || policyCase["package_selectable"] != false {
		t.Fatalf("portable execution-policy positive is incomplete: %#v", policyCase)
	}

	argv := vector["argv"].([]any)
	if len(argv) != 5 {
		t.Fatalf("go-v1 argv forms = %d, want 5", len(argv))
	}
	wantArgvNames := []string{"telemetry-off", "version", "env", "list", "build"}
	for index, name := range wantArgvNames {
		item := argv[index].(map[string]any)
		if item["name"] != name || len(item["argv"].([]any)) == 0 || item["argv"].([]any)[0] != "/absolute/trusted/goroot/bin/go" {
			t.Fatalf("argv form %d = %#v", index, item)
		}
	}
	buildArgv := argv[4].(map[string]any)["argv"].([]any)
	for _, fixed := range []any{"-mod=vendor", "-trimpath", "-pgo=off", "-ldflags=-linkmode=internal -libgcc=none", "."} {
		if !containsValue(buildArgv, fixed) {
			t.Fatalf("build argv misses %q: %#v", fixed, buildArgv)
		}
	}
	environment := vector["fixed_environment"].(map[string]any)
	for key, value := range map[string]any{
		"GOENV": "off", "GOPROXY": "off", "GOWORK": "off", "GOTOOLCHAIN": "local",
		"CGO_ENABLED": "0", "GO_EXTLINK_ENABLED": "0", "GOARM64": "v8.0", "PATH": "<operation-private>/empty-path",
	} {
		if environment[key] != value {
			t.Fatalf("fixed environment %s = %v, want %v", key, environment[key], value)
		}
	}
	for _, forbidden := range []string{"CC", "CXX", "PKG_CONFIG", "AR", "GCCGO", "GOAUTH", "GOTELEMETRY"} {
		if _, ok := environment[forbidden]; ok {
			t.Fatalf("fixed environment inherits forbidden variable %s", forbidden)
		}
	}
	for _, name := range []string{"protected-cache-hit", "compiler-free-dry-run-miss"} {
		commands := positive[name]["source_aware_go_commands"].([]any)
		if len(commands) != 0 {
			t.Fatalf("%s executes source-aware Go commands: %#v", name, commands)
		}
		if positive[name]["cache_key"] != buildDriverCacheKey {
			t.Fatalf("%s does not use the portable rc.5 cache key: %v", name, positive[name]["cache_key"])
		}
	}
}

func TestBuildDriverRejectionCoverageAndNamedOutcomes(t *testing.T) {
	root := repositoryRoot(t)
	vector := readObject(t, filepath.Join(root, "conformance", "v1", "vectors", "build-drivers.json"))
	cases := namedObjects(t, vector["rejection_cases"])
	want := []string{
		"schema-5-build-command", "unknown-driver", "forbidden-args", "forbidden-env", "forbidden-output", "forbidden-toolchain", "forbidden-hooks", "mixed-script-build-shape",
		"missing-build-roots", "missing-build-root-directory", "unused-build-root", "overlapping-build-roots", "runtime-overlapping-build-root", "root-build-root", "build-root-symlink", "build-root-special-file",
		"root-source-dir", "escaped-source-dir", "source-outside-root", "source-link", "source-special-file", "source-not-directory", "missing-root-go-mod", "nested-module", "non-main-package", "multiple-packages",
		"missing-vendored-dependency", "inconsistent-vendor-modules", "workspace-only-dependency", "toolchain-switch-request", "unsupported-go-pre-1-23", "unsupported-go-future-family", "cgo-only-package",
		"native-c-input", "native-cxx-input", "native-swig-input", "root-syso", "transitive-syso", "root-assembly-absolute-include", "transitive-assembly-escaping-include", "escaped-embed-input",
		"cgo-import-dynamic", "attempted-go-generate", "default-pgo", "poisoned-path", "inherited-goflags-toolexec", "inherited-goenv", "inherited-gowork", "vcs-metadata", "repository-local-fake-go",
		"telemetry-command-failure", "telemetry-private-dir-escape", "external-link-required", "libgcc-fallback-attempt", "child-outside-goroot-tools", "wrong-go-executable-path", "toolchain-digest-mismatch",
		"cache-key-mismatch", "cache-wrong-target", "cache-wrong-toolchain", "cache-wrong-policy", "cache-wrong-build-source", "receipt-hash-mismatch", "artifact-hash-mismatch", "artifact-size-mismatch", "artifact-path-mismatch",
		"noncanonical-receipt-whitespace", "noncanonical-receipt-trailing-lf", "partial-cache-entry", "artifact-link", "artifact-special-file", "concurrent-publisher-different-bytes",
		"self-consistent-forged-receipt-outside-protected-state", "marker-embed-build-source-regression", "build-root-content-in-context",
		"legacy-rc4-input-without-execution-policy", "reserved-hardened-execution-policy",
	}
	assertNamedSet(t, cases, want)
	for name, item := range cases {
		expected, ok := item["expected"].(map[string]any)
		if !ok || expected["result"] != "reject" || expected["error"] == nil || expected["error"] == "" || expected["artifact_executed"] != false {
			t.Fatalf("rejection %s lacks a named non-executing outcome: %#v", name, item)
		}
	}
	forged := cases["self-consistent-forged-receipt-outside-protected-state"]
	candidate := forged["candidate"].(map[string]any)
	receipt := candidate["receipt"].(map[string]any)
	if sha256Identity(canonicalBytes(receipt)) != buildDriverForgedReceiptSHA256 || candidate["receipt_sha256"] != buildDriverForgedReceiptSHA256 {
		t.Fatalf("forged receipt is not the exact self-consistent regression candidate: %#v", candidate)
	}
	if candidate["receipt_sha256"] == supersededRC4ForgedReceiptSHA256 {
		t.Fatal("forged receipt still reproduces the superseded rc.4 digest")
	}
	if receipt["cache_key"] != buildDriverCacheKey {
		t.Fatalf("forged receipt no longer binds its own portable input: %v", receipt["cache_key"])
	}
	marker := cases["marker-embed-build-source-regression"]
	markerInput := marker["input"].(map[string]any)
	variants := markerInput["variants"].([]any)
	if markerInput["legacy_content_sha256"] != buildDriverMarkerEmbedLegacySHA256 || variants[0].(map[string]any)["build_source"].(map[string]any)["content_sha256"] == variants[1].(map[string]any)["build_source"].(map[string]any)["content_sha256"] {
		t.Fatalf("marker-embed regression identities are incomplete: %#v", marker)
	}
}

func TestBuildSourceAndToolchainByteVectors(t *testing.T) {
	root := repositoryRoot(t)
	vector := readObject(t, filepath.Join(root, "conformance", "v1", "vectors", "build-drivers.json"))
	buildCases := namedObjects(t, vector["build_source_cases"])
	assertNamedSet(t, buildCases, []string{
		"fixture-exact-build-source", "domain-prefix-ordering-framing-empty-binary-and-root-marker", "mode-and-timestamp-are-non-inputs",
		"invalid-unicode-build-source-path", "duplicate-build-source-path", "build-source-symbolic-link", "build-source-special-file",
		"build-source-mutation-during-use", "legacy-nul-stream-structural-collision", "root-marker-bytes-are-build-input",
	})
	if buildCases["fixture-exact-build-source"]["content_sha256"] != buildDriverBuildSourceHash {
		t.Fatalf("fixture build-source digest changed: %v", buildCases["fixture-exact-build-source"]["content_sha256"])
	}
	edge := buildCases["domain-prefix-ordering-framing-empty-binary-and-root-marker"]
	if edge["content_sha256"] != buildDriverEdgeBuildSourceSHA256 {
		t.Fatalf("build-source edge digest changed: %v", edge["content_sha256"])
	}
	collision := buildCases["legacy-nul-stream-structural-collision"]
	framed := collision["framed_content_sha256"].([]any)
	if collision["legacy_streams_equal"] != true || collision["framed_hashes_equal"] != false || framed[0] == framed[1] {
		t.Fatalf("legacy NUL collision regression is incomplete: %#v", collision)
	}

	toolchainCases := namedObjects(t, vector["toolchain_cases"])
	assertNamedSet(t, toolchainCases, []string{
		"unsorted-directories-files-and-internal-link", "crlf-version-normalizes-to-lf-identity", "toolchain-mode-and-timestamp-are-non-inputs",
		"toolchain-version-missing-terminal-lf", "toolchain-version-multiple-terminal-newlines", "invalid-unicode-toolchain-path", "duplicate-toolchain-path",
		"escaping-toolchain-link", "absolute-toolchain-link", "dangling-toolchain-link", "selected-go-outside-goroot", "toolchain-tree-mutation-during-use",
	})
	exact := toolchainCases["unsorted-directories-files-and-internal-link"]
	if exact["content_sha256"] != buildDriverToolchainSHA256 || exact["normalized_go_version"] != buildDriverNormalizedGoVersionValue {
		t.Fatalf("toolchain exact vector changed: %#v", exact)
	}
	if toolchainCases["crlf-version-normalizes-to-lf-identity"]["content_sha256"] != buildDriverToolchainSHA256 {
		t.Fatal("CRLF go version did not normalize to the LF toolchain identity")
	}
}

func TestBuildDriverGenerationIsDeterministic(t *testing.T) {
	root := repositoryRoot(t)
	fixture := filepath.Join(root, "conformance", "v1", "fixtures", "go-build-skill")
	marker := readObject(t, filepath.Join(root, "conformance", "v1", "expected", "marker.json"))
	one := t.TempDir()
	two := t.TempDir()
	writeBuildDriverVectors(filepath.Join(one, "vectors"), fixture, filepath.Join(one, "expected"), marker)
	writeBuildDriverVectors(filepath.Join(two, "vectors"), fixture, filepath.Join(two, "expected"), marker)
	oneFiles := regularFiles(one)
	twoFiles := regularFiles(two)
	if !reflect.DeepEqual(oneFiles, twoFiles) {
		t.Fatalf("deterministic generation inventory differs: %#v != %#v", oneFiles, twoFiles)
	}
	for _, name := range oneFiles {
		left, err := os.ReadFile(filepath.Join(one, filepath.FromSlash(name)))
		if err != nil {
			t.Fatal(err)
		}
		right, err := os.ReadFile(filepath.Join(two, filepath.FromSlash(name)))
		if err != nil {
			t.Fatal(err)
		}
		if !bytes.Equal(left, right) {
			t.Fatalf("deterministic generation differs for %s", name)
		}
	}
}

func TestBuildDriverGenerationPreservesScriptFixtureAndRegistryGoldens(t *testing.T) {
	root := repositoryRoot(t)
	want := map[string]string{
		"conformance/v1/fixtures/skill/.skill_triggers/en.md":       "ba431f8ce1d9c6cb079b381caae9c71a470e26d4dbbdc2e6badbd392e753c679",
		"conformance/v1/fixtures/skill/README.md":                   "1a9d7c9c5b8df5b83f485f43c1a536a3c078796b8d1ef3642ced6cc2e4d7f1a6",
		"conformance/v1/fixtures/skill/SKILL.md":                    "998b2482cc522a3b0091e377bce1aeda049bf8504ac32164ab345214569c8575",
		"conformance/v1/fixtures/skill/agent-skill.json":            "4e8adc18905769d60511a795fca139dbb9ee7e7f0316d9a7279a8c5ca376c075",
		"conformance/v1/fixtures/skill/locales/metadata.json":       "fcf376ac8bd03713871a55a0b2f5d9e207c4536eec9e1698036fc9e61f4cfdd3",
		"conformance/v1/fixtures/skill/references/notes.md":         "eb30e8c7ba3b1c16870dd28b828e45e3f3b290dea3da1b703f872763fb64b1c0",
		"conformance/v1/fixtures/skill/scripts/golden-tool":         "823c5909efd8d73239bdcd64fce67ff79f43c7b36de8d921194b7e4e3cf0fb04",
		"conformance/v1/expected/registry/bundle.json":              "b51676030624be7427b7276ec5a2f98f6a0fcd9b86f99bce2e1e12708b991a07",
		"conformance/v1/expected/registry/log.json":                 "894a905bc2652e906b857e771c1f82477e31fb3b7c0a10b8cb0cef8096058f4e",
		"conformance/v1/expected/registry/pinned_key.txt":           "bd4a0eb75144aea935dfb3a8a69c12826d49ed54c49db6e30bfdfe2cac7c36c4",
		"conformance/v1/expected/registry/record_audited.json":      "994220de5f8f40861b3bdd1bd4f3cc0c1716c2cf79540f7499dafe50d3dc1d0a",
		"conformance/v1/expected/registry/record_forged.json":       "3721c1b0b6bd6ecdce261272901e45f66306653ac4d2d008aec10a340efb84df",
		"conformance/v1/expected/registry/record_revoked.json":      "fc4fa99f6ceb732dd018e1d4b30c41ccbd92e96b0ec7e85c6d5304c19d75602d",
		"conformance/v1/expected/registry/record_wrong_key_id.json": "cb3bb9b8a2c79f93088f725b2bfc7fe19d14864c280eaa5c141d936d0c0e54bd",
		"conformance/v1/expected/registry/snapshot.json":            "6ffc2378a139f1c16ca8d3a0e4609563e6a48a16a7fb86493b801101ee7b1f3c",
	}
	for name, digest := range want {
		payload, err := os.ReadFile(filepath.Join(root, filepath.FromSlash(name)))
		if err != nil {
			t.Fatal(err)
		}
		got := sha256.Sum256(payload)
		if hex.EncodeToString(got[:]) != digest {
			t.Fatalf("frozen script/registry golden changed: %s", name)
		}
	}
}

// TestBuildDriverContextSelectionExcludesOnlyDeclaredBuildRoots proves the
// build-root exclusion added to the shared context selector is scoped: it
// removes the schema-6 build root from the build fixture's agent context and
// leaves the script-only fixture's selection byte-identical.
func TestBuildDriverContextSelectionExcludesOnlyDeclaredBuildRoots(t *testing.T) {
	root := repositoryRoot(t)
	buildFixture := filepath.Join(root, "conformance", "v1", "fixtures", "go-build-skill")
	if got, want := selectedContextFiles(buildFixture), []string{"SKILL.md", "assets/prompt.md"}; !reflect.DeepEqual(got, want) {
		t.Fatalf("build fixture context selection = %#v, want %#v", got, want)
	}
	scriptFixture := filepath.Join(root, "conformance", "v1", "fixtures", "skill")
	selected := selectedContextFiles(scriptFixture)
	var published []any
	readJSON(t, filepath.Join(root, "conformance", "v1", "expected", "context_files.json"), &published)
	if len(selected) != len(published) {
		t.Fatalf("script fixture context selection = %#v, published %#v", selected, published)
	}
	for index, name := range selected {
		if published[index] != name {
			t.Fatalf("script fixture context selection changed at %d: %q != %v", index, name, published[index])
		}
	}
	if got, want := contentHash(scriptFixture, selected), strings.TrimSpace(string(mustReadFile(t, filepath.Join(root, "conformance", "v1", "expected", "context_sha256.txt")))); got != want {
		t.Fatalf("script fixture context hash = %s, want %s", got, want)
	}
}

func mustReadFile(t *testing.T, path string) []byte {
	t.Helper()
	payload, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	return payload
}

func assertNamedSet(t *testing.T, got map[string]map[string]any, want []string) {
	t.Helper()
	wantSet := make(map[string]bool, len(want))
	for _, name := range want {
		wantSet[name] = true
	}
	gotSet := make(map[string]bool, len(got))
	for name := range got {
		gotSet[name] = true
	}
	if !reflect.DeepEqual(gotSet, wantSet) {
		t.Fatalf("named case coverage = %#v, want %#v", gotSet, wantSet)
	}
}

func TestCCJ1RemovesOnlyOuterSignature(t *testing.T) {
	value := map[string]any{
		"z": "заметка",
		"endorsement": map[string]any{
			"sig": map[string]any{"key_id": "nested"},
		},
		"sig": map[string]any{"key_id": "outer"},
	}
	want := `{"endorsement":{"sig":{"key_id":"nested"}},"z":"заметка"}`
	if got := string(canonicalBytes(value)); got != want {
		t.Fatalf("CCJ-1 = %s, want %s", got, want)
	}
}

func TestCCJ1Escapes(t *testing.T) {
	value := map[string]any{"s": "\b\f\n\r\t<>/&\\\""}
	want := `{"s":"\b\f\n\r\t<>/&\\\""}`
	if got := string(canonicalBytes(value)); got != want {
		t.Fatalf("CCJ-1 escapes = %s, want %s", got, want)
	}
}

func TestGeneratedRegistryVectors(t *testing.T) {
	root := repositoryRoot(t)
	registryDir := filepath.Join(root, "conformance", "v1", "expected", "registry")
	pinnedPayload, err := os.ReadFile(filepath.Join(registryDir, "pinned_key.txt"))
	if err != nil {
		t.Fatal(err)
	}
	pinned := strings.TrimSpace(string(pinnedPayload))
	publicBytes, err := base64.StdEncoding.DecodeString(strings.TrimPrefix(pinned, "ed25519:"))
	if err != nil {
		t.Fatal(err)
	}
	public := ed25519.PublicKey(publicBytes)

	for _, name := range []string{"record_audited.json", "record_revoked.json", "snapshot.json"} {
		object := readObject(t, filepath.Join(registryDir, name))
		if !verifySignedVector(object, public) {
			t.Fatalf("%s must verify", name)
		}
	}
	if verifySignedVector(readObject(t, filepath.Join(registryDir, "record_forged.json")), public) {
		t.Fatal("forged record must not verify")
	}
	if verifySignedVector(readObject(t, filepath.Join(registryDir, "record_wrong_key_id.json")), public) {
		t.Fatal("record with wrong key id must not verify")
	}

	logObject := readObject(t, filepath.Join(registryDir, "log.json"))
	rawEntries, ok := logObject["entries"].([]any)
	if !ok || len(rawEntries) != 2 {
		t.Fatalf("log entries = %#v", logObject["entries"])
	}
	entries := make([]map[string]any, len(rawEntries))
	prev := genesis
	for index, raw := range rawEntries {
		entry := raw.(map[string]any)
		entries[index] = entry
		if entry["prev_hash"] != prev {
			t.Fatalf("entry %d prev_hash = %v, want %s", index+1, entry["prev_hash"], prev)
		}
		record := entry["record"].(map[string]any)
		sum := sha256.Sum256(append([]byte(prev), canonicalBytes(record)...))
		prev = hex.EncodeToString(sum[:])
		if entry["entry_hash"] != prev {
			t.Fatalf("entry %d hash = %v, want %s", index+1, entry["entry_hash"], prev)
		}
	}
	snapshot := readObject(t, filepath.Join(registryDir, "snapshot.json"))
	if snapshot["head"] != prev || snapshot["merkle_root"] != merkleRoot(entries) {
		t.Fatal("snapshot does not commit to the generated log")
	}

	bundle := readObject(t, filepath.Join(registryDir, "bundle.json"))
	if bundle["snapshot"].(map[string]any)["head"] != snapshot["head"] {
		t.Fatal("bundle snapshot differs from the standalone snapshot")
	}
}

func validateEmptyPackIndex(item map[string]any, objectFormat string, expectIndexChecksum bool) error {
	width := 20
	if objectFormat == "sha256" {
		width = 32
	} else if objectFormat != "sha1" {
		return fmt.Errorf("unsupported object format %q", objectFormat)
	}
	pack, err := hex.DecodeString(item["pack_hex"].(string))
	if err != nil {
		return fmt.Errorf("decode pack: %w", err)
	}
	index, err := hex.DecodeString(item["index_hex"].(string))
	if err != nil {
		return fmt.Errorf("decode index: %w", err)
	}
	if len(pack) != 12+width {
		return fmt.Errorf("pack size %d does not match %s", len(pack), objectFormat)
	}
	if string(pack[:4]) != "PACK" {
		return fmt.Errorf("wrong pack magic")
	}
	packVersion := binary.BigEndian.Uint32(pack[4:8])
	if item["pack_version"] != json.Number(fmt.Sprint(packVersion)) {
		return fmt.Errorf("pack version metadata is false")
	}
	if binary.BigEndian.Uint32(pack[8:12]) != 0 {
		return fmt.Errorf("pack is not empty")
	}
	packChecksum := pack[len(pack)-width:]
	if !bytes.Equal(packChecksum, objectDigest(objectFormat, pack[:len(pack)-width])) {
		return fmt.Errorf("pack checksum is invalid")
	}
	if item["pack_name"] != "pack-"+hex.EncodeToString(packChecksum)+".pack" {
		return fmt.Errorf("pack filename does not match checksum")
	}

	if len(index) != 8+256*4+2*width {
		return fmt.Errorf("index size %d does not match %s", len(index), objectFormat)
	}
	if !bytes.Equal(index[:4], []byte{0xff, 0x74, 0x4f, 0x63}) {
		return fmt.Errorf("wrong index magic")
	}
	indexVersion := binary.BigEndian.Uint32(index[4:8])
	if item["index_version"] != json.Number(fmt.Sprint(indexVersion)) {
		return fmt.Errorf("index version metadata is false")
	}
	var previous uint32
	for offset := 8; offset < 8+256*4; offset += 4 {
		current := binary.BigEndian.Uint32(index[offset : offset+4])
		if current < previous {
			return fmt.Errorf("index fanout is not monotonic")
		}
		previous = current
	}
	if previous != 0 {
		return fmt.Errorf("empty-pack index fanout is not zero")
	}
	packChecksumOffset := 8 + 256*4
	if !bytes.Equal(index[packChecksumOffset:packChecksumOffset+width], packChecksum) {
		return fmt.Errorf("index embeds the wrong pack checksum")
	}
	actualIndexChecksum := index[len(index)-width:]
	expectedIndexChecksum := objectDigest(objectFormat, index[:len(index)-width])
	if bytes.Equal(actualIndexChecksum, expectedIndexChecksum) != expectIndexChecksum {
		return fmt.Errorf("index checksum validity does not match the fixture outcome")
	}
	return nil
}

func validateAuditPath(item map[string]any, globalPositions map[string]int, cache, compiler bool) error {
	rawPhases, ok := item["ordered_phases"].([]any)
	if !ok || len(rawPhases) == 0 {
		return fmt.Errorf("ordered_phases is absent")
	}
	positions := make([]int, 0, len(rawPhases))
	seen := map[string]bool{}
	for _, raw := range rawPhases {
		phase, ok := raw.(string)
		if !ok {
			return fmt.Errorf("phase is not text")
		}
		position, exists := globalPositions[phase]
		if !exists || seen[phase] {
			return fmt.Errorf("unknown or duplicate phase %q", phase)
		}
		seen[phase] = true
		positions = append(positions, position)
	}
	for index := 1; index < len(positions); index++ {
		if positions[index-1] >= positions[index] {
			return fmt.Errorf("phases do not follow whole-snapshot order")
		}
	}
	for _, required := range []string{
		"exact-source-acquisition",
		"whole-snapshot-validation",
		"independent-external-audit",
	} {
		if !seen[required] {
			return fmt.Errorf("missing %s", required)
		}
	}
	if seen["artifact-cache-lookup"] != cache || seen["compiler"] != compiler {
		return fmt.Errorf("cache/compiler phases do not match the path outcome")
	}
	if cache && globalPositions["independent-external-audit"] >= globalPositions["artifact-cache-lookup"] {
		return fmt.Errorf("audit does not precede cache lookup")
	}
	if compiler && globalPositions["independent-external-audit"] >= globalPositions["compiler"] {
		return fmt.Errorf("audit does not precede compiler")
	}
	return nil
}

func validateExternalReceiptOracles(receipt, marker, plan map[string]any) error {
	input, ok := receipt["input"].(map[string]any)
	if !ok {
		return fmt.Errorf("receipt input is absent")
	}
	cacheKey := canonicalSHA256(input)
	if receipt["cache_key"] != cacheKey {
		return fmt.Errorf("receipt cache_key is not SHA-256(CCJ-1(input))")
	}
	receiptHash := canonicalSHA256(receipt)
	builds, ok := marker["builds"].(map[string]any)
	if !ok {
		return fmt.Errorf("marker builds are absent")
	}
	record, ok := builds["golden-tool"].(map[string]any)
	if !ok || record["cache_key"] != cacheKey || record["receipt_sha256"] != receiptHash {
		return fmt.Errorf("marker does not carry the exact receipt hashes")
	}
	commands, ok := plan["commands"].([]any)
	if !ok {
		return fmt.Errorf("mixed-build plan commands are absent")
	}
	for _, raw := range commands {
		command, ok := raw.(map[string]any)
		if !ok || command["name"] != "golden-tool" {
			continue
		}
		if command["cache_key"] != cacheKey || command["receipt_sha256"] != receiptHash {
			return fmt.Errorf("mixed-build plan does not carry the exact receipt hashes")
		}
		return nil
	}
	return fmt.Errorf("mixed-build plan has no external command")
}

func verifySignedVector(object map[string]any, public ed25519.PublicKey) bool {
	sig, ok := object["sig"].(map[string]any)
	if !ok || sig["algorithm"] != "ed25519" {
		return false
	}
	keyHash := sha256.Sum256(public)
	if sig["key_id"] != hex.EncodeToString(keyHash[:])[:16] {
		return false
	}
	signatureText, ok := sig["signature"].(string)
	if !ok {
		return false
	}
	signature, err := base64.StdEncoding.DecodeString(signatureText)
	return err == nil && ed25519.Verify(public, canonicalBytes(object), signature)
}

func readObject(t *testing.T, path string) map[string]any {
	t.Helper()
	var object map[string]any
	readJSON(t, path, &object)
	return object
}

func readJSON(t *testing.T, path string, value any) {
	t.Helper()
	file, err := os.Open(path)
	if err != nil {
		t.Fatal(err)
	}
	defer file.Close()
	decoder := json.NewDecoder(file)
	decoder.UseNumber()
	if err := decoder.Decode(value); err != nil {
		t.Fatal(err)
	}
}

func repositoryRoot(t *testing.T) string {
	t.Helper()
	_, file, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("cannot locate test file")
	}
	return filepath.Clean(filepath.Join(filepath.Dir(file), "..", ".."))
}

func containsValue(values []any, want any) bool {
	for _, value := range values {
		if reflect.DeepEqual(value, want) {
			return true
		}
	}
	return false
}

func indexedSchemaCases(index []map[string]any, schema string) map[string]bool {
	prefix := strings.TrimSuffix(schema, ".schema.json") + "/"
	result := map[string]bool{}
	for _, item := range index {
		if item["schema"] == schema {
			result[strings.TrimPrefix(item["instance"].(string), prefix)] = item["valid"].(bool)
		}
	}
	return result
}

func namedObjects(t *testing.T, value any) map[string]map[string]any {
	t.Helper()
	items, ok := value.([]any)
	if !ok {
		t.Fatalf("named cases are not an array: %#v", value)
	}
	result := make(map[string]map[string]any, len(items))
	for _, raw := range items {
		item, ok := raw.(map[string]any)
		if !ok {
			t.Fatalf("named case is not an object: %#v", raw)
		}
		name, ok := item["name"].(string)
		if !ok || name == "" {
			t.Fatalf("named case has no name: %#v", item)
		}
		if _, duplicate := result[name]; duplicate {
			t.Fatalf("duplicate named case %s", name)
		}
		result[name] = item
	}
	return result
}

func assertPropertySet(t *testing.T, name string, schema map[string]any, want []string) {
	t.Helper()
	properties, ok := schema["properties"].(map[string]any)
	if !ok {
		t.Fatalf("%s has no object properties", name)
	}
	gotSet := make(map[string]bool, len(properties))
	for field := range properties {
		gotSet[field] = true
	}
	wantSet := make(map[string]bool, len(want))
	for _, field := range want {
		wantSet[field] = true
	}
	if !reflect.DeepEqual(gotSet, wantSet) {
		t.Fatalf("%s declared properties changed: got %#v, want %#v", name, gotSet, wantSet)
	}
}

func assertNoDeclaredProperties(t *testing.T, name string, schema map[string]any, forbidden []string) {
	t.Helper()
	declared := map[string]bool{}
	collectDeclaredProperties(schema, declared)
	for _, field := range forbidden {
		if declared[field] {
			t.Fatalf("%s gained forbidden build/provenance surface %q", name, field)
		}
	}
}

func collectDeclaredProperties(value any, declared map[string]bool) {
	switch value := value.(type) {
	case map[string]any:
		if properties, ok := value["properties"].(map[string]any); ok {
			for field := range properties {
				declared[field] = true
			}
		}
		for _, child := range value {
			collectDeclaredProperties(child, declared)
		}
	case []any:
		for _, child := range value {
			collectDeclaredProperties(child, declared)
		}
	}
}
