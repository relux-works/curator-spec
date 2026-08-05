package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"io/fs"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"testing"
)

// generateInto runs exactly what main does, against an arbitrary root, so a
// test can prove byte stability and portable-suite non-interference without
// writing into the repository.
func generateInto(t *testing.T, root string) {
	t.Helper()
	suite := filepath.Join(root, "conformance", "hardened", "v1")
	vectors := filepath.Join(suite, "vectors")
	if err := os.MkdirAll(vectors, 0o755); err != nil {
		t.Fatalf("prepare suite: %v", err)
	}
	writeProfileVector(vectors)
	writeAdversarialVector(vectors)
	writeIdentitySeparationVector(vectors)
	writeSchemaCases(suite)
	writeManifest(suite)
	writeReleaseMetadata(root, suite)
}

// seedPortableManifest copies only the portable manifest, which the release
// metadata pins as a read-only baseline.
func seedPortableManifest(t *testing.T, root string) []byte {
	t.Helper()
	payload, err := os.ReadFile(filepath.Join("..", "..", "conformance", "v1", "manifest.json"))
	if err != nil {
		t.Fatalf("read portable manifest: %v", err)
	}
	target := filepath.Join(root, "conformance", "v1")
	if err := os.MkdirAll(target, 0o755); err != nil {
		t.Fatalf("prepare portable baseline: %v", err)
	}
	if err := os.WriteFile(filepath.Join(target, "manifest.json"), payload, 0o644); err != nil {
		t.Fatalf("seed portable manifest: %v", err)
	}
	return payload
}

func treeDigests(t *testing.T, root string) map[string]string {
	t.Helper()
	digests := map[string]string{}
	err := filepath.WalkDir(root, func(path string, entry fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if !entry.Type().IsRegular() {
			return nil
		}
		rel, relErr := filepath.Rel(root, path)
		if relErr != nil {
			return relErr
		}
		payload, readErr := os.ReadFile(path)
		if readErr != nil {
			return readErr
		}
		sum := sha256.Sum256(payload)
		digests[filepath.ToSlash(rel)] = hex.EncodeToString(sum[:])
		return nil
	})
	if err != nil {
		t.Fatalf("walk %s: %v", root, err)
	}
	return digests
}

// TestRecordedPolicySlotKeysAreReproduced pins the three rc.5 keys this suite
// compares against. None of them is a hardened build input: rc.5 marks the
// reserved hardened policy-slot input schema_valid: false.
func TestRecordedPolicySlotKeysAreReproduced(t *testing.T) {
	cases := []struct {
		name   string
		policy any
		want   string
	}{
		{"rc5-reserved-policy-slot", hardenedExecutionPolicy, reservedPolicySlotCacheKey},
		{"portable", portableExecutionPolicy, portableCacheKey},
		{"pre-revision", nil, legacyRC4CacheKey},
	}
	for _, item := range cases {
		got := canonicalSHA256(buildInput(item.policy))
		if got != item.want {
			t.Errorf("%s cache key = %s, want %s", item.name, got, item.want)
		}
	}
}

// TestHardenedInputIsThePortableInputPlusOneClosedMember proves the hardened
// build input adds exactly one member and changes exactly one value.
func TestHardenedInputIsThePortableInputPlusOneClosedMember(t *testing.T) {
	hardened := hardenedBuildInput(hardenedTCB())
	portable := buildInput(portableExecutionPolicy)

	identity, ok := hardened["hardened"].(map[string]any)
	if !ok {
		t.Fatal("the hardened build input carries no hardened identity member")
	}
	if identity["profile"] != hardenedProfileIdentity {
		t.Error("the hardened identity member does not carry the profile identity")
	}
	digest := identity["tcb"].(map[string]any)
	if digest["algorithm"] != tcbDigestAlgorithm || digest["content_sha256"] != tcbDigest(hardenedTCB()) {
		t.Error("the hardened identity member does not carry the trusted-computing-base digest")
	}

	delete(hardened, "hardened")
	delete(hardened["policy"].(map[string]any), "execution_policy")
	delete(portable["policy"].(map[string]any), "execution_policy")
	if !reflect.DeepEqual(hardened, portable) {
		t.Fatal("the hardened build input differs from the portable input beyond the hardened member and the policy slot")
	}
}

// TestHardenedIdentityBindsTheCacheKey is the executable form of the binding
// requirement: profile identity and trusted-computing-base identity are inside
// the hashed input, so neither can be changed without changing cache identity.
func TestHardenedIdentityBindsTheCacheKey(t *testing.T) {
	base := hardenedBuildInput(hardenedTCB())
	baseKey := canonicalSHA256(base)

	rotated := canonicalSHA256(hardenedBuildInput(rotatedTCB()))
	if rotated == baseKey {
		t.Error("rotating the trusted computing base does not change the cache key")
	}

	reprofiled := hardenedBuildInput(hardenedTCB())
	reprofiled["hardened"].(map[string]any)["profile"] = "hardened-profile-v2"
	if canonicalSHA256(reprofiled) == baseKey {
		t.Error("changing the profile identity does not change the cache key")
	}

	keys := map[string]string{
		"hardened":             baseKey,
		"hardened-rotated-tcb": rotated,
		"rc5-reserved-slot":    canonicalSHA256(buildInput(hardenedExecutionPolicy)),
		"portable":             canonicalSHA256(buildInput(portableExecutionPolicy)),
		"pre-revision":         canonicalSHA256(buildInput(nil)),
	}
	seen := map[string]string{}
	for name, key := range keys {
		if other, ok := seen[key]; ok {
			t.Errorf("%s aliases %s", name, other)
		}
		seen[key] = name
	}
}

// TestTcbDigestIsDomainSeparated keeps the trusted-computing-base digest from
// ever equaling a cache key over the same canonical bytes.
func TestTcbDigestIsDomainSeparated(t *testing.T) {
	record := hardenedTCB()
	if tcbDigest(record) == canonicalSHA256(record) {
		t.Fatal("the trusted-computing-base digest is a bare canonical digest")
	}
	if tcbDigest(record) == tcbDigest(rotatedTCB()) {
		t.Fatal("two different trusted computing bases share a digest")
	}
}

