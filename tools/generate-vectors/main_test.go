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
)

const (
	legacyWireBaselineCommit        = "57c1f56846d221ecc55786bd3c2467ec32f11730"
	conformanceClaimV1SchemaSHA256  = "c9f49460618ccc8b1d7d2dfaf760fc6ad3a53a870a6685a685ddc148d3c87b3f"
	conformanceClaimV1ValidSHA256   = "799682489be118331135d91798db90b8d020cbb703207331824ab113f037693c"
	conformanceClaimV1InvalidSHA256 = "de9568757a2bb89c87702e47f6d9c162df24f5ee964f1ef49b9e191ed94b7017"
)

func TestSchemaV7WireSurfacesAreClosedAndVersioned(t *testing.T) {
	root := repositoryRoot(t)
	for _, filename := range []string{
		"agent-skill-v7.schema.json",
		"csk-skill-v7.schema.json",
		"curator-build-v1.schema.json",
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
		"buildRepositoryV1", "repositoryBuildCommandV1", "curatorBuildTargetV1",
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
		defs["buildRepositoryV1"], defs["repositoryBuildCommandV1"], defs["curatorBuildTargetV1"],
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
		"curator-build-v1.schema.json": {
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
		"conformance/v1/schema-cases/build-receipt-v1/valid.json":     "93217cf1ce2965435042f8e20ebfec45498bae67a128cc16f38b3f4c8b64ecab",
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
	if policy["additionalProperties"] != false || len(policy["properties"].(map[string]any)) != 11 {
		t.Fatalf("go-v1 policy is not fixed: %#v", policy)
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