// TestHardenedReceiptsBindProfileAndTcb checks the chain a reader follows:
// receipt bytes carry the concrete record, the hashed input carries its
// digest, and the cache key is the digest of that input.
func TestHardenedReceiptsBindProfileAndTcb(t *testing.T) {
	for name, receipt := range map[string]map[string]any{
		"go-v1":            validHardenedReceiptV3(),
		"go-repository-v1": validHardenedReceiptV4(),
	} {
		input := receipt["input"].(map[string]any)
		identity := input["hardened"].(map[string]any)
		if identity["profile"] != hardenedProfileIdentity {
			t.Errorf("%s receipt does not bind the profile identity", name)
		}
		record, ok := receipt["tcb"].(map[string]any)
		if !ok {
			t.Fatalf("%s receipt carries no trusted-computing-base record", name)
		}
		if identity["tcb"].(map[string]any)["content_sha256"] != tcbDigest(record) {
			t.Errorf("%s receipt input digest does not match its own record", name)
		}
		if receipt["cache_key"] != canonicalSHA256(input) {
			t.Errorf("%s receipt cache key is not the digest of its input", name)
		}
	}
}

// tcbMembers is the closed hardened-tcb-v1 record. Review cycle 2 rejected a
// record that named only the supervisor, the worker, and the toolchain: a
// trusted computing base that omits the manager parent, the observed host, the
// backend version and configuration, or the additional mutable components lets
// two materially different bases hash to one digest.
var tcbMembers = []string{
	"backend",
	"enforcement_backend",
	"execution_policy",
	"hardened_profile",
	"host",
	"parent_sha256",
	"platform",
	"record_version",
	"supervisor_sha256",
	"toolchain",
	"trusted_components",
	"worker_sha256",
}

func TestTcbRecordIsCompleteAndClosedOnEveryPlatform(t *testing.T) {
	for platform := range platformBindings() {
		record := tcbFor(platform)
		keys := make([]string, 0, len(record))
		for key := range record {
			keys = append(keys, key)
		}
		sort.Strings(keys)
		if !reflect.DeepEqual(keys, tcbMembers) {
			t.Errorf("%s trusted computing base members = %v, want %v", platform, keys, tcbMembers)
		}
		if record["enforcement_backend"] != bindingFor(platform).backend {
			t.Errorf("%s names a backend another platform declares", platform)
		}
		host := record["host"].(map[string]any)
		for _, field := range []string{"kind", "identity", "version"} {
			if value, ok := host[field].(string); !ok || value == "" {
				t.Errorf("%s host identity has no observed %s", platform, field)
			}
		}
		backend := record["backend"].(map[string]any)
		if version, ok := backend["version"].(string); !ok || version == "" {
			t.Errorf("%s enforcement backend reports no observed version", platform)
		}
		if _, ok := backend["configuration"].([]any); !ok {
			t.Errorf("%s enforcement backend reports no configuration", platform)
		}
	}
}

// TestTrustedComponentsAreClosedCryptographicRecords is the direct answer to
// the reviewer's mutable-interpreter probe: a component named by a bare string
// carries no identity at all.
func TestTrustedComponentsAreClosedCryptographicRecords(t *testing.T) {
	previous := ""
	for _, item := range trustedComponents() {
		component, ok := item.(map[string]any)
		if !ok {
			t.Fatal("a trusted component is not a record")
		}
		keys := make([]string, 0, len(component))
		for key := range component {
			keys = append(keys, key)
		}
		sort.Strings(keys)
		want := []string{"algorithm", "content_sha256", "kind", "name"}
		if !reflect.DeepEqual(keys, want) {
			t.Errorf("trusted component members = %v, want %v", keys, want)
		}
		digest, _ := component["content_sha256"].(string)
		if len(digest) != len("sha256:")+64 {
			t.Errorf("trusted component %v carries no content digest", component["name"])
		}
		order := component["kind"].(string) + "\x00" + component["name"].(string)
		if order <= previous {
			t.Errorf("trusted components are not sorted by kind then name at %s", order)
		}
		previous = order
	}
}

// TestEveryRotationMovesTheCacheKey is the mechanical form of "the trusted
// computing base binds cache reuse". Every member of the closed record is
// rotated in turn and every rotation must produce a distinct key.
func TestEveryRotationMovesTheCacheKey(t *testing.T) {
	base := hardenedTCB()
	baseKey := canonicalSHA256(hardenedBuildInput(base))
	seen := map[string]string{baseKey: "base"}
	digests := map[string]string{tcbDigest(base): "base"}
	for _, rotation := range tcbRotations() {
		record := rotatedRecord(rotation)
		if reflect.DeepEqual(record, base) {
			t.Errorf("rotation %s rotates nothing", rotation.name)
		}
		digest := tcbDigest(record)
		if other, ok := digests[digest]; ok {
			t.Errorf("rotation %s shares a trusted-computing-base digest with %s", rotation.name, other)
		}
		digests[digest] = rotation.name
		key := canonicalSHA256(hardenedBuildInput(record))
		if other, ok := seen[key]; ok {
			t.Errorf("rotation %s aliases the cache key of %s", rotation.name, other)
		}
		seen[key] = rotation.name
	}
}

// TestPackageInvisibleRotationsChangeOnlyTheHardenedMember isolates the effect
// under test: no value a package can see differs, so only the trusted
// computing base can have moved the key.
func TestPackageInvisibleRotationsChangeOnlyTheHardenedMember(t *testing.T) {
	baseInput := hardenedBuildInput(hardenedTCB())
	baseVisible := deepClone(baseInput)
	delete(baseVisible, "hardened")
	invisible := 0
	for _, rotation := range tcbRotations() {
		input := hardenedBuildInput(rotatedRecord(rotation))
		visible := deepClone(input)
		delete(visible, "hardened")
		changed := !reflect.DeepEqual(visible, baseVisible)
		if changed != rotation.packageVisible {
			t.Errorf("rotation %s misreports whether a package-visible value changed", rotation.name)
		}
		if changed && rotation.reason == "" {
			t.Errorf("rotation %s changes a visible value without stating why", rotation.name)
		}
		if !changed {
			invisible++
		}
	}
	if invisible == 0 {
		t.Fatal("no rotation isolates the trusted computing base from every package-visible value")
	}
}

// TestEveryMutableTcbMemberIsRotated keeps the completeness statement honest:
// a member nothing rotates is a member nothing proves is bound.
func TestEveryMutableTcbMemberIsRotated(t *testing.T) {
	constants := map[string]bool{"record_version": true, "hardened_profile": true, "execution_policy": true}
	rotated := map[string]bool{}
	for _, rotation := range tcbRotations() {
		for _, field := range rotation.fields {
			rotated[field] = true
		}
	}
	for _, member := range tcbMembers {
		if constants[member] {
			if rotated[member] {
				t.Errorf("%s is fixed by this revision but is rotated", member)
			}
			continue
		}
		if !rotated[member] {
			t.Errorf("trusted-computing-base member %s is never rotated", member)
		}
	}
	for _, item := range tcbBoundFields() {
		field := item.(map[string]any)
		name := field["field"].(string)
		rotations := field["rotated_by"].([]any)
		if constants[name] != (len(rotations) == 0) {
			t.Errorf("bound field %s misreports whether it can be rotated", name)
		}
	}
}

// TestClaimRequiredConfigurationIsObservedInItsOwnTcb keeps a claim from
// requiring a configuration the trusted base it names never had.
func TestClaimRequiredConfigurationIsObservedInItsOwnTcb(t *testing.T) {
	claim := validHardenedClaimV4()
	record := claim["tcb"].(map[string]any)
	observed := map[string]string{}
	for _, item := range record["backend"].(map[string]any)["configuration"].([]any) {
		entry := item.(map[string]any)
		observed[entry["setting"].(string)] = entry["observed_value"].(string)
	}
	declared := map[string]bool{}
	for _, item := range claim["operating_systems"].([]any) {
		declared[item.(string)] = true
	}
	if !declared[record["platform"].(string)] {
		t.Fatalf("the claim names a trusted computing base for %v, which it does not claim", record["platform"])
	}
	for _, item := range claim["enforcement_backends"].([]any) {
		entry := item.(map[string]any)
		if entry["operating_system"] != record["platform"] {
			continue
		}
		if entry["enforcement_backend"] != record["enforcement_backend"] {
			t.Error("the claim declares one enforcement backend and runs another")
		}
		for _, raw := range entry["required_configuration"].([]any) {
			requirement := raw.(map[string]any)
			setting := requirement["setting"].(string)
			if observed[setting] != requirement["required_value"] {
				t.Errorf("the claim requires %s, which its own trusted computing base did not observe", setting)
			}
		}
	}
}

func TestGuaranteeClassMappingIsExhaustive(t *testing.T) {
	classes := map[string]bool{}
	for _, name := range capabilityClasses {
		classes[name] = false
	}
	for guarantee, required := range guaranteeClasses {
		if len(required) == 0 {
			t.Errorf("guarantee %s requires no capability class", guarantee)
		}
		for _, class := range required {
			if _, ok := classes[class]; !ok {
				t.Errorf("guarantee %s requires unknown class %s", guarantee, class)
				continue
			}
			classes[class] = true
		}
	}
	var unused []string
	for class, used := range classes {
		if !used {
			unused = append(unused, class)
		}
	}
	sort.Strings(unused)
	if len(unused) != 0 {
		t.Errorf("capability classes serve no guarantee: %v", unused)
	}
	if len(guaranteeClasses) != len(guaranteeNames) {
		t.Errorf("guarantee mapping covers %d of %d guarantees", len(guaranteeClasses), len(guaranteeNames))
	}
	for _, name := range guaranteeNames {
		if _, ok := guaranteeClasses[name]; !ok {
			t.Errorf("guarantee %s has no capability mapping", name)
		}
		if _, ok := classes[name]; ok {
			t.Errorf("guarantee %s is also used as a capability class name", name)
		}
	}
}

func TestSuiteGenerationIsByteStable(t *testing.T) {
	first := t.TempDir()
	second := t.TempDir()
	seedPortableManifest(t, first)
	seedPortableManifest(t, second)
	generateInto(t, first)
	generateInto(t, second)
	if !reflect.DeepEqual(treeDigests(t, first), treeDigests(t, second)) {
		t.Fatal("regenerating the hardened suite is not byte stable")
	}
}

func TestGenerationLeavesThePortableSuiteUntouched(t *testing.T) {
	root := t.TempDir()
	seeded := seedPortableManifest(t, root)
	generateInto(t, root)

	after, err := os.ReadFile(filepath.Join(root, "conformance", "v1", "manifest.json"))
	if err != nil {
		t.Fatalf("read portable manifest after generation: %v", err)
	}
	if string(after) != string(seeded) {
		t.Fatal("generation rewrote the portable rc.5 suite manifest")
	}
	for path := range treeDigests(t, root) {
		if path == "conformance/v1/manifest.json" {
			continue
		}
		if len(path) >= len("conformance/v1/") && path[:len("conformance/v1/")] == "conformance/v1/" {
			t.Errorf("generation wrote %s inside the portable suite", path)
		}
		if path == "release/"+portableProtocolVersion+".json" {
			t.Errorf("generation wrote the portable release metadata")
		}
	}
}

func TestReleaseMetadataPinsBothSuitesHonestly(t *testing.T) {
	root := t.TempDir()
	portable := seedPortableManifest(t, root)
	generateInto(t, root)

	release := readJSONMap(t, filepath.Join(root, "release", hardenedProfileVersion+".json"))
	hardenedManifest, err := os.ReadFile(filepath.Join(root, "conformance", "hardened", "v1", "manifest.json"))
	if err != nil {
		t.Fatalf("read hardened manifest: %v", err)
	}
	hardenedSum := sha256.Sum256(hardenedManifest)
	portableSum := sha256.Sum256(portable)

	pin := release["candidate_protocol_pin"].(map[string]any)
	if pin["manifest_sha256"] != "sha256:"+hex.EncodeToString(hardenedSum[:]) {
		t.Error("hardened pin does not match the hardened manifest")
	}
	baseline := release["portable_baseline"].(map[string]any)
	if baseline["manifest_sha256"] != "sha256:"+hex.EncodeToString(portableSum[:]) {
		t.Error("portable baseline pin does not match the portable manifest")
	}
	if baseline["modified"] != false {
		t.Error("release metadata claims the portable baseline changed")
	}
	if claims := release["claim_v4"].(map[string]any)["claims_emitted"].([]any); len(claims) != 0 {
		t.Error("release metadata fabricates a hardened conformance claim")
	}
	if platforms := release["qualified_platforms"].([]any); len(platforms) != 0 {
		t.Error("release metadata fabricates a qualified platform")
	}
}

func TestEveryPlatformDeclarationIsUnqualified(t *testing.T) {
	for _, item := range platformDeclarations() {
		declaration := item.(map[string]any)
		if declaration["qualification_status"] != "unqualified" {
			t.Errorf("%v is declared qualified without native evidence", declaration["platform"])
		}
		if declaration["native_evidence"] != "absent" {
			t.Errorf("%v claims native evidence", declaration["platform"])
		}
		blocking := declaration["blocking_capability_classes"].([]any)
		if len(blocking) == 0 && declaration["blocking_reason"] != nil {
			t.Errorf("%v states a blocking reason with no blocking class", declaration["platform"])
		}
		if len(blocking) != 0 && declaration["blocking_reason"] == nil {
			t.Errorf("%v blocks without a stated reason", declaration["platform"])
		}
	}
}

// TestNoInDomainActorRunsBeforeDomainEntry is the rule that makes the phase
// list executable. A phase performed by a process inside the build domain
// cannot precede the phase that creates the first such process.
func TestNoInDomainActorRunsBeforeDomainEntry(t *testing.T) {
	entered := false
	exposed := false
	for _, item := range orderedPhases() {
		phase := item.(map[string]any)
		name := phase["name"].(string)
		if phase["actor_in_build_domain"].(bool) && !entered {
			t.Errorf("phase %s is performed inside the domain before %s", name, domainEntryPhase)
		}
		if phase["package_bytes_reach_go_process"].(bool) && !exposed && name != firstPackagePhase {
			t.Errorf("phase %s exposes package bytes before %s", name, firstPackagePhase)
		}
		if name == domainEntryPhase {
			entered = true
		}
		if name == firstPackagePhase {
			exposed = true
		}
	}
	if !entered || !exposed {
		t.Fatal("the ordered phases never enter the build domain or never compile")
	}
}

// TestOrderingInvariantsHoldInThePhaseList checks every published relation
// against the one authoritative list.
func TestOrderingInvariantsHoldInThePhaseList(t *testing.T) {
	for _, item := range orderingInvariants() {
		invariant := item.(map[string]any)
		earlier := phaseIndex(invariant["earlier"].(string))
		later := phaseIndex(invariant["later"].(string))
		if earlier >= later {
			t.Errorf("invariant %s does not hold: %s is not before %s",
				invariant["name"], invariant["earlier"], invariant["later"])
		}
	}
	selfTest := inDomainSelfTest()
	if selfTest["actor"] != inDomainActor {
		t.Error("the in-domain self-test names an actor that is not inside the domain")
	}
	if phaseIndex(selfTest["phase"].(string)) <= phaseIndex(domainEntryPhase) {
		t.Error("the in-domain self-test is ordered before the domain it tests exists")
	}
	if phaseIndex(selfTest["phase"].(string)) >= phaseIndex(firstPackagePhase) {
		t.Error("the in-domain self-test is ordered after package bytes are exposed")
	}
}

// TestProcessGraphAndPhaseListAgree keeps the two views of the same state
// machine from drifting.
func TestProcessGraphAndPhaseListAgree(t *testing.T) {
	assigned := map[string]bool{}
	for _, item := range processGraph() {
		node := item.(map[string]any)
		name := node["node"].(string)
		inDomain := node["in_build_domain"].(bool)
		for _, phase := range node["performs_phases"].([]any) {
			assigned[phase.(string)] = true
			if inDomain && phaseIndex(phase.(string)) < phaseIndex(domainEntryPhase) {
				t.Errorf("node %s performs %s before domain entry", name, phase)
			}
		}
	}
	for _, spec := range phaseSpecs() {
		if !assigned[spec.name] {
			t.Errorf("phase %s has no graph node that performs it", spec.name)
		}
	}
}

func readJSONMap(t *testing.T, path string) map[string]any {
	t.Helper()
	payload, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read %s: %v", path, err)
	}
	var document map[string]any
	if err := json.Unmarshal(payload, &document); err != nil {
		t.Fatalf("parse %s: %v", path, err)
	}
	return document
}

// -----------------------------------------------------------------------
// review-cycle-3 finding R3-1: the trusted-component digest algorithms
// -----------------------------------------------------------------------

// TestComponentFixturesAreDistinctAndStable is the generator side of the
// independent-reproduction argument: this file computes the digests in Go and
// tools/validate_hardened.py recomputes every one of them in Python from the
// published bytes. Two implementations agreeing is what makes content_sha256
// reproducible under one normative contract.
func TestComponentFixturesAreDistinctAndStable(t *testing.T) {
	seen := map[string]string{}
	for _, fixture := range componentFixtures() {
		digest := fixture.digest()
		if len(digest) != len("sha256:")+64 {
			t.Fatalf("fixture %s produced %q", fixture.name, digest)
		}
		if again := fixture.digest(); again != digest {
			t.Errorf("fixture %s is not stable: %s then %s", fixture.name, digest, again)
		}
		if other, ok := seen[digest]; ok {
			t.Errorf("fixture %s aliases %s", fixture.name, other)
		}
		seen[digest] = fixture.name
		if fixture.statement == "" {
			t.Errorf("fixture %s states nothing", fixture.name)
		}
	}
}

// TestTheTwoComponentAlgorithmsAreDomainSeparated proves the empty cases cannot
// collide, which is the weakest point of any length-framed construction.
func TestTheTwoComponentAlgorithmsAreDomainSeparated(t *testing.T) {
	if componentFileDigest("") == componentTreeDigest(nil) {
		t.Fatal("the empty file and the empty tree share one digest")
	}
	if componentFileDigest("x") == componentTreeDigest([]componentEntry{{kind: "F", path: "", payload: "x"}}) {
		t.Fatal("a file digest collides with a single-entry tree over the same bytes")
	}
}

// TestComponentTreeEntryKindIsHashed is the substitution review cycle 3 asked
// for: a regular file holding the referent's exact bytes must not reproduce the
// digest of the tree whose symbolic link it replaced.
func TestComponentTreeEntryKindIsHashed(t *testing.T) {
	base := fixtureFor("capability-probe-suite").digest()
	for _, name := range []string{
		"capability-probe-suite-extra-member",
		"capability-probe-suite-retyped-entry",
		"capability-probe-suite-link-substituted",
	} {
		if fixtureFor(name).digest() == base {
			t.Errorf("fixture %s reproduces the base tree digest", name)
		}
	}
	link := fixtureFor("capability-probe-suite")
	var referent string
	for _, entry := range link.entries {
		if entry.path == "probes/network.probe" {
			referent = entry.payload
		}
	}
	substituted := fixtureFor("capability-probe-suite-link-substituted")
	found := false
	for _, entry := range substituted.entries {
		if entry.path != "probes/current.probe" {
			continue
		}
		found = true
		if entry.kind != "F" || entry.payload != referent {
			t.Errorf("the substitution fixture does not hold the referent's exact bytes as a file")
		}
	}
	if !found {
		t.Fatal("the substitution fixture does not replace the link")
	}
}

// TestComponentTreeDigestIgnoresInputOrder proves the sort is part of the
// construction rather than an accident of how the fixture is written.
func TestComponentTreeDigestIgnoresInputOrder(t *testing.T) {
	forward := []componentEntry{
		{kind: "D", path: "probes", payload: ""},
		{kind: "F", path: "probes/a", payload: "x"},
		{kind: "F", path: "probes/b", payload: "y"},
	}
	reversed := []componentEntry{forward[2], forward[0], forward[1]}
	if componentTreeDigest(forward) != componentTreeDigest(reversed) {
		t.Fatal("component tree digest depends on the order entries are supplied in")
	}
}

// TestEveryTrustedComponentDigestComesFromAFixture keeps invented constants out
// of the record: a component digest nobody can recompute is not an identity.
func TestEveryTrustedComponentDigestComesFromAFixture(t *testing.T) {
	published := map[string]bool{}
	for _, fixture := range componentFixtures() {
		published[fixture.digest()] = true
	}
	for _, platform := range []string{"linux", "macos", "windows"} {
		for _, item := range tcbFor(platform)["trusted_components"].([]any) {
			entry := item.(map[string]any)
			if !published[entry["content_sha256"].(string)] {
				t.Errorf("%s component %v carries a digest no fixture reproduces", platform, entry["name"])
			}
		}
	}
	for _, rotation := range tcbRotations() {
		for _, item := range rotatedRecord(rotation)["trusted_components"].([]any) {
			entry := item.(map[string]any)
			if !published[entry["content_sha256"].(string)] {
				t.Errorf("rotation %s carries a digest no fixture reproduces", rotation.name)
			}
		}
	}
}

// TestEveryComponentAlgorithmMatchesItsKind mirrors the schema relation, so a
// fixture cannot ship a record the shipped schemas reject.
func TestEveryComponentAlgorithmMatchesItsKind(t *testing.T) {
	admitted := map[string][]string{
		"capability-probe":       {componentFileAlgorithm, componentTreeAlgorithm},
		"enforcement-adapter":    {componentFileAlgorithm, componentTreeAlgorithm},
		"helper-executable":      {componentFileAlgorithm},
		"identity-verifier":      {componentFileAlgorithm, componentTreeAlgorithm},
		"installed-package-tree": {componentTreeAlgorithm},
		"interpreter":            {componentFileAlgorithm},
		"sandbox-policy-file":    {componentFileAlgorithm},
		"script":                 {componentFileAlgorithm},
		"shared-library":         {componentFileAlgorithm},
	}
	check := func(label string, components []any) {
		for _, item := range components {
			entry := item.(map[string]any)
			kind := entry["kind"].(string)
			algorithm := entry["algorithm"].(string)
			ok := false
			for _, candidate := range admitted[kind] {
				if candidate == algorithm {
					ok = true
				}
			}
			if !ok {
				t.Errorf("%s: kind %s does not admit %s", label, kind, algorithm)
			}
		}
	}
	check("base", trustedComponents())
	for _, rotation := range tcbRotations() {
		check("rotation "+rotation.name, rotatedRecord(rotation)["trusted_components"].([]any))
	}
}

// TestEveryComponentFacetIsRotated is the coverage review cycle 3 required:
// rotating the trusted_components array is not coverage for the kind, the name,
// the algorithm, the tree membership, an entry type, or a link substitution.
func TestEveryComponentFacetIsRotated(t *testing.T) {
	rotated := map[string][]string{}
	for _, rotation := range tcbRotations() {
		for _, aspect := range rotation.aspects {
			rotated[aspect] = append(rotated[aspect], rotation.name)
		}
	}
	for _, item := range componentAspects {
		if len(rotated[item.aspect]) == 0 {
			t.Errorf("component facet %s is never rotated", item.aspect)
		}
		if item.statement == "" {
			t.Errorf("component facet %s states nothing", item.aspect)
		}
	}
	if len(rotated) != len(componentAspects) {
		t.Errorf("rotations declare %d facets, the coverage table names %d", len(rotated), len(componentAspects))
	}
}

// -----------------------------------------------------------------------
// review-cycle-3 finding R3-2: comparable backend versions and observed hosts
// -----------------------------------------------------------------------

func TestBackendVersionGrammarAndComparison(t *testing.T) {
	for _, value := range []string{"sandbox-2", "sandbox-2.0.0", "cgroup2-6.12", "appcontainer-10.0.26100.1"} {
		if _, _, ok := parseBackendVersion(value); !ok {
			t.Errorf("grammar rejects the legal value %q", value)
		}
	}
	for _, value := range []string{
		"2.0", "cgroup2-06.1", "cgroup2-", "cgroup2-1.2.3.4.5", "latest", "", "Sandbox-2.0",
		// A pattern whose tail is $ admits this one in engines where $ also
		// matches before a final newline, giving one backend two spellings of
		// the same version.
		"sandbox-2.0\n", " sandbox-2.0", "sandbox-2.0 ",
	} {
		if _, _, ok := parseBackendVersion(value); ok {
			t.Errorf("grammar accepts the illegal value %q", value)
		}
	}
	cases := []struct {
		observed, minimum             string
		wantSatisfied, wantComparable bool
	}{
		{"cgroup2-6.12", "cgroup2-6.1", true, true},
		{"cgroup2-6.1", "cgroup2-6.1", true, true},
		{"sandbox-2", "sandbox-2.0.0", true, true},
		{"cgroup2-6.9", "cgroup2-6.10", false, true},
		{"cgroup2-0", "cgroup2-999999", false, true},
		{"cgroup2-6.12", "sandbox-2.0", false, false},
		{"6.1", "cgroup2-6.1", false, false},
	}
	for _, item := range cases {
		satisfied, comparable := backendVersionAtLeast(item.observed, item.minimum)
		if satisfied != item.wantSatisfied || comparable != item.wantComparable {
			t.Errorf("backendVersionAtLeast(%q, %q) = (%v, %v), want (%v, %v)",
				item.observed, item.minimum, satisfied, comparable, item.wantSatisfied, item.wantComparable)
		}
	}
}

// TestEveryFixtureBackendVersionCarriesItsOwnSeries keeps the example records
// inside the relation the schemas enforce.
func TestEveryFixtureBackendVersionCarriesItsOwnSeries(t *testing.T) {
	series := map[string]string{
		"linux-namespace-seccomp-v1":  "cgroup2",
		"macos-sandbox-v1":            "sandbox",
		"windows-appcontainer-job-v1": "appcontainer",
	}
	for _, platform := range []string{"linux", "macos", "windows"} {
		record := tcbFor(platform)
		version := record["backend"].(map[string]any)["version"].(string)
		token, _, ok := parseBackendVersion(version)
		if !ok {
			t.Fatalf("%s observed backend version %q is outside the grammar", platform, version)
		}
		if want := series[record["enforcement_backend"].(string)]; token != want {
			t.Errorf("%s reports the %q series, want %q", platform, token, want)
		}
	}
}

// TestObservedHostFollowsThePlatform is the exact contradiction review cycle 3
// accepted: a linux record whose observed host identity was windows.
func TestObservedHostFollowsThePlatform(t *testing.T) {
	canonical := map[string]string{"linux": "linux", "macos": "darwin", "windows": "windows-nt"}
	for _, platform := range []string{"linux", "macos", "windows"} {
		host := tcbFor(platform)["host"].(map[string]any)
		if host["kind"] != "operating-system" {
			t.Errorf("%s reports host kind %v, but every backend of this revision is an OS mechanism", platform, host["kind"])
		}
		if host["identity"] != canonical[platform] {
			t.Errorf("%s observed %v, want %s", platform, host["identity"], canonical[platform])
		}
	}
}

// TestTheClaimQualifiesUnderItsOwnMinimumVersion checks the example claim is not
// merely well formed but actually satisfies the qualification it declares.
func TestTheClaimQualifiesUnderItsOwnMinimumVersion(t *testing.T) {
	claim := validHardenedClaimV4()
	observed := claim["tcb"].(map[string]any)["backend"].(map[string]any)["version"].(string)
	entry := claim["enforcement_backends"].([]any)[0].(map[string]any)
	satisfied, comparable := backendVersionAtLeast(observed, entry["minimum_version"].(string))
	if !comparable {
		t.Fatalf("the example claim declares a minimum %q incomparable with its observed %q",
			entry["minimum_version"], observed)
	}
	if !satisfied {
		t.Fatalf("the example claim observes %q below its own declared minimum %q",
			observed, entry["minimum_version"])
	}
}

// TestBackendVersionComparisonCasesAreDecidedNotDeclared proves the published
// verdicts follow from the comparison rather than being asserted.
func TestBackendVersionComparisonCasesAreDecidedNotDeclared(t *testing.T) {
	block := backendVersionComparison()
	cases := block["cases"].([]any)
	if len(cases) < 8 {
		t.Fatalf("backend version comparison coverage is too thin: %d cases", len(cases))
	}
	sawBelow, sawEqual, sawAbove, sawIncomparable, sawMalformed := false, false, false, false, false
	for _, item := range cases {
		record := item.(map[string]any)
		satisfied, comparable := backendVersionAtLeast(
			record["observed"].(string), record["minimum"].(string))
		if satisfied != record["satisfied"].(bool) || comparable != record["comparable"].(bool) {
			t.Errorf("case %v publishes a verdict the comparison disproves", record["name"])
		}
		_, _, observedOK := parseBackendVersion(record["observed"].(string))
		_, _, minimumOK := parseBackendVersion(record["minimum"].(string))
		switch {
		case !observedOK || !minimumOK:
			sawMalformed = true
		case !comparable:
			sawIncomparable = true
		case satisfied && record["observed"].(string) == record["minimum"].(string):
			sawEqual = true
		case satisfied:
			sawAbove = true
		default:
			sawBelow = true
		}
	}
	if !sawBelow || !sawEqual || !sawAbove || !sawIncomparable || !sawMalformed {
		t.Errorf("comparison cases miss an outcome: below=%v equal=%v above=%v incomparable=%v malformed=%v",
			sawBelow, sawEqual, sawAbove, sawIncomparable, sawMalformed)
	}
}

// -----------------------------------------------------------------------
// review-cycle-4 finding R4-1: the kernel build identity
// -----------------------------------------------------------------------

func TestHostBuildFixturesAreDistinctAndStable(t *testing.T) {
	seen := map[string]string{}
	for _, fixture := range hostBuildFixtures() {
		digest := fixture.digest()
		if digest != fixture.digest() {
			t.Errorf("host build fixture %s is not stable", fixture.name)
		}
		if other, clash := seen[digest]; clash {
			t.Errorf("host build fixture %s aliases %s", fixture.name, other)
		}
		seen[digest] = fixture.name
		if fixture.statement == "" {
			t.Errorf("host build fixture %s states nothing", fixture.name)
		}
	}
	if len(seen) != len(hostBuildFixtures()) {
		t.Errorf("published %d host build fixtures, %d distinct digests", len(hostBuildFixtures()), len(seen))
	}
}

// TestTwoKernelsWithOneObservedTupleDoNotShareABuildDigest is the finding
// itself: before this revision the two hosts below produced one record.
func TestTwoKernelsWithOneObservedTupleDoNotShareABuildDigest(t *testing.T) {
	base := hostBuildFixtureFor("macos-host-build")
	rebuilt := hostBuildFixtureFor("macos-host-build-recompiled-kernel")
	if base.platform != rebuilt.platform || base.identity != rebuilt.identity ||
		base.version != rebuilt.version || base.identifier() != rebuilt.identifier() {
		t.Fatalf("the recompiled-kernel fixture does not share the base's observed tuple")
	}
	differs := false
	for index := range base.sources {
		if base.sources[index].value != rebuilt.sources[index].value {
			differs = true
		}
	}
	if !differs {
		t.Fatalf("the recompiled-kernel fixture observes the same kernel as the base")
	}
	if base.digest() == rebuilt.digest() {
		t.Errorf("two materially different kernels share one build digest")
	}
}

// TestHashingOnlyTheObservedValuesWouldAlias is what the boundary-shift fixture
// proves: an implementation that hashed the declared source values as one blob
// would give two different observations one build identity.
func TestHashingOnlyTheObservedValuesWouldAlias(t *testing.T) {
	base := hostBuildFixtureFor("macos-host-build")
	shifted := hostBuildFixtureFor("macos-host-build-source-boundary-shift")
	concatenate := func(fixture hostBuildFixture) string {
		out := ""
		for _, item := range fixture.sources {
			out += item.value
		}
		return out
	}
	if concatenate(base) != concatenate(shifted) {
		t.Fatalf("the boundary-shift fixture does not carry the base's concatenated source bytes")
	}
	if base.digest() == shifted.digest() {
		t.Errorf("the declared source values alone decide the kernel build identity")
	}
}

// TestHostBuildDigestIsLengthFramed attacks the framing directly: two field
// lists whose hashed byte stream concatenates identically. Without the uint64be
// lengths, "a|bc" and "ab|c" are one input.
func TestHostBuildDigestIsLengthFramed(t *testing.T) {
	left := []hostBuildSource{source("a", "bc")}
	right := []hostBuildSource{source("ab", "c")}
	if left[0].name+left[0].value != right[0].name+right[0].value {
		t.Fatalf("the probe lists do not concatenate identically")
	}
	if hostBuildDigest("darwin", "25.0.0", "25A123", left) ==
		hostBuildDigest("darwin", "25.0.0", "25A123", right) {
		t.Errorf("two field lists with one concatenation share a build digest")
	}
	// The same property across the leading fields, which are adjacent in the
	// hashed stream: identity || version || identifier.
	if hostBuildDigest("darwin", "25.0", "025A123", nil) ==
		hostBuildDigest("darwin", "25.0025", "A123", nil) {
		t.Errorf("the leading fields are not separated by their own lengths")
	}
	// A truncated observation list is a different input from the full one. The
	// per-field framing already separates them; the hashed count makes the
	// cardinality explicit rather than inferred, and both implementations must
	// agree on it, which is what the cross-implementation fixture check proves.
	full := []hostBuildSource{source("kern.osversion", "25A123"), source("kern.version", "x")}
	if hostBuildDigest("darwin", "25.0.0", "25A123", full) ==
		hostBuildDigest("darwin", "25.0.0", "25A123", full[:1]) {
		t.Errorf("a truncated observation list reproduces the full one")
	}
}

func TestHostBuildDigestIsDomainSeparated(t *testing.T) {
	empty := hostBuildDigest("", "", "", nil)
	if empty == componentFileDigest("") || empty == componentTreeDigest(nil) {
		t.Errorf("a kernel build identity collides with a trusted-component digest")
	}
	sources := []hostBuildSource{source("kern.osversion", "25A123")}
	base := hostBuildDigest("darwin", "25.0.0", "25A123", sources)
	for _, other := range []string{
		hostBuildDigest("linux", "25.0.0", "25A123", sources),
		hostBuildDigest("darwin", "25.1.0", "25A123", sources),
		hostBuildDigest("darwin", "25.0.0", "25A124", sources),
		hostBuildDigest("darwin", "25.0.0", "25A123", nil),
	} {
		if base == other {
			t.Errorf("the observed host tuple is not inside the build digest")
		}
	}
}

func TestEveryHostBuildIdentifierIsItsDeclaredSource(t *testing.T) {
	for _, fixture := range hostBuildFixtures() {
		declaration := hostBuildDeclarationFor(fixture.platform)
		found := ""
		for _, item := range fixture.sources {
			if item.name == declaration.identifierSource {
				found = item.value
			}
		}
		if found == "" || found != fixture.identifier() {
			t.Errorf("host build fixture %s publishes an identifier that is not its %s source",
				fixture.name, declaration.identifierSource)
		}
	}
}

func TestEveryObservedHostBuildComesFromAFixture(t *testing.T) {
	published := map[string]hostBuildFixture{}
	for _, fixture := range hostBuildFixtures() {
		published[fixture.digest()] = fixture
	}
	checked := 0
	for _, platform := range []string{"linux", "macos", "windows"} {
		record := tcbFor(platform)
		host := record["host"].(map[string]any)
		build, ok := host["build"].(map[string]any)
		if !ok {
			t.Fatalf("%s observes no closed kernel build identity", platform)
		}
		if build["algorithm"] != hostBuildAlgorithm {
			t.Errorf("%s uses build algorithm %v", platform, build["algorithm"])
		}
		fixture, known := published[build["content_sha256"].(string)]
		if !known {
			t.Fatalf("%s carries a kernel build digest no fixture reproduces", platform)
		}
		if fixture.platform != platform || fixture.identity != host["identity"] ||
			fixture.version != host["version"] || fixture.identifier() != build["identifier"] {
			t.Errorf("%s publishes a build digest computed over another observed host", platform)
		}
		checked++
	}
	for _, rotation := range tcbRotations() {
		host := rotatedRecord(rotation)["host"].(map[string]any)
		build := host["build"].(map[string]any)
		if _, known := published[build["content_sha256"].(string)]; !known {
			t.Errorf("rotation %s invents a kernel build identity", rotation.name)
		}
		checked++
	}
	if checked < 4 {
		t.Errorf("only %d observed hosts were checked", checked)
	}
}

func TestEveryHostBuildFacetIsRotated(t *testing.T) {
	rotated := map[string][]string{}
	for _, rotation := range tcbRotations() {
		for _, aspect := range rotation.hostAspects {
			rotated[aspect] = append(rotated[aspect], rotation.name)
		}
		if len(rotation.hostAspects) > 0 {
			carries := false
			for _, field := range rotation.fields {
				if field == "host" {
					carries = true
				}
			}
			if !carries {
				t.Errorf("rotation %s claims a kernel build facet without rotating host", rotation.name)
			}
		}
	}
	for _, item := range hostBuildAspects {
		if len(rotated[item.aspect]) == 0 {
			t.Errorf("kernel build facet %s is never rotated", item.aspect)
		}
		if item.statement == "" {
			t.Errorf("kernel build facet %s states nothing", item.aspect)
		}
	}
	if len(rotated) != len(hostBuildAspects) {
		t.Errorf("rotations declare %d kernel build facets, the coverage table names %d",
			len(rotated), len(hostBuildAspects))
	}
}

func TestEveryPlatformDeclaresItsOwnBuildIdentitySources(t *testing.T) {
	declarations := hostBuildDeclarations()
	for _, platform := range []string{"linux", "macos", "windows"} {
		declaration, ok := declarations[platform]
		if !ok {
			t.Fatalf("%s declares no build-identity sources", platform)
		}
		if len(declaration.sources) == 0 {
			t.Errorf("%s declares an empty build-identity source list", platform)
		}
		named := false
		seen := map[string]bool{}
		for _, name := range declaration.sources {
			if seen[name] {
				t.Errorf("%s declares %s twice", platform, name)
			}
			seen[name] = true
			if name == declaration.identifierSource {
				named = true
			}
		}
		if !named {
			t.Errorf("%s reads its identifier from a source the digest does not cover", platform)
		}
	}
}

// -----------------------------------------------------------------------
// review-cycle-4 finding R4-2: end-of-operation re-verification
// -----------------------------------------------------------------------

func TestTeardownPrecedesIdentityReverification(t *testing.T) {
	teardown := phaseIndex("domain-teardown")
	reverify := phaseIndex("identity-reverification")
	publication := phaseIndex("publication")
	if teardown >= reverify {
		t.Errorf("the trusted computing base is re-verified before the domain is destroyed and joined")
	}
	if reverify >= publication {
		t.Errorf("the trusted computing base is re-verified after publication")
	}
	specs := phaseSpecs()
	if specs[reverify].actor != "manager-parent" {
		t.Errorf("re-verification is performed by %s", specs[reverify].actor)
	}
	if !specs[reverify].skippedOnCacheHit || specs[publication].skippedOnCacheHit {
		t.Errorf("an exact cache hit must skip re-verification and still publish")
	}
}

func TestReverificationCoversEveryMutableTcbMember(t *testing.T) {
	constant := map[string]bool{"record_version": true, "hardened_profile": true, "execution_policy": true}
	want := map[string]bool{"source-snapshot": true}
	for _, item := range tcbBoundFields() {
		field := item.(map[string]any)["field"].(string)
		if !constant[field] {
			want[field] = true
		}
	}
	got := map[string]bool{}
	for _, member := range reverifiedMembers() {
		got[member] = true
	}
	if !reflect.DeepEqual(want, got) {
		t.Errorf("re-verification covers %v, the closed record needs %v", reverifiedMembers(), want)
	}
	check := identityReverification()
	if check["runs_after_phase"] != "domain-teardown" {
		t.Errorf("re-verification runs after %v", check["runs_after_phase"])
	}
	if check["partial_reverification_permitted"] != false ||
		check["restating_earlier_record_permitted"] != false {
		t.Errorf("re-verification admits a partial or restated record")
	}
	if check["comparison"] != "byte-identical-record-and-digest" {
		t.Errorf("re-verification compares %v", check["comparison"])
	}
}

func TestEveryReverifiedMemberHasAnOmissionCase(t *testing.T) {
	omitted := map[string]bool{}
	kinds := map[string]bool{}
	for _, entry := range reverificationCases() {
		item := entry.(map[string]any)
		kinds[item["kind"].(string)] = true
		if item["kind"] == "omitted-member" {
			omitted[item["omitted_member"].(string)] = true
		}
		if item["published"] != false || item["cache_entry_written"] != false ||
			item["marker_updated"] != false {
			t.Errorf("reverification case %v still changes reusable state", item["name"])
		}
	}
	for _, member := range reverifiedMembers() {
		if !omitted[member] {
			t.Errorf("re-verified member %s has no omission case", member)
		}
	}
	for _, kind := range []string{"omitted-member", "phase-order", "restated-record", "changed-member"} {
		if !kinds[kind] {
			t.Errorf("reverification cases do not cover the %s failure kind", kind)
		}
	}
}
